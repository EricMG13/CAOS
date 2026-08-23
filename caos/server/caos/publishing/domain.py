from __future__ import annotations

import copy
import io
from typing import Any

from ..contracts import clean_json, digest
from ..store import MemoryStore, now_iso


def freeze_report(store: MemoryStore, case_id: str, actor: str, snapshot: dict[str, Any], thesis: dict[str, Any], recommendations: dict[str, Any], include_model: bool) -> dict[str, Any]:
    if not snapshot:
        raise ValueError("SNAPSHOT_REQUIRED")
    if not thesis or not recommendations:
        raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")
    if recommendations.get("stale") or any(not row.get("recommendation") for row in recommendations.get("rows", [])):
        raise ValueError("RECOMMENDATION_MATRIX_NOT_ELIGIBLE")
    if recommendations.get("accepted_snapshot_id") != snapshot["id"]:
        raise ValueError("RECOMMENDATION_SNAPSHOT_MISMATCH")
    if include_model:
        raise ValueError("CP_MODEL_AUTHORITY_BLOCKED")
    content = {
        "case_id": case_id,
        "snapshot_id": snapshot["id"],
        "snapshot_digest": digest(snapshot),
        "thesis_version": thesis["version"],
        "recommendation_version": recommendations["version"],
        "include_model": False,
    }
    content["input_fingerprint"] = digest(clean_json({"snapshot": snapshot, "thesis": thesis, "recommendations": recommendations, "include_model": include_model}))
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
        "markdown": render_markdown(store, snapshot, thesis, recommendations, preview_digest),
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


def render_markdown(store: MemoryStore, snapshot: dict[str, Any], thesis: dict[str, Any], recommendations: dict[str, Any], report_digest: str) -> str:
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
    sheet.append(["Model appendix", "Blocked pending signed Deploy V CP-MODEL correction"])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
