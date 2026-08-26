import assert from "node:assert/strict";
import test from "node:test";
import {
  applicationBuildDelta,
  applyAssumptionValue,
  applyServerAssumptions,
  assumptionScope,
  mergeRebasedAssumptions,
  normalizeAssumptions,
  previewMatchesDraft,
  primaryModelAction,
  sensitivityPeriodRows,
  type AssumptionDefinition,
  type ModelAssumptionValue,
  type ModelPreview,
} from "./modelBuilderState.ts";

const definition: AssumptionDefinition = {
  assumption_id: "operating.revenue_growth.division_1",
  label: "Division 1 revenue growth",
  family: "OPERATING",
  description: "Canonical division growth.",
  unit: "PERCENT_DECIMAL",
  cases: ["BASE", "DOWNSIDE"],
  sensitivity_default: { range: "0.02", step: "0.01" },
  hard_min: "-0.75",
  hard_max: "2",
  affected_outputs: ["revenue", "total_leverage"],
};

const rows = ["BASE", "DOWNSIDE"].flatMap((caseName) => ["FY2025", "FY2026", "FY2027"].map((period, index) => ({
  assumption_id: definition.assumption_id,
  case: caseName as "BASE" | "DOWNSIDE",
  period_id: period,
  unit: definition.unit,
  status: "READY" as const,
  value: String(0.03 + index / 100),
  gap_code: null,
  default_value: String(0.03 + index / 100),
  default_status: "READY" as const,
  default_gap_code: null,
  source_context: { authority_module: "CP-2G" as const, gap_code: "", provenance: [{ source_id: "src_1", source_locator: "page 4", as_of: "2026-08-25" }] },
  source_context_digest: "a".repeat(64),
})));

test("normalizes methodology numeric strings without dropping source context", () => {
  const normalized = normalizeAssumptions(rows);

  assert.equal(normalized[0].value, 0.03);
  assert.equal(normalized[0].default_value, 0.03);
  assert.equal(normalized[0].source_context?.provenance[0].source_locator, "page 4");
  assert.notStrictEqual(normalized[0], rows[0]);
});

test("assumption delta is measured against the Application Model Build default", () => {
  const row = normalizeAssumptions(rows)[0];
  const signedValue = { ...row, value: 0.02, default_value: 0.03 };
  const localDraft = { ...signedValue, value: 0.04 };

  assert.ok(Math.abs(applicationBuildDelta(localDraft)! - 0.01) < Number.EPSILON);
  assert.equal(applicationBuildDelta({ ...localDraft, default_value: null }), null);
});

test("all-year editing broadcasts within one case and enforces methodology bounds", () => {
  const normalized = normalizeAssumptions(rows);
  const changed = applyAssumptionValue(normalized, definition, "BASE", "ALL", 0.12);

  assert.deepEqual(changed.filter((row) => row.case === "BASE").map((row) => row.value), [0.12, 0.12, 0.12]);
  assert.deepEqual(changed.filter((row) => row.case === "DOWNSIDE").map((row) => row.value), [0.03, 0.04, 0.05]);
  assert.throws(() => applyAssumptionValue(normalized, definition, "BASE", "FY2026", 2.01), /ASSUMPTION_OUT_OF_BOUNDS/);
});

test("server scenario and rebase assumptions replace the draft locally by identity", () => {
  const normalized = normalizeAssumptions(rows);
  const serverRows: ModelAssumptionValue[] = normalized.map((row) => row.case === "DOWNSIDE" && row.period_id === "FY2027" ? { ...row, value: -0.2 } : row);
  const applied = applyServerAssumptions(normalized, serverRows);

  assert.equal(applied.find((row) => row.case === "DOWNSIDE" && row.period_id === "FY2027")?.value, -0.2);
  assert.equal(applied.length, normalized.length);
});

test("preview eligibility binds draft generation, build, registry, parent, and active head", () => {
  const preview = {
    build_id: "model_1",
    build_input_fingerprint: "b".repeat(64),
    build_payload_digest: "c".repeat(64),
    registry_version: "registry.v1",
    registry_digest: "d".repeat(64),
    parent_revision_id: "revision_1",
    draft_generation: 7,
    preview_digest: "e".repeat(64),
  } as ModelPreview;
  const identity = {
    buildId: "model_1",
    buildInputFingerprint: "b".repeat(64),
    buildPayloadDigest: "c".repeat(64),
    registryVersion: "registry.v1",
    registryDigest: "d".repeat(64),
    parentRevisionId: "revision_1",
    expectedHeadRevisionId: "revision_1",
    currentHeadRevisionId: "revision_1",
    draftGeneration: 7,
  };

  assert.equal(previewMatchesDraft(preview, identity), true);
  assert.equal(previewMatchesDraft(preview, { ...identity, draftGeneration: 8 }), false);
  assert.equal(previewMatchesDraft(preview, { ...identity, currentHeadRevisionId: "revision_2" }), false);
  assert.equal(previewMatchesDraft(preview, { ...identity, buildPayloadDigest: "f".repeat(64) }), false);
});

