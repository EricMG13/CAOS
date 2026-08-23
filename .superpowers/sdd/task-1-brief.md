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

