# REF_CP-SR_E | Early Warning Dashboard — Indicator Definitions & RAG Logic
# Version: 2.0 | 2026-06-10 | Generalized: core cross-sector indicators + sector overlay slots (telecom values moved to overlay example)

## STRUCTURE
The dashboard combines two indicator sets, both emitted in the `early_warning_dashboard` array with Red/Amber/Green status per the CP-SR payload schema:
1. **Core indicators (EW-01 … EW-08)** — cross-sector, always populated where data exists.
2. **Sector overlay indicators (EW-S1 … EW-S4)** — 2–4 sector-specific operating indicators defined at review setup per the Overlay Rules below.

## CORE INDICATORS (cross-sector)
| ID | Indicator | Metric Definition | Green | Amber | Red | Source | Refresh |
|---|---|---|---|---|---|---|---|
| EW-01 | Sector Default Rate (TTM) | Trailing 12-month HY bond default rate | <2.0% | 2.0–4.0% | >4.0% | Fitch/Moody's/S&P | Monthly |
| EW-02 | Leveraged Loan Default Rate (TTM) | Trailing 12-month LL default rate | <1.5% | 1.5–3.0% | >3.0% | Fitch/S&P | Monthly |
| EW-03 | Market Concern List Share | % of sector issuers on concern list | <5% | 5–10% | >10% | Fitch / internal | Monthly |
| EW-04 | Net Rating Drift | Net upgrades minus downgrades / rated universe | >0% | -5% to 0% | <-5% | Rating agencies | Quarterly |
| EW-05 | Sector Spread vs Broad HY | Sector OAS less broad HY OAS (state index) | <-25bps | -25 to +50bps | >+50bps | Market data | Weekly |
| EW-06 | Aggregate Leverage Trend | YoY change in median net debt/EBITDA | <-0.2x | -0.2x to +0.2x | >+0.2x | Filings | Quarterly |
| EW-07 | Capex Intensity Trend | YoY change in median capex/revenue | Declining | Stable | Rising | Filings | Quarterly |
| EW-08 | Refinancing Wall Concentration | % sector debt maturing in 24 months | <15% | 15–25% | >25% | Filings / trustee | Semi-annual |

## SECTOR OVERLAY RULES
- Select 2–4 operating indicators that capture the sector's **first-break variables** — the earliest operating metrics to deteriorate under stress. Use REF_CP-2B_FragilityDriverTaxonomy.md (Revenue and Margin fragility groups) as the candidate vocabulary and REF_CP-2B_MonitoringIndicatorLibrary.md leading-indicator list for calibration.
- Each overlay indicator must state: metric definition, Green/Amber/Red thresholds, source, refresh cadence, and **leading or lagging** classification.
- Thresholds must be source-supported (historical sector data, rating-agency studies, or documented internal framework). If no supported threshold exists, classify by direction only and state: "Quantitative threshold not available in provided materials."
- Carry overlay definitions forward between review cycles for comparability; log any indicator change and its reason in the review's version note.

### Overlay example — European Telecom
| ID | Indicator | Metric Definition | Green | Amber | Red | Source | Refresh | Lead/Lag |
|---|---|---|---|---|---|---|---|---|
| EW-S1 | ARPU Trend | YoY change in blended ARPU | >+1% | -1% to +1% | <-1% | Filings | Quarterly | Leading |
| EW-S2 | Subscriber Churn | Broadband / mobile net adds | Positive | Flat | Negative | Filings | Quarterly | Leading |

## TREND CLASSIFICATION
| Direction | Definition |
|---|---|
| Improving | Current value better than prior period and moving toward Green |
| Stable | No material change from prior period |
| Deteriorating | Current value worse than prior period and moving toward Red |

## EVIDENCE DISCIPLINE
- Every indicator value carries source and as-of date. Do not infer or extrapolate missing values — mark `N/A — [reason]` and log in the gaps section.
- A Red status must state the risk mechanic and credit implication (per REF_CP-SR_F canonical values) and route a trigger signal to CP-MON.
