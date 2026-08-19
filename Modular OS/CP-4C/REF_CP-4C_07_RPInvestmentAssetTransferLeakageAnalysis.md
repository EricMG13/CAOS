<!-- REF_CP-4C_07 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="07" name="RP, Investment, Asset Transfer, and Leakage Analysis">
<input>T4C.5 Capacity Register; RP/investment/asset transfer/USub provisions.</input>
<gate>Step 6 complete.</gate>

## Instructions
1. Analyze value movement away from creditor reach.
2. For each route: record Leakage Route, Supported Fact, Formula/Basket, Usage/Remaining Capacity, Restricted-Group/Collateral Impact, Severity (5-value), Credit Implication, Evidence ID.
3. Cover: RP baskets, builder basket, available amount, dividends, sponsor distributions, investments in non-guarantors, USub designation, IP/material asset transfers, non-guarantor transfers, asset sale reinvestment flexibility.
4. Aggregate total leakage capacity while applying Double-Counting Discipline.
5. Translate leakage capacity into recovery/LGD implications.

## Output
T4C.7: `Leakage Route`|`Supported Fact`|`Formula / Basket`|`Usage / Remaining Capacity`|`Restricted-Group / Collateral Impact`|`Severity`|`Credit Implication`|`Evidence ID`
</step_reference>
