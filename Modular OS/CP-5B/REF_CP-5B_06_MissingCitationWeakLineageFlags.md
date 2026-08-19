<!-- REF_CP-5B_06 (T2) | 2026-06-03 -->
<step_reference module="CP-5B" step="06" name="Missing Citation and Weak-Lineage Flags">
<input>T5B.3, T5B.4, T5B.5.</input>
<gate>Step 5 complete.</gate>

## Instructions
1. Identify ALL: missing citations, weak lineage, untraced claims, conflicting claims, and evidence gaps from T5B.3–T5B.5.
2. For each finding: record Severity (Critical/Material/Minor), Conclusion, Issue, Classification (from Lineage Taxonomy), Why It Matters (risk mechanic → credit implication), Required Remediation, and Affected Output/Export Record.
3. Apply Severity Rules:
   - **Critical:** Affects economics, legal meaning, recommendation, security selection, position sizing, committee decision, PD, LGD, recovery, refinancing, or relative value.
   - **Material:** Affects monitoring, confidence, source quality, or downstream structured export.
   - **Minor:** Formatting, metadata, or non-decision-critical citation issue.
4. Apply Orphan Claim Protocol: If lineage_class is Untraced, Weak Lineage, or Insufficient Information AND conclusion appears in committee-facing output AND no mitigation flag → trigger VE-015 (ORPHAN_CLAIM).

## Output
T5B.6: `Severity`|`Conclusion`|`Issue`|`Classification`|`Why It Matters`|`Required Remediation`|`Affected Output / Export Record`
</step_reference>
