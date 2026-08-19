"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type Destination = "Cases" | "Sources" | "Run Console" | "Deep-Dive" | "RV Screener" | "Command Center" | "Model Builder" | "Report Studio" | "Admin Studio";
type CaseRecord = { id: string; name: string; issuer: string; sector: string; source_count?: number; accepted_snapshot?: Snapshot | null; pathway_fit?: { fit: string; message: string } };
type Snapshot = { id: string; digest: string; accepted_at: string; source_set_version?: number | null; artifacts: { id: string; module_id: string; digest: string }[] };
type RunRecord = { id: string; status: string; plan: { pathway: string; depth: string; profile_id: string; selection_id: string }; nodes: { id: string; module_id: string; status: string; artifact_id?: string | null }[]; error?: { message?: string } | null };

const destinations: { label: Destination; href: string; group: string }[] = [
  { label: "Cases", href: "/cases", group: "INTAKE" },
  { label: "Sources", href: "/sources", group: "INTAKE" },
  { label: "Run Console", href: "/run-console", group: "ANALYZE" },
  { label: "Deep-Dive", href: "/deep-dive", group: "ANALYZE" },
  { label: "RV Screener", href: "/rv-screener", group: "DECIDE" },
  { label: "Command Center", href: "/command-center", group: "DECIDE" },
  { label: "Model Builder", href: "/model-builder", group: "DECIDE" },
  { label: "Report Studio", href: "/report-studio", group: "PUBLISH" },
  { label: "Admin Studio", href: "/admin-studio", group: "ADMIN" },
];

const pathways = [
  ["FULL_CREDIT", "Full Credit"],
  ["EARNINGS_UPDATE", "Earnings Update"],
  ["COVENANT_REFINANCING", "Covenant & Refinancing"],
  ["RELATIVE_VALUE", "Relative Value"],
  ["DISTRESSED_RESTRUCTURING", "Distressed & Restructuring"],
  ["DEEP_RESEARCH", "Deep Research"],
];

