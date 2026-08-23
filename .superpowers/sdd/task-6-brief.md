# Task 6 — Workbench visual polish, reflow, and verification

Implement only Task 6 from `docs/superpowers/plans/2026-08-22-analyst-workbench-foundation.md` (lines 890–1070).

## Scope

- Change `LoadState` only to add the three-bar semantic loading skeleton; preserve explicit error/empty copy and avoid an unused state framework.
- Style the existing Workbench shell to the concrete institutional hierarchy in the plan: 184px rail (desktop), 52–58px authority bar, dominant canvas, native centered palette and fixed non-shrinking 440px max contextual drawer, compact mono chips/selection strip, restrained non-pulsing skeleton. Preserve existing token values, Report Studio paper scope, and the user’s reduced-motion fix.
- Use CSS media queries only for 1100/900/520 reflow rules. No JS viewport hook; page-level horizontal overflow is unacceptable (tables use their existing scroll wrappers).
- Expand existing axe runner to desktop/laptop/reflow contexts for all existing routes, include viewport in violation records, retain one JSON result; do not add another audit tool.
- Add reduced-motion and shared-client case-list request-count checks to the real smoke. Do not mask a client identity failure with cache/storage/global state.
- Use populated real case to capture/inspect screenshots at 1440×1000 and 1024×768 under `outputs/`; do not commit screenshots unless an existing policy requires it.

## Boundaries

- No gradients/glow/icon packages/animated cards/dependencies.
- Preserve user WIP: globals and Workspace require surgical `git add -p`; use apply_patch.
- Before symbols edits, perform GitNexus impact checks and tell parent of HIGH/CRITICAL.
- Do not implement Task 7 reviews; its gates are handled next.

## Verification

- typecheck, lint, production build, complete server suite via viable disposable environment, fresh live smoke, and `npm run a11y` with zero violations across all 27 route/viewport combinations.
- Smoke performance must remain at or below 110% of Task 1 JSON baseline: DCL 58.6ms, FCP 68ms, and linked focus must produce no request. Investigate any excess; do not raise budget.
- Inspect screenshots for hierarchy, authority readability, compact QA/source affordances, and clipping; record observations.

## Delivery

- Commit intended code `style(frontend): polish analyst workbench foundation`; outputs stay uncommitted unless existing project policy dictates otherwise.
- Append `.superpowers/sdd/task-6-report.md` with measurements/screenshots/results/deviations and generate `.superpowers/sdd/review-ea9161d..HEAD.diff` with SHA-256.
