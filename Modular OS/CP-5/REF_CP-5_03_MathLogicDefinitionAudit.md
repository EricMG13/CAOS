<!-- REF_CP-5_03 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="03" name="Math / Logic / Definition Audit">
<input>T5.1; all module outputs containing calculations.</input>
<gate>Step 2 complete.</gate>

## Instructions
1. Execute Audit Lane 2 (Calculation) across all audited modules.
2. For each formula/metric/ratio: verify ALL required elements present (formula, numerator, denominator, period, units/currency, source trace, normalization/pro forma adjustments, sign convention).
3. If any required element is missing → classify as Not Calculable from Provided Materials (unless missing element immaterial and limitation disclosed).
4. Check: metric definition matches governing definition (legal for covenant metrics, CP-1 for financial metrics). Flag metric-definition drift between modules.
5. Verify sign conventions, pro forma adjustment disclosure, and reconciliation to module output.
6. For each finding: record Severity, Module, Metric/Logic Issue, Formula/Definition Issue, Source Conflict, Required Fix, Clearance Impact.
7. Severity: Critical if changes material metric; Material if affects consistency; Minor if rounding/formatting.

## Output
T5.3: `Severity`|`Module`|`Metric / Logic Issue`|`Formula / Definition Issue`|`Source Conflict`|`Required Fix`|`Clearance Impact`
</step_reference>
