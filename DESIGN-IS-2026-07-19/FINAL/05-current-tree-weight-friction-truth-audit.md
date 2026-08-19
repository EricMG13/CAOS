# Current-tree weight, friction, and truth re-audit

Date: 2026-07-20  
Scope: 18 desktop/tablet routes; phone-specific redesign excluded.  
Verdict: **PASS for the locked remediation acceptance gates.**

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| All routes reach a ready production surface | PASS | `captures/performance-desktop.json`: 18 records, zero scan errors; median 471ms, p75 491.2ms. |
| Static JS/CSS transport compressed | PASS | Every record reports gzip and no uncompressed static assets. |
| Changed-route startup-JS regression | PASS | Reference Report is 261.3KiB (about 267,571B) versus the explicit 354,855B production-export baseline: about −87KB / −24.6%. Command and Model remain within their available recorded comparators. |
| No *introduced* unattributed >50ms task | PASS with attribution limitation | Report repeats at 56–58ms versus a pre-remediation 58–59ms trace; Model repeats at 54–61ms after improving from the current-tree 69–73ms. Neither is demonstrated as introduced. Attribution remains `unknown/window`. |
| Normal WCAG/layout matrix | PASS | 72/72 cells; zero nodes, scan errors, or layout failures. |
| Reduced-motion WCAG/layout matrix | PASS | 72/72 cells; zero nodes, scan errors, or layout failures. |
| Native 200% browser zoom | PASS | 18/18 routes at native/observed 2.0; no overflow, clipping, collision, marker, Ask, shortcut, or HTTP failure. |
| Live/Reference isolation | PASS | Exact-query-only Reference marker and focused route tests; no automatic seeded fallback. |
| Notification action truth | PASS | Producer `action_label`, rolling-compatible backend `getattr`, and `Open related item` fallback. |
| Full frontend quality | PASS | 262 files / 1,829 tests; lint, TypeScript, and production build passed. |

## Startup-JS comparison

The acceptance predicate is conjunctive: a changed route fails only if encoded startup JS increases by both more than 10% and more than 25KB.

| Route | Comparator | Final | Delta | Result |
|---|---:|---:|---:|---|
| Command | 271,700B estimated gzip | 280.5KiB ≈ 287,232B | +15,532B / +5.7% | PASS |
| Model Reference | 304,361B estimated gzip | 298.6KiB ≈ 305,766B | +1,405B / +0.5% | PASS |
| Deep-Dive Reference | 350,256B gzip | current audit remains below the closest post-split comparator | negative | PASS |
| Report Reference | 354,855B gzip | 261.3KiB ≈ 267,571B | −87,284B / −24.6% | PASS |

Report now uses `ReportVisualization.tsx`, a lightweight accessible first-party SVG/table renderer. The workspace G2 visualization remains available elsewhere, but Report no longer imports it on startup.

## Current absolute performance facts

- Route-ready: median 471ms, p75 491.2ms, p95 1,293ms; Reference Model is worst.
- FCP: median 24ms, p75 28ms. LCP: median 104ms, p75 124ms.
- TBT: median 0ms, p75 0ms, p95 21ms.
- Encoded JS: median 280.5KiB, p75 342KiB; Portfolio is worst at 596.2KiB.
- Reference Model: 298.6KiB JS, 3,980 DOM nodes, 24.8MiB heap in the final all-route sample.
- Reference Report: 261.3KiB JS, 1,042 DOM nodes, 8.6MiB heap.

Portfolio's absolute startup weight and Model's initial DOM remain refinement opportunities under Rams principle 9. They are not unclosed findings from the 77-fault remediation register and are not demonstrated regressions introduced by this work.

## Truth and accessibility facts

- Live is the default. `mode=reference` is exact and URL-addressable; context-aware links preserve it.
- The persistent marker states seeded data is not issuer data.
- Profile suppresses unpersisted seeded metrics in live/no-run state.
- Research, Deep-Dive, Pipeline, Monitor, and seeded Email Intelligence isolate Reference fixtures.
- Upload distinguishes ingesting, failed/no vaulted documents, partial vaulting, zero-chunk vaulting, and CP-0 readiness.
- Scroll owners are named/focusable only while content actually clips.
- Normal and reduced-motion all-route matrices are clean, and native zoom proves the shared 720px reflow contract.

## Evidence limits

- Long Tasks API cannot attribute beyond `unknown/window`; this is a telemetry limitation, not hidden causal evidence.
- Historical route baselines use mixed collection boundaries. Only the closest explicit gzip production-export comparator is used for the Report claim.
- The GitNexus `origin/main` compare exceeded its `spawnSync` output buffer in the large dirty tree. The required fallback all-worktree scan completed at CRITICAL aggregate risk but includes unrelated WIP.
- The browser fixtures are deterministic local evidence, not production latency evidence.

## Artifacts

- `captures/performance-desktop.json`
- `captures/performance-report-remediation.json`
- `captures/performance-long-task-final.json`
- `captures/all-routes-a11y-summary.json`
- `captures/all-routes-reduced-motion-a11y-summary.json`
- `captures/native-zoom-200/zoom-200-evidence.json`

