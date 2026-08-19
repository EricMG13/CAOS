# Fallow cleanup log

Static audit of `caos/frontend` (JS/TS) via `fallow 2.101.0`. One pass.
Date: 2026-06-22. Scope: dead-code, duplication, complexity hotspots.

## Result: no unsafe code removed. 3 false positives suppressed, verified clean.

---

## Dead-code — 3 findings, all FALSE POSITIVES (resolved)

All three are real tooling that lives outside the Next.js import graph, so
static analysis can't see the usage. Confirmed with `fallow --trace` before
touching anything (all returned `is_reachable: false` / `import_count: 0`,
i.e. fallow genuinely can't see them — not that they're unused).

| Finding | Proof of real use | Fix applied |
|---|---|---|
| `scripts/a11y-axe.mjs` (unused-file) | The WCAG axe-core harness, run via `node scripts/a11y-axe.mjs`; not imported by app code. | `// fallow-ignore-file unused-file` at top of the file (self-documenting, path-resolution-independent). |
| `axe-core` (unused-dev-dependency) | Loaded by that script via `require.resolve('axe-core/axe.min.js')` — dynamic, untraceable. | Added to `ignoreDependencies` in root `.fallowrc.json`. |
| `eslint-config-next` (unused-dev-dependency) | Pulled in by `compat.extends("next/core-web-vitals","next/typescript")` (FlatCompat string) in `eslint.config.mjs`. | Added to `ignoreDependencies` in root `.fallowrc.json`. |

Per task rule "do not remove exports used dynamically/via reflection without
proof" — proof showed all three ARE used, just invisibly. Suppression (the
fallow-documented fix for false positives), not deletion.

**Verification:** re-ran `fallow dead-code --format json` → `total_issues: 0`.

---

## Duplication — 0.67%, left intentionally (no safe win)

7 clone groups, 14 instances, 123/18,309 lines (0.67%). All tiny (5–17 lines).
Largest (`dup:dd3fc494`, 17 lines) is the shared sub-header scaffold + a 4-line
`useSimRun` setup across `app/command/page.tsx` and `app/monitor/page.tsx` — but
the two pages diverge immediately after the shared prefix. Extracting a shared
component for 2 call-sites at this duplication level is a leaky abstraction, not
a cleanup. **No action** — extracting here would add complexity, not remove it.

Other 6 groups are 5–11 line near-clones inside single files
(`pipeline/views.tsx`, `deepdive` output maps, `reports/ReportDoc.tsx`) — below
any worthwhile-extraction threshold.

---

## Complexity hotspots — 87 over threshold (25 critical / 20 high)

NOT refactored. These are large stateful React components/render functions; the
high CRAP scores are driven by ~zero test coverage (istanbul matched 136/1452
functions), so a safe refactor needs the components under test FIRST. That is
the "requires human domain knowledge / test coverage" stop condition — refactoring
a critical-path render function with no test net would be reckless.

Top 10 critical (by CRAP = complexity × low-coverage penalty):

| File:line | Function | cyc | cog | crap | lines |
|---|---|---|---|---|---|
| src/components/query/GraphCanvas.tsx:168 | NodeMark | 34 | 42 | 1190 | 69 |
| src/app/pipeline/page.tsx:34 | PipelineVisualizer | 33 | 56 | 1122 | 218 |
| src/components/upload/UploadWizard.tsx:56 | UploadWizard | 32 | 58 | 1056 | 370 |
| src/components/model/ModelSheet.tsx:102 | renderCell | 31 | 44 | 992 | 44 |
| src/app/deepdive/page.tsx:62 | DeepDive | 29 | 53 | 870 | 245 |
| src/components/command/SectorReview.tsx:47 | SectorReview | 23 | 34 | 552 | 245 |
| src/components/reports/EvidenceModal.tsx:76 | EvidenceModal | 20 | 25 | 420 | 133 |
| src/components/deepdive/tabs.tsx:351 | ModuleView | 19 | 22 | 380 | 110 |
| src/components/query/GraphCanvas.tsx:253 | legendFor | 16 | 19 | 272 | 22 |
| src/components/command/NlQuery.tsx:49 | Cell | 15 | 13 | 240 | 26 |

Recommended path (human-led, not auto): add component tests for the top 3–5,
then split state/derivation out of the render bodies. Lower CRAP will follow
coverage even before any structural change.

---

## Stop reason

Loop terminated: fallow reports **zero safe-cleanup opportunities** after
suppression (dead-code now clean; duplication too small to extract safely), and
the only remaining work (complexity refactor) requires test coverage + domain
knowledge — both declared stop conditions in the task.
