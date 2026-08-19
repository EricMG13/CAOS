<!-- REF_CP-2E_06 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="06" name="Months to Empty Calculation">
<input>T2E.5 (Beginning accessible liquidity, cash-burn data).</input>
<gate>Step 5 complete. Calculate only where beginning accessible liquidity AND cash-burn basis are both supported. If either is unsupported, state [Insufficient Information] and list missing inputs.</gate>

## Instructions
1. Calculate: **Months to Empty = Beginning accessible liquidity / average monthly cash burn.**
2. Use Python for calculation.
3. State the source period for cash burn and whether it is recurring, seasonal, or distorted.
4. Do not annualize or monthly-average volatile cash flows without explaining the limitation.
5. If cash-burn basis is from a non-representative period (seasonal, one-off, restructuring), state the limitation and its impact on the MTE figure.
6. If unsupported, state [Insufficient Information] and list each missing input.

## Output
T2E.6: Months to Empty result (numeric) + calculation basis narrative, OR [Insufficient Information] with missing-input list.
</step_reference>
