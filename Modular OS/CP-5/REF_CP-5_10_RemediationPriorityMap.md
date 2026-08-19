<!-- REF_CP-5_10 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="10" name="Remediation Priority Map">
<input>T5.9 Consolidated Issue Log.</input>
<gate>Step 9 complete.</gate>

## Instructions
1. Group required fixes from the Issue Log into exactly 4 priority tiers:
   - **Must-fix before committee:** All Critical issues + Material issues that affect committee clearance.
   - **Must-fix before database / CP-DB ingestion:** Material issues affecting structured exports, schema, evidence trace, or database integrity.
   - **Monitoring follow-up:** Material/Minor issues requiring future action or re-audit trigger.
   - **Formatting / hygiene:** Minor presentation-only issues.
2. For each group: list Issue IDs and concise remediation instructions.
3. Provide ONLY remediation instructions — do NOT silently rewrite the underlying module analysis.
4. If no issues in a tier, state "None."

## Output
Narrative: 4 prioritized remediation groups with Issue ID references. No table.
</step_reference>
