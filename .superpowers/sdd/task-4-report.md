# Task 4 report

## Commit

`c4cff7b feat(frontend): add contextual authority drawers`

## Changes

- Added one controlled native contextual dialog to `WorkbenchShell.tsx`, with opener capture, heading focus, Escape/close handling, next-frame trigger focus restoration, and close-on-null behavior.
- Added truthful QA, source, and evidence drawer bodies. QA uses the required unavailable copy; source metadata is limited to count and accepted source-set version; evidence shows the stable ID, filename, full SHA-256, accepted snapshot/source-set identity, source-level precision limitation, and React-interpolated available text.
- Added cross-case and cross-user direct-object authorization assertions to the existing clean-slate journey. No server or request-helper code changed.
- `Workspace.tsx` required no Task 4 diff: Task 3 already owns the atomic `DrawerState`, clears it before `caseId`, and clears it again at the external case boundary.

## Impact

- Pre-edit GitNexus resolved `Workspace` and the server test at LOW risk. The newer `WorkbenchShell`, `DrawerState`, and `selectCase` symbols remained absent from the stale index and returned UNKNOWN; `rg` found `Workspace` as the sole shell importer and TypeScript verified its contract.
- Pre-commit `detect_changes(scope: staged)` reported LOW risk: two files, one indexed test symbol, zero affected processes.

## Verification

| Command / check | Result |
| --- | --- |
| `cd caos/frontend && npx tsc --noEmit` | PASS |
| `cd caos/frontend && npm run lint -- --max-warnings=0` | PASS |
| `cd caos/frontend && npm run build` | PASS; all static routes generated |
| `cd caos && PYTHONPATH=server /private/tmp/caos-task1-venv/bin/python -m pytest tests/test_clean_slate.py::test_end_to_end_source_run_snapshot_and_stale_boundary -q` | PASS; 1 passed |
| `cd caos && PYTHONPATH=server /private/tmp/caos-task1-venv/bin/python -m pytest tests/test_clean_slate.py -q` | PASS; 28 passed |
| Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | Task 4 GREEN: QA dialog and Escape focus return pass; journey advances to Sources and stops at the intentionally missing Task 5 evidence-chip locator |
| Focused Playwright forced case-switch probe | PASS: source drawer changed from Case A count 1 to Case B count 0, closed on the boundary, and restored focus to the opener |
| `git diff --cached --check` | PASS |

The disposable test environment reused the Task 1 venv after adding the repository's pinned development requirements. No repository environment was modified.

## Rewrite tournament

**Winner:** Incumbent holds, `caos/frontend/src/components/WorkbenchShell.tsx` drawer logic and body rendering.

- Speed challenger memoization added bookkeeping to a bounded three-branch render with no meaningful hot-path reduction.
- Memory challenger deferred block rendering behind another component/state boundary, changing visible behavior and adding allocation rather than removing it.
- Readability challenger extracted a one-use drawer component but required the same authority, case, selection, and focus contracts as props; it increased indirection and file surface.

Final code:

```tsx
useEffect(() => {
  const dialog = drawerRef.current;
  if (!dialog) return;
  if (!drawer) {
    if (dialog.open) dialog.close();
    return;
  }
  if (!dialog.open) {
    drawerTriggerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
  }
  const frame = window.requestAnimationFrame(() => drawerHeadingRef.current?.focus());
  return () => window.cancelAnimationFrame(frame);
}, [drawer]);
```

Verification: TypeScript, lint, production build, full clean-slate suite, live smoke through the Task 4 boundary, and the focused atomicity/focus probe passed. Impact-set re-check: the sole `Workspace` importer compiles and the controlled state path passes live.

## Confidence review — contextual authority drawers

Least confident about (ranked):

1. Close/focus ordering across Escape and case changes.
   - investigated → traced null state through the native dialog `close` event and forced a live case change while the modal was open.
   - verdict → fine; both the contract Escape check and forced case-switch focus probe passed.
   - patch → n/a.
2. Stale drawer contents crossing cases.
   - investigated → `selectCase` clears the drawer before `caseId`; the external case effect also clears it. A live Case A (one source) to Case B (zero sources) probe reopened with only B's count.
   - verdict → fine.
   - patch → n/a.
3. Source text truncation implying completeness.
   - investigated → the drawer deliberately caps rendering at 20 blocks to bound the overlay, but initially omitted that fact.
   - verdict → CONFIRMED bug.
   - patch → added an explicit remaining-block count and full-source action.
4. Fabricated QA or citation precision.
   - investigated → the QA branch contains the exact unavailable statement and never reads run state; the evidence branch uses the exact source-level limitation, shows no locator, and contains no HTML injection path.
   - verdict → fine; exact diff and live QA check verified.
   - patch → n/a.
5. Direct-object authorization assumptions.
   - investigated → new cross-case and outsider checks both return 404 through the existing case authorization boundary.
   - verdict → fine; focused and full server suites passed.
   - patch → n/a.

Fixed: transparent disclosure of the 20-block preview ceiling.

Verified fine: native focus lifecycle, case-atomic drawer state, truthful QA/evidence copy, and existing server authorization.

By-design: right-edge positioning and final visual polish remain in Task 6; this task supplies the `.context-drawer` semantic hook and native modal behavior without touching the user's dirty stylesheet.

