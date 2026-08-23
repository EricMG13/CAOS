### Task 3: Install the workflow shell, accepted-authority bar, and scoped command palette

**Files:**

- Create: `caos/frontend/src/components/WorkbenchShell.tsx`
- Modify: `caos/frontend/src/components/Workspace.tsx`
- Modify: `caos/frontend/scripts/workbench-smoke.mjs`

- [ ] **Step 1: Extend the failing contract for stale authority and local search**

Add these assertions before implementation:

```js
await page.getByRole("button", { name: /Open command palette/ }).click();
const search = page.getByRole("combobox", { name: "Search commands" });
await search.fill("Northstar");
await page.getByRole("option", { name: /Northstar \/ Workbench QA/ }).waitFor();
await search.fill("src_deadbeef");
await page.getByRole("option", { name: /Open source ID in this case/ }).waitFor();
await search.fill("secret issuer");
await page.getByText("No authorized matches").waitFor();
```

Expected: current dialog and destination rail do not satisfy the contract.

- [ ] **Step 2: Define only the shared shell data shapes**

Move the existing `Snapshot` and `CaseRecord` types from `Workspace.tsx` into `workbench.ts` and export them. Extend, but do not change server semantics:

```ts
export type Snapshot = {
  id: string;
  digest: string;
  accepted_at: string;
  source_set_version?: number | null;
  artifacts: { id: string; module_id: string; digest: string }[];
};

export type SnapshotView = {
  accepted: Snapshot | null;
  latest_accepted: Snapshot | null;
  switch_required: boolean;
  diff?: { changed?: boolean } | null;
};

export type CaseRecord = {
  id: string;
  name: string;
  issuer: string;
  sector: string;
  source_count?: number;
  accepted_snapshot?: Snapshot | null;
  pathway_fit?: { fit: string; message: string };
  current_execution_id?: string | null;
};
```

- [ ] **Step 3: Make selected-case authority explicit and stale-response safe**

In `Workspace`, add `authority`, a request sequence, and a case-change effect. Reuse `request()` unchanged:

```tsx
const [authority, setAuthority] = useState<SnapshotView | null>(null);
const authorityRequest = useRef(0);

const refreshCase = async (id = caseId, signal?: AbortSignal) => {
  if (!id) return;
  const requestId = ++authorityRequest.current;
  try {
    const [detail, snapshot] = await Promise.all([
      request<CaseRecord>(`/api/cases/${id}`, {}, signal),
      request<SnapshotView>(`/api/cases/${id}/snapshot`, {}, signal),
    ]);
    if (requestId !== authorityRequest.current) return;
    setCases((previous) => previous.map((item) => item.id === id ? { ...item, ...detail } : item));
    setAuthority(snapshot);
  } catch (caught) {
    if (requestId !== authorityRequest.current) return;
    if (!(caught instanceof DOMException && caught.name === "AbortError")) {
      setError(caught instanceof Error ? caught.message : "Unable to load case authority");
    }
  }
};

useEffect(() => {
  authorityRequest.current += 1;
  // The visible authority must clear at the external case boundary.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  setAuthority(null);
  if (!caseId) return;
  const controller = new AbortController();
  void refreshCase(caseId, controller.signal);
  return () => controller.abort();
  // `refreshCase` deliberately resolves the current external authority.
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [caseId]);
```

Update the two mutation callers to `await refreshCase(caseId)` after upload or acceptance. In `selectCase`, clear the drawer and authority before setting the new ID so prior-case status never rests under the next case name.

- [ ] **Step 4: Create `WorkbenchShell` with bounded props**

Use this public surface in `caos/frontend/src/components/WorkbenchShell.tsx`:

```tsx
"use client";

import Link from "next/link";
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  CaseRecord,
  Destination,
  SnapshotView,
  evidenceKind,
  withQuery,
  workflowFor,
  workflows,
} from "../lib/workbench";

export type DrawerState =
  | { kind: "qa" }
  | { kind: "sources" }
  | {
      kind: "evidence";
      evidenceId: string;
      source: {
        id: string;
        filename: string;
        sha256: string;
        blocks: { block_id: string; locator: Record<string, unknown>; text?: string }[];
      };
    };

type Props = {
  active: Destination;
  authority: SnapshotView | null;
  cases: CaseRecord[];
  caseId: string;
  drawer: DrawerState | null;
  error: string;
  onCaseChange: (caseId: string) => void;
  onDrawerChange: (drawer: DrawerState | null) => void;
  role: string;
  selectedCase: CaseRecord | null;
  children: ReactNode;
};
```

