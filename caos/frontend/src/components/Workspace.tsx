"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { FormEvent, ReactNode, useCallback, useEffect, useId, useMemo, useReducer, useRef, useState } from "react";
import EvidenceChip from "./EvidenceChip";
import ModelBuilder from "./model/ModelBuilder";
import ReportStudio from "./report/ReportStudio";
import { api as request, type ArtifactRecord, type CaseRecord, type LoanFinding, type LoanRow, type LoanUniverseResponse, type ResearchPlan, type RunRecord, type SourceRecord } from "../lib/api";
import { initialAuthorityState, matchesAuthority, requestContext, workspaceAuthorityReducer, type AuthorityEvent } from "../lib/workspaceAuthority";

import WorkbenchShell, { type DrawerState } from "./WorkbenchShell";
import { type Destination, type Snapshot, type SnapshotView, destinationFromSlug, routeDestinations, withQuery } from "../lib/workbench";

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
  const [authorityState, reducerDispatch] = useReducer(workspaceAuthorityReducer, initialAuthorityState);
  const authorityRef = useRef(initialAuthorityState);
  const dispatchAuthority = useCallback((event: AuthorityEvent) => {
    const next = workspaceAuthorityReducer(authorityRef.current, event);
    authorityRef.current = next;
    reducerDispatch(event);
    return next;
  }, []);
  const caseId = authorityState.caseId || "";
  const runId = authorityState.runId || "";
  const hydrated = authorityState.hydrated;
  const authorityStatus = authorityState.status;
  const [run, setRun] = useState<RunRecord | null>(null);
  const [casesLoading, setCasesLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState("");
  const [error, setError] = useState("");
  const [pendingAction, setPendingAction] = useState("");
  const [role, setRole] = useState("ANALYST");
  const [authority, setAuthority] = useState<SnapshotView | null>(null);
  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const casesRequest = useRef(0);
  const caseRefresh = useRef(0);
  const runRefresh = useRef(0);
  const runCreation = useRef(0);
  const routeAuthorityRef = useRef("");
  const modelDraftDirtyRef = useRef(false);
  const reportDraftDirtyRef = useRef(false);
  const modelHistoryGuardRef = useRef(false);
  const historyGuardRetiringRef = useRef(false);
  const historyGuardRearmRef = useRef(false);
  const suppressNextModelHistoryPopRef = useRef(false);
  const modelHistoryPopFenceTimerRef = useRef<number | null>(null);
  const selectedCase = useMemo(() => cases.find((item) => item.id === caseId) || null, [cases, caseId]);
  const caseIsAuthorized = selectedCase !== null;

  const armOwnedHistoryGuard = useCallback((marker: "model" | "report") => {
    if (typeof window === "undefined") return;
    if (historyGuardRetiringRef.current) {
      historyGuardRearmRef.current = true;
      return;
    }
    if (!modelHistoryGuardRef.current && !historyGuardRetiringRef.current) {
      window.history.pushState({ ...window.history.state, [marker === "model" ? "caosModelDraftGuard" : "caosReportDraftGuard"]: true }, "", window.location.href);
      modelHistoryGuardRef.current = true;
    }
  }, []);

  const retireOwnedHistoryGuard = useCallback(() => {
    if (typeof window === "undefined" || modelDraftDirtyRef.current || reportDraftDirtyRef.current || !modelHistoryGuardRef.current || historyGuardRetiringRef.current) return;
    modelHistoryGuardRef.current = false;
    historyGuardRetiringRef.current = true;
    historyGuardRearmRef.current = false;
    suppressNextModelHistoryPopRef.current = true;
    window.history.back();
    if (modelHistoryPopFenceTimerRef.current !== null) window.clearTimeout(modelHistoryPopFenceTimerRef.current);
    modelHistoryPopFenceTimerRef.current = window.setTimeout(() => {
      if (!historyGuardRetiringRef.current) return;
      historyGuardRetiringRef.current = false;
      suppressNextModelHistoryPopRef.current = false;
      modelHistoryGuardRef.current = true;
      historyGuardRearmRef.current = false;
      modelHistoryPopFenceTimerRef.current = null;
    }, 1000);
  }, []);

  const onModelDraftStateChange = useCallback((dirty: boolean) => {
    modelDraftDirtyRef.current = dirty;
    if (dirty) armOwnedHistoryGuard("model");
    else if (!modelDraftDirtyRef.current && !reportDraftDirtyRef.current) retireOwnedHistoryGuard();
  }, [armOwnedHistoryGuard, retireOwnedHistoryGuard]);

  const onReportDraftStateChange = useCallback((dirty: boolean) => {
    reportDraftDirtyRef.current = dirty;
    if (dirty) armOwnedHistoryGuard("report");
    else if (!modelDraftDirtyRef.current && !reportDraftDirtyRef.current) retireOwnedHistoryGuard();
  }, [armOwnedHistoryGuard, retireOwnedHistoryGuard]);

  const confirmModelDraftDiscard = useCallback((detail: string) => {
    if (!modelDraftDirtyRef.current) return true;
    if (!window.confirm(detail)) return false;
    modelDraftDirtyRef.current = false;
    if (!reportDraftDirtyRef.current) modelHistoryGuardRef.current = false;
    return true;
  }, []);

  const confirmReportDraftDiscard = useCallback((detail: string) => {
    if (!reportDraftDirtyRef.current) return true;
    if (!window.confirm(detail)) return false;
    reportDraftDirtyRef.current = false;
    if (!modelDraftDirtyRef.current) modelHistoryGuardRef.current = false;
    return true;
  }, []);

  const selectCase = useCallback((nextCaseId: string, availableCases = cases) => {
    const currentCaseId = authorityRef.current.caseId || "";
    if (nextCaseId === currentCaseId) return true;
    if (!confirmModelDraftDiscard("Discard the unsigned Model Builder Draft Revision before changing case?")) return false;
    if (!confirmReportDraftDiscard("Discard the unsaved Report Studio changes before changing case?")) return false;
    dispatchAuthority({ type: "selectCase", caseId: nextCaseId || null });
    const nextRunId = availableCases.find((item) => item.id === nextCaseId)?.current_execution_id || "";
    if (nextRunId) dispatchAuthority({ type: "selectRun", caseId: nextCaseId, runId: nextRunId });
    setRunLoading(false);
    setPendingAction("");
    setDrawer(null);
    setAuthority(null);
    setRun(null);
    setRunError("");
    setError("");
    return true;
  }, [cases, confirmModelDraftDiscard, confirmReportDraftDiscard, dispatchAuthority]);

  const refreshCases = async (signal?: AbortSignal) => {
    const requestId = ++casesRequest.current;
    const context = requestContext(authorityRef.current);
    setCasesLoading(true);
    try {
      const next = await request<CaseRecord[]>("/api/cases", {}, signal);
      if (requestId !== casesRequest.current || !matchesAuthority(authorityRef.current, context)) return;
      setCases(next);
      setCasesLoading(false);
      dispatchAuthority({ type: "requestSucceeded", context, scope: "cases" });
      const requestedCaseId = queryParam("case");
      const requestedRunId = queryParam("run");
      const requestedCase = next.find((item) => item.id === requestedCaseId);
      const currentCaseId = authorityRef.current.caseId || "";
      const resolvedCaseId = next.find((item) => item.id === currentCaseId)?.id || requestedCase?.id || next[0]?.id || "";
      if (resolvedCaseId !== currentCaseId) {
        if (requestedCaseId && !requestedCase) routeAuthorityRef.current = `${requestedCaseId}\u0000${requestedRunId}`;
        if (!selectCase(resolvedCaseId, next)) return;
        if (requestedRunId && (!requestedCaseId || requestedCase)) {
          dispatchAuthority({ type: "selectRun", caseId: resolvedCaseId, runId: requestedRunId });
        }
      }
      if (!authorityRef.current.runId && !requestedRunId) {
        const resolvedCase = next.find((item) => item.id === resolvedCaseId);
        if (resolvedCase?.current_execution_id) {
          dispatchAuthority({ type: "selectRun", caseId: resolvedCaseId, runId: resolvedCase.current_execution_id });
        }
      }
      if (authorityRef.current.caseId) dispatchAuthority({ type: "requestStarted", scope: "case" });
    } catch (caught) {
      if (requestId !== casesRequest.current || !matchesAuthority(authorityRef.current, context)) return;
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(caught instanceof Error ? caught.message : "Unable to load cases");
        setCasesLoading(false);
        dispatchAuthority({ type: "requestFailed", context, scope: "cases" });
      }
    }
  };

  const refreshCase = async (id = caseId, signal?: AbortSignal) => {
    const context = requestContext(authorityRef.current);
    if (!id || id !== context.caseId) return null;
    const requestId = ++caseRefresh.current;
    try {
      const [detail, snapshot] = await Promise.all([
        request<CaseRecord>(`/api/cases/${id}`, {}, signal),
        request<SnapshotView>(`/api/cases/${id}/snapshot`, {}, signal),
      ]);
      if (requestId !== caseRefresh.current || !matchesAuthority(authorityRef.current, context)) return null;
      setCases((previous) => previous.map((item) => item.id === id ? { ...item, ...detail } : item));
      setAuthority(snapshot);
      dispatchAuthority({ type: "requestSucceeded", context, scope: "case" });
      if (snapshot.accepted) dispatchAuthority({ type: "snapshotAccepted", context, snapshotId: snapshot.accepted.id });
      return snapshot;
    } catch (caught) {
      if (requestId !== caseRefresh.current || !matchesAuthority(authorityRef.current, context)) return null;
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(caught instanceof Error ? caught.message : "Unable to load case authority");
        dispatchAuthority({ type: "requestFailed", context, scope: "case" });
      }
      return null;
    }
  };

  const refreshRun = async (id = runId) => {
    if (!id) { setRun(null); setRunLoading(false); return; }
    const context = requestContext(authorityRef.current);
    if (id !== context.runId) return;
    const requestId = ++runRefresh.current;
    setRunLoading(true);
    setRunError("");
    try {
      const next = await request<RunRecord>(`/api/runs/${id}`);
      if (requestId !== runRefresh.current || !matchesAuthority(authorityRef.current, context)) return;
      if (next.case_id !== context.caseId) {
        setRun(null);
        setRunLoading(false);
        setRunError("Requested run does not belong to the selected case.");
        dispatchAuthority({ type: "requestFailed", context, scope: "run" });
        if (context.caseId) dispatchAuthority({ type: "invalidateRun", caseId: context.caseId, runId: id });
        return;
      }
      setRun(next);
      dispatchAuthority({ type: "requestSucceeded", context, scope: "run" });
    } catch (caught) {
      if (requestId !== runRefresh.current || !matchesAuthority(authorityRef.current, context)) return;
      const message = caught instanceof Error ? caught.message : "Unable to refresh run";
      setRunError(message);
      setError(message);
      dispatchAuthority({ type: "requestFailed", context, scope: "run" });
    } finally {
      if (requestId !== runRefresh.current || !matchesAuthority(authorityRef.current, context)) return;
      setRunLoading(false);
    }
  };

  useEffect(() => {
    // URL-derived state is hydrated after the server render to keep the shell deterministic.
    dispatchAuthority({ type: "hydrate", caseId: requestedCaseId || null, runId: requestedRunId || null });
    const controller = new AbortController();
    const guardDraftNavigation = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target.closest("a[href]") : null;
      const href = target?.getAttribute("href") || "";
      if (!target || !href.startsWith("/") || target.getAttribute("download") !== null) return;
      if (!confirmModelDraftDiscard("Discard the unsigned Model Builder Draft Revision and leave this page?")) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      if (!confirmReportDraftDiscard("Discard the unsaved Report Studio changes and leave this page?")) { event.preventDefault(); event.stopImmediatePropagation(); }
    };
    const guardBrowserHistory = (event: PopStateEvent) => {
      if (suppressNextModelHistoryPopRef.current) {
        suppressNextModelHistoryPopRef.current = false;
        if (modelHistoryPopFenceTimerRef.current !== null) window.clearTimeout(modelHistoryPopFenceTimerRef.current);
        modelHistoryPopFenceTimerRef.current = null;
        if (historyGuardRetiringRef.current) {
          historyGuardRetiringRef.current = false;
          const rearm = historyGuardRearmRef.current || modelDraftDirtyRef.current || reportDraftDirtyRef.current;
          historyGuardRearmRef.current = false;
          if (rearm) armOwnedHistoryGuard(modelDraftDirtyRef.current ? "model" : "report");
        }
        return;
      }
      if (!modelDraftDirtyRef.current && !reportDraftDirtyRef.current) return;
      event.stopImmediatePropagation();
      const label = modelDraftDirtyRef.current && reportDraftDirtyRef.current ? "Discard the unsigned Model Builder Draft Revision and unsaved Report Studio changes, then use browser history?" : modelDraftDirtyRef.current ? "Discard the unsigned Model Builder Draft Revision and use browser history?" : "Discard the unsaved Report Studio changes and use browser history?";
      if (window.confirm(label)) {
        modelDraftDirtyRef.current = false;
        reportDraftDirtyRef.current = false;
        modelHistoryGuardRef.current = false;
        window.history.back();
      } else if (modelHistoryGuardRef.current) {
        suppressNextModelHistoryPopRef.current = true;
        window.history.forward();
        modelHistoryPopFenceTimerRef.current = window.setTimeout(() => {
          suppressNextModelHistoryPopRef.current = false;
          modelHistoryPopFenceTimerRef.current = null;
        }, 1000);
      }
    };
    const guardUnload = (event: BeforeUnloadEvent) => {
      if (!modelDraftDirtyRef.current && !reportDraftDirtyRef.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    document.addEventListener("click", guardDraftNavigation, true);
    window.addEventListener("popstate", guardBrowserHistory, true);
    window.addEventListener("beforeunload", guardUnload);
    void request<{ role: string }>("/api/me", {}, controller.signal).then((who) => setRole(who.role)).catch((caught) => {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof Error ? caught.message : "Unable to load identity");
    });
    const timer = window.setTimeout(() => void refreshCases(controller.signal), 0);
    return () => { controller.abort(); window.clearTimeout(timer); if (modelHistoryPopFenceTimerRef.current !== null) window.clearTimeout(modelHistoryPopFenceTimerRef.current); suppressNextModelHistoryPopRef.current = false; historyGuardRetiringRef.current = false; historyGuardRearmRef.current = false; modelHistoryPopFenceTimerRef.current = null; document.removeEventListener("click", guardDraftNavigation, true); window.removeEventListener("popstate", guardBrowserHistory, true); window.removeEventListener("beforeunload", guardUnload); };
    // The selected case is intentionally not a fetch dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [armOwnedHistoryGuard, confirmModelDraftDiscard, confirmReportDraftDiscard]);

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
          dispatchAuthority({ type: "selectRun", caseId: authorizedCase.id, runId: requestedRunId });
        }
        routeAuthorityRef.current = routeAuthority;
        return;
      }
      // A workflow link may omit `run`; in that case the selected case keeps its
      // current execution. An explicit run query always wins for the same case.
      if (requestedRunId && requestedRunId !== runId) {
        setRun(null);
        dispatchAuthority({ type: "selectRun", caseId, runId: requestedRunId });
      }
      routeAuthorityRef.current = routeAuthority;
    }, 0);
    return () => window.clearTimeout(timer);
  }, [caseId, cases, casesLoading, dispatchAuthority, hydrated, requestedCaseId, requestedRunId, runId, selectCase]);

  useEffect(() => {
    // Visible case authority and its drawer must clear at every reducer authority generation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAuthority(null); setDrawer(null);
    if (!caseId || !caseIsAuthorized) return;
    const controller = new AbortController();
    void refreshCase(caseId, controller.signal);
    return () => controller.abort();
    // `refreshCase` deliberately resolves the current external authority.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorityState.generation, caseId, caseIsAuthorized]);

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
    const context = requestContext(authorityRef.current);
    setPendingAction("create-case");
    try {
      const created = await request<CaseRecord>("/api/cases", { method: "POST", body: JSON.stringify({ name: form.get("name"), issuer: form.get("issuer"), sector: form.get("sector") || "Unclassified" }) });
      if (!matchesAuthority(authorityRef.current, context)) return;
      casesRequest.current += 1;
      setCases((previous) => [created, ...previous]);
      dispatchAuthority({ type: "requestSucceeded", context, scope: "create-case" });
      setPendingAction("");
      selectCase(created.id); formElement.reset();
    } catch (caught) {
      if (!matchesAuthority(authorityRef.current, context)) return;
      setError(caught instanceof Error ? caught.message : "Unable to create case");
      dispatchAuthority({ type: "requestFailed", context, scope: "create-case" });
    } finally {
      if (matchesAuthority(authorityRef.current, context)) setPendingAction("");
    }
  };

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!caseId) return; setError("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const context = requestContext(authorityRef.current);
    setPendingAction("upload");
    try {
      await request(`/api/cases/${caseId}/sources`, { method: "POST", body: form });
      if (!matchesAuthority(authorityRef.current, context)) return;
      dispatchAuthority({ type: "requestSucceeded", context, scope: "upload" });
      await refreshCase(caseId);
      if (matchesAuthority(authorityRef.current, context)) formElement.reset();
    } catch (caught) {
      if (!matchesAuthority(authorityRef.current, context)) return;
      setError(caught instanceof Error ? caught.message : "Unable to upload source");
      dispatchAuthority({ type: "requestFailed", context, scope: "upload" });
    } finally {
      if (matchesAuthority(authorityRef.current, context)) setPendingAction("");
    }
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
    const context = requestContext(authorityRef.current);
    const expectedCaseId = context.caseId;
    if (!expectedCaseId) return;
    const requestId = ++runCreation.current;
    setPendingAction("start-run");
    try {
      const created = await request<RunRecord>(`/api/cases/${expectedCaseId}/runs`, { method: "POST", body: JSON.stringify({ pathway, depth, focus_questions: [], ...(researchBrief ? { research_brief: researchBrief } : {}) }) });
      if (requestId !== runCreation.current || !matchesAuthority(authorityRef.current, context)) return;
      if (created.case_id !== expectedCaseId) {
        const message = "Started run does not belong to the selected case.";
        setRunError(message);
        setError(message);
        dispatchAuthority({ type: "requestFailed", context, scope: "start-run" });
        return;
      }
      setRun(created);
      dispatchAuthority({ type: "requestSucceeded", context, scope: "start-run" });
      setPendingAction((current) => current === "start-run" ? "" : current);
      dispatchAuthority({ type: "selectRun", caseId: expectedCaseId, runId: created.id });
    } catch (caught) {
      if (requestId !== runCreation.current || !matchesAuthority(authorityRef.current, context)) return;
      setError(caught instanceof Error ? caught.message : "Unable to start run");
      dispatchAuthority({ type: "requestFailed", context, scope: "start-run" });
    } finally {
      if (requestId === runCreation.current && matchesAuthority(authorityRef.current, context)) setPendingAction((current) => current === "start-run" ? "" : current);
    }
  };

  const acceptRun = async () => {
    if (!runId || !run || run.id !== runId || run.case_id !== caseId) {
      setRunError("Only a run bound to the selected case can be accepted.");
      return;
    }
    if (!window.confirm("Accept this analytical snapshot as the visible authority for the case?")) return;
    const context = requestContext(authorityRef.current);
    setPendingAction("accept-run");
    try {
      const accepted = await request<Snapshot>(`/api/runs/${runId}/accept`, { method: "POST" });
      if (!matchesAuthority(authorityRef.current, context)) return;
      dispatchAuthority({ type: "snapshotAccepted", context, snapshotId: accepted.id });
      await refreshCase(caseId); await refreshRun(runId);
    } catch (caught) {
      if (!matchesAuthority(authorityRef.current, context)) return;
      setError(caught instanceof Error ? caught.message : "Unable to accept snapshot");
      dispatchAuthority({ type: "requestFailed", context, scope: "accept-run" });
    } finally {
      if (matchesAuthority(authorityRef.current, context)) setPendingAction("");
    }
  };

  const approveResearchPlan = async (planHash: string) => {
    if (!runId || !run || run.id !== runId || run.case_id !== caseId) return;
    const context = requestContext(authorityRef.current);
    const expectedCaseId = context.caseId;
    const expectedRunId = context.runId;
    if (!expectedCaseId || !expectedRunId) return;
    setError("");
    setPendingAction("approve-research-plan");
    try {
      await request(`/api/runs/${expectedRunId}/research-plan/approve`, { method: "POST", body: JSON.stringify({ plan_hash: planHash }) });
      if (!matchesAuthority(authorityRef.current, context)) return;
      dispatchAuthority({ type: "requestSucceeded", context, scope: "research-plan" });
      await refreshRun(expectedRunId);
    } catch (caught) {
      if (!matchesAuthority(authorityRef.current, context)) return;
      setError(caught instanceof Error ? caught.message : "Unable to approve research plan");
      dispatchAuthority({ type: "requestFailed", context, scope: "research-plan" });
    } finally {
      if (matchesAuthority(authorityRef.current, context)) setPendingAction((current) => current === "approve-research-plan" ? "" : current);
    }
  };

  const switchSnapshot = async (snapshotId: string) => {
    const context = requestContext(authorityRef.current);
    if (!context.caseId) return null;
    try {
      const switched = await request<Snapshot>(`/api/cases/${context.caseId}/snapshot/switch`, { method: "POST", body: JSON.stringify({ snapshot_id: snapshotId }) });
      if (!matchesAuthority(authorityRef.current, context)) return null;
      dispatchAuthority({ type: "snapshotAccepted", context, snapshotId: switched.id });
      return refreshCase(context.caseId);
    } catch (caught) {
      if (!matchesAuthority(authorityRef.current, context)) return null;
      dispatchAuthority({ type: "requestFailed", context, scope: "switch-snapshot" });
      throw caught;
    }
  };

  const renderDestination = () => {
    if (!selectedCase && active !== "Cases" && active !== "Admin Studio") return <EmptyState text="Create or select a case before entering an analytical workspace." action="Open Cases" href="/cases/" />;
    switch (active) {
      case "Cases": return <CasesView cases={cases} casesLoading={casesLoading} selectedCase={selectedCase} caseId={caseId} onCaseChange={selectCase} createCase={createCase} upload={upload} pendingAction={pendingAction} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} />;
      case "Sources": return <SourcesView selectedCase={selectedCase} artifactId={routeArtifactId} sourceId={routeSourceId} upload={upload} pendingAction={pendingAction} onOpenEvidence={(evidenceId, source) => setDrawer({ kind: "evidence", evidenceId, source })} />;
      case "Run Console": return <RunConsole caseId={caseId} selectedCase={selectedCase} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} approveResearchPlan={approveResearchPlan} pendingAction={pendingAction} />;
      case "Deep-Dive": return <DeepDive selectedCase={selectedCase} question={routeQuestion} caseId={caseId} pendingAction={pendingAction} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} onSwitchSnapshot={switchSnapshot} />;
      case "RV Screener": return <RVView key={caseId} caseId={caseId} />;
      case "Command Center": return <CommandView caseId={caseId} question={routeQuestion} />;
      case "Model Builder": return <ModelBuilder caseId={caseId} role={role} onDraftStateChange={onModelDraftStateChange} />;
      case "Report Studio": return <ReportStudio key={caseId} caseId={caseId} role={role} selectedCase={selectedCase} onDraftStateChange={onReportDraftStateChange} />;
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

