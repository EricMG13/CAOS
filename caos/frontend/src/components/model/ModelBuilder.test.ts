import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const workspace = readFileSync(new URL("../Workspace.tsx", import.meta.url), "utf8");
const modelBuilder = readFileSync(new URL("./ModelBuilder.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../../lib/api.ts", import.meta.url), "utf8");

test("Workspace delegates Model Builder to the extracted component", () => {
  assert.match(workspace, /import ModelBuilder from "\.\/model\/ModelBuilder";/);
  assert.match(workspace, /case "Model Builder": return <ModelBuilder caseId=\{caseId\} role=\{role\}/);
  assert.doesNotMatch(workspace, /function ModelView\(/);
  assert.doesNotMatch(workspace, /function WorksheetGrid\(/);
});

test("extraction preserves the read-only worksheet keyboard and lineage contract", () => {
  assert.match(modelBuilder, /function WorksheetGrid\(/);
  assert.match(modelBuilder, /ArrowUp:[\s\S]*ArrowDown:[\s\S]*ArrowLeft:[\s\S]*ArrowRight:/);
  assert.match(modelBuilder, /event\.key === "Enter" \|\| event\.key === " "/);
  assert.match(modelBuilder, /tabIndex=\{activeCell\.row === row && activeCell\.column === column \? 0 : -1\}/);
  assert.match(modelBuilder, /aria-controls="model-cell-lineage"/);
  assert.match(modelBuilder, /READ ONLY/);
  assert.doesNotMatch(modelBuilder, /contentEditable|contenteditable/);
});

test("authoring is registry-driven, browser-memory-only, and identity fenced", () => {
  for (const label of ["Model", "Assumptions", "Sensitivities", "History"]) {
    assert.match(modelBuilder, new RegExp(`label: "${label}"`));
  }
  assert.match(modelBuilder, /assumptionRegistryPath\(expectedCaseId, nextBuild\.id\)/);
  assert.match(api, /models\/assumption-registry\?build_id=/);
  for (const route of [
    "models/previews",
    "model-revisions/sign-off",
    "model-revisions/rebase-preview",
    "models/scenarios",
    "models/sensitivities/one-way",
  ]) {
    assert.ok(modelBuilder.includes(route), `missing Phase 3 route ${route}`);
  }
  assert.match(modelBuilder, /previewMatchesDraft/);
  assert.match(modelBuilder, /draftGeneration/);
  assert.match(modelBuilder, /expected_head_revision_id/);
  assert.match(workspace, /beforeunload/);
  assert.doesNotMatch(modelBuilder, /localStorage|sessionStorage/);
  assert.doesNotMatch(modelBuilder, /eval\(|Function\(/);
});

test("the component exposes the accepted analyst journeys and role gates", () => {
  assert.match(modelBuilder, /Sign-Off Note/);
  assert.match(modelBuilder, /Compatible/);
  assert.match(modelBuilder, /Changed/);
  assert.match(modelBuilder, /Invalidated/);
  assert.match(modelBuilder, /One-way table/);
  assert.match(modelBuilder, /One-way tornado/);
  assert.match(modelBuilder, /Breakpoint/);
  assert.match(modelBuilder, /Multi-Driver Scenario/);
  assert.match(modelBuilder, /Apply to Draft/);
  assert.match(modelBuilder, /Application Model Build/);
  assert.match(modelBuilder, /data-primary-model-action/);
  assert.match(modelBuilder, /role !== "READER"/);
});

test("readers can run local temporary calculations while shared writes remain gated", () => {
  assert.doesNotMatch(modelBuilder, /disabled=\{!canWrite \|\| row\.status !== "READY"\}/);
  assert.doesNotMatch(modelBuilder, /scenario && canWrite/);
  assert.match(modelBuilder, /canWrite && .*Sign Off|canWrite \? "SIGN_OFF"/s);
  assert.match(modelBuilder, /canWrite && \(revision\.export\.status/);
});

test("authoring tabs implement roving WAI-ARIA keyboard semantics", () => {
  assert.match(modelBuilder, /model-builder-tab-\$\{item\.id\.toLowerCase\(\)\}/);
  assert.match(modelBuilder, /tabIndex=\{view === item\.id \? 0 : -1\}/);
  assert.match(modelBuilder, /ArrowLeft/);
  assert.match(modelBuilder, /ArrowRight/);
  assert.match(modelBuilder, /Home/);
  assert.match(modelBuilder, /End/);
  assert.match(modelBuilder, /aria-controls=\{`model-builder-panel-/);
  for (const view of ["model", "assumptions", "sensitivities", "history"]) {
    assert.match(modelBuilder, new RegExp(`aria-labelledby="model-builder-tab-${view}"`));
  }
});

test("assumption review exposes application defaults, application-build deltas, mixed state, and applicability", () => {
  assert.match(modelBuilder, /Application default/);
  assert.match(modelBuilder, /Effective minus Application build/);
  assert.match(modelBuilder, /applicationBuildDelta\(row\)/);
  assert.match(modelBuilder, /mixed=\{broadcastScope\.mixed\}/);
  assert.match(modelBuilder, /broadcastScope\.editable/);
  assert.match(modelBuilder, /sensitivityScope\.editable/);
  assert.match(modelBuilder, /<label>Output<select/);
  assert.doesNotMatch(modelBuilder, /Output ID<input/);
  assert.match(modelBuilder, /aria-live="polite"/);
});

test("last successful preview remains visible but non-signable when stale or retry fails", () => {
  assert.match(modelBuilder, /Last successful preview/);
  assert.match(modelBuilder, /Preview stale/);
  assert.doesNotMatch(modelBuilder, /const invalidatePreview[\s\S]{0,400}setPreview\(null\)/);
});

test("dirty conflicts and navigation are recoverable rather than destructive", () => {
  assert.match(modelBuilder, /mergeRebasedAssumptions/);
  assert.match(modelBuilder, /Review and rebase local Draft/);
  assert.match(workspace, /popstate/);
  assert.match(workspace, /modelDraftDirtyRef/);
  assert.match(workspace, /suppressNextModelHistoryPopRef/);
});
