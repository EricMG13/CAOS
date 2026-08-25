from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IdentityResponse(WireModel):
    subject: str
    email: str
    role: str
    destinations: list[str]


class CaseResponse(WireModel):
    id: str
    name: str
    issuer: str
    sector: str
    created_by: str
    created_at: str
    members: dict[str, str]
    accepted_snapshot_id: str | None
    visible_snapshot_id: str | None
    current_execution_id: str | None


class SourceSetResponse(WireModel):
    id: str
    case_id: str
    version: int
    source_ids: list[str]
    created_by: str
    created_at: str


class SourceBlockResponse(WireModel):
    block_id: str
    text: str
    locator: dict[str, str | int]
    confidence: str
    untrusted_data: bool
    extractor_version: str


class SourceBaseResponse(WireModel):
    id: str
    case_id: str
    filename: str
    media_type: str
    bytes: int
    sha256: str
    created_by: str
    created_at: str
    blocks: list[SourceBlockResponse]
    withdrawn: bool


class UploadedSourceResponse(SourceBaseResponse):
    source_set: SourceSetResponse


class StoredSourceResponse(SourceBaseResponse):
    pass


class PromotedNoteSourceResponse(SourceBaseResponse):
    source_kind: Literal["analyst_note"]


class SourceResponse(
    RootModel[UploadedSourceResponse | PromotedNoteSourceResponse | StoredSourceResponse]
):
    pass


class RunNodeResponse(WireModel):
    id: str
    run_id: str
    case_id: str
    module_id: str
    stage: int
    dependencies: list[str]
    status: str
    attempt: int
    artifact_id: str | None
    error: dict[str, Any] | None


class RunEventResponse(WireModel):
    id: int
    event: str
    at: str
    data: dict[str, Any]


class RunResponse(WireModel):
    id: str
    case_id: str
    status: str
    plan: dict[str, Any]
    node_ids: list[str]
    nodes: list[RunNodeResponse]
    events: list[RunEventResponse]
    current_node_id: str | None
    accepted_snapshot_id: str | None
    upgraded_from_run_id: str | None
    created_by: str
    created_at: str
    error: dict[str, Any] | None


class SnapshotArtifactResponse(WireModel):
    id: str
    module_id: str
    digest: str


class SnapshotResponse(WireModel):
    id: str
    case_id: str
    run_id: str
    source_set_id: str
    source_set_version: int
    artifacts: list[SnapshotArtifactResponse]
    digest: str
    previous_snapshot_id: str | None
    accepted_at: str


class ArtifactResponse(WireModel):
    id: str
    case_id: str
    run_id: str
    module_id: str
    payload: dict[str, Any]
    markdown: str
    digest: str
    input_fingerprint: str
    created_by: str
    created_at: str


class ErrorResponse(WireModel):
    code: str
    detail: str


class CalculationRuntimeResponse(WireModel):
    name: str
    version: str
    sha256: str


class ModelRequirementResponse(WireModel):
    module_id: str
    status: str


class ModelReadinessSnapshotResponse(WireModel):
    id: str
    run_id: str
    digest: str


class ModelReadinessSourceSetResponse(WireModel):
    id: str
    version: int
    digest: str


class ModelBlockerResponse(WireModel):
    code: str
    detail: str


class ModelReadinessResponse(WireModel):
    status: str
    module_id: str
    accepted_snapshot: ModelReadinessSnapshotResponse | None
    source_set: ModelReadinessSourceSetResponse | None
    requirements: list[ModelRequirementResponse]
    calculation_runtime: CalculationRuntimeResponse | None
    worksheet_schema_version: str
    blockers: list[ModelBlockerResponse]
    build: "ModelBuildResponse | None"


class ModelExportResponse(WireModel):
    status: str
    error: ErrorResponse | None


class ModelBuildBaseResponse(WireModel):
    id: str
    case_id: str
    accepted_run_id: str
    accepted_snapshot_id: str
    source_set_id: str
    input_fingerprint: str
    queued_at: str
    export: ModelExportResponse
    worksheet_schema_version: str
    calculation_runtime: CalculationRuntimeResponse


class QueuedModelBuildResponse(ModelBuildBaseResponse):
    status: Literal["QUEUED"]
    started_at: None
    completed_at: None
    error: None


class FailedModelBuildResponse(ModelBuildBaseResponse):
    status: Literal["FAILED"]
    started_at: str | None
    completed_at: str
    error: ErrorResponse


class ModelSemanticCheckResponse(WireModel):
    check_id: str
    status: str
    period_id: str | None
    difference: float | int | str | None
    tolerance: float | int | str | None
    detail: str


class ModelSourceManifestResponse(WireModel):
    module_id: str
    filename: str
    sha256: str


class ModelQualityResponse(WireModel):
    status: Literal["PASS"]
    semantic_checks: list[ModelSemanticCheckResponse]
    semantic_check_count: int
    formula_count: int
    worksheet_cell_count: int
    limitation_flags: list[str]
    validation_warnings: list[str]
    source_manifest: list[ModelSourceManifestResponse]


class ReadyModelBuildResponse(ModelBuildBaseResponse):
    status: Literal["READY"]
    started_at: str | None
    completed_at: str
    error: None
    qa: ModelQualityResponse
    payload_digest: str


