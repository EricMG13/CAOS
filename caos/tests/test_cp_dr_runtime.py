from __future__ import annotations

import copy
import hashlib
import json
import shutil
import threading
from pathlib import Path
from typing import Any

import pytest
import anthropic
import httpx2
from anthropic.types import TextBlock, ToolUseBlock
from caos.config import Settings
from caos.contracts import digest
from caos.artifacts.domain import build_snapshot_payload, cpdr_artifact_is_valid, create_note, promote_note
from caos.http import create_app
from caos.memory_ledgers import MemoryLedgerSet
from caos.methodology.bundle import DeployVBundle, MethodologyError
from caos.methodology.cpdr import CPDRPayload, CPDRValidationError, confidence_inputs, validate_cpdr_payload
from caos.methodology.prompt import compile_cpdr_prompts
from caos.store import JobFencedError
from caos.workflows import domain as workflow_domain
from caos.workflows import provider as provider_module
from caos.workflows.domain import WorkflowError, WorkflowRuntime
from caos.workflows.provider import (
    AgentError,
    AgentLoop,
    AnthropicGateway,
    ProviderBlock,
    ProviderMessage,
    ProviderRequest,
    ProviderUnavailable,
    ProviderUsage,
)
from ledger_helpers import (
    list_artifacts,
    mutate_node,
    mutate_run,
    mutate_source,
    replace_artifact,
    replace_current_source_set,
    seed_source,
)


DEPLOY_V = Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v"
WORKER_EVENTS = {"run.running", "node.running", "node.succeeded", "node.failed", "run.succeeded", "run.failed"}


def _cpdr_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "module_id": "CP-DR",
        "run_id": "run-1",
        "case_id": "case-1",
        "profile_id": "FULL_CREDIT_32",
        "selection_id": "DEEP_RESEARCH",
        "source_set_id": "set-1",
        "source_set_version": 1,
        "approved_plan_hash": "sha256:" + "a" * 64,
        "upstream_digests": ["d" * 64],
        "scope_type": "issuer",
        "scope_key": "case-1",
        "subject_name": "Issuer",
        "research_question": "Can the issuer refinance?",
        "reporting_period": "2026-08-23",
        "source_mode": "supplied_only",
        "workstream_findings": [{"workstream_id": "WS-1", "finding": "Liquidity supports the near-term maturity.", "claim_ids": ["C-1"], "status": "complete"}],
        "material_claims": [{"claim_id": "C-1", "claim": "The issuer source characterises liquidity as supportive of the near-term maturity.", "claim_type": "source_characterisation", "workstream_id": "WS-1", "lineage": "Directly Sourced", "evidence_refs": [{"source_id": "src-1", "block_id": "b00001"}], "counter_evidence_refs": [], "coverage_status": "adequate", "confidence": 90, "material": True}],
        "evidence": [{"evidence_id": "E-1", "source_id": "src-1", "source_digest": "e" * 64, "block_id": "b00001", "locator": "{\"line\":1}", "extractor_version": "builtin-v1", "source_confidence": "HIGH", "quoted": False, "entity": "Issuer", "period": "2026-08-23", "unit_currency": "USD", "perimeter": "consolidated", "lineage": "Directly Sourced", "independence_family": "issuer filing", "numeric_value": 100.0}],
        "conflicts": [],
        "gaps": [],
        "qa_findings": [],
        "scope_adherence": [],
        "direct_answer": "The supplied liquidity evidence supports the near-term refinancing case, subject to the stated perimeter and reporting-date limits.",
        "causal_synthesis": "Available liquidity covers the identified maturity and reduces immediate refinancing pressure.",
        "implications_scenarios": ["Monitor liquidity and maturity coverage at the next reporting date."],
        "coverage_score": 100,
        "research_status": "Complete",
        "research_stop_reason": "coverage_satisfied",
    }
    payload.update(overrides)
    return payload


def _cpdr_host() -> dict[str, Any]:
    return {
        "module_id": "CP-DR",
        "run_id": "run-1",
        "case_id": "case-1",
        "profile_id": "FULL_CREDIT_32",
        "selection_id": "DEEP_RESEARCH",
        "source_set_id": "set-1",
        "source_set_version": 1,
        "approved_plan_hash": "sha256:" + "a" * 64,
        "upstream_digests": ["d" * 64],
        "scope_type": "issuer",
        "scope_key": "case-1",
        "subject_name": "Issuer",
        "research_question": "Can the issuer refinance?",
        "reporting_period": "2026-08-23",
        "source_mode": "supplied_only",
    }


def _returned_evidence() -> dict[tuple[str, str], dict[str, str]]:
    return {("src-1", "b00001"): {"source_digest": "e" * 64, "origin_family": "e" * 64, "authority_class": "primary_authority", "locator": "{\"line\":1}", "extractor_version": "builtin-v1", "confidence": "HIGH"}}


def test_cpdr_transport_is_strict_and_host_validated() -> None:
    parsed = validate_cpdr_payload(_cpdr_payload(), _cpdr_host(), {"WS-1"}, _returned_evidence())
    assert isinstance(parsed, CPDRPayload)

    for invalid in (
        _cpdr_payload(extra="forbidden"),
        _cpdr_payload(run_id="wrong"),
        _cpdr_payload(coverage_score=99),
        _cpdr_payload(coverage_score="100"),
        _cpdr_payload(material_claims=[{**_cpdr_payload()["material_claims"][0], "numeric_value": True}]),
        _cpdr_payload(material_claims=[{**_cpdr_payload()["material_claims"][0], "provider_only": "forbidden"}]),
        _cpdr_payload(direct_answer="x" * 8_001),
        _cpdr_payload(material_claims=[]),
        _cpdr_payload(workstream_findings=[]),
    ):
        with pytest.raises(CPDRValidationError):
            validate_cpdr_payload(invalid, _cpdr_host(), {"WS-1"}, _returned_evidence())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_cpdr_rejects_nonfinite_and_false_citations(value: float) -> None:
    with pytest.raises(CPDRValidationError):
        validate_cpdr_payload(_cpdr_payload(evidence=[{**_cpdr_payload()["evidence"][0], "numeric_value": value}]), _cpdr_host(), {"WS-1"}, _returned_evidence())
    with pytest.raises(CPDRValidationError, match="returned"):
        validate_cpdr_payload(_cpdr_payload(), _cpdr_host(), {"WS-1"}, {})


def test_cpdr_numeric_evidence_requires_context() -> None:
    row = {**_cpdr_payload()["evidence"][0], "unit_currency": None}
    with pytest.raises(CPDRValidationError, match="numeric context"):
        validate_cpdr_payload(_cpdr_payload(evidence=[row]), _cpdr_host(), {"WS-1"}, _returned_evidence())


def test_cpdr_concatenated_numeric_claim_requires_context() -> None:
    claim = {**_cpdr_payload()["material_claims"][0], "claim": "Issuer liquidity was USD100m.", "numeric_value": None}
    with pytest.raises(CPDRValidationError, match="numeric claim"):
        validate_cpdr_payload(_cpdr_payload(material_claims=[claim]), _cpdr_host(), {"WS-1"}, _returned_evidence())


def test_cpdr_host_provenance_controls_adequacy_and_confidence() -> None:
    fact = {**_cpdr_payload()["material_claims"][0], "claim_type": "fact"}
    unclassified = {
        key: {**metadata, "authority_class": "unclassified"}
        for key, metadata in _returned_evidence().items()
    }
    with pytest.raises(CPDRValidationError, match="host coverage"):
        validate_cpdr_payload(_cpdr_payload(material_claims=[fact]), _cpdr_host(), {"WS-1"}, unclassified)

    second_row = {**_cpdr_payload()["evidence"][0], "evidence_id": "E-2", "source_id": "src-2", "source_digest": "f" * 64, "block_id": "b00002", "independence_family": "forged-second-family"}
    two_refs = [{"source_id": "src-1", "block_id": "b00001"}, {"source_id": "src-2", "block_id": "b00002"}]
    fact["evidence_refs"] = two_refs
    copied = {**unclassified, ("src-2", "b00002"): {**unclassified[("src-1", "b00001")], "source_digest": "f" * 64}}
    with pytest.raises(CPDRValidationError, match="host coverage"):
        validate_cpdr_payload(_cpdr_payload(material_claims=[fact], evidence=[_cpdr_payload()["evidence"][0], second_row]), _cpdr_host(), {"WS-1"}, copied)

    independent = {**copied, ("src-2", "b00002"): {**copied[("src-2", "b00002")], "origin_family": "f" * 64}}
    parsed = validate_cpdr_payload(_cpdr_payload(material_claims=[fact], evidence=[_cpdr_payload()["evidence"][0], second_row]), _cpdr_host(), {"WS-1"}, independent)
    forged = parsed.model_copy(update={"material_claims": [parsed.material_claims[0].model_copy(update={"lineage": "Analyst Inference"})], "qa_findings": []})
    inputs = confidence_inputs(forged, independent)
    assert inputs["lineage_counts"] == {"Weak Lineage": 1}
    assert inputs["source_gate"] == "pass" and inputs["findings"] == {}


def test_material_source_characterisation_cannot_forge_host_provenance_or_complete_coverage() -> None:
    forged_claim = {
        **_cpdr_payload()["material_claims"][0],
        "claim": "The issuer has ample liquidity according to the supplied document.",
        "claim_type": "source_characterisation",
        "lineage": "Directly Sourced",
        "confidence": 100,
        "material": True,
    }
    forged_evidence = {
        **_cpdr_payload()["evidence"][0],
        "lineage": "Directly Sourced",
        "independence_family": "provider-forged-family",
    }
    unclassified = {
        key: {**metadata, "authority_class": "unclassified"}
        for key, metadata in _returned_evidence().items()
    }
    with pytest.raises(CPDRValidationError, match="host coverage"):
        validate_cpdr_payload(
            _cpdr_payload(material_claims=[forged_claim], evidence=[forged_evidence]),
            _cpdr_host(), {"WS-1"}, unclassified,
        )


def test_promoted_note_origin_digest_is_exact_canonical_content_bytes() -> None:
    ledger_set = MemoryLedgerSet()
    case = ledger_set.runs.create_case("Origin", "Issuer", "Testing", "analyst")
    note = create_note(
        ledger_set.publications, case["id"], "analyst", "canonical note bytes"
    )
    promoted = promote_note(
        ledger_set.publications, case["id"], note["id"], "analyst"
    )
    source = ledger_set.sources.get_source(promoted["promoted_source_id"])
    assert source is not None
    assert source["sha256"] == hashlib.sha256(b"canonical note bytes").hexdigest()


