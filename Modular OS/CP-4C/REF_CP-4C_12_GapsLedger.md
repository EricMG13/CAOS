<!-- REF_CP-4C_12 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="12" name="Gaps Ledger">
<input>All prior step outputs (T4C.1–T4C.11); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–11 into a consolidated ledger.
2. For each gap: record Gap, Missing Data, Why It Matters, Impact on Output (which step/table/calculation is affected), and Required Follow-Up.
3. Reference Standard Gaps Library where applicable:
   - Missing executed CA/indenture → cannot confirm governing capacity provisions.
   - Missing compliance certificate → maintenance headroom unconfirmable.
   - Missing covenant EBITDA bridge → ratio capacity unreliable.
   - Missing debt schedule → debt numerator/capacity limited.
   - Missing basket usage tracker → remaining capacity undetermined.
   - Missing guarantor/collateral/USub schedules → recovery/leakage incomplete.
   - Missing MFN details → incremental debt economics unassessable.
   - Conflicting EBITDA definitions → capacity may be materially misstated.
4. Every [Insufficient Information] in Steps 1–11 must have a corresponding gap entry.
5. Flag gaps with downstream impact on CP-6A, CP-6E, CP-3D.

## Output
T4C.12: `Gap`|`Missing Data`|`Why It Matters`|`Impact on Output`|`Required Follow-Up`
</step_reference>
