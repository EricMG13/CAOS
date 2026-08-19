<!-- REF_CP-3C_02 (T2) | 2026-06-03 -->
<step_reference module="CP-3C" step="02" name="Portfolio Fit Register">
<input>T3C.1 Portfolio Input Gate; CP-3 output, CP-3B instrument preference, CP-3D refinancing/LME, CP-2B downside, CP-2E liquidity, CP-4/CP-4C legal/covenant, mandate guidelines.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Assess whether the issuer/security fits the relevant strategy, mandate, and portfolio role.
2. Assign Fit Category: Mandate fit / RV fit / Liquidity fit / Risk-budget fit / Not fit / Not assessable.
3. Identify portfolio role where supported: yield carry, spread duration, convexity, defensive senior secured, catalyst, RV switch, recovery-sensitive upside, watchlist/monitoring only.
4. For each issuer/security: provide Evidence, Risk Mechanic, Why It Fits / Does Not Fit, Constraints/Notes, and Source Trace.
5. Incorporate where available: mandate eligibility, RV support (CP-3), instrument support (CP-3B), downside support (CP-2B/CP-2E), legal/covenant support (CP-4/CP-4C), refinancing/LME support (CP-3D).

## Output
T3C.2: `Name / Instrument`|`Fit Category`|`Evidence`|`Risk Mechanic`|`Why It Fits / Does Not Fit`|`Constraints / Notes`|`Source Trace`
</step_reference>
