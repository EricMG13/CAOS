from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import anthropic
import httpx2
from anthropic.types import TextBlock, ToolUseBlock
from caos.config import Settings
from caos.contracts import digest
from caos.artifacts.domain import (
    build_snapshot_payload,
    cpdr_artifact_is_valid,
    create_note,
    promote_note,
)
from caos.http import create_app
from caos.memory_ledgers import MemoryLedgerSet
from caos.postgres_ledgers import PostgresLedgerSet
from caos.methodology.bundle import DeployVBundle, MethodologyError
from caos.methodology.cpdr import (
    CPDRPayload,
    CPDRValidationError,
    confidence_inputs,
    validate_cpdr_payload,
)
from caos.methodology.prompt import compile_cpdr_prompts
from caos.store import JobFencedError
from caos.workflows import domain as workflow_domain
from caos.workflows import provider as provider_module
from caos.workflows.domain import WorkflowError, WorkflowRuntime, _LeaseFence
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


DEPLOY_V = (
    Path(__file__).parents[1]
    / "server"
    / "caos"
    / "methodology"
    / "vendor"
    / "deploy_v"
)
WORKER_EVENTS = {
    "run.running",
    "node.running",
    "node.succeeded",
    "node.failed",
    "run.succeeded",
    "run.failed",
}


class _RunLedgerDouble:
    def __init__(self, ledger: object) -> None:
        self.ledger = ledger

    def __getattr__(self, name: str) -> Any:
        return getattr(self.ledger, name)


class _SourceCatalogDouble:
    def __init__(self, ledger: object) -> None:
        self.ledger = ledger
        self.source_overrides: dict[str, dict[str, Any]] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.ledger, name)

    def override_source(self, source_id: str, mutate: Any) -> dict[str, Any]:
        source = self.ledger.get_source(source_id)
        assert source is not None
        mutate(source)
        self.source_overrides[source_id] = source
        return source

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        if source_id in self.source_overrides:
            return copy.deepcopy(self.source_overrides[source_id])
        return self.ledger.get_source(source_id)

    def read_pinned_evidence(
        self,
        case_id: str,
        source_set_id: str,
        source_id: str,
        block_ids: list[str],
    ) -> list[dict[str, Any]]:
        if source_id not in self.source_overrides:
            return self.ledger.read_pinned_evidence(
                case_id, source_set_id, source_id, block_ids
            )
        source_set = self.ledger.source_set(source_set_id)
        source = self.source_overrides[source_id]
        if (
            not source_set
            or source_set.get("case_id") != case_id
            or source_id not in source_set.get("source_ids", [])
            or source.get("case_id") != case_id
            or source.get("withdrawn")
        ):
            raise ValueError("AGENT_AUTHORITY_MISMATCH")
        blocks = {block.get("block_id"): block for block in source.get("blocks", [])}
        if any(block_id not in blocks for block_id in block_ids):
            raise ValueError("AGENT_OUTPUT_INVALID")
        return [
            {
                "source_id": source_id,
                "source_digest": source["sha256"],
                "origin_family": source.get("origin_family", source["sha256"]),
                "authority_class": source.get("authority_class", "unclassified"),
                "block_id": block_id,
                "locator": copy.deepcopy(blocks[block_id].get("locator")),
                "extractor_version": blocks[block_id].get("extractor_version"),
                "confidence": blocks[block_id].get("confidence"),
                "text": blocks[block_id].get("text"),
            }
            for block_id in block_ids
        ]


def _mutate_research(
    ledgers: MemoryLedgerSet,
    run_id: str,
    mutate: Any,
) -> dict[str, Any]:
    run = ledgers.runs.get_run(run_id)
    assert run is not None
    research = copy.deepcopy(run["research"])
    mutate(research)
    token = ledgers.runs.claim(run_id, "test-research-mutation")
    assert token is not None
    ledgers.runs.update_run_fenced(run_id, token, research=research)
    ledgers.runs.finish(run_id, token)
    updated = ledgers.runs.get_run(run_id)
    assert updated is not None
    return updated


def _complete_cpdr_node_for_test(
    ledgers: MemoryLedgerSet,
    approved: dict[str, Any],
    cpdr_node: dict[str, Any],
    artifact: dict[str, Any],
    *,
    reset_to_pending: bool = False,
    finish_job: bool = True,
) -> dict[str, Any]:
    research = copy.deepcopy(approved["research"])
    research["phase"] = "researching" if reset_to_pending else "complete"
    token = ledgers.runs.claim(approved["id"], "test-artifact-seed")
    assert token is not None
    stored = ledgers.runs.complete_node(
        approved["id"],
        token,
        cpdr_node["id"],
        artifact,
        research,
        {"node_id": cpdr_node["id"], "module_id": "CP-DR"},
    )
    if reset_to_pending:
        ledgers.runs.update_node_fenced(
            approved["id"],
            token,
            cpdr_node["id"],
            status="pending",
            artifact_id=None,
        )
    if finish_job:
        ledgers.runs.finish(approved["id"], token)
    return stored


def _queued_ledger_run(
    ledgers: MemoryLedgerSet,
    *,
    dependencies: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    case = ledgers.runs.create_case("Lease test", "Issuer", "Testing", "analyst")
    nodes = (
        [{"module_id": "CP-TEST", "dependencies": dependencies, "stage": 1}]
        if dependencies is not None
        else []
    )
    run = ledgers.runs.create_run_with_nodes(
        case["id"], "analyst", {"nodes": nodes}, nodes
    )
    return run, run["nodes"][0] if nodes else None


def _artifact(run_id: str, module_id: str = "CP-TEST") -> dict[str, Any]:
    return {
        "id": f"artifact-{run_id}",
        "run_id": run_id,
        "module_id": module_id,
        "input_fingerprint": "fingerprint",
    }


def _postgres_url() -> str:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "CAOS_TEST_DATABASE_URL is required for real PostgreSQL lease tests"
        )
    return database_url


def test_replacement_finishes_run_after_atomic_completion_preceded_terminal_events() -> (
    None
):
    ledgers = MemoryLedgerSet()
    run, node = _queued_ledger_run(ledgers, dependencies=[])
    assert node is not None
    token = ledgers.runs.claim(run["id"], "first")
    assert token is not None
    payload: dict[str, Any] = {}
    ledgers.runs.complete_node(
        run["id"],
        token,
        node["id"],
        {
            **_artifact(run["id"]),
            "case_id": run["case_id"],
            "payload": payload,
            "digest": digest(payload),
        },
        None,
        {"node_id": node["id"]},
    )
    ledgers.runs.finish(run["id"], token)
    runtime = WorkflowRuntime(
        ledgers.runs,
        ledgers.sources,
        object(),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-terminal-recovery"),
            deploy_v_root=DEPLOY_V,
        ),
    )  # type: ignore[arg-type]
    try:
        runtime._execute(run["id"], "replacement")
        completed = ledgers.runs.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert completed["events"][-1]["event"] == "run.succeeded"
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "forgery", ["running_node", "missing_artifact", "wrong_artifact"]
)
def test_snapshot_payload_rejects_forged_succeeded_run(forgery: str) -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Snapshot", "Issuer", "Testing", "analyst")
    source = ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "source.txt",
            "media_type": "text/plain",
            "bytes": 6,
            "sha256": "c" * 64,
            "vault_path": None,
            "blocks": [],
        },
        "analyst",
    )
    nodes = [{"module_id": "CP-TEST", "dependencies": [], "stage": 1}]
    run = ledgers.runs.create_run_with_nodes(
        case["id"],
        "analyst",
        {"source_set_id": source["source_set"]["id"], "nodes": nodes},
        nodes,
    )
    node = run["nodes"][0]
    assert node is not None
    token = ledgers.runs.claim(run["id"], "worker")
    assert token is not None
    payload: dict[str, Any] = {}
    ledgers.runs.complete_node(
        run["id"],
        token,
        node["id"],
        {
            **_artifact(run["id"]),
            "case_id": case["id"],
            "payload": payload,
            "digest": digest(payload),
        },
        None,
        {"node_id": node["id"]},
    )
    ledgers.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})
    run = ledgers.runs.get_run(run["id"])
    assert run is not None

    class ForgedRuns(_RunLedgerDouble):
        def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
            if forgery == "missing_artifact":
                return None
            value = self.ledger.get_artifact(artifact_id)  # type: ignore[attr-defined]
            if value is not None and forgery == "wrong_artifact":
                value["module_id"] = "OTHER"
            return value

    if forgery == "running_node":
        run["nodes"][0]["status"] = "running"

    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        build_snapshot_payload(ForgedRuns(ledgers.runs), ledgers.sources, run)


