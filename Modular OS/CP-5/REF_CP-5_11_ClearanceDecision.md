<!-- REF_CP-5_11 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="11" name="Clearance Decision">
<input>T5.9 Consolidated Issue Log; Remediation Priority Map (Step 10).</input>
<gate>Always executes.</gate>

## Instructions
1. Apply Severity Engine:
   - Any Critical finding → qa_status = Blocked
   - Any Material (no Critical) → qa_status = Restricted
   - Only Minor or none → qa_status = Passed
2. Apply Committee Clearance Logic:
   - **Pass:** No Critical and no unresolved Material issues.
   - **Pass with Remediation:** No unresolved Critical, but ≥1 Material or Minor requiring correction/disclosure.
   - **Fail:** ≥1 unresolved Critical, missing auditable output, inability to identify issuer/entity, or defects blocking committee use.
3. Write the required clearance statement using EXACTLY this format:
   "CLEARANCE DECISION: [Pass / Pass with Remediation / Fail]. Critical Issues: [Count]. Material Issues: [Count]. Minor Issues: [Count]. Committee Use: [Approved / Restricted / Blocked]."
4. Follow with a 1–3 sentence explanation of the clearance rationale, citing the most impactful issues.
5. If Fail: state what remediation is required before clearance can be reconsidered.
6. If Pass with Remediation: state which Material issues must be disclosed for committee use.
7. No override of Blocked status is permitted within CP-5.

## Output
Narrative: Clearance statement in required format + rationale. No table.
</step_reference>
