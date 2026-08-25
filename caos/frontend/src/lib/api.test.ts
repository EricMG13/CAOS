import assert from "node:assert/strict";
import test from "node:test";
import { api } from "./api.ts";

test("api returns parsed JSON from successful responses", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(JSON.stringify({ id: "case_1" }), { status: 200 });

  assert.deepEqual(await api<{ id: string }>("/api/cases/case_1"), { id: "case_1" });
});

test("api resolves successful 204 responses without parsing JSON", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(null, { status: 204 });

  assert.equal(await api<void>("/api/cases/case_1"), undefined);
});

test("api still parses non-204 successful responses as JSON", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(null, { status: 200 });

  await assert.rejects(api("/api/cases/case_1"), SyntaxError);
});

test("api extracts stable error details", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: "Case access denied" }), { status: 403 });

  await assert.rejects(api("/api/cases/case_1"), new Error("Case access denied"));
});