function CasesView({ cases, casesLoading, selectedCase, caseId, onCaseChange, createCase, upload, pendingAction, run, runLoading, runError, startRun, acceptRun }: { cases: CaseRecord[]; casesLoading: boolean; selectedCase: CaseRecord | null; caseId: string; onCaseChange: (id: string) => void; createCase: (event: FormEvent<HTMLFormElement>) => void; upload: (event: FormEvent<HTMLFormElement>) => void; pendingAction: string; run: RunRecord | null; runLoading: boolean; runError: string; startRun: (event: FormEvent<HTMLFormElement>) => void; acceptRun: () => void }) {
  const [search, setSearch] = useState("");
  const [snapshotFilter, setSnapshotFilter] = useState<"all" | "accepted" | "unaccepted">("all");
  const visibleCases = useMemo(() => cases.filter((item) => {
    const matchesSearch = `${item.issuer} ${item.name} ${item.sector}`.toLowerCase().includes(search.trim().toLowerCase());
    const matchesFilter = snapshotFilter === "all"
      || (snapshotFilter === "accepted" ? Boolean(item.accepted_snapshot) : !item.accepted_snapshot);
    return matchesSearch && matchesFilter;
  }), [cases, search, snapshotFilter]);
  return <div className="grid cases-layout">
    <section className="panel cases-register"><div className="panel-header"><h2>Case register</h2><span className="panel-meta">{casesLoading ? "Loading…" : `${visibleCases.length} of ${cases.length}`}</span></div><div className="worklist-toolbar"><div className="field"><label htmlFor="case-search">Search cases</label><input id="case-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Issuer, case, or sector" /></div><div className="field"><label htmlFor="case-snapshot-filter">Snapshot</label><select id="case-snapshot-filter" value={snapshotFilter} onChange={(event) => setSnapshotFilter(event.target.value as "all" | "accepted" | "unaccepted")}><option value="all">All</option><option value="accepted">Accepted</option><option value="unaccepted">Not accepted</option></select></div></div><div className="panel-body table-wrap" tabIndex={0} role="region" aria-label="Scrollable table"><table><thead><tr><th scope="col">Issuer</th><th scope="col">Case</th><th scope="col">Sources</th><th scope="col">Snapshot</th><th scope="col">Actions</th></tr></thead><tbody>{visibleCases.map((item) => <tr key={item.id}><td>{item.issuer}</td><td>{item.name}<div className="muted">{item.sector}</div></td><td className="num">{item.source_count ?? "—"}</td><td>{item.accepted_snapshot ? <span className="status success">accepted</span> : <span className="status warning">not accepted</span>}</td><td><button className="button small" type="button" aria-pressed={caseId === item.id} onClick={() => onCaseChange(item.id)}>{caseId === item.id ? "Selected" : "Select"}</button></td></tr>)}</tbody></table>{!visibleCases.length && <LoadState loading={casesLoading} empty={cases.length ? "No cases match this search and filter." : "No cases yet. Create the first case to establish the context boundary."} />}</div></section>
    <section className="panel cases-create"><div className="panel-header"><h2>Create case</h2></div><div className="panel-body"><form onSubmit={createCase}><div className="field"><label htmlFor="case-name">Case name</label><input id="case-name" name="name" autoComplete="off" required placeholder="Q3 credit review…" /></div><div className="field"><label htmlFor="issuer">Issuer</label><input id="issuer" name="issuer" autoComplete="organization" required placeholder="Issuer legal name…" /></div><div className="field"><label htmlFor="sector">Sector</label><input id="sector" name="sector" autoComplete="off" placeholder="Business services…" /></div><button className={`button ${selectedCase ? "" : "primary"}`} type="submit" disabled={pendingAction === "create-case"}>{pendingAction === "create-case" ? "Creating…" : "Create case"}</button></form></div></section>
    <section className="panel cases-fit"><div className="panel-header"><h2>Pathway fit</h2></div><div className="panel-body">{selectedCase ? <><span className={`status ${selectedCase.pathway_fit?.fit === "READY" ? "success" : "warning"}`}>{selectedCase.pathway_fit?.fit || "NEEDS_SOURCE"}</span><p>{selectedCase.pathway_fit?.message || "Upload a source to see fit."}</p></> : <div className="empty">Select a case to inspect pathway fit.</div>}</div></section>
    <section className="panel cases-intake"><div className="panel-header"><h2>Source intake</h2><span className="panel-meta">Immutable · versioned</span></div><div className="panel-body">{selectedCase ? <><p className="muted">{selectedCase.issuer} / {selectedCase.name}</p><form onSubmit={upload}><div className="field"><label htmlFor="case-source">Source file</label><input id="case-source" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit" disabled={pendingAction === "upload"}>{pendingAction === "upload" ? "Uploading…" : "Upload and version source set"}</button></form></> : <div className="empty">Select a case before adding governed source material.</div>}</div></section>
    <InlineRun caseId={caseId} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} pendingAction={pendingAction} />
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
    <section className="panel span-8"><div className="panel-header"><h2>Source set</h2><span className="eyebrow">{loading ? "LOADING…" : `${sources.length} immutable objects`}</span></div><div className="panel-body table-wrap" tabIndex={0} role="region" aria-label="Scrollable table">{selectedEvidenceId && <div className="selection-strip" role="status"><span>Evidence {selectedEvidenceId}</span><button type="button" className="button small" onClick={() => setSelectedEvidenceId("")}>Clear</button></div>}{artifactError && !artifactId && <p className="error" role="alert">{artifactError}</p>}<table><thead><tr><th scope="col">File</th><th scope="col">SHA-256</th><th scope="col">Blocks</th></tr></thead><tbody>{sources.map((source) => <tr id={`source-${source.id}`} className={activeEvidenceId === source.id ? "evidence-match" : undefined} key={source.id}><td><div className="source-file"><details><summary>{source.filename}</summary><div className="source-blocks">{source.blocks.slice(0, 20).map((block) => <article className="source-block" id={`block-${source.id}-${block.block_id}`} key={block.block_id}><div className="eyebrow">{block.block_id} · {JSON.stringify(block.locator)}</div><p>{block.text || "No extracted text."}</p></article>)}{source.blocks.length > 20 && <p className="muted">Showing the first 20 blocks. Use the source object for the remaining {source.blocks.length - 20} blocks.</p>}</div></details>{evidenceRefs.includes(source.id) && <EvidenceChip evidenceId={source.id} linkedId={activeEvidenceId} onOpen={openEvidence} onPreview={setLinkedEvidenceId} onPreviewEnd={() => setLinkedEvidenceId("")} />}</div></td><td className="mono">{source.sha256.slice(0, 16)}…</td><td className="num">{source.blocks.length}</td></tr>)}</tbody></table>{!sources.length && <LoadState loading={loading} error={loadError} empty="No source objects in this case." />}{sources.length > 0 && loadError && <p className="error" role="alert">{loadError}</p>}</div></section>
    <section className="panel span-4"><div className="panel-header"><h2>Add source</h2><span className="eyebrow">BOUNDARY</span></div><div className="panel-body">{selectedCase ? <form onSubmit={upload}><div className="field"><label htmlFor="source-file">Source file</label><input id="source-file" name="file" type="file" accept=".pdf,.xlsx,.json,.txt,.md,.csv" required /></div><button className="button primary" type="submit" disabled={pendingAction === "upload"}>{pendingAction === "upload" ? "Uploading…" : "Ingest safely"}</button></form> : <div className="empty">Select a case.</div>}</div></section>
  </div>;
}

