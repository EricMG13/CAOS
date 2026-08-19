<!-- REF_CP-1_12_CoverageGateDownstreamReadiness (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="12" name="Coverage Gate & Downstream Readiness">
<input>All outputs from Steps 1–11. Complete gap inventory.</input>
<gate>Always executes. Final quality gate before output assembly.</gate>

## Detailed Instructions
1. Consolidate ALL gaps from ALL prior steps into Gaps & Validation Warnings.
2. Assess CP-1 output sufficiency for each downstream consumer (13 modules):
   | Consumer | Type | Key CP-1 Dependencies |
   |----------|------|----------------------|
   | CP-1B | Analytical | Normalized financials, entity scope |
   | CP-1C | Analytical | Normalized financials, period coverage |
   | CP-2 | Analytical | All KPIs, calculation register, FCF build |
   | CP-2B | Analytical | Cash flow metrics, liquidity data |
   | CP-2E | Analytical | Earnings quality metrics |
   | CP-3 | Analytical | Debt classification, capital structure |
   | CP-3D | Analytical | Debt schedule, maturity profile |
   | CP-4 | Analytical | Covenant-relevant metrics, EBITDA definitions |
   | CP-4C | Analytical | Covenant compliance calculations |
   | CP-5B | Infra | Structured data for database |
   | CP-5 | Infra | Full data set |
   | CP-RENDER | Infra | Formatted output |
   | CP-EXTRACT | Infra | .docx appendix parsing |
3. Per consumer: Readiness Status (Ready / Ready with Limitations / Not Ready), gaps, actions.
4. After this step → load SCHEMA_REFERENCE.md for 17-section output assembly.

## Output — T4.12 Gaps & Validation Warnings
`Gap Description` | `Affected Line Item or Metric` | `Affected Period(s)` | `Downstream Impact` | `Severity` | `Recommended Action`

## Output — T4.13 Downstream Readiness Matrix
`Downstream Module` | `Readiness Status` | `Gaps or Limitations` | `Recommended Actions`

## Warnings
- Every gap from every prior step must appear in T4.12. Cumulative — no omissions.
- Downstream Readiness must cover ALL 13 consumers.
</step_reference>
