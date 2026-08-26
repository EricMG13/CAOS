---
module_id: CP-2G
module_name: "Forward Credit Model"
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

Source-grounded Base and Downside forecast assumptions are provided for the canonical model build.

## Analysis

### Forward credit view

The Base case assumes measured Services growth moderates across the three-year forecast while discretionary financing flows remain controlled. The Downside case applies a near-term revenue contraction followed by gradual stabilization, retaining the same explicit financing assumptions so the operating shock remains isolated and auditable. The first material inflection is therefore the opening forecast year, when weaker revenue pressures cash generation and slows deleveraging. Liquidity, leverage, coverage, and refinancing consequences are calculated by CP-MODEL from these named drivers and the validated historical balance sheet. Monitoring focuses on reported revenue trajectory, cash conversion, debt movement, and evidence that the issuer preserves available liquidity rather than substituting unsupported model plugs.

### T2H.3 — forecast assumption register

<!-- table-id: cp2g.cp_model_forecast_drivers -->
| driver_id | slot_id | case | period_id | fiscal_year | value | unit | assumption_id | status | source_id | source_locator | as_of | gap_code |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| division_growth | DIVISION_1 | BASE | FY2025 | 2025 | 0.05 | PERCENT_DECIMAL | operating.revenue_growth.division_1 | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| division_growth | DIVISION_2 | BASE | FY2025 | 2025 |  | PERCENT_DECIMAL | operating.revenue_growth.division_2 | NOT_APPLICABLE |  |  |  |  |
| division_growth | DIVISION_3 | BASE | FY2025 | 2025 |  | PERCENT_DECIMAL | operating.revenue_growth.division_3 | NOT_APPLICABLE |  |  |  |  |
| consolidated_revenue_growth |  | BASE | FY2025 | 2025 |  | PERCENT_DECIMAL | operating.consolidated_revenue_growth | NOT_APPLICABLE |  |  |  |  |
| adjusted_ebitda_margin |  | BASE | FY2025 | 2025 | 0.2 | PERCENT_DECIMAL | operating.adjusted_ebitda_margin | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| identified_addbacks |  | BASE | FY2025 | 2025 | 4 | CURRENCY_MM | operating.identified_addbacks | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| capex_pct_revenue |  | BASE | FY2025 | 2025 | 0.05 | PERCENT_DECIMAL | cash_flow.capex_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| working_capital_pct_revenue |  | BASE | FY2025 | 2025 | -0.02 | PERCENT_DECIMAL | cash_flow.working_capital_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| cash_tax_pct_revenue |  | BASE | FY2025 | 2025 | -0.02 | PERCENT_DECIMAL | cash_flow.cash_tax_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| lease_cash_pct_revenue |  | BASE | FY2025 | 2025 | -0.01 | PERCENT_DECIMAL | cash_flow.lease_cash_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| base_rate |  | BASE | FY2025 | 2025 | 0.05 | PERCENT_DECIMAL | rates.base_rate | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_spread |  | BASE | FY2025 | 2025 | 0.04 | PERCENT_DECIMAL | rates.debt_spread | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| contractual_amortization |  | BASE | FY2025 | 2025 | 10 | CURRENCY_MM | capital.contractual_amortization | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_issuance |  | BASE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.debt_issuance | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_repayment |  | BASE | FY2025 | 2025 | 5 | CURRENCY_MM | capital.debt_repayment | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| refinancing_proceeds |  | BASE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.refinancing_proceeds | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| acquisitions_disposals |  | BASE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.acquisitions_disposals | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| net_equity_issue_repay |  | BASE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.net_equity_issue_repay | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| dividends_paid |  | BASE | FY2025 | 2025 | -5 | CURRENCY_MM | capital.dividends_paid | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| other_investing_financing |  | BASE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.other_investing_financing | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| minimum_operating_cash |  | BASE | FY2025 | 2025 | 25 | CURRENCY_MM | liquidity.minimum_operating_cash | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| undrawn_revolver |  | BASE | FY2025 | 2025 | 100 | CURRENCY_MM | liquidity.undrawn_revolver | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| max_total_leverage |  | BASE | FY2025 | 2025 |  | MULTIPLE | covenant.max_total_leverage | UNAVAILABLE |  |  |  | COVENANT_DEFINITION_UNAVAILABLE |
| division_growth | DIVISION_1 | BASE | FY2026 | 2026 | 0.04 | PERCENT_DECIMAL | operating.revenue_growth.division_1 | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| division_growth | DIVISION_2 | BASE | FY2026 | 2026 |  | PERCENT_DECIMAL | operating.revenue_growth.division_2 | NOT_APPLICABLE |  |  |  |  |
| division_growth | DIVISION_3 | BASE | FY2026 | 2026 |  | PERCENT_DECIMAL | operating.revenue_growth.division_3 | NOT_APPLICABLE |  |  |  |  |
| consolidated_revenue_growth |  | BASE | FY2026 | 2026 |  | PERCENT_DECIMAL | operating.consolidated_revenue_growth | NOT_APPLICABLE |  |  |  |  |
| adjusted_ebitda_margin |  | BASE | FY2026 | 2026 | 0.21 | PERCENT_DECIMAL | operating.adjusted_ebitda_margin | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| identified_addbacks |  | BASE | FY2026 | 2026 | 4 | CURRENCY_MM | operating.identified_addbacks | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| capex_pct_revenue |  | BASE | FY2026 | 2026 | 0.05 | PERCENT_DECIMAL | cash_flow.capex_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| working_capital_pct_revenue |  | BASE | FY2026 | 2026 | -0.02 | PERCENT_DECIMAL | cash_flow.working_capital_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| cash_tax_pct_revenue |  | BASE | FY2026 | 2026 | -0.02 | PERCENT_DECIMAL | cash_flow.cash_tax_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| lease_cash_pct_revenue |  | BASE | FY2026 | 2026 | -0.01 | PERCENT_DECIMAL | cash_flow.lease_cash_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| base_rate |  | BASE | FY2026 | 2026 | 0.045 | PERCENT_DECIMAL | rates.base_rate | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_spread |  | BASE | FY2026 | 2026 | 0.04 | PERCENT_DECIMAL | rates.debt_spread | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| contractual_amortization |  | BASE | FY2026 | 2026 | 10 | CURRENCY_MM | capital.contractual_amortization | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_issuance |  | BASE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.debt_issuance | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_repayment |  | BASE | FY2026 | 2026 | 5 | CURRENCY_MM | capital.debt_repayment | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| refinancing_proceeds |  | BASE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.refinancing_proceeds | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| acquisitions_disposals |  | BASE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.acquisitions_disposals | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| net_equity_issue_repay |  | BASE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.net_equity_issue_repay | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| dividends_paid |  | BASE | FY2026 | 2026 | -5 | CURRENCY_MM | capital.dividends_paid | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| other_investing_financing |  | BASE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.other_investing_financing | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| minimum_operating_cash |  | BASE | FY2026 | 2026 | 25 | CURRENCY_MM | liquidity.minimum_operating_cash | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| undrawn_revolver |  | BASE | FY2026 | 2026 | 100 | CURRENCY_MM | liquidity.undrawn_revolver | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| max_total_leverage |  | BASE | FY2026 | 2026 |  | MULTIPLE | covenant.max_total_leverage | UNAVAILABLE |  |  |  | COVENANT_DEFINITION_UNAVAILABLE |
| division_growth | DIVISION_1 | BASE | FY2027 | 2027 | 0.03 | PERCENT_DECIMAL | operating.revenue_growth.division_1 | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| division_growth | DIVISION_2 | BASE | FY2027 | 2027 |  | PERCENT_DECIMAL | operating.revenue_growth.division_2 | NOT_APPLICABLE |  |  |  |  |
| division_growth | DIVISION_3 | BASE | FY2027 | 2027 |  | PERCENT_DECIMAL | operating.revenue_growth.division_3 | NOT_APPLICABLE |  |  |  |  |
| consolidated_revenue_growth |  | BASE | FY2027 | 2027 |  | PERCENT_DECIMAL | operating.consolidated_revenue_growth | NOT_APPLICABLE |  |  |  |  |
| adjusted_ebitda_margin |  | BASE | FY2027 | 2027 | 0.22 | PERCENT_DECIMAL | operating.adjusted_ebitda_margin | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| identified_addbacks |  | BASE | FY2027 | 2027 | 4 | CURRENCY_MM | operating.identified_addbacks | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| capex_pct_revenue |  | BASE | FY2027 | 2027 | 0.05 | PERCENT_DECIMAL | cash_flow.capex_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| working_capital_pct_revenue |  | BASE | FY2027 | 2027 | -0.02 | PERCENT_DECIMAL | cash_flow.working_capital_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| cash_tax_pct_revenue |  | BASE | FY2027 | 2027 | -0.02 | PERCENT_DECIMAL | cash_flow.cash_tax_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| lease_cash_pct_revenue |  | BASE | FY2027 | 2027 | -0.01 | PERCENT_DECIMAL | cash_flow.lease_cash_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| base_rate |  | BASE | FY2027 | 2027 | 0.04 | PERCENT_DECIMAL | rates.base_rate | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_spread |  | BASE | FY2027 | 2027 | 0.04 | PERCENT_DECIMAL | rates.debt_spread | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| contractual_amortization |  | BASE | FY2027 | 2027 | 10 | CURRENCY_MM | capital.contractual_amortization | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_issuance |  | BASE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.debt_issuance | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_repayment |  | BASE | FY2027 | 2027 | 5 | CURRENCY_MM | capital.debt_repayment | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| refinancing_proceeds |  | BASE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.refinancing_proceeds | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| acquisitions_disposals |  | BASE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.acquisitions_disposals | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| net_equity_issue_repay |  | BASE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.net_equity_issue_repay | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| dividends_paid |  | BASE | FY2027 | 2027 | -5 | CURRENCY_MM | capital.dividends_paid | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| other_investing_financing |  | BASE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.other_investing_financing | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| minimum_operating_cash |  | BASE | FY2027 | 2027 | 25 | CURRENCY_MM | liquidity.minimum_operating_cash | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| undrawn_revolver |  | BASE | FY2027 | 2027 | 100 | CURRENCY_MM | liquidity.undrawn_revolver | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| max_total_leverage |  | BASE | FY2027 | 2027 |  | MULTIPLE | covenant.max_total_leverage | UNAVAILABLE |  |  |  | COVENANT_DEFINITION_UNAVAILABLE |
| division_growth | DIVISION_1 | DOWNSIDE | FY2025 | 2025 | -0.05 | PERCENT_DECIMAL | operating.revenue_growth.division_1 | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| division_growth | DIVISION_2 | DOWNSIDE | FY2025 | 2025 |  | PERCENT_DECIMAL | operating.revenue_growth.division_2 | NOT_APPLICABLE |  |  |  |  |
| division_growth | DIVISION_3 | DOWNSIDE | FY2025 | 2025 |  | PERCENT_DECIMAL | operating.revenue_growth.division_3 | NOT_APPLICABLE |  |  |  |  |
| consolidated_revenue_growth |  | DOWNSIDE | FY2025 | 2025 |  | PERCENT_DECIMAL | operating.consolidated_revenue_growth | NOT_APPLICABLE |  |  |  |  |
| adjusted_ebitda_margin |  | DOWNSIDE | FY2025 | 2025 | 0.16 | PERCENT_DECIMAL | operating.adjusted_ebitda_margin | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| identified_addbacks |  | DOWNSIDE | FY2025 | 2025 | 4 | CURRENCY_MM | operating.identified_addbacks | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| capex_pct_revenue |  | DOWNSIDE | FY2025 | 2025 | 0.05 | PERCENT_DECIMAL | cash_flow.capex_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| working_capital_pct_revenue |  | DOWNSIDE | FY2025 | 2025 | -0.02 | PERCENT_DECIMAL | cash_flow.working_capital_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| cash_tax_pct_revenue |  | DOWNSIDE | FY2025 | 2025 | -0.02 | PERCENT_DECIMAL | cash_flow.cash_tax_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| lease_cash_pct_revenue |  | DOWNSIDE | FY2025 | 2025 | -0.01 | PERCENT_DECIMAL | cash_flow.lease_cash_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| base_rate |  | DOWNSIDE | FY2025 | 2025 | 0.05 | PERCENT_DECIMAL | rates.base_rate | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_spread |  | DOWNSIDE | FY2025 | 2025 | 0.04 | PERCENT_DECIMAL | rates.debt_spread | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| contractual_amortization |  | DOWNSIDE | FY2025 | 2025 | 10 | CURRENCY_MM | capital.contractual_amortization | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_issuance |  | DOWNSIDE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.debt_issuance | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_repayment |  | DOWNSIDE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.debt_repayment | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| refinancing_proceeds |  | DOWNSIDE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.refinancing_proceeds | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| acquisitions_disposals |  | DOWNSIDE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.acquisitions_disposals | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| net_equity_issue_repay |  | DOWNSIDE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.net_equity_issue_repay | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| dividends_paid |  | DOWNSIDE | FY2025 | 2025 | -2 | CURRENCY_MM | capital.dividends_paid | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| other_investing_financing |  | DOWNSIDE | FY2025 | 2025 | 0 | CURRENCY_MM | capital.other_investing_financing | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| minimum_operating_cash |  | DOWNSIDE | FY2025 | 2025 | 25 | CURRENCY_MM | liquidity.minimum_operating_cash | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| undrawn_revolver |  | DOWNSIDE | FY2025 | 2025 | 100 | CURRENCY_MM | liquidity.undrawn_revolver | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| max_total_leverage |  | DOWNSIDE | FY2025 | 2025 |  | MULTIPLE | covenant.max_total_leverage | UNAVAILABLE |  |  |  | COVENANT_DEFINITION_UNAVAILABLE |
| division_growth | DIVISION_1 | DOWNSIDE | FY2026 | 2026 | -0.03 | PERCENT_DECIMAL | operating.revenue_growth.division_1 | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| division_growth | DIVISION_2 | DOWNSIDE | FY2026 | 2026 |  | PERCENT_DECIMAL | operating.revenue_growth.division_2 | NOT_APPLICABLE |  |  |  |  |
| division_growth | DIVISION_3 | DOWNSIDE | FY2026 | 2026 |  | PERCENT_DECIMAL | operating.revenue_growth.division_3 | NOT_APPLICABLE |  |  |  |  |
| consolidated_revenue_growth |  | DOWNSIDE | FY2026 | 2026 |  | PERCENT_DECIMAL | operating.consolidated_revenue_growth | NOT_APPLICABLE |  |  |  |  |
| adjusted_ebitda_margin |  | DOWNSIDE | FY2026 | 2026 | 0.15 | PERCENT_DECIMAL | operating.adjusted_ebitda_margin | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| identified_addbacks |  | DOWNSIDE | FY2026 | 2026 | 4 | CURRENCY_MM | operating.identified_addbacks | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| capex_pct_revenue |  | DOWNSIDE | FY2026 | 2026 | 0.05 | PERCENT_DECIMAL | cash_flow.capex_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| working_capital_pct_revenue |  | DOWNSIDE | FY2026 | 2026 | -0.02 | PERCENT_DECIMAL | cash_flow.working_capital_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| cash_tax_pct_revenue |  | DOWNSIDE | FY2026 | 2026 | -0.02 | PERCENT_DECIMAL | cash_flow.cash_tax_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| lease_cash_pct_revenue |  | DOWNSIDE | FY2026 | 2026 | -0.01 | PERCENT_DECIMAL | cash_flow.lease_cash_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| base_rate |  | DOWNSIDE | FY2026 | 2026 | 0.045 | PERCENT_DECIMAL | rates.base_rate | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_spread |  | DOWNSIDE | FY2026 | 2026 | 0.04 | PERCENT_DECIMAL | rates.debt_spread | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| contractual_amortization |  | DOWNSIDE | FY2026 | 2026 | 10 | CURRENCY_MM | capital.contractual_amortization | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_issuance |  | DOWNSIDE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.debt_issuance | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_repayment |  | DOWNSIDE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.debt_repayment | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| refinancing_proceeds |  | DOWNSIDE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.refinancing_proceeds | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| acquisitions_disposals |  | DOWNSIDE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.acquisitions_disposals | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| net_equity_issue_repay |  | DOWNSIDE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.net_equity_issue_repay | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| dividends_paid |  | DOWNSIDE | FY2026 | 2026 | -2 | CURRENCY_MM | capital.dividends_paid | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| other_investing_financing |  | DOWNSIDE | FY2026 | 2026 | 0 | CURRENCY_MM | capital.other_investing_financing | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| minimum_operating_cash |  | DOWNSIDE | FY2026 | 2026 | 25 | CURRENCY_MM | liquidity.minimum_operating_cash | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| undrawn_revolver |  | DOWNSIDE | FY2026 | 2026 | 100 | CURRENCY_MM | liquidity.undrawn_revolver | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| max_total_leverage |  | DOWNSIDE | FY2026 | 2026 |  | MULTIPLE | covenant.max_total_leverage | UNAVAILABLE |  |  |  | COVENANT_DEFINITION_UNAVAILABLE |
| division_growth | DIVISION_1 | DOWNSIDE | FY2027 | 2027 | 0 | PERCENT_DECIMAL | operating.revenue_growth.division_1 | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| division_growth | DIVISION_2 | DOWNSIDE | FY2027 | 2027 |  | PERCENT_DECIMAL | operating.revenue_growth.division_2 | NOT_APPLICABLE |  |  |  |  |
| division_growth | DIVISION_3 | DOWNSIDE | FY2027 | 2027 |  | PERCENT_DECIMAL | operating.revenue_growth.division_3 | NOT_APPLICABLE |  |  |  |  |
| consolidated_revenue_growth |  | DOWNSIDE | FY2027 | 2027 |  | PERCENT_DECIMAL | operating.consolidated_revenue_growth | NOT_APPLICABLE |  |  |  |  |
| adjusted_ebitda_margin |  | DOWNSIDE | FY2027 | 2027 | 0.15 | PERCENT_DECIMAL | operating.adjusted_ebitda_margin | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| identified_addbacks |  | DOWNSIDE | FY2027 | 2027 | 4 | CURRENCY_MM | operating.identified_addbacks | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| capex_pct_revenue |  | DOWNSIDE | FY2027 | 2027 | 0.05 | PERCENT_DECIMAL | cash_flow.capex_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| working_capital_pct_revenue |  | DOWNSIDE | FY2027 | 2027 | -0.02 | PERCENT_DECIMAL | cash_flow.working_capital_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| cash_tax_pct_revenue |  | DOWNSIDE | FY2027 | 2027 | -0.02 | PERCENT_DECIMAL | cash_flow.cash_tax_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| lease_cash_pct_revenue |  | DOWNSIDE | FY2027 | 2027 | -0.01 | PERCENT_DECIMAL | cash_flow.lease_cash_pct_revenue | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| base_rate |  | DOWNSIDE | FY2027 | 2027 | 0.04 | PERCENT_DECIMAL | rates.base_rate | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_spread |  | DOWNSIDE | FY2027 | 2027 | 0.04 | PERCENT_DECIMAL | rates.debt_spread | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| contractual_amortization |  | DOWNSIDE | FY2027 | 2027 | 10 | CURRENCY_MM | capital.contractual_amortization | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_issuance |  | DOWNSIDE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.debt_issuance | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| debt_repayment |  | DOWNSIDE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.debt_repayment | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| refinancing_proceeds |  | DOWNSIDE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.refinancing_proceeds | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| acquisitions_disposals |  | DOWNSIDE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.acquisitions_disposals | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| net_equity_issue_repay |  | DOWNSIDE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.net_equity_issue_repay | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| dividends_paid |  | DOWNSIDE | FY2027 | 2027 | -2 | CURRENCY_MM | capital.dividends_paid | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| other_investing_financing |  | DOWNSIDE | FY2027 | 2027 | 0 | CURRENCY_MM | capital.other_investing_financing | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| minimum_operating_cash |  | DOWNSIDE | FY2027 | 2027 | 25 | CURRENCY_MM | liquidity.minimum_operating_cash | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| undrawn_revolver |  | DOWNSIDE | FY2027 | 2027 | 100 | CURRENCY_MM | liquidity.undrawn_revolver | READY | SRC-1 | Annual report 2024 p. 42 | 2025-02-15 |  |
| max_total_leverage |  | DOWNSIDE | FY2027 | 2027 |  | MULTIPLE | covenant.max_total_leverage | UNAVAILABLE |  |  |  | COVENANT_DEFINITION_UNAVAILABLE |

## Evidence Trace

| source_id | block_id | source_digest | locator | extractor_version | confidence |
|---|---|---|---|---|---|
| SRC-1 | block-1 | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb | Annual report 2024 p. 42 | builtin-v1 | HIGH |

## Source Registry

| source_id | source_digest | origin_family | authority_class |
|---|---|---|---|
| SRC-1 | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb | primary |

## Gaps & Conflicts

Covenant headroom remains unavailable because no covenant definition has been accepted; CP-MODEL returns the named covenant gap and null output.

## QA Validation

Canonical identity, provenance, registry completeness, stable table coverage, scenario coverage, and explicit gaps are validated.
