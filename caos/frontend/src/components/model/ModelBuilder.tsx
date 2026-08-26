"use client";

import Link from "next/link";
import { KeyboardEvent as ReactKeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api as request, assumptionRegistryPath, type ModelInventory, type ModelReadiness, type WorksheetCell, type WorksheetResponse, type WorksheetTab } from "../../lib/api";
import { withQuery } from "../../lib/workbench";
import {
  applicationBuildDelta,
  applyAssumptionValue,
  applyServerAssumptions,
  assumptionChangeCount,
  assumptionKey,
  assumptionScope,
  mergeRebasedAssumptions,
  normalizeAssumptions,
  previewMatchesDraft,
  primaryModelAction,
  sensitivityPeriodRows,
  type AssumptionDefinition,
  type AssumptionRegistry,
  type ModelAssumptionValue,
  type ModelCase,
  type ModelPreview,
  type WireAssumptionValue,
} from "./modelBuilderState";

const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

const worksheetFillClasses: Record<string, string> = {
  "0a2e63": "worksheet-fill-section",
  "1f4e78": "worksheet-fill-header",
  d9eaf7: "worksheet-fill-subheader",
  eaf3f8: "worksheet-fill-label",
  fff4cc: "worksheet-fill-input",
  e2f0d9: "worksheet-fill-positive",
  fce4d6: "worksheet-fill-negative",
  e7e6e6: "worksheet-fill-muted",
};

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function LoadState({ loading, error }: { loading: boolean; error?: string }) {
  if (loading) return <div className="state-skeleton" role="status" aria-live="polite" aria-label="Loading"><span /><span /><span /></div>;
  return <div className="empty error-state" role="alert"><strong>Unable to load this view.</strong><p>{error}</p><button className="button small" type="button" onClick={() => window.location.reload()}>Retry</button></div>;
}

function formatWorksheetValue(cell?: WorksheetCell) {
  if (!cell || cell.value === null || cell.value === "") return "";
  if (typeof cell.value !== "number") return String(cell.value);
  if (cell.number_format.includes("%")) return `${(cell.value * 100).toFixed(1)}%`;
  if (cell.number_format.includes("0.0x")) return `${cell.value.toFixed(1)}x`;
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(cell.value);
}

function WorksheetGrid({ tab, selected, onSelect }: { tab: WorksheetTab; selected: WorksheetCell | null; onSelect: (cell: WorksheetCell) => void }) {
  const cells = useMemo(() => new Map(tab.cells.map((cell) => [`${cell.row}:${cell.column}`, cell])), [tab.cells]);
  const [activeCell, setActiveCell] = useState({ row: 1, column: 1 });
  const onCellKeyDown = (event: ReactKeyboardEvent<HTMLTableCellElement>, row: number, column: number, cell?: WorksheetCell) => {
    if ((event.key === "Enter" || event.key === " ") && cell && (cell.source_refs || cell.formula)) {
      event.preventDefault();
      onSelect(cell);
      return;
    }
    const movement = {
      ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1],
    }[event.key];
    if (!movement) return;
    event.preventDefault();
    const next = {
      row: Math.min(tab.max_row, Math.max(1, row + movement[0])),
      column: Math.min(tab.max_column, Math.max(1, column + movement[1])),
    };
    setActiveCell(next);
    event.currentTarget.closest("table")?.querySelector<HTMLTableCellElement>(`td[data-row="${next.row}"][data-column="${next.column}"]`)?.focus();
  };
  return <div className="worksheet-scroll" tabIndex={0} role="region" aria-label={`${tab.name} worksheet; scroll horizontally and vertically`}>
    <table className="worksheet-grid">
      <caption className="sr-only">Read-only {tab.name} worksheet. Formula values are calculated by CP-MODEL on the server.</caption>
      <colgroup><col className="worksheet-row-number" />{tab.columns.map((column) => <col key={column.column} style={{ width: `${Math.min(200, Math.max(48, (column.width || 10) * 7))}px` }} />)}</colgroup>
      <thead><tr><th scope="col"><span className="sr-only">Row number</span></th>{tab.columns.map((column) => <th scope="col" key={column.column}>{column.letter}</th>)}</tr></thead>
      <tbody>{Array.from({ length: tab.max_row }, (_, rowIndex) => {
        const row = rowIndex + 1;
        return <tr key={row}><th scope="row">{row}</th>{Array.from({ length: tab.max_column }, (_unused, columnIndex) => {
          const cell = cells.get(`${row}:${columnIndex + 1}`);
          const fillClass = cell?.style.fill ? worksheetFillClasses[cell.style.fill.toLowerCase()] || "" : "";
          const className = ["worksheet-cell", fillClass, cell?.style.bold ? "is-bold" : "", cell?.style.italic ? "is-italic" : "", cell?.value_type === "number" || cell?.value_type === "formula" && typeof cell.value === "number" ? "num" : "", selected?.address === cell?.address ? "is-selected" : ""].filter(Boolean).join(" ");
          const value = formatWorksheetValue(cell);
          const column = columnIndex + 1;
          const address = cell?.address || `${tab.columns[columnIndex]?.letter || column}${row}`;
          const hasLineage = Boolean(cell && (cell.source_refs || cell.formula));
          return <td key={column} className={className} title={cell?.formula || undefined} data-address={address} data-row={row} data-column={column} tabIndex={activeCell.row === row && activeCell.column === column ? 0 : -1} aria-label={`${address}: ${value === "" ? "blank" : value}${hasLineage ? ". Press Enter to show lineage." : ""}`} onFocus={() => setActiveCell({ row, column })} onKeyDown={(event) => onCellKeyDown(event, row, column, cell)}>{hasLineage && cell ? <button className="worksheet-cell-link" type="button" tabIndex={-1} aria-label={`Show lineage for ${cell.semantic_id || cell.address}`} aria-controls="model-cell-lineage" aria-expanded={selected?.address === cell.address} onClick={() => { setActiveCell({ row, column }); onSelect(cell); }}>{value || "—"}</button> : value}</td>;
        })}</tr>;
      })}</tbody>
    </table>
  </div>;
}

function modelStatusTone(status?: ModelReadiness["status"]) {
  if (status === "READY") return "success";
  if (status === "FAILED" || status === "NOT_READY") return "critical";
  return "warning";
}

type BuilderView = "MODEL" | "ASSUMPTIONS" | "SENSITIVITIES" | "HISTORY";
const builderViews: { id: BuilderView; label: string }[] = [
  { id: "MODEL", label: "Model" },
  { id: "ASSUMPTIONS", label: "Assumptions" },
  { id: "SENSITIVITIES", label: "Sensitivities" },
  { id: "HISTORY", label: "History" },
];
type RevisionExport = { status: "NOT_REQUESTED" | "QUEUED" | "EXPORTING" | "READY" | "FAILED"; error?: { code: string; detail: string } | null; filename?: string; sha256?: string; size?: number };
type ModelRevision = Omit<ModelPreview, "draft_generation" | "deltas"> & {
  id: string;
  effective_assumptions: WireAssumptionValue[];
  note: string;
  revision_number: number;
  signed_by: string;
  signed_at: string;
  state: "ACTIVE" | "SUPERSEDED" | "STALE";
  export: RevisionExport;
};
type RebasePreview = {
  source_revision_id: string;
  source_build_id: string;
  build_id: string;
  draft_generation: number;
  compatible: Record<string, unknown>[];
  changed: Record<string, unknown>[];
  invalidated: Record<string, unknown>[];
  candidate_assumptions: WireAssumptionValue[];
  preview: ModelPreview | null;
};
type ScenarioResult = {
  draft_generation: number;
  baseline: Record<string, unknown>;
  scenario: { effective_assumptions: WireAssumptionValue[]; outputs: Record<string, unknown>; deltas: Record<string, unknown> };
  scenario_digest: string;
};
type AnnualOutputs = Record<string, Record<string, Record<string, unknown>>>;
type SensitivityPoint = { value: number | string; outputs: AnnualOutputs; deltas: AnnualOutputs };
type SensitivityResult = {
  draft_generation: number;
  build_id: string;
  assumption_id: string;
  case: ModelCase;
  period_scope: string;
  output_id: string;
  points: SensitivityPoint[];
  breakpoint: Record<string, unknown> | null;
};
type ConflictMetadata = { current?: ModelRevision | null; current_build?: { id?: string; input_fingerprint?: string; payload_digest?: string } | null };
type DraftAuthority = { buildId: string; registryDigest: string; parentRevisionId: string | null };