test("the workflow exposes only the primary action appropriate to current state", () => {
  assert.equal(primaryModelAction({ status: "READY_TO_BUILD", canWrite: true, dirty: false, previewCurrent: false }), "BUILD");
  assert.equal(primaryModelAction({ status: "READY", canWrite: true, dirty: true, previewCurrent: false }), "PREVIEW");
  assert.equal(primaryModelAction({ status: "READY", canWrite: true, dirty: true, previewCurrent: true }), "SIGN_OFF");
  assert.equal(primaryModelAction({ status: "READY", canWrite: false, dirty: true, previewCurrent: true }), null);
});

test("one-way rows consume nested Base and Downside annual server outputs exactly", () => {
  const result = {
    case: "BASE" as const,
    period_scope: "ALL",
    output_id: "total_leverage",
    points: [
      { value: 0.01, outputs: { BASE: { FY2025: { total_leverage: "4.3" }, FY2026: { total_leverage: null } }, DOWNSIDE: { FY2025: { total_leverage: "5.1" } } }, deltas: { BASE: { FY2025: { total_leverage: "0.1" }, FY2026: { total_leverage: null } }, DOWNSIDE: { FY2025: { total_leverage: "0.2" } } } },
      { value: 0.05, outputs: { BASE: { FY2025: { total_leverage: "3.9" }, FY2026: { total_leverage: "3.7" } }, DOWNSIDE: { FY2025: { total_leverage: "4.8" } } }, deltas: { BASE: { FY2025: { total_leverage: "-0.3" }, FY2026: { total_leverage: "-0.4" } }, DOWNSIDE: { FY2025: { total_leverage: "-0.1" } } } },
    ],
  };

  assert.deepEqual(sensitivityPeriodRows(result), [
    { input: 0.01, periodId: "FY2025", output: "4.3", delta: "0.1" },
    { input: 0.01, periodId: "FY2026", output: null, delta: null },
    { input: 0.05, periodId: "FY2025", output: "3.9", delta: "-0.3" },
    { input: 0.05, periodId: "FY2026", output: "3.7", delta: "-0.4" },
  ]);
  assert.deepEqual(sensitivityPeriodRows({ ...result, case: "DOWNSIDE", period_scope: "FY2025" }), [
    { input: 0.01, periodId: "FY2025", output: "5.1", delta: "0.2" },
    { input: 0.05, periodId: "FY2025", output: "4.8", delta: "-0.1" },
  ]);
});

test("assumption scopes expose controlled same/mixed values and disable unavailable scopes", () => {
  const normalized = normalizeAssumptions(rows);
  assert.deepEqual(assumptionScope(normalized, definition.assumption_id, "BASE", "ALL"), {
    rows: normalized.filter((row) => row.case === "BASE"),
    editable: true,
    mixed: true,
    value: "",
  });
  const same = applyAssumptionValue(normalized, definition, "BASE", "ALL", 0.12);
  assert.equal(assumptionScope(same, definition.assumption_id, "BASE", "ALL").value, "0.12");
  const unavailable = same.map((row) => row.case === "BASE" && row.period_id === "FY2026" ? { ...row, status: "UNAVAILABLE" as const, value: null, gap_code: "LIQUIDITY_UNAVAILABLE" } : row);
  assert.equal(assumptionScope(unavailable, definition.assumption_id, "BASE", "ALL").editable, false);
  assert.equal(assumptionScope(unavailable, definition.assumption_id, "BASE", "FY2025").editable, true);
});

test("rebase candidates retain local draft shocks over the server-owned candidate", () => {
  const baseline = normalizeAssumptions(rows);
  const draft = applyAssumptionValue(baseline, definition, "BASE", "FY2025", 0.12);
  const candidate = baseline.map((row) => row.case === "DOWNSIDE" && row.period_id === "FY2027" ? { ...row, value: -0.15 } : row);
  const merged = mergeRebasedAssumptions(baseline, draft, candidate);

  assert.equal(merged.find((row) => row.case === "BASE" && row.period_id === "FY2025")?.value, 0.12);
  assert.equal(merged.find((row) => row.case === "DOWNSIDE" && row.period_id === "FY2027")?.value, -0.15);
});
