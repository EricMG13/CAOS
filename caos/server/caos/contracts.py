from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Role(StrEnum):
    ANALYST = "ANALYST"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"
    READER = "READER"


class Depth(StrEnum):
    SCREEN = "screen"
    FULL = "full"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class SystemSignal(StrEnum):
    ATTRACTIVE = "ATTRACTIVE"
    FAIR = "FAIR"
    UNATTRACTIVE = "UNATTRACTIVE"


class Recommendation(StrEnum):
    OVERWEIGHT = "OVERWEIGHT"
    MARKET_WEIGHT = "MARKET WEIGHT"
    UNDERWEIGHT = "UNDERWEIGHT"
    NA = "N/A"


class WorkspaceTheme(StrEnum):
    DARK = "dark"
    LIGHT = "light"


PATHWAYS = {
    "FULL_CREDIT": "Full Credit",
    "EARNINGS_UPDATE": "Earnings Update",
    "COVENANT_REFINANCING": "Covenant & Refinancing",
    "RELATIVE_VALUE": "Relative Value",
    "DISTRESSED_RESTRUCTURING": "Distressed & Restructuring",
    "DEEP_RESEARCH": "Deep Research",
}

INTERNAL_PATHWAYS = (*PATHWAYS.keys(), "PORTFOLIO_DECISION", "DECISION_LEDGER")

DESTINATIONS = (
    "Cases",
    "Sources",
    "Run Console",
    "Deep-Dive",
    "RV Screener",
    "Command Center",
    "Model Builder",
    "Report Studio",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateCaseRequest(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    issuer: str = Field(min_length=1, max_length=160)
    sector: str = Field(default="Unclassified", max_length=120)


class MemberRequest(StrictModel):
    subject: str = Field(min_length=1, max_length=200)
    role: Role = Role.READER


class MethodologyDraftRequest(StrictModel):
    expected_build_id: str = Field(min_length=64, max_length=64)
    module_id: str = Field(min_length=3, max_length=40)
    field: Literal["reader_question", "required_decision_drivers", "prohibited_conclusions", "visual_recipe"]
    before: str = Field(min_length=1, max_length=4000)
    after: str = Field(min_length=1, max_length=4000)
    rationale: str = Field(min_length=1, max_length=2000)


class ConfirmDraftRequest(StrictModel):
    confirmation: Literal["CONFIRM_DRAFT"]


ResearchBriefItem = Annotated[str, Field(min_length=1, max_length=200)]


class ResearchBrief(StrictModel):
    research_question: str = Field(min_length=1, max_length=400)
    decision_context: str = Field(min_length=1, max_length=400)
    as_of_date: date
    time_horizon: str = Field(min_length=1, max_length=200)
    must_answer: list[ResearchBriefItem] = Field(default_factory=list, max_length=10)
    exclusions: list[ResearchBriefItem] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def combined_item_cap(self) -> ResearchBrief:
        if not all(value.strip() for value in (self.research_question, self.decision_context, self.time_horizon, *self.must_answer, *self.exclusions)):
            raise ValueError("research brief text must not be blank")
        if len(self.must_answer) + len(self.exclusions) > 10:
            raise ValueError("must_answer and exclusions may contain at most 10 entries combined")
        return self


class StartRunRequest(StrictModel):
    pathway: str
    depth: Depth
    focus_questions: list[str] = Field(default_factory=list, max_length=5)
    research_brief: ResearchBrief | None = None

    @field_validator("pathway")
    @classmethod
    def known_pathway(cls, value: str) -> str:
        if value not in PATHWAYS:
            raise ValueError("unknown pathway")
        return value

    @model_validator(mode="after")
    def research_pathway_contract(self) -> StartRunRequest:
        if self.pathway == "DEEP_RESEARCH":
            if self.depth is not Depth.FULL:
                raise ValueError("DEEP_RESEARCH requires full depth")
            if self.research_brief is None:
                raise ValueError("DEEP_RESEARCH requires a research brief")
        elif self.research_brief is not None:
            raise ValueError("research_brief is only valid for DEEP_RESEARCH")
        return self


class ApproveResearchPlanRequest(StrictModel):
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ThesisRequest(StrictModel):
    expected_version: int = Field(ge=0)
    core_thesis: str = Field(min_length=1, max_length=4000)
    drivers: list[str] = Field(default_factory=list, max_length=12)
    risks: list[str] = Field(default_factory=list, max_length=12)
    catalysts: list[str] = Field(default_factory=list, max_length=12)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=12)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)


class RecommendationRow(StrictModel):
    instrument_id: str = Field(min_length=1, max_length=120)
    instrument: str = Field(min_length=1, max_length=160)
    recommendation: Recommendation
    rationale: str = Field(min_length=1, max_length=2000)
    primary: bool = False


class RecommendationMatrixRequest(StrictModel):
    expected_version: int = Field(ge=0)
    market_snapshot_id: str = Field(min_length=1, max_length=120)
    rows: list[RecommendationRow] = Field(min_length=1, max_length=50)
    analytical_dependency_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("rows")
    @classmethod
    def complete_rows(cls, value: list[RecommendationRow]) -> list[RecommendationRow]:
        if any(not row.recommendation for row in value):
            raise ValueError("blank recommendations are not allowed")
        primaries = sum(row.primary for row in value)
        if primaries != 1:
            raise ValueError("select exactly one primary instrument")
        return value


class ReportInputsRequest(StrictModel):
    thesis: ThesisRequest
    recommendations: RecommendationMatrixRequest


class NoteRequest(StrictModel):
    body: str = Field(min_length=1, max_length=12000)


class AssumptionRequest(StrictModel):
    statement: str = Field(min_length=1, max_length=2000)
    supporting_claim: str = Field(default="", max_length=2000)
    conflicting_claim: str = Field(default="", max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    affected_module_ids: list[str] = Field(default_factory=list, max_length=30)


class RVRow(StrictModel):
    instrument: str = Field(min_length=1, max_length=160)
    observation_date: str = Field(min_length=10, max_length=10)
    source_version: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    price: float | None = None
    yield_bps: float | None = None
    spread_bps: float | None = None
    seniority: str = Field(min_length=1, max_length=40)
    maturity: str = Field(min_length=10, max_length=10)
    duration: float | None = None

    @field_validator("price", "yield_bps", "spread_bps", "duration")
    @classmethod
    def finite_number(cls, value: float | None) -> float | None:
        return finite_or_none(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value


class RVUniverseRequest(StrictModel):
    source_version: str = Field(min_length=1, max_length=120)
    rows: list[RVRow] = Field(min_length=1, max_length=500)


class FreezeReportRequest(StrictModel):
    thesis_version: int = Field(ge=1)
    recommendation_version: int = Field(ge=1)
    model_build_id: str | None = Field(default=None, min_length=1, max_length=120)
    include_model: Literal[False] = False


class ApproveRequest(StrictModel):
    expected_status: Literal["PENDING_APPROVAL"] = "PENDING_APPROVAL"
    preview_digest: str | None = None
    input_fingerprint: str | None = None
    comment: str = Field(default="", max_length=2000)


class SnapshotSwitchRequest(StrictModel):
    snapshot_id: str = Field(min_length=1, max_length=120)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def clean_json(value: Any) -> Any:
    """Reject non-finite values before they can reach an API or artifact."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite numeric values are not serializable")
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    return value


def finite_or_none(value: float | None) -> float | None:
    if value is not None and not math.isfinite(value):
        raise ValueError("non-finite numeric value")
    return value
