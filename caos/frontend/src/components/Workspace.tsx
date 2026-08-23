"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import EvidenceChip from "./EvidenceChip";
import FiledProof from "./FiledProof";

const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
import WorkbenchShell, { type AuthorityStatus, type DrawerState } from "./WorkbenchShell";
import { type CaseRecord, type Destination, type Snapshot, type SnapshotView, destinationFromSlug, routeDestinations, withQuery } from "../lib/workbench";

type ResearchWorkstream = { id: string; kind: string; question: string; assigned_questions?: string[]; perspective: string; hypothesis: string; evidence_needs: string[]; source_classes: string[]; disconfirming_test: string; completion_test: string; effort_cap: string };
type ResearchPlan = { methodology_build_id: string; brief_digest: string; source_set: { id: string; version: number }; upstream_artifacts: { module_id: string; artifact_id: string; digest: string }[]; scope: { type?: string | null; key?: string | null; source_mode?: string | null }; workstreams: ResearchWorkstream[] };
type RunRecord = { id: string; case_id: string; status: string; plan: { pathway: string; depth: string; profile_id: string; selection_id: string }; nodes: { id: string; module_id: string; status: string; artifact_id?: string | null }[]; error?: { code?: string; message?: string } | null; research?: { phase?: string; proposed_plan_hash?: string | null; approved_plan_hash?: string | null; proposed_plan?: ResearchPlan | null } | null };
type SourceRecord = { id: string; filename: string; sha256: string; blocks: { block_id: string; locator: Record<string, unknown>; text?: string }[] };
type ArtifactRecord = { id: string; module_id: string; digest: string; markdown?: string; created_at?: string; payload?: { summary?: string; evidence_refs?: string[]; narrative?: { takeaway?: string; basis?: string }; visual?: { freshness?: string; units?: string } } };
type RVRowDraft = { instrument: string; observation_date: string; source_version: string; currency: string; price: string; yield_bps: string; spread_bps: string; seniority: string; maturity: string; duration: string };
type ReportDraft = { thesis?: string; instrument?: string; recommendation?: string; evidenceIds?: string };
type EvidenceOption = { id: string; kind: "Snapshot" | "Artifact" | "Source"; label: string };

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

function evidenceIdsFrom(value: string) {
  return [...new Set(value.split(",").map((id) => id.trim()).filter(Boolean))];
}