class ModelBuildResponse(
    RootModel[QueuedModelBuildResponse | FailedModelBuildResponse | ReadyModelBuildResponse]
):
    pass


class ReportContentResponse(WireModel):
    case_id: str
    snapshot_id: str
    snapshot_digest: str
    thesis_version: int
    recommendation_version: int
    include_model: bool
    model: dict[str, Any] | None
    input_fingerprint: str


class ReportResponse(WireModel):
    id: str
    case_id: str
    status: str
    created_by: str
    created_at: str
    content: ReportContentResponse
    snapshot_digest: str
    input_fingerprint: str
    preview_digest: str
    digest: str
    markdown: str


class AuditEventBaseResponse(WireModel):
    id: str
    actor: str
    at: str


class CaseCreatedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["case.created"]
    case_id: str


class SourceIngestedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["source.ingested"]
    case_id: str
    source_id: str
    sha256: str


class CaseSourceAuditEventResponse(AuditEventBaseResponse):
    action: Literal["source.withdrawn"]
    case_id: str
    source_id: str


class RunCreatedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["run.created"]
    case_id: str
    run_id: str


class SnapshotAcceptedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["snapshot.accepted"]
    case_id: str
    run_id: str
    snapshot_id: str


class SnapshotVisibleSwitchedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["snapshot.visible_switched"]
    case_id: str
    snapshot_id: str


class CaseBuildAuditEventResponse(AuditEventBaseResponse):
    action: Literal[
        "model.queued",
        "model.retried",
        "model.calculate.succeeded",
        "model.export.succeeded",
        "model.export.downloaded",
    ]
    case_id: str
    build_id: str


class CaseBuildFailedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["model.calculate.failed", "model.export.failed"]
    case_id: str
    build_id: str
    code: str


class ThesisVersionedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["thesis.versioned"]
    case_id: str
    version: int


class RecommendationVersionedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["recommendation.versioned"]
    case_id: str
    version: int


class CaseReportAuditEventResponse(AuditEventBaseResponse):
    action: Literal["report.frozen", "report.approved"]
    case_id: str
    report_id: str


class MethodologyDraftCreatedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["methodology.draft_created"]
    draft_id: str
    module_id: str


class MethodologyDraftValidatedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["methodology.draft_validated"]
    draft_id: str


class MethodologyDraftConfirmedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["methodology.draft_confirmed"]
    draft_id: str
    signature: str


class CaseMemberAddedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["case.member_added"]
    case_id: str
    member: str
    role: str


class CaseVersionedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["rv.universe_versioned"]
    case_id: str
    version: int


class CaseNoteAuditEventResponse(AuditEventBaseResponse):
    action: Literal["note.created"]
    case_id: str
    note_id: str


class CaseNoteSourceAuditEventResponse(AuditEventBaseResponse):
    action: Literal["note.promoted"]
    case_id: str
    note_id: str
    source_id: str


class CaseAssumptionAuditEventResponse(AuditEventBaseResponse):
    action: Literal["assumption.created"]
    case_id: str
    assumption_id: str


class ResearchPlanApprovedAuditEventResponse(AuditEventBaseResponse):
    action: Literal["research.plan_approved"]
    case_id: str
    run_id: str
    plan_hash: str


AuditEvent = Annotated[
    CaseCreatedAuditEventResponse
    | SourceIngestedAuditEventResponse
    | CaseSourceAuditEventResponse
    | RunCreatedAuditEventResponse
    | SnapshotAcceptedAuditEventResponse
    | SnapshotVisibleSwitchedAuditEventResponse
    | CaseBuildAuditEventResponse
    | CaseBuildFailedAuditEventResponse
    | ThesisVersionedAuditEventResponse
    | RecommendationVersionedAuditEventResponse
    | CaseReportAuditEventResponse
    | MethodologyDraftCreatedAuditEventResponse
    | MethodologyDraftValidatedAuditEventResponse
    | MethodologyDraftConfirmedAuditEventResponse
    | CaseMemberAddedAuditEventResponse
    | CaseVersionedAuditEventResponse
    | CaseNoteAuditEventResponse
    | CaseNoteSourceAuditEventResponse
    | CaseAssumptionAuditEventResponse
    | ResearchPlanApprovedAuditEventResponse,
    Field(discriminator="action"),
]


class AuditEventResponse(RootModel[AuditEvent]):
    pass


class SemanticDiffResponse(WireModel):
    before: str
    after: str


class MethodologyDraftBaseResponse(WireModel):
    id: str
    expected_build_id: str
    module_id: str
    field: str
    before: str
    after: str
    rationale: str
    created_by: str
    created_at: str
    semantic_diff: SemanticDiffResponse
    digest: str


class DraftMethodologyDraftResponse(MethodologyDraftBaseResponse):
    status: Literal["DRAFT"]


class ValidatedMethodologyDraftResponse(MethodologyDraftBaseResponse):
    status: Literal["VALIDATED"]
    validated_by: str
    validated_at: str


class ConfirmedMethodologyDraftResponse(ValidatedMethodologyDraftResponse):
    status: Literal["CONFIRMED_PENDING_SIGNED_AUTHORITY"]
    confirmed_by: str
    confirmed_at: str
    signature: str


class MethodologyDraftResponse(
    RootModel[
        DraftMethodologyDraftResponse
        | ValidatedMethodologyDraftResponse
        | ConfirmedMethodologyDraftResponse
    ]
):
    pass