def test_runtime_heartbeat_renews_once_and_is_joined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renewed = threading.Event()

    class HeartbeatRuns(_RunLedgerDouble):
        def __init__(self, ledger: object) -> None:
            super().__init__(ledger)
            self.renewals = 0

        def renew(self, run_id: str, attempt_token: str) -> bool:
            current = self.ledger.renew(run_id, attempt_token)  # type: ignore[attr-defined]
            self.renewals += 1
            renewed.set()
            return current

        def get_run(self, run_id: str) -> dict[str, Any] | None:
            assert renewed.wait(1)
            return self.ledger.get_run(run_id)  # type: ignore[attr-defined,no-any-return]

    real_thread = threading.Thread
    created: list["TrackingThread"] = []

    class TrackingThread(real_thread):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.joined = False
            created.append(self)

        def join(self, timeout: float | None = None) -> None:
            super().join(timeout)
            self.joined = True

    ledgers = MemoryLedgerSet()
    run, _ = _queued_ledger_run(ledgers)
    runs = HeartbeatRuns(ledgers.runs)
    runtime = WorkflowRuntime(
        runs,
        ledgers.sources,
        object(),
        Settings(storage_dir=Path("/tmp/caos-heartbeat"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    monkeypatch.setattr(workflow_domain, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(workflow_domain.threading, "Thread", TrackingThread)
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert workflow_domain.HEARTBEAT_INTERVAL_SECONDS == 0.01
    assert runs.renewals >= 1
    assert len(created) == 1
    assert created[0].joined and not created[0].is_alive()


def test_runtime_heartbeat_is_joined_when_execution_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ExplodingRuns(_RunLedgerDouble):
        def update_run_fenced(
            self, run_id: str, attempt_token: str, **changes: Any
        ) -> None:
            raise RuntimeError("write failed")

    real_thread = threading.Thread
    created: list["TrackingThread"] = []

    class TrackingThread(real_thread):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.joined = False
            created.append(self)

        def join(self, timeout: float | None = None) -> None:
            super().join(timeout)
            self.joined = True

    ledgers = MemoryLedgerSet()
    run, _ = _queued_ledger_run(ledgers)
    runtime = WorkflowRuntime(
        ExplodingRuns(ledgers.runs),
        ledgers.sources,
        object(),
        Settings(storage_dir=Path("/tmp/caos-heartbeat-error"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    monkeypatch.setattr(workflow_domain.threading, "Thread", TrackingThread)
    try:
        with pytest.raises(RuntimeError, match="write failed"):
            runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert len(created) == 1
    assert created[0].joined and not created[0].is_alive()


@pytest.mark.parametrize("renewal_error", [False, True])
def test_runtime_fails_closed_when_heartbeat_loses_lease(
    monkeypatch: pytest.MonkeyPatch, renewal_error: bool
) -> None:
    renewal_attempted = threading.Event()

    class LostLeaseRuns(_RunLedgerDouble):
        def renew(self, run_id: str, attempt_token: str) -> bool:
            renewal_attempted.set()
            if renewal_error:
                raise RuntimeError("renewal failed")
            return False

        def get_run(self, run_id: str) -> dict[str, Any] | None:
            assert renewal_attempted.wait(1)
            return self.ledger.get_run(run_id)  # type: ignore[attr-defined,no-any-return]

    ledgers = MemoryLedgerSet()
    run, _ = _queued_ledger_run(ledgers)
    runtime = WorkflowRuntime(
        LostLeaseRuns(ledgers.runs),
        ledgers.sources,
        object(),
        Settings(storage_dir=Path("/tmp/caos-lost-lease"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    monkeypatch.setattr(workflow_domain, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    current = ledgers.runs.get_run(run["id"])
    assert current is not None and current["status"] == "running"
    assert [event["event"] for event in current["events"]] == ["run.running"]


def test_runtime_serializes_loss_publication_before_lifecycle_write() -> None:
    fence = _LeaseFence()
    write_started = threading.Event()
    release_write = threading.Event()
    loss_started = threading.Event()
    writes: list[str] = []

    def write(value: str) -> None:
        write_started.set()
        assert release_write.wait(1)
        writes.append(value)

    def lose() -> None:
        loss_started.set()
        fence.lose()

    with ThreadPoolExecutor(max_workers=2) as pool:
        writing = pool.submit(fence.call, write, "before-loss")
        assert write_started.wait(1)
        losing = pool.submit(lose)
        assert loss_started.wait(1)
        release_write.set()
        writing.result(timeout=1)
        losing.result(timeout=1)

    with pytest.raises(JobFencedError):
        fence.call(writes.append, "after-loss")
    assert writes == ["before-loss"]


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (False, ["run.running", "node.running", "node.succeeded", "run.succeeded"]),
        (True, ["run.running", "node.running", "node.failed", "run.failed"]),
    ],
)
def test_worker_lifecycle_events_are_fenced(failure: bool, expected: list[str]) -> None:
    class LifecycleRuns(_RunLedgerDouble):
        def emit(self, run_id: str, event: str, data: dict[str, Any]) -> None:
            if event in WORKER_EVENTS:
                raise AssertionError(f"worker event escaped fencing: {event}")
            self.ledger.emit(run_id, event, data)  # type: ignore[attr-defined]

    class Runtime(WorkflowRuntime):
        def _build_artifact_with_slot(
            self,
            run: dict[str, Any],
            node: dict[str, Any],
            actor: str,
            fenced_call: Any | None = None,
            lease_check: Any | None = None,
        ) -> dict[str, Any]:
            if failure:
                raise RuntimeError("node failed")
            return _artifact(run["id"], node["module_id"])

    ledgers = MemoryLedgerSet()
    run, _ = _queued_ledger_run(ledgers, dependencies=[])
    runtime = Runtime(
        LifecycleRuns(ledgers.runs),
        ledgers.sources,
        object(),
        Settings(storage_dir=Path("/tmp/caos-lifecycle"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    completed = ledgers.runs.get_run(run["id"])
    assert completed is not None
    assert [event["event"] for event in completed["events"]] == expected


@pytest.mark.parametrize("blocked", [False, True])
def test_expired_worker_cannot_emit_terminal_lifecycle_event(blocked: bool) -> None:
    class ExpiringRuns(_RunLedgerDouble):
        def update_run_fenced(
            self, run_id: str, attempt_token: str, **changes: Any
        ) -> None:
            if changes.get("status") == "failed":
                raise JobFencedError("lost workflow lease")
            self.ledger.update_run_fenced(run_id, attempt_token, **changes)  # type: ignore[attr-defined]

        def finalize_success(
            self,
            run_id: str,
            attempt_token: str,
            research: dict[str, Any] | None,
            event_data: dict[str, Any],
            *,
            deadline: float | None = None,
        ) -> None:
            raise JobFencedError("lost workflow lease")

    ledgers = MemoryLedgerSet()
    run, _ = _queued_ledger_run(ledgers, dependencies=["missing"] if blocked else None)
    runtime = WorkflowRuntime(
        ExpiringRuns(ledgers.runs),
        ledgers.sources,
        object(),
        Settings(storage_dir=Path("/tmp/caos-expired-worker"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    current = ledgers.runs.get_run(run["id"])
    assert current is not None
    events = [event["event"] for event in current["events"]]
    assert events == ["run.running"]


def test_memory_research_plan_pause_and_exact_approval_smoke() -> None:
    ledgers = MemoryLedgerSet()
    runtime = WorkflowRuntime(
        ledgers.runs,
        ledgers.sources,
        DeployVBundle(DEPLOY_V),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-plan-smoke"),
            deploy_v_root=DEPLOY_V,
        ),
    )
    case = ledgers.runs.create_case("Plan smoke", "Issuer", "Testing", "analyst")
    ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "source.txt",
            "media_type": "text/plain",
            "bytes": 6,
            "sha256": "d" * 64,
            "vault_path": None,
            "blocks": [],
        },
        "analyst",
    )
    brief = {
        "research_question": "Can the issuer refinance?",
        "decision_context": "Underwrite first-lien risk.",
        "as_of_date": "2026-08-23",
        "time_horizon": "Through 2029",
        "must_answer": [],
        "exclusions": [],
    }
    try:
        run = runtime.start_run(
            case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief
        )
        runtime._execute(run["id"], "analyst")
        paused = ledgers.runs.get_run(run["id"])
        assert paused is not None and paused["status"] == "paused"
        assert paused["research"]["phase"] == "awaiting_approval"
        approved = runtime.approve_research_plan(
            run["id"], "approver", paused["research"]["proposed_plan_hash"]
        )
        assert (
            approved["id"] == run["id"] and approved["research"]["phase"] == "approved"
        )
    finally:
        runtime.close()


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
        "workstream_findings": [
            {
                "workstream_id": "WS-1",
                "finding": "Liquidity supports the near-term maturity.",
                "claim_ids": ["C-1"],
                "status": "complete",
            }
        ],
        "material_claims": [
            {
                "claim_id": "C-1",
                "claim": "The issuer source characterises liquidity as supportive of the near-term maturity.",
                "claim_type": "source_characterisation",
                "workstream_id": "WS-1",
                "lineage": "Directly Sourced",
                "evidence_refs": [{"source_id": "src-1", "block_id": "b00001"}],
                "counter_evidence_refs": [],
                "coverage_status": "adequate",
                "confidence": 90,
                "material": True,
            }
        ],
        "evidence": [
            {
                "evidence_id": "E-1",
                "source_id": "src-1",
                "source_digest": "e" * 64,
                "block_id": "b00001",
                "locator": '{"line":1}',
                "extractor_version": "builtin-v1",
                "source_confidence": "HIGH",
                "quoted": False,
                "entity": "Issuer",
                "period": "2026-08-23",
                "unit_currency": "USD",
                "perimeter": "consolidated",
                "lineage": "Directly Sourced",
                "independence_family": "issuer filing",
                "numeric_value": 100.0,
            }
        ],
        "conflicts": [],
        "gaps": [],
        "qa_findings": [],
        "scope_adherence": [],
        "direct_answer": "The supplied liquidity evidence supports the near-term refinancing case, subject to the stated perimeter and reporting-date limits.",
        "causal_synthesis": "Available liquidity covers the identified maturity and reduces immediate refinancing pressure.",
        "implications_scenarios": [
            "Monitor liquidity and maturity coverage at the next reporting date."
        ],
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
    return {
        ("src-1", "b00001"): {
            "source_digest": "e" * 64,
            "origin_family": "e" * 64,
            "authority_class": "primary_authority",
            "locator": '{"line":1}',
            "extractor_version": "builtin-v1",
            "confidence": "HIGH",
        }
    }


def test_cpdr_transport_is_strict_and_host_validated() -> None:
    parsed = validate_cpdr_payload(
        _cpdr_payload(), _cpdr_host(), {"WS-1"}, _returned_evidence()
    )
    assert isinstance(parsed, CPDRPayload)

    for invalid in (
        _cpdr_payload(extra="forbidden"),
        _cpdr_payload(run_id="wrong"),
        _cpdr_payload(coverage_score=99),
        _cpdr_payload(coverage_score="100"),
        _cpdr_payload(
            material_claims=[
                {**_cpdr_payload()["material_claims"][0], "numeric_value": True}
            ]
        ),
        _cpdr_payload(
            material_claims=[
                {**_cpdr_payload()["material_claims"][0], "provider_only": "forbidden"}
            ]
        ),
        _cpdr_payload(direct_answer="x" * 8_001),
        _cpdr_payload(material_claims=[]),
        _cpdr_payload(workstream_findings=[]),
    ):
        with pytest.raises(CPDRValidationError):
            validate_cpdr_payload(invalid, _cpdr_host(), {"WS-1"}, _returned_evidence())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_cpdr_rejects_nonfinite_and_false_citations(value: float) -> None:
    with pytest.raises(CPDRValidationError):
        validate_cpdr_payload(
            _cpdr_payload(
                evidence=[{**_cpdr_payload()["evidence"][0], "numeric_value": value}]
            ),
            _cpdr_host(),
            {"WS-1"},
            _returned_evidence(),
        )
    with pytest.raises(CPDRValidationError, match="returned"):
        validate_cpdr_payload(_cpdr_payload(), _cpdr_host(), {"WS-1"}, {})


def test_cpdr_numeric_evidence_requires_context() -> None:
    row = {**_cpdr_payload()["evidence"][0], "unit_currency": None}
    with pytest.raises(CPDRValidationError, match="numeric context"):
        validate_cpdr_payload(
            _cpdr_payload(evidence=[row]), _cpdr_host(), {"WS-1"}, _returned_evidence()
        )


def test_cpdr_concatenated_numeric_claim_requires_context() -> None:
    claim = {
        **_cpdr_payload()["material_claims"][0],
        "claim": "Issuer liquidity was USD100m.",
        "numeric_value": None,
    }
    with pytest.raises(CPDRValidationError, match="numeric claim"):
        validate_cpdr_payload(
            _cpdr_payload(material_claims=[claim]),
            _cpdr_host(),
            {"WS-1"},
            _returned_evidence(),
        )


def test_cpdr_host_provenance_controls_adequacy_and_confidence() -> None:
    fact = {**_cpdr_payload()["material_claims"][0], "claim_type": "fact"}
    unclassified = {
        key: {**metadata, "authority_class": "unclassified"}
        for key, metadata in _returned_evidence().items()
    }
    with pytest.raises(CPDRValidationError, match="host coverage"):
        validate_cpdr_payload(
            _cpdr_payload(material_claims=[fact]), _cpdr_host(), {"WS-1"}, unclassified
        )

    second_row = {
        **_cpdr_payload()["evidence"][0],
        "evidence_id": "E-2",
        "source_id": "src-2",
        "source_digest": "f" * 64,
        "block_id": "b00002",
        "independence_family": "forged-second-family",
    }
    two_refs = [
        {"source_id": "src-1", "block_id": "b00001"},
        {"source_id": "src-2", "block_id": "b00002"},
    ]
    fact["evidence_refs"] = two_refs
    copied = {
        **unclassified,
        ("src-2", "b00002"): {
            **unclassified[("src-1", "b00001")],
            "source_digest": "f" * 64,
        },
    }
    with pytest.raises(CPDRValidationError, match="host coverage"):
        validate_cpdr_payload(
            _cpdr_payload(
                material_claims=[fact],
                evidence=[_cpdr_payload()["evidence"][0], second_row],
            ),
            _cpdr_host(),
            {"WS-1"},
            copied,
        )

    independent = {
        **copied,
        ("src-2", "b00002"): {**copied[("src-2", "b00002")], "origin_family": "f" * 64},
    }
    parsed = validate_cpdr_payload(
        _cpdr_payload(
            material_claims=[fact],
            evidence=[_cpdr_payload()["evidence"][0], second_row],
        ),
        _cpdr_host(),
        {"WS-1"},
        independent,
    )
    forged = parsed.model_copy(
        update={
            "material_claims": [
                parsed.material_claims[0].model_copy(
                    update={"lineage": "Analyst Inference"}
                )
            ],
            "qa_findings": [],
        }
    )
    inputs = confidence_inputs(forged, independent)
    assert inputs["lineage_counts"] == {"Weak Lineage": 1}
    assert inputs["source_gate"] == "pass" and inputs["findings"] == {}


def test_material_source_characterisation_cannot_forge_host_provenance_or_complete_coverage() -> (
    None
):
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
            _cpdr_host(),
            {"WS-1"},
            unclassified,
        )


def test_promoted_note_origin_digest_is_exact_canonical_content_bytes() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Origin", "Issuer", "Testing", "analyst")
    note = create_note(
        ledgers.publications, case["id"], "analyst", "canonical note bytes"
    )
    promoted = promote_note(ledgers.publications, case["id"], note["id"], "analyst")
    source = ledgers.sources.get_source(promoted["promoted_source_id"])
    assert source is not None
    assert source["sha256"] == hashlib.sha256(b"canonical note bytes").hexdigest()


def test_cpdr_host_confidence_penalizes_material_gaps_without_provider_qa() -> None:
    claim = {
        **_cpdr_payload()["material_claims"][0],
        "evidence_refs": [],
        "coverage_status": "gap",
    }
    payload = _cpdr_payload(
        material_claims=[claim],
        evidence=[],
        gaps=[
            {
                "workstream_id": "WS-1",
                "description": "Material evidence remains unavailable.",
                "material": True,
            }
        ],
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
    plan = {
        "workstreams": [{"id": "WS-1", "assigned_questions": ["sentinel-must-answer"]}]
    }
    brief = {
        "must_answer": ["sentinel-must-answer"],
        "exclusions": ["sentinel-exclusion"],
    }
    rows = [
        {
            "kind": "must_answer",
            "item": "sentinel-must-answer",
            "workstream_id": "WS-1",
            "respected": True,
        },
        {
            "kind": "exclusion",
            "item": "sentinel-exclusion",
            "workstream_id": None,
            "respected": True,
        },
    ]
    assert validate_cpdr_payload(
        _cpdr_payload(scope_adherence=rows),
        _cpdr_host(),
        {"WS-1"},
        _returned_evidence(),
        plan,
        brief,
    )
    invalid_rows = [
        rows[:1],
        rows + [rows[1]],
        [{**rows[0], "item": "changed"}, rows[1]],
        [rows[0], {**rows[1], "respected": False}],
    ]
    for invalid in invalid_rows:
        with pytest.raises(CPDRValidationError, match="scope adherence"):
            validate_cpdr_payload(
                _cpdr_payload(scope_adherence=invalid),
                _cpdr_host(),
                {"WS-1"},
                _returned_evidence(),
                plan,
                brief,
            )
    duplicate_brief = {
        **brief,
        "exclusions": ["sentinel-exclusion", "sentinel-exclusion"],
    }
    with pytest.raises(CPDRValidationError, match="scope items must be unique"):
        validate_cpdr_payload(
            _cpdr_payload(scope_adherence=rows),
            _cpdr_host(),
            {"WS-1"},
            _returned_evidence(),
            plan,
            duplicate_brief,
        )


def test_cpdr_conflict_citations_are_exhaustive_unique_and_registered() -> None:
    ghost = {
        "conflict_id": "K-1",
        "claim_ids": ["C-1"],
        "evidence_refs": [
            {"source_id": "ghost", "block_id": "missing"},
            {"source_id": "ghost", "block_id": "missing"},
        ],
        "description": "Conflict",
        "status": "unresolved",
    }
    with pytest.raises(CPDRValidationError):
        validate_cpdr_payload(
            _cpdr_payload(conflicts=[ghost]),
            _cpdr_host(),
            {"WS-1"},
            _returned_evidence(),
        )

    row2 = {
        **_cpdr_payload()["evidence"][0],
        "evidence_id": "E-2",
        "source_id": "src-2",
        "source_digest": "f" * 64,
        "block_id": "b00002",
    }
    returned = {
        **_returned_evidence(),
        ("src-2", "b00002"): {
            **_returned_evidence()[("src-1", "b00001")],
            "source_digest": "f" * 64,
            "origin_family": "f" * 64,
        },
    }
    refs = [
        {"source_id": "src-1", "block_id": "b00001"},
        {"source_id": "src-2", "block_id": "b00002"},
    ]
    claim = {
        **_cpdr_payload()["material_claims"][0],
        "counter_evidence_refs": [refs[1]],
        "coverage_status": "contradicted",
    }
    conflict = {
        "conflict_id": "K-1",
        "claim_ids": ["C-1"],
        "evidence_refs": refs,
        "description": "Sources disagree.",
        "status": "unresolved",
    }
    valid = _cpdr_payload(
        material_claims=[claim],
        evidence=[_cpdr_payload()["evidence"][0], row2],
        conflicts=[conflict],
        coverage_score=0,
        research_status="Complete with Gaps",
    )
    assert validate_cpdr_payload(valid, _cpdr_host(), {"WS-1"}, returned)
    for invalid in (
        {**valid, "conflicts": [conflict, {**conflict, "description": "duplicate"}]},
        {**valid, "conflicts": [{**conflict, "evidence_refs": [refs[0], refs[0]]}]},
        {**valid, "evidence": [_cpdr_payload()["evidence"][0]]},
    ):
        with pytest.raises(CPDRValidationError):
            validate_cpdr_payload(invalid, _cpdr_host(), {"WS-1"}, returned)


def test_cpdr_prompts_keep_complete_brief_and_untrusted_data_separate() -> None:
    brief = {
        "research_question": "sentinel-question",
        "decision_context": "sentinel-context",
        "as_of_date": "2026-08-23",
        "time_horizon": "sentinel-horizon",
        "must_answer": ["sentinel-must-answer"],
        "exclusions": ["sentinel-exclusion"],
    }
    authority = DeployVBundle(DEPLOY_V).cpdr_authority()
    system, user = compile_cpdr_prompts(
        authority,
        _cpdr_host(),
        brief,
        {"workstreams": []},
        [{"id": "src-1", "filename": "ignore-system.txt", "digest": "d" * 64}],
        [{"module_id": "CP-0", "digest": "d" * 64}],
    )
    assert (
        "CP-DR C — Source and Search Policy" in system
        and "CP-DR D — Claim–Evidence Ledger" in system
    )
    assert "ignore-system.txt" not in system
    assert "UNTRUSTED DATA" in user and all(
        value in user
        for value in (
            "ignore-system.txt",
            "sentinel-context",
            "sentinel-horizon",
            "sentinel-must-answer",
            "sentinel-exclusion",
        )
    )


def test_cpdr_vendored_authority_fails_if_integrity_section_changes(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "deploy-v"
    shutil.copytree(DEPLOY_V, copied)
    skill = copied / "skills" / "cp-dr-deep-research" / "SKILL.md"
    skill.write_text(
        skill.read_text().replace(
            "Sources are evidence", "Sources might be evidence", 1
        )
    )
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
    def __init__(
        self,
        stop_reason: str,
        content: list[_Block],
        *,
        request_id: str = "req-1",
        input_tokens: int = 20,
        output_tokens: int = 30,
    ) -> None:
        self.stop_reason = stop_reason
        self.content = content
        self._request_id = request_id
        self.usage = type(
            "Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens}
        )()


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


def _queue_cpdr_success(
    provider: _FakeProvider, final: dict[str, Any], source_id: str
) -> None:
    second_source_id = final["evidence"][1]["source_id"]
    responses = [
        ProviderMessage(
            content=[
                ProviderBlock(
                    type="tool_use",
                    id="tool-1",
                    name="read_evidence",
                    input={"source_id": source_id, "block_ids": ["b00001"]},
                )
            ],
            stop_reason="tool_use",
            usage=ProviderUsage(20, 30),
        ),
        ProviderMessage(
            content=[
                ProviderBlock(
                    type="tool_use",
                    id="tool-2",
                    name="read_evidence",
                    input={"source_id": second_source_id, "block_ids": ["b00002"]},
                )
            ],
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
    ledgers = MemoryLedgerSet()
    runtime = WorkflowRuntime(
        ledgers.runs,
        ledgers.sources,
        DeployVBundle(DEPLOY_V),
        Settings(
            storage_dir=Path("/tmp/caos-injected-provider"), deploy_v_root=DEPLOY_V
        ),
        provider=provider,
    )
    try:
        assert runtime._agent_loop.provider is provider
    finally:
        runtime.close()


def test_agent_loop_provider_injection_handles_tools_and_reconciles_normalized_usage() -> (
    None
):
    provider = _FakeProvider(
        [
            ProviderMessage(
                content=[
                    ProviderBlock(
                        type="tool_use",
                        id="tool-1",
                        name="read_evidence",
                        input={"source_id": "src-1", "block_ids": ["b00001"]},
                    )
                ],
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
        ]
    )
    reconciliations: list[tuple[Any, ...]] = []

    result = AgentLoop(provider).run(
        system="authority",
        user="brief",
        read_evidence=lambda source_id, block_ids: [
            {"source_id": source_id, "block_id": block_ids[0], "text": "evidence"}
        ],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *args: reconciliations.append(args),
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert [kind for kind, _request in provider.calls] == [
        "count_tokens",
        "create",
        "count_tokens",
        "create",
    ]
    second_count = provider.calls[2][1]
    assert second_count.messages[-2]["content"] == [
        ProviderBlock(
            type="tool_use",
            id="tool-1",
            name="read_evidence",
            input={"source_id": "src-1", "block_ids": ["b00001"]},
        ),
    ]
    assert second_count.messages[-1]["content"][0]["tool_use_id"] == "tool-1"
    assert [items[-2:] for items in reconciliations] == [(20, 4), (24, 30)]


def test_agent_loop_provider_injection_retries_one_normalized_timeout() -> None:
    provider = _FakeProvider(
        [
            AgentError("AGENT_PROVIDER_TIMEOUT"),
            ProviderMessage(
                content=[ProviderBlock(type="text", text=json.dumps(_cpdr_payload()))],
                stop_reason="end_turn",
                usage=ProviderUsage(input_tokens=20, output_tokens=30),
            ),
        ],
        counts=[20],
    )
    reservations: list[tuple[Any, ...]] = []

    result = AgentLoop(provider).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *args: reservations.append(args),
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert provider.calls[1][1] == provider.calls[2][1]
    assert [reservation[-1] for reservation in reservations] == [False, True]


def test_agent_loop_provider_injection_rejects_malformed_normalized_usage() -> None:
    provider = _FakeProvider(
        [
            ProviderMessage(
                content=[ProviderBlock(type="text", text=json.dumps(_cpdr_payload()))],
                stop_reason="end_turn",
                usage=ProviderUsage(input_tokens=20, output_tokens=1.5),  # type: ignore[arg-type]
            ),
        ]
    )
    reconciliations: list[tuple[Any, ...]] = []

    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AgentLoop(provider).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *args: reconciliations.append(args),
            record=lambda *_args, **_kwargs: None,
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert reconciliations == []


def test_gateway_preserves_assistant_content_and_orders_tool_results() -> None:
    tool_response = _Response(
        "tool_use",
        [
            _Block("text", text="checking"),
            _Block(
                "tool_use",
                id="tool-1",
                name="read_evidence",
                input={"source_id": "src-1", "block_ids": ["b00001"]},
            ),
        ],
    )
    final_response = _Response(
        "end_turn",
        [_Block("text", text=json.dumps(_cpdr_payload()))],
        request_id="req-2",
    )
    client = _Client([tool_response, final_response])
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=client)
    reservations: list[tuple[str, int, int, bool]] = []

    result = gateway.run(
        system="authority",
        user="brief",
        read_evidence=lambda source_id, block_ids: [
            {"source_id": source_id, "block_id": block_ids[0], "text": "evidence"}
        ],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda digest, inputs, outputs, retry: reservations.append(
            (digest, inputs, outputs, retry)
        ),
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    first = client.messages.create_calls[0]
    assert first["system"] == [
        {"type": "text", "text": "authority", "cache_control": {"type": "ephemeral"}}
    ]
    assert first["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert (
        first["tools"][0]["name"] == "read_evidence"
        and first["tools"][0]["strict"] is True
    )
    assert "output_config" in first and "output_format" not in first
    second_messages = client.messages.create_calls[1]["messages"]
    assert second_messages[-2]["content"] == [
        vars(block) for block in tool_response.content
    ]
    assert second_messages[-1]["content"][0]["type"] == "tool_result"
    assert len(reservations) == 2


@pytest.mark.parametrize(
    "stop_reason",
    ["refusal", "max_tokens", "model_context_window_exceeded", "pause_turn", "unknown"],
)
def test_gateway_rejects_non_final_stop_reasons(stop_reason: str) -> None:
    gateway = AnthropicGateway(
        "key",
        "claude-sonnet-4-6",
        client=_Client([_Response(stop_reason, [_Block("text", text="no")])]),
    )
    events: list[tuple[str, dict[str, Any]]] = []
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        gateway.run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)),
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert any(
        details.get("terminal_code") == "AGENT_OUTPUT_INVALID"
        for _kind, details in events
    )


def _gateway_call(
    client: _Client,
    *,
    semaphore: threading.BoundedSemaphore | None = None,
    events: list[tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *_: None,
        record=lambda kind, **details: (
            events.append((kind, details)) if events is not None else None
        ),
        active_time=lambda _elapsed: None,
        semaphore=semaphore or threading.BoundedSemaphore(2),
    )


def test_gateway_missing_key_is_explicitly_unavailable() -> None:
    with pytest.raises(AgentError, match="AGENT_PROVIDER_UNAVAILABLE"):
        AnthropicGateway("", "claude-sonnet-4-6")


def test_gateway_real_sdk_constructor_disables_hidden_retries_and_sets_timeout() -> (
    None
):
    gateway = AnthropicGateway(
        "constructor-probe-only", "claude-sonnet-4-6", timeout=37.5
    )
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
        "verified authority",
        _cpdr_host(),
        brief,
        {"workstreams": [{"id": "WS-1", "assigned_questions": brief["must_answer"]}]},
        [],
        [],
    )

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        requests.append((request.url.path, body))
        if request.url.path.endswith("/count_tokens"):
            return httpx2.Response(200, json={"input_tokens": 20})
        return httpx2.Response(
            200,
            json={
                "id": "msg_local",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{"type": "text", "text": json.dumps(_cpdr_payload())}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 20, "output_tokens": 30},
            },
        )

    sdk = anthropic.Anthropic(
        api_key="constructor-probe-only",
        max_retries=0,
        timeout=37.5,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    result = AnthropicGateway(
        "constructor-probe-only", "claude-sonnet-4-6", client=sdk
    ).run(
        system=system_prompt,
        user=user_prompt,
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert [path for path, _body in requests] == [
        "/v1/messages/count_tokens",
        "/v1/messages",
    ]
    create = requests[1][1]
    assert create["model"] == "claude-sonnet-4-6" and create["max_tokens"] == 2_000
    serialized_create = json.dumps(create, sort_keys=True)
    assert create["system"] == [
        {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
    ] and create["messages"] == [{"role": "user", "content": user_prompt}]
    for sentinel in (
        "sdk-question-sentinel",
        "sdk-decision-sentinel",
        "sdk-horizon-sentinel",
        "sdk-must-answer-sentinel",
        "sdk-exclusion-sentinel",
    ):
        assert sentinel in serialized_create
    assert (
        create["tools"][0]["name"] == "read_evidence"
        and create["output_config"]["format"]["type"] == "json_schema"
    )


def test_gateway_retries_one_identical_timeout_request() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client(
        [
            anthropic.APITimeoutError(request),
            _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
        ]
    )
    reservations: list[tuple[Any, ...]] = []
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=client)

    result = gateway.run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *args: reservations.append(args),
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert {
        key: value
        for key, value in client.messages.create_calls[0].items()
        if key != "timeout"
    } == {
        key: value
        for key, value in client.messages.create_calls[1].items()
        if key != "timeout"
    }
    assert [reservation[-1] for reservation in reservations] == [False, True]


def test_gateway_preserves_legacy_request_digest_bytes_across_retry() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client(
        [
            anthropic.APITimeoutError(request),
            _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
        ]
    )
    reservations: list[tuple[Any, ...]] = []

    AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *args: reservations.append(args),
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )

    legacy_preimage = {
        "model": "claude-sonnet-4-6",
        "system": [
            {"type": "text", "text": "authority", "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [{"role": "user", "content": "brief"}],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(CPDRPayload.model_json_schema()),
            }
        },
        "tools": [provider_module.READ_EVIDENCE_TOOL, provider_module.SEND_TO_USER_TOOL],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "max_tokens": 2_000,
    }
    expected_bytes = json.dumps(
        legacy_preimage, sort_keys=True, default=lambda value: vars(value)
    ).encode("utf-8")
    actual_bytes = json.dumps(
        {
            key: value
            for key, value in client.messages.create_calls[0].items()
            if key != "timeout"
        },
        sort_keys=True,
        default=lambda value: vars(value),
    ).encode("utf-8")
    assert actual_bytes == expected_bytes
    assert [reservation[0] for reservation in reservations] == [
        hashlib.sha256(expected_bytes).hexdigest()
    ] * 2


def test_gateway_preserves_legacy_sdk_block_fields_in_continuation_digest() -> None:
    tool_blocks = [
        TextBlock(citations=None, text="checking", type="text"),
        ToolUseBlock(
            id="tool-1",
            caller=None,
            input={"source_id": "src-1", "block_ids": ["b00001"]},
            name="read_evidence",
            type="tool_use",
            toolset_name=None,
        ),
    ]
    evidence = [{"source_id": "src-1", "block_id": "b00001", "text": "evidence"}]
    client = _Client(
        [
            _Response("tool_use", tool_blocks),  # type: ignore[arg-type]
            _Response(
                "end_turn",
                [
                    TextBlock(
                        citations=None, text=json.dumps(_cpdr_payload()), type="text"
                    )
                ],  # type: ignore[list-item]
            ),
        ]
    )
    reservations: list[tuple[Any, ...]] = []
    remaining = iter([5.0, 4.0, 3.0, 2.0, 1.0])

    AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: evidence,
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *args: reservations.append(args),
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        remaining_time=lambda: next(remaining),
        semaphore=threading.BoundedSemaphore(2),
    )

    legacy_preimage = {
        "model": "claude-sonnet-4-6",
        "system": [
            {"type": "text", "text": "authority", "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [
            {"role": "user", "content": "brief"},
            {"role": "assistant", "content": tool_blocks},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-1",
                        "content": json.dumps(evidence, sort_keys=True),
                    }
                ],
            },
        ],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(CPDRPayload.model_json_schema()),
            }
        },
        "tools": [provider_module.READ_EVIDENCE_TOOL, provider_module.SEND_TO_USER_TOOL],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "max_tokens": 2_000,
    }
    expected_bytes = json.dumps(
        legacy_preimage, sort_keys=True, default=lambda value: vars(value)
    ).encode("utf-8")
    assert all(
        field in expected_bytes
        for field in (b'"citations": null', b'"caller": null', b'"toolset_name": null')
    )
    assert (
        b'"timeout"' not in expected_bytes
        and client.messages.create_calls[1]["timeout"] == 1.0
    )
    assert reservations[1][0] == hashlib.sha256(expected_bytes).hexdigest()


def test_gateway_schema_transform_failure_is_not_a_provider_interaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)),
            active_time=charged.append,
            semaphore=threading.BoundedSemaphore(2),
        )

    assert client.messages.count_calls == []
    assert events == []
    assert charged == []


def _production_injected_runtime(
    monkeypatch: pytest.MonkeyPatch, client: _Client
) -> WorkflowRuntime:
    monkeypatch.setattr(
        provider_module.anthropic, "Anthropic", lambda **_kwargs: client
    )
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


def test_production_injection_preserves_legacy_request_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _Client(
        [_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])]
    )
    runtime = _production_injected_runtime(monkeypatch, client)
    reservations: list[tuple[Any, ...]] = []
    try:
        runtime._agent_loop.run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *args: reservations.append(args),
            reconcile=lambda *_: None,
            record=lambda *_args, **_kwargs: None,
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    finally:
        runtime.close()

    legacy_preimage = {
        "model": "claude-sonnet-4-6",
        "system": [
            {"type": "text", "text": "authority", "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [{"role": "user", "content": "brief"}],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": anthropic.transform_schema(CPDRPayload.model_json_schema()),
            }
        },
        "tools": [provider_module.READ_EVIDENCE_TOOL, provider_module.SEND_TO_USER_TOOL],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "max_tokens": 2_000,
    }
    expected = hashlib.sha256(
        json.dumps(
            legacy_preimage, sort_keys=True, default=lambda value: vars(value)
        ).encode("utf-8")
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
                system="authority",
                user="brief",
                read_evidence=lambda *_: [],
                validate=lambda value: value,
                lease_check=lambda: None,
                reserve=lambda *_: None,
                reconcile=lambda *_: None,
                record=lambda kind, **details: events.append((kind, details)),
                active_time=charged.append,
                semaphore=threading.BoundedSemaphore(2),
            )
    finally:
        runtime.close()

    assert client.messages.count_calls == []
    assert events == []
    assert charged == []


def test_gateway_caps_each_sdk_call_to_decreasing_remaining_active_time() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client(
        [
            anthropic.APITimeoutError(request),
            _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
        ]
    )
    remaining = iter([9.0, 8.0, 7.0])

    result = AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=lambda _elapsed: None,
        remaining_time=lambda: next(remaining),
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert client.messages.count_calls[0]["timeout"] == 9.0
    assert [call["timeout"] for call in client.messages.create_calls] == [8.0, 7.0]
    assert {
        key: value
        for key, value in client.messages.create_calls[0].items()
        if key != "timeout"
    } == {
        key: value
        for key, value in client.messages.create_calls[1].items()
        if key != "timeout"
    }


def test_gateway_charges_failed_evidence_and_validation_time() -> None:
    tool_response = _Response(
        "tool_use",
        [
            _Block(
                "tool_use",
                id="tool-1",
                name="read_evidence",
                input={"source_id": "src-1", "block_ids": ["b00001"]},
            )
        ],
    )
    charged: list[float] = []
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AnthropicGateway(
            "key", "claude-sonnet-4-6", client=_Client([tool_response])
        ).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: (_ for _ in ()).throw(
                AgentError("AGENT_OUTPUT_INVALID")
            ),
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=lambda *_args, **_kwargs: None,
            active_time=charged.append,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert len(charged) >= 2 and charged[-1] >= 0

    charged.clear()
    final_response = _Response(
        "end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]
    )
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        AnthropicGateway(
            "key", "claude-sonnet-4-6", client=_Client([final_response])
        ).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda _value: (_ for _ in ()).throw(
                AgentError("AGENT_OUTPUT_INVALID")
            ),
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=lambda *_args, **_kwargs: None,
            active_time=charged.append,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert len(charged) >= 2 and charged[-1] >= 0


def test_gateway_rejects_duplicate_json_keys_and_records_terminal_interaction() -> None:
    duplicate = '{"module_id":"CP-DR","module_id":"forged"}'
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client(
        [
            _Response("end_turn", [_Block("text", text=duplicate)]),
            _Response("end_turn", [_Block("text", text=duplicate)]),
        ]
    )

    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        _gateway_call(client, events=events)

    assert any(
        details.get("terminal_code") == "AGENT_OUTPUT_INVALID"
        for _kind, details in events
    )


def test_gateway_records_terminal_when_create_reservation_fails_after_count() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client(
        [_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])]
    )
    with pytest.raises(AgentError, match="AGENT_BUDGET_EXCEEDED"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: (_ for _ in ()).throw(
                AgentError("AGENT_BUDGET_EXCEEDED")
            ),
            reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)),
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert client.messages.create_calls == []
    assert any(
        details.get("terminal_code") == "AGENT_BUDGET_EXCEEDED"
        for _kind, details in events
    )


def test_gateway_auth_permission_and_policy_rejections_do_not_retry() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    failures = [
        anthropic.AuthenticationError(
            "secret body",
            response=httpx2.Response(401, request=request),
            body={"secret": "body"},
        ),
        anthropic.PermissionDeniedError(
            "secret body",
            response=httpx2.Response(403, request=request),
            body={"secret": "body"},
        ),
        anthropic.APIStatusError(
            "secret body",
            response=httpx2.Response(422, request=request),
            body={"secret": "body"},
        ),
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
    failure = anthropic.APIStatusError(
        "redirect", response=httpx2.Response(302, request=request), body=None
    )
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
            return anthropic.RateLimitError(
                "rate", response=httpx2.Response(429, request=request), body=None
            )
        return anthropic.APIStatusError(
            "server", response=httpx2.Response(503, request=request), body=None
        )

    client = _Client([failure(), failure()])
    with pytest.raises(AgentError, match="AGENT_PROVIDER_TIMEOUT"):
        _gateway_call(client)
    assert len(client.messages.create_calls) == 2


def test_gateway_concurrency_denial_does_not_reserve_tokens() -> None:
    semaphore = threading.BoundedSemaphore(1)
    semaphore.acquire()
    reservations: list[tuple[Any, ...]] = []
    gateway = AnthropicGateway(
        "key",
        "claude-sonnet-4-6",
        client=_Client([_Response("end_turn", [_Block("text", text="{}")])]),
    )
    try:
        with pytest.raises(AgentError, match="AGENT_BUDGET_EXCEEDED"):
            gateway.run(
                system="authority",
                user="brief",
                read_evidence=lambda *_: [],
                validate=lambda value: value,
                lease_check=lambda: None,
                reserve=lambda *args: reservations.append(args),
                reconcile=lambda *_: None,
                record=lambda *_args, **_kwargs: None,
                active_time=lambda _elapsed: None,
                semaphore=semaphore,
            )
    finally:
        semaphore.release()
    assert reservations == []


@pytest.mark.parametrize(
    "invalid_at",
    [
        "negative_count",
        "fractional_count",
        "negative_input_usage",
        "fractional_output_usage",
    ],
)
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
        client.messages.count_tokens = lambda **_kwargs: type(
            "Count", (), {"input_tokens": invalid}
        )()

    events: list[tuple[str, dict[str, Any]]] = []
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        _gateway_call(client, events=events)
    assert any(
        details.get("terminal_code") == "AGENT_OUTPUT_INVALID"
        for _kind, details in events
    )


def test_gateway_uses_one_repair_without_evidence_tools() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client(
        [
            _Response("end_turn", [_Block("text", text="{}")]),
            _Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]),
        ]
    )
    result = AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: (
            value
            if value.get("module_id") == "CP-DR"
            else (_ for _ in ()).throw(ValueError("module_id required"))
        ),
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *_: None,
        record=lambda kind, **details: events.append((kind, details)),
        active_time=lambda _elapsed: None,
        semaphore=threading.BoundedSemaphore(2),
    )
    assert result["module_id"] == "CP-DR"
    assert "repair_reserve" in [kind for kind, _ in events]
    assert "tools" not in client.messages.create_calls[-1]


