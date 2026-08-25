from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import anthropic
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .artifacts.domain import (
    accepted_snapshot,
    latest_accepted_snapshot,
    recommendation_state,
    snapshot_diff,
)
from .artifacts.relative_value import compare_universe, save_universe
from .artifacts.loan_universe import (
    LoanUniverseImportRejected,
    LoanUniverseSourceError,
    import_loan_source,
)
from .config import Settings
from .contracts import (
    DESTINATIONS,
    ApproveResearchPlanRequest,
    ApproveRequest,
    AssumptionRequest,
    ConfirmDraftRequest,
    CreateCaseRequest,
    Depth,
    FreezeReportRequest,
    LoanUniverseImportRequest,
    MemberRequest,
    MethodologyDraftRequest,
    NoteRequest,
    RecommendationMatrixRequest,
    ReportInputsRequest,
    RVUniverseRequest,
    SnapshotSwitchRequest,
    StartRunRequest,
    ThesisRequest,
    digest,
)
from .identity_cases.domain import (
    Identity,
    identity_from_request,
    require_case,
    require_role,
)
from .methodology.bundle import DeployVBundle, MethodologyError
from .models.domain import CpModelBundle
from .models.runtime import (
    MAX_EXPORT_BYTES,
    ModelBuildRuntime,
    ModelReadinessService,
    public_model_build,
)
from .publishing.domain import (
    freeze_report,
    render_pdf,
    render_xlsx,
)
from .publishing.recipes import validate_recipe
from .responses import (
    ActiveLoanUniverseRouteResponse,
    AdminBundleResponse,
    ArtifactResponse,
    AssumptionResponse,
    AuditRouteResponse,
    CaseDetailResponse,
    CaseMemberResponse,
    CaseLensResponse,
    CaseResponse,
    HealthResponse,
    IdentityResponse,
    LoanUniverseResponse,
    MethodologyDraftResponse,
    MethodologyVerificationResponse,
    ModelBuildRouteResponse,
    ModelListResponse,
    ModelReadinessRouteResponse,
    ModelWorksheetResponse,
    NoteRouteResponse,
    PathwayFitResponse,
    QueueModelExportResponse,
    QueueModelResponse,
    RecommendationHistoryResponse,
    RecommendationResponse,
    ReportInputsResponse,
    ReportRouteResponse,
    RunRouteResponse,
    RVRouteResponse,
    RVUniverseResponse,
    SnapshotOverviewResponse,
    SnapshotResponse,
    SourceResponse,
    ThesisHistoryResponse,
    ThesisResponse,
    VisualRecipeValidationResponse,
)
from .sources.domain import current_source_set, ingest_upload, list_sources, pathway_fit
from .memory_ledgers import MemoryLedgerSet
from .postgres_ledgers import PostgresLedgerSet
from .workflows.domain import WorkflowError, WorkflowRuntime
from .workflows.provider import AnthropicProvider


