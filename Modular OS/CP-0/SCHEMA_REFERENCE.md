<!-- CP-0 Schema Reference (Tier 3) | 2026-06-02 -->
<schema_reference module="CP-0" tier="3">
## Tables
| ID | Name | Key Columns |
|----|------|-------------|
| T1 | Input Gate | run_id, issuer, period, source_status, limitation |
| T2 | File & Quality Registry | file_id, name, type, category, date, entity, confidence, quality_label, reliability, contents, downstream, usability, limitation |
| T3 | Source Hierarchy | source_id, type, tier, period, entity, downstream_use |
| T4 | Content-to-Module Map | file_id, content_basis, downstream_module, mapping_status, readiness_effect |
| T5 | Gaps/Conflicts | issue_id, type, severity, affected_modules, credit_impact, remediation |
| T6 | Evidence Trace | claim_id, source_id, locator, extraction_type, validation_status |
| T7 | Master Index State | master_index_id, issuer, module, status, date, mode, export_status |
## 13 Output Sections: Scope/Input Gate, File Registry, Entity Universe, Period/Version Map, Source Hierarchy, Content Map, Gaps, Conflicts, Quality Risk, Readiness, Master Index, MODULE_HANDOFF, Export
## QA: Sources classified | Tiers assigned | Gaps identified | Routing produced | No M-prefix | Appendices A-E
## Export: [Issuer]_CP-0_[YYYYMMDD].docx
</schema_reference>
