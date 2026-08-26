import type { ReactNode } from "react";

export type EvidenceCitation = { source_id: string; block_ids: string[]; claim: string };
export type NarrativeBlock = { kind: "NARRATIVE"; block_id: string; slot_id: string; text: string; content_mode: "EVIDENCE" | "ANALYST_JUDGMENT"; citations: EvidenceCitation[] };
export type EvidenceRegisterBlock = { kind: "EVIDENCE_REGISTER"; block_id: string; slot_id: string; citations: EvidenceCitation[] };
export type LimitationsBlock = { kind: "LIMITATIONS"; block_id: string; slot_id: string; text: string; citations: EvidenceCitation[] };
export type GeneratedMetricBlock = { kind: "GENERATED_METRIC"; block_id: string; slot_id: string; metric_ids: string[] };
export type GeneratedTableBlock = { kind: "GENERATED_TABLE"; block_id: string; slot_id: string; table_id: string; field_ids: string[] };
export type GeneratedChartBlock = { kind: "GENERATED_CHART"; block_id: string; slot_id: string; recipe: Record<string, unknown> };
export type ScenarioExhibitBlock = { kind: "SCENARIO_EXHIBIT"; block_id: string; slot_id: string; title: string; shocks: Record<string, unknown>[]; scenario: Record<string, unknown>; scenario_digest: string };
export type ModelAppendixBlock = { kind: "MODEL_APPENDIX"; block_id: string; slot_id: string };
export type DeliverableBlock = NarrativeBlock | EvidenceRegisterBlock | LimitationsBlock | GeneratedMetricBlock | GeneratedTableBlock | GeneratedChartBlock | ScenarioExhibitBlock | ModelAppendixBlock;

export type TemplateBlock = { block_id: string; slot_id: string; kind: string; title: string; required: boolean; order: number };
export type FrozenPayload = {
  schema_version: string;
  case_id: string;
  pathway: string;
  draft: { id: string; version: number; digest: string };
  template: { title: string; template_id: string; template_version: string };
  authority: { accepted_snapshot_id?: string | null; accepted_snapshot_digest?: string | null; source_set_id?: string | null; source_set_digest?: string | null };
  model: (Record<string, unknown> & {
    outputs?: Record<string, unknown>;
    effective_assumptions?: Record<string, unknown>[];
    assumption_gaps?: Record<string, unknown>[];
    debt?: Record<string, unknown>;
    warnings?: Record<string, unknown>;
    application_build?: { payload?: Record<string, unknown>; qa?: Record<string, unknown>; calculation_runtime?: Record<string, unknown>; export?: Record<string, unknown> | null };
    model_export?: Record<string, unknown> | null;
  }) | null;
  content: { model_selection: Record<string, unknown> | null; model_identity?: Record<string, unknown> | null; blocks: DeliverableBlock[]; generated_blocks: Record<string, unknown> };
  evidence: { source_id?: string; sha256?: string; block_ids?: string[]; withdrawn?: boolean }[];
  methodology: Record<string, unknown>;
  renderer: Record<string, unknown>;
  input_fingerprint: string;
  preview_digest: string;
};

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unavailable";
  if (typeof value === "number") return Number.isFinite(value) ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 20 }).format(value) : "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function flatten(value: unknown, prefix = ""): { label: string; value: unknown }[] {
  if (!value || typeof value !== "object") return [{ label: prefix || "Value", value }];
  if (Array.isArray(value)) return value.flatMap((item, index) => flatten(item, `${prefix || "Item"} / ${index + 1}`));
  return Object.entries(value as Record<string, unknown>).flatMap(([key, item]) => {
    const label = prefix ? `${prefix} / ${key}` : key;
    return item && typeof item === "object" ? flatten(item, label) : [{ label, value: item }];
  });
}

