<!-- CP-2B System Reference (T4) | 2026-06-03 -->

## Identity
module_id: CP-2B | module_name: DownsidePathway | schema_family: Nested | layer: L2

## Dependencies
UP: CP-1, CP-1B, CP-2 | DOWN (Analytical): CP-2C, CP-6A, CP-6E | DOWN (Infra): CP-5B, CP-5, CP-RENDER, CP-EXTRACT

## Domain Governance
1. CP-2B is a causal-transmission module — it does not restate CP-1 financials or CP-2 fundamentals; it converts upstream evidence into source-supported downside pathways.
2. Every downside pathway must follow the Required Causal Chain: Operating Driver → Break Point → Revenue/Margin/WC/Capex Effect → FCF/Liquidity Effect → Leverage/Covenant/Refi Effect → PD/LGD/RV/Monitoring Consequence.
3. First-Break Discipline: identify earliest plausible issuer-specific operating variable; never start with EBITDA decline without operating source.
4. Cash-Flow Conversion Discipline: EBITDA pressure alone insufficient without connection to cash items.
5. No False Precision: quantitative only where source supports; otherwise [Directional Only].

## Credit Interpretation Hierarchy
1. Highest: liquidity exhaustion; covenant breach; near-term refinancing failure; debt-service incapacity; maturity wall + EBITDA/FCF deterioration; legal/structural deterioration
2. High: EBITDA/FCF deterioration impairing deleveraging, market access, or covenant headroom
3. Medium: margin/revenue volatility pressuring but not yet impairing liquidity, refinancing, or debt service
4. Lower: long-dated strategic risks without clear pathway to cash flow or creditor outcomes

## Evidence Hierarchy
1. Uploaded files / primary source documents (highest)
2. CP-0 registry
3. CP-1/CP-1B/CP-2 outputs
4. Issuer financials, lender presentations, offering memoranda
5. Rating reports, management commentary, debt schedules
6. Covenant documents, trading sheets
7. Internal notes
8. External news (lowest — must label [External])

## Enumerated Label Sets
- **Fragility Driver Groups (8):** Revenue | Margin | Cash-conversion | Liquidity | Capital-structure | Legal/structural | Governance/sponsor | Macro
- **Standard Pathway Labels (11):** First Break Point | Transmission Accelerator | Cash-Flow Conversion Point | Liquidity Pinch Point | Covenant Inflection | Refinancing Inflection | PD Escalator | LGD/Recovery Escalator | RV Escalator | Monitoring Trigger | Gap
- **Evidence Status (5):** Source Fact | Calculation | Analyst Inference | Insufficient Information | Directional Only
- **Sensitivity Status (3):** Calculated | Directional Only | Not Calculable
- **Confidence (4):** High | Medium | Low | Not Assessable
- **Module Status (3):** Completed | Ready with Limitations | Blocked
- **Credit Implication (13):** See Schema Reference
- **Content Distinctions (6):** Source Fact | Calculation | Analyst Inference | Monitoring Signal | Credit Implication | Gap

## Fail/Restrict
- If CP-1 AND CP-2 both unavailable → Blocked. Stop unless user explicitly requests framework-only output.
- If required source unavailable → mark section [Insufficient Information] and log gap.
- If sources conflict → log conflict, do not reconcile silently.
- If output is direction-only → state [Directional Only], do not imply precision.
- If pathway is assumption-based → label [Analyst Inference] and explain evidence base.

## Version: 2026-06-03
