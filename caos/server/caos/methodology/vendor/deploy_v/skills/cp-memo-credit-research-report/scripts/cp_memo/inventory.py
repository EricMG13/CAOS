"""Validate a host-materialized issuer-run snapshot without analysing it."""

from __future__ import annotations

import hashlib
import importlib
import re
from collections import defaultdict
from typing import Any, Iterable

from .domain import (
    ELIGIBLE,
    EXCLUDED,
    LIMITATIONS_ONLY,
    ArtifactRecord,
    Candidate,
    InventoryResult,
    RunAnchor,
)

MAX_ARTIFACTS = 256
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
LIMITATION_MODULES = frozenset({"CP-0", "CP-5"})
NON_SUBSTANTIVE = frozenset({"CP-OS", "CP-MODEL", "CP-MEMO"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class InventoryError(ValueError):
    pass


def _validator():
    for name in ("validate_handoff", "tools.validate_handoff"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    raise InventoryError("validate_handoff is unavailable")


def _credit_os_runtime():
    try:
        envelope = importlib.import_module("credit_os_v.envelope")
        routing = importlib.import_module("credit_os_v.routing")
    except ImportError as exc:
        raise InventoryError("CP-OS — Credit OS route/envelope runtime is unavailable") from exc
    return envelope, routing


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _candidate(entry: dict[str, Any], validator) -> Candidate:
    if not isinstance(entry, dict) or set(entry) - {"name", "text", "sha256"}:
        raise InventoryError("each artifact must contain only name, text, and optional sha256")
    name = entry.get("name")
    text = entry.get("text")
    if not isinstance(name, str) or not name or "/" in name or "\\" in name:
        raise InventoryError("artifact name must be a basename")
    if not isinstance(text, str):
        raise InventoryError(f"{name}: text must be a string")
    size = len(text.encode("utf-8"))
    if size > MAX_ARTIFACT_BYTES:
        raise InventoryError(f"{name}: artifact exceeds byte limit")
    sha256 = _digest(text)
    declared_sha = entry.get("sha256")
    if declared_sha is not None and (not isinstance(declared_sha, str) or declared_sha != sha256):
        raise InventoryError(f"{name}: supplied sha256 does not match content")
    result = validator.validate_text(text, filename=name)
    return Candidate(
        name=name,
        text=text,
        sha256=sha256,
        fields=result.fields,
        validation_exit_code=result.exit_code,
        validation_errors=tuple(result.errors),
        identity_mismatches=tuple(result.identity_mismatches),
    )


def _catalog_modules(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    modules = catalog.get("modules")
    if not isinstance(modules, list):
        raise InventoryError("verified catalog has no module list")
    result: dict[str, dict[str, Any]] = {}
    for module in modules:
        if not isinstance(module, dict):
            raise InventoryError("verified catalog contains a malformed module")
        module_id = _clean_string(module.get("module_id"))
        display = _clean_string(module.get("display"))
        module_name = _clean_string(module.get("module_name"))
        if not module_id or not display or not module_name or module_id in result:
            raise InventoryError("verified catalog module identity is invalid or duplicated")
        if display != f"{module_id} — {module_name}":
            raise InventoryError(f"verified catalog display mismatch for {module_id}")
        result[module_id] = module
    return result


def _run_id(fields: dict[str, Any] | None) -> str | None:
    if not fields:
        return None
    return _clean_string(fields.get("credit_os_run_id")) or _clean_string(fields.get("run_id"))


def _profile(fields: dict[str, Any]) -> str | None:
    return _clean_string(fields.get("credit_os_profile_id")) or _clean_string(fields.get("profile_id"))


def _selection(fields: dict[str, Any]) -> str | None:
    return _clean_string(fields.get("credit_os_selection_id")) or _clean_string(fields.get("selection_id"))


def _authority(fields: dict[str, Any]) -> str | None:
    value = _clean_string(fields.get("credit_os_authority_bundle_sha256"))
    return value if value and SHA256_RE.fullmatch(value) else None


def _base_record(candidate: Candidate, catalog_by_id: dict[str, dict[str, Any]], disposition: str, reason: str) -> ArtifactRecord:
    fields = candidate.fields or {}
    module_id = _clean_string(fields.get("module_id"))
    catalog_module = catalog_by_id.get(module_id or "")
    module_name = _clean_string(catalog_module.get("module_name")) if catalog_module else None
    display = _clean_string(catalog_module.get("display")) if catalog_module else None
    score = fields.get("confidence_score")
    return ArtifactRecord(
        name=candidate.name,
        sha256=candidate.sha256,
        module_id=module_id,
        module_name=module_name,
        display=display,
        run_id=_run_id(fields),
        issuer_id=_clean_string(fields.get("issuer_id")),
        issuer_name=_clean_string(fields.get("issuer_name")),
        reporting_period=_clean_string(fields.get("reporting_period")),
        analysis_date=_clean_string(fields.get("analysis_date")),
        profile_id=_profile(fields),
        selection_id=_selection(fields),
        route_node_id=_clean_string(fields.get("credit_os_route_node_id")),
        qa_status=_clean_string(fields.get("qa_status")),
        confidence_score=score if isinstance(score, int) and not isinstance(score, bool) else None,
        confidence_band=_clean_string(fields.get("confidence_band")),
        disposition=disposition,
        reason=reason,
        text=candidate.text,
    )


def _catalog_route(catalog: dict[str, Any], profile_id: str, selection_id: str) -> dict[str, dict[str, Any]]:
    try:
        nodes = catalog["profiles"][profile_id]["pathways"][selection_id]["nodes"]
    except (KeyError, TypeError) as exc:
        raise InventoryError(f"unknown profile/selection: {profile_id}/{selection_id}") from exc
    if not isinstance(nodes, list) or not nodes or nodes[0].get("module_id") != "CP-0":
        raise InventoryError("selected live route does not begin with CP-0 — SourceReadiness")
    return {str(node.get("route_node_id")): node for node in nodes}


def _anchor_from_cp0(cp0: Candidate, expected_authority: str) -> RunAnchor:
    fields = cp0.fields or {}
    values = {
        "issuer_id": _clean_string(fields.get("issuer_id")),
        "issuer_name": _clean_string(fields.get("issuer_name")),
        "run_id": _run_id(fields),
        "profile_id": _profile(fields),
        "selection_id": _selection(fields),
        "reporting_period": _clean_string(fields.get("reporting_period")),
        "analysis_date": _clean_string(fields.get("analysis_date")),
        "authority_digest": _authority(fields),
    }
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise InventoryError(f"CP-0 — SourceReadiness anchor is missing {', '.join(missing)}")
    if values["authority_digest"] != expected_authority:
        raise InventoryError("run authority digest does not match the verified package authority")
    return RunAnchor(**values)  # type: ignore[arg-type]


def _identity_problem(candidate: Candidate, anchor: RunAnchor, catalog_by_id: dict[str, dict[str, Any]], route: dict[str, dict[str, Any]]) -> str | None:
    fields = candidate.fields or {}
    module_id = _clean_string(fields.get("module_id"))
    module = catalog_by_id.get(module_id or "")
    if module is None:
        return "module is not a live verified catalog owner"
    if module.get("surface_role") != "canonical_markdown_output":
        return "module does not own a canonical Markdown handoff"
    if _clean_string(fields.get("module_name")) != module.get("module_name"):
        return "handoff module name does not match the verified catalog"
    exact = {
        "run_id": _run_id(fields),
        "issuer_id": _clean_string(fields.get("issuer_id")),
        "issuer_name": _clean_string(fields.get("issuer_name")),
        "reporting_period": _clean_string(fields.get("reporting_period")),
        "profile_id": _profile(fields),
        "selection_id": _selection(fields),
        "authority_digest": _authority(fields),
    }
    for key, observed in exact.items():
        if observed != getattr(anchor, key):
            return f"{key} does not match the selected run anchor"
    route_node_id = _clean_string(fields.get("credit_os_route_node_id"))
    node = route.get(route_node_id or "")
    if node is None or node.get("module_id") != module_id:
        return "route occurrence does not match the selected live pathway"
    return None


def inventory_snapshot(snapshot: dict[str, Any], catalog: dict[str, Any], authority_digest: str, requested_run_id: str | None = None) -> InventoryResult:
    """Return a complete, conservative disposition for a materialized snapshot."""
    if not isinstance(snapshot, dict) or set(snapshot) - {"artifacts", "run_id"}:
        raise InventoryError("snapshot must contain artifacts and optional run_id only")
    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise InventoryError("snapshot artifacts must be a non-empty list")
    if len(artifacts) > MAX_ARTIFACTS:
        raise InventoryError("snapshot exceeds artifact count limit")
    total = sum(len(str(item.get("text", "")).encode("utf-8")) for item in artifacts if isinstance(item, dict))
    if total > MAX_TOTAL_BYTES:
        raise InventoryError("snapshot exceeds total byte limit")
    catalog_by_id = _catalog_modules(catalog)
    validator = _validator()
    candidates = tuple(_candidate(item, validator) for item in artifacts)
    candidate_run_ids = tuple(_run_id(item.fields) for item in candidates)
    run_ids = sorted({run_id for run_id in candidate_run_ids if run_id})
    chosen = requested_run_id if requested_run_id is not None else snapshot.get("run_id")
    if chosen is not None and (not isinstance(chosen, str) or chosen not in run_ids):
        return InventoryResult("RUN_NOT_FOUND", None, (), tuple(run_ids), "requested run_id is not present")
    if chosen is None and len(run_ids) != 1:
        status = "SELECT_RUN" if run_ids else "NO_COHERENT_RUN"
        return InventoryResult(status, None, (), tuple(run_ids), "select one exact run_id" if run_ids else "no run identity found")
    chosen = str(chosen or run_ids[0])
    in_run = [item for item, run_id in zip(candidates, candidate_run_ids) if run_id == chosen]
    cp0 = [item for item in in_run if (item.fields or {}).get("module_id") == "CP-0" and item.validation_exit_code == 0]
    if len(cp0) != 1:
        return InventoryResult("NO_COHERENT_RUN", None, (), tuple(run_ids), "selected run requires exactly one valid CP-0 — SourceReadiness anchor")
    try:
        anchor = _anchor_from_cp0(cp0[0], authority_digest)
        route = _catalog_route(catalog, anchor.profile_id, anchor.selection_id)
        envelope_runtime, routing_runtime = _credit_os_runtime()
        route_runtime = routing_runtime.Route(catalog, anchor.profile_id, anchor.selection_id)
    except InventoryError as exc:
        return InventoryResult("NO_COHERENT_RUN", None, (), tuple(run_ids), str(exc))
    except (TypeError, ValueError) as exc:
        return InventoryResult("NO_COHERENT_RUN", None, (), tuple(run_ids), str(exc))

    provisional: list[ArtifactRecord] = []
    eligible_candidates: list[Candidate] = []
    for candidate, run_id in zip(candidates, candidate_run_ids):
        if run_id != chosen:
            provisional.append(_base_record(candidate, catalog_by_id, EXCLUDED, "belongs to another run"))
            continue
        if candidate.validation_exit_code == 3:
            provisional.append(_base_record(candidate, catalog_by_id, EXCLUDED, "qa_status is Blocked"))
            continue
        if candidate.validation_exit_code != 0:
            detail = "; ".join(candidate.validation_errors + candidate.identity_mismatches) or "canonical validation failed"
            provisional.append(_base_record(candidate, catalog_by_id, EXCLUDED, detail))
            continue
        problem = _identity_problem(candidate, anchor, catalog_by_id, route)
        if problem:
            provisional.append(_base_record(candidate, catalog_by_id, EXCLUDED, problem))
            continue
        eligible_candidates.append(candidate)

    by_occurrence: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in eligible_candidates:
        by_occurrence[_clean_string((candidate.fields or {}).get("credit_os_route_node_id")) or ""].append(candidate)
    unique_by_occurrence: dict[str, Candidate] = {}
    ambiguous_occurrences: list[str] = []
    for occurrence, records in sorted(by_occurrence.items()):
        if len(records) > 1:
            ambiguous_occurrences.append(occurrence)
            for candidate in records:
                provisional.append(_base_record(candidate, catalog_by_id, EXCLUDED, f"AMBIGUOUS_RETRY: multiple valid artifacts claim {occurrence}"))
            continue
        unique_by_occurrence[occurrence] = records[0]

    accepted: dict[str, str] = {}
    cp0_route = route_runtime.by_module["CP-0"]["route_node_id"]
    cp0_fields = cp0[0].fields or {}
    for node in route_runtime.nodes:
        occurrence = str(node["route_node_id"])
        candidate = unique_by_occurrence.get(occurrence)
        if candidate is None:
            continue
        fields = candidate.fields or {}
        module_id = str(fields.get("module_id") or "")
        try:
            upstream = routing_runtime.expected_upstream_digests(
                route_runtime, occurrence, accepted
            )
            accepted_cp0 = envelope_runtime.ZERO_SHA256 if module_id == "CP-0" else accepted.get(cp0_route)
            if accepted_cp0 is None:
                raise ValueError("downstream artifact is missing accepted CP-0 — SourceReadiness lineage")
            envelope_runtime.reproduce_and_match(
                fields,
                run_id=anchor.run_id,
                profile_id=anchor.profile_id,
                selection_id=anchor.selection_id,
                route_node_id=occurrence,
                module_id=module_id,
                module_name=str(node["module_name"]),
                expected_output_filename=candidate.name,
                authority_bundle_sha256=anchor.authority_digest,
                accepted_cp0_sha256=accepted_cp0,
                required_upstream_digests=upstream,
                parent_run_id=_clean_string(cp0_fields.get("credit_os_parent_run_id")),
                upgrade_source_sha256=_clean_string(cp0_fields.get("credit_os_upgrade_source_sha256")),
                ordinal=None,
            )
        except (TypeError, ValueError, getattr(envelope_runtime, "EnvelopeError")) as exc:
            provisional.append(_base_record(candidate, catalog_by_id, EXCLUDED, f"lineage/envelope validation failed: {exc}"))
            continue
        accepted[occurrence] = candidate.sha256
        disposition = LIMITATIONS_ONLY if module_id in LIMITATION_MODULES else ELIGIBLE
        provisional.append(_base_record(candidate, catalog_by_id, disposition, "accepted active live-host handoff"))

    provisional.sort(key=lambda item: (item.module_id or "~", item.name))
    has_substantive = any(
        item.disposition == ELIGIBLE and item.module_id not in NON_SUBSTANTIVE
        for item in provisional
    )
    if not has_substantive:
        return InventoryResult("NO_SUBSTANTIVE_HANDOFF", anchor, tuple(provisional), tuple(run_ids), "no eligible substantive handoff exists")
    if ambiguous_occurrences:
        return InventoryResult(
            "NO_COHERENT_RUN",
            anchor,
            tuple(provisional),
            tuple(run_ids),
            "ambiguous valid route occurrence(s): " + ", ".join(ambiguous_occurrences),
        )
    return InventoryResult("READY", anchor, tuple(provisional), tuple(run_ids), "")
