```text
/make-plan Redesign the shared CAOS frontend experience architecture across all 18 routes. Current design failed audit at 17/30 with critical gaps in principles #4 understandable and #6 honest.

Verdict paragraph (quoted from 03-verdict.md):
> REDESIGN — At 17/30, CAOS should redesign its shared persona, navigation, action-language, and narrow-task architecture while explicitly preserving the institutional visual system, evidence/provenance model, state grammar, and Report Studio paper identity.

Why redesign and not refine: The Rams total is below the mechanical 20-point threshold, and the role/view promise plus action/data language failures recur in shared, load-bearing contracts rather than isolated route styling.

Preserve from current design (MUST be non-empty — at minimum, name the brand tokens):
- Dark institutional terminal tokens and signal semantics: `caos/frontend/src/app/globals.css:5-70`; keep `#0a0a0f` → `#11131d` → `#1d2030`, hairline borders, Inter/JetBrains Mono, tabular numerics, accent/status colors, and reduced-motion behavior.
- Evidence/provenance and decision structure: `caos/frontend/src/components/shared/DecisionHeader.tsx:135-196`, `caos/frontend/src/components/shared/ProvenanceChip.tsx:13-25`, and source viewers; retain change/impact/action/evidence, live/demo/reference authority, and one-click evidence access.
- Committee paper identity and readiness gates: `caos/frontend/src/app/reports/page.tsx:750-768,773-860` and `caos/frontend/src/app/globals.css:626-674`; preserve the cream paper, immutable versions, publish gate, and report/model lineage.
- Shared explicit state and accessibility primitives: `caos/frontend/src/components/shared/SurfaceState.tsx:6-40`, `caos/frontend/src/app/layout.tsx:40-57`, and `caos/frontend/src/app/globals.css:175-186,498-518`.

Discard (MUST be non-empty — name the structural patterns causing the failures):
- Inert persona configuration presented as a working composition contract. Evidence: `caos/frontend/src/lib/persona-composition.ts:55-95` values are only emitted as data attributes by `caos/frontend/src/components/shared/PersonaWorkbench.tsx:201-206`. Caused failure on principles #2, #4, and #6.
- Equal-weight global navigation and tooltip/icon-dependent compact discovery for 15 destinations. Evidence: `caos/frontend/src/lib/nav.ts:13-60` and `caos/frontend/src/components/shared/WorkflowRail.tsx:18-75`. Caused failure on principles #4 and #10.
- “All capabilities remain in the DOM” as the responsive success criterion. Evidence: current 390×844 Report, Pipeline, Model, and Issuers captures show clipped/lateral task surfaces despite zero harness layout overflow. Caused failure on principles #2, #3, and #8.
- Ambiguous high-stakes verbs and mixed truth contexts: Report drawer naming, Monitor live/demo co-location, no-run demo issuer metrics, and environment-key copy. Evidence: `caos/frontend/src/app/reports/page.tsx:735-768`, `caos/frontend/src/app/monitor/page.tsx:199-268`, `caos/frontend/src/app/issuers/profile/ProfileContent.tsx:702-814`, `caos/frontend/src/app/settings/page.tsx:520-658`. Caused failure on principles #4 and #6.

