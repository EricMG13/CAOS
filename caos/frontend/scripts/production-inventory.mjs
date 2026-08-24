import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { performance } from "node:perf_hooks";
import { chromium, request } from "playwright";

const baseURL = process.env.CAOS_URL || "http://127.0.0.1:8000";
const edgeSecret = process.env.CAOS_EDGE_SECRET;
assert.ok(edgeSecret, "CAOS_EDGE_SECRET is required for the production inventory");

const denseCaseId = process.env.CAOS_CASE_ID || "case_d5e3151a64554296";
const analystUser = process.env.CAOS_ANALYST_USER || "analyst.qa@local.invalid";
const approverUser = process.env.CAOS_PM_USER || "pm.qa@local.invalid";
const adminUser = process.env.CAOS_ADMIN_USER || "admin.qa@local.invalid";
const readerUser = process.env.CAOS_READER_USER || "reader.qa@local.invalid";
const maxBurstP95Ms = Number(process.env.CAOS_MAX_BURST_P95_MS || 1500);
const maxPostLoadMs = Number(process.env.CAOS_MAX_POST_LOAD_MS || 500);
assert.ok(Number.isFinite(maxBurstP95Ms) && maxBurstP95Ms > 0, "CAOS_MAX_BURST_P95_MS must be positive");
assert.ok(Number.isFinite(maxPostLoadMs) && maxPostLoadMs > 0, "CAOS_MAX_POST_LOAD_MS must be positive");

const headersFor = (user, groups) => ({
  "x-edge-authorization": edgeSecret,
  "x-forwarded-user": user,
  "x-forwarded-email": user,
  "x-forwarded-groups": groups,
});
const analystHeaders = headersFor(analystUser, "caos-analyst");
const approverHeaders = headersFor(approverUser, "caos-approver");
const adminHeaders = headersFor(adminUser, "caos-admin");
const readerHeaders = headersFor(readerUser, "caos-reader");
const exactURL = (path) => new URL(path, baseURL).href;
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const expectedPathways = [
  "COVENANT_REFINANCING",
  "DEEP_RESEARCH",
  "DISTRESSED_RESTRUCTURING",
  "EARNINGS_UPDATE",
  "FULL_CREDIT",
  "RELATIVE_VALUE",
];
const destinations = [
  ["cases", "Cases"],
  ["sources", "Sources"],
  ["run-console", "Run Console"],
  ["deep-dive", "Deep-Dive"],
  ["rv-screener", "RV Screener"],
  ["command-center", "Command Center"],
  ["model-builder", "Model Builder"],
  ["report-studio", "Report Studio"],
];

async function waitForRun(api, runId) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const response = await api.get(`/api/runs/${runId}`);
    assert.equal(response.status(), 200);
    const run = await response.json();
    if (["succeeded", "failed", "paused"].includes(run.status)) return run;
    await sleep(50);
  }
  assert.fail(`run ${runId} did not reach a terminal state`);
}

async function addMember(adminApi, caseId, subject, role) {
  const response = await adminApi.post(`/api/cases/${caseId}/members`, { data: { subject, role } });
  assert.equal(response.status(), 201);
}

async function probeLoading(context, role, url, endpoint) {
  const page = await context.newPage();
  let hits = 0;
  let markSeen;
  let release;
  const seen = new Promise((resolve) => { markSeen = resolve; });
  const barrier = new Promise((resolve) => { release = resolve; });
  const predicate = (candidate) => candidate.href === exactURL(endpoint);
  await page.route(predicate, async (route) => {
    hits += 1;
    markSeen();
    await barrier;
    await route.continue();
  });
  try {
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await seen;
    await page.getByRole("status", { name: "Loading" }).first().waitFor();
  } finally {
    release();
    await page.waitForLoadState("networkidle");
    await page.unroute(predicate);
    await page.close();
  }
  assert.ok(hits > 0, `${role} loading probe did not intercept ${endpoint}`);
  return { role, endpoint, hits };
}

async function probeError(context, role, url, endpoint, expectedText = "Unable to load this view.") {
  const page = await context.newPage();
  let hits = 0;
  const predicate = (candidate) => candidate.href === exactURL(endpoint);
  await page.route(predicate, async (route) => {
    hits += 1;
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "production inventory state probe" }),
    });
  });
  try {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.getByText(expectedText, { exact: true }).first().waitFor();
  } finally {
    await page.unroute(predicate);
    await page.close();
  }
  assert.ok(hits > 0, `${role} error probe did not intercept ${endpoint}`);
  return { role, endpoint, hits };
}

