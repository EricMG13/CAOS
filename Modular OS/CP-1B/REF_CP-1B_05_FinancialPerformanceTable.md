<!-- REF_CP-1B_05 (T2) | 2026-06-02 -->
<step_reference module="CP-1B" step="05" name="Financial Performance Table">
<input>CP-1 normalized financials</input>
<gate>Normalized data available</gate>

## Instructions
Multi-period table. 19 lines: Revenue, COGS, Gross Profit, Gross Margin, SG&A, EBITDA, EBITDA Margin, D&A, EBIT, Cash Interest Paid, Cash Taxes Paid, Total/Maint/Growth Capex, WC Change, OCF, FCF, DCF, Net Income.

Apply REF_CP-1B_CalculationDiscipline.md (calculation engine, prohibited calculations, period construction, cash-flow rules) to every calculated cell and variance.

## Output
T4.4: `Line Item`|`Period 1`…`N`|`YoY Change (Abs)`|`YoY Change (%)`|`Analyst Note`
</step_reference>
