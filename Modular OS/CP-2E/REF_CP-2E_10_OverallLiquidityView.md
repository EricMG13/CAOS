<!-- REF_CP-2E_10 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="10" name="Overall Liquidity View">
<input>All prior step outputs (T2E.1–T2E.9); Liquidity Risk Level from Step 8.</input>
<gate>Always executes. Synthesis only — no new data.</gate>

## Instructions
1. Write a committee-ready narrative synthesis using the template:
   "Overall, [Issuer] has [adequate / tight / weak / insufficient information] near-term liquidity. Beginning accessible liquidity is [amount / insufficient information], while expected 12-month cash uses are [amount / insufficient information]. The key liquidity pressure is [driver], which matters because [risk mechanic] and implies [credit implication]. Months to Empty is [result / insufficient information]. Further analysis requires [missing data]."
2. Do not introduce new data, new calculations, or new assessments — synthesize only from Steps 1–9.
3. End with one of:
   - "CP-2E Completed. Liquidity Risk Level: [Level]."
   - "CP-2E Completed with Limitations. Liquidity Risk Level: [Level]. Key Gaps: [List]."
   - "CP-2E Blocked. Missing Required Inputs: [List]."

## Output
Narrative synthesis (no table). Module completion statement with Liquidity Risk Level.
</step_reference>
