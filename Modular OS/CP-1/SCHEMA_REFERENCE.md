<!-- CP-1 Schema Reference (Tier 3) | 2026-06-02 -->
<schema_reference module="CP-1" tier="3">
## Required Tables (13)
| ID | Name | Key Columns |
|----|------|-------------|
| T4.1 | Source Register | File Name, Doc Type, Period, Currency, Unit, Perimeter, Basis, Tier, Use, Limits |
| T4.2 | Entity Period Key | Entity, Role, FY End, Currency, Unit, Perimeter, Basis, Periods |
| T4.3 | Normalization Reg | Description, Source, Type, Before, After, Rationale, Periods |
| T4.4 | Income Statement | Line Item, Period 1…N |
| T4.5 | Cash Flow Statement | Line Item, Period 1…N |
| T4.6 | Balance Sheet | Line Item, Period 1…N |
| T4.7 | Normalized Financials | Line Item, Statement Source, Period 1…N |
| T4.8 | Constructed Period Reg | Metric, Type, FY/Stubs, Value, Status, Sources, Limits |
| T4.9 | Calculation Register | Metric, Formula, Num/Den+Source, Period, Value, Status, Tier, Limits |
| T4.10 | KPI Dashboard | Category, Metric, Periods, Trend, Analyst Note |
| T4.11 | Def Conflict Reg | Metric, Canonical, Issuer, Source, Periods, Materiality, Downstream, Resolution |
| T4.12 | Gaps & Warnings | Description, Item, Periods, Downstream, Severity, Action |
| T4.13 | Downstream Readiness | Module, Status, Gaps, Actions |

## 17-Section Output
1. Source Register  2. Entity Period Key  3. FS Coverage  4. Normalized IS
5. Normalized BS  6. Normalized CFS  7. Normalization Register  8. Calculation Register
9. Constructed Period Register  10. KPI Dashboard  11. Definition Conflict Register
12. Gaps & Warnings  13. Downstream Readiness  14. Evidence Trace  15. QA Status
16. Limitation Flags  17. Module Handoff

## Canonical Extraction Types (13)
sourced_fact | quoted_text | table_value | calculated_metric | analyst_inference |
upstream_artifact | user_instruction | documentary_fact | definition_conflict |
gap | source_limitation | insufficient_information | not_available

## QA Checklist (11)
- [ ] Sources classified with quality labels + tiers
- [ ] All tables present or [Insufficient Information]
- [ ] Calculations have audit trail in T4.9
- [ ] Four-category separation discipline maintained
- [ ] No M-prefix references
- [ ] Appendix JSON blocks A–E present
- [ ] No silent reconciliation — conflicts in T4.11
- [ ] All gaps in T4.12 + inline
- [ ] Null storage rule applied
- [ ] Def Conflict Register populated or alignment confirmed
- [ ] Downstream Readiness covers all 13 consumers

## Export: [Issuer]_CP-1_[YYYYMMDD].docx per CP-COMMON export contract
</schema_reference>
