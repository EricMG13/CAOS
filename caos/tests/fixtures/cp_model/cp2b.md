---
module_id: CP-2B
module_name: "Catalyst and Event-Risk Projection"
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

Canonical fixture catalyst projection.

## Analysis

### CP-MODEL catalysts

<!-- table-id: cp2b.cp_model_catalysts -->
| rank | event_date_or_window | event | credit_relevance | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|---|---|
| 1 | 2025-06-30 | Covenant test | Tests headroom and refinancing flexibility | READY | SRC-1 | Annual report 2024 note 12 | 2024-12-31 |

## Evidence Trace

The catalyst maps to SRC-1.

## Source Registry

SRC-1 is the 2024 annual report.

## Gaps & Conflicts

None for the fixture.

## QA Validation

The catalyst is dated and source-grounded.
