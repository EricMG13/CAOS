<!-- CP-2B Schema Reference (T3) | 2026-06-03 -->

## Required Tables (9)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T2B.1 | Source Register | source_document_id, source_document_name, source_quality, period, entity_covered, data_supplied, limitation, downstream_use |
| T2B.2 | Business Model Snapshot | Dimension, Source-Supported Fact, Risk Mechanic, Credit Implication, Source Trace, Limitation |
| T2B.3 | Fragility Map | Fragility Driver, First Break Point, Evidence, Risk Mechanic, Credit Implication, Confidence, Source Trace |
| T2B.4 | Stress Transmission Table | Operating Stress, Cash-Flow Impact, Leverage / Liquidity Result, Credit Consequence, Evidence Status, Source Trace |
| T2B.5 | Downside Pathway Register | Pathway Row ID, Pathway Category, Driver, Causal Vector, PD/LGD/RV/Monitoring Consequence, Source Trace, Confidence, Downstream Module |
| T2B.6 | Downside Sensitivity Matrix | Sensitivity, Input Basis, Formula / Method, Result, Credit Interpretation, Status, Source Trace |
| T2B.7 | Monitoring Sensitivity Flags | Trigger ID, Indicator, Leading / Lagging, Threshold or Qualitative Signal, Linked Pathway Row, Escalation Consequence, Source Trace, Limitation |
| T2B.8 | Cross-Module Handoff Register | Downstream Module, Handoff Item, Why It Matters, Required Consumer Action, Source / Pathway Link, Limitation |
| T2B.9 | Gaps Ledger | Gap ID, Missing Data, Why It Matters, Affected Pathway / Calculation / Trigger, Consequence for Confidence, Required Follow-Up Source |

## Canonical Credit Implication (13 values)
Positive — Deleveraging | Positive — Margin Expansion | Positive — Revenue Growth | Positive — Liquidity Improvement | Positive — Covenant Headroom Expansion | Neutral — Stable | Negative — Leverage Increase | Negative — Margin Compression | Negative — Revenue Decline | Negative — Liquidity Deterioration | Negative — Covenant Erosion | Negative — Refinancing Risk | Insufficient Information

## Evidence Status Values
Source Fact | Calculation | Analyst Inference | Insufficient Information | Directional Only

## Sensitivity Status Values
Calculated | Directional Only | Not Calculable

## Confidence Values
High | Medium | Low | Not Assessable

## QA Checklist
- [ ] Source register completed with all available sources and limitations
- [ ] Module status stated: Completed / Ready with Limitations / Blocked
- [ ] Blocking gate enforced: both CP-1 and CP-2 unavailable → Blocked
- [ ] Every material conclusion follows [Evidence] → [Risk Mechanic] → [Credit Implication]
- [ ] Required Causal Chain applied: Operating Driver → Break Point → Effect → FCF/Liquidity → Leverage/Covenant/Refi → Consequence
- [ ] First-Break Discipline: no pathway begins with EBITDA decline without identifying operating source
- [ ] Cash-Flow Conversion Discipline: every path translates to cash-flow effects
- [ ] Directional Vector Discipline: explicit arrows, no broad statements without transmission mechanism
- [ ] No False Precision: quantitative sensitivities only where source supports
- [ ] Content distinctions applied: Source Fact | Calculation | Analyst Inference | Monitoring Signal | Credit Implication | Gap
- [ ] All pathway rows have Pathway Row IDs (CP-2B-DP-###)
- [ ] All triggers map to pathway rows
- [ ] All trigger IDs follow format (CP-2B-MON-###)
- [ ] All gaps logged with Gap IDs (CP-2B-GAP-###)
- [ ] Cross-module handoff register covers all 11 downstream consumers
- [ ] Overall View contains no new data — synthesis only
- [ ] Export contract followed: single .docx + Appendices A-E

## Export: [Issuer]_CP-2B_[YYYYMMDD].docx