class ModelRequestError extends Error {
  constructor(readonly status: number, readonly detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
  }
}

async function modelRequest<T>(path: string, options: RequestInit, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...options, signal, headers: { "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ModelRequestError(response.status, body?.detail ?? body);
  return body as T;
}

function formatModelValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unavailable";
  if (typeof value === "number") return Number.isFinite(value) ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value) : "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function outputEntries(value: Record<string, unknown>, prefix = ""): { label: string; value: unknown }[] {
  return Object.entries(value).flatMap(([key, item]) => {
    const label = prefix ? `${prefix} / ${key}` : key;
    if (item && typeof item === "object" && !Array.isArray(item)) return outputEntries(item as Record<string, unknown>, label);
    return [{ label, value: item }];
  });
}

function OutputTable({ label, outputs }: { label: string; outputs: Record<string, unknown> }) {
  const entries = outputEntries(outputs);
  return <div className="table-wrap" tabIndex={0} role="region" aria-label={label}><table><thead><tr><th scope="col">Output</th><th scope="col">Value</th></tr></thead><tbody>{entries.length ? entries.map((item) => <tr key={item.label}><th scope="row">{item.label.replaceAll("_", " ")}</th><td className="num">{formatModelValue(item.value)}</td></tr>) : <tr><td colSpan={2} className="muted">No calculated outputs are available.</td></tr>}</tbody></table></div>;
}

function ControlledAssumptionInput({
  value,
  mixed = false,
  disabled,
  label,
  describedBy,
  onCommit,
}: {
  value: string;
  mixed?: boolean;
  disabled: boolean;
  label: string;
  describedBy?: string;
  onCommit: (value: string) => boolean;
}) {
  const [input, setInput] = useState(value);
  const commit = () => {
    if (input.trim() === "" || !onCommit(input)) setInput(value);
  };
  return <input
    aria-label={label}
    aria-describedby={describedBy}
    type="number"
    inputMode="decimal"
    step="any"
    value={input}
    placeholder={mixed ? "Mixed" : undefined}
    disabled={disabled}
    onChange={(event) => setInput(event.currentTarget.value)}
    onBlur={commit}
    onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
  />;
}

function firstErrorMessage(caught: unknown, fallback: string) {
  if (caught instanceof ModelRequestError && caught.detail && typeof caught.detail === "object") {
    const detail = caught.detail as { detail?: string; code?: string };
    return detail.detail || detail.code || fallback;
  }
  return caught instanceof Error ? caught.message : fallback;
}

