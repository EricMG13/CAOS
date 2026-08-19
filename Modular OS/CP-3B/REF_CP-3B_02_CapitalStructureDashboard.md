<!-- REF_CP-3B_02 (T2) | 2026-06-03 -->
<step_reference module="CP-3B" step="02" name="Capital Structure Dashboard">
<input>T3B.1 Source Register; capital structure data from credit agreements, indentures, lender presentations, CP-3 output.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Map all instruments in the issuer's capital structure.
2. Order instruments by structural priority (not maturity).
3. For each instrument: record Type (using Instrument Type Taxonomy), Amount, Currency, Maturity, Seniority/Lien position, Collateral, Guarantors, Coupon/Margin, Fixed/Floating, and Source Trace.
4. Identify total secured debt, total unsecured debt, total debt.
5. Flag instruments where seniority, collateral, or guarantor information is incomplete.

## Output
T3B.2: `Instrument`|`Type`|`Amount`|`Currency`|`Maturity`|`Seniority / Lien`|`Collateral`|`Guarantors`|`Coupon / Margin`|`Fixed / Floating`|`Source Trace`
</step_reference>
