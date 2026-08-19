<!-- REF_CP-2G_05 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-2G" step="05" name="Sustainability-Linked Debt Mechanics">
<input>T2G.1; sustainability-linked loan / bond terms, KPI and SPT definitions, ratchet schedule, second-party opinion / verification.</input>
<gate>Step 1 complete. Not Applicable if the issuer has no sustainability-linked debt — state and skip.</gate>

## Instructions
1. For each sustainability-linked instrument capture: KPI definition and ambition, SPT thresholds and test dates, ratchet direction and size (bps), step-up / step-down symmetry, consequence of a miss, and reporting / verification (second-party opinion, assurance).
2. Judge whether the ratchet is **credit-meaningful or cosmetic** (size vs spread, symmetry, ambition of the SPT).
3. Translate to the expected spread effect and any covenant-headroom or reporting / monitoring implication.
4. Do not fabricate KPI, SPT, or ratchet terms — mark [Insufficient Information] where the document is silent.

## Output
T2G.5: KPI / SPT / Ratchet Table — `Instrument`|`KPI`|`SPT + Test Date`|`Ratchet (direction, bps)`|`Symmetry`|`Credit-Meaningful?`|`Expected Spread Effect`|`Evidence ID`
</step_reference>
