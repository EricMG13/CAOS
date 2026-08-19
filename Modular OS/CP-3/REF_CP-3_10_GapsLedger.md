<!-- REF_CP-3_10 (T2) | 2026-06-03 -->
<step_reference module="CP-3" step="10" name="Gaps Ledger">
<input>All prior step outputs (T3.1–T3.9); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–9 into a consolidated ledger.
2. For each gap: record Missing Data, Why It Matters, Impact on Output (which step/table/score/recommendation is affected), and Required Follow-Up.
3. Cover gaps in: market data (pricing, spreads, yields, DM), comparable instruments, legal/recovery data (credit agreements, indentures, intercreditor, collateral), covenant terms, financial data (leverage, FCF, liquidity), rating-agency views, trading technicals, ownership/concentration data, portfolio constraints.
4. Flag gaps that prevent scoring, RV classification, ranking, or recommendation assignment.

## Output
T3.10: `Gap`|`Missing Data`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`
</step_reference>
