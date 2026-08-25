import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  initialAuthorityState,
  matchesAuthority,
  requestContext,
  workspaceAuthorityReducer,
} from "./workspaceAuthority.ts";

const reduce = (event: Parameters<typeof workspaceAuthorityReducer>[1]) => workspaceAuthorityReducer(initialAuthorityState, event);

test("case authority refresh follows every reducer generation", () => {
  const workspace = readFileSync(new URL("../components/Workspace.tsx", import.meta.url), "utf8");
  const effect = workspace.match(/void refreshCase\(caseId, controller\.signal\);[\s\S]*?\}, \[([^\]]+)\]\);/);

  assert.ok(effect, "case authority refresh effect is present");
  assert.match(effect[1], /\bauthorityState\.generation\b/);
});

test("hydrates route authority as a loading case/run boundary", () => {
  const state = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });

  assert.deepEqual(state, {
    caseId: "case_a",
    runId: "run_a",
    hydrated: true,
    status: "loading",
    generation: 1,
    pending: {
      scope: "case",
      context: { generation: 1, caseId: "case_a", runId: "run_a" },
    },
    acceptedSnapshotId: null,
  });
  assert.strictEqual(workspaceAuthorityReducer(state, {
    type: "requestSucceeded",
    context: requestContext(state),
    scope: "cases",
  }), state);
  assert.strictEqual(workspaceAuthorityReducer(state, {
    type: "requestFailed",
    context: requestContext(state),
    scope: "cases",
  }), state);
});

test("hydrates an empty route into a new authority generation", () => {
  const beforeHydration = requestContext(initialAuthorityState);
  const hydrated = reduce({ type: "hydrate", caseId: null, runId: null });

  assert.equal(hydrated.generation, initialAuthorityState.generation + 1);
  assert.strictEqual(
    workspaceAuthorityReducer(hydrated, { type: "requestSucceeded", context: beforeHydration, scope: "case" }),
    hydrated,
  );
});

test("selecting a different case clears the selected run and snapshot authority", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const ready = workspaceAuthorityReducer(hydrated, {
    type: "requestSucceeded",
    context: requestContext(hydrated),
    scope: "case",
  });
  const accepted = workspaceAuthorityReducer(ready, {
    type: "snapshotAccepted",
    context: requestContext(ready),
    snapshotId: "snapshot_a",
  });

  const state = workspaceAuthorityReducer(accepted, { type: "selectCase", caseId: "case_b" });

  assert.equal(state.caseId, "case_b");
  assert.equal(state.runId, null);
  assert.equal(state.acceptedSnapshotId, null);
  assert.equal(state.generation, accepted.generation + 1);
  assert.equal(state.status, "loading");
  assert.deepEqual(state.pending, { scope: "case", context: requestContext(state) });
});

test("rejects a run selected for a different case without changing state", () => {
  const state = reduce({ type: "hydrate", caseId: "case_a", runId: null });

  assert.strictEqual(workspaceAuthorityReducer(state, { type: "selectRun", caseId: "case_b", runId: "run_b" }), state);
});

test("starting a request increments generation and records its context", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const state = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "case" });

  assert.equal(state.generation, hydrated.generation + 1);
  assert.deepEqual(state.pending, { scope: "case", context: requestContext(state) });
  assert.equal(state.status, "loading");
});

test("rejects a previous-generation completion for the same case and run", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const first = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "case" });
  const replacement = workspaceAuthorityReducer(first, { type: "requestStarted", scope: "case" });

  assert.strictEqual(
    workspaceAuthorityReducer(replacement, { type: "requestSucceeded", context: requestContext(first), scope: "case" }),
    replacement,
  );
});

test("only a matching case completion can terminate authority after case and run selection", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const selectedCase = workspaceAuthorityReducer(hydrated, { type: "selectCase", caseId: "case_b" });
  const selectedRun = workspaceAuthorityReducer(selectedCase, { type: "selectRun", caseId: "case_b", runId: "run_b" });
  const context = requestContext(selectedRun);

  assert.equal(selectedRun.status, "loading");
  assert.deepEqual(selectedRun.pending, { scope: "case", context });

  const afterRunSuccess = workspaceAuthorityReducer(selectedRun, { type: "requestSucceeded", context, scope: "run" });
  assert.strictEqual(afterRunSuccess, selectedRun);
  const afterRunFailure = workspaceAuthorityReducer(afterRunSuccess, { type: "requestFailed", context, scope: "run" });
  assert.strictEqual(afterRunFailure, selectedRun);

  const failed = workspaceAuthorityReducer(afterRunFailure, { type: "requestFailed", context, scope: "case" });
  assert.equal(failed.status, "error");
  assert.equal(failed.pending, null);
});

