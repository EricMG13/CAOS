# Exhaustive fault and persona register

This register consolidates every fault identified by the current-source,
1440×900/390×844 render, detector, performance, accessibility, copy/honesty,
and dual-agent critique passes. **P1** materially risks a primary task, wrong
read, accessibility, or trust; **P2** creates repeated friction or inconsistency;
**P3** is localized polish/debt. No P0 was established in this design-only pass.

## Shared-system faults

| ID | Pri | Fault | Evidence | Persona / goal impact |
|---|---:|---|---|---|
| F-001 | P1 | Role composition is mostly inert. `dominantRepresentation`, `summaryDensity`, and `tableColumnPreset` are declared but only emitted as data attributes; runtime behavior mainly changes context/inspector open defaults. | `caos/frontend/src/lib/persona-composition.ts:55-95`; `caos/frontend/src/components/shared/PersonaWorkbench.tsx:51-55,201-206` | PMs do not get posture-first summaries; QA does not get gate-first governance; the Analyst/PM/QA switch overpromises. |
| F-002 | P1 | The role switch explicitly promises PM “posture / what changed first” and QA “governance / gates first,” so F-001 is a visible contract breach rather than hidden technical debt. | `caos/frontend/src/components/shared/RoleViewSwitch.tsx:11-15,26-59` | Damages trust and makes the personas appear cosmetic. |
| F-003 | P1 | Fifteen destinations are given near-equal global prominence. Default keyboard order reaches 20 shared controls before route-specific work. | `caos/frontend/src/lib/nav.ts:13-60`; `caos/frontend/src/components/shared/WorkflowRail.tsx:18-75` | Frequent analysts and PMs pay a repeated navigation tax; occasional users cannot infer priority. |
| F-004 | P1 | Compact navigation hides most inactive labels and leans on icon/tooltip recognition. | `caos/frontend/src/components/shared/ConceptNav.tsx:190-260`; `caos/frontend/src/app/globals.css:188-213` | Touch and keyboard users lose recognition; new analysts must memorize the ontology. |
| F-005 | P1 | Screen identity is commonly 12 px—the body tier—despite the design register specifying a 16 px title. Narrow identities are deliberately truncated. | `caos/frontend/src/components/shared/ShellIdentity.tsx:47-50`; `DESIGN.md:52-58`; `caos/frontend/src/components/shared/SubHeader.tsx:164-167` | Issuer/run/surface orientation is too weak for multi-window desk work. |
| F-006 | P1 | Typography is over-compressed: panel headers are 11 px, toolbar titles 13 px, and the codebase contains 373 uppercase/tracked label usages. | `caos/frontend/src/components/shared/Panel.tsx:39-55`; `caos/frontend/src/components/shared/WorkbenchToolbar.tsx:48-54`; source count in `01-evidence.md` | Hierarchy relies on casing/spacing rather than size/weight; scan fatigue rises. |
| F-007 | P1 | Report appendix text is 5.3–7 px and paper body/table labels are often 8–9.5 px in the on-screen preview. | `caos/frontend/src/app/globals.css:626-674` | Analysts cannot reliably proof numbers/citations at normal zoom; low-vision users are excluded from the core deliverable. |
| F-008 | P1 | `RouteHeading` omits Portfolios and Decisions, producing an sr-only h1 “CAOS”; Portfolio then adds a separate visible h1. | `caos/frontend/src/components/shared/RouteHeading.tsx:9-29`; `caos/frontend/src/components/portfolio/PortfolioLabWorkbench.tsx:534` | Screen-reader orientation is wrong; Portfolio can expose two h1s while IC Book has a non-specific h1. |
| F-009 | P1 | Ask reserves a fixed 380 px reader inside a phone-width dialog and renders a nested `<main>` inside the application's main landmark. | `caos/frontend/src/components/shared/Ask.tsx:770-830`; `caos/frontend/src/app/layout.tsx:53-59` | Results can collapse at 390 px; landmark navigation becomes ambiguous. |
| F-010 | P1 | Desktop axe finds one serious `scrollable-region-focusable` failure in Report Studio. | Rendered axe; target matches `caos/frontend/src/components/shared/Panel.tsx:5-20,59-84` | Keyboard users can miss a scrollable report region. |
| F-011 | P1 | Normal critical text on the elevated surface is 4.29:1, below the 4.5:1 AA floor. | Token math from `DESIGN.md:5-37` | Critical caveats can be less legible precisely where risk should be most visible. |
| F-012 | P1 | “Responsive” often means the component owns lateral scroll. Report, Pipeline, Model, Issuers, Profile tabs, and Sector tabs preserve capability but not task usability at 390 px. | `/tmp/caos-a11y-narrow/*-390x844.png`; `caos/frontend/src/app/globals.css:1186-1252` | A phone reviewer sees clipped artifacts and must discover horizontal movement; authoring/review contracts are undefined. |
| F-013 | P1 | Primary-action semantics are not consistent: Model has two header actions despite a one-primary contract; Sector has no page-level primary; Report's default native-disabled action leaves the tab order. | `caos/frontend/src/components/shared/SubHeader.tsx:121-126`; `caos/frontend/src/app/model/page.tsx:866-878`; `caos/frontend/src/components/sector/SectorReviewDossier.tsx:424-445`; `caos/frontend/src/app/reports/page.tsx:864-877` | Action priority is less predictable across concepts; keyboard users receive a different primary-action model. |
| F-014 | P2 | Success/closure is route-specific (`ready`, `ratified`, `published`, `affirmed`) and absent from the shared state union. | `caos/frontend/src/components/shared/SurfaceState.tsx:6-40` | Analysts, PMs, and QA lack one stable “safely complete” grammar. |
| F-015 | P2 | Nineteen excess same-purpose affordances repeat evidence openers or actions. | Deep-Dive `OutputRegister.tsx:212-367`, `tabs.tsx:112-487`; Report `ReportDoc.tsx:273-300`, `panels.tsx:114-128`; IC Book `ICBookWorkbench.tsx:641,1094-1099`; Research `page.tsx:224-240,426-432,535-546` | Adds tab stops and makes “one interaction from evidence” feel like duplicated chrome rather than a clear path. |
| F-016 | P2 | Multiple static choice bands exceed four options: 15 global destinations, five/six Ask starters, seven Deep-Dive layers, six profile/sector tabs, five upload modes, five report zoom values, and an 11-control IC form. | `caos/frontend/src/lib/nav.ts:13-60`; `Ask.tsx:83-145`; route citations in `01-evidence.md` | Recognition degrades into search/memory; PM quick-scan and new-user orientation suffer. |
| F-017 | P2 | Many empty states are placed inside full-height, mostly blank canvases. The copy is good, but the density-with-hierarchy promise collapses into sparse framing. | Current desktop captures for Issuers, Research, Sector, RV, Sponsors, IC Book, Portfolio, Command | The terminal feels unfinished during common cold-start/no-data states. |
| F-018 | P2 | 64 literal colors are referenced in `globals.css`, exceeding the perceived palette and making paper/alpha/special cases harder to govern. | Static color inventory; `caos/frontend/src/app/globals.css` | Design-system drift and contrast regressions become harder to detect. |
| F-019 | P2 | Product chrome exposes implementation-policy copy—“COMPOSITION ONLY · PERMISSIONS UNCHANGED”—on Query, Sector, and RV. | `QueryInvestigationWorkbench.tsx:914-929`; `SectorReviewDossier.tsx:424-445`; `RVScreenerWorkbench.tsx:442-451` | Adds no decision value and makes the interface sound like an internal acceptance test. |
| F-020 | P3 | The persistent Ask dock reserves about 52 px on every authenticated route. The harness found no collision, but it reduces scarce vertical workbench space and remains visually dominant at the lower-right edge. | `caos/frontend/src/app/globals.css:134-147`; all current captures | Most costly on 390×844 Report/Model/Pipeline and finalization surfaces. |

