<!-- CP-3 Schema Reference (T3) | 2026-06-03 -->

## Required Tables (7)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T3.1 | Source Register | source_document_id, source_document_name, source_quality, period, entity_covered, data_supplied, limitation, downstream_use |
| T3.3 | Issuer / Security Scorecard | Category, Factor, Weight, Raw Score 1–5, Weighted Score, Confidence, Evidence, Risk Mechanic, Credit Implication |
| T3.4 | Override Log | Override Type, Trigger Evidence, Score Cap / Penalty, Revised Composite Score, Explanation |
| T3.5 | Relative Value Table | Security, Market Level, Market Date, Source, Quote Quality, Comps, Seniority / Security, Compensation vs. Risk, RV Label |
| T3.6 | Fundamental Value Matrix | Security / Issuer, Fundamental View, Relative-Value View, Structural / Recovery View, Final Matrix Bucket, Rationale |
| T3.7 | Final Ranking | Rank, Issuer, Security / Tranche, Composite Score /100, Normalized /5.0, Credit Tier, Fundamental View, Relative Value View, Final Recommendation, Strongest Attribute, Weakest Attribute, Key Credit Issue, Monitoring Trigger |
| T3.9 | Monitoring Triggers | Trigger, Threshold / Signal, Why It Matters, Credit / RV Impact, Evidence ID |

## Standalone Tables
| ID | Name | Columns |
|----|------|---------|
| T3.10 | Gaps Ledger | Gap, Missing Data, Why It Matters, Impact on Output, Required Follow-Up |

## QA Checklist
- [ ] Execution mode determined and required inputs verified per mode
- [ ] Module Status assigned (Full Run / Ready with Limitations / Blocked)
- [ ] Every material factual claim, score, RV conclusion, and recommendation is source-traceable
- [ ] Content distinctions maintained: Sourced Fact | Calculated Metric | Analyst Inference | Insufficient Information | Unsupported Conclusion
- [ ] Scope separation maintained: Fundamental | Structural | Legal/Recovery | Market Compensation | Technicals/Liquidity | Portfolio Constraints | Recommendation
- [ ] Score Direction correct: 1 = Conservative → 5 = Aggressive
- [ ] Every score includes Confidence tag (High / Medium / Low / Not Assessable)
- [ ] No precise composite score assigned if factor evidence materially incomplete — use range, Not Scorable, or Not Assessable
- [ ] Credit Tier correctly mapped from composite score
- [ ] Hard-risk overrides applied only where justified by evidence; not used to force ranking
- [ ] RV label assigned only with dated market evidence; Unclear used when market data absent
- [ ] Market claims identify: pricing date, source, instrument, currency, seniority, maturity, metric basis, liquidity/quote-quality limitation
- [ ] Instrument comparisons disclose seniority, maturity, currency, metric basis, and pricing-source limitations
- [ ] Weak credit not classified as Preferred solely due to wide spread
- [ ] Strong credit not classified as Avoid solely due to tight spread (unless clearly inadequate)
- [ ] Security-Selection formulation used for Step 8 conclusions
- [ ] Final Credit/RV View formulation used for Step 11 synthesis
- [ ] Monitoring triggers are specific and observable
- [ ] Gaps Ledger is cumulative across all steps
- [ ] Final view introduces no new data
- [ ] Module completion statement includes Recommendation and RV labels
- [ ] Generic adjectives absent unless issuer-specific evidence and dated market data support them
- [ ] No fabrication of spreads, prices, yields, DM, ratings, covenant terms, recovery assumptions, or technicals
- [ ] Python used for all arithmetic (scorecard weighting, composite score, normalization)
- [ ] Structured exports use null (not zero) for unavailable numeric values unless source explicitly states zero
- [ ] Percentages stored as decimals in structured exports
- [ ] CP-1 metric definitions preserved where applicable

## Export: [Issuer]_CP-3_[YYYYMMDD].docx
