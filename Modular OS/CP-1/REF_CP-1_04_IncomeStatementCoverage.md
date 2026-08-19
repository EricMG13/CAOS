<!-- REF_CP-1_04_IncomeStatementCoverage (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="4" name="Income Statement Coverage">
<input>Normalized source data (Step 3 basis).</input>
<gate>Always executes. If IS data unavailable, produce empty table + log all gaps.</gate>

## Detailed Instructions
1. Extract + normalize full IS for every available period on Step 3 basis.
2. Required line items (null + gap where unavailable):
   Revenue | COGS | Gross Profit | SGA | Other Operating | EBITDA (Reported) | EBITDA (Adjusted) | D&A | EBIT | Interest Expense (Total/Cash) | Interest Income | Other Non-Operating | PBT | Tax (Total/Cash) | Net Income | Exceptionals | SBC
3. Each item: source file, period, currency, unit, value, evidence tier.
4. EBITDA not stated → derive from components `[Calculated]`. Insufficient → null.
5. Populate Financial Statement Coverage entries for IS.

## Output — T4.4 Income Statement
`Line Item` | `Period 1` … `Period N`

## Warnings
- Do NOT fabricate missing items. Non-derivable = null + gap.
- EBITDA definition conflicts → log BOTH reported and adjusted for Step 10.
</step_reference>
