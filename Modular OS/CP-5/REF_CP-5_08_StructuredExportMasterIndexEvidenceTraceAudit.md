<!-- REF_CP-5_08 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="08" name="Structured Export, Master Index, and Evidence Trace Audit">
<input>T5.1; all module .docx appendices (A–E); CP-5B evidence trace outputs.</input>
<gate>Step 7 complete.</gate>

## Instructions
1. Execute Audit Lanes 6 (Evidence Trace), 7 (Schema), and 8 (Export) across all audited modules.
2. **Evidence Trace (Lane 6):** Check CP-5B classification of material conclusions. Identify orphan claims (VE-015). Flag weak-lineage and untraced conclusions. Verify traceability map consistency with module outputs.
3. **Schema (Lane 7):** Verify structured records use correct record_type prefixes (cp1_, cp2_, etc.). Check required fields populated or correctly null. Verify schema_version, issuer_id/deterministic_entity_key. Confirm numeric values stored correctly (null not zero, percentages as decimals).
4. **Export (Lane 8):** Verify all required appendices present (A–E). Check export manifest completeness. Verify master index fields populated. Confirm .docx is sole output artifact (no separate JSON/JSONL).
5. For each finding: record Severity, Module, Export Component, Defect, Required Fix, CP-DB/Database Impact.
6. Severity: Critical if blocks ingestion; Material if data quality; Minor if metadata/formatting.

## Output
T5.8: `Severity`|`Module`|`Export Component`|`Defect`|`Required Fix`|`CP-DB / Database Impact`
</step_reference>
