---
target: query concept
total_score: 24
p0_count: 0
p1_count: 3
timestamp: 2026-06-30T02-01-27Z
slug: caos-frontend-src-app-query-page-tsx
---
# Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Strong ready/active/running/caveat states; errors lack recovery actions. |
| 2 | Match System / Real World | 3 | Analyst language fits, but capability labels still require prior CAOS module knowledge. |
| 3 | User Control and Freedom | 3 | Rail collapse, reset view, layout switch, inspector, and exports are present; Ask duplicates Query instead of helping the current state. |
| 4 | Consistency and Standards | 2 | Query page and Ask modal present similar but divergent workspaces and labels. |
| 5 | Error Prevention | 2 | Disabled capability reasons and runnable prompt filtering are good; unsupported or failed query paths do not guide recovery enough. |
| 6 | Recognition Rather Than Recall | 3 | Capability rail and runnable prompts are visible; the visible option count is too high. |
| 7 | Flexibility and Efficiency | 3 | Search, rail, prompt chips, graph modes, export, zoom, and node selection give experts multiple paths. |
| 8 | Aesthetic and Minimalist Design | 2 | Desktop is credible; the same concept is offered twice and mobile/narrow layout breaks. |
| 9 | Error Recovery | 2 | Graph/capability errors render inline, but messages are not actionable and lack retry/fallback paths. |
| 10 | Help and Documentation | 1 | No contextual explanation for mode choice, capability meaning, disabled states beyond raw reasons, or evidence interaction. |
| **Total** | | **24/40** | **Acceptable: live foundation, significant UX cleanup needed** |

# Anti-Patterns Verdict

**LLM assessment**: This does not look like generic AI slop. The desktop surface feels like a real institutional credit tool: dense rail, live readiness counts, graph canvas, caveats, and evidence inspector all match CAOS's "committee terminal" direction. The failure mode is product strangeness, not decoration. Query is already a full search workspace, yet the global Ask launcher opens a second Query-like modal on top of Query. That makes the concept feel less resolved than the visual craft.

**Deterministic scan**: `detect.mjs --json caos/frontend/src/app/query/page.tsx` returned `[]`. No detector findings for the source target.

**Visual overlays**: No reliable user-visible overlay is available. Mutable overlay preflight failed because browser evaluation could not set `document.title` or append a script (`Cannot set property title ... which has only a getter`). Browser fallback evidence was live inspection at `http://localhost:3001/query`, desktop screenshot, Ask-modal screenshot, and mobile viewport screenshot.

# Overall Impression

Query is a credible live concept: it loads 20/23 capabilities, auto-runs a backend-backed graph, exposes graph/table/scatter/lineage views, and keeps evidence close. The biggest opportunity is to make Query the one canonical place for graph search instead of letting Ask recreate it, then fix the narrow-viewport collapse so the surface survives analyst multi-window use.

# What's Working

1. **It opens on useful data, not an empty state.** Auto-running the first runnable preferred capability gives the analyst immediate graph evidence and proves liveness.
2. **Capability honesty is strong.** The rail distinguishes ready and unavailable capabilities with counts and reasons instead of hiding gaps or pretending all graph walks are available.
3. **The graph-to-evidence loop is visible.** Graph modes, node selection, citation viewer, inspector, caveats, and export actions form the right analytical vocabulary for a defensible credit workspace.

# Priority Issues

**[P1] Query and Ask compete on the Query route**

**Why it matters**: On `/query`, the analyst already has a full Query workspace. The floating Ask launcher opens a second modal with similar prompt chips and search behavior. This creates a concept loop: "Ask" is no longer a cross-surface assistive layer; it becomes another Query inside Query.

**Fix**: On `/query`, either hide the global Ask trigger or make it focus the existing Query input. Keep the overlay behavior for other concepts where it adds value without changing route.

**Suggested command**: `$impeccable distill query concept`

**[P1] Narrow viewport layout is structurally broken**

**Why it matters**: At 390px wide, the fixed 260px capability rail consumes most of the screen and leaves the search/results pane clipped. This also hurts desktop multi-window workflows, not just phones.

**Fix**: Collapse the capability rail by default below a practical width, expose it as a drawer or compact strip, and let the query/results pane own the viewport. Keep the active capability and ready count in the header.

**Suggested command**: `$impeccable adapt query concept`

**[P1] Some result interactions are mouse-first**

**Why it matters**: `GraphCanvas` nodes are keyboard focusable, but the table rows and lineage cards use clickable rows/divs without equivalent keyboard button semantics. Analysts using keyboard navigation can reach some graph states but not all result modes consistently.

**Fix**: Convert selectable lineage cards and table rows to accessible buttons or add `role="button"`, `tabIndex`, `onActivate`, and visible focus. Keep row density; do not add bulky controls.

**Suggested command**: `$impeccable audit query concept`

**[P2] Capability choice overload is high**

**Why it matters**: The primary decision point shows a search box, five prompt chips, four layout modes, export actions, inspector, and a rail with 23 capabilities across seven groups. Expert analysts can parse it, but first use requires too much scanning before intent is clear.

**Fix**: Keep search + 3-5 runnable prompt chips as the primary entry. Make the rail a secondary "Capability Index" with group collapse or filtering. Preserve the ready/unavailable counts because they carry trust.

**Suggested command**: `$impeccable layout query concept`

**[P2] Evidence affordance is present but under-explained**

**Why it matters**: The inspector is important to "show your work," but its trigger reads like a tool toggle rather than the payoff for selecting a node. The graph tells the analyst what is connected, but not clearly how to turn a node into evidence.

**Fix**: Rename or reframe `INSPECTOR` as `EVIDENCE`, show a compact selected-node state in the result header, and add a one-line graph hint only when no node is selected. Avoid onboarding copy; make it operational.

**Suggested command**: `$impeccable clarify query concept`

# Persona Red Flags

**Alex, power credit analyst**: The desktop path is fast because Query auto-runs and offers prompt chips, but Alex hits friction from duplicated Ask on `/query` and no visible query history/recent runs. They can run the graph quickly, but the second Query modal reads like redundant chrome.

**Sam, keyboard/accessibility-dependent analyst**: The main graph has focusable SVG nodes, which is good. But table rows and lineage cards are click-only, so equivalent result modes do not offer the same keyboard path. This violates the CAOS requirement that dense analytical controls remain keyboard-operable.

**Buy-side credit analyst, committee-prep mode**: The surface is defensible when it shows caveats and source links. The weak point is that disabled capability reasons and query errors are terse; when a graph walk cannot run, the analyst needs the next defensible action, not just the blocker.

# Minor Observations

- `EXPORT PDF` invokes `window.print()`. Label it `PRINT / PDF` unless a true PDF artifact is generated.
- `Lineage Flow` uses hover language; keyboard and touch users need the same instruction framed around selection.
- The modal Ask surface uses decorative text glyphs where the rest of Query has an SVG mark. Use the same mark vocabulary.
- The graph legend is useful but can crowd narrow screens; it should wrap below the canvas only when space allows.
- The capability rail's disabled reasons are valuable but visually cramped; long reasons need truncation plus tooltip/title.

# Questions to Consider

- Should `/query` be the canonical graph-search workspace, with Ask merely deep-linking or focusing it when already there?
- What is the one decision the analyst should make first: type a question, pick a capability group, or inspect the auto-run graph?
- Which unavailable capability reasons should become next actions, rather than just explanations?
