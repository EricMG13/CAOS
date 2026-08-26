---
module_id: CP-1
module_name: "Canonical Data Foundation"
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

Canonical four-quarter fixture in USD millions.

## Analysis

### Model period register

<!-- table-id: cp1.model_period_register -->
| period_id | fiscal_year | fiscal_quarter | period_type | start_date | end_date | day_count | audit_status | currency | unit | accounting_basis | entity_perimeter | source_id | source_locator | component_period_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FY2024_Q1 | 2024 | 1 | QUARTER | 2024-01-01 | 2024-03-31 | 91 | UNAUDITED | USD | MILLIONS | IFRS | Consolidated | SRC-1 | Annual report 2024 p. 42 | - |
| FY2024_Q2 | 2024 | 2 | QUARTER | 2024-04-01 | 2024-06-30 | 91 | UNAUDITED | USD | MILLIONS | IFRS | Consolidated | SRC-1 | Annual report 2024 p. 42 | - |
| FY2024_Q3 | 2024 | 3 | QUARTER | 2024-07-01 | 2024-09-30 | 92 | UNAUDITED | USD | MILLIONS | IFRS | Consolidated | SRC-1 | Annual report 2024 p. 42 | - |
| FY2024_Q4 | 2024 | 4 | QUARTER | 2024-10-01 | 2024-12-31 | 92 | UNAUDITED | USD | MILLIONS | IFRS | Consolidated | SRC-1 | Annual report 2024 p. 42 | - |

### Model account register

<!-- table-id: cp1.model_account_register -->
| metric_id | period_id | value | sign_convention | value_class | calculation_status | source_id | source_locator | conflict_refs | limitation_refs |
|---|---|---|---|---|---|---|---|---|---|
| revenue | FY2024_Q1 | 100 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cogs | FY2024_Q1 | -60 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| opex_including_da | FY2024_Q1 | -25 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| depreciation_amortization | FY2024_Q1 | 5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| ebitda | FY2024_Q1 | 20 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| adjusted_ebitda | FY2024_Q1 | 21 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_interest_paid | FY2024_Q1 | -4 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_lease_payments | FY2024_Q1 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_taxes_paid | FY2024_Q1 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cfo_ncfo | FY2024_Q1 | 15 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| working_capital_change | FY2024_Q1 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| capex_and_intangible_investment | FY2024_Q1 | -5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| acquisitions_disposals | FY2024_Q1 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_debt_issue_repay | FY2024_Q1 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_equity_issue_repay | FY2024_Q1 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| dividends_paid | FY2024_Q1 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| other_investing_financing | FY2024_Q1 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_cash_change | FY2024_Q1 | 9 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_and_equivalents | FY2024_Q1 | 29 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| rcf_commitment | FY2024_Q1 | 100 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| rcf_drawn | FY2024_Q1 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| senior_secured_debt | FY2024_Q1 | 200 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| unsecured_debt | FY2024_Q1 | 50 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| total_debt | FY2024_Q1 | 250 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| net_accounts_receivable | FY2024_Q1 | 20 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| inventory | FY2024_Q1 | 10 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| accounts_payable | FY2024_Q1 | 15 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| effective_tax_rate | FY2024_Q1 | 0.25 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| revenue | FY2024_Q2 | 110 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cogs | FY2024_Q2 | -66 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| opex_including_da | FY2024_Q2 | -27.5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| depreciation_amortization | FY2024_Q2 | 5.5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| ebitda | FY2024_Q2 | 22 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| adjusted_ebitda | FY2024_Q2 | 23 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_interest_paid | FY2024_Q2 | -4 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_lease_payments | FY2024_Q2 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_taxes_paid | FY2024_Q2 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cfo_ncfo | FY2024_Q2 | 16 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| working_capital_change | FY2024_Q2 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| capex_and_intangible_investment | FY2024_Q2 | -5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| acquisitions_disposals | FY2024_Q2 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_debt_issue_repay | FY2024_Q2 | -5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_equity_issue_repay | FY2024_Q2 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| dividends_paid | FY2024_Q2 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| other_investing_financing | FY2024_Q2 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_cash_change | FY2024_Q2 | 5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_and_equivalents | FY2024_Q2 | 34 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| rcf_commitment | FY2024_Q2 | 100 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| rcf_drawn | FY2024_Q2 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| senior_secured_debt | FY2024_Q2 | 195 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| unsecured_debt | FY2024_Q2 | 50 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| total_debt | FY2024_Q2 | 245 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| net_accounts_receivable | FY2024_Q2 | 22 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| inventory | FY2024_Q2 | 11 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| accounts_payable | FY2024_Q2 | 16 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| effective_tax_rate | FY2024_Q2 | 0.25 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| revenue | FY2024_Q3 | 120 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cogs | FY2024_Q3 | -72 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| opex_including_da | FY2024_Q3 | -30 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| depreciation_amortization | FY2024_Q3 | 6 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| ebitda | FY2024_Q3 | 24 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| adjusted_ebitda | FY2024_Q3 | 25 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_interest_paid | FY2024_Q3 | -4 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_lease_payments | FY2024_Q3 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_taxes_paid | FY2024_Q3 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cfo_ncfo | FY2024_Q3 | 17 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| working_capital_change | FY2024_Q3 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| capex_and_intangible_investment | FY2024_Q3 | -6 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| acquisitions_disposals | FY2024_Q3 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_debt_issue_repay | FY2024_Q3 | -5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_equity_issue_repay | FY2024_Q3 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| dividends_paid | FY2024_Q3 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| other_investing_financing | FY2024_Q3 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_cash_change | FY2024_Q3 | 5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_and_equivalents | FY2024_Q3 | 39 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| rcf_commitment | FY2024_Q3 | 100 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| rcf_drawn | FY2024_Q3 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| senior_secured_debt | FY2024_Q3 | 190 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| unsecured_debt | FY2024_Q3 | 50 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| total_debt | FY2024_Q3 | 240 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| net_accounts_receivable | FY2024_Q3 | 24 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| inventory | FY2024_Q3 | 12 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| accounts_payable | FY2024_Q3 | 17 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| effective_tax_rate | FY2024_Q3 | 0.25 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| revenue | FY2024_Q4 | 130 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cogs | FY2024_Q4 | -78 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| opex_including_da | FY2024_Q4 | -32.5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| depreciation_amortization | FY2024_Q4 | 6.5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| ebitda | FY2024_Q4 | 26 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| adjusted_ebitda | FY2024_Q4 | 27 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_interest_paid | FY2024_Q4 | -4 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_lease_payments | FY2024_Q4 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_taxes_paid | FY2024_Q4 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cfo_ncfo | FY2024_Q4 | 18 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| working_capital_change | FY2024_Q4 | -2 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| capex_and_intangible_investment | FY2024_Q4 | -6 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| acquisitions_disposals | FY2024_Q4 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_debt_issue_repay | FY2024_Q4 | -5 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_equity_issue_repay | FY2024_Q4 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| dividends_paid | FY2024_Q4 | -1 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| other_investing_financing | FY2024_Q4 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| net_cash_change | FY2024_Q4 | 6 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| cash_and_equivalents | FY2024_Q4 | 45 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |
| rcf_commitment | FY2024_Q4 | 100 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| rcf_drawn | FY2024_Q4 | 0 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| senior_secured_debt | FY2024_Q4 | 185 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| unsecured_debt | FY2024_Q4 | 50 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| total_debt | FY2024_Q4 | 235 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 note 12 | - | - |
| net_accounts_receivable | FY2024_Q4 | 26 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| inventory | FY2024_Q4 | 13 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| accounts_payable | FY2024_Q4 | 18 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 43 | - | - |
| effective_tax_rate | FY2024_Q4 | 0.25 | SIGNED_AS_REPORTED | SOURCED | Verified | SRC-1 | Annual report 2024 p. 42 | - | - |