## Route and concept faults

### Entry and Intake

| ID | Pri | Surface | Fault and concept-goal mismatch | Evidence |
|---|---:|---|---|---|
| F-021 | P2 | `/` | Role-aware redirect is useful, but because the role setting is composition-light (F-001), the landing distinction overstates how different the resulting workspaces are. | `caos/frontend/src/app/page.tsx:11-27`; F-001 |
| F-022 | P2 | Issuer Directory | The desktop table is four rows inside a nearly full-height empty register; on phone, Rating and later columns are offscreen with no strong visible “more columns” cue. | Current `issuers-1440x900.png` and `issuers-390x844.png` |
| F-023 | P2 | Issuer Directory | Blank square image/placeholders consume the first column and read like missing assets rather than useful credit identity. Search copy also truncates on phone. | Same captures; `caos/frontend/src/app/issuers/page.tsx:433-514` |
| F-024 | P1 | Issuer Directory | New Issuer says creation “opens its module route,” but success opens the issuer profile overlay. | `caos/frontend/src/app/issuers/page.tsx:204-209,669-675,728-730` |
| F-025 | P1 | Issuer Profile | When no completed run exists, dominant cards still show large 2.3×/8.5×/$1.9bn demo values while repeating “Source unavailable.” “DEMO SEED” is honest but insufficiently separates illustrative numbers from a real issuer. | `caos/frontend/src/app/issuers/profile/ProfileContent.tsx:702-814`; current profile captures |
| F-026 | P2 | Issuer Profile | Six tabs clip later destinations on phone; the fixed bottom action band also truncates its labels. | `ProfileContent.tsx:47-55`; current profile 390 px capture |
| F-027 | P2 | Issuer Profile | “LIVE” denotes persisted-run origin rather than necessarily-current data; freshness is separate, so the word can be misread as current. | `ProfileContent.tsx:636-670` |
| F-028 | P1 | Upload | “MNPI · restricted handling enforced” is an unqualified compliance/security assurance with no visible control evidence or policy link. | `caos/frontend/src/app/upload/page.tsx:13,25` |
| F-029 | P1 | Upload | The result headline is always “Intake complete · CP-0 ready” after processing, even when every file failed and zero documents were vaulted. | `UploadWizard.tsx:423-426`; `steps.tsx:450-461,571-574` |
| F-030 | P2 | Upload | Analyst-selected LIVE/REFERENCE/DEMO and REPORTED/DERIVED/MODELLED provenance is described as flowing downstream without clearly labeling it “declared by analyst” rather than system-validated. | `caos/frontend/src/components/upload/steps.tsx:293-308` |
| F-031 | P3 | Upload | The header “Jump to intake form” points to the already-visible primary wizard on common desktop/phone states. | `caos/frontend/src/app/upload/page.tsx:34-46`; current captures |

