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
const crossCaseUpload = await api.post(`/api/cases/${raceCase.id}/sources`, {
  multipart: {
    file: {
      name: "second-earnings.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Revenue 820\nEBITDA 140"),
    },
  },
});
assert.equal(crossCaseUpload.status(), 201);
const crossCaseRunResponse = await api.post(`/api/cases/${raceCase.id}/runs`, {
  data: { pathway: "EARNINGS_UPDATE", depth: "screen", focus_questions: [] },
});
assert.equal(crossCaseRunResponse.status(), 202);
const crossCaseRun = await crossCaseRunResponse.json();
let crossCaseRunState;
for (let attempt = 0; attempt < 60; attempt += 1) {
  const response = await api.get(`/api/runs/${crossCaseRun.id}`);
  crossCaseRunState = await response.json();
  if (crossCaseRunState.status === "succeeded") break;
  await new Promise((resolve) => setTimeout(resolve, 50));
}
assert.equal(crossCaseRunState?.status, "succeeded");
const failedCaseResponse = await api.post("/api/cases", {
  data: { name: "Authority Failure", issuer: "Unavailable", sector: "Services" },
});
assert.equal(failedCaseResponse.status(), 201);
const failedCase = await failedCaseResponse.json();
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
  let authorityRequests = 0;
  let expectedAuthorityFailureURL = "";
  let expectedAuthorityFailureSeen = false;
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    if (!expectedAuthorityFailureSeen
      && message.location().url === expectedAuthorityFailureURL
      && message.text() === "Failed to load resource: the server responded with a status of 503 (Service Unavailable)") {
      expectedAuthorityFailureSeen = true;
      return;
    }
    errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (requestValue) => {
    const pathname = new URL(requestValue.url()).pathname;
    if (pathname === "/api/cases") caseRequests += 1;
    if (/^\/api\/cases\/[^/]+\/(?:lens|snapshot)$/.test(pathname)) authorityRequests += 1;
  });

  let releaseAuthorityDetail;
  const authorityDetailBarrier = new Promise((resolve) => {
    releaseAuthorityDetail = resolve;
  });
  const heldAuthorityDetail = (url) => url.pathname === `/api/cases/${caseRecord.id}`;
  const holdAuthorityDetail = async (route) => {
    await authorityDetailBarrier;
    await route.continue();
  };
  await page.route(heldAuthorityDetail, holdAuthorityDetail);
  await page.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "domcontentloaded" });
  const loadingSourcesTrigger = page.getByRole("button", { name: "Sources loading" });
  await loadingSourcesTrigger.click();
  const sourceDrawer = page.getByRole("dialog", { name: "Source details" });
  await sourceDrawer.getByText("Loading source authority…").waitFor();
  assert.equal(await sourceDrawer.getByText(/^0$/).count(), 0);
  assert.equal(await sourceDrawer.getByText(/No accepted/).count(), 0);
  await page.keyboard.press("Escape");
  releaseAuthorityDetail();
  await page.getByRole("region", { name: "Accepted authority" }).getByText(/Source set v1/).waitFor();
  const resolvedSourcesTrigger = page.getByRole("button", { name: "1 sources" });
  await resolvedSourcesTrigger.click();
  await sourceDrawer.getByText("Current source count").waitFor();
  await page.getByRole("combobox", { name: "Select case" }).evaluate((element) => {
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
  assert.equal(await sourceDrawer.isVisible(), true, "reselecting the current case closed the resolved authority drawer");
  assert.equal(await resolvedSourcesTrigger.count(), 1, "reselecting the current case exposed a false authority lifecycle state");
  assert.equal(await sourceDrawer.getByText("Loading source authority…").count(), 0);
  assert.equal(await sourceDrawer.getByText("Source authority unavailable.").count(), 0);
  await page.keyboard.press("Escape");
  await page.unroute(heldAuthorityDetail, holdAuthorityDetail);
  const timing = await page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0];
    const paint = performance.getEntriesByName("first-contentful-paint")[0];
    return {
      domContentLoaded: navigation?.domContentLoadedEventEnd ?? null,
      firstContentfulPaint: paint?.startTime ?? null,
    };
  });
  console.log(JSON.stringify({ timing, caseRequests }));

  const failedAuthorityDetail = (url) => url.pathname === `/api/cases/${failedCase.id}`;
  const failAuthorityDetail = (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "authority unavailable" }),
  });
  await page.route(failedAuthorityDetail, failAuthorityDetail);
  expectedAuthorityFailureURL = `${baseURL}/api/cases/${failedCase.id}`;
  expectedAuthorityFailureSeen = false;
  await page.getByRole("combobox", { name: "Select case" }).selectOption(failedCase.id);
  const unavailableSourcesTrigger = page.getByRole("button", { name: "Sources unavailable" });
  await unavailableSourcesTrigger.click();
  await sourceDrawer.getByText("Source authority unavailable.").waitFor();
  assert.equal(await sourceDrawer.getByText(/^0$/).count(), 0);
  assert.equal(await sourceDrawer.getByText(/No accepted/).count(), 0);
  assert.equal(expectedAuthorityFailureSeen, true, "controlled authority 503 did not emit the expected console error");
  await page.keyboard.press("Escape");
  await page.unroute(failedAuthorityDetail, failAuthorityDetail);
  expectedAuthorityFailureURL = "";
  await page.getByRole("combobox", { name: "Select case" }).selectOption(caseRecord.id);
  await page.getByRole("region", { name: "Accepted authority" }).getByText(/Source set v1/).waitFor();

  await page.evaluate((caseId) => window.sessionStorage.setItem(`caos-report-draft:${caseId}`, JSON.stringify({ thesis: "Unsaved analyst view" })), caseRecord.id);
  let cancelledRoutePrompts = 0;
  const cancelRouteChange = (dialog) => {
    cancelledRoutePrompts += 1;
    void dialog.dismiss();
  };
  page.on("dialog", cancelRouteChange);
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await page.evaluate((nextCaseId) => window.history.pushState(null, "", `/command-center/?case=${nextCaseId}`), raceCase.id);
    await page.waitForFunction((expectedCaseId) => new URL(window.location.href).searchParams.get("case") === expectedCaseId, caseRecord.id);
    await page.getByRole("region", { name: "Accepted authority" }).getByText("Northstar / Workbench QA").waitFor();
  }
  assert.equal(cancelledRoutePrompts, 2, "a cancelled draft-bound route change was not retryable");
  page.off("dialog", cancelRouteChange);
  await page.evaluate((caseId) => window.sessionStorage.removeItem(`caos-report-draft:${caseId}`), caseRecord.id);

  let crossCaseAcceptRequests = 0;
  const countCrossCaseAccept = (requestValue) => {
    if (requestValue.method() === "POST"
      && new URL(requestValue.url()).pathname === `/api/runs/${crossCaseRun.id}/accept`) crossCaseAcceptRequests += 1;
  };
  page.on("request", countCrossCaseAccept);
  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}&run=${crossCaseRun.id}`, { waitUntil: "networkidle" });
  await page.getByText("Requested run does not belong to the selected case.", { exact: true }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Accept analytical snapshot" }).count(), 0, "cross-case run exposed an acceptance action");
  await page.waitForFunction((runId) => new URL(window.location.href).searchParams.get("run") !== runId, crossCaseRun.id);
  assert.equal(crossCaseAcceptRequests, 0, "cross-case run was accepted from the selected case");
  page.off("request", countCrossCaseAccept);

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
  await page.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  caseRequests = 0;
  authorityRequests = 0;

  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  const artifactPalette = page.getByRole("dialog", { name: "Command palette" });
  await artifactPalette.getByRole("combobox", { name: "Search commands" }).fill(artifact.id);
  await artifactPalette.getByRole("option", { name: "Open artifact ID in this case" }).click();
  await page.waitForURL((url) => url.pathname === "/sources/"
    && url.searchParams.get("case") === caseRecord.id
    && url.searchParams.get("artifact") === artifact.id);
  const evidenceFocus = page.getByRole("heading", { name: "Evidence focus" }).locator("../..");
  await evidenceFocus.getByText(artifact.digest, { exact: true }).waitFor();

  const deepDiveQuestion = "What changed in refinancing capacity?";
  await page.evaluate(({ caseId, question }) => {
    const query = new URLSearchParams({ case: caseId, q: question });
    window.history.pushState(null, "", `/deep-dive/?${query}`);
  }, { caseId: caseRecord.id, question: deepDiveQuestion });
  await page.waitForURL((url) => url.pathname === "/deep-dive/" && url.searchParams.get("q") === deepDiveQuestion);
  await page.getByText(deepDiveQuestion, { exact: true }).waitFor();

  const commandQuestion = "Which evidence changes the downside case?";
  await page.evaluate(({ caseId, question }) => {
    const query = new URLSearchParams({ case: caseId, q: question });
    window.history.pushState(null, "", `/command-center/?${query}`);
  }, { caseId: caseRecord.id, question: commandQuestion });
  await page.waitForURL((url) => url.pathname === "/command-center/" && url.searchParams.get("q") === commandQuestion);
  await page.getByText(commandQuestion, { exact: true }).waitFor();

  for (const label of ["Overview", "Sources", "Analyse"]) {
    await page.getByRole("navigation", { name: "Workflows" }).getByRole("link", { name: label, exact: true }).click();
    await page.waitForLoadState("networkidle");
  }
  assert.equal(caseRequests, 0, "same-client query/workflow navigation repeated the case-list request");
  assert.ok(authorityRequests <= 12, `same-client navigation caused an authority refresh loop (${authorityRequests} requests)`);
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
  let markAcceptanceIntercepted;
  const acceptanceIntercepted = new Promise((resolve) => {
    markAcceptanceIntercepted = resolve;
  });
  let releaseAcceptance;
  const acceptanceBarrier = new Promise((resolve) => {
    releaseAcceptance = resolve;
  });
  await page.route(`**/api/runs/${nextRun.id}/accept`, async (route) => {
    const heldAcceptanceResponse = await route.fetch();
    markAcceptanceIntercepted();
    await acceptanceBarrier;
    await route.fulfill({ response: heldAcceptanceResponse });
  });
  const delayedAcceptResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/runs/${nextRun.id}/accept`,
  );
  let switchedToRaceCase = false;
  const forbiddenAuthorityRequests = [];
  const trackAuthorityRequest = (requestValue) => {
    if (!switchedToRaceCase) return;
    const pathname = new URL(requestValue.url()).pathname;
    if (pathname === `/api/cases/${caseRecord.id}`
      || pathname === `/api/cases/${caseRecord.id}/snapshot`) {
      forbiddenAuthorityRequests.push(pathname);
    }
  };
  page.on("request", trackAuthorityRequest);
  page.once("dialog", (dialog) => void dialog.accept());
  await acceptTrigger.click();
  await acceptanceIntercepted;
  await page.getByRole("combobox", { name: "Select case" }).selectOption(raceCase.id);
  switchedToRaceCase = true;
  releaseAcceptance();
  const acceptanceResponse = await delayedAcceptResponse;
  assert.equal(acceptanceResponse.status(), 200);
  await acceptanceResponse.finished();
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
  const authority = page.getByRole("region", { name: "Accepted authority" });
  await authority.getByText("Second / Authority Race").waitFor();
  await authority.getByText("No accepted snapshot").waitFor();
  assert.equal(await authority.getByText(/Source set v1/).count(), 0);
  assert.deepEqual(
    forbiddenAuthorityRequests,
    [],
    "accepted Case A mutation refreshed authority after switching to Case B",
  );
  page.off("request", trackAuthorityRequest);

  const qaTrigger = page.getByRole("button", { name: /QA unavailable/ });
  await qaTrigger.click();
  await page.getByRole("dialog", { name: "QA details" }).getByText(/No governed snapshot-level QA summary/).waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => qaTrigger.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the QA trigger");
  }));

  await page.goto(`${baseURL}/sources/?case=${caseRecord.id}&artifact=${artifact.id}`, { waitUntil: "networkidle" });
  const matching = page.locator(`[data-evidence-id="${source.id}"]`);
  assert.equal(await matching.count(), 2);
  const chip = matching.first();
  await chip.focus();
  await page.waitForFunction((evidenceId) => {
    const nodes = [...document.querySelectorAll(`[data-evidence-id="${evidenceId}"]`)];
    return nodes.length === 2 && nodes.every((node) => node.classList.contains("is-linked"));
  }, source.id);
  await chip.click();
  const evidence = page.getByRole("dialog", { name: `Evidence ${source.id}` });
  await evidence.getByText("earnings.txt").waitFor();
  await evidence.getByText(/Source-level reference; no block locator supplied/).waitFor();
  await evidence.getByRole("link", { name: "Open full source" }).waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => chip.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the evidence trigger");
  }));

  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  const sourcePalette = page.getByRole("dialog", { name: "Command palette" });
  await sourcePalette.getByRole("combobox", { name: "Search commands" }).fill(source.id);
  await sourcePalette.getByRole("option", { name: "Open source ID in this case" }).click();
  await page.waitForURL((url) => url.pathname.replace(/\/$/, "") === "/sources" && url.searchParams.get("source") === source.id);
  await evidence.getByText("earnings.txt").waitFor();
  await page.keyboard.press("Escape");
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
  assert.equal(await evidence.isVisible(), false, "same-route source query reopened after the drawer was closed");

  const sourceListURL = `${baseURL}/api/cases/${caseRecord.id}/sources`;
  const failedSourceList = (url) => url.href === sourceListURL;
  const failSourceList = (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: "not-json",
  });
  await page.route(failedSourceList, failSourceList);
  await page.goto(`${baseURL}/sources/?case=${caseRecord.id}&source=${source.id}`, { waitUntil: "networkidle" });
  await page.getByRole("alert").getByText("Unable to load this view.").waitFor();
  assert.equal(await page.getByText(/not in the active case source set/).count(), 0);
  assert.equal(await evidence.count(), 0, "failed source authority opened an evidence drawer");
  await page.unroute(failedSourceList, failSourceList);
  await page.reload({ waitUntil: "networkidle" });
  await evidence.getByText("earnings.txt").waitFor();
  await page.keyboard.press("Escape");

  await page.setViewportSize({ width: 720, height: 900 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  assert.equal(overflow, false, "workbench causes page-level horizontal overflow at reflow width");
  assert.deepEqual(errors, []);
  await context.close();

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
} finally {
  await browser.close();
  await api.dispose();
}
