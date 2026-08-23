# Task 5 report

## Commit

`a1afc3a feat(frontend): restore linked evidence chips`

## Changes

- Added a dependency-free `EvidenceChip` that renders the complete raw `src_*` identifier, uses a native button for keyboard activation, exposes local focus/hover preview callbacks, and renders no warning without evidence-level QA data.
- Replaced the artifact evidence count with real chips and rendered the same chip beside each matching authorized source row. Temporary and persistent linked state share `linkedEvidenceId || selectedEvidenceId`; activation opens the existing evidence drawer and Clear removes the persistent selection.
- Added exact `source` query hydration after the active case source set resolves. A case/source ref prevents reopening after the drawer closes; an ID outside the active set fails closed through the existing scoped error state.
- Strengthened the browser contract to require exactly two matching chips and synchronized `.is-linked` state.
- Bounded the smoke harness's intentional authority-503 console error to the interval where its controlled 503 route is active. This fixes a pre-existing false failure without weakening the final assertion for any other console or page error.

No source labels, cross-case search/cache, evidence warnings, citation precision, fetch-on-highlight path, dependency, or Task 6 styling was added.

## Impact

- Pre-edit GitNexus: `Workspace` LOW (0 upstream), `SourcesView` LOW (1 direct / 2 total), and `renderDestination` LOW (1 direct).
- The concrete impact set is `renderDestination → SourcesView`; the existing drawer contract remains owned by `WorkbenchShell`.
- Pre-commit staged detection reported MEDIUM across five broad `Workspace` flows. Its stale line map also named untouched `refreshCases` and `ask`; exact staged inspection contained only source-query state, the Sources route props, `SourcesView`, the new chip, and smoke assertions.

## Verification

| Command / check | Result |
| --- | --- |
| `cd caos/frontend && npx tsc --noEmit` | PASS |
| `cd caos/frontend && npm run lint -- --max-warnings=0` | PASS |
| `cd caos/frontend && npm run build` | PASS; all static routes generated |
| Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | PASS; exact two-chip match, synchronized linked state, drawer contents, focus return, clean console, and reflow all passed |
| Focused exact-source query probe | PASS; authorized raw ID opened once, remained closed after Escape/re-render, and caused zero requests after the initial source-list load |
| Focused invalid-source query probe | PASS; exact active-set error rendered and no evidence dialog opened |
| `git diff --cached --check` | PASS |

The disposable server and venv were reused only for local verification; repository dependencies and server code were not changed.

## Rewrite tournament

**Winner:** Incumbent holds — `caos/frontend/src/components/Workspace.tsx:313-365` (`SourcesView`).

- A speed challenger replaced `evidenceRefs.includes` with another memoized set, adding bookkeeping to a bounded source list while the existing ID map already optimizes the authorization/open path.
- A memory challenger removed the map in favor of repeated linear lookup, reducing one small allocation but weakening activation/query performance and obscuring the active-set boundary.
- A readability challenger extracted one-use chip factories/effects, increasing indirection without reducing state, side effects, or the authorization contract.

Final code:

```tsx
const sourceById = useMemo(() => new Map(sources.map((source) => [source.id, source])), [sources]);
const activeEvidenceId = linkedEvidenceId || selectedEvidenceId;
const openEvidence = (evidenceId: string) => {
  const source = sourceById.get(evidenceId);
  if (!source) {
    setArtifactError(`Evidence ${evidenceId} is not in the active case source set.`);
    return;
  }
  setArtifactError("");
  setSelectedEvidenceId(evidenceId);
  onOpenEvidence(evidenceId, source);
};
```

Verification: `npx tsc --noEmit`, lint, production build, fresh-stack `npm run test:workbench`, exact-source query, and invalid-source probes passed. The sole indexed direct caller (`renderDestination`) compiled and passed the real journey.

## Confidence review — linked evidence chips

Least confident about (ranked):

1. Exact query hydration reopening after the drawer updates parent state.
   - investigated → traced the parent callback rerender and the `${caseId}:${sourceId}` ref gate; a focused live probe opened the drawer, closed it, waited through rerender, and observed no reopen or post-load request.
   - verdict → fine.
   - patch → n/a.
2. An exact source ID escaping the active case boundary.
   - investigated → both activation and query hydration resolve only through the authorized `/api/cases/{case}/sources` result map. A live `src_deadbeef` query rendered the scoped error and no dialog.
   - verdict → fine.
   - patch → n/a.
3. Hover/focus causing network work or losing persistent selection.
   - investigated → preview handlers only set/clear local state; activation separately owns `selectedEvidenceId`. The live journey showed both chips linked on focus, opened the drawer on activation, and returned focus on Escape.
   - verdict → fine.
   - patch → n/a.
4. Selection surviving a case or workflow boundary.
   - investigated → `SourcesView` remains inside the existing `${active}:${caseId}` keyed boundary, so either change unmounts all local linked/selected state; same-case reselection intentionally remains a no-op.
   - verdict → fine.
   - patch → n/a.
