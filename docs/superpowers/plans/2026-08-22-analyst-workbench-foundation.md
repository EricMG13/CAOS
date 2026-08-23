# Analyst Workbench Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the destination-led chrome with a fast, case-scoped Analyst Workbench foundation so an analyst can navigate by workflow, confirm the accepted authority, and reach QA or evidence without losing the main reading canvas.

**Architecture:** Keep `Workspace` as the existing data and workflow coordinator, move only application-shell concerns into one client component, and centralize the six-workflow mapping in one dependency-free module shared by routing and navigation. Reuse the existing authorized case, snapshot, artifact, and source routes. Keep linked evidence state local to `SourcesView`; use one global native-dialog drawer owned by the shell. Do not alter the shared `request()` helper or any server response contract in this phase.

**Tech Stack:** Next.js 16 static App Router, React 19, TypeScript 5.8, native `<dialog>`, CSS, Playwright 1.61, axe-core, FastAPI contract tests.

## Global Constraints

- Implement only rollout phase 1, **Foundation**. Overview/Sources content redesign, Deep-Dive charts, Compare, Model, Publish, and consolidation require later plans.
- Preserve every existing URL. The workflow rail may point to existing routes, but do not add pretend redirects before each workflow has a real canonical surface.
- Search only the `/api/cases` result already authorized for the current identity. Until the issuer registry ships, issuer matches are labels on visible case results, not a separate issuer search authority.
- An exact `src_*` or `art_*` palette query may open the current case's authorized Sources route. Never enumerate, label, or cache evidence from another scope.
- Display `QA unavailable` until a governed snapshot-level QA summary exists. Do not infer `Passed` from run success, CP-5 presence, confidence, or artifact status.
- Current artifact evidence references identify source objects, not exact blocks. The drawer must say `Source-level reference; no block locator supplied by this artifact.` and must not present the first block as the cited excerpt.
- Do not change `request()`. GitNexus reports **CRITICAL** upstream impact: 11 direct callers, 15 affected symbols, and seven execution flows. `renderDestination`, `refreshCase`, and `SourcesView` are LOW risk.
- Preserve the user's existing unstaged edits in `Workspace.tsx`, `globals.css`, and the rest of the dirty worktree. Inspect diffs before each edit and use partial staging for overlapping files.
- Performance targets, measured before and after against the same local build and fixture:
  - no more than 10% regression in initial `domContentLoadedEventEnd` or first-contentful-paint;
  - workflow navigation while the `Workspace` client instance is preserved makes zero additional `/api/cases` requests;
  - evidence hover/focus highlighting is synchronous and performs no network request;
  - the drawer request, when needed, does not block or replace the main canvas.
- Accessibility release gate: zero axe violations at 1440×1000, 1024×768, and 720×900; keyboard-only palette, rail, chips, and drawers; visible focus; Escape close and trigger-focus return; usable reflow at an effective 200% zoom.

---

## File and Responsibility Map

**Create**

- `caos/frontend/src/lib/workbench.ts` — destination/workflow types, six-workflow configuration, route parsing, query preservation, and exact evidence-ID classification.
- `caos/frontend/src/components/WorkbenchShell.tsx` — workflow rail, authority bar, command palette, QA/source/evidence drawer, focus restoration, and main-canvas frame.
- `caos/frontend/src/components/EvidenceChip.tsx` — compact legacy chip semantics and local matching-ID preview callbacks.
- `caos/frontend/scripts/workbench-smoke.mjs` — one real browser contract covering navigation, authority, palette, drawer, evidence, reflow, and performance logging.

**Modify**

- `caos/frontend/src/components/Workspace.tsx` — import shared types/config, load selected-case authority safely, coordinate drawer state, and pass existing views through the new shell.
- `caos/frontend/app/[destination]/page.tsx` — reuse the route-to-destination parser instead of duplicating label rules.
- `caos/frontend/app/globals.css` — institutional shell, overlay drawer, command palette, evidence-chip, linked-state, skeleton, and responsive styles.
- `caos/frontend/scripts/a11y-axe.mjs` — exercise desktop, laptop, and narrow/reflow viewports.
- `caos/frontend/package.json` — expose the focused browser contract as `test:workbench`.
- `caos/tests/test_clean_slate.py` — pin the existing cross-case artifact authorization behaviour used by exact palette lookups.

**Do not modify**

- `caos/server/caos/http.py`, `caos/server/caos/workflows/domain.py`, or other server production code.
- Existing analytical view logic beyond the minimum `SourcesView` evidence-chip adoption and shared loading-state presentation.
- The Report Studio paper hierarchy or model authority semantics.

