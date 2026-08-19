<!-- REF_CP-2E_03 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="03" name="Mandatory Cash Uses Register">
<input>T2E.1, T2E.2; debt schedules, cash-flow statements, covenant documents, capex data, interest/tax schedules.</input>
<gate>Step 2 complete.</gate>

## Instructions
1. Build the mandatory and discretionary cash uses register over the 12-month bridge horizon using permitted Cash-Use Category labels.
2. Cover: cash interest, cash taxes, debt amortization, maturities within 12 months, leases, mandatory capex, restructuring/integration cash costs, working-capital outflows, dividends/distributions, and other committed cash uses where supported.
3. For each: record Amount, Timing, Mandatory / Discretionary classification, Source Trace, Risk Mechanic, Credit Implication, and Limitation.
4. Do not assume any cash-use category is zero unless explicitly supported.
5. Flag any cash uses that are management-guided, provisional, or analyst-estimated with the appropriate Liquidity Data Status Label.

## Output
T2E.3: `Cash Use`|`Amount`|`Timing`|`Mandatory / Discretionary`|`Source Trace`|`Risk Mechanic`|`Credit Implication`|`Limitation`
</step_reference>
