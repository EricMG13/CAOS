"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api as request, assumptionRegistryPath, type CaseRecord, type SourceRecord } from "../../lib/api";
import DeliverableDocument, {
  type DeliverableBlock,
  type EvidenceCitation,
  type FrozenPayload,
  type NarrativeBlock,
  type TemplateBlock,
} from "./DeliverableDocument";

const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
const AUTOSAVE_DELAY_MS = 850;
const pathwayOptions = [
  ["FULL_CREDIT", "Full Credit"],
  ["EARNINGS_UPDATE", "Earnings Update"],
  ["COVENANT_REFINANCING", "Covenant & Refinancing"],
  ["RELATIVE_VALUE", "Relative Value"],
  ["DISTRESSED_RESTRUCTURING", "Distressed & Restructuring"],
  ["DEEP_RESEARCH", "Deep Research"],
] as const;

type Pathway = typeof pathwayOptions[number][0];
type OptionalPolicy = { kind: DeliverableBlock["kind"]; slot_stem: string; max_items: number; order: number; model_dependent: boolean };
type DeliverableTemplate = { template_id: string; template_version: string; pathway: Pathway; title: string; model_requirement: "REQUIRED" | "OPTIONAL"; allowed_appendices: string[]; optional_blocks: OptionalPolicy[]; blocks: TemplateBlock[] };
type ModelSelection = { kind: "ANALYST_REVISION"; build_id: string; revision_id: string } | { kind: "APPLICATION_BUILD"; build_id: string; fallback_acknowledged: true };
type ModelEligibility = {
  active_revision: { revision_id: string; build_id: string; revision_number: number; signed_by: string; signed_at: string } | null;
  application_build: { build_id: string; accepted_snapshot_id: string; input_fingerprint: string; payload_digest: string; status: "READY" } | null;
  fallback_acknowledgement_required: boolean;
  default_model_selection: ModelSelection | null;
};
type DraftRevision = { id: string; case_id: string; pathway: Pathway; version: number; author: string; created_at: string; template_id: string; template_version: string; digest: string; content: { template_id: string; template_version: string; model_selection: ModelSelection | null; model_identity?: Record<string, unknown> | null; blocks: DeliverableBlock[]; generated_blocks: Record<string, unknown> } };
type ExportMetadata = { format: "md" | "pdf" | "xlsx"; sha256: string; size: number };
type FrozenDeliverable = { id: string; case_id: string; pathway: Pathway; draft_version: number; status: "FROZEN" | "FILED" | "SUPERSEDED" | "CHANGES_REQUESTED"; frozen_by: string; frozen_at: string; approved_by: string | null; approved_at: string | null; superseded_by_id: string | null; change_request: { comment?: string; requested_by?: string; requested_at?: string } | null; digest: string; preview_digest: string; input_fingerprint: string; payload: FrozenPayload; exports: Partial<Record<"md" | "pdf" | "xlsx", ExportMetadata>> };
type WorkspaceResponse = { template: DeliverableTemplate; current: DraftRevision | null; history: DraftRevision[]; frozen_history: FrozenDeliverable[]; model_eligibility: ModelEligibility };
type SaveState = { kind: "IDLE" | "INCOMPLETE" | "DIRTY" | "SAVING" | "SAVED" | "CONFLICT" | "ERROR"; detail?: string; version?: number };
type RegistryResponse = {
  version: string;
  digest: string;
  build_id: string;
  definitions: { assumption_id: string; label?: string }[];
  defaults: { assumption_id: string; case: "BASE" | "DOWNSIDE"; period_id: string; status: string }[];
};
type ScenarioResponse = { draft_generation: number; scenario: Record<string, unknown>; scenario_digest: string };
type LifecycleToken = { caseId: string; pathway: Pathway; scope: string; generation: number };

class ReportRequestError extends Error {
  constructor(readonly status: number, readonly detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
  }
}