---

### Task 1: Capture the baseline and add the failing workbench browser contract

**Files:**

- Create: `caos/frontend/scripts/workbench-smoke.mjs`
- Modify: `caos/frontend/package.json`

- [ ] **Step 1: Verify the current build and launch the combined application**

Run from the repository root:

```bash
cd caos/frontend
npm run lint -- --max-warnings=0
npx tsc --noEmit
npm run build
cd ..
mkdir -p server/static
cp -R frontend/out/. server/static/.
PYTHONPATH=server .venv/bin/python server/run.py
```

Keep the final process running in its own terminal. Expected: `Uvicorn running on http://0.0.0.0:8000`.

- [ ] **Step 2: Measure the unchanged shell before adding assertions**

Run this from `caos/frontend`:

```bash
node --input-type=module -e 'import { chromium } from "playwright"; const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:1440,height:1000}}); let caseRequests=0; page.on("request", request => { if (new URL(request.url()).pathname === "/api/cases") caseRequests += 1; }); await page.goto("http://127.0.0.1:8000/cases/", {waitUntil:"networkidle"}); const timing=await page.evaluate(() => { const navigation=performance.getEntriesByType("navigation")[0]; const paint=performance.getEntriesByName("first-contentful-paint")[0]; return {domContentLoaded: navigation?.domContentLoadedEventEnd ?? null, firstContentfulPaint: paint?.startTime ?? null}; }); console.log(JSON.stringify({...timing,caseRequests})); await browser.close();'
```

Record the JSON in the Task 1 commit message. Use these numbers for the 10% comparison in Task 6; do not invent a universal millisecond threshold.

- [ ] **Step 3: Add the focused browser command**

Add this script entry to `caos/frontend/package.json`:

```json
"test:workbench": "node scripts/workbench-smoke.mjs"
```

- [ ] **Step 4: Write the failing browser contract**

Create `caos/frontend/scripts/workbench-smoke.mjs` with one fixture and one browser journey. Use the existing Playwright dependency—add no test framework.

```js
import assert from "node:assert/strict";
import { chromium, request } from "playwright";

const baseURL = process.env.CAOS_URL || "http://127.0.0.1:8000";
const api = await request.newContext({ baseURL });
const created = await api.post("/api/cases", {
  data: { name: "Workbench QA", issuer: "Northstar", sector: "Services" },
});
assert.equal(created.status(), 201);
const caseRecord = await created.json();
const upload = await api.post(`/api/cases/${caseRecord.id}/sources`, {
  multipart: {
    file: {
      name: "earnings.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Revenue 1,160\nEBITDA 222"),
    },
  },
});
assert.equal(upload.status(), 201);
const source = await upload.json();
const started = await api.post(`/api/cases/${caseRecord.id}/runs`, {
  data: { pathway: "EARNINGS_UPDATE", depth: "screen", focus_questions: [] },
});
assert.equal(started.status(), 202);
const run = await started.json();
let runState;
for (let attempt = 0; attempt < 60; attempt += 1) {
  const response = await api.get(`/api/runs/${run.id}`);
  runState = await response.json();
  if (runState.status === "succeeded") break;
  await new Promise((resolve) => setTimeout(resolve, 50));
}
assert.equal(runState?.status, "succeeded");
const acceptedResponse = await api.post(`/api/runs/${run.id}/accept`);
assert.equal(acceptedResponse.status(), 200);
const accepted = await acceptedResponse.json();
const artifact = accepted.artifacts.find((item) => item.module_id === "CP-0");
assert.ok(artifact);

const browser = await chromium.launch({ headless: true });
const errors = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  let caseRequests = 0;
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (requestValue) => {
    if (new URL(requestValue.url()).pathname === "/api/cases") caseRequests += 1;
  });

  await page.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  const timing = await page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0];
    const paint = performance.getEntriesByName("first-contentful-paint")[0];
    return {
      domContentLoaded: navigation?.domContentLoadedEventEnd ?? null,
      firstContentfulPaint: paint?.startTime ?? null,
    };
  });
  console.log(JSON.stringify({ timing, caseRequests }));

  const workflows = ["Overview", "Sources", "Analyse", "Compare", "Model", "Publish"];
  for (const label of workflows) {
    await page.getByRole("navigation", { name: "Workflows" }).getByRole("link", { name: label, exact: true }).waitFor();
  }
  await page.getByRole("region", { name: "Accepted authority" }).getByText("Northstar / Workbench QA").waitFor();
  await page.getByRole("region", { name: "Accepted authority" }).getByText(/Source set v1/).waitFor();
  await page.getByRole("button", { name: /QA unavailable/ }).waitFor();

  const paletteTrigger = page.getByRole("button", { name: /Open command palette/ });
  await paletteTrigger.focus();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  const palette = page.getByRole("dialog", { name: "Command palette" });
  await palette.getByRole("combobox", { name: "Search commands" }).fill("Northstar");
  await palette.getByRole("option", { name: /Northstar \/ Workbench QA/ }).waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => paletteTrigger.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the palette trigger");
  }));

  const qaTrigger = page.getByRole("button", { name: /QA unavailable/ });
  await qaTrigger.click();
  await page.getByRole("dialog", { name: "QA details" }).getByText(/No governed snapshot-level QA summary/).waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => qaTrigger.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the QA trigger");
  }));

  await page.goto(`${baseURL}/sources/?case=${caseRecord.id}&artifact=${artifact.id}`, { waitUntil: "networkidle" });
  const chip = page.locator(`[data-evidence-id="${source.id}"]`).first();
  await chip.focus();
  await assert.doesNotReject(() => chip.evaluate((element) => {
    if (!element.classList.contains("is-linked")) throw new Error("focused evidence was not linked");
  }));
  await chip.click();
  const evidence = page.getByRole("dialog", { name: `Evidence ${source.id}` });
  await evidence.getByText("earnings.txt").waitFor();
  await evidence.getByText(/Source-level reference; no block locator supplied/).waitFor();
  await evidence.getByRole("link", { name: "Open full source" }).waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => chip.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the evidence trigger");
  }));

  await page.setViewportSize({ width: 720, height: 900 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  assert.equal(overflow, false, "workbench causes page-level horizontal overflow at reflow width");
  assert.deepEqual(errors, []);
  await context.close();
} finally {
  await browser.close();
  await api.dispose();
}
```

