"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { type Destination, routeDestinations, withQuery } from "../lib/workbench";

type CaseRecord = { id: string; name: string; issuer: string; sector: string; source_count?: number; accepted_snapshot?: Snapshot | null; pathway_fit?: { fit: string; message: string }; current_execution_id?: string | null };
type Snapshot = { id: string; digest: string; accepted_at: string; source_set_version?: number | null; artifacts: { id: string; module_id: string; digest: string }[] };
type RunRecord = { id: string; status: string; plan: { pathway: string; depth: string; profile_id: string; selection_id: string }; nodes: { id: string; module_id: string; status: string; artifact_id?: string | null }[]; error?: { message?: string } | null };
type SourceRecord = { id: string; filename: string; sha256: string; blocks: { block_id: string; locator: Record<string, unknown>; text?: string }[] };
type ArtifactRecord = { id: string; module_id: string; digest: string; markdown?: string; created_at?: string; payload?: { summary?: string; evidence_refs?: string[]; narrative?: { takeaway?: string; basis?: string }; visual?: { freshness?: string; units?: string } } };
type RVRowDraft = { instrument: string; observation_date: string; source_version: string; currency: string; price: string; yield_bps: string; spread_bps: string; seniority: string; maturity: string; duration: string };
type ReportDraft = { thesis?: string; instrument?: string; recommendation?: string; evidenceIds?: string };

const pathways = [
  ["FULL_CREDIT", "Full Credit"],
  ["EARNINGS_UPDATE", "Earnings Update"],
  ["COVENANT_REFINANCING", "Covenant & Refinancing"],
  ["RELATIVE_VALUE", "Relative Value"],
  ["DISTRESSED_RESTRUCTURING", "Distressed & Restructuring"],
  ["DEEP_RESEARCH", "Deep Research"],
];

