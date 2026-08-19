# Desktop/tablet remediation ledger

Implementation baseline: `codex/112` at `2228a73`. Support target is desktop
and tablet at `>=768px`, keyboard operation, and real browser zoom at 200%.
Phone-only findings F-012, F-026, F-038, F-053, F-056, F-061, and F-070 are
excluded. For mixed findings, only the desktop/tablet clauses are binding.

| Phase | Findings | Owner / seams | Acceptance evidence | Before / after capture |
|---|---|---|---|---|
| P1 persona + navigation | F-001–F-004, F-016, F-021, F-044, F-072, F-073 | `persona-composition`, `PersonaWorkbench`, nav registry/rail/compact nav, Command, Monitor | Persona composition, role switch, nav, Command and Monitor tests; 18-route × 3-role contract | `captures/before/{route}-{width}.png` → `captures/after/{route}-{width}.png` |
| P2 shared hierarchy + accessibility | F-005–F-011, F-013–F-015, F-018, F-020, F-052, F-058, F-062, F-063 | route metadata, identity, Panel, Ask, Report, evidence registers, shared tokens | route-heading, shell, Panel, action and evidence tests; axe 0 at 1440/1024/768; real 200% check | same matrix plus Report proofing captures |
| P3 truth + reference mode | F-019, F-024–F-030, F-033–F-035, F-040, F-046, F-047, F-054, F-060, F-066–F-069, F-076, F-077 | Profile, Upload, Research, Query, RV, Portfolio, Deep-Dive, Report, Pipeline, Monitor, Settings, notifications | exact label→effect tests; live/reference isolation; upload all-failed/partial/zero-chunk; notification multi-destination | before/after affected routes at 1440/1024 |
| P4 route density + alignment | F-017, F-022, F-023, F-031, F-032, F-036, F-037, F-039, F-041–F-043, F-045, F-048–F-051, F-055, F-057–F-059, F-064, F-065, F-071, F-074, F-075 | all affected routes, Model/IC/Report/Pipeline flagship workbenches | route interaction tests; <=1 page primary; <=5 toolbar actions; Model <=40 visible controls; visual matrix | all affected routes at 1440/1280/1024/768 |
| P5 release gate | all included findings | full frontend and notification API boundary | lint, typecheck, unit/E2E, build, axe, layout/perf harness, design-is and impeccable rescore | archived matrix under `captures/after/` |

## Durable status

### Final closure — 2026-07-20

- [x] All 71 in-scope desktop/tablet, shared-accessibility, persona, and truth-contract obligations in the approved register are closed. Mixed findings close only their desktop/tablet/shared clauses.
- [x] Phone-only F-012, F-026, F-038, F-053, F-056, F-061, and F-070 remain excluded; phone clauses of F-022, F-023, F-048, and F-065 remain excluded.
- [x] Final normal-motion axe/layout matrix: 18 routes × 4 viewports, zero nodes, scan errors, or layout failures.
- [x] Final reduced-motion axe/layout matrix: 18 routes × 4 viewports, zero nodes, scan errors, or layout failures.
- [x] Native Chrome 200% zoom: 18 routes, observed 2.0×, zero clipping/overflow/collision/Ask/marker/HTTP failures.
- [x] Final frontend verification: 262 files / 1,829 tests; lint, TypeScript, and production build pass.
- [x] Full server suite previously passed 2,592 tests in `.venv311`; notification compatibility boundary remains covered.
- [x] Startup-JS regression gate passes after Report's lightweight visualization repair; Report is 261.3KiB versus the recorded 354,855B comparator.
- [x] Impeccable detector final output is `[]`; Rams 26/30; Nielsen 39/40; Impeccable technical audit 19/20.
- [x] No staging or commit performed; unrelated dirty-tree changes preserved.

- [x] Scope locked and phone exclusions recorded.
- [x] GitNexus impact run for the initial shared hubs; CRITICAL blast radius
  disclosed before edits.
- [x] Implementation-architecture red-team gate recorded.
- [x] P1 persona + navigation reviewed and verified (62 focused tests, TypeScript,
  scoped lint, six desktop/tablet axe scans, and independent re-review clean).
- [x] P2A shared hierarchy/accessibility foundation reviewed and verified (155
  focused/regression tests plus Research heading edge, scope-wide color gate,
  9 axe scans, and real headed-Chrome 200% zoom on Report/Command/Settings).
- [x] P2 shared hierarchy + accessibility reviewed and verified (typed actions,
  orthogonal completion, evidence selection, 9-cell axe, and all independent
  re-reviews clean; final release gate will recalibrate native 200% after P4).
- [x] P3A explicit live/reference boundary verified for the shared shell,
  Profile, Research, and Deep-Dive (76 focused tests, 68 prior-shell
  regressions, real Next-link/direct-URL round trip, TypeScript, changed-file
  lint, scoped GitNexus audit, 18 initial live/reference axe/layout scans, and
  12 affected repair scans at 1440/1024/768). Profile live/no-run hides all
  unpersisted analytical values; Reference mode is exact-query-only; late
  Research completions and live-run Deep-Dive state cannot cross the boundary.
- [x] P3 truth + reference mode reviewed and verified (Tasks 3A–3C; explicit URL mode, no silent seeded fallback, runtime-isolated Pipeline/Monitor references, outcome-derived Upload states, exact action effects, producer-owned notification labels, and all independent re-reviews clean).
- [x] P4 Task 4A cold-state and route-control slice reviewed and verified
  (F-017, F-022, F-023, F-031, F-032, F-036, F-037, F-039,
  F-041–F-043, F-045, F-048–F-050; 144 focused tests, TypeScript,
  changed-file lint, production build, 32-cell axe/layout matrix plus the
  8-cell reviewer rerun, retained open-menu geometry harness, and native
  headed-Chromium 200% Portfolio/Sector checks). Evidence:
  `.superpowers/sdd/caos-remediation-task-4a-report.md`.
- [x] P4 Task 4B flagship analyst-workbench slice reviewed and verified
  (F-051, F-055, F-057–F-059, F-064; 118 focused tests, 16-cell primary
  matrix, 8-cell populated keyboard matrix, reduced-motion rerun, production
  build, and native 200% Deep-Dive/Model/IC Book/Report checks). Evidence:
  `.superpowers/sdd/caos-remediation-task-4b-report.md`.
- [x] P4 Task 4C Pipeline/Monitor/Settings slice implemented and verified for
  desktop/tablet (F-065 desktop/tablet clause, F-071, F-074, F-075; 1,825
  frontend tests, 12 populated browser cells, 3 reduced-motion cells, native
  200% checks on all three routes, coarse-phone Ask smoke, and zero captured
  HTTP failures). Evidence:
  `.superpowers/sdd/caos-remediation-task-4c-report.md` and
  `captures/after/task4c-*.json`.
- [x] P4 route density + alignment reviewed and verified. Tasks 4A–4C all have
  clean independent re-reviews; P5 full verification and re-audit remains.
- [ ] P5 full verification and re-audit complete.

## Preserve boundary

- One shared authority and permission model across Analyst, PM, and QA.
- DecisionHeader, evidence identifiers, context URLs, immutable publish gates,
  dark terminal tokens, paper output identity, tabular numerics, focus recovery,
  and reduced-motion behavior remain intact.
- Existing uncommitted user work is preserved; staging, if requested later, is
  explicit-path only.
