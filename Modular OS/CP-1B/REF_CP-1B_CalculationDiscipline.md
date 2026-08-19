<!-- REF_CP-1B_CalculationDiscipline (T2 Library) | 2026-06-10 | Restored from CP-1B__SUPPORT__Calculation_Period_and_Monitoring_Rules §2.5 -->
<library_reference module="CP-1B" name="Calculation Discipline">
<consumers>REF_CP-1B_05 (Financial Performance); REF_CP-1B_06 (KPI Dashboard); REF_CP-1B_07 (Variance Analysis)</consumers>

# CP-1B Calculation Discipline

## Calculation Engine Rule
All calculations use normalized figures inherited from CP-1. CP-1B does not transform, re-normalize, or re-base CP-1 data. If a calculation requires a figure CP-1 stores as null, the result is null and the limitation is logged.

## Calculation Discipline
- Every calculated value must be reproducible from its stated inputs and formula.
- Formulas must match the CP-1 canonical definitions exactly.
- If any input is null, the result is null — not zero, not estimated, not interpolated.
- Rounding must match the precision established by CP-1 for each metric.
- Period alignment must be exact: do not mix figures from different periods, stubs, or fiscal-year conventions in a single calculation.

## Prohibited Calculations
- Do not estimate missing inputs by interpolation, extrapolation, or averaging.
- Do not apply growth rates from one metric to impute another.
- Do not create new metrics not defined in the CP-1 definition register.
- Do not adjust CP-1 figures for items the analyst considers non-recurring unless CP-1 has already made that adjustment.
- Do not reverse CP-1 normalization adjustments.

## Period Construction Rules
- Year-over-year variance: compare same-period figures (Q3 FY2024 vs Q3 FY2023, or FY2024 vs FY2023).
- Sequential variance: compare consecutive periods (Q3 FY2024 vs Q2 FY2024).
- LTM: most recent full year + current stub − prior-year comparable stub. If any component is null, LTM is null.
- YTD: sum of sub-periods within the current fiscal year. If any sub-period component is null, YTD is null.
- Do not mix annual and quarterly figures in the same variance unless the comparison basis is explicitly annualized and flagged.

## Cash Flow Calculation Rules
- Use cash interest paid and cash taxes paid for cash-flow metrics (not accrued interest expense or total tax expense) unless CP-1 has flagged that cash figures are unavailable.
- Capex uses the CP-1 canonical classification (maintenance vs growth) where available. If disaggregated capex is unavailable, use total capex and flag the limitation.
- Working capital changes follow the CP-1 sign convention.
</library_reference>
