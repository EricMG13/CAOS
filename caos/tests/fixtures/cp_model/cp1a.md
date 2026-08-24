---
module_id: CP-1A
module_name: "Business and Transaction Fact Pack"
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

Canonical fixture fact pack.

## Analysis

### CP-MODEL snapshot fields

<!-- table-id: cp1a.cp_model_snapshot_fields -->
| field_id | value | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|
| issuer_name | Acme Credit Ltd | READY | SRC-1 | Annual report 2024 cover | 2024-12-31 |
| sector | Business services | READY | SRC-1 | Annual report 2024 p. 3 | 2024-12-31 |
| country | United Kingdom | READY | SRC-1 | Annual report 2024 p. 2 | 2024-12-31 |
| shareholders | Diversified institutional ownership | READY | SRC-1 | Annual report 2024 p. 7 | 2024-12-31 |
| transaction_summary | Existing senior secured capital structure | READY | SRC-1 | Annual report 2024 note 12 | 2024-12-31 |
| business_description | Provider of recurring business services | READY | SRC-1 | Annual report 2024 p. 3 | 2024-12-31 |

## Evidence Trace

All fields cite SRC-1.

## Source Registry

SRC-1 is the 2024 annual report.

## Gaps & Conflicts

None for the fixture.

## QA Validation

All required snapshot fields are ready.
