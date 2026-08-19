<!-- REF_CP-3B_03 (T2) | 2026-06-03 -->
<step_reference module="CP-3B" step="03" name="Instrument Matrix">
<input>T3B.1, T3B.2; market data (pricing sheets, trading data, CP-3 RV table).</input>
<gate>Step 2 complete.</gate>

## Instructions
1. Build the instrument matrix combining structural data with market data.
2. For each instrument: record Price, Spread/Yield/DM, Market Date, Pricing Source, Quote Quality, Call Schedule (if bond), Covenant Package summary, Liquidity assessment, and Source Trace.
3. If market data is absent for an instrument, record [Insufficient Information] for market fields.
4. Identify instruments with stale pricing (flag market date vs. analysis date).
5. Note liquidity limitations (bid-ask spread, dealer count, trading frequency where available).

## Output
T3B.3: `Instrument`|`Price`|`Spread / Yield / DM`|`Market Date`|`Source`|`Quote Quality`|`Call Schedule`|`Covenant Package`|`Liquidity`|`Source Trace`
</step_reference>
