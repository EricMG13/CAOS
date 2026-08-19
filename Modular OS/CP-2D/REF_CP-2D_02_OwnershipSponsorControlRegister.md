<!-- REF_CP-2D_02 (T2) | 2026-06-03 -->
<step_reference module="CP-2D" step="02" name="Ownership, Sponsor & Control Register">
<input>T2D.1 Source Register; all ownership, sponsor, shareholder, and governance source materials.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Build the issuer ownership and control register covering: current owner/sponsor/shareholder, ownership percentage, sponsor fund/vehicle, fund vintage/life-left, acquisition date/ownership transition, equity contribution/purchase price/entry multiple, board/control/veto/consent rights, restricted-group/holdco structure, sponsor/shareholder fees.
2. For each item: record Source-Supported Fact, Evidence Quality (High/Medium/Low/Insufficient), Source Trace, Credit Mechanic, Credit Implication, and Limitation.
3. If fund vintage, fund life-left, ownership percentage, or control rights are not explicitly disclosed, write [Insufficient Information].
4. Do not infer exit pressure from vintage unless both fund vintage and life-left are disclosed.
5. Use names only to identify disclosed roles, signatories, ownership interests, or governance functions — do not evaluate persons.

## Output
T2D.2: `Item`|`Source-Supported Fact`|`Evidence Quality`|`Source Trace`|`Credit Mechanic`|`Credit Implication`|`Limitation`
</step_reference>
