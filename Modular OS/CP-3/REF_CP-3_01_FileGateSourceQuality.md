<!-- REF_CP-3_01 (T2) | 2026-06-03 -->
<step_reference module="CP-3" step="01" name="File Gate & Source Quality">
<input>All available source materials: CP-1/CP-1C/CP-2/CP-2E exports, market data, legal review, pricing sheets, CLO lists, prior CP-3 outputs, credit agreements, recovery analysis, trading sheets, internal notes.</input>
<gate>Always executes. This IS the gate check.</gate>

## Instructions
1. Determine execution mode: CLO Screening / Single-Name RV / Capital-Structure RV / Watchlist Monitoring. Verify required inputs per mode (see Active Prompt — Execution Modes).
2. Catalogue all sources: record source_document_id, source_document_name, source_quality, period, entity_covered, data_supplied, limitation, downstream_use.
3. Assess market-data quality (pricing date, source, quote quality, staleness).
4. Assess legal-data quality (credit agreement, indenture, intercreditor, recovery analysis availability).
5. Confirm issuer entity keys and structured-export feasibility.
6. Assign Module Status:
   - **Full Run:** Sufficient fundamental + market + legal evidence for complete scoring, RV, and recommendation.
   - **Ready with Limitations:** Partial evidence; proceed but flag gaps (e.g., no market data → RV = Unclear).
   - **Blocked:** Critical sources absent (e.g., no CP-1/CP-2 or equivalent fundamental evidence).
7. If Blocked, STOP after the blocked message.

## Output
T3.1: `source_document_id`|`source_document_name`|`source_quality`|`period`|`entity_covered`|`data_supplied`|`limitation`|`downstream_use`
+ Module Status: Full Run / Ready with Limitations / Blocked
+ Execution Mode: CLO Screening / Single-Name RV / Capital-Structure RV / Watchlist Monitoring
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
