from __future__ import annotations

import copy
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .artifacts.domain import (
    accepted_snapshot,
    create_assumption,
    create_note,
    latest_accepted_snapshot,
    latest_version,
    mark_assumptions_stale,
    promote_note,
    recommendation_state,
    save_recommendations,
    save_report_inputs,
    save_thesis,
    snapshot_diff,
)
from .artifacts.relative_value import compare_universe, save_universe
from .config import Settings
from .contracts import (
    DESTINATIONS,
    ApproveRequest,
    AssumptionRequest,
    ConfirmDraftRequest,
    CreateCaseRequest,
    Depth,
    FreezeReportRequest,
    MemberRequest,
    MethodologyDraftRequest,
    NoteRequest,
    RecommendationMatrixRequest,
    ReportInputsRequest,
    RVUniverseRequest,
    SnapshotSwitchRequest,
    StartRunRequest,
    ThesisRequest,
    clean_json,
    digest,
)
from .identity_cases.domain import (
    Identity,
    identity_from_request,
    require_case,
    require_role,
)
from .methodology.bundle import DeployVBundle, MethodologyError
from .publishing.domain import freeze_report, render_pdf, render_xlsx
from .publishing.recipes import validate_recipe
from .sources.domain import current_source_set, ingest_upload, list_sources, pathway_fit
from .store import STORE, MemoryStore, PostgresStore, now_iso
from .workflows.domain import WorkflowError, WorkflowRuntime


