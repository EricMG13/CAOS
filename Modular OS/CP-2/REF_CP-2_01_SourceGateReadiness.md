<!-- REF_CP-2_01 (T2) | 2026-06-03 -->
<step_reference module="CP-2" step="01" name="Source Gate and Readiness">
<input>Uploaded files, CP-0 registry, CP-1/CP-1A/CP-1B/CP-1C outputs (if available)</input>
<gate>Always executes. Determines module status: Full Run / Ready with Limitations / Blocked.</gate>

## Instructions
Confirm available sources, source quality, issuer entity keys, reporting periods, and capital-structure data. Assess each source for quality, period coverage, entity coverage, data supplied, limitations, and downstream use.

Build a source register. State module status:
- **Full Run:** All gating sources available.
- **Ready with Limitations:** Partial sources — proceed with gap logging.
- **Blocked:** Missing gating evidence — stop after identifying gaps.

If blocked, stop after the blocked message.

## Output
**Source Register:** `source_document_id`|`source_document_name`|`source_quality`|`period`|`entity_covered`|`data_supplied`|`limitation`|`downstream_use`
**Module Status:** Full Run / Ready with Limitations / Blocked
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
