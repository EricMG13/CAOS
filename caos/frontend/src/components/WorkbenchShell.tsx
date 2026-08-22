"use client";

import Link from "next/link";
import { KeyboardEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  CaseRecord,
  Destination,
  SnapshotView,
  evidenceKind,
  withQuery,
  workflowFor,
  workflows,
} from "../lib/workbench";

export type DrawerState =
  | { kind: "qa" }
  | { kind: "sources" }
  | {
      kind: "evidence";
      evidenceId: string;
      source: {
        id: string;
        filename: string;
        sha256: string;
        blocks: { block_id: string; locator: Record<string, unknown>; text?: string }[];
      };
    };

type Props = {
  active: Destination;
  authority: SnapshotView | null;
  cases: CaseRecord[];
  caseId: string;
  drawer: DrawerState | null;
  error: string;
  onCaseChange: (caseId: string) => void;
  onDrawerChange: (drawer: DrawerState | null) => void;
  role: string;
  selectedCase: CaseRecord | null;
  children: ReactNode;
};

export default function WorkbenchShell({
  active,
  authority,
  cases,
  caseId,
  drawer,
  error,
  onCaseChange,
  onDrawerChange,
  role,
  selectedCase,
  children,
}: Props) {
  const activeWorkflow = workflowFor(active);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeResult, setActiveResult] = useState(0);
  const [runId, setRunId] = useState("");

  const caseItems = useMemo(() => cases.filter((item) =>
    `${item.issuer} ${item.name} ${item.sector}`.toLowerCase().includes(query.toLowerCase()),
  ), [cases, query]);
  const workflowItems = useMemo(() => workflows.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()),
  ), [query]);
  const exactEvidenceKind = caseId ? evidenceKind(query) : null;
  const resultCount = caseItems.length + workflowItems.length + (exactEvidenceKind ? 1 : 0);

  useEffect(() => {
    const timer = window.setTimeout(() => setRunId(new URLSearchParams(window.location.search).get("run") || ""), 0);
    return () => window.clearTimeout(timer);
  }, [active, caseId]);

  const openPalette = () => {
    setPaletteOpen(true);
    setQuery("");
    setActiveResult(0);
    if (!dialogRef.current?.open) dialogRef.current?.showModal();
    window.requestAnimationFrame(() => searchRef.current?.focus());
  };

  const closePalette = () => dialogRef.current?.close();

  useEffect(() => {
    const openShortcut = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openPalette();
      }
    };
    window.addEventListener("keydown", openShortcut);
    return () => window.removeEventListener("keydown", openShortcut);
  });

  const paletteKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closePalette();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!resultCount) return;
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActiveResult((current) => (current + step + resultCount) % resultCount);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      resultRef.current?.querySelectorAll<HTMLElement>("[role=option]")[activeResult]?.click();
    }
  };

  const workflowHref = (href: string, destination?: Destination) => withQuery(href, {
    case: caseId || undefined,
    run: destination === "Run Console" ? runId || undefined : undefined,
  });
  const overviewHref = selectedCase ? "/command-center" : "/cases";
  const accepted = authority?.accepted;
  const evidenceHref = exactEvidenceKind === "source"
    ? withQuery("/sources", { case: caseId, source: query.trim() })
    : withQuery("/sources", { case: caseId, artifact: query.trim() });
  let resultIndex = 0;

  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <div className="app-shell">
      <aside className="rail" aria-label="Primary navigation">
        <Link href={workflowHref(selectedCase ? "/command-center" : "/cases")} className="wordmark">CAOS<small>Credit Agent OS</small></Link>
        <nav aria-label="Workflows" className="nav-group">
          <div className="nav-label">WORKFLOWS</div>
          {workflows.map((workflow) => {
            const current = workflow.id === activeWorkflow.id;
            const href = workflow.id === "overview" ? overviewHref : workflow.href;
            return <Link
              aria-current={current ? "page" : undefined}
              className={`nav-link ${current ? "active" : ""}`}
              href={workflowHref(href)}
              key={workflow.id}
            >{workflow.label}</Link>;
          })}
        </nav>
        {activeWorkflow.tools?.length ? <nav aria-label={`${activeWorkflow.label} tools`} className="nav-group">
          <div className="nav-label">TOOLS</div>
          {activeWorkflow.tools.map((tool) => <Link
            aria-current={active === tool.destination ? "page" : undefined}
            className={`nav-link ${active === tool.destination ? "active" : ""}`}
            href={workflowHref(tool.href, tool.destination)}
            key={tool.destination}
          >{tool.label}{tool.destination === "Run Console" && <span className="shortcut">LIVE</span>}</Link>)}
        </nav> : null}
        {role === "ADMIN" && <div className="nav-group"><div className="nav-label">UTILITY</div><Link className={`nav-link ${active === "Admin Studio" ? "active" : ""}`} aria-current={active === "Admin Studio" ? "page" : undefined} href={workflowHref("/admin-studio")}>Admin Studio</Link></div>}
      </aside>
      <section className="workspace">
        <div role="region" className="topbar" aria-label="Accepted authority">
          <div className="case-context">
            <span className="eyebrow">CASE</span>
            <strong>{selectedCase ? `${selectedCase.issuer} / ${selectedCase.name}` : "No case selected"}</strong>
            {selectedCase && !authority && <span className="muted">Loading authority…</span>}
            {selectedCase && authority && !accepted && <span className="status warning">No accepted snapshot</span>}
            {accepted && <><span className="status success">Accepted {new Date(accepted.accepted_at).toLocaleString()}</span><span className="mono">Source set v{accepted.source_set_version ?? "—"}</span></>}
            {(authority?.switch_required || authority?.diff?.changed) && <span className="status warning">New analysis available</span>}
          </div>
          <div className="top-actions">
            <label className="sr-only" htmlFor="case-select">Select case</label>
            <select id="case-select" aria-label="Select case" value={caseId} onChange={(event) => onCaseChange(event.target.value)}>
              <option value="">Select case</option>
              {cases.map((item) => <option key={item.id} value={item.id}>{item.issuer} — {item.name}</option>)}
            </select>
            <button className="button small" type="button" disabled={!selectedCase} aria-expanded={drawer?.kind === "sources"} onClick={() => onDrawerChange({ kind: "sources" })}>{selectedCase?.source_count ?? 0} sources</button>
            <button className="button small" type="button" disabled={!selectedCase} aria-expanded={drawer?.kind === "qa"} onClick={() => onDrawerChange({ kind: "qa" })}>QA unavailable</button>
            <button ref={triggerRef} className="button small" type="button" aria-label="Open command palette" onClick={openPalette}>Command <span className="shortcut">⌘K</span></button>
          </div>
        </div>
        <main className={active === "Report Studio" ? "content paper" : "content"} id="main-content">
          <div className="page-title"><div><div className="eyebrow">{active === "Cases" ? "INTAKE / CASE CONTEXT" : `CAOS / ${active}`}</div><h1>{active}</h1></div>{error && <div className="error" role="alert" aria-live="assertive">{error}</div>}</div>
          {children}
        </main>
      </section>
    </div>
    <dialog
      ref={dialogRef}
      aria-labelledby="palette-title"
      onClose={() => { setPaletteOpen(false); setQuery(""); triggerRef.current?.focus(); }}
    >
      <div className="dialog-body">
        <div className="panel-header"><h2 id="palette-title">Command palette</h2><button type="button" className="button small" onClick={closePalette}>Close</button></div>
        <div className="field">
          <label htmlFor="command-search">Search commands</label>
          <input
            ref={searchRef}
            id="command-search"
            role="combobox"
            aria-controls="command-results"
            aria-expanded={paletteOpen}
            aria-activedescendant={resultCount ? `command-result-${activeResult}` : undefined}
            autoComplete="off"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setActiveResult(0); }}
            onKeyDown={paletteKeyDown}
          />
        </div>
        <div ref={resultRef} id="command-results" role="listbox">
          {caseItems.map((item) => {
            const index = resultIndex++;
            return <button
              id={`command-result-${index}`}
              role="option"
              aria-selected={activeResult === index}
              className="nav-link"
              type="button"
              tabIndex={-1}
              key={item.id}
              onClick={() => { onCaseChange(item.id); closePalette(); }}
            >{item.issuer} / {item.name}<span className="muted">{item.sector}</span></button>;
          })}
          {workflowItems.map((workflow) => {
            const index = resultIndex++;
            const href = workflow.id === "overview" ? overviewHref : workflow.href;
            return <Link
              id={`command-result-${index}`}
              role="option"
              aria-selected={activeResult === index}
              className="nav-link"
              tabIndex={-1}
              key={workflow.id}
              href={workflowHref(href)}
              onClick={closePalette}
            >Open {workflow.label}</Link>;
          })}
          {exactEvidenceKind && (() => {
            const index = resultIndex++;
            return <Link
              id={`command-result-${index}`}
              role="option"
              aria-selected={activeResult === index}
              className="nav-link"
              tabIndex={-1}
              href={evidenceHref}
              onClick={closePalette}
            >Open {exactEvidenceKind} ID in this case</Link>;
          })()}
          {!resultCount && <p className="muted">No authorized matches</p>}
        </div>
      </div>
    </dialog>
  </>;
}