### Segment revenue schedule

<!-- table-id: cp1.segment_revenue_schedule -->
| segment_id | segment_name | segment_type | display_priority | period_id | revenue | status | source_id | source_locator |
|---|---|---|---|---|---|---|---|---|
| services | Services | OPERATING_SEGMENT | 1 | FY2024_Q1 | 100 | Verified | SRC-1 | Annual report 2024 p. 15 |
| services | Services | OPERATING_SEGMENT | 1 | FY2024_Q2 | 110 | Verified | SRC-1 | Annual report 2024 p. 15 |
| services | Services | OPERATING_SEGMENT | 1 | FY2024_Q3 | 120 | Verified | SRC-1 | Annual report 2024 p. 15 |
| services | Services | OPERATING_SEGMENT | 1 | FY2024_Q4 | 130 | Verified | SRC-1 | Annual report 2024 p. 15 |

### CP-MODEL segment allocation

<!-- table-id: cp1.cp_model_segment_allocation -->
| slot_id | slot_label | component_segment_ids |
|---|---|---|
| DIVISION_1 | Services | services |

### Adjusted EBITDA bridge

<!-- table-id: cp1.adjusted_ebitda_bridge -->
| addback_id | addback_label | addback_classification | realization_status | display_priority | period_id | value | status | source_definition | source_id | source_locator |
|---|---|---|---|---|---|---|---|---|---|---|
| restructuring | Restructuring costs | RESTRUCTURING | REALIZED | 1 | FY2024_Q1 | 1 | Verified | Reported restructuring adjustment | SRC-1 | Annual report 2024 p. 47 |
| restructuring | Restructuring costs | RESTRUCTURING | REALIZED | 1 | FY2024_Q2 | 1 | Verified | Reported restructuring adjustment | SRC-1 | Annual report 2024 p. 47 |
| restructuring | Restructuring costs | RESTRUCTURING | REALIZED | 1 | FY2024_Q3 | 1 | Verified | Reported restructuring adjustment | SRC-1 | Annual report 2024 p. 47 |
| restructuring | Restructuring costs | RESTRUCTURING | REALIZED | 1 | FY2024_Q4 | 1 | Verified | Reported restructuring adjustment | SRC-1 | Annual report 2024 p. 47 |

### Debt facility register

