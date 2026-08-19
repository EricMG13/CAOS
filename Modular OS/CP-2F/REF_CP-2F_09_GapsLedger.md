<!-- REF_CP-2F_09 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="09" name="Gaps Ledger">
<input>All prior step outputs (T2F.1–T2F.8 + Risk Level); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–8 into a consolidated ledger.
2. For each gap: record Missing Data, Why It Matters (credit relevance), Impact on Output (which step/table/calculation is affected), Required Follow-Up (what source is needed), and Downstream Module Affected.
3. Cover gaps in: debt schedules (fixed/floating split), base-rate references, hedge documentation (type, notional, rate/strike, maturity, coverage), FX revenue/cost/debt/EBITDA/cash/covenant currency data, commodity/raw-material cost breakdown, pass-through mechanism evidence, inflation data, energy/freight/wage cost data, demand elasticity data.
4. Flag gaps that prevent +100 bps sensitivity calculation or Macro Risk Level assignment.

## Output
T2F.9: `Gap`|`Missing Data`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`|`Downstream Module Affected`
</step_reference>
