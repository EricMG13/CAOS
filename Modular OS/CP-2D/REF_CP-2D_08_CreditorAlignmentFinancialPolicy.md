<!-- REF_CP-2D_08 (T2) | 2026-06-03 -->
<step_reference module="CP-2D" step="08" name="Creditor Alignment & Financial Policy Assessment">
<input>T2D.2–T2D.7; all behavior flags, capital allocation, governance, and disclosure evidence.</input>
<gate>Steps 2–7 complete.</gate>

## Instructions
1. Assess the combined creditor-alignment signal across 9 scoring dimensions.
2. Dimensions: Leverage tolerance, Shareholder extraction risk, Acquisition appetite, Support behavior, Disclosure transparency, Creditor treatment / amendment behavior, Legal-capacity linkage, Reporting quality, Related-party leakage risk.
3. For each dimension: record Assessment (Creditor-favorable / Mixed / Adverse / Not Scorable), Evidence, Risk Mechanic, Credit Implication, Score (1 / 3 / 5 / Not Scorable), Evidence Quality, Source Trace, Limitation.
4. Do not score a dimension if evidence is missing — use Not Scorable.
5. If legal capacity is high but willingness evidence is missing, separate capacity from willingness.
6. Do not calculate a composite governance score unless ≥4 dimensions are evidence-supported. If <4, mark composite as Not Scorable and assign Risk Level = Insufficient Information (unless one clearly High-risk documented action).

## Output
T2D.8: `Dimension`|`Assessment`|`Evidence`|`Risk Mechanic`|`Credit Implication`|`Score`|`Evidence Quality`|`Source Trace`|`Limitation`
</step_reference>
