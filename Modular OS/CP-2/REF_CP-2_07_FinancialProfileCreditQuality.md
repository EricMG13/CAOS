<!-- REF_CP-2_07 (T2) | 2026-06-03 -->
<step_reference module="CP-2" step="07" name="Financial Profile & Credit Quality Assessment">
<input>Steps 1-6 outputs; CP-1B financial data; uploaded financials</input>
<gate>Step 6 complete.</gate>

## Instructions
Evaluate issuer financial durability using a ratings-style lens. Complete the 9-dimension Financial Profile table (permitted Assessment values per Active Prompt: Strong / Average / Weak / Not Assessable). For each dimension provide Assessment + Credit Rationale grounded in the dimension-specific factors below:

| Dimension | Credit Rationale must consider |
|---|---|
| Scale / market position | Revenue scale, market relevance, market share if available, competitive standing, shock absorption |
| Competitive advantage | Moat, differentiation, switching costs, retention, IP, brand, contracts, regulation, network effects, execution |
| Business diversification | Product, customer, end-market, geography, channel, supplier, contract diversification |
| Cost and capex flexibility | Fixed-cost burden, input-cost exposure, maintenance capex, growth capex, working capital, cash preservation |
| Margin stability | Pricing power, pass-through, volatility, operating leverage, input costs, integration / restructuring risk |
| Free cash flow stability | EBITDA-to-FCF conversion, interest, taxes, capex, working capital, restructuring, dividends, recurring leakage |
| Ability to refinance / access capital markets | Maturity profile, market access, ratings trajectory if available, sponsor / parent support, lender appetite, market-window sensitivity |
| Liquidity position | Cash, revolver availability, covenant headroom, near-term maturities, working-capital needs, seasonality, cash burn |
| Financial policy and governance | Leverage tolerance, dividend policy, M&A appetite, sponsor behavior, governance, reporting transparency, creditor alignment |

After the table, synthesize: main credit supports, constraints, trend, and key missing datapoints.

If detailed financial data is unavailable, state: "Financial profile assessment is qualitative because detailed financial data is not available in the provided materials."

> **REPRODUCIBILITY NOTE — Strong/Average/Weak rubric.** The permitted labels (`Strong / Average / Weak / Not Assessable`) have **no evidence→label anchors** in the corpus — only the per-dimension "Credit Rationale must consider" factors above, which say *what to weigh*, not *what threshold makes a dimension Strong vs Average vs Weak*. The label is therefore analyst-judgment and may differ between analysts on the same evidence. Until a methodology owner defines per-dimension anchors, every `Assessment` **must carry an explicit `Credit Rationale` that names the specific issuer evidence driving the label** (already required by this step), so the *reasoning* is auditable even though the label itself is not yet rubric-pinned. Do not invent numeric cutoffs that the corpus does not define.

## Output
**T2.7 Financial Profile Scorecard:** `Dimension`|`Assessment`|`Credit Rationale`
Narrative: Synthesis of credit supports, constraints, trend, missing data.
</step_reference>
