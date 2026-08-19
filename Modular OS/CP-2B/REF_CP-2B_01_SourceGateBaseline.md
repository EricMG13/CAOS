<!-- REF_CP-2B_01 (T2) | 2026-06-03 -->
<step_reference module="CP-2B" step="01" name="Source Gate and Baseline">
<input>Uploaded files, CP-0 registry, CP-1/CP-1B/CP-2 outputs (if available)</input>
<gate>Always executes. Blocking gate: If CP-1 (or equivalent financial baseline) AND CP-2 (or equivalent business-risk baseline) are BOTH unavailable → STOP after blocked message unless user explicitly requests framework-only output.</gate>

## Instructions
Confirm available sources, source quality, issuer entity keys, reporting periods, prior-module coverage, operating-driver evidence, financial baseline, business-risk baseline, capital-structure evidence, liquidity evidence, covenant evidence, maturity/refinancing evidence, and structured-output feasibility.

State module status: Completed / Ready with Limitations / Blocked.

Build source register. Document: files and modules used, baseline financial and operating assumptions inherited, missing baseline inputs.

**Gate failure behavior:** If both CP-1 and CP-2 unavailable → Blocked. Stop after identifying missing gating evidence.

## Output
**T2B.1 Source Register:** `source_document_id`|`source_document_name`|`source_quality`|`period`|`entity_covered`|`data_supplied`|`limitation`|`downstream_use`
**Module Status:** Completed / Ready with Limitations / Blocked
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
