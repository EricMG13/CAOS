import assert from "node:assert/strict";
import test from "node:test";
import { api } from "./api.ts";

test("api returns parsed JSON from successful responses", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(JSON.stringify({ id: "case_1" }), { status: 200 });

  assert.deepEqual(await api<{ id: string }>("/api/cases/case_1"), { id: "case_1" });
});

test("api parses empty 204 responses without a special case", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(null, { status: 204 });

  await assert.rejects(api("/api/cases/case_1"), SyntaxError);
});

test("api extracts stable error details", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: "Case access denied" }), { status: 403 });

  await assert.rejects(api("/api/cases/case_1"), new Error("Case access denied"));
});
