# Consolidated audit evidence

Date: 2026-07-20  
Scope: the 18 desktop/tablet routes listed in `00-scope.md`; phone-specific redesign remains excluded.

## Visual system and hierarchy

- The final normal-motion capture matrix is archived under [`captures/all-routes/`](captures/all-routes/). It covers 1440×900, 1280×900, 1024×768, and 768×1024 for every route.
- The institutional terminal system remains coherent across the matrix: dark stepped surfaces, semantic signal color, Inter/JetBrains Mono roles, tabular numerics, restrained hairlines, and one deliberate light-paper Report counterpoint. Representative evidence: [`command-1440x900.png`](captures/all-routes/command-1440x900.png), [`model-mode-reference-1024x768.png`](captures/all-routes/model-mode-reference-1024x768.png), and [`reports-mode-reference-1440x900.png`](captures/all-routes/reports-mode-reference-1440x900.png).
- Shell identity, route headings, primary actions, and dense panel titles use the shared hierarchy rather than route-local title dialects. The route-registry and hierarchy/color contract tests are included in the 1,829-test final frontend run.
- Sparse Command and Monitor data no longer sit inside misleading full-height artifact frames. Evidence: [`command-1440x900.png`](captures/all-routes/command-1440x900.png) and [`monitor-1440x900.png`](captures/all-routes/monitor-1440x900.png).

## Usefulness, information architecture, and personas

- `SurfaceComposition` resolves surface × persona slot order, emphasis, leading dataset, open panels, table presets, summary limits, and action priority. The final suite includes `persona-composition.test.ts` and `PersonaWorkbench.test.tsx`; all personas retain the shared authorized inventory.
- Analyst priority navigation leads with Directory, Deep-Dive, Model Builder, Report Studio, and Pipeline. PM and QA projections retain the canonical ontology while changing the five priority destinations and surface-leading content.
- Command PM and Monitor QA are behaviorally differentiated through leading region, dataset, columns, and inspector defaults—not diagnostic attributes alone. The route interaction/persona tests passed in the final suite.
- The route-level density repairs are visible in the final captures: Model keeps the analytical sheet dominant, Pipeline presents analyst stages plus an ordered peer table, Report uses a single IC-room path, and Settings presents three task-outcome tabs with legacy aliases.

## Accessibility and responsive evidence

- [`captures/all-routes-a11y-summary.json`](captures/all-routes-a11y-summary.json): 72 route/viewport cells, `total_nodes: 0`, `scan_errors: 0`, and `layout_failures: 0` for WCAG 2 A/AA, WCAG 2.1 A/AA, WCAG 2.2 AA, and axe best-practice rules.
- [`captures/all-routes-reduced-motion-a11y-summary.json`](captures/all-routes-reduced-motion-a11y-summary.json): the same 72 cells under `prefers-reduced-motion`, again with zero nodes, scan errors, or layout failures.
- [`captures/native-zoom-200/zoom-200-evidence.json`](captures/native-zoom-200/zoom-200-evidence.json): all 18 routes at native Chrome page zoom 2.0, observed zoom 2.0, DPR 4, 720px CSS viewport, and no document overflow, clipped controls, clipped narrative text, header collisions, Reference-marker mismatches, Ask duplication, Alt+K failures, or HTTP failures.
- Scroll regions become named keyboard stops only when their measured horizontal or vertical overflow exists. The native-zoom artifact records the resulting names and `tabIndex: 0` on actual scroll owners; `Panel.test.tsx` covers both fit and horizontal-clipping transitions.
- Ask is a labelled region rather than a nested main landmark, retains one accessible utility entry, and consumes available tablet/zoom width. The shell, Ask, skip-target, and landmark contracts are covered by tests and the browser matrices.

## Honesty and action truth

- Live is the default. Only exact `?mode=reference` activates seeded fixtures, and the persistent marker reads `REFERENCE · SEEDED, NOT ISSUER DATA`. Profile, Research, Deep-Dive, Pipeline, Monitor, and seeded Email Intelligence never silently substitute Reference data into live mode.
- Pipeline explicitly presents `24 planned · 0 executed`; planned nodes use planned semantics. Evidence: [`pipeline-mode-reference-1280x900.png`](captures/all-routes/pipeline-mode-reference-1280x900.png).
- Completion is decomposed across execution, persistence, approval, and freshness. No generic success state is used to imply all four axes.
- Upload completion copy derives from actual vaulted/chunk/readiness outcomes, including all-failed, partial, and zero-chunk cases. Renamed action tests cover immediate effect language across issuer creation, thresholds, stress preview, IC entry, intake, and notifications.
- Notifications carry producer-supplied `action_label`; the server uses rolling-compatible `getattr`, and older producers fall back to `Open related item`. Full server verification previously passed 2,592 tests; the notification boundary passed focused server and frontend tests.

## Performance and resource evidence

- [`captures/performance-desktop.json`](captures/performance-desktop.json) contains 18 records, zero scan errors, gzip for every static JS/CSS asset, median/p75 TBT of 0ms, median route-ready 471ms, and p75 route-ready 491.2ms.
- The lightweight first-party Report SVG renderer removed the G2 startup dependency from Report. Reference Report is now 261.3KiB encoded JS (about 267,571B), below the recorded 354,855B production-export baseline by about 87KB / 24.6%. Evidence: [`captures/performance-report-remediation.json`](captures/performance-report-remediation.json).
- Reference Model is the worst readiness/DOM surface at 1,293ms and 3,980 DOM nodes; Portfolio is the largest current startup-JS route at 596.2KiB. These are absolute optimization opportunities, not regressions demonstrated by this remediation.
- Repeated long-task evidence in [`captures/performance-long-task-final.json`](captures/performance-long-task-final.json) records Report at 56–58ms and Model at 54–61ms with browser attribution limited to `unknown/window`. Report's pre-remediation trace was already 58–59ms; Model improved from the current-tree pre-repair 69–73ms. The acceptance predicate prohibits *introduced* >50ms tasks; the evidence does not show an introduced regression.

## Technical quality and regression evidence

- Final frontend: 262 files and 1,829 tests passed.
- `npm run lint`: passed with zero findings.
- `npx tsc --noEmit`: passed.
- `npm run build`: passed; Next.js generated all 20 static pages.
- Impeccable detector over `caos/frontend/src/app` and `caos/frontend/src/components`: `[]`. Its two initial advisory graph-label literals were replaced with `--caos-muted` and `--caos-text`; the focused Query visualization run passed 5/5.
- GitNexus `detect_changes(scope: compare, base_ref: origin/main)` reached the tool's `spawnSync git ENOBUFS` limit in the very large dirty tree. The fallback all-worktree scan completed: 716 changed indexed symbols, 184 files, 46 affected processes, CRITICAL aggregate risk. That result includes unrelated parallel WIP and is not attributable to this remediation alone; no files were staged or committed.

## Known evidence limits

- Long Tasks API attribution remains `unknown/window`; it cannot identify a script or component.
- Historical route baselines use mixed capture boundaries. Only explicit comparable production-export gzip figures are used for regression claims.
- Performance captures use deterministic authenticated local fixtures and production output, not a real network or production database.
- Phone usability is deliberately not scored. Only shared semantic/reflow non-regression is in scope.

