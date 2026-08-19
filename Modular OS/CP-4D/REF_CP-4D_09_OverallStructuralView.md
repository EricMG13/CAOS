<!-- REF_CP-4D_09 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-4D" step="09" name="Overall Structural View">
<input>All prior step outputs (T4D.1–T4D.8).</input>
<gate>Step 8 complete.</gate>

## Instructions
1. Synthesize the structural view. Lead with the highest-severity open leakage route and the most material structural-subordination gap.
2. State overall structural risk weighted to the worst route — **not** an average of routes.
3. Summarize recovery-access by creditor class (qualitative ranking by reachable value), explicitly flagging classes that are structurally subordinated or priming-exposed.
4. Produce the handoff register:
   - **To CP-3B:** the structural-priority map + reachable-value-by-entity, as the input for the dollar recovery waterfall and LGD.
   - **To CP-6A:** the single most material structural vulnerability for debate.
   - **To CP-4C:** any entity-perimeter constraint affecting capacity calculations.
5. State module confidence as the numeric `confidence_score` (0–100) with its derived band, computed per `CP_CONFIDENCE_SCORE.md`, and name its drivers (evidence quality, coverage, source gate, any QA penalties). Also state module status (Completed / Completed with Limitations) and the limitation drivers.

## Output
Narrative synthesis (1–2 pages) + handoff register naming the artifact passed to CP-3B, CP-6A, and CP-4C.
</step_reference>