test("unrelated completions cannot alter resolved case authority", () => {
  const pendingCase = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const context = requestContext(pendingCase);
  const completed = workspaceAuthorityReducer(pendingCase, { type: "requestSucceeded", context, scope: "case" });

  assert.equal(completed.status, "ready");
  assert.equal(completed.pending, null);

  const afterRunSuccess = workspaceAuthorityReducer(completed, { type: "requestSucceeded", context, scope: "run" });
  assert.strictEqual(afterRunSuccess, completed);
  const afterRunFailure = workspaceAuthorityReducer(completed, { type: "requestFailed", context, scope: "run" });
  assert.strictEqual(afterRunFailure, completed);

  const failedCaseRefresh = workspaceAuthorityReducer(completed, { type: "requestFailed", context, scope: "case" });
  assert.equal(failedCaseRefresh.status, "error");
});

test("rejects a late result after the selected run changes", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const started = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "run" });
  assert.strictEqual(started, hydrated);
  const lateContext = requestContext(started);
  const nextRun = workspaceAuthorityReducer(started, { type: "selectRun", caseId: "case_a", runId: "run_b" });

  assert.strictEqual(
    workspaceAuthorityReducer(nextRun, { type: "requestSucceeded", context: lateContext, scope: "run" }),
    nextRun,
  );
  assert.equal(matchesAuthority(nextRun, lateContext), false);
});

test("rejects a late response after selecting a different case and run", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const started = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "run" });
  assert.strictEqual(started, hydrated);
  const lateContext = requestContext(started);
  const nextCase = workspaceAuthorityReducer(started, { type: "selectCase", caseId: "case_b" });
  const nextRun = workspaceAuthorityReducer(nextCase, { type: "selectRun", caseId: "case_b", runId: "run_b" });

  assert.strictEqual(
    workspaceAuthorityReducer(nextRun, { type: "requestSucceeded", context: lateContext, scope: "run" }),
    nextRun,
  );
  assert.deepEqual(requestContext(nextRun), { generation: 3, caseId: "case_b", runId: "run_b" });
  assert.equal(matchesAuthority(nextRun, lateContext), false);
});

test("rejects a stale failed request", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const started = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "case" });
  const nextRun = workspaceAuthorityReducer(started, { type: "selectRun", caseId: "case_a", runId: "run_b" });

  assert.strictEqual(
    workspaceAuthorityReducer(nextRun, { type: "requestFailed", context: requestContext(started), scope: "case" }),
    nextRun,
  );
});

test("accepts a matching snapshot refresh", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const started = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "case" });
  assert.strictEqual(workspaceAuthorityReducer(started, {
    type: "snapshotAccepted",
    context: requestContext(started),
    snapshotId: "snapshot_a",
  }), started);
  const succeeded = workspaceAuthorityReducer(started, { type: "requestSucceeded", context: requestContext(started), scope: "case" });
  const state = workspaceAuthorityReducer(succeeded, {
    type: "snapshotAccepted",
    context: requestContext(succeeded),
    snapshotId: "snapshot_a",
  });

  assert.equal(state.status, "ready");
  assert.equal(state.acceptedSnapshotId, "snapshot_a");
  assert.equal(state.pending, null);
});

test("invalidates only the active case or run authority", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });

  assert.strictEqual(workspaceAuthorityReducer(hydrated, { type: "invalidateCase", caseId: "case_b" }), hydrated);
  assert.strictEqual(workspaceAuthorityReducer(hydrated, { type: "invalidateRun", caseId: "case_a", runId: "run_b" }), hydrated);

  const runInvalidated = workspaceAuthorityReducer(hydrated, { type: "invalidateRun", caseId: "case_a", runId: "run_a" });
  assert.equal(runInvalidated.caseId, "case_a");
  assert.equal(runInvalidated.runId, null);
  assert.equal(runInvalidated.generation, hydrated.generation + 1);

  const caseInvalidated = workspaceAuthorityReducer(hydrated, { type: "invalidateCase", caseId: "case_a" });
  assert.equal(caseInvalidated.caseId, null);
  assert.equal(caseInvalidated.runId, null);
  assert.equal(caseInvalidated.status, "idle");
});
