<!-- CP-2C Schema Reference (T3) | 2026-06-02 -->
## Required Tables (7)
| ID | Table | Key Columns |
|----|-------|-------------|
| T5.1 | Event Source Register | Event ID, Source Document, Event Description, Event Category, Date/Range, Evidence Quality, Source Reliability |
| T5.2 | Catalyst Calendar | Date/Window, Event Description, Event Category, Credit Relevance Summary, Source |
| T5.3 | Event Risk Register | Event ID, Description, Probability, Credit Impact Channel(s), Impact Severity, Affected Metrics, Risk Direction, Source |
| T5.4 | Probability/Impact Matrix | Event ID, Description, Probability, Impact, P/I Classification |
| T5.5 | Monitoring Priority Table | Event ID, Description, Priority, Monitoring Frequency, Trigger Condition, Responsible Module |
| T5.6 | Watchlist Handoff Register | Event ID, Description, Priority, Receiving Module, Handoff Content, Timing, Rationale |
| T5.7 | Gaps & Limitations Ledger | Gap Description, Affected Section, Downstream Impact, Severity, Recommended Action |

## QA Checklist
- [ ] All events source-supported  - [ ] Calendar events explicitly dated/scheduled only (no inferred dates; undated events in Gaps Ledger)  - [ ] Probability/impact labels ordinal only  - [ ] Event risk channels mapped  - [ ] Priority rankings assigned  - [ ] Cross-module handoff complete  - [ ] Gaps cumulative  - [ ] Closing statement includes event count and horizon  - [ ] Appendix JSON A-E present

## Export: [Issuer]_CP-2C_[YYYYMMDD].docx
