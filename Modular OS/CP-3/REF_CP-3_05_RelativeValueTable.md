<!-- REF_CP-3_05 (T2) | 2026-06-03 -->
<step_reference module="CP-3" step="05" name="Relative Value Table">
<input>T3.1 (market data quality), T3.3/T3.4 (scorecard + overrides); pricing/spread/yield/DM evidence; comparable instruments.</input>
<gate>Steps 3–4 complete. If no market data available, label all securities as Unclear and proceed.</gate>

## Instructions
1. Build the RV table for each available security/instrument.
2. For each: record market level (spread/yield/DM/price), market-data date, pricing source, quote quality, relevant comps (with seniority/maturity/currency/metric basis disclosed), market compensation vs. risk assessment, and RV Label (Cheap / Fair / Rich / Unclear).
3. RV conclusions require dated market evidence. If absent, RV = Unclear.
4. Do not state current relative value without dated market evidence.
5. Do not compare instruments unless seniority, maturity, currency, metric basis, and pricing-source limitations are disclosed.
6. Identify liquidity/quote-quality limitations for each security.

## Output
T3.5: `Security`|`Market Level`|`Market Date`|`Source`|`Quote Quality`|`Comps`|`Seniority / Security`|`Compensation vs. Risk`|`RV Label`
</step_reference>