- [ ] **Step 5: Run the contract and confirm the intended failure**

```bash
cd caos/frontend
npm run test:workbench
```

Expected: failure at `navigation[name="Workflows"]`; the current shell exposes destination groups instead.

- [ ] **Step 6: Commit only the new check**

```bash
git add caos/frontend/package.json caos/frontend/scripts/workbench-smoke.mjs
git diff --cached --check
git commit -m "test(frontend): define analyst workbench contract"
```

---

### Task 2: Centralize the workflow map without breaking existing routes

**Files:**

- Create: `caos/frontend/src/lib/workbench.ts`
- Modify: `caos/frontend/app/[destination]/page.tsx`
- Modify: `caos/frontend/src/components/Workspace.tsx`

- [ ] **Step 1: Pin route parsing in the browser contract**

Before production edits, add visits for `/cases/`, `/run-console/`, and `/report-studio/` to `workbench-smoke.mjs`; assert that each renders and the expected workflow link has `aria-current="page"`:

```js
for (const [route, workflow] of [
  ["/cases/", "Overview"],
  ["/run-console/", "Analyse"],
  ["/report-studio/", "Publish"],
]) {
  await page.goto(`${baseURL}${route}?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  await page.getByRole("navigation", { name: "Workflows" })
    .getByRole("link", { name: workflow, exact: true })
    .evaluate((element) => {
      if (element.getAttribute("aria-current") !== "page") throw new Error("workflow is not active");
    });
}
```

Run `npm run test:workbench`; expected failure remains the missing workflow rail.

- [ ] **Step 2: Add one dependency-free workflow module**

Create `caos/frontend/src/lib/workbench.ts`:

```ts
export const routeDestinations = [
  ["cases", "Cases"],
  ["sources", "Sources"],
  ["run-console", "Run Console"],
  ["deep-dive", "Deep-Dive"],
  ["rv-screener", "RV Screener"],
  ["command-center", "Command Center"],
  ["model-builder", "Model Builder"],
  ["report-studio", "Report Studio"],
  ["admin-studio", "Admin Studio"],
] as const;

export type Destination = (typeof routeDestinations)[number][1];
export type WorkflowId = "overview" | "sources" | "analyse" | "compare" | "model" | "publish";

export type Workflow = {
  id: WorkflowId;
  label: string;
  href: string;
  destinations: readonly Destination[];
  tools?: readonly { label: string; href: string; destination: Destination }[];
};

