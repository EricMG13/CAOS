<!-- REF_CP-5_04 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="04" name="Legal / Structural Claim Audit">
<input>T5.1; all module outputs containing legal/covenant/structural claims (especially CP-4, CP-4C, CP-3B).</input>
<gate>Step 3 complete.</gate>

## Instructions
1. Execute Audit Lane 3 (Legal / Covenant) across all audited modules.
2. For each legal/structural claim: verify clause-level source support from executed governing document.
3. Each legal QA finding must distinguish: contractual provision, analyst interpretation, credit implication, and legal-review dependency.
4. Check: covenant-capacity calculations supported by legal formula + financial input + usage data. Flag Covenant/Basket Overreach and Recovery/Ranking Overreach.
5. If only summary or draft legal evidence exists → mark [Legal Review Required] or [Source Limitation].
6. For each finding: record Severity, Module, Legal/Structural Claim, Required Legal Source, Evidence Gap, Required Fix, Legal Review Dependency.
7. Severity: Critical if affects creditor rights, recovery, or legal meaning; Material if legal review required; Minor if formatting.

## Output
T5.4: `Severity`|`Module`|`Legal / Structural Claim`|`Required Legal Source`|`Evidence Gap`|`Required Fix`|`Legal Review Dependency`
</step_reference>
