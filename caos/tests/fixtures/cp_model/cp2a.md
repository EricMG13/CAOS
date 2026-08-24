---
module_id: CP-2A
module_name: "Downside Pathway"
run_id: "run-cp-model-fixture"
reporting_period: "FY2024"
analysis_date: "2025-02-15"
confidence_score: 85
confidence_band: High
qa_status: Passed
committee_status: Draft Only
limitation_flags: []
validation_warnings: []
upstream_artifacts_used: []
downstream_consumers: [CP-MODEL]
issuer_name: "Acme Credit Ltd"
issuer_id: "Acme-Credit"
---

## Audit Summary

Canonical fixture downside pathway with the absorbed CP-2B registers.

## Analysis

### T5.1 — Event Source Register
| Event ID | Source Document | Event Description | Event Category | Date/Range | Evidence Quality | Source Reliability |
|---|---|---|---|---|---|---|
| EVT-1 | SRC-1 | Covenant test | Covenant | 2025-06-30 | High | Primary filing |

### T5.2 — Catalyst Calendar
| Date/Window | Event Description | Event Category | Credit Relevance Summary | Source |
|---|---|---|---|---|
| 2025-06-30 | Covenant test | Covenant | Tests headroom | SRC-1 Annual report 2024 note 12 |

### T5.3 — Event Risk Register
| Event ID | Description | Probability | Credit Impact Channel(s) | Impact Severity | Affected Metrics | Risk Direction | Source |
|---|---|---|---|---|---|---|---|
| EVT-1 | Covenant test | Medium | covenant | High | leverage | Negative | SRC-1 Annual report 2024 note 12 |

### T5.4 — Probability Impact Matrix
| Event ID | Description | Probability | Impact | P/I Classification |
|---|---|---|---|---|
| EVT-1 | Covenant test | Medium | High | Medium High |

### T5.5 — Monitoring Priority Table
| Event ID | Description | Priority | Monitoring Frequency | Trigger Condition | Responsible Module |
|---|---|---|---|---|---|
| EVT-1 | Covenant test | High | Monthly | Headroom below 15 percent | CP-4 |

### T5.6 — Watchlist Handoff Register
| Event ID | Description | Priority | Receiving Module | Handoff Content | Timing | Rationale |
|---|---|---|---|---|---|---|
| EVT-1 | Covenant test | High | CP-4 | Recalculate covenant headroom | Monthly | Protect against breach risk |

### T5.7 — Gaps and Limitations Ledger
| Gap Description | Affected Section | Downstream Impact | Severity | Recommended Action |
|---|---|---|---|---|
| Interim covenant calculation unavailable | T5.5 | Monitoring uses annual baseline | Medium | Refresh after interim filing |

### CP-MODEL catalysts

<!-- table-id: cp2b.cp_model_catalysts -->
| rank | event_date_or_window | event | credit_relevance | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|---|---|
| 1 | 2025-06-30 | Covenant test | Tests headroom and refinancing flexibility | READY | SRC-1 | Annual report 2024 note 12 | 2024-12-31 |

## Evidence Trace

All event rows preserve the SRC-1 locator.

## Source Registry

SRC-1 is the 2024 annual report.

## Gaps & Conflicts

The interim covenant calculation is unavailable.

## QA Validation

T5.1 through T5.7 and the CP-MODEL catalyst projection are complete.
