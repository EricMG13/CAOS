# Task 3 report

## Changes

- Added `WorkbenchShell.tsx` with exactly six workflow links, active-workflow tools, role-gated Admin Studio, accepted-authority controls, and the client-only scoped command palette.
- Moved `Snapshot` and `CaseRecord` to the existing `workbench.ts` mapping and added `SnapshotView`; no second workflow map was created.
- Replaced only the legacy shell in `Workspace`, added abortable/sequenced authority refresh, and cleared authority/drawer state at case boundaries. `request()` and server production code were not changed.
- Extended the browser contract for authorized case search, exact source IDs, and unauthorized no-match behavior.

## Impact

- Pre-edit GitNexus: `Workspace` LOW with no upstream dependents; `refreshCase` LOW with two direct callers (`upload`, `acceptRun`) and two affected flows. Newer Task 2/new shell symbols were not resolvable despite refreshing the index, so `rg` and TypeScript were used as the caller-contract fallback.
- Pre-commit `detect_changes(scope: staged)`: HIGH, 11 changed symbols and 8 processes. Review found graph line-range over-attribution inside the `Workspace.tsx` monolith (it named untouched `DeepDive`, `ReportView`, and `approve`). The actual changed execution flow remains the two `refreshCase` callers plus the Workspace shell boundary; both callers compile and the live journey exercises accepted authority.

## Tests and RED/GREEN evidence

| Command | Result |
| --- | --- |
| `cd caos/frontend && npx tsc --noEmit` | PASS |
| `cd caos/frontend && npm run lint -- --max-warnings=0` | PASS |
| `cd caos/frontend && npm run build` | PASS; all static routes generated |
| pre-implementation `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | RED at line 68: missing `navigation[name="Workflows"]` / `Overview` |
| post-implementation same smoke on a fresh in-memory stack | Task 3 GREEN; advanced through workflow, authority, palette, unauthorized-search, and focus assertions; first failure is the Task 4-only `dialog[name="QA details"]` text `/No governed snapshot-level QA summary/` at line 103 |
| focused Playwright route/keyboard check | PASS: 6 workflows; Run href retained `run`; Review omitted `run`; ArrowDown/ArrowUp updated active result; zero console/page errors |
| focused delayed-response case-switch check | PASS: old accepted authority was ignored; next case showed `No accepted snapshot` and no stale `Source set v1` |
| `git diff --cached --check` | PASS |

The disposable uvicorn server was terminated after testing.

## Rewrite tournament

Targets: `WorkbenchShell` and `refreshCase`. Speed and memory challengers proposed flattening palette results; the readability challenger proposed extracting palette subcomponents. All added indirection or changed the exact bounded prop/visible-command contract without measurable benefit. Winner: **Incumbent holds**. The existing code preserves the two-caller refresh signature, authorized inputs, keyboard behavior, and route-scoping invariants. Verification: TypeScript, lint, production build, live smoke, focused keyboard/routes, and delayed-response race all passed to the expected Task 4 boundary.

## Confidence review

Least confident about (ranked):

1. Cross-case stale authority — adversarially delayed the first case's detail/snapshot responses, switched cases, and verified no accepted source-set identity leaked. Verdict: fine.
2. Palette authorization and identifier disclosure — traced inputs to the already-authorized `cases` prop, static workflows, and exact `src_*`/`art_*` syntax; live checks verified generic ID wording and `No authorized matches`. Verdict: fine.
3. Query preservation — inspected generated links and live-verified `case` everywhere and `run` only on Run Console. Verdict: fine.
4. Keyboard/focus semantics — live-verified Cmd/Ctrl+K focus, arrow active-result movement, Escape focus return, and no console errors. Verdict: fine.
5. Parallel WIP contamination — staged interactively and verified the remaining unstaged `Workspace.tsx` diff contains only the pre-existing request sequencing/form/Admin changes. Verdict: fine.

Fixed during review: made case-selector labels distinct from the visible authority label so strict accessible lookup is unambiguous. No confirmed product bugs remain in Task 3 scope.

## Commit

`a7bf2cd feat(frontend): add analyst workflow shell`

## Concerns

- QA and evidence dialogs are intentionally absent until Task 4; the real smoke stops at the first QA-dialog assertion.
- GitNexus still serves stale symbol bodies for `refreshCase` and cannot resolve `WorkbenchShell` even after a successful refresh; its pre-commit HIGH rating is therefore treated as conservative line-shift over-attribution, not ignored.

## 2026-08-22 review fixes

### Changes

- Added a synchronous `caseIdRef` ownership token. Every direct case-state setter updates it before React state; `refreshCase` rejects foreign ownership before incrementing the request sequence and rechecks ownership before committing data or errors. This prevents a completed old-case mutation from superseding the current case refresh.
- Replaced WorkbenchShell's one-time URL-derived run state with the live Workspace `runId` prop. Run Console links now update in the same render as `startRun` updates Workspace state.
- Extended the real smoke with an unaccepted second case, a same-case UI-created run/link assertion, and a delayed acceptance followed by an immediate case switch.

### Impact

- GitNexus pre-edit: `Workspace` LOW/no upstream dependents; `refreshCase` LOW with direct callers `upload` and `acceptRun` across two flows. `WorkbenchShell` remains unresolved by the index; `rg` finds exactly one importer (`Workspace`) and TypeScript verifies the prop contract.

### Focused verification

| Command | Result |
| --- | --- |
| `cd caos/frontend && npx tsc --noEmit` | PASS |
| `cd caos/frontend && npm run lint -- --max-warnings=0` | PASS |
| `cd caos/frontend && npm run build` | PASS |
| fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | New run-link and delayed-mutation ownership regressions PASS; first failure remains Task 4's missing `dialog[name="QA details"]` text at line 148 |

The live log confirms Case B detail/snapshot loaded before delayed Case A acceptance completed and no post-accept Case A detail/snapshot refresh was issued. The temporary server was terminated.

### Rewrite tournament and confidence review

Winner: **Incumbent holds** for the revised `refreshCase`. Speed/memory alternatives merged the ownership and sequence conditions after request creation, which reintroduced the bug by letting an obsolete call invalidate the current request. The readability alternative extracted a generic ownership helper but added indirection for two exact comparisons. The retained preflight ownership check plus post-await ownership/sequence checks is the shortest correct version.

Confidence review ranked: (1) obsolete mutation beginning after case switch, verified by delayed live acceptance; (2) current Case B refresh being invalidated by that obsolete call, verified by absence of a post-accept A refresh and correct B authority; (3) stale Run href after same-case `startRun`, verified against the returned new run ID without reload; (4) initialization/default-case ref synchronization, verified by tracing all three direct `setCaseId` sites and TypeScript/lint/build. No open Task 3 defects remain.

### Follow-up commit

`9fc6997 fix(frontend): bind workbench authority ownership`

Pre-commit GitNexus `detect_changes(scope: staged)` reported HIGH with five changed symbols/seven flows, but included stale/nonexistent `toggleTheme` and untouched `startRun`/`refreshCases` line-range matches. Exact staged-diff inspection confirmed only the reviewed ownership, run prop, and smoke changes; the two real `refreshCase` callers remained the verified impact set.

## 2026-08-22 deterministic race-test follow-up

### Change

- Hardened only `workbench-smoke.mjs`. Once the selector has committed Case B, the smoke records any forbidden Case A detail or snapshot request, waits for the delayed acceptance response body to finish, advances two browser render ticks, verifies Case B remains the visible authority, and asserts that the forbidden request log is empty.
- The response-body and render boundary closes the prior gap where Playwright could observe the POST response before the page handler parsed it and launched a stale `refreshCase(A)`.

### Impact and verification

- GitNexus could not resolve the standalone smoke script as an indexed symbol (`UNKNOWN`, zero graph dependents). Pre-commit `detect_changes(scope: staged)` reported one changed file, zero changed symbols/processes, LOW risk.
- `node --check scripts/workbench-smoke.mjs`: PASS.
- `npx tsc --noEmit`: PASS.
- `npm run lint -- --max-warnings=0`: PASS.
- `npm run build`: PASS.
- Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench`: hardened acceptance/case-ownership gate PASS; first failure remains the expected Task 4 boundary at `dialog[name="QA details"]` line 171. The disposable uvicorn server was terminated.