function RunStatusBadge({ run }: { run: RunRecord | null }) {
  return <span role="status" aria-live="polite" aria-atomic="true" className={run ? `status ${run.status === "succeeded" ? "success" : run.status === "failed" ? "critical" : "warning"}` : "sr-only"}>{run?.error?.code === "PLAN_APPROVAL_REQUIRED" ? "Pending approval" : run?.status || ""}</span>;
}

function RunForm({ caseId, startRun, pendingAction }: { caseId: string; startRun: (event: FormEvent<HTMLFormElement>) => void; pendingAction: string }) {
  const id = useId();
  return <form onSubmit={startRun}>
    <div className="field"><label htmlFor={`${id}-pathway`}>Purpose</label><select id={`${id}-pathway`} name="pathway" defaultValue="EARNINGS_UPDATE">{pathways.filter(([value]) => value !== "DEEP_RESEARCH").map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div>
    <div className="field"><label htmlFor={`${id}-depth`}>Depth</label><select id={`${id}-depth`} name="depth" defaultValue="screen"><option value="screen">Screen</option><option value="full">Full</option></select></div>
    <button className="button primary" type="submit" disabled={!caseId || pendingAction === "start-run"}>{pendingAction === "start-run" ? "Compiling…" : "Compile and run"}</button>
  </form>;
}

// Shared by Run Console and the inline panels on Cases and Deep-Dive. `approvalSlot`
// is how Run Console injects the full ResearchPlanView; inline surfaces route to it
// instead, since plan approval is a Run Console responsibility.
function RunStatus({ run, runLoading, runError, acceptRun, pendingAction, approvalSlot }: { run: RunRecord | null; runLoading: boolean; runError: string; acceptRun: () => void; pendingAction: string; approvalSlot: ReactNode }) {
  if (!run) return <LoadState loading={runLoading} error={runError} empty="No current execution. Select a purpose and depth to create an immutable plan." />;
  return <>
    <div className="dag">{run.nodes.map((node, index) => <div className="dag-step" key={node.id}>{index > 0 && <span className="dag-edge" aria-hidden="true">→</span>}<div className={`dag-node ${node.status}`}><strong>{node.module_id}</strong><div className="muted">{node.status}</div></div></div>)}</div>
    {run.status === "failed" && run.error && <p className="error" role="alert">{run.error.code ? `${run.error.code}: ` : ""}{run.error.message || "Run exception"}</p>}
    {run.status === "succeeded" && <button className="button primary" disabled={pendingAction === "accept-run"} onClick={acceptRun}>{pendingAction === "accept-run" ? "Accepting…" : "Accept analytical snapshot"}</button>}
    {run.status === "paused" && run.error?.code === "SOURCE_SET_EMPTY" && <div className="callout warning" role="status" aria-live="polite">Material exception: upload governed source material before execution.</div>}
    {run.status === "paused" && run.error?.code === "PLAN_APPROVAL_REQUIRED" && approvalSlot}
    {run.status === "paused" && !["SOURCE_SET_EMPTY", "PLAN_APPROVAL_REQUIRED"].includes(run.error?.code || "") && <div className="callout warning" role="status" aria-live="polite"><strong>{run.error?.code || "RUN_PAUSED"}</strong><p>{run.error?.message || "Run paused."}</p></div>}
  </>;
}

// Compile, watch and accept a route without leaving the analytical surface.
function InlineRun({ caseId, run, runLoading, runError, startRun, acceptRun, pendingAction }: { caseId: string; run: RunRecord | null; runLoading: boolean; runError: string; startRun: (event: FormEvent<HTMLFormElement>) => void; acceptRun: () => void; pendingAction: string }) {
  return <section className="panel span-12 inline-run" aria-label="Inline execution">
    <div className="panel-header inline-run-header"><h2>Inline execution</h2><div className="inline-run-actions"><RunStatusBadge run={run} /><Link className="button small" href={withQuery("/run-console", { case: caseId })}>Open Run Console</Link></div></div>
    <div className="panel-body inline-run-body">
      <div className="inline-run-form"><RunForm caseId={caseId} startRun={startRun} pendingAction={pendingAction} /></div>
      <div className="inline-run-status"><RunStatus run={run} runLoading={runLoading} runError={runError} acceptRun={acceptRun} pendingAction={pendingAction} approvalSlot={<div className="callout warning" role="status" aria-live="polite"><strong>Plan approval required</strong><p>Approve the bounded research plan in Run Console before this route can continue.</p></div>} /></div>
    </div>
  </section>;
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
      <div className="panel-header"><h2>Persisted DAG</h2><RunStatusBadge run={run} /></div>
      <div className="panel-body flow"><RunStatus run={run} runLoading={runLoading} runError={runError} acceptRun={acceptRun} pendingAction={pendingAction} approvalSlot={approvalPlan && approvalHash ? <ResearchPlanView plan={approvalPlan} planHash={approvalHash} approving={pendingAction === "approve-research-plan"} onApprove={approveResearchPlan} /> : <div className="callout warning" role="status" aria-live="polite"><strong>PLAN_APPROVAL_REQUIRED</strong><p>The persisted approval plan is unavailable; approval remains blocked.</p></div>} /></div>
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

function DeepDive({ selectedCase, question, caseId, pendingAction, run, runLoading, runError, startRun, acceptRun, onSwitchSnapshot }: { selectedCase: CaseRecord | null; question: string; caseId: string; pendingAction: string; run: RunRecord | null; runLoading: boolean; runError: string; startRun: (event: FormEvent<HTMLFormElement>) => void; acceptRun: () => void; onSwitchSnapshot: (snapshotId: string) => Promise<SnapshotView | null> }) {
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
      const next = await onSwitchSnapshot(view.latest_accepted.id);
      if (!next) return;
      setView(next);
      setMessage("Visible snapshot switched.");
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to switch snapshot"); }
  };
  const snapshot = view?.accepted || selectedCase?.accepted_snapshot;
  return <div className="grid deep-dive-layout">{question && <section className="context-strip span-12"><strong>Evidence request</strong><p>{question}</p></section>}<section className="panel span-8"><div className="panel-header"><h2>Accepted analysis</h2><span className="panel-meta">Visible authority</span></div><div className="panel-body flow">{snapshot ? <><div className="callout"><strong>Visible accepted snapshot</strong><br /><span className="mono">{snapshot.digest}</span><br /><span className="muted">Source set v{snapshot.source_set_version ?? "—"} · accepted {formatDate(snapshot.accepted_at)}</span></div><h3>Artifact register</h3><div className="table-wrap" tabIndex={0} role="region" aria-label="Scrollable table"><table><caption className="muted">Typed artifacts bound to this snapshot</caption><thead><tr><th scope="col">Module</th><th scope="col">Artifact digest</th><th scope="col">Evidence</th></tr></thead><tbody>{snapshot.artifacts.map((artifact) => <tr key={artifact.id}><td className="mono">{artifact.module_id}</td><td className="mono">{artifact.digest.slice(0, 16)}…</td><td><Link href={withQuery("/sources/", { case: selectedCase?.id, artifact: artifact.id })}>Open source rail</Link></td></tr>)}</tbody></table></div>{view?.switch_required && <div className="callout warning">A newer accepted execution exists. This view remains on the selected snapshot until you switch it explicitly.<div className="top-actions"><button className="button small" type="button" onClick={switchSnapshot}>Switch visible snapshot</button></div></div>}{message && <p className="muted" role="status">{message}</p>}</> : loading || loadError ? <LoadState loading={loading} error={loadError} /> : <ActionState title="Analysis unavailable" detail="No accepted snapshot. Run the selected route, inspect exceptions, then accept it explicitly." action="Open Run Console" href={withQuery("/run-console", { case: selectedCase?.id })} />}</div></section><section className="panel span-4 evidence-rail"><div className="panel-header"><h2>Evidence rail</h2></div><div className="panel-body flow">{snapshot ? <><p className="muted">Pinned to source set v{snapshot.source_set_version ?? "—"}, accepted {formatDate(snapshot.accepted_at)}.</p><ul className="evidence-rail-list">{snapshot.artifacts.map((artifact) => <li key={artifact.id}><Link href={withQuery("/sources/", { case: selectedCase?.id, artifact: artifact.id })}><span className="mono">{artifact.module_id}</span></Link><div className="muted mono">{artifact.digest.slice(0, 16)}…</div></li>)}</ul></> : <p className="muted">No accepted snapshot, so no evidence is bound yet.</p>}</div></section><InlineRun caseId={caseId} run={run} runLoading={runLoading} runError={runError} startRun={startRun} acceptRun={acceptRun} pendingAction={pendingAction} /></div>;
}

const loanColumns: { key: keyof LoanRow; label: string; numeric?: boolean; signed?: boolean }[] = [
  { key: "company", label: "Company" }, { key: "borrower_name", label: "Borrower" }, { key: "business_description", label: "Business description" }, { key: "sector", label: "Sector" }, { key: "sub_sector", label: "Sub-sector" }, { key: "sub_group", label: "Sub-group" }, { key: "public_private", label: "Public / private" },
  { key: "bloomberg_loan_id", label: "Bloomberg" }, { key: "figi", label: "FIGI" },
  { key: "loan_type", label: "Loan type" }, { key: "ranking", label: "Ranking" }, { key: "ratings", label: "Ratings" }, { key: "size_mn", label: "Size ($mn)", numeric: true }, { key: "margin_bps", label: "Margin (bps)", numeric: true }, { key: "maturity_date", label: "Maturity" },
  { key: "bid_points", label: "Bid (pts)", numeric: true }, { key: "ask_points", label: "Ask (pts)", numeric: true }, { key: "change_1d_points", label: "Δ 1D (pts)", numeric: true, signed: true }, { key: "change_1w_points", label: "Δ 1W (pts)", numeric: true, signed: true }, { key: "change_1m_points", label: "Δ 1M (pts)", numeric: true, signed: true }, { key: "change_3m_points", label: "Δ 3M (pts)", numeric: true, signed: true }, { key: "change_6m_points", label: "Δ 6M (pts)", numeric: true, signed: true }, { key: "change_1yr_points", label: "Δ 1YR (pts)", numeric: true, signed: true }, { key: "change_ytd_points", label: "Δ YTD (pts)", numeric: true, signed: true }, { key: "mid_ytm_pct", label: "Mid YTM (%)", numeric: true }, { key: "mid_3y_dm_bps", label: "Mid 3Y DM (bps)", numeric: true },
];
const LOAN_PAGE_SIZE = 250;

function loanCell(value: LoanRow[keyof LoanRow], signed = false) {
  if (value === null || value === undefined || value === "") return "N/A";
  if (typeof value !== "number") return String(value);
  const formatted = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
  return signed && value > 0 ? `+${formatted}` : formatted;
}

function RVView({ caseId }: { caseId: string }) {
  const [rv, setRv] = useState<LoanUniverseResponse | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [findings, setFindings] = useState<LoanFinding[]>([]);
  const [pending, setPending] = useState(false);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState("");
  const [rating, setRating] = useState("");
  const [ranking, setRanking] = useState("");
  const [loanType, setLoanType] = useState("");
  const [maturityFrom, setMaturityFrom] = useState("");
  const [maturityTo, setMaturityTo] = useState("");
  const [marginMin, setMarginMin] = useState("");
  const [marginMax, setMarginMax] = useState("");
  const [dmMin, setDmMin] = useState("");
  const [dmMax, setDmMax] = useState("");
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ key: keyof LoanRow; direction: "asc" | "desc" }>({ key: "borrower_name", direction: "asc" });
  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!caseId) return;
    setLoading(true); setLoadError("");
    try { setRv(await request<LoanUniverseResponse>(`/api/cases/${caseId}/rv/loan-universes/active`, {}, signal)); }
    catch (caught) { if (!(caught instanceof DOMException && caught.name === "AbortError")) setLoadError(caught instanceof Error ? caught.message : "Unable to load loan universe"); }
    finally { if (!signal?.aborted) setLoading(false); }
  }, [caseId]);
  // The active universe is case-scoped external state.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setRv(null); setMessage(""); setFindings([]); const controller = new AbortController(); void refresh(controller.signal); return () => controller.abort(); }, [refresh]);
  const filterOptions = useMemo(() => {
    const values = (key: "sector" | "ratings" | "ranking" | "loan_type") => [...new Set((rv?.rows || []).map((row) => row[key]).filter((value): value is string => Boolean(value)))].sort();
    return { sector: values("sector"), ratings: values("ratings"), ranking: values("ranking"), loan_type: values("loan_type") };
  }, [rv]);
  const filteredRows = useMemo(() => {
    const inRange = (value: number | null, minimum: string, maximum: string) => value !== null && (!minimum || value >= Number(minimum)) && (!maximum || value <= Number(maximum));
    const query = search.trim().toLowerCase();
    return (rv?.rows || []).filter((row) =>
      (!query || [row.company, row.borrower_name, row.bloomberg_loan_id, row.figi].some((value) => value?.toLowerCase().includes(query)))
      && (!sector || row.sector === sector) && (!rating || row.ratings === rating) && (!ranking || row.ranking === ranking) && (!loanType || row.loan_type === loanType)
      && (!maturityFrom || Boolean(row.maturity_date && row.maturity_date >= maturityFrom)) && (!maturityTo || Boolean(row.maturity_date && row.maturity_date <= maturityTo))
      && (!marginMin && !marginMax || inRange(row.margin_bps, marginMin, marginMax)) && (!dmMin && !dmMax || inRange(row.mid_3y_dm_bps, dmMin, dmMax))
    ).sort((left, right) => {
      const a = left[sort.key]; const b = right[sort.key];
      if (a === b) return left.instrument_key.localeCompare(right.instrument_key);
      if (a === null || a === undefined) return 1;
      if (b === null || b === undefined) return -1;
      const order = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), undefined, { numeric: true });
      return sort.direction === "asc" ? order : -order;
    });
  }, [rv, search, sector, rating, ranking, loanType, maturityFrom, maturityTo, marginMin, marginMax, dmMin, dmMax, sort]);
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / LOAN_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageRows = filteredRows.slice(currentPage * LOAN_PAGE_SIZE, (currentPage + 1) * LOAN_PAGE_SIZE);
  // Filters and ordering define a new result set, so return to its first page.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setPage(0); }, [search, sector, rating, ranking, loanType, maturityFrom, maturityTo, marginMin, marginMax, dmMin, dmMax, sort]);
  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    setPending(true); setMessage("Uploading and scanning workbook…"); setFindings([]);
    try {
      const form = new FormData(); form.append("file", file);
      const source = await request<SourceRecord>(`/api/cases/${caseId}/sources`, { method: "POST", body: form });
      setMessage("Validating the fixed CP-3 workbook…");
      const response = await fetch(`/api/cases/${caseId}/rv/loan-universes`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_id: source.id }) });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail || {};
        setFindings(Array.isArray(detail.findings) ? detail.findings : []);
        throw new Error(detail.message || `Workbook import failed (${response.status})`);
      }
      setMessage(`Active loan universe v${body.version} · ${body.row_count} instruments.`); setFile(null);
      await refresh();
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Unable to import workbook"); }
    finally { setPending(false); }
  };
  const changeSort = (key: keyof LoanRow) => setSort((current) => ({ key, direction: current.key === key && current.direction === "asc" ? "desc" : "asc" }));
  const messageIsError = Boolean(message && !pending && !message.startsWith("Active loan universe"));
  return <div className="grid loan-rv">
    <section className="panel span-12"><div className="panel-header"><h2>Leveraged-loan universe</h2><span className="eyebrow">SOURCE DATA · UNANALYZED</span></div><div className="panel-body loan-upload"><form onSubmit={upload}><div className="field"><label htmlFor="loan-workbook">Fixed CP-3 sector workbook (.xlsx)</label><input id="loan-workbook" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></div><button className="button primary" type="submit" disabled={pending || !file}>{pending ? "Importing…" : "Upload CP-3 workbook"}</button></form><p className="muted">All visible sector tabs are ingested. Values remain in workbook units: prices and changes in points, margin and discount margin in bps, yield in percent.</p>{message && <p className={messageIsError ? "error" : "muted"} role={messageIsError ? "alert" : "status"}>{message}</p>}{findings.length ? <ul className="loan-findings" role="alert">{findings.map((finding, index) => <li key={`${finding.code}-${index}`}><strong>{finding.code}</strong> {finding.sheet ? `${finding.sheet}${finding.row ? ` R${finding.row}` : ""}: ` : ""}{finding.detail}</li>)}</ul> : null}</div></section>
    {rv?.universe ? <section className="panel span-12"><div className="panel-header"><h2>Active authority</h2><span className="status success">ACTIVE · v{rv.universe.version}</span></div><div className="panel-body loan-authority"><dl><dt>Workbook date</dt><dd>{rv.universe.workbook_date || "N/A"}</dd><dt>Source</dt><dd><Link href={withQuery("/sources/", { case: caseId, source: rv.universe.source_id })}>{rv.universe.source_filename}</Link></dd><dt>Instruments</dt><dd className="num">{rv.universe.row_count}</dd><dt>Template</dt><dd className="mono">{rv.universe.template_version}</dd><dt>Digest</dt><dd className="mono">{rv.universe.universe_digest}</dd></dl></div></section> : null}
    <section className="panel span-12"><div className="panel-header"><h2>Loan screener</h2><span className="panel-meta">{filteredRows.length} / {rv?.rows.length || 0} instruments</span></div><div className="panel-body loan-filters"><div className="field"><label htmlFor="loan-search">Issuer / ID</label><input id="loan-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></div>{[["loan-sector", "Sector", sector, setSector, filterOptions.sector], ["loan-rating", "Rating", rating, setRating, filterOptions.ratings], ["loan-ranking", "Ranking", ranking, setRanking, filterOptions.ranking], ["loan-type", "Loan type", loanType, setLoanType, filterOptions.loan_type]] .map(([id, label, value, setter, values]) => <div className="field" key={id as string}><label htmlFor={id as string}>{label as string}</label><select id={id as string} value={value as string} onChange={(event) => (setter as (value: string) => void)(event.target.value)}><option value="">All</option>{(values as string[]).map((option) => <option key={option}>{option}</option>)}</select></div>)}<div className="field"><label htmlFor="loan-maturity-from">Maturity from</label><input id="loan-maturity-from" type="date" value={maturityFrom} onChange={(event) => setMaturityFrom(event.target.value)} /></div><div className="field"><label htmlFor="loan-maturity-to">Maturity to</label><input id="loan-maturity-to" type="date" value={maturityTo} onChange={(event) => setMaturityTo(event.target.value)} /></div>{[["loan-margin-min", "Min margin (bps)", marginMin, setMarginMin], ["loan-margin-max", "Max margin (bps)", marginMax, setMarginMax], ["loan-dm-min", "Min 3Y DM (bps)", dmMin, setDmMin], ["loan-dm-max", "Max 3Y DM (bps)", dmMax, setDmMax]].map(([id, label, value, setter]) => <div className="field" key={id as string}><label htmlFor={id as string}>{label as string}</label><input id={id as string} type="number" step="any" value={value as string} onChange={(event) => (setter as (value: string) => void)(event.target.value)} /></div>)}</div><div className="table-wrap loan-table-wrap" tabIndex={0} role="region" aria-label="Leveraged-loan screener; scroll horizontally to review all workbook fields">{rv?.rows.length ? <table className="loan-table"><caption className="sr-only">Active leveraged-loan universe. Column labels state the source unit.</caption><thead><tr className="loan-groups"><th scope="colgroup" colSpan={7}>Issuer profile</th><th scope="colgroup" colSpan={2}>Identifiers</th><th scope="colgroup" colSpan={6}>Loan terms</th><th scope="colgroup" colSpan={11}>Market data</th><th scope="colgroup" colSpan={1}>Source</th></tr><tr>{loanColumns.map((column) => <th scope="col" key={column.key} aria-sort={sort.key === column.key ? (sort.direction === "asc" ? "ascending" : "descending") : undefined}><button className="loan-sort" type="button" onClick={() => changeSort(column.key)}>{column.label}{sort.key === column.key ? (sort.direction === "asc" ? " ↑" : " ↓") : ""}</button></th>)}<th scope="col">Locator</th></tr></thead><tbody>{pageRows.map((row) => <tr key={row.instrument_key}>{loanColumns.map((column) => { const value = row[column.key]; const change = column.signed && typeof value === "number" ? value > 0 ? "positive" : value < 0 ? "negative" : "flat" : ""; return <td key={column.key} className={`${column.numeric ? "num" : ""} ${change}`.trim()}>{loanCell(value, column.signed)}</td>; })}<td className="mono">{row.source_locators.map((locator) => `${locator.sheet} R${locator.row}`).join("; ")}</td></tr>)}</tbody></table> : <LoadState loading={loading} error={loadError} empty="Upload the fixed CP-3 workbook to activate a leveraged-loan universe." />}{rv?.rows.length && !filteredRows.length ? <div className="empty">No loans match the current filters.</div> : null}</div>{filteredRows.length > LOAN_PAGE_SIZE ? <nav className="loan-pagination" aria-label="Loan screener pages"><button className="button small" type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span className="mono">Page {currentPage + 1} of {pageCount}</span><button className="button small" type="button" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Next</button></nav> : null}</section>
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