def test_cpdr_fake_provider_end_to_end_produces_one_canonical_fenced_artifact() -> None:
    ledgers = MemoryLedgerSet()
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
        ledgers.runs,
        ledgers.sources,
        DeployVBundle(DEPLOY_V),
        settings,
        provider=provider,
    )
    case = ledgers.runs.create_case("CP-DR", "Issuer", "Testing", "analyst")
    source = ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "issuer.txt",
            "media_type": "text/plain",
            "bytes": 48,
            "sha256": "e" * 64,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00001",
                    "locator": {"line": 1},
                    "text": "Issuer liquidity was USD 100m at 2026-08-23.",
                    "extractor_version": "builtin-v1",
                    "confidence": "HIGH",
                }
            ],
        },
        "analyst",
    )
    source_id = source["id"]
    second_source = ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "facility.txt",
            "media_type": "text/plain",
            "bytes": 43,
            "sha256": "f" * 64,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00002",
                    "locator": {"line": 2},
                    "text": "Facility availability extends through 2029.",
                    "extractor_version": "builtin-v1",
                    "confidence": "HIGH",
                }
            ],
        },
        "analyst",
    )
    second_source_id = second_source["id"]
    source_set_id = second_source["source_set"]["id"]
    brief = {
        "research_question": "Can the issuer refinance?",
        "decision_context": "Underwrite first-lien risk.",
        "as_of_date": "2026-08-23",
        "time_horizon": "Through 2029",
        "must_answer": [],
        "exclusions": [],
    }
    try:
        run = runtime.start_run(
            case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief
        )
        runtime._execute(run["id"], "analyst")
        paused = ledgers.runs.get_run(run["id"])
        assert paused is not None and paused["status"] == "paused"
        runtime.approve_research_plan(
            run["id"], "approver", paused["research"]["proposed_plan_hash"]
        )
        approved = ledgers.runs.get_run(run["id"])
        assert approved is not None
        cp0_node = next(
            node for node in approved["nodes"] if node["module_id"] == "CP-0"
        )
        cp0 = ledgers.runs.get_artifact(cp0_node["artifact_id"])
        assert cp0 is not None
        workstreams = approved["research"]["proposed_plan"]["workstreams"]
        final = _cpdr_payload(
            run_id=run["id"],
            case_id=case["id"],
            source_set_id=source_set_id,
            source_set_version=second_source["source_set"]["version"],
            approved_plan_hash=approved["research"]["approved_plan_hash"],
            upstream_digests=[cp0["digest"]],
            scope_key=case["id"].replace("_", "-"),
            workstream_findings=[
                {
                    "workstream_id": item["id"],
                    "finding": "The supplied evidence resolves this approved lane."
                    if index == 0
                    else "No additional material claim was required for this lane.",
                    "claim_ids": ["C-1"] if index == 0 else [],
                    "status": "complete",
                }
                for index, item in enumerate(workstreams)
            ],
            material_claims=[
                {
                    **_cpdr_payload()["material_claims"][0],
                    "workstream_id": workstreams[0]["id"],
                    "evidence_refs": [
                        {"source_id": source_id, "block_id": "b00001"},
                        {"source_id": second_source_id, "block_id": "b00002"},
                    ],
                }
            ],
            evidence=[
                {
                    **_cpdr_payload()["evidence"][0],
                    "source_id": source_id,
                    "block_id": "b00001",
                },
                {
                    **_cpdr_payload()["evidence"][0],
                    "evidence_id": "E-2",
                    "source_id": second_source_id,
                    "source_digest": "f" * 64,
                    "block_id": "b00002",
                    "locator": '{"line":2}',
                },
            ],
        )
        provider.responses.extend(
            [
                AgentError("AGENT_PROVIDER_TIMEOUT"),
                ProviderMessage(
                    content=[
                        ProviderBlock(
                            type="tool_use",
                            id="tool-1",
                            name="read_evidence",
                            input={"source_id": source_id, "block_ids": ["b00001"]},
                        )
                    ],
                    stop_reason="tool_use",
                    usage=ProviderUsage(20, 30),
                ),
                ProviderMessage(
                    content=[
                        ProviderBlock(
                            type="tool_use",
                            id="tool-2",
                            name="read_evidence",
                            input={
                                "source_id": second_source_id,
                                "block_ids": ["b00002"],
                            },
                        )
                    ],
                    stop_reason="tool_use",
                    usage=ProviderUsage(20, 30),
                ),
                ProviderMessage(
                    content=[ProviderBlock(type="text", text="{}")],
                    stop_reason="end_turn",
                    usage=ProviderUsage(20, 30),
                    request_id="req-invalid",
                ),
                ProviderMessage(
                    content=[ProviderBlock(type="text", text=json.dumps(final))],
                    stop_reason="end_turn",
                    usage=ProviderUsage(20, 30),
                    request_id="req-final",
                ),
            ]
        )
        provider.counts.extend([20] * 5)

        runtime._execute(run["id"], "approver")

        completed = ledgers.runs.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded", (
            completed and completed.get("error")
        )
        cpdr_node = next(
            node for node in completed["nodes"] if node["module_id"] == "CP-DR"
        )
        artifact = ledgers.runs.get_artifact(cpdr_node["artifact_id"])
        # The CP-DR filename is dated by the run's creation date
        # (workflows/domain.py passes run["created_at"][:10]), so derive the
        # expectation instead of hardcoding a day that rots overnight.
        expected_date = completed["created_at"][:10].replace("-", "")
        assert artifact is not None and artifact["filename"].endswith(
            f"_CP-DR_{expected_date}.md"
        )
        assert set(artifact["payload"]) == {
            "schema_version",
            "module_id",
            "transport",
            "host_confidence",
            "canonical_output",
            "methodology",
            "source_set",
            "upstream_artifacts",
        }
        assert artifact["payload"]["transport"]["module_id"] == "CP-DR"
        assert (
            artifact["payload"]["canonical_output"]["filename"] == artifact["filename"]
        )
        rerendered_filename, rerendered_markdown = workflow_domain.render_cpdr_markdown(
            CPDRPayload.model_validate(artifact["payload"]["transport"]),
            artifact["payload"]["host_confidence"],
            completed["created_at"][:10],
            artifact["payload"]["upstream_artifacts"],
        )
        assert (rerendered_filename, rerendered_markdown) == (
            artifact["filename"],
            artifact["markdown"],
        )
        assert [
            line[3:]
            for line in artifact["markdown"].splitlines()
            if line.startswith("## ")
        ] == [
            "Audit Summary",
            "Analysis",
            "Evidence Trace",
            "Source Registry",
            "Gaps & Conflicts",
            "QA Validation",
        ]
        assert (
            artifact["markdown"]
            .split("## Analysis", 1)[1]
            .lstrip()
            .startswith("### Executive answer")
        )
        assert (
            len([node for node in completed["nodes"] if node["module_id"] == "CP-DR"])
            == 1
        )
        assert (
            len(
                [
                    event
                    for event in ledgers.runs.events_after(run["id"])
                    if event["event"] == "node.succeeded"
                    and event["data"].get("module_id") == "CP-DR"
                ]
            )
            == 1
        )
        assert completed["research"]["budget_used"]["provider_retries"] == 1
        assert completed["research"]["budget_used"]["repairs"] == 1
        assert completed["research"]["budget_used"]["turns"] == 5
        original_artifact = copy.deepcopy(artifact)
        mutations = [
            lambda item: item["payload"]["host_confidence"].update(confidence_score=99),
            lambda item: item["payload"]["canonical_output"].update(
                filename="forged.md"
            ),
            lambda item: item.update(markdown=item["markdown"] + "\nforged"),
            lambda item: item["payload"]["methodology"].update(
                approved_plan_hash="sha256:forged"
            ),
            lambda item: item["payload"]["source_set"].update(version=999),
            lambda item: item["payload"].update(upstream_artifacts=[]),
        ]
        for mutate in mutations:
            forged_artifact = copy.deepcopy(original_artifact)
            mutate(forged_artifact)

            class ForgedRuns(_RunLedgerDouble):
                def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
                    if artifact_id == forged_artifact["id"]:
                        return copy.deepcopy(forged_artifact)
                    return self.ledger.get_artifact(artifact_id)

            with pytest.raises(ValueError, match="RUN_NOT_READY"):
                build_snapshot_payload(
                    ForgedRuns(ledgers.runs),
                    ledgers.sources,
                    ledgers.runs.get_run(run["id"]) or {},
                    runtime.bundle,
                )
        snapshot = runtime.accept_run(case["id"], run["id"], "analyst")
        assert any(item["module_id"] == "CP-DR" for item in snapshot["artifacts"])
        persisted = json.dumps(
            {
                "run": completed,
                "events": ledgers.runs.events_after(run["id"]),
                "audit": ledgers.publications.list_audit(),
            }
        )
        for secret in (
            "test-only-key",
            "Issuer liquidity was USD 100m",
            "CAOS CP-DR RESEARCH AUTHORITY",
            "VALIDATION ERRORS",
        ):
            assert secret not in persisted
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (
            Settings(
                environment="production",
                storage_dir=Path("/tmp/caos-cpdr-disabled"),
                deploy_v_root=DEPLOY_V,
            ),
            "AGENT_PROVIDER_UNAVAILABLE",
        ),
        (
            Settings(
                environment="production",
                storage_dir=Path("/tmp/caos-cpdr-no-key"),
                deploy_v_root=DEPLOY_V,
                cpdr_agent_enabled=True,
                cpdr_pilot_subjects=("analyst",),
            ),
            "AGENT_PROVIDER_UNAVAILABLE",
        ),
    ],
)
def test_approved_cpdr_disabled_or_missing_key_fails_explicitly(
    settings: Settings, expected: str
) -> None:
    ledgers = MemoryLedgerSet()
    runtime = WorkflowRuntime(
        ledgers.runs, ledgers.sources, DeployVBundle(DEPLOY_V), settings
    )
    case = ledgers.runs.create_case("CP-DR", "Issuer", "Testing", "analyst")
    ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "source.txt",
            "media_type": "text/plain",
            "bytes": 1,
            "sha256": "a" * 64,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00001",
                    "locator": {"line": 1},
                    "text": "x",
                    "extractor_version": "builtin-v1",
                    "confidence": "HIGH",
                }
            ],
        },
        "analyst",
    )
    brief = {
        "research_question": "Question",
        "decision_context": "Context",
        "as_of_date": "2026-08-23",
        "time_horizon": "2029",
        "must_answer": [],
        "exclusions": [],
    }
    try:
        run = runtime.start_run(
            case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief
        )
        runtime._execute(run["id"], "analyst")
        paused = ledgers.runs.get_run(run["id"])
        assert paused is not None
        runtime.approve_research_plan(
            run["id"], "analyst", paused["research"]["proposed_plan_hash"]
        )
        runtime._execute(run["id"], "analyst")
        failed = ledgers.runs.get_run(run["id"])
        assert failed is not None and failed["error"]["code"] == expected
        cpdr_node = next(
            node for node in failed["nodes"] if node["module_id"] == "CP-DR"
        )
        assert cpdr_node["artifact_id"] is None
    finally:
        runtime.close()


