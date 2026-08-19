<!-- REF_CP-2F_05 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="05" name="+100 bps Base-Rate Sensitivity">
<input>T2F.4 (Unhedged floating-rate debt).</input>
<gate>Step 4 complete. Calculate only where unhedged floating-rate exposure is supported. If unsupported, state [Insufficient Information] and list missing inputs.</gate>

## Instructions
1. Calculate: **+100 bps cash-interest impact = Unhedged floating-rate debt × 1.00%.**
2. Use Python for calculation.
3. Present: Sensitivity name, Formula, Source Inputs, Estimated Cash Impact, FCF / Liquidity Implication, Status, and Source Trace.
4. Translate the cash-interest impact into FCF, liquidity, and debt service mechanics.
5. If unhedged floating-rate debt is [Insufficient Information], state the sensitivity as [Insufficient Information] and list each missing input.

## Output
T2F.5: `Sensitivity`|`Formula`|`Source Inputs`|`Estimated Cash Impact`|`FCF / Liquidity Implication`|`Status`|`Source Trace`
</step_reference>
