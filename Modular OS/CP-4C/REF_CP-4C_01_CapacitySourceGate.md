<!-- REF_CP-4C_01 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="01" name="Capacity Source Gate">
<input>All available source materials: CP-4 Legal/Covenant Review output, CP-1 financial foundation, executed credit agreements, indentures, intercreditor agreements, amendments, compliance certificates, debt schedules, basket usage trackers, covenant schedules, guarantor/collateral/subsidiary schedules.</input>
<gate>Always executes. This IS the gate check. BLOCKING: CP-4 Legal/Covenant Review output or at least one executed governing legal document must be available. If neither: Module Status = Blocked, STOP.</gate>

## Instructions
1. Confirm execution mode and required input availability.
2. Check: CP-4 output available? Executed legal documents available? CP-1 financial inputs available? Usage data available?
3. Assess legal formula availability, current financial input availability, usage data availability, and source quality.
4. Verify structured-export readiness.
5. Assign Module Status:
   - **Completed:** Legal formulas + current financial inputs + usage data all available.
   - **Completed with Limitations:** Legal formulas available but missing financial inputs, usage data, compliance certificates, or CP-4 output is itself limited.
   - **Blocked:** No executed governing document AND no CP-4 output. Output blocked message and STOP.
6. If CP-1 financials missing: headroom/capacity calculations limited — flag.
7. If CP-4 output missing or limited: legal provision extraction may be incomplete — flag.

## Output
T4C.1: Source gate register (input inventory + availability + quality + limitations)
+ Module Status: Completed / Completed with Limitations / Blocked
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
