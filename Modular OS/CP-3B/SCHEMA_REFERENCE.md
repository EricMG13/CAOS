<!-- CP-3B Schema Reference (T3) | 2026-06-03 -->

## Required Tables (9)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T3B.1 | Source Register | source_document_id, source_document_name, source_quality, period, entity_covered, data_supplied, limitation, downstream_use |
| T3B.2 | Capital Structure Dashboard | Instrument, Type, Amount, Currency, Maturity, Seniority / Lien, Collateral, Guarantors, Coupon / Margin, Fixed / Floating, Source Trace |
| T3B.3 | Instrument Matrix | Instrument, Price, Spread / Yield / DM, Market Date, Source, Quote Quality, Call Schedule, Covenant Package, Liquidity, Source Trace |
| T3B.4 | Structural Positioning Log | Instrument, Structural Rank, Contractual Seniority, Lien Priority, Guarantee Coverage, Collateral Coverage, Structural Subordination, Priming Capacity, Key Risk Mechanic, Source Trace |
| T3B.5 | Legal / Covenant / LME Overlay | Instrument, Legal / Structural Finding, Priming Risk, Leakage Risk, Weak Collateral, Covenant Weakness, LME Vulnerability, Exposed Creditor Class, Source (CP-4 / CP-4C / CP-3D), Source Trace |
| T3B.6 | Recovery Sensitivity | Instrument, Recovery Sensitivity, Evidence, Risk Mechanic, Credit Implication, Confidence, Source Trace |
| T3B.7 | Compensation Cross-Check | Instrument, Market Level, Market Date, Structural Rank, Recovery Sensitivity, Compensation Adequacy, Compensation vs. Risk, Source Trace |
| T3B.8 | Preference Decision Table | Instrument, Preference, Structural Position, Recovery Sensitivity, Compensation Adequacy, Confidence, Key Reason, Monitoring Trigger, Source Trace |
| T3B.10 | Monitoring Triggers | Trigger, Instrument, Threshold / Signal, Why It Matters, Credit / Recovery Impact, Evidence ID |

## Standalone Tables
| ID | Name | Columns |
|----|------|---------|
| T3B.11 | Gaps Ledger | Gap, Missing Data, Why It Matters, Impact on Output, Required Follow-Up |

## QA Checklist
- [ ] Input gates verified: CP-3 RV analysis available AND capital structure includes seniority/subordination
- [ ] Module Status assigned (Full Run / Ready with Limitations / Blocked)
- [ ] Every material factual claim, instrument datapoint, market datapoint, legal/structural conclusion, recovery interpretation, and refinancing/LME overlay is source-traceable
- [ ] Content distinctions maintained: Instrument Fact | Market Datapoint | Legal/Structural Fact | Recovery Interpretation | Refinancing/LME Overlay | Relative-Value Judgment | Recommendation | Gap
- [ ] Instruments ordered by structural priority (not maturity)
- [ ] Instrument Type Taxonomy labels used consistently
- [ ] Structural Concepts applied correctly per instrument
- [ ] Recovery Sensitivity Label assigned per instrument (Low / Moderate / High / Binary / Insufficient Information)
- [ ] Evidence Confidence Label assigned per instrument (High / Medium / Low / Structural Only / Market Only / Insufficient Information)
- [ ] Compensation Adequacy Label assigned per instrument (Attractive / Adequate / Inadequate / Unclear / Insufficient Information)
- [ ] Preference Decision Rules applied correctly (Preferred / Secondary / Avoid / Requires More Work)
- [ ] Yield alone does not override weak recovery, legal position, maturity concentration, liquidity, or LME exposure
- [ ] No forced preference where pricing, ranking, collateral, guarantor, recovery, or legal data is insufficient
- [ ] CP-4/CP-4C findings (priming, leakage, weak collateral, covenant weakness) carried into structural and recovery assessment
- [ ] CP-3D findings (refinancing/LME vulnerability) mapped to exposed creditor class
- [ ] Draft, unsigned, stale, incomplete, or conflicting documents flagged with reduced confidence
- [ ] Monitoring triggers are specific, observable, and per-instrument
- [ ] Gaps Ledger is cumulative across all steps
- [ ] Overall view introduces no new data
- [ ] Module completion statement includes preference assignments
- [ ] Generic adjectives absent unless issuer-specific evidence supports them
- [ ] No fabrication of recovery values, collateral sufficiency, guarantor coverage, priming capacity, pricing, liquidity, or instrument eligibility
- [ ] Structured exports use null (not zero) for unavailable numeric values unless source explicitly states zero
- [ ] No generic buy/sell language — Preferred/Secondary/Avoid/Requires More Work only

## Export: [Issuer]_CP-3B_[YYYYMMDD].docx