async function reportRequest<T>(path: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...options, signal, headers: { "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ReportRequestError(response.status, body?.detail ?? body);
  return body as T;
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function aggregateCitations(blocks: DeliverableBlock[]): EvidenceCitation[] {
  const seen = new Set<string>();
  return blocks.flatMap((block) => "citations" in block ? block.citations : []).filter((citation) => {
    const key = `${citation.source_id}\u0000${citation.block_ids.join("\u0000")}\u0000${citation.claim}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function initializeBlocks(template: DeliverableTemplate): DeliverableBlock[] {
  return template.blocks.map((block) => block.kind === "EVIDENCE_REGISTER"
    ? { kind: "EVIDENCE_REGISTER", block_id: block.block_id, slot_id: block.slot_id, citations: [] }
    : { kind: "NARRATIVE", block_id: block.block_id, slot_id: block.slot_id, text: "", content_mode: "ANALYST_JUDGMENT", citations: [] }) as DeliverableBlock[];
}

function blocksForSave(blocks: DeliverableBlock[]): DeliverableBlock[] {
  const citations = aggregateCitations(blocks.filter((block) => block.kind !== "EVIDENCE_REGISTER"));
  return blocks.map((block) => block.kind === "EVIDENCE_REGISTER" ? { ...block, citations } : block);
}

function draftIsValid(blocks: DeliverableBlock[], template: DeliverableTemplate): boolean {
  const required = new Map(template.blocks.map((block) => [block.block_id, block]));
  return blocks.every((block) => {
    if (block.kind === "NARRATIVE") return Boolean(block.text.trim()) && (block.content_mode === "ANALYST_JUDGMENT" || block.citations.length > 0);
    if (block.kind === "LIMITATIONS") return Boolean(block.text.trim());
    return true;
  }) && [...required].every(([id, definition]) => blocks.some((block) => block.block_id === id && block.kind === definition.kind));
}

function modelSelectionIsCurrent(selection: ModelSelection | null, eligibility: ModelEligibility): boolean {
  if (!selection) return true;
  if (selection.kind === "ANALYST_REVISION") return selection.revision_id === eligibility.active_revision?.revision_id && selection.build_id === eligibility.active_revision?.build_id;
  return eligibility.active_revision === null && selection.build_id === eligibility.application_build?.build_id;
}

function optionalBlock(policy: OptionalPolicy, index: number): DeliverableBlock {
  const identity = { block_id: `${policy.slot_stem}.${index.toString().padStart(2, "0")}`, slot_id: `${policy.slot_stem}.${index.toString().padStart(2, "0")}` };
  if (policy.kind === "GENERATED_METRIC") return { ...identity, kind: "GENERATED_METRIC", metric_ids: ["total_leverage", "accessible_liquidity"] };
  if (policy.kind === "GENERATED_TABLE") return { ...identity, kind: "GENERATED_TABLE", table_id: "annual_model", field_ids: ["revenue", "adjusted_ebitda_calc", "fcf", "total_leverage"] };
  if (policy.kind === "GENERATED_CHART") return { ...identity, kind: "GENERATED_CHART", recipe: { kind: "scenario_path", schema_version: "1.0", fields: ["total_leverage"], units: "x", metric_ids: ["total_leverage"], polarity: "higher_is_worse", accessible_table: true } };
  if (policy.kind === "MODEL_APPENDIX") return { ...identity, kind: "MODEL_APPENDIX" };
  return { ...identity, kind: "LIMITATIONS", text: "Limitations and unavailable authority.", citations: [] };
}

function saveLabel(state: SaveState): string {
  if (state.kind === "SAVING") return "Saving";
  if (state.kind === "SAVED") return `Saved v${state.version}`;
  if (state.kind === "CONFLICT") return "Conflict";
  if (state.kind === "INCOMPLETE") return "Complete required sections to autosave";
  if (state.kind === "ERROR") return state.detail || "Save failed";
  return state.kind === "DIRTY" ? "Unsaved changes" : "Ready";
}

export default function ReportStudio({ caseId, role, selectedCase, onDraftStateChange }: { caseId: string; role: string; selectedCase: CaseRecord | null; onDraftStateChange: (dirty: boolean) => void }) {
  const [pathway, setPathway] = useState<Pathway>("FULL_CREDIT");
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);
  const [blocks, setBlocks] = useState<DeliverableBlock[]>([]);
  const [modelSelection, setModelSelection] = useState<ModelSelection | null>(null);
  const [selectedBlockId, setSelectedBlockId] = useState("");
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [evidenceError, setEvidenceError] = useState("");
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>({ kind: "IDLE" });
  const [draftIsUnsaved, setDraftIsUnsaved] = useState(false);
  const [persistedVersion, setPersistedVersion] = useState(0);
  const [conflict, setConflict] = useState<DraftRevision | null>(null);
  const [selectedFrozen, setSelectedFrozen] = useState<FrozenDeliverable | null>(null);
  const [pending, setPending] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [changeComment, setChangeComment] = useState("");
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [scenarioForm, setScenarioForm] = useState({ assumptionId: "", case: "BASE", periodId: "", value: "" });
  const loadGeneration = useRef(0);
  const draftGeneration = useRef(0);
  const saveGeneration = useRef(0);
  const savedVersion = useRef(0);
  const unsavedDraft = useRef(false);
  const saveTimer = useRef<number | null>(null);
  const saveChain = useRef<Promise<void>>(Promise.resolve());
  const editorFocus = useRef<HTMLTextAreaElement | null>(null);
  const currentScope = useRef("");
  const lifecycleGeneration = useRef(0);
  const lifecycleInFlight = useRef(false);
  const canWrite = role !== "READER";
  const canApprove = role === "APPROVER" || role === "ADMIN";
  const pathwayLabel = pathwayOptions.find(([id]) => id === pathway)?.[1] || pathway;

  const lifecycleIsCurrent = useCallback((token: LifecycleToken) => (
    token.generation === lifecycleGeneration.current
    && token.scope === currentScope.current
  ), []);

  const beginLifecycle = useCallback((operation: string): LifecycleToken | null => {
    const scope = `${caseId}\u0000${pathway}`;
    if (lifecycleInFlight.current || currentScope.current !== scope) return null;
    const token = { caseId, pathway, scope, generation: ++lifecycleGeneration.current };
    lifecycleInFlight.current = true;
    setPending(operation);
    setError("");
    return token;
  }, [caseId, pathway]);

  const finishLifecycle = useCallback((token: LifecycleToken) => {
    if (!lifecycleIsCurrent(token)) return;
    lifecycleInFlight.current = false;
    setPending("");
  }, [lifecycleIsCurrent]);

  const invalidateLifecycle = useCallback((nextScope: string) => {
    lifecycleGeneration.current += 1;
    lifecycleInFlight.current = false;
    currentScope.current = nextScope;
    setPending("");
  }, []);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!caseId) return;
    const generation = ++loadGeneration.current;
    const scope = `${caseId}\u0000${pathway}`;
    currentScope.current = scope;
    setLoading(true); setLoadError(""); setError(""); setMessage(""); setSelectedFrozen(null); setConflict(null);
    try {
      const [next, sourceResult] = await Promise.all([
        reportRequest<WorkspaceResponse>(`/api/cases/${caseId}/deliverables/${pathway}`, {}, signal),
        request<SourceRecord[]>(`/api/cases/${caseId}/sources`, {}, signal).then((value) => ({ value, error: "" })).catch((caught) => ({ value: [], error: caught instanceof Error ? caught.message : "Evidence inventory unavailable" })),
      ]);
      if (generation !== loadGeneration.current || currentScope.current !== scope) return;
      const nextBlocks = next.current?.content.blocks || initializeBlocks(next.template);
      savedVersion.current = next.current?.version || 0;
      unsavedDraft.current = false;
      setDraftIsUnsaved(false);
      setPersistedVersion(savedVersion.current);
      const nextModelSelection = next.current?.content.model_selection || next.model_eligibility.default_model_selection;
      setWorkspace(next); setBlocks(nextBlocks); setModelSelection(nextModelSelection); setSelectedBlockId(nextBlocks[0]?.block_id || ""); setSources(sourceResult.value); setEvidenceError(sourceResult.error); setSaveState(next.current ? { kind: "SAVED", version: next.current.version } : { kind: "IDLE" });
      const buildId = nextModelSelection?.build_id;
      if (buildId) {
        void request<RegistryResponse>(assumptionRegistryPath(caseId, buildId), {}, signal).then((value) => {
          if (generation !== loadGeneration.current || currentScope.current !== scope) return;
          if (value.build_id !== buildId) throw new Error("Scenario registry identity does not match the selected model build.");
          const scenarioDefault = value.defaults.find((row) => row.case === "BASE" && row.status === "READY") || value.defaults.find((row) => row.status === "READY");
          setRegistry(value);
          setScenarioForm({
            assumptionId: scenarioDefault?.assumption_id || value.definitions[0]?.assumption_id || "",
            case: scenarioDefault?.case || "BASE",
            periodId: scenarioDefault?.period_id || "",
            value: "",
          });
        }).catch((caught) => {
          if (generation !== loadGeneration.current || currentScope.current !== scope) return;
          setRegistry(null);
          setError(caught instanceof Error ? caught.message : "Scenario registry unavailable");
        });
      } else setRegistry(null);
      onDraftStateChange(false);
    } catch (caught) {
      if (generation !== loadGeneration.current || caught instanceof DOMException && caught.name === "AbortError") return;
      setLoadError(caught instanceof Error ? caught.message : "Unable to load Report Studio");
    } finally { if (generation === loadGeneration.current) setLoading(false); }
  }, [caseId, onDraftStateChange, pathway]);

  useEffect(() => {
    loadGeneration.current += 1; draftGeneration.current = 0; saveGeneration.current = 0; savedVersion.current = 0; unsavedDraft.current = false; saveChain.current = Promise.resolve();
    lifecycleGeneration.current += 1; lifecycleInFlight.current = false; currentScope.current = `${caseId}\u0000${pathway}`;
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => { controller.abort(); window.clearTimeout(timer); loadGeneration.current += 1; lifecycleGeneration.current += 1; lifecycleInFlight.current = false; if (saveTimer.current !== null) window.clearTimeout(saveTimer.current); };
  }, [caseId, load, pathway]);

  const enqueueSave = useCallback((snapshot: DeliverableBlock[], selection: ModelSelection | null, generation: number, scope: string) => {
    if (!workspace || !canWrite || scope !== currentScope.current) return;
    const prepared = blocksForSave(snapshot);
    if (!draftIsValid(prepared, workspace.template)) { setSaveState({ kind: "INCOMPLETE" }); return; }
    setSaveState({ kind: "SAVING" });
    saveChain.current = saveChain.current.then(async () => {
      if (scope !== currentScope.current || generation > saveGeneration.current) return;
      try {
        const next = await reportRequest<WorkspaceResponse>(`/api/cases/${caseId}/deliverables/${pathway}/draft`, { method: "PUT", body: JSON.stringify({ expected_version: savedVersion.current, template_id: workspace.template.template_id, template_version: workspace.template.template_version, model_selection: selection, blocks: prepared }) });
        if (scope !== currentScope.current) return;
        savedVersion.current = next.current?.version || savedVersion.current;
        setPersistedVersion(savedVersion.current);
        setWorkspace(next); setConflict(null);
        if (generation === saveGeneration.current) { unsavedDraft.current = false; setDraftIsUnsaved(false); setBlocks(next.current?.content.blocks || prepared); setSaveState({ kind: "SAVED", version: savedVersion.current }); onDraftStateChange(false); }
      } catch (caught) {
        if (scope !== currentScope.current) return;
        if (caught instanceof ReportRequestError && caught.status === 409 && typeof caught.detail === "object" && caught.detail) {
          const detail = caught.detail as { code?: string; current?: DraftRevision | null };
          if (detail.code === "DELIVERABLE_VERSION_CONFLICT") { setConflict(detail.current || null); setSaveState({ kind: "CONFLICT", detail: "A newer shared revision is available." }); return; }
        }
        setSaveState({ kind: "ERROR", detail: caught instanceof Error ? caught.message : "Autosave failed" });
      }
    });
  }, [canWrite, caseId, onDraftStateChange, pathway, workspace]);

  const markChanged = useCallback((nextBlocks: DeliverableBlock[], nextSelection = modelSelection) => {
    setBlocks(nextBlocks); setModelSelection(nextSelection); setSelectedFrozen(null); setMessage(""); setError(""); setConflict(null);
    const generation = ++draftGeneration.current;
    saveGeneration.current = generation;
    unsavedDraft.current = true;
    setDraftIsUnsaved(true);
    setSaveState({ kind: "DIRTY" }); onDraftStateChange(true);
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
    const scope = currentScope.current;
    saveTimer.current = window.setTimeout(() => enqueueSave(nextBlocks, nextSelection, generation, scope), AUTOSAVE_DELAY_MS);
  }, [enqueueSave, modelSelection, onDraftStateChange]);

  const updateNarrative = (blockId: string, patch: Partial<NarrativeBlock>) => markChanged(blocks.map((block) => block.block_id === blockId && block.kind === "NARRATIVE" ? { ...block, ...patch } : block));
  const selectedBlock = blocks.find((block) => block.block_id === selectedBlockId) || null;
  const visibleSources = useMemo(() => { const query = evidenceQuery.trim().toLowerCase(); return sources.filter((source) => `${source.filename} ${source.id}`.toLowerCase().includes(query)); }, [evidenceQuery, sources]);
  const scenarioPeriods = [...new Set(registry?.defaults.filter((row) => row.status === "READY" && row.assumption_id === scenarioForm.assumptionId && row.case === scenarioForm.case).map((row) => row.period_id) || [])].sort();

  const cite = (source: SourceRecord, blockId: string) => {
    if (selectedBlock?.kind !== "NARRATIVE" && selectedBlock?.kind !== "LIMITATIONS") return;
    const citation = { source_id: source.id, block_ids: [blockId], claim: selectedBlock.kind === "NARRATIVE" ? selectedBlock.text.slice(0, 1000) || "Evidence supporting this section." : "Evidence supporting this limitation." };
    markChanged(blocks.map((block) => block.block_id === selectedBlock.block_id && "citations" in block ? { ...block, citations: [...block.citations.filter((item) => !(item.source_id === source.id && item.block_ids.includes(blockId))), citation] } : block));
  };

  const removeCitation = (sourceId: string, blockId: string) => {
    if (!selectedBlock || !("citations" in selectedBlock)) return;
    markChanged(blocks.map((block) => block.block_id === selectedBlock.block_id && "citations" in block ? { ...block, citations: block.citations.filter((item) => !(item.source_id === sourceId && item.block_ids.includes(blockId))) } : block));
  };

  const addOptional = (policy: OptionalPolicy) => {
    const count = blocks.filter((block) => block.kind === policy.kind).length + 1;
    if (count > policy.max_items || policy.kind === "SCENARIO_EXHIBIT") return;
    markChanged([...blocks, optionalBlock(policy, count)].sort((left, right) => {
      const leftOrder = workspace?.template.optional_blocks.find((item) => item.kind === left.kind)?.order || 0;
      const rightOrder = workspace?.template.optional_blocks.find((item) => item.kind === right.kind)?.order || 0;
      return leftOrder - rightOrder;
    }));
  };

  const removeOptional = (blockId: string) => {
    if (workspace?.template.blocks.some((block) => block.block_id === blockId)) return;
    const remaining = blocks.filter((block) => block.block_id !== blockId);
    const counts = new Map<string, number>();
    markChanged(remaining.map((block) => {
      const policy = workspace?.template.optional_blocks.find((item) => item.kind === block.kind);
      if (!policy) return block;
      const index = (counts.get(block.kind) || 0) + 1; counts.set(block.kind, index);
      return { ...block, block_id: `${policy.slot_stem}.${index.toString().padStart(2, "0")}`, slot_id: `${policy.slot_stem}.${index.toString().padStart(2, "0")}` } as DeliverableBlock;
    }));
  };

  const chooseModel = (kind: "ACTIVE" | "FALLBACK" | "NONE") => {
    if (!workspace) return;
    let selection: ModelSelection | null = null;
    if (kind === "ACTIVE" && workspace.model_eligibility.active_revision) selection = { kind: "ANALYST_REVISION", build_id: workspace.model_eligibility.active_revision.build_id, revision_id: workspace.model_eligibility.active_revision.revision_id };
    if (kind === "FALLBACK" && workspace.model_eligibility.application_build) selection = { kind: "APPLICATION_BUILD", build_id: workspace.model_eligibility.application_build.build_id, fallback_acknowledged: true };
    markChanged(blocks, selection);
  };

  const insertScenario = async () => {
    if (!workspace || !registry || !modelSelection || !scenarioForm.assumptionId || !scenarioForm.value) return;
    const numeric = Number(scenarioForm.value);
    if (!Number.isFinite(numeric)) { setError("Scenario value must be finite."); return; }
    const token = beginLifecycle("scenario");
    if (!token) return;
    const generation = ++draftGeneration.current;
    try {
      const shocks = [{ assumption_id: scenarioForm.assumptionId, case: scenarioForm.case, period_id: scenarioForm.periodId, value: numeric }];
      const next = await reportRequest<ScenarioResponse>(`/api/cases/${caseId}/models/scenarios`, { method: "POST", body: JSON.stringify({ build_id: modelSelection.build_id, base_revision_id: modelSelection.kind === "ANALYST_REVISION" ? modelSelection.revision_id : null, registry_version: registry.version, registry_digest: registry.digest, shocks, draft_generation: generation }) });
      if (!lifecycleIsCurrent(token) || generation !== draftGeneration.current || next.draft_generation !== generation) return;
      const policy = workspace.template.optional_blocks.find((item) => item.kind === "SCENARIO_EXHIBIT");
      if (!policy) return;
      const index = blocks.filter((block) => block.kind === "SCENARIO_EXHIBIT").length + 1;
      markChanged([...blocks, { kind: "SCENARIO_EXHIBIT", block_id: `${policy.slot_stem}.${index.toString().padStart(2, "0")}`, slot_id: `${policy.slot_stem}.${index.toString().padStart(2, "0")}`, title: `Scenario · ${scenarioForm.assumptionId}`, shocks, scenario: next.scenario, scenario_digest: next.scenario_digest }]);
      setMessage("Server-calculated Scenario Exhibit inserted into the Draft.");
    } catch (caught) { if (lifecycleIsCurrent(token)) setError(caught instanceof Error ? caught.message : "Scenario calculation failed"); }
    finally { finishLifecycle(token); }
  };

  const restoreRevision = async (revision: DraftRevision) => {
    if (!workspace || !canWrite || unsavedDraft.current || saveState.kind !== "SAVED") return;
    const token = beginLifecycle("restore");
    if (!token) return;
    try {
      const next = await reportRequest<WorkspaceResponse>(`/api/cases/${caseId}/deliverables/${pathway}/draft`, { method: "PUT", body: JSON.stringify({ expected_version: workspace.current?.version || 0, template_id: workspace.template.template_id, template_version: workspace.template.template_version, model_selection: revision.content.model_selection, blocks: revision.content.blocks }) });
      if (!lifecycleIsCurrent(token)) return;
      savedVersion.current = next.current?.version || savedVersion.current; unsavedDraft.current = false; setDraftIsUnsaved(false); setPersistedVersion(savedVersion.current); setWorkspace(next); setBlocks(next.current?.content.blocks || revision.content.blocks); setModelSelection(next.current?.content.model_selection || null); setSelectedFrozen(null); setSaveState({ kind: "SAVED", version: savedVersion.current }); onDraftStateChange(false); setMessage(`Restored v${revision.version} as new revision v${savedVersion.current}.`); editorFocus.current?.focus();
    } catch (caught) { if (lifecycleIsCurrent(token)) setError(caught instanceof Error ? caught.message : "Unable to restore revision"); }
    finally { finishLifecycle(token); }
  };

  const freeze = async () => {
    const current = workspace?.current;
    if (!current || unsavedDraft.current || saveState.kind !== "SAVED" || current.version !== savedVersion.current || !modelSelectionIsCurrent(modelSelection, workspace.model_eligibility)) return;
    const token = beginLifecycle("freeze");
    if (!token) return;
    try {
      const frozen = await reportRequest<FrozenDeliverable>(`/api/cases/${caseId}/deliverables/${pathway}/freeze`, { method: "POST", body: JSON.stringify({ draft_id: current.id, draft_version: current.version, draft_digest: current.digest }) });
      if (!lifecycleIsCurrent(token)) return;
      setWorkspace((value) => value ? { ...value, frozen_history: [...value.frozen_history.filter((item) => item.id !== frozen.id), frozen] } : value);
      setSelectedFrozen(frozen); setMessage(`Frozen exact Draft v${current.version}.`);
    } catch (caught) { if (lifecycleIsCurrent(token)) setError(caught instanceof Error ? caught.message : "Unable to freeze Deliverable"); }
    finally { finishLifecycle(token); }
  };

  const fileFrozen = async () => {
    if (!selectedFrozen || !canApprove) return;
    const token = beginLifecycle("file");
    if (!token) return;
    try {
      const filed = await reportRequest<FrozenDeliverable>(`/api/cases/${caseId}/deliverables/by-id/${selectedFrozen.id}/approve`, { method: "POST", body: JSON.stringify({ preview_digest: selectedFrozen.preview_digest, input_fingerprint: selectedFrozen.input_fingerprint }) });
      if (!lifecycleIsCurrent(token)) return;
      setSelectedFrozen(filed); setWorkspace((current) => current ? { ...current, frozen_history: current.frozen_history.map((item) => item.id === filed.id ? filed : item.status === "FILED" ? { ...item, status: "SUPERSEDED", superseded_by_id: filed.id } : item) } : current); setMessage("Exact Frozen Deliverable filed.");
    } catch (caught) { if (lifecycleIsCurrent(token)) setError(caught instanceof Error ? caught.message : "Unable to file Deliverable"); }
    finally { finishLifecycle(token); }
  };

  const requestChanges = async () => {
    if (!selectedFrozen || !canApprove || !changeComment.trim()) return;
    const token = beginLifecycle("changes");
    if (!token) return;
    try {
      const next = await reportRequest<{ frozen: FrozenDeliverable; draft: DraftRevision }>(`/api/cases/${caseId}/deliverables/by-id/${selectedFrozen.id}/request-changes`, { method: "POST", body: JSON.stringify({ preview_digest: selectedFrozen.preview_digest, input_fingerprint: selectedFrozen.input_fingerprint, comment: changeComment.trim() }) });
      if (!lifecycleIsCurrent(token)) return;
      savedVersion.current = next.draft.version; unsavedDraft.current = false; setDraftIsUnsaved(false); setPersistedVersion(next.draft.version); setSelectedFrozen(null); setBlocks(next.draft.content.blocks); setModelSelection(next.draft.content.model_selection); setWorkspace((current) => current ? { ...current, current: next.draft, history: [...current.history, next.draft], frozen_history: current.frozen_history.map((item) => item.id === next.frozen.id ? next.frozen : item) } : current); setSaveState({ kind: "SAVED", version: next.draft.version }); setChangeComment(""); setMessage(`Changes requested; editable Draft v${next.draft.version} created.`); onDraftStateChange(false); window.setTimeout(() => { if (lifecycleIsCurrent(token)) editorFocus.current?.focus(); }, 0);
    } catch (caught) { if (lifecycleIsCurrent(token)) setError(caught instanceof Error ? caught.message : "Unable to request changes"); }
    finally { finishLifecycle(token); }
  };

  const switchPathway = (next: Pathway) => {
    if (next === pathway) return;
    if ((unsavedDraft.current || ["DIRTY", "SAVING", "INCOMPLETE", "ERROR"].includes(saveState.kind)) && !window.confirm("Discard the unsaved Report Studio changes and change pathway?")) return;
    invalidateLifecycle(`${caseId}\u0000${next}`);
    onDraftStateChange(false); setPathway(next);
  };

  if (loading || loadError || !workspace) return <div className="panel"><div className="panel-body">{loading ? <div className="state-skeleton" role="status" aria-live="polite" aria-label="Loading"><span /><span /><span /></div> : <div className="empty error-state" role="alert"><strong>Unable to load Report Studio.</strong><p>{loadError}</p><button className="button small" type="button" onClick={() => void load()}>Retry</button></div>}</div></div>;

  const frozenBlocks = selectedFrozen?.payload.content.blocks || [];
  const previewBlocks = selectedFrozen ? frozenBlocks : blocksForSave(blocks);
  const previewGenerated = selectedFrozen?.payload.content.generated_blocks || workspace.current?.content.generated_blocks || {};
  const modelStale = !modelSelectionIsCurrent(modelSelection, workspace.model_eligibility);
  const requiredModelMissing = workspace.template.model_requirement === "REQUIRED" && modelSelection === null;
  const freezeReady = canWrite && Boolean(workspace.current) && !draftIsUnsaved && saveState.kind === "SAVED" && workspace.current?.version === persistedVersion && !modelStale && !requiredModelMissing;
  const lifecycleBusy = pending !== "";
  const authoringLocked = lifecycleBusy;
  const selectedNarrative = selectedBlock?.kind === "NARRATIVE" ? selectedBlock : null;

  return <div className="report-studio report-studio-structured">
    <aside className="panel report-outline" aria-label="Deliverable composition">
      <div className="panel-header"><h2>Structure</h2><span className="panel-meta">{workspace.template.template_version}</span></div>
      <div className="panel-body report-rail-scroll">
        <div className="field"><label htmlFor="report-pathway">Pathway template</label><select id="report-pathway" value={pathway} onChange={(event) => switchPathway(event.target.value as Pathway)}>{pathwayOptions.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></div>
        <nav className="report-section-nav" aria-label="Deliverable sections">{blocks.map((block, index) => <button key={block.block_id} type="button" className={selectedBlockId === block.block_id ? "is-active" : ""} aria-current={selectedBlockId === block.block_id ? "true" : undefined} onClick={() => setSelectedBlockId(block.block_id)}><span>{(index + 1).toString().padStart(2, "0")}</span>{workspace.template.blocks.find((item) => item.block_id === block.block_id)?.title || (block.kind === "SCENARIO_EXHIBIT" ? block.title : block.kind.replaceAll("_", " "))}<small>{workspace.template.blocks.some((item) => item.block_id === block.block_id) ? "Required" : "Optional"}</small></button>)}</nav>
        <div className="report-optional"><h3>Optional composition</h3>{workspace.template.optional_blocks.map((policy) => <button className="button small" type="button" key={policy.kind} onClick={() => addOptional(policy)} disabled={!canWrite || authoringLocked || policy.kind === "SCENARIO_EXHIBIT" || policy.model_dependent && !modelSelection || blocks.filter((block) => block.kind === policy.kind).length >= policy.max_items}>Add {policy.kind.replaceAll("_", " ").toLowerCase()}</button>)}</div>
        <div className="report-history"><h3>Draft revisions</h3>{[...workspace.history].reverse().map((revision) => <div className="history-entry" key={revision.id}><strong>v{revision.version}</strong><span>{revision.author} · {formatDate(revision.created_at)}</span><button className="button small" type="button" onClick={() => void restoreRevision(revision)} disabled={!canWrite || lifecycleBusy || draftIsUnsaved || saveState.kind !== "SAVED"}>Restore as new revision</button></div>)}<h3>Frozen / Filed</h3>{[...workspace.frozen_history].reverse().map((item) => <button className="history-entry history-button" type="button" key={item.id} onClick={() => setSelectedFrozen(item)} disabled={lifecycleBusy}><strong>{item.status} · Draft v{item.draft_version}</strong><span>{item.frozen_by} · {formatDate(item.frozen_at)}</span></button>)}</div>
      </div>
    </aside>

    <section className="panel report-compose" aria-labelledby="report-compose-title">
      <div className="panel-header"><h2 id="report-compose-title">Compose</h2><span className={`status ${saveState.kind === "SAVED" ? "success" : saveState.kind === "CONFLICT" || saveState.kind === "ERROR" ? "critical" : "warning"}`} aria-live="polite">{saveLabel(saveState)}</span></div>
      <div className="panel-body report-editor-scroll">
        {selectedFrozen ? <div className="flow"><p className="status warning">Immutable {selectedFrozen.status} review · Draft v{selectedFrozen.draft_version}</p><button className="button small" type="button" onClick={() => setSelectedFrozen(null)} disabled={lifecycleBusy}>Return to shared Draft</button>{selectedFrozen.status === "FROZEN" && canApprove ? <div className="approval-panel"><button className="button primary" type="button" onClick={() => void fileFrozen()} disabled={lifecycleBusy}>{pending === "file" ? "Filing…" : "File exact Frozen version"}</button><div className="field"><label htmlFor="change-request-comment">Required comment to request changes</label><textarea id="change-request-comment" value={changeComment} maxLength={2000} onChange={(event) => setChangeComment(event.target.value)} disabled={lifecycleBusy} /></div><button className="button" type="button" onClick={() => void requestChanges()} disabled={!changeComment.trim() || lifecycleBusy}>{pending === "changes" ? "Creating new Draft…" : "Request changes"}</button></div> : null}{["FILED", "SUPERSEDED"].includes(selectedFrozen.status) ? <div className="proof-actions">{(["md", "pdf", "xlsx"] as const).map((format) => <a className="button small" key={format} download href={`${apiBase}/api/cases/${caseId}/deliverables/by-id/${selectedFrozen.id}/export/${format}`}>{format.toUpperCase()}</a>)}</div> : <p className="muted">Downloads unlock only after independent filing.</p>}</div> : <>
          <div className="report-authority-strip"><div><span>Model authority</span><strong>{modelSelection?.kind === "ANALYST_REVISION" ? `Active Revision ${workspace.model_eligibility.active_revision?.revision_number || ""}` : modelSelection?.kind === "APPLICATION_BUILD" ? "Application Model Build · acknowledged fallback" : "No model selected"}</strong></div>{modelStale ? <span className="status critical">Stale model identity</span> : null}</div>
          <fieldset className="report-model-picker"><legend>Deliverable model</legend>{workspace.model_eligibility.active_revision ? <label><input type="radio" name="report-model" checked={modelSelection?.kind === "ANALYST_REVISION"} onChange={() => chooseModel("ACTIVE")} disabled={!canWrite || authoringLocked} />Active Analyst Model <code>{workspace.model_eligibility.active_revision.revision_id}</code></label> : null}{!workspace.model_eligibility.active_revision && workspace.model_eligibility.application_build ? <label><input type="checkbox" checked={modelSelection?.kind === "APPLICATION_BUILD"} onChange={(event) => chooseModel(event.target.checked ? "FALLBACK" : "NONE")} disabled={!canWrite || authoringLocked} />I acknowledge fallback to the Application Model Build <code>{workspace.model_eligibility.application_build.build_id}</code></label> : null}{workspace.template.model_requirement === "OPTIONAL" ? <button className="button small" type="button" onClick={() => chooseModel("NONE")} disabled={!canWrite || authoringLocked || modelSelection === null}>Omit model</button> : null}</fieldset>
          {selectedNarrative ? <div className="flow"><div className="field"><label htmlFor={`narrative-${selectedNarrative.block_id}`}>{workspace.template.blocks.find((item) => item.block_id === selectedNarrative.block_id)?.title || "Narrative"}</label><textarea ref={editorFocus} id={`narrative-${selectedNarrative.block_id}`} value={selectedNarrative.text} maxLength={20000} rows={12} onChange={(event) => updateNarrative(selectedNarrative.block_id, { text: event.target.value })} disabled={!canWrite || authoringLocked} /><span className="field-meta">{selectedNarrative.text.length.toLocaleString()} / 20,000</span></div><fieldset><legend>Claim authority</legend><label><input type="radio" name={`mode-${selectedNarrative.block_id}`} checked={selectedNarrative.content_mode === "EVIDENCE"} onChange={() => updateNarrative(selectedNarrative.block_id, { content_mode: "EVIDENCE" })} disabled={!canWrite || authoringLocked} />Evidence-bound</label><label><input type="radio" name={`mode-${selectedNarrative.block_id}`} checked={selectedNarrative.content_mode === "ANALYST_JUDGMENT"} onChange={() => updateNarrative(selectedNarrative.block_id, { content_mode: "ANALYST_JUDGMENT" })} disabled={!canWrite || authoringLocked} />ANALYST_JUDGMENT</label></fieldset>{selectedNarrative.content_mode === "EVIDENCE" && !selectedNarrative.citations.length ? <p className="error" role="alert">Evidence-bound narrative requires at least one citation.</p> : null}</div> : selectedBlock ? <div className="generated-block-card"><span className="eyebrow">{selectedBlock.kind}</span><h3>Read-only structured block</h3><p>Calculated values and Scenario outputs are accepted only from the server response.</p>{!workspace.template.blocks.some((item) => item.block_id === selectedBlock.block_id) ? <button className="button small" type="button" onClick={() => removeOptional(selectedBlock.block_id)} disabled={!canWrite || authoringLocked}>Omit block</button> : null}</div> : null}
          <section className="evidence-inspector" aria-labelledby="evidence-inspector-title"><div className="section-heading"><h3 id="evidence-inspector-title">Evidence inspector</h3><span>{sources.length} sources</span></div><div className="field"><label htmlFor="report-evidence-search">Find case evidence</label><input id="report-evidence-search" type="search" value={evidenceQuery} onChange={(event) => setEvidenceQuery(event.target.value)} /></div>{evidenceError ? <p className="error" role="alert">{evidenceError}</p> : null}<div className="evidence-source-list">{visibleSources.slice(0, 8).map((source) => <details key={source.id}><summary>{source.filename}<code>{source.id}</code></summary>{source.blocks.slice(0, 12).map((item) => <div className="evidence-source-block" key={item.block_id}><p>{item.text || item.block_id}</p>{selectedBlock && "citations" in selectedBlock && selectedBlock.citations.some((citation) => citation.source_id === source.id && citation.block_ids.includes(item.block_id)) ? <button className="button small" type="button" onClick={() => removeCitation(source.id, item.block_id)} disabled={!canWrite || authoringLocked}>Remove citation</button> : <button className="button small" type="button" onClick={() => cite(source, item.block_id)} disabled={!canWrite || authoringLocked || !selectedBlock || !("citations" in selectedBlock)}>Cite block</button>}</div>)}</details>)}</div></section>
          {modelSelection && registry ? <section className="scenario-insert" aria-labelledby="scenario-insert-title"><div className="section-heading"><h3 id="scenario-insert-title">Scenario Exhibit</h3><span>Temporary server calculation</span></div><div className="scenario-fields"><div className="field"><label htmlFor="scenario-assumption">Assumption</label><select id="scenario-assumption" value={scenarioForm.assumptionId} onChange={(event) => { const assumptionId = event.target.value; const available = registry.defaults.find((row) => row.assumption_id === assumptionId && row.case === scenarioForm.case && row.status === "READY") || registry.defaults.find((row) => row.assumption_id === assumptionId && row.status === "READY"); setScenarioForm((current) => ({ ...current, assumptionId, case: available?.case || current.case, periodId: available?.period_id || "" })); }} disabled={authoringLocked}>{registry.definitions.map((definition) => <option key={definition.assumption_id} value={definition.assumption_id}>{definition.label || definition.assumption_id}</option>)}</select></div><div className="field"><label htmlFor="scenario-case">Case</label><select id="scenario-case" value={scenarioForm.case} onChange={(event) => { const caseName = event.target.value as "BASE" | "DOWNSIDE"; const available = registry.defaults.find((row) => row.assumption_id === scenarioForm.assumptionId && row.case === caseName && row.status === "READY"); setScenarioForm((current) => ({ ...current, case: caseName, periodId: available?.period_id || "" })); }} disabled={authoringLocked}><option value="BASE">Base</option><option value="DOWNSIDE">Downside</option></select></div><div className="field"><label htmlFor="scenario-period">Period</label><select id="scenario-period" value={scenarioForm.periodId} onChange={(event) => setScenarioForm((current) => ({ ...current, periodId: event.target.value }))} disabled={authoringLocked}>{scenarioPeriods.map((periodId) => <option key={periodId} value={periodId}>{periodId}</option>)}</select></div><div className="field"><label htmlFor="scenario-value">Shock value</label><input id="scenario-value" inputMode="decimal" value={scenarioForm.value} onChange={(event) => setScenarioForm((current) => ({ ...current, value: event.target.value }))} disabled={authoringLocked} /></div></div><button className="button small" type="button" onClick={() => void insertScenario()} disabled={!canWrite || authoringLocked || !scenarioForm.periodId || !scenarioForm.value}>{pending === "scenario" ? "Calculating…" : "Calculate and insert exact exhibit"}</button></section> : null}
          {conflict ? <div className="action-state warning" role="alert"><strong>Shared Draft conflict</strong><p>{conflict.author} saved v{conflict.version} at {formatDate(conflict.created_at)}. Your local content remains unchanged.</p><button className="button small" type="button" onClick={() => { savedVersion.current = conflict.version; setPersistedVersion(conflict.version); setWorkspace((current) => current ? { ...current, current: conflict, history: [...current.history.filter((item) => item.id !== conflict.id), conflict] } : current); setSaveState({ kind: "DIRTY" }); markChanged(blocks); }} disabled={authoringLocked}>Retry over current v{conflict.version}</button><button className="button small" type="button" onClick={() => { setBlocks(conflict.content.blocks); setModelSelection(conflict.content.model_selection); savedVersion.current = conflict.version; unsavedDraft.current = false; setDraftIsUnsaved(false); setPersistedVersion(conflict.version); setConflict(null); setSaveState({ kind: "SAVED", version: conflict.version }); onDraftStateChange(false); }} disabled={authoringLocked}>Use shared v{conflict.version}</button></div> : null}
          <div className="report-actions"><button className="button primary" data-primary-report-action type="button" onClick={() => void freeze()} disabled={!freezeReady || lifecycleBusy}>{pending === "freeze" ? "Freezing…" : `Freeze saved v${workspace.current?.version || "—"}`}</button><span>{requiredModelMissing ? "An eligible model is required." : modelStale ? "Refresh the stale model selection." : saveState.kind !== "SAVED" ? "Freeze requires an exact saved revision." : "Freeze revalidates all authority on the server."}</span></div>
        </>}
        {message ? <p className="status success" role="status" aria-live="polite">{message}</p> : null}{error ? <p className="error" role="alert">{error}</p> : null}
      </div>
    </section>

    <section className="report-proof-stage" aria-label="Deliverable paper preview" tabIndex={0}><DeliverableDocument title={selectedFrozen?.payload.template.title || workspace.template.title} issuer={selectedCase ? `${selectedCase.issuer} — ${selectedCase.name}` : workspace.template.title} pathwayLabel={pathwayLabel} status={selectedFrozen?.status || "DRAFT"} version={selectedFrozen?.draft_version || workspace.current?.version} digest={selectedFrozen?.digest || workspace.current?.digest} blocks={previewBlocks} templateBlocks={workspace.template.blocks} generated={previewGenerated} frozen={Boolean(selectedFrozen)} frozenPayload={selectedFrozen?.payload || null} /></section>
  </div>;
}
