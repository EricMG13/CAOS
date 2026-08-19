<!-- REF_CP-5B_01 (T2) | 2026-06-03 -->
<step_reference module="CP-5B" step="01" name="Traceability Source Gate and Readiness">
<input>CP-5 QA output, all substantive module outputs (.docx with appendices), source files, citation map, issuer entity keys, reporting periods, evidence-trace exports.</input>
<gate>Always executes. This IS the gate check. BLOCKING: CP-5 QA output or at least one substantive module output must be available. If no auditable inputs: Module Status = Blocked, STOP.</gate>

## Instructions
1. Confirm availability of: CP-5 QA output, substantive module outputs, source files, citation map, issuer entity keys, reporting periods, evidence-trace exports, and structured-output feasibility.
2. Build Source Register: for each source document, record source_document_id, source_document_name, source_quality, period, entity covered, data supplied, limitation, and downstream use.
3. Assign Module Status:
   - **Full Run:** All target inputs available with CP-5 QA clearance.
   - **Ready with Limitations:** Some inputs available but missing appendices, incomplete source packages, or CP-5 QA not yet cleared.
   - **Blocked:** No substantive module outputs or CP-5 QA output available. Output blocked message and STOP.
4. Determine Traceability Scope: Top 5 (default) or Full (if user requests).
5. Record: files and modules used, missing required inputs, citation limitations, entity-key status (issuer_id available / deterministic_entity_key generated / entity key missing).

## Output
T5B.1: `Source Document ID`|`Source Document Name`|`Source Quality`|`Period`|`Entity Covered`|`Data Supplied`|`Limitation`|`Downstream Use`
+ Module Status: Full Run / Ready with Limitations / Blocked
+ Traceability Scope: Top 5 / Full
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