<!-- table-id: cp1.debt_facility_register -->
| facility_id | facility_name | period_id | facility_type | carrying_value | principal | drawn_amount | commitment | secured_status | seniority | currency | margin_or_coupon | maturity_date | lease_classification | source_id | source_locator |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| term-loan | Senior term loan | FY2024_Q1 | TERM LOAN | 200 | 200 | 200 | 200 | SECURED | SENIOR | USD | SOFR plus 400bp | 2028-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| notes | Senior notes | FY2024_Q1 | SENIOR NOTES | 50 | 50 | 50 | 50 | UNSECURED | SENIOR | USD | 6.5 percent | 2029-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| rcf | Revolving credit facility | FY2024_Q1 | REVOLVING CREDIT FACILITY | 0 | 100 | 0 | 100 | SECURED | SUPER_SENIOR | USD | SOFR plus 350bp | 2027-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| term-loan | Senior term loan | FY2024_Q2 | TERM LOAN | 195 | 195 | 195 | 195 | SECURED | SENIOR | USD | SOFR plus 400bp | 2028-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| notes | Senior notes | FY2024_Q2 | SENIOR NOTES | 50 | 50 | 50 | 50 | UNSECURED | SENIOR | USD | 6.5 percent | 2029-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| rcf | Revolving credit facility | FY2024_Q2 | REVOLVING CREDIT FACILITY | 0 | 100 | 0 | 100 | SECURED | SUPER_SENIOR | USD | SOFR plus 350bp | 2027-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| term-loan | Senior term loan | FY2024_Q3 | TERM LOAN | 190 | 190 | 190 | 190 | SECURED | SENIOR | USD | SOFR plus 400bp | 2028-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| notes | Senior notes | FY2024_Q3 | SENIOR NOTES | 50 | 50 | 50 | 50 | UNSECURED | SENIOR | USD | 6.5 percent | 2029-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| rcf | Revolving credit facility | FY2024_Q3 | REVOLVING CREDIT FACILITY | 0 | 100 | 0 | 100 | SECURED | SUPER_SENIOR | USD | SOFR plus 350bp | 2027-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| term-loan | Senior term loan | FY2024_Q4 | TERM LOAN | 185 | 185 | 185 | 185 | SECURED | SENIOR | USD | SOFR plus 400bp | 2028-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| notes | Senior notes | FY2024_Q4 | SENIOR NOTES | 50 | 50 | 50 | 50 | UNSECURED | SENIOR | USD | 6.5 percent | 2029-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |
| rcf | Revolving credit facility | FY2024_Q4 | REVOLVING CREDIT FACILITY | 0 | 100 | 0 | 100 | SECURED | SUPER_SENIOR | USD | SOFR plus 350bp | 2027-06-30 | NOT_LEASE | SRC-1 | Annual report 2024 note 12 |

### Model reconciliation register

<!-- table-id: cp1.model_reconciliation_register -->
| check_id | period_id | check_type | reported_value | calculated_value | difference | tolerance | status | explanation | source_refs |
|---|---|---|---|---|---|---|---|---|---|
| segment-q1 | FY2024_Q1 | SEGMENT_REVENUE | 100 | 100 | 0 | 0 | PASS | Segment equals reported revenue | SRC-1 |
| ebitda-q1 | FY2024_Q1 | ADJUSTED_EBITDA_BRIDGE | 21 | 21 | 0 | 0 | PASS | EBITDA plus add-back | SRC-1 |
| segment-q2 | FY2024_Q2 | SEGMENT_REVENUE | 110 | 110 | 0 | 0 | PASS | Segment equals reported revenue | SRC-1 |
| ebitda-q2 | FY2024_Q2 | ADJUSTED_EBITDA_BRIDGE | 23 | 23 | 0 | 0 | PASS | EBITDA plus add-back | SRC-1 |
| segment-q3 | FY2024_Q3 | SEGMENT_REVENUE | 120 | 120 | 0 | 0 | PASS | Segment equals reported revenue | SRC-1 |
| ebitda-q3 | FY2024_Q3 | ADJUSTED_EBITDA_BRIDGE | 25 | 25 | 0 | 0 | PASS | EBITDA plus add-back | SRC-1 |
| segment-q4 | FY2024_Q4 | SEGMENT_REVENUE | 130 | 130 | 0 | 0 | PASS | Segment equals reported revenue | SRC-1 |
| ebitda-q4 | FY2024_Q4 | ADJUSTED_EBITDA_BRIDGE | 27 | 27 | 0 | 0 | PASS | EBITDA plus add-back | SRC-1 |

### Downstream readiness

<!-- table-id: cp1.downstream_readiness -->
| downstream_module | status | missing_metric_ids | conflict_refs | explanation |
|---|---|---|---|---|
| CP-MODEL | ready | - | - | Four complete quarters reconciled |

## Evidence Trace

All fixture values map to SRC-1 with precise locators.

## Source Registry

SRC-1 is the 2024 annual report.

## Gaps & Conflicts

None for the fixture.

## QA Validation

Periods, accounts, segments, add-backs, debt, and reconciliations are complete.
