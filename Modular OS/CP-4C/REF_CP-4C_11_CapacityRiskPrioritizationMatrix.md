<!-- REF_CP-4C_11 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="11" name="Capacity Risk Prioritization Matrix">
<input>All capacity analysis from Steps 4–10.</input>
<gate>Step 10 complete.</gate>

## Instructions
1. Prioritize supported capacity items by creditor relevance.
2. For each: record Priority (rank), Capacity Item, Severity, Confidence, Primary Risk Mechanic, PD Effect, LGD/Recovery Effect, Monitoring Action, Evidence ID.
3. Rank only supported items — do not rank items with [Insufficient Information] unless they can be partially characterized.
4. If ranking is not supportable, use [Insufficient Information].
5. Do not create exact scores unless evidence supports them.
6. This matrix is a key downstream input for CP-6A (bear legal-control attack) and CP-6E (portfolio sizing constraint).

## Output
T4C.11: `Priority`|`Capacity Item`|`Severity`|`Confidence`|`Primary Risk Mechanic`|`PD Effect`|`LGD / Recovery Effect`|`Monitoring Action`|`Evidence ID`
</step_reference>
