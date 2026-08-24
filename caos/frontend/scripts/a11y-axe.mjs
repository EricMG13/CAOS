// CAOS_URL must point at the combined app — the static export served by FastAPI,
// as caos/scripts/build_frontend.sh + caos/server/run.py produce and CI runs. The
// pending-plan fixture below drives client routing that only behaves correctly
// against that build; pointing this at `next dev` fails on the "Proposed research
// plan" wait, which looks like a product defect but is a harness mismatch.
import assert from "node:assert/strict";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const baseUrl = process.env.CAOS_URL || "http://127.0.0.1:8000";
const identityHeaders = process.env.CAOS_EDGE_SECRET ? {
  "x-edge-authorization": process.env.CAOS_EDGE_SECRET,
  "x-forwarded-user": process.env.CAOS_TEST_USER || "analyst.qa@local.invalid",
  "x-forwarded-email": process.env.CAOS_TEST_USER || "analyst.qa@local.invalid",
  "x-forwarded-groups": process.env.CAOS_TEST_GROUPS || "caos-analyst",
} : {};
const caseQuery = process.env.CAOS_CASE_ID ? `?case=${encodeURIComponent(process.env.CAOS_CASE_ID)}` : "";
const routes = ["/cases/", "/sources/", "/run-console/", "/deep-dive/", "/rv-screener/", "/command-center/", "/model-builder/", "/report-studio/", "/admin-studio/"];
const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "laptop", width: 1024, height: 768 },
  { name: "reflow", width: 720, height: 900 },
];
const browser = await chromium.launch({ headless: true });
const violations = [];

