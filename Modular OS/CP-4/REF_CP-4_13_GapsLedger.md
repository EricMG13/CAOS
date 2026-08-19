<!-- REF_CP-4_13 (T2) | 2026-06-03 -->
<step_reference module="CP-4" step="13" name="Gaps Ledger">
<input>All prior step outputs (T4.1–T4.12); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–12 into a consolidated ledger.
2. For each gap: record Gap, Missing Document/Clause/Schedule, Why It Matters, Impact on Output (which step/table/score/section is affected), and Required Follow-Up.
3. Cover gaps in: governing documents, amendments, ICA, compliance certificates, schedules/exhibits, financial inputs (CP-1), CP-3D LME output, market-norm comparators, covenant-review reports, rating agency commentary.
4. Flag gaps that prevent scoring (aggressiveness score), capacity calculation, or recovery assessment.
5. Flag gaps requiring downstream resolution (CP-4C for capacity calcs, CP-6A for debate evidence).
6. Every section marked [Insufficient Information] in Steps 1–12 must have a corresponding gap entry.

## Output
T4.13: `Gap`|`Missing Document / Clause / Schedule`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`
</step_reference>
