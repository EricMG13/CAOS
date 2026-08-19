<!-- REF_CP-3D_02 (T2) | 2026-06-03 -->
<step_reference module="CP-3D" step="02" name="Maturity Wall and Refinancing Register">
<input>T3D.1 Source Register; debt schedules, maturity profiles, capital structure data.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Map all debt instruments by maturity date, ordered chronologically.
2. For each instrument: record Instrument, Amount, Currency, Maturity Date, Years to Maturity, Seniority/Lien, Coupon/Margin, Fixed/Floating, Call Date (if applicable), Refinancing Pressure (using Refinancing Pressure Indicators), and Source Trace.
3. Identify maturity wall: cluster maturities by year and assess concentration.
4. Flag near-term maturities relative to liquidity (Refinancing Pressure Indicator #1).
5. Identify springing maturities or maturity acceleration triggers.
6. Translate maturity wall into credit implication using Evidence → Risk Mechanic → Credit Implication.
7. Do not infer maturity wall unless supported by provided evidence.

## Output
T3D.2: `Instrument`|`Amount`|`Currency`|`Maturity Date`|`Years to Maturity`|`Seniority / Lien`|`Coupon / Margin`|`Fixed / Floating`|`Call Date`|`Refinancing Pressure`|`Credit Implication`|`Source Trace`
