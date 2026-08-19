<!-- REF_CP-1B_01 (T2) | 2026-06-02 -->
<step_reference module="CP-1B" step="01" name="File Gate & Source Validation">
<input>CP-1 data + sources</input>
<gate>CP-1 available</gate>

## Instructions
Validate CP-1 + source availability. Identify all sources by name/type/period/evidence tier.

## Output
T4.1: `Source File Name`|`Document Type`|`Period Coverage`|`Evidence Quality Tier`|`Analytical Use`|`Limitations`
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
