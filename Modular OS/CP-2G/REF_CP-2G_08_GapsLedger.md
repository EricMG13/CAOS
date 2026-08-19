<!-- REF_CP-2G_08 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-2G" step="08" name="Gaps Ledger">
<input>All prior step outputs (T2G.1–T2G.7); cumulative gaps identified throughout the workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps from Steps 1–7 into one consolidated ledger.
2. For each gap record: Gap, Missing Item (emissions disclosure, transition exposure, KPI / SPT terms, ratchet size, verification), Why It Matters, Impact on Output, Required Follow-Up.
3. Flag where missing disclosure prevented a materiality classification (factor left Insufficient Information).
4. Every section marked [Insufficient Information] in Steps 1–7 must have a corresponding gap entry.

## Output
T2G.8: Gaps Ledger — `Gap`|`Missing Item`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`
</step_reference>
