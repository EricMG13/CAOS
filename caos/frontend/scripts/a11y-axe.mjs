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
} finally {
  await browser.close();
}

if (violations.length) {
  console.error(JSON.stringify({ violations }, null, 2));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ routes: routes.length, viewports: viewports.length, combinations: routes.length * viewports.length + 1, pendingPlanFixture: true, violations: 0 }));
}
