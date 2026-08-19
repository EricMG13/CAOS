<!-- REF_CP-2E_09 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="09" name="Gaps Ledger">
<input>All prior step outputs (T2E.1–T2E.8 + Risk Assessment); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–8 into a consolidated ledger.
2. For each gap: record Missing Data, Why It Matters (credit relevance), Impact on Output (which step/table/calculation is affected), Required Follow-Up (what source is needed), and Downstream Module Affected.
3. Cover gaps in: cash balances, restricted cash classification, revolver commitment/availability, borrowing-base data, covenant constraints on revolver, debt amortization schedules, maturity schedules, cash interest schedules, cash tax estimates, working-capital data, capex breakdown (mandatory vs. growth), lease obligations, restructuring/integration costs, dividend/distribution commitments, sponsor support evidence, asset-sale proceeds, covenant headroom data (CP-4C), refinancing-window data (CP-3D).
4. Flag gaps that prevent Months to Empty calculation or Liquidity Risk Level assignment.

## Output
T2E.9: `Gap`|`Missing Data`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`|`Downstream Module Affected`
</step_reference>
