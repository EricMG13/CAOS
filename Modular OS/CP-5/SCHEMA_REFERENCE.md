<!-- CP-5 Schema Reference (T3) | 2026-06-03 -->

## Required Output Sections (11)
All 11 sections must be present using exact required headings.

## Required Tables (9)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T5.1 | Input Module Register | Module, Document / Output, Scope, Source Quality, Appendix Status, QA Status, Notes |
| T5.2 | Citation and Evidence Support Audit | Severity, Module, Claim / Section, Evidence Status, Issue, Required Fix, Clearance Impact |
| T5.3 | Math / Logic / Definition Audit | Severity, Module, Metric / Logic Issue, Formula / Definition Issue, Source Conflict, Required Fix, Clearance Impact |
| T5.4 | Legal / Structural Claim Audit | Severity, Module, Legal / Structural Claim, Required Legal Source, Evidence Gap, Required Fix, Legal Review Dependency |
| T5.5 | Relative Value / Market Claim Audit | Severity, Module, Market / RV Claim, Missing Datapoint, Evidence Gap, Required Fix, Committee Impact |
| T5.6 | Cross-Module Consistency and Version-Control Audit | Severity, Affected Modules, Data / Claim Conflict, Version Issue, Required Fix, Downstream Impact |
| T5.7 | Duplication / Materiality / Committee-Readiness Audit | Severity, Module, Issue Type, Description, Required Fix, Committee Impact |
| T5.8 | Structured Export Audit | Severity, Module, Export Component, Defect, Required Fix, CP-DB / Database Impact |
| T5.9 | Issue Log | Issue ID, Severity, Module, Issue Type, Description, Required Fix, Clearance Impact, Status |

## Narrative Sections (2)
| Step | Section | Format |
|------|---------|--------|
| 10 | Remediation Priority Map | 4 prioritized groups: must-fix before committee, must-fix before CP-DB, monitoring follow-up, formatting/hygiene |
| 11 | Clearance Decision | Required format: "CLEARANCE DECISION: [Pass / Pass with Remediation / Fail]. Critical Issues: [N]. Material Issues: [N]. Minor Issues: [N]. Committee Use: [Approved / Restricted / Blocked]." |

## QA Checklist
- [ ] All 11 output sections present using exact required headings
- [ ] All severity values use ONLY: CRITICAL / MATERIAL / MINOR (no other scale)
- [ ] All evidence classifications use ONLY: Supported / Partially Supported / Unsupported / Conflicting / Insufficient Information
- [ ] All defect categories use ONLY the 23 permitted values
- [ ] All clearance impact labels use ONLY the 9 permitted values
- [ ] Every Issue Log entry has sequential Issue ID (CP5-NNN format)
- [ ] Every finding states: what is wrong, why it matters, what fix is required, whether output can be used before correction
- [ ] Severity Escalation Rules applied correctly (Critical/Material/Minor triggers verified)
- [ ] Remediation Priority Map groups all issues into exactly 4 tiers
- [ ] Clearance Decision uses exact required format
- [ ] Clearance Decision is consistent with Severity Engine (Critical → Fail/Blocked, Material → Pass with Remediation/Restricted, Minor → Pass/Approved)
- [ ] No silent rewriting of underlying module analysis
- [ ] All appendix JSON blocks present
- [ ] Exact source filenames quoted when making QA findings (NATIVE CITATIONS)
- [ ] Required headings match FINAL_OUTPUT_STRUCTURE exactly

## Export: [Issuer]_CP-5_[YYYYMMDD].docx
