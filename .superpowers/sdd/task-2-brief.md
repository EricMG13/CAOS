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