export const workflows: readonly Workflow[] = [
  { id: "overview", label: "Overview", href: "/command-center", destinations: ["Cases", "Command Center"], tools: [{ label: "Case register", href: "/cases", destination: "Cases" }] },
  { id: "sources", label: "Sources", href: "/sources", destinations: ["Sources"] },
  { id: "analyse", label: "Analyse", href: "/deep-dive", destinations: ["Run Console", "Deep-Dive"], tools: [{ label: "Run", href: "/run-console", destination: "Run Console" }, { label: "Review", href: "/deep-dive", destination: "Deep-Dive" }] },
  { id: "compare", label: "Compare", href: "/rv-screener", destinations: ["RV Screener"] },
  { id: "model", label: "Model", href: "/model-builder", destinations: ["Model Builder"] },
  { id: "publish", label: "Publish", href: "/report-studio", destinations: ["Report Studio"] },
];

export function destinationFromSlug(slug: string): Destination {
  return routeDestinations.find(([route]) => route === slug)?.[1] ?? "Cases";
}

export function workflowFor(destination: Destination): Workflow {
  return workflows.find((workflow) => workflow.destinations.includes(destination)) ?? workflows[0];
}

export function withQuery(path: string, values: Record<string, string | undefined>) {
  const [pathname, rawQuery] = path.split("?");
  const query = new URLSearchParams(rawQuery);
  for (const [key, value] of Object.entries(values)) {
    if (value) query.set(key, value);
    else query.delete(key);
  }
  return `${pathname}${query.size ? `?${query}` : ""}`;
}

export function evidenceKind(value: string): "source" | "artifact" | null {
  const id = value.trim();
  if (/^src_[a-zA-Z0-9]+$/.test(id)) return "source";
  if (/^art_[a-zA-Z0-9]+$/.test(id)) return "artifact";
  return null;
}
```

This is the only workflow configuration. Do not add a second palette or route map.

- [ ] **Step 3: Reuse route parsing in the App Router page**

Replace duplicated label casing in `caos/frontend/app/[destination]/page.tsx` with:

```tsx
import type { Metadata } from "next";
import Workspace from "../../src/components/Workspace";
import { destinationFromSlug, routeDestinations } from "../../src/lib/workbench";

export function generateStaticParams() {
  return routeDestinations.map(([destination]) => ({ destination }));
}

export async function generateMetadata({ params }: { params: Promise<{ destination: string }> }): Promise<Metadata> {
  const { destination } = await params;
  return { title: `CAOS — ${destinationFromSlug(destination)}` };
}

export default async function DestinationPage({ params }: { params: Promise<{ destination: string }> }) {
  const { destination } = await params;
  return <Workspace destination={destinationFromSlug(destination)} />;
}
```

- [ ] **Step 4: Point `Workspace` at the shared types and helpers**

In `Workspace.tsx`, remove the local `Destination`, `destinations`, and `withQuery` declarations. Import:

```ts
import { Destination, withQuery } from "../lib/workbench";
```

Change the component prop to `{ destination: Destination }` and use `const active = destination`. Keep `pathways`; it describes analytical execution, not navigation.

- [ ] **Step 5: Verify parsing and type safety**

```bash
cd caos/frontend
npx tsc --noEmit
npm run lint -- --max-warnings=0
```

Expected: both commands exit 0. `npm run test:workbench` still fails only because the new shell is not rendered.

- [ ] **Step 6: Commit the workflow boundary**

Because `Workspace.tsx` already contains user changes, stage its import/config hunk interactively and inspect it:

```bash
git add caos/frontend/src/lib/workbench.ts 'caos/frontend/app/[destination]/page.tsx'
git add -p -- caos/frontend/src/components/Workspace.tsx
git diff --cached --check
git diff --cached
git commit -m "refactor(frontend): centralize workflow routing"
```

---

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

### Task 4: Add contextual drawers without fabricating QA or source precision

**Files:**

- Modify: `caos/frontend/src/components/WorkbenchShell.tsx`
- Modify: `caos/frontend/src/components/Workspace.tsx`
- Modify: `caos/tests/test_clean_slate.py`

- [ ] **Step 1: Pin direct-object protection used by the palette**

In `test_end_to_end_source_run_snapshot_and_stale_boundary`, immediately after locating `cp0`, add:

```py
        other_case_id = client.post(
            "/api/cases",
            json={"name": "Other", "issuer": "Other issuer", "sector": "Other"},
        ).json()["id"]
        assert client.get(f"/api/cases/{other_case_id}/artifacts/{cp0['id']}").status_code == 404
        assert client.get(
            f"/api/cases/{case_id}/artifacts/{cp0['id']}",
            headers={"x-forwarded-user": "outsider"},
        ).status_code == 404
