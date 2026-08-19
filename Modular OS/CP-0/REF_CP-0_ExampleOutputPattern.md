<!-- REF_CP-0_ExampleOutputPattern.md (T2 Example Library) | 2026-06-10 | Ported from Agent Files: CP-0__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt -->


================================================================================
FILE: CP-0__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt
MODULE: CP-0 — SourceReadiness
STATUS: UPDATED (vNext)
MECHANICAL CHANGES APPLIED: MC-1, MC-2 (export alignment)
GOVERNING CONTRACT: CP_GLOBAL_AGENT_INSTRUCTIONS_v3.2.txt
PURPOSE: Example output structure and appendix template for CP-0
================================================================================

EXAMPLE OUTPUT STRUCTURE

- Source Register (table: source_id, source_name, type, quality_label,
  coverage, gaps)
- Readiness Summary (overall readiness, critical gaps, source count)
- Routing Recommendation (recommended modules, blocked modules, reasons)

APPENDIX TEMPLATE (vNext Standard)

Appendix A — MODULE_HANDOFF
Fenced ```json block: CP_MODULE_HANDOFF_JSON
Contains: common_envelope, module_payload (CP-0 schema), qa_result

Appendix B — Evidence Trace and Source Registry
Fenced ```json blocks: CP_EVIDENCE_TRACE_JSON, CP_SOURCE_REGISTRY_JSON

Appendix C — QA / Validation Status
Fenced ```json block: CP_QA_VALIDATION_JSON

Appendix D — Export Manifest
Fenced ```json block: CP_EXPORT_MANIFEST_JSON

Appendix E — Gaps, Conflicts, and Downstream Consumers
Fenced ```json block: CP_GAPS_CONFLICTS_DOWNSTREAM_JSON

EXPORT CONTRACT

Single .docx only. Full contract defined in
CP-0__SUPPORT__WORKFLOW_OUTPUT_QA_EXPORT_CONTRACT.txt.
