<!-- REF_CP-1C_06C (T2) | 2026-06-02 -->
<step_reference module="CP-1C" step="06C" name="Implied EV Table">
<input>T4.8+T4.9+CP-1 metrics</input>
<gate>Sufficient multiples</gate>

## Instructions
Calculate implied EV: 4 methods (EV/EBITDA, EV/Revenue, TV/EBITDA, TV/Revenue) + range (Low/Median/High) using the Implied EV Formulas and Valuation Calculation Constraints in REF_CP-1C_ValuationAndOutlierRules.md. Each calculation states: multiple source, borrower metric used, period, definition, calculation status. State: indicative context ONLY, NOT recovery estimate (recovery belongs to CP-4 / CP-4C). Web-scraped multiples → 'Provisional — Web-Sourced' if not cross-checked.

## Output
T4.10: `Method`|`Multiple Source`|`Multiple Value`|`Borrower Metric`|`Period`|`Implied EV`|`Low`|`Median`|`High`|`Calc Status`|`Limitations`
</step_reference>
