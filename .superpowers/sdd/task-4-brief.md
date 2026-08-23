# Task 4 — Contextual authority drawers

Implement only Task 4 from `docs/superpowers/plans/2026-08-22-analyst-workbench-foundation.md` (lines 638–742).

## Scope

- Add the direct-object authorization assertions to `caos/tests/test_clean_slate.py`; do not change server code.
- Add one native, right-side dialog drawer to `WorkbenchShell.tsx`, including trigger focus restoration and a close-on-null state transition.
- In `Workspace.tsx`, own atomic drawer state and clear it before a case change. Wire the existing QA/source/evidence affordances to the drawer.
- QA must state exactly: `No governed snapshot-level QA summary is available.` Never infer a QA result from any other state.
- Sources drawer exposes only the current source count, accepted source-set version, and an Open Sources link; do not fetch/list titles.
- Evidence drawer shows stable ID, filename, full SHA-256, snapshot/source-set identity, and exactly: `Source-level reference; no block locator supplied by this artifact.` Label blocks `Available source text`; use React interpolation only (no `dangerouslySetInnerHTML`).
- Preserve the existing request helper and server API behavior.

## Required safeguards

- Read the frontend guide and relevant source flow before edits; run GitNexus upstream impact before every symbol edit. Warn the parent if it reports HIGH/CRITICAL.
- Preserve all user WIP. `Workspace.tsx` has unrelated unstaged work: stage it with `git add -p` only.
- Use `apply_patch` for file edits.
- No dependencies, no custom focus trap, no fake QA/source precision.
- Native dialog may use semantic HTML/CSS already present; detailed visual polish belongs to Task 6.

## Verification

1. Run the focused/full clean-slate server test through a disposable working virtualenv if the repository venv is broken.
2. Run TypeScript, lint, production build, and live `npm run test:workbench` against the built FastAPI static app. The smoke should now pass drawers and stop only at the Task 5 evidence-chip assertion.
3. Perform a concise confidence check for stale drawer content/focus behavior and report it.

## Delivery

- Commit only intended Task 4 files with message `feat(frontend): add contextual authority drawers` (amend suffix acceptable for needed follow-up).
- Append `.superpowers/sdd/task-4-report.md` with commits, changed files, test results, limitations, and any deviations.
- Produce `.superpowers/sdd/review-3a70e20..HEAD.diff` with the SDD `review-package` helper, including SHA-256.