function DataTable({ value, label, maxRows = 80 }: { value: unknown; label: string; maxRows?: number | null }) {
  const flattened = flatten(value);
  const rows = maxRows === null ? flattened : flattened.slice(0, maxRows);
  if (!rows.length) return <p className="paper-muted">No server-generated values are available.</p>;
  return <div className="table-wrap report-generated-table" tabIndex={0} role="region" aria-label={label}>
    <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{rows.map((row) => <tr key={row.label}><th scope="row">{row.label}</th><td className="num">{displayValue(row.value)}</td></tr>)}</tbody></table>
  </div>;
}

function CitationList({ citations }: { citations: EvidenceCitation[] }) {
  if (!citations.length) return null;
  return <ol className="report-citations" aria-label="Evidence citations">{citations.map((citation, index) => <li key={`${citation.source_id}:${citation.block_ids.join(":")}:${index}`}><span>{citation.claim}</span><code>{citation.source_id} · {citation.block_ids.join(", ")}</code></li>)}</ol>;
}

function sectionTitle(block: DeliverableBlock, templateBlocks: TemplateBlock[]): string {
  return templateBlocks.find((item) => item.block_id === block.block_id)?.title
    || (block.kind === "SCENARIO_EXHIBIT" ? block.title : block.kind.replaceAll("_", " "));
}

function FrozenEnvelope({ payload }: { payload: FrozenPayload }) {
  const model = payload.model;
  const applicationBuild = model?.application_build;
  const modelIdentity = model ? Object.fromEntries(Object.entries(model).filter(([key]) => ![
    "outputs", "effective_assumptions", "assumption_gaps", "debt", "warnings", "application_build",
  ].includes(key))) : null;
  return <div className="frozen-authority-envelope" aria-label="Exact Frozen authority envelope">
    <section className="deliverable-paper-section">
      <h3>Frozen authority</h3>
      <DataTable label="Frozen authority identities" maxRows={null} value={{ schema_version: payload.schema_version, case_id: payload.case_id, pathway: payload.pathway, accepted: payload.authority, draft: payload.draft, input_fingerprint: payload.input_fingerprint, preview_digest: payload.preview_digest }} />
    </section>
    <section className="deliverable-paper-section">
      <h3>Evidence authority</h3>
      <DataTable label="Frozen evidence authority" maxRows={null} value={payload.evidence} />
    </section>
    {model ? <>
      <section className="deliverable-paper-section"><h3>Model authority record</h3><DataTable label="Frozen model identity and export" maxRows={null} value={modelIdentity} /></section>
      <section className="deliverable-paper-section"><h3>Base / Downside Model Analysis</h3><DataTable label="Frozen Base and Downside outputs" maxRows={null} value={model.outputs || {}} /></section>
      <section className="deliverable-paper-section"><h3>Effective Assumptions</h3><DataTable label="Frozen effective assumptions" maxRows={null} value={model.effective_assumptions || []} /></section>
      <section className="deliverable-paper-section"><h3>Debt Schedule</h3><DataTable label="Frozen debt outputs" maxRows={null} value={model.debt || {}} /></section>
      <section className="deliverable-paper-section"><h3>Model Gaps and Warnings</h3><DataTable label="Frozen model gaps and warnings" maxRows={null} value={{ assumption_gaps: model.assumption_gaps || [], warnings: model.warnings || {} }} /></section>
      <section className="deliverable-paper-section"><h3>Application Model Build authority</h3><DataTable label="Frozen application build QA runtime and export" maxRows={null} value={{ qa: applicationBuild?.qa || {}, calculation_runtime: applicationBuild?.calculation_runtime || {}, export: applicationBuild?.export || null, model_export: model.model_export || null }} />{applicationBuild?.payload ? <details><summary>Application Model Build payload</summary><DataTable label="Frozen application model payload" maxRows={null} value={applicationBuild.payload} /></details> : null}</section>
    </> : <section className="deliverable-paper-section"><h3>Model authority record</h3><p className="paper-muted">No model authority is included for this pathway.</p></section>}
    <section className="deliverable-paper-section"><h3>Methodology, template, and renderer identities</h3><DataTable label="Frozen methodology template and renderer identities" maxRows={null} value={{ template: payload.template, methodology: payload.methodology, renderer: payload.renderer }} /></section>
    <section className="deliverable-paper-section"><h3>Revision Record</h3><DataTable label="Frozen revision record" maxRows={null} value={{ draft: payload.draft, input_fingerprint: payload.input_fingerprint, preview_digest: payload.preview_digest }} /></section>
  </div>;
}

