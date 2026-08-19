<!-- REF_CP-4C_09 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="09" name="Leakage and Basket Flags">
<input>All capacity analysis from Steps 5–8.</input>
<gate>Step 8 complete.</gate>

## Instructions
1. Build the Leakage and Basket Flags table consolidating creditor-adverse findings.
2. For each: record Flag, Supported Fact, Creditor Risk, Severity (Low/Moderate/High/Critical/Insufficient Information), Confidence (5-value), Downstream Module, Evidence ID.
3. Prioritize flags with highest severity and broadest downstream impact.
4. Include flags for: double-counting risk, reclassification features, fungibility between baskets, USub designation capacity, collateral/guarantor release mechanics, amendment flexibility.
5. Map each flag to the downstream module(s) it affects.

## Output
T4C.9: `Flag`|`Supported Fact`|`Creditor Risk`|`Severity`|`Confidence`|`Downstream Module`|`Evidence ID`
</step_reference>