Implement the default `WorkbenchShell` export against this exact prop contract; keep all network requests in `Workspace` and all shell, palette, and dialog state in this component.

Within that component:

- render exactly six primary links from `workflows` in `<nav aria-label="Workflows">`;
- use `workflowFor(active)` for `aria-current="page"`;
- for Overview, use `/cases` when there is no selected case and `/command-center` otherwise;
- render active workflow tools only, so Run and Review remain visible without restoring the old destination rail;
- keep Admin Studio as a role-gated utility link outside the six workflows;
- preserve `case`, and preserve `run` only for Run Console links;
- put the case selector, accepted date/source-set identity, new-analysis warning, textual `QA unavailable`, source count, and command trigger in `<div role="region" aria-label="Accepted authority">`;
- keep the report `paper` class on the main canvas only.

- [ ] **Step 5: Implement a client-only authorized palette**

Use one `<dialog aria-labelledby="palette-title">` and one input with `role="combobox"`, `aria-controls`, and `aria-expanded`. Results use `role="listbox"` and `role="option"`.

Filter only:

```ts
const caseItems = cases.filter((item) =>
  `${item.issuer} ${item.name} ${item.sector}`.toLowerCase().includes(query.toLowerCase()),
);
const workflowItems = workflows.filter((item) =>
  item.label.toLowerCase().includes(query.toLowerCase()),
);
const exactEvidenceKind = caseId ? evidenceKind(query) : null;
```

Case selection calls `onCaseChange(item.id)` and closes. Workflow items are ordinary `Link`s with visible equivalents in the rail. Exact evidence actions use:

```ts
const evidenceHref = exactEvidenceKind === "source"
  ? withQuery("/sources", { case: caseId, source: query.trim() })
  : withQuery("/sources", { case: caseId, artifact: query.trim() });
```

Do not call a search endpoint, retain query history, or show labels for an unverified identifier.

- [ ] **Step 6: Preserve keyboard behaviour and focus**

- Command/Ctrl+K opens the palette and focuses the search input.
- ArrowDown/ArrowUp moves the active result; Enter activates it; Escape closes.
- The close path returns focus to the palette trigger.
- Every command still exists as a visible link, selector, or evidence-ID path.
- Do not add a keyboard-shortcut dependency.

- [ ] **Step 7: Replace only the shell JSX in `Workspace`**

Delete the old destination rail, topbar, ask dialog, `askQuestion`, `dialogRef`, `ask()`, and its Command/Ctrl+K effect. Keep `renderDestination()` and all current view functions.

Render:

```tsx
return (
  <WorkbenchShell
    active={active}
    authority={authority}
    cases={cases}
    caseId={caseId}
    drawer={drawer}
    error={error}
    onCaseChange={selectCase}
    onDrawerChange={setDrawer}
    role={role}
    selectedCase={selectedCase}
  >
    <div key={`${active}:${caseId}`}>{renderDestination()}</div>
  </WorkbenchShell>
);
```

The key intentionally clears incompatible view-local selection on workflow or case change. The existing Report Studio draft guard still runs before navigation.

- [ ] **Step 8: Run the focused checks**

```bash
cd caos/frontend
npx tsc --noEmit
npm run lint -- --max-warnings=0
npm run test:workbench
```

Expected at this stage: typecheck and lint pass; browser assertions reach the not-yet-built drawer/evidence steps.

- [ ] **Step 9: Commit the shell and palette**

```bash
git add caos/frontend/src/components/WorkbenchShell.tsx caos/frontend/scripts/workbench-smoke.mjs
git add -p -- caos/frontend/src/components/Workspace.tsx caos/frontend/src/lib/workbench.ts
git diff --cached --check
git diff --cached
git commit -m "feat(frontend): add analyst workflow shell"
```

---