def test_cpdr_host_confidence_penalizes_material_gaps_without_provider_qa() -> None:
    claim = {**_cpdr_payload()["material_claims"][0], "evidence_refs": [], "coverage_status": "gap"}
    payload = _cpdr_payload(
        material_claims=[claim],
        evidence=[],
        gaps=[{"workstream_id": "WS-1", "description": "Material evidence remains unavailable.", "material": True}],
        coverage_score=0,
        research_status="Complete with Gaps",
        research_stop_reason="sources_exhausted",
        qa_findings=[],
    )
    parsed = validate_cpdr_payload(payload, _cpdr_host(), {"WS-1"}, {})
    inputs = confidence_inputs(parsed, {})
    assert inputs["lineage_counts"] == {"Insufficient Information": 1}
    assert inputs["source_gate"] == "fail"
    assert inputs["findings"]["MATERIAL"] >= 1


def test_cpdr_scope_adherence_is_exact_and_bound_to_approved_plan() -> None:
    plan = {"workstreams": [{"id": "WS-1", "assigned_questions": ["sentinel-must-answer"]}]}
    brief = {"must_answer": ["sentinel-must-answer"], "exclusions": ["sentinel-exclusion"]}
    rows = [
        {"kind": "must_answer", "item": "sentinel-must-answer", "workstream_id": "WS-1", "respected": True},
        {"kind": "exclusion", "item": "sentinel-exclusion", "workstream_id": None, "respected": True},
    ]
    assert validate_cpdr_payload(_cpdr_payload(scope_adherence=rows), _cpdr_host(), {"WS-1"}, _returned_evidence(), plan, brief)
    invalid_rows = [rows[:1], rows + [rows[1]], [{**rows[0], "item": "changed"}, rows[1]], [rows[0], {**rows[1], "respected": False}]]
    for invalid in invalid_rows:
        with pytest.raises(CPDRValidationError, match="scope adherence"):
            validate_cpdr_payload(_cpdr_payload(scope_adherence=invalid), _cpdr_host(), {"WS-1"}, _returned_evidence(), plan, brief)
    duplicate_brief = {**brief, "exclusions": ["sentinel-exclusion", "sentinel-exclusion"]}
    with pytest.raises(CPDRValidationError, match="scope items must be unique"):
        validate_cpdr_payload(_cpdr_payload(scope_adherence=rows), _cpdr_host(), {"WS-1"}, _returned_evidence(), plan, duplicate_brief)


def test_cpdr_conflict_citations_are_exhaustive_unique_and_registered() -> None:
    ghost = {"conflict_id": "K-1", "claim_ids": ["C-1"], "evidence_refs": [{"source_id": "ghost", "block_id": "missing"}, {"source_id": "ghost", "block_id": "missing"}], "description": "Conflict", "status": "unresolved"}
    with pytest.raises(CPDRValidationError):
        validate_cpdr_payload(_cpdr_payload(conflicts=[ghost]), _cpdr_host(), {"WS-1"}, _returned_evidence())

    row2 = {**_cpdr_payload()["evidence"][0], "evidence_id": "E-2", "source_id": "src-2", "source_digest": "f" * 64, "block_id": "b00002"}
    returned = {**_returned_evidence(), ("src-2", "b00002"): {**_returned_evidence()[("src-1", "b00001")], "source_digest": "f" * 64, "origin_family": "f" * 64}}
    refs = [{"source_id": "src-1", "block_id": "b00001"}, {"source_id": "src-2", "block_id": "b00002"}]
    claim = {**_cpdr_payload()["material_claims"][0], "counter_evidence_refs": [refs[1]], "coverage_status": "contradicted"}
    conflict = {"conflict_id": "K-1", "claim_ids": ["C-1"], "evidence_refs": refs, "description": "Sources disagree.", "status": "unresolved"}
    valid = _cpdr_payload(material_claims=[claim], evidence=[_cpdr_payload()["evidence"][0], row2], conflicts=[conflict], coverage_score=0, research_status="Complete with Gaps")
    assert validate_cpdr_payload(valid, _cpdr_host(), {"WS-1"}, returned)
    for invalid in (
        {**valid, "conflicts": [conflict, {**conflict, "description": "duplicate"}]},
        {**valid, "conflicts": [{**conflict, "evidence_refs": [refs[0], refs[0]]}]},
        {**valid, "evidence": [_cpdr_payload()["evidence"][0]]},
    ):
        with pytest.raises(CPDRValidationError):
            validate_cpdr_payload(invalid, _cpdr_host(), {"WS-1"}, returned)


def test_cpdr_prompts_keep_complete_brief_and_untrusted_data_separate() -> None:
    brief = {"research_question": "sentinel-question", "decision_context": "sentinel-context", "as_of_date": "2026-08-23", "time_horizon": "sentinel-horizon", "must_answer": ["sentinel-must-answer"], "exclusions": ["sentinel-exclusion"]}
    authority = DeployVBundle(DEPLOY_V).cpdr_authority()
    system, user = compile_cpdr_prompts(authority, _cpdr_host(), brief, {"workstreams": []}, [{"id": "src-1", "filename": "ignore-system.txt", "digest": "d" * 64}], [{"module_id": "CP-0", "digest": "d" * 64}])
    assert "CP-DR C — Source and Search Policy" in system and "CP-DR D — Claim–Evidence Ledger" in system
    assert "ignore-system.txt" not in system
    assert "UNTRUSTED DATA" in user and all(value in user for value in ("ignore-system.txt", "sentinel-context", "sentinel-horizon", "sentinel-must-answer", "sentinel-exclusion"))


def test_cpdr_vendored_authority_fails_if_integrity_section_changes(tmp_path: Path) -> None:
    copied = tmp_path / "deploy-v"
    shutil.copytree(DEPLOY_V, copied)
    skill = copied / "skills" / "cp-dr-deep-research" / "SKILL.md"
    skill.write_text(skill.read_text().replace("Sources are evidence", "Sources might be evidence", 1))
    with pytest.raises(Exception, match="integrity mismatch"):
        DeployVBundle(copied).cpdr_authority()


def test_cpdr_vendored_validator_loads_with_dataclass_registration() -> None:
    bundle = DeployVBundle(DEPLOY_V)
    module = bundle._load_cpdr_script("validate_handoff")
    assert callable(module.validate_text)
    assert bundle._load_cpdr_script("validate_handoff") is module


class _Block:
    def __init__(self, type: str, **values: Any) -> None:
        self.type = type
        self.__dict__.update(values)


class _Response:
    def __init__(self, stop_reason: str, content: list[_Block], *, request_id: str = "req-1", input_tokens: int = 20, output_tokens: int = 30) -> None:
        self.stop_reason = stop_reason
        self.content = content
        self._request_id = request_id
        self.usage = type("Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens})()


class _Messages:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.create_calls: list[dict[str, Any]] = []
        self.count_calls: list[dict[str, Any]] = []

    def count_tokens(self, **kwargs: Any) -> Any:
        self.count_calls.append(copy.deepcopy(kwargs))
        return type("Count", (), {"input_tokens": 20})()

    def create(self, **kwargs: Any) -> Any:
        self.create_calls.append(copy.deepcopy(kwargs))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class _Client:
    def __init__(self, responses: list[Any]) -> None:
        self.messages = _Messages(responses)


class _FakeProvider:
    def __init__(self, responses: list[Any], counts: list[Any] | None = None) -> None:
        self.responses = list(responses)
        self.counts = list(counts or [20] * len(responses))
        self.calls: list[tuple[str, ProviderRequest]] = []

    def count_tokens(self, request: ProviderRequest) -> int:
        self.calls.append(("count_tokens", copy.deepcopy(request)))
        result = self.counts.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def create_message(self, request: ProviderRequest) -> ProviderMessage:
        self.calls.append(("create", copy.deepcopy(request)))
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def _queue_cpdr_success(provider: _FakeProvider, final: dict[str, Any], source_id: str) -> None:
    secondary_source_id = final["evidence"][1]["source_id"]
    responses = [
        ProviderMessage(
            content=[ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})],
            stop_reason="tool_use",
            usage=ProviderUsage(20, 30),
        ),
        ProviderMessage(
            content=[ProviderBlock(type="tool_use", id="tool-2", name="read_evidence", input={"source_id": secondary_source_id, "block_ids": ["b00002"]})],
            stop_reason="tool_use",
            usage=ProviderUsage(20, 30),
        ),
        ProviderMessage(
            content=[ProviderBlock(type="text", text=json.dumps(final))],
            stop_reason="end_turn",
            usage=ProviderUsage(20, 30),
        ),
    ]
    provider.responses.extend(responses)
    provider.counts.extend([20] * len(responses))


def test_workflow_runtime_uses_one_agent_loop_for_injected_provider() -> None:
    provider = _FakeProvider([])
    ledger_set = MemoryLedgerSet()
    runtime = WorkflowRuntime(
        ledger_set.runs,
        ledger_set.sources,
        DeployVBundle(DEPLOY_V),
        Settings(storage_dir=Path("/tmp/caos-injected-provider"), deploy_v_root=DEPLOY_V),
        provider=provider,
    )
    try:
        assert runtime._agent_loop.provider is provider
    finally:
        runtime.close()