def create_app(settings: Settings | None = None, ledger_set: Any | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.environment == "production":
        settings.validate_runtime()
    ledger_set = ledger_set or (
        PostgresLedgerSet(settings.database_url)
        if settings.environment == "production"
        else MemoryLedgerSet()
    )
    sources_catalog = ledger_set.sources
    runs_ledger = ledger_set.runs
    publications = ledger_set.publications
    models_ledger = ledger_set.models
    bundle = DeployVBundle(settings.deploy_v_root)
    provider = (
        AnthropicProvider(
            settings.anthropic_api_key,
            settings.anthropic_model,
            settings.anthropic_timeout_seconds,
        )
        if settings.anthropic_api_key
        and (settings.canonical_agent_enabled or settings.cpdr_agent_enabled)
        else None
    )
    runtime = WorkflowRuntime(
        runs_ledger,
        sources_catalog,
        bundle,
        settings,
        provider=provider,
        schema_transform=anthropic.transform_schema if provider else None,
        request_preimage=provider._request_preimage if provider else None,
    )
    model_bundle = CpModelBundle(settings.deploy_v_root)
    model_readiness = ModelReadinessService(
        runs_ledger, models_ledger, sources_catalog, bundle, model_bundle
    )
    model_runtime = ModelBuildRuntime(
        models_ledger, model_readiness, model_bundle, runtime.executor, settings.storage_dir
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.validate_runtime()
        app.state.bundle_report = bundle.verify()
        yield
        runtime.close()

    app = FastAPI(title="CAOS", version="0.1.0", lifespan=lifespan, docs_url=None if settings.environment == "production" else "/api/docs", redoc_url=None, openapi_url=None if settings.environment == "production" else "/openapi.json")
    app.state.settings = settings
    app.state.ledger_set = ledger_set
    app.state.bundle = bundle
    app.state.runtime = runtime
    app.state.model_readiness = model_readiness
    app.state.model_runtime = model_runtime

    def identity(request: Request) -> Identity:
        return identity_from_request(request, settings)

    def admin_step_up(request: Request) -> Identity:
        who = identity(request)
        require_role(who, "ADMIN")
        if request.headers.get("x-oidc-step-up") != settings.session_secret:
            raise HTTPException(status_code=401, detail="OIDC step-up required")
        return who

    def get_run_or_404(run_id: str, actor: Identity) -> dict[str, Any]:
        run = runs_ledger.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        require_case(runs_ledger, run["case_id"], actor)
        return run

    def model_for_case(case_id: str, build_id: str) -> dict[str, Any]:
        build = models_ledger.get_build(build_id)
        if build is None or build.get("case_id") != case_id:
            raise HTTPException(status_code=404, detail="model build not found")
        return build

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "caos", "bundle_build_id": bundle.build_id, "database": "postgres-configured" if settings.database_url else "memory-dev", "worker": "same-image"}

    @app.get("/api/me", response_model=IdentityResponse)
    def me(request: Request) -> dict[str, Any]:
        who = identity(request)
        return {"subject": who.subject, "email": who.email, "role": who.role, "destinations": ["Admin Studio"] if who.role == "ADMIN" else list(DESTINATIONS)}

    @app.get("/api/methodology/verify", response_model=MethodologyVerificationResponse)
    def methodology_verify(request: Request) -> dict[str, Any]:
        require_role(identity(request), "ADMIN", "ANALYST", "APPROVER")
        return bundle.verify()

    @app.get("/api/cases", response_model=list[CaseResponse])
    def cases(request: Request) -> list[dict[str, Any]]:
        return runs_ledger.list_cases(identity(request).subject)

    @app.post("/api/cases", status_code=201, response_model=CaseResponse)
    def create_case(payload: CreateCaseRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_role(who, "ADMIN", "ANALYST", "APPROVER")
        return runs_ledger.create_case(payload.name, payload.issuer, payload.sector, who.subject)

    @app.get("/api/cases/{case_id}", response_model=CaseDetailResponse)
    def case_detail(case_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        case = require_case(runs_ledger, case_id, who)
        latest = runs_ledger.latest_run(case_id)
        deep_research_available = settings.cpdr_agent_enabled and (case_id in settings.cpdr_pilot_case_ids or who.subject in settings.cpdr_pilot_subjects)
        deep_research_unavailable_reason = None if deep_research_available else (
            "Deep Research is disabled for this deployment."
            if not settings.cpdr_agent_enabled
            else "Deep Research is outside the pilot allowlist."
        )
        return {**case, "source_set": current_source_set(sources_catalog, case_id), "source_count": len(list_sources(sources_catalog, case_id)), "pathway_fit": pathway_fit(sources_catalog, case_id), "accepted_snapshot": accepted_snapshot(runs_ledger, case_id), "latest_run": runs_ledger.get_run(latest["id"]) if latest else None, "deep_research_available": deep_research_available, "deep_research_unavailable_reason": deep_research_unavailable_reason}

    @app.post("/api/cases/{case_id}/members", status_code=201, response_model=CaseMemberResponse)
    def add_member(case_id: str, payload: MemberRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        if not runs_ledger.get_case(case_id):
            raise HTTPException(status_code=404, detail="case not found")
        if who.role != "ADMIN":
            require_case(runs_ledger, case_id, who, write=True)
        if not runs_ledger.add_member(case_id, who.subject, payload.subject, payload.role.value, who.role):
            raise HTTPException(status_code=403, detail="case membership authority required")
        return {"case_id": case_id, "subject": payload.subject, "role": payload.role.value}

    @app.get("/api/cases/{case_id}/sources", response_model=list[SourceResponse])
    def sources(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(runs_ledger, case_id, identity(request))
        return list_sources(sources_catalog, case_id)

    @app.post("/api/cases/{case_id}/sources", status_code=201, response_model=SourceResponse)
    async def upload_source(case_id: str, request: Request, file: UploadFile) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        return await ingest_upload(
            sources_catalog,
            runtime.vault,
            case_id,
            who.subject,
            file,
            settings.max_upload_bytes,
        )

    @app.get("/api/cases/{case_id}/sources/{source_id}", response_model=SourceResponse)
    def source_detail(case_id: str, source_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        source = sources_catalog.get_source(source_id)
        if not source or source["case_id"] != case_id:
            raise HTTPException(status_code=404, detail="source not found")
        return source

    @app.get("/api/cases/{case_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
    def artifact_detail(case_id: str, artifact_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        artifact = runs_ledger.get_artifact(artifact_id)
        if not artifact or artifact.get("case_id") != case_id:
            raise HTTPException(status_code=404, detail="artifact not found")
        return artifact

    @app.post("/api/cases/{case_id}/sources/{source_id}/withdraw", response_model=SourceResponse)
    def withdraw_source(case_id: str, source_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        source = sources_catalog.withdraw(case_id, source_id, who.subject)
        if source is None:
            raise HTTPException(status_code=404, detail="source not found")
        return {key: value for key, value in source.items() if key != "withdrawn_at"}

    @app.get("/api/cases/{case_id}/pathway-fit", response_model=PathwayFitResponse)
    def fit(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        return pathway_fit(sources_catalog, case_id)

    @app.get("/api/cases/{case_id}/runs", response_model=list[RunRouteResponse])
    def runs(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(runs_ledger, case_id, identity(request))
        return runs_ledger.list_runs(case_id)

    @app.post("/api/cases/{case_id}/runs", status_code=202, response_model=RunRouteResponse)
    def start_run(case_id: str, payload: StartRunRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        if payload.pathway == "DEEP_RESEARCH":
            if not settings.cpdr_agent_enabled:
                raise HTTPException(status_code=403, detail="Deep Research is disabled for this deployment.")
            if case_id not in settings.cpdr_pilot_case_ids and who.subject not in settings.cpdr_pilot_subjects:
                raise HTTPException(status_code=403, detail="Deep Research is outside the pilot allowlist.")
        try:
            research_brief = payload.research_brief.model_dump(mode="json") if payload.research_brief else None
            return runtime.start_run(case_id, who.subject, payload.pathway, payload.depth, payload.focus_questions, research_brief)
        except MethodologyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/upgrade", status_code=202, response_model=RunRouteResponse)
    def upgrade_run(run_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        previous = get_run_or_404(run_id, who)
        require_case(runs_ledger, previous["case_id"], who, write=True)
        if previous["plan"]["depth"] != Depth.SCREEN.value:
            raise HTTPException(status_code=409, detail="only Screen runs can be upgraded")
        try:
            return runtime.start_run(previous["case_id"], who.subject, previous["plan"]["pathway"], Depth.FULL, previous["plan"].get("focus_questions", []), upgraded_from_run_id=previous["id"])
        except MethodologyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}", response_model=RunRouteResponse)
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

    @app.post("/api/runs/{run_id}/research-plan/approve", response_model=RunRouteResponse)
    def approve_research_plan(run_id: str, payload: ApproveResearchPlanRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        run = get_run_or_404(run_id, who)
        require_case(runs_ledger, run["case_id"], who, write=True)
        try:
            return runtime.approve_research_plan(run_id, who.subject, payload.plan_hash)
        except WorkflowError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/accept", response_model=SnapshotResponse)
    def accept_run(run_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        run = get_run_or_404(run_id, who)
        require_case(runs_ledger, run["case_id"], who, write=True)
        try:
            return runtime.accept_run(run["case_id"], run_id, who.subject)
        except WorkflowError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/snapshot", response_model=SnapshotOverviewResponse)
    def snapshot(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        current = accepted_snapshot(runs_ledger, case_id)
        latest_snapshot = latest_accepted_snapshot(runs_ledger, case_id)
        return {"accepted": current, "latest_accepted": latest_snapshot, "diff": snapshot_diff(current, latest_snapshot) if latest_snapshot else None, "switch_required": bool(current and latest_snapshot and current["id"] != latest_snapshot["id"])}

    @app.post("/api/cases/{case_id}/snapshot/switch", response_model=SnapshotResponse)
    def switch_snapshot(case_id: str, payload: SnapshotSwitchRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        target = runs_ledger.switch_visible_snapshot(
            case_id, payload.snapshot_id, who.subject
        )
        if target is None:
            raise HTTPException(status_code=404, detail="snapshot not found")
        return target

    @app.get("/api/cases/{case_id}/lens", response_model=CaseLensResponse)
    def lens(case_id: str, request: Request) -> dict[str, Any]:
        case = require_case(runs_ledger, case_id, identity(request))
        accepted = accepted_snapshot(runs_ledger, case_id)
        return {"issuer": case["issuer"], "sector": case["sector"], "accepted_snapshot_id": accepted["id"] if accepted else None, "accepted_snapshot_digest": accepted["digest"] if accepted else None, "source_set": current_source_set(sources_catalog, case_id)}

    @app.get("/api/cases/{case_id}/thesis", response_model=ThesisHistoryResponse)
    def thesis(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        versions = publications.list_theses(case_id)
        return {"versions": versions, "current": versions[-1] if versions else None}

    @app.post("/api/cases/{case_id}/report-inputs", status_code=201, response_model=ReportInputsResponse)
    def report_inputs(case_id: str, payload: ReportInputsRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            accepted = accepted_snapshot(runs_ledger, case_id)
            if not accepted:
                raise HTTPException(status_code=409, detail="SNAPSHOT_REQUIRED")
            return publications.save_report_inputs(
                case_id,
                who.subject,
                payload.thesis.model_dump(mode="json"),
                payload.recommendations.model_dump(mode="json"),
                accepted["id"],
            )
        except ValueError as exc:
            status = 409 if str(exc) == "VERSION_CONFLICT" else 422
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    @app.post("/api/cases/{case_id}/thesis", status_code=201, response_model=ThesisResponse)
    def write_thesis(case_id: str, payload: ThesisRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            thesis_value = payload.model_dump(mode="json")
            return publications.append_thesis(
                case_id,
                who.subject,
                payload.expected_version,
                {key: value for key, value in thesis_value.items() if key != "expected_version"},
            )
        except ValueError as exc:
            if str(exc) == "VERSION_CONFLICT":
                raise HTTPException(status_code=409, detail="thesis version changed") from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/recommendations", response_model=RecommendationHistoryResponse)
    def recommendations(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        versions = publications.list_recommendations(case_id)
        return {"versions": versions, "current": recommendation_state(runs_ledger, case_id, versions[-1] if versions else None)}

    @app.post("/api/cases/{case_id}/recommendations", status_code=201, response_model=RecommendationResponse)
    def write_recommendations(case_id: str, payload: RecommendationMatrixRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            accepted = accepted_snapshot(runs_ledger, case_id)
            recommendation = payload.model_dump(mode="json")
            recommendation["accepted_snapshot_id"] = accepted["id"] if accepted else None
            return publications.append_recommendations(
                case_id,
                who.subject,
                payload.expected_version,
                {key: value for key, value in recommendation.items() if key != "expected_version"},
            )
        except ValueError as exc:
            if str(exc) == "VERSION_CONFLICT":
                raise HTTPException(status_code=409, detail="recommendation version changed") from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/notes", response_model=list[NoteRouteResponse])
    def notes(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(runs_ledger, case_id, identity(request))
        return publications.list_notes(case_id)

    @app.post("/api/cases/{case_id}/notes", status_code=201, response_model=NoteRouteResponse)
    def write_note(case_id: str, payload: NoteRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        return publications.create_note(case_id, who.subject, payload.body)

    @app.post("/api/cases/{case_id}/notes/{note_id}/promote", response_model=NoteRouteResponse)
    def promote(case_id: str, note_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            return publications.promote_note(case_id, note_id, who.subject)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="note not found") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/assumptions", response_model=list[AssumptionResponse])
    def assumptions(case_id: str, request: Request) -> list[dict[str, Any]]:
        require_case(runs_ledger, case_id, identity(request))
        return publications.list_assumptions(case_id)

    @app.post("/api/cases/{case_id}/assumptions", status_code=201, response_model=AssumptionResponse)
    def write_assumption(case_id: str, payload: AssumptionRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            return publications.create_assumption(
                case_id,
                who.subject,
                payload.statement,
                payload.evidence_ids,
                payload.affected_module_ids,
                payload.supporting_claim,
                payload.conflicting_claim,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/rv", response_model=RVRouteResponse)
    def rv(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        return compare_universe(publications, case_id, accepted_snapshot(runs_ledger, case_id))

    @app.post("/api/cases/{case_id}/rv", status_code=201, response_model=RVUniverseResponse)
    def write_rv(case_id: str, payload: RVUniverseRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            return save_universe(publications, case_id, who.subject, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/rv/loan-universes/active", response_model=ActiveLoanUniverseRouteResponse)
    def active_loan_universe(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        active = sources_catalog.active_loan_universe(case_id)
        if not active:
            return {"status": "NO_ACTIVE_UNIVERSE", "universe": None, "rows": []}
        rows = active.pop("rows")
        return {"status": "ACTIVE", "universe": active, "rows": rows}

    @app.post(
        "/api/cases/{case_id}/rv/loan-universes",
        status_code=201,
        response_model=LoanUniverseResponse,
        responses={200: {"model": LoanUniverseResponse}},
    )
    def import_case_loan_universe(
        case_id: str,
        payload: LoanUniverseImportRequest,
        request: Request,
        response: Response,
    ) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            record, created = import_loan_source(
                sources_catalog,
                settings.storage_dir,
                case_id,
                payload.source_id,
                who.subject,
            )
        except LoanUniverseImportRejected as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RV_WORKBOOK_INVALID",
                    "message": "Workbook rejected; the prior active universe is unchanged.",
                    "universe_id": exc.record["id"],
                    "findings": exc.record["findings"],
                },
            ) from exc
        except LoanUniverseSourceError as exc:
            status_code = {
                "RV_SOURCE_NOT_FOUND": 404,
                "RV_SOURCE_TYPE_INVALID": 415,
                "RV_SOURCE_WITHDRAWN": 409,
                "RV_SOURCE_BYTES_UNAVAILABLE": 409,
            }.get(exc.code, 422)
            raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.detail}) from exc
        if not created:
            response.status_code = 200
        return record

    @app.get("/api/cases/{case_id}/model", response_model=ModelReadinessRouteResponse)
    def model(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        return model_readiness.readiness(case_id)

    @app.get("/api/cases/{case_id}/models", response_model=ModelListResponse)
    def models(case_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        return {
            "readiness": model_readiness.readiness(case_id),
            "builds": [public_model_build(build) for build in models_ledger.list_builds(case_id)],
        }

    @app.post("/api/cases/{case_id}/models", status_code=202, response_model=QueueModelResponse)
    def queue_model(case_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        try:
            build, created = model_readiness.queue(case_id, who.subject)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="MODEL_NOT_READY") from exc
        if created and settings.environment != "production":
            model_runtime.schedule(build["id"], who.subject)
        return {"build": public_model_build(build), "created": created}

    @app.get("/api/cases/{case_id}/models/{build_id}", response_model=ModelBuildRouteResponse)
    def model_status(case_id: str, build_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        return public_model_build(model_for_case(case_id, build_id))

    @app.get("/api/cases/{case_id}/models/{build_id}/worksheet", response_model=ModelWorksheetResponse)
    def model_worksheet(case_id: str, build_id: str, request: Request) -> dict[str, Any]:
        require_case(runs_ledger, case_id, identity(request))
        build = model_for_case(case_id, build_id)
        if build.get("status") != "READY" or not isinstance(build.get("payload"), dict):
            raise HTTPException(status_code=409, detail="MODEL_NOT_READY")
        return {
            "build_id": build["id"],
            "input_fingerprint": build["input_fingerprint"],
            "payload_digest": build["payload_digest"],
            "qa": build["qa"],
            "payload": build["payload"],
        }

    @app.post("/api/cases/{case_id}/models/{build_id}/export", status_code=202, response_model=QueueModelExportResponse)
    def queue_model_export(case_id: str, build_id: str, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        model_for_case(case_id, build_id)
        try:
            build, queued = models_ledger.queue_export(build_id, who.subject)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="MODEL_EXPORT_NOT_READY") from exc
        if queued and settings.environment != "production":
            model_runtime.schedule_export(build_id, who.subject)
        return {"build": public_model_build(build), "queued": queued}

    @app.get("/api/cases/{case_id}/models/{build_id}/download")
    def download_model(case_id: str, build_id: str, request: Request) -> Response:
        who = identity(request)
        require_case(runs_ledger, case_id, who)
        build = model_for_case(case_id, build_id)
        export = build.get("export") or {}
        key = export.get("vault_key")
        if export.get("status") != "READY" or not isinstance(key, str):
            raise HTTPException(status_code=409, detail="MODEL_EXPORT_NOT_READY")
        root = settings.storage_dir.resolve()
        candidate = root / key
        try:
            path = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail="MODEL_EXPORT_UNAVAILABLE") from exc
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(status_code=409, detail="MODEL_EXPORT_UNAVAILABLE")
        size = path.stat().st_size
        expected_size = export.get("size")
        if (
            not isinstance(expected_size, int)
            or expected_size <= 0
            or expected_size > MAX_EXPORT_BYTES
            or size != expected_size
        ):
            raise HTTPException(status_code=409, detail="MODEL_EXPORT_INTEGRITY_FAILED")
        with path.open("rb") as exported:
            checksum = hashlib.file_digest(exported, "sha256").hexdigest()
        if checksum != export.get("sha256"):
            raise HTTPException(status_code=409, detail="MODEL_EXPORT_INTEGRITY_FAILED")
        models_ledger.record_export_download(build_id, case_id, who.subject)
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{build_id}.xlsx",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.post("/api/cases/{case_id}/reports/freeze", status_code=201, response_model=ReportRouteResponse)
    def freeze(case_id: str, payload: FreezeReportRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        snapshot_value = accepted_snapshot(runs_ledger, case_id)
        thesis_value = next((value for value in publications.list_theses(case_id) if value["version"] == payload.thesis_version), None)
        recommendation_value = recommendation_state(runs_ledger, case_id, next((value for value in publications.list_recommendations(case_id) if value["version"] == payload.recommendation_version), None))
        model_build = (
            model_for_case(case_id, payload.model_build_id)
            if payload.model_build_id
            else None
        )
        try:
            return freeze_report(
                publications,
                case_id,
                who.subject,
                snapshot_value,
                thesis_value,
                recommendation_value,
                model_build,
                include_model_export=payload.include_model_export,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/reports", response_model=ReportRouteResponse | None)
    def reports(case_id: str, request: Request) -> dict[str, Any] | None:
        require_case(runs_ledger, case_id, identity(request))
        return publications.get_report(case_id)

    @app.post("/api/cases/{case_id}/reports/approve", response_model=ReportRouteResponse)
    def approve(case_id: str, payload: ApproveRequest, request: Request) -> dict[str, Any]:
        who = identity(request)
        require_case(runs_ledger, case_id, who, write=True)
        require_role(who, "APPROVER", "ADMIN")
        try:
            return publications.approve_report(
                case_id,
                who.subject,
                payload.expected_status,
                payload.preview_digest,
                payload.input_fingerprint,
                payload.comment,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/reports/export/{format_name}")
    def export_report(case_id: str, format_name: str, request: Request) -> Response:
        who = identity(request)
        require_case(runs_ledger, case_id, who)
        report = publications.get_report(case_id)
        if not report or report["status"] != "APPROVED":
            raise HTTPException(status_code=409, detail="approved frozen report required")
        if format_name == "md":
            return Response(report["markdown"], media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={report['id']}.md"})
        if format_name == "pdf":
            return Response(render_pdf(report), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report['id']}.pdf"})
        if format_name == "xlsx":
            return Response(render_xlsx(report), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={report['id']}.xlsx"})
        raise HTTPException(status_code=404, detail="unknown export format")

    @app.get("/api/admin/audit", response_model=list[AuditRouteResponse])
    def audit(request: Request) -> list[dict[str, Any]]:
        admin_step_up(request)
        return publications.list_audit()

    @app.get("/api/admin/bundle", response_model=AdminBundleResponse)
    def admin_bundle(request: Request) -> dict[str, Any]:
        admin_step_up(request)
        return {"build_id": bundle.build_id, "integrity": bundle.verify(), "drafts": publications.list_methodology_drafts()}

    @app.get("/api/admin/drafts", response_model=list[MethodologyDraftResponse])
    def methodology_drafts(request: Request) -> list[dict[str, Any]]:
        admin_step_up(request)
        return publications.list_methodology_drafts()

    @app.post("/api/admin/drafts", status_code=201, response_model=MethodologyDraftResponse)
    def create_methodology_draft(payload: MethodologyDraftRequest, request: Request) -> dict[str, Any]:
        who = admin_step_up(request)
        module_ids = {item["module_id"] for item in bundle.catalog["modules"]}
        if payload.expected_build_id != bundle.build_id or payload.module_id not in module_ids:
            raise HTTPException(status_code=422, detail="draft authority identity is not current")
        if payload.before == payload.after:
            raise HTTPException(status_code=422, detail="draft must change a governed value")
        draft = {
            "expected_build_id": payload.expected_build_id,
            "module_id": payload.module_id,
            "field": payload.field,
            "before": payload.before,
            "after": payload.after,
            "rationale": payload.rationale,
            "semantic_diff": {"before": payload.before, "after": payload.after},
        }
        return publications.create_methodology_draft(draft, who.subject)

    @app.post("/api/admin/drafts/{draft_id}/validate", response_model=MethodologyDraftResponse)
    def validate_methodology_draft(draft_id: str, request: Request) -> dict[str, Any]:
        who = admin_step_up(request)
        draft = next(
            (item for item in publications.list_methodology_drafts() if item["id"] == draft_id),
            None,
        )
        if draft is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if draft["expected_build_id"] != bundle.build_id:
            raise HTTPException(
                status_code=422,
                detail="draft does not validate against the current authority",
            )
        try:
            return publications.validate_methodology_draft(draft_id, who.subject)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="draft not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/admin/drafts/{draft_id}/confirm", response_model=MethodologyDraftResponse)
    def confirm_methodology_draft(draft_id: str, payload: ConfirmDraftRequest, request: Request) -> dict[str, Any]:
        who = admin_step_up(request)
        draft = next(
            (item for item in publications.list_methodology_drafts() if item["id"] == draft_id),
            None,
        )
        if draft is None:
            raise HTTPException(status_code=404, detail="draft not found")
        signature = digest({"draft": draft["digest"], "build_id": bundle.build_id, "confirmation": payload.confirmation})
        try:
            return publications.confirm_methodology_draft(
                draft_id, who.subject, signature
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/admin/recipes/validate", response_model=VisualRecipeValidationResponse)
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
