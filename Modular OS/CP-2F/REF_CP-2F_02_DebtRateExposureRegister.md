<!-- REF_CP-2F_02 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="02" name="Debt & Rate Exposure Register">
<input>T2F.1 Source Register; debt schedules, credit agreements, indentures, lender presentations with fixed/floating detail.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Build the debt and rate exposure register using Rate Exposure Labels.
2. For each debt instrument: record Amount, Fixed / Floating classification, Base Rate (e.g., SOFR, EURIBOR), Margin / Coupon, Currency, Maturity, Hedge Status, Source Trace, and Credit Implication.
3. Identify total fixed-rate debt and total floating-rate debt.
4. Do not assume all debt is floating rate unless disclosed.
5. Flag instruments where fixed/floating classification is unclear or missing.

## Output
T2F.2: `Debt Instrument`|`Amount`|`Fixed / Floating`|`Base Rate`|`Margin / Coupon`|`Currency`|`Maturity`|`Hedge Status`|`Source Trace`|`Credit Implication`
</step_reference>