async function request<T>(path: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...options, signal, headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function Workspace({ destination }: { destination: string }) {
  const active = (destinations.find((item) => item.label === destination)?.label || "Cases") as Destination;
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [caseId, setCaseId] = useState("");
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<RunRecord | null>(null);
  const [error, setError] = useState("");
  const [askQuestion, setAskQuestion] = useState("");
  const [role, setRole] = useState("ANALYST");
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    const saved = window.localStorage.getItem("caos-theme");
    return saved === "light" ? "light" : "dark";
  });
  const dialogRef = useRef<HTMLDialogElement>(null);

  const selectedCase = useMemo(() => cases.find((item) => item.id === caseId) || null, [cases, caseId]);
  const visibleDestinations = useMemo(() => role === "ADMIN" ? destinations : destinations.filter((item) => item.group !== "ADMIN"), [role]);

  const refreshCases = async (signal?: AbortSignal) => {
    try {
      const next = await request<CaseRecord[]>("/api/cases", {}, signal);
      setCases(next);
      if (!caseId && next[0]) setCaseId(next[0].id);
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof Error ? caught.message : "Unable to load cases");
    }
  };

  const refreshCase = async () => {
    if (!caseId) return;
    try {
      const next = await request<CaseRecord>(`/api/cases/${caseId}`);
      setCases((previous) => previous.map((item) => item.id === caseId ? { ...item, ...next } : item));
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to refresh case"); }
  };

  const refreshRun = async () => {
    if (!runId) return;
    try { setRun(await request<RunRecord>(`/api/runs/${runId}`)); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to refresh run"); }
  };

  useEffect(() => {
    const controller = new AbortController();
    void request<{ role: string }>("/api/me", {}, controller.signal).then((who) => setRole(who.role)).catch(() => undefined);
    const timer = window.setTimeout(() => void refreshCases(controller.signal), 0);
    return () => { controller.abort(); window.clearTimeout(timer); };
    // The selected case is intentionally not a fetch dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const openAsk = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        dialogRef.current?.showModal();
      }
    };
    window.addEventListener("keydown", openAsk);
    return () => window.removeEventListener("keydown", openAsk);
  }, [theme]);

  useEffect(() => {
    if (!runId) return;
    const source = new EventSource(`/api/runs/${runId}/events`);
    const refresh = () => void refreshRun();
    ["run.running", "node.running", "node.succeeded", "node.failed", "run.succeeded", "run.failed", "run.paused", "snapshot.accepted"].forEach((name) => source.addEventListener(name, refresh));
    const timer = window.setInterval(refresh, 1200);
    return () => { source.close(); window.clearInterval(timer); };
    // refreshRun only depends on the current run id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem("caos-theme", next);
  };

  const createCase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const form = new FormData(event.currentTarget);
    try {
      const created = await request<CaseRecord>("/api/cases", { method: "POST", body: JSON.stringify({ name: form.get("name"), issuer: form.get("issuer"), sector: form.get("sector") || "Unclassified" }) });
      setCases((previous) => [created, ...previous]); setCaseId(created.id); event.currentTarget.reset();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create case"); }
  };

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const form = new FormData(event.currentTarget);
    try { await request(`/api/cases/${caseId}/sources`, { method: "POST", body: form }); await refreshCase(); event.currentTarget.reset(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to upload source"); }
  };

  const startRun = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const form = new FormData(event.currentTarget);
    try {
      const created = await request<RunRecord>(`/api/cases/${caseId}/runs`, { method: "POST", body: JSON.stringify({ pathway: form.get("pathway"), depth: form.get("depth"), focus_questions: [] }) });
      setRun(created); setRunId(created.id);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to start run"); }
  };

  const acceptRun = async () => {
    if (!runId) return;
    try { await request(`/api/runs/${runId}/accept`, { method: "POST" }); await refreshCase(); await refreshRun(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to accept snapshot"); }
  };

  const ask = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    dialogRef.current?.close();
    const destination = /issuer|lens|posture/i.test(askQuestion) ? "command-center" : "deep-dive";
    window.location.assign(`/${destination}/`);
  };

  const renderDestination = () => {
    if (!selectedCase && active !== "Cases") return <EmptyState text="Create or select a case in Cases before entering an analytical workspace." />;
    switch (active) {
      case "Cases": return <CasesView cases={cases} selectedCase={selectedCase} caseId={caseId} setCaseId={setCaseId} createCase={createCase} upload={upload} />;
      case "Sources": return <SourcesView selectedCase={selectedCase} upload={upload} />;
      case "Run Console": return <RunConsole caseId={caseId} run={run} startRun={startRun} acceptRun={acceptRun} />;
      case "Deep-Dive": return <DeepDive selectedCase={selectedCase} />;
      case "RV Screener": return <RVView caseId={caseId} />;
      case "Command Center": return <CommandView caseId={caseId} />;
      case "Model Builder": return <ModelView caseId={caseId} />;
      case "Report Studio": return <ReportView caseId={caseId} role={role} />;
      case "Admin Studio": return <AdminView />;
    }
  };

  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <div className="desktop-gate"><div><p className="eyebrow">CAOS / WORKSPACE BOUNDARY</p><h1>Desktop workspace required</h1><p className="muted">This analytical surface is designed for a supported desktop width. No credit conclusion is hidden behind a compromised mobile layout.</p></div></div>
    <div className="app-shell" data-theme={theme}>
      <aside className="rail" aria-label="Primary navigation">
        <Link href="/cases" className="wordmark">CAOS<small>Credit Agent OS</small></Link>
        {Array.from(new Set(visibleDestinations.map((item) => item.group))).map((group) => <div className="nav-group" key={group}><div className="nav-label">{group}</div>{visibleDestinations.filter((item) => item.group === group).map((item) => <Link className={`nav-link ${active === item.label ? "active" : ""}`} href={item.href} key={item.label}>{item.label}{item.label === "Run Console" && <span className="shortcut">LIVE</span>}</Link>)}</div>)}
        <div className="nav-group"><div className="nav-label">GLOBAL</div><button className="nav-link" onClick={() => dialogRef.current?.showModal()}>Ask <span className="shortcut">⌘K</span></button></div>
      </aside>
      <section className="workspace">
        <div role="region" className="topbar" aria-label="Workspace controls"><div className="case-context"><span className="eyebrow">CASE</span><strong>{selectedCase ? `${selectedCase.issuer} / ${selectedCase.name}` : "No case selected"}</strong>{selectedCase?.accepted_snapshot && <span className="status success">accepted snapshot</span>}</div><div className="top-actions"><select aria-label="Select case" value={caseId} onChange={(event) => setCaseId(event.target.value)}><option value="">Select case</option>{cases.map((item) => <option key={item.id} value={item.id}>{item.issuer} / {item.name}</option>)}</select><button className="button small" onClick={toggleTheme}>{theme === "dark" ? "Light" : "Dark"} theme</button></div></div>
        <main className={active === "Report Studio" ? "content paper" : "content"} id="main-content"><div className="page-title"><div><div className="eyebrow">{active === "Cases" ? "INTAKE / CASE CONTEXT" : `CAOS / ${active}`}</div><h1>{active}</h1></div>{error && <div className="error" role="alert">{error}</div>}</div>{renderDestination()}</main>
      </section>
    </div>
    <dialog ref={dialogRef} aria-labelledby="ask-title"><div className="dialog-body"><div className="panel-header"><h2 id="ask-title">Ask ⌘K</h2><button type="button" className="button small" onClick={() => dialogRef.current?.close()}>Close</button></div><p className="muted">Ask is case-scoped. It can open the Issuer Lens or navigate to a visible evidence surface; it cannot create an analyst recommendation.</p><form onSubmit={ask}><div className="field"><label htmlFor="ask">Question</label><input id="ask" value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} placeholder="e.g. What changed in the accepted snapshot?" /></div><button className="button primary" type="submit">Open evidence surface</button></form></div></dialog>
  </>;
}

function EmptyState({ text }: { text: string }) { return <div className="panel"><div className="empty">{text}</div></div>; }

function CasesView({ cases, selectedCase, caseId, setCaseId, createCase, upload }: { cases: CaseRecord[]; selectedCase: CaseRecord | null; caseId: string; setCaseId: (id: string) => void; createCase: (event: FormEvent<HTMLFormElement>) => void; upload: (event: FormEvent<HTMLFormElement>) => void }) {
  return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Create case</h2><span className="eyebrow">01 / INTAKE</span></div><div className="panel-body"><form onSubmit={createCase}><div className="field"><label htmlFor="case-name">Case name</label><input id="case-name" name="name" required placeholder="Q3 credit review" /></div><div className="field"><label htmlFor="issuer">Issuer</label><input id="issuer" name="issuer" required placeholder="Issuer legal name" /></div><div className="field"><label htmlFor="sector">Sector</label><input id="sector" name="sector" placeholder="Business services" /></div><button className="button primary" type="submit">Create case</button></form></div></section><section className="panel span-8"><div className="panel-header"><h2>Case register</h2><span className="eyebrow">{cases.length} visible</span></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">Issuer</th><th scope="col">Case</th><th scope="col">Sources</th><th scope="col">Snapshot</th><th scope="col">Actions</th></tr></thead><tbody>{cases.map((item) => <tr key={item.id}><td>{item.issuer}</td><td>{item.name}<div className="muted">{item.sector}</div></td><td className="num">{item.source_count ?? "—"}</td><td>{item.accepted_snapshot ? <span className="status success">accepted</span> : <span className="status warning">not accepted</span>}</td><td><button className="button small" onClick={() => setCaseId(item.id)}>{caseId === item.id ? "Selected" : "Select"}</button></td></tr>)}</tbody></table>{!cases.length && <div className="empty">No cases yet. Create the first case to establish the context boundary.</div>}</div></section><section className="panel span-8"><div className="panel-header"><h2>Source intake</h2><span className="eyebrow">IMMUTABLE / VERSIONED</span></div><div className="panel-body">{selectedCase ? <><p className="muted">{selectedCase.issuer} / {selectedCase.name}</p><form onSubmit={upload}><div className="field"><label htmlFor="case-source">Source file</label><input id="case-source" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit">Upload and version source set</button></form></> : <div className="empty">Select a case first.</div>}</div></section><section className="panel span-4"><div className="panel-header"><h2>Pathway fit</h2><span className="eyebrow">NOT CP-0</span></div><div className="panel-body">{selectedCase ? <><span className={`status ${selectedCase.pathway_fit?.fit === "READY" ? "success" : "warning"}`}>{selectedCase.pathway_fit?.fit || "NEEDS_SOURCE"}</span><p>{selectedCase.pathway_fit?.message || "Upload a source to see fit."}</p></> : <div className="empty">—</div>}</div></section></div>;
}

