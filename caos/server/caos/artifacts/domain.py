from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from ..contracts import RecommendationMatrixRequest, ThesisRequest, digest
from ..methodology.canonical import (
    CANONICAL_MODULES,
    CanonicalModuleRunner,
    is_canonical_full_credit,
)
from ..methodology.cpdr import confidence_inputs, render_cpdr_markdown, validate_cpdr_payload
from ..ledgers import PublicationLedger, RunLedger, SourceCatalog
from ..store import now_iso


def save_thesis(
    publications: PublicationLedger,
    case_id: str,
    actor: str,
    request: ThesisRequest,
) -> dict[str, Any]:
    value = request.model_dump(mode="json")
    return publications.append_thesis(
        case_id,
        actor,
        request.expected_version,
        {key: item for key, item in value.items() if key != "expected_version"},
    )


def save_recommendations(
    publications: PublicationLedger,
    case_id: str,
    actor: str,
    request: RecommendationMatrixRequest,
    accepted_snapshot_id: str | None = None,
) -> dict[str, Any]:
    value = request.model_dump(mode="json")
    value["accepted_snapshot_id"] = accepted_snapshot_id
    return publications.append_recommendations(
        case_id,
        actor,
        request.expected_version,
        {key: item for key, item in value.items() if key != "expected_version"},
    )


def save_report_inputs(
    publications: PublicationLedger,
    case_id: str,
    actor: str,
    thesis_request: ThesisRequest,
    recommendation_request: RecommendationMatrixRequest,
    accepted_snapshot_id: str | None = None,
) -> dict[str, Any]:
    return publications.save_report_inputs(
        case_id,
        actor,
        thesis_request.model_dump(mode="json"),
        recommendation_request.model_dump(mode="json"),
        accepted_snapshot_id,
    )


def create_note(
    publications: PublicationLedger, case_id: str, actor: str, body: str
) -> dict[str, Any]:
    return publications.create_note(case_id, actor, body)


def promote_note(
    publications: PublicationLedger, case_id: str, note_id: str, actor: str
) -> dict[str, Any]:
    return publications.promote_note(case_id, note_id, actor)


def create_assumption(
    publications: PublicationLedger,
    case_id: str,
    actor: str,
    statement: str,
    evidence_ids: list[str],
    affected_module_ids: list[str],
    supporting_claim: str = "",
    conflicting_claim: str = "",
) -> dict[str, Any]:
    return publications.create_assumption(
        case_id,
        actor,
        statement,
        evidence_ids,
        affected_module_ids,
        supporting_claim,
        conflicting_claim,
    )


def build_snapshot_payload(runs: RunLedger, sources: SourceCatalog, run: dict[str, Any], bundle: Any | None = None) -> dict[str, Any]:
    if run.get("status") != "succeeded" or len(run.get("nodes", [])) != len(run.get("node_ids", [])):
        raise ValueError("RUN_NOT_READY")
    canonical_required = is_canonical_full_credit(run.get("plan") or {})
    canonical_runner = CanonicalModuleRunner(bundle) if canonical_required and bundle is not None else None
    canonical_artifacts: dict[str, dict[str, Any]] = {}
    artifacts = []
    for node in run["nodes"]:
        artifact = runs.get_artifact(node.get("artifact_id")) if node.get("artifact_id") else None
        if (
            node.get("status") != "succeeded"
            or not artifact
            or artifact.get("run_id") != run.get("id")
            or artifact.get("case_id") not in {None, run.get("case_id")}
            or artifact.get("module_id") != node.get("module_id")
            or artifact.get("digest") != digest(artifact.get("payload"))
        ):
            raise ValueError("RUN_NOT_READY")
        if node.get("module_id") == "CP-DR" and not cpdr_artifact_is_valid(runs, sources, run, node, artifact, bundle):
            raise ValueError("RUN_NOT_READY")
        if node.get("module_id") in CANONICAL_MODULES and canonical_required:
            if not canonical_artifact_is_valid(
                runs,
                sources,
                run,
                node,
                artifact,
                canonical_runner,
            ):
                raise ValueError("RUN_NOT_READY")
            canonical_artifacts[node["module_id"]] = artifact
        artifacts.append(artifact)
    if canonical_required:
        try:
            if canonical_runner is None or set(canonical_artifacts) != set(CANONICAL_MODULES):
                raise ValueError("RUN_NOT_READY")
            canonical_runner.validate_bundle(canonical_artifacts, run["id"])
        except Exception as exc:
            raise ValueError("RUN_NOT_READY") from exc
    source_set = sources.source_set(run["plan"].get("source_set_id"))
    if not source_set:
        raise ValueError("SOURCE_SET_CHANGED")
    return {
        "case_id": run["case_id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"] if source_set else None,
        "source_set_version": source_set["version"] if source_set else None,
        "artifacts": [{"id": artifact["id"], "module_id": artifact["module_id"], "digest": artifact["digest"]} for artifact in artifacts],
        "accepted_at": now_iso(),
    }


