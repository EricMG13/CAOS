<!-- REF_CP-2D_10 (T2) | 2026-06-03 -->
<step_reference module="CP-2D" step="10" name="Cross-Module Handoff Register">
<input>T2D.1–T2D.9; all flags, risk level, gaps, and behavior evidence.</input>
<gate>Steps 1–9 complete.</gate>

## Instructions
1. Identify how CP-2D output should be consumed downstream.
2. Use predefined handoff tags:
   - **CP-2D-HANDOFF-CP-2:** fundamental governance / financial-policy input
   - **CP-2D-HANDOFF-CP-2B:** downside-pathway behavior input
   - **CP-2D-HANDOFF-CP-2E:** liquidity support / extraction input
   - **CP-2D-HANDOFF-CP-3:** scorecard and RV governance input
   - **CP-2D-HANDOFF-CP-3D:** sponsor willingness / LME behavior input
   - **CP-2D-HANDOFF-CP-4C:** legal capacity / leakage monitoring input
   - **CP-2D-HANDOFF-CP-5:** QA citation and supportability input
   - **CP-2D-HANDOFF-CP-5B:** evidence traceability input
   - **CP-2D-HANDOFF-CP-6A:** IC debate sponsor / governance input
   - **CP-2D-HANDOFF-CP-6E:** portfolio debate sponsor / concentration / behavior input
   - **CP-2D-HANDOFF-CP-DB:** GovernanceSponsorFlag / EvidenceTrace database export input
3. For each: record Downstream Module, Handoff Tag, Handoff Item, Why It Matters, Required Consumer Action, Source / Flag Link, Limitation.

## Output
T2D.10: `Downstream Module`|`Handoff Tag`|`Handoff Item`|`Why It Matters`|`Required Consumer Action`|`Source / Flag Link`|`Limitation`
</step_reference>