async function probeEmpty(context, role, url, expectedText, endpoint) {
  const page = await context.newPage();
  let hits = 0;
  const predicate = endpoint ? (candidate) => candidate.href === exactURL(endpoint) : null;
  if (predicate) {
    await page.route(predicate, async (route) => {
      hits += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
  }
  try {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.getByText(expectedText, { exact: true }).first().waitFor();
  } finally {
    if (predicate) await page.unroute(predicate);
    await page.close();
  }
  if (endpoint) assert.ok(hits > 0, `${role} empty probe did not intercept ${endpoint}`);
  return { role, expectedText, hits };
}

async function inventoryLoadedRoute(context, role, slug, title) {
  const page = await context.newPage();
  try {
    await page.goto(`${baseURL}/${slug}/?case=${denseCaseId}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: title, level: 1 }).waitFor();
    await page.locator("#main-content .state-skeleton").waitFor({ state: "detached" });
    const result = await page.evaluate(({ roleName, routeSlug }) => {
      const main = document.querySelector("#main-content");
      const visible = (element) => {
        const style = getComputedStyle(element);
        const bounds = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && bounds.width > 0 && bounds.height > 0;
      };
      const controls = [...main.querySelectorAll("button,input,select,textarea,summary,a")].filter(visible);
      const kinds = {};
      for (const control of controls) kinds[control.tagName.toLowerCase()] = (kinds[control.tagName.toLowerCase()] || 0) + 1;
      return {
        role: roleName,
        route: routeSlug,
        controls: controls.length,
        kinds,
        alerts: [...main.querySelectorAll('[role="alert"]')].filter(visible).length,
        loading: main.querySelectorAll(".state-skeleton").length,
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    }, { roleName: role, routeSlug: slug });
    assert.equal(result.alerts, 0, `${role} ${slug} has an unexpected alert`);
    assert.equal(result.loading, 0, `${role} ${slug} has a stuck loader`);
    assert.equal(result.overflow, false, `${role} ${slug} overflows horizontally`);

    if (slug === "cases") {
      await page.getByRole("button", { name: "Create case" }).waitFor();
      await page.getByRole("button", { name: "Upload and version source set" }).waitFor();
    } else if (slug === "sources") {
      await page.getByRole("button", { name: "Ingest safely" }).waitFor();
      assert.ok(await page.locator("#main-content summary").count() >= 100);
    } else if (slug === "run-console") {
      await page.getByRole("button", { name: "Compile and run" }).waitFor();
      assert.deepEqual(await page.getByLabel("Purpose").locator("option").evaluateAll((options) => options.map((option) => option.value).sort()), expectedPathways);
      assert.deepEqual(await page.getByLabel("Depth").locator("option").evaluateAll((options) => options.map((option) => option.value).sort()), ["full", "screen"]);
    } else if (slug === "deep-dive") {
      await page.getByRole("link", { name: "Open source rail" }).first().waitFor();
    } else if (slug === "rv-screener") {
      await page.getByRole("button", { name: "Add row" }).waitFor();
      await page.getByRole("button", { name: "Version market universe" }).waitFor();
      await page.getByText("50 excluded rows", { exact: true }).waitFor();
    } else if (slug === "command-center") {
      await page.getByRole("heading", { name: "Synthetic Dense Issuer" }).waitFor();
    } else if (slug === "model-builder") {
      await page.getByText("CANONICAL MODEL INPUTS INVALID", { exact: true }).waitFor();
    } else if (slug === "report-studio") {
      await page.getByRole("button", { name: "Freeze report snapshot" }).waitFor();
      for (const name of ["Markdown", "PDF", "XLSX"]) await page.getByRole("link", { name, exact: true }).waitFor();
    }
    return result;
  } finally {
    await page.close();
  }
}

function percentile(sorted, fraction) {
  return sorted[Math.max(0, Math.ceil(sorted.length * fraction) - 1)];
}

async function runLoadStage(headers, workers, paths) {
  const timings = [];
  let failures = 0;
  let next = 0;
  const runWorker = async () => {
    while (next < 30) {
      const index = next;
      next += 1;
      const started = performance.now();
      const response = await fetch(exactURL(paths[index % paths.length]), { headers });
      await response.arrayBuffer();
      timings.push(performance.now() - started);
      if (response.status !== 200) failures += 1;
    }
  };
  await Promise.all(Array.from({ length: workers }, runWorker));
  timings.sort((left, right) => left - right);
  return {
    workers,
    requests: timings.length,
    failures,
    p50_ms: Number(percentile(timings, 0.5).toFixed(1)),
    p95_ms: Number(percentile(timings, 0.95).toFixed(1)),
    max_ms: Number(timings.at(-1).toFixed(1)),
  };
}

const analystApi = await request.newContext({ baseURL, extraHTTPHeaders: analystHeaders });
const approverApi = await request.newContext({ baseURL, extraHTTPHeaders: approverHeaders });
const adminApi = await request.newContext({ baseURL, extraHTTPHeaders: adminHeaders });
const readerApi = await request.newContext({ baseURL, extraHTTPHeaders: readerHeaders });
const browser = await chromium.launch({ headless: true });
const contexts = [];

try {
  assert.equal((await (await analystApi.get("/api/me")).json()).role, "ANALYST");
  assert.equal((await (await approverApi.get("/api/me")).json()).role, "APPROVER");
  assert.equal((await (await adminApi.get("/api/me")).json()).role, "ADMIN");
  assert.equal((await (await readerApi.get("/api/me")).json()).role, "READER");

  const denseDetailResponse = await analystApi.get(`/api/cases/${denseCaseId}`);
  assert.equal(denseDetailResponse.status(), 200);
  const denseDetail = await denseDetailResponse.json();
  assert.equal(denseDetail.issuer, "Synthetic Dense Issuer");
  assert.ok(denseDetail.source_count >= 100);
  const denseRuns = await (await analystApi.get(`/api/cases/${denseCaseId}/runs`)).json();
  assert.deepEqual([...new Set(denseRuns.map((run) => run.plan.pathway))].sort(), expectedPathways);
  assert.ok(expectedPathways.every((pathway) => denseRuns.some((run) => run.plan.pathway === pathway
    && run.status === "succeeded"
    && run.accepted_snapshot_id
    && run.nodes.length > 0
    && run.nodes.every((node) => node.status === "succeeded" && node.artifact_id))));
  const denseRV = await (await analystApi.get(`/api/cases/${denseCaseId}/rv`)).json();
  assert.equal(denseRV.rows.length, 250);
  assert.equal(denseRV.excluded.length, 50);

  const analystContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, extraHTTPHeaders: analystHeaders });
  contexts.push(analystContext);
  const journeyPage = await analystContext.newPage();
  const suffix = randomUUID().slice(0, 8);
  const issuer = `Inventory-${suffix}`;
  const caseName = "Production inventory journey";
  let journeyCase;
  let firstSource;
  let firstRun;
  try {
    await journeyPage.goto(`${baseURL}/cases/`, { waitUntil: "networkidle" });
    await journeyPage.getByLabel("Case name").fill(caseName);
    await journeyPage.getByLabel("Issuer").fill(issuer);
    await journeyPage.getByLabel("Sector").fill("Synthetic services");
    const createResponse = journeyPage.waitForResponse((response) => response.url() === exactURL("/api/cases") && response.request().method() === "POST");
    await journeyPage.getByRole("button", { name: "Create case" }).click();
    const created = await createResponse;
    assert.equal(created.status(), 201);
    journeyCase = await created.json();
    await journeyPage.getByRole("region", { name: "Accepted authority" }).getByText(`${issuer} / ${caseName}`, { exact: true }).waitFor();

    const caseUploadPath = `/api/cases/${journeyCase.id}/sources`;
    await journeyPage.getByLabel("Source file").setInputFiles({
      name: `case-intake-${suffix}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.from("Synthetic only. Revenue 1200. EBITDA 240. Net debt 960."),
    });
    const caseUploadResponse = journeyPage.waitForResponse((response) => response.url() === exactURL(caseUploadPath) && response.request().method() === "POST");
    await journeyPage.getByRole("button", { name: "Upload and version source set" }).click();
    const uploaded = await caseUploadResponse;
    assert.equal(uploaded.status(), 201);
    firstSource = await uploaded.json();
    await journeyPage.getByText("READY", { exact: true }).waitFor();

    await journeyPage.goto(`${baseURL}/sources/?case=${journeyCase.id}`, { waitUntil: "networkidle" });
    await journeyPage.getByLabel("Source file").setInputFiles({
      name: `source-workspace-${suffix}.md`,
      mimeType: "text/markdown",
      buffer: Buffer.from("# Synthetic source\n\nLiquidity remains adequate under the synthetic downside case."),
    });
    const sourceUploadResponse = journeyPage.waitForResponse((response) => response.url() === exactURL(caseUploadPath) && response.request().method() === "POST");
    await journeyPage.getByRole("button", { name: "Ingest safely" }).click();
    assert.equal((await sourceUploadResponse).status(), 201);
    const summary = journeyPage.getByText(`source-workspace-${suffix}.md`, { exact: true });
    await summary.waitFor();
    await summary.click();
    await journeyPage.getByText("Liquidity remains adequate under the synthetic downside case.", { exact: true }).waitFor();

    await journeyPage.goto(`${baseURL}/run-console/?case=${journeyCase.id}`, { waitUntil: "networkidle" });
    assert.deepEqual(await journeyPage.getByLabel("Purpose").locator("option").evaluateAll((options) => options.map((option) => option.value).sort()), expectedPathways);
    await journeyPage.getByLabel("Purpose").selectOption("EARNINGS_UPDATE");
    await journeyPage.getByLabel("Depth").selectOption("screen");
    const startResponse = journeyPage.waitForResponse((response) => response.url() === exactURL(`/api/cases/${journeyCase.id}/runs`) && response.request().method() === "POST");
    await journeyPage.getByRole("button", { name: "Compile and run" }).click();
    const started = await startResponse;
    assert.equal(started.status(), 202);
    firstRun = await started.json();
    assert.equal((await waitForRun(analystApi, firstRun.id)).status, "succeeded");
    const acceptButton = journeyPage.getByRole("button", { name: "Accept analytical snapshot" });
    await acceptButton.waitFor();
    journeyPage.once("dialog", (dialog) => void dialog.accept());
    const acceptResponse = journeyPage.waitForResponse((response) => response.url() === exactURL(`/api/runs/${firstRun.id}/accept`) && response.request().method() === "POST");
    await acceptButton.click();
    assert.equal((await acceptResponse).status(), 200);

    const nextStart = await analystApi.post(`/api/cases/${journeyCase.id}/runs`, { data: { pathway: "RELATIVE_VALUE", depth: "screen", focus_questions: [] } });
    assert.equal(nextStart.status(), 202);
    const nextRun = await nextStart.json();
    assert.equal((await waitForRun(analystApi, nextRun.id)).status, "succeeded");
    assert.equal((await analystApi.post(`/api/runs/${nextRun.id}/accept`)).status(), 200);
    const preSwitch = await (await analystApi.get(`/api/cases/${journeyCase.id}/snapshot`)).json();
    assert.equal(preSwitch.switch_required, true);
    await journeyPage.goto(`${baseURL}/deep-dive/?case=${journeyCase.id}`, { waitUntil: "networkidle" });
    await journeyPage.getByRole("button", { name: "Switch visible snapshot" }).click();
    await journeyPage.getByText("Visible snapshot switched.", { exact: true }).waitFor();
    assert.equal((await (await analystApi.get(`/api/cases/${journeyCase.id}/snapshot`)).json()).switch_required, false);

    await journeyPage.goto(`${baseURL}/rv-screener/?case=${journeyCase.id}`, { waitUntil: "networkidle" });
    await journeyPage.getByRole("button", { name: "Add row" }).click();
    await journeyPage.getByRole("button", { name: "Remove row" }).last().click();
    await journeyPage.getByLabel("Instrument").fill("Synthetic 1L 2030");
    await journeyPage.getByLabel("Observation date").fill("2026-08-22");
    await journeyPage.getByLabel("Source version").fill(`synthetic-${suffix}`);
    await journeyPage.getByLabel("Spread (bps)").fill("425");
    await journeyPage.getByLabel("Maturity").fill("2030-12-31");
    await journeyPage.getByLabel("Duration").fill("3.5");
    const rvResponse = journeyPage.waitForResponse((response) => response.url() === exactURL(`/api/cases/${journeyCase.id}/rv`) && response.request().method() === "POST");
    await journeyPage.getByRole("button", { name: "Version market universe" }).click();
    assert.equal((await rvResponse).status(), 201);
    await journeyPage.getByText("Market universe versioned.", { exact: true }).waitFor();
    await journeyPage.getByRole("cell", { name: "Synthetic 1L 2030" }).waitFor();

    await journeyPage.goto(`${baseURL}/report-studio/?case=${journeyCase.id}`, { waitUntil: "networkidle" });
    await journeyPage.getByLabel("Core thesis").fill("Synthetic issuer has stable leverage and adequate liquidity.");
    await journeyPage.getByLabel("Primary instrument").fill("Synthetic 1L 2030");
    await journeyPage.getByLabel("Recommendation").selectOption("MARKET WEIGHT");
    await journeyPage.getByLabel("Evidence IDs").fill(firstSource.id);
    const freezeResponse = journeyPage.waitForResponse((response) => response.url() === exactURL(`/api/cases/${journeyCase.id}/reports/freeze`) && response.request().method() === "POST");
    await journeyPage.getByRole("button", { name: "Freeze report snapshot" }).click();
    assert.equal((await freezeResponse).status(), 201);
    await journeyPage.getByText("PENDING_APPROVAL", { exact: true }).waitFor();
    assert.equal(await journeyPage.getByRole("button", { name: "Approve frozen report" }).count(), 0);
  } finally {
    await journeyPage.close();
  }

  const emptyResponse = await analystApi.post("/api/cases", { data: { name: "Production inventory empty states", issuer: `Empty-${suffix}`, sector: "Synthetic services" } });
  assert.equal(emptyResponse.status(), 201);
  const emptyCase = await emptyResponse.json();
  await addMember(adminApi, journeyCase.id, approverUser, "APPROVER");
  await addMember(adminApi, emptyCase.id, approverUser, "APPROVER");
  await addMember(adminApi, journeyCase.id, readerUser, "READER");
  assert.equal((await readerApi.get(`/api/cases/${journeyCase.id}`)).status(), 200);
  assert.equal((await readerApi.post(`/api/cases/${journeyCase.id}/runs`, { data: { pathway: "FULL_CREDIT", depth: "screen", focus_questions: [] } })).status(), 403);

  const approverContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, extraHTTPHeaders: approverHeaders });
  contexts.push(approverContext);
  const approvalPage = await approverContext.newPage();
  const exports = {};
  try {
    await approvalPage.goto(`${baseURL}/report-studio/?case=${journeyCase.id}`, { waitUntil: "networkidle" });
    const approvalResponse = approvalPage.waitForResponse((response) => response.url() === exactURL(`/api/cases/${journeyCase.id}/reports/approve`) && response.request().method() === "POST");
    await approvalPage.getByRole("button", { name: "Approve frozen report" }).click();
    assert.equal((await approvalResponse).status(), 200);
    await approvalPage.getByText("APPROVED", { exact: true }).waitFor();
    for (const format of ["md", "pdf", "xlsx"]) {
      const response = await approvalPage.request.get(`${baseURL}/api/cases/${journeyCase.id}/reports/export/${format}`);
      const body = await response.body();
      assert.equal(response.status(), 200);
      if (format === "md") assert.ok(body.toString().includes("Synthetic issuer has stable leverage"));
      if (format === "pdf") assert.equal(body.subarray(0, 4).toString(), "%PDF");
      if (format === "xlsx") assert.equal(body.subarray(0, 2).toString(), "PK");
      exports[format] = { bytes: body.length, content_type: response.headers()["content-type"] };
    }
  } finally {
    await approvalPage.close();
  }

  const roleContexts = [
    ["analyst", analystContext],
    ["pm_qa", approverContext],
  ];
  const loaded = [];
  const states = { loading: [], error: [], empty: [] };
  const stateSpecs = [
    { slug: "cases", endpoint: "/api/cases", url: `${baseURL}/cases/`, errorText: "production inventory state probe", emptyText: "No cases yet. Create the first case to establish the context boundary.", emptyEndpoint: "/api/cases" },
    { slug: "sources", endpoint: `/api/cases/${emptyCase.id}/sources`, url: `${baseURL}/sources/?case=${emptyCase.id}`, emptyText: "No source objects in this case." },
    { slug: "run-console", endpoint: `/api/runs/${firstRun.id}`, url: `${baseURL}/run-console/?case=${journeyCase.id}&run=${firstRun.id}`, emptyURL: `${baseURL}/run-console/?case=${emptyCase.id}`, emptyText: "No current execution. Select a purpose and depth to create an immutable plan." },
    { slug: "deep-dive", endpoint: `/api/cases/${emptyCase.id}/snapshot`, url: `${baseURL}/deep-dive/?case=${emptyCase.id}`, emptyText: "No accepted snapshot. Run the selected route, inspect exceptions, then accept it explicitly." },
    { slug: "rv-screener", endpoint: `/api/cases/${emptyCase.id}/rv`, url: `${baseURL}/rv-screener/?case=${emptyCase.id}`, emptyText: "Version a comparable market universe to see eligible rows." },
    { slug: "command-center", endpoint: `/api/cases/${emptyCase.id}/lens`, url: `${baseURL}/command-center/?case=${emptyCase.id}`, emptyText: "No accepted snapshot yet. Posture becomes reviewable after an explicit acceptance." },
    { slug: "model-builder", endpoint: `/api/cases/${emptyCase.id}/models`, url: `${baseURL}/model-builder/?case=${emptyCase.id}`, emptyText: "ACCEPTED FULL CREDIT REQUIRED", emptyEndpoint: null },
    { slug: "report-studio", endpoint: `/api/cases/${emptyCase.id}/reports`, url: `${baseURL}/report-studio/?case=${emptyCase.id}`, emptyText: "No frozen report for this case." },
  ];

  for (const [role, context] of roleContexts) {
    for (const [slug, title] of destinations) loaded.push(await inventoryLoadedRoute(context, role, slug, title));
    for (const spec of stateSpecs) {
      states.loading.push(await probeLoading(context, role, spec.url, spec.endpoint));
      states.error.push(await probeError(context, role, spec.url, spec.endpoint, spec.errorText));
      if (spec.emptyText) states.empty.push(await probeEmpty(context, role, spec.emptyURL || spec.url, spec.emptyText, spec.emptyEndpoint));
    }
  }

  const loadPaths = [
    "/api/cases",
    `/api/cases/${denseCaseId}`,
    `/api/cases/${denseCaseId}/sources`,
    `/api/cases/${denseCaseId}/rv`,
    `/api/cases/${denseCaseId}/snapshot`,
    `/api/cases/${denseCaseId}/runs`,
  ];
  const load = [];
  for (const workers of [1, 4, 12, 24]) {
    const stage = await runLoadStage(analystHeaders, workers, loadPaths);
    assert.equal(stage.failures, 0, `${workers}-worker load stage returned failures`);
    if (workers === 24) assert.ok(stage.p95_ms <= maxBurstP95Ms, `burst p95 ${stage.p95_ms}ms exceeds ${maxBurstP95Ms}ms`);
    load.push(stage);
  }
  const recoveryStarted = performance.now();
  const recoveryResponse = await fetch(exactURL(`/api/cases/${denseCaseId}`), { headers: analystHeaders });
  await recoveryResponse.arrayBuffer();
  const recoveryMs = performance.now() - recoveryStarted;
  assert.equal(recoveryResponse.status, 200);
  assert.ok(recoveryMs <= maxPostLoadMs, `post-load recovery ${recoveryMs.toFixed(1)}ms exceeds ${maxPostLoadMs}ms`);

  console.log(JSON.stringify({
    dataset: {
      dense_case_id: denseCaseId,
      dense_sources: denseDetail.source_count,
      roles: ["ADMIN", "ANALYST", "APPROVER", "READER"],
      pathways: expectedPathways,
      rv: { eligible: denseRV.rows.length, excluded: denseRV.excluded.length },
    },
    journey: { case_id: journeyCase.id, empty_case_id: emptyCase.id, run_id: firstRun.id, exports },
    loaded_inventory: { combinations: loaded.length, failures: 0, rows: loaded },
    state_inventory: {
      loading: states.loading.length,
      error: states.error.length,
      empty: states.empty.length,
      failures: 0,
    },
    load: { stages: load, post_load_ms: Number(recoveryMs.toFixed(1)), failures: 0 },
  }));
} finally {
  for (const context of contexts.reverse()) await context.close();
  await browser.close();
  await analystApi.dispose();
  await approverApi.dispose();
  await adminApi.dispose();
  await readerApi.dispose();
}
