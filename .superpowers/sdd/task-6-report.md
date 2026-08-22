# Task 6 report — Workbench polish, reflow, and verification

## Delivery

- Commit: `e013294 style(frontend): polish analyst workbench foundation`
- Base: `ea9161d`
- Screenshots (uncommitted):
  - `/Users/ericguei/Claude/Projects/CAOS/outputs/workbench-foundation-1440.png`
  - `/Users/ericguei/Claude/Projects/CAOS/outputs/workbench-foundation-1024.png`

## Implementation

- Reworked the shell hierarchy around a 184px sticky workflow rail, 56px authority bar, dominant 1600px canvas, centered native palette, and fixed 440px contextual drawer.
- Added compact linked evidence chips, selection/state treatments, and the requested non-pulsing three-bar `LoadState` skeleton while preserving explicit error and empty states.
- Added CSS-only 1100/900/520 reflow, with table overflow remaining local to `.table-wrap`.
- Expanded the existing axe runner to all nine routes at desktop, laptop, and reflow sizes, retaining one JSON result with viewport names.
- Added reduced-motion and same-client case-list request assertions to the real smoke journey.
- The new request assertion exposed a real dynamic-page remount. `Workspace` now lives in the persistent root layout and derives its active destination from `usePathname`; same-client workflow navigation retains the shell and case list without cache/storage/global state.

## Verification

| Check | Result |
|---|---|
| `npm run lint -- --max-warnings=0` | PASS |
| `npx tsc --noEmit` | PASS |
| `npm run build` | PASS; 12 static pages generated |
| `PYTHONPATH=server /private/tmp/caos-task1-venv/bin/python -m pytest tests/test_clean_slate.py -q` | PASS; 28 passed, one upstream Starlette deprecation warning |
| Fresh `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | PASS; same-client workflow case-list requests `0`, reduced motion PASS, no linked-focus request, clean console, no reflow overflow |
| Final smoke timing | DCL `23.8ms`, FCP `40ms`; both below Task 1 110% limits (`64.46ms`, `74.8ms`) |
| `CAOS_URL=http://127.0.0.1:8010 npm run a11y` | PASS; 27 route/viewport combinations, 0 violations |
| GitNexus staged change detection | MEDIUM; six intended files, four Workspace render processes, no HIGH/CRITICAL risk |

## Visual inspection

- 1440×1000: workflow hierarchy, case authority, and dominant change/implication canvas are clean and unclipped; Sources/QA/Command remain compact.
- 1024×768: accepted authority copy is abbreviated responsively, new-analysis state remains visible, and controls stay readable without horizontal overflow.
- QA drawer: fixed right overlay does not shrink the canvas, focusable heading/copy are legible, and the contextual action remains reachable.
- Design detector findings for established Inter/JetBrains Mono, legacy radii/paper literals, and existing callout side rules were reviewed against `DESIGN.md` and `.impeccable.md`; they are pre-existing documented vocabulary, not Task 6 drift. The new evidence chip was aligned to the documented 2px radius.

## Confidence review

1. Persistent shell ownership could have duplicated page shells: verified with production build plus direct-route and client-navigation smoke; root layout intentionally owns the visible shell and the existing pages retain route metadata/static generation.
2. Responsive chrome could clip at 1024/720: adversarially checked screenshots, explicit 720px scroll-width assertion, and axe at all three viewports; no clipping or page-level overflow found.
3. The drawer could shrink the analytical canvas or lose focus: verified fixed top-layer positioning and the existing smoke focus-return assertions.
4. Timing/request assertions could hide a regression: no cache/storage/module global was added; the route remount was fixed at the layout boundary and measured below budget.

Fixed: dynamic-page Workspace remount and laptop authority wrapping. Verified fine: authority/drawer focus, responsive overflow, reduced motion, evidence linking, performance, and all 27 a11y contexts. Still open: none in Task 6 scope.

Rewrite tournament skipped: the only production logic additions are the native pathname-to-destination expression and a semantic loading branch; neither meets the skill's non-trivial rewrite threshold. The full branch tournament remains Task 7.

## Reviewer follow-up — reactive URL authority

- Replaced mount-only `q`/`artifact` hydration and the source-only synchronization helper with direct `useSearchParams` derivation, so persistent-shell navigation updates Sources, Deep-Dive, and Command Center immediately.
- Added authority-gated synchronization for URL `case` and explicit non-empty `run` changes. Workflow links that omit `run` preserve the selected case's current execution.
- Keyed authority synchronization to actual case/run query changes. This prevents internal case selection from being mistaken for stale external navigation and causing an authority refresh loop.
- Extended the live smoke from Command Center through the command palette to an exact artifact-backed Sources view, then through Deep-Dive and Command Center question URLs. The journey proves the artifact digest and both questions render without another case-list request, and caps authority reads to catch refresh oscillation.

### Follow-up verification

| Check | Result |
|---|---|
| `npm run lint -- --max-warnings=0` | PASS |
| `npx tsc --noEmit` | PASS |
| `npm run build` | PASS; 12 static pages generated |
| Fresh `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | PASS; artifact/q same-client navigation, zero repeated case-list requests after reset, no authority refresh loop |
| Final smoke timing | DCL `16.3ms`, FCP `72ms` |
| Fresh `CAOS_URL=http://127.0.0.1:8010 npm run a11y` | PASS; 27 route/viewport combinations, 0 violations |
| GitNexus staged change detection | HIGH at monolithic `Workspace` symbol granularity; inspected context shows no incoming callers and broad render-flow attribution from stale line bounds, while the staged diff is confined to query synchronization plus smoke/report |

Confidence review found and fixed one real race: state-driven case selection briefly left the old query visible, so an unrestricted synchronization effect could reverse the selection and oscillate authority requests. Query-signature gating now distinguishes external URL changes from internal state transitions, and the live smoke includes a request ceiling for regression coverage. The direct-query design won the rewrite comparison because it eliminates three mirrored route-state stores; the remaining case/run state is intentionally retained for authority and execution lifecycle control.