def test_agent_loop_provider_injection_handles_tools_and_reconciles_normalized_usage() -> None:
    provider = _FakeProvider([
        ProviderMessage(
            content=[ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": "src-1", "block_ids": ["b00001"]})],
            stop_reason="tool_use",
            usage=ProviderUsage(input_tokens=20, output_tokens=4),
            request_id="req-tool",
        ),
        ProviderMessage(
            content=[ProviderBlock(type="text", text=json.dumps(_cpdr_payload()))],
            stop_reason="end_turn",
            usage=ProviderUsage(input_tokens=24, output_tokens=30),
            request_id="req-final",
        ),
    ])
    reconciliations: list[tuple[Any, ...]] = []

    result = AgentLoop(provider).run(
        system="authority",
        user="brief",
        read_evidence=lambda source_id, block_ids: [{"source_id": source_id, "block_id": block_ids[0], "text": "evidence"}],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *args: reconciliations.append(args),
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert [kind for kind, _request in provider.calls] == ["count_tokens", "create", "count_tokens", "create"]
    second_count = provider.calls[2][1]
    assert second_count.messages[-2]["content"] == [
        ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": "src-1", "block_ids": ["b00001"]}),
    ]
    assert second_count.messages[-1]["content"][0]["tool_use_id"] == "tool-1"
    assert [items[-2:] for items in reconciliations] == [(20, 4), (24, 30)]


def test_agent_loop_provider_injection_retries_one_normalized_timeout() -> None:
    provider = _FakeProvider([
        AgentError("AGENT_PROVIDER_TIMEOUT"),
        ProviderMessage(
            content=[ProviderBlock(type="text", text=json.dumps(_cpdr_payload()))],
            stop_reason="end_turn",
            usage=ProviderUsage(input_tokens=20, output_tokens=30),
        ),
    ], counts=[20])
    reservations: list[tuple[Any, ...]] = []

    result = AgentLoop(provider).run(
        system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
        lease_check=lambda: None, reserve=lambda *args: reservations.append(args), reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert provider.calls[1][1] == provider.calls[2][1]
    assert [reservation[-1] for reservation in reservations] == [False, True]


def test_agent_loop_provider_injection_rejects_malformed_normalized_usage() -> None:
    provider = _FakeProvider([
        ProviderMessage(
            content=[ProviderBlock(type="text", text=json.dumps(_cpdr_payload()))],
            stop_reason="end_turn",
            usage=ProviderUsage(input_tokens=20, output_tokens=1.5),  # type: ignore[arg-type]
        ),
    ])
    reconciliations: list[tuple[Any, ...]] = []

    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AgentLoop(provider).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *args: reconciliations.append(args),
            record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert reconciliations == []


def test_gateway_preserves_assistant_content_and_orders_tool_results() -> None:
    tool_response = _Response("tool_use", [_Block("text", text="checking"), _Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": "src-1", "block_ids": ["b00001"]})])
    final_response = _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))], request_id="req-2")
    client = _Client([tool_response, final_response])
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=client)
    reservations: list[tuple[str, int, int, bool]] = []

    result = gateway.run(
        system="authority",
        user="brief",
        read_evidence=lambda source_id, block_ids: [{"source_id": source_id, "block_id": block_ids[0], "text": "evidence"}],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda digest, inputs, outputs, retry: reservations.append((digest, inputs, outputs, retry)),
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    first = client.messages.create_calls[0]
    assert first["system"] == "authority"
    assert first["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert first["tools"][0]["name"] == "read_evidence" and first["tools"][0]["strict"] is True
    assert "output_config" in first and "output_format" not in first
    second_messages = client.messages.create_calls[1]["messages"]
    assert second_messages[-2]["content"] == [vars(block) for block in tool_response.content]
    assert second_messages[-1]["content"][0]["type"] == "tool_result"
    assert len(reservations) == 2


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens", "model_context_window_exceeded", "pause_turn", "unknown"])
def test_gateway_rejects_non_final_stop_reasons(stop_reason: str) -> None:
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=_Client([_Response(stop_reason, [_Block("text", text="no")])]))
    events: list[tuple[str, dict[str, Any]]] = []
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        gateway.run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)), active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert any(details.get("terminal_code") == "AGENT_OUTPUT_INVALID" for _kind, details in events)


def _gateway_call(client: _Client, *, semaphore: threading.BoundedSemaphore | None = None, events: list[tuple[str, dict[str, Any]]] | None = None) -> dict[str, Any]:
    return AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *_: None,
        record=lambda kind, **details: events.append((kind, details)) if events is not None else None,
        active_time=lambda _elapsed: None,
        semaphore=semaphore or threading.BoundedSemaphore(2),
    )


def test_gateway_missing_key_is_explicitly_unavailable() -> None:
    with pytest.raises(AgentError, match="AGENT_PROVIDER_UNAVAILABLE"):
        AnthropicGateway("", "claude-sonnet-4-6")


def test_gateway_real_sdk_constructor_disables_hidden_retries_and_sets_timeout() -> None:
    gateway = AnthropicGateway("constructor-probe-only", "claude-sonnet-4-6", timeout=37.5)
    assert gateway.client.max_retries == 0
    assert gateway.client.timeout == 37.5


def test_gateway_real_sdk_mock_transport_serializes_expected_messages_request() -> None:
    requests: list[tuple[str, dict[str, Any]]] = []
    brief = {
        "research_question": "sdk-question-sentinel",
        "decision_context": "sdk-decision-sentinel",
        "as_of_date": "2026-08-23",
        "time_horizon": "sdk-horizon-sentinel",
        "must_answer": ["sdk-must-answer-sentinel"],
        "exclusions": ["sdk-exclusion-sentinel"],
    }
    system_prompt, user_prompt = compile_cpdr_prompts(
        "verified authority", _cpdr_host(), brief,
        {"workstreams": [{"id": "WS-1", "assigned_questions": brief["must_answer"]}]}, [], [],
    )

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        requests.append((request.url.path, body))
        if request.url.path.endswith("/count_tokens"):
            return httpx2.Response(200, json={"input_tokens": 20})
        return httpx2.Response(
            200,
            json={
                "id": "msg_local", "type": "message", "role": "assistant", "model": "claude-sonnet-4-6",
                "content": [{"type": "text", "text": json.dumps(_cpdr_payload())}],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 20, "output_tokens": 30},
            },
        )

    sdk = anthropic.Anthropic(
        api_key="constructor-probe-only", max_retries=0, timeout=37.5,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    result = AnthropicGateway("constructor-probe-only", "claude-sonnet-4-6", client=sdk).run(
        system=system_prompt, user=user_prompt, read_evidence=lambda *_: [],
        validate=lambda value: value, lease_check=lambda: None, reserve=lambda *_: None,
        reconcile=lambda *_: None, record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None, semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert [path for path, _body in requests] == ["/v1/messages/count_tokens", "/v1/messages"]
    create = requests[1][1]
    assert create["model"] == "claude-sonnet-4-6" and create["max_tokens"] == 2_000
    serialized_create = json.dumps(create, sort_keys=True)
    assert create["system"] == system_prompt and create["messages"] == [{"role": "user", "content": user_prompt}]
    for sentinel in (
        "sdk-question-sentinel", "sdk-decision-sentinel", "sdk-horizon-sentinel",
        "sdk-must-answer-sentinel", "sdk-exclusion-sentinel",
    ):
        assert sentinel in serialized_create
    assert create["tools"][0]["name"] == "read_evidence" and create["output_config"]["format"]["type"] == "json_schema"


def test_gateway_retries_one_identical_timeout_request() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client([anthropic.APITimeoutError(request), _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])
    reservations: list[tuple[Any, ...]] = []
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=client)

    result = gateway.run(
        system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
        lease_check=lambda: None, reserve=lambda *args: reservations.append(args), reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert {key: value for key, value in client.messages.create_calls[0].items() if key != "timeout"} == {
        key: value for key, value in client.messages.create_calls[1].items() if key != "timeout"
    }
    assert [reservation[-1] for reservation in reservations] == [False, True]


def test_gateway_preserves_legacy_request_digest_bytes_across_retry() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client([
        anthropic.APITimeoutError(request),
        _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
    ])
    reservations: list[tuple[Any, ...]] = []

    AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
        lease_check=lambda: None, reserve=lambda *args: reservations.append(args), reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    legacy_preimage = {
        "model": "claude-sonnet-4-6",
        "system": "authority",
        "messages": [{"role": "user", "content": "brief"}],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(CPDRPayload.model_json_schema()),
            }
        },
        "tools": [provider_module.READ_EVIDENCE_TOOL],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "max_tokens": 2_000,
    }
    expected_bytes = json.dumps(legacy_preimage, sort_keys=True, default=lambda value: vars(value)).encode("utf-8")
    actual_bytes = json.dumps(
        {key: value for key, value in client.messages.create_calls[0].items() if key != "timeout"},
        sort_keys=True,
        default=lambda value: vars(value),
    ).encode("utf-8")
    assert actual_bytes == expected_bytes
    assert [reservation[0] for reservation in reservations] == [hashlib.sha256(expected_bytes).hexdigest()] * 2


def test_gateway_preserves_legacy_sdk_block_fields_in_continuation_digest() -> None:
    tool_blocks = [
        TextBlock(citations=None, text="checking", type="text"),
        ToolUseBlock(
            id="tool-1", caller=None, input={"source_id": "src-1", "block_ids": ["b00001"]},
            name="read_evidence", type="tool_use", toolset_name=None,
        ),
    ]
    evidence = [{"source_id": "src-1", "block_id": "b00001", "text": "evidence"}]
    client = _Client([
        _Response("tool_use", tool_blocks),  # type: ignore[arg-type]
        _Response(
            "end_turn",
            [TextBlock(citations=None, text=json.dumps(_cpdr_payload()), type="text")],  # type: ignore[list-item]
        ),
    ])
    reservations: list[tuple[Any, ...]] = []
    remaining = iter([5.0, 4.0, 3.0, 2.0, 1.0])

    AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority", user="brief", read_evidence=lambda *_: evidence, validate=lambda value: value,
        lease_check=lambda: None, reserve=lambda *args: reservations.append(args), reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
        remaining_time=lambda: next(remaining), semaphore=threading.BoundedSemaphore(2),
    )

    legacy_preimage = {
        "model": "claude-sonnet-4-6",
        "system": "authority",
        "messages": [
            {"role": "user", "content": "brief"},
            {"role": "assistant", "content": tool_blocks},
            {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": "tool-1",
                    "content": json.dumps(evidence, sort_keys=True),
                }],
            },
        ],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(CPDRPayload.model_json_schema()),
            }
        },
        "tools": [provider_module.READ_EVIDENCE_TOOL],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "max_tokens": 2_000,
    }
    expected_bytes = json.dumps(legacy_preimage, sort_keys=True, default=lambda value: vars(value)).encode("utf-8")
    assert all(field in expected_bytes for field in (b'"citations": null', b'"caller": null', b'"toolset_name": null'))
    assert b'"timeout"' not in expected_bytes and client.messages.create_calls[1]["timeout"] == 1.0
    assert reservations[1][0] == hashlib.sha256(expected_bytes).hexdigest()


def test_gateway_schema_transform_failure_is_not_a_provider_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client([])
    events: list[tuple[str, dict[str, Any]]] = []
    charged: list[float] = []
    monkeypatch.setattr(
        provider_module.anthropic,
        "transform_schema",
        lambda _schema: (_ for _ in ()).throw(ValueError("invalid schema")),
    )

    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)), active_time=charged.append,
            semaphore=threading.BoundedSemaphore(2),
        )

    assert client.messages.count_calls == []
    assert events == []
    assert charged == []


