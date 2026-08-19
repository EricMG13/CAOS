<!-- REF_CP-6E_09 (T2) | 2026-06-03 -->
<step_reference module="CP-6E" step="09" name="Exact Portfolio Constraint">
<input>Steps 1-8; Portfolio Constraint Taxonomy.</input>
<gate>Step 8 complete.</gate>

## Instructions
1. Identify exactly **one** binding portfolio constraint using the Portfolio Constraint Taxonomy (12-type priority order in Active Prompt).
2. For this constraint, state:
   - **Exact Portfolio Constraint:** [Constraint category from taxonomy]
   - **Evidence:** (specific source, metric, limit)
   - **Risk Mechanic:** (how the constraint caps position size)
   - **Credit / Portfolio Implication:** (what happens if breached or near-breached)
   - **Evidence Needed to Resolve:** (what data would relax or confirm the constraint)
3. If several constraints apply → pick the one that most directly caps size; list others as residual risks in CIO memo.
4. If mandate constraints are unavailable → write [Insufficient Information] and specify the missing mandate/exposure report.
5. Do NOT convert generic credit risk into a portfolio constraint unless it maps to an explicit limit, bucket, or risk-budget metric.

## Output
Exact Portfolio Constraint: structured statement with constraint category, evidence, risk mechanic, credit/portfolio implication, evidence needed to resolve.
</step_reference>
