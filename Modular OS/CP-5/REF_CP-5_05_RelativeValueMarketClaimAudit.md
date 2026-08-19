<!-- REF_CP-5_05 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="05" name="Relative Value / Market Claim Audit">
<input>T5.1; all module outputs containing market/RV claims (especially CP-3, CP-6A, CP-6E).</input>
<gate>Step 4 complete.</gate>

## Instructions
1. Execute Audit Lane 4 (Market / RV) across all audited modules.
2. For each market/RV claim: verify required fields present — date, source, security/instrument, currency, seniority, price/spread/yield/DM (as applicable), rating (if used), comparable set (if used), instrument type, basis for ranking or value label.
3. If current market data is absent → mark [Market Data Not Provided] and prohibit current-RV conclusions.
4. Verify comparable set is disclosed and appropriate.
5. For each finding: record Severity, Module, Market/RV Claim, Missing Datapoint, Evidence Gap, Required Fix, Committee Impact.
6. Severity: Critical if changes recommendation; Material if affects RV classification; Minor if stale but immaterial.

## Output
T5.5: `Severity`|`Module`|`Market / RV Claim`|`Missing Datapoint`|`Evidence Gap`|`Required Fix`|`Committee Impact`
</step_reference>
