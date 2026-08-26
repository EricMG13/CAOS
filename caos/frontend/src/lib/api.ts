export type { CaseRecord, Snapshot, Snapshot as SnapshotRecord, SnapshotView } from "./workbench";

export type ResearchWorkstream = { id: string; kind: string; question: string; assigned_questions?: string[]; perspective: string; hypothesis: string; evidence_needs: string[]; source_classes: string[]; disconfirming_test: string; completion_test: string; effort_cap: string };
export type ResearchPlan = { methodology_build_id: string; brief_digest: string; source_set: { id: string; version: number }; upstream_artifacts: { module_id: string; artifact_id: string; digest: string }[]; scope: { type?: string | null; key?: string | null; source_mode?: string | null }; workstreams: ResearchWorkstream[] };
export type RunRecord = { id: string; case_id: string; status: string; plan: { pathway: string; depth: string; profile_id: string; selection_id: string }; nodes: { id: string; module_id: string; status: string; artifact_id?: string | null }[]; error?: { code?: string; message?: string } | null; research?: { phase?: string; proposed_plan_hash?: string | null; approved_plan_hash?: string | null; proposed_plan?: ResearchPlan | null } | null };
export type SourceRecord = { id: string; filename: string; sha256: string; blocks: { block_id: string; locator: Record<string, unknown>; text?: string }[] };
export type ArtifactRecord = { id: string; module_id: string; digest: string; markdown?: string; created_at?: string; payload?: { summary?: string; evidence_refs?: string[]; narrative?: { takeaway?: string; basis?: string }; visual?: { freshness?: string; units?: string } } };
export type LoanLocator = { sheet: string; row: number };
export type LoanRow = { instrument_key: string; company: string | null; borrower_name: string | null; business_description: string | null; sector: string; sub_sector: string | null; sub_group: string | null; public_private: string | null; bloomberg_loan_id: string | null; figi: string | null; loan_type: string | null; ranking: string | null; ratings: string | null; size_mn: number | null; margin_bps: number | null; maturity_date: string | null; bid_points: number | null; ask_points: number | null; change_1d_points: number | null; change_1w_points: number | null; change_1m_points: number | null; change_3m_points: number | null; change_6m_points: number | null; change_1yr_points: number | null; change_ytd_points: number | null; mid_ytm_pct: number | null; mid_3y_dm_bps: number | null; source_locators: LoanLocator[] };
export type LoanUniverse = { id: string; source_id: string; source_filename: string; source_sha256: string; workbook_date: string | null; template_version: string; importer_version: string; universe_digest: string; row_count: number; version: number; status: string; activated_at: string };
export type LoanUniverseResponse = { status: "ACTIVE" | "NO_ACTIVE_UNIVERSE"; universe: LoanUniverse | null; rows: LoanRow[] };
export type LoanFinding = { code: string; detail: string; sheet?: string | null; row?: number | null; column?: string | null };
export type ReportDraft = { thesis?: string; instrument?: string; recommendation?: string; evidenceIds?: string };
export type EvidenceOption = { id: string; kind: "Snapshot" | "Artifact" | "Source"; label: string };
export type ModelBuild = { id: string; case_id: string; accepted_run_id: string; accepted_snapshot_id: string; source_set_id: string; input_fingerprint: string; status: "QUEUED" | "BUILDING" | "READY" | "FAILED"; queued_at: string; started_at?: string | null; completed_at?: string | null; error?: { code: string; detail: string } | null; export: { status: "NOT_REQUESTED" | "QUEUED" | "EXPORTING" | "READY" | "FAILED"; error?: { code: string; detail: string } | null; filename?: string; sha256?: string; size?: number }; qa?: { status: string; semantic_check_count: number; formula_count: number; worksheet_cell_count: number; validation_warnings?: string[]; limitation_flags?: string[] }; payload_digest?: string };
export type ModelReadiness = { status: "NOT_READY" | "READY_TO_BUILD" | ModelBuild["status"]; module_id: "CP-MODEL"; accepted_snapshot: { id: string; run_id: string; digest?: string } | null; source_set: { id: string; version: number; digest: string } | null; requirements: { module_id: string; status: string; digest?: string }[]; blockers: { code: string; detail: string }[]; build: ModelBuild | null };
export type ModelInventory = { readiness: ModelReadiness; builds: ModelBuild[] };
export type WorksheetCell = { address: string; row: number; column: number; value: string | number | boolean | null; value_type: "formula" | "boolean" | "number" | "date" | "text"; formula: string | null; semantic_id: string | null; owner: string | null; write_class: string | null; period_id: string | null; source_refs: string | null; number_format: string; style: { bold: boolean; italic: boolean; fill: string | null; align: string | null; wrap: boolean } };
export type WorksheetTab = { id: string; name: string; max_row: number; max_column: number; freeze_panes: string; merged_cells: string[]; columns: { column: number; letter: string; width?: number; hidden: boolean }[]; cells: WorksheetCell[] };
export type WorksheetResponse = { build_id: string; input_fingerprint: string; payload_digest: string; qa: ModelBuild["qa"]; payload: { schema_version: string; identity: { issuer_id: string; issuer_name: string; analysis_date: string }; tabs: WorksheetTab[] } };

export function assumptionRegistryPath(caseId: string, buildId: string) {
  return `/api/cases/${caseId}/models/assumption-registry?build_id=${encodeURIComponent(buildId)}`;
}

export async function api<T>(path: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...options, signal, headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
