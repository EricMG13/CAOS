<!-- REF_CP-5B_05 (T2) | 2026-06-03 -->
<step_reference module="CP-5B" step="05" name="Calculation and Assumption Register">
<input>T5B.3, T5B.4; module outputs containing calculations.</input>
<gate>Step 4 complete.</gate>

## Instructions
1. Trace calculations and assumptions used by upstream modules.
2. For each item: record Item (metric/assumption), Where Used (section), Source Inputs/Assumption, Formula or Logic, Status (Calculated/Assumption-Based/Not Calculable), Claim Status, Confidence Level, Credit Relevance (PD/LGD/liquidity/refinancing/RV/monitoring), and Source Trace.
3. All calculated metrics MUST show: formula, numerator, denominator, period, source trace, and normalization.
4. If formula support is unavailable → label Not Calculable from Provided Materials.
5. Flag any metric-definition drift between modules (e.g., EBITDA definition mismatch).

## Output
T5B.5: `Item`|`Where Used`|`Source Inputs / Assumption`|`Formula or Logic`|`Status`|`Claim Status`|`Confidence Level`|`Credit Relevance`|`Source Trace`
</step_reference>
