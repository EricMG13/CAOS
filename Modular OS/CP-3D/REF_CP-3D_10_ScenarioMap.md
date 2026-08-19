<!-- REF_CP-3D_10 (T2) | 2026-06-03 -->
<step_reference module="CP-3D" step="10" name="Scenario Map: Base, Stress, and LME Case">
<input>T3D.2–T3D.9; all analytical evidence and path/vulnerability assessments.</input>
<gate>Step 9 complete.</gate>

## Instructions
1. Construct 3 scenarios:
   - **Base Case:** Most likely refinancing path under current conditions. State assumptions, path, timeline, creditor impact, and recovery implication.
   - **Stress Case:** Refinancing under adverse conditions (market dislocation, operational deterioration, covenant breach). State stress assumptions, most likely path under stress, creditor impact, and recovery implication.
   - **LME Case:** Most adverse creditor-impact LME path. State LME assumptions, specific path mechanics, which creditor classes are impaired, priming/subordination mechanics, and recovery implication.
2. For each scenario: record Scenario, Key Assumptions, Refinancing Path, Timeline, Creditor Impact, Recovery Implication, Probability Direction (using labels), Confidence, and Source Trace.
3. Clearly distinguish scenarios from each other.
4. Use Evidence → Risk Mechanic → Credit Implication chain for each scenario.

> **REPRODUCIBILITY NOTE — stress magnitude.** The Stress and LME cases are **narrative scenarios**, and the corpus pins no default magnitude for the adverse conditions invoked (market dislocation, operational deterioration, covenant breach) — contrast CP-2F, which fixes a deterministic **+100 bps** base-rate move (CP-2F `REF_CP-2F_05`). Where a scenario quantifies a shock, state the magnitude and its basis in `Key Assumptions` so the path is reproducible; two analysts must not assume different severities silently. Do not fabricate a magnitude the evidence does not support — keep the assumption directional if unquantifiable.

## Output
T3D.10: `Scenario`|`Key Assumptions`|`Refinancing Path`|`Timeline`|`Creditor Impact`|`Recovery Implication`|`Probability Direction`|`Confidence`|`Source Trace`