### Confidence review

- The initial draft used `waitForLoadState("networkidle")`; review identified that the page could already have reached that lifecycle state during navigation. It was replaced with `acceptanceResponse.finished()` plus two animation frames, directly crossing response-body completion and browser task/render boundaries.
- The request observer is enabled before the mutation/switch sequence and starts recording immediately after `selectOption` resolves. The controlled 300 ms acceptance delay ensures Case B commits before the accepted response can resume the page handler. No production check was weakened and no production file changed.
- Rewrite tournament was skipped because this follow-up is test-only instrumentation.

### Commit

`a5bbdc4 test(frontend): harden authority race smoke`

## 2026-08-22 explicit acceptance barrier follow-up

### Change

- Replaced the fixed 300 ms acceptance delay with an explicit two-sided promise barrier.
- The route now completes the real acceptance mutation with `route.fetch()`, holds that preserved response, signals that interception is complete, waits for Case B `selectOption` to commit with forbidden-request tracking active, then releases the unchanged response through `route.fulfill({ response })`.
- Retained response-body completion, double-frame stabilization, Case B authority checks, and the zero-forbidden-Case-A-request assertion.

### Verification and confidence review

- `node --check scripts/workbench-smoke.mjs`: PASS.
- `npm run lint -- --max-warnings=0`: PASS.
- Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench`: explicit held-response barrier and Task 3 ownership assertions PASS; first failure remains the expected Task 4 QA-dialog boundary at line 183. The disposable server was terminated.
- GitNexus pre-edit could not resolve the standalone smoke script (`UNKNOWN`, zero graph dependents); staged `detect_changes` reported one changed file, zero symbols/processes, LOW risk.
- Confidence review rejected an initial request-holding implementation because it delayed the mutation rather than the completed response. The committed implementation uses `route.fetch()` before the barrier and `route.fulfill({ response })` after Case B commits, which reproduces the intended response/handler race without timing assumptions. Resolver assignment is synchronous, and the live smoke proved the click/barrier path does not deadlock.
- Rewrite tournament was skipped because this is test-only instrumentation.

### Commit

`3a70e20 test(frontend): synchronize authority race smoke`
