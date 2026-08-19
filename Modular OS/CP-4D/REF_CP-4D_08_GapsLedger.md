<!-- REF_CP-4D_08 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-4D" step="08" name="Gaps Ledger">
<input>All prior step outputs (T4D.1–T4D.7); cumulative gaps identified throughout the workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps from Steps 1–7 into one consolidated ledger.
2. For each gap record: Gap, Missing Document / Schedule / Provision, Why It Matters, Impact on Output (which table/label/route is affected), Required Follow-Up.
3. Cover gaps in: org chart, guarantor schedule, security/collateral schedule, subsidiary designations, intercreditor agreement, entity-level debt/EBITDA, CP-4 enabling findings.
4. Flag gaps that prevent assigning a Structural-Priority Label, scoring a leakage route, or reaching a recovery-access view.
5. Flag gaps requiring downstream resolution (CP-3B for the dollar waterfall, CP-6A for debate evidence).
6. Every section marked [Insufficient Information] in Steps 1–7 must have a corresponding gap entry.

## Output
T4D.8: Gaps Ledger — `Gap`|`Missing Document / Schedule / Provision`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`
</step_reference>
