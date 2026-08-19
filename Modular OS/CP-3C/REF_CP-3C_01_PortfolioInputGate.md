<!-- REF_CP-3C_01 (T2) | 2026-06-03 -->
<step_reference module="CP-3C" step="01" name="Portfolio Input Gate">
<input>All available source materials: CP-3 output, issuer/security identifiers, mandate constraints, current holdings/exposure, concentration data, liquidity/trading constraints, downside/recovery/legal/LME inputs, portfolio reports, PM notes, committee notes.</input>
<gate>Always executes. This IS the gate check. BLOCKING: CP-3 output must be available. If missing: output "Blocked — Missing required inputs for CP-3C Portfolio Fit / Position Sizing / Risk Budget." STOP.</gate>

## Instructions
1. Confirm CP-3 output / security-selection conclusion is available. If missing → Blocked, STOP.
2. Catalogue all sources: source_document_id, source_document_name, source_quality, period/date, entity_covered, data_supplied, limitation, downstream_use.
3. Check each required input: CP-3 output, issuer/security identifiers, mandate constraints, current holdings/exposure, concentration data, liquidity/trading constraints, downside/recovery/legal/LME inputs.
4. For each: record Available/Missing, Source, Limitation, Portfolio Impact.
5. Determine whether output will be mandate-specific or generic portfolio-fit logic (based on mandate data availability).
6. Assign Module Status: Completed / Completed with Limitations / Blocked.
7. Flag stale, draft, incomplete, unaudited, management-adjusted, pro forma, or conflicting sources.

## Output
T3C.1: `Input`|`Available / Missing`|`Source`|`Limitation`|`Portfolio Impact`
+ Module Status: Completed / Completed with Limitations / Blocked
+ Output Mode: Mandate-Specific / Generic Portfolio-Fit Logic
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