Still open: evidence-chip activation is intentionally Task 5; the browser journey stops at that boundary.

## Deviations and limitations

- No `Workspace.tsx` code was added because its Task 4 ownership/clearing contract was already implemented and verified in Task 3. This avoided duplicating state or touching unrelated user WIP.
- The source/evidence drawer does not fetch source titles or infer snapshot QA.
- The contextual drawer's fixed right-edge dimensions are intentionally deferred to Task 6's stylesheet pass.

## 2026-08-22 reviewer fix — unresolved authority semantics

### Commit

`ec4b5b8 fix(frontend): distinguish unresolved authority`

### Changes

- Added an explicit `idle | loading | ready | error` authority lifecycle owned by `Workspace` and passed to the shell.
- Loading and failed case-detail/snapshot requests no longer collapse an unknown source count to `0` or an unknown accepted state to `No accepted…`.
- The source trigger and drawer now say loading/unavailable until authority resolves. The evidence drawer uses the same honest snapshot/source-set identity. The Sources link remains available in every drawer state.
- Added deterministic Playwright barriers for a delayed case-detail response and a fulfilled 503 response. Both assert the drawer contains neither a false numeric zero nor an accepted-absence claim before returning to the normal journey.

### Verification

| Command / check | Result |
| --- | --- |
| `npx tsc --noEmit` | PASS |
| `npm run lint -- --max-warnings=0` | PASS |
| `node --check scripts/workbench-smoke.mjs` | PASS |
| `npm run build` | PASS; all static routes generated |
| Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | Delayed and failed authority assertions PASS; original Task 3/4 journey PASS; expected timeout remains only the Task 5 evidence chip at line 234 |

The already-green full server suite was not rerun because this follow-up changes only client state/presentation and browser coverage.

### Impact, tournament, and confidence review

- Pre-edit GitNexus: `Workspace` LOW/no upstream dependents; `refreshCase` LOW with direct `upload` and `acceptRun` callers. New shell/smoke symbols remained unavailable in the stale index.
- Pre-commit staged detection reported HIGH with six symbols/six flows, but line-shift mapping named nonexistent/untouched `toggleTheme`, `visibleDestinations`, `createCase`, and `acceptRun`. Exact staged inspection confirmed only the authority lifecycle/prop and deterministic smoke; the real `refreshCase` caller set remained unchanged and live-verified.
- Rewrite tournament winner: **Incumbent holds**. A reducer/state-machine challenger added machinery for four linear states; deriving readiness from nullable data recreated the reviewed bug; moving the status into the shell duplicated fetch knowledge. The explicit four-state value is the shortest honest contract.
- Confidence review ranked: (1) stale status after case races — existing request ownership checks prevent foreign completion and the live delayed response passed; (2) failure after previously resolved authority — any failed authority refresh now marks the displayed identity unavailable rather than reusing possibly stale facts; (3) false zero/absence during initial selection — both are withheld by deterministic drawer assertions; (4) staging contamination — exact staged diff excluded the user's request sequencing/form/Admin changes. No open Task 4 defect remains.

## 2026-08-22 reviewer follow-up — same-case reselection

Commit: `6f18695 fix(frontend): preserve authority on same-case selection`

### Resolution

- `selectCase` now returns immediately when the requested case is already the controlled case. A same-case selection no longer clears the resolved authority, opens a false loading lifecycle, closes the contextual drawer, or resets run/error state.
- The workbench smoke reselects the current case through the controlled selector after authority has resolved, waits two animation frames, and verifies the resolved `1 sources` trigger and source drawer remain available with neither loading nor unavailable authority copy.
- The existing delayed-authority and failed-authority checks remain in the same journey and passed alongside the new assertion.

### Verification

| Command / check | Result |
| --- | --- |
| `npm run lint -- --max-warnings=0` | PASS |
| `npx tsc --noEmit` | PASS |
| `node --check scripts/workbench-smoke.mjs` | PASS |
| `npm run build` | PASS; all static routes generated |
| Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | PASS; complete journey, including delayed, failed, same-case, authority-race, QA, evidence, focus-return, and reflow assertions |

### Impact, tournament, and confidence review

- Pre-edit GitNexus could not resolve the nested `selectCase` callback and returned UNKNOWN. Concrete callers are the shell selector, command-palette case result, and Cases table selector; the function signature and changed-case behavior are unchanged.
- Staged `detect_changes` reported MEDIUM across the enclosing `Workspace` flows and also attributed `refreshCases` because the index maps nested edits to broad/stale symbols. Exact staged inspection contained only the one-line guard and the smoke assertion.
- Rewrite tournament skipped: the production edit is a single early-return guard under the skill's trivial-change threshold; the remaining change is test-only.
- Confidence review ranked: (1) stale closure risk — every UI caller receives the callback from the render owning the controlled `caseId`, while new-case creation supplies a distinct ID and still follows the normal transition; (2) accidentally suppressing a desired refresh — same-case selection had no refresh contract and previously left authority permanently loading because the `caseId` effect could not rerun, so no-op is the reviewed behavior; (3) regression coverage missing the transient — the smoke dispatches the selector change, waits two frames, and asserts the drawer stayed open and no loading/unavailable copy appeared; (4) parallel WIP contamination — the committed diff is exactly two files/15 insertions, with unrelated `Workspace` hunks left unstaged. No open Task 4 defect remains.
