<!-- REF_CP-3B_01 (T2) | 2026-06-03 -->
<step_reference module="CP-3B" step="01" name="Instrument Data Gate">
<input>All available source materials: CP-3 RV output, capital structure data (credit agreements, indentures, lender presentations), instrument terms, market data (pricing/spread/yield/DM), CP-4/CP-4C legal/recovery outputs, CP-3D refinancing/LME outputs, CP-0/CP-1/CP-2 fundamentals.</input>
<gate>Always executes. This IS the gate check. BLOCKING: CP-3 RV analysis must be available AND capital structure must include seniority/subordination. If not met: qa_status = Blocked, limitation_flag = UPSTREAM_DEPENDENCY_MISSING. STOP.</gate>

## Instructions
1. Verify Gate 1: CP-3 RV analysis available.
2. Verify Gate 2: Capital structure includes seniority/subordination detail.
3. If either gate fails: set qa_status = Blocked, limitation_flag = UPSTREAM_DEPENDENCY_MISSING, STOP.
4. Catalogue all sources: record source_document_id, source_document_name, source_quality, period, entity_covered, data_supplied, limitation, downstream_use.
5. Assess market-data quality (pricing date, source, quote quality, staleness).
6. Assess legal-data quality (credit agreement, indenture, intercreditor availability).
7. Assess recovery-data quality (CP-4/CP-4C availability, CP-3D refinancing/LME outputs).
8. Flag draft, unsigned, stale, incomplete, or conflicting documents — reduce confidence.
9. Assign Module Status: Full Run / Ready with Limitations / Blocked.

## Output
T3B.1: `source_document_id`|`source_document_name`|`source_quality`|`period`|`entity_covered`|`data_supplied`|`limitation`|`downstream_use`
+ Module Status: Full Run / Ready with Limitations / Blocked
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
