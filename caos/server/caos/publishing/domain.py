from __future__ import annotations

import copy
import io
from typing import Any

from ..contracts import clean_json, digest
from ..store import MemoryStore, now_iso


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
    store: MemoryStore,
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
    if recommendations.get("stale") or any(not row.get("recommendation") for row in recommendations.get("rows", [])):
        raise ValueError("RECOMMENDATION_MATRIX_NOT_ELIGIBLE")
    if recommendations.get("accepted_snapshot_id") != snapshot["id"]:
        raise ValueError("RECOMMENDATION_SNAPSHOT_MISMATCH")
    if model_build is False:
        model_build = None
    if model_build is True or (model_build is not None and not isinstance(model_build, dict)):
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
        "id": store._id("report"),
        "case_id": case_id,
        "created_by": actor,
        "created_at": now_iso(),
        "status": "PENDING_APPROVAL",
        "digest": preview_digest,
        "preview_digest": preview_digest,
        "input_fingerprint": content["input_fingerprint"],
        "snapshot_digest": content["snapshot_digest"],
        "content": content,
        "markdown": render_markdown(
            store, snapshot, thesis, recommendations, preview_digest, model_identity
        ),
    }
    with store.lock:
        previous_report = store.reports.get(case_id)
        audit_start = len(store.audit)
        store.reports[case_id] = report
        store.audit_event("report.frozen", actor, case_id=case_id, report_id=report["id"])
        try:
            store.persist()
        except Exception:
            if previous_report is None:
                store.reports.pop(case_id, None)
            else:
                store.reports[case_id] = previous_report
            del store.audit[audit_start:]
            raise
    return copy.deepcopy(report)


def render_markdown(store: MemoryStore, snapshot: dict[str, Any], thesis: dict[str, Any], recommendations: dict[str, Any], report_digest: str, model_identity: dict[str, Any] | None = None) -> str:
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
    lines.extend(f"| {row['instrument']} | {row['recommendation']} | {'Yes' if row.get('primary') else 'No'} | {row['rationale']} |" for row in recommendations["rows"])
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
    lines.extend(["", "## Evidence & QA", "", "Every conclusion is bound to the accepted snapshot and its immutable artifact lineage."])
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
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    output.write(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.write(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
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
