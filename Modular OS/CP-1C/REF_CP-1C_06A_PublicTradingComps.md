<!-- REF_CP-1C_06A (T2) | 2026-06-02 -->
<step_reference module="CP-1C" step="06A" name="Public Trading Comps">
<input>T4.1 (public peers)</input>
<gate>Public peers available</gate>

## Instructions
Produce trading comps table. Apply the 12-point Valuation Discipline and EV formula in REF_CP-1C_ValuationAndOutlierRules.md. Stale multiples (>12mo) labelled. No averaging non-comparable.

## Output
T4.8: `Entity`|`Mkt Cap`|`Mkt Cap Date`|`EV`|`EV/Rev`|`EV/EBITDA`|`Period Used`|`Metric Def`|`Comp Status`|`Source`
</step_reference>
