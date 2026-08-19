<!-- REF_CP-2B_03 (T2) | 2026-06-03 -->
<step_reference module="CP-2B" step="03" name="Fragility Map">
<input>Steps 1-2 outputs; CP-1B/CP-2 data</input>
<gate>Step 2 complete.</gate>

## Instructions
Identify business-model points most likely to break first under stress. Apply First-Break Discipline: identify the earliest plausible issuer-specific operating variable that deteriorates. Do not begin with EBITDA decline unless the operating source is identified.

Include where relevant and supported: price, volume, mix, churn/retention, customer concentration, supplier concentration, input costs, labour/wage inflation, margin pass-through, working capital, capex, regulation, substitution, seasonality, integration/restructuring, refinancing, covenant headroom, market access, and sponsor/LME risk.

Use REF_CP-2B_FragilityDriverTaxonomy.md as the controlled driver vocabulary (full lists for all 8 groups; the Active Prompt table is abbreviated).

## Output
**T2B.3 Fragility Map:** `Fragility Driver`|`First Break Point`|`Evidence`|`Risk Mechanic`|`Credit Implication`|`Confidence`|`Source Trace`
- Fragility Driver: one of 8 groups (Revenue/Margin/Cash Conversion/Liquidity/Capital Structure/Legal/Governance/Macro)
- Confidence: High / Medium / Low / Not Assessable
</step_reference>
