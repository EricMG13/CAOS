import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { chromium, request } from "playwright";

const baseURL = process.env.CAOS_URL || "http://127.0.0.1:8000";
const fixtureSuffix = randomUUID().slice(0, 8);
const primaryIssuer = `Northstar-${fixtureSuffix}`;
const raceIssuer = `Second-${fixtureSuffix}`;
const primaryLabel = `${primaryIssuer} / Workbench QA`;
const raceLabel = `${raceIssuer} / Authority Race`;
const maxDomContentLoadedMs = Number(process.env.CAOS_MAX_DCL_MS || 250);
// Observed FCP on shared CI runners across 8 runs: 188, 200, 212, 224, 232,
// 252, 272, 332ms. Two of those (272 and 332) are the same commit, so ~60ms
// of the spread is runner noise alone. A 300ms budget sat inside that noise
// band and failed on load, not on regression; 400ms clears the worst
// observed sample while still catching anything that adds ~150ms.
const maxFirstContentfulPaintMs = Number(process.env.CAOS_MAX_FCP_MS || 400);
assert.ok(Number.isFinite(maxDomContentLoadedMs) && maxDomContentLoadedMs > 0, "CAOS_MAX_DCL_MS must be a positive finite number");
assert.ok(Number.isFinite(maxFirstContentfulPaintMs) && maxFirstContentfulPaintMs > 0, "CAOS_MAX_FCP_MS must be a positive finite number");
const identityHeaders = process.env.CAOS_EDGE_SECRET ? {
  "x-edge-authorization": process.env.CAOS_EDGE_SECRET,
  "x-forwarded-user": process.env.CAOS_TEST_USER || "analyst.qa@local.invalid",
  "x-forwarded-email": process.env.CAOS_TEST_USER || "analyst.qa@local.invalid",
  "x-forwarded-groups": process.env.CAOS_TEST_GROUPS || "caos-analyst",
} : {};
const api = await request.newContext({ baseURL, extraHTTPHeaders: identityHeaders });
const created = await api.post("/api/cases", {
  data: { name: "Workbench QA", issuer: primaryIssuer, sector: "Services" },
});
assert.equal(created.status(), 201);
const caseRecord = await created.json();
const raceCaseResponse = await api.post("/api/cases", {
  data: { name: "Authority Race", issuer: raceIssuer, sector: "Services" },
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
const idleCaseResponse = await api.post("/api/cases", {
  data: { name: "No Run Boundary", issuer: "Idle", sector: "Services" },
});
assert.equal(idleCaseResponse.status(), 201);
const idleCase = await idleCaseResponse.json();
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
const researchPlanHash = `sha256:${"a".repeat(64)}`;
const researchPlanLongText = "The supplied evidence must resolve the complete refinancing perimeter without truncating this deliberately long committee-review sentence.";
const proposedResearchPlan = {
  methodology_build_id: "",
  brief_digest: "",
  source_set: { id: "", version: 7 },
  upstream_artifacts: [],
  scope: { type: "", key: "", source_mode: "" },
  workstreams: [
    {
      id: "",
      kind: "topical",
      question: researchPlanLongText,
      assigned_questions: ["Liquidity runway?", "Liquidity runway?", ""],
      perspective: "Buy-side credit analyst",
      hypothesis: "Refinancing is feasible if liquidity remains durable.",
      evidence_needs: ["Debt maturity schedule", "Debt maturity schedule", ""],
      source_classes: ["supplied_case_sources", "supplied_case_sources", ""],
      disconfirming_test: "Identify supplied evidence that contradicts the refinancing case.",
      completion_test: "Answer each assigned question with source locators or record the evidence gap.",
      effort_cap: "Within the fixed standard research budget.",
    },
    {
      id: "",
      kind: "",
      question: "",
      assigned_questions: [],
      perspective: "",
      hypothesis: "",
      evidence_needs: [],
      source_classes: [],
      disconfirming_test: "",
      completion_test: "",
      effort_cap: "",
    },
  ],
};
const pendingResearchRun = {
  id: `run_plan_${fixtureSuffix}`,
  case_id: caseRecord.id,
  status: "paused",
  plan: { pathway: "DEEP_RESEARCH", depth: "full", profile_id: "DEEP_RESEARCH_FULL", selection_id: "fixture-selection" },
  nodes: [
    { id: "node-cp0", module_id: "CP-0", status: "succeeded", artifact_id: artifact.id },
    { id: "node-cpdr", module_id: "CP-DR", status: "pending", artifact_id: null },
  ],
  error: { code: "PLAN_APPROVAL_REQUIRED", message: "Approve the exact deterministic research plan before agent execution." },
  research: { phase: "awaiting_approval", proposed_plan_hash: researchPlanHash, proposed_plan: proposedResearchPlan },
};

const browser = await chromium.launch({ headless: true });
const errors = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, extraHTTPHeaders: identityHeaders });
  const page = await context.newPage();
  await page.addInitScript(() => {
    window.__caosUrlWrites = [];
    for (const method of ["pushState", "replaceState"]) {
      const original = history[method].bind(history);
      history[method] = (...args) => {
        const result = original(...args);
        window.__caosUrlWrites.push(location.search);
        return result;
      };
    }
  });
  let caseRequests = 0;
  let authorityRequests = 0;
  let expectedAuthorityFailureURL = "";
  let expectedAuthorityFailureSeen = false;
  let expectedNotFoundURL = "";
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    if (message.location().url === expectedNotFoundURL
      && message.text() === "Failed to load resource: the server responded with a status of 404 (Not Found)") {
      expectedNotFoundURL = "";
      return;
    }
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
  let markAuthorityDetailSeen;
  const authorityDetailSeen = new Promise((resolve) => {
    markAuthorityDetailSeen = resolve;
  });
  const heldAuthorityDetail = (url) => url.pathname === `/api/cases/${caseRecord.id}`;
  const holdAuthorityDetail = async (route) => {
    markAuthorityDetailSeen();
    await authorityDetailBarrier;
    await route.continue();
  };
  await page.route(heldAuthorityDetail, holdAuthorityDetail);
  await page.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "domcontentloaded" });
  await authorityDetailSeen;
  const loadingSourcesTrigger = page.getByRole("button", { name: "Sources loading" });
  assert.equal(await loadingSourcesTrigger.getAttribute("aria-expanded"), "false",
    "client authority request did not establish a closed, hydrated source drawer");
  await loadingSourcesTrigger.click();
  const sourceDrawer = page.getByRole("dialog", { name: "Source details" });
  await sourceDrawer.getByText("Loading source authority…").waitFor();
  assert.equal(await sourceDrawer.getByText(/^0$/).count(), 0);
  assert.equal(await sourceDrawer.getByText(/No accepted/).count(), 0);
  await page.keyboard.press("Escape");
  releaseAuthorityDetail();
  await page.getByRole("region", { name: "Accepted authority" }).getByText(/Source set v1/).waitFor();
  const resolvedSourcesTrigger = page.getByRole("button", { name: "1 source", exact: true });
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
  const timing = await page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0];
    const paint = performance.getEntriesByName("first-contentful-paint")[0];
    return {
      domContentLoaded: navigation?.domContentLoadedEventEnd ?? null,
      firstContentfulPaint: paint?.startTime ?? null,
    };
  });
  assert.ok(timing.domContentLoaded !== null && timing.domContentLoaded <= maxDomContentLoadedMs, `DCL ${timing.domContentLoaded}ms exceeds ${maxDomContentLoadedMs}ms`);
  assert.ok(timing.firstContentfulPaint !== null && timing.firstContentfulPaint <= maxFirstContentfulPaintMs, `FCP ${timing.firstContentfulPaint}ms exceeds ${maxFirstContentfulPaintMs}ms`);
  console.log(JSON.stringify({ timing, caseRequests }));
  await sourceDrawer.getByRole("link", { name: "Open Sources" }).click();
  await page.waitForURL((url) => url.pathname.replace(/\/$/, "") === "/sources" && url.searchParams.get("case") === caseRecord.id);
  await sourceDrawer.waitFor({ state: "hidden" });
  await page.unroute(heldAuthorityDetail, holdAuthorityDetail);
  await page.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "networkidle" });

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
    await page.getByRole("region", { name: "Accepted authority" }).getByText(primaryLabel).waitFor();
  }
  assert.equal(cancelledRoutePrompts, 2, "a cancelled draft-bound route change was not retryable");
  page.off("dialog", cancelRouteChange);
  await page.evaluate((caseId) => window.sessionStorage.removeItem(`caos-report-draft:${caseId}`), caseRecord.id);

  const missingCaseId = `case_missing_${fixtureSuffix}`;
  await page.goto(`${baseURL}/run-console/?case=${missingCaseId}&run=${run.id}`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction((invalidCaseId) => {
    const selected = document.querySelector('[aria-label="Select case"]');
    return selected instanceof HTMLSelectElement && selected.value && selected.value !== invalidCaseId;
  }, missingCaseId);
  await page.getByRole("status", { name: "Loading" }).waitFor({ state: "detached" });
  assert.equal(await page.getByRole("status", { name: "Loading" }).count(), 0, "invalid initial case/run authority left the workspace permanently loading");

  let releaseStaleRun;
  const staleRunBarrier = new Promise((resolve) => { releaseStaleRun = resolve; });
  const holdStaleRun = async (route) => {
    await staleRunBarrier;
    await route.continue().catch((caught) => {
      if (!(caught instanceof Error) || !caught.message.includes("Route is already handled")) throw caught;
    });
  };
  const staleRunPath = (url) => url.pathname === `/api/runs/${run.id}`;
  await page.route(staleRunPath, holdStaleRun);
  const staleRunRequest = page.waitForRequest((requestValue) => new URL(requestValue.url()).pathname === `/api/runs/${run.id}`);
  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}&run=${run.id}`, { waitUntil: "domcontentloaded" });
  await staleRunRequest;
  await page.getByRole("combobox", { name: "Select case" }).selectOption(idleCase.id);
  releaseStaleRun();
  await page.unroute(staleRunPath, holdStaleRun);
  await page.waitForFunction((expectedCaseId) => {
    const url = new URL(window.location.href);
    return url.searchParams.get("case") === expectedCaseId && !url.searchParams.has("run");
  }, idleCase.id);
  await page.getByText("No current execution. Select a purpose and depth to create an immutable plan.", { exact: true }).waitFor();
  // The URL settling correctly is not enough: a stale route replay can re-attach the
  // previous issuer's run and then self-correct, which is still a wrong read.
  const boundaryUrlWrites = await page.evaluate(([boundaryCaseId, staleRunId]) => {
    const writes = window.__caosUrlWrites || [];
    const switchedAt = writes.findIndex((search) => search.includes(`case=${boundaryCaseId}`));
    return { switchedAt, reattached: switchedAt === -1 ? [] : writes.slice(switchedAt + 1).filter((search) => search.includes(`run=${staleRunId}`)) };
  }, [idleCase.id, run.id]);
  assert.notEqual(boundaryUrlWrites.switchedAt, -1, "the case boundary was never written to the URL, so the stale-run check did not run");
  assert.deepEqual(boundaryUrlWrites.reattached, [], "a stale run was re-attached to the URL after the case boundary");
  assert.equal(await page.getByRole("status", { name: "Loading" }).count(), 0, "case switch left the run console permanently loading");
  assert.equal(await page.getByRole("button", { name: "Accept analytical snapshot" }).count(), 0, "stale run data survived the case boundary");
  await page.getByRole("combobox", { name: "Select case" }).selectOption(caseRecord.id);
  await page.getByRole("region", { name: "Accepted authority" }).getByText(primaryLabel).waitFor();

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
  expectedNotFoundURL = `${baseURL}/missing-${fixtureSuffix}`;
  await page.goto(expectedNotFoundURL, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Page not found" }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Case register" }).count(), 0, "unknown route rendered the default Cases page");
  await page.goto(`${baseURL}/command-center/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  caseRequests = 0;
  authorityRequests = 0;

  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  const artifactPalette = page.getByRole("dialog", { name: "Command palette" });
  await artifactPalette.getByRole("combobox", { name: "Search commands" }).fill(artifact.id);
  await artifactPalette.getByRole("option", { name: "Open artifact ID in this case" }).click();
  await page.waitForURL((url) => url.pathname.replace(/\/$/, "") === "/sources"
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

  const rail = page.locator(".evidence-rail");
  assert.equal(
    await rail.getByText("Artifact links open the matching source rail.").count(),
    0,
    "evidence rail still renders its static policy copy",
  );
  await rail.getByText(/Pinned to source set v/).waitFor();
  assert.ok(
    await rail.locator(".evidence-rail-list li").count() > 0,
    "evidence rail lists no artifacts for an accepted snapshot",
  );



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
  await page.getByRole("region", { name: "Accepted authority" }).getByText(primaryLabel).waitFor();
  await page.getByRole("region", { name: "Accepted authority" }).getByText(/Source set v1/).waitFor();
  await page.getByRole("button", { name: /QA unavailable/ }).waitFor();

  const paletteTrigger = page.getByRole("button", { name: /Open command palette/ });
  await paletteTrigger.focus();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  const palette = page.getByRole("dialog", { name: "Command palette" });
  await palette.getByRole("combobox", { name: "Search commands" }).fill(primaryIssuer);
  await palette.getByRole("option", { name: primaryLabel }).waitFor();
  await palette.getByRole("combobox", { name: "Search commands" }).fill("src_deadbeef");
  await palette.getByRole("option", { name: /Open source ID in this case/ }).waitFor();
  await palette.getByRole("combobox", { name: "Search commands" }).fill("secret issuer");
  await palette.getByText("No authorized matches").waitFor();
  await page.keyboard.press("Escape");
  await assert.doesNotReject(() => paletteTrigger.evaluate((element) => {
    if (document.activeElement !== element) throw new Error("focus did not return to the palette trigger");
  }));

  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  const deepResearchOption = page.locator('#pathway option[value="DEEP_RESEARCH"]');
  assert.equal(await deepResearchOption.isDisabled(), true, "Deep Research was enabled before actor-specific availability resolved");
  await page.getByText("Deep Research is disabled for this deployment.", { exact: true }).waitFor();

  let caseDetailFixtureHits = 0;
  let startFixtureHits = 0;
  let runFixtureHits = 0;
  let approvalFixtureHits = 0;
  let approvedResearchPlan = false;
  let researchBriefPayload;
  let approvalPayload;
  const caseDetailFixturePath = (url) => url.pathname === `/api/cases/${caseRecord.id}`;
  const startResearchFixturePath = (url) => url.pathname === `/api/cases/${caseRecord.id}/runs`;
  const researchRunFixturePath = (url) => url.pathname === `/api/runs/${pendingResearchRun.id}`;
  const researchEventsFixturePath = (url) => url.pathname === `/api/runs/${pendingResearchRun.id}/events`;
  const approveResearchFixturePath = (url) => url.pathname === `/api/runs/${pendingResearchRun.id}/research-plan/approve`;
  const caseDetailFixtureResponse = await api.get(`/api/cases/${caseRecord.id}`);
  assert.equal(caseDetailFixtureResponse.status(), 200);
  const caseDetailFixture = await caseDetailFixtureResponse.json();
  await page.route(caseDetailFixturePath, async (route) => {
    caseDetailFixtureHits += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...caseDetailFixture, deep_research_available: true, deep_research_unavailable_reason: null }) });
  });
  await page.route(startResearchFixturePath, async (route) => {
    startFixtureHits += 1;
    researchBriefPayload = route.request().postDataJSON();
    await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify(pendingResearchRun) });
  });
  await page.route(researchRunFixturePath, async (route) => {
    runFixtureHits += 1;
    const fixture = approvedResearchPlan
      ? { ...pendingResearchRun, status: "queued", error: null, research: { ...pendingResearchRun.research, phase: "approved", approved_plan_hash: researchPlanHash } }
      : pendingResearchRun;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture) });
  });
  await page.route(researchEventsFixturePath, (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: "retry: 60000\n\n" }));
  await page.route(approveResearchFixturePath, async (route) => {
    approvalFixtureHits += 1;
    approvalPayload = route.request().postDataJSON();
    approvedResearchPlan = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...pendingResearchRun, status: "queued", error: null }) });
  });
  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}&fixture=pending-plan`, { waitUntil: "networkidle" });
  await page.getByRole("combobox", { name: "Purpose" }).selectOption("DEEP_RESEARCH");
  const depth = page.getByRole("combobox", { name: "Depth" });
  assert.equal(await depth.inputValue(), "full", "Deep Research did not force full depth");
  assert.equal(await depth.locator('option[value="screen"]').isDisabled(), true, "Deep Research left Screen selectable");
  await page.getByRole("textbox", { name: "Research question" }).fill("Can Northstar refinance its 2028 maturities?");
  await page.getByRole("textbox", { name: "Decision context" }).fill("Underwrite a first-lien position.");
  await page.getByLabel("As-of date").fill("2026-08-23");
  await page.getByRole("textbox", { name: "Time horizon" }).fill("Through 2029");
  await page.getByRole("textbox", { name: "Must-answer lines" }).fill(Array.from({ length: 11 }, (_, index) => `Question ${index + 1}`).join("\n"));
  await page.getByRole("button", { name: "Compile and run" }).click();
  await page.getByRole("alert").getByText("Research brief lists allow at most 10 nonblank lines combined, and each line is limited to 200 characters.", { exact: true }).waitFor();
  assert.equal(startFixtureHits, 0, "an over-limit research brief reached the start route");
  await page.getByRole("textbox", { name: "Must-answer lines" }).fill(" Liquidity runway? \n\n Downside breach? ");
  await page.getByRole("textbox", { name: "Exclusion lines" }).fill(" Equity valuation \n");
  await page.getByRole("button", { name: "Compile and run" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { name: "Proposed research plan" }).waitFor();
  assert.deepEqual(researchBriefPayload, {
    pathway: "DEEP_RESEARCH",
    depth: "full",
    focus_questions: [],
    research_brief: {
      research_question: "Can Northstar refinance its 2028 maturities?",
      decision_context: "Underwrite a first-lien position.",
      as_of_date: "2026-08-23",
      time_horizon: "Through 2029",
      must_answer: ["Liquidity runway?", "Downside breach?"],
      exclusions: ["Equity valuation"],
    },
  });
  const researchPlan = page.locator(".research-plan");
  await researchPlan.getByText(researchPlanHash, { exact: true }).waitFor();
  await researchPlan.getByText(researchPlanLongText, { exact: true }).waitFor();
  for (const label of ["Methodology build", "Brief digest", "Source set", "Upstream artifacts", "Scope", "ID", "Kind", "Question", "Assigned questions", "Perspective", "Hypothesis", "Evidence needs", "Source classes", "Disconfirming test", "Completion test", "Effort cap"]) {
    assert.ok(await researchPlan.getByText(label, { exact: true }).count(), `pending plan omitted ${label}`);
  }
  const definitionValue = (container, label) => container.locator("dt").filter({ hasText: new RegExp(`^${label}$`) }).locator("xpath=following-sibling::dd[1]");
  const topLevelFacts = researchPlan.locator(":scope > .research-plan-facts");
  for (const label of ["Methodology build", "Brief digest", "Source set"]) {
    assert.equal(await definitionValue(topLevelFacts, label).getByText("None", { exact: true }).count(), 1, `${label} did not expose its empty scalar`);
  }
  assert.equal(await definitionValue(topLevelFacts, "Upstream artifacts").getByText("Empty", { exact: true }).count(), 1, "empty upstream artifacts were rendered as blank space");
  assert.equal(await definitionValue(topLevelFacts, "Scope").getByText("None", { exact: true }).count(), 3, "empty scope scalars were not explicit");
  const workstreams = researchPlan.locator(".research-workstreams > li");
  assert.equal(await workstreams.count(), 2, "pending plan did not render every repeated-ID workstream");
  for (const [label, value] of [["Assigned questions", "Liquidity runway?"], ["Evidence needs", "Debt maturity schedule"], ["Source classes", "supplied_case_sources"]]) {
    assert.equal(await definitionValue(workstreams.first(), label).getByText(value, { exact: true }).count(), 2, `${label} did not preserve repeated plan values`);
    assert.equal(await definitionValue(workstreams.first(), label).getByText("None", { exact: true }).count(), 1, `${label} rendered an empty list value as blank space`);
  }
  for (const label of ["ID", "Kind", "Question", "Perspective", "Hypothesis", "Disconfirming test", "Completion test", "Effort cap"]) {
    assert.equal(await definitionValue(workstreams.nth(1), label).getByText("None", { exact: true }).count(), 1, `${label} did not expose its empty scalar`);
  }
  for (const label of ["Assigned questions", "Evidence needs", "Source classes"]) {
    assert.equal(await definitionValue(workstreams.nth(1), label).getByText("Empty", { exact: true }).count(), 1, `${label} did not expose its empty list`);
  }
  assert.equal(errors.some((message) => /children with the same key|duplicate key/i.test(message)), false, "repeated exact-plan values emitted a React duplicate-key warning");
  await page.setViewportSize({ width: 375, height: 812 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, "pending research plan causes page overflow at 375px");
  assert.ok(await researchPlan.evaluate((element) => element.scrollWidth <= element.clientWidth), "pending research plan content overflows its panel");
  const approveResearchPlan = page.getByRole("button", { name: "Approve research plan" });
  await approveResearchPlan.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("status").getByText("queued", { exact: true }).waitFor();
  assert.deepEqual(approvalPayload, { plan_hash: researchPlanHash });
  assert.ok(caseDetailFixtureHits > 0, "pending-plan case detail fixture was not exercised");
  assert.ok(startFixtureHits > 0, "pending-plan start fixture was not exercised");
  assert.ok(runFixtureHits > 0, "pending-plan run fixture was not exercised");
  assert.ok(approvalFixtureHits > 0, "pending-plan approval fixture was not exercised");
  await page.unroute(caseDetailFixturePath);
  await page.unroute(startResearchFixturePath);
  await page.unroute(researchRunFixturePath);
  await page.unroute(researchEventsFixturePath);
  await page.unroute(approveResearchFixturePath);
  await page.setViewportSize({ width: 1440, height: 1000 });

  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}&run=${run.id}`, { waitUntil: "networkidle" });
  let markStartRunIntercepted;
  const startRunIntercepted = new Promise((resolve) => { markStartRunIntercepted = resolve; });
  let releaseStartRun;
  const startRunBarrier = new Promise((resolve) => { releaseStartRun = resolve; });
  const startRunPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/runs`;
  const holdStartRun = async (route) => {
    const heldResponse = await route.fetch();
    markStartRunIntercepted();
    await startRunBarrier;
    await route.fulfill({ response: heldResponse });
  };
  await page.route(startRunPath, holdStartRun);
  const nextRunResponsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/cases/${caseRecord.id}/runs`,
  );
  await page.getByRole("button", { name: "Compile and run" }).click();
  await startRunIntercepted;
  await page.getByRole("combobox", { name: "Select case" }).selectOption(raceCase.id);
  releaseStartRun();
  const nextRunResponse = await nextRunResponsePromise;
  assert.equal(nextRunResponse.status(), 202);
  const nextRun = await nextRunResponse.json();
  await nextRunResponse.finished();
  await page.unroute(startRunPath, holdStartRun);
  await page.waitForFunction(({ expectedCaseId, rejectedRunId }) => {
    const url = new URL(window.location.href);
    return url.searchParams.get("case") === expectedCaseId && url.searchParams.get("run") !== rejectedRunId;
  }, { expectedCaseId: raceCase.id, rejectedRunId: nextRun.id });
  await page.getByRole("region", { name: "Accepted authority" }).getByText(raceLabel).waitFor();
  assert.equal(new URL(page.url()).searchParams.get("run"), crossCaseRun.id, "late Case A run creation replaced Case B execution authority");
  await page.goto(`${baseURL}/run-console/?case=${caseRecord.id}&run=${nextRun.id}`, { waitUntil: "networkidle" });
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
  const secondAccepted = await acceptanceResponse.json();
  await acceptanceResponse.finished();
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
  const authority = page.getByRole("region", { name: "Accepted authority" });
  await authority.getByText(raceLabel).waitFor();
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

  const modelBuildId = `model_${fixtureSuffix}`;
  let inventoryModelBuildId = modelBuildId;
  const modelRequirements = ["CP-1", "CP-1A", "CP-1B", "CP-2", "CP-2A", "CP-2B"].map((module_id) => ({ module_id, status: "READY", digest: "a".repeat(64) }));
  let modelState = "READY_TO_BUILD";
  let modelExportState = "NOT_REQUESTED";
  let modelGets = 0;
  let modelPosts = 0;
  let exportPosts = 0;
  let worksheetGets = 0;
  let modelGetDelay = 0;
  let modelGetsInFlight = 0;
  let maxModelGetsInFlight = 0;
  let modelLoadFails = false;
  const modelBuild = () => ({ id: inventoryModelBuildId, case_id: caseRecord.id, accepted_run_id: run.id, accepted_snapshot_id: accepted.id, source_set_id: "set-model", input_fingerprint: "b".repeat(64), status: modelState, queued_at: "2026-08-24T12:00:00Z", started_at: null, completed_at: modelState === "READY" ? "2026-08-24T12:01:00Z" : null, error: modelState === "FAILED" ? { code: "MODEL_CALCULATION_FAILED", detail: "The model calculation did not complete." } : null, export: { status: modelExportState, error: modelExportState === "FAILED" ? { code: "MODEL_EXPORT_FAILED", detail: "The XLSX export did not complete." } : null }, qa: modelState === "READY" ? { status: "PASS", semantic_check_count: 20, formula_count: 4, worksheet_cell_count: 12 } : undefined, payload_digest: modelState === "READY" ? "c".repeat(64) : undefined });
  const modelInventory = () => ({
    readiness: {
      status: modelState,
      module_id: "CP-MODEL",
      accepted_snapshot: modelState === "NOT_READY" ? null : { id: accepted.id, run_id: run.id, digest: accepted.digest },
      source_set: modelState === "NOT_READY" ? null : { id: "set-model", version: 1, digest: "d".repeat(64) },
      requirements: modelState === "NOT_READY" ? modelRequirements.map(({ module_id }) => ({ module_id, status: "MISSING" })) : modelRequirements,
      blockers: modelState === "NOT_READY" ? [{ code: "ACCEPTED_FULL_CREDIT_REQUIRED", detail: "Accept a completed Full Credit run before building a model." }] : [],
      build: ["QUEUED", "BUILDING", "READY", "FAILED"].includes(modelState) ? modelBuild() : null,
    },
    builds: ["QUEUED", "BUILDING", "READY", "FAILED"].includes(modelState) ? [modelBuild(), { ...modelBuild(), id: `model_history_${fixtureSuffix}`, status: "FAILED", input_fingerprint: "e".repeat(64) }] : [],
  });
  const modelWorksheet = {
    build_id: modelBuildId,
    input_fingerprint: "b".repeat(64),
    payload_digest: "c".repeat(64),
    qa: { status: "PASS", semantic_check_count: 20, formula_count: 4, worksheet_cell_count: 12 },
    payload: {
      schema_version: "caos.model.worksheet.v1",
      identity: { issuer_id: "northstar", issuer_name: primaryIssuer, analysis_date: "2026-08-24" },
      tabs: ["Credit Snapshot", "Model", "KPIs"].map((name) => ({
        id: name.toUpperCase().replaceAll(" ", "_"), name, max_row: 2, max_column: 2, freeze_panes: "B2", merged_cells: [],
        columns: [{ column: 1, letter: "A", width: 22, hidden: false }, { column: 2, letter: "B", width: 14, hidden: false }],
        cells: [
          { address: "A1", row: 1, column: 1, value: name, value_type: "text", formula: null, semantic_id: null, owner: null, write_class: null, period_id: null, source_refs: null, number_format: "General", style: { bold: true, italic: false, fill: "0A2E63", align: "left", wrap: false } },
          { address: "A2", row: 2, column: 1, value: 1160, value_type: "number", formula: null, semantic_id: "account::revenue::FY2025", owner: "CP-1", write_class: "SOURCE", period_id: "FY2025", source_refs: "SRC-1 | page 42 | 2026-08-24", number_format: "#,##0.0", style: { bold: false, italic: false, fill: "FFF4CC", align: "right", wrap: false } },
          { address: "B2", row: 2, column: 2, value: 4.2, value_type: "formula", formula: "=A2/276", semantic_id: "metric::leverage::FY2025", owner: "CP-MODEL", write_class: "FORMULA", period_id: "FY2025", source_refs: null, number_format: "0.0x", style: { bold: false, italic: false, fill: null, align: "right", wrap: false } },
        ],
      })),
    },
  };
  const modelsPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/models`;
  const worksheetPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/models/${modelBuildId}/worksheet`;
  const exportPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/models/${modelBuildId}/export`;
  await page.route(modelsPath, async (route) => {
    if (route.request().method() === "POST") {
      modelPosts += 1; modelState = "QUEUED";
      await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ build: modelBuild(), created: true }) });
      return;
    }
    modelGets += 1;
    modelGetsInFlight += 1;
    maxModelGetsInFlight = Math.max(maxModelGetsInFlight, modelGetsInFlight);
    if (modelGetDelay) await new Promise((resolve) => setTimeout(resolve, modelGetDelay));
    modelGetsInFlight -= 1;
    if (modelLoadFails) {
      await route.fulfill({ status: 200, contentType: "application/json", body: "not-json" });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(modelInventory()) });
  });
  await page.route(worksheetPath, (route) => {
    worksheetGets += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(modelWorksheet) });
  });
  await page.route(exportPath, async (route) => {
    exportPosts += 1; modelExportState = "QUEUED";
    await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ build: modelBuild(), queued: true }) });
  });
  await page.goto(`${baseURL}/model-builder/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  const buildButton = page.getByRole("button", { name: "Build model" });
  await buildButton.click();
  await page.getByText("Build queued", { exact: true }).waitFor();
  await buildButton.click({ force: true }).catch(() => {});
  assert.equal(modelPosts, 1, "disabled model control submitted a duplicate build");
  modelState = "BUILDING";
  modelGetDelay = 1700;
  await page.getByText("Calculating worksheet", { exact: true }).waitFor({ timeout: 4000 });
  modelGetDelay = 0;
  assert.equal(maxModelGetsInFlight, 1, "Model Builder overlapped slow poll requests");
  modelState = "READY";
  await page.getByRole("tab", { name: "Credit Snapshot" }).waitFor({ timeout: 4000 });
  const terminalGets = modelGets;
  await page.waitForTimeout(1800);
  assert.equal(modelGets, terminalGets, "Model Builder kept polling after READY");
  const firstGridCell = page.locator('td[data-address="A1"]');
  await firstGridCell.focus();
  await page.keyboard.press("ArrowDown");
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-address")), "A2", "worksheet ArrowDown did not move one row");
  await page.keyboard.press("ArrowRight");
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-address")), "B2", "worksheet ArrowRight did not move one column");
  await page.keyboard.press("Enter");
  await page.locator("#model-cell-lineage").getByText("=A2/276", { exact: true }).waitFor();
  const sourceCell = page.getByRole("button", { name: /Show lineage for account::revenue/ });
  await sourceCell.click();
  await page.locator("#model-cell-lineage").getByText(/SRC-1 \| page 42/).waitFor();
  const firstTab = page.getByRole("tab", { name: "Credit Snapshot" });
  await firstTab.focus();
  await page.keyboard.press("ArrowRight");
  assert.equal(await page.getByRole("tab", { name: "Model" }).getAttribute("aria-selected"), "true");
  const formulaCell = page.getByRole("button", { name: /Show lineage for metric::leverage/ });
  await formulaCell.focus();
  await page.keyboard.press("Enter");
  await page.locator("#model-cell-lineage").getByText("=A2/276", { exact: true }).waitFor();
  assert.equal(await page.getByRole("region", { name: "Model build history" }).locator("tbody tr").count(), 2, "immutable model history was not rendered");
  const terminalWorksheetGets = worksheetGets;
  await page.getByRole("button", { name: "Export XLSX" }).click();
  await page.getByRole("button", { name: "Export queued" }).waitFor();
  assert.equal(exportPosts, 1);
  modelExportState = "READY";
  await page.getByRole("link", { name: "Download XLSX" }).waitFor({ timeout: 4000 });
  const exportTerminalGets = modelGets;
  await page.waitForTimeout(1800);
  assert.equal(modelGets, exportTerminalGets, "Model Builder kept polling after export READY");
  assert.equal(worksheetGets, terminalWorksheetGets, "export polling reloaded an immutable worksheet");
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, "Model Builder causes page-level horizontal overflow at 390px");
  await page.setViewportSize({ width: 1440, height: 1000 });
  modelState = "READY"; modelExportState = "FAILED";
  await page.goto(`${baseURL}/model-builder/?case=${caseRecord.id}&state=export-failed`, { waitUntil: "networkidle" });
  await page.getByText("MODEL_EXPORT_FAILED", { exact: true }).waitFor();
  await page.getByRole("tab", { name: "Credit Snapshot" }).waitFor();
  for (const [state, text] of [["FAILED", "MODEL_CALCULATION_FAILED"], ["NOT_READY", "ACCEPTED FULL CREDIT REQUIRED"]]) {
    modelState = state; modelExportState = "NOT_REQUESTED";
    await page.goto(`${baseURL}/model-builder/?case=${caseRecord.id}&state=${state}`, { waitUntil: "networkidle" });
    await page.getByText(text, { exact: true }).waitFor();
  }
  modelLoadFails = true;
  await page.goto(`${baseURL}/model-builder/?case=${caseRecord.id}&state=load-error`, { waitUntil: "networkidle" });
  await page.getByText("Unavailable", { exact: true }).waitFor();
  modelLoadFails = false;
  await page.unroute(modelsPath);
  await page.unroute(worksheetPath);
  await page.unroute(exportPath);

  modelState = "READY"; modelExportState = "READY";
  await page.route(modelsPath, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(modelInventory()) }));

  await page.evaluate((caseId) => window.sessionStorage.setItem(`caos-report-draft:${caseId}`, JSON.stringify({ evidenceIds: 17 })), caseRecord.id);
  await page.goto(`${baseURL}/report-studio/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Compose" }).waitFor();
  await page.getByRole("heading", { name: `${caseRecord.issuer} — ${caseRecord.name}` }).waitFor();
  assert.equal(
    await page.getByRole("heading", { name: "Paper proof", exact: true }).count(),
    0,
    "the filed sheet is still titled by the panel name rather than the case",
  );
  assert.equal(await page.locator(".evidence-option", { hasText: "earnings.txt" }).count(), 1, "Report Studio omitted a case source from the evidence picker");
  assert.equal(await page.evaluate((caseId) => window.sessionStorage.getItem(`caos-report-draft:${caseId}`), caseRecord.id), null, "Report Studio retained an invalid local draft");
  const includeReadyModel = page.getByRole("checkbox", { name: /Include ready model/ });
  const includeReadyExport = page.getByRole("checkbox", { name: /Include ready XLSX export/ });
  assert.equal(await includeReadyExport.isDisabled(), true, "Report Studio enabled export attachment before model selection");
  await includeReadyModel.check();
  assert.equal(await includeReadyExport.isDisabled(), false, "Report Studio did not expose the selected model's ready export");
  assert.equal(await includeReadyExport.isChecked(), false, "Report Studio silently selected the ready export");
  await includeReadyExport.check();

  let reportInputPayload;
  let freezePayload;
  const reportInputsPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/report-inputs`;
  const reportFreezePath = (url) => url.pathname === `/api/cases/${caseRecord.id}/reports/freeze`;
  const reportsGetPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/reports`;
  const frozenReportFixture = {
    status: "PENDING_APPROVAL",
    digest: "f3f75eb17981f75a3109fde54e2ad4e277928607e40421e633dc0af2e037dfe2",
    snapshot_digest: "af8ea7238bea6e8472430ab7c711b0d33a87f078ec8a04a8aac740ad73a4c868",
    markdown: [
      "# CAOS Credit Snapshot",
      "",
      "Snapshot digest: `af8ea7238bea6e84`",
      "",
      "## Recommendation matrix",
      "",
      "| Instrument | Recommendation | Primary |",
      "| --- | --- | --- |",
      "| Northstar 1L 2029 | MARKET WEIGHT | Yes |",
      "",
    ].join("\n"),
  };
  await page.route(reportInputsPath, async (route) => {
    reportInputPayload = route.request().postDataJSON();
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ thesis: { version: 101 }, recommendations: { version: 202 } }) });
  });
  await page.route(reportFreezePath, async (route) => {
    freezePayload = route.request().postDataJSON();
    inventoryModelBuildId = `model_replacement_${fixtureSuffix}`;
    await route.fulfill({ status: 201, contentType: "application/json", body: "{}" });
  });
  await page.route(reportsGetPath, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(frozenReportFixture) });
  });
  await page.getByRole("textbox", { name: "Core thesis" }).fill("Defensible test thesis");
  await page.getByRole("textbox", { name: "Primary instrument" }).fill("Northstar 1L 2029");
  await page.getByRole("textbox", { name: "Evidence IDs" }).fill(secondAccepted.id);
  await page.getByRole("button", { name: "Freeze report snapshot" }).click();
  await page.getByRole("status").getByText("Frozen report pending Approver ratification.").waitFor();
  assert.equal(await includeReadyModel.isChecked(), false, "Report Studio transferred model consent to a replacement build");
  assert.equal(await includeReadyExport.isChecked(), false, "Report Studio transferred XLSX consent to a replacement build");

  const proof = page.locator(".report-proof-stage");
  await proof.locator("table.filed-table th", { hasText: "Instrument" }).waitFor();
  assert.equal(await proof.locator("pre").count(), 0, "filed proof still renders a raw <pre> dump");
  const proofText = await proof.locator(".filed-body").innerText();
  assert.ok(!proofText.includes("| --- |"), "filed proof still contains raw markdown table syntax");
  assert.ok(!/(^|\n)#{1,3}\s/.test(proofText), "filed proof still contains a raw markdown heading");
  assert.ok(!proofText.includes("`"), "filed proof still contains raw markdown code fences");
  assert.deepEqual(reportInputPayload.thesis.evidence_ids, [secondAccepted.id], "a valid case snapshot outside the visible picker was rejected client-side");
  assert.deepEqual(freezePayload, { thesis_version: 101, recommendation_version: 202, model_build_id: modelBuildId, include_model_export: true });
  await page.unroute(reportInputsPath);
  await page.unroute(reportFreezePath);
  await page.unroute(reportsGetPath);
  await page.unroute(modelsPath);

  const reportSourcesPath = (url) => url.pathname === `/api/cases/${caseRecord.id}/sources`;
  await page.route(reportSourcesPath, (route) => route.fulfill({ status: 200, contentType: "application/json", body: "not-json" }));
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("alert").getByText(/Evidence inventory unavailable/).waitFor();
  assert.equal(await page.getByRole("textbox", { name: "Core thesis" }).count(), 1, "evidence inventory failure blocked the report editor");
  await page.unroute(reportSourcesPath);

  let releaseSlowModel;
  let markSlowModelStarted;
  const slowModel = new Promise((resolve) => { releaseSlowModel = resolve; });
  const slowModelStarted = new Promise((resolve) => { markSlowModelStarted = resolve; });
  await page.route(modelsPath, async (route) => {
    markSlowModelStarted();
    await slowModel;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(modelInventory()) }).catch(() => {});
  });
  await page.getByRole("combobox", { name: "Select case" }).selectOption(raceCase.id);
  await page.getByText("Freeze unavailable", { exact: true }).waitFor();
  await page.getByRole("combobox", { name: "Select case" }).selectOption(caseRecord.id);
  await slowModelStarted;
  await page.getByRole("combobox", { name: "Select case" }).selectOption(raceCase.id);
  await page.getByText("Freeze unavailable", { exact: true }).waitFor();
  releaseSlowModel();
  await page.waitForTimeout(100);
  assert.equal(await page.getByRole("combobox", { name: "Select case" }).inputValue(), raceCase.id, "stale report refresh changed the selected case");
  await page.getByText("No ready model", { exact: true }).waitFor();
  await page.unroute(modelsPath);
  assert.equal(await page.getByRole("button", { name: "Freeze report snapshot" }).isDisabled(), true, "Report Studio allowed freeze without an accepted snapshot");

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
  await evidence.getByRole("link", { name: "Open full source" }).click();
  await page.waitForURL((url) => url.pathname.replace(/\/$/, "") === "/sources" && url.hash === `#source-${source.id}`);
  await evidence.waitFor({ state: "hidden" });
  await page.locator(`#source-${source.id}`).waitFor();

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

  await page.goto(`${baseURL}/cases/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  const registerMeta = page.locator(".cases-register .panel-meta");
  const caseSearch = page.getByRole("searchbox", { name: "Search cases" });
  await caseSearch.fill("zzzz-no-such-issuer");
  await page.getByText("No cases match this search and filter.", { exact: true }).waitFor();
  assert.ok(
    (await registerMeta.innerText()).startsWith("0 of "),
    "case register count did not follow the search filter",
  );
  await caseSearch.fill("");
  const snapshotFilter = page.getByRole("combobox", { name: "Snapshot" });
  await snapshotFilter.selectOption("accepted");
  await page.locator(".cases-register tbody tr").first().waitFor();
  await snapshotFilter.selectOption("all");

  await page.goto(`${baseURL}/deep-dive/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  const caseContext = page.locator(".case-context");
  await page.setViewportSize({ width: 720, height: 900 });
  await caseContext.locator(".optional").waitFor({ state: "visible" });
  await caseContext.locator(".mono").first().waitFor({ state: "visible" });
  await page.setViewportSize({ width: 390, height: 844 });
  await caseContext.locator(".mono").first().waitFor({ state: "visible" });
  assert.ok(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    "page overflows horizontally at 390px",
  );
  await page.setViewportSize({ width: 1280, height: 720 });
  await context.close();

  const reduced = await browser.newContext({
    viewport: { width: 1024, height: 768 },
    reducedMotion: "reduce",
    extraHTTPHeaders: identityHeaders,
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

  const narrow = await browser.newContext({
    viewport: { width: 375, height: 812 },
    hasTouch: true,
    extraHTTPHeaders: identityHeaders,
  });
  const narrowPage = await narrow.newPage();
  await narrowPage.goto(`${baseURL}/deep-dive/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  // A palette route whose client payload 404s degrades into a full document load, but only
  // after the router has pushed the destination URL. `waitForURL` then resolves on that
  // pushed entry and the following `goto` races the fallback load, which cancels it.
  const narrowDocumentLoads = [];
  narrowPage.on("request", (requestValue) => {
    if (requestValue.isNavigationRequest()) narrowDocumentLoads.push(requestValue.url());
  });
  await narrowPage.getByRole("button", { name: "Open command palette" }).click();
  const narrowPalette = narrowPage.getByRole("dialog", { name: "Command palette" });
  await narrowPalette.getByRole("combobox", { name: "Search commands" }).fill("Case register");
  await narrowPalette.getByRole("option", { name: "Open Case register" }).click();
  await narrowPage.waitForURL((url) => url.pathname.replace(/\/$/, "") === "/cases" && url.searchParams.get("case") === caseRecord.id);
  await narrowPage.getByRole("button", { name: "Open command palette" }).click();
  await narrowPalette.getByRole("combobox", { name: "Search commands" }).fill("Run");
  await narrowPalette.getByRole("option", { name: "Open Run", exact: true }).click();
  await narrowPage.waitForURL((url) => url.pathname.replace(/\/$/, "") === "/run-console"
    && url.searchParams.get("case") === caseRecord.id
    && url.searchParams.get("run") === nextRun.id);
  assert.deepEqual(narrowDocumentLoads, [], "command palette navigation fell back to a full document load");
  await narrowPage.goto(`${baseURL}/report-studio/?case=${caseRecord.id}`, { waitUntil: "networkidle" });
  assert.equal(await narrowPage.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, "Report Studio causes page-level horizontal overflow at 375px");


  await narrow.close();
} finally {
  await browser.close();
  await api.dispose();
}