```

Run:

```bash
cd caos
.venv/bin/python -m pytest tests/test_clean_slate.py::test_end_to_end_source_run_snapshot_and_stale_boundary -q
```

Expected: pass. This verifies existing authorization; no server edit is needed.

- [ ] **Step 2: Implement one global right-side native dialog**

In `WorkbenchShell`, keep a ref to the drawer dialog and the element that opened it. When `drawer` becomes non-null, store `document.activeElement`, call `showModal()`, and focus the drawer heading. On `close`, call `onDrawerChange(null)` and return focus on the next animation frame.

Use one dialog:

```tsx
<dialog
  className="context-drawer"
  ref={drawerRef}
  aria-labelledby="drawer-title"
  onClose={closeDrawer}
>
  <div className="drawer-header">
    <div>
      <span className="eyebrow">CONTEXT</span>
      <h2 id="drawer-title" tabIndex={-1}>{drawerTitle}</h2>
    </div>
    <button className="button small" type="button" onClick={() => drawerRef.current?.close()}>Close</button>
  </div>
  <div className="drawer-body">{drawerBody}</div>
</dialog>
```

Do not implement a custom focus trap; native modal dialog behaviour covers containment.

- [ ] **Step 3: Render honest QA and source summaries**

For `{ kind: "qa" }`, render:

```tsx
<div className="state-block unavailable">
  <strong>No governed snapshot-level QA summary is available.</strong>
  <p>Run and artifact status are not substituted for QA. Review module exceptions in Analyse.</p>
  <Link className="button small" href={withQuery("/run-console", { case: caseId })}>Open Run Console</Link>
</div>
```

For `{ kind: "sources" }`, show the current source count, accepted source-set version, and an `Open Sources` link. Do not fetch or list source titles in the shell.

For `{ kind: "evidence" }`, show the stable identifier, filename, full SHA-256, snapshot/source-set identity, and this required limitation:

```tsx
<p className="status warning">Source-level reference; no block locator supplied by this artifact.</p>
```

Label extracted blocks `Available source text`, not `Cited excerpt`. Render text only with React interpolation; never use `dangerouslySetInnerHTML`.

- [ ] **Step 4: Keep drawer content atomic across case changes**

`selectCase()` must call `setDrawer(null)` before changing `caseId`. `WorkbenchShell` must also close the dialog if `drawer` becomes null. Never retain an evidence object's source data after the case changes.

- [ ] **Step 5: Run the server and browser checks**

```bash
cd caos
.venv/bin/python -m pytest tests/test_clean_slate.py -q
cd frontend
npm run test:workbench
```

Expected: server suite passes; browser contract reaches the missing evidence-chip assertion.

- [ ] **Step 6: Commit the drawer boundary**

```bash
git add caos/frontend/src/components/WorkbenchShell.tsx caos/tests/test_clean_slate.py
git add -p -- caos/frontend/src/components/Workspace.tsx
git diff --cached --check
git diff --cached
git commit -m "feat(frontend): add contextual authority drawers"
```

---

### Task 5: Carry legacy evidence chips and linked focus into real artifact review

**Files:**

- Create: `caos/frontend/src/components/EvidenceChip.tsx`
- Modify: `caos/frontend/src/components/Workspace.tsx`
- Modify: `caos/frontend/scripts/workbench-smoke.mjs`

- [ ] **Step 1: Add the matching-ID check before implementation**

The artifact view will show the same cited source in the artifact evidence list and beside the matching source row. Assert that both real chips synchronize:

```js
const matching = page.locator(`[data-evidence-id="${source.id}"]`);
assert.equal(await matching.count(), 2);
await matching.first().focus();
await page.waitForFunction((evidenceId) => {
  const nodes = [...document.querySelectorAll(`[data-evidence-id="${evidenceId}"]`)];
  return nodes.length === 2 && nodes.every((node) => node.classList.contains("is-linked"));
}, source.id);
```

Expected: failure because no evidence chip exists yet.

- [ ] **Step 2: Create the smallest shared chip**

Create `caos/frontend/src/components/EvidenceChip.tsx`:

```tsx
type Props = {
  evidenceId: string;
  linkedId: string;
  onOpen: (evidenceId: string) => void;
  onPreview: (evidenceId: string) => void;
  onPreviewEnd: () => void;
  warning?: boolean;
};