async function request<T>(path: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...options, signal, headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function Workspace({ destination, children }: { destination?: Destination; children?: ReactNode } = {}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const routeSlug = pathname.split("/").filter(Boolean)[0] || "cases";
  const routeIsKnown = destination !== undefined || routeDestinations.some(([route]) => route === routeSlug);
  const active = destination ?? destinationFromSlug(routeSlug);
  const requestedCaseId = searchParams.get("case") || "";
  const requestedRunId = searchParams.get("run") || "";
  const routeQuestion = searchParams.get("q") || "";
  const routeArtifactId = searchParams.get("artifact") || "";
  const routeSourceId = searchParams.get("source") || "";
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [caseId, setCaseId] = useState("");
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<RunRecord | null>(null);
  const [casesLoading, setCasesLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState("");
  const [error, setError] = useState("");
  const [pendingAction, setPendingAction] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [role, setRole] = useState("ANALYST");
  const [authority, setAuthority] = useState<SnapshotView | null>(null);
  const [authorityStatus, setAuthorityStatus] = useState<AuthorityStatus>("idle");
  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const casesRequest = useRef(0);
  const authorityRequest = useRef(0);
  const runRequest = useRef(0);
  const startRunRequest = useRef(0);
  const caseIdRef = useRef("");
  const runIdRef = useRef("");
  const routeAuthorityRef = useRef("");
  const selectedCase = useMemo(() => cases.find((item) => item.id === caseId) || null, [cases, caseId]);
  const caseIsAuthorized = selectedCase !== null;

  const selectCase = useCallback((nextCaseId: string, availableCases = cases) => {
    if (nextCaseId === caseId) return true;
    const draftKey = caseId ? `caos-report-draft:${caseId}` : "";
    if (draftKey && nextCaseId !== caseId && window.sessionStorage.getItem(draftKey) && !window.confirm("Discard the unsaved Report Studio draft before changing case?")) return false;
    if (draftKey && nextCaseId !== caseId) window.sessionStorage.removeItem(draftKey);
    // A case boundary owns both the active run and any in-flight run reads.
    runRequest.current += 1;
    startRunRequest.current += 1;
    setRunLoading(false);
    setPendingAction((current) => current === "start-run" ? "" : current);
    caseIdRef.current = nextCaseId;
    setDrawer(null);
    setAuthority(null);
    setAuthorityStatus(nextCaseId ? "loading" : "idle");
    setCaseId(nextCaseId);
    const nextRunId = availableCases.find((item) => item.id === nextCaseId)?.current_execution_id || "";
    runIdRef.current = nextRunId;
    setRunId(nextRunId);
    setRun(null);
    setRunError("");
    setError("");
    return true;
  }, [caseId, cases]);

  const refreshCases = async (signal?: AbortSignal) => {
    const requestId = ++casesRequest.current;
    setCasesLoading(true);
    try {
      const next = await request<CaseRecord[]>("/api/cases", {}, signal);
      if (requestId !== casesRequest.current) return;
      setCases(next);
      const requestedCaseId = queryParam("case");
      const requestedRunId = queryParam("run");
      const requestedCase = next.find((item) => item.id === requestedCaseId);
      const currentCaseId = caseIdRef.current;
      const resolvedCaseId = next.find((item) => item.id === currentCaseId)?.id || requestedCase?.id || next[0]?.id || "";
      if (resolvedCaseId !== currentCaseId) {
        if (requestedCaseId && !requestedCase) routeAuthorityRef.current = `${requestedCaseId}\u0000${requestedRunId}`;
        if (!selectCase(resolvedCaseId, next)) return;
        if (requestedRunId && (!requestedCaseId || requestedCase)) {
          runIdRef.current = requestedRunId;
          setRunId(requestedRunId);
        }
      }
      if (!runIdRef.current && !requestedRunId) {
        const resolvedCase = next.find((item) => item.id === resolvedCaseId);
        if (resolvedCase?.current_execution_id) {
          runIdRef.current = resolvedCase.current_execution_id;
          setRunId(resolvedCase.current_execution_id);
        }
      }
    } catch (caught) {
      if (requestId !== casesRequest.current) return;
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof Error ? caught.message : "Unable to load cases");
    } finally {
      if (requestId !== casesRequest.current) return;
      setCasesLoading(false);
    }
  };

  const refreshCase = async (id = caseId, signal?: AbortSignal) => {
    if (!id || id !== caseIdRef.current) return;
    const requestId = ++authorityRequest.current;
    try {
      const [detail, snapshot] = await Promise.all([
        request<CaseRecord>(`/api/cases/${id}`, {}, signal),
        request<SnapshotView>(`/api/cases/${id}/snapshot`, {}, signal),
      ]);
      if (requestId !== authorityRequest.current || id !== caseIdRef.current) return;
      setCases((previous) => previous.map((item) => item.id === id ? { ...item, ...detail } : item));
      setAuthority(snapshot);
      setAuthorityStatus("ready");
    } catch (caught) {
      if (requestId !== authorityRequest.current || id !== caseIdRef.current) return;
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setAuthorityStatus("error");
        setError(caught instanceof Error ? caught.message : "Unable to load case authority");
      }
    }
  };

  const refreshRun = async (id = runId) => {
    const requestId = ++runRequest.current;
    if (!id) { setRun(null); setRunLoading(false); return; }
    const expectedCaseId = caseIdRef.current;
    setRunLoading(true);
    setRunError("");
    try {
      const next = await request<RunRecord>(`/api/runs/${id}`);
      if (requestId !== runRequest.current || expectedCaseId !== caseIdRef.current || id !== runIdRef.current) return;
      if (next.case_id !== expectedCaseId) {
        setRun(null);
        setRunLoading(false);
        setRunId((current) => {
          const nextRunId = current === id ? "" : current;
          runIdRef.current = nextRunId;
          return nextRunId;
        });
        setRunError("Requested run does not belong to the selected case.");
        return;
      }
      setRun(next);
    } catch (caught) {
      if (requestId !== runRequest.current || expectedCaseId !== caseIdRef.current || id !== runIdRef.current) return;
      const message = caught instanceof Error ? caught.message : "Unable to refresh run";
      setRunError(message);
      setError(message);
    } finally {
      if (requestId !== runRequest.current || expectedCaseId !== caseIdRef.current || id !== runIdRef.current) return;
      setRunLoading(false);
    }
  };

  useEffect(() => {
    // URL-derived state is hydrated after the server render to keep the shell deterministic.
    caseIdRef.current = requestedCaseId;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCaseId(requestedCaseId);
    setAuthorityStatus(requestedCaseId ? "loading" : "idle");
    runIdRef.current = requestedRunId;
    setRunId(requestedRunId);
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
    if (!hydrated) return;
    const authorizedCase = requestedCaseId ? cases.find((item) => item.id === requestedCaseId) : null;
    const routeAuthority = `${requestedCaseId}\u0000${requestedRunId}`;
    if (routeAuthorityRef.current === routeAuthority || (requestedCaseId && !authorizedCase && casesLoading)) return;
    const scheduledUnder = routeAuthorityRef.current;
    const timer = window.setTimeout(() => {
      // A local case selection acknowledges its own authority synchronously below.
      // If that happened after this route was queued, the query string it was
      // scheduled from is stale and must not be replayed over the newer selection.
      if (routeAuthorityRef.current !== scheduledUnder) return;
      if (authorizedCase && authorizedCase.id !== caseId) {
        if (!selectCase(authorizedCase.id)) {
          const url = new URL(window.location.href);
          if (caseId) url.searchParams.set("case", caseId); else url.searchParams.delete("case");
          if (runId) url.searchParams.set("run", runId); else url.searchParams.delete("run");
          window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
          return;
        }
        if (requestedRunId) {
          runIdRef.current = requestedRunId;
          setRunId(requestedRunId);
        }
        routeAuthorityRef.current = routeAuthority;
        return;
      }
      // A workflow link may omit `run`; in that case the selected case keeps its
      // current execution. An explicit run query always wins for the same case.
      if (requestedRunId && requestedRunId !== runId) {
        setRun(null);
        runIdRef.current = requestedRunId;
        setRunId(requestedRunId);
      }
      routeAuthorityRef.current = routeAuthority;
    }, 0);
    return () => window.clearTimeout(timer);
  }, [caseId, cases, casesLoading, hydrated, requestedCaseId, requestedRunId, runId, selectCase]);

  useEffect(() => {
    authorityRequest.current += 1;
    // The visible authority and contextual drawer must clear at the external case boundary.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAuthority(null); setDrawer(null); setAuthorityStatus(caseId ? "loading" : "idle");
    if (!caseId || !caseIsAuthorized) return;
    const controller = new AbortController();
    void refreshCase(caseId, controller.signal);
    return () => controller.abort();
    // `refreshCase` deliberately resolves the current external authority.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, caseIsAuthorized]);

  useEffect(() => {
    document.title = `CAOS — ${active}`;
  }, [active]);

  useEffect(() => {
    if (!hydrated) return;
    const url = new URL(window.location.href);
    if (caseId) url.searchParams.set("case", caseId); else url.searchParams.delete("case");
    if (runId) url.searchParams.set("run", runId); else url.searchParams.delete("run");
    // `useSearchParams` trails this write by a render, so the route effect above can
    // still observe the previous case/run. Claim that authority here, synchronously,
    // or a case switch can be reverted by its own stale query string and the previous
    // issuer's run re-attached after the analyst has already moved on.
    routeAuthorityRef.current = `${caseId}\u0000${runId}`;
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }, [hydrated, caseId, runId]);

  useEffect(() => {
    if (!runId || !caseIsAuthorized) return;
    // The initial refresh is an external synchronization boundary.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshRun(runId);
    // refreshRun only depends on the current run id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseIsAuthorized, runId]);

  useEffect(() => {
    if (!runId || !run || run.id !== runId || run.case_id !== caseId) return;
    const source = new EventSource(`/api/runs/${runId}/events`);
    const refresh = () => void refreshRun();
    ["run.running", "node.running", "node.succeeded", "node.failed", "run.succeeded", "run.failed", "run.paused", "research.plan_ready", "research.plan_approved", "snapshot.accepted"].forEach((name) => source.addEventListener(name, refresh));
    const timer = window.setInterval(refresh, 1200);
    return () => { source.close(); window.clearInterval(timer); };
    // Event updates only begin after the run has passed its case authority check.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, run?.case_id, run?.id, runId]);

  const createCase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setPendingAction("create-case");
    try {
      const created = await request<CaseRecord>("/api/cases", { method: "POST", body: JSON.stringify({ name: form.get("name"), issuer: form.get("issuer"), sector: form.get("sector") || "Unclassified" }) });
      casesRequest.current += 1;
      setCases((previous) => [created, ...previous]); selectCase(created.id); formElement.reset();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create case"); }
    finally { setPendingAction(""); }
  };

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setPendingAction("upload");
    try { await request(`/api/cases/${caseId}/sources`, { method: "POST", body: form }); await refreshCase(caseId); formElement.reset(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to upload source"); }
    finally { setPendingAction(""); }
  };

  const startRun = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const form = new FormData(event.currentTarget);
    const pathway = String(form.get("pathway") || "");
    const depth = String(form.get("depth") || "");
    const mustAnswer = String(form.get("must_answer") || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const exclusions = String(form.get("exclusions") || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (pathway === "DEEP_RESEARCH" && (mustAnswer.length > 10 || exclusions.length > 10 || mustAnswer.length + exclusions.length > 10 || [...mustAnswer, ...exclusions].some((line) => line.length > 200))) {
      setError("Research brief lists allow at most 10 nonblank lines combined, and each line is limited to 200 characters.");
      return;
    }
    const researchBrief = pathway === "DEEP_RESEARCH" ? {
      research_question: String(form.get("research_question") || "").trim(),
      decision_context: String(form.get("decision_context") || "").trim(),
      as_of_date: String(form.get("as_of_date") || ""),
      time_horizon: String(form.get("time_horizon") || "").trim(),
      must_answer: mustAnswer,
      exclusions,
    } : undefined;
    const expectedCaseId = caseIdRef.current;
    const requestId = ++startRunRequest.current;
    setPendingAction("start-run");
    try {
      const created = await request<RunRecord>(`/api/cases/${expectedCaseId}/runs`, { method: "POST", body: JSON.stringify({ pathway, depth, focus_questions: [], ...(researchBrief ? { research_brief: researchBrief } : {}) }) });
      if (requestId !== startRunRequest.current || expectedCaseId !== caseIdRef.current) return;
      if (created.case_id !== expectedCaseId) {
        const message = "Started run does not belong to the selected case.";
        setRunError(message);
        setError(message);
        return;
      }
      setRun(created); runIdRef.current = created.id; setRunId(created.id);
    } catch (caught) {
      if (requestId === startRunRequest.current && expectedCaseId === caseIdRef.current) setError(caught instanceof Error ? caught.message : "Unable to start run");
    } finally {
      if (requestId === startRunRequest.current) setPendingAction((current) => current === "start-run" ? "" : current);
    }
  };

  const acceptRun = async () => {
    if (!runId || !run || run.id !== runId || run.case_id !== caseId) {
      setRunError("Only a run bound to the selected case can be accepted.");
      return;
    }
    if (!window.confirm("Accept this analytical snapshot as the visible authority for the case?")) return;
    setPendingAction("accept-run");
    try { await request(`/api/runs/${runId}/accept`, { method: "POST" }); await refreshCase(caseId); await refreshRun(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to accept snapshot"); }
    finally { setPendingAction(""); }
  };

  const approveResearchPlan = async (planHash: string) => {
    if (!runId || !run || run.id !== runId || run.case_id !== caseId) return;
    const expectedCaseId = caseId;
    const expectedRunId = runId;
    setError("");
    setPendingAction("approve-research-plan");
    try {
      await request(`/api/runs/${expectedRunId}/research-plan/approve`, { method: "POST", body: JSON.stringify({ plan_hash: planHash }) });
      if (expectedCaseId === caseIdRef.current && expectedRunId === runIdRef.current) await refreshRun(expectedRunId);
    } catch (caught) {
      if (expectedCaseId === caseIdRef.current && expectedRunId === runIdRef.current) setError(caught instanceof Error ? caught.message : "Unable to approve research plan");
    } finally {
      setPendingAction((current) => current === "approve-research-plan" ? "" : current);
    }
  };

  const renderDestination = () => {
    if (!selectedCase && active !== "Cases" && active !== "Admin Studio") return <EmptyState text="Create or select a case before entering an analytical workspace." action="Open Cases" href="/cases" />;
    switch (active) {
      case "Cases": return <CasesView cases={cases} casesLoading={casesLoading} selectedCase={selectedCase} caseId={caseId} setCaseId={selectCase} createCase={createCase} upload={upload} pendingAction={pendingAction} />;
      case "Sources": return <SourcesView selectedCase={selectedCase} artifactId={routeArtifactId} sourceId={routeSourceId} upload={upload} pendingAction={pendingAction} onOpenEvidence={(evidenceId, source) => setDrawer({ kind: "evidence", evidenceId, source })} />;
      case "Run Console": return <RunConsole caseId={caseId} selectedCase={selectedCase} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} approveResearchPlan={approveResearchPlan} pendingAction={pendingAction} />;
      case "Deep-Dive": return <DeepDive selectedCase={selectedCase} question={routeQuestion} />;
      case "RV Screener": return <RVView caseId={caseId} />;
      case "Command Center": return <CommandView caseId={caseId} question={routeQuestion} />;
      case "Model Builder": return <ModelView caseId={caseId} />;
      case "Report Studio": return <ReportView acceptedSnapshot={authority?.accepted ?? null} caseId={caseId} role={role} selectedCase={selectedCase} />;
      case "Admin Studio": return <AdminView />;
    }
  };

  return <WorkbenchShell
      active={active}
      authority={authority}
      authorityStatus={authorityStatus}
      cases={cases}
      caseId={caseId}
      drawer={drawer}
      error={error}
      onCaseChange={selectCase}
      onDrawerChange={setDrawer}
      role={role}
      runId={runId}
      selectedCase={selectedCase}
    >
      <div key={`${active}:${caseId}`}>{routeIsKnown ? <>{renderDestination()}{children}</> : children}</div>
    </WorkbenchShell>;
}

function EmptyState({ text, action, href }: { text: string; action?: string; href?: string }) {
  return <div className="panel"><div className="empty"><p>{text}</p>{action && href && <Link className="button small" href={href}>{action}</Link>}</div></div>;
}

function LoadState({ loading, error, empty }: { loading: boolean; error?: string; empty?: string }) {
  if (loading) return <div className="state-skeleton" role="status" aria-live="polite" aria-label="Loading"><span /><span /><span /></div>;
  if (error) return <div className="empty error-state" role="alert"><strong>Unable to load this view.</strong><p>{error}</p><button className="button small" type="button" onClick={() => window.location.reload()}>Retry</button></div>;
  return <div className="empty">{empty || "No data available."}</div>;
}

function ActionState({ title, detail, action, href, warning = false }: { title: string; detail: string; action: string; href: string; warning?: boolean }) {
  return <div className={`action-state${warning ? " warning" : ""}`}><strong>{title}</strong><p>{detail}</p><Link className="button small" href={href}>{action}</Link></div>;
}

function CasesView({ cases, casesLoading, selectedCase, caseId, setCaseId, createCase, upload, pendingAction }: { cases: CaseRecord[]; casesLoading: boolean; selectedCase: CaseRecord | null; caseId: string; setCaseId: (id: string) => void; createCase: (event: FormEvent<HTMLFormElement>) => void; upload: (event: FormEvent<HTMLFormElement>) => void; pendingAction: string }) {
  const [search, setSearch] = useState("");
  const [snapshotFilter, setSnapshotFilter] = useState<"all" | "accepted" | "unaccepted">("all");
  const visibleCases = useMemo(() => cases.filter((item) => {
    const matchesSearch = `${item.issuer} ${item.name} ${item.sector}`.toLowerCase().includes(search.trim().toLowerCase());
    const matchesFilter = snapshotFilter === "all"
      || (snapshotFilter === "accepted" ? Boolean(item.accepted_snapshot) : !item.accepted_snapshot);
    return matchesSearch && matchesFilter;
  }), [cases, search, snapshotFilter]);
  return <div className="grid cases-layout">
    <section className="panel cases-register"><div className="panel-header"><h2>Case register</h2><span className="panel-meta">{casesLoading ? "Loading…" : `${visibleCases.length} of ${cases.length}`}</span></div><div className="worklist-toolbar"><div className="field"><label htmlFor="case-search">Search cases</label><input id="case-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Issuer, case, or sector" /></div><div className="field"><label htmlFor="case-snapshot-filter">Snapshot</label><select id="case-snapshot-filter" value={snapshotFilter} onChange={(event) => setSnapshotFilter(event.target.value as "all" | "accepted" | "unaccepted")}><option value="all">All</option><option value="accepted">Accepted</option><option value="unaccepted">Not accepted</option></select></div></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">Issuer</th><th scope="col">Case</th><th scope="col">Sources</th><th scope="col">Snapshot</th><th scope="col">Actions</th></tr></thead><tbody>{visibleCases.map((item) => <tr key={item.id}><td>{item.issuer}</td><td>{item.name}<div className="muted">{item.sector}</div></td><td className="num">{item.source_count ?? "—"}</td><td>{item.accepted_snapshot ? <span className="status success">accepted</span> : <span className="status warning">not accepted</span>}</td><td><button className="button small" type="button" aria-pressed={caseId === item.id} onClick={() => setCaseId(item.id)}>{caseId === item.id ? "Selected" : "Select"}</button></td></tr>)}</tbody></table>{!visibleCases.length && <LoadState loading={casesLoading} empty={cases.length ? "No cases match this search and filter." : "No cases yet. Create the first case to establish the context boundary."} />}</div></section>
    <section className="panel cases-create"><div className="panel-header"><h2>Create case</h2></div><div className="panel-body"><form onSubmit={createCase}><div className="field"><label htmlFor="case-name">Case name</label><input id="case-name" name="name" autoComplete="off" required placeholder="Q3 credit review…" /></div><div className="field"><label htmlFor="issuer">Issuer</label><input id="issuer" name="issuer" autoComplete="organization" required placeholder="Issuer legal name…" /></div><div className="field"><label htmlFor="sector">Sector</label><input id="sector" name="sector" autoComplete="off" placeholder="Business services…" /></div><button className={`button ${selectedCase ? "" : "primary"}`} type="submit" disabled={pendingAction === "create-case"}>{pendingAction === "create-case" ? "Creating…" : "Create case"}</button></form></div></section>
    <section className="panel cases-fit"><div className="panel-header"><h2>Pathway fit</h2></div><div className="panel-body">{selectedCase ? <><span className={`status ${selectedCase.pathway_fit?.fit === "READY" ? "success" : "warning"}`}>{selectedCase.pathway_fit?.fit || "NEEDS_SOURCE"}</span><p>{selectedCase.pathway_fit?.message || "Upload a source to see fit."}</p></> : <div className="empty">Select a case to inspect pathway fit.</div>}</div></section>
    <section className="panel cases-intake"><div className="panel-header"><h2>Source intake</h2><span className="panel-meta">Immutable · versioned</span></div><div className="panel-body">{selectedCase ? <><p className="muted">{selectedCase.issuer} / {selectedCase.name}</p><form onSubmit={upload}><div className="field"><label htmlFor="case-source">Source file</label><input id="case-source" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit" disabled={pendingAction === "upload"}>{pendingAction === "upload" ? "Uploading…" : "Upload and version source set"}</button></form></> : <div className="empty">Select a case before adding governed source material.</div>}</div></section>
  </div>;
}

function SourcesView({ selectedCase, artifactId, sourceId, upload, pendingAction, onOpenEvidence }: { selectedCase: CaseRecord | null; artifactId: string; sourceId: string; upload: (event: FormEvent<HTMLFormElement>) => void; pendingAction: string; onOpenEvidence: (evidenceId: string, source: SourceRecord) => void }) {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [artifact, setArtifact] = useState<ArtifactRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [readySourceCaseId, setReadySourceCaseId] = useState("");
  const [artifactError, setArtifactError] = useState("");
  const [linkedEvidenceId, setLinkedEvidenceId] = useState("");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState("");
  const openedSourceQuery = useRef("");
  useEffect(() => {
    if (!selectedCase) return;
    let ignore = false;
    // The fetch boundary intentionally resets its loading and error state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true); setLoadError(""); setReadySourceCaseId(""); setArtifactError(""); setArtifact(null);
    void request<SourceRecord[]>(`/api/cases/${selectedCase.id}/sources`).then((next) => { if (!ignore) { setSources(next); setReadySourceCaseId(selectedCase.id); } }).catch((caught) => { if (!ignore) setLoadError(caught instanceof Error ? caught.message : "Unable to load source objects"); }).finally(() => { if (!ignore) setLoading(false); });
    if (artifactId) void request<ArtifactRecord>(`/api/cases/${selectedCase.id}/artifacts/${artifactId}`).then((next) => { if (!ignore) setArtifact(next); }).catch((caught) => { if (!ignore) setArtifactError(caught instanceof Error ? caught.message : "Unable to load evidence artifact"); });
    return () => { ignore = true; };
  }, [selectedCase, artifactId]);
  const evidenceRefs = artifact?.payload?.evidence_refs || [];
  const sourceById = useMemo(() => new Map(sources.map((source) => [source.id, source])), [sources]);
  const activeEvidenceId = linkedEvidenceId || selectedEvidenceId;
  const openEvidence = (evidenceId: string) => {
    const source = sourceById.get(evidenceId);
    if (!source) {
      setArtifactError(`Evidence ${evidenceId} is not in the active case source set.`);
      return;
    }
    setArtifactError("");
    setSelectedEvidenceId(evidenceId);
    onOpenEvidence(evidenceId, source);
  };
  useEffect(() => {
    if (!selectedCase || !sourceId || loading || readySourceCaseId !== selectedCase.id) return;
    const queryKey = `${selectedCase.id}:${sourceId}`;
    if (openedSourceQuery.current === queryKey) return;
    openedSourceQuery.current = queryKey;
    const source = sourceById.get(sourceId);
    if (!source) {
      // The requested ID stays scoped to the active case source set.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setArtifactError(`Evidence ${sourceId} is not in the active case source set.`);
      return;
    }
    // Exact source-query hydration is an external navigation boundary.
    setSelectedEvidenceId(sourceId);
    onOpenEvidence(sourceId, source);
  }, [loading, onOpenEvidence, readySourceCaseId, selectedCase, sourceById, sourceId]);
  return <div className="grid">
    {artifactId && <section className="panel span-12 evidence-focus"><div className="panel-header"><h2>Evidence focus</h2><span className="eyebrow">ARTIFACT {artifact?.module_id || artifactId}</span></div><div className="panel-body">{artifact ? <><p className="mono">{artifact.digest}</p><p>{artifact.payload?.summary || artifact.payload?.narrative?.takeaway || "No artifact summary available."}</p><p className="muted">{artifact.payload?.narrative?.basis || "Typed artifact lineage."}{artifact.payload?.visual?.freshness ? ` · ${artifact.payload.visual.freshness}` : ""}</p><div className="evidence-list" aria-label="Artifact evidence">{evidenceRefs.map((evidenceId) => <EvidenceChip evidenceId={evidenceId} key={evidenceId} linkedId={activeEvidenceId} onOpen={openEvidence} onPreview={setLinkedEvidenceId} onPreviewEnd={() => setLinkedEvidenceId("")} />)}</div></> : <LoadState loading={!artifactError && loading} error={artifactError} empty="No artifact details were returned." />}</div></section>}
    <section className="panel span-8"><div className="panel-header"><h2>Source set</h2><span className="eyebrow">{loading ? "LOADING…" : `${sources.length} immutable objects`}</span></div><div className="panel-body table-wrap">{selectedEvidenceId && <div className="selection-strip" role="status"><span>Evidence {selectedEvidenceId}</span><button type="button" className="button small" onClick={() => setSelectedEvidenceId("")}>Clear</button></div>}{artifactError && !artifactId && <p className="error" role="alert">{artifactError}</p>}<table><thead><tr><th scope="col">File</th><th scope="col">SHA-256</th><th scope="col">Blocks</th></tr></thead><tbody>{sources.map((source) => <tr id={`source-${source.id}`} className={activeEvidenceId === source.id ? "evidence-match" : undefined} key={source.id}><td><div className="source-file"><details><summary>{source.filename}</summary><div className="source-blocks">{source.blocks.slice(0, 20).map((block) => <article className="source-block" id={`block-${source.id}-${block.block_id}`} key={block.block_id}><div className="eyebrow">{block.block_id} · {JSON.stringify(block.locator)}</div><p>{block.text || "No extracted text."}</p></article>)}{source.blocks.length > 20 && <p className="muted">Showing the first 20 blocks. Use the source object for the remaining {source.blocks.length - 20} blocks.</p>}</div></details>{evidenceRefs.includes(source.id) && <EvidenceChip evidenceId={source.id} linkedId={activeEvidenceId} onOpen={openEvidence} onPreview={setLinkedEvidenceId} onPreviewEnd={() => setLinkedEvidenceId("")} />}</div></td><td className="mono">{source.sha256.slice(0, 16)}…</td><td className="num">{source.blocks.length}</td></tr>)}</tbody></table>{!sources.length && <LoadState loading={loading} error={loadError} empty="No source objects in this case." />}{sources.length > 0 && loadError && <p className="error" role="alert">{loadError}</p>}</div></section>
    <section className="panel span-4"><div className="panel-header"><h2>Add source</h2><span className="eyebrow">BOUNDARY</span></div><div className="panel-body">{selectedCase ? <form onSubmit={upload}><div className="field"><label htmlFor="source-file">Source file</label><input id="source-file" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit" disabled={pendingAction === "upload"}>{pendingAction === "upload" ? "Uploading…" : "Ingest safely"}</button></form> : <div className="empty">Select a case.</div>}</div></section>
  </div>;
}

function RunConsole({ caseId, selectedCase, run, runLoading, runError, startRun, acceptRun, approveResearchPlan, pendingAction }: { caseId: string; selectedCase: CaseRecord | null; run: RunRecord | null; runLoading: boolean; runError: string; startRun: (event: FormEvent<HTMLFormElement>) => void; acceptRun: () => void; approveResearchPlan: (planHash: string) => void; pendingAction: string }) {
  const [pathway, setPathway] = useState("EARNINGS_UPDATE");
  const [depth, setDepth] = useState("screen");
  const deepResearchAvailable = selectedCase?.deep_research_available === true;
  const deepResearchReason = selectedCase?.deep_research_unavailable_reason || "Checking Deep Research availability…";
  const approvalPlan = run?.status === "paused" && run.error?.code === "PLAN_APPROVAL_REQUIRED" ? run.research?.proposed_plan : null;
  const approvalHash = run?.status === "paused" && run.error?.code === "PLAN_APPROVAL_REQUIRED" ? run.research?.proposed_plan_hash : null;
  return <div className="grid">
    <section className="panel span-4">
      <div className="panel-header"><h2>Compile route</h2><span className="panel-meta">Immutable plan</span></div>
      <div className="panel-body flow">
        <form onSubmit={startRun}>
          <div className="field">
            <label htmlFor="pathway">Purpose</label>
            <select id="pathway" name="pathway" value={pathway} aria-describedby={!deepResearchAvailable ? "deep-research-availability" : undefined} onChange={(event) => { setPathway(event.target.value); if (event.target.value === "DEEP_RESEARCH") setDepth("full"); }}>
              {pathways.map(([value, label]) => <option value={value} disabled={value === "DEEP_RESEARCH" && !deepResearchAvailable} key={value}>{label}</option>)}
            </select>
          </div>
          {!deepResearchAvailable && <p className="muted" id="deep-research-availability">{deepResearchReason}</p>}
          <div className="field">
            <label htmlFor="depth">Depth</label>
            <select id="depth" name="depth" value={depth} onChange={(event) => setDepth(event.target.value)}><option value="screen" disabled={pathway === "DEEP_RESEARCH"}>Screen</option><option value="full">Full</option></select>
          </div>
          {pathway === "DEEP_RESEARCH" && <fieldset className="research-brief">
            <legend>Bounded research brief</legend>
            <div className="field"><label htmlFor="research-question">Research question</label><textarea id="research-question" name="research_question" maxLength={400} required /></div>
            <div className="field"><label htmlFor="decision-context">Decision context</label><textarea id="decision-context" name="decision_context" maxLength={400} required /></div>
            <div className="field"><label htmlFor="as-of-date">As-of date</label><input id="as-of-date" name="as_of_date" type="date" required /></div>
            <div className="field"><label htmlFor="time-horizon">Time horizon</label><input id="time-horizon" name="time_horizon" maxLength={200} required /></div>
            <div className="field"><label htmlFor="must-answer">Must-answer lines</label><textarea id="must-answer" name="must_answer" maxLength={2009} aria-describedby="research-list-bounds" /></div>
            <div className="field"><label htmlFor="exclusions">Exclusion lines</label><textarea id="exclusions" name="exclusions" maxLength={2009} aria-describedby="research-list-bounds" /></div>
            <p className="muted" id="research-list-bounds">One item per line; 10 items combined, 200 characters per item.</p>
          </fieldset>}
          <button className="button primary" type="submit" disabled={!caseId || pendingAction === "start-run"}>{pendingAction === "start-run" ? "Compiling…" : "Compile and run"}</button>
        </form>
        <div className="callout">Every route begins by parsing your sources; the readiness check then runs against that exact parse.</div>
      </div>
    </section>
    <section className="panel span-8">
      <div className="panel-header"><h2>Persisted DAG</h2><span role="status" aria-live="polite" aria-atomic="true" className={run ? `status ${run.status === "succeeded" ? "success" : run.status === "failed" ? "critical" : "warning"}` : "sr-only"}>{run?.error?.code === "PLAN_APPROVAL_REQUIRED" ? "Pending approval" : run?.status || ""}</span></div>
      <div className="panel-body flow">{run ? <>
        <div className="dag">{run.nodes.map((node, index) => <div className="dag-step" key={node.id}>{index > 0 && <span className="dag-edge" aria-hidden="true">→</span>}<div className={`dag-node ${node.status}`}><strong>{node.module_id}</strong><div className="muted">{node.status}</div></div></div>)}</div>
        {run.status === "failed" && run.error && <p className="error" role="alert">{run.error.code ? `${run.error.code}: ` : ""}{run.error.message || "Run exception"}</p>}
        {run.status === "succeeded" && <button className="button primary" disabled={pendingAction === "accept-run"} onClick={acceptRun}>{pendingAction === "accept-run" ? "Accepting…" : "Accept analytical snapshot"}</button>}
        {run.status === "paused" && run.error?.code === "SOURCE_SET_EMPTY" && <div className="callout warning" role="status" aria-live="polite">Material exception: upload governed source material before execution.</div>}
        {run.status === "paused" && run.error?.code === "PLAN_APPROVAL_REQUIRED" && approvalPlan && approvalHash && <ResearchPlanView plan={approvalPlan} planHash={approvalHash} approving={pendingAction === "approve-research-plan"} onApprove={approveResearchPlan} />}
        {run.status === "paused" && run.error?.code === "PLAN_APPROVAL_REQUIRED" && (!approvalPlan || !approvalHash) && <div className="callout warning" role="status" aria-live="polite"><strong>PLAN_APPROVAL_REQUIRED</strong><p>The persisted approval plan is unavailable; approval remains blocked.</p></div>}
        {run.status === "paused" && !["SOURCE_SET_EMPTY", "PLAN_APPROVAL_REQUIRED"].includes(run.error?.code || "") && <div className="callout warning" role="status" aria-live="polite"><strong>{run.error?.code || "RUN_PAUSED"}</strong><p>{run.error?.message || "Run paused."}</p></div>}
      </> : <LoadState loading={runLoading} error={runError} empty="No current execution. Select a purpose and depth to create an immutable plan." />}</div>
    </section>
  </div>;
}

function ResearchPlanView({ plan, planHash, approving, onApprove }: { plan: ResearchPlan; planHash: string; approving: boolean; onApprove: (planHash: string) => void }) {
  const scalar = (value: string | number | null | undefined) => value === "" || value == null ? <span className="muted">None</span> : value;
  return <section className="research-plan" role="region" aria-labelledby="research-plan-heading">
    <h3 id="research-plan-heading">Proposed research plan</h3>
    <p>Review the complete deterministic plan. Approval binds execution to the exact hash shown here.</p>
    <dl className="research-plan-facts">
      <dt>Plan hash</dt><dd className="mono">{planHash}</dd>
      <dt>Methodology build</dt><dd className="mono">{scalar(plan.methodology_build_id)}</dd>
      <dt>Brief digest</dt><dd className="mono">{scalar(plan.brief_digest)}</dd>
      <dt>Source set</dt><dd><span className="mono">{scalar(plan.source_set.id)}</span> · version {scalar(plan.source_set.version)}</dd>
      <dt>Upstream artifacts</dt><dd>{plan.upstream_artifacts.length ? <ul>{plan.upstream_artifacts.map((artifact, artifactIndex) => <li key={`upstream:${artifactIndex}`}><strong>{scalar(artifact.module_id)}</strong> · <span className="mono">{scalar(artifact.artifact_id)}</span> · <span className="mono">{scalar(artifact.digest)}</span></li>)}</ul> : <span className="muted">Empty</span>}</dd>
      <dt>Scope</dt><dd>Type {scalar(plan.scope.type)} · key <span className="mono">{scalar(plan.scope.key)}</span> · source mode {scalar(plan.scope.source_mode)}</dd>
    </dl>
    <h4>Workstreams</h4>
    {plan.workstreams.length ? <ol className="research-workstreams">{plan.workstreams.map((workstream, workstreamIndex) => <li key={`workstream:${workstreamIndex}`}>
      <h5>{scalar(workstream.id)} · {scalar(workstream.kind)}</h5>
      <dl className="research-plan-facts">
        <dt>ID</dt><dd className="mono">{scalar(workstream.id)}</dd>
        <dt>Kind</dt><dd>{scalar(workstream.kind)}</dd>
        <dt>Question</dt><dd>{scalar(workstream.question)}</dd>
        <dt>Assigned questions</dt><dd>{workstream.assigned_questions?.length ? <ul>{workstream.assigned_questions.map((item, index) => <li key={`assigned:${index}`}>{scalar(item)}</li>)}</ul> : <span className="muted">Empty</span>}</dd>
        <dt>Perspective</dt><dd>{scalar(workstream.perspective)}</dd>
        <dt>Hypothesis</dt><dd>{scalar(workstream.hypothesis)}</dd>
        <dt>Evidence needs</dt><dd>{workstream.evidence_needs.length ? <ul>{workstream.evidence_needs.map((item, index) => <li key={`evidence:${index}`}>{scalar(item)}</li>)}</ul> : <span className="muted">Empty</span>}</dd>
        <dt>Source classes</dt><dd>{workstream.source_classes.length ? <ul>{workstream.source_classes.map((item, index) => <li className="mono" key={`source:${index}`}>{scalar(item)}</li>)}</ul> : <span className="muted">Empty</span>}</dd>
        <dt>Disconfirming test</dt><dd>{scalar(workstream.disconfirming_test)}</dd>
        <dt>Completion test</dt><dd>{scalar(workstream.completion_test)}</dd>
        <dt>Effort cap</dt><dd>{scalar(workstream.effort_cap)}</dd>
      </dl>
    </li>)}</ol> : <p className="muted">Empty</p>}
    <button className="button primary" type="button" disabled={approving} onClick={() => onApprove(planHash)}>{approving ? "Approving…" : "Approve research plan"}</button>
  </section>;
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
  return <div className="grid deep-dive-layout">{question && <section className="context-strip span-12"><strong>Evidence request</strong><p>{question}</p></section>}<section className="panel span-8"><div className="panel-header"><h2>Accepted analysis</h2><span className="panel-meta">Visible authority</span></div><div className="panel-body flow">{snapshot ? <><div className="callout"><strong>Visible accepted snapshot</strong><br /><span className="mono">{snapshot.digest}</span><br /><span className="muted">Source set v{snapshot.source_set_version ?? "—"} · accepted {formatDate(snapshot.accepted_at)}</span></div><h3>Artifact register</h3><div className="table-wrap"><table><caption className="muted">Typed artifacts bound to this snapshot</caption><thead><tr><th scope="col">Module</th><th scope="col">Artifact digest</th><th scope="col">Evidence</th></tr></thead><tbody>{snapshot.artifacts.map((artifact) => <tr key={artifact.id}><td className="mono">{artifact.module_id}</td><td className="mono">{artifact.digest.slice(0, 16)}…</td><td><Link href={withQuery("/sources/", { case: selectedCase?.id, artifact: artifact.id })}>Open source rail</Link></td></tr>)}</tbody></table></div>{view?.switch_required && <div className="callout warning">A newer accepted execution exists. This view remains on the selected snapshot until you switch it explicitly.<div className="top-actions"><button className="button small" type="button" onClick={switchSnapshot}>Switch visible snapshot</button></div></div>}{message && <p className="muted" role="status">{message}</p>}</> : loading || loadError ? <LoadState loading={loading} error={loadError} /> : <ActionState title="Analysis unavailable" detail="No accepted snapshot. Run the selected route, inspect exceptions, then accept it explicitly." action="Open Run Console" href={withQuery("/run-console", { case: selectedCase?.id })} />}</div></section><section className="panel span-4 evidence-rail"><div className="panel-header"><h2>Evidence rail</h2></div><div className="panel-body flow">{snapshot ? <><p className="muted">Pinned to source set v{snapshot.source_set_version ?? "—"}, accepted {formatDate(snapshot.accepted_at)}.</p><ul className="evidence-rail-list">{snapshot.artifacts.map((artifact) => <li key={artifact.id}><Link href={withQuery("/sources/", { case: selectedCase?.id, artifact: artifact.id })}><span className="mono">{artifact.module_id}</span></Link><div className="muted mono">{artifact.digest.slice(0, 16)}…</div></li>)}</ul></> : <p className="muted">No accepted snapshot, so no evidence is bound yet.</p>}</div></section></div>;
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
  return <div className="grid command-layout">{question && <section className="context-strip span-12"><strong>Evidence request</strong><p>{question}</p></section>}<section className="panel command-changes"><div className="panel-header"><h2>What changed</h2><span className="panel-meta">Snapshot diff</span></div><div className="panel-body flow">{loading || loadError ? <LoadState loading={loading} error={loadError} /> : !snapshot?.accepted ? <ActionState title="Posture unavailable" detail="No accepted snapshot yet. Posture becomes reviewable after an explicit acceptance." action="Open Run Console" href={withQuery("/run-console", { case: caseId })} /> : diff?.changed ? <><div className="callout warning">Accepted snapshot differs from the latest accepted execution.</div><ul className="change-list">{diff.source_set_changed && <li>Source set changed.</li>}{(diff.added?.length ?? 0) > 0 && <li>{diff.added?.length} module{diff.added?.length === 1 ? "" : "s"} added.</li>}{(diff.modified?.length ?? 0) > 0 && <li>{diff.modified?.length} module{diff.modified?.length === 1 ? "" : "s"} modified.</li>}{(diff.removed?.length ?? 0) > 0 && <li>{diff.removed?.length} module{diff.removed?.length === 1 ? "" : "s"} removed.</li>}</ul></> : <div className="callout">No material change in the current accepted snapshot.</div>}</div></section><section className="panel command-lens"><div className="panel-header"><h2>Issuer lens</h2><span className="panel-meta">Case scoped</span></div><div className="panel-body flow">{loading || loadError ? <LoadState loading={loading} error={loadError} /> : <><h2>{lens?.issuer || "—"}</h2><p className="muted">{lens?.sector || "—"}</p><p className="mono">Snapshot: {lens?.accepted_snapshot_id || "none accepted"}</p><p className="mono">Source set: {lens?.source_set?.version ? `v${lens.source_set.version}` : "none"}</p></>}</div></section><section className="context-strip command-boundary"><strong>Analyst boundary</strong><p>No system recommendation is shown here. Instrument-specific recommendations are analyst-owned and versioned in Report Studio.</p></section></div>;
}

function ModelView({ caseId }: { caseId: string }) {
  const [model, setModel] = useState<{ status: string; reason: string } | null>(null); const [loading, setLoading] = useState(true); const [loadError, setLoadError] = useState(""); const [checkedAt, setCheckedAt] = useState("");
  // Model authority is external state; loading flags intentionally reset at the fetch boundary.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (!caseId) return; let ignore = false; setLoading(true); setLoadError(""); void request<typeof model>(`/api/cases/${caseId}/model`).then((next) => { if (!ignore) { setModel(next); setCheckedAt(new Date().toISOString()); } }).catch((caught) => { if (!ignore) setLoadError(caught instanceof Error ? caught.message : "Unable to load model authority"); }).finally(() => { if (!ignore) setLoading(false); }); return () => { ignore = true; }; }, [caseId]);
  return <div className="grid"><section className="panel span-12 model-workspace"><div className="panel-header"><h2>Methodology authority</h2><span className="status warning">Blocked</span></div><div className="panel-body flow readable">{loading || loadError ? <LoadState loading={loading} error={loadError} /> : <><div className="callout warning"><strong>Official CP-MODEL blocked</strong><br />{model?.reason || "Signed Deploy V authority correction required."}</div><dl className="state-facts"><dt>Owner</dt><dd>Methodology governance</dd><dt>Last checked</dt><dd>{formatDate(checkedAt)}</dd><dt>Available work</dt><dd>Review accepted analysis and source evidence; no provisional workbook is labelled official.</dd></dl><p>CAOS will not fabricate CP-2B, alias CP-2A, or label a provisional workbook as official. The model surface becomes available when the external authority gate is signed.</p><div className="row-actions"><Link className="button small" href={withQuery("/deep-dive", { case: caseId })}>Review accepted analysis</Link><button className="button small" type="button" onClick={() => window.location.reload()}>Check again</button></div></>}</div></section></div>;
}

function AdminView() {
  const [stepUp, setStepUp] = useState(""); const [bundle, setBundle] = useState<{ build_id: string; integrity: { checked: number; mismatches: number } } | null>(null); const [audit, setAudit] = useState<{ action: string; actor: string; at: string }[]>([]); const [message, setMessage] = useState(""); const [pending, setPending] = useState(false); const headers = { "x-oidc-step-up": stepUp };
  const load = async () => { setMessage(""); setPending(true); try { const [nextBundle, nextAudit] = await Promise.all([request<typeof bundle>("/api/admin/bundle", { headers }), request<typeof audit>("/api/admin/audit", { headers })]); setBundle(nextBundle); setAudit(nextAudit); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Admin verification failed"); } finally { setPending(false); } };
  return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Step-up</h2><span className="eyebrow">ADMIN ONLY</span></div><div className="panel-body"><form onSubmit={(event) => { event.preventDefault(); void load(); }}><div className="field"><label htmlFor="step-up">OIDC step-up token</label><input id="step-up" name="step-up" autoComplete="one-time-code" type="password" value={stepUp} onChange={(event) => setStepUp(event.target.value)} required /></div><button className="button primary" type="submit" disabled={pending}>{pending ? "Verifying…" : "Verify authority"}</button>{message && <p className="error" role="alert">{message}</p>}</form></div></section><section className="panel span-8"><div className="panel-header"><h2>Bundle integrity</h2><span className="eyebrow">DEPLOY V</span></div><div className="panel-body">{bundle ? <><p className="mono">Build {bundle.build_id}</p><p className="status success">{bundle.integrity.checked} files verified · {bundle.integrity.mismatches} mismatches</p></> : <div className="empty">Step up to inspect the signed methodology bundle and audit trail.</div>}</div></section><section className="panel span-12"><div className="panel-header"><h2>Audit trail</h2><span className="eyebrow">IMMUTABLE EVENTS</span></div><div className="panel-body table-wrap"><table><thead><tr><th scope="col">Time</th><th scope="col">Actor</th><th scope="col">Action</th></tr></thead><tbody>{audit.map((event, index) => <tr key={`${event.at}-${index}`}><td className="mono">{formatDate(event.at)}</td><td>{event.actor}</td><td className="mono">{event.action}</td></tr>)}</tbody></table>{!audit.length && <div className="empty">No audit events loaded.</div>}</div></section></div>;
}

function ReportView({ acceptedSnapshot, caseId, role, selectedCase }: { acceptedSnapshot: Snapshot | null; caseId: string; role: string; selectedCase: CaseRecord | null }) {
  type DraftState = Required<ReportDraft> & { dirty: boolean };
  const [report, setReport] = useState<{ id?: string; status: string; digest: string; preview_digest?: string; input_fingerprint?: string; snapshot_digest: string; markdown: string } | null>(null);
  const [versions, setVersions] = useState({ thesis: 0, recommendation: 0 });
  const [draft, setDraft] = useState<DraftState>({ thesis: "", instrument: "", recommendation: "MARKET WEIGHT", evidenceIds: "", dirty: false });
  const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [sources, setSources] = useState<SourceRecord[]>([]); const [evidenceError, setEvidenceError] = useState(""); const [evidenceQuery, setEvidenceQuery] = useState(""); const [loading, setLoading] = useState(true); const [pending, setPending] = useState(""); const [readyCaseId, setReadyCaseId] = useState("");
  const draftKey = `caos-report-draft:${caseId}`;
  const refresh = async () => {
    if (!caseId) { setLoading(false); return; }
    setLoading(true); setError(""); setEvidenceError("");
    try {
      const [nextReport, nextThesis, nextRecommendations, nextSources] = await Promise.all([
        request<typeof report>(`/api/cases/${caseId}/reports`),
        request<{ current?: { version: number; core_thesis: string; evidence_ids?: string[] } }>(`/api/cases/${caseId}/thesis`),
        request<{ current?: { version: number; rows: { instrument: string; recommendation: string; primary?: boolean }[] } }>(`/api/cases/${caseId}/recommendations`),
        request<SourceRecord[]>(`/api/cases/${caseId}/sources`).catch((caught) => {
          setEvidenceError(caught instanceof Error ? caught.message : "Unable to load evidence inventory");
          return [];
        }),
      ]);
      const primary = nextRecommendations.current?.rows.find((row) => row.primary) || nextRecommendations.current?.rows[0];
      const stored = window.sessionStorage.getItem(draftKey);
      let storedDraft: ReportDraft | null = null;
      if (stored) {
        try {
          const parsed: unknown = JSON.parse(stored);
          const fields = ["thesis", "instrument", "recommendation", "evidenceIds"] as const;
          if (parsed && typeof parsed === "object" && fields.every((field) => (parsed as Record<string, unknown>)[field] === undefined || typeof (parsed as Record<string, unknown>)[field] === "string")) storedDraft = parsed as ReportDraft;
          else window.sessionStorage.removeItem(draftKey);
        } catch { window.sessionStorage.removeItem(draftKey); }
      }
      setReport(nextReport); setSources(nextSources);
      setVersions({ thesis: nextThesis.current?.version ?? 0, recommendation: nextRecommendations.current?.version ?? 0 });
      setDraft({
        thesis: storedDraft?.thesis ?? nextThesis.current?.core_thesis ?? "",
        instrument: storedDraft?.instrument ?? primary?.instrument ?? "",
        recommendation: storedDraft?.recommendation ?? primary?.recommendation ?? "MARKET WEIGHT",
        evidenceIds: storedDraft?.evidenceIds ?? nextThesis.current?.evidence_ids?.join(", ") ?? "",
        dirty: Boolean(storedDraft),
      });
      setReadyCaseId(caseId);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load report workspace"); }
    finally { setLoading(false); }
  };
  // Draft loading synchronizes persisted browser state with the selected case.
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { setReadyCaseId(""); void refresh(); }, [caseId]);
  useEffect(() => { if (readyCaseId !== caseId || !draft.dirty) return; window.sessionStorage.setItem(draftKey, JSON.stringify({ thesis: draft.thesis, instrument: draft.instrument, recommendation: draft.recommendation, evidenceIds: draft.evidenceIds })); }, [caseId, draft, draftKey, readyCaseId]);
  useEffect(() => { if (!draft.dirty) return; const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [draft.dirty]);
  const updateDraft = (field: keyof ReportDraft, value: string) => setDraft((current) => ({ ...current, [field]: value, dirty: true }));
  const evidenceOptions = useMemo<EvidenceOption[]>(() => [
    ...(acceptedSnapshot ? [{ id: acceptedSnapshot.id, kind: "Snapshot" as const, label: `Accepted snapshot · ${acceptedSnapshot.digest.slice(0, 12)}…` }] : []),
    ...(acceptedSnapshot?.artifacts.map((artifact) => ({ id: artifact.id, kind: "Artifact" as const, label: `${artifact.module_id} · ${artifact.digest.slice(0, 12)}…` })) ?? []),
    ...sources.map((source) => ({ id: source.id, kind: "Source" as const, label: source.filename })),
  ], [acceptedSnapshot, sources]);
  const selectedEvidence = useMemo(() => new Set(evidenceIdsFrom(draft.evidenceIds)), [draft.evidenceIds]);
  const visibleEvidence = useMemo(() => { const query = evidenceQuery.toLowerCase(); return evidenceOptions.filter((option) => `${option.kind} ${option.label} ${option.id}`.toLowerCase().includes(query)); }, [evidenceOptions, evidenceQuery]);
  const toggleEvidence = (id: string) => setDraft((current) => { const ids = evidenceIdsFrom(current.evidenceIds); return { ...current, evidenceIds: (ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]).join(", "), dirty: true }; });
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setMessage(""); setError("");
    if (!acceptedSnapshot) { setError("Accept an analytical snapshot before freezing this report. Your draft is saved locally."); return; }
    const refs = evidenceIdsFrom(draft.evidenceIds);
    setPending("freeze");
    try {
      const saved = await request<{ thesis: { version: number }; recommendations: { version: number } }>(`/api/cases/${caseId}/report-inputs`, {
        method: "POST",
        body: JSON.stringify({
          thesis: { expected_version: versions.thesis, core_thesis: draft.thesis, drivers: [], risks: [], catalysts: [], unresolved_questions: [], evidence_ids: refs },
          recommendations: { expected_version: versions.recommendation, market_snapshot_id: "internal-market-latest", rows: [{ instrument_id: draft.instrument, instrument: draft.instrument, recommendation: draft.recommendation, rationale: "Analyst-owned recommendation pending committee review.", primary: true }], analytical_dependency_ids: [] },
        }),
      });
      setVersions({ thesis: saved.thesis.version, recommendation: saved.recommendations.version });
      await request(`/api/cases/${caseId}/reports/freeze`, { method: "POST", body: JSON.stringify({ thesis_version: saved.thesis.version, recommendation_version: saved.recommendations.version, include_model: false }) });
      window.sessionStorage.removeItem(draftKey);
      setDraft((current) => ({ ...current, dirty: false }));
      setMessage("Frozen report pending Approver ratification.");
      await refresh();
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : "Unable to freeze report";
      setError(detail.includes("SNAPSHOT_REQUIRED")
        ? "Accept an analytical snapshot before freezing this report. Your draft is saved locally."
        : detail.includes("EVIDENCE_CASE_MISMATCH")
          ? "One or more evidence IDs do not belong to this case."
          : detail.includes("EVIDENCE_SOURCE_WITHDRAWN")
            ? "Remove withdrawn sources before freezing this report."
            : detail);
    } finally { setPending(""); }
  };
  const approve = async () => { if (!report?.preview_digest || !report.input_fingerprint) return; setPending("approve"); setError(""); try { await request(`/api/cases/${caseId}/reports/approve`, { method: "POST", body: JSON.stringify({ expected_status: "PENDING_APPROVAL", preview_digest: report.preview_digest, input_fingerprint: report.input_fingerprint }) }); setMessage("Report approved; exports are available."); await refresh(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to approve report"); } finally { setPending(""); } };
  const busy = pending === "freeze";
  return <div className="report-studio">
    <section className="panel report-editor">
      <div className="panel-header"><h2>Compose</h2><span className="panel-meta">Analyst authority</span></div>
      <div className="panel-body report-editor-scroll">{loading || (error && readyCaseId !== caseId) ? <LoadState loading={loading} error={error} /> : <form className="flow" onSubmit={save}>
        <div className="field"><label htmlFor="thesis">Core thesis</label><textarea id="thesis" name="core-thesis" autoComplete="off" value={draft.thesis} onChange={(event) => updateDraft("thesis", event.target.value)} required disabled={busy} placeholder="State the defensible credit view…" /></div>
        <div className="field"><label htmlFor="instrument">Primary instrument</label><input id="instrument" name="instrument" autoComplete="off" value={draft.instrument} onChange={(event) => updateDraft("instrument", event.target.value)} required disabled={busy} placeholder="Issuer 1L 2029…" /></div>
        <div className="field"><label htmlFor="recommendation">Recommendation</label><select id="recommendation" name="recommendation" value={draft.recommendation} onChange={(event) => updateDraft("recommendation", event.target.value)} disabled={busy}><option>OVERWEIGHT</option><option>MARKET WEIGHT</option><option>UNDERWEIGHT</option><option>N/A</option></select></div>
        <fieldset className="evidence-picker">
          <legend>Case evidence</legend>
          <div className="field"><label htmlFor="evidence-search">Find evidence</label><input id="evidence-search" type="search" value={evidenceQuery} onChange={(event) => setEvidenceQuery(event.target.value)} placeholder="Search sources and accepted artifacts…" disabled={busy} /></div>
          <div className="evidence-options">{visibleEvidence.slice(0, 12).map((option) => <label className="evidence-option" key={option.id}><input type="checkbox" checked={selectedEvidence.has(option.id)} onChange={() => toggleEvidence(option.id)} disabled={busy} /><span><strong>{option.kind}</strong> {option.label}<span className="mono">{option.id}</span></span></label>)}</div>
          {!visibleEvidence.length && <p className="muted">No case-scoped evidence matches this search.</p>}
          {visibleEvidence.length > 12 && <p className="muted">Showing 12 of {visibleEvidence.length} matches. Narrow the search to attach another item.</p>}
        </fieldset>
        {evidenceError && <p className="error" role="alert">Evidence inventory unavailable: {evidenceError}</p>}
        <div className="field"><label htmlFor="evidence-ids">Evidence IDs</label><input id="evidence-ids" name="evidence-ids" autoComplete="off" value={draft.evidenceIds} onChange={(event) => updateDraft("evidenceIds", event.target.value)} placeholder="src_…, art_…, snapshot_…" disabled={busy} /><span className="muted">Paste case-scoped IDs or use the picker above.</span></div>
        {draft.dirty && <p className="status warning" role="status">Draft saved locally</p>}
        {!acceptedSnapshot && <ActionState title="Freeze unavailable" detail="Accept an analytical snapshot before freezing this report. Your draft remains available in this browser." action="Open Run Console" href={withQuery("/run-console", { case: caseId })} warning />}
        <div className="report-actions"><button className="button primary" type="submit" disabled={busy || !acceptedSnapshot}>{busy ? "Freezing…" : "Freeze report snapshot"}</button>{acceptedSnapshot ? <span className="muted">Server authority is checked again at freeze.</span> : <Link className="button small" href={withQuery("/run-console", { case: caseId })}>Accept a snapshot first</Link>}</div>
        {message && <p className="muted" role="status">{message}</p>}{error && <p className="error" role="alert">{error}</p>}
      </form>}</div>
    </section>
    <section className="report-proof-stage" aria-labelledby="paper-proof-title">
      <article className="paper report-paper">
        <header className="report-paper-header"><div><span className="paper-kicker">CAOS · filed proof</span><h2 id="paper-proof-title">{selectedCase ? `${selectedCase.issuer} — ${selectedCase.name}` : "Filed proof"}</h2></div>{report && <span className={`status ${report.status === "APPROVED" ? "success" : "warning"}`}>{report.status}</span>}</header>
        <div className="report-paper-body">{loading ? <LoadState loading /> : report ? <div className="flow"><p className="mono">{report.digest}</p><p className="muted mono">Snapshot {report.snapshot_digest}</p>{report.status === "PENDING_APPROVAL" && (role === "APPROVER" || role === "ADMIN") && <button className="button primary" type="button" onClick={approve} disabled={pending === "approve"}>{pending === "approve" ? "Approving…" : "Approve frozen report"}</button>}{report.status === "APPROVED" && <div className="proof-actions"><a className="button small" download href={`${apiBase}/api/cases/${caseId}/reports/export/md`}>Markdown</a><a className="button small" download href={`${apiBase}/api/cases/${caseId}/reports/export/pdf`}>PDF</a><a className="button small" download href={`${apiBase}/api/cases/${caseId}/reports/export/xlsx`}>XLSX</a></div>}<FiledProof markdown={report.markdown} /></div> : <div className="empty">No frozen report for this case.</div>}</div>
      </article>
    </section>
  </div>;
}
