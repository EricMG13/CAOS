<!-- REF_CP-1_10_DefinitionConflictRegister (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="10" name="Definition Conflict Register">
<input>All outputs from Steps 1–9.</input>
<gate>Always executes. No conflicts → explicit alignment confirmation.</gate>

## Detailed Instructions
1. Review all metrics: issuer def vs. canonical? Sources disagree? Definition changed across periods?
2. Log each conflict: metric, canonical def, issuer def, source, periods, materiality (quantify), downstream modules, resolution.
3. Common conflict areas:
   - **EBITDA** — add-backs, exclusions, management vs. audited
   - **Debt** — leases, pensions, drawn facilities
   - **FCF** — levered vs. unlevered, WC inclusion
   - **Capex** — capitalized items, maint vs. growth
   - **Net Debt** — restricted cash, ST investments
4. No conflicts → "No definition conflicts identified across [N] metrics and [M] sources."
5. Supports Definition Inheritance Model for downstream modules.

## Output — T4.11 Definition Conflict Register
`Metric Name` | `Canonical Definition` | `Issuer-Reported Definition` | `Source of Conflict` | `Periods Affected` | `Materiality` | `Downstream Modules Affected` | `Resolution / Recommendation`

## Warnings
- Silent definition acceptance is NOT valid. Log conflicts OR confirm alignment.
- EBITDA adjustments = most common conflict source in leveraged finance.
</step_reference>