def _approved_cpdr_case(
    ledgers: MemoryLedgerSet | None = None,
    provider: _FakeProvider | None = None,
) -> tuple[MemoryLedgerSet, WorkflowRuntime, dict[str, Any], str]:
    ledgers = ledgers or MemoryLedgerSet()
    settings = Settings(
        environment="production",
        storage_dir=Path("/tmp/caos-cpdr-matrix"),
        deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key",
        cpdr_agent_enabled=True,
        cpdr_pilot_subjects=("analyst",),
    )
    runtime = WorkflowRuntime(
        ledgers.runs,
        ledgers.sources,
        DeployVBundle(DEPLOY_V),
        settings,
        provider=provider,
    )
    case = ledgers.runs.create_case("CP-DR matrix", "Issuer", "Testing", "analyst")
    source = ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "issuer.txt",
            "media_type": "text/plain",
            "bytes": 48,
            "sha256": "e" * 64,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00001",
                    "locator": {"line": 1},
                    "text": "Issuer liquidity was USD 100m at 2026-08-23.",
                    "extractor_version": "builtin-v1",
                    "confidence": "HIGH",
                }
            ],
        },
        "analyst",
    )
    source_id = source["id"]
    second_source = ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "facility.txt",
            "media_type": "text/plain",
            "bytes": 44,
            "sha256": "f" * 64,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00002",
                    "locator": {"line": 2},
                    "text": "The facility remains available through 2029.",
                    "extractor_version": "builtin-v1",
                    "confidence": "HIGH",
                }
            ],
        },
        "analyst",
    )
    brief = {
        "research_question": "Can the issuer refinance?",
        "decision_context": "Underwrite risk.",
        "as_of_date": "2026-08-23",
        "time_horizon": "Through 2029",
        "must_answer": [],
        "exclusions": [],
    }
    run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
    runtime._execute(run["id"], "analyst")
    paused = ledgers.runs.get_run(run["id"])
    assert paused is not None
    runtime.approve_research_plan(
        run["id"], "approver", paused["research"]["proposed_plan_hash"]
    )
    approved = ledgers.runs.get_run(run["id"])
    assert approved is not None
    approved["_test_second_source_id"] = second_source["id"]
    return ledgers, runtime, approved, source_id