Top 3–5 moves from the audit (verbatim):
1. Principles #2/#4 — Make persona composition real: apply `dominantRepresentation`, `summaryDensity`, `tableColumnPreset`, and role-specific slot order to rendered content while keeping permissions and underlying data identical. Evidence: `caos/frontend/src/lib/persona-composition.ts:55-95`; `caos/frontend/src/components/shared/PersonaWorkbench.tsx:51-55,201-206`.
2. Principles #4/#10 — Rebuild navigation around role and frequency: replace the equal-weight 15-destination rail/compact icon burden with a short role-prioritized primary set plus a complete labelled browse/palette fallback, and move route actions earlier in keyboard order. Evidence: `caos/frontend/src/lib/nav.ts:13-60`; `caos/frontend/src/components/shared/WorkflowRail.tsx:18-75`; `01-evidence.md#accessibility-and-responsive-evidence`.
3. Principles #2/#3/#8 — Define explicit narrow task contracts: decide per surface whether 390 px is authoring, review, or triage, then provide a task-shaped representation—fit-to-width report reading, an ordered Pipeline stage list, a Model summary/handoff, and deliberate table/tab reveal—instead of treating scroll ownership as sufficient responsiveness. Evidence: `/tmp/caos-a11y-narrow/reports-390x844.png`, `/tmp/caos-a11y-narrow/pipeline-390x844.png`, `/tmp/caos-a11y-narrow/model-390x844.png`, `/tmp/caos-a11y-narrow/issuers-390x844.png`.
4. Principle #6 — Enforce one verb and one truth context per action/data lane: rename the Report drawer action to what it does, visually separate Monitor live work from seeded replay, segregate demo issuer metrics from no-run real context, and remove composition/environment implementation language from analyst chrome. Evidence: `caos/frontend/src/app/reports/page.tsx:735-768`; `caos/frontend/src/app/monitor/page.tsx:199-207,228-268`; `caos/frontend/src/app/issuers/profile/ProfileContent.tsx:702-814`; `caos/frontend/src/app/settings/page.tsx:520-658`.
5. Principles #3/#4/#8 — Restore hierarchy and finish accessibility edges: promote route identity to the declared 16 px title tier, establish a readable on-screen paper/appendix floor, fix Ask's 380 px reader and nested main, fix the Report scrollable-region violation and critical-on-elevated contrast, complete route h1 mappings, and converge happy-path closure. Evidence: `caos/frontend/src/components/shared/ShellIdentity.tsx:47-50`; `caos/frontend/src/app/globals.css:626-674`; `caos/frontend/src/components/shared/Ask.tsx:770-830`; `caos/frontend/src/components/shared/RouteHeading.tsx:9-29`; `01-evidence.md#accessibility-and-responsive-evidence`.

Redesign principles in priority order:
1. Principle #4 — Understandable — every role should identify its first task, primary action, truth context, and navigation path without tooltip-dependent or implementation-language interpretation.
2. Principle #6 — Honest — role settings must visibly change composition, every high-stakes verb must map 1:1 to mutation behavior, and live/reference/demo data must occupy unambiguous contexts.
3. Principle #2 — Useful — each desktop and narrow surface must optimize the actual analyst/PM/QA task, not merely preserve every component.

Deliverables for the plan:
- New shared information architecture (not derived mechanically from the 15-link rail), including Analyst, PM/CIO, and Head of Research/QA route priorities.
- New persona-composition contract showing exactly which representation, density, columns, slots, and actions change while permissions/data remain invariant.
- New primary flows for Command, Deep-Dive, Model, Report, Monitor, and support routes, with desktop and narrow low-fi states compared side-by-side to current.
- Copy/action truth matrix for role claims, Report/IC actions, live/demo/reference lanes, Settings language, and disabled-action explanations.
- States checklist: empty, loading, error, success, focus, disabled, stale, partial, offline, and unavailable.
- Accessibility and performance verification: axe at 1440×900/390×844, 200% zoom, full primary-action keyboard path, contrast, no page overflow, and production JS/request budget.
- Migration path that preserves route URLs, saved analyst settings, data authority, report versions, evidence links, and keyboard shortcuts.
- Cutover criteria: persona behavior tests pass, the five priority actions map 1:1 to labels, narrow task contracts complete without blind lateral discovery, Report axe is clean, and preserved visual/evidence invariants remain intact.

Anti-patterns to guard against (specific to REDESIGN):
- Porting old structure under new styling.
- Keeping both designs behind a flag indefinitely.
- Redesigning to follow a trend rather than the principles above.
- Treating the Preserve list as optional — it must be filled before this handoff is valid.
```
