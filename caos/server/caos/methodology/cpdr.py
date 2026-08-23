from __future__ import annotations

import json
import re
from collections import Counter
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


ShortText = Annotated[str, Field(min_length=1, max_length=500)]
LongText = Annotated[str, Field(min_length=1, max_length=8_000)]
Identifier = Annotated[str, Field(min_length=1, max_length=160)]


class CPDRValidationError(ValueError):
    pass


def _host_coverage_status(
    claim: MaterialClaim,
    conflict_claims: set[str],
    gapped_workstreams: set[str],
    returned_evidence: dict[tuple[str, str], dict[str, str]],
) -> str:
    pairs = [(ref.source_id, ref.block_id) for ref in claim.evidence_refs]
    origins = {returned_evidence[pair]["origin_family"] for pair in pairs}
    authorities = {returned_evidence[pair]["authority_class"] for pair in pairs}
    if claim.claim_id in conflict_claims or claim.counter_evidence_refs:
        return "contradicted"
    if claim.workstream_id in gapped_workstreams:
        return "gap"
    source_characterisation_is_sufficient = claim.claim_type == "source_characterisation" and not claim.material
    if pairs and (source_characterisation_is_sufficient or "primary_authority" in authorities or len(origins) >= 2):
        return "adequate"
    return "gap"


def _host_claim_provenance(
    claim: MaterialClaim,
    host_status: str,
    returned_evidence: dict[tuple[str, str], dict[str, str]],
) -> tuple[str, int]:
    if host_status == "contradicted":
        return "Conflicting", 25
    if host_status == "gap":
        return "Insufficient Information", 0
    evidence = [returned_evidence[(ref.source_id, ref.block_id)] for ref in claim.evidence_refs]
    if any(item["authority_class"] == "primary_authority" for item in evidence):
        return "Directly Sourced", 100
    if len({item["origin_family"] for item in evidence}) >= 2:
        return "Weak Lineage", 70
    return "Weak Lineage", 50


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, strict=True)


class EvidenceReference(_StrictModel):
    source_id: Identifier
    block_id: Identifier


class WorkstreamFinding(_StrictModel):
    workstream_id: Identifier
    finding: LongText
    claim_ids: list[Identifier] = Field(default_factory=list, max_length=50)
    status: Literal["complete", "gapped"]


class MaterialClaim(_StrictModel):
    claim_id: Identifier
    claim: LongText
    claim_type: Literal["fact", "source_characterisation", "inference", "analyst_judgment"]
    workstream_id: Identifier
    lineage: Literal[
        "Directly Sourced",
        "Calculated",
        "Assumption-Based",
        "Analyst Inference",
        "Weak Lineage",
        "Untraced",
        "Conflicting",
        "Insufficient Information",
    ]
    evidence_refs: list[EvidenceReference] = Field(default_factory=list, max_length=50)
    counter_evidence_refs: list[EvidenceReference] = Field(default_factory=list, max_length=50)
    coverage_status: Literal["adequate", "gap", "contradicted"]
    confidence: int = Field(ge=0, le=100)
    material: bool
    numeric_value: float | None = None
    entity: ShortText | None = None
    period: ShortText | None = None
    unit_currency: ShortText | None = None
    perimeter: ShortText | None = None

    @model_validator(mode="after")
    def numeric_context(self) -> MaterialClaim:
        contains_number = re.search(r"\d", self.claim) is not None
        if contains_number and self.numeric_value is None:
            raise ValueError("numeric claim text requires an explicit numeric_value")
        if self.numeric_value is not None and not all((self.entity, self.period, self.unit_currency, self.perimeter)):
            raise ValueError("numeric context requires entity, period, unit/currency and perimeter")
        return self


class EvidenceRow(_StrictModel):
    evidence_id: Identifier
    source_id: Identifier
    source_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    block_id: Identifier
    locator: ShortText
    extractor_version: ShortText
    source_confidence: ShortText
    quoted: bool
    entity: ShortText | None = None
    period: ShortText | None = None
    unit_currency: ShortText | None = None
    perimeter: ShortText | None = None
    lineage: Literal[
        "Directly Sourced",
        "Calculated",
        "Assumption-Based",
        "Analyst Inference",
        "Weak Lineage",
        "Untraced",
        "Conflicting",
        "Insufficient Information",
    ]
    independence_family: ShortText
    numeric_value: float | None = None

    @model_validator(mode="after")
    def numeric_context(self) -> EvidenceRow:
        if self.numeric_value is not None and not all((self.entity, self.period, self.unit_currency, self.perimeter)):
            raise ValueError("numeric context requires entity, period, unit/currency and perimeter")
        return self