function ApplicationModelBuild({ caseId, role }: { caseId: string; role: string }) {
  const [inventory, setInventory] = useState<ModelInventory | null>(null);
  const [worksheet, setWorksheet] = useState<WorksheetResponse | null>(null);
  const [activeTab, setActiveTab] = useState("CREDIT_SNAPSHOT");
  const [selectedCell, setSelectedCell] = useState<WorksheetCell | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState("");
  const [readyCaseId, setReadyCaseId] = useState("");
  const requestId = useRef(0);
  const actionId = useRef(0);
  const worksheetRef = useRef<WorksheetResponse | null>(null);
  const refresh = useCallback(async (signal?: AbortSignal, showLoading = true) => {
    if (!caseId) return;
    const expectedCaseId = caseId;
    const currentRequest = ++requestId.current;
    if (showLoading) setLoading(true);
    setLoadError("");
    try {
      const next = await request<ModelInventory>(`/api/cases/${caseId}/models`, {}, signal);
      if (currentRequest !== requestId.current || expectedCaseId !== caseId) return;
      const build = next.readiness.build || next.builds[0] || null;
      let nextWorksheet: WorksheetResponse | null = null;
      if (build?.status === "READY") {
        const cached = worksheetRef.current;
        const cacheMatches = cached?.build_id === build.id
          && cached.input_fingerprint === build.input_fingerprint
          && (!build.payload_digest || cached.payload_digest === build.payload_digest);
        nextWorksheet = cacheMatches
          ? cached
          : await request<WorksheetResponse>(`/api/cases/${caseId}/models/${build.id}/worksheet`, {}, signal);
        if (nextWorksheet.build_id !== build.id
          || nextWorksheet.input_fingerprint !== build.input_fingerprint
          || build.payload_digest && nextWorksheet.payload_digest !== build.payload_digest) {
          throw new Error("Model worksheet identity does not match the selected build.");
        }
      }
      if (currentRequest !== requestId.current || expectedCaseId !== caseId) return;
      if (worksheetRef.current !== nextWorksheet) setSelectedCell(null);
      worksheetRef.current = nextWorksheet;
      setInventory(next);
      setWorksheet(nextWorksheet);
      setReadyCaseId(caseId);
    } catch (caught) {
      if (currentRequest !== requestId.current || expectedCaseId !== caseId || caught instanceof DOMException && caught.name === "AbortError") return;
      setLoadError(caught instanceof Error ? caught.message : "Unable to load Model Builder");
      setReadyCaseId(expectedCaseId);
    } finally {
      if (currentRequest === requestId.current && expectedCaseId === caseId) setLoading(false);
    }
  }, [caseId]);
  // Model state is an external synchronization boundary; reset selection when its case changes.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { requestId.current += 1; actionId.current += 1; worksheetRef.current = null; setSelectedCell(null); setReadyCaseId(""); setMessage(""); setPending(""); const controller = new AbortController(); void refresh(controller.signal); return () => { controller.abort(); requestId.current += 1; actionId.current += 1; }; }, [refresh]);
  const status = inventory?.readiness.status;
  const build = inventory?.readiness.build || inventory?.builds[0] || null;
  const exportStatus = build?.export.status;
  useEffect(() => {
    if (status !== "QUEUED" && status !== "BUILDING" && exportStatus !== "QUEUED" && exportStatus !== "EXPORTING") return;
    let cancelled = false;
    let timer = 0;
    const poll = async () => {
      await refresh(undefined, false);
      if (!cancelled) timer = window.setTimeout(() => { void poll(); }, 1500);
    };
    timer = window.setTimeout(() => { void poll(); }, 1500);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [exportStatus, refresh, status]);
  const tab = worksheet?.payload.tabs.find((item) => item.id === activeTab) || worksheet?.payload.tabs[0] || null;
  const canWrite = role !== "READER";
  const buildModel = async () => {
    const currentAction = ++actionId.current;
    setPending("build"); setMessage("");
    try { await request(`/api/cases/${caseId}/models`, { method: "POST" }); if (currentAction !== actionId.current) return; setMessage(status === "FAILED" ? "Model rebuild queued." : "Model build queued."); await refresh(undefined, false); }
    catch (caught) { if (currentAction === actionId.current) setMessage(caught instanceof Error ? caught.message : "Unable to queue model build"); }
    finally { if (currentAction === actionId.current) setPending(""); }
  };
  const exportModel = async () => {
    if (!build) return;
    const currentAction = ++actionId.current;
    setPending("export"); setMessage("");
    try { await request(`/api/cases/${caseId}/models/${build.id}/export`, { method: "POST" }); if (currentAction !== actionId.current) return; setMessage(build.export.status === "FAILED" ? "XLSX export retry queued." : "XLSX export queued."); await refresh(undefined, false); }
    catch (caught) { if (currentAction === actionId.current) setMessage(caught instanceof Error ? caught.message : "Unable to queue XLSX export"); }
    finally { if (currentAction === actionId.current) setPending(""); }
  };
  const selectTab = (nextTab: WorksheetTab) => { setActiveTab(nextTab.id); setSelectedCell(null); };
  const onTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!worksheet || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = worksheet.payload.tabs;
    const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    selectTab(tabs[nextIndex]);
    document.getElementById(`model-tab-${tabs[nextIndex].id}`)?.focus();
  };
  if (loadError && readyCaseId === caseId) return <div className="grid"><section className="panel span-12"><div className="panel-header"><h2>Model Builder</h2><span className="status critical">Unavailable</span></div><div className="panel-body"><LoadState loading={false} error={loadError} /></div></section></div>;
  if (!caseId || readyCaseId !== caseId || loading && !inventory) return <div className="grid"><section className="panel span-12"><div className="panel-header"><h2>Model Builder</h2></div><div className="panel-body"><LoadState loading error={loadError} /></div></section></div>;
  return <div className="grid model-builder">
    <section className="panel span-12"><div className="panel-header"><h2>Model Builder</h2><span className={`status ${modelStatusTone(status)}`} role="status" aria-live="polite" aria-atomic="true">{status?.replaceAll("_", " ")}</span></div><div className="panel-body model-summary"><div><p className="eyebrow">ACCEPTED AUTHORITY</p><dl className="state-facts"><dt>Snapshot</dt><dd className="mono">{inventory?.readiness.accepted_snapshot?.id || "Not accepted"}</dd><dt>Source set</dt><dd className="mono">{inventory?.readiness.source_set ? `v${inventory.readiness.source_set.version} · ${inventory.readiness.source_set.id}` : "Unavailable"}</dd><dt>Build</dt><dd className="mono">{build?.id || "Not built"}</dd></dl></div><div><p className="eyebrow">HANDOFF GATE</p><ul className="model-requirements">{inventory?.readiness.requirements.map((item) => <li key={item.module_id}><span className={`status ${item.status === "READY" ? "success" : "critical"}`}>{item.module_id}</span><span className="mono muted">{item.digest?.slice(0, 12) || item.status}</span></li>)}</ul></div><div className="model-actions">{status === "NOT_READY" ? <Link className="button small" href={withQuery("/run-console", { case: caseId })}>Open Run Console</Link> : canWrite && (status === "READY_TO_BUILD" || status === "FAILED") ? <button className="button primary" type="button" disabled={pending === "build"} onClick={() => void buildModel()}>{pending === "build" ? "Queuing…" : status === "FAILED" ? "Retry build" : "Build model"}</button> : null}<button className="button small" type="button" disabled={loading} onClick={() => void refresh()}>{loading ? "Refreshing…" : "Refresh"}</button></div></div>{inventory?.readiness.blockers.map((blocker) => <div className="callout warning model-blocker" key={blocker.code}><strong>{blocker.code.replaceAll("_", " ")}</strong><br />{blocker.detail}</div>)}{message ? <p className={message.includes("Unable") || message.includes("NOT_") ? "error" : "muted"} role="status">{message}</p> : null}</section>
    {status === "READY" && worksheet && tab ? <><section className="panel model-sheet"><div className="panel-header"><h2>{worksheet.payload.identity.issuer_name}</h2><span className="panel-meta">READ ONLY · {worksheet.payload.identity.analysis_date}</span></div><div className="worksheet-tabs" role="tablist" aria-label="Model worksheets">{worksheet.payload.tabs.map((item, index) => <button id={`model-tab-${item.id}`} key={item.id} className="worksheet-tab" type="button" role="tab" aria-selected={item.id === tab.id} aria-controls="model-worksheet-panel" tabIndex={item.id === tab.id ? 0 : -1} onClick={() => selectTab(item)} onKeyDown={(event) => onTabKeyDown(event, index)}>{item.name}</button>)}</div><div id="model-worksheet-panel" role="tabpanel" aria-labelledby={`model-tab-${tab.id}`}><WorksheetGrid key={tab.id} tab={tab} selected={selectedCell} onSelect={setSelectedCell} /></div></section><section className="panel model-lineage" id="model-cell-lineage" aria-labelledby="model-cell-lineage-heading"><div className="panel-header"><h2 id="model-cell-lineage-heading">Cell lineage</h2><span className="panel-meta">ONE CLICK</span></div><div className="panel-body flow">{selectedCell ? <><dl className="state-facts"><dt>Cell</dt><dd className="mono">{tab.name}!{selectedCell.address}</dd><dt>Semantic ID</dt><dd className="mono">{selectedCell.semantic_id}</dd><dt>Owner</dt><dd>{selectedCell.owner}</dd><dt>Period</dt><dd className="mono">{selectedCell.period_id || "—"}</dd></dl>{selectedCell.formula ? <><p className="eyebrow">FORMULA</p><code className="lineage-code">{selectedCell.formula}</code></> : null}<p className="eyebrow">SOURCE REFS</p><p className="mono lineage-source">{selectedCell.source_refs || "Calculated by CP-MODEL from mapped inputs."}</p></> : <p className="muted">Select a sourced or calculated worksheet value to inspect its lineage.</p>}</div></section><section className="panel span-12"><div className="panel-header"><h2>Model QA & export</h2><span className={`status ${build?.qa?.status === "PASS" ? "success" : "warning"}`}>{build?.qa?.status || "Pending"}</span></div><div className="panel-body model-export"><dl className="state-facts"><dt>Semantic checks</dt><dd className="num">{build?.qa?.semantic_check_count ?? "—"}</dd><dt>Formula cells</dt><dd className="num">{build?.qa?.formula_count ?? "—"}</dd><dt>Worksheet cells</dt><dd className="num">{build?.qa?.worksheet_cell_count ?? "—"}</dd><dt>Payload</dt><dd className="mono">{build?.payload_digest || "—"}</dd><dt>XLSX</dt><dd>{build?.export.status.replaceAll("_", " ")}</dd></dl><div className="row-actions">{canWrite && build?.export.status === "NOT_REQUESTED" ? <button className="button" type="button" disabled={pending === "export"} onClick={() => void exportModel()}>{pending === "export" ? "Queuing…" : "Export XLSX"}</button> : null}{canWrite && build?.export.status === "FAILED" ? <button className="button" type="button" disabled={pending === "export"} onClick={() => void exportModel()}>{pending === "export" ? "Queuing…" : "Retry export"}</button> : null}{build?.export.status === "READY" ? <a className="button primary" href={`${apiBase}/api/cases/${caseId}/models/${build.id}/download`} download>Download XLSX</a> : null}{build?.export.status === "QUEUED" || build?.export.status === "EXPORTING" ? <button className="button" type="button" disabled>{build.export.status === "QUEUED" ? "Export queued" : "Exporting…"}</button> : null}</div></div>{build?.export.status === "FAILED" && build.export.error ? <div className="callout warning model-blocker" role="alert"><strong>{build.export.error.code}</strong><br />{build.export.error.detail}</div> : null}</section></> : status === "FAILED" ? <section className="panel span-12"><div className="panel-body"><div className="callout warning"><strong>{build?.error?.code || "MODEL_CALCULATION_FAILED"}</strong><br />{build?.error?.detail || "The model calculation did not complete."}</div></div></section> : status === "QUEUED" || status === "BUILDING" ? <section className="panel span-12"><div className="panel-body"><div className="callout"><strong>{status === "QUEUED" ? "Build queued" : "Calculating worksheet"}</strong><br />The worker is validating canonical inputs, reconciling the Python model, and persisting the read-only worksheet payload.</div></div></section> : null}
    {inventory?.builds.length ? <section className="panel span-12"><div className="panel-header"><h2>Build history</h2><span className="panel-meta">IMMUTABLE FINGERPRINTS</span></div><div className="panel-body table-wrap" tabIndex={0} role="region" aria-label="Model build history"><table><thead><tr><th scope="col">Queued</th><th scope="col">Build</th><th scope="col">Status</th><th scope="col">Input fingerprint</th><th scope="col">Export</th></tr></thead><tbody>{inventory.builds.map((item) => <tr key={item.id}><td>{formatDate(item.queued_at)}</td><td className="mono">{item.id}</td><td><span className={`status ${modelStatusTone(item.status)}`}>{item.status}</span></td><td className="mono">{item.input_fingerprint}</td><td>{item.export.status.replaceAll("_", " ")}</td></tr>)}</tbody></table></div></section> : null}
  </div>;
}

