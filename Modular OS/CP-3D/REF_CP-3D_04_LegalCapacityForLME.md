<!-- REF_CP-3D_04 (T2) | 2026-06-03 -->
<step_reference module="CP-3D" step="04" name="Legal Capacity for LME">
<input>T3D.1–T3D.3; CP-4/CP-4C legal/covenant outputs, credit agreements, indentures, intercreditor agreements.</input>
<gate>Step 3 complete. If CP-4/CP-4C unavailable, do not infer exact capacity — flag and proceed with [Insufficient Information] for legal fields.</gate>

## Instructions
1. Assess legal capacity across 14 Legal-Capacity Indicators:
   Incremental debt capacity, Lien capacity, Unrestricted subsidiary capacity, Investment capacity, RP/junior debt payment capacity, Collateral release, Guarantor release, Amendment thresholds, Sacred rights, Open-market purchase provisions, MFN protection, Intercreditor terms, Class voting, Pro rata sharing provisions.
2. For each: record Indicator, Available/Not Available/Unclear, Evidence, Risk Mechanic (how it enables or constrains LME paths), Which LME Paths Enabled, Confidence, and Source Trace.
3. Do not infer legal capacity from market convention — use source-supported provisions only.
4. If CP-4C unavailable, do not infer exact basket availability or capacity.
5. Cross-reference legal capacity with each LME path type to identify which paths are legally feasible.
6. Flag where legal capacity creates priming, subordination, or collateral leakage risk.

## Output
T3D.4: `Legal-Capacity Indicator`|`Available / Not Available / Unclear`|`Evidence`|`Risk Mechanic`|`LME Paths Enabled`|`Confidence`|`Source Trace`