def _approved_final(
    ledgers: MemoryLedgerSet, approved: dict[str, Any], source_id: str
) -> dict[str, Any]:
    cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
    cp0 = ledgers.runs.get_artifact(cp0_node["artifact_id"])
    assert cp0 is not None
    source_set = approved["research"]["proposed_plan"]["source_set"]
    second_source_id = approved["_test_second_source_id"]
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
            {
                "workstream_id": item["id"],
                "finding": "The lane is supported."
                if index == 0
                else "No additional material claim was required.",
                "claim_ids": ["C-1"] if index == 0 else [],
                "status": "complete",
            }
            for index, item in enumerate(workstreams)
        ],
        material_claims=[
            {
                **_cpdr_payload()["material_claims"][0],
                "workstream_id": workstreams[0]["id"],
                "evidence_refs": [
                    {"source_id": source_id, "block_id": "b00001"},
                    {"source_id": second_source_id, "block_id": "b00002"},
                ],
            }
        ],
        evidence=[
            {**_cpdr_payload()["evidence"][0], "source_id": source_id},
            {
                **_cpdr_payload()["evidence"][0],
                "evidence_id": "E-2",
                "source_id": second_source_id,
                "source_digest": "f" * 64,
                "block_id": "b00002",
                "locator": '{"line":2}',
            },
        ],
    )


def _canonical_cpdr_artifact(
    ledgers: MemoryLedgerSet,
    runtime: WorkflowRuntime,
    approved: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
    cp0 = ledgers.runs.get_artifact(cp0_node["artifact_id"])
    source_set = ledgers.sources.source_set(approved["plan"]["source_set_id"])
    assert cp0 is not None and source_set is not None
    upstream = [
        {"module_id": "CP-0", "artifact_id": cp0["id"], "digest": cp0["digest"]}
    ]
    raw = _approved_final(ledgers, approved, source_id)
    returned = {
        (source_id, "b00001"): {
            "source_digest": "e" * 64,
            "origin_family": "e" * 64,
            "authority_class": "unclassified",
            "locator": '{"line":1}',
            "extractor_version": "builtin-v1",
            "confidence": "HIGH",
        },
        (approved["_test_second_source_id"], "b00002"): {
            "source_digest": "f" * 64,
            "origin_family": "f" * 64,
            "authority_class": "unclassified",
            "locator": '{"line":2}',
            "extractor_version": "builtin-v1",
            "confidence": "HIGH",
        },
    }
    host = {key: raw[key] for key in _cpdr_host()}
    workstreams = {
        item["id"] for item in approved["research"]["proposed_plan"]["workstreams"]
    }
    payload = validate_cpdr_payload(
        raw,
        host,
        workstreams,
        returned,
        approved["research"]["proposed_plan"],
        approved["research"]["brief"],
    )
    confidence = runtime.bundle.cpdr_confidence(confidence_inputs(payload, returned))
    filename, markdown = workflow_domain.render_cpdr_markdown(
        payload, confidence, approved["created_at"][:10], upstream
    )
    envelope = workflow_domain._build_cpdr_envelope(
        payload.model_dump(mode="json"),
        confidence,
        filename,
        markdown,
        runtime.bundle.build_id,
        approved["research"]["approved_plan_hash"],
        source_set,
        upstream,
    )
    fingerprint = digest(
        {
            "plan": approved["plan"]["plan_digest"],
            "module": "CP-DR",
            "source_set": source_set,
            "source_ids": list(source_set["source_ids"]),
            "upstream_artifacts": upstream,
        }
    )
    return {
        "id": "art-canonical",
        "case_id": approved["case_id"],
        "run_id": approved["id"],
        "module_id": "CP-DR",
        "created_by": "analyst",
        "payload": envelope,
        "markdown": markdown,
        "filename": filename,
        "digest": digest(envelope),
        "input_fingerprint": fingerprint,
        "created_at": approved["created_at"],
    }


@pytest.mark.parametrize(
    "mutation",
    ["plan_hash", "model", "source_set", "cp0"],
)
def test_cpdr_authority_mismatches_fail_closed(mutation: str) -> None:
    ledgers, runtime, approved, _ = _approved_cpdr_case()
    try:
        if mutation == "plan_hash":
            _mutate_research(
                ledgers,
                approved["id"],
                lambda research: research.update(
                    approved_plan_hash="sha256:" + "b" * 64
                ),
            )
        elif mutation == "model":
            _mutate_research(
                ledgers,
                approved["id"],
                lambda research: research.update(model="other-model"),
            )
        elif mutation == "source_set":
            ledgers.sources.ingest(
                {
                    "case_id": approved["case_id"],
                    "filename": "changed.txt",
                    "media_type": "text/plain",
                    "bytes": 1,
                    "sha256": "9" * 64,
                    "vault_path": None,
                    "blocks": [],
                },
                "analyst",
            )
        else:
            cp0_node = next(
                node for node in approved["nodes"] if node["module_id"] == "CP-0"
            )
            cp0 = ledgers.runs.get_artifact(cp0_node["artifact_id"])
            assert cp0 is not None
            forged_cp0 = copy.deepcopy(cp0)
            forged_cp0["payload"]["status"] = "BLOCKED"

            class ForgedCP0Runs(_RunLedgerDouble):
                def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
                    if artifact_id == forged_cp0["id"]:
                        return copy.deepcopy(forged_cp0)
                    return self.ledger.get_artifact(artifact_id)

            runtime.runs = ForgedCP0Runs(ledgers.runs)
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert (
            failed is not None and failed["error"]["code"] == "AGENT_AUTHORITY_MISMATCH"
        )
        cpdr_node = next(
            node for node in failed["nodes"] if node["module_id"] == "CP-DR"
        )
        assert cpdr_node["artifact_id"] is None
    finally:
        runtime.close()


def test_cpdr_reclaimed_unresolved_inflight_fails_closed() -> None:
    ledgers, runtime, approved, _ = _approved_cpdr_case()
    try:
        _mutate_research(
            ledgers,
            approved["id"],
            lambda research: research.update(inflight_request_digest="unknown-spend"),
        )
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
    finally:
        runtime.close()


def test_cpdr_reconciled_attempt_without_artifact_restarts_with_remaining_budget() -> (
    None
):
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research.update(
            phase="researching", inflight_request_digest=None
        ),
    )
    final = _approved_final(ledgers, approved, source_id)
    _queue_cpdr_success(provider, final, source_id)
    try:
        runtime._execute(approved["id"], "replacement")
        completed = ledgers.runs.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert completed["research"]["phase"] == "complete"
    finally:
        runtime.close()


