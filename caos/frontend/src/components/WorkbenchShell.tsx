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

export type AuthorityStatus = "idle" | "loading" | "ready" | "error";

type Props = {
  active: Destination;
  authority: SnapshotView | null;
  authorityStatus: AuthorityStatus;
  cases: CaseRecord[];
  caseId: string;
  drawer: DrawerState | null;
  error: string;
  onCaseChange: (caseId: string) => void;
  onDrawerChange: (drawer: DrawerState | null) => void;
  role: string;
  runId: string;
  selectedCase: CaseRecord | null;
  children: ReactNode;
};

export default function WorkbenchShell({
  active,
  authority,
  authorityStatus,
  cases,
  caseId,
  drawer,
  error,
  onCaseChange,
  onDrawerChange,
  role,
  runId,
  selectedCase,
  children,
}: Props) {
  const activeWorkflow = workflowFor(active);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const drawerRef = useRef<HTMLDialogElement>(null);
  const drawerHeadingRef = useRef<HTMLHeadingElement>(null);
  const drawerTriggerRef = useRef<HTMLElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeResult, setActiveResult] = useState(0);

  const caseItems = useMemo(() => cases.filter((item) =>
    `${item.issuer} ${item.name} ${item.sector}`.toLowerCase().includes(query.toLowerCase()),
  ), [cases, query]);
  const workflowItems = useMemo(() => workflows.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()),
  ), [query]);
  const toolItems = useMemo(() => workflows.flatMap((workflow) => workflow.tools ?? []).filter((tool) =>
    !workflows.some((workflow) => workflow.href === tool.href)
      && tool.label.toLowerCase().includes(query.toLowerCase()),
  ), [query]);
  const exactEvidenceKind = caseId ? evidenceKind(query) : null;
  const resultCount = caseItems.length + workflowItems.length + toolItems.length + (exactEvidenceKind ? 1 : 0);

  const openPalette = () => {
    setPaletteOpen(true);
    setQuery("");
    setActiveResult(0);
    if (!dialogRef.current?.open) dialogRef.current?.showModal();
    window.requestAnimationFrame(() => searchRef.current?.focus());
  };

  const closePalette = () => dialogRef.current?.close();

  const closeDrawer = () => {
    onDrawerChange(null);
    const trigger = drawerTriggerRef.current;
    window.requestAnimationFrame(() => trigger?.focus());
  };

  useEffect(() => {
    const dialog = drawerRef.current;
    if (!dialog) return;
    if (!drawer) {
      if (dialog.open) dialog.close();
      return;
    }
    if (!dialog.open) {
      drawerTriggerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      dialog.showModal();
    }
    const frame = window.requestAnimationFrame(() => drawerHeadingRef.current?.focus());
    return () => window.cancelAnimationFrame(frame);
  }, [drawer]);

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
  const authorityPending = authorityStatus === "idle" || authorityStatus === "loading";
  const acceptedSnapshotIdentity = authorityPending
    ? "Loading authority…"
    : authorityStatus === "error"
      ? "Authority unavailable"
      : accepted?.id ?? "No accepted snapshot";
  const acceptedSourceSetIdentity = authorityPending
    ? "Loading authority…"
    : authorityStatus === "error"
      ? "Authority unavailable"
      : accepted
        ? accepted.source_set_version == null ? "Version unavailable" : `v${accepted.source_set_version}`
        : "No accepted source set";
  const drawerTitle = drawer?.kind === "qa"
    ? "QA details"
    : drawer?.kind === "sources"
      ? "Source details"
      : drawer?.kind === "evidence"
        ? `Evidence ${drawer.evidenceId}`
        : "Context";
  let drawerBody: ReactNode = null;
  if (drawer?.kind === "qa") {
    drawerBody = <div className="state-block unavailable">
      <strong>No governed snapshot-level QA summary is available.</strong>
      <p>Run and artifact status are not substituted for QA. Review module exceptions in Analyse.</p>
      <Link className="button small" href={withQuery("/run-console", { case: caseId })} onNavigate={closeDrawer}>Open Run Console</Link>
    </div>;
  } else if (drawer?.kind === "sources") {
    drawerBody = authorityPending ? <div className="state-block" role="status">
      <strong>Loading source authority…</strong>
      <p>Source count and accepted source-set identity are not shown until the case authority resolves.</p>
      <Link className="button small" href={withQuery("/sources", { case: caseId })} onNavigate={closeDrawer}>Open Sources</Link>
    </div> : authorityStatus === "error" ? <div className="state-block unavailable">
      <strong>Source authority unavailable.</strong>
      <p>Current source count and accepted source-set identity could not be verified.</p>
      <Link className="button small" href={withQuery("/sources", { case: caseId })} onNavigate={closeDrawer}>Open Sources</Link>
    </div> : <div className="state-block">
      <dl>
        <dt>Current source count</dt><dd className="mono">{selectedCase?.source_count ?? "Unavailable"}</dd>
        <dt>Accepted source set</dt><dd className="mono">{acceptedSourceSetIdentity}</dd>
      </dl>
      <Link className="button small" href={withQuery("/sources", { case: caseId })} onNavigate={closeDrawer}>Open Sources</Link>
    </div>;
  } else if (drawer?.kind === "evidence") {
    drawerBody = <div className="state-block">
      <dl>
        <dt>Stable ID</dt><dd className="mono">{drawer.evidenceId}</dd>
        <dt>Filename</dt><dd>{drawer.source.filename}</dd>
        <dt>SHA-256</dt><dd className="mono">{drawer.source.sha256}</dd>
        <dt>Accepted snapshot</dt><dd className="mono">{acceptedSnapshotIdentity}</dd>
        <dt>Accepted source set</dt><dd className="mono">{acceptedSourceSetIdentity}</dd>
      </dl>
      <p className="status warning">Source-level reference; no block locator supplied by this artifact.</p>
      <h3>Available source text</h3>
      <div className="source-blocks">
        {drawer.source.blocks.slice(0, 20).map((block) => <article className="source-block" key={block.block_id}>
          <div className="eyebrow">{block.block_id}</div>
          <p>{block.text || "No extracted text."}</p>
        </article>)}
        {!drawer.source.blocks.length && <p className="muted">No extracted source text.</p>}
        {drawer.source.blocks.length > 20 && <p className="muted">Showing the first 20 blocks. Open the full source for the remaining {drawer.source.blocks.length - 20} blocks.</p>}
      </div>
      <Link className="button small" href={`${withQuery("/sources", { case: caseId })}#source-${drawer.source.id}`} onNavigate={closeDrawer}>Open full source</Link>
    </div>;
  }
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
            {selectedCase && authorityPending && <span className="muted">Loading authority…</span>}
            {selectedCase && authorityStatus === "error" && <span className="status warning">Authority unavailable</span>}
            {selectedCase && authorityStatus === "ready" && !accepted && <span className="status warning">No accepted snapshot</span>}
            {authorityStatus === "ready" && accepted && <><span className="status success">Accepted <span className="optional">{new Date(accepted.accepted_at).toLocaleString()}</span></span><span className="mono">Source set v{accepted.source_set_version ?? "—"}</span></>}
            {(authority?.switch_required || authority?.diff?.changed) && <span className="status warning">New analysis available</span>}
          </div>
          <div className="top-actions">
            <label className="sr-only" htmlFor="case-select">Select case</label>
            <select id="case-select" aria-label="Select case" value={caseId} onChange={(event) => onCaseChange(event.target.value)}>
              <option value="">Select case</option>
              {cases.map((item) => <option key={item.id} value={item.id}>{item.issuer} — {item.name}</option>)}
            </select>
            <button className="button small" type="button" disabled={!selectedCase} aria-controls="context-drawer" aria-expanded={drawer?.kind === "sources"} onClick={() => onDrawerChange({ kind: "sources" })}>{!selectedCase ? "Sources" : authorityPending ? "Sources loading" : authorityStatus === "error" || selectedCase.source_count == null ? "Sources unavailable" : `${selectedCase.source_count} ${selectedCase.source_count === 1 ? "source" : "sources"}`}</button>
            <button className="button small" type="button" disabled={!selectedCase} aria-label="QA unavailable — open QA status" aria-controls="context-drawer" aria-expanded={drawer?.kind === "qa"} onClick={() => onDrawerChange({ kind: "qa" })}>QA status</button>
            <button ref={triggerRef} className="button small" type="button" aria-label="Open command palette" onClick={openPalette}>Command <span className="shortcut">⌘K</span></button>
          </div>
        </div>
        <main className={`content${active === "Report Studio" ? " report-content" : ""}`} id="main-content">
          <div className="page-title"><h1>{active}</h1>{error && <div className="error" role="alert" aria-live="assertive">{error}</div>}</div>
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
          {caseItems.length > 0 && <div role="group" aria-labelledby="palette-cases-label"><div className="palette-group-label" id="palette-cases-label">Cases</div>{caseItems.map((item) => {
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
          })}</div>}
          {workflowItems.length > 0 && <div role="group" aria-labelledby="palette-workflows-label"><div className="palette-group-label" id="palette-workflows-label">Workflows</div>{workflowItems.map((workflow) => {
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
          })}</div>}
          {toolItems.length > 0 && <div role="group" aria-labelledby="palette-tools-label"><div className="palette-group-label" id="palette-tools-label">Tools</div>{toolItems.map((tool) => {
            const index = resultIndex++;
            return <Link
              id={`command-result-${index}`}
              role="option"
              aria-selected={activeResult === index}
              className="nav-link"
              tabIndex={-1}
              key={tool.destination}
              href={workflowHref(tool.href, tool.destination)}
              onClick={closePalette}
            >Open {tool.label}</Link>;
          })}</div>}
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
    <dialog
      className="context-drawer"
      id="context-drawer"
      ref={drawerRef}
      aria-labelledby="drawer-title"
      onClose={closeDrawer}
    >
      <div className="drawer-header">
        <div>
          <span className="eyebrow">CONTEXT</span>
          <h2 id="drawer-title" ref={drawerHeadingRef} tabIndex={-1}>{drawerTitle}</h2>
        </div>
        <button className="button small" type="button" onClick={() => drawerRef.current?.close()}>Close</button>
      </div>
      <div className="drawer-body">{drawerBody}</div>
    </dialog>
  </>;
}