### Analyze

| ID | Pri | Surface | Fault and concept-goal mismatch | Evidence |
|---|---:|---|---|---|
| F-032 | P2 | Research | The run action is duplicated in the header and brief panel; the empty report uses most of the canvas. | `caos/frontend/src/app/research/page.tsx:224-240,426-432,535-546`; current desktop capture |
| F-033 | P2 | Research | Demo configuration is honest, but “Run example research” becomes the primary concept action, so the surface demonstrates rather than performs institutional research until a key exists. | `caos/frontend/src/app/research/page.tsx:227-232,453-459` |
| F-034 | P2 | Query | Metric / Graph / Grounded “lanes,” Capability, and Downstream Consumers expose internal ontology with insufficient plain-language task framing. | `QueryInvestigationWorkbench.tsx:744-794,873-879` |
| F-035 | P2 | Query | “COMPOSITION ONLY · PERMISSIONS UNCHANGED” takes premium status-bar space and distracts from question, lane, and history. | `QueryInvestigationWorkbench.tsx:914-929`; current desktop capture |
| F-036 | P2 | Sector Review | No page-level primary action exists; “Request refresh” is relegated to the finalization bar while a large empty dossier dominates. | `SectorReviewDossier.tsx:424-445`; current desktop/phone captures |
| F-037 | P2 | Sector Review | Six dossier tabs plus a sector rail and evidence inspector overload the cold-start state; “ALERTS ON” reads ambiguously as state, toggle, or coverage fact. | `SectorReviewPanels.tsx:12-21`; current desktop capture |
| F-038 | P1 | Sector Review | On phone the tab band clips after the early tabs and the bottom finalization/action bar competes with the persistent Ask dock. The harness avoids collision but the available work viewport is small. | Current `sector-390x844.png`; `globals.css:134-147` |
| F-039 | P2 | RV Screener | The cold-start layout reserves large empty table, classification visualization, and inspector regions for a single “run the screen” instruction. | Current `sector-rv-1440x900.png` |
| F-040 | P1 | RV Screener | “Monitor threshold” only pins an analysis finding; it does not configure a monitor threshold. | `RVScreenerWorkbench.tsx:206-217,283,405-411` |
| F-041 | P2 | RV Screener | Table/Distribution/Compare plus dense DM/bp/cohort terminology relies on specialist inference; candidate actions exceed the compact choice band. | `RVScreenerWorkbench.tsx:347-363,405-414` |
| F-042 | P2 | Sponsors | The empty list and empty track-record panels repeat nearly the same setup instruction and leave most of the canvas blank. | `caos/frontend/src/app/sponsors/page.tsx:191-275`; current captures |
| F-043 | P2 | Sponsors | The disabled “Review selected sponsor” occupies the header before there is a sponsor, while the reason is a tiny secondary line. | `caos/frontend/src/app/sponsors/page.tsx:167-171,264-272`; current captures |

