<!-- CP-4D Schema Reference (T3) | PROPOSED | 2026-06-22 -->

## Required Output Sections (9)
All 9 sections must be present. If source materials do not support analysis, the section must still appear with [Insufficient Information] and a gap ledger entry.

## Required Tables (8)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T4D.1 | Source Gate Register | Source, Status, Authority Rank, Limitations, Module Status |
| T4D.2 | Restricted / Unrestricted Entity Register | Entity, Role, Jurisdiction, Parent, Designation, Material Value Held, Inside Credit Group?, Evidence ID |
| T4D.3 | Guarantor Coverage Matrix | Entity × Tranche, Guarantee Type, Direction, Release Trigger, Evidence ID |
| T4D.4 | Collateral-by-Entity Matrix | Entity × Lien, Excluded Assets, Release Mechanic, Perfection Limit, Evidence ID |
| T4D.5 | Structural Priority Table | Claim/Tranche, Obligor Entity, Reachable Value, Structural-Priority Label, Stranded Value Named, Recovery-Access Implication, Confidence, Evidence ID |
| T4D.6 | Drop-down / Transfer Capacity Register | Route, Entity Path, Enabling Provision (CP-4 ref), Value Exposed, Severity 1–5, Recovery/Priority Implication, Demonstrated vs Theoretical, Evidence ID |
| T4D.7 | Priming-Exposure Findings | Vulnerability, Enabling Provision (CP-4 ref), Affected Creditor Class, Demonstrated vs Theoretical, Structural Implication, Confidence, Evidence ID |
| T4D.8 | Gaps Ledger | Gap, Missing Document/Schedule/Provision, Why It Matters, Impact on Output, Required Follow-Up |

## Narrative Section (Step 9 — Overall Structural View)
Synthesis weighted to the worst open route + handoff register naming the artifact passed to CP-3B, CP-6A, and CP-4C.

## QA Checklist
- [ ] All 9 output sections present and populated (or [Insufficient Information] with gap logged)
- [ ] Every structural-subordination finding names the entity gap AND the stranded value
- [ ] Every claim ranked by reachable value at its obligor entity, not stated lien alone
- [ ] Every leakage route cites a CP-4 enabling provision (or is marked [Insufficient Information])
- [ ] Leakage-route severity uses only the canonical 1–5 / Not Scorable scale
- [ ] Demonstrated capacity separated from theoretical capacity
- [ ] No dollar recoveries / LGD percentages (handed to CP-3B)
- [ ] No covenant aggressiveness scoring (owned by CP-4)
- [ ] Structural-priority labels drawn only from the 7 canonical CP-4D values
- [ ] Source gate status documented (Completed / Completed with Limitations / Blocked)
- [ ] All gaps logged with affected downstream modules
- [ ] Numeric Confidence Score (0–100) computed per `CP_CONFIDENCE_SCORE.md` and shown with its band in the Audit Summary
- [ ] Both artifacts produced — (A) `.docx` report and (B) `.md` handoff — identical content; single Audit Appendix at the end of (A); canonical YAML envelope + H2 headings in (B)

## Export
Per `CP_AB_EXPORT_SPEC.md`, two artifacts per run, identical content:
- **(A) REPORT** — `[Issuer]_CP-4D_[YYYYMMDD].docx` — Header → Audit Summary + numeric Confidence Score (0–100) → 9-section analysis narrative (= chat) → single Audit Appendix.
- **(B) HANDOFF** — `[Issuer]_CP-4D_[YYYYMMDD].md` — YAML envelope (`confidence_score` + `confidence_band`) + canonical H2 headings (`## Audit Summary`, `## Analysis`, `## Evidence Trace`, `## Source Registry`, `## Gaps & Conflicts`, `## QA Validation`); saved to OneDrive as the agent handoff.