def test_cpdr_existing_fingerprint_is_relinked_without_provider_call() -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    recovered = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)
    assert cpdr_artifact_is_valid(
        ledgers.runs,
        ledgers.sources,
        approved,
        cpdr_node,
        recovered,
        runtime.bundle,
    )
    research = copy.deepcopy(approved["research"])
    research["phase"] = "researching"
    token = ledgers.runs.claim(approved["id"], "recovery-seed")
    assert token is not None
    recovered = ledgers.runs.complete_node(
        approved["id"],
        token,
        cpdr_node["id"],
        recovered,
        research,
        {"node_id": cpdr_node["id"], "module_id": "CP-DR"},
    )
    ledgers.runs.update_node_fenced(
        approved["id"],
        token,
        cpdr_node["id"],
        status="pending",
        artifact_id=None,
    )
    ledgers.runs.finish(approved["id"], token)
    try:
        runtime._execute(approved["id"], "replacement")
        completed = ledgers.runs.get_run(approved["id"])
        linked = (
            next(node for node in completed["nodes"] if node["id"] == cpdr_node["id"])
            if completed
            else None
        )
        assert completed is not None and completed["status"] == "succeeded"
        assert linked is not None and linked["artifact_id"] == recovered["id"]
        assert (
            len(
                [
                    event
                    for event in ledgers.runs.events_after(approved["id"])
                    if event["event"] == "node.succeeded"
                    and event["data"].get("module_id") == "CP-DR"
                ]
            )
            == 2
        )
        assert provider.calls == []
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "markdown",
        "transport",
        "confidence",
        "filename",
        "digest",
        "fingerprint",
        "plan_hash",
        "withdrawn",
    ],
)
def test_strict_cpdr_artifact_validator_rejects_noncanonical_artifacts(
    mutation: str,
) -> None:
    ledgers, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)
    invalid = copy.deepcopy(canonical)
    if mutation == "markdown":
        invalid["markdown"] += "forged\n"
    elif mutation == "transport":
        invalid["payload"]["transport"]["evidence"][0]["independence_family"] = (
            "provider-forged-family"
        )
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
        approved = _mutate_research(
            ledgers,
            approved["id"],
            lambda research: research.update(approved_plan_hash="sha256:" + "0" * 64),
        )
    else:
        ledgers.sources.withdraw(
            approved["case_id"], approved["_test_second_source_id"], "analyst"
        )
    try:
        assert not cpdr_artifact_is_valid(
            ledgers.runs,
            ledgers.sources,
            approved,
            cpdr_node,
            invalid,
            runtime.bundle,
        )
        forged_run = copy.deepcopy(approved)
        forged_run["status"] = "succeeded"
        forged_node = next(
            node for node in forged_run["nodes"] if node["id"] == cpdr_node["id"]
        )
        forged_node.update(status="succeeded", artifact_id=invalid["id"])

        class InvalidArtifactRuns(_RunLedgerDouble):
            def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
                if artifact_id == invalid["id"]:
                    return copy.deepcopy(invalid)
                return self.ledger.get_artifact(artifact_id)

        with pytest.raises(ValueError, match="RUN_NOT_READY"):
            build_snapshot_payload(
                InvalidArtifactRuns(ledgers.runs),
                ledgers.sources,
                forged_run,
                runtime.bundle,
            )
    finally:
        runtime.close()


def test_strict_cpdr_artifact_validator_requires_real_vendored_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)
    monkeypatch.setattr(
        runtime.bundle,
        "validate_cpdr_handoff",
        lambda *_args, **_kwargs: type(
            "InvalidHandoff",
            (),
            {"identity_mismatches": [], "errors": ["invalid"], "exit_code": 1},
        )(),
    )
    try:
        assert not cpdr_artifact_is_valid(
            ledgers.runs,
            ledgers.sources,
            approved,
            cpdr_node,
            canonical,
            runtime.bundle,
        )
    finally:
        runtime.close()


@pytest.mark.parametrize("entrypoint", ["reuse", "run_success", "snapshot"])
def test_strict_cpdr_artifact_entrypoints_require_current_bundle_integrity(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    ledgers, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)

    def fail_integrity() -> Any:
        raise MethodologyError("forced current integrity failure")

    monkeypatch.setattr(runtime.bundle, "verify", fail_integrity)
    try:
        assert not cpdr_artifact_is_valid(
            ledgers.runs,
            ledgers.sources,
            approved,
            cpdr_node,
            canonical,
            runtime.bundle,
        )
        if entrypoint == "reuse":
            _complete_cpdr_node_for_test(
                ledgers, approved, cpdr_node, canonical, reset_to_pending=True
            )
            runtime._execute(approved["id"], "replacement")
            failed = ledgers.runs.get_run(approved["id"])
            assert failed is not None and failed["status"] == "failed"
            assert failed["error"]["code"] == "AGENT_AUTHORITY_MISMATCH"
        elif entrypoint == "run_success":
            _complete_cpdr_node_for_test(ledgers, approved, cpdr_node, canonical)
            runtime._execute(approved["id"], "final-validator")
            failed = ledgers.runs.get_run(approved["id"])
            assert failed is not None and failed["status"] == "failed"
            assert failed["error"]["code"] == "DAG_BLOCKED"
        else:
            forged_run = copy.deepcopy(approved)
            forged_run["status"] = "succeeded"
            forged_node = next(
                node for node in forged_run["nodes"] if node["id"] == cpdr_node["id"]
            )
            forged_node.update(status="succeeded", artifact_id=canonical["id"])

            class CanonicalArtifactRuns(_RunLedgerDouble):
                def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
                    if artifact_id == canonical["id"]:
                        return copy.deepcopy(canonical)
                    return self.ledger.get_artifact(artifact_id)

            with pytest.raises(ValueError, match="RUN_NOT_READY"):
                build_snapshot_payload(
                    CanonicalArtifactRuns(ledgers.runs),
                    ledgers.sources,
                    forged_run,
                    runtime.bundle,
                )
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_atomic_completion_replaces_invalid_same_fingerprint_artifact(
    backend: str,
) -> None:
    ledgers: MemoryLedgerSet | PostgresLedgerSet = (
        PostgresLedgerSet(_postgres_url(), lease_seconds=1.0)
        if backend == "postgres"
        else MemoryLedgerSet(lease_seconds=1.0)
    )
    ledgers, runtime, approved, source_id = _approved_cpdr_case(ledgers)  # type: ignore[arg-type]
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    valid = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)  # type: ignore[arg-type]
    valid["id"] = f"art-valid-{backend}"
    invalid = copy.deepcopy(valid)
    invalid["id"] = f"art-invalid-{backend}"
    invalid["markdown"] += "forged\n"
    seed_token = ledgers.runs.claim(approved["id"], "collision-seed")
    assert seed_token is not None
    invalid = ledgers.runs.complete_node(
        approved["id"],
        seed_token,
        cpdr_node["id"],
        invalid,
        {**approved["research"], "phase": "researching"},
        {"node_id": cpdr_node["id"], "module_id": "CP-DR"},
    )
    ledgers.runs.update_node_fenced(
        approved["id"],
        seed_token,
        cpdr_node["id"],
        status="pending",
        artifact_id=None,
    )
    time.sleep(1.05)
    token = ledgers.runs.claim(approved["id"], "collision-worker")
    assert token is not None
    full_run = ledgers.runs.get_run(approved["id"])
    assert full_run is not None

    def validator(candidate: dict[str, Any]) -> bool:
        return cpdr_artifact_is_valid(
            ledgers.runs,
            ledgers.sources,
            full_run,
            cpdr_node,
            candidate,
            runtime.bundle,
        )

    try:
        completed = ledgers.runs.complete_node(
            approved["id"],
            token,
            cpdr_node["id"],
            valid,
            {**approved["research"], "phase": "complete"},
            {"node_id": cpdr_node["id"], "module_id": "CP-DR"},
            validator,
        )
        assert completed["id"] != invalid["id"]
        assert ledgers.runs.get_artifact(invalid["id"]) is None
        durable = (
            PostgresLedgerSet(_postgres_url()) if backend == "postgres" else ledgers
        )
        durable_run = durable.runs.get_run(approved["id"])
        durable_node = (
            next(node for node in durable_run["nodes"] if node["id"] == cpdr_node["id"])
            if durable_run
            else None
        )
        assert (
            durable_node is not None and durable_node["artifact_id"] == completed["id"]
        )
        assert cpdr_artifact_is_valid(
            durable.runs,
            durable.sources,
            durable_run or {},
            durable_node,
            completed,
            runtime.bundle,
        )
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
def test_cpdr_evidence_reads_enforce_case_pin_withdrawal_and_block_identity(
    mode: str, expected: str
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    sources = _SourceCatalogDouble(ledgers.sources)
    runtime.sources = sources
    tool_source = source_id
    tool_block = "b00001"
    if mode == "cross_case":
        sources.override_source(
            source_id, lambda source: source.update(case_id="other-case")
        )
    elif mode == "unpinned":
        tool_source = "src_unpinned"
    elif mode == "withdrawn":
        sources.override_source(source_id, lambda source: source.update(withdrawn=True))
    elif mode == "absent_block":
        tool_block = "missing"
    block_ids = [tool_block, tool_block] if mode == "duplicate_block" else [tool_block]
    provider.responses.append(
        ProviderMessage(
            content=[
                ProviderBlock(
                    type="tool_use",
                    id="tool-1",
                    name="read_evidence",
                    input={"source_id": tool_source, "block_ids": block_ids},
                )
            ],
            stop_reason="tool_use",
            usage=ProviderUsage(20, 30),
        )
    )
    provider.counts.append(20)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == expected
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "budget",
    [
        "turns",
        "input_tokens",
        "output_tokens",
        "active_minutes",
        "evidence_reads",
        "evidence_bytes",
    ],
)
def test_cpdr_runwide_budget_ceilings_fail_before_overspend(budget: str) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    limit = 0 if budget != "evidence_bytes" else 1
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research["budget_limits"].update({budget: limit}),
    )
    if budget in {"evidence_reads", "evidence_bytes"}:
        response = ProviderMessage(
            content=[
                ProviderBlock(
                    type="tool_use",
                    id="tool-1",
                    name="read_evidence",
                    input={"source_id": source_id, "block_ids": ["b00001"]},
                )
            ],
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
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        cpdr_node = next(
            node for node in failed["nodes"] if node["module_id"] == "CP-DR"
        )
        assert cpdr_node["artifact_id"] is None
    finally:
        runtime.close()


@pytest.mark.parametrize("limit", ["blocks", "bytes"])
def test_cpdr_manifest_ceiling_fails_before_provider_construction(limit: str) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    sources = _SourceCatalogDouble(ledgers.sources)
    runtime.sources = sources
    if limit == "blocks":
        sources.override_source(
            source_id,
            lambda source: source.update(
                blocks=[
                    {
                        "block_id": f"b{index:05d}",
                        "locator": {"line": index},
                        "text": "x",
                        "extractor_version": "builtin-v1",
                        "confidence": "HIGH",
                    }
                    for index in range(2_001)
                ]
            ),
        )
    else:
        sources.override_source(
            source_id,
            lambda source: source["blocks"][0].update(
                locator={"section": "x" * (256 * 1_024)}
            ),
        )
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert provider.calls == []
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "field", ["filename", "media_type", "locator", "extractor_version", "confidence"]
)
def test_cpdr_manifest_rejects_oversized_fields_before_encoding(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    sources = _SourceCatalogDouble(ledgers.sources)
    runtime.sources = sources
    sentinel = "manifest-sentinel-" + "x" * (512 * 1_024)

    def mutate_source(source: dict[str, Any]) -> None:
        if field in {"filename", "media_type"}:
            source[field] = sentinel
        elif field == "locator":
            source["blocks"][0][field] = {"nested": sentinel}
        else:
            source["blocks"][0][field] = sentinel

    sources.override_source(source_id, mutate_source)
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
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert provider.calls == []
    finally:
        runtime.close()


def test_cpdr_manifest_rejects_many_short_locator_nodes_before_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    sources = _SourceCatalogDouble(ledgers.sources)
    runtime.sources = sources
    locator = {"groups": [list(range(100)) for _ in range(6)]}
    sources.override_source(
        source_id, lambda source: source["blocks"][0].update(locator=locator)
    )
    original_dumps = workflow_domain.json.dumps

    def guarded_dumps(value: Any, *args: Any, **kwargs: Any) -> str:
        assert not isinstance(value, dict) or value.get("locator") is not locator
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(workflow_domain.json, "dumps", guarded_dumps)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert provider.calls == []
    finally:
        runtime.close()


def test_cpdr_manifest_exact_block_and_encoded_byte_boundaries_are_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider(
        [], counts=[ProviderUnavailable("boundary reached provider")]
    )
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    expected_manifest = []
    for manifest_source_id in (source_id, approved["_test_second_source_id"]):
        source = ledgers.sources.get_source(manifest_source_id)
        assert source is not None
        block = source["blocks"][0]
        expected_manifest.append(
            {
                "source_id": manifest_source_id,
                "digest": source["sha256"],
                "filename": source["filename"],
                "media_type": source["media_type"],
                "blocks": [
                    {
                        "block_id": block["block_id"],
                        "locator": block["locator"],
                        "extractor_version": block["extractor_version"],
                        "confidence": block["confidence"],
                    }
                ],
            }
        )
    encoded_bytes = len(
        json.dumps(
            expected_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    )
    monkeypatch.setattr(workflow_domain, "MAX_CPDR_MANIFEST_BLOCKS", 2)
    monkeypatch.setattr(workflow_domain, "MAX_CPDR_MANIFEST_BYTES", encoded_bytes)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert (
            failed is not None
            and failed["error"]["code"] == "AGENT_PROVIDER_UNAVAILABLE"
        )
        assert [kind for kind, _request in provider.calls] == ["count_tokens"]
    finally:
        runtime.close()


def test_cpdr_unexpected_post_provider_failure_is_sanitized_and_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    final = _approved_final(ledgers, approved, source_id)
    _queue_cpdr_success(provider, final, source_id)
    monkeypatch.setattr(
        workflow_domain,
        "render_cpdr_markdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("secret-post-provider")
        ),
    )
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert failed["research"]["phase"] == "failed"
        assert any(
            item.get("terminal_code") == "AGENT_OUTPUT_INVALID"
            for item in failed["research"]["attempts"]
        )
        assert "secret-post-provider" not in json.dumps(
            {
                "run": failed,
                "events": ledgers.runs.events_after(approved["id"]),
            }
        )
    finally:
        runtime.close()


def test_cpdr_prior_179_seconds_caps_next_operation_to_one_second(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider([], counts=[ProviderUnavailable("captured")])
    ledgers, runtime, approved, _source_id = _approved_cpdr_case(provider=provider)
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research["budget_used"].update(active_minutes=179 / 60),
    )
    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: 1_000.0)
    try:
        runtime._execute(approved["id"], "approver")
        assert provider.calls and 0 < provider.calls[0][1].timeout <= 1.0
        run = ledgers.runs.get_run(approved["id"])
        assert run is not None
        cpdr_node = next(node for node in run["nodes"] if node["module_id"] == "CP-DR")
        assert cpdr_node["artifact_id"] is None
    finally:
        runtime.close()


