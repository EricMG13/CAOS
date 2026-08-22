import assert from "node:assert/strict";
import { chromium, request } from "playwright";

const baseURL = process.env.CAOS_URL || "http://127.0.0.1:8000";
const api = await request.newContext({ baseURL });
const created = await api.post("/api/cases", {
  data: { name: "Workbench QA", issuer: "Northstar", sector: "Services" },
});
assert.equal(created.status(), 201);
const caseRecord = await created.json();
const raceCaseResponse = await api.post("/api/cases", {
  data: { name: "Authority Race", issuer: "Second", sector: "Services" },
});
assert.equal(raceCaseResponse.status(), 201);
const raceCase = await raceCaseResponse.json();
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
  await page.getByRole("region", { name: "Accepted authority" }).getByText("Northstar / Workbench QA").waitFor();
  await page.getByRole("region", { name: "Accepted authority" }).getByText(/Source set v1/).waitFor();
  await page.getByRole("button", { name: /QA unavailable/ }).waitFor();

  const paletteTrigger = page.getByRole("button", { name: /Open command palette/ });
  await paletteTrigger.focus();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  const palette = page.getByRole("dialog", { name: "Command palette" });
  await palette.getByRole("combobox", { name: "Search commands" }).fill("Northstar");
  await palette.getByRole("option", { name: /Northstar \/ Workbench QA/ }).waitFor();
  await palette.getByRole("combobox", { name: "Search commands" }).fill("src_deadbeef");
  await palette.getByRole("option", { name: /Open source ID in this case/ }).waitFor();
  await palette.getByRole("combobox", { name: "Search commands" }).fill("secret issuer");
  await palette.getByText("No authorized matches").waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => paletteTrigger.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the palette trigger");
  }));

  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}&run=${run.id}`, { waitUntil: "networkidle" });
  const nextRunResponsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/cases/${caseRecord.id}/runs`,
  );
  await page.getByRole("button", { name: "Compile and run" }).click();
  const nextRunResponse = await nextRunResponsePromise;
  assert.equal(nextRunResponse.status(), 202);
  const nextRun = await nextRunResponse.json();
  await page.waitForFunction((expectedRunId) => Array.from(document.querySelectorAll('nav[aria-label="Analyse tools"] a'))
    .some((element) => element.textContent?.includes("Run")
      && new URL(element.href).searchParams.get("run") === expectedRunId), nextRun.id);

  let nextRunState;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const response = await api.get(`/api/runs/${nextRun.id}`);
    nextRunState = await response.json();
    if (nextRunState.status === "succeeded") break;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  assert.equal(nextRunState?.status, "succeeded");
  const acceptTrigger = page.getByRole("button", { name: "Accept analytical snapshot" });
  await acceptTrigger.waitFor();
  await page.route(`**/api/runs/${nextRun.id}/accept`, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.continue();
  });
  const delayedAcceptResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/runs/${nextRun.id}/accept`,
  );
  page.once("dialog", (dialog) => void dialog.accept());
  await acceptTrigger.click();
  await page.getByRole("combobox", { name: "Select case" }).selectOption(raceCase.id);
  assert.equal((await delayedAcceptResponse).status(), 200);
  const authority = page.getByRole("region", { name: "Accepted authority" });
  await authority.getByText("Second / Authority Race").waitFor();
  await authority.getByText("No accepted snapshot").waitFor();
  assert.equal(await authority.getByText(/Source set v1/).count(), 0);

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
