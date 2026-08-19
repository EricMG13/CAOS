<!-- REF_CP-2B_06 (T2) | 2026-06-03 -->
<step_reference module="CP-2B" step="06" name="Downside Sensitivity Matrix">
<input>Steps 1-5 outputs; financial data</input>
<gate>Step 5 complete.</gate>

## Instructions
Where source data supports quantitative sensitivity, calculate or summarize directional effects. Otherwise mark [Directional Only]. Apply No False Precision rule: use quantitative sensitivities only where source inputs support the calculation.

Potential sensitivities: revenue decline, price decline, volume decline, gross margin compression, EBITDA margin compression, working-capital outflow, capex increase, cash-interest increase, liquidity draw, leverage increase, covenant headroom erosion, refinancing spread/coupon reset.

> **REPRODUCIBILITY NOTE — shock magnitude.** The corpus pins **no default magnitude** for the shocks in this matrix (unlike CP-2F, which fixes a **+100 bps** base-rate move — CP-2F `REF_CP-2F_05`). Each sensitivity's shock size is therefore **analyst-chosen and must be recorded in the `Input Basis` / `Formula / Method` columns** (e.g. "−10% revenue", "+200 bps refi coupon") so the result is reproducible; an unstated magnitude makes the `Result` non-comparable across runs. Per the No False Precision rule, only quantify where source inputs support the calculation — otherwise mark `[Directional Only]`. Do not fabricate a magnitude that the sources do not ground.

## Output
**T2B.6 Downside Sensitivity Matrix:** `Sensitivity`|`Input Basis`|`Formula / Method`|`Result`|`Credit Interpretation`|`Status`|`Source Trace`
- Status: Calculated / Directional Only / Not Calculable
</step_reference>
