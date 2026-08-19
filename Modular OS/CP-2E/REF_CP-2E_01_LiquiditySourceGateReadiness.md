<!-- REF_CP-2E_01 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="01" name="Liquidity Source Gate & Readiness">
<input>All available liquidity, cash-flow, debt-amortization, maturity, revolver, covenant, working-capital, capex, cash-interest, cash-tax evidence; CP-0 registry; CP-1/CP-1B/CP-2/CP-2B/CP-2D/CP-2F/CP-3D/CP-4C outputs where available.</input>
<gate>Always executes. This IS the gate check.</gate>

## Instructions
1. Catalogue all available source materials for liquidity and cash-flow bridge analysis.
2. For each source, record: source_document_id, source_document_name, source_quality, period, entity_covered, data_supplied, limitation, and downstream_use.
3. Confirm issuer entity keys and structured-output feasibility.
4. Identify missing required inputs: cash balances, revolver data, debt schedules, cash-flow statements, covenant documents, working-capital data, capex data.
5. Assign Module Status:
   - **Full Run:** Sufficient liquidity/cash-flow evidence for all core steps.
   - **Ready with Limitations:** Partial evidence; proceed but flag gaps.
   - **Blocked:** Critical sources absent (e.g., no cash position or cash-flow data identifiable).
6. State citation discipline requirement.

## Output
T2E.1: `source_document_id`|`source_document_name`|`source_quality`|`period`|`entity_covered`|`data_supplied`|`limitation`|`downstream_use`
+ Module Status: Full Run / Ready with Limitations / Blocked
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
