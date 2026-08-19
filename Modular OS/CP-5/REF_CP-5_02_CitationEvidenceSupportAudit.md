<!-- REF_CP-5_02 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="02" name="Citation and Evidence Support Audit">
<input>T5.1; all module outputs; source materials.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Execute Audit Lane 1 (Unsupported Claim) across all audited modules.
2. For each material claim: classify evidence status using 5-value framework (Supported / Partially Supported / Unsupported / Conflicting / Insufficient Information).
3. Focus on: factual claims, financial metrics, legal assertions, market datapoints, relative-value claims, recovery claims, sponsor/governance labels, liquidity assertions, and committee conclusions.
4. For each finding: record Severity (CRITICAL/MATERIAL/MINOR), Module, Claim/Section, Evidence Status, Issue (what is wrong and why it matters), Required Fix, and Clearance Impact.
5. Apply Severity Escalation Rules: Critical if thesis-changing; Material if affects traceability; Minor if immaterial.
6. Flag promotional or management-characterization claims not distinguished from source-supported fact.
7. If conflicting sources exist, verify the conflict is logged in the audited module.

## Output
T5.2: `Severity`|`Module`|`Claim / Section`|`Evidence Status`|`Issue`|`Required Fix`|`Clearance Impact`
</step_reference>
