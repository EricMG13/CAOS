<!-- REF_CP-3B_07 (T2) | 2026-06-03 -->
<step_reference module="CP-3B" step="07" name="Relative Value and Compensation Cross-Check">
<input>T3B.3 (market data), T3B.4 (structural positioning), T3B.6 (recovery sensitivity); CP-3 RV table.</input>
<gate>Step 6 complete.</gate>

## Instructions
1. Cross-check market compensation against structural rank, recovery sensitivity, maturity risk, liquidity, and LME exposure for each instrument.
2. Assign Compensation Adequacy Label: Attractive / Adequate / Inadequate / Unclear / Insufficient Information.
3. Do not allow yield alone to override weak recovery, legal position, maturity concentration, liquidity, or LME exposure.
4. If market data is absent, Compensation Adequacy = Unclear or Insufficient Information.
5. For each: record Market Level, Market Date, Structural Rank, Recovery Sensitivity, Compensation Adequacy, Compensation vs. Risk assessment narrative, and Source Trace.

## Output
T3B.7: `Instrument`|`Market Level`|`Market Date`|`Structural Rank`|`Recovery Sensitivity`|`Compensation Adequacy`|`Compensation vs. Risk`|`Source Trace`
</step_reference>