function SourcesView({ selectedCase, upload }: { selectedCase: CaseRecord | null; upload: (event: FormEvent<HTMLFormElement>) => void }) {
  const [sources, setSources] = useState<{ id: string; filename: string; sha256: string; blocks: { block_id: string; locator: Record<string, unknown> }[] }[]>([]);
  useEffect(() => { if (selectedCase) void request<typeof sources>(`/api/cases/${selectedCase.id}/sources`).then(setSources).catch(() => undefined); }, [selectedCase]);
  return <div className="grid"><section className="panel span-8"><div className="panel-header"><h2>Source set</h2><span className="eyebrow">{sources.length} immutable objects</span></div><div className="panel-body table-wrap"><table><thead><tr><th>File</th><th>SHA-256</th><th>Blocks</th></tr></thead><tbody>{sources.map((source) => <tr key={source.id}><td>{source.filename}</td><td className="mono">{source.sha256.slice(0, 16)}…</td><td className="num">{source.blocks.length}</td></tr>)}</tbody></table>{!sources.length && <div className="empty">No source objects in this case.</div>}</div></section><section className="panel span-4"><div className="panel-header"><h2>Add source</h2><span className="eyebrow">BOUNDARY</span></div><div className="panel-body">{selectedCase ? <form onSubmit={upload}><div className="field"><label htmlFor="source-file">Source file</label><input id="source-file" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit">Ingest safely</button></form> : <div className="empty">Select a case.</div>}</div></section></div>;
}

function RunConsole({ caseId, run, startRun, acceptRun }: { caseId: string; run: RunRecord | null; startRun: (event: FormEvent<HTMLFormElement>) => void; acceptRun: () => void }) {
  return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Compile route</h2><span className="eyebrow">IMMUTABLE PLAN</span></div><div className="panel-body"><form onSubmit={startRun}><div className="field"><label htmlFor="pathway">Purpose</label><select id="pathway" name="pathway" defaultValue="EARNINGS_UPDATE">{pathways.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div><div className="field"><label htmlFor="depth">Depth</label><select id="depth" name="depth" defaultValue="screen"><option value="screen">Screen</option><option value="full">Full</option></select></div><button className="button primary" type="submit" disabled={!caseId}>Compile and run</button></form><div className="callout" style={{ marginTop: 14 }}>CP-PARSE is prepended to every route and CP-0 consumes its digest.</div></div></section><section className="panel span-8"><div className="panel-header"><h2>Persisted DAG</h2>{run && <span className={`status ${run.status === "succeeded" ? "success" : run.status === "failed" ? "critical" : "warning"}`}>{run.status}</span>}</div><div className="panel-body">{run ? <><div className="dag">{run.nodes.map((node) => <div className={`dag-node ${node.status}`} key={node.id}><strong>{node.module_id}</strong><div className="muted">{node.status}</div></div>)}</div>{run.error && <p className="error">{run.error.message || "Run exception"}</p>}{run.status === "succeeded" && <button className="button primary" style={{ marginTop: 15 }} onClick={acceptRun}>Accept analytical snapshot</button>}{run.status === "paused" && <div className="callout warning" style={{ marginTop: 15 }}>Material exception: upload governed source material before execution.</div>}</> : <div className="empty">No current execution. Select a purpose and depth to create an immutable plan.</div>}</div></section></div>;
}

function DeepDive({ selectedCase }: { selectedCase: CaseRecord | null }) {
  const [view, setView] = useState<{ accepted: Snapshot | null; latest_accepted: Snapshot | null; switch_required: boolean } | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { if (selectedCase) void request<typeof view>(`/api/cases/${selectedCase.id}/snapshot`).then(setView).catch(() => undefined); }, [selectedCase]);
  const switchSnapshot = async () => {
    if (!selectedCase || !view?.latest_accepted) return;
    try {
      await request(`/api/cases/${selectedCase.id}/snapshot/switch`, { method: "POST", body: JSON.stringify({ snapshot_id: view.latest_accepted.id }) });
      setView(await request<typeof view>(`/api/cases/${selectedCase.id}/snapshot`));
      setMessage("Visible snapshot switched.");
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to switch snapshot"); }
  };
  const snapshot = view?.accepted || selectedCase?.accepted_snapshot;
  return <div className="grid"><section className="panel span-8"><div className="panel-header"><h2>Overview / visible authority</h2><span className="eyebrow">DEEP-DIVE</span></div><div className="panel-body">{snapshot ? <><div className="callout"><strong>Visible accepted snapshot</strong><br /><span className="mono">{snapshot.digest}</span><br /><span className="muted">Source set v{snapshot.source_set_version ?? "—"} · accepted {snapshot.accepted_at}</span></div><h3>Artifact register</h3><div className="table-wrap"><table><caption className="muted">Typed artifacts bound to this snapshot</caption><thead><tr><th>Module</th><th>Artifact digest</th><th>Evidence</th></tr></thead><tbody>{snapshot.artifacts.map((artifact) => <tr key={artifact.id}><td className="mono">{artifact.module_id}</td><td className="mono">{artifact.digest.slice(0, 16)}…</td><td><Link href={`/sources/?artifact=${artifact.id}`}>Open source rail</Link></td></tr>)}</tbody></table></div>{view?.switch_required && <div className="callout warning" style={{ marginTop: 14 }}>A newer accepted execution exists. This view remains on the selected snapshot until you switch it explicitly.<div className="top-actions" style={{ marginTop: 10 }}><button className="button small" type="button" onClick={switchSnapshot}>Switch visible snapshot</button></div></div>}{message && <p className="muted" role="status">{message}</p>}</> : <div className="empty">No accepted snapshot. Run the selected route, inspect exceptions, then accept it explicitly.</div>}</div></section><section className="panel span-4"><div className="panel-header"><h2>Evidence rail</h2><span className="eyebrow">SYNCHRONIZED</span></div><div className="panel-body"><p className="muted">Every visible conclusion stays one interaction from its source blocks.</p><ul><li>Source set identity is pinned to the visible snapshot.</li><li>Newer execution state cannot relabel this view.</li><li>Material exceptions remain visible in Run Console.</li></ul></div></section></div>;
}

function RVView({ caseId }: { caseId: string }) { const [rv, setRv] = useState<{ status: string; rows: { instrument: string; system_signal: string | null }[]; excluded: { reasons: string[] }[] } | null>(null); const [raw, setRaw] = useState(""); const [message, setMessage] = useState(""); const refresh = () => { if (caseId) void request<typeof rv>(`/api/cases/${caseId}/rv`).then(setRv).catch(() => undefined); }; useEffect(refresh, [caseId]); const save = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setMessage(""); try { const parsed = JSON.parse(raw); const payload = Array.isArray(parsed) ? { source_version: "manual-market-sheet", rows: parsed } : parsed; await request(`/api/cases/${caseId}/rv`, { method: "POST", body: JSON.stringify(payload) }); setMessage("Market universe versioned."); refresh(); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Market universe needs valid JSON"); } }; return <div className="grid"><section className="panel span-8"><div className="panel-header"><h2>Relative value</h2><span className="eyebrow">SYSTEM SIGNAL / ANALYST SEPARATE</span></div><div className="panel-body table-wrap"><table><thead><tr><th>Instrument</th><th>System signal</th><th>Analyst recommendation</th></tr></thead><tbody>{rv?.rows.map((row) => <tr key={row.instrument}><td>{row.instrument}</td><td><span className="status">{row.system_signal || "N/A"}</span></td><td className="muted">Not written by system</td></tr>)}</tbody></table>{!rv?.rows.length && <div className="empty">Version a comparable market universe to see eligible rows.</div>}</div></section><section className="panel span-4"><div className="panel-header"><h2>Version universe</h2><span className="eyebrow">BOUNDARY</span></div><div className="panel-body"><form onSubmit={save}><div className="field"><label htmlFor="rv-json">Market rows (JSON)</label><textarea id="rv-json" value={raw} onChange={(event) => setRaw(event.target.value)} aria-describedby="rv-help" placeholder='{"source_version":"2026-08-18","rows":[{"instrument":"Issuer 1L 2029","observation_date":"2026-08-18","currency":"USD","price":98,"yield_bps":650,"spread_bps":420,"seniority":"1L","maturity":"2029-06-01","duration":2.4}]}' required /></div><p id="rv-help" className="muted">Missing comparability fields are excluded as N/A. System signal never becomes an analyst recommendation.</p><button className="button primary" type="submit">Version market universe</button>{message && <p className="muted" role="status">{message}</p>}</form><p className="mono">Excluded rows: {rv?.excluded?.length ?? 0}</p></div></section></div>; }

function CommandView({ caseId }: { caseId: string }) { const [lens, setLens] = useState<{ issuer: string; sector: string; accepted_snapshot_id: string | null; source_set?: { version: number } | null } | null>(null); useEffect(() => { if (caseId) void request<typeof lens>(`/api/cases/${caseId}/lens`).then(setLens).catch(() => undefined); }, [caseId]); return <div className="grid"><section className="panel span-6"><div className="panel-header"><h2>Issuer Lens</h2><span className="eyebrow">CASE-SCOPED</span></div><div className="panel-body"><p className="eyebrow">Issuer</p><h2>{lens?.issuer || "—"}</h2><p className="muted">{lens?.sector || "—"}</p><p className="mono">Snapshot: {lens?.accepted_snapshot_id || "none accepted"}</p><p className="mono">Source set: {lens?.source_set?.version ? `v${lens.source_set.version}` : "none"}</p></div></section><section className="panel span-6"><div className="panel-header"><h2>Posture</h2><span className="eyebrow">WHAT CHANGED</span></div><div className="panel-body"><div className="callout">No system recommendation is shown here. The analyst matrix is instrument-specific and versioned in Report Studio.</div></div></section></div>; }

function ModelView({ caseId }: { caseId: string }) { const [model, setModel] = useState<{ status: string; reason: string } | null>(null); useEffect(() => { if (caseId) void request<typeof model>(`/api/cases/${caseId}/model`).then(setModel).catch(() => undefined); }, [caseId]); return <div className="grid"><section className="panel span-8"><div className="panel-header"><h2>Model Builder</h2><span className="eyebrow">DETERMINISTIC GRAPH</span></div><div className="panel-body"><div className="callout warning"><strong>Official CP-MODEL blocked</strong><br />{model?.reason || "Signed Deploy V authority correction required."}</div><p>CAOS will not fabricate CP-2B, alias CP-2A, or label a provisional workbook as official. The model surface becomes available when the external authority gate is signed.</p></div></section></div>; }

function AdminView() { const [stepUp, setStepUp] = useState(""); const [bundle, setBundle] = useState<{ build_id: string; integrity: { checked: number; mismatches: number } } | null>(null); const [audit, setAudit] = useState<{ action: string; actor: string; at: string }[]>([]); const [message, setMessage] = useState(""); const headers = { "x-oidc-step-up": stepUp }; const load = async () => { setMessage(""); try { const [nextBundle, nextAudit] = await Promise.all([request<typeof bundle>("/api/admin/bundle", { headers }), request<typeof audit>("/api/admin/audit", { headers })]); setBundle(nextBundle); setAudit(nextAudit); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Admin verification failed"); } }; return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Step-up</h2><span className="eyebrow">ADMIN ONLY</span></div><div className="panel-body"><form onSubmit={(event) => { event.preventDefault(); void load(); }}><div className="field"><label htmlFor="step-up">OIDC step-up token</label><input id="step-up" type="password" value={stepUp} onChange={(event) => setStepUp(event.target.value)} required /></div><button className="button primary" type="submit">Verify authority</button>{message && <p className="error" role="alert">{message}</p>}</form></div></section><section className="panel span-8"><div className="panel-header"><h2>Bundle integrity</h2><span className="eyebrow">DEPLOY V</span></div><div className="panel-body">{bundle ? <><p className="mono">Build {bundle.build_id}</p><p className="status success">{bundle.integrity.checked} files verified · {bundle.integrity.mismatches} mismatches</p></> : <div className="empty">Step up to inspect the signed methodology bundle and audit trail.</div>}</div></section><section className="panel span-12"><div className="panel-header"><h2>Audit trail</h2><span className="eyebrow">IMMUTABLE EVENTS</span></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">Time</th><th scope="col">Actor</th><th scope="col">Action</th></tr></thead><tbody>{audit.map((event, index) => <tr key={`${event.at}-${index}`}><td className="mono">{event.at}</td><td>{event.actor}</td><td className="mono">{event.action}</td></tr>)}</tbody></table>{!audit.length && <div className="empty">No audit events loaded.</div>}</div></section></div>; }

function ReportView({ caseId, role }: { caseId: string; role: string }) { const [report, setReport] = useState<{ id?: string; status: string; digest: string; preview_digest?: string; input_fingerprint?: string; snapshot_digest: string; markdown: string } | null>(null); const [message, setMessage] = useState(""); const [thesis, setThesis] = useState(""); const [instrument, setInstrument] = useState(""); const [recommendation, setRecommendation] = useState("MARKET WEIGHT"); const refresh = () => { if (caseId) void request<typeof report>(`/api/cases/${caseId}/reports`).then(setReport).catch(() => undefined); }; useEffect(refresh, [caseId]); const save = async (event: FormEvent) => { event.preventDefault(); setMessage(""); try { await request(`/api/cases/${caseId}/thesis`, { method: "POST", body: JSON.stringify({ expected_version: 0, core_thesis: thesis, drivers: [], risks: [], catalysts: [], unresolved_questions: [], evidence_ids: [] }) }); await request(`/api/cases/${caseId}/recommendations`, { method: "POST", body: JSON.stringify({ expected_version: 0, market_snapshot_id: "internal-market-latest", rows: [{ instrument_id: instrument, instrument, recommendation, rationale: "Analyst-owned recommendation pending committee review.", primary: true }], analytical_dependency_ids: [] }) }); await request(`/api/cases/${caseId}/reports/freeze`, { method: "POST", body: JSON.stringify({ thesis_version: 1, recommendation_version: 1, include_model: false }) }); setMessage("Frozen report pending Approver ratification."); refresh(); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to freeze report"); } }; const approve = async () => { if (!report?.preview_digest || !report.input_fingerprint) return; try { await request(`/api/cases/${caseId}/reports/approve`, { method: "POST", body: JSON.stringify({ expected_status: "PENDING_APPROVAL", preview_digest: report.preview_digest, input_fingerprint: report.input_fingerprint }) }); setMessage("Report approved; exports are available."); refresh(); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to approve report"); } }; return <div className="grid"><section className="panel span-6"><div className="panel-header"><h2>Compose</h2><span className="eyebrow">ANALYST AUTHORITY</span></div><div className="panel-body"><form onSubmit={save}><div className="field"><label htmlFor="thesis">Core thesis</label><textarea id="thesis" value={thesis} onChange={(event) => setThesis(event.target.value)} required placeholder="State the defensible credit view." /></div><div className="field"><label htmlFor="instrument">Primary instrument</label><input id="instrument" value={instrument} onChange={(event) => setInstrument(event.target.value)} required placeholder="Issuer 1L 2029" /></div><div className="field"><label htmlFor="recommendation">Recommendation</label><select id="recommendation" value={recommendation} onChange={(event) => setRecommendation(event.target.value)}><option>OVERWEIGHT</option><option>MARKET WEIGHT</option><option>UNDERWEIGHT</option><option>N/A</option></select></div><button className="button primary" type="submit">Freeze report snapshot</button>{message && <p className={message.includes("Unable") ? "error" : "muted"} role="status">{message}</p>}</form></div></section><section className="panel span-6"><div className="panel-header"><h2>Paper proof</h2><span className="eyebrow">FROZEN DIGEST</span></div><div className="panel-body">{report ? <><span className={`status ${report.status === "APPROVED" ? "success" : "warning"}`}>{report.status}</span><p className="mono">{report.digest}</p><p className="muted">Snapshot {report.snapshot_digest}</p>{report.status === "PENDING_APPROVAL" && (role === "APPROVER" || role === "ADMIN") && <button className="button primary" type="button" onClick={approve}>Approve frozen report</button>}{report.status === "APPROVED" && <div className="top-actions"><a className="button small" href={`/api/cases/${caseId}/reports/export/md`}>Markdown</a><a className="button small" href={`/api/cases/${caseId}/reports/export/pdf`}>PDF</a><a className="button small" href={`/api/cases/${caseId}/reports/export/xlsx`}>XLSX</a></div>}<pre className="mono report-preview">{report.markdown}</pre></> : <div className="empty">No frozen report for this case.</div>}</div></section></div>; }
