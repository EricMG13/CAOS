<!-- REF_CP-1B_07 (T2) | 2026-06-02 -->
<step_reference module="CP-1B" step="07" name="Variance Analysis">
<input>T4.4 + T4.5</input>
<gate>≥1 period pair</gate>

## Instructions
Detailed variance for all material metrics. Bases: YoY, sequential, LTM, actual vs base case/guidance/rating-agency. Apply REF_CP-1B_CalculationDiscipline.md period-construction rules (same-period YoY, consecutive sequential, null-propagating LTM/YTD; no mixed annual/quarterly bases without annualization flag).

## Output
T4.6: `Metric`|`Comparison Basis`|`Prior Value`|`Current Value`|`Abs Change`|`% Change`|`Mgmt Driver`|`Analyst Driver`|`Credit Implication`
</step_reference>
