// The filed report is produced by caos/server/caos/publishing/domain.py::render_markdown,
// so the grammar is closed: two heading levels, paragraphs, inline `code`, and one
// pipe table. This is deliberately not a general Markdown parser.

export type Inline = { kind: "text"; value: string } | { kind: "code"; value: string };
export type Cell = Inline[];
export type Block =
  | { kind: "heading"; level: 1 | 2; content: Cell }
  | { kind: "paragraph"; content: Cell }
  | { kind: "table"; head: Cell[]; rows: Cell[][] };

function parseInline(text: string): Cell {
  const parts = text.split("`");
  const content: Cell = [];
  for (let index = 0; index < parts.length; index += 1) {
    if (parts[index] === "") continue;
    content.push({ kind: index % 2 === 1 ? "code" : "text", value: parts[index] });
  }
  return content;
}

const isRow = (line: string) => line.startsWith("|") && line.endsWith("|") && line.length > 1;
const isDivider = (line: string) => isRow(line) && /^\|[\s|:-]+\|$/.test(line) && line.includes("-");
const toCells = (line: string): Cell[] =>
  line.slice(1, -1).split("|").map((cell) => parseInline(cell.trim()));

export function parseFiledMarkdown(source: string): Block[] {
  const lines = source.split("\n");
  const blocks: Block[] = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line) continue;
    if (line.startsWith("## ")) {
      blocks.push({ kind: "heading", level: 2, content: parseInline(line.slice(3)) });
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push({ kind: "heading", level: 1, content: parseInline(line.slice(2)) });
      continue;
    }
    if (isRow(line) && isDivider((lines[index + 1] ?? "").trim())) {
      const head = toCells(line);
      const rows: Cell[][] = [];
      index += 2;
      while (index < lines.length && isRow(lines[index].trim())) {
        rows.push(toCells(lines[index].trim()));
        index += 1;
      }
      index -= 1;
      blocks.push({ kind: "table", head, rows });
      continue;
    }
    blocks.push({ kind: "paragraph", content: parseInline(line) });
  }
  return blocks;
}
