# Remaining CAOS Surfaces — Feature-Parity Gate

This register is the retirement gate for the compatibility-first Workbench +
Evidence Atlas migration. A checked baseline item is a capability that exists in
the pre-retirement implementation and must remain reachable. A legacy state path
may be removed only after its row has automated or browser evidence in the final
column.

Status legend: **baseline** = confirmed in the current implementation;
**wired** = bound to the new owned context/version contract; **verified** =
behavior exercised after migration.

| Surface | Preserved baseline contract | New compatibility contract | Status / release evidence |
|---|---|---|---|
| Issuers | Filters, saved views, selection, batch actions, ownership, coverage and profile opening | Typed `issuers` surface state; context-preserving profile handoff | Verified; live browser + context tests |
| Upload | Multi-file intake, supported formats, malware scan, chunking, run-mode selection, retry and run creation | Immutable `SourceManifest` with hashes, origin, method, extraction and scan state | Verified; manifest API + full server suite |
| Research | Brief composer, background polling, progress, result, source list, retry and Deep-Dive/Report exits | Analyst/context-owned resumable job; authority envelope; finding handoff | Verified; research contracts + browser matrix |
| Sponsors | Sponsor grouping, affected issuers, event/profile detail and navigation | Typed sponsor selection plus context artifact reference | Verified; live browser + lint/type gates |
| Command | Existing coverage/risk modules, ranked changes, governance queue, portfolio views and alerts | Context-preserving findings, alert events and evidence inspection | Verified; ranked-change/governance tests + browser matrix |
| Deep-Dive | Full module tree; generic and bespoke tabs; Summary/Report/Dense layouts; Evidence Sync; decision/source rails; QA flags; issuer chat; ASK; simulation; vault export; report/model handoffs | Selected issuer run and thesis/finding references in owned context | Verified; 673-test frontend suite + desktop/phone/zoom captures |
| Model Builder | Full spreadsheet grid; direct edits; multi-cell paste; formula bar; assumptions; scenarios; quarters; collapse; evidence; undo/redo; local checkpoints; database save; CSV export | Mutable `SavedModel` plus immutable analyst-owned `ModelCheckpoint`; context/run linkage and restore API | Verified; compatibility tests, checkpoint API, desktop/phone/zoom captures |
| Report Studio | Light paper editor; compose controls; edits; omissions; zoom; lineage; Decision Room; model appendix; print/PDF | Server-owned `ReportDraft`; immutable `ReportVersion` tied to exact run/checkpoint/thesis; export gate | Verified; draft/version contract tests + live browser capture |
| Pipeline | Live/reference modes, run list, stages, progress, failures, recovery and explicit open | Source-manifest/run references and typed `pipeline` state | Verified; exact-run handoff + browser matrix |
| Monitor | Alert inbox, acknowledgement, assignment, resolution, control-plane and phone triage | Immutable team-visible `AlertEvent` plus existing lifecycle `AlertState` | Verified; inbox/governance/phone tests + browser matrix |
| Settings | Analyst preferences, integrations and environment information | Partial optimistic-revision PATCH; compatibility PUT retained | Verified; revision tests + live browser capture |
| Issuer Profile | All existing sections/metrics, watchlist, risk posture, profile navigation and analyst handoffs | Context identity, selected run and version-aware handoffs | Verified; profile tests + seeded live browser capture |
| Global ASK | Navigation, actions, modules, issuers, saved-view lookup, contextual question and route exits | Analytical questions execute through `/api/query/runs`; findings can be pinned | Verified; analytical execution uses versioned Query run; issuer-scoped ASK retained |

## Deep-Dive no-regression checklist

- [x] Module navigation and all registered modules remain rendered by the existing implementation.
- [x] Summary, Report and Dense layout controls remain available.
- [x] Bespoke and generic module output tabs remain intact.
- [x] Cross-pane Evidence Sync and source details remain intact.
- [x] QA actions and issuer chat remain intact.
- [x] Simulation controls, ASK, vault export and downstream handoffs remain intact.
- [x] Ratification appends a thesis version, updates the active context and can pin a finding.
- [x] Desktop and 200% zoom keyboard/browser parity recorded.

## Model Builder no-regression checklist

- [x] Editable grid and formula bar remain the specialist workspace.
- [x] Multi-cell paste, overrides and input validation remain intact.
- [x] Assumptions, scenarios, quarter toggle and panel collapse remain intact.
- [x] Undo/redo and local named checkpoint controls remain intact during migration.
- [x] Database draft save and model CSV export remain intact.
- [x] Page primary action saves an immutable server checkpoint after the draft save succeeds.
- [x] Server checkpoint list/restore, conflict and report handoff exercised.
- [x] Desktop, narrow read-only handoff and 200% zoom browser parity recorded.

## Retirement rule

Do not delete a legacy persistence or route-specific recovery path while any
corresponding checkbox is open. Query, Sector Review and RV Screener are
integration dependencies only and are excluded from layout migration in this
register.
