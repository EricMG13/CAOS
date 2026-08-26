from __future__ import annotations

import io
from typing import Any

import copy

from ..contracts import DeliverableDraftRequest, clean_json, digest
from ..ledgers import ModelLedger, PublicationLedger, SourceCatalog
from .recipes import validate_recipe
from .templates import template_for


GENERATED_OUTPUT_FIELDS = {
    "revenue",
    "adjusted_ebitda_calc",
    "adjusted_ebitda_margin",
    "fcf",
    "cumulative_fcf",
    "cash_and_equivalents",
    "accessible_liquidity",
    "liquidity_headroom",
    "total_debt_reported",
    "net_debt",
    "total_leverage",
    "net_leverage",
    "interest_coverage",
    "covenant_headroom",
}
GENERATED_TABLE_FIELDS = {
    "annual_model": GENERATED_OUTPUT_FIELDS,
    "liquidity": {
        "cash_and_equivalents",
        "accessible_liquidity",
        "liquidity_headroom",
    },
    "leverage": {
        "total_debt_reported",
        "net_debt",
        "total_leverage",
        "net_leverage",
        "interest_coverage",
    },
    "covenants": {"covenant_headroom"},
}


def _selected_outputs(value: Any, fields: set[str]) -> Any:
    if not isinstance(value, dict):
        return None
    selected: dict[str, Any] = {}
    for key, item in value.items():
        if key in fields:
            selected[key] = copy.deepcopy(item)
        elif isinstance(item, dict):
            nested = _selected_outputs(item, fields)
            if nested:
                selected[key] = nested
    return selected


