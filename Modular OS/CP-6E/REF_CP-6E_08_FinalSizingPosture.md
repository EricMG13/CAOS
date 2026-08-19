<!-- REF_CP-6E_08 (T2) | 2026-06-03 -->
<step_reference module="CP-6E" step="08" name="Final Sizing Posture">
<input>T6E.6, T6E.7; debate record (Steps 3-7); Posture Guardrails.</input>
<gate>Step 7 complete.</gate>

## Instructions
1. Choose one of the 6 permitted Portfolio Posture values: Include | Avoid | Resize-Reduce | Resize-Increase | Maintain-Hold | Requires More Work.
2. Use the required formulation:
   "Final Sizing Posture: [Posture]. The decision is driven by [top evidence], because [risk mechanic], which implies [portfolio yield / concentration / downgrade / liquidity / recovery / mandate implication]."
3. Cross-check against Posture Guardrails (Active Prompt) — selected posture must be consistent with the evidence pattern.
4. Apply CIO Decision Rules:
   - CP-3 missing → cannot Include.
   - CP-3C/mandate missing → cannot claim sizing within limits.
   - Compliance proves binding breach + RV cannot show headroom → cannot Include.
   - RV proves spread + downside + headroom but legal leakage unresolved → Include (Starter Position) with constraint.
   - Both sides weak → Requires More Work.
5. State which persona won the debate (RV Trader / Compliance Officer / Neither) and why.
6. Include the canonical translation (e.g., "Include maps to Starter Position given constraint").

## Output
Final Sizing Posture formulation (required format). Debate winner statement. Canonical translation.
</step_reference>