export default function EvidenceChip({ evidenceId, linkedId, onOpen, onPreview, onPreviewEnd, warning = false }: Props) {
  const linked = linkedId === evidenceId;
  return (
    <button
      type="button"
      className={`evidence-chip${warning ? " warning" : ""}${linked ? " is-linked" : ""}`}
      data-evidence-id={evidenceId}
      aria-label={`Open evidence ${evidenceId}${warning ? ", QA concern" : ""}`}
      onBlur={onPreviewEnd}
      onClick={() => onOpen(evidenceId)}
      onFocus={() => onPreview(evidenceId)}
      onMouseEnter={() => onPreview(evidenceId)}
      onMouseLeave={onPreviewEnd}
    >
      {warning && <span aria-hidden="true">▲</span>}
      {evidenceId}
    </button>
  );
}
```

Do not abbreviate or relabel the identifier. Do not set `warning` without an actual evidence-level QA concern.

- [ ] **Step 3: Adopt chips in `SourcesView` using existing artifact refs**

Add `sourceId`, `snapshot`, and `onOpenEvidence` props. Keep `linkedEvidenceId` local:

```tsx
const [linkedEvidenceId, setLinkedEvidenceId] = useState("");
const sourceById = useMemo(
  () => new Map(sources.map((source) => [source.id, source])),
  [sources],
);
const openEvidence = (evidenceId: string) => {
  const source = sourceById.get(evidenceId);
  if (!source) {
    setArtifactError(`Evidence ${evidenceId} is not in the active case source set.`);
    return;
  }
  onOpenEvidence(evidenceId, source);
};
```

Replace `Evidence refs: N` with:

```tsx
<div className="evidence-list" aria-label="Artifact evidence">
  {evidenceRefs.map((evidenceId) => (
    <EvidenceChip
      evidenceId={evidenceId}
      key={evidenceId}
      linkedId={linkedEvidenceId}
      onOpen={openEvidence}
      onPreview={setLinkedEvidenceId}
      onPreviewEnd={() => setLinkedEvidenceId("")}
    />
  ))}
</div>
```

For a source row included in `evidenceRefs`, render the same `EvidenceChip` beside its filename, with the same callbacks. Keep existing source-row highlighting, but drive it from `linkedEvidenceId || selectedEvidenceId`; do not infer any other relationship.

- [ ] **Step 4: Support exact palette IDs without leaking labels**

Hydrate `source` from the URL beside the existing `artifact` query. Once the authorized source list loads, open that exact source once. Use a ref keyed by `${selectedCase.id}:${sourceId}` to prevent repeated drawer opening. If it is absent, render the existing error state; do not search other cases.

- [ ] **Step 5: Keep linked selection local and clearable**

When a chip is activated, set a persistent `selectedEvidenceId` and show a compact strip above the source table:

```tsx
{selectedEvidenceId && (
  <div className="selection-strip" role="status">
    <span>Evidence {selectedEvidenceId}</span>
    <button type="button" className="button small" onClick={() => setSelectedEvidenceId("")}>Clear</button>
  </div>
)}
```

Hover/focus preview is temporary. Activation is persistent until Clear, case change, or workflow navigation. No network request is made for linked highlighting.

- [ ] **Step 6: Verify the interaction**

```bash
cd caos/frontend
npx tsc --noEmit
npm run lint -- --max-warnings=0
npm run test:workbench
```

Expected: all focused browser assertions pass before visual styling is judged.

- [ ] **Step 7: Commit the evidence interaction**

```bash
git add caos/frontend/src/components/EvidenceChip.tsx caos/frontend/scripts/workbench-smoke.mjs
git add -p -- caos/frontend/src/components/Workspace.tsx
git diff --cached --check
git diff --cached
git commit -m "feat(frontend): restore linked evidence chips"
```

---

### Task 6: Polish hierarchy, responsive behaviour, shared states, and screenshots

**Files:**

- Modify: `caos/frontend/app/globals.css`
- Modify: `caos/frontend/src/components/Workspace.tsx`
- Modify: `caos/frontend/scripts/a11y-axe.mjs`
- Modify: `caos/frontend/scripts/workbench-smoke.mjs`

- [ ] **Step 1: Make loading preserve geometry**

Keep the existing `LoadState` function in `Workspace.tsx`; do not extract an unused state framework. Change only its loading branch:

```tsx
if (loading) return (
  <div className="state-skeleton" role="status" aria-live="polite" aria-label="Loading">
    <span />
    <span />
    <span />
  </div>
);
```

Retain explicit error and empty copy. Add `.state-block.partial`, `.stale`, `.error`, and `.unavailable` only where the shell or drawer actually uses them.

- [ ] **Step 2: Apply the institutional shell hierarchy**

In `globals.css`, preserve the existing token values and the user's reduced-motion fix. Implement these concrete behaviours:

- `.app-shell`: 184px workflow rail plus flexible workspace at 1440px and above.
- `.rail`: one compact workflow stack, no old group labels, fixed/sticky within the viewport.
- `.authority-bar`: 52–58px, single hairline border, issuer/case text first, accepted/source/QA metadata second, controls last.
- `.content`: one dominant canvas, max width 1600px, no equal-weight dashboard-card treatment added.
- `.workflow-tools`: visible only for the active workflow, subordinate to the primary link.
- `.command-palette`: centered modal, maximum 680px, results scroll inside the dialog.
- `.context-drawer`: fixed to the right edge via dialog positioning, width `min(440px, 100vw)`, height 100dvh, no canvas shrink.
- `.evidence-chip`: inline mono 10–11px, blue outline, transparent fill; `.warning` amber with glyph; `.is-linked` uses outline plus a light background so selection is not colour-only.
- `.selection-strip`: compact flex row with one Clear action.
- `.state-skeleton`: three restrained fixed-height bars using the elevated surface; no infinite pulse.
- Keep `Report Studio` paper styles scoped under `.paper`.

Do not add gradients, glow, icon packages, animated chart shells, or decorative cards.

- [ ] **Step 3: Implement the responsive rules**

Use existing breakpoints rather than adding a JavaScript viewport hook:

```css
@media (max-width: 1100px) {
  .app-shell { grid-template-columns: 156px minmax(0, 1fr); }
  .authority-secondary .optional { display: none; }
}