function renderBlock(block: DeliverableBlock, templateBlocks: TemplateBlock[], generated: Record<string, unknown>): ReactNode {
  const title = sectionTitle(block, templateBlocks);
  if (block.kind === "NARRATIVE") return <section className="deliverable-paper-section" key={block.block_id} data-block-id={block.block_id}>
    <div className="deliverable-paper-heading"><h3>{title}</h3><span>{block.content_mode === "ANALYST_JUDGMENT" ? "Analyst judgment" : "Evidence-bound"}</span></div>
    <p>{block.text || "Not yet drafted."}</p><CitationList citations={block.citations} />
  </section>;
  if (block.kind === "EVIDENCE_REGISTER") return <section className="deliverable-paper-section" key={block.block_id} data-block-id={block.block_id}><h3>{title}</h3>{block.citations.length ? <CitationList citations={block.citations} /> : <p className="paper-muted">No citations attached.</p>}</section>;
  if (block.kind === "LIMITATIONS") return <section className="deliverable-paper-section" key={block.block_id} data-block-id={block.block_id}><h3>{title}</h3><p>{block.text}</p><CitationList citations={block.citations} /></section>;
  if (block.kind === "SCENARIO_EXHIBIT") return <section className="deliverable-paper-section" key={block.block_id} data-block-id={block.block_id}><div className="deliverable-paper-heading"><h3>{title}</h3><span>Server-calculated</span></div><p className="mono paper-digest">Scenario {block.scenario_digest}</p><DataTable label={`${title} scenario values`} value={block.scenario.outputs} /></section>;
  if (block.kind === "GENERATED_CHART") return <section className="deliverable-paper-section" key={block.block_id} data-block-id={block.block_id}><div className="deliverable-paper-heading"><h3>{title}</h3><span>Read only</span></div><DataTable label={`${title} accessible chart data`} value={generated[block.block_id]} /></section>;
  return <section className="deliverable-paper-section" key={block.block_id} data-block-id={block.block_id}><div className="deliverable-paper-heading"><h3>{title}</h3><span>Read only · server generated</span></div><DataTable label={`${title} generated values`} value={generated[block.block_id]} /></section>;
}

export default function DeliverableDocument({
  title,
  issuer,
  pathwayLabel,
  status,
  version,
  digest,
  blocks,
  templateBlocks,
  generated,
  frozen = false,
  frozenPayload = null,
}: {
  title: string;
  issuer: string;
  pathwayLabel: string;
  status: string;
  version?: number;
  digest?: string;
  blocks: DeliverableBlock[];
  templateBlocks: TemplateBlock[];
  generated: Record<string, unknown>;
  frozen?: boolean;
  frozenPayload?: FrozenPayload | null;
}) {
  return <article className="paper report-paper deliverable-document" aria-label={`${frozen ? "Frozen" : "Draft"} Deliverable preview`}>
    <header className="report-paper-header"><div><span className="paper-kicker">CAOS · {pathwayLabel}</span><h2>{issuer || title}</h2><p>{title}</p></div><div className="paper-authority"><span className={`status ${status === "FILED" ? "success" : status === "FROZEN" ? "warning" : "idle"}`}>{status}</span>{version ? <span className="mono">v{version}</span> : null}</div></header>
    {digest ? <p className="paper-digest mono">Exact identity {digest}</p> : null}
    <div className="report-paper-body">{frozenPayload ? <FrozenEnvelope payload={frozenPayload} /> : null}{blocks.map((block) => renderBlock(block, templateBlocks, generated))}</div>
  </article>;
}