function AdminView() {
  const [stepUp, setStepUp] = useState(""); const [bundle, setBundle] = useState<{ build_id: string; integrity: { checked: number; mismatches: number } } | null>(null); const [audit, setAudit] = useState<{ action: string; actor: string; at: string }[]>([]); const [message, setMessage] = useState(""); const [pending, setPending] = useState(false); const headers = { "x-oidc-step-up": stepUp };
  const load = async () => { setMessage(""); setPending(true); try { const [nextBundle, nextAudit] = await Promise.all([request<typeof bundle>("/api/admin/bundle", { headers }), request<typeof audit>("/api/admin/audit", { headers })]); setBundle(nextBundle); setAudit(nextAudit); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Admin verification failed"); } finally { setPending(false); } };
  return <div className="grid"><section className="panel span-4"><div className="panel-header"><h2>Step-up</h2><span className="eyebrow">ADMIN ONLY</span></div><div className="panel-body"><form onSubmit={(event) => { event.preventDefault(); void load(); }}><div className="field"><label htmlFor="step-up">OIDC step-up token</label><input id="step-up" name="step-up" autoComplete="one-time-code" type="password" value={stepUp} onChange={(event) => setStepUp(event.target.value)} required /></div><button className="button primary" type="submit" disabled={pending}>{pending ? "Verifying…" : "Verify authority"}</button>{message && <p className="error" role="alert">{message}</p>}</form></div></section><section className="panel span-8"><div className="panel-header"><h2>Bundle integrity</h2><span className="eyebrow">DEPLOY V</span></div><div className="panel-body">{bundle ? <><p className="mono">Build {bundle.build_id}</p><p className="status success">{bundle.integrity.checked} files verified · {bundle.integrity.mismatches} mismatches</p></> : <div className="empty">Step up to inspect the signed methodology bundle and audit trail.</div>}</div></section><section className="panel span-12"><div className="panel-header"><h2>Audit trail</h2><span className="eyebrow">IMMUTABLE EVENTS</span></div><div className="panel-body table-wrap" tabIndex={0} role="region" aria-label="Scrollable table"><table><thead><tr><th scope="col">Time</th><th scope="col">Actor</th><th scope="col">Action</th></tr></thead><tbody>{audit.map((event, index) => <tr key={`${event.at}-${index}`}><td className="mono">{formatDate(event.at)}</td><td>{event.actor}</td><td className="mono">{event.action}</td></tr>)}</tbody></table>{!audit.length && <div className="empty">No audit events loaded.</div>}</div></section></div>;
}