### Decide

| ID | Pri | Surface | Fault and concept-goal mismatch | Evidence |
|---|---:|---|---|---|
| F-044 | P1 | Command | PM/CIO “what changed in ten seconds” is not materially recomposed by the PM role; the same decision, main dataset, digest, governance, and cited-brief structure remains. | F-001/F-002; `caos/frontend/src/app/command/page.tsx:350-452` |
| F-045 | P2 | Command | In the observed-empty state, the four-cell Decision Brief, empty live-coverage canvas, Daily Digest, Governance Summary, and Cited Brief compete despite having no live runs. | Current `command-1440x900.png` |
| F-046 | P2 | Command | “Open top change” remains the primary header action while there is no top change; `ActionReason` keeps it focusable, but the visual hierarchy still advertises an unavailable action. | `caos/frontend/src/app/command/page.tsx:350-359`; current captures |
| F-047 | P1 | Portfolio Lab | The primary “Run portfolio stress” only opens a preview; the actual run is later “Confirm and persist,” while another control is correctly named “Preview stress.” | `PortfolioLabWorkbench.tsx:679-705,713-722` |
| F-048 | P1 | Portfolio Lab | At 1440 px the filter band hides part of Sort behind the adjacent View panel; on phone a matrix of empty/disabled controls precedes the no-portfolio explanation. | Current portfolio desktop/phone captures |
| F-049 | P2 | Portfolio Lab | A 9 px “SIZING WORKBENCH” eyebrow and decorative 2 px side stripes create a localized visual dialect outside the institutional system. | `caos/frontend/src/app/globals.css:1302,1365,1368` |
| F-050 | P2 | Portfolio Lab | A deterministic stress panel remains visible when no portfolio exists, adding a second unavailable context instead of consolidating setup. | Current portfolio captures |
| F-051 | P1 | Deep-Dive | Seven layers and an expanded seven-module L2 band create a high learned-navigation burden before the analyst reaches evidence or debate. | `caos/frontend/src/app/deepdive/page.tsx:106-113,634-683` |
| F-052 | P2 | Deep-Dive | Evidence IDs are independently openable in multiple places (11 excess controls), increasing tab stops and weakening one canonical source path. | `OutputRegister.tsx:212-367`; `tabs.tsx:112-487`; `OutSections.tsx:92-127` |
| F-053 | P2 | Deep-Dive | The permanent first-run tip, layer strip, standing-view strip, annotation controls, collapsed source register, and analysis cards consume several narrow rows before core argument text. | Current deep-dive phone capture; `page.tsx:607-740` |
| F-054 | P2 | Deep-Dive | A seeded adversarial debate can be richly populated while the scenario network says a completed live run is required. Labels are honest, but illustrative and unavailable-live contexts are cognitively adjacent. | Current desktop/phone captures; `page.tsx:540-560` |
| F-055 | P1 | Model Builder | The route has 79 interactive declaration sites—the product maximum—and presents assumptions, spreadsheet, scenario, evidence, history, save, export, and checkpoint controls simultaneously. | AST count; `caos/frontend/src/app/model/ModelV2Workbench.tsx:549-1884`; `app/model/page.tsx:825-1118` |
| F-056 | P1 | Model Builder | At 390 px the full sheet remains the dominant artifact, with small row labels and lateral columns; there is no explicit summary/read-only phone contract or handoff to desktop authoring. | Current `model-390x844.png`; `globals.css:1210-1223` |
| F-057 | P2 | Model Builder | Save Checkpoint and Export Model both occupy top-level action weight despite the shared one-primary-action contract. | `app/model/page.tsx:866-878`; `SubHeader.tsx:121-126` |
| F-058 | P1 | IC Book | `RouteHeading` announces “CAOS,” not IC Book, and the page duplicates “Add agenda item” in header and empty state. | `RouteHeading.tsx:9-29`; `ICBookWorkbench.tsx:641,1094-1099` |
| F-059 | P2 | IC Book | Expanding the agenda form reveals 11 controls across reference, decision, and thesis fields without staged sub-group progression. | `ICBookWorkbench.tsx:728-748` |

