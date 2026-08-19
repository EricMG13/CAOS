<!-- CP-X Schema Reference (T3) | 2026-06-03 -->

## Required Output Sections (7)
All 7 sections must be present using exact required headings.

## Required Tables (5)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| TX.2 | Module Execution Sequence | Order, Module ID, Module Name, Layer, Readiness, Depends On |
| TX.3 | Module Readiness Register | Module ID, Module Name, Readiness Status, Source Dependencies Met, Limitation Flags, Blocking Reason |
| TX.4 | One-Owner-Per-Object Validation | owned_object, Owning Module, Conflict Detected, Resolution |
| TX.5 | Source-to-Module Routing Map | Source Document, Source Quality, Modules Supported, Limitation |
| TX.6 | Limitation Propagation Register | Limitation, Source, Affected Modules, Impact, Propagated Flag |

## Structured Sections (2)
| Step | Section | Format |
|------|---------|--------|
| 1 | Route Plan Source Gate | Gate status (Full Run / Ready with Limitations / Blocked) + CP-0 completeness assessment |
| 7 | Route Plan Summary | Required formulation: "Route plan includes [N] modules for execution ([M] Full Run, [K] Ready with Limitations, [J] Blocked)..." |

## QA Checklist
- [ ] CP-0 output received and validated
- [ ] All modules assessed for readiness (none omitted)
- [ ] Execution sequence is dependency-ordered (layer precedence enforced)
- [ ] One-owner-per-object validated for all modules in execution plan
- [ ] Source-to-module routing complete (every CP-0 source mapped)
- [ ] All CP-0 limitations propagated to affected downstream modules
- [ ] No M-prefix references in any output
- [ ] All appendix JSON blocks present in export
- [ ] Blocked modules listed with specific blocking reasons
- [ ] Ready with Limitations modules have specific limitation flags
- [ ] No modules added without CP-0 readiness evidence
- [ ] No modules skipped that CP-0 marks as Ready or Ready with Limitations

## Export: [Issuer]_CP-X_[YYYYMMDD].docx
