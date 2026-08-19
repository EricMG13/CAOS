<!-- REF_CP-2C_01 (T2) | 2026-06-02 -->
<step_reference module="CP-2C" step="01" name="Source Gate & Calendar Scope">
<input>CP-2 output + source materials</input>
<gate>CP-2 data available</gate>

## Instructions
Validate source materials. Establish calendar horizon (default 12 months, extend if material events beyond). Confirm issuer identity and monitoring context from CP-2.

## Output
Calendar scope confirmation: issuer, horizon, source inventory.
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