export default function ModelBuilder({
  caseId,
  role,
  onDraftStateChange,
}: {
  caseId: string;
  role: string;
  onDraftStateChange?: (dirty: boolean) => void;
}) {
  const [view, setView] = useState<BuilderView>("MODEL");
  const [modelSurface, setModelSurface] = useState<"ANALYST" | "APPLICATION">("ANALYST");
  const [inventory, setInventory] = useState<ModelInventory | null>(null);
  const [registry, setRegistry] = useState<AssumptionRegistry | null>(null);
  const [revisions, setRevisions] = useState<ModelRevision[]>([]);
  const [baseline, setBaseline] = useState<ModelAssumptionValue[]>([]);
  const [draft, setDraft] = useState<ModelAssumptionValue[]>([]);
  const [draftGeneration, setDraftGeneration] = useState(0);
  const [draftAuthority, setDraftAuthority] = useState<DraftAuthority | null>(null);
  const [preview, setPreview] = useState<ModelPreview | null>(null);
  const [rebase, setRebase] = useState<RebasePreview | null>(null);
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResult | null>(null);
  const [selectedDefinitionId, setSelectedDefinitionId] = useState("");
  const [selectedCase, setSelectedCase] = useState<ModelCase>("BASE");
  const [periodScope, setPeriodScope] = useState("ALL");
  const [outputId, setOutputId] = useState("total_leverage");
  const [rangeMinimum, setRangeMinimum] = useState("");
  const [rangeMaximum, setRangeMaximum] = useState("");
  const [rangeStep, setRangeStep] = useState("");
  const [signOffNote, setSignOffNote] = useState("");
  const [conflict, setConflict] = useState<ConflictMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [pending, setPending] = useState("");
  const [message, setMessage] = useState("");
  const [loadedCaseId, setLoadedCaseId] = useState("");
  const requestGeneration = useRef(0);
  const actionGeneration = useRef(0);
  const draftGenerationRef = useRef(0);
  const authorityKey = useRef("");
  const draftCaseIdRef = useRef("");
  const baselineRef = useRef<ModelAssumptionValue[]>([]);
  const draftRef = useRef<ModelAssumptionValue[]>([]);
  const dirtyRef = useRef(false);
  const draftAuthorityRef = useRef<DraftAuthority | null>(null);
  const canWrite = role !== "READER";

  const refresh = useCallback(async (signal?: AbortSignal, showLoading = true) => {
    if (!caseId) return;
    const expectedCaseId = caseId;
    const generation = ++requestGeneration.current;
    if (showLoading) setLoading(true);
    setLoadError("");
    try {
      const nextInventory = await request<ModelInventory>(`/api/cases/${expectedCaseId}/models`, {}, signal);
      if (generation !== requestGeneration.current) return;
      const nextBuild = nextInventory.readiness.build || nextInventory.builds[0] || null;
      let nextRegistry: AssumptionRegistry | null = null;
      let nextRevisions: ModelRevision[] = [];
      if (nextBuild?.status === "READY") {
        const [registryResponse, revisionResponse] = await Promise.all([
          request<AssumptionRegistry>(assumptionRegistryPath(expectedCaseId, nextBuild.id), {}, signal),
          request<{ revisions: ModelRevision[] }>(`/api/cases/${expectedCaseId}/model-revisions`, {}, signal),
        ]);
        if (registryResponse.build_id !== nextBuild.id || registryResponse.input_fingerprint !== nextBuild.input_fingerprint) {
          throw new Error("Assumption registry identity does not match the current Application Model Build.");
        }
        nextRegistry = registryResponse;
        nextRevisions = revisionResponse.revisions;
      }
      if (generation !== requestGeneration.current || expectedCaseId !== caseId) return;
      const nextActive = nextRevisions.find((item) => item.state === "ACTIVE" && item.build_id === nextBuild?.id) || null;
      const nextAuthorityKey = nextBuild && nextRegistry
        ? [expectedCaseId, nextBuild.id, nextBuild.input_fingerprint, nextBuild.payload_digest || "", nextRegistry.digest, nextActive?.id || ""].join("|")
        : `${expectedCaseId}|${nextInventory.readiness.status}`;
      if (nextAuthorityKey !== authorityKey.current) {
        actionGeneration.current += 1;
        const preserveDirtyDraft = draftCaseIdRef.current === expectedCaseId && dirtyRef.current;
        authorityKey.current = nextAuthorityKey;
        if (preserveDirtyDraft) {
          setConflict((current) => current || { current: nextActive, current_build: nextBuild });
          setMessage("Authority changed. Your local Draft Revision and last preview are preserved; review and rebase before previewing again.");
          setPending("");
        } else {
          draftGenerationRef.current = 0;
          const nextBaseline = nextRegistry ? normalizeAssumptions(nextActive?.effective_assumptions || nextRegistry.defaults) : [];
          const nextDraftAuthority = nextBuild && nextRegistry
            ? { buildId: nextBuild.id, registryDigest: nextRegistry.digest, parentRevisionId: nextActive?.id || null }
            : null;
          draftCaseIdRef.current = expectedCaseId;
          baselineRef.current = nextBaseline;
          draftRef.current = nextBaseline;
          dirtyRef.current = false;
          draftAuthorityRef.current = nextDraftAuthority;
          setBaseline(nextBaseline);
          setDraft(nextBaseline);
          setDraftGeneration(0);
          setDraftAuthority(nextDraftAuthority);
          setPreview(null);
          setRebase(null);
          setScenario(null);
          setSensitivity(null);
          setConflict(null);
          setSignOffNote("");
          setMessage("");
          setPending("");
          setView("MODEL");
          setModelSurface(nextActive ? "ANALYST" : "APPLICATION");
          setSelectedDefinitionId((current) => {
            if (nextRegistry?.definitions.some((item) => item.assumption_id === current
              && assumptionScope(nextBaseline, current, "BASE", "ALL").editable)) return current;
            return nextRegistry?.definitions.find((item) => assumptionScope(nextBaseline, item.assumption_id, "BASE", "ALL").editable)?.assumption_id
              || nextRegistry?.definitions[0]?.assumption_id
              || "";
          });
        }
      }
      setInventory(nextInventory);
      setRegistry(nextRegistry);
      setRevisions(nextRevisions);
      setLoadedCaseId(expectedCaseId);
    } catch (caught) {
      if (generation !== requestGeneration.current || caught instanceof DOMException && caught.name === "AbortError") return;
      setLoadError(firstErrorMessage(caught, "Unable to load Model Builder"));
      setLoadedCaseId(expectedCaseId);
    } finally {
      if (generation === requestGeneration.current) setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    requestGeneration.current += 1;
    actionGeneration.current += 1;
    authorityKey.current = "";
    const controller = new AbortController();
    queueMicrotask(() => { if (!controller.signal.aborted) void refresh(controller.signal); });
    return () => { controller.abort(); requestGeneration.current += 1; };
  }, [refresh]);

  const status = inventory?.readiness.status;
  const build = inventory?.readiness.build || inventory?.builds[0] || null;
  const activeRevision = revisions.find((item) => item.state === "ACTIVE" && item.build_id === build?.id) || null;
  const currentHeadRevisionId = activeRevision?.id || null;
  const dirtyCount = assumptionChangeCount(baseline, draft);
  const dirty = dirtyCount > 0;
  const authorityMismatch = Boolean(build && registry && draftAuthority
    && (draftAuthority.buildId !== build.id
      || draftAuthority.registryDigest !== registry.digest
      || draftAuthority.parentRevisionId !== currentHeadRevisionId));
  const previewCurrent = Boolean(build && registry && previewMatchesDraft(preview, {
    buildId: build.id,
    buildInputFingerprint: build.input_fingerprint,
    buildPayloadDigest: build.payload_digest || "",
    registryVersion: registry.version,
    registryDigest: registry.digest,
    parentRevisionId: draftAuthority?.parentRevisionId || null,
    expectedHeadRevisionId: draftAuthority?.parentRevisionId || null,
    currentHeadRevisionId,
    draftGeneration,
  }));
  const primaryAction = authorityMismatch ? null : primaryModelAction({ status, canWrite, dirty, previewCurrent });
  const selectedDefinition = registry?.definitions.find((item) => item.assumption_id === selectedDefinitionId) || registry?.definitions[0] || null;
  const sensitivityOutputIds = [...new Set(registry?.definitions.flatMap((item) => item.affected_outputs) || [])].sort();
  const sensitivityOutputId = sensitivityOutputIds.includes(outputId) ? outputId : sensitivityOutputIds[0] || "";
  const assumptionPeriods = selectedDefinition
    ? [...new Set(draft.filter((row) => row.assumption_id === selectedDefinition.assumption_id && row.case === selectedCase).map((row) => row.period_id))].sort()
    : [];
  const broadcastScope = selectedDefinition
    ? assumptionScope(draft, selectedDefinition.assumption_id, selectedCase, "ALL")
    : { rows: [], editable: false, mixed: false, value: "" };
  const sensitivityScope = selectedDefinition
    ? assumptionScope(draft, selectedDefinition.assumption_id, selectedCase, periodScope)
    : { rows: [], editable: false, mixed: false, value: "" };
  const sensitivityRows = sensitivity ? sensitivityPeriodRows(sensitivity) : [];
  const conflictSourceRevision = draftAuthority?.parentRevisionId
    ? revisions.find((item) => item.id === draftAuthority.parentRevisionId) || null
    : null;
  const conflictRebaseRevision = conflictSourceRevision || activeRevision;

  useEffect(() => {
    dirtyRef.current = dirty;
    baselineRef.current = baseline;
    draftRef.current = draft;
    draftAuthorityRef.current = draftAuthority;
  }, [baseline, draft, draftAuthority, dirty]);
  useEffect(() => { onDraftStateChange?.(dirty); }, [dirty, onDraftStateChange]);
  useEffect(() => () => onDraftStateChange?.(false), [onDraftStateChange]);
  useEffect(() => {
    const exportPending = revisions.some((item) => item.export.status === "QUEUED" || item.export.status === "EXPORTING");
    if (status !== "QUEUED" && status !== "BUILDING" && !exportPending) return;
    const timer = window.setTimeout(() => { void refresh(undefined, false); }, 1500);
    return () => window.clearTimeout(timer);
  }, [refresh, revisions, status]);

  const invalidatePreview = (next: ModelAssumptionValue[]) => {
    actionGeneration.current += 1;
    draftGenerationRef.current += 1;
    draftRef.current = next;
    dirtyRef.current = assumptionChangeCount(baselineRef.current, next) > 0;
    setDraft(next);
    setDraftGeneration(draftGenerationRef.current);
    setScenario(null);
    setSensitivity(null);
    setMessage("");
  };
  const editAssumption = (definition: AssumptionDefinition, caseName: ModelCase, scope: string, rawValue: string) => {
    if (rawValue.trim() === "") return false;
    try {
      invalidatePreview(applyAssumptionValue(draftRef.current, definition, caseName, scope, Number(rawValue)));
      return true;
    } catch (caught) {
      setMessage(`${firstErrorMessage(caught, "Unable to update assumption")}. Enter a finite value from ${definition.hard_min} to ${definition.hard_max} for a READY assumption.`);
      return false;
    }
  };
  const selectAssumptionCase = (nextCase: ModelCase) => {
    setSelectedCase(nextCase);
    if (!selectedDefinition || !assumptionScope(draft, selectedDefinition.assumption_id, nextCase, "ALL").editable) {
      const nextDefinition = registry?.definitions.find((item) => assumptionScope(draft, item.assumption_id, nextCase, "ALL").editable);
      if (nextDefinition) setSelectedDefinitionId(nextDefinition.assumption_id);
    }
    setPeriodScope("ALL");
    setSensitivity(null);
  };
  const selectBuilderView = (nextView: BuilderView, moveFocus = false) => {
    setView(nextView);
    if (moveFocus) queueMicrotask(() => document.getElementById(`model-builder-tab-${nextView.toLowerCase()}`)?.focus());
  };
  const onBuilderTabKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? builderViews.length - 1
        : (index + (event.key === "ArrowRight" ? 1 : -1) + builderViews.length) % builderViews.length;
    selectBuilderView(builderViews[nextIndex].id, true);
  };
  const buildModel = async () => {
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    setPending("build"); setMessage("");
    try { await request(`/api/cases/${caseId}/models`, { method: "POST" }); if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current) return; setMessage(status === "FAILED" ? "Model rebuild queued." : "Build queued"); await refresh(undefined, false); }
    catch (caught) { if (action === actionGeneration.current && expectedAuthority === authorityKey.current) setMessage(firstErrorMessage(caught, "Unable to queue model build")); }
    finally { if (action === actionGeneration.current) setPending(""); }
  };
  const previewDraft = async () => {
    if (!build || !registry || !draftAuthority || !dirty || authorityMismatch) return;
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    const expectedGeneration = draftGeneration;
    setPending("preview"); setMessage("");
    try {
      const next = await modelRequest<ModelPreview>(`/api/cases/${caseId}/models/previews`, { method: "POST", body: JSON.stringify({ build_id: build.id, parent_revision_id: draftAuthority.parentRevisionId, registry_version: registry.version, registry_digest: registry.digest, assumptions: draft, draft_generation: expectedGeneration }) });
      if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current || expectedGeneration !== draftGenerationRef.current || next.draft_generation !== expectedGeneration || next.build_id !== build.id || next.registry_digest !== registry.digest || next.parent_revision_id !== draftAuthority.parentRevisionId) return;
      setPreview(next); setMessage("Exact preview calculated. Review deltas, then add one Sign-Off Note.");
    } catch (caught) { if (action === actionGeneration.current && expectedAuthority === authorityKey.current) setMessage(firstErrorMessage(caught, "Unable to calculate preview")); }
    finally { if (action === actionGeneration.current) setPending(""); }
  };
  const signOff = async () => {
    if (!canWrite || !build || !registry || !draftAuthority || !previewCurrent || !preview || !signOffNote.trim()) return;
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    setPending("sign-off"); setMessage(""); setConflict(null);
    try {
      await modelRequest<ModelRevision>(`/api/cases/${caseId}/model-revisions/sign-off`, { method: "POST", body: JSON.stringify({ build_id: build.id, parent_revision_id: draftAuthority.parentRevisionId, registry_version: registry.version, registry_digest: registry.digest, assumptions: draft, draft_generation: draftGeneration, preview_digest: preview.preview_digest, expected_head_revision_id: draftAuthority.parentRevisionId, note: signOffNote.trim() }) });
      if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current || draftGeneration !== draftGenerationRef.current) return;
      dirtyRef.current = false;
      setMessage("Analyst Model Revision signed. Exact XLSX export queued.");
      await refresh(undefined, false);
    } catch (caught) {
      if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current) return;
      if (caught instanceof ModelRequestError && caught.status === 409 && caught.detail && typeof caught.detail === "object") {
        setConflict(caught.detail as ConflictMetadata);
        setMessage("Sign-off conflict. The model authority changed; review current metadata or rebase.");
        await refresh(undefined, false);
      } else setMessage(firstErrorMessage(caught, "Unable to sign off revision"));
    } finally { if (action === actionGeneration.current) setPending(""); }
  };
  const requestRebase = async (revision: ModelRevision) => {
    if (!build) return;
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    setPending(`rebase:${revision.id}`); setMessage("");
    try {
      const next = await modelRequest<RebasePreview>(`/api/cases/${caseId}/model-revisions/rebase-preview`, { method: "POST", body: JSON.stringify({ revision_id: revision.id, build_id: build.id, draft_generation: draftGeneration + 1 }) });
      if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current || next.build_id !== build.id) return;
      setRebase(next); setView("HISTORY"); setMessage("Rebase Candidate calculated. Nothing has been stored.");
    } catch (caught) { if (action === actionGeneration.current && expectedAuthority === authorityKey.current) setMessage(firstErrorMessage(caught, "Unable to calculate Rebase Candidate")); }
    finally { if (action === actionGeneration.current) setPending(""); }
  };
  const applyRebase = () => {
    if (!rebase || rebase.build_id !== build?.id || !registry || rebase.invalidated.length) return;
    try {
      const nextBaseline = normalizeAssumptions(activeRevision?.effective_assumptions || rebase.candidate_assumptions);
      const nextDraft = mergeRebasedAssumptions(baselineRef.current, draftRef.current, nextBaseline);
      baselineRef.current = nextBaseline;
      draftAuthorityRef.current = { buildId: build.id, registryDigest: registry.digest, parentRevisionId: activeRevision?.id || null };
      setBaseline(nextBaseline);
      setDraftAuthority(draftAuthorityRef.current);
      setConflict(null);
      invalidatePreview(nextDraft);
      setRebase(null);
      selectBuilderView("ASSUMPTIONS");
      setMessage("Rebase Candidate merged with your local shocks in this browser-memory Draft Revision. Run a fresh preview before Sign-Off.");
    }
    catch (caught) { setMessage(firstErrorMessage(caught, "Rebase Candidate no longer matches the registry")); }
  };
  const runOneWay = async () => {
    if (!build || !registry || !selectedDefinition || !sensitivityScope.editable) return;
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    setPending("one-way"); setMessage("");
    const optionalNumber = (value: string) => value.trim() === "" ? undefined : Number(value);
    try {
      const next = await modelRequest<SensitivityResult>(`/api/cases/${caseId}/models/sensitivities/one-way`, { method: "POST", body: JSON.stringify({ build_id: build.id, base_revision_id: activeRevision?.id || null, registry_version: registry.version, registry_digest: registry.digest, assumption_id: selectedDefinition.assumption_id, case: selectedCase, period_scope: periodScope, minimum: optionalNumber(rangeMinimum), maximum: optionalNumber(rangeMaximum), step: optionalNumber(rangeStep), output_id: sensitivityOutputId, draft_generation: draftGeneration }) });
      if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current || next.draft_generation !== draftGenerationRef.current || next.build_id !== build.id) return;
      setSensitivity(next); setMessage("One-way sensitivity calculated by CP-MODEL. Nothing has been stored.");
    } catch (caught) { if (action === actionGeneration.current && expectedAuthority === authorityKey.current) setMessage(firstErrorMessage(caught, "Unable to calculate one-way sensitivity")); }
    finally { if (action === actionGeneration.current) setPending(""); }
  };
  const runScenario = async () => {
    if (!build || !registry) return;
    const baselineByKey = new Map(baseline.map((row) => [assumptionKey(row), row]));
    const shocks = draft.filter((row) => row.status === "READY" && row.value !== null && baselineByKey.get(assumptionKey(row))?.value !== row.value).map((row) => ({ assumption_id: row.assumption_id, case: row.case, period_id: row.period_id, value: row.value }));
    if (!shocks.length) { setMessage("Change at least one assumption before running a Multi-Driver Scenario."); return; }
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    setPending("scenario"); setMessage("");
    try {
      const next = await modelRequest<ScenarioResult>(`/api/cases/${caseId}/models/scenarios`, { method: "POST", body: JSON.stringify({ build_id: build.id, base_revision_id: activeRevision?.id || null, registry_version: registry.version, registry_digest: registry.digest, shocks, draft_generation: draftGeneration }) });
      if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current || next.draft_generation !== draftGenerationRef.current) return;
      setScenario(next); setMessage("Multi-Driver Scenario calculated by CP-MODEL. Nothing has been stored.");
    } catch (caught) { if (action === actionGeneration.current && expectedAuthority === authorityKey.current) setMessage(firstErrorMessage(caught, "Unable to calculate scenario")); }
    finally { if (action === actionGeneration.current) setPending(""); }
  };
  const applyScenario = () => {
    if (!scenario) return;
    try { invalidatePreview(applyServerAssumptions(draft, scenario.scenario.effective_assumptions)); setScenario(null); selectBuilderView("ASSUMPTIONS"); setMessage("Scenario assumptions applied to this browser-memory Draft Revision only."); }
    catch (caught) { setMessage(firstErrorMessage(caught, "Scenario no longer matches the registry")); }
  };
  const queueRevisionExport = async (revision: ModelRevision) => {
    const action = ++actionGeneration.current;
    const expectedAuthority = authorityKey.current;
    setPending(`export:${revision.id}`); setMessage("");
    try { await request(`/api/cases/${caseId}/model-revisions/${revision.id}/export`, { method: "POST" }); if (action !== actionGeneration.current || expectedAuthority !== authorityKey.current) return; setMessage("Exact revision XLSX export queued."); await refresh(undefined, false); }
    catch (caught) { if (action === actionGeneration.current && expectedAuthority === authorityKey.current) setMessage(firstErrorMessage(caught, "Unable to queue revision export")); }
    finally { if (action === actionGeneration.current) setPending(""); }
  };

  if (loadError && loadedCaseId === caseId) return <div className="grid"><section className="panel span-12"><div className="panel-header"><h2>Model Builder</h2><span className="status critical">Unavailable</span></div><div className="panel-body"><LoadState loading={false} error={loadError} /></div></section></div>;
  if (!caseId || loadedCaseId !== caseId || loading && !inventory) return <div className="grid"><section className="panel span-12"><div className="panel-header"><h2>Model Builder</h2></div><div className="panel-body"><LoadState loading error={loadError} /></div></section></div>;

  const modelOutputs = activeRevision?.outputs || {};
  const renderPrimaryAction = () => {
    if (!primaryAction) return null;
    if (primaryAction === "BUILD") return <button data-primary-model-action="BUILD" className="button primary" type="button" disabled={pending === "build"} onClick={() => void buildModel()}>{pending === "build" ? "Queuing…" : status === "FAILED" ? "Retry build" : "Build model"}</button>;
    if (primaryAction === "PREVIEW") return <button data-primary-model-action="PREVIEW" className="button primary" type="button" disabled={pending === "preview"} onClick={() => void previewDraft()}>{pending === "preview" ? "Calculating…" : "Preview Draft Revision"}</button>;
    return <button data-primary-model-action="SIGN_OFF" className="button primary" type="button" disabled={pending === "sign-off" || !signOffNote.trim()} onClick={() => void signOff()}>{pending === "sign-off" ? "Signing…" : "Sign Off Revision"}</button>;
  };

  return <div className="grid model-builder analyst-model-builder">
    <section className="panel span-12 model-builder-command">
      <div className="panel-header"><div><p className="eyebrow">SIGNED ANALYST AUTHORITY</p><h2>Model Builder</h2></div><span className={`status ${modelStatusTone(status)}`} role="status" aria-live="polite">{status?.replaceAll("_", " ")}</span></div>
      <div className="panel-body model-builder-command-body"><div><strong>{activeRevision ? `Active Analyst Model · R${activeRevision.revision_number}` : "No Active Analyst Model"}</strong><p className="muted">{activeRevision ? `${activeRevision.signed_by} · ${formatDate(activeRevision.signed_at)} · ${activeRevision.note}` : "Application Model Build is available for comparison. Sign-off stores only the exact revision you approve."}</p></div><div className="model-primary-action">{renderPrimaryAction()}<button className="button small" type="button" disabled={loading} onClick={() => void refresh()}>{loading ? "Refreshing…" : "Refresh authority"}</button></div></div>
      {status === "QUEUED" || status === "BUILDING" ? <div className="callout"><strong>{status === "QUEUED" ? "Build queued" : "Calculating worksheet"}</strong><br />CP-MODEL is validating canonical inputs and calculating the Application Model Build.</div> : null}
      {status === "FAILED" ? <div className="callout warning" role="alert"><strong>{build?.error?.code || "MODEL_CALCULATION_FAILED"}</strong><br />{build?.error?.detail || "The model calculation did not complete."}</div> : null}
      {inventory?.readiness.blockers.map((blocker) => <div className="callout warning model-blocker" key={blocker.code}><strong>{blocker.code.replaceAll("_", " ")}</strong><br />{blocker.detail}</div>)}
      {message ? <p className={message.includes("Unable") || message.includes("conflict") || message.includes("changed") || message.includes("no longer") ? "error" : "muted"} role="status" aria-live="polite">{message}</p> : null}
      {conflict || authorityMismatch ? <div className="callout warning" role="alert"><strong>Authority conflict</strong><p>Your local Draft Revision is preserved. Current head <span className="mono">{conflict?.current?.id || currentHeadRevisionId || "none"}</span>; current build <span className="mono">{conflict?.current_build?.id || build?.id || "unavailable"}</span>; draft parent <span className="mono">{draftAuthority?.parentRevisionId || "application defaults"}</span>.</p><div className="row-actions"><button className="button small" type="button" onClick={() => void refresh()}>Review current authority</button>{conflictRebaseRevision && build?.status === "READY" ? <button className="button small" type="button" disabled={pending === `rebase:${conflictRebaseRevision.id}`} onClick={() => void requestRebase(conflictRebaseRevision)}>Review and rebase local Draft</button> : null}</div></div> : null}
    </section>

    <section className="panel span-12 model-builder-workspace">
      <div className="model-builder-view-tabs" role="tablist" aria-label="Model Builder views">
        {builderViews.map((item, index) => <button id={`model-builder-tab-${item.id.toLowerCase()}`} key={item.id} type="button" role="tab" aria-selected={view === item.id} aria-controls={`model-builder-panel-${item.id.toLowerCase()}`} tabIndex={view === item.id ? 0 : -1} className="model-builder-view-tab" onClick={() => selectBuilderView(item.id)} onKeyDown={(event) => onBuilderTabKeyDown(event, index)}>{item.label}</button>)}
      </div>

      {view === "MODEL" ? <div id="model-builder-panel-model" className="model-builder-view" role="tabpanel" aria-labelledby="model-builder-tab-model"><div className="model-surface-switch" aria-label="Model authority surface"><button type="button" className={modelSurface === "ANALYST" ? "button small is-active" : "button small"} aria-pressed={modelSurface === "ANALYST"} onClick={() => setModelSurface("ANALYST")}>Active Analyst Model</button><button type="button" className={modelSurface === "APPLICATION" ? "button small is-active" : "button small"} aria-pressed={modelSurface === "APPLICATION"} onClick={() => setModelSurface("APPLICATION")}>Application Model Build</button></div>{modelSurface === "APPLICATION" ? status === "READY" ? <ApplicationModelBuild caseId={caseId} role={role} /> : <div className="empty">The Application Model Build worksheet will appear when CP-MODEL reaches READY.</div> : <div className="model-authority-output"><div className="model-authority-strip"><dl className="state-facts"><dt>Revision</dt><dd className="mono">{activeRevision?.id || "Unsigned draft"}</dd><dt>Build fingerprint</dt><dd className="mono">{build?.input_fingerprint || "Unavailable"}</dd><dt>Registry</dt><dd className="mono">{registry ? `${registry.version} · ${registry.digest.slice(0, 12)}` : "Unavailable"}</dd><dt>Draft changes</dt><dd className="num">{dirtyCount}</dd></dl></div><OutputTable label="Active Analyst Model outputs" outputs={modelOutputs} />{preview ? <div className={previewCurrent ? "callout" : "callout warning"}><strong>{previewCurrent ? "Last successful preview · current" : "Preview stale · last successful preview"}</strong><p className="mono">Build {preview.build_id} · Registry {preview.registry_digest.slice(0, 12)} · Draft generation {preview.draft_generation}</p><OutputTable label="Last successful preview outputs" outputs={preview.outputs} /><OutputTable label="Last successful preview deltas" outputs={preview.deltas} /></div> : null}</div>}</div> : null}

      {view === "ASSUMPTIONS" ? <div id="model-builder-panel-assumptions" className="model-builder-view model-assumptions" role="tabpanel" aria-labelledby="model-builder-tab-assumptions"><div className="model-assumption-toolbar"><label>Case<select value={selectedCase} onChange={(event) => selectAssumptionCase(event.target.value as ModelCase)}><option value="BASE">Base</option><option value="DOWNSIDE">Downside</option></select></label><label>Assumption<select value={selectedDefinition?.assumption_id || ""} onChange={(event) => { setSelectedDefinitionId(event.target.value); setPeriodScope("ALL"); setSensitivity(null); }}>{registry?.definitions.map((item) => { const available = assumptionScope(draft, item.assumption_id, selectedCase, "ALL").editable; return <option value={item.assumption_id} key={item.assumption_id}>{item.family} · {item.label}{available ? "" : " · unavailable for all-year scope"}</option>; })}</select></label><span className="status warning">{dirtyCount} LOCAL UNSIGNED CHANGES</span></div>{selectedDefinition ? <><div className="model-assumption-definition"><div><p className="eyebrow">{selectedDefinition.family}</p><h3>{selectedDefinition.label}</h3><p>{selectedDefinition.description}</p></div><dl className="state-facts"><dt>Unit</dt><dd>{selectedDefinition.unit}</dd><dt>Hard bounds</dt><dd className="mono">{selectedDefinition.hard_min} — {selectedDefinition.hard_max}</dd><dt>Affected outputs</dt><dd>{selectedDefinition.affected_outputs.join(", ")}</dd></dl></div><div className="model-broadcast"><span>All-year broadcast · {selectedCase === "BASE" ? "Base" : "Downside"}</span><ControlledAssumptionInput key={`${selectedDefinition.assumption_id}:${selectedCase}:ALL:${draftGeneration}`} value={broadcastScope.value} mixed={broadcastScope.mixed} label={`All-year broadcast ${selectedDefinition.label} ${selectedCase}`} describedBy="assumption-broadcast-status" disabled={!broadcastScope.editable} onCommit={(value) => editAssumption(selectedDefinition, selectedCase, "ALL", value)} /><span id="assumption-broadcast-status" className="mono muted" aria-live="polite">{broadcastScope.editable ? `${selectedDefinition.unit} · ${broadcastScope.mixed ? "Mixed across" : "applies to"} exactly ${assumptionPeriods.length} registry years · bounds ${selectedDefinition.hard_min} to ${selectedDefinition.hard_max}` : `Broadcast unavailable: every included period must be READY. ${broadcastScope.rows.map((row) => row.gap_code || row.status).join(" · ")}`}</span></div><div className="table-wrap" tabIndex={0} role="region" aria-label={`${selectedDefinition.label} ${selectedCase} assumptions`}><table><thead><tr><th scope="col">Period</th><th scope="col">Effective value</th><th scope="col">Application default</th><th scope="col">Effective minus Application build</th><th scope="col">Status / named gap</th><th scope="col">Default provenance</th></tr></thead><tbody>{draft.filter((row) => row.assumption_id === selectedDefinition.assumption_id && row.case === selectedCase).map((row) => { const delta = applicationBuildDelta(row); return <tr key={assumptionKey(row)}><th scope="row">{row.period_id}</th><td><ControlledAssumptionInput key={`${assumptionKey(row)}:${draftGeneration}`} value={row.value === null ? "" : String(row.value)} label={`${selectedDefinition.label} ${row.case} ${row.period_id}`} describedBy={`assumption-status-${row.case}-${row.period_id}`} disabled={row.status !== "READY"} onCommit={(value) => editAssumption(selectedDefinition, selectedCase, row.period_id, value)} /></td><td className="num">{formatModelValue(row.default_value)}</td><td className="num">{delta === null ? "Unavailable" : formatModelValue(delta)}</td><td id={`assumption-status-${row.case}-${row.period_id}`}><span className={`status ${row.status === "READY" ? "success" : "warning"}`}>{row.status.replaceAll("_", " ")}</span>{row.gap_code ? <span className="mono"> · {row.gap_code}</span> : null}</td><td className="mono">{row.source_context?.provenance.map((item) => `${item.source_id}:${item.source_locator}`).join(" · ") || row.default_gap_code || "Methodology default"}</td></tr>; })}</tbody></table></div></> : <div className="empty">No methodology-owned assumption registry is available.</div>}{previewCurrent && canWrite ? <div className="model-signoff-note"><label htmlFor="model-signoff-note">Sign-Off Note <span aria-hidden="true">*</span></label><textarea id="model-signoff-note" required maxLength={2000} value={signOffNote} onChange={(event) => setSignOffNote(event.target.value)} placeholder="What changed, why, and the evidence behind the approved assumptions." /><p className="muted">One note is stored with the signed revision. The unsigned draft remains only in this browser component.</p></div> : null}{!canWrite ? <p className="callout">Reader mode: local shocks, previews, scenarios, sensitivities, and Apply to Draft are temporary. Sign-Off and shared writes remain unavailable.</p> : null}</div> : null}

      {view === "SENSITIVITIES" ? <div id="model-builder-panel-sensitivities" className="model-builder-view model-sensitivities" role="tabpanel" aria-labelledby="model-builder-tab-sensitivities"><section aria-labelledby="one-way-heading"><div className="panel-header"><h3 id="one-way-heading">One-way sensitivity</h3><span className="panel-meta">SERVER CALCULATED · TRANSIENT</span></div><div className="sensitivity-controls"><label>Assumption<select value={selectedDefinition?.assumption_id || ""} onChange={(event) => { setSelectedDefinitionId(event.target.value); setPeriodScope("ALL"); setSensitivity(null); }}>{registry?.definitions.map((item) => <option value={item.assumption_id} key={item.assumption_id}>{item.label}</option>)}</select></label><label>Case<select value={selectedCase} onChange={(event) => selectAssumptionCase(event.target.value as ModelCase)}><option value="BASE">Base</option><option value="DOWNSIDE">Downside</option></select></label><label>Period<select value={periodScope} onChange={(event) => { setPeriodScope(event.target.value); setSensitivity(null); }}><option value="ALL" disabled={!broadcastScope.editable}>All years</option>{assumptionPeriods.map((period) => <option key={period} value={period} disabled={!assumptionScope(draft, selectedDefinition?.assumption_id || "", selectedCase, period).editable}>{period}</option>)}</select></label><label>Minimum<input type="number" inputMode="decimal" value={rangeMinimum} onChange={(event) => setRangeMinimum(event.target.value)} placeholder={selectedDefinition?.hard_min} /></label><label>Maximum<input type="number" inputMode="decimal" value={rangeMaximum} onChange={(event) => setRangeMaximum(event.target.value)} placeholder={selectedDefinition?.hard_max} /></label><label>Step<input type="number" inputMode="decimal" value={rangeStep} onChange={(event) => setRangeStep(event.target.value)} placeholder={selectedDefinition?.sensitivity_default.step} /></label><label>Output<select value={sensitivityOutputId} onChange={(event) => setOutputId(event.target.value)}>{sensitivityOutputIds.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label><button className="button" type="button" disabled={!build || !sensitivityScope.editable || !sensitivityOutputId || pending === "one-way"} onClick={() => void runOneWay()}>{pending === "one-way" ? "Calculating…" : "Run one-way"}</button></div>{!sensitivityScope.editable ? <p className="callout warning" role="status">This assumption scope is unavailable. Select READY periods before running sensitivity.</p> : null}{sensitivity ? <div className="sensitivity-results"><div className="table-wrap" tabIndex={0} role="region" aria-label="One-way table"><table><thead><tr><th scope="col">Input</th><th scope="col">Period</th><th scope="col">Server output</th><th scope="col">Server delta</th></tr></thead><tbody>{sensitivityRows.map((row) => <tr key={`${row.input}:${row.periodId}`}><td className="num">{formatModelValue(row.input)}</td><th scope="row">{row.periodId}</th><td className="num">{formatModelValue(row.output)}</td><td className="num">{formatModelValue(row.delta)}</td></tr>)}</tbody></table></div><div className="model-tornado" role="img" aria-label={`One-way tornado for ${sensitivity.case}; server values listed in sorted point and period order`}><h4>One-way tornado</h4>{sensitivityRows.map((row) => <div className="tornado-row" key={`${row.input}:${row.periodId}`}><span className="mono">{formatModelValue(row.input)} · {row.periodId}</span><span>{formatModelValue(row.output)} · Δ {formatModelValue(row.delta)}</span></div>)}</div><div className="callout"><strong>Breakpoint</strong>{sensitivity.breakpoint ? <OutputTable label="First sensitivity breakpoint" outputs={sensitivity.breakpoint} /> : <p>No breakpoint in the tested server range.</p>}</div></div> : null}</section><section aria-labelledby="scenario-heading"><div className="panel-header"><h3 id="scenario-heading">Multi-Driver Scenario</h3><span className="panel-meta">{dirtyCount} LOCAL SHOCKS</span></div><p>Runs every changed local value through the same server calculation path. It creates no revision, audit, or saved scenario.</p><div className="row-actions"><button className="button" type="button" disabled={!dirty || pending === "scenario"} onClick={() => void runScenario()}>{pending === "scenario" ? "Calculating…" : "Run Multi-Driver Scenario"}</button>{scenario ? <button className="button" type="button" onClick={applyScenario}>Apply to Draft</button> : null}</div>{scenario ? <><OutputTable label="Multi-Driver Scenario outputs" outputs={scenario.scenario.outputs} /><OutputTable label="Multi-Driver Scenario deltas" outputs={scenario.scenario.deltas} /></> : null}</section></div> : null}

      {view === "HISTORY" ? <div id="model-builder-panel-history" className="model-builder-view model-history" role="tabpanel" aria-labelledby="model-builder-tab-history">{rebase ? <div className="rebase-candidate"><div className="panel-header"><h3>Rebase Candidate</h3><span className="panel-meta">TRANSIENT · NOT STORED</span></div><div className="rebase-columns"><div><h4>Compatible</h4><p className="num">{rebase.compatible.length}</p></div><div><h4>Changed</h4><p className="num">{rebase.changed.length}</p></div><div><h4>Invalidated</h4><p className="num">{rebase.invalidated.length}</p></div></div>{rebase.invalidated.length ? <div className="callout warning" role="alert">Invalidated assumptions require analyst review before a candidate can be applied.</div> : null}<button className="button" type="button" disabled={Boolean(rebase.invalidated.length)} onClick={applyRebase}>Apply Rebase Candidate to Draft</button></div> : null}<div className="table-wrap" tabIndex={0} role="region" aria-label="Signed Analyst Model Revision history"><table><thead><tr><th scope="col">Revision</th><th scope="col">State</th><th scope="col">Signed</th><th scope="col">Sign-Off Note</th><th scope="col">Build</th><th scope="col">XLSX</th></tr></thead><tbody>{revisions.length ? revisions.map((revision) => <tr key={revision.id}><td className="mono">R{revision.revision_number}<br />{revision.id}</td><td><span className={`status ${revision.state === "ACTIVE" ? "success" : revision.state === "STALE" ? "warning" : "idle"}`}>{revision.state}</span></td><td>{revision.signed_by}<br /><span className="muted">{formatDate(revision.signed_at)}</span></td><td>{revision.note}</td><td className="mono">{revision.build_id}</td><td><div className="row-actions">{revision.export.status === "READY" ? <a className="button small" href={`${apiBase}/api/cases/${caseId}/model-revisions/${revision.id}/download`} download>Download exact XLSX</a> : null}{canWrite && (revision.export.status === "FAILED" || revision.export.status === "NOT_REQUESTED") ? <button className="button small" type="button" disabled={pending === `export:${revision.id}`} onClick={() => void queueRevisionExport(revision)}>{revision.export.status === "FAILED" ? "Retry exact export" : "Queue exact export"}</button> : null}{revision.export.status === "QUEUED" || revision.export.status === "EXPORTING" ? <span className="status warning">{revision.export.status}</span> : null}{revision.state !== "ACTIVE" && build?.status === "READY" ? <button className="button small" type="button" disabled={pending === `rebase:${revision.id}`} onClick={() => void requestRebase(revision)}>Rebase</button> : null}</div></td></tr>) : <tr><td colSpan={6} className="muted">No signed Analyst Model Revisions.</td></tr>}</tbody></table></div>{inventory?.builds.length ? <details><summary>Application Model Build history</summary><div className="table-wrap" tabIndex={0} role="region" aria-label="Application Model Build history"><table><thead><tr><th scope="col">Queued</th><th scope="col">Build</th><th scope="col">Status</th><th scope="col">Input fingerprint</th></tr></thead><tbody>{inventory.builds.map((item) => <tr key={item.id}><td>{formatDate(item.queued_at)}</td><td className="mono">{item.id}</td><td>{item.status}</td><td className="mono">{item.input_fingerprint}</td></tr>)}</tbody></table></div></details> : null}</div> : null}
    </section>
  </div>;
}
