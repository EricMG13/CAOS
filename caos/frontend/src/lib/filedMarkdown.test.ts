import test from "node:test";
import assert from "node:assert/strict";
import { parseFiledMarkdown } from "./filedMarkdown.ts";

test("parses the two heading levels", () => {
  const blocks = parseFiledMarkdown("# CAOS Credit Snapshot\n\n## Analyst thesis\n");
  assert.deepEqual(blocks, [
    { kind: "heading", level: 1, content: [{ kind: "text", value: "CAOS Credit Snapshot" }] },
    { kind: "heading", level: 2, content: [{ kind: "text", value: "Analyst thesis" }] },
  ]);
});

test("splits inline code out of a paragraph", () => {
  const blocks = parseFiledMarkdown("Snapshot digest: `0f27202e`\n");
  assert.deepEqual(blocks, [{
    kind: "paragraph",
    content: [
      { kind: "text", value: "Snapshot digest: " },
      { kind: "code", value: "0f27202e" },
    ],
  }]);
});

test("parses a pipe table with its divider row", () => {
  const source = [
    "| Instrument | Recommendation |",
    "| --- | --- |",
    "| Zenith 1L 2031 | MARKET WEIGHT |",
    "",
  ].join("\n");
  assert.deepEqual(parseFiledMarkdown(source), [{
    kind: "table",
    head: [[{ kind: "text", value: "Instrument" }], [{ kind: "text", value: "Recommendation" }]],
    rows: [[[{ kind: "text", value: "Zenith 1L 2031" }], [{ kind: "text", value: "MARKET WEIGHT" }]]],
  }]);
});

test("analyst free text containing pipes stays a paragraph", () => {
  const blocks = parseFiledMarkdown("Headroom is thin | watch Q4 closely\n");
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].kind, "paragraph");
});

test("analyst free text starting with a hash is not promoted to a heading", () => {
  const blocks = parseFiledMarkdown("#1 risk is the covenant step-down\n");
  assert.equal(blocks[0].kind, "paragraph");
});

test("returns an empty list for empty input", () => {
  assert.deepEqual(parseFiledMarkdown(""), []);
});
