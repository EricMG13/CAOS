# Task 5 — Linked evidence chips

Implement only Task 5 from `docs/superpowers/plans/2026-08-22-analyst-workbench-foundation.md` (lines 746–889).

## Scope

- Create the smallest dependency-free `EvidenceChip.tsx` using the exact raw `src_*` evidence ID, keyboard focus/activation, local preview callbacks, and optional warning only for an actual evidence-level QA concern. Do not abbreviate/relabel IDs or add warnings without data.
- Integrate it in `SourcesView` only: same evidence chip in artifact evidence list and alongside matching source row; linked highlighting must use `linkedEvidenceId || selectedEvidenceId` and make no network request.
- Chip activation opens the existing contextual evidence drawer only for a source in the active authorized set; show the existing scoped error otherwise.
- Support source query hydration exactly once for the active case/source pair after the authorized source list loads; no cross-case search/labels/cache.
- Add clearable persistent selection; hover/focus is temporary and remains local to SourcesView. Clear selection on case change/workflow navigation.
- Extend the real browser smoke assertion to require exactly two matching source chips and synchronized `.is-linked` state.

## Safety / quality

- Read source flow first; GitNexus upstream impact before editing each existing symbol. Report HIGH/CRITICAL to parent before editing.
- Preserve unrelated user WIP; `Workspace.tsx` must be staged only with `git add -p`.
- Use `apply_patch`; no new dependency/framework and no fetch for highlighting.
- Keep Task 4 drawer semantics intact (truthful QA/source/evidence state).

## Verification and delivery

- Run `tsc`, lint, production build, and real live `npm run test:workbench`; it should pass all Task 5 checks (Task 6 UI/a11y assertions may still be absent).
- Add concise confidence review, especially query exactness, repeated opening, and local-only linked state.
- Commit intended files as `feat(frontend): restore linked evidence chips`, append `.superpowers/sdd/task-5-report.md`, and build `.superpowers/sdd/review-6f18695f..HEAD.diff` with SHA-256.