### Publish and Monitor

| ID | Pri | Surface | Fault and concept-goal mismatch | Evidence |
|---|---:|---|---|---|
| F-060 | P1 | Report Studio | “Submit to IC” and “Open IC decision” both open the same drawer; the first verb implies a consequential submission that has not occurred. | `caos/frontend/src/app/reports/page.tsx:977-995,1056` |
| F-061 | P1 | Report Studio | At 390 px the fixed-width paper opens clipped and text is too small to proof; authoring/lineage/export remain below the fold. Capability exists but the primary review task is not usable without zoom/pan. | Current `reports-390x844.png`; `globals.css:1225-1252,626-674` |
| F-062 | P1 | Report Studio | Desktop axe finds a serious scrollable-region-focusable defect, and the default native-disabled primary action disappears from keyboard order. | Rendered axe; `app/reports/page.tsx:864-877`; `Panel.tsx:5-20,59-84` |
| F-063 | P2 | Report Studio | Six evidence IDs are openable in both the paper and Lineage rail; the right rail also repeats composition/export facts already visible in the document. | `ReportDoc.tsx:273-300`; `panels.tsx:114-128`; current desktop capture |
| F-064 | P2 | Report Studio | Five zoom choices (50/75/85/100/Fit) increase control scanning without guaranteeing a readable 390 px default. | `app/reports/page.tsx:936-952` |
| F-065 | P1 | Pipeline | The desktop CP-X graph is a low-contrast edge hairball with truncated module labels; the phone opens on a partially visible graph with no ordered stage-list alternative/minimap. | Current pipeline desktop/phone captures; `components/pipeline/views.tsx:210-230` |
| F-066 | P2 | Pipeline | The header says demo route 0/24 modules while the route-plan graph is populated and lineage drivers are seeded; labels disclose demo, but the completion count and apparent graph fullness conflict at a glance. | `app/pipeline/page.tsx:282-319,357-387`; current captures |
| F-067 | P2 | Pipeline | DAG, SWIMLANES, CP-X, L0, orchestrator event log, CP-5B, and DIM ✓ expose engine ontology where analyst-facing stage/clearance language should lead. | `app/pipeline/page.tsx:268,308,536,550,553` |
| F-068 | P1 | Monitor | The surface is labelled LIVE while a seeded replay occupies the same Alerts dataset; real and illustrative events require continual visual parsing. | `app/monitor/page.tsx:199-207,228-268`; current desktop capture |
| F-069 | P1 | Monitor | Email Intelligence is built from static email constants but presented as “CP-MON intake”; populated copy says “sample,” not seeded/demo/illustrative, and another line calls intake a reconciled EOD tape. | `MonitorStreams.tsx:8-9,88-104,157-158`; `app/monitor/page.tsx:199-200,245-252,418` |
| F-070 | P1 | Monitor | Phone retains “Acknowledge selected,” but the phone triage component has no matching selection event and only per-alert Ack/Assign/Resolve. | `app/monitor/page.tsx:204-212,245-248`; `AlertInbox.tsx:419-440`; `PhoneTriage.tsx:176-209` |
| F-071 | P2 | Monitor | When there are no live alerts, an empty severity chart and equivalent-table control still consume a large middle column. | Current monitor desktop capture |

## Task 4A closure evidence

Closed on 2026-07-19 for the desktop/tablet remediation scope. The focused
implementation and verification record is
`.superpowers/sdd/caos-remediation-task-4a-report.md`.

