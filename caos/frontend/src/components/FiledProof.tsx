import { Cell, parseFiledMarkdown } from "../lib/filedMarkdown";

function renderCell(content: Cell) {
  return content.map((part, index) => part.kind === "code"
    ? <code className="filed-code" key={index}>{part.value}</code>
    : <span key={index}>{part.value}</span>);
}

export default function FiledProof({ markdown }: { markdown: string }) {
  return <div className="filed-body">{parseFiledMarkdown(markdown).map((block, index) => {
    if (block.kind === "heading") {
      return block.level === 1
        ? <h3 className="filed-title" key={index}>{renderCell(block.content)}</h3>
        : <h4 className="filed-section" key={index}>{renderCell(block.content)}</h4>;
    }
    if (block.kind === "table") {
      return <div className="table-wrap" key={index} tabIndex={0} role="region" aria-label="Scrollable filed report table">
        <table className="filed-table">
          <thead><tr>{block.head.map((cell, column) => <th key={column} scope="col">{renderCell(cell)}</th>)}</tr></thead>
          <tbody>{block.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, column) => <td key={column}>{renderCell(cell)}</td>)}</tr>)}</tbody>
        </table>
      </div>;
    }
    return <p className="filed-copy" key={index}>{renderCell(block.content)}</p>;
  })}</div>;
}
