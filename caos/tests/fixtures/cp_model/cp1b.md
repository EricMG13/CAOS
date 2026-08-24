---
module_id: CP-1B
module_name: "Earnings Delta"
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

Canonical fixture earnings comparison.

## Analysis

### Model comparator register

<!-- table-id: cp1b.model_comparator_register -->
| metric_id | current_period_id | reference_period_id | comparison_basis | current_value | reference_value | absolute_change | percentage_change | calculation_status | restatement_flag | basis_change_flag | perimeter_change_flag | definition_change_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| revenue | FY2024_Q4 | FY2024_Q3 | SEQUENTIAL | 130 | 120 | 10 | 0.083333 | Calculated | false | false | false | false |

### Model validation register

<!-- table-id: cp1b.model_validation_register -->
| metric_id | period_id | cp1_value | cp1b_comparison_value | difference | tolerance | status | explanation | source_or_conflict_ref |
|---|---|---|---|---|---|---|---|---|
| revenue | FY2024_Q1 | 100 | 100 | 0 | 0 | PASS | Matched | SRC-1 |
| ebitda | FY2024_Q1 | 20 | 20 | 0 | 0 | PASS | Matched | SRC-1 |
| adjusted_ebitda | FY2024_Q1 | 21 | 21 | 0 | 0 | PASS | Matched | SRC-1 |
| cfo_ncfo | FY2024_Q1 | 15 | 15 | 0 | 0 | PASS | Matched | SRC-1 |
| capex_and_intangible_investment | FY2024_Q1 | -5 | -5 | 0 | 0 | PASS | Matched | SRC-1 |
| total_debt | FY2024_Q1 | 250 | 250 | 0 | 0 | PASS | Matched | SRC-1 |
| cash_and_equivalents | FY2024_Q1 | 29 | 29 | 0 | 0 | PASS | Matched | SRC-1 |
| revenue | FY2024_Q2 | 110 | 110 | 0 | 0 | PASS | Matched | SRC-1 |
| ebitda | FY2024_Q2 | 22 | 22 | 0 | 0 | PASS | Matched | SRC-1 |
| adjusted_ebitda | FY2024_Q2 | 23 | 23 | 0 | 0 | PASS | Matched | SRC-1 |
| cfo_ncfo | FY2024_Q2 | 16 | 16 | 0 | 0 | PASS | Matched | SRC-1 |
| capex_and_intangible_investment | FY2024_Q2 | -5 | -5 | 0 | 0 | PASS | Matched | SRC-1 |
| total_debt | FY2024_Q2 | 245 | 245 | 0 | 0 | PASS | Matched | SRC-1 |
| cash_and_equivalents | FY2024_Q2 | 34 | 34 | 0 | 0 | PASS | Matched | SRC-1 |
| revenue | FY2024_Q3 | 120 | 120 | 0 | 0 | PASS | Matched | SRC-1 |
| ebitda | FY2024_Q3 | 24 | 24 | 0 | 0 | PASS | Matched | SRC-1 |
| adjusted_ebitda | FY2024_Q3 | 25 | 25 | 0 | 0 | PASS | Matched | SRC-1 |
| cfo_ncfo | FY2024_Q3 | 17 | 17 | 0 | 0 | PASS | Matched | SRC-1 |
| capex_and_intangible_investment | FY2024_Q3 | -6 | -6 | 0 | 0 | PASS | Matched | SRC-1 |
| total_debt | FY2024_Q3 | 240 | 240 | 0 | 0 | PASS | Matched | SRC-1 |
| cash_and_equivalents | FY2024_Q3 | 39 | 39 | 0 | 0 | PASS | Matched | SRC-1 |
| revenue | FY2024_Q4 | 130 | 130 | 0 | 0 | PASS | Matched | SRC-1 |
| ebitda | FY2024_Q4 | 26 | 26 | 0 | 0 | PASS | Matched | SRC-1 |
| adjusted_ebitda | FY2024_Q4 | 27 | 27 | 0 | 0 | PASS | Matched | SRC-1 |
| cfo_ncfo | FY2024_Q4 | 18 | 18 | 0 | 0 | PASS | Matched | SRC-1 |
| capex_and_intangible_investment | FY2024_Q4 | -6 | -6 | 0 | 0 | PASS | Matched | SRC-1 |
| total_debt | FY2024_Q4 | 235 | 235 | 0 | 0 | PASS | Matched | SRC-1 |
| cash_and_equivalents | FY2024_Q4 | 45 | 45 | 0 | 0 | PASS | Matched | SRC-1 |

### Add-back validation register

<!-- table-id: cp1b.addback_validation_register -->
| addback_id | period_id | cp1_value | cp1b_comparison_value | difference | tolerance | status | label_match | definition_change_flag | explanation | source_or_conflict_ref |
|---|---|---|---|---|---|---|---|---|---|---|
| restructuring | FY2024_Q1 | 1 | 1 | 0 | 0 | PASS | true | false | Matched | SRC-1 |
| restructuring | FY2024_Q2 | 1 | 1 | 0 | 0 | PASS | true | false | Matched | SRC-1 |
| restructuring | FY2024_Q3 | 1 | 1 | 0 | 0 | PASS | true | false | Matched | SRC-1 |
| restructuring | FY2024_Q4 | 1 | 1 | 0 | 0 | PASS | true | false | Matched | SRC-1 |

### Model readiness

<!-- table-id: cp1b.model_readiness -->
| downstream_module | status | blocking_metric_ids | blocking_period_ids | conflict_refs | explanation |
|---|---|---|---|---|---|
| CP-MODEL | ready | - | - | - | Required comparisons validated |

### CP-MODEL snapshot fields

<!-- table-id: cp1b.cp_model_snapshot_fields -->
| field_id | value | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|
| historical_performance | Revenue and EBITDA increased through FY2024 | READY | SRC-1 | Annual report 2024 p. 42 | 2024-12-31 |

## Evidence Trace

All validation rows map to SRC-1.

## Source Registry

SRC-1 is the 2024 annual report.

## Gaps & Conflicts

None for the fixture.

## QA Validation

All CP-MODEL validation rows pass.