class ConflictRow(_StrictModel):
    conflict_id: Identifier
    claim_ids: list[Identifier] = Field(min_length=1, max_length=50)
    evidence_refs: list[EvidenceReference] = Field(min_length=2, max_length=50)
    description: LongText
    status: Literal["resolved", "unresolved"]


class GapRow(_StrictModel):
    workstream_id: Identifier
    description: LongText
    material: bool


class QAFinding(_StrictModel):
    severity: Literal["CRITICAL", "MATERIAL", "MINOR"]
    finding: LongText


class ScopeAdherenceRow(_StrictModel):
    kind: Literal["must_answer", "exclusion"]
    item: ShortText
    workstream_id: Identifier | None = None
    respected: bool


class CPDRPayload(_StrictModel):
    module_id: Literal["CP-DR"]
    run_id: Identifier
    case_id: Identifier
    profile_id: Identifier
    selection_id: Identifier
    source_set_id: Identifier
    source_set_version: int = Field(ge=1)
    approved_plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    upstream_digests: list[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]] = Field(default_factory=list, max_length=50)
    scope_type: Literal["issuer"]
    scope_key: Identifier
    subject_name: ShortText
    research_question: ShortText
    reporting_period: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    source_mode: Literal["supplied_only"]
    workstream_findings: list[WorkstreamFinding] = Field(min_length=1, max_length=20)
    material_claims: list[MaterialClaim] = Field(min_length=1, max_length=200)
    evidence: list[EvidenceRow] = Field(default_factory=list, max_length=500)
    conflicts: list[ConflictRow] = Field(default_factory=list, max_length=100)
    gaps: list[GapRow] = Field(default_factory=list, max_length=100)
    qa_findings: list[QAFinding] = Field(default_factory=list, max_length=100)
    scope_adherence: list[ScopeAdherenceRow] = Field(default_factory=list, max_length=20)
    direct_answer: LongText
    causal_synthesis: LongText
    implications_scenarios: list[LongText] = Field(min_length=1, max_length=30)
    coverage_score: int = Field(ge=0, le=100)
    research_status: Literal["Complete", "Complete with Gaps", "Blocked"]
    research_stop_reason: Literal["coverage_satisfied", "budget_exhausted", "sources_exhausted", "blocked", "user_stopped"]

    @field_validator("upstream_digests")
    @classmethod
    def unique_upstream_digests(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("upstream digests must be unique")
        return values


HOST_IDENTITY_FIELDS = (
    "module_id",
    "run_id",
    "case_id",
    "profile_id",
    "selection_id",
    "source_set_id",
    "source_set_version",
    "approved_plan_hash",
    "upstream_digests",
    "scope_type",
    "scope_key",
    "subject_name",
    "research_question",
    "reporting_period",
    "source_mode",
)


def validate_cpdr_payload(
    value: dict[str, Any],
    host_identity: dict[str, Any],
    approved_workstream_ids: set[str],
    returned_evidence: dict[tuple[str, str], dict[str, str]],
    approved_plan: dict[str, Any] | None = None,
    approved_brief: dict[str, Any] | None = None,
) -> CPDRPayload:
    try:
        payload = CPDRPayload.model_validate(value)
    except ValidationError as exc:
        raise CPDRValidationError(str(exc)) from exc

    observed = payload.model_dump(mode="json")
    mismatches = [field for field in HOST_IDENTITY_FIELDS if observed[field] != host_identity.get(field)]
    if mismatches:
        raise CPDRValidationError("host identity mismatch: " + ", ".join(mismatches))

    findings = {row.workstream_id for row in payload.workstream_findings}
    if len(findings) != len(payload.workstream_findings):
        raise CPDRValidationError("workstream finding IDs must be unique")
    explicit_gaps = {row.workstream_id for row in payload.gaps}
    missing_workstreams = approved_workstream_ids - findings - explicit_gaps
    unknown_workstreams = (findings | explicit_gaps | {row.workstream_id for row in payload.material_claims}) - approved_workstream_ids
    if missing_workstreams or unknown_workstreams:
        raise CPDRValidationError(
            f"workstream coverage mismatch: missing={sorted(missing_workstreams)} unknown={sorted(unknown_workstreams)}"
        )

    claims = {row.claim_id: row for row in payload.material_claims}
    if len(claims) != len(payload.material_claims):
        raise CPDRValidationError("claim IDs must be unique")
    evidence_ids = {row.evidence_id for row in payload.evidence}
    if len(evidence_ids) != len(payload.evidence):
        raise CPDRValidationError("evidence IDs must be unique")
    conflict_ids = {row.conflict_id for row in payload.conflicts}
    if len(conflict_ids) != len(payload.conflicts):
        raise CPDRValidationError("conflict IDs must be unique")
    for conflict in payload.conflicts:
        refs = [(ref.source_id, ref.block_id) for ref in conflict.evidence_refs]
        if len(refs) != len(set(refs)) or len(conflict.claim_ids) != len(set(conflict.claim_ids)):
            raise CPDRValidationError("conflict references and claim IDs must be unique")
    cited_pairs = {
        (ref.source_id, ref.block_id)
        for claim in payload.material_claims
        for ref in (*claim.evidence_refs, *claim.counter_evidence_refs)
    } | {(ref.source_id, ref.block_id) for conflict in payload.conflicts for ref in conflict.evidence_refs}
    evidence_pairs = {(row.source_id, row.block_id) for row in payload.evidence}
    if len(evidence_pairs) != len(payload.evidence):
        raise CPDRValidationError("source/block evidence identities must be unique")
    if not cited_pairs | evidence_pairs <= returned_evidence.keys():
        raise CPDRValidationError("every citation and evidence row must reference a block returned by this run")
    if not cited_pairs <= evidence_pairs:
        raise CPDRValidationError("every citation must appear exactly once in the evidence registry")
    for row in payload.evidence:
        returned = returned_evidence[(row.source_id, row.block_id)]
        if (
            row.source_digest != returned["source_digest"]
            or row.locator != returned["locator"]
            or row.extractor_version != returned["extractor_version"]
            or row.source_confidence != returned["confidence"]
        ):
            raise CPDRValidationError("evidence metadata must match the host-returned block")
    if any(claim_id not in claims for row in payload.workstream_findings for claim_id in row.claim_ids):
        raise CPDRValidationError("workstream findings reference an unknown claim")
    finding_claims = {(row.workstream_id, claim_id) for row in payload.workstream_findings for claim_id in row.claim_ids}
    if any((claim.workstream_id, claim.claim_id) not in finding_claims for claim in payload.material_claims):
        raise CPDRValidationError("every claim must appear in its workstream finding")
    conflict_claims = {claim_id for row in payload.conflicts for claim_id in row.claim_ids}
    gapped_workstreams = {row.workstream_id for row in payload.workstream_findings if row.status == "gapped"} | {
        row.workstream_id for row in payload.gaps if row.material
    }
    for conflict in payload.conflicts:
        origins = {returned_evidence[(ref.source_id, ref.block_id)]["origin_family"] for ref in conflict.evidence_refs}
        if len(origins) < 2:
            raise CPDRValidationError("conflict evidence must preserve distinct host origin families")
    host_statuses: dict[str, str] = {}
    for claim in payload.material_claims:
        host_status = _host_coverage_status(claim, conflict_claims, gapped_workstreams, returned_evidence)
        host_statuses[claim.claim_id] = host_status
        if claim.coverage_status != host_status:
            raise CPDRValidationError(f"provider coverage must equal host coverage for {claim.claim_id}: {host_status}")

    canonical_evidence = []
    for row in payload.evidence:
        returned = returned_evidence[(row.source_id, row.block_id)]
        canonical_evidence.append(
            row.model_copy(
                update={
                    "independence_family": returned["origin_family"],
                    "lineage": "Directly Sourced" if returned["authority_class"] == "primary_authority" else "Weak Lineage",
                }
            )
        )
    canonical_claims = []
    for claim in payload.material_claims:
        lineage, confidence = _host_claim_provenance(claim, host_statuses[claim.claim_id], returned_evidence)
        canonical_claims.append(claim.model_copy(update={"lineage": lineage, "confidence": confidence}))
    payload = payload.model_copy(update={"evidence": canonical_evidence, "material_claims": canonical_claims})

    material = [claim for claim in payload.material_claims if claim.material]
    if not material:
        raise CPDRValidationError("at least one material claim is required")
    adequate = sum(host_statuses[claim.claim_id] == "adequate" for claim in material)
    expected_coverage = round(adequate / len(material) * 100)
    if payload.coverage_score != expected_coverage:
        raise CPDRValidationError(f"coverage_score must equal host arithmetic ({expected_coverage})")

    conflicted_claims = {claim.claim_id for claim in payload.material_claims if claim.counter_evidence_refs or claim.coverage_status == "contradicted"}
    visible_conflicts = {claim_id for row in payload.conflicts for claim_id in row.claim_ids}
    if not conflicted_claims <= visible_conflicts:
        raise CPDRValidationError("contradictions must be visible in the conflict register")
    if any(claim_id not in claims for row in payload.conflicts for claim_id in row.claim_ids):
        raise CPDRValidationError("conflict register references an unknown claim")

    plan = approved_plan or {"workstreams": []}
    brief = approved_brief or {"must_answer": [], "exclusions": []}
    scope_items = [*brief.get("must_answer", []), *brief.get("exclusions", [])]
    if len(scope_items) != len(set(scope_items)):
        raise CPDRValidationError("approved scope items must be unique")
    assigned: dict[str, str] = {}
    for workstream in plan.get("workstreams", []):
        for question in workstream.get("assigned_questions", []):
            if question in assigned:
                raise CPDRValidationError("approved must-answer item is assigned more than once")
            assigned[question] = workstream.get("id")
    expected_scope = {("must_answer", item): assigned.get(item) for item in brief.get("must_answer", [])}
    expected_scope.update({("exclusion", item): None for item in brief.get("exclusions", [])})
    observed_scope = {(row.kind, row.item): row for row in payload.scope_adherence}
    if (
        len(observed_scope) != len(payload.scope_adherence)
        or set(observed_scope) != set(expected_scope)
        or any(not row.respected or row.workstream_id != expected_scope[key] for key, row in observed_scope.items())
        or any(kind == "must_answer" and workstream is None for (kind, _), workstream in expected_scope.items())
    ):
        raise CPDRValidationError("scope adherence must exactly cover approved questions and exclusions")

    has_material_gap = expected_coverage < 100 or any(row.status == "gapped" for row in payload.workstream_findings) or any(gap.material for gap in payload.gaps) or any(row.status == "unresolved" for row in payload.conflicts)
    if payload.research_status == "Complete" and (has_material_gap or payload.research_stop_reason != "coverage_satisfied"):
        raise CPDRValidationError("Complete status requires full coverage and coverage_satisfied")
    if payload.research_status == "Complete with Gaps" and not has_material_gap:
        raise CPDRValidationError("Complete with Gaps requires a material gap or unresolved conflict")
    if (payload.research_status == "Blocked") != (payload.research_stop_reason == "blocked"):
        raise CPDRValidationError("Blocked status and stop reason must agree")
    return payload


def confidence_inputs(payload: CPDRPayload, returned_evidence: dict[tuple[str, str], dict[str, str]]) -> dict[str, Any]:
    conflict_claims = {claim_id for row in payload.conflicts for claim_id in row.claim_ids}
    gapped_workstreams = {row.workstream_id for row in payload.workstream_findings if row.status == "gapped"} | {
        row.workstream_id for row in payload.gaps if row.material
    }
    lineage: Counter[str] = Counter()
    findings: Counter[str] = Counter()
    material = [claim for claim in payload.material_claims if claim.material]
    for claim in material:
        host_status = _host_coverage_status(claim, conflict_claims, gapped_workstreams, returned_evidence)
        if host_status == "contradicted":
            lineage["Conflicting"] += 1
        elif host_status == "gap":
            lineage["Insufficient Information"] += 1
            findings["MATERIAL"] += 1
        elif any(
            returned_evidence[(ref.source_id, ref.block_id)]["authority_class"] == "primary_authority"
            for ref in claim.evidence_refs
        ):
            lineage["Directly Sourced"] += 1
        else:
            lineage["Weak Lineage"] += 1
    findings["MATERIAL"] += sum(row.material for row in payload.gaps)
    findings["MATERIAL"] += sum(row.status == "unresolved" for row in payload.conflicts)
    if payload.research_status == "Blocked":
        findings["CRITICAL"] += 1
    adequate = sum(claim.coverage_status == "adequate" for claim in material)
    source_gate = "pass" if material and adequate == len(material) else "partial" if adequate else "fail"
    required = (
        payload.direct_answer,
        payload.causal_synthesis,
        payload.implications_scenarios,
        payload.workstream_findings,
        payload.material_claims,
        payload.evidence,
    )
    return {
        "lineage_counts": dict(lineage),
        "fields_present": sum(bool(value) for value in required),
        "fields_total": len(required),
        "source_gate": source_gate,
        "findings": {key: value for key, value in findings.items() if value},
    }


def render_cpdr_markdown(
    payload: CPDRPayload,
    confidence: dict[str, Any],
    analysis_date: str,
    upstream_artifacts: list[dict[str, str]],
) -> tuple[str, str]:
    def yaml_value(value: Any) -> str:
        if isinstance(value, dict):
            return "{" + ", ".join(f"{key}: {yaml_value(item)}" for key, item in value.items()) + "}"
        if isinstance(value, list):
            return "[" + ", ".join(yaml_value(item) for item in value) + "]"
        return json.dumps(value, ensure_ascii=True)

    filename = f"{payload.scope_key}_CP-DR_{analysis_date.replace('-', '')}.md"
    upstream = [
        {"module_id": item["module_id"], "run_id": payload.run_id, "period": payload.reporting_period}
        for item in upstream_artifacts
    ]
    limitations = [gap.description for gap in payload.gaps if gap.material][:20]
    warnings = [row.finding for row in payload.qa_findings][:20]
    committee_status = {
        "Passed": "Committee Ready" if payload.research_status == "Complete" else "Requires More Work",
        "Restricted": "Restricted",
        "Blocked": "Blocked",
    }[confidence["qa_status"]]
    frontmatter = {
        "module_id": "CP-DR",
        "module_name": "DeepResearch",
        "run_id": payload.run_id,
        "reporting_period": payload.reporting_period,
        "analysis_date": analysis_date,
        "confidence_score": confidence["confidence_score"],
        "confidence_band": confidence["confidence_band"],
        "qa_status": confidence["qa_status"],
        "committee_status": committee_status,
        "limitation_flags": limitations,
        "validation_warnings": warnings,
        "upstream_artifacts_used": upstream,
        "downstream_consumers": ["CP-X", "CP-1", "CP-2", "CP-5A", "CP-6", "CP-6A"],
        "scope_type": payload.scope_type,
        "scope_key": payload.scope_key,
        "subject_name": payload.subject_name,
        "research_question": payload.research_question,
        "source_mode": "supplied_only",
        "approved_plan_hash": payload.approved_plan_hash,
        "coverage_score": payload.coverage_score,
        "research_status": payload.research_status,
        "research_stop_reason": payload.research_stop_reason,
    }
    lines = ["---", *(f"{key}: {yaml_value(value)}" for key, value in frontmatter.items()), "---", "", "## Audit Summary", "", f"Approved plan `{payload.approved_plan_hash}` completed with {payload.coverage_score}% material-claim coverage. Confidence: {confidence['confidence_score']} ({confidence['confidence_band']}); QA: {confidence['qa_status']}.", "", "## Analysis", "", "### Executive answer", "", payload.direct_answer, "", payload.causal_synthesis]
    lines.extend(["", "### Workstream findings", ""])
    lines.extend(f"- **{row.workstream_id} ({row.status})** — {row.finding}" for row in payload.workstream_findings)
    lines.extend(["", "### Implications and scenarios", ""])
    lines.extend(f"- {item}" for item in payload.implications_scenarios)
    lines.extend(["", "## Evidence Trace", ""])
    for claim in payload.material_claims:
        refs = ", ".join(f"`{ref.source_id}:{ref.block_id}`" for ref in claim.evidence_refs) or "no adequate evidence"
        lines.append(f"- **{claim.claim_id} [{claim.coverage_status}]** {claim.claim} — {refs}")
    lines.extend(["", "## Source Registry", ""])
    for row in payload.evidence:
        lines.append(f"- **{row.evidence_id}** `{row.source_id}:{row.block_id}` — {row.locator}; {row.entity or 'entity not applicable'}; {row.period or 'period not applicable'}; {row.unit_currency or 'unit not applicable'}; {row.perimeter or 'perimeter not applicable'}; family: {row.independence_family}.")
    lines.extend(["", "## Gaps & Conflicts", ""])
    if not payload.gaps and not payload.conflicts:
        lines.append("No unresolved evidence gaps or conflicts remain within the approved scope.")
    lines.extend(f"- **Gap {row.workstream_id}:** {row.description}" for row in payload.gaps)
    lines.extend(f"- **Conflict {row.conflict_id} ({row.status}):** {row.description}" for row in payload.conflicts)
    lines.extend(["", "## QA Validation", "", f"- Coverage arithmetic: {payload.coverage_score}%.", f"- Confidence working: {confidence['working']}", "- Evidence citations were checked against blocks returned by the host evidence tool.", "- Host identity, approved workstreams, numerical context, conflicts, and canonical handoff were validated."])
    lines.extend(f"- **{row.severity}:** {row.finding}" for row in payload.qa_findings)
    return filename, "\n".join(lines).rstrip() + "\n"