try {
  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport, extraHTTPHeaders: identityHeaders });
    const page = await context.newPage();
    for (const route of routes) {
      await page.goto(`${baseUrl}${route}${route === "/admin-studio/" ? "" : caseQuery}`, { waitUntil: "networkidle" });
      const result = await new AxeBuilder({ page }).analyze();
      for (const violation of result.violations) violations.push({ viewport: viewport.name, route, id: violation.id, impact: violation.impact, nodes: violation.nodes.map((node) => ({ target: node.target, html: node.html, summary: node.failureSummary })) });
    }
    await context.close();
  }
  const pendingContext = await browser.newContext({ viewport: { width: 375, height: 812 }, extraHTTPHeaders: identityHeaders });
  const pendingPage = await pendingContext.newPage();
  const pendingConsoleErrors = [];
  pendingPage.on("console", (message) => {
    if (message.type() === "error") pendingConsoleErrors.push(message.text());
  });
  pendingPage.on("pageerror", (error) => pendingConsoleErrors.push(error.message));
  const caseId = "case_a11y_pending_plan";
  const runId = "run_a11y_pending_plan";
  const planHash = `sha256:${"b".repeat(64)}`;
  const caseFixture = { id: caseId, name: "Pending plan", issuer: "Northstar", sector: "Services", current_execution_id: runId, deep_research_available: true, deep_research_unavailable_reason: null };
  const runFixture = {
    id: runId,
    case_id: caseId,
    status: "paused",
    plan: { pathway: "DEEP_RESEARCH", depth: "full", profile_id: "DEEP_RESEARCH_FULL", selection_id: "a11y-fixture" },
    nodes: [{ id: "node-cp0", module_id: "CP-0", status: "succeeded" }, { id: "node-cpdr", module_id: "CP-DR", status: "pending" }],
    error: { code: "PLAN_APPROVAL_REQUIRED", message: "Approve the exact deterministic research plan before agent execution." },
    research: {
      phase: "awaiting_approval",
      proposed_plan_hash: planHash,
      proposed_plan: {
        methodology_build_id: "deploy-v-a11y-fixture",
        brief_digest: "a11y-brief-digest",
        source_set: { id: "set_a11y", version: 1 },
        upstream_artifacts: [
          { module_id: "CP-0", artifact_id: "art_a11y", digest: "" },
          { module_id: "CP-0", artifact_id: "art_a11y", digest: "" },
        ],
        scope: { type: "issuer", key: "case-a11y-pending-plan", source_mode: "supplied_only" },
        workstreams: [
          { id: "", kind: "topical", question: "Can the issuer refinance?", assigned_questions: ["Liquidity runway?", "Liquidity runway?", ""], perspective: "Buy-side credit analyst", hypothesis: "Liquidity supports refinancing.", evidence_needs: ["Debt maturity schedule", "Debt maturity schedule", ""], source_classes: ["supplied_case_sources", "supplied_case_sources", ""], disconfirming_test: "Find contrary supplied evidence.", completion_test: "Answer with source locators or record the gap.", effort_cap: "Within the fixed standard research budget." },
          { id: "", kind: "", question: "", assigned_questions: [], perspective: "", hypothesis: "", evidence_needs: [], source_classes: [], disconfirming_test: "", completion_test: "", effort_cap: "" },
        ],
      },
    },
  };
  let caseFixtureHits = 0;
  let runFixtureHits = 0;
  await pendingPage.route((url) => url.pathname === "/api/cases", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([caseFixture]) }));
  await pendingPage.route((url) => url.pathname === `/api/cases/${caseId}`, (route) => {
    caseFixtureHits += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(caseFixture) });
  });
  await pendingPage.route((url) => url.pathname === `/api/cases/${caseId}/snapshot`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ accepted: null, latest_accepted: null, switch_required: false, diff: null }) }));
  await pendingPage.route((url) => url.pathname === `/api/runs/${runId}`, (route) => {
    runFixtureHits += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(runFixture) });
  });
  await pendingPage.route((url) => url.pathname === `/api/runs/${runId}/events`, (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: "retry: 60000\n\n" }));
  await pendingPage.goto(`${baseUrl}/run-console/?case=${caseId}&run=${runId}&fixture=pending-plan`, { waitUntil: "networkidle" });
  await pendingPage.getByRole("heading", { name: "Proposed research plan" }).waitFor();
  const pendingPlan = pendingPage.locator(".research-plan");
  assert.ok(await pendingPlan.getByText("None", { exact: true }).count() >= 9, "pending-plan axe fixture did not render explicit empty-scalar markers");
  assert.ok(await pendingPlan.getByText("Empty", { exact: true }).count() >= 3, "pending-plan axe fixture did not render explicit empty-list markers");
  const upstreamArtifacts = pendingPlan.locator(":scope > .research-plan-facts > dt").filter({ hasText: /^Upstream artifacts$/ }).locator("xpath=following-sibling::dd[1]/ul/li");
  assert.equal(await upstreamArtifacts.count(), 2, "pending-plan axe fixture did not preserve repeated upstream artifacts");
  const workstreams = pendingPlan.locator(".research-workstreams > li");
  assert.equal(await workstreams.count(), 2, "pending-plan axe fixture did not preserve repeated-ID workstreams");
  assert.equal(await workstreams.first().getByText("Liquidity runway?", { exact: true }).count(), 2, "pending-plan axe fixture did not preserve repeated workstream values");
  assert.equal(pendingConsoleErrors.some((message) => /children with the same key|duplicate key/i.test(message)), false, "pending-plan axe fixture emitted a React duplicate-key warning");
  const pendingResult = await new AxeBuilder({ page: pendingPage }).analyze();
  for (const violation of pendingResult.violations) violations.push({ viewport: "pending-plan-375", route: "/run-console/", id: violation.id, impact: violation.impact, nodes: violation.nodes.map((node) => ({ target: node.target, html: node.html, summary: node.failureSummary })) });
  assert.ok(caseFixtureHits > 0, "pending-plan case fixture was not exercised");
  assert.ok(runFixtureHits > 0, "pending-plan run fixture was not exercised");
  await pendingContext.close();

  const modelContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, extraHTTPHeaders: identityHeaders });
  const modelPage = await modelContext.newPage();
  const modelCaseId = "case_a11y_ready_model";
  const modelBuildId = "model_a11y_ready";
  const modelCase = { id: modelCaseId, name: "Ready model", issuer: "Northstar", sector: "Services", current_execution_id: null };
  const modelBuild = { id: modelBuildId, case_id: modelCaseId, accepted_run_id: "run_a11y_model", accepted_snapshot_id: "snap_a11y_model", source_set_id: "set_a11y_model", input_fingerprint: "a".repeat(64), status: "READY", queued_at: "2026-08-24T00:00:00Z", started_at: "2026-08-24T00:00:01Z", completed_at: "2026-08-24T00:00:02Z", error: null, export: { status: "NOT_REQUESTED", error: null }, qa: { status: "PASS", semantic_check_count: 2, formula_count: 1, worksheet_cell_count: 3 }, payload_digest: "b".repeat(64) };
  const modelReadiness = { status: "READY", module_id: "CP-MODEL", accepted_snapshot: { id: "snap_a11y_model", run_id: "run_a11y_model", digest: "c".repeat(64) }, source_set: { id: "set_a11y_model", version: 1, digest: "d".repeat(64) }, requirements: ["CP-1", "CP-1A", "CP-1B", "CP-2", "CP-2A", "CP-2B"].map((module_id) => ({ module_id, status: "READY", digest: "e".repeat(64) })), blockers: [], build: modelBuild };
  const worksheetTab = (name) => ({ id: name.toUpperCase().replaceAll(" ", "_"), name, max_row: 2, max_column: 2, freeze_panes: "B2", merged_cells: [], columns: [{ column: 1, letter: "A", width: 18, hidden: false }, { column: 2, letter: "B", width: 12, hidden: false }], cells: [{ address: "A1", row: 1, column: 1, value: name, value_type: "text", formula: null, semantic_id: null, owner: null, write_class: null, period_id: null, source_refs: null, number_format: "General", style: { bold: true, italic: false, fill: "0A2E63", align: "left", wrap: false } }, { address: "A2", row: 2, column: 1, value: 100, value_type: "number", formula: null, semantic_id: "account::revenue", owner: "CP-1", write_class: "SOURCE", period_id: "FY2025", source_refs: "SRC-1 | page 1 | 2026-08-24", number_format: "#,##0.0", style: { bold: false, italic: false, fill: "FFF4CC", align: "right", wrap: false } }, { address: "B2", row: 2, column: 2, value: 2.5, value_type: "formula", formula: "=A2/40", semantic_id: "metric::leverage", owner: "CP-MODEL", write_class: "FORMULA", period_id: "FY2025", source_refs: null, number_format: "0.0x", style: { bold: false, italic: false, fill: null, align: "right", wrap: false } }] });
  await modelPage.route((url) => url.pathname === "/api/cases", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([modelCase]) }));
  await modelPage.route((url) => url.pathname === `/api/cases/${modelCaseId}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(modelCase) }));
  await modelPage.route((url) => url.pathname === `/api/cases/${modelCaseId}/snapshot`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ accepted: null, latest_accepted: null, switch_required: false, diff: null }) }));
  await modelPage.route((url) => url.pathname === `/api/cases/${modelCaseId}/models`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ readiness: modelReadiness, builds: [modelBuild] }) }));
  await modelPage.route((url) => url.pathname === `/api/cases/${modelCaseId}/models/${modelBuildId}/worksheet`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ build_id: modelBuildId, input_fingerprint: modelBuild.input_fingerprint, payload_digest: modelBuild.payload_digest, qa: modelBuild.qa, payload: { schema_version: "caos.model.worksheet.v1", identity: { issuer_id: "northstar", issuer_name: "Northstar", analysis_date: "2026-08-24" }, tabs: [worksheetTab("Credit Snapshot"), worksheetTab("Model"), worksheetTab("KPIs")] } }) }));
  await modelPage.goto(`${baseUrl}/model-builder/?case=${modelCaseId}&fixture=ready-model`, { waitUntil: "networkidle" });
  await modelPage.getByRole("tab", { name: "Credit Snapshot" }).waitFor();
  await modelPage.getByRole("button", { name: /Show lineage for account::revenue/ }).click();
  await modelPage.locator("#model-cell-lineage").getByText(/SRC-1/).waitFor();
  const modelResult = await new AxeBuilder({ page: modelPage }).analyze();
  for (const violation of modelResult.violations) violations.push({ viewport: "ready-model-1280", route: "/model-builder/", id: violation.id, impact: violation.impact, nodes: violation.nodes.map((node) => ({ target: node.target, html: node.html, summary: node.failureSummary })) });
  await modelContext.close();
} finally {
  await browser.close();
}

if (violations.length) {
  console.error(JSON.stringify({ violations }, null, 2));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ routes: routes.length, viewports: viewports.length, combinations: routes.length * viewports.length + 2, pendingPlanFixture: true, readyModelFixture: true, violations: 0 }));
}
