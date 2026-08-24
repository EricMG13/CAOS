---
module_id: CP-2
module_name: "Fundamental Credit Synthesis"
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

Canonical fixture synthesis.

## Analysis

### CP-MODEL strengths and weaknesses

<!-- table-id: cp2.cp_model_strengths_weaknesses -->
| direction | rank | label | mechanism | evidence_ids | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|---|---|---|
| STRENGTH | 1 | Recurring revenue | Contracted services support cash generation | EV-1 | READY | SRC-1 | Annual report 2024 p. 3 | 2024-12-31 |
| WEAKNESS | 1 | Leverage | Debt load constrains financial flexibility | EV-2 | READY | SRC-1 | Annual report 2024 note 12 | 2024-12-31 |

## Evidence Trace

EV-1 and EV-2 map to SRC-1.

## Source Registry

SRC-1 is the 2024 annual report.

## Gaps & Conflicts

None for the fixture.

## QA Validation

Rankings are contiguous and source-grounded.
