---
target: caos/frontend/src/app/command/page.tsx
total_score: 27
p0_count: 0
p1_count: 2
timestamp: 2026-06-28T23-48-27Z
slug: caos-frontend-src-app-command-page-tsx
---
#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Live/sample labels are present, but lens-specific status gets muddled across Portfolio and Sector RV. |
| 2 | Match System / Real World | 4 | Credit-desk language, table density, RV labels, and QA posture fit the analyst domain. |
| 3 | User Control and Freedom | 2 | Filtering exists but is hidden behind double-click and lacks a visible keyboard path. |
| 4 | Consistency and Standards | 3 | Shared panels/nav are strong; table header behavior diverges between sort and filter. |
| 5 | Error Prevention | 2 | Sector RV can produce invalid nested button markup when filter UI opens inside sortable headers. |
| 6 | Recognition Rather Than Recall | 2 | Header filters depend on title text and prior knowledge, not visible affordances. |
| 7 | Flexibility and Efficiency of Use | 3 | Power-user density, hotkeys, sorting, and filters exist, but discovery weakens them. |
| 8 | Aesthetic and Minimalist Design | 3 | The visual system is disciplined; the first view still has too many equal-weight signals. |
| 9 | Error Recovery | 3 | Query errors and clear actions exist, but table recovery is hidden behind per-column popovers. |
| 10 | Help and Documentation | 2 | Starter prompts and tooltips help; table mechanics and live-vs-sample scope need clearer inline help. |
| **Total** | | **27/40** | **Acceptable: strong system, significant interaction fixes needed** |

#### Anti-Patterns Verdict

**LLM assessment**: This does not read as generic AI UI. The Command Center has a specific institutional terminal language: restrained dark tokens, compact panel chrome, tabular numbers, and honest source/state labeling. The risk is the opposite of AI slop: the interface is so desk-dense that some useful controls become invisible.

**Deterministic scan**: The bundled detector found 0 issues for `caos/frontend/src/app/command/page.tsx` and 0 issues for the widened scope `caos/frontend/src/components/command`.

**Visual overlays**: No reliable user-visible detector overlay was available. Browser inspection and screenshot succeeded on `http://localhost:3000/command`, but the available browser API did not expose the mutable injection path required by the overlay flow.

#### Overall Impression

Command Center looks credible and domain-native. It feels like a real credit desk surface, not a marketing dashboard. The single biggest opportunity is turning hidden table power features into visible, keyboard-safe controls without reducing density.

#### What's Working

- **The product tone is right.** `Sample portfolio - not live`, `grounded in the metric store`, and `market-data file` are honest labels that protect analyst trust.
- **The shared chrome works.** Panel headers, concept navigation, dense type, and semantic color are coherent across Portfolio, Research, and Sector RV.
- **Sector RV is the strongest visual lens.** The native sector dropdown, table hierarchy, and lower summary panels give the analyst a clear desk-sheet workflow.

#### Priority Issues

**[P1] Hidden filter controls and invalid sortable-filter headers**

**Why it matters**: Portfolio and RV filtering is powerful, but users must discover it through `title="Double-click to filter..."`. Keyboard users cannot activate Portfolio filters directly, and Sector RV nests `FilterHeader` inside a sort `<button>`, which can create `<button>` inside `<button>` when the filter dialog opens.

**Fix**: Split table header controls into two explicit targets: a sort button on the label and a small filter button/icon beside it. Render the filter popover outside the sort button, ideally through a fixed-position portal or sibling. Add Enter/Space support and `aria-haspopup`.

**Suggested command**: `$impeccable harden caos/frontend/src/components/shared/TableColumnFilter.tsx`

**[P1] Wide tables lose decision context**

**Why it matters**: Portfolio uses a 24-column, 2020px-wide grid; Sector RV uses a 1760px-wide peer table. On normal laptop width, the analyst loses issuer identity while scanning right-side metrics unless they keep mentally mapping rows.

**Fix**: Freeze the first one or two identity columns for Portfolio and Sector RV, add a compact column-set control, and keep the row action/issuer anchor visible while horizontally scrolling.

**Suggested command**: `$impeccable adapt caos/frontend/src/components/command`

**[P2] Header status is not lens-specific enough**

**Why it matters**: In Sector RV, the header still shows `Sample portfolio - not live`, Watch, QA open, and Alerts today. Those badges may be true globally, but they compete with RV-specific context and blur what is live, sample, or file-derived in the active lens.

**Fix**: Make the right header cluster lens-aware: Portfolio gets sample/watch/QA posture, Research gets freshness/QA/gaps, Sector RV gets market-data file timestamp, row count, and coverage universe.

**Suggested command**: `$impeccable clarify caos/frontend/src/app/command/page.tsx`

**[P2] First-view hierarchy overload**

**Why it matters**: The first view asks the analyst to process concept nav, lens toggle, sample warning, Watch/QA/Alerts, query prompt, starter prompts, and a dense coverage table. The pieces are useful, but too many compete before the analyst picks a task.

**Fix**: Let the active lens declare one primary workflow. In Portfolio, keep Ask across issuers compact until focused or after a query. In Sector RV, let the sector selector and peer table own the first row.

**Suggested command**: `$impeccable layout caos/frontend/src/app/command/page.tsx`

#### Persona Red Flags

**Alex (Power User)**: Alex can move fast once they know the system, but hidden double-click filters slow discovery. They will expect sortable and filterable headers to expose separate visible controls and keyboard access.

**Sam (Accessibility-Dependent User)**: Sam can reach many elements because the app has focus rings and semantic buttons, but Portfolio filter headers are generic spans with double-click handlers. Sector RV's nested interactive markup is a screen-reader and hydration risk.

**Buy-Side Credit Analyst "Priya"**: Priya trusts the dense table and RV math, but loses row context when comparing right-side metrics. Sticky issuer identity and lens-specific metadata would reduce misreads under committee pressure.

#### Minor Observations

- The native Sector RV dropdown is the right call; keep it.
- Starter prompts in Ask across issuers are useful, but they should visually recede after the user understands the tool.
- The `Sample portfolio - not live` label is excellent in Portfolio, but should not be universal chrome for every Command Center lens.
- The detector is clean because the issues are interaction semantics, not visual slop patterns.

#### Questions to Consider

- What is the Command Center's primary first action: ask a question, scan portfolio posture, or inspect market RV?
- Should Portfolio and Sector RV share the same table control vocabulary, or does RV need a stronger trading-sheet header pattern?
- Which columns are committee-critical enough to stay pinned at all times?