@media (max-width: 900px) {
  .app-shell { display: block; }
  .rail { position: static; flex-direction: row; overflow-x: auto; }
  .workflow-tools { display: none; }
  .authority-bar { align-items: stretch; flex-direction: column; }
  .authority-actions { width: 100%; }
  .authority-actions select { min-width: 0; flex: 1; }
  .context-drawer { width: min(440px, 100vw); }
}

@media (max-width: 520px) {
  .authority-secondary { display: none; }
  .context-drawer { max-width: 100vw; }
  .evidence-chip { min-height: 24px; }
}
```

Wide tables keep their own `.table-wrap` horizontal scroll. Page-level horizontal overflow is a failure.

- [ ] **Step 4: Expand the real axe runner instead of adding a second audit script**

Change `a11y-axe.mjs` to loop over:

```js
const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "laptop", width: 1024, height: 768 },
  { name: "reflow", width: 720, height: 900 },
];
```

Create a new context per viewport, run all existing routes, and include `viewport` in each violation record. Keep one final JSON result.

- [ ] **Step 5: Add a reduced-motion and request-count assertion**

In the browser script, create one reduced-motion context and assert:

```js
const reduced = await browser.newContext({
  viewport: { width: 1024, height: 768 },
  reducedMotion: "reduce",
});
const reducedPage = await reduced.newPage();
await reducedPage.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
const reducedStyle = await reducedPage.evaluate(() => {
  const style = getComputedStyle(document.querySelector(".app-shell"));
  return { iterationCount: style.animationIterationCount, playState: style.animationPlayState };
});
assert.equal(reducedStyle.iterationCount, "1");
assert.equal(reducedStyle.playState, "paused");
await reduced.close();
```

Reset `caseRequests`, click Overview → Sources → Analyse with the same case, and assert no additional `/api/cases` list request. If this fails, stop and preserve the `Workspace` client identity across those dynamic-route transitions before proceeding; do not hide the regression with client storage, a module-global cache, or a cache library.

- [ ] **Step 6: Run all checks**

```bash
cd caos/frontend
npm run lint -- --max-warnings=0
npx tsc --noEmit
npm run build
cd ..
mkdir -p server/static
cp -R frontend/out/. server/static/.
PYTHONPATH=server .venv/bin/python -m pytest tests/test_clean_slate.py -q
```

Restart the local application with the rebuilt static output, then:

```bash
cd caos/frontend
npm run test:workbench
npm run a11y
```

Expected: all commands exit 0; axe reports `violations: 0` for all 27 route/viewport combinations.

- [ ] **Step 7: Compare measured performance with Task 1**

Use the JSON printed by `test:workbench`. Expected:

- `domContentLoaded` and first-contentful-paint are each at or below 110% of the Task 1 baseline;
- linked focus causes no request;
- no extra `/api/cases` request when the same client instance is retained.

If a timing exceeds the target, profile before accepting it. Do not hide the failure by increasing the budget.

- [ ] **Step 8: Capture the requested screenshots**

With the populated Workbench QA case selected, capture:

```bash
cd caos/frontend
node --input-type=module -e 'import { chromium } from "playwright"; const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1}); await page.goto(process.env.CAOS_SCREENSHOT_URL,{waitUntil:"networkidle"}); await page.screenshot({path:"../../outputs/workbench-foundation-1440.png",fullPage:true}); await page.setViewportSize({width:1024,height:768}); await page.screenshot({path:"../../outputs/workbench-foundation-1024.png",fullPage:true}); await browser.close();'
```

Set `CAOS_SCREENSHOT_URL` to the exact `/command-center/?case=...` URL first. Inspect both images. Confirm the change/implication canvas is dominant, authority is readable, QA/Sources are compact, and no content is clipped.

- [ ] **Step 9: Commit the polish and verification changes**

Do not commit screenshot output unless the repository's existing output policy requires it.

```bash
git add caos/frontend/scripts/a11y-axe.mjs caos/frontend/scripts/workbench-smoke.mjs
git add -p -- caos/frontend/app/globals.css caos/frontend/src/components/Workspace.tsx
git diff --cached --check
git diff --cached
git commit -m "style(frontend): polish analyst workbench foundation"
```

---

### Task 7: Adversarial review, impact verification, and handoff

**Files:**

- Review all files listed in the File and Responsibility Map.
- Append only if a new high-impact objection is discovered: `.agent-reviews/redteam.md`
- Append only for an actual skill defect: `skill-observations/observation-log.md`

- [ ] **Step 1: Run the mandatory rewrite tournament**

Invoke `rewrite-tournament` in no-argument post-edit mode on the changed functions in:

- `Workspace`
- `refreshCase`
- `SourcesView`
- `WorkbenchShell`
- `EvidenceChip`

Accept a rewrite only if it preserves native-dialog focus, authorization scope, exact authority binding, report draft guards, and the browser contract. Re-run the focused check after any accepted rewrite.

- [ ] **Step 2: Run the mandatory confidence review**

Invoke `confidence-review`. At minimum investigate:

- stale selected-case authority after rapid switching;
- palette result leakage or arbitrary evidence-label disclosure;
- Escape and explicit-close focus restoration for both dialogs;
- native dialog behaviour at 720px and 200% zoom;
- source-level evidence copy accidentally implying block-level precision;
- Report Studio draft navigation after shell replacement;
- role-gated Admin Studio visibility;
- duplicated `/api/cases` fetches and timing regression;
- user-owned pre-existing hunks accidentally staged.

Patch confirmed issues and rerun their smallest failing check.

- [ ] **Step 3: Run GitNexus change detection before the final commit**

```text
detect_changes({scope: "compare", base_ref: "origin/main", repo: "CAOS"})
```

Expected: frontend Workspace flows, destination route rendering, and the clean-slate contract test are affected. Investigate any server production symbol, publishing calculation, or methodology flow not named in this plan.

- [ ] **Step 4: Run the final suite**

```bash
cd caos/frontend
npm run lint -- --max-warnings=0
npx tsc --noEmit
npm run build
npm run test:workbench
npm run a11y
cd ..
.venv/bin/python -m pytest tests/test_clean_slate.py -q
```

Expected: all pass.

- [ ] **Step 5: Inspect and commit only remaining plan-owned hunks**

```bash
git status --short
git diff --check
git add caos/frontend/src/lib/workbench.ts caos/frontend/src/components/WorkbenchShell.tsx caos/frontend/src/components/EvidenceChip.tsx caos/frontend/scripts/workbench-smoke.mjs caos/frontend/scripts/a11y-axe.mjs caos/frontend/package.json 'caos/frontend/app/[destination]/page.tsx' caos/tests/test_clean_slate.py
git add -p -- caos/frontend/src/components/Workspace.tsx caos/frontend/app/globals.css
git diff --cached --check
git diff --cached
git commit -m "feat(frontend): complete workbench foundation"
```

If there are no remaining staged changes after the task commits, skip the empty final commit.

- [ ] **Step 6: Handoff with explicit ceilings**

Report:

- six workflow navigation and case-scoped palette shipped;
- accepted authority, freshness, source count, and honest QA state shipped;
- QA/source/evidence drawers and legacy-style source evidence chips shipped;
- screenshots and verification paths;
- deferred by design: issuer registry search, governed QA summary, block-level citations, canonical workflow redirects, Overview/Sources content redesign, and analytical visualisations.

Do not claim the full five-phase application redesign is complete.