| Findings | Closure evidence |
|---|---|
| F-017, F-022, F-023 | Issuer register sizes to observed rows and carries text identity without blank logo placeholders; Research, Sector, RV, Sponsors, Command, and Portfolio now consolidate their cold/no-data states instead of reserving empty workbench shells. |
| F-031, F-032 | Upload no longer advertises an already-visible jump target; Research exposes one run action and a compact cold report state. |
| F-036, F-037 | Sector refresh is the page primary; cold context/inspector regions are absent; four direct dossier tabs remain and Early Warning/Sources move under More; alert coverage uses an explicit active/inactive label. |
| F-039, F-041 | RV pre-screen uses one spanning setup state and keeps three candidate actions direct, with secondary actions under More. |
| F-042, F-043 | Sponsors uses one spanning observed-empty setup and withholds the header primary until a sponsor is selected. |
| F-045 | Command's no-coverage state presents one setup decision and suppresses empty digest, governance, cited-brief, and dataset shells while preserving the exact document-intake action. |
| F-048, F-049, F-050 | Portfolio filters are container-aware; the bespoke eyebrow class/rendering and decorative side stripes are absent; no-selection mounts one setup state without dataset, Context, Evidence, cited-brief, or stress frames, while populated preview/persist semantics remain unchanged. |
| F-072 | P1 | Monitor | QA role composition does not make governance/control-plane content structurally dominant; it mainly opens the inspector by default. | F-001/F-002; `PersonaWorkbench.tsx:51-55` |

### Settings and global feedback

| ID | Pri | Surface | Fault and concept-goal mismatch | Evidence |
|---|---:|---|---|---|
| F-073 | P1 | Settings | Role View copy promises working-density/posture/governance compositions that the renderer does not implement. | `app/settings/page.tsx:572-595`; F-001/F-002 |
| F-074 | P2 | Settings | Runtime model, “LLM lanes,” deployment variable names, code constants, and secret-key environment names are exposed to the primary analyst persona. | `app/settings/page.tsx:57-107,520-658`; current settings capture |
| F-075 | P2 | Settings | Maximum component depth is 14; stacked panels, 10–11 px prose, role/profile/device badges, and five tabs produce a configuration dump more than a task-oriented analyst settings surface. | `app/settings/page.tsx:519,534-536,763-796`; current captures |
| F-076 | P2 | Settings | “feed built near production” is vague and unverifiable. | `app/settings/page.tsx:714-719` |
| F-077 | P2 | Notifications | Every arbitrary toast `href` is labelled “Open execution graph,” so label and destination can diverge. | `components/shared/Notifications.tsx:19-50,138-144` |

## Persona findings

### Buy-side credit analyst — primary

| Need | Faults | Consequence |
|---|---|---|
| Defensible issuer view with one-click evidence | F-015, F-025, F-052, F-063 | Evidence is abundant but duplicated; demo metrics and repeated source entry points increase wrong-read/rechecking risk. |
| Fast deep work in Deep-Dive/Model/Reports | F-051–F-057, F-060–F-064 | Core surfaces are powerful at desktop but have high simultaneous-control density, ambiguous IC wording, and no credible phone review contract. |
| Multi-window orientation | F-005–F-008 | Small/truncated route identity and incorrect h1 mapping make it harder to know which issuer/run/artifact is active. |
| Committee-safe actions | F-028–F-030, F-047, F-060 | Compliance, readiness, preview/run, and submit/open language are not consistently 1:1 with behavior. |
| Efficient keyboard path | F-003, F-009, F-010, F-015 | Shared navigation and duplicated evidence controls create excess focus travel; Report has a verified focusability defect. |

### PM / CIO — secondary

| Need | Faults | Consequence |
|---|---|---|
| Ten-second posture and “what changed” | F-001, F-002, F-044–F-046 | PM view does not materially change dominant representation or columns; empty governance/digest/brief structures compete for attention. |
| Confidence without analytical excavation | F-014, F-025, F-068–F-071 | Completion grammar is inconsistent; demo/live contexts and demo issuer metrics demand analyst-level interpretation. |
| Short, role-prioritized navigation | F-003, F-004, F-016 | PMs receive the same 15-concept ontology as analysts rather than a posture/decision subset. |

### Head of Research / QA — secondary

