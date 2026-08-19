<!-- REF_CP-2F_04 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="04" name="Unhedged Floating-Rate Exposure">
<input>T2F.2, T2F.3; debt and hedge registers.</input>
<gate>Steps 2–3 complete.</gate>

## Instructions
1. Calculate and present the unhedged floating-rate exposure breakdown.
2. Required rows: Total debt, Gross floating-rate debt, Hedged floating-rate debt, Unhedged floating-rate debt, Unhedged debt percentage.
3. For each: record Amount, Formula / Source basis, Status (use Reported / Calculated / Insufficient Information), Credit Implication, and Source Trace.
4. Use Python for calculations:
   - Unhedged floating-rate debt = Gross floating-rate debt − Hedged floating-rate debt.
   - Unhedged debt percentage = Unhedged floating-rate debt / Total debt.
5. If either gross floating-rate debt or hedge data is unsupported, state [Insufficient Information] for unhedged exposure.

## Output
T2F.4: `Metric`|`Amount`|`Formula / Source`|`Status`|`Credit Implication`|`Source Trace`
</step_reference>