def _production_injected_runtime(monkeypatch: pytest.MonkeyPatch, client: _Client) -> WorkflowRuntime:
    monkeypatch.setattr(provider_module.anthropic, "Anthropic", lambda **_kwargs: client)
    app = create_app(
        Settings(
            environment="test",
            storage_dir=Path("/tmp/caos-production-provider-hooks"),
            deploy_v_root=DEPLOY_V,
            anthropic_api_key="test-only-key",
            cpdr_agent_enabled=True,
        ),
        MemoryLedgerSet(),
    )
    return app.state.runtime


def test_production_injection_preserves_legacy_request_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client([_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])
    runtime = _production_injected_runtime(monkeypatch, client)
    reservations: list[tuple[Any, ...]] = []
    try:
        runtime._agent_loop.run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *args: reservations.append(args), reconcile=lambda *_: None,
            record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    finally:
        runtime.close()

    legacy_preimage = {
        "model": "claude-sonnet-4-6",
        "system": "authority",
        "messages": [{"role": "user", "content": "brief"}],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(CPDRPayload.model_json_schema()),
            }
        },
        "tools": [provider_module.READ_EVIDENCE_TOOL],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "max_tokens": 2_000,
    }
    expected = hashlib.sha256(
        json.dumps(legacy_preimage, sort_keys=True, default=lambda value: vars(value)).encode("utf-8")
    ).hexdigest()
    assert reservations[0][0] == expected


def test_production_injection_schema_failure_has_no_provider_contact_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _Client([])
    monkeypatch.setattr(
        provider_module.anthropic,
        "transform_schema",
        lambda _schema: (_ for _ in ()).throw(ValueError("invalid schema")),
    )
    runtime = _production_injected_runtime(monkeypatch, client)
    events: list[tuple[str, dict[str, Any]]] = []
    charged: list[float] = []
    try:
        with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
            runtime._agent_loop.run(
                system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
                lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
                record=lambda kind, **details: events.append((kind, details)), active_time=charged.append,
                semaphore=threading.BoundedSemaphore(2),
            )
    finally:
        runtime.close()

    assert client.messages.count_calls == []
    assert events == []
    assert charged == []


def test_gateway_caps_each_sdk_call_to_decreasing_remaining_active_time() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client([anthropic.APITimeoutError(request), _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])
    remaining = iter([9.0, 8.0, 7.0])

    result = AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
        lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
        remaining_time=lambda: next(remaining), semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert client.messages.count_calls[0]["timeout"] == 9.0
    assert [call["timeout"] for call in client.messages.create_calls] == [8.0, 7.0]
    assert {key: value for key, value in client.messages.create_calls[0].items() if key != "timeout"} == {
        key: value for key, value in client.messages.create_calls[1].items() if key != "timeout"
    }


def test_gateway_charges_failed_evidence_and_validation_time() -> None:
    tool_response = _Response(
        "tool_use",
        [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": "src-1", "block_ids": ["b00001"]})],
    )
    charged: list[float] = []
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=_Client([tool_response])).run(
            system="authority", user="brief",
            read_evidence=lambda *_: (_ for _ in ()).throw(AgentError("AGENT_OUTPUT_INVALID")),
            validate=lambda value: value, lease_check=lambda: None, reserve=lambda *_: None,
            reconcile=lambda *_: None, record=lambda *_args, **_kwargs: None,
            active_time=charged.append, semaphore=threading.BoundedSemaphore(2),
        )
    assert len(charged) >= 2 and charged[-1] >= 0

    charged.clear()
    final_response = _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=_Client([final_response])).run(
            system="authority", user="brief", read_evidence=lambda *_: [],
            validate=lambda _value: (_ for _ in ()).throw(AgentError("AGENT_OUTPUT_INVALID")),
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=lambda *_args, **_kwargs: None, active_time=charged.append,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert len(charged) >= 2 and charged[-1] >= 0


def test_gateway_rejects_duplicate_json_keys_and_records_terminal_interaction() -> None:
    duplicate = '{"module_id":"CP-DR","module_id":"forged"}'
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client([
        _Response("end_turn", [_Block("text", text=duplicate)]),
        _Response("end_turn", [_Block("text", text=duplicate)]),
    ])

    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        _gateway_call(client, events=events)

    assert any(details.get("terminal_code") == "AGENT_OUTPUT_INVALID" for _kind, details in events)


def test_gateway_records_terminal_when_create_reservation_fails_after_count() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client([_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])
    with pytest.raises(AgentError, match="AGENT_BUDGET_EXCEEDED"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: (_ for _ in ()).throw(AgentError("AGENT_BUDGET_EXCEEDED")),
            reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)),
            active_time=lambda _elapsed: None, semaphore=threading.BoundedSemaphore(2),
        )
    assert client.messages.create_calls == []
    assert any(details.get("terminal_code") == "AGENT_BUDGET_EXCEEDED" for _kind, details in events)


def test_gateway_auth_permission_and_policy_rejections_do_not_retry() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    failures = [
        anthropic.AuthenticationError("secret body", response=httpx2.Response(401, request=request), body={"secret": "body"}),
        anthropic.PermissionDeniedError("secret body", response=httpx2.Response(403, request=request), body={"secret": "body"}),
        anthropic.APIStatusError("secret body", response=httpx2.Response(422, request=request), body={"secret": "body"}),
    ]
    for failure in failures:
        client = _Client([failure])
        events: list[tuple[str, dict[str, Any]]] = []
        with pytest.raises(AgentError, match="AGENT_PROVIDER_REJECTED"):
            _gateway_call(client, events=events)
        assert len(client.messages.create_calls) == 1
        assert "secret" not in json.dumps(events)


def test_gateway_unknown_http_status_is_invalid_not_timeout() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    failure = anthropic.APIStatusError("redirect", response=httpx2.Response(302, request=request), body=None)
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        _gateway_call(_Client([failure]))


@pytest.mark.parametrize("kind", ["timeout", "connection", "rate", "status"])
def test_gateway_retryable_failures_timeout_after_one_retry(kind: str) -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    def failure() -> BaseException:
        if kind == "timeout":
            return anthropic.APITimeoutError(request)
        if kind == "connection":
            return anthropic.APIConnectionError(request=request)
        if kind == "rate":
            return anthropic.RateLimitError("rate", response=httpx2.Response(429, request=request), body=None)
        return anthropic.APIStatusError("server", response=httpx2.Response(503, request=request), body=None)

    client = _Client([failure(), failure()])
    with pytest.raises(AgentError, match="AGENT_PROVIDER_TIMEOUT"):
        _gateway_call(client)
    assert len(client.messages.create_calls) == 2


def test_gateway_concurrency_denial_does_not_reserve_tokens() -> None:
    semaphore = threading.BoundedSemaphore(1)
    semaphore.acquire()
    reservations: list[tuple[Any, ...]] = []
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=_Client([_Response("end_turn", [_Block("text", text="{}")])]))
    try:
        with pytest.raises(AgentError, match="AGENT_BUDGET_EXCEEDED"):
            gateway.run(
                system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
                lease_check=lambda: None, reserve=lambda *args: reservations.append(args), reconcile=lambda *_: None,
                record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None, semaphore=semaphore,
            )
    finally:
        semaphore.release()
    assert reservations == []


@pytest.mark.parametrize("invalid_at", ["negative_count", "fractional_count", "negative_input_usage", "fractional_output_usage"])
def test_gateway_rejects_invalid_provider_token_counts(invalid_at: str) -> None:
    response = _Response(
        "end_turn",
        [_Block("text", text=json.dumps(_cpdr_payload()))],
        input_tokens=-1 if invalid_at == "negative_input_usage" else 20,
        output_tokens=1.5 if invalid_at == "fractional_output_usage" else 30,
    )
    client = _Client([response])
    if invalid_at in {"negative_count", "fractional_count"}:
        invalid = -1 if invalid_at == "negative_count" else 1.5
        client.messages.count_tokens = lambda **_kwargs: type("Count", (), {"input_tokens": invalid})()

    events: list[tuple[str, dict[str, Any]]] = []
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        _gateway_call(client, events=events)
    assert any(details.get("terminal_code") == "AGENT_OUTPUT_INVALID" for _kind, details in events)


def test_gateway_uses_one_repair_without_evidence_tools() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client([
        _Response("end_turn", [_Block("text", text="{}")]),
        _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
    ])
    result = AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority", user="brief", read_evidence=lambda *_: [],
        validate=lambda value: value if value.get("module_id") == "CP-DR" else (_ for _ in ()).throw(ValueError("module_id required")),
        lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
        record=lambda kind, **details: events.append((kind, details)), active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )
    assert result["module_id"] == "CP-DR"
    assert "repair_reserve" in [kind for kind, _ in events]
    assert "tools" not in client.messages.create_calls[-1]