5. The intentional 503 authority probe polluting the clean-console assertion.
   - investigated → reproduced on two fresh smoke runs; Chromium reports the controlled 503 as a console error even though the UI correctly handles it.
   - verdict → CONFIRMED test-harness bug.
   - patch → ignore only the exact 503 message while that one controlled failure interval is active; all other console/page errors still fail the journey.

Fixed: deterministic treatment of the intentional 503 probe.

Verified fine: exact active-case lookup, one-shot query opening, local-only linked state, persistent/Clear behavior, raw identifiers, drawer truthfulness, keyboard operation, and case/workflow reset ownership.

By-design: visual hierarchy and chip styling remain Task 6; source-level evidence still carries the existing precision limitation and never invents a block locator.

Still open: none in Task 5 scope.

## Scope and staging

- The commit contains exactly three intended files: `EvidenceChip.tsx`, the Task 5 hunks from `Workspace.tsx`, and `workbench-smoke.mjs`.
- `Workspace.tsx` was staged interactively. Parallel request sequencing, form-reset, Admin, stylesheet, server, test, deployment, and review-log changes remain unstaged.

## 2026-08-22 reviewer follow-up — reactive and truthful source queries

### Commit

`ea9161d fix(frontend): react to source query navigation`

### Resolution

- Added a tiny `useSearchParams` synchronizer inside a local Suspense boundary. The existing `routeSourceId` now follows same-route Next Link changes, so an exact palette source action from the Sources workspace opens the authorized evidence drawer without a reload.
- Added a case-keyed successful-source-list readiness state. Query hydration does not consume its `${case}:${source}` one-shot key until the authorized list has actually resolved; a rejected/invalid response retains the existing load error and a later reload can resolve and open the same query.
- Replaced the broad 503 suppression with an exact controlled URL, exact Chromium message, and one-consumption gate. The journey also asserts that the expected console event was observed; a second or unrelated 503 still fails the final clean-console assertion.
- Added real smoke coverage for same-route palette navigation, no reopen after close, failed-list truthfulness/no drawer, and successful retry.

### Verification

| Command / check | Result |
| --- | --- |
| `npx tsc --noEmit` | PASS |
| `npm run lint -- --max-warnings=0` | PASS |
| `node --check scripts/workbench-smoke.mjs` | PASS |
| `npm run build` | PASS; static routes generated with the local Suspense boundary |
| Fresh-stack `CAOS_URL=http://127.0.0.1:8010 npm run test:workbench` | PASS; complete journey including all three reviewer regressions |
| `git diff --cached --check` | PASS |

The first reviewer-regression run exposed only a test pathname assumption: Next's same-route action correctly navigated to `/sources?...`, while the assertion required `/sources/`. The assertion now normalizes the optional trailing slash; the next fresh run passed.

### Rewrite tournament

**Winner:** Incumbent holds — `SourceQuerySync` plus the explicit `readySourceCaseId` gate.

- Inferring readiness from `!loading && !loadError` loses case ownership and can treat stale source state as current authority.
- Patching `history.pushState` or adding a router wrapper duplicates Next's native reactive search-param contract.
- Folding fetch, query, drawer, and selection state into a reducer adds machinery without removing a branch or request.

Final code:

```tsx
function SourceQuerySync({ onChange }: { onChange: (sourceId: string) => void }) {
  const sourceId = useSearchParams().get("source") || "";
  useEffect(() => onChange(sourceId), [onChange, sourceId]);
  return null;
}

if (!selectedCase || !sourceId || loading || readySourceCaseId !== selectedCase.id) return;
```

Verification: TypeScript, lint, production build, and the full fresh browser journey passed. The indexed impact remains the existing `Workspace → SourcesView` process.

### Confidence review — reviewer corrections

Least confident about (ranked):

1. Same-route Link navigation not updating the source query.
   - investigated → reproduced the original mount-only behavior, replaced it with Next's reactive search params, and clicked the exact source option while already on Sources.
   - verdict → CONFIRMED bug, fixed; the drawer opened at the new raw source URL.
2. A failed source list being mistaken for an authoritative empty list.
   - investigated → forced every source-list response to reject during initial query hydration. The load error remained, no active-set error or drawer appeared, and the same query opened after the route was restored and reloaded.
   - verdict → CONFIRMED bug, fixed with successful case-keyed readiness.
3. Console suppression hiding unrelated server failures.
   - investigated → the old boolean/message-substring filter accepted any simultaneous 503. The replacement requires the exact failed-case URL, exact message, and first occurrence, and asserts consumption.
   - verdict → CONFIRMED test-harness weakness, fixed.
4. Suspense changing the visible shell or static export.
   - investigated → only the invisible query synchronizer is suspended with `null`; the shell is its sibling. The production static build and live journey passed.
   - verdict → fine.

Fixed: reactive same-route palette opening, failure-safe query ownership/retry, and exact console filtering.

Verified fine: static rendering, one-shot close behavior, raw active-set lookup, existing drawer truthfulness, original two-chip synchronization, clean console, and responsive reflow.

By-design: artifact query reactivity and Task 6 styling remain outside this reviewer correction.

Still open: none in Task 5 scope.
