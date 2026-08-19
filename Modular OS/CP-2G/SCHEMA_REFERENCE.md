<!-- CP-2G Schema Reference (T3) | PROPOSED | 2026-06-22 -->

## Required Output Sections (8)
All 8 sections must be present. Where ESG is immaterial or disclosure is missing, the section still appears — stating "Immaterial to Credit" or [Insufficient Information] with a gap ledger entry.

## Required Tables (8)
| ID | Table Name | Key Columns |
|----|-----------|-------------|
| T2G.1 | Source Register | Source, Reliability (audited/assured vs self-reported), Greenwashing Flag, Module Status |
| T2G.2 | Transition Risk Register | Exposure, Source/Date, Transmission Mechanic, Affected Driver, Evidence ID |
| T2G.3 | Social Event-Risk Register | Exposure, Source/Date, Transmission Mechanic, Event-Risk vs Ongoing, Evidence ID |
| T2G.4 | Materiality Table | Factor, Materiality Class, Transmission Basis, Catalyst (if Watch), Evidence ID |
| T2G.5 | KPI / SPT / Ratchet Table | Instrument, KPI, SPT + Test Date, Ratchet (direction, bps), Symmetry, Credit-Meaningful?, Expected Spread Effect, Evidence ID |
| T2G.6 | Demand / Access Implications | Effect, Direction, Quantified vs Directional, Linked Maturity/Funding Need, Evidence ID |
| T2G.7 | ESG Credit Implication Table | Material Factor, Risk Mechanic, Credit Implication, Confidence, Evidence ID |
| T2G.8 | Gaps Ledger | Gap, Missing Item, Why It Matters, Impact on Output, Required Follow-Up |

## QA Checklist
- [ ] All 8 output sections present and populated (or "Immaterial to Credit" / [Insufficient Information] with gap logged)
- [ ] No ESG values judgement, ethics score, or non-credit ESG rating
- [ ] Every factor classified for materiality before any implication; default Immaterial unless transmission shown
- [ ] Materiality classes drawn only from the 5 canonical values
- [ ] No materiality inferred from sector reputation alone
- [ ] Sustainability-linked terms captured with ratchet size and credit-meaningful vs cosmetic judgement
- [ ] Green/sustainability labels not treated as protection without enforceable provision
- [ ] Governance/sponsor conduct referenced to CP-2D, not duplicated
- [ ] Every material credit implication completes Evidence → Risk Mechanic → Credit Implication
- [ ] Source/Module status documented (Completed / Completed with Limitations / Not Applicable / Blocked)
- [ ] Both artifacts produced — (A) `.docx` report and (B) `.md` handoff — with identical content (per `CP_AB_EXPORT_SPEC.md`)
- [ ] Numeric `confidence_score` (0–100) emitted as the primary measure with its derived `confidence_band` (per `CP_CONFIDENCE_SCORE.md`)
- [ ] (B) carries the YAML envelope and canonical H2 headings; single Audit Appendix holds all audit items

## Export
Per `CP_AB_EXPORT_SPEC.md`, the module self-authors two artifacts per run, identical content:
- **(A) REPORT** — `[Issuer]_CP-2G_[YYYYMMDD].docx` (Header → Audit Summary + numeric Confidence Score → 8-section analysis narrative [CHAT = REPORT] → single Audit Appendix).
- **(B) HANDOFF** — `[Issuer]_CP-2G_[YYYYMMDD].md` (YAML envelope incl. `confidence_score` + `confidence_band` + canonical H2 headings), saved to OneDrive and attached as grounding to the next agent.