def test_cpdr_approval_wait_is_excluded_while_planning_time_is_charged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers = MemoryLedgerSet()
    settings = Settings(
        environment="production",
        storage_dir=Path("/tmp/caos-cpdr-approval-time"),
        deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key",
        cpdr_agent_enabled=True,
        cpdr_pilot_subjects=("analyst",),
    )
    bundle = DeployVBundle(DEPLOY_V)
    provider = _FakeProvider(
        [], counts=[ProviderUnavailable("stop after timing check")]
    )
    runtime = WorkflowRuntime(
        ledgers.runs, ledgers.sources, bundle, settings, provider=provider
    )
    case = ledgers.runs.create_case("Approval time", "Issuer", "Testing", "analyst")
    ledgers.sources.ingest(
        {
            "case_id": case["id"],
            "filename": "issuer.txt",
            "media_type": "text/plain",
            "bytes": 1,
            "sha256": "a" * 64,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00001",
                    "locator": {"line": 1},
                    "text": "x",
                    "extractor_version": "builtin-v1",
                    "confidence": "HIGH",
                }
            ],
        },
        "analyst",
    )
    brief = {
        "research_question": "Question",
        "decision_context": "Context",
        "as_of_date": "2026-08-23",
        "time_horizon": "2029",
        "must_answer": [],
        "exclusions": [],
    }

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
        run = runtime.start_run(
            case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief
        )
        runtime._execute(run["id"], "analyst")
        paused = ledgers.runs.get_run(run["id"])
        assert paused is not None and paused["research"]["budget_used"][
            "active_minutes"
        ] == pytest.approx(2 / 60)
        Clock.now += 10_000
        runtime.approve_research_plan(
            run["id"], "approver", paused["research"]["proposed_plan_hash"]
        )
        runtime._execute(run["id"], "approver")
        failed = ledgers.runs.get_run(run["id"])
        assert failed is not None and failed["research"]["budget_used"][
            "active_minutes"
        ] == pytest.approx(2 / 60)
    finally:
        runtime.close()


def test_cpdr_slow_render_is_charged_before_artifact_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research["budget_used"].update(active_minutes=179 / 60),
    )
    final = _approved_final(ledgers, approved, source_id)

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
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        cpdr_node = next(
            node for node in failed["nodes"] if node["module_id"] == "CP-DR"
        )
        assert cpdr_node["artifact_id"] is None
    finally:
        runtime.close()


@pytest.mark.parametrize("operation", ["scorer", "renderer", "validator", "envelope"])
def test_cpdr_throwing_host_operations_charge_active_time(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    final = _approved_final(ledgers, approved, source_id)

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
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert failed["research"]["budget_used"]["active_minutes"] >= 2 / 60
    finally:
        runtime.close()


def test_cpdr_slow_atomic_completion_crosses_ceiling_and_cannot_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider([])
    ledgers, runtime, approved, source_id = _approved_cpdr_case(provider=provider)
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research["budget_used"].update(active_minutes=179 / 60),
    )
    final = _approved_final(ledgers, approved, source_id)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    _queue_cpdr_success(provider, final, source_id)

    class SlowCompletionRuns(_RunLedgerDouble):
        def complete_node(self, *args: Any, **kwargs: Any) -> Any:
            Clock.now += 2.0
            return self.ledger.complete_node(*args, **kwargs)

    runtime.runs = SlowCompletionRuns(ledgers.runs)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        cpdr_node = (
            next(node for node in failed["nodes"] if node["module_id"] == "CP-DR")
            if failed
            else None
        )
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 181 / 60
        assert cpdr_node is not None and cpdr_node["status"] == "failed"
    finally:
        runtime.close()


def test_cpdr_no_pending_final_validation_is_charged_before_run_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers, runtime, approved, source_id = _approved_cpdr_case()
    artifact = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    approved["research"]["budget_used"]["active_minutes"] = 179 / 60
    _complete_cpdr_node_for_test(ledgers, approved, cpdr_node, artifact)

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
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 181 / 60
        assert not any(
            item["event"] == "run.succeeded"
            for item in ledgers.runs.events_after(approved["id"])
        )
    finally:
        runtime.close()


def _ready_cpdr_finalization() -> tuple[
    MemoryLedgerSet, WorkflowRuntime, dict[str, Any], dict[str, Any], dict[str, Any]
]:
    ledgers, runtime, approved, source_id = _approved_cpdr_case()
    artifact = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    artifact = _complete_cpdr_node_for_test(ledgers, approved, cpdr_node, artifact)
    return ledgers, runtime, approved, cpdr_node, artifact


def _assert_run_cannot_be_accepted(
    runtime: WorkflowRuntime, run: dict[str, Any]
) -> None:
    with pytest.raises(WorkflowError, match="RUN_NOT_READY"):
        runtime.accept_run(run["case_id"], run["id"], "approver")


def test_cpdr_finalization_allowance_is_fixed_and_ponytail_bounded() -> None:
    assert 2.0 < workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS <= 5.0


def test_cpdr_179_seconds_cannot_enter_atomic_success_finalization() -> None:
    ledgers, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research["budget_used"].update(active_minutes=179 / 60),
    )
    try:
        runtime._execute(approved["id"], "final-reserve")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 180 / 60
        assert not any(
            item["event"] == "run.succeeded"
            for item in ledgers.runs.events_after(approved["id"])
        )
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()


def test_cpdr_finalization_reservation_failure_is_sanitized_before_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    research_writes = 0

    class FailingReservationRuns(_RunLedgerDouble):
        def update_run_fenced(
            self, run_id: str, attempt_token: str, **changes: Any
        ) -> None:
            nonlocal research_writes
            if set(changes) == {"research"}:
                research_writes += 1
                if research_writes == 2:
                    raise RuntimeError("secret-final-reservation")
            self.ledger.update_run_fenced(run_id, attempt_token, **changes)

    runtime.runs = FailingReservationRuns(ledgers.runs)
    try:
        runtime._execute(approved["id"], "reservation-failure")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        events = ledgers.runs.events_after(approved["id"])
        assert not any(item["event"] == "run.succeeded" for item in events)
        assert "secret-final-reservation" not in json.dumps(
            {"run": failed, "events": events}
        )
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()


def test_cpdr_atomic_success_persistence_failure_rolls_back_and_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()

    class FailingFinalizationRuns(_RunLedgerDouble):
        def finalize_success(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("secret-atomic-finalization")

    runtime.runs = FailingFinalizationRuns(ledgers.runs)
    try:
        runtime._execute(approved["id"], "atomic-failure")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        events = ledgers.runs.events_after(approved["id"])
        assert not any(item["event"] == "run.succeeded" for item in events)
        assert "secret-atomic-finalization" not in json.dumps(
            {"run": failed, "events": events}
        )
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()


def test_cpdr_success_finalization_is_single_terminal_run_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers, runtime, approved, cpdr_node, artifact = _ready_cpdr_finalization()
    finalized = False
    post_final_updates: list[dict[str, Any]] = []

    class TrackingFinalizationRuns(_RunLedgerDouble):
        def finalize_success(self, *args: Any, **kwargs: Any) -> None:
            nonlocal finalized
            self.ledger.finalize_success(*args, **kwargs)
            finalized = True

        def update_run_fenced(
            self, run_id: str, attempt_token: str, **changes: Any
        ) -> None:
            if finalized:
                post_final_updates.append(copy.deepcopy(changes))
            self.ledger.update_run_fenced(run_id, attempt_token, **changes)

    runtime.runs = TrackingFinalizationRuns(ledgers.runs)
    try:
        runtime._execute(approved["id"], "atomic-success")
        completed = ledgers.runs.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert completed["research"]["budget_used"]["active_minutes"] >= (
            workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS / 60
        )
        completed_node = next(
            item for item in completed["nodes"] if item["id"] == cpdr_node["id"]
        )
        assert (
            completed_node["status"] == "succeeded"
            and completed_node["artifact_id"] == artifact["id"]
        )
        assert ledgers.runs.get_artifact(artifact["id"])["digest"] == artifact["digest"]  # type: ignore[index]
        assert [item["event"] for item in completed["events"]].count(
            "run.succeeded"
        ) == 1
        assert post_final_updates == []
    finally:
        runtime.close()


def test_cpdr_two_second_atomic_finalization_is_covered_by_fixed_reserve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledgers, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    _mutate_research(
        ledgers,
        approved["id"],
        lambda research: research["budget_used"].update(active_minutes=170 / 60),
    )

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)
    finalization_seconds: list[float] = []

    class SlowFinalizationRuns(_RunLedgerDouble):
        def finalize_success(self, *args: Any, **kwargs: Any) -> None:
            started = Clock.now
            Clock.now += 2.0
            self.ledger.finalize_success(*args, **kwargs)
            finalization_seconds.append(Clock.now - started)

    runtime.runs = SlowFinalizationRuns(ledgers.runs)
    try:
        runtime._execute(approved["id"], "slow-atomic-success")
        completed = ledgers.runs.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert finalization_seconds == [2.0]
        assert (
            finalization_seconds[0]
            <= workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS
        )
        assert completed["research"]["budget_used"]["active_minutes"] >= (
            (170 + workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS) / 60
        )
    finally:
        runtime.close()


