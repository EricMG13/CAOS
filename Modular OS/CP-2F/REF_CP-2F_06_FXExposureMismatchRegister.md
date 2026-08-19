<!-- REF_CP-2F_06 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="06" name="FX Exposure & Mismatch Register">
<input>T2F.1–T2F.5; revenue, cost, debt, EBITDA, cash, and covenant currency data from source materials and upstream modules.</input>
<gate>Steps 2–5 complete. Skip with [Insufficient Information] if no FX/currency data available.</gate>

## Instructions
1. Build the FX exposure and mismatch register using FX Exposure Labels.
2. For each exposure type: record Revenue Currency / Region, Cost Currency / Region, Debt / EBITDA / Cash / Covenant Currency, Natural Hedge? (Yes / No / Partial / Insufficient Information), Evidence, Risk Mechanic, Credit Implication, Source Trace, and Limitation.
3. Identify translation vs. transaction exposure.
4. Identify covenant currency mismatch risk and cash repatriation constraints.
5. Do not infer FX exposure from geography alone — require revenue/cost/debt/EBITDA/cash/covenant currency data.

## Output
T2F.6: `Exposure Type`|`Revenue Currency / Region`|`Cost Currency / Region`|`Debt / EBITDA / Cash / Covenant Currency`|`Natural Hedge?`|`Evidence`|`Risk Mechanic`|`Credit Implication`|`Source Trace`|`Limitation`
</step_reference>