def canonical_artifact_is_valid(
    runs: RunLedger,
    sources: SourceCatalog,
    run: dict[str, Any],
    node: dict[str, Any],
    artifact: dict[str, Any],
    runner: CanonicalModuleRunner | None,
) -> bool:
    try:
        if runner is None:
            return False
        runner.bundle.verify()
        module_id = node["module_id"]
        envelope = artifact["payload"]
        expected_keys = {
            "schema_version",
            "module_id",
            "confidence_inputs",
            "host_confidence",
            "canonical_output",
            "methodology",
            "source_set",
            "upstream_artifacts",
            "evidence_refs",
        }
        generation = run.get("canonical_generation") or {}
        source_set = sources.source_set(run["plan"].get("source_set_id"))
        case = runs.get_case(run["case_id"])
        if (
            not isinstance(envelope, dict)
            or set(envelope) != expected_keys
            or not source_set
            or not case
            or generation.get("reporting_period") != run["created_at"][:10]
            or generation.get("phase") != "complete"
            or set(generation.get("completed_modules") or []) != set(CANONICAL_MODULES)
        ):
            return False
        expected_upstream = []
        for dependency in node.get("dependencies", []):
            dependency_node = next(
                (item for item in run["nodes"] if item.get("module_id") == dependency),
                None,
            )
            dependency_artifact = (
                runs.get_artifact(dependency_node.get("artifact_id"))
                if dependency_node
                else None
            )
            if not dependency_artifact:
                return False
            expected_upstream.append(
                {
                    "module_id": dependency,
                    "artifact_id": dependency_artifact["id"],
                    "digest": dependency_artifact["digest"],
                }
            )
        expected_fingerprint = digest(
            {
                "plan": run["plan"]["plan_digest"],
                "module": module_id,
                "source_set": source_set,
                "source_ids": list(source_set["source_ids"]),
                "upstream_artifacts": expected_upstream,
            }
        )
        if (
            artifact.get("case_id") != run["case_id"]
            or artifact.get("run_id") != run["id"]
            or artifact.get("module_id") != module_id
            or artifact.get("input_fingerprint") != expected_fingerprint
            or envelope["schema_version"] != "caos.canonical.artifact.v1"
            or envelope["module_id"] != module_id
            or envelope["methodology"]
            != {
                "build_id": runner.bundle.build_id,
                "authority_digest": digest(runner.authority(module_id)),
            }
            or envelope["source_set"]
            != {
                "id": source_set["id"],
                "version": source_set["version"],
                "digest": digest(source_set),
            }
            or envelope["upstream_artifacts"] != expected_upstream
        ):
            return False
        evidence_refs = envelope["evidence_refs"]
        if not isinstance(evidence_refs, list) or any(not isinstance(row, dict) for row in evidence_refs):
            return False
        evidence_keys = [(row.get("source_id"), row.get("block_id")) for row in evidence_refs]
        if len(evidence_keys) != len(set(evidence_keys)):
            return False
        expected_evidence = []
        for row in evidence_refs:
            source = sources.get_source(row.get("source_id"))
            blocks = (source or {}).get("blocks") or []
            matching = [
                block
                for block in blocks
                if isinstance(block, dict) and block.get("block_id") == row.get("block_id")
            ]
            if (
                not source
                or source.get("case_id") != run["case_id"]
                or source.get("withdrawn")
                or source["id"] not in source_set["source_ids"]
                or len(matching) != 1
            ):
                return False
            block = matching[0]
            expected_evidence.append(
                {
                    "source_id": source["id"],
                    "block_id": block["block_id"],
                    "source_digest": source["sha256"],
                    "origin_family": source["sha256"],
                    "authority_class": "unclassified",
                    "locator": json.dumps(
                        block.get("locator"), sort_keys=True, separators=(",", ":")
                    ),
                    "extractor_version": str(block.get("extractor_version")),
                    "confidence": str(block.get("confidence")),
                }
            )
        if evidence_refs != sorted(
            expected_evidence, key=lambda item: (item["source_id"], item["block_id"])
        ):
            return False
        runner.validate_model_sources(
            artifact.get("markdown", ""),
            {item["source_id"] for item in expected_evidence},
        )
        confidence = runner.confidence(module_id, envelope["confidence_inputs"])
        if envelope["host_confidence"] != confidence or confidence["qa_status"] != "Passed":
            return False
        markdown = artifact.get("markdown")
        filename = artifact.get("filename")
        if not isinstance(markdown, str) or not isinstance(filename, str):
            return False
        validation = runner.validate_handoff(
            module_id,
            markdown,
            run_id=run["id"],
            reporting_period=generation["reporting_period"],
            filename=filename,
        )
        fields = validation.fields or {}
        canonical_output = {
            "filename": filename,
            "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        }
        return bool(
            fields.get("issuer_name") == case["issuer"]
            and str(fields.get("issuer_id")) == run["case_id"].replace("_", "-")
            and fields.get("confidence_score") == confidence["confidence_score"]
            and fields.get("confidence_band") == confidence["confidence_band"]
            and envelope["canonical_output"] == canonical_output
            and artifact.get("digest") == digest(envelope)
        )
    except Exception:
        return False


def cpdr_artifact_is_valid(
    runs: RunLedger,
    sources: SourceCatalog,
    run: dict[str, Any],
    node: dict[str, Any],
    artifact: dict[str, Any],
    bundle: Any | None,
) -> bool:
    try:
        if bundle is None:
            return False
        bundle.verify()
        envelope = artifact["payload"]
        expected_keys = {
            "schema_version", "module_id", "transport", "host_confidence", "canonical_output",
            "methodology", "source_set", "upstream_artifacts",
        }
        if not isinstance(envelope, dict) or set(envelope) != expected_keys:
            return False
        source_set = sources.source_set(run["plan"].get("source_set_id"))
        research = run.get("research") or {}
        approved_plan = research.get("proposed_plan")
        brief = research.get("brief")
        if not source_set or not isinstance(approved_plan, dict) or not isinstance(brief, dict):
            return False
        expected_upstream = []
        for dependency in node.get("dependencies", []):
            dependency_node = next((item for item in run["nodes"] if item.get("module_id") == dependency), None)
            dependency_artifact = runs.get_artifact(dependency_node.get("artifact_id")) if dependency_node else None
            if not dependency_artifact:
                return False
            expected_upstream.append(
                {"module_id": dependency, "artifact_id": dependency_artifact["id"], "digest": dependency_artifact["digest"]}
            )
        approved_hash = research.get("approved_plan_hash")
        expected_scope = {
            "type": brief.get("scope_type"),
            "key": brief.get("scope_key"),
            "source_mode": brief.get("source_mode"),
        }
        expected_fingerprint = digest(
            {
                "plan": run["plan"]["plan_digest"],
                "module": "CP-DR",
                "source_set": source_set,
                "source_ids": list(source_set["source_ids"]),
                "upstream_artifacts": expected_upstream,
            }
        )
        if (
            approved_hash != f"sha256:{digest(approved_plan)}"
            or approved_hash != research.get("proposed_plan_hash")
            or approved_plan.get("methodology_build_id") != bundle.build_id
            or approved_plan.get("brief_digest") != digest(brief)
            or approved_plan.get("source_set") != {"id": source_set["id"], "version": source_set["version"]}
            or approved_plan.get("scope") != expected_scope
            or approved_plan.get("upstream_artifacts") != expected_upstream
            or artifact.get("case_id") != run["case_id"]
            or artifact.get("run_id") != run["id"]
            or artifact.get("module_id") != "CP-DR"
            or artifact.get("input_fingerprint") != expected_fingerprint
        ):
            return False
        host_identity = {
            "module_id": "CP-DR",
            "run_id": run["id"],
            "case_id": run["case_id"],
            "profile_id": run["plan"]["profile_id"],
            "selection_id": run["plan"]["selection_id"],
            "source_set_id": source_set["id"],
            "source_set_version": source_set["version"],
            "approved_plan_hash": approved_hash,
            "upstream_digests": [item["digest"] for item in expected_upstream],
            "scope_type": brief["scope_type"],
            "scope_key": brief["scope_key"],
            "subject_name": brief["subject_name"],
            "research_question": brief["research_question"],
            "reporting_period": brief["as_of_date"],
            "source_mode": "supplied_only",
        }
        transport = envelope["transport"]
        if not isinstance(transport, dict):
            return False
        pinned_sources: dict[str, dict[str, Any]] = {}
        for source_id in source_set["source_ids"]:
            source = sources.get_source(source_id)
            source_digest = (source or {}).get("sha256")
            blocks = (source or {}).get("blocks")
            if (
                not source
                or source.get("case_id") != run["case_id"]
                or source.get("withdrawn")
                or not isinstance(source_digest, str)
                or len(source_digest) != 64
                or any(character not in "0123456789abcdef" for character in source_digest)
                or not isinstance(blocks, list)
                or len({block.get("block_id") for block in blocks if isinstance(block, dict)}) != len(blocks)
            ):
                return False
            pinned_sources[source_id] = source
        returned_evidence: dict[tuple[str, str], dict[str, str]] = {}
        for row in transport.get("evidence", []):
            if not isinstance(row, dict):
                return False
            source = pinned_sources.get(row.get("source_id"))
            if source is None:
                return False
            blocks = [item for item in source.get("blocks", []) if item.get("block_id") == row.get("block_id")]
            if len(blocks) != 1:
                return False
            block = blocks[0]
            source_digest = source["sha256"]
            returned_evidence[(source["id"], block["block_id"])] = {
                "source_digest": source_digest,
                "origin_family": source_digest,
                "authority_class": "unclassified",
                "locator": json.dumps(block.get("locator"), sort_keys=True, separators=(",", ":")),
                "extractor_version": str(block.get("extractor_version")),
                "confidence": str(block.get("confidence")),
            }
        workstream_ids = {item["id"] for item in approved_plan.get("workstreams", [])}
        payload = validate_cpdr_payload(
            transport,
            host_identity,
            workstream_ids,
            returned_evidence,
            approved_plan,
            brief,
        )
        if payload.model_dump(mode="json") != transport:
            return False
        confidence = bundle.cpdr_confidence(confidence_inputs(payload, returned_evidence))
        if envelope["host_confidence"] != confidence:
            return False
        filename, markdown = render_cpdr_markdown(payload, confidence, run["created_at"][:10], expected_upstream)
        canonical_output = envelope["canonical_output"]
        validation = bundle.validate_cpdr_handoff(markdown, filename, run["id"], brief["as_of_date"])
        return bool(
            envelope["schema_version"] == "caos.cpdr.artifact.v1"
            and envelope["module_id"] == "CP-DR"
            and envelope["methodology"]
            == {"build_id": bundle.build_id, "approved_plan_hash": approved_hash}
            and envelope["source_set"]
            == {"id": source_set["id"], "version": source_set["version"], "digest": digest(source_set)}
            and envelope["upstream_artifacts"] == expected_upstream
            and isinstance(canonical_output, dict)
            and set(canonical_output) == {"filename", "markdown_sha256"}
            and canonical_output == {
                "filename": filename,
                "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            }
            and artifact.get("filename") == filename
            and artifact.get("markdown") == markdown
            and artifact.get("digest") == digest(envelope)
            and not validation.identity_mismatches
            and not validation.errors
            and validation.exit_code == 0
        )
    except Exception:
        return False


def snapshot_diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if not previous:
        return {"changed": True, "added": current.get("artifacts", []), "removed": [], "source_set_changed": True}
    old = {item["module_id"]: item["digest"] for item in previous.get("artifacts", [])}
    new = {item["module_id"]: item["digest"] for item in current.get("artifacts", [])}
    return {
        "changed": old != new or previous.get("source_set_id") != current.get("source_set_id"),
        "added": [{"module_id": k, "digest": v} for k, v in new.items() if k not in old],
        "removed": [{"module_id": k, "digest": v} for k, v in old.items() if k not in new],
        "modified": [{"module_id": k, "before": old[k], "after": v} for k, v in new.items() if k in old and old[k] != v],
        "source_set_changed": previous.get("source_set_id") != current.get("source_set_id"),
    }


def recommendation_state(
    runs: RunLedger, case_id: str, value: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not value:
        return None
    result = copy.deepcopy(value)
    accepted = accepted_snapshot(runs, case_id)
    if (
        result.get("accepted_snapshot_id")
        and accepted
        and result["accepted_snapshot_id"] != accepted["id"]
    ):
        result["stale"] = True
        result["stale_reasons"] = ["ACCEPTED_SNAPSHOT_CHANGED"]
    return result


def accepted_snapshot(runs: RunLedger, case_id: str) -> dict[str, Any] | None:
    case = runs.get_case(case_id)
    snapshot_id = (case.get("visible_snapshot_id") or case.get("accepted_snapshot_id")) if case else None
    return runs.get_snapshot(snapshot_id) if snapshot_id else None


def latest_accepted_snapshot(runs: RunLedger, case_id: str) -> dict[str, Any] | None:
    case = runs.get_case(case_id)
    return runs.get_snapshot(case["accepted_snapshot_id"]) if case and case.get("accepted_snapshot_id") else None