def test_cpdr_fake_provider_end_to_end_produces_one_canonical_fenced_artifact() -> None:
    ledger_set = MemoryLedgerSet()
    provider = _FakeProvider([])
    settings = Settings(
        environment="production",
        storage_dir=Path("/tmp/caos-cpdr-e2e"),
        deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key",
        cpdr_agent_enabled=True,
        cpdr_pilot_subjects=("analyst",),
    )
    runtime = WorkflowRuntime(
        ledger_set.runs,
        ledger_set.sources,
        DeployVBundle(DEPLOY_V),
        settings,
        provider=provider,
    )
    case = ledger_set.runs.create_case("CP-DR", "Issuer", "Testing", "analyst")
    first = seed_source(
        ledger_set,
        case["id"],
        "analyst",
        filename="issuer.txt",
        sha256="e" * 64,
        blocks=[{"block_id": "b00001", "locator": {"line": 1}, "text": "Issuer liquidity was USD 100m at 2026-08-23.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    )
    source_id = first["id"]
    second = seed_source(
        ledger_set,
        case["id"],
        "analyst",
        filename="facility.txt",
        sha256="f" * 64,
        blocks=[{"block_id": "b00002", "locator": {"line": 2}, "text": "Facility availability extends through 2029.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    )
    second_source_id = second["id"]
    source_set = second["source_set"]
    brief = {"research_question": "Can the issuer refinance?", "decision_context": "Underwrite first-lien risk.", "as_of_date": "2026-08-23", "time_horizon": "Through 2029", "must_answer": [], "exclusions": []}
    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = ledger_set.runs.get_run(run["id"])
        assert paused is not None and paused["status"] == "paused"
        runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
        approved = ledger_set.runs.get_run(run["id"])
        assert approved is not None
        cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
        cp0 = ledger_set.runs.get_artifact(cp0_node["artifact_id"])
        assert cp0 is not None
        workstreams = approved["research"]["proposed_plan"]["workstreams"]
        final = _cpdr_payload(
            run_id=run["id"],
            case_id=case["id"],
            source_set_id=source_set["id"],
            source_set_version=source_set["version"],
            approved_plan_hash=approved["research"]["approved_plan_hash"],
            upstream_digests=[cp0["digest"]],
            scope_key=case["id"].replace("_", "-"),
            workstream_findings=[
                {"workstream_id": item["id"], "finding": "The supplied evidence resolves this approved lane." if index == 0 else "No additional material claim was required for this lane.", "claim_ids": ["C-1"] if index == 0 else [], "status": "complete"}
                for index, item in enumerate(workstreams)
            ],
            material_claims=[{**_cpdr_payload()["material_claims"][0], "workstream_id": workstreams[0]["id"], "evidence_refs": [{"source_id": source_id, "block_id": "b00001"}, {"source_id": second_source_id, "block_id": "b00002"}]}],
            evidence=[
                {**_cpdr_payload()["evidence"][0], "source_id": source_id, "block_id": "b00001"},
                {**_cpdr_payload()["evidence"][0], "evidence_id": "E-2", "source_id": second_source_id, "source_digest": "f" * 64, "block_id": "b00002", "locator": "{\"line\":2}"},
            ],
        )
        provider.responses.extend([
            AgentError("AGENT_PROVIDER_TIMEOUT"),
            ProviderMessage(
                content=[ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})],
                stop_reason="tool_use", usage=ProviderUsage(20, 30),
            ),
            ProviderMessage(
                content=[ProviderBlock(type="tool_use", id="tool-2", name="read_evidence", input={"source_id": second_source_id, "block_ids": ["b00002"]})],
                stop_reason="tool_use", usage=ProviderUsage(20, 30),
            ),
            ProviderMessage(
                content=[ProviderBlock(type="text", text="{}")], stop_reason="end_turn",
                usage=ProviderUsage(20, 30), request_id="req-invalid",
            ),
            ProviderMessage(
                content=[ProviderBlock(type="text", text=json.dumps(final))], stop_reason="end_turn",
                usage=ProviderUsage(20, 30), request_id="req-final",
            ),
        ])
        provider.counts.extend([20] * 5)

        runtime._execute(run["id"], "approver")

        completed = ledger_set.runs.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded", completed and completed.get("error")
        cpdr_node = next(node for node in completed["nodes"] if node["module_id"] == "CP-DR")
        artifact = ledger_set.runs.get_artifact(cpdr_node["artifact_id"])
        # The CP-DR filename is dated by the run's creation date
        # (workflows/domain.py passes run["created_at"][:10]), so derive the
        # expectation instead of hardcoding a day that rots overnight.
        expected_date = completed["created_at"][:10].replace("-", "")
        assert artifact is not None and artifact["filename"].endswith(f"_CP-DR_{expected_date}.md")
        assert set(artifact["payload"]) == {
            "schema_version", "module_id", "transport", "host_confidence", "canonical_output",
            "methodology", "source_set", "upstream_artifacts",
        }
        assert artifact["payload"]["transport"]["module_id"] == "CP-DR"
        assert artifact["payload"]["canonical_output"]["filename"] == artifact["filename"]
        rerendered_filename, rerendered_markdown = workflow_domain.render_cpdr_markdown(
            CPDRPayload.model_validate(artifact["payload"]["transport"]),
            artifact["payload"]["host_confidence"],
            completed["created_at"][:10],
            artifact["payload"]["upstream_artifacts"],
        )
        assert (rerendered_filename, rerendered_markdown) == (artifact["filename"], artifact["markdown"])
        assert [line[3:] for line in artifact["markdown"].splitlines() if line.startswith("## ")] == ["Audit Summary", "Analysis", "Evidence Trace", "Source Registry", "Gaps & Conflicts", "QA Validation"]
        assert artifact["markdown"].split("## Analysis", 1)[1].lstrip().startswith("### Executive answer")
        assert len(list_artifacts(ledger_set, run_id=run["id"], module_id="CP-DR")) == 1
        assert completed["research"]["budget_used"]["provider_retries"] == 1
        assert completed["research"]["budget_used"]["repairs"] == 1
        assert completed["research"]["budget_used"]["turns"] == 5
        original_artifact = copy.deepcopy(artifact)
        mutations = [
            lambda item: item["payload"]["host_confidence"].update(confidence_score=99),
            lambda item: item["payload"]["canonical_output"].update(filename="forged.md"),
            lambda item: item.update(markdown=item["markdown"] + "\nforged"),
            lambda item: item["payload"]["methodology"].update(approved_plan_hash="sha256:forged"),
            lambda item: item["payload"]["source_set"].update(version=999),
            lambda item: item["payload"].update(upstream_artifacts=[]),
        ]
        for mutate in mutations:
            forged = copy.deepcopy(original_artifact)
            mutate(forged)
            replace_artifact(ledger_set, artifact["id"], forged)
            with pytest.raises(ValueError, match="RUN_NOT_READY"):
                build_snapshot_payload(
                    ledger_set.runs,
                    ledger_set.sources,
                    ledger_set.runs.get_run(run["id"]) or {},
                    runtime.bundle,
                )
        replace_artifact(ledger_set, artifact["id"], original_artifact)
        snapshot = runtime.accept_run(case["id"], run["id"], "analyst")
        assert any(item["module_id"] == "CP-DR" for item in snapshot["artifacts"])
        persisted = json.dumps({"run": completed, "events": ledger_set.runs.events_after(run["id"]), "audit": ledger_set.publications.list_audit()})
        for secret in ("test-only-key", "Issuer liquidity was USD 100m", "CAOS CP-DR RESEARCH AUTHORITY", "VALIDATION ERRORS"):
            assert secret not in persisted
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(environment="production", storage_dir=Path("/tmp/caos-cpdr-disabled"), deploy_v_root=DEPLOY_V), "AGENT_PROVIDER_UNAVAILABLE"),
        (Settings(environment="production", storage_dir=Path("/tmp/caos-cpdr-no-key"), deploy_v_root=DEPLOY_V, cpdr_agent_enabled=True, cpdr_pilot_subjects=("analyst",)), "AGENT_PROVIDER_UNAVAILABLE"),
    ],
)
def test_approved_cpdr_disabled_or_missing_key_fails_explicitly(settings: Settings, expected: str) -> None:
    ledger_set = MemoryLedgerSet()
    runtime = WorkflowRuntime(
        ledger_set.runs, ledger_set.sources, DeployVBundle(DEPLOY_V), settings
    )
    case = ledger_set.runs.create_case("CP-DR", "Issuer", "Testing", "analyst")
    seed_source(
        ledger_set,
        case["id"],
        "analyst",
        sha256="e" * 64,
        blocks=[{"block_id": "b00001", "locator": {"line": 1}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    )
    brief = {"research_question": "Question", "decision_context": "Context", "as_of_date": "2026-08-23", "time_horizon": "2029", "must_answer": [], "exclusions": []}
    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = ledger_set.runs.get_run(run["id"])
        assert paused is not None
        runtime.approve_research_plan(run["id"], "analyst", paused["research"]["proposed_plan_hash"])
        runtime._execute(run["id"], "analyst")
        failed = ledger_set.runs.get_run(run["id"])
        assert failed is not None and failed["error"]["code"] == expected
        assert not list_artifacts(ledger_set, run_id=run["id"], module_id="CP-DR")
    finally:
        runtime.close()


def _approved_cpdr_case(
    ledger_set: MemoryLedgerSet | None = None,
    provider: _FakeProvider | None = None,
) -> tuple[MemoryLedgerSet, WorkflowRuntime, dict[str, Any], str]:
    ledger_set = ledger_set or MemoryLedgerSet()
    settings = Settings(
        environment="production",
        storage_dir=Path("/tmp/caos-cpdr-matrix"),
        deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key",
        cpdr_agent_enabled=True,
        cpdr_pilot_subjects=("analyst",),
    )
    runtime = WorkflowRuntime(
        ledger_set.runs,
        ledger_set.sources,
        DeployVBundle(DEPLOY_V),
        settings,
        provider=provider,
    )
    case = ledger_set.runs.create_case(
        "CP-DR matrix", "Issuer", "Testing", "analyst"
    )
    source = seed_source(
        ledger_set,
        case["id"],
        "analyst",
        filename="issuer.txt",
        sha256="e" * 64,
        blocks=[{"block_id": "b00001", "locator": {"line": 1}, "text": "Issuer liquidity was USD 100m at 2026-08-23.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    )
    source_id = source["id"]
    seed_source(
        ledger_set,
        case["id"],
        "analyst",
        filename="facility.txt",
        sha256="f" * 64,
        blocks=[{"block_id": "b00002", "locator": {"line": 2}, "text": "The facility remains available through 2029.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    )
    brief = {"research_question": "Can the issuer refinance?", "decision_context": "Underwrite risk.", "as_of_date": "2026-08-23", "time_horizon": "Through 2029", "must_answer": [], "exclusions": []}
    run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
    runtime._execute(run["id"], "analyst")
    paused = ledger_set.runs.get_run(run["id"])
    assert paused is not None
    runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
    approved = ledger_set.runs.get_run(run["id"])
    assert approved is not None
    return ledger_set, runtime, approved, source_id


def _approved_final(ledger_set: MemoryLedgerSet, approved: dict[str, Any], source_id: str) -> dict[str, Any]:
    cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
    cp0 = ledger_set.runs.get_artifact(cp0_node["artifact_id"])
    assert cp0 is not None
    source_set = ledger_set.sources.source_set(approved["plan"]["source_set_id"])
    assert source_set is not None
    secondary_source_id = next(item for item in source_set["source_ids"] if item != source_id)
    workstreams = approved["research"]["proposed_plan"]["workstreams"]
    return _cpdr_payload(
        run_id=approved["id"],
        case_id=approved["case_id"],
        source_set_id=source_set["id"],
        source_set_version=source_set["version"],
        approved_plan_hash=approved["research"]["approved_plan_hash"],
        upstream_digests=[cp0["digest"]],
        scope_key=approved["case_id"].replace("_", "-"),
        workstream_findings=[
            {"workstream_id": item["id"], "finding": "The lane is supported." if index == 0 else "No additional material claim was required.", "claim_ids": ["C-1"] if index == 0 else [], "status": "complete"}
            for index, item in enumerate(workstreams)
        ],
        material_claims=[{**_cpdr_payload()["material_claims"][0], "workstream_id": workstreams[0]["id"], "evidence_refs": [{"source_id": source_id, "block_id": "b00001"}, {"source_id": secondary_source_id, "block_id": "b00002"}]}],
        evidence=[
            {**_cpdr_payload()["evidence"][0], "source_id": source_id},
            {**_cpdr_payload()["evidence"][0], "evidence_id": "E-2", "source_id": secondary_source_id, "source_digest": "f" * 64, "block_id": "b00002", "locator": "{\"line\":2}"},
        ],
    )


def _canonical_cpdr_artifact(ledger_set: MemoryLedgerSet, runtime: WorkflowRuntime, approved: dict[str, Any], source_id: str) -> dict[str, Any]:
    cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
    cp0 = ledger_set.runs.get_artifact(cp0_node["artifact_id"])
    source_set = ledger_set.sources.source_set(approved["plan"]["source_set_id"])
    assert cp0 is not None and source_set is not None
    upstream = [{"module_id": "CP-0", "artifact_id": cp0["id"], "digest": cp0["digest"]}]
    raw = _approved_final(ledger_set, approved, source_id)
    secondary_source_id = next(item for item in source_set["source_ids"] if item != source_id)
    returned = {
        (source_id, "b00001"): {
            "source_digest": "e" * 64, "origin_family": "e" * 64, "authority_class": "unclassified",
            "locator": "{\"line\":1}", "extractor_version": "builtin-v1", "confidence": "HIGH",
        },
        (secondary_source_id, "b00002"): {
            "source_digest": "f" * 64, "origin_family": "f" * 64, "authority_class": "unclassified",
            "locator": "{\"line\":2}", "extractor_version": "builtin-v1", "confidence": "HIGH",
        },
    }
    host = {key: raw[key] for key in _cpdr_host()}
    workstreams = {item["id"] for item in approved["research"]["proposed_plan"]["workstreams"]}
    payload = validate_cpdr_payload(
        raw, host, workstreams, returned, approved["research"]["proposed_plan"], approved["research"]["brief"]
    )
    confidence = runtime.bundle.cpdr_confidence(confidence_inputs(payload, returned))
    filename, markdown = workflow_domain.render_cpdr_markdown(payload, confidence, approved["created_at"][:10], upstream)
    envelope = workflow_domain._build_cpdr_envelope(
        payload.model_dump(mode="json"), confidence, filename, markdown, runtime.bundle.build_id,
        approved["research"]["approved_plan_hash"], source_set, upstream,
    )
    fingerprint = digest({
        "plan": approved["plan"]["plan_digest"], "module": "CP-DR", "source_set": source_set,
        "source_ids": list(source_set["source_ids"]), "upstream_artifacts": upstream,
    })
    return {
        "id": "art-canonical", "case_id": approved["case_id"], "run_id": approved["id"], "module_id": "CP-DR",
        "created_by": "analyst", "payload": envelope, "markdown": markdown, "filename": filename,
        "digest": digest(envelope), "input_fingerprint": fingerprint, "created_at": approved["created_at"],
    }


@pytest.mark.parametrize(
    "mutation",
    ["plan_hash", "model", "source_set", "cp0"],
)
def test_cpdr_authority_mismatches_fail_closed(mutation: str) -> None:
    ledger_set, runtime, approved, _ = _approved_cpdr_case()
    try:
        if mutation == "plan_hash":
            research = copy.deepcopy(approved["research"])
            research["approved_plan_hash"] = "sha256:" + "b" * 64
            mutate_run(ledger_set, approved["id"], research=research)
        elif mutation == "model":
            research = copy.deepcopy(approved["research"])
            research["model"] = "other-model"
            mutate_run(ledger_set, approved["id"], research=research)
        elif mutation == "source_set":
            source_set = ledger_set.sources.current_source_set(approved["case_id"])
            assert source_set is not None
            replace_current_source_set(
                ledger_set,
                approved["case_id"],
                {**source_set, "id": "changed", "version": source_set["version"] + 1},
            )
        else:
            cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
            cp0 = ledger_set.runs.get_artifact(cp0_node["artifact_id"])
            assert cp0 is not None
            cp0["payload"]["status"] = "BLOCKED"
            replace_artifact(ledger_set, cp0["id"], cp0)
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_AUTHORITY_MISMATCH"
        assert not list_artifacts(ledger_set, run_id=approved["id"], module_id="CP-DR")
    finally:
        runtime.close()


def test_cpdr_reclaimed_unresolved_inflight_fails_closed() -> None:
    ledger_set, runtime, approved, _ = _approved_cpdr_case()
    try:
        research = copy.deepcopy(approved["research"])
        research["inflight_request_digest"] = "unknown-spend"
        mutate_run(ledger_set, approved["id"], research=research)
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
    finally:
        runtime.close()


def test_cpdr_reconciled_attempt_without_artifact_restarts_with_remaining_budget() -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    research = copy.deepcopy(approved["research"])
    research.update(phase="researching", inflight_request_digest=None)
    mutate_run(ledger_set, approved["id"], research=research)
    final = _approved_final(ledger_set, approved, source_id)
    _queue_cpdr_success(provider, final, source_id)
    try:
        runtime._execute(approved["id"], "replacement")
        completed = ledger_set.runs.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert completed["research"]["phase"] == "complete"
    finally:
        runtime.close()


def test_cpdr_existing_fingerprint_is_relinked_without_provider_call() -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    recovered = _canonical_cpdr_artifact(ledger_set, runtime, approved, source_id)
    assert cpdr_artifact_is_valid(ledger_set.runs, ledger_set.sources, approved, cpdr_node, recovered, runtime.bundle)
    replace_artifact(ledger_set, recovered["id"], recovered)
    research = copy.deepcopy(approved["research"])
    research["phase"] = "researching"
    mutate_run(ledger_set, approved["id"], research=research)
    try:
        runtime._execute(approved["id"], "replacement")
        completed = ledger_set.runs.get_run(approved["id"])
        linked = next(node for node in completed["nodes"] if node["id"] == cpdr_node["id"]) if completed else None
        assert completed is not None and completed["status"] == "succeeded"
        assert linked is not None and linked["artifact_id"] == recovered["id"]
        assert len(list_artifacts(ledger_set, module_id="CP-DR")) == 1
        assert provider.calls == []
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "mutation", ["markdown", "transport", "confidence", "filename", "digest", "fingerprint", "plan_hash", "withdrawn"]
)
def test_strict_cpdr_artifact_validator_rejects_noncanonical_artifacts(mutation: str) -> None:
    ledger_set, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(ledger_set, runtime, approved, source_id)
    invalid = copy.deepcopy(canonical)
    if mutation == "markdown":
        invalid["markdown"] += "forged\n"
    elif mutation == "transport":
        invalid["payload"]["transport"]["evidence"][0]["independence_family"] = "provider-forged-family"
        invalid["digest"] = digest(invalid["payload"])
    elif mutation == "confidence":
        invalid["payload"]["host_confidence"]["confidence_score"] += 1
        invalid["digest"] = digest(invalid["payload"])
    elif mutation == "filename":
        invalid["filename"] = "forged.md"
    elif mutation == "digest":
        invalid["digest"] = "0" * 64
    elif mutation == "fingerprint":
        invalid["input_fingerprint"] = "forged"
    elif mutation == "plan_hash":
        research = copy.deepcopy(approved["research"])
        research["approved_plan_hash"] = "sha256:" + "0" * 64
        mutate_run(ledger_set, approved["id"], research=research)
        approved = ledger_set.runs.get_run(approved["id"]) or approved
    else:
        source_set = ledger_set.sources.source_set(approved["plan"]["source_set_id"])
        assert source_set is not None
        secondary_source_id = next(item for item in source_set["source_ids"] if item != source_id)
        mutate_source(ledger_set, secondary_source_id, withdrawn=True)
    try:
        assert not cpdr_artifact_is_valid(ledger_set.runs, ledger_set.sources, approved, cpdr_node, invalid, runtime.bundle)
        replace_artifact(ledger_set, invalid["id"], invalid)
        mutate_node(ledger_set, cpdr_node["id"], status="succeeded", artifact_id=invalid["id"])
        mutate_run(ledger_set, approved["id"], status="succeeded")
        with pytest.raises(ValueError, match="RUN_NOT_READY"):
            build_snapshot_payload(ledger_set.runs, ledger_set.sources, ledger_set.runs.get_run(approved["id"]) or {}, runtime.bundle)
    finally:
        runtime.close()


def test_strict_cpdr_artifact_validator_requires_real_vendored_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_set, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(ledger_set, runtime, approved, source_id)
    monkeypatch.setattr(
        runtime.bundle,
        "validate_cpdr_handoff",
        lambda *_args, **_kwargs: type("InvalidHandoff", (), {"identity_mismatches": [], "errors": ["invalid"], "exit_code": 1})(),
    )
    try:
        assert not cpdr_artifact_is_valid(ledger_set.runs, ledger_set.sources, approved, cpdr_node, canonical, runtime.bundle)
    finally:
        runtime.close()


@pytest.mark.parametrize("entrypoint", ["reuse", "run_success", "snapshot"])
def test_strict_cpdr_artifact_entrypoints_require_current_bundle_integrity(
    monkeypatch: pytest.MonkeyPatch, entrypoint: str,
) -> None:
    ledger_set, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(ledger_set, runtime, approved, source_id)
    replace_artifact(ledger_set, canonical["id"], canonical)

    def fail_integrity() -> Any:
        raise MethodologyError("forced current integrity failure")

    monkeypatch.setattr(runtime.bundle, "verify", fail_integrity)
    try:
        assert not cpdr_artifact_is_valid(ledger_set.runs, ledger_set.sources, approved, cpdr_node, canonical, runtime.bundle)
        if entrypoint == "reuse":
            research = copy.deepcopy(approved["research"])
            research["phase"] = "researching"
            mutate_run(ledger_set, approved["id"], research=research)
            runtime._execute(approved["id"], "replacement")
            failed = ledger_set.runs.get_run(approved["id"])
            assert failed is not None and failed["status"] == "failed"
            assert failed["error"]["code"] == "AGENT_AUTHORITY_MISMATCH"
        elif entrypoint == "run_success":
            mutate_node(ledger_set, cpdr_node["id"], status="succeeded", artifact_id=canonical["id"])
            runtime._execute(approved["id"], "final-validator")
            failed = ledger_set.runs.get_run(approved["id"])
            assert failed is not None and failed["status"] == "failed"
            assert failed["error"]["code"] == "DAG_BLOCKED"
        else:
            mutate_node(ledger_set, cpdr_node["id"], status="succeeded", artifact_id=canonical["id"])
            mutate_run(ledger_set, approved["id"], status="succeeded")
            with pytest.raises(ValueError, match="RUN_NOT_READY"):
                build_snapshot_payload(ledger_set.runs, ledger_set.sources, ledger_set.runs.get_run(approved["id"]) or {}, runtime.bundle)
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("cross_case", "AGENT_AUTHORITY_MISMATCH"),
        ("unpinned", "AGENT_AUTHORITY_MISMATCH"),
        ("withdrawn", "AGENT_AUTHORITY_MISMATCH"),
        ("absent_block", "AGENT_OUTPUT_INVALID"),
        ("duplicate_block", "AGENT_OUTPUT_INVALID"),
    ],
)
def test_cpdr_evidence_reads_enforce_case_pin_withdrawal_and_block_identity(mode: str, expected: str) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    tool_source = source_id
    tool_block = "b00001"
    if mode == "cross_case":
        mutate_source(ledger_set, source_id, case_id="other-case")
    elif mode == "unpinned":
        tool_source = seed_source(
            ledger_set,
            approved["case_id"],
            "analyst",
            sha256="9" * 64,
            blocks=[{"block_id": "b00001", "locator": {"line": 1}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
        )["id"]
    elif mode == "withdrawn":
        mutate_source(ledger_set, source_id, withdrawn=True)
    elif mode == "absent_block":
        tool_block = "missing"
    block_ids = [tool_block, tool_block] if mode == "duplicate_block" else [tool_block]
    provider.responses.append(ProviderMessage(
        content=[ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": tool_source, "block_ids": block_ids})],
        stop_reason="tool_use",
        usage=ProviderUsage(20, 30),
    ))
    provider.counts.append(20)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == expected
    finally:
        runtime.close()


@pytest.mark.parametrize("budget", ["turns", "input_tokens", "output_tokens", "active_minutes", "evidence_reads", "evidence_bytes"])
def test_cpdr_runwide_budget_ceilings_fail_before_overspend(budget: str) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    research = copy.deepcopy(approved["research"])
    research["budget_limits"][budget] = 0 if budget != "evidence_bytes" else 1
    mutate_run(ledger_set, approved["id"], research=research)
    if budget in {"evidence_reads", "evidence_bytes"}:
        response = ProviderMessage(
            content=[ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})],
            stop_reason="tool_use",
            usage=ProviderUsage(20, 30),
        )
    else:
        response = ProviderMessage(
            content=[ProviderBlock(type="text", text="{}")],
            stop_reason="end_turn",
            usage=ProviderUsage(20, 30),
        )
    provider.responses.append(response)
    provider.counts.append(20)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert not list_artifacts(ledger_set, run_id=approved["id"], module_id="CP-DR")
    finally:
        runtime.close()


@pytest.mark.parametrize("limit", ["blocks", "bytes"])
def test_cpdr_manifest_ceiling_fails_before_provider_construction(limit: str) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    source = ledger_set.sources.get_source(source_id)
    assert source is not None
    if limit == "blocks":
        blocks = [
            {"block_id": f"b{index:05d}", "locator": {"line": index}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}
            for index in range(2_001)
        ]
    else:
        blocks = copy.deepcopy(source["blocks"])
        blocks[0]["locator"] = {"section": "x" * (256 * 1_024)}
    mutate_source(ledger_set, source_id, blocks=blocks)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert provider.calls == []
    finally:
        runtime.close()


@pytest.mark.parametrize("field", ["filename", "media_type", "locator", "extractor_version", "confidence"])
def test_cpdr_manifest_rejects_oversized_fields_before_encoding(monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    source = ledger_set.sources.get_source(source_id)
    assert source is not None
    sentinel = "manifest-sentinel-" + "x" * (512 * 1_024)
    if field in {"filename", "media_type"}:
        source[field] = sentinel
    elif field == "locator":
        source["blocks"][0][field] = {"nested": sentinel}
    else:
        source["blocks"][0][field] = sentinel
    mutate_source(
        ledger_set,
        source_id,
        filename=source["filename"],
        media_type=source["media_type"],
        blocks=source["blocks"],
    )
    original_dumps = workflow_domain.json.dumps

    def guarded_dumps(value: Any, *args: Any, **kwargs: Any) -> str:
        if isinstance(value, dict):
            assert sentinel not in value.values()
            locator = value.get("locator")
            assert not isinstance(locator, dict) or sentinel not in locator.values()
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(workflow_domain.json, "dumps", guarded_dumps)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert provider.calls == []
    finally:
        runtime.close()


def test_cpdr_manifest_rejects_many_short_locator_nodes_before_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    locator = {"groups": [list(range(100)) for _ in range(6)]}
    source = ledger_set.sources.get_source(source_id)
    assert source is not None
    blocks = copy.deepcopy(source["blocks"])
    blocks[0]["locator"] = locator
    mutate_source(ledger_set, source_id, blocks=blocks)
    original_dumps = workflow_domain.json.dumps

    def guarded_dumps(value: Any, *args: Any, **kwargs: Any) -> str:
        assert not isinstance(value, dict) or value.get("locator") is not locator
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(workflow_domain.json, "dumps", guarded_dumps)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert provider.calls == []
    finally:
        runtime.close()


def test_cpdr_manifest_exact_block_and_encoded_byte_boundaries_are_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider([], counts=[ProviderUnavailable("boundary reached provider")])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    expected_manifest = []
    source_set = ledger_set.sources.source_set(approved["plan"]["source_set_id"])
    assert source_set is not None
    for manifest_source_id in source_set["source_ids"]:
        source = ledger_set.sources.get_source(manifest_source_id)
        assert source is not None
        block = source["blocks"][0]
        expected_manifest.append({
            "source_id": manifest_source_id,
            "digest": source["sha256"],
            "filename": source["filename"],
            "media_type": source["media_type"],
            "blocks": [{
                "block_id": block["block_id"], "locator": block["locator"],
                "extractor_version": block["extractor_version"], "confidence": block["confidence"],
            }],
        })
    encoded_bytes = len(json.dumps(expected_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    monkeypatch.setattr(workflow_domain, "MAX_CPDR_MANIFEST_BLOCKS", 2)
    monkeypatch.setattr(workflow_domain, "MAX_CPDR_MANIFEST_BYTES", encoded_bytes)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_PROVIDER_UNAVAILABLE"
        assert [kind for kind, _request in provider.calls] == ["count_tokens"]
    finally:
        runtime.close()


def test_cpdr_unexpected_post_provider_failure_is_sanitized_and_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    final = _approved_final(ledger_set, approved, source_id)
    _queue_cpdr_success(provider, final, source_id)
    monkeypatch.setattr(workflow_domain, "render_cpdr_markdown", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("secret-post-provider")))
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert failed["research"]["phase"] == "failed"
        assert any(item.get("terminal_code") == "AGENT_OUTPUT_INVALID" for item in failed["research"]["attempts"])
        assert "secret-post-provider" not in json.dumps({"run": failed, "events": ledger_set.runs.events_after(approved["id"])})
    finally:
        runtime.close()


def test_cpdr_prior_179_seconds_caps_next_operation_to_one_second(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider([], counts=[ProviderUnavailable("captured")])
    ledger_set, runtime, approved, _source_id = _approved_cpdr_case(provider=provider)
    research = copy.deepcopy(approved["research"])
    research["budget_used"]["active_minutes"] = 179 / 60
    mutate_run(ledger_set, approved["id"], research=research)
    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: 1_000.0)
    try:
        runtime._execute(approved["id"], "approver")
        assert provider.calls and 0 < provider.calls[0][1].timeout <= 1.0
        assert not list_artifacts(ledger_set, run_id=approved["id"], module_id="CP-DR")
    finally:
        runtime.close()


def test_cpdr_approval_wait_is_excluded_while_planning_time_is_charged(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_set = MemoryLedgerSet()
    settings = Settings(
        environment="production", storage_dir=Path("/tmp/caos-cpdr-approval-time"), deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key", cpdr_agent_enabled=True, cpdr_pilot_subjects=("analyst",),
    )
    bundle = DeployVBundle(DEPLOY_V)
    provider = _FakeProvider([], counts=[ProviderUnavailable("stop after timing check")])
    runtime = WorkflowRuntime(ledger_set.runs, ledger_set.sources, bundle, settings, provider=provider)
    case = ledger_set.runs.create_case("Approval time", "Issuer", "Testing", "analyst")
    seed_source(
        ledger_set,
        case["id"],
        "analyst",
        sha256="a" * 64,
        blocks=[{"block_id": "b00001", "locator": {"line": 1}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    )
    brief = {"research_question": "Question", "decision_context": "Context", "as_of_date": "2026-08-23", "time_horizon": "2029", "must_answer": [], "exclusions": []}

    class Clock:
        now = 0.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)
    original_plan = bundle.plan_research

    def measured_plan(*args: Any, **kwargs: Any) -> Any:
        result = original_plan(*args, **kwargs)
        Clock.now += 2.0
        return result

    monkeypatch.setattr(bundle, "plan_research", measured_plan)

    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = ledger_set.runs.get_run(run["id"])
        assert paused is not None and paused["research"]["budget_used"]["active_minutes"] == pytest.approx(2 / 60)
        Clock.now += 10_000
        runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
        runtime._execute(run["id"], "approver")
        failed = ledger_set.runs.get_run(run["id"])
        assert failed is not None and failed["research"]["budget_used"]["active_minutes"] == pytest.approx(2 / 60)
    finally:
        runtime.close()


def test_cpdr_slow_render_is_charged_before_artifact_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    research = copy.deepcopy(approved["research"])
    research["budget_used"]["active_minutes"] = 179 / 60
    mutate_run(ledger_set, approved["id"], research=research)
    final = _approved_final(ledger_set, approved, source_id)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    _queue_cpdr_success(provider, final, source_id)

    original_render = workflow_domain.render_cpdr_markdown

    def slow_render(*args: Any, **kwargs: Any) -> Any:
        rendered = original_render(*args, **kwargs)
        Clock.now += 2.0
        return rendered

    monkeypatch.setattr(workflow_domain, "render_cpdr_markdown", slow_render)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert not list_artifacts(ledger_set, run_id=approved["id"], module_id="CP-DR")
    finally:
        runtime.close()


@pytest.mark.parametrize("operation", ["scorer", "renderer", "validator", "envelope"])
def test_cpdr_throwing_host_operations_charge_active_time(monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    provider = _FakeProvider([])
    ledger_set, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    final = _approved_final(ledger_set, approved, source_id)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    _queue_cpdr_success(provider, final, source_id)

    def throwing(*_args: Any, **_kwargs: Any) -> Any:
        Clock.now += 2.0
        raise RuntimeError("host operation failed")

    if operation == "scorer":
        monkeypatch.setattr(runtime.bundle, "cpdr_confidence", throwing)
    elif operation == "renderer":
        monkeypatch.setattr(workflow_domain, "render_cpdr_markdown", throwing)
    elif operation == "validator":
        monkeypatch.setattr(runtime.bundle, "validate_cpdr_handoff", throwing)
    else:
        monkeypatch.setattr(workflow_domain, "_build_cpdr_envelope", throwing)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert failed["research"]["budget_used"]["active_minutes"] >= 2 / 60
    finally:
        runtime.close()


def test_cpdr_no_pending_final_validation_is_charged_before_run_success(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_set, runtime, approved, source_id = _approved_cpdr_case()
    artifact = _canonical_cpdr_artifact(ledger_set, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    replace_artifact(ledger_set, artifact["id"], artifact)
    mutate_node(ledger_set, cpdr_node["id"], status="succeeded", artifact_id=artifact["id"])
    research = copy.deepcopy(approved["research"])
    research["phase"] = "complete"
    research["budget_used"]["active_minutes"] = 179 / 60
    mutate_run(ledger_set, approved["id"], research=research)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)
    original_score = runtime.bundle.cpdr_confidence

    def slow_score(*args: Any, **kwargs: Any) -> Any:
        result = original_score(*args, **kwargs)
        Clock.now += 2.0
        return result

    monkeypatch.setattr(runtime.bundle, "cpdr_confidence", slow_score)
    try:
        runtime._execute(approved["id"], "final-validator")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 181 / 60
        assert not any(item["event"] == "run.succeeded" for item in ledger_set.runs.events_after(approved["id"]))
    finally:
        runtime.close()


def _ready_cpdr_finalization() -> tuple[MemoryLedgerSet, WorkflowRuntime, dict[str, Any], dict[str, Any], dict[str, Any]]:
    ledger_set, runtime, approved, source_id = _approved_cpdr_case()
    artifact = _canonical_cpdr_artifact(ledger_set, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    replace_artifact(ledger_set, artifact["id"], artifact)
    mutate_node(ledger_set, cpdr_node["id"], status="succeeded", artifact_id=artifact["id"])
    research = copy.deepcopy(approved["research"])
    research["phase"] = "complete"
    mutate_run(ledger_set, approved["id"], research=research)
    return ledger_set, runtime, approved, cpdr_node, artifact


def _assert_run_cannot_be_accepted(runtime: WorkflowRuntime, run: dict[str, Any]) -> None:
    with pytest.raises(WorkflowError, match="RUN_NOT_READY"):
        runtime.accept_run(run["case_id"], run["id"], "approver")


def test_cpdr_finalization_allowance_is_fixed_and_ponytail_bounded() -> None:
    assert 2.0 < workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS <= 5.0


def test_cpdr_179_seconds_cannot_enter_atomic_success_finalization() -> None:
    ledger_set, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    research = copy.deepcopy(approved["research"])
    research["phase"] = "complete"
    research["budget_used"]["active_minutes"] = 179 / 60
    mutate_run(ledger_set, approved["id"], research=research)
    try:
        runtime._execute(approved["id"], "final-reserve")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 180 / 60
        assert not any(item["event"] == "run.succeeded" for item in ledger_set.runs.events_after(approved["id"]))
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()



def test_gateway_fake_clock_charges_slow_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    moments = iter([0.0, 0.0, 0.0, 0.0, 0.0, 2.0])
    monkeypatch.setattr(provider_module.time, "monotonic", lambda: next(moments))
    charged: list[float] = []
    final_response = _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])

    result = AnthropicGateway("key", "claude-sonnet-4-6", client=_Client([final_response])).run(
        system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
        lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None, active_time=charged.append,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert charged[-1] == 2.0


@pytest.mark.parametrize("operation", ["count", "create"])
def test_gateway_crossing_active_ceiling_records_terminal_attempt(operation: str) -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    calls = 0
    client = _Client([_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])

    def charge(_elapsed: float) -> None:
        nonlocal calls
        calls += 1
        if (operation == "count" and calls == 1) or (operation == "create" and calls == 2):
            raise AgentError("AGENT_BUDGET_EXCEEDED")

    with pytest.raises(AgentError, match="AGENT_BUDGET_EXCEEDED"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)), active_time=charge,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert any(details.get("terminal_code") == "AGENT_BUDGET_EXCEEDED" for _kind, details in events)


def test_gateway_transient_ordinary_record_failure_is_sanitized_and_terminalized() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    failed_once = False

    def record(kind: str, **details: Any) -> None:
        nonlocal failed_once
        if kind != "terminal" and not failed_once:
            failed_once = True
            raise RuntimeError("sensitive transient record failure")
        events.append((kind, details))

    client = _Client([_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])
    with pytest.raises(AgentError) as captured:
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=record, active_time=lambda _elapsed: None, semaphore=threading.BoundedSemaphore(2),
        )
    assert captured.value.code == "AGENT_OUTPUT_INVALID"
    assert any(details.get("terminal_code") == "AGENT_OUTPUT_INVALID" for _kind, details in events)
    assert "sensitive transient record failure" not in json.dumps(events)


def test_gateway_post_count_budget_check_failure_is_terminalized() -> None:
    current = True
    events: list[tuple[str, dict[str, Any]]] = []

    class BudgetLosingMessages(_Messages):
        def count_tokens(self, **kwargs: Any) -> Any:
            nonlocal current
            current = False
            return type("Count", (), {"input_tokens": 20})()

    client = _Client([])
    client.messages = BudgetLosingMessages([])

    def budget_check() -> None:
        if not current:
            raise AgentError("AGENT_BUDGET_EXCEEDED")

    with pytest.raises(AgentError) as captured:
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=budget_check, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)), active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert captured.value.code == "AGENT_BUDGET_EXCEEDED"
    assert any(details.get("terminal_code") == "AGENT_BUDGET_EXCEEDED" for _kind, details in events)


@pytest.mark.parametrize(
    "operation",
    ["reconcile", "generation_record", "provider_retry_record", "evidence_handling", "final_validation"],
)
@pytest.mark.parametrize("failure_kind", ["ordinary", "agent"])
def test_gateway_all_post_interaction_failures_are_sanitized_and_terminalized(
    operation: str, failure_kind: str,
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    secret = f"secret-{operation}-{failure_kind}"

    def fail() -> None:
        if failure_kind == "agent":
            raise AgentError("AGENT_BUDGET_EXCEEDED")
        raise RuntimeError(secret)

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    if operation == "provider_retry_record":
        client = _Client([
            anthropic.APITimeoutError(request),
            _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
        ])
    elif operation == "evidence_handling":
        client = _Client([
            _Response(
                "tool_use",
                [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": "src-1", "block_ids": ["b1"]})],
            ),
        ])
    else:
        client = _Client([_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])

    def record(kind: str, **details: Any) -> None:
        if (operation == "generation_record" and kind == "generation") or (
            operation == "provider_retry_record" and kind == "provider_retry"
        ):
            fail()
        events.append((kind, details))

    with pytest.raises(AgentError) as captured:
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority",
            user="brief",
            read_evidence=(lambda *_: fail()) if operation == "evidence_handling" else (lambda *_: []),
            validate=(lambda _value: fail()) if operation == "final_validation" else (lambda value: value),
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=(lambda *_: fail()) if operation == "reconcile" else (lambda *_: None),
            record=record,
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )

    expected = "AGENT_BUDGET_EXCEEDED" if failure_kind == "agent" else "AGENT_OUTPUT_INVALID"
    assert captured.value.code == expected
    assert any(details.get("terminal_code") == expected for _kind, details in events)
    assert secret not in json.dumps(events)


def test_gateway_post_interaction_fencing_remains_silent() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client([_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])])

    with pytest.raises(JobFencedError):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None,
            reconcile=lambda *_: (_ for _ in ()).throw(JobFencedError("lost after interaction")),
            record=lambda kind, **details: events.append((kind, details)), active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )

    assert not any(kind == "terminal" for kind, _details in events)


def test_gateway_discards_result_when_lease_is_lost_during_sdk_call() -> None:
    current = True
    records: list[str] = []

    class LosingMessages(_Messages):
        def count_tokens(self, **kwargs: Any) -> Any:
            nonlocal current
            current = False
            return type("Count", (), {"input_tokens": 20})()

    client = _Client([])
    client.messages = LosingMessages([])
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=client)

    def lease_check() -> None:
        if not current:
            raise JobFencedError("lost")

    with pytest.raises(JobFencedError):
        gateway.run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lease_check, reserve=lambda *_: records.append("reserved"), reconcile=lambda *_: records.append("reconciled"),
            record=lambda *_args, **_kwargs: records.append("recorded"), active_time=lambda _elapsed: records.append("timed"),
            semaphore=threading.BoundedSemaphore(2),
        )
    assert records == []


def test_cpdr_failure_metadata_does_not_persist_secret_body_prompt_or_evidence() -> None:
    provider = _FakeProvider([], counts=[AgentError("AGENT_PROVIDER_REJECTED", "secret-provider-body provider-body")])
    ledger_set, runtime, approved, _ = _approved_cpdr_case(provider=provider)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledger_set.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_PROVIDER_REJECTED"
        persisted = json.dumps({"run": failed, "events": ledger_set.runs.events_after(approved["id"]), "audit": ledger_set.publications.list_audit()})
        for forbidden in ("test-only-key", "secret-provider-body", "provider-body", "Issuer liquidity was USD 100m", "CAOS CP-DR RESEARCH AUTHORITY"):
            assert forbidden not in persisted
    finally:
        runtime.close()


def test_cpdr_semantic_gates_reject_locator_gapped_complete_coverage_and_hidden_conflict() -> None:
    cases = [
        _cpdr_payload(evidence=[{**_cpdr_payload()["evidence"][0], "locator": "fabricated"}]),
        _cpdr_payload(workstream_findings=[{**_cpdr_payload()["workstream_findings"][0], "status": "gapped"}]),
        _cpdr_payload(coverage_score=99),
        _cpdr_payload(material_claims=[{**_cpdr_payload()["material_claims"][0], "counter_evidence_refs": [{"source_id": "src-1", "block_id": "b00001"}]}]),
    ]
    for value in cases:
        with pytest.raises(CPDRValidationError):
            validate_cpdr_payload(value, _cpdr_host(), {"WS-1"}, _returned_evidence())
