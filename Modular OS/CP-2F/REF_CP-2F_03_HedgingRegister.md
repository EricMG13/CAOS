<!-- REF_CP-2F_03 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="03" name="Hedging Register">
<input>T2F.1, T2F.2; hedge documentation, credit agreements, lender presentations, company presentations.</input>
<gate>Step 2 complete. Skip with [Insufficient Information] if no hedge data available.</gate>

## Instructions
1. Build the hedging register using Hedge Labels (Types and Coverage Status).
2. Include where disclosed: interest-rate swaps, caps, collars, fixed-rate debt acting as hedge, FX forwards, FX options, natural hedges, commodity hedges, fuel/energy hedges, inflation-linked pass-throughs.
3. For each: record Hedge Type, Notional, Instrument Covered (link to T2F.2 debt instrument), Rate / Strike, Maturity, Coverage Status (Effective where supported / Partial / Expired / Maturity mismatch / Notional disclosed only / Terms insufficient / Insufficient Information), Source Trace, and Limitation.
4. Do not assume swaps/caps/collars/forwards are effective unless terms are disclosed.
5. Do not treat notional hedge amount as effective cash-flow protection unless instrument, covered exposure, rate/strike, maturity, and coverage period are sufficiently disclosed.

## Output
T2F.3: `Hedge Type`|`Notional`|`Instrument Covered`|`Rate / Strike`|`Maturity`|`Coverage Status`|`Source Trace`|`Limitation`
</step_reference>
