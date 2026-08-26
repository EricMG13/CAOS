import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const workspace = readFileSync(new URL("../Workspace.tsx", import.meta.url), "utf8");
const studio = readFileSync(new URL("./ReportStudio.tsx", import.meta.url), "utf8");
const document = readFileSync(new URL("./DeliverableDocument.tsx", import.meta.url), "utf8");

test("Workspace delegates Report Studio to the structured component", () => {
  assert.match(workspace, /import ReportStudio from "\.\/report\/ReportStudio";/);
  assert.match(workspace, /case "Report Studio": return <ReportStudio/);
  assert.doesNotMatch(workspace, /function ReportView\(/);
  assert.doesNotMatch(workspace, /caos-report-draft|sessionStorage/);
});

test("authoring uses the six server templates and shared append-only draft route", () => {
  for (const pathway of ["FULL_CREDIT", "EARNINGS_UPDATE", "COVENANT_REFINANCING", "RELATIVE_VALUE", "DISTRESSED_RESTRUCTURING", "DEEP_RESEARCH"]) {
    assert.match(studio, new RegExp(pathway));
  }
  assert.match(studio, /deliverables\/\$\{pathway\}\/draft/);
  assert.match(studio, /expected_version/);
  assert.match(studio, /850/);
  assert.match(studio, /Saving/);
  assert.match(studio, /Saved v/);
  assert.match(studio, /Conflict/);
  assert.match(studio, /saveGeneration/);
  assert.match(studio, /saveChain/);
});

test("the structured document is safe and keeps generated content read-only", () => {
  assert.match(document, /GENERATED_METRIC/);
  assert.match(document, /SCENARIO_EXHIBIT/);
  assert.match(document, /ANALYST_JUDGMENT/);
  assert.doesNotMatch(document, /dangerouslySetInnerHTML|contentEditable|contenteditable/);
  assert.doesNotMatch(studio, /eval\(|Function\(/);
  assert.doesNotMatch(studio, /localStorage|sessionStorage/);
});

test("exact Frozen and Filed lifecycle is identity-bound and role-gated", () => {
  assert.match(studio, /draft_digest/);
  assert.match(studio, /preview_digest/);
  assert.match(studio, /input_fingerprint/);
  assert.match(studio, /role === "APPROVER" \|\| role === "ADMIN"/);
  assert.match(studio, /request-changes/);
  assert.match(studio, /export\/\$\{format\}/);
  assert.match(studio, /frozen_history/);
  assert.match(studio, /Restore as new revision/);
  assert.match(studio, /const unsavedDraft = useRef\(false\)/);
  assert.match(studio, /if \(!workspace \|\| !canWrite \|\| unsavedDraft\.current \|\| saveState\.kind !== "SAVED"\) return/);
  assert.match(studio, /disabled=\{!canWrite \|\| lifecycleBusy \|\| draftIsUnsaved \|\| saveState\.kind !== "SAVED"\}/);
  assert.doesNotMatch(studio, /onClick=\{\(\) => setBlocks\(revision\.content\.blocks\)\}/);
});

test("model fallback, evidence, scenario, focus, and case fences remain explicit", () => {
  assert.match(studio, /fallback_acknowledged: true/);
  assert.match(studio, /ANALYST_REVISION/);
  assert.match(studio, /APPLICATION_BUILD/);
  assert.match(studio, /models\/scenarios/);
  assert.match(studio, /draft_generation/);
  assert.match(studio, /AbortController/);
  assert.match(studio, /aria-live="polite"/);
  assert.match(studio, /onDraftStateChange/);
});

test("Scenario registry is build-bound and seeded only from server defaults", () => {
  assert.match(studio, /assumptionRegistryPath\(caseId, buildId\)/);
  assert.match(studio, /value\.build_id !== buildId/);
  assert.match(studio, /value\.defaults\.find\(\(row\) => row\.case === "BASE" && row\.status === "READY"\)/);
  assert.match(studio, /<select id="scenario-period"/);
  assert.doesNotMatch(studio, /<input id="scenario-period"/);
  assert.doesNotMatch(studio, /FY2025/);
  assert.match(studio, /Scenario registry unavailable/);
});

test("every lifecycle mutation shares one scope generation and in-flight gate", () => {
  assert.match(studio, /type LifecycleToken/);
  assert.match(studio, /const lifecycleGeneration = useRef\(0\)/);
  assert.match(studio, /const lifecycleInFlight = useRef\(false\)/);
  assert.match(studio, /beginLifecycle/);
  assert.match(studio, /lifecycleIsCurrent/);
  assert.match(studio, /invalidateLifecycle/);
  assert.match(studio, /const lifecycleBusy = pending !== ""/);
  assert.match(studio, /disabled=\{[^}]*lifecycleBusy[^}]*\}/);
  assert.doesNotMatch(studio, /await load\(\);\s*setSelectedFrozen/);
});

test("one lifecycle lock disables every draft-mutating authoring control", () => {
  assert.match(studio, /const authoringLocked = lifecycleBusy/);
  assert.match(studio, /narrative-\$\{selectedNarrative\.block_id\}[\s\S]*?disabled=\{!canWrite \|\| authoringLocked\}/);
  assert.match(studio, /name=\{`mode-\$\{selectedNarrative\.block_id\}`\}[\s\S]*?disabled=\{!canWrite \|\| authoringLocked\}/);
  assert.match(studio, /name="report-model"[\s\S]*?disabled=\{!canWrite \|\| authoringLocked\}/);
  assert.match(studio, /disabled=\{[^}]*authoringLocked[^}]*\}>Add \{policy\.kind/);
  assert.match(studio, /disabled=\{[^}]*authoringLocked[^}]*\}>Omit block/);
  assert.match(studio, /disabled=\{[^}]*authoringLocked[^}]*\}>Remove citation/);
  assert.match(studio, /disabled=\{[^}]*authoringLocked[^}]*\}>Cite block/);
  for (const id of ["scenario-assumption", "scenario-case", "scenario-period", "scenario-value"]) {
    assert.match(studio, new RegExp(`id="${id}"[\\s\\S]{0,500}?disabled=\\{authoringLocked\\}`));
  }
  assert.match(studio, /disabled=\{authoringLocked\}>Retry over current v\{conflict\.version\}/);
  assert.match(studio, /disabled=\{authoringLocked\}>Use shared v\{conflict\.version\}/);
  assert.match(studio, /disabled=\{lifecycleBusy\}>\{pending === "file"/);
  assert.match(studio, /disabled=\{!changeComment\.trim\(\) \|\| lifecycleBusy\}/);
  assert.match(studio, /disabled=\{!canWrite \|\| lifecycleBusy \|\| draftIsUnsaved/);
});

test("Frozen review accepts the complete immutable authority and model envelope", () => {
  assert.match(studio, /payload: FrozenPayload/);
  for (const field of ["authority", "model", "evidence", "methodology", "renderer", "input_fingerprint", "preview_digest"]) {
    assert.match(document, new RegExp(`${field}:`));
  }
  assert.match(studio, /frozenPayload=\{selectedFrozen\?\.payload/);
  assert.match(document, /Base \/ Downside Model Analysis/);
  assert.match(document, /Effective Assumptions/);
  assert.match(document, /Model Gaps and Warnings/);
  assert.match(document, /Frozen authority/);
  assert.match(document, /Revision Record/);
  assert.match(document, /maximumFractionDigits: 20/);
});

test("Workspace owns and retires at most one shared draft-history sentinel", () => {
  assert.match(workspace, /historyGuardRetiringRef/);
  assert.match(workspace, /retireOwnedHistoryGuard/);
  assert.match(workspace, /if \(!modelHistoryGuardRef\.current && !historyGuardRetiringRef\.current\)/);
  assert.match(workspace, /if \(!modelDraftDirtyRef\.current && !reportDraftDirtyRef\.current\) retireOwnedHistoryGuard\(\)/);
});
