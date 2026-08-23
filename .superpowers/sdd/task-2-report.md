# Task 2 — Centralize the workflow map

## Implementation

- Added `caos/frontend/src/lib/workbench.ts` as the sole shared workflow and route configuration, including destination parsing, workflow lookup, query propagation, and evidence-ID classification.
- Replaced App Router slug casing with `destinationFromSlug` and `routeDestinations`; all nine existing route slugs remain statically generated.
- Removed the local `Destination`, destination route list, and `withQuery` from `Workspace`; its legacy grouped navigation is derived from the canonical route tuples, preserving URLs and the ADMIN visibility rule.
- Added the specified `/cases/`, `/run-console/`, and `/report-studio/` active-workflow checks to the browser contract. No workflow rail or shell was implemented.

## Files

- `caos/frontend/src/lib/workbench.ts` — new canonical workflow/route module.
- `caos/frontend/app/[destination]/page.tsx` — canonical slug-to-destination parsing.
- `caos/frontend/src/components/Workspace.tsx` — uses the shared destination type and query helper; only Task 2 hunks staged.
- `caos/frontend/scripts/workbench-smoke.mjs` — route/active-workflow contract extensions.

## TDD evidence

- RED: added the specified browser assertions before production edits. `npm run test:workbench` could not reach the local service in this environment: sandboxed execution failed with `connect EPERM 127.0.0.1:8000`; the approved retry reached the socket but failed with `socket hang up` on `POST /api/cases`. The intended existing red condition remains the absent `navigation[aria-label="Workflows"]`; this task deliberately does not render it.
- GREEN: `npx tsc --noEmit` exited 0.
- GREEN: `npm run lint -- --max-warnings=0` exited 0.
- GREEN: a focused Node assertion check exercised known and unknown slug parsing, workflow selection, query replacement/deletion, and source/artifact ID classification.

## GitNexus impact

GitNexus was refreshed before edits. Upstream impact for `generateStaticParams`, `DestinationPage`, and `Workspace` was LOW: zero direct callers, zero affected processes, zero affected modules. `generateMetadata` was not indexed, so its change was verified through TypeScript. Pre-commit `detect_changes(scope: staged)` reported the four intended files and a MEDIUM route/workspace surface: Workspace → EmptyState/CasesView/SourcesView/RunConsole plus Timer → Request. The latter reflects unrelated unstaged Workspace work; the cached diff contains no `refreshCases` changes.

## Rewrite tournament and confidence review

Rewrite tournament (inline, per the no-subagent constraint): incumbent holds for the exact required `workbench.ts` contracts. A shorter alternative would either duplicate route labels or obscure the explicit workflow mapping; a helper abstraction would add a second configuration layer. Type signatures and URL outputs remain unchanged at their callers.

Least-confidence review:

1. Legacy route preservation — verified every prior slug is present in `routeDestinations`; `destinationFromSlug` retains the former unknown-slug fallback to `Cases`.
2. Query semantics — verified empty values are deleted and existing values are retained/replaced using `URLSearchParams`, matching the removed helper's behavior.
3. Workspace parallel changes — verified the cached `Workspace.tsx` diff contains only imports, shared route derivation, and prop typing; all pre-existing request/race and form changes remain unstaged.
4. Browser test placement — the new assertions are intentionally unreachable until Task 3 supplies the absent rail, preserving the planned RED contract rather than papering it over.

No confirmed defects found; no server production code or `request()` changed.

## Commit

`126b4ba refactor(frontend): centralize workflow routing`

## Concerns

The end-to-end smoke suite could not run against the currently available local service because its API connection hung. Re-run it with a healthy CAOS stack; it should remain red specifically at the missing workflow rail until the shell task lands.
