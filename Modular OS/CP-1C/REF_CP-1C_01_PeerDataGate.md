<!-- REF_CP-1C_01 (T2) | 2026-06-02 -->
<step_reference module="CP-1C" step="01" name="Peer Data Gate">
<input>Step 0 output + sources</input>
<gate>Sufficient peer data</gate>

## Instructions
Validate each candidate has accessible financial data. If web-scraped, confirm data beyond entity identification. Identify all peer source materials by name/type/period/evidence quality/provenance. Confirm CP-1 borrower data available. Flag if insufficient.

## Output
Data sufficiency assessment. Status: Full Run / Ready with Limitations / Blocked.
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
