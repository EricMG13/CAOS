import test from "node:test";
import assert from "node:assert/strict";
import { withQuery } from "./workbench.ts";

test("every route path keeps its trailing slash", () => {
  assert.equal(withQuery("/run-console", { case: "case_1" }), "/run-console/?case=case_1");
  assert.equal(withQuery("/sources/", { case: "case_1" }), "/sources/?case=case_1");
  assert.equal(withQuery("/cases", {}), "/cases/");
  assert.equal(withQuery("/", {}), "/");
});

test("values set, replace, and clear query keys", () => {
  assert.equal(withQuery("/run-console?run=run_old", { run: "run_new" }), "/run-console/?run=run_new");
  assert.equal(withQuery("/run-console?run=run_old", { run: undefined }), "/run-console/");
  assert.equal(withQuery("/run-console?case=case_1", { run: "run_1" }), "/run-console/?case=case_1&run=run_1");
});
