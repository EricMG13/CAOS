<!-- CP-1B Schema Reference (T3) | 2026-06-02 -->
## Required Tables (11)
| ID | Table | Key Columns |
|----|-------|-------------|
| T4.1 | Source Classification Register | Source File Name, Document Type, Period Coverage, Evidence Quality Tier, Analytical Use, Limitations |
| T4.2 | Definition Inheritance | Metric Name, CP-1 Canonical Def, CP-1 Formula, EBITDA Def in Use, Inheritance Status, Conflict Note |
| T4.3 | Summary / Top-Sheet | Row Label, Value/Observation (13 rows) |
| T4.4 | Financial Performance | Line Item, Period 1…N, YoY Abs/%, Analyst Note (19 lines) |
| T4.5 | KPI Dashboard | KPI Category, Metric, Period 1…N, YoY Change, Trend, Calc Status, Note |
| T4.6 | Variance Register | Metric, Basis, Prior/Current, Abs/%, Mgmt/Analyst Driver, Credit Implication |
| T4.7 | Corporate Actions | Event, Date, Description, Impact, Comparability Effect, Credit Implication, Source |
| T4.8 | Comparative Evaluation | Metric, Benchmark Source/Type, Expected/Actual, Variance, Credit Implication |
| T4.9 | Conflict Log | Conflict, Sources, Metrics, Periods, Materiality, Resolution, Downstream Impact |
| T4.10 | Monitoring Assessment | Signal Type, Metric, Evidence, Severity, Credit Implication, Action |
| T4.11 | Gaps & Limitations | Gap, Affected Metric, Periods, Downstream Impact, Severity, Action |

## QA Checklist
- [ ] CP-1 defs inherited/confirmed  - [ ] All 11 tables present  - [ ] Calcs traceable  - [ ] Content distinctions maintained  - [ ] No def switching  - [ ] Variance bases explicit  - [ ] Gaps cumulative in T4.11  - [ ] Appendix JSON A-E present  - [ ] Null ≠ zero

## Export: [Issuer]_CP-1B_[YYYYMMDD].docx
