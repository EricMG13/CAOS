# Verdict

**REDESIGN — At 17/30, CAOS should redesign its shared persona, navigation, action-language, and narrow-task architecture while explicitly preserving the institutional visual system, evidence/provenance model, state grammar, and Report Studio paper identity.**

The mechanical verdict is REDESIGN because the total is below 20. This is not a
recommendation to restyle or rebuild every route: the visual language and many
analytical primitives are strong. The load-bearing failures recur across shared
experience contracts—particularly understandable (#4) and honest (#6)—so
route-by-route polish alone cannot resolve them.

## Highest-leverage moves

1. **Principles #2/#4 — Make persona composition real:** apply `dominantRepresentation`, `summaryDensity`, `tableColumnPreset`, and role-specific slot order to rendered content while keeping permissions and underlying data identical. Evidence: `caos/frontend/src/lib/persona-composition.ts:55-95`; `caos/frontend/src/components/shared/PersonaWorkbench.tsx:51-55,201-206`.
2. **Principles #4/#10 — Rebuild navigation around role and frequency:** replace the equal-weight 15-destination rail/compact icon burden with a short role-prioritized primary set plus a complete labelled browse/palette fallback, and move route actions earlier in keyboard order. Evidence: `caos/frontend/src/lib/nav.ts:13-60`; `caos/frontend/src/components/shared/WorkflowRail.tsx:18-75`; `01-evidence.md#accessibility-and-responsive-evidence`.
3. **Principles #2/#3/#8 — Define explicit narrow task contracts:** decide per surface whether 390 px is authoring, review, or triage, then provide a task-shaped representation—fit-to-width report reading, an ordered Pipeline stage list, a Model summary/handoff, and deliberate table/tab reveal—instead of treating scroll ownership as sufficient responsiveness. Evidence: `/tmp/caos-a11y-narrow/reports-390x844.png`, `/tmp/caos-a11y-narrow/pipeline-390x844.png`, `/tmp/caos-a11y-narrow/model-390x844.png`, `/tmp/caos-a11y-narrow/issuers-390x844.png`.
4. **Principle #6 — Enforce one verb and one truth context per action/data lane:** rename the Report drawer action to what it does, visually separate Monitor live work from seeded replay, segregate demo issuer metrics from no-run real context, and remove composition/environment implementation language from analyst chrome. Evidence: `caos/frontend/src/app/reports/page.tsx:735-768`; `caos/frontend/src/app/monitor/page.tsx:199-207,228-268`; `caos/frontend/src/app/issuers/profile/ProfileContent.tsx:702-814`; `caos/frontend/src/app/settings/page.tsx:520-658`.
5. **Principles #3/#4/#8 — Restore hierarchy and finish accessibility edges:** promote route identity to the declared 16 px title tier, establish a readable on-screen paper/appendix floor, fix Ask's 380 px reader and nested main, fix the Report scrollable-region violation and critical-on-elevated contrast, complete route h1 mappings, and converge happy-path closure. Evidence: `caos/frontend/src/components/shared/ShellIdentity.tsx:47-50`; `caos/frontend/src/app/globals.css:626-674`; `caos/frontend/src/components/shared/Ask.tsx:770-830`; `caos/frontend/src/components/shared/RouteHeading.tsx:9-29`; `01-evidence.md#accessibility-and-responsive-evidence`.

## Preserve boundary

- Preserve the workspace palette, mono/tabular numeric grammar, hairline grouping,
  signal-only status color, and reduced-motion behavior.
- Preserve DecisionHeader's change/impact/action/evidence contract, explicit
  live/demo/reference authority, source-level evidence access, publish/readiness
  gates, and immutable finalization.
- Preserve the light Report Studio paper as a distinct committee artifact.
- Preserve the underlying data authority and permissions across all role views.

The red-team decision gate for this interpretation is recorded in
`.agent-reviews/redteam.md` under “All-surface frontend design-audit critic pass.”
