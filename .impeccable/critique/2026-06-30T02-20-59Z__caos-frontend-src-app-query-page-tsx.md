---
target: query page
total_score: 34
p0_count: 0
p1_count: 0
timestamp: 2026-06-30T02-20-59Z
slug: caos-frontend-src-app-query-page-tsx
---
# Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Loading status, walking graph animations, and selection indicator in header are highly explicit. |
| 2 | Match System / Real World | 4 | Domain-appropriate analyst edge paths CP-1/2/5 speak the user's credit vocabulary fluently. |
| 3 | User Control and Freedom | 4 | Flexible navigation, layout switcher, scrollable aside panels, and resolved hotkey modal containment. |
| 4 | Consistency and Standards | 4 | Cohesive visual tokens, custom SVG marks, and aligned buttons/shortcuts. |
| 5 | Error Prevention | 3 | Blocked capabilities are greyed out with tooltips, and suggest did-you-mean alternatives, preventing dead-ends. |
| 6 | Recognition Rather Than Recall | 4 | Runnable prompt chips and Evidence hints make capabilities and interaction payloads discoverable. |
| 7 | Flexibility and Efficiency | 4 | Accel hotkeys, customizable viewports, layout switchers (graph, lineage, table, scatter) cater to expert flow. |
| 8 | Aesthetic and Minimalist Design | 4 | Restrained dark terminal style with functional seniorities. Auto-collapsing sidebar and scrollable legend on mobile protect space. |
| 9 | Error Recovery | 3 | Failures and blocked queries render inline with did-you-mean suggestions to guide next actions. |
| 10 | Help and Documentation | 3 | Lineage guidelines and caveats are contextually printed, though a general query guide could benefit novices. |
| **Total** | | **34/40** | **Good: solid foundation, minor improvements needed** |

# Anti-Patterns Verdict

**LLM assessment**: The query interface has been dramatically cleaned up and matches the "designed Bloomberg terminal" aesthetic of CAOS. The sidebar choice overload is eliminated via collapsible groups, the mobile viewport behaves perfectly with auto-collapse, and the hotkey clash with global Ask has been completely resolved. The layout is clean and avoids SaaS clichés.

**Deterministic scan**: `detect.mjs` returned `[]` findings. No automated anti-pattern issues detected.

**Visual overlays**: Skipped due to browser automation CDP context management error. Fallback signal used (manual check on dev server port 3001).

# Overall Impression

The Query page has evolved from a conflicting workspace layer to a canonical graph search hub. The desktop path is efficient, and the mobile view behaves correctly. The biggest remaining opportunity is keyboard navigation for the scatter plot points and introducing query history for power analysts.

# What's Working

1. **Hotkey and Search Containment**: Alt+K and ⌘K now focus the search input instead of spawning a competing Ask modal inside a query workspace, keeping the route clean.
2. **Side Group Collapsibility**: Collapsing categories reduces choices from 23 down to 7 readable headers with auto-expanding active traversals.
3. **Responsive Spacing**: Sidebar auto-collapsing below 1024px and MetricPill label hiding at narrow breakpoints allow the query and results canvas to own the viewport space.

# Priority Issues

**[P2] Scatter Plot points are click-only**
- **Why it matters**: Sam (keyboard-only analyst) cannot select or hover points in the Scatter view. Focus outline and keyboard actions (`Enter`/`Space`) are missing on svg `<g>` nodes in `ScatterCanvas.tsx`.
- **Fix**: Add `tabIndex={0}`, `role="button"`, and `onKeyDown` handlers on the container group of each plotted scatter point. Connect `onFocus`/`onBlur` events to trigger highlight states.
- **Suggested command**: `$impeccable audit query concept`

**[P2] No visible search history or recent queries**
- **Why it matters**: Power credit analysts like Alex run complex graph searches and need to look back at recently walked edges or compare results, but currently must retype or reselect from scratch.
- **Fix**: Persist the last 5-10 run capability IDs in localStorage and render a "Recent Queries" list of chips above the prompt suggestions.
- **Suggested command**: `$impeccable onboard query concept`

**[P3] Lack of domain definitions for capability terms**
- **Why it matters**: Novices like Jordan might struggle to understand specific graph walks (e.g. CP-2 contagion shocks vs CP-1C credit profile mapping) without inline hints or glossary lookups.
- **Fix**: Render a tiny information icon next to expanded capability names that displays a tooltip explaining the metric definition or source model.
- **Suggested command**: `$impeccable clarify query concept`

# Persona Red Flags

**Alex (Power User)**: Alex's speed is high, but the lack of search history means they have to retype query search criteria or re-toggle collapsible sidebar lists to run repetitive credit graph assessments.

**Sam (Keyboard/A11y Analyst)**: Sam can navigate the Relative Value table and Lineage flow keyboard-only, but gets blocked when using the Scatter view layout since points cannot receive keyboard focus or selection events.

**Jordan (First-Timer)**: Jordan finds the cleaner collapsible rail easier to parse, but requires domain terminology translation (e.g. what is CP-1C?) which is currently missing.

# Minor Observations

- The scrollable legend now prevents horizontal wrapping overflow on mobile, but could use a subtle gradient indicator at the right edge to show there's more content to scroll.
- The `PRINT / PDF` button now accurately reflects the action (window.print).
- The `AskMark` SVG replaced the decorative `✦` stars, aligning visual assets.
