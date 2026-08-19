# REF_CP-SR_D | Comparative Table — Fixed Column Schema
# Version: 2.0 | 2026-06-10 | Sub-segment generalized; peer-statistics discipline added (from CP-1C standard)

## TABLE SCHEMA
| Column | Type | Source | Required |
|---|---|---|---|
| Issuer | string | Universe list | Yes |
| Sub-Segment | enum, sector-specific taxonomy fixed at review setup (e.g., telecom: Incumbent/Cable/TowerCo/AltNet/FibreCo/MVNO) | Analyst | Yes |
| Country | string | Analyst | Yes |
| Agency Rating (M/S/F) | string | Rating agencies | Yes |
| Rating Outlook | enum Pos/Sta/Neg/Watch | Rating agencies | Yes |
| Net Leverage (LTM) | float, x | Filings / estimates | Yes |
| EBITDA Margin (LTM) | float, % | Filings | Yes |
| FCF/Debt (LTM) | float, % | Filings / estimates | Preferred |
| Capex/Revenue (LTM) | float, % | Filings | Preferred |
| Revenue Growth (YoY) | float, % | Filings | Preferred |
| Spread (z-spread or OAS) | bps | Market data | Conditional |
| Maturity Wall (next 3yr) | string, currency amount | Filings / trustee | Preferred |
| Recovery Tier | enum RR1-RR6 | Internal model / agencies | Conditional |
| Sector Risk Score | int 1-5 | CP-SR derived | Derived |
| Data As-Of | date | Multiple | Yes |

## NOTES
- Minimum 5 issuers required for meaningful comparison unless the sector universe is smaller.
- Data gaps must be flagged per cell as `N/A — [reason]`.
- Spread data is conditional on market data availability.
- Recovery tier is conditional on internal model or agency recovery analysis.
- Do not infer missing ratings, spreads, leverage, or recovery values.

## PEER-STATISTICS DISCIPLINE (inherited from CP-1C standard)
- Do not calculate average, median, or quartile statistics without sufficient comparable datapoints: minimum 3 for median, 4 for quartile, 5 for meaningful average. Fewer than 2 → show individual observations only.
- Exclude non-comparable issuers from statistic calculations (different metric definitions, perimeters, accounting standards, or stale data without disclosure).
- Always state N (number of issuers) for each statistic.
- If an outlier materially distorts the average, show the median alongside and flag the outlier impact; where an outlier results from a comparability limitation, classify it Non-Comparable rather than treating it as a credit signal.
- Mixed financial bases (IFRS/GAAP, FYE, currency, perimeter) must be flagged per row.