class DeliverableService:
    """Validate and version one shared structured draft per case/pathway."""

    def __init__(
        self,
        publications: PublicationLedger,
        sources: SourceCatalog,
        models: ModelLedger,
        scenario_service: Any | None = None,
    ) -> None:
        self.publications = publications
        self.sources = sources
        self.models = models
        self.scenario_service = scenario_service

    def _model_eligibility(self, case_id: str) -> dict[str, Any]:
        current_build = next(
            (
                build
                for build in self.models.list_builds(case_id)
                if build.get("status") == "READY"
            ),
            None,
        )
        head = self.models.get_revision_head(case_id)
        active = (
            head
            if head is not None
            and current_build is not None
            and head.get("build_id") == current_build.get("id")
            else None
        )
        return {
            "active_revision": self._revision_identity(active),
            "application_build": self._build_identity(current_build),
            "fallback_acknowledgement_required": active is None
            and current_build is not None,
            "default_model_selection": (
                {
                    "kind": "ANALYST_REVISION",
                    "build_id": active["build_id"],
                    "revision_id": active["id"],
                }
                if active is not None
                else None
            ),
        }

    @staticmethod
    def _build_identity(build: dict[str, Any] | None) -> dict[str, Any] | None:
        if build is None:
            return None
        return {
            "build_id": build["id"],
            "accepted_snapshot_id": build.get("accepted_snapshot_id"),
            "input_fingerprint": build.get("input_fingerprint"),
            "payload_digest": build.get("payload_digest"),
            "status": build.get("status"),
        }

    @staticmethod
    def _revision_identity(revision: dict[str, Any] | None) -> dict[str, Any] | None:
        if revision is None:
            return None
        return {
            "revision_id": revision["id"],
            "build_id": revision["build_id"],
            "revision_number": revision.get("revision_number"),
            "signed_by": revision.get("signed_by"),
            "signed_at": revision.get("signed_at"),
        }

    def read(self, case_id: str, pathway: str) -> dict[str, Any]:
        template = copy.deepcopy(template_for(pathway))
        history = self.publications.list_deliverable_revisions(case_id, pathway)
        return {
            "template": template,
            "current": copy.deepcopy(history[-1]) if history else None,
            "history": copy.deepcopy(history),
            "model_eligibility": self._model_eligibility(case_id),
        }

    def get_by_id(self, case_id: str, deliverable_id: str) -> dict[str, Any] | None:
        revision = self.publications.get_deliverable_revision(deliverable_id)
        if revision is None or revision.get("case_id") != case_id:
            return None
        return revision

    def _validate_model(
        self, case_id: str, selection: dict[str, Any] | None
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if selection is None:
            return None, None
        eligibility = self._model_eligibility(case_id)
        if selection["kind"] == "ANALYST_REVISION":
            active = eligibility["active_revision"]
            if (
                active is None
                or active["revision_id"] != selection["revision_id"]
                or active["build_id"] != selection["build_id"]
            ):
                raise ValueError("DELIVERABLE_MODEL_REVISION_STALE")
            revision = self.models.get_revision(selection["revision_id"])
            if (
                revision is None
                or revision.get("case_id") != case_id
                or revision.get("id") != selection["revision_id"]
                or revision.get("build_id") != selection["build_id"]
            ):
                raise ValueError("DELIVERABLE_MODEL_REVISION_STALE")
            return active, revision
        if eligibility["active_revision"] is not None:
            raise ValueError("DELIVERABLE_APPLICATION_BUILD_FALLBACK_NOT_ELIGIBLE")
        build = eligibility["application_build"]
        if build is None or build["build_id"] != selection["build_id"]:
            raise ValueError("DELIVERABLE_MODEL_BUILD_STALE")
        model_record = self.models.get_build(selection["build_id"])
        if (
            model_record is None
            or model_record.get("case_id") != case_id
            or model_record.get("id") != selection["build_id"]
            or model_record.get("status") != "READY"
        ):
            raise ValueError("DELIVERABLE_MODEL_BUILD_STALE")
        return build, model_record

    @staticmethod
    def _pinned_model_identity(
        selection: dict[str, Any] | None, record: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if selection is None or record is None:
            return None
        if selection["kind"] == "ANALYST_REVISION":
            return {
                "kind": selection["kind"],
                "revision_id": record["id"],
                "build_id": record["build_id"],
                "accepted_snapshot_id": record["accepted_snapshot_id"],
                "build_input_fingerprint": record["build_input_fingerprint"],
                "build_payload_digest": record["build_payload_digest"],
                "registry_version": record["registry_version"],
                "registry_digest": record["registry_digest"],
                "calculation_contract_version": record[
                    "calculation_contract_version"
                ],
                "assumptions_digest": record["assumptions_digest"],
                "outputs_digest": record["outputs_digest"],
            }
        return {
            "kind": selection["kind"],
            "build_id": record["id"],
            "accepted_snapshot_id": record["accepted_snapshot_id"],
            "build_input_fingerprint": record["input_fingerprint"],
            "build_payload_digest": record["payload_digest"],
            "calculation_runtime": copy.deepcopy(record["calculation_runtime"]),
        }

    def _validate_citations(
        self, case_id: str, citations: list[dict[str, Any]]
    ) -> None:
        for citation in citations:
            source = self.sources.get_source(citation["source_id"])
            if source is None or source.get("case_id") != case_id:
                raise ValueError("EVIDENCE_CASE_MISMATCH")
            if source.get("withdrawn"):
                raise ValueError("EVIDENCE_SOURCE_WITHDRAWN")
            available = {block.get("block_id") for block in source.get("blocks", [])}
            if not set(citation["block_ids"]).issubset(available):
                raise ValueError("EVIDENCE_BLOCK_MISMATCH")

    def _validate_blocks(
        self,
        case_id: str,
        pathway: str,
        blocks: list[dict[str, Any]],
        model_record: dict[str, Any] | None,
        model_identity: dict[str, Any] | None,
    ) -> dict[str, Any]:
        template = template_for(pathway)
        if len({block["block_id"] for block in blocks}) != len(blocks):
            raise ValueError("DELIVERABLE_BLOCK_ID_DUPLICATE")
        if len({block["slot_id"] for block in blocks}) != len(blocks):
            raise ValueError("DELIVERABLE_SLOT_ID_DUPLICATE")
        required = template["blocks"]
        if len(blocks) < len(required):
            raise ValueError("DELIVERABLE_REQUIRED_BLOCK_MISSING")
        for expected, actual in zip(required, blocks, strict=False):
            if (
                actual["block_id"] != expected["block_id"]
                or actual["slot_id"] != expected["slot_id"]
                or actual["kind"] != expected["kind"]
            ):
                raise ValueError("DELIVERABLE_TEMPLATE_ORDER_INVALID")
        optional_policies = {
            policy["kind"]: policy for policy in template["optional_blocks"]
        }
        optional_counts: dict[str, int] = {}
        last_optional_order = 0
        generated: dict[str, Any] = {}
        for index, block in enumerate(blocks):
            policy = None
            if index >= len(required):
                policy = optional_policies.get(block["kind"])
                if policy is None:
                    raise ValueError("DELIVERABLE_SLOT_INVALID")
                if policy["order"] < last_optional_order:
                    raise ValueError("DELIVERABLE_TEMPLATE_ORDER_INVALID")
                optional_count = optional_counts.get(block["kind"], 0) + 1
                if (
                    optional_count > policy["max_items"]
                    or block["slot_id"]
                    != f"{policy['slot_stem']}.{optional_count:02d}"
                ):
                    raise ValueError("DELIVERABLE_SLOT_INVALID")
                optional_counts[block["kind"]] = optional_count
                last_optional_order = policy["order"]
                if policy["model_dependent"] and (
                    model_record is None or model_identity is None
                ):
                    raise ValueError("DELIVERABLE_MODEL_REQUIRED_FOR_BLOCK")
            citations = block.get("citations", [])
            self._validate_citations(case_id, citations)
            if block["kind"] == "GENERATED_CHART":
                generated[block["block_id"]] = {
                    "kind": block["kind"],
                    "model_digest": digest(model_identity),
                    "recipe": validate_recipe(
                        block["recipe"], GENERATED_OUTPUT_FIELDS
                    ),
                    "payload_digest": model_identity["build_payload_digest"],
                }
            elif block["kind"] in {"GENERATED_METRIC", "GENERATED_TABLE"}:
                if block["kind"] == "GENERATED_METRIC":
                    fields = set(block["metric_ids"])
                    if not fields.issubset(GENERATED_OUTPUT_FIELDS):
                        raise ValueError("DELIVERABLE_GENERATED_FIELD_INVALID")
                else:
                    allowed = GENERATED_TABLE_FIELDS.get(block["table_id"])
                    fields = set(block["field_ids"])
                    if allowed is None or not fields.issubset(allowed):
                        raise ValueError("DELIVERABLE_GENERATED_FIELD_INVALID")
                outputs = model_record.get("outputs")
                generated[block["block_id"]] = {
                    "kind": block["kind"],
                    "model_digest": digest(model_identity),
                    "status": "READY" if isinstance(outputs, dict) else "UNAVAILABLE",
                    "outputs": _selected_outputs(outputs, fields),
                    "payload_digest": model_identity["build_payload_digest"],
                }
            elif block["kind"] == "MODEL_APPENDIX":
                generated[block["block_id"]] = {
                    "kind": block["kind"],
                    "model_digest": digest(model_identity),
                    "status": "READY",
                    "payload_digest": model_identity["build_payload_digest"],
                }
            elif block["kind"] == "SCENARIO_EXHIBIT":
                scenario = block["scenario"]
                if digest(scenario) != block["scenario_digest"]:
                    raise ValueError("SCENARIO_EXHIBIT_DIGEST_INVALID")
                base_revision_id = scenario["base_revision_id"]
                if (
                    model_identity["kind"] == "ANALYST_REVISION"
                    and base_revision_id != model_identity["revision_id"]
                ) or (
                    model_identity["kind"] == "APPLICATION_BUILD"
                    and base_revision_id is not None
                ):
                    raise ValueError("SCENARIO_EXHIBIT_IDENTITY_INVALID")
                build = self.models.get_build(scenario["build_id"])
                current_build = next(
                    (
                        candidate
                        for candidate in self.models.list_builds(case_id)
                        if candidate.get("status") == "READY"
                    ),
                    None,
                )
                runtime = (build or {}).get("calculation_runtime") or {}
                if (
                    scenario["case_id"] != case_id
                    or scenario["build_id"] != model_identity["build_id"]
                    or build is None
                    or current_build is None
                    or current_build.get("id") != build.get("id")
                    or build.get("case_id") != case_id
                    or build.get("status") != "READY"
                    or runtime.get("assumption_registry_version")
                    != scenario["registry_version"]
                    or runtime.get("assumption_registry_digest")
                    != scenario["registry_digest"]
                    or digest(scenario["effective_assumptions"])
                    != scenario["assumptions_digest"]
                    or digest(scenario["outputs"]) != scenario["outputs_digest"]
                ):
                    raise ValueError("SCENARIO_EXHIBIT_IDENTITY_INVALID")
                if base_revision_id is not None:
                    revision = self.models.get_revision(base_revision_id)
                    if (
                        revision is None
                        or revision.get("id") != base_revision_id
                        or revision.get("case_id") != case_id
                        or revision.get("build_id") != build.get("id")
                    ):
                        raise ValueError("SCENARIO_EXHIBIT_IDENTITY_INVALID")
                if self.scenario_service is None:
                    raise ValueError("SCENARIO_EXHIBIT_VALIDATOR_UNAVAILABLE")
                recalculated = self.scenario_service.scenario(
                    case_id,
                    scenario["build_id"],
                    scenario["registry_version"],
                    scenario["registry_digest"],
                    copy.deepcopy(block["shocks"]),
                    base_revision_id=scenario["base_revision_id"],
                    draft_generation=scenario["draft_generation"],
                )
                if (
                    recalculated.get("scenario") != scenario
                    or recalculated.get("scenario_digest")
                    != block["scenario_digest"]
                ):
                    raise ValueError("SCENARIO_EXHIBIT_CALCULATION_MISMATCH")
                generated[block["block_id"]] = {
                    **copy.deepcopy(block),
                    "model_digest": digest(model_identity),
                    "model_identity": {
                        "accepted_snapshot_id": build["accepted_snapshot_id"],
                        "build_input_fingerprint": build["input_fingerprint"],
                        "build_payload_digest": build["payload_digest"],
                        "calculation_contract_version": runtime[
                            "calculation_contract_version"
                        ],
                    },
                }
        return generated

    def save(
        self,
        case_id: str,
        pathway: str,
        actor: str,
        request: DeliverableDraftRequest,
    ) -> dict[str, Any]:
        template = template_for(pathway)
        if (
            request.template_id != template["template_id"]
            or request.template_version != template["template_version"]
        ):
            raise ValueError("DELIVERABLE_TEMPLATE_STALE")
        dumped = request.model_dump(mode="json")
        selection = dumped["model_selection"]
        _eligible_identity, model_record = self._validate_model(case_id, selection)
        model_identity = self._pinned_model_identity(selection, model_record)
        blocks = dumped["blocks"]
        generated = self._validate_blocks(
            case_id, pathway, blocks, model_record, model_identity
        )
        content = {
            "template_id": request.template_id,
            "template_version": request.template_version,
            "model_selection": selection,
            "model_identity": model_identity,
            "blocks": blocks,
            "generated_blocks": generated,
        }
        self.publications.append_deliverable_revision(
            case_id,
            pathway,
            actor,
            request.expected_version,
            {
                "template_id": request.template_id,
                "template_version": request.template_version,
                "digest": digest(content),
                "content": content,
            },
        )
        return self.read(case_id, pathway)


def model_report_identity(
    model_build: dict[str, Any] | None,
    snapshot: dict[str, Any],
    *,
    include_export: bool = False,
) -> dict[str, Any] | None:
    if model_build is None:
        return None
    if not isinstance(snapshot, dict):
        raise ValueError("MODEL_SNAPSHOT_MISMATCH")
    if (
        model_build.get("status") != "READY"
        or model_build.get("case_id") != snapshot.get("case_id")
        or model_build.get("accepted_snapshot_id") != snapshot.get("id")
        or not isinstance(model_build.get("payload_digest"), str)
        or not isinstance(model_build.get("input_fingerprint"), str)
    ):
        raise ValueError("MODEL_SNAPSHOT_MISMATCH")
    identity = {
        "build_id": model_build["id"],
        "accepted_snapshot_id": model_build["accepted_snapshot_id"],
        "payload_digest": model_build["payload_digest"],
        "input_fingerprint": model_build["input_fingerprint"],
    }
    export = model_build.get("export") or {}
    if include_export:
        if (
            export.get("status") != "READY"
            or not isinstance(export.get("sha256"), str)
            or not isinstance(export.get("size"), int)
        ):
            raise ValueError("MODEL_EXPORT_MISMATCH")
        identity["export"] = {
            "sha256": export["sha256"],
            "size": export["size"],
            "filename": export.get("filename"),
        }
    return identity


def report_input_fingerprint(
    snapshot: dict[str, Any],
    thesis: dict[str, Any],
    recommendations: dict[str, Any],
    model_identity: dict[str, Any] | None,
) -> str:
    return digest(
        clean_json(
            {
                "snapshot": snapshot,
                "thesis": thesis,
                "recommendations": recommendations,
                "model": model_identity,
            }
        )
    )


def freeze_report(
    publications: PublicationLedger,
    case_id: str,
    actor: str,
    snapshot: dict[str, Any],
    thesis: dict[str, Any],
    recommendations: dict[str, Any],
    model_build: dict[str, Any] | None | bool = None,
    *,
    include_model_export: bool = False,
) -> dict[str, Any]:
    if not snapshot:
        raise ValueError("SNAPSHOT_REQUIRED")
    if not thesis or not recommendations:
        raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")
    if recommendations.get("stale") or any(
        not row.get("recommendation") for row in recommendations.get("rows", [])
    ):
        raise ValueError("RECOMMENDATION_MATRIX_NOT_ELIGIBLE")
    if recommendations.get("accepted_snapshot_id") != snapshot["id"]:
        raise ValueError("RECOMMENDATION_SNAPSHOT_MISMATCH")
    if model_build is False:
        model_build = None
    if model_build is True or (
        model_build is not None and not isinstance(model_build, dict)
    ):
        raise ValueError("MODEL_BUILD_INVALID")
    if include_model_export and model_build is None:
        raise ValueError("MODEL_EXPORT_MISMATCH")
    model_identity = model_report_identity(
        model_build, snapshot, include_export=include_model_export
    )
    content = {
        "case_id": case_id,
        "snapshot_id": snapshot["id"],
        "snapshot_digest": digest(snapshot),
        "thesis_version": thesis["version"],
        "recommendation_version": recommendations["version"],
        "include_model": model_identity is not None,
        "model": model_identity,
    }
    content["input_fingerprint"] = report_input_fingerprint(
        snapshot, thesis, recommendations, model_identity
    )
    preview_digest = digest(content)
    report = {
        "case_id": case_id,
        "digest": preview_digest,
        "preview_digest": preview_digest,
        "input_fingerprint": content["input_fingerprint"],
        "snapshot_digest": content["snapshot_digest"],
        "content": content,
        "markdown": render_markdown(
            snapshot, thesis, recommendations, preview_digest, model_identity
        ),
    }
    return publications.freeze_report(case_id, actor, report)


def render_markdown(
    snapshot: dict[str, Any],
    thesis: dict[str, Any],
    recommendations: dict[str, Any],
    report_digest: str,
    model_identity: dict[str, Any] | None = None,
) -> str:
    lines = [
        "# CAOS Credit Snapshot",
        "",
        f"Snapshot digest: `{digest(snapshot)}`",
        f"Report digest: `{report_digest}`",
        f"Accepted at: {snapshot.get('accepted_at', 'unavailable')}",
        "",
        "## Analyst thesis",
        "",
        thesis["core_thesis"],
        "",
        "## Recommendation matrix",
        "",
        "| Instrument | Recommendation | Primary | Rationale |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {row['instrument']} | {row['recommendation']} | {'Yes' if row.get('primary') else 'No'} | {row['rationale']} |"
        for row in recommendations["rows"]
    )
    lines.extend(
        [
            "",
            "## CP-MODEL",
            "",
            (
                f"Included build `{model_identity['build_id']}` with worksheet payload "
                f"`{model_identity['payload_digest']}`."
                if model_identity
                else "No CP-MODEL build included in this report."
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Evidence & QA",
            "",
            "Every conclusion is bound to the accepted snapshot and its immutable artifact lineage.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_pdf(report: dict[str, Any]) -> bytes:
    # Minimal valid single-page PDF; the frozen snapshot digest is embedded in
    # plain text so a consumer can verify the PDF/Markdown identity.
    text = f"CAOS Credit Snapshot\nDigest: {report['snapshot_digest']}\nReport: {report['digest']}"
    stream = f"BT /F1 10 Tf 50 740 Td ({text.replace('(', '[').replace(')', ']')}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.write(
        b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    )
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return output.getvalue()


def render_xlsx(report: dict[str, Any]) -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for XLSX export") from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Credit Snapshot"
    sheet.append(["Field", "Value"])
    sheet.append(["Report digest", report["digest"]])
    sheet.append(["Accepted snapshot digest", report["snapshot_digest"]])
    model = report.get("content", {}).get("model")
    sheet.append(
        [
            "Model appendix",
            (
                f"{model['build_id']} | payload {model['payload_digest']}"
                if model
                else "Not included"
            ),
        ]
    )
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
