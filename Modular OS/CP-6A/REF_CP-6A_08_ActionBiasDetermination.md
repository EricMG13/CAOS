<!-- REF_CP-6A_08 (T2) | 2026-06-03 -->
<step_reference module="CP-6A" step="08" name="Action Bias Determination">
<input>T6A.6, T6A.7; debate record (Steps 3-7); Final Bias Guardrails.</input>
<gate>Step 7 complete.</gate>

## Instructions
1. Determine the final action bias from exactly the 8 permitted values: Avoid | Watchlist | Starter Position | Core Hold | Add / Increase | Reduce / Trim | Exit | Requires More Work.
2. Use the required formulation:
   "Final Action Bias: [Action Bias]. The decision is driven by [top evidence], because [risk mechanic], which implies [PD / LGD / liquidity / RV / portfolio implication]. The main factor preventing a higher-conviction recommendation is [constraint]."
3. Cross-check against Final Bias Guardrails (Active Prompt) — the selected bias must be consistent with the evidence pattern.
4. Apply Chair Decision Rules:
   - Bear proves Zero-Bound path + Bull cannot quantify liquidity protection → bias ≤ Watchlist.
   - Bull proves durable FCF + liquidity + maturities + RV but legal leakage unresolved → Starter Position.
   - Both sides weak evidence → Requires More Work.
5. State which persona won the debate (Bull / Bear / Neither) and why.

## Output
Final Action Bias formulation (required format). Debate winner statement.
</step_reference>