| Need | Faults | Consequence |
|---|---|---|
| Governance/gates first | F-001, F-002, F-036, F-072, F-073 | QA view does not make governance the dominant representation; gate work remains one pane among many. |
| Clear truth boundary and immutable closure | F-014, F-028–F-030, F-060, F-068–F-070 | Mixed demo/live lanes and mismatched completion/action labels complicate audit ownership. |
| Coverage-health overview | F-037, F-042–F-045, F-071 | Empty canvas, repeated setup states, and no-data visualizations obscure where QA intervention is actually required. |

### Accessibility and inclusion scenarios

| Scenario | Faults | Consequence |
|---|---|---|
| Low vision / 200% zoom | F-005–F-007, F-011, F-012, F-061 | Microtype, clipped fixed artifacts, and one contrast failure make high-stakes numbers harder to verify. Current 200% behavior remains untested. |
| Keyboard-only | F-003, F-008–F-010, F-013, F-015, F-058, F-062 | The app is broadly keyboard-aware, but shared focus overhead, landmark errors, duplicated controls, and the Report violation remain. |
| Touch/phone | F-004, F-009, F-012, F-020, F-026, F-038, F-056, F-061, F-065, F-070 | Controls meet a 44 px floor and phone axe is clean, but task representations are often horizontally discoverable rather than deliberately adapted. |
| New specialist user | F-003, F-004, F-016, F-019, F-034, F-041, F-067, F-074 | Domain language is appropriate, but internal engine/permission/deployment vocabulary adds avoidable learning. |

## Goal-alignment summary

| Product/design goal | Assessment | Evidence |
|---|---|---|
| Precise, defensible, alert | **Strong but breached by action semantics.** Provenance, readiness, timestamps, gates, and explicit no-output states are excellent; F-024, F-028–F-030, F-040, F-047, F-060, and F-068–F-070 weaken the truth contract. | `01-evidence.md#copy-and-honesty-evidence` |
| Density with hierarchy | **Mixed.** Model and Report desktop are organized; route identity/microtype compress the hierarchy, while cold-start surfaces are sparse rather than meaningfully dense. | F-005–F-007, F-017, route captures |
| Color is signal | **Mostly achieved.** Core contrast and status signaling are strong; critical-on-elevated fails and Portfolio adds decorative side stripes. | F-011, F-049 |
| Show your work | **Best-in-product strength.** Evidence is pervasive and one click away, but repeated evidence affordances and demo metrics make the path noisier than necessary. | F-015, F-025, F-052, F-063 |
| Motion only for life | **Achieved.** Zero idle animations in the initial state; active motion is conditional and reduced-motion gated. | `01-evidence.md#weight-and-attention-evidence` |
| Committee-ready by default | **Strong output, weak verbs/preview readability.** Report paper and gates are excellent; Submit/Open wording, tiny appendix, phone clipping, and Report focusability are not committee-safe. | F-007, F-010, F-060–F-064 |
| WCAG 2.1 AA | **Close, not complete.** Phone axe is clean and focus/skip/reduced-motion contracts are good; one desktop serious violation, one contrast failure, wrong h1 mappings, and microtype remain. | F-007–F-012 |

## Confirmed strengths that should not be “fixed away”

- No AI-template/slop signature: the deterministic detector returned `[]`; the
  interface is domain-specific, restrained, and not a pastel card dashboard.
- Explicit live/demo/reference, reported/derived/modelled, freshness, QA,
  immutable-finalization, and no-sample-substitution copy is unusually strong.
- DecisionHeader's change/impact/action/evidence structure is the correct shared
  cognitive frame.
- The dark terminal palette, tabular numerical grammar, hairline grouping, and
  light paper counterpoint align strongly with the application goal.
- Global focus rings, skip links, reduced-motion rules, modal focus trapping,
  44 px phone controls, and error recovery are intentional and broadly effective.

## Audit limitations

- The rendered matrices cover current default/fixture states at 1440×900 and
  390×844, not every live-data branch, dialog, 200% zoom state, or coarse pointer.
- Backend truth behind “immutable,” “restricted handling,” “authorized,” and
  “authoritative” was not audited; those findings identify frontend claim risk,
  not proof that the backend is wrong.
- Visual harness “no layout failure” means controls were not clipped outside a
  scroll owner; it does not mean the analyst task remained usable without lateral
  discovery.