def _ready_cpdr_finalization_on(
    ledgers: MemoryLedgerSet | PostgresLedgerSet,
    *,
    active_minutes: float | None = None,
) -> tuple[
    MemoryLedgerSet | PostgresLedgerSet,
    WorkflowRuntime,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    ledgers, runtime, approved, source_id = _approved_cpdr_case(ledgers)  # type: ignore[arg-type]
    artifact = _canonical_cpdr_artifact(ledgers, runtime, approved, source_id)  # type: ignore[arg-type]
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    if active_minutes is not None:
        approved["research"]["budget_used"]["active_minutes"] = active_minutes
    is_postgres = isinstance(ledgers, PostgresLedgerSet)
    artifact = _complete_cpdr_node_for_test(  # type: ignore[arg-type]
        ledgers, approved, cpdr_node, artifact, finish_job=not is_postgres
    )
    if is_postgres:
        time.sleep(1.05)
    return ledgers, runtime, approved, cpdr_node, artifact


@pytest.mark.parametrize("backend", ["memory", "postgres"])
@pytest.mark.parametrize("delay_site", ["before_entry", "during_persistence"])
def test_cpdr_174_plus_ten_second_finalization_never_commits_success(
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
    delay_site: str,
) -> None:
    selected_ledgers: MemoryLedgerSet | PostgresLedgerSet = (
        PostgresLedgerSet(_postgres_url(), lease_seconds=1.0)
        if backend == "postgres"
        else MemoryLedgerSet()
    )
    ledgers, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization_on(
        selected_ledgers,
        active_minutes=174 / 60,
    )

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    class DelayedFinalizationRuns(_RunLedgerDouble):
        def finalize_success(self, *args: Any, **kwargs: Any) -> None:
            Clock.now += 10.0
            self.ledger.finalize_success(*args, **kwargs)

    runtime.runs = DelayedFinalizationRuns(ledgers.runs)

    try:
        runtime._execute(approved["id"], f"deadline-{backend}-{delay_site}")
        failed = ledgers.runs.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 179 / 60
        assert not any(item["event"] == "run.succeeded" for item in failed["events"])
        _assert_run_cannot_be_accepted(runtime, failed)
        if backend == "postgres":
            restored = PostgresLedgerSet(_postgres_url()).runs.get_run(approved["id"])
            assert restored is not None and restored["status"] == "failed"
            assert not any(
                item["event"] == "run.succeeded" for item in restored["events"]
            )
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_cpdr_two_second_finalization_commits_inside_absolute_deadline(
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    selected_ledgers: MemoryLedgerSet | PostgresLedgerSet = (
        PostgresLedgerSet(_postgres_url(), lease_seconds=1.0)
        if backend == "postgres"
        else MemoryLedgerSet()
    )
    ledgers, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization_on(
        selected_ledgers,
        active_minutes=170 / 60,
    )

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    class DelayedFinalizationRuns(_RunLedgerDouble):
        def finalize_success(self, *args: Any, **kwargs: Any) -> None:
            Clock.now += 2.0
            self.ledger.finalize_success(*args, **kwargs)

    runtime.runs = DelayedFinalizationRuns(ledgers.runs)
    try:
        runtime._execute(approved["id"], f"within-deadline-{backend}")
        completed = ledgers.runs.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert [item["event"] for item in completed["events"]].count(
            "run.succeeded"
        ) == 1
        if backend == "postgres":
            restored = PostgresLedgerSet(_postgres_url()).runs.get_run(approved["id"])
            assert restored is not None and restored["status"] == "succeeded"
            assert [item["event"] for item in restored["events"]].count(
                "run.succeeded"
            ) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_expired_finalization_deadline_does_not_mask_job_fencing(backend: str) -> None:
    ledgers: MemoryLedgerSet | PostgresLedgerSet = (
        PostgresLedgerSet(_postgres_url(), lease_seconds=0.5)
        if backend == "postgres"
        else MemoryLedgerSet(lease_seconds=0.5)
    )
    run, node = _queued_ledger_run(ledgers, dependencies=[])  # type: ignore[arg-type]
    assert node is not None
    token = ledgers.runs.claim(run["id"], f"fenced-deadline-{backend}")
    assert token is not None
    artifact_payload: dict[str, Any] = {}
    ledgers.runs.complete_node(
        run["id"],
        token,
        node["id"],
        {
            **_artifact(run["id"]),
            "case_id": run["case_id"],
            "payload": artifact_payload,
            "digest": digest(artifact_payload),
            "created_at": "2026-08-25T00:00:00+00:00",
        },
        None,
        {"node_id": node["id"], "module_id": node["module_id"]},
    )
    time.sleep(0.55)

    with pytest.raises(JobFencedError):
        ledgers.runs.finalize_success(
            run["id"],
            token,
            None,
            {"run_id": run["id"]},
            deadline=time.monotonic() - 1,
        )


def test_open_postgres_event_stream_refreshes_worker_events_without_reconnect() -> None:
    database_url = _postgres_url()
    api_ledgers = PostgresLedgerSet(database_url)
    worker_ledgers = PostgresLedgerSet(database_url)
    run, node = _queued_ledger_run(worker_ledgers, dependencies=[])  # type: ignore[arg-type]
    assert node is not None
    runtime = WorkflowRuntime(
        api_ledgers.runs,
        object(),
        object(),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-sse-refresh"),
            deploy_v_root=DEPLOY_V,
        ),
    )  # type: ignore[arg-type]
    stream = runtime.stream_events(run["id"])
    try:
        assert next(stream) == ": keepalive\n\n"
        token = worker_ledgers.runs.claim(run["id"], "sse-worker")
        assert token is not None
        worker_ledgers.runs.update_run_fenced(run["id"], token, status="running")
        worker_ledgers.runs.emit_fenced(
            run["id"], token, "run.running", {"run_id": run["id"]}
        )
        worker_ledgers.runs.complete_node(
            run["id"],
            token,
            node["id"],
            {
                **_artifact(run["id"]),
                "payload": {},
                "digest": digest({}),
                "markdown": "",
                "created_at": "2026-08-25T00:00:00+00:00",
            },
            None,
            {"node_id": node["id"], "module_id": node["module_id"]},
        )
        worker_ledgers.runs.finalize_success(
            run["id"],
            token,
            None,
            {"run_id": run["id"]},
            deadline=time.monotonic()
            + workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS,
        )

        delivered = [next(stream), *list(stream)]
        assert [item.split("\n", 2)[0] for item in delivered] == [
            "id: 1",
            "id: 2",
            "id: 3",
        ]
        assert [item.split("\n", 2)[1] for item in delivered] == [
            "event: run.running",
            "event: node.succeeded",
            "event: run.succeeded",
        ]
    finally:
        runtime.close()


def test_gateway_fake_clock_charges_slow_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moments = iter([0.0, 0.0, 0.0, 0.0, 0.0, 2.0])
    monkeypatch.setattr(provider_module.time, "monotonic", lambda: next(moments))
    charged: list[float] = []
    final_response = _Response(
        "end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]
    )

    result = AnthropicGateway(
        "key", "claude-sonnet-4-6", client=_Client([final_response])
    ).run(
        system="authority",
        user="brief",
        read_evidence=lambda *_: [],
        validate=lambda value: value,
        lease_check=lambda: None,
        reserve=lambda *_: None,
        reconcile=lambda *_: None,
        record=lambda *_args, **_kwargs: None,
        active_time=charged.append,
        semaphore=threading.BoundedSemaphore(2),
    )

    assert result["module_id"] == "CP-DR"
    assert charged[-1] == 2.0


@pytest.mark.parametrize("operation", ["count", "create"])
def test_gateway_crossing_active_ceiling_records_terminal_attempt(
    operation: str,
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    calls = 0
    client = _Client(
        [_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])]
    )

    def charge(_elapsed: float) -> None:
        nonlocal calls
        calls += 1
        if (operation == "count" and calls == 1) or (
            operation == "create" and calls == 2
        ):
            raise AgentError("AGENT_BUDGET_EXCEEDED")

    with pytest.raises(AgentError, match="AGENT_BUDGET_EXCEEDED"):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)),
            active_time=charge,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert any(
        details.get("terminal_code") == "AGENT_BUDGET_EXCEEDED"
        for _kind, details in events
    )


def test_gateway_transient_ordinary_record_failure_is_sanitized_and_terminalized() -> (
    None
):
    events: list[tuple[str, dict[str, Any]]] = []
    failed_once = False

    def record(kind: str, **details: Any) -> None:
        nonlocal failed_once
        if kind != "terminal" and not failed_once:
            failed_once = True
            raise RuntimeError("sensitive transient record failure")
        events.append((kind, details))

    client = _Client(
        [_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])]
    )
    with pytest.raises(AgentError) as captured:
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=record,
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert captured.value.code == "AGENT_OUTPUT_INVALID"
    assert any(
        details.get("terminal_code") == "AGENT_OUTPUT_INVALID"
        for _kind, details in events
    )
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
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=budget_check,
            reserve=lambda *_: None,
            reconcile=lambda *_: None,
            record=lambda kind, **details: events.append((kind, details)),
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )
    assert captured.value.code == "AGENT_BUDGET_EXCEEDED"
    assert any(
        details.get("terminal_code") == "AGENT_BUDGET_EXCEEDED"
        for _kind, details in events
    )


@pytest.mark.parametrize(
    "operation",
    [
        "reconcile",
        "generation_record",
        "provider_retry_record",
        "evidence_handling",
        "final_validation",
    ],
)
@pytest.mark.parametrize("failure_kind", ["ordinary", "agent"])
def test_gateway_all_post_interaction_failures_are_sanitized_and_terminalized(
    operation: str,
    failure_kind: str,
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    secret = f"secret-{operation}-{failure_kind}"

    def fail() -> None:
        if failure_kind == "agent":
            raise AgentError("AGENT_BUDGET_EXCEEDED")
        raise RuntimeError(secret)

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    if operation == "provider_retry_record":
        client = _Client(
            [
                anthropic.APITimeoutError(request),
                _Response(
                    "end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))]
                ),
            ]
        )
    elif operation == "evidence_handling":
        client = _Client(
            [
                _Response(
                    "tool_use",
                    [
                        _Block(
                            "tool_use",
                            id="tool-1",
                            name="read_evidence",
                            input={"source_id": "src-1", "block_ids": ["b1"]},
                        )
                    ],
                ),
            ]
        )
    else:
        client = _Client(
            [_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])]
        )

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
            read_evidence=(lambda *_: fail())
            if operation == "evidence_handling"
            else (lambda *_: []),
            validate=(lambda _value: fail())
            if operation == "final_validation"
            else (lambda value: value),
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=(lambda *_: fail())
            if operation == "reconcile"
            else (lambda *_: None),
            record=record,
            active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )

    expected = (
        "AGENT_BUDGET_EXCEEDED" if failure_kind == "agent" else "AGENT_OUTPUT_INVALID"
    )
    assert captured.value.code == expected
    assert any(details.get("terminal_code") == expected for _kind, details in events)
    assert secret not in json.dumps(events)


def test_gateway_post_interaction_fencing_remains_silent() -> None:
    events: list[tuple[str, dict[str, Any]]] = []
    client = _Client(
        [_Response("end_turn", [_Block("text", text=json.dumps(_cpdr_payload()))])]
    )

    with pytest.raises(JobFencedError):
        AnthropicGateway("key", "claude-sonnet-4-6", client=client).run(
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lambda: None,
            reserve=lambda *_: None,
            reconcile=lambda *_: (_ for _ in ()).throw(
                JobFencedError("lost after interaction")
            ),
            record=lambda kind, **details: events.append((kind, details)),
            active_time=lambda _elapsed: None,
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
            system="authority",
            user="brief",
            read_evidence=lambda *_: [],
            validate=lambda value: value,
            lease_check=lease_check,
            reserve=lambda *_: records.append("reserved"),
            reconcile=lambda *_: records.append("reconciled"),
            record=lambda *_args, **_kwargs: records.append("recorded"),
            active_time=lambda _elapsed: records.append("timed"),
            semaphore=threading.BoundedSemaphore(2),
        )
    assert records == []


def test_cpdr_failure_metadata_does_not_persist_secret_body_prompt_or_evidence() -> (
    None
):
    provider = _FakeProvider(
        [],
        counts=[
            AgentError("AGENT_PROVIDER_REJECTED", "secret-provider-body provider-body")
        ],
    )
    ledgers, runtime, approved, _ = _approved_cpdr_case(provider=provider)
    try:
        runtime._execute(approved["id"], "approver")
        failed = ledgers.runs.get_run(approved["id"])
        assert (
            failed is not None and failed["error"]["code"] == "AGENT_PROVIDER_REJECTED"
        )
        persisted = json.dumps(
            {
                "run": failed,
                "events": ledgers.runs.events_after(approved["id"]),
                "audit": ledgers.publications.list_audit(),
            }
        )
        for forbidden in (
            "test-only-key",
            "secret-provider-body",
            "provider-body",
            "Issuer liquidity was USD 100m",
            "CAOS CP-DR RESEARCH AUTHORITY",
        ):
            assert forbidden not in persisted
    finally:
        runtime.close()


def test_cpdr_semantic_gates_reject_locator_gapped_complete_coverage_and_hidden_conflict() -> (
    None
):
    cases = [
        _cpdr_payload(
            evidence=[{**_cpdr_payload()["evidence"][0], "locator": "fabricated"}]
        ),
        _cpdr_payload(
            workstream_findings=[
                {**_cpdr_payload()["workstream_findings"][0], "status": "gapped"}
            ]
        ),
        _cpdr_payload(coverage_score=99),
        _cpdr_payload(
            material_claims=[
                {
                    **_cpdr_payload()["material_claims"][0],
                    "counter_evidence_refs": [
                        {"source_id": "src-1", "block_id": "b00001"}
                    ],
                }
            ]
        ),
    ]
    for value in cases:
        with pytest.raises(CPDRValidationError):
            validate_cpdr_payload(value, _cpdr_host(), {"WS-1"}, _returned_evidence())