def create_app(settings: Settings | None = None, store: MemoryStore | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.environment == "production":
        settings.validate_runtime()
    store = store or (PostgresStore(settings.database_url) if settings.environment == "production" else STORE)
    bundle = DeployVBundle(settings.deploy_v_root)
    runtime = WorkflowRuntime(store, bundle, settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.validate_runtime()
        app.state.bundle_report = bundle.verify()
        yield
        runtime.close()

    app = FastAPI(title="CAOS", version="0.1.0", lifespan=lifespan, docs_url=None if settings.environment == "production" else "/api/docs", redoc_url=None, openapi_url=None if settings.environment == "production" else "/openapi.json")
    app.state.settings = settings
    app.state.store = store
    app.state.bundle = bundle
    app.state.runtime = runtime

    @app.middleware("http")
    async def refresh_production_state(request: Request, call_next: Any) -> Response:
        if settings.environment == "production" and request.url.path.startswith("/api/"):
            await run_in_threadpool(store.refresh)
        return await call_next(request)

    def identity(request: Request) -> Identity:
        return identity_from_request(request, settings)

    def admin_step_up(request: Request) -> Identity:
        who = identity(request)
        require_role(who, "ADMIN")
        if request.headers.get("x-oidc-step-up") != settings.session_secret:
            raise HTTPException(status_code=401, detail="OIDC step-up required")
        return who

    def get_run_or_404(run_id: str, actor: Identity) -> dict[str, Any]:
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        require_case(store, run["case_id"], actor)
        return run

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "caos", "bundle_build_id": bundle.build_id, "database": "postgres-configured" if settings.database_url else "memory-dev", "worker": "same-image"}

    @app.get("/api/me")
    def me(request: Request) -> dict[str, Any]:
        who = identity(request)
        return {"subject": who.subject, "email": who.email, "role": who.role, "destinations": ["Admin Studio"] if who.role == "ADMIN" else list(DESTINATIONS)}

    @app.get("/api/methodology/verify")
    def methodology_verify(request: Request) -> dict[str, Any]:
        require_role(identity(request), "ADMIN", "ANALYST", "APPROVER")
        return bundle.verify()

    @app.get("/api/cases")
    def cases(request: Request) -> list[dict[str, Any]]:
        return store.list_cases(identity(request).subject)

    @app.post("/api/cases", status_code=201)
    def create_case(payload: CreateCaseRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_role(who, "ADMIN", "ANALYST", "APPROVER")
        return store.create_case(payload.name, payload.issuer, payload.sector, who.subject)

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        case = require_case(store, case_id, who)
        latest = store.latest_run_for_case(case_id)
        return {**case, "source_set": current_source_set(store, case_id), "source_count": len(list_sources(store, case_id)), "pathway_fit": pathway_fit(store, case_id), "accepted_snapshot": accepted_snapshot(store, case_id), "latest_run": store.get_run(latest["id"]) if latest else None}

    @app.post("/api/cases/{case_id}/members", status_code=201)
    def add_member(case_id: str, payload: MemberRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        if not store.get_case(case_id):
            raise HTTPException(status_code=404, detail="case not found")
        if who.role != "ADMIN":
            require_case(store, case_id, who, write=True)
        if not store.add_member(case_id, who.subject, payload.subject, payload.role.value, who.role):
            raise HTTPException(status_code=403, detail="case membership authority required")
        return {"case_id": case_id, "subject": payload.subject, "role": payload.role.value}

    @app.get("/api/cases/{case_id}/sources")
    def sources(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(store, case_id, identity(request))
        return list_sources(store, case_id)

    @app.post("/api/cases/{case_id}/sources", status_code=201)
    async def upload_source(case_id: str, request: Request, file: UploadFile) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        result = await ingest_upload(store, runtime.vault, case_id, who.subject, file, settings.max_upload_bytes)
        mark_assumptions_stale(store, case_id, {result["id"]})
        return result

    @app.get("/api/cases/{case_id}/sources/{source_id}")
    def source_detail(case_id: str, source_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        with store.lock:
            source = store.sources.get(source_id)
            if not source or source["case_id"] != case_id:
                raise HTTPException(status_code=404, detail="source not found")
            return {key: value for key, value in source.items() if key != "vault_path"}

    @app.get("/api/cases/{case_id}/artifacts/{artifact_id}")
    def artifact_detail(case_id: str, artifact_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        artifact = store.get_artifact(artifact_id)
        if not artifact or artifact.get("case_id") != case_id:
            raise HTTPException(status_code=404, detail="artifact not found")
        return artifact

    @app.post("/api/cases/{case_id}/sources/{source_id}/withdraw")
    def withdraw_source(case_id: str, source_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        with store.lock:
            source = store.sources.get(source_id)
            if not source or source["case_id"] != case_id:
                raise HTTPException(status_code=404, detail="source not found")
            if source.get("withdrawn"):
                return {key: value for key, value in source.items() if key != "vault_path"}
            prior_source_set = store.source_sets.get(case_id)
            prior_withdrawn = source.get("withdrawn", False)
            prior_assumptions = copy.deepcopy(store.assumptions.get(case_id))
            audit_start = len(store.audit)
            source["withdrawn"] = True
            current = store.source_sets.get(case_id)
            new_source_set_id: str | None = None
            if current:
                active_source_ids = [existing_id for existing_id in current["source_ids"] if not store.sources.get(existing_id, {}).get("withdrawn")]
                new_source_set_id = store._id("set")
                store.register_source_set({"id": new_source_set_id, "case_id": case_id, "version": current["version"] + 1, "source_ids": active_source_ids, "created_by": who.subject, "created_at": now_iso()})
            mark_assumptions_stale(store, case_id, {source_id}, persist=False)
            store.audit_event("source.withdrawn", who.subject, case_id=case_id, source_id=source_id)
            try:
                store.persist()
            except Exception:
                source["withdrawn"] = prior_withdrawn
                if prior_source_set is None:
                    store.source_sets.pop(case_id, None)
                else:
                    store.source_sets[case_id] = prior_source_set
                if new_source_set_id:
                    store.source_set_history.pop(new_source_set_id, None)
                if prior_assumptions is None:
                    store.assumptions.pop(case_id, None)
                else:
                    store.assumptions[case_id] = prior_assumptions
                del store.audit[audit_start:]
                raise
        return {key: value for key, value in source.items() if key != "vault_path"}

    @app.get("/api/cases/{case_id}/pathway-fit")
    def fit(case_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        return pathway_fit(store, case_id)

    @app.get("/api/cases/{case_id}/runs")
    def runs(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(store, case_id, identity(request))
        with store.lock:
            return [store.get_run(run["id"]) for run in store.runs.values() if run["case_id"] == case_id]

    @app.post("/api/cases/{case_id}/runs", status_code=202)
    def start_run(case_id: str, payload: StartRunRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            return runtime.start_run(case_id, who.subject, payload.pathway, payload.depth, payload.focus_questions)
        except MethodologyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/upgrade", status_code=202)
    def upgrade_run(run_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        previous = get_run_or_404(run_id, who)
        require_case(store, previous["case_id"], who, write=True)
        if previous["plan"]["depth"] != Depth.SCREEN.value:
            raise HTTPException(status_code=409, detail="only Screen runs can be upgraded")
        try:
            return runtime.start_run(previous["case_id"], who.subject, previous["plan"]["pathway"], Depth.FULL, previous["plan"].get("focus_questions", []), previous["id"])
        except MethodologyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str, request: Request) -> dict[str, Any]:
        return get_run_or_404(run_id, identity(request))

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str, request: Request) -> StreamingResponse:
        get_run_or_404(run_id, identity(request))
        try:
            cursor = int(request.headers.get("last-event-id", "0"))
        except ValueError:
            cursor = 0
        return StreamingResponse(runtime.stream_events(run_id, cursor), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/runs/{run_id}/accept")
    def accept_run(run_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        run = get_run_or_404(run_id, who)
        require_case(store, run["case_id"], who, write=True)
        try:
            return runtime.accept_run(run["case_id"], run_id, who.subject)
        except WorkflowError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/snapshot")
    def snapshot(case_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        current = accepted_snapshot(store, case_id)
        latest_snapshot = latest_accepted_snapshot(store, case_id)
        return {"accepted": current, "latest_accepted": latest_snapshot, "diff": snapshot_diff(current, latest_snapshot) if latest_snapshot else None, "switch_required": bool(current and latest_snapshot and current["id"] != latest_snapshot["id"])}

    @app.post("/api/cases/{case_id}/snapshot/switch")
    def switch_snapshot(case_id: str, payload: SnapshotSwitchRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        with store.lock:
            target = store.snapshots.get(payload.snapshot_id)
            if not target or target["case_id"] != case_id:
                raise HTTPException(status_code=404, detail="snapshot not found")
            store.cases[case_id]["visible_snapshot_id"] = payload.snapshot_id
            store.audit_event("snapshot.visible_switched", who.subject, case_id=case_id, snapshot_id=payload.snapshot_id)
            store.persist()
        return target.copy()

    @app.get("/api/cases/{case_id}/lens")
    def lens(case_id: str, request: Request) -> dict[str, Any]:
        case = require_case(store, case_id, identity(request))
        accepted = accepted_snapshot(store, case_id)
        return {"issuer": case["issuer"], "sector": case["sector"], "accepted_snapshot_id": accepted["id"] if accepted else None, "accepted_snapshot_digest": accepted["digest"] if accepted else None, "source_set": current_source_set(store, case_id)}

    @app.get("/api/cases/{case_id}/thesis")
    def thesis(case_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        return {"versions": store.versioned(store.theses, case_id), "current": latest_version(store, store.theses, case_id)}

    @app.post("/api/cases/{case_id}/report-inputs", status_code=201)
    def report_inputs(case_id: str, payload: ReportInputsRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            accepted = accepted_snapshot(store, case_id)
            if not accepted:
                raise HTTPException(status_code=409, detail="SNAPSHOT_REQUIRED")
            return save_report_inputs(store, case_id, who.subject, payload.thesis, payload.recommendations, accepted["id"])
        except ValueError as exc:
            status = 409 if str(exc) == "VERSION_CONFLICT" else 422
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    @app.post("/api/cases/{case_id}/thesis", status_code=201)
    def write_thesis(case_id: str, payload: ThesisRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            return save_thesis(store, case_id, who.subject, payload)
        except ValueError as exc:
            if str(exc) == "VERSION_CONFLICT":
                raise HTTPException(status_code=409, detail="thesis version changed") from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/recommendations")
    def recommendations(case_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        versions = store.versioned(store.recommendations, case_id)
        return {"versions": versions, "current": recommendation_state(store, case_id, versions[-1] if versions else None)}

    @app.post("/api/cases/{case_id}/recommendations", status_code=201)
    def write_recommendations(case_id: str, payload: RecommendationMatrixRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            accepted = accepted_snapshot(store, case_id)
            return save_recommendations(store, case_id, who.subject, payload, accepted["id"] if accepted else None)
        except ValueError as exc:
            if str(exc) == "VERSION_CONFLICT":
                raise HTTPException(status_code=409, detail="recommendation version changed") from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/notes")
    def notes(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(store, case_id, identity(request))
        return store.versioned(store.notes, case_id)

    @app.post("/api/cases/{case_id}/notes", status_code=201)
    def write_note(case_id: str, payload: NoteRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        return create_note(store, case_id, who.subject, payload.body)

    @app.post("/api/cases/{case_id}/notes/{note_id}/promote")
    def promote(case_id: str, note_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            return promote_note(store, case_id, note_id, who.subject)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="note not found") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/assumptions")
    def assumptions(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(store, case_id, identity(request))
        return store.versioned(store.assumptions, case_id)

    @app.post("/api/cases/{case_id}/assumptions", status_code=201)
    def write_assumption(case_id: str, payload: AssumptionRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            return create_assumption(store, case_id, who.subject, payload.statement, payload.evidence_ids, payload.affected_module_ids, payload.supporting_claim, payload.conflicting_claim)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/rv")
    def rv(case_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        return compare_universe(store, case_id, accepted_snapshot(store, case_id))

    @app.post("/api/cases/{case_id}/rv", status_code=201)
    def write_rv(case_id: str, payload: RVUniverseRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        try:
            return save_universe(store, case_id, who.subject, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/model")
    def model(case_id: str, request: Request) -> dict[str, Any]:
        require_case(store, case_id, identity(request))
        return {"status": "BLOCKED", "official": False, "module_id": "CP-MODEL", "reason": "signed Deploy V CP-MODEL correction required", "note": "No provisional workbook is labelled as an official CP-MODEL output."}

    @app.post("/api/cases/{case_id}/reports/freeze", status_code=201)
    def freeze(case_id: str, payload: FreezeReportRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        snapshot_value = accepted_snapshot(store, case_id)
        thesis_value = next((value for value in store.versioned(store.theses, case_id) if value["version"] == payload.thesis_version), None)
        recommendation_value = recommendation_state(store, case_id, next((value for value in store.versioned(store.recommendations, case_id) if value["version"] == payload.recommendation_version), None))
        try:
            return freeze_report(store, case_id, who.subject, snapshot_value, thesis_value, recommendation_value, payload.include_model)
        except ValueError as exc:
            status = 423 if str(exc) == "CP_MODEL_AUTHORITY_BLOCKED" else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/reports")
    def reports(case_id: str, request: Request) -> dict[str, Any] | None:
        require_case(store, case_id, identity(request))
        value = store.reports.get(case_id)
        return value.copy() if value else None

    @app.post("/api/cases/{case_id}/reports/approve")
    def approve(case_id: str, payload: ApproveRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(store, case_id, who, write=True)
        require_role(who, "APPROVER", "ADMIN")
        with store.lock:
            report = store.reports.get(case_id)
            if not report or report["status"] != payload.expected_status:
                raise HTTPException(status_code=409, detail="report changed or missing")
            if payload.preview_digest != report["preview_digest"] or payload.input_fingerprint != report["input_fingerprint"]:
                raise HTTPException(status_code=409, detail="STALE_PREVIEW")
            snapshot_value = accepted_snapshot(store, case_id)
            thesis_value = next((value for value in store.versioned(store.theses, case_id) if value["version"] == report["content"]["thesis_version"]), None)
            recommendation_value = recommendation_state(store, case_id, next((value for value in store.versioned(store.recommendations, case_id) if value["version"] == report["content"]["recommendation_version"]), None))
            current_fingerprint = digest(clean_json({"snapshot": snapshot_value, "thesis": thesis_value, "recommendations": recommendation_value, "include_model": False}))
            if current_fingerprint != report["input_fingerprint"]:
                raise HTTPException(status_code=409, detail="STALE_PREVIEW")
            prior_report = copy.deepcopy(report)
            audit_start = len(store.audit)
            report["status"] = "APPROVED"
            report["approved_by"] = who.subject
            report["approved_at"] = now_iso()
            report["approval_comment"] = payload.comment
            store.audit_event("report.approved", who.subject, case_id=case_id, report_id=report["id"])
            try:
                store.persist()
            except Exception:
                store.reports[case_id] = prior_report
                del store.audit[audit_start:]
                raise
        return report.copy()

    @app.get("/api/cases/{case_id}/reports/export/{format_name}")
    def export_report(case_id: str, format_name: str, request: Request) -> Response:
        who = identity(request)
        require_case(store, case_id, who)
        report = store.reports.get(case_id)
        if not report or report["status"] != "APPROVED":
            raise HTTPException(status_code=409, detail="approved frozen report required")
        if format_name == "md":
            return Response(report["markdown"], media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={report['id']}.md"})
        if format_name == "pdf":
            return Response(render_pdf(report), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report['id']}.pdf"})
        if format_name == "xlsx":
            return Response(render_xlsx(report), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={report['id']}.xlsx"})
        raise HTTPException(status_code=404, detail="unknown export format")

    @app.get("/api/admin/audit")
    def audit(request: Request) -> list[dict[str, Any]]:
        admin_step_up(request)
        return list(store.audit)

    @app.get("/api/admin/bundle")
    def admin_bundle(request: Request) -> dict[str, Any]:
        admin_step_up(request)
        return {"build_id": bundle.build_id, "integrity": bundle.verify(), "drafts": list(store.methodology_drafts.values())}

    @app.get("/api/admin/drafts")
    def methodology_drafts(request: Request) -> list[dict[str, Any]]:
        admin_step_up(request)
        return list(store.methodology_drafts.values())

    @app.post("/api/admin/drafts", status_code=201)
    def create_methodology_draft(payload: MethodologyDraftRequest, request: Request) -> dict[str, Any]:
        who = admin_step_up(request)
        module_ids = {item["module_id"] for item in bundle.catalog["modules"]}
        if payload.expected_build_id != bundle.build_id or payload.module_id not in module_ids:
            raise HTTPException(status_code=422, detail="draft authority identity is not current")
        if payload.before == payload.after:
            raise HTTPException(status_code=422, detail="draft must change a governed value")
        draft = {
            "id": store._id("draft"),
            "status": "DRAFT",
            "expected_build_id": payload.expected_build_id,
            "module_id": payload.module_id,
            "field": payload.field,
            "before": payload.before,
            "after": payload.after,
            "rationale": payload.rationale,
            "created_by": who.subject,
            "created_at": now_iso(),
            "semantic_diff": {"before": payload.before, "after": payload.after},
        }
        draft["digest"] = digest(draft)
        with store.lock:
            audit_start = len(store.audit)
            store.methodology_drafts[draft["id"]] = draft
            store.audit_event("methodology.draft_created", who.subject, draft_id=draft["id"], module_id=draft["module_id"])
            try:
                store.persist()
            except Exception:
                store.methodology_drafts.pop(draft["id"], None)
                del store.audit[audit_start:]
                raise
        return draft

    @app.post("/api/admin/drafts/{draft_id}/validate")
    def validate_methodology_draft(draft_id: str, request: Request) -> dict[str, Any]:
        who = admin_step_up(request)
        with store.lock:
            draft = store.methodology_drafts.get(draft_id)
            if not draft:
                raise HTTPException(status_code=404, detail="draft not found")
            if draft["expected_build_id"] != bundle.build_id or draft["before"] == draft["after"]:
                raise HTTPException(status_code=422, detail="draft does not validate against the current authority")
            prior_draft = copy.deepcopy(draft)
            audit_start = len(store.audit)
            draft["status"] = "VALIDATED"
            draft["validated_by"] = who.subject
            draft["validated_at"] = now_iso()
            store.audit_event("methodology.draft_validated", who.subject, draft_id=draft_id)
            try:
                store.persist()
            except Exception:
                store.methodology_drafts[draft_id] = prior_draft
                del store.audit[audit_start:]
                raise
        return draft.copy()

    @app.post("/api/admin/drafts/{draft_id}/confirm")
    def confirm_methodology_draft(draft_id: str, payload: ConfirmDraftRequest, request: Request) -> dict[str, Any]:
        who = admin_step_up(request)
        with store.lock:
            draft = store.methodology_drafts.get(draft_id)
            if not draft:
                raise HTTPException(status_code=404, detail="draft not found")
            if draft["status"] != "VALIDATED":
                raise HTTPException(status_code=409, detail="validated draft required")
            prior_draft = copy.deepcopy(draft)
            audit_start = len(store.audit)
            draft["status"] = "CONFIRMED_PENDING_SIGNED_AUTHORITY"
            draft["confirmed_by"] = who.subject
            draft["confirmed_at"] = now_iso()
            draft["signature"] = digest({"draft": draft["digest"], "build_id": bundle.build_id, "confirmation": payload.confirmation})
            store.audit_event("methodology.draft_confirmed", who.subject, draft_id=draft_id, signature=draft["signature"])
            try:
                store.persist()
            except Exception:
                store.methodology_drafts[draft_id] = prior_draft
                del store.audit[audit_start:]
                raise
        return draft.copy()

    @app.post("/api/admin/recipes/validate")
    def validate_visual_recipe(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        admin_step_up(request)
        try:
            return {"valid": True, "recipe": validate_recipe(payload, {"periods", "revenue", "ebitda", "delta", "spread_bps", "duration", "system_signal"})}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()
