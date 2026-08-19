<!-- REF_CP-5_06 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="06" name="Cross-Module Consistency and Version-Control Audit">
<input>T5.1; all module outputs (full set for cross-comparison).</input>
<gate>Step 5 complete. Requires ≥2 module outputs for meaningful comparison.</gate>

## Instructions
1. Execute Audit Lane 5 (Cross-Module Consistency) across all audited modules.
2. Compare: issuer_id/deterministic_entity_key, issuer/borrower/parent/guarantor names, restricted-group perimeter, reporting period, EBITDA definition, net debt/gross debt/first-lien debt/secured debt, liquidity and revolver availability, maturities, covenant capacity and basket usage, recovery assumptions, legal capacity, market data, recommendation/monitoring posture.
3. If conflicts exist → log Version Conflict or Cross-Module Inconsistency and identify evidence required to resolve.
4. For each finding: record Severity, Affected Modules, Data/Claim Conflict, Version Issue, Required Fix, Downstream Impact.
5. Severity: Critical if creates contradictory conclusions; Material if affects downstream workflow; Minor if immaterial.

## Output
T5.6: `Severity`|`Affected Modules`|`Data / Claim Conflict`|`Version Issue`|`Required Fix`|`Downstream Impact`
</step_reference>