function queryParam(key: string) {
  if (typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get(key) || "";
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

async function request<T>(path: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...options, signal, headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function Workspace({ destination }: { destination: Destination }) {
  const active = destination;
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [caseId, setCaseId] = useState("");
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<RunRecord | null>(null);
  const [casesLoading, setCasesLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState("");
  const [error, setError] = useState("");
  const [askQuestion, setAskQuestion] = useState("");
  const [pendingAction, setPendingAction] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [role, setRole] = useState("ANALYST");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [routeQuestion, setRouteQuestion] = useState("");
  const [routeArtifactId, setRouteArtifactId] = useState("");

  const selectedCase = useMemo(() => cases.find((item) => item.id === caseId) || null, [cases, caseId]);
  const visibleDestinations = useMemo(() => routeDestinations
    .filter(([slug]) => role === "ADMIN" || slug !== "admin-studio")
    .map(([slug, label]) => ({ label, href: `/${slug}`, group: label === "Cases" || label === "Sources" ? "INTAKE" : label === "Run Console" || label === "Deep-Dive" ? "ANALYZE" : label === "Report Studio" ? "PUBLISH" : label === "Admin Studio" ? "ADMIN" : "DECIDE" })), [role]);

  const selectCase = (nextCaseId: string) => {
    const draftKey = caseId ? `caos-report-draft:${caseId}` : "";
    if (draftKey && nextCaseId !== caseId && window.sessionStorage.getItem(draftKey) && !window.confirm("Discard the unsaved Report Studio draft before changing case?")) return;
    if (draftKey && nextCaseId !== caseId) window.sessionStorage.removeItem(draftKey);
    setCaseId(nextCaseId);
    setRunId(cases.find((item) => item.id === nextCaseId)?.current_execution_id || "");
    setRun(null);
    setRunError("");
    setError("");
  };

  const refreshCases = async (signal?: AbortSignal) => {
    setCasesLoading(true);
    try {
      const next = await request<CaseRecord[]>("/api/cases", {}, signal);
      setCases(next);
      const requestedCaseId = queryParam("case");
      const requestedRunId = queryParam("run");
      const resolvedCaseId = next.find((item) => item.id === caseId)?.id || next.find((item) => item.id === requestedCaseId)?.id || next[0]?.id || "";
      if (resolvedCaseId !== caseId) setCaseId(resolvedCaseId);
      if (!runId && !requestedRunId) {
        const resolvedCase = next.find((item) => item.id === resolvedCaseId);
        if (resolvedCase?.current_execution_id) setRunId(resolvedCase.current_execution_id);
      }
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof Error ? caught.message : "Unable to load cases");
    } finally {
      setCasesLoading(false);
    }
  };

  const refreshCase = async () => {
    if (!caseId) return;
    try {
      const next = await request<CaseRecord>(`/api/cases/${caseId}`);
      setCases((previous) => previous.map((item) => item.id === caseId ? { ...item, ...next } : item));
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to refresh case"); }
  };

  const refreshRun = async (id = runId) => {
    if (!id) { setRun(null); return; }
    setRunLoading(true);
    setRunError("");
    try { setRun(await request<RunRecord>(`/api/runs/${id}`)); } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unable to refresh run";
      setRunError(message);
      setError(message);
    } finally {
      setRunLoading(false);
    }
  };

  useEffect(() => {
    // URL-derived state is hydrated after the server render to keep the shell deterministic.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCaseId(queryParam("case"));
    setRunId(queryParam("run"));
    setRouteQuestion(queryParam("q"));
    setRouteArtifactId(queryParam("artifact"));
    setHydrated(true);
    const controller = new AbortController();
    const guardDraftNavigation = (event: MouseEvent) => {
      const currentCaseId = queryParam("case");
      const draftKey = currentCaseId ? `caos-report-draft:${currentCaseId}` : "";
      if (!draftKey || !window.sessionStorage.getItem(draftKey)) return;
      const target = event.target instanceof Element ? event.target.closest("a[href]") : null;
      const href = target?.getAttribute("href") || "";
      if (!target || !href.startsWith("/") || target.getAttribute("download") !== null) return;
      if (window.confirm("Discard the unsaved Report Studio draft before leaving?")) window.sessionStorage.removeItem(draftKey);
      else event.preventDefault();
    };
    document.addEventListener("click", guardDraftNavigation, true);
    void request<{ role: string }>("/api/me", {}, controller.signal).then((who) => setRole(who.role)).catch((caught) => {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof Error ? caught.message : "Unable to load identity");
    });
    const timer = window.setTimeout(() => void refreshCases(controller.signal), 0);
    return () => { controller.abort(); window.clearTimeout(timer); document.removeEventListener("click", guardDraftNavigation, true); };
    // The selected case is intentionally not a fetch dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.title = `CAOS — ${active}`;
    const openAsk = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (!dialogRef.current?.open) {
          dialogRef.current?.showModal();
          window.requestAnimationFrame(() => document.getElementById("ask")?.focus());
        }
      }
    };
    window.addEventListener("keydown", openAsk);
    return () => window.removeEventListener("keydown", openAsk);
  }, [active]);

  useEffect(() => {
    if (!hydrated) return;
    const url = new URL(window.location.href);
    if (caseId) url.searchParams.set("case", caseId); else url.searchParams.delete("case");
    if (runId) url.searchParams.set("run", runId); else url.searchParams.delete("run");
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }, [hydrated, caseId, runId]);

  useEffect(() => {
    if (!runId) return;
    // The initial refresh is an external synchronization boundary.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshRun(runId);
    const source = new EventSource(`/api/runs/${runId}/events`);
    const refresh = () => void refreshRun();
    ["run.running", "node.running", "node.succeeded", "node.failed", "run.succeeded", "run.failed", "run.paused", "snapshot.accepted"].forEach((name) => source.addEventListener(name, refresh));
    const timer = window.setInterval(refresh, 1200);
    return () => { source.close(); window.clearInterval(timer); };
    // refreshRun only depends on the current run id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const createCase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const form = new FormData(event.currentTarget);
    setPendingAction("create-case");
    try {
      const created = await request<CaseRecord>("/api/cases", { method: "POST", body: JSON.stringify({ name: form.get("name"), issuer: form.get("issuer"), sector: form.get("sector") || "Unclassified" }) });
      setCases((previous) => [created, ...previous]); selectCase(created.id); event.currentTarget.reset();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create case"); }
    finally { setPendingAction(""); }
  };

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const form = new FormData(event.currentTarget);
    setPendingAction("upload");
    try { await request(`/api/cases/${caseId}/sources`, { method: "POST", body: form }); await refreshCase(); event.currentTarget.reset(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to upload source"); }
    finally { setPendingAction(""); }
  };

  const startRun = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const form = new FormData(event.currentTarget);
    setPendingAction("start-run");
    try {
      const created = await request<RunRecord>(`/api/cases/${caseId}/runs`, { method: "POST", body: JSON.stringify({ pathway: form.get("pathway"), depth: form.get("depth"), focus_questions: [] }) });
      setRun(created); setRunId(created.id);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to start run"); }
    finally { setPendingAction(""); }
  };

  const acceptRun = async () => {
    if (!runId || !window.confirm("Accept this analytical snapshot as the visible authority for the case?")) return;
    setPendingAction("accept-run");
    try { await request(`/api/runs/${runId}/accept`, { method: "POST" }); await refreshCase(); await refreshRun(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to accept snapshot"); }
    finally { setPendingAction(""); }
  };

  const ask = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    dialogRef.current?.close();
    const destination = /issuer|lens|posture/i.test(askQuestion) ? "command-center" : "deep-dive";
    const query = new URLSearchParams();
    if (caseId) query.set("case", caseId);
    if (askQuestion.trim()) query.set("q", askQuestion.trim());
    window.location.assign(`/${destination}/?${query.toString()}`);
  };

  const renderDestination = () => {
    if (!selectedCase && active !== "Cases") return <EmptyState text="Create or select a case in Cases before entering an analytical workspace." />;
    switch (active) {
      case "Cases": return <CasesView cases={cases} casesLoading={casesLoading} selectedCase={selectedCase} caseId={caseId} setCaseId={selectCase} createCase={createCase} upload={upload} pendingAction={pendingAction} />;
      case "Sources": return <SourcesView selectedCase={selectedCase} artifactId={routeArtifactId} upload={upload} pendingAction={pendingAction} />;
      case "Run Console": return <RunConsole caseId={caseId} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} pendingAction={pendingAction} />;
      case "Deep-Dive": return <DeepDive selectedCase={selectedCase} question={routeQuestion} />;
      case "RV Screener": return <RVView caseId={caseId} />;
      case "Command Center": return <CommandView caseId={caseId} question={routeQuestion} />;
      case "Model Builder": return <ModelView caseId={caseId} />;
      case "Report Studio": return <ReportView caseId={caseId} role={role} />;
      case "Admin Studio": return <AdminView />;
    }
  };

  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <div className="app-shell">
      <aside className="rail" aria-label="Primary navigation">
        <Link href={withQuery("/cases", { case: caseId || undefined })} className="wordmark">CAOS<small>Credit Agent OS</small></Link>
        {Array.from(new Set(visibleDestinations.map((item) => item.group))).map((group) => <div className="nav-group" key={group}><div className="nav-label">{group}</div>{visibleDestinations.filter((item) => item.group === group).map((item) => <Link aria-current={active === item.label ? "page" : undefined} className={`nav-link ${active === item.label ? "active" : ""}`} href={withQuery(item.href, { case: caseId || undefined })} key={item.label}>{item.label}{item.label === "Run Console" && <span className="shortcut">LIVE</span>}</Link>)}</div>)}
        <div className="nav-group"><div className="nav-label">GLOBAL</div><button className="nav-link" onClick={() => { if (!dialogRef.current?.open) { dialogRef.current?.showModal(); window.requestAnimationFrame(() => document.getElementById("ask")?.focus()); } }}>Find evidence <span className="shortcut">⌘K</span></button></div>
      </aside>
      <section className="workspace">
        <div role="region" className="topbar" aria-label="Workspace controls"><div className="case-context"><span className="eyebrow">CASE</span><strong>{selectedCase ? `${selectedCase.issuer} / ${selectedCase.name}` : "No case selected"}</strong>{selectedCase?.accepted_snapshot && <span className="status success">accepted snapshot</span>}</div><div className="top-actions"><label className="sr-only" htmlFor="case-select">Select case</label><select id="case-select" aria-label="Select case" value={caseId} onChange={(event) => selectCase(event.target.value)}><option value="">Select case</option>{cases.map((item) => <option key={item.id} value={item.id}>{item.issuer} / {item.name}</option>)}</select></div></div>
        <main className={active === "Report Studio" ? "content paper" : "content"} id="main-content"><div className="page-title"><div><div className="eyebrow">{active === "Cases" ? "INTAKE / CASE CONTEXT" : `CAOS / ${active}`}</div><h1>{active}</h1></div>{error && <div className="error" role="alert" aria-live="assertive">{error}</div>}</div>{renderDestination()}</main>
      </section>
    </div>
    <dialog ref={dialogRef} aria-labelledby="ask-title" aria-describedby="ask-description"><div className="dialog-body"><div className="panel-header"><h2 id="ask-title">Find evidence ⌘K</h2><button type="button" className="button small" onClick={() => dialogRef.current?.close()}>Close</button></div><p id="ask-description" className="muted">Describe the evidence you need. CAOS will open the most relevant case-scoped surface and keep your question in the URL for review.</p><form onSubmit={ask}><div className="field"><label htmlFor="ask">Question</label><input id="ask" name="question" autoComplete="off" value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} placeholder="What changed in the accepted snapshot…" /></div><button className="button primary" type="submit">Open evidence surface</button></form></div></dialog>
  </>;
}

function EmptyState({ text }: { text: string }) { return <div className="panel"><div className="empty">{text}</div></div>; }

function LoadState({ loading, error, empty }: { loading: boolean; error?: string; empty?: string }) {
  if (loading) return <div className="empty" role="status" aria-live="polite">Loading…</div>;
  if (error) return <div className="empty error-state" role="alert"><strong>Unable to load this view.</strong><br /><span>{error}</span><br /><span className="muted">Retry by refreshing the destination.</span></div>;
  return <div className="empty">{empty || "No data available."}</div>;
}

function CasesView({ cases, casesLoading, selectedCase, caseId, setCaseId, createCase, upload, pendingAction }: { cases: CaseRecord[]; casesLoading: boolean; selectedCase: CaseRecord | null; caseId: string; setCaseId: (id: string) => void; createCase: (event: FormEvent<HTMLFormElement>) => void; upload: (event: FormEvent<HTMLFormElement>) => void; pendingAction: string }) {
  return <div className="grid">
    <section className="panel span-4"><div className="panel-header"><h2>Create case</h2><span className="eyebrow">01 / INTAKE</span></div><div className="panel-body"><form onSubmit={createCase}><div className="field"><label htmlFor="case-name">Case name</label><input id="case-name" name="name" autoComplete="off" required placeholder="Q3 credit review…" /></div><div className="field"><label htmlFor="issuer">Issuer</label><input id="issuer" name="issuer" autoComplete="organization" required placeholder="Issuer legal name…" /></div><div className="field"><label htmlFor="sector">Sector</label><input id="sector" name="sector" autoComplete="off" placeholder="Business services…" /></div><button className="button primary" type="submit" disabled={pendingAction === "create-case"}>{pendingAction === "create-case" ? "Creating…" : "Create case"}</button></form></div></section>
    <section className="panel span-8"><div className="panel-header"><h2>Case register</h2><span className="eyebrow">{casesLoading ? "LOADING…" : `${cases.length} visible`}</span></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">Issuer</th><th scope="col">Case</th><th scope="col">Sources</th><th scope="col">Snapshot</th><th scope="col">Actions</th></tr></thead><tbody>{cases.map((item) => <tr key={item.id}><td>{item.issuer}</td><td>{item.name}<div className="muted">{item.sector}</div></td><td className="num">{item.source_count ?? "—"}</td><td>{item.accepted_snapshot ? <span className="status success">accepted</span> : <span className="status warning">not accepted</span>}</td><td><button className="button small" type="button" aria-pressed={caseId === item.id} onClick={() => setCaseId(item.id)}>{caseId === item.id ? "Selected" : "Select"}</button></td></tr>)}</tbody></table>{!cases.length && <LoadState loading={casesLoading} empty="No cases yet. Create the first case to establish the context boundary." />}</div></section>
    <section className="panel span-8"><div className="panel-header"><h2>Source intake</h2><span className="eyebrow">IMMUTABLE / VERSIONED</span></div><div className="panel-body">{selectedCase ? <><p className="muted">{selectedCase.issuer} / {selectedCase.name}</p><form onSubmit={upload}><div className="field"><label htmlFor="case-source">Source file</label><input id="case-source" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit" disabled={pendingAction === "upload"}>{pendingAction === "upload" ? "Uploading…" : "Upload and version source set"}</button></form></> : <div className="empty">Select a case first.</div>}</div></section>
    <section className="panel span-4"><div className="panel-header"><h2>Pathway fit</h2><span className="eyebrow">NOT CP-0</span></div><div className="panel-body">{selectedCase ? <><span className={`status ${selectedCase.pathway_fit?.fit === "READY" ? "success" : "warning"}`}>{selectedCase.pathway_fit?.fit || "NEEDS_SOURCE"}</span><p>{selectedCase.pathway_fit?.message || "Upload a source to see fit."}</p></> : <div className="empty">—</div>}</div></section>
  </div>;
}

function SourcesView({ selectedCase, artifactId, upload, pendingAction }: { selectedCase: CaseRecord | null; artifactId: string; upload: (event: FormEvent<HTMLFormElement>) => void; pendingAction: string }) {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [artifact, setArtifact] = useState<ArtifactRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [artifactError, setArtifactError] = useState("");
  useEffect(() => {
    if (!selectedCase) return;
    let ignore = false;
    // The fetch boundary intentionally resets its loading and error state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true); setLoadError(""); setArtifactError(""); setArtifact(null);
    void request<SourceRecord[]>(`/api/cases/${selectedCase.id}/sources`).then((next) => { if (!ignore) setSources(next); }).catch((caught) => { if (!ignore) setLoadError(caught instanceof Error ? caught.message : "Unable to load source objects"); }).finally(() => { if (!ignore) setLoading(false); });
    if (artifactId) void request<ArtifactRecord>(`/api/cases/${selectedCase.id}/artifacts/${artifactId}`).then((next) => { if (!ignore) setArtifact(next); }).catch((caught) => { if (!ignore) setArtifactError(caught instanceof Error ? caught.message : "Unable to load evidence artifact"); });
    return () => { ignore = true; };
  }, [selectedCase, artifactId]);
  const evidenceRefs = artifact?.payload?.evidence_refs || [];
  return <div className="grid">
    {artifactId && <section className="panel span-12 evidence-focus"><div className="panel-header"><h2>Evidence focus</h2><span className="eyebrow">ARTIFACT {artifact?.module_id || artifactId}</span></div><div className="panel-body">{artifact ? <><p className="mono">{artifact.digest}</p><p>{artifact.payload?.summary || artifact.payload?.narrative?.takeaway || "No artifact summary available."}</p><p className="muted">{artifact.payload?.narrative?.basis || "Typed artifact lineage."}{artifact.payload?.visual?.freshness ? ` · ${artifact.payload.visual.freshness}` : ""}</p><p className="mono">Evidence refs: {evidenceRefs.length || 0}</p></> : <LoadState loading={!artifactError && loading} error={artifactError} empty="No artifact details were returned." />}</div></section>}
    <section className="panel span-8"><div className="panel-header"><h2>Source set</h2><span className="eyebrow">{loading ? "LOADING…" : `${sources.length} immutable objects`}</span></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">File</th><th scope="col">SHA-256</th><th scope="col">Blocks</th></tr></thead><tbody>{sources.map((source) => <tr id={`source-${source.id}`} className={evidenceRefs.includes(source.id) ? "evidence-match" : undefined} key={source.id}><td><details><summary>{source.filename}</summary><div className="source-blocks">{source.blocks.slice(0, 20).map((block) => <article className="source-block" id={`block-${source.id}-${block.block_id}`} key={block.block_id}><div className="eyebrow">{block.block_id} · {JSON.stringify(block.locator)}</div><p>{block.text || "No extracted text."}</p></article>)}{source.blocks.length > 20 && <p className="muted">Showing the first 20 blocks. Use the source object for the remaining {source.blocks.length - 20} blocks.</p>}</div></details></td><td className="mono">{source.sha256.slice(0, 16)}…</td><td className="num">{source.blocks.length}</td></tr>)}</tbody></table>{!sources.length && <LoadState loading={loading} error={loadError} empty="No source objects in this case." />}{sources.length > 0 && loadError && <p className="error" role="alert">{loadError}</p>}</div></section>
    <section className="panel span-4"><div className="panel-header"><h2>Add source</h2><span className="eyebrow">BOUNDARY</span></div><div className="panel-body">{selectedCase ? <form onSubmit={upload}><div className="field"><label htmlFor="source-file">Source file</label><input id="source-file" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit" disabled={pendingAction === "upload"}>{pendingAction === "upload" ? "Uploading…" : "Ingest safely"}</button></form> : <div className="empty">Select a case.</div>}</div></section>
  </div>;
}

function RunConsole({ caseId, run, runLoading, runError, startRun, acceptRun, pendingAction }: { caseId: string; run: RunRecord | null; runLoading: boolean; runError: string; startRun: (event: FormEvent<HTMLFormElement>) => void; acceptRun: () => void; pendingAction: string }) {
  return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Compile route</h2><span className="eyebrow">IMMUTABLE PLAN</span></div><div className="panel-body"><form onSubmit={startRun}><div className="field"><label htmlFor="pathway">Purpose</label><select id="pathway" name="pathway" defaultValue="EARNINGS_UPDATE">{pathways.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div><div className="field"><label htmlFor="depth">Depth</label><select id="depth" name="depth" defaultValue="screen"><option value="screen">Screen</option><option value="full">Full</option></select></div><button className="button primary" type="submit" disabled={!caseId || pendingAction === "start-run"}>{pendingAction === "start-run" ? "Compiling…" : "Compile and run"}</button></form><div className="callout" style={{ marginTop: 14 }}>CP-PARSE is prepended to every route and CP-0 consumes its digest.</div></div></section><section className="panel span-8"><div className="panel-header"><h2>Persisted DAG</h2>{run && <span className={`status ${run.status === "succeeded" ? "success" : run.status === "failed" ? "critical" : "warning"}`}>{run.status}</span>}</div><div className="panel-body">{run ? <><div className="dag">{run.nodes.map((node) => <div className={`dag-node ${node.status}`} key={node.id}><strong>{node.module_id}</strong><div className="muted">{node.status}</div></div>)}</div>{run.error && <p className="error" role="alert">{run.error.message || "Run exception"}</p>}{run.status === "succeeded" && <button className="button primary" style={{ marginTop: 15 }} disabled={pendingAction === "accept-run"} onClick={acceptRun}>{pendingAction === "accept-run" ? "Accepting…" : "Accept analytical snapshot"}</button>}{run.status === "paused" && <div className="callout warning" style={{ marginTop: 15 }}>Material exception: upload governed source material before execution.</div>}</> : <LoadState loading={runLoading} error={runError} empty="No current execution. Select a purpose and depth to create an immutable plan." />}</div></section></div>;
}

function DeepDive({ selectedCase, question }: { selectedCase: CaseRecord | null; question: string }) {
  const [view, setView] = useState<{ accepted: Snapshot | null; latest_accepted: Snapshot | null; switch_required: boolean } | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  useEffect(() => {
    if (!selectedCase) return;
    let ignore = false;
    // The fetch boundary intentionally resets its loading and error state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true); setLoadError("");
    void request<typeof view>(`/api/cases/${selectedCase.id}/snapshot`).then((next) => { if (!ignore) setView(next); }).catch((caught) => { if (!ignore) setLoadError(caught instanceof Error ? caught.message : "Unable to load snapshot authority"); }).finally(() => { if (!ignore) setLoading(false); });
    return () => { ignore = true; };
  }, [selectedCase]);
  const switchSnapshot = async () => {
    if (!selectedCase || !view?.latest_accepted) return;
    try {
      await request(`/api/cases/${selectedCase.id}/snapshot/switch`, { method: "POST", body: JSON.stringify({ snapshot_id: view.latest_accepted.id }) });
      setView(await request<typeof view>(`/api/cases/${selectedCase.id}/snapshot`));
      setMessage("Visible snapshot switched.");
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to switch snapshot"); }
  };
  const snapshot = view?.accepted || selectedCase?.accepted_snapshot;
  return <div className="grid">{question && <section className="panel span-12"><div className="panel-body"><div className="eyebrow">EVIDENCE REQUEST</div><p>{question}</p></div></section>}<section className="panel span-8"><div className="panel-header"><h2>Overview / visible authority</h2><span className="eyebrow">DEEP-DIVE</span></div><div className="panel-body">{snapshot ? <><div className="callout"><strong>Visible accepted snapshot</strong><br /><span className="mono">{snapshot.digest}</span><br /><span className="muted">Source set v{snapshot.source_set_version ?? "—"} · accepted {formatDate(snapshot.accepted_at)}</span></div><h3>Artifact register</h3><div className="table-wrap"><table><caption className="muted">Typed artifacts bound to this snapshot</caption><thead><tr><th scope="col">Module</th><th scope="col">Artifact digest</th><th scope="col">Evidence</th></tr></thead><tbody>{snapshot.artifacts.map((artifact) => <tr key={artifact.id}><td className="mono">{artifact.module_id}</td><td className="mono">{artifact.digest.slice(0, 16)}…</td><td><Link href={withQuery("/sources/", { case: selectedCase?.id, artifact: artifact.id })}>Open source rail</Link></td></tr>)}</tbody></table></div>{view?.switch_required && <div className="callout warning" style={{ marginTop: 14 }}>A newer accepted execution exists. This view remains on the selected snapshot until you switch it explicitly.<div className="top-actions" style={{ marginTop: 10 }}><button className="button small" type="button" onClick={switchSnapshot}>Switch visible snapshot</button></div></div>}{message && <p className="muted" role="status">{message}</p>}</> : <LoadState loading={loading} error={loadError} empty="No accepted snapshot. Run the selected route, inspect exceptions, then accept it explicitly." />}</div></section><section className="panel span-4"><div className="panel-header"><h2>Evidence rail</h2><span className="eyebrow">SYNCHRONIZED</span></div><div className="panel-body"><p className="muted">Evidence focus stays attached to the visible snapshot.</p><ul><li>Source set identity is pinned to the visible snapshot.</li><li>Artifact links open the matching source rail.</li><li>Material exceptions remain visible in Run Console.</li></ul></div></section></div>;
}

function RVView({ caseId }: { caseId: string }) {
  const [rv, setRv] = useState<{ status: string; rows: { instrument: string; system_signal: string | null; spread_bps?: number; yield_bps?: number; price?: number }[]; excluded: { row: { instrument: string }; reasons: string[] }[] } | null>(null);
  const [rows, setRows] = useState<RVRowDraft[]>([{ instrument: "", observation_date: "", source_version: "", currency: "USD", price: "", yield_bps: "", spread_bps: "", seniority: "1L", maturity: "", duration: "" }]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const refresh = async () => {
    if (!caseId) return;
    setLoading(true); setLoadError("");
    try { setRv(await request<typeof rv>(`/api/cases/${caseId}/rv`)); }
    catch (caught) { setLoadError(caught instanceof Error ? caught.message : "Unable to load relative-value universe"); }
    finally { setLoading(false); }
  };
  // RV data is an external synchronization boundary; refresh flags intentionally reset here.
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void refresh(); }, [caseId]);
  const updateRow = (index: number, key: keyof RVRowDraft, value: string) => setRows((previous) => previous.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setMessage("");
    const invalid = rows.find((row) => !row.instrument || !row.observation_date || !row.source_version || row.currency.length !== 3 || !row.seniority || !row.maturity || !row.duration || (!row.price && !row.yield_bps && !row.spread_bps));
    if (invalid) { setMessage("Each row needs identity, comparability dates, duration, and at least one market measure."); return; }
    setPending(true);
    const number = (value: string) => value.trim() ? Number(value) : undefined;
    try {
      const payload = { source_version: rows[0].source_version, rows: rows.map((row) => ({ ...row, currency: row.currency.toUpperCase(), price: number(row.price), yield_bps: number(row.yield_bps), spread_bps: number(row.spread_bps), duration: number(row.duration) })) };
      await request(`/api/cases/${caseId}/rv`, { method: "POST", body: JSON.stringify(payload) });
      setMessage("Market universe versioned."); await refresh();
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to version market universe"); }
    finally { setPending(false); }
  };
  return <div className="grid">
    <section className="panel span-8"><div className="panel-header"><h2>Relative value</h2><span className="eyebrow">SYSTEM SIGNAL / ANALYST SEPARATE</span></div><div className="panel-body table-wrap"><table><caption className="muted">Eligible rows are comparable on date, currency, source version, and basis.</caption><thead><tr><th scope="col">Instrument</th><th scope="col">Spread / yield</th><th scope="col">System signal</th><th scope="col">Analyst recommendation</th></tr></thead><tbody>{rv?.rows.map((row) => <tr key={row.instrument}><td>{row.instrument}</td><td className="num">{row.spread_bps ?? row.yield_bps ?? row.price ?? "—"}</td><td><span className="status">{row.system_signal || "N/A"}</span></td><td className="muted">Not written by system</td></tr>)}</tbody></table>{!rv?.rows.length && <LoadState loading={loading} error={loadError} empty="Version a comparable market universe to see eligible rows." />}{rv?.excluded.length ? <details className="excluded"><summary>{rv.excluded.length} excluded rows</summary><ul>{rv.excluded.map((item, index) => <li key={`${item.row.instrument}-${index}`}><strong>{item.row.instrument}</strong> — {item.reasons.join(", ")}</li>)}</ul></details> : null}</div></section>
    <section className="panel span-4"><div className="panel-header"><h2>Version universe</h2><span className="eyebrow">BOUNDARY</span></div><div className="panel-body"><form onSubmit={save}><p id="rv-help" className="muted">Enter comparable rows as fields. Missing measures or comparability fields are excluded; system signal never becomes an analyst recommendation.</p>{rows.map((row, index) => <fieldset className="rv-row" key={index}><legend>Row {index + 1}</legend><div className="rv-grid"><div className="field"><label htmlFor={`rv-instrument-${index}`}>Instrument</label><input id={`rv-instrument-${index}`} name={`instrument-${index}`} autoComplete="off" value={row.instrument} onChange={(event) => updateRow(index, "instrument", event.target.value)} required /></div><div className="field"><label htmlFor={`rv-date-${index}`}>Observation date</label><input id={`rv-date-${index}`} name={`observation-date-${index}`} type="date" value={row.observation_date} onChange={(event) => updateRow(index, "observation_date", event.target.value)} required /></div><div className="field"><label htmlFor={`rv-source-${index}`}>Source version</label><input id={`rv-source-${index}`} name={`source-version-${index}`} autoComplete="off" value={row.source_version} onChange={(event) => updateRow(index, "source_version", event.target.value)} required /></div><div className="field"><label htmlFor={`rv-currency-${index}`}>Currency</label><input id={`rv-currency-${index}`} name={`currency-${index}`} autoComplete="off" maxLength={3} value={row.currency} onChange={(event) => updateRow(index, "currency", event.target.value.toUpperCase())} required /></div><div className="field"><label htmlFor={`rv-price-${index}`}>Price</label><input id={`rv-price-${index}`} name={`price-${index}`} type="number" inputMode="decimal" step="any" value={row.price} onChange={(event) => updateRow(index, "price", event.target.value)} /></div><div className="field"><label htmlFor={`rv-yield-${index}`}>Yield (bps)</label><input id={`rv-yield-${index}`} name={`yield-${index}`} type="number" inputMode="decimal" step="any" value={row.yield_bps} onChange={(event) => updateRow(index, "yield_bps", event.target.value)} /></div><div className="field"><label htmlFor={`rv-spread-${index}`}>Spread (bps)</label><input id={`rv-spread-${index}`} name={`spread-${index}`} type="number" inputMode="decimal" step="any" value={row.spread_bps} onChange={(event) => updateRow(index, "spread_bps", event.target.value)} /></div><div className="field"><label htmlFor={`rv-seniority-${index}`}>Seniority</label><input id={`rv-seniority-${index}`} name={`seniority-${index}`} autoComplete="off" value={row.seniority} onChange={(event) => updateRow(index, "seniority", event.target.value)} required /></div><div className="field"><label htmlFor={`rv-maturity-${index}`}>Maturity</label><input id={`rv-maturity-${index}`} name={`maturity-${index}`} type="date" value={row.maturity} onChange={(event) => updateRow(index, "maturity", event.target.value)} required /></div><div className="field"><label htmlFor={`rv-duration-${index}`}>Duration</label><input id={`rv-duration-${index}`} name={`duration-${index}`} type="number" inputMode="decimal" step="any" value={row.duration} onChange={(event) => updateRow(index, "duration", event.target.value)} required /></div></div>{rows.length > 1 && <button className="button small" type="button" onClick={() => setRows((previous) => previous.filter((_, rowIndex) => rowIndex !== index))}>Remove row</button>}</fieldset>)}<div className="row-actions"><button className="button small" type="button" onClick={() => setRows((previous) => [...previous, { ...previous[previous.length - 1], instrument: "", price: "", yield_bps: "", spread_bps: "" }])}>Add row</button><button className="button primary" type="submit" disabled={pending}>{pending ? "Versioning…" : "Version market universe"}</button></div>{message && <p className={message.startsWith("Unable") || message.startsWith("Each") ? "error" : "muted"} role="status">{message}</p>}</form></div></section>
  </div>;
}

function CommandView({ caseId, question }: { caseId: string; question: string }) {
  const [lens, setLens] = useState<{ issuer: string; sector: string; accepted_snapshot_id: string | null; source_set?: { version: number } | null } | null>(null);
  const [snapshot, setSnapshot] = useState<{ accepted: Snapshot | null; latest_accepted: Snapshot | null; diff: { changed?: boolean; added?: { module_id: string; digest: string }[]; removed?: { module_id: string; digest: string }[]; modified?: { module_id: string; before: string; after: string }[]; source_set_changed?: boolean } | null } | null>(null);
  const [loading, setLoading] = useState(true); const [loadError, setLoadError] = useState("");
  // Command-center state is synchronized from two external authorities.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (!caseId) return; let ignore = false; setLoading(true); setLoadError(""); void Promise.all([request<typeof lens>(`/api/cases/${caseId}/lens`), request<typeof snapshot>(`/api/cases/${caseId}/snapshot`)]).then(([nextLens, nextSnapshot]) => { if (!ignore) { setLens(nextLens); setSnapshot(nextSnapshot); } }).catch((caught) => { if (!ignore) setLoadError(caught instanceof Error ? caught.message : "Unable to load command-center posture"); }).finally(() => { if (!ignore) setLoading(false); }); return () => { ignore = true; }; }, [caseId]);
  const diff = snapshot?.diff;
  return <div className="grid">{question && <section className="panel span-12"><div className="panel-body"><div className="eyebrow">EVIDENCE REQUEST</div><p>{question}</p></div></section>}<section className="panel span-6"><div className="panel-header"><h2>Issuer lens</h2><span className="eyebrow">CASE-SCOPED</span></div><div className="panel-body">{loading || loadError ? <LoadState loading={loading} error={loadError} /> : <><p className="eyebrow">Issuer</p><h2>{lens?.issuer || "—"}</h2><p className="muted">{lens?.sector || "—"}</p><p className="mono">Snapshot: {lens?.accepted_snapshot_id || "none accepted"}</p><p className="mono">Source set: {lens?.source_set?.version ? `v${lens.source_set.version}` : "none"}</p></>}</div></section><section className="panel span-6"><div className="panel-header"><h2>What changed</h2><span className="eyebrow">SNAPSHOT DIFF</span></div><div className="panel-body">{loading || loadError ? <LoadState loading={loading} error={loadError} /> : !snapshot?.accepted ? <div className="empty">No accepted snapshot yet. Posture becomes reviewable after an explicit acceptance.</div> : diff?.changed ? <><div className="callout warning">Accepted snapshot differs from the latest accepted execution.</div><ul className="change-list">{diff.source_set_changed && <li>Source set changed.</li>}{(diff.added?.length ?? 0) > 0 && <li>{diff.added?.length} module{diff.added?.length === 1 ? "" : "s"} added.</li>}{(diff.modified?.length ?? 0) > 0 && <li>{diff.modified?.length} module{diff.modified?.length === 1 ? "" : "s"} modified.</li>}{(diff.removed?.length ?? 0) > 0 && <li>{diff.removed?.length} module{diff.removed?.length === 1 ? "" : "s"} removed.</li>}</ul></> : <div className="callout">No material change in the current accepted snapshot.</div>}</div></section><section className="panel span-12"><div className="panel-header"><h2>Analyst boundary</h2><span className="eyebrow">AUTHORITY</span></div><div className="panel-body"><div className="callout">No system recommendation is shown here. Instrument-specific recommendations are analyst-owned and versioned in Report Studio.</div></div></section></div>;
}

function ModelView({ caseId }: { caseId: string }) {
  const [model, setModel] = useState<{ status: string; reason: string } | null>(null); const [loading, setLoading] = useState(true); const [loadError, setLoadError] = useState("");
  // Model authority is external state; loading flags intentionally reset at the fetch boundary.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (!caseId) return; let ignore = false; setLoading(true); setLoadError(""); void request<typeof model>(`/api/cases/${caseId}/model`).then((next) => { if (!ignore) setModel(next); }).catch((caught) => { if (!ignore) setLoadError(caught instanceof Error ? caught.message : "Unable to load model authority"); }).finally(() => { if (!ignore) setLoading(false); }); return () => { ignore = true; }; }, [caseId]);
  return <div className="grid"><section className="panel span-8"><div className="panel-header"><h2>Model Builder</h2><span className="eyebrow">DETERMINISTIC GRAPH</span></div><div className="panel-body">{loading || loadError ? <LoadState loading={loading} error={loadError} /> : <><div className="callout warning"><strong>Official CP-MODEL blocked</strong><br />{model?.reason || "Signed Deploy V authority correction required."}</div><p>CAOS will not fabricate CP-2B, alias CP-2A, or label a provisional workbook as official. The model surface becomes available when the external authority gate is signed.</p></>}</div></section></div>;
}

function AdminView() {
  const [stepUp, setStepUp] = useState(""); const [bundle, setBundle] = useState<{ build_id: string; integrity: { checked: number; mismatches: number } } | null>(null); const [audit, setAudit] = useState<{ action: string; actor: string; at: string }[]>([]); const [message, setMessage] = useState(""); const [pending, setPending] = useState(false); const headers = { "x-oidc-step-up": stepUp };
  const load = async () => { setMessage(""); setPending(true); try { const [nextBundle, nextAudit] = await Promise.all([request<typeof bundle>("/api/admin/bundle", { headers }), request<typeof audit>("/api/admin/audit", { headers })]); setBundle(nextBundle); setAudit(nextAudit); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Admin verification failed"); } finally { setPending(false); } };
  return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Step-up</h2><span className="eyebrow">ADMIN ONLY</span></div><div className="panel-body"><form onSubmit={(event) => { event.preventDefault(); void load(); }}><div className="field"><label htmlFor="step-up">OIDC step-up token</label><input id="step-up" name="step-up" autoComplete="one-time-code" type="password" value={stepUp} onChange={(event) => setStepUp(event.target.value)} required /></div><button className="button primary" type="submit" disabled={pending}>{pending ? "Verifying…" : "Verify authority"}</button>{message && <p className="error" role="alert">{message}</p>}</form></div></section><section className="panel span-8"><div className="panel-header"><h2>Bundle integrity</h2><span className="eyebrow">DEPLOY V</span></div><div className="panel-body">{bundle ? <><p className="mono">Build {bundle.build_id}</p><p className="status success">{bundle.integrity.checked} files verified · {bundle.integrity.mismatches} mismatches</p></> : <div className="empty">Step up to inspect the signed methodology bundle and audit trail.</div>}</div></section><section className="panel span-12"><div className="panel-header"><h2>Audit trail</h2><span className="eyebrow">IMMUTABLE EVENTS</span></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">Time</th><th scope="col">Actor</th><th scope="col">Action</th></tr></thead><tbody>{audit.map((event, index) => <tr key={`${event.at}-${index}`}><td className="mono">{formatDate(event.at)}</td><td>{event.actor}</td><td className="mono">{event.action}</td></tr>)}</tbody></table>{!audit.length && <div className="empty">No audit events loaded.</div>}</div></section></div>;
}

function ReportView({ caseId, role }: { caseId: string; role: string }) {
  const [report, setReport] = useState<{ id?: string; status: string; digest: string; preview_digest?: string; input_fingerprint?: string; snapshot_digest: string; markdown: string } | null>(null);
  const [thesisVersion, setThesisVersion] = useState(0); const [recommendationVersion, setRecommendationVersion] = useState(0); const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [thesis, setThesis] = useState(""); const [instrument, setInstrument] = useState(""); const [recommendation, setRecommendation] = useState("MARKET WEIGHT"); const [evidenceIds, setEvidenceIds] = useState(""); const [loading, setLoading] = useState(true); const [pending, setPending] = useState(""); const [draftDirty, setDraftDirty] = useState(false); const [readyCaseId, setReadyCaseId] = useState("");
  const draftKey = `caos-report-draft:${caseId}`;
  const refresh = async () => { if (!caseId) { setLoading(false); return; } setLoading(true); setError(""); try { const [nextReport, nextThesis, nextRecommendations] = await Promise.all([request<typeof report>(`/api/cases/${caseId}/reports`), request<{ current?: { version: number; core_thesis: string; evidence_ids?: string[] } }>(`/api/cases/${caseId}/thesis`), request<{ current?: { version: number; rows: { instrument: string; recommendation: string; primary?: boolean }[] } }>(`/api/cases/${caseId}/recommendations`)]); setReport(nextReport); setThesisVersion(nextThesis.current?.version || 0); setRecommendationVersion(nextRecommendations.current?.version || 0); const primary = nextRecommendations.current?.rows.find((row) => row.primary) || nextRecommendations.current?.rows[0]; const draft = window.sessionStorage.getItem(draftKey); let values: ReportDraft | null = null; if (draft) { try { values = JSON.parse(draft) as ReportDraft; } catch { window.sessionStorage.removeItem(draftKey); } } setThesis(values?.thesis ?? nextThesis.current?.core_thesis ?? ""); setInstrument(values?.instrument ?? primary?.instrument ?? ""); setRecommendation(values?.recommendation ?? primary?.recommendation ?? "MARKET WEIGHT"); setEvidenceIds(values?.evidenceIds ?? nextThesis.current?.evidence_ids?.join(", ") ?? ""); setDraftDirty(Boolean(values)); setReadyCaseId(caseId); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load report workspace"); } finally { setLoading(false); } };
  // Draft loading synchronizes persisted browser state with the selected case.
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { setReadyCaseId(""); void refresh(); }, [caseId]);
  useEffect(() => { if (readyCaseId !== caseId || !draftDirty) return; window.sessionStorage.setItem(draftKey, JSON.stringify({ thesis, instrument, recommendation, evidenceIds })); }, [caseId, draftKey, draftDirty, evidenceIds, instrument, recommendation, readyCaseId, thesis]);
  useEffect(() => { if (!draftDirty) return; const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [draftDirty]);
  const markDraft = () => setDraftDirty(true);
  const save = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setMessage(""); setError(""); setPending("freeze"); try { const refs = evidenceIds.split(",").map((value) => value.trim()).filter(Boolean); const saved = await request<{ thesis: { version: number }; recommendations: { version: number } }>(`/api/cases/${caseId}/report-inputs`, { method: "POST", body: JSON.stringify({ thesis: { expected_version: thesisVersion, core_thesis: thesis, drivers: [], risks: [], catalysts: [], unresolved_questions: [], evidence_ids: refs }, recommendations: { expected_version: recommendationVersion, market_snapshot_id: "internal-market-latest", rows: [{ instrument_id: instrument, instrument, recommendation, rationale: "Analyst-owned recommendation pending committee review.", primary: true }], analytical_dependency_ids: [] } }) }); setThesisVersion(saved.thesis.version); setRecommendationVersion(saved.recommendations.version); await request(`/api/cases/${caseId}/reports/freeze`, { method: "POST", body: JSON.stringify({ thesis_version: saved.thesis.version, recommendation_version: saved.recommendations.version, include_model: false }) }); window.sessionStorage.removeItem(draftKey); setDraftDirty(false); setMessage("Frozen report pending Approver ratification."); await refresh(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to freeze report"); } finally { setPending(""); } };
  const approve = async () => { if (!report?.preview_digest || !report.input_fingerprint) return; setPending("approve"); setError(""); try { await request(`/api/cases/${caseId}/reports/approve`, { method: "POST", body: JSON.stringify({ expected_status: "PENDING_APPROVAL", preview_digest: report.preview_digest, input_fingerprint: report.input_fingerprint }) }); setMessage("Report approved; exports are available."); await refresh(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to approve report"); } finally { setPending(""); } };
  const busy = pending === "freeze";
  return <div className="grid"><section className="panel span-6"><div className="panel-header"><h2>Compose</h2><span className="eyebrow">ANALYST AUTHORITY</span></div><div className="panel-body">{loading || (error && readyCaseId !== caseId) ? <LoadState loading={loading} error={error} /> : <form onSubmit={save}><div className="field"><label htmlFor="thesis">Core thesis</label><textarea id="thesis" name="core-thesis" autoComplete="off" value={thesis} onChange={(event) => { setThesis(event.target.value); markDraft(); }} required disabled={busy} placeholder="State the defensible credit view…" /></div><div className="field"><label htmlFor="instrument">Primary instrument</label><input id="instrument" name="instrument" autoComplete="off" value={instrument} onChange={(event) => { setInstrument(event.target.value); markDraft(); }} required disabled={busy} placeholder="Issuer 1L 2029…" /></div><div className="field"><label htmlFor="recommendation">Recommendation</label><select id="recommendation" name="recommendation" value={recommendation} onChange={(event) => { setRecommendation(event.target.value); markDraft(); }} disabled={busy}><option>OVERWEIGHT</option><option>MARKET WEIGHT</option><option>UNDERWEIGHT</option><option>N/A</option></select></div><div className="field"><label htmlFor="evidence-ids">Evidence IDs</label><input id="evidence-ids" name="evidence-ids" autoComplete="off" value={evidenceIds} onChange={(event) => { setEvidenceIds(event.target.value); markDraft(); }} placeholder="src_…, artifact_…" disabled={busy} /><span className="muted">Comma-separated source, artifact, or snapshot IDs.</span></div>{draftDirty && <p className="status warning" role="status">Draft not saved</p>}<button className="button primary" type="submit" disabled={busy}>{busy ? "Freezing…" : "Freeze report snapshot"}</button>{message && <p className="muted" role="status">{message}</p>}{error && <p className="error" role="alert">{error}</p>}</form>}</div></section><section className="panel span-6"><div className="panel-header"><h2>Paper proof</h2><span className="eyebrow">FROZEN DIGEST</span></div><div className="panel-body">{loading ? <LoadState loading /> : report ? <><span className={`status ${report.status === "APPROVED" ? "success" : "warning"}`}>{report.status}</span><p className="mono">{report.digest}</p><p className="muted">Snapshot {report.snapshot_digest}</p>{report.status === "PENDING_APPROVAL" && (role === "APPROVER" || role === "ADMIN") && <button className="button primary" type="button" onClick={approve} disabled={pending === "approve"}>{pending === "approve" ? "Approving…" : "Approve frozen report"}</button>}{report.status === "APPROVED" && <div className="top-actions"><a className="button small" href={`/api/cases/${caseId}/reports/export/md`}>Markdown</a><a className="button small" href={`/api/cases/${caseId}/reports/export/pdf`}>PDF</a><a className="button small" href={`/api/cases/${caseId}/reports/export/xlsx`}>XLSX</a></div>}<pre className="mono report-preview">{report.markdown}</pre></> : <div className="empty">No frozen report for this case.</div>}</div></section></div>;
}
