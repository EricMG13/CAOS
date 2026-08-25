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
    pending: { scope: "case", context: { generation: 1, caseId: "case_a", runId: "run_a" } },
    acceptedSnapshotId: null,
  });
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
  const accepted = workspaceAuthorityReducer(hydrated, {
    type: "snapshotAccepted",
    context: requestContext(hydrated),
    snapshotId: "snapshot_a",
  });

  const state = workspaceAuthorityReducer(accepted, { type: "selectCase", caseId: "case_b" });

  assert.equal(state.caseId, "case_b");
  assert.equal(state.runId, null);
  assert.equal(state.acceptedSnapshotId, null);
  assert.equal(state.generation, accepted.generation + 1);
  assert.equal(state.status, "loading");
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

test("does not let a run refresh resolve pending case authority", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const pendingCase = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "case" });

  assert.strictEqual(
    workspaceAuthorityReducer(pendingCase, {
      type: "requestSucceeded",
      context: requestContext(pendingCase),
      scope: "run",
    }),
    pendingCase,
  );
});

test("initial registry failure fails closed over pending case authority", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const failed = workspaceAuthorityReducer(hydrated, {
    type: "requestFailed",
    context: requestContext(hydrated),
    scope: "cases",
  });

  assert.equal(failed.status, "error");
  assert.equal(failed.pending, null);
});

test("case success cannot resolve a pending run before run success", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const pendingRun = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "run" });
  const context = requestContext(pendingRun);

  assert.strictEqual(
    workspaceAuthorityReducer(pendingRun, { type: "requestSucceeded", context, scope: "case" }),
    pendingRun,
  );
  const succeeded = workspaceAuthorityReducer(pendingRun, { type: "requestSucceeded", context, scope: "run" });
  assert.equal(succeeded.status, "ready");
  assert.equal(succeeded.pending, null);
});

test("parent failure from a stale generation cannot resolve current authority", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const firstRun = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "run" });
  const staleContext = requestContext(firstRun);
  const currentRun = workspaceAuthorityReducer(firstRun, { type: "requestStarted", scope: "run" });

  assert.strictEqual(
    workspaceAuthorityReducer(currentRun, { type: "requestFailed", context: staleContext, scope: "cases" }),
    currentRun,
  );
});

test("selected case authority failure resolves its pending generation", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const selected = workspaceAuthorityReducer(hydrated, { type: "selectCase", caseId: "case_b" });

  assert.deepEqual(selected.pending, { scope: "case", context: requestContext(selected) });
  assert.equal(
    workspaceAuthorityReducer(selected, {
      type: "requestFailed",
      context: requestContext(selected),
      scope: "case",
    }).status,
    "error",
  );
});

test("rejects a late result after the selected run changes", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const started = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "run" });
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
  const lateContext = requestContext(started);
  const nextCase = workspaceAuthorityReducer(started, { type: "selectCase", caseId: "case_b" });
  const nextRun = workspaceAuthorityReducer(nextCase, { type: "selectRun", caseId: "case_b", runId: "run_b" });

  assert.strictEqual(
    workspaceAuthorityReducer(nextRun, { type: "requestSucceeded", context: lateContext, scope: "run" }),
    nextRun,
  );
  assert.deepEqual(requestContext(nextRun), { generation: 4, caseId: "case_b", runId: "run_b" });
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

test("records snapshot acceptance without resolving pending case authority", () => {
  const pendingCase = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const context = requestContext(pendingCase);
  const accepted = workspaceAuthorityReducer(pendingCase, {
    type: "snapshotAccepted",
    context,
    snapshotId: "snapshot_a",
  });

  assert.equal(accepted.status, "loading");
  assert.deepEqual(accepted.pending, pendingCase.pending);
  assert.equal(accepted.acceptedSnapshotId, "snapshot_a");

  const succeeded = workspaceAuthorityReducer(accepted, { type: "requestSucceeded", context, scope: "case" });
  assert.equal(succeeded.status, "ready");
  assert.equal(succeeded.pending, null);
  assert.equal(succeeded.acceptedSnapshotId, "snapshot_a");
});

test("accepts a matching snapshot refresh when no authority request is pending", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const started = workspaceAuthorityReducer(hydrated, { type: "requestStarted", scope: "case" });
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

test("rejects snapshot acceptance from a stale authority context", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });
  const staleContext = requestContext(hydrated);
  const selected = workspaceAuthorityReducer(hydrated, { type: "selectCase", caseId: "case_b" });

  assert.strictEqual(
    workspaceAuthorityReducer(selected, { type: "snapshotAccepted", context: staleContext, snapshotId: "snapshot_a" }),
    selected,
  );
});

test("invalidates only the active case or run authority", () => {
  const hydrated = reduce({ type: "hydrate", caseId: "case_a", runId: "run_a" });

  assert.strictEqual(workspaceAuthorityReducer(hydrated, { type: "invalidateCase", caseId: "case_b" }), hydrated);
  assert.strictEqual(workspaceAuthorityReducer(hydrated, { type: "invalidateRun", caseId: "case_a", runId: "run_b" }), hydrated);

  const runInvalidated = workspaceAuthorityReducer(hydrated, { type: "invalidateRun", caseId: "case_a", runId: "run_a" });
  assert.equal(runInvalidated.caseId, "case_a");
  assert.equal(runInvalidated.runId, null);
  assert.equal(runInvalidated.generation, hydrated.generation + 1);
  assert.deepEqual(runInvalidated.pending, { scope: "case", context: requestContext(runInvalidated) });

  const caseInvalidated = workspaceAuthorityReducer(hydrated, { type: "invalidateCase", caseId: "case_a" });
  assert.equal(caseInvalidated.caseId, null);
  assert.equal(caseInvalidated.runId, null);
  assert.equal(caseInvalidated.status, "idle");
});
