<!-- CP-3C Schema Reference (T3) | 2026-06-03 -->

## Required Tables (8)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T3C.1 | Portfolio Input Gate | Input, Available / Missing, Source, Limitation, Portfolio Impact |
| T3C.2 | Portfolio Fit Register | Name / Instrument, Fit Category, Evidence, Risk Mechanic, Why It Fits / Does Not Fit, Constraints / Notes, Source Trace |
| T3C.3 | Position Sizing Posture Table | Name / Instrument, Sizing Posture, Evidence, Reason, Key Risk, Implementation Note, Confidence, Source Trace |
| T3C.4 | Risk Budget Flags | Flag, Evidence, Risk Mechanic, Why It Matters, Caution Level, Portfolio Impact, Source Trace |
| T3C.5 | Concentration and Correlation Register | Exposure Dimension, Current Exposure, Proposed / Pro Forma Exposure, Limit / Capacity, Evidence Status, Risk Mechanic, Portfolio Implication, Source Trace |
| T3C.6 | Liquidity and Implementation Assessment | Liquidity / Implementation Factor, Evidence, Risk Mechanic, Implementation Consequence, Constraint / Action, Source Trace |
| T3C.7 | Downside Budget and Recovery Sensitivity | Downside Scenario / Driver, Input Basis, Formula / Method, Result / Directional View, Portfolio Loss / Risk-Budget Implication, Status, Source Trace |
| T3C.8 | Monitoring Triggers | Trigger ID, Indicator, Leading / Lagging, Threshold or Qualitative Signal, Linked Risk Flag, Portfolio Action, Source Trace, Limitation |

## Standalone Tables
| ID | Name | Columns |
|----|------|---------|
| T3C.9 | Gaps Ledger | Gap ID, Missing Data, Why It Matters, Affected Sizing / Risk Budget / Trigger, Consequence for Confidence, Required Follow-Up Source |

## QA Checklist
- [ ] CP-3 output available — if missing, module is Blocked
- [ ] Module Status assigned (Completed / Completed with Limitations / Blocked)
- [ ] Output mode determined (Mandate-Specific / Generic Portfolio-Fit Logic)
- [ ] Every material factual claim, position number, mandate limit, security datapoint, market datapoint, legal/structural conclusion, liquidity assertion, and sizing conclusion is source-traceable
- [ ] Content distinctions maintained: Source Fact | Calculation | Analyst Inference | Portfolio Implication | Gap
- [ ] Sizing Posture assigned from canonical 7-value taxonomy (Avoid / Watchlist / Starter Position / Core Hold / Hold Existing Only / Reduce / Trim / Requires More Work)
- [ ] Minimum Evidence for Core verified — all 7 items present, or Core labelled as hypothetical framework-only
- [ ] Starter Conditions verified where Starter assigned
- [ ] Credit attractiveness alone does not justify Core Hold — portfolio capacity, liquidity, concentration, and downside-budget support required
- [ ] Numeric size expressed only if user provided one and portfolio constraints available
- [ ] Confidence label assigned per sizing conclusion (High / Medium / Low / Not Assessable)
- [ ] Fit Category assigned per issuer/security (Mandate fit / RV fit / Liquidity fit / Risk-budget fit / Not fit / Not assessable)
- [ ] Concentration assessed across 7 dimensions where data available
- [ ] Null used for unavailable numeric values — no unexplained blanks
- [ ] Liquidity/exit risk flagged where missing
- [ ] Scaling assumption not made without trading evidence
- [ ] Downside budget connected to portfolio loss at proposed size
- [ ] Monitoring triggers are specific, observable, and linked to portfolio actions
- [ ] Trigger IDs use CP-3C-MON-NNN format; Gap IDs use CP-3C-GAP-NNN format
- [ ] Gaps Ledger is cumulative across all steps
- [ ] Overall view introduces no new data
- [ ] Module completion statement includes Sizing Posture and Structured Export Status
- [ ] No generic buy/sell language — controlled sizing/action labels only
- [ ] No promotional language, equity-upside framing, or unsupported sizing conviction
- [ ] Limitations stated next to affected conclusion, not hidden in footnotes
- [ ] Structured exports use null (not zero) for unavailable numeric values unless source explicitly states zero

## Export: [Issuer]_CP-3C_[YYYYMMDD].docx
