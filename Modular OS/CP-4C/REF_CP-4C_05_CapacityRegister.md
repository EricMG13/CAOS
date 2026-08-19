<!-- REF_CP-4C_05 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="05" name="Capacity Register">
<input>T4C.2, T4C.3, T4C.4; all capacity provisions from controlling documents; financial inputs; usage data.</input>
<gate>Step 4 complete.</gate>

## Instructions
1. Build the Capacity Register covering: debt incurrence, incremental facilities, incremental equivalent debt, ratio debt, acquisition debt, refinancing debt, liens, restricted payments, junior debt payments, investments, permitted acquisitions, asset sales/transfers, unrestricted subsidiaries, non-guarantor transfers, add-backs, leakage paths, collateral release capacity, and guarantor release capacity.
2. For each: record Capacity Type, Basket/Test, Formula, Conditions, Current Input, Usage, Estimated Capacity, Remaining Capacity, Status (7-value), Severity (5-value), Risk Mechanic, Credit Implication, Evidence ID.
3. Apply Double-Counting Discipline: identify fungibility, shared caps, reclassification constraints.
4. Apply Calculation Rules: every calculated item must include formula, source inputs, result, period, status, limitation, source trace.
5. Apply null-handling strictly: null for unavailable numerics, [Insufficient Information] in narrative.

## Output
T4C.5: `Capacity Type`|`Basket / Test`|`Formula`|`Conditions`|`Current Input`|`Usage`|`Estimated Capacity`|`Remaining Capacity`|`Status`|`Severity`|`Risk Mechanic`|`Credit Implication`|`Evidence ID`
</step_reference>
