from __future__ import annotations

import copy
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

import pytest
import anthropic
import httpx2
from caos.config import Settings
from caos.methodology.bundle import DeployVBundle
from caos.methodology.cpdr import CPDRPayload, CPDRValidationError, validate_cpdr_payload
from caos.methodology.prompt import compile_cpdr_prompts
from caos.store import JobFencedError, MemoryStore, PostgresStore
from caos.workflows import domain as workflow_domain
from caos.workflows.domain import WorkflowRuntime, _LeaseFence
from caos.workflows.provider import AgentError, AnthropicGateway


DEPLOY_V = Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v"
WORKER_EVENTS = {"run.running", "node.running", "node.succeeded", "node.failed", "run.succeeded", "run.failed"}


def _queued_run(store: MemoryStore, *, dependencies: list[str] | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    case = store.create_case("Lease test", "Issuer", "Testing", "analyst")
    run = store.create_run(case["id"], "analyst", {"nodes": []}, [])
    node = store.add_node(run["id"], case["id"], "CP-TEST", dependencies, 1) if dependencies is not None else None
    store.update_run(run["id"], node_ids=[node["id"]] if node else [], status="queued")
    return store.runs[run["id"]], node


def _claim(store: MemoryStore) -> tuple[str, str]:
    run, _ = _queued_run(store)
    token = store.claim_job(run["id"], "worker")
    assert token is not None
    return run["id"], token


def _artifact(run_id: str, module_id: str = "CP-TEST") -> dict[str, Any]:
    return {"id": f"artifact-{run_id}", "run_id": run_id, "module_id": module_id, "input_fingerprint": "fingerprint"}


def _postgres_url() -> str:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for real PostgreSQL lease tests")
    return database_url


def _postgres_store(application_name: str | None = None) -> PostgresStore:
    database_url = _postgres_url()
    if application_name:
        database_url = f"{database_url}{'&' if '?' in database_url else '?'}application_name={application_name}"
    return PostgresStore(database_url)


def test_memory_lease_renewal_extends_current_token() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)
    prior_expiry = store.jobs[run_id]["lease_until"]

    assert store.renew_job(run_id, token) is True
    assert store.jobs[run_id]["lease_until"] > prior_expiry


def test_memory_lease_renewal_refuses_expired_and_stale_tokens() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)
    store.jobs[run_id]["lease_until"] = time.monotonic() - 1
    expired_at = store.jobs[run_id]["lease_until"]

    assert store.renew_job(run_id, token) is False
    assert store.jobs[run_id]["lease_until"] == expired_at
    replacement = store.claim_job(run_id, "replacement")
    assert replacement is not None
    assert store.renew_job(run_id, token) is False


def test_memory_finish_job_requires_current_lease() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)
    store.jobs[run_id]["lease_until"] = time.monotonic() - 1
    before = copy.deepcopy(store.jobs[run_id])

    store.finish_job(run_id, token)

    assert store.jobs[run_id] == before


def test_memory_finish_job_releases_current_lease_reservation() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)

    store.finish_job(run_id, token)

    assert store.jobs[run_id]["status"] == "finished"
    assert store.jobs[run_id]["budget_reserved"] == 0
    before = copy.deepcopy((store.runs, store.events, store.audit, store.artifacts, store.jobs))
    assert store.job_is_current(run_id, token) is False
    assert store.renew_job(run_id, token) is False
    with pytest.raises(JobFencedError):
        store.update_run_fenced(run_id, token, status="succeeded")
    with pytest.raises(JobFencedError):
        store.emit_fenced(run_id, token, "run.succeeded", {"run_id": run_id})
    with pytest.raises(JobFencedError):
        store.audit_event_fenced(run_id, token, "run.succeeded", "worker")
    with pytest.raises(JobFencedError):
        store.put_artifact_fenced(run_id, token, _artifact(run_id))
    assert (store.runs, store.events, store.audit, store.artifacts, store.jobs) == before


def test_memory_takeover_fences_all_worker_writes() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)
    store.jobs[run_id]["lease_until"] = time.monotonic() - 1
    replacement = store.claim_job(run_id, "replacement")
    assert replacement is not None
    before = copy.deepcopy((store.runs, store.events, store.audit, store.artifacts, store.jobs))

    with pytest.raises(JobFencedError):
        store.update_run_fenced(run_id, token, status="succeeded")
    with pytest.raises(JobFencedError):
        store.emit_fenced(run_id, token, "run.succeeded", {"run_id": run_id})
    with pytest.raises(JobFencedError):
        store.audit_event_fenced(run_id, token, "run.succeeded", "worker")
    with pytest.raises(JobFencedError):
        store.put_artifact_fenced(run_id, token, _artifact(run_id))
    store.finish_job(run_id, token)

    assert (store.runs, store.events, store.audit, store.artifacts, store.jobs) == before


def test_successful_fenced_event_wakes_waiter() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)
    condition = store.event_conditions[run_id]
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(store.wait_for_events, run_id, 0, 1.0)
        deadline = time.monotonic() + 1
        while not condition._waiters and time.monotonic() < deadline:  # type: ignore[attr-defined]
            time.sleep(0.001)
        assert condition._waiters  # type: ignore[attr-defined]
        store.emit_fenced(run_id, token, "run.running", {"run_id": run_id})
        assert waiting.result(timeout=1)[0]["event"] == "run.running"


def test_fenced_audit_records_the_owning_run() -> None:
    store = MemoryStore()
    run_id, token = _claim(store)

    store.audit_event_fenced(run_id, token, "worker.checked", "worker")

    assert store.audit[-1]["run_id"] == run_id


def test_runtime_heartbeat_renews_once_and_is_joined(monkeypatch: pytest.MonkeyPatch) -> None:
    renewed = threading.Event()

    class HeartbeatStore(MemoryStore):
        def __init__(self) -> None:
            super().__init__()
            self.renewals = 0

        def renew_job(self, run_id: str, attempt_token: str) -> bool:
            current = super().renew_job(run_id, attempt_token)
            self.renewals += 1
            renewed.set()
            return current

        def get_run(self, run_id: str) -> dict[str, Any] | None:
            assert renewed.wait(1)
            return super().get_run(run_id)

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

    store = HeartbeatStore()
    run, _ = _queued_run(store)
    runtime = WorkflowRuntime(store, object(), Settings(storage_dir=Path("/tmp/caos-heartbeat"), deploy_v_root=DEPLOY_V))  # type: ignore[arg-type]
    monkeypatch.setattr(workflow_domain, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(workflow_domain.threading, "Thread", TrackingThread)
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert workflow_domain.HEARTBEAT_INTERVAL_SECONDS == 0.01
    assert store.renewals >= 1
    assert len(created) == 1
    assert created[0].joined and not created[0].is_alive()


def test_runtime_heartbeat_is_joined_when_execution_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class ExplodingStore(MemoryStore):
        def update_run_fenced(self, run_id: str, attempt_token: str, **changes: Any) -> None:
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

    store = ExplodingStore()
    run, _ = _queued_run(store)
    runtime = WorkflowRuntime(store, object(), Settings(storage_dir=Path("/tmp/caos-heartbeat-error"), deploy_v_root=DEPLOY_V))  # type: ignore[arg-type]
    monkeypatch.setattr(workflow_domain.threading, "Thread", TrackingThread)
    try:
        with pytest.raises(RuntimeError, match="write failed"):
            runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert len(created) == 1
    assert created[0].joined and not created[0].is_alive()


@pytest.mark.parametrize("renewal_error", [False, True])
def test_runtime_fails_closed_when_heartbeat_loses_lease(monkeypatch: pytest.MonkeyPatch, renewal_error: bool) -> None:
    renewal_attempted = threading.Event()

    class LostLeaseStore(MemoryStore):
        def renew_job(self, run_id: str, attempt_token: str) -> bool:
            renewal_attempted.set()
            if renewal_error:
                raise RuntimeError("renewal failed")
            return False

        def get_run(self, run_id: str) -> dict[str, Any] | None:
            assert renewal_attempted.wait(1)
            return super().get_run(run_id)

    store = LostLeaseStore()
    run, _ = _queued_run(store)
    runtime = WorkflowRuntime(store, object(), Settings(storage_dir=Path("/tmp/caos-lost-lease"), deploy_v_root=DEPLOY_V))  # type: ignore[arg-type]
    monkeypatch.setattr(workflow_domain, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert store.runs[run["id"]]["status"] == "running"
    assert [event["event"] for event in store.events[run["id"]]] == ["run.running"]
    assert store.jobs[run["id"]]["status"] == "running"
    assert store.jobs[run["id"]]["budget_reserved"] == 1


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
    class LifecycleStore(MemoryStore):
        def emit(self, run_id: str, event: str, data: dict[str, Any]) -> None:
            if event in WORKER_EVENTS:
                raise AssertionError(f"worker event escaped fencing: {event}")
            super().emit(run_id, event, data)

    class Runtime(WorkflowRuntime):
        def _build_artifact_with_slot(self, run: dict[str, Any], node: dict[str, Any], actor: str, fenced_call: Any | None = None, lease_check: Any | None = None) -> dict[str, Any]:
            if failure:
                raise RuntimeError("node failed")
            return _artifact(run["id"], node["module_id"])

    store = LifecycleStore()
    run, _ = _queued_run(store, dependencies=[])
    runtime = Runtime(store, object(), Settings(storage_dir=Path("/tmp/caos-lifecycle"), deploy_v_root=DEPLOY_V))  # type: ignore[arg-type]
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert [event["event"] for event in store.events[run["id"]]] == expected


@pytest.mark.parametrize("blocked", [False, True])
def test_expired_worker_cannot_emit_terminal_lifecycle_event(blocked: bool) -> None:
    class ExpiringStore(MemoryStore):
        def update_run_fenced(self, run_id: str, attempt_token: str, **changes: Any) -> None:
            if changes.get("status") in {"succeeded", "failed"}:
                with self.lock:
                    self.jobs[run_id]["lease_until"] = time.monotonic() - 1
            super().update_run_fenced(run_id, attempt_token, **changes)

    store = ExpiringStore()
    run, _ = _queued_run(store, dependencies=["missing"] if blocked else None)
    runtime = WorkflowRuntime(store, object(), Settings(storage_dir=Path("/tmp/caos-expired-worker"), deploy_v_root=DEPLOY_V))  # type: ignore[arg-type]
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    events = [event["event"] for event in store.events[run["id"]]]
    assert events == ["run.running"]


def test_postgres_lease_renewal_refuses_stale_and_expired_tokens() -> None:
    store = _postgres_store()
    run_id, token = _claim(store)

    assert store.renew_job(run_id, "stale-token") is False
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run_id,))
        connection.commit()
    assert store.renew_job(run_id, token) is False
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT lease_until <= now() FROM jobs WHERE run_id = %s", (run_id,))
            assert cursor.fetchone() == (True,)


def test_postgres_takeover_fences_all_worker_writes() -> None:
    store = _postgres_store()
    run_id, token = _claim(store)
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run_id,))
        connection.commit()
    replacement = store.claim_job(run_id, "replacement")
    assert replacement is not None
    before = copy.deepcopy((store.runs, store.events, store.audit, store.artifacts, store.jobs))

    with pytest.raises(JobFencedError):
        store.update_run_fenced(run_id, token, status="succeeded")
    with pytest.raises(JobFencedError):
        store.emit_fenced(run_id, token, "run.succeeded", {"run_id": run_id})
    with pytest.raises(JobFencedError):
        store.audit_event_fenced(run_id, token, "run.succeeded", "worker")
    with pytest.raises(JobFencedError):
        store.put_artifact_fenced(run_id, token, _artifact(run_id))
    store.finish_job(run_id, token)

    assert (store.runs, store.events, store.audit, store.artifacts, store.jobs) == before
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT state, budget_reserved, attempt_token FROM jobs WHERE run_id = %s", (run_id,))
            assert cursor.fetchone() == ("claimed", 1, replacement)


def test_postgres_finish_job_requires_current_lease() -> None:
    store = _postgres_store()
    run_id, token = _claim(store)
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run_id,))
        connection.commit()

    store.finish_job(run_id, token)

    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT state, budget_reserved, lease_until <= now() FROM jobs WHERE run_id = %s", (run_id,))
            assert cursor.fetchone() == ("claimed", 1, True)
    assert store.jobs[run_id]["status"] == "running"


def test_postgres_finish_job_releases_current_lease_reservation() -> None:
    store = _postgres_store()
    run_id, token = _claim(store)

    store.finish_job(run_id, token)

    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT state, budget_reserved, lease_until FROM jobs WHERE run_id = %s", (run_id,))
            assert cursor.fetchone() == ("succeeded", 0, None)
    assert store.jobs[run_id]["status"] == "finished"


def test_postgres_lease_renewal_uses_database_time_after_row_lock() -> None:
    database_url = _postgres_url()
    application_name = f"caos-lease-renew-{uuid.uuid4().hex}"
    store = _postgres_store(application_name)
    run_id, token = _claim(store)
    started = threading.Event()

    with store._psycopg.connect(database_url) as locking_connection:
        with locking_connection.cursor() as cursor:
            cursor.execute("SELECT id FROM jobs WHERE run_id = %s FOR UPDATE", (run_id,))

            def renew() -> bool:
                started.set()
                return store.renew_job(run_id, token)

            with ThreadPoolExecutor(max_workers=1) as pool:
                waiting = pool.submit(renew)
                assert started.wait(1)
                observed: tuple[str, str, str, str] | None = None
                deadline = time.monotonic() + 1
                with store._psycopg.connect(database_url, autocommit=True) as observer:
                    while observed is None and time.monotonic() < deadline:
                        with observer.cursor() as observer_cursor:
                            observer_cursor.execute(
                                "SELECT state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE application_name = %s AND state = 'active' AND wait_event_type = 'Lock' AND query LIKE %s AND query LIKE %s AND query LIKE %s",
                                (application_name, "UPDATE jobs SET lease_until = now() + interval '60 seconds'%", "%attempt_token%", "%lease_until > now()%"),
                            )
                            observed = observer_cursor.fetchone()
                        if observed is None:
                            time.sleep(0.01)
                if observed is None:
                    locking_connection.rollback()
                    waiting.result(timeout=1)
                    pytest.fail("renewal UPDATE was not observed waiting on the locked job row")
                assert observed[0:2] == ("active", "Lock")
                assert "UPDATE jobs SET lease_until = now() + interval '60 seconds'" in observed[3]
                assert "attempt_token" in observed[3] and "lease_until > now()" in observed[3]
                with pytest.raises(TimeoutError):
                    waiting.result(timeout=0.1)
                cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run_id,))
                locking_connection.commit()
                assert waiting.result(timeout=1) is False

    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT lease_until <= now() FROM jobs WHERE run_id = %s", (run_id,))
            assert cursor.fetchone() == (True,)


def test_memory_research_plan_pause_and_exact_approval_smoke() -> None:
    store = MemoryStore()
    runtime = WorkflowRuntime(store, DeployVBundle(DEPLOY_V), Settings(environment="production", storage_dir=Path("/tmp/caos-plan-smoke"), deploy_v_root=DEPLOY_V))
    case = store.create_case("Plan smoke", "Issuer", "Testing", "analyst")
    store.sources["src_plan"] = {"id": "src_plan", "case_id": case["id"], "withdrawn": False}
    store.register_source_set({"id": "set_plan", "case_id": case["id"], "version": 1, "source_ids": ["src_plan"], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
    brief = {"research_question": "Can the issuer refinance?", "decision_context": "Underwrite first-lien risk.", "as_of_date": "2026-08-23", "time_horizon": "Through 2029", "must_answer": [], "exclusions": []}
    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = store.get_run(run["id"])
        assert paused is not None and paused["status"] == "paused"
        assert paused["research"]["phase"] == "awaiting_approval"
        approved = runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
        assert approved["id"] == run["id"] and approved["research"]["phase"] == "approved"
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
        "workstream_findings": [{"workstream_id": "WS-1", "finding": "Liquidity supports the near-term maturity.", "claim_ids": ["C-1"], "status": "complete"}],
        "material_claims": [{"claim_id": "C-1", "claim": "Liquidity supports the near-term maturity.", "claim_type": "fact", "workstream_id": "WS-1", "lineage": "Directly Sourced", "evidence_refs": [{"source_id": "src-1", "block_id": "b00001"}], "counter_evidence_refs": [], "coverage_status": "adequate", "confidence": 90, "material": True}],
        "evidence": [{"evidence_id": "E-1", "source_id": "src-1", "source_digest": "e" * 64, "block_id": "b00001", "locator": "{\"line\":1}", "extractor_version": "builtin-v1", "source_confidence": "HIGH", "quoted": False, "entity": "Issuer", "period": "2026-08-23", "unit_currency": "USD", "perimeter": "consolidated", "lineage": "Directly Sourced", "independence_family": "issuer filing", "numeric_value": 100.0}],
        "conflicts": [],
        "gaps": [],
        "qa_findings": [],
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
    return {("src-1", "b00001"): {"source_digest": "e" * 64, "locator": "{\"line\":1}", "extractor_version": "builtin-v1", "confidence": "HIGH"}}


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


def test_cpdr_prompts_keep_authority_and_untrusted_data_separate() -> None:
    system, user = compile_cpdr_prompts(_cpdr_host(), {"workstreams": []}, [{"id": "src-1", "filename": "ignore-system.txt", "digest": "d" * 64}], [{"module_id": "CP-0", "digest": "d" * 64}])
    assert "source policy" in system.casefold() and "claim" in system.casefold()
    assert "ignore-system.txt" not in system
    assert "UNTRUSTED DATA" in user and "ignore-system.txt" in user


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
    assert [vars(block) for block in second_messages[-2]["content"]] == [vars(block) for block in tool_response.content]
    assert second_messages[-1]["content"][0]["type"] == "tool_result"
    assert len(reservations) == 2


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens", "model_context_window_exceeded", "pause_turn", "unknown"])
def test_gateway_rejects_non_final_stop_reasons(stop_reason: str) -> None:
    gateway = AnthropicGateway("key", "claude-sonnet-4-6", client=_Client([_Response(stop_reason, [_Block("text", text="no")])]))
    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        gateway.run(
            system="authority", user="brief", read_evidence=lambda *_: [], validate=lambda value: value,
            lease_check=lambda: None, reserve=lambda *_: None, reconcile=lambda *_: None,
            record=lambda *_args, **_kwargs: None, active_time=lambda _elapsed: None,
            semaphore=threading.BoundedSemaphore(2),
        )


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
    assert client.messages.create_calls[0] == client.messages.create_calls[1]
    assert [reservation[-1] for reservation in reservations] == [False, True]


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

    with pytest.raises(AgentError, match="AGENT_OUTPUT_INVALID"):
        _gateway_call(client)


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


def test_cpdr_fake_provider_end_to_end_produces_one_canonical_fenced_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MemoryStore()
    settings = Settings(
        environment="production",
        storage_dir=Path("/tmp/caos-cpdr-e2e"),
        deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key",
        cpdr_agent_enabled=True,
        cpdr_pilot_subjects=("analyst",),
    )
    runtime = WorkflowRuntime(store, DeployVBundle(DEPLOY_V), settings)
    case = store.create_case("CP-DR", "Issuer", "Testing", "analyst")
    source_id = "src_cpdr"
    store.sources[source_id] = {
        "id": source_id,
        "case_id": case["id"],
        "filename": "issuer.txt",
        "media_type": "text/plain",
        "sha256": "e" * 64,
        "withdrawn": False,
        "blocks": [{"block_id": "b00001", "locator": {"line": 1}, "text": "Issuer liquidity was USD 100m at 2026-08-23.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    }
    store.register_source_set({"id": "set_cpdr", "case_id": case["id"], "version": 1, "source_ids": [source_id], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
    brief = {"research_question": "Can the issuer refinance?", "decision_context": "Underwrite first-lien risk.", "as_of_date": "2026-08-23", "time_horizon": "Through 2029", "must_answer": [], "exclusions": []}
    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = store.get_run(run["id"])
        assert paused is not None and paused["status"] == "paused"
        runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
        approved = store.get_run(run["id"])
        assert approved is not None
        cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
        cp0 = store.get_artifact(cp0_node["artifact_id"])
        assert cp0 is not None
        workstreams = approved["research"]["proposed_plan"]["workstreams"]
        final = _cpdr_payload(
            run_id=run["id"],
            case_id=case["id"],
            source_set_id="set_cpdr",
            approved_plan_hash=approved["research"]["approved_plan_hash"],
            upstream_digests=[cp0["digest"]],
            scope_key=case["id"].replace("_", "-"),
            workstream_findings=[
                {"workstream_id": item["id"], "finding": "The supplied evidence resolves this approved lane." if index == 0 else "No additional material claim was required for this lane.", "claim_ids": ["C-1"] if index == 0 else [], "status": "complete"}
                for index, item in enumerate(workstreams)
            ],
            material_claims=[{**_cpdr_payload()["material_claims"][0], "workstream_id": workstreams[0]["id"], "evidence_refs": [{"source_id": source_id, "block_id": "b00001"}]}],
            evidence=[{**_cpdr_payload()["evidence"][0], "source_id": source_id, "block_id": "b00001"}],
        )
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        client = _Client([
            anthropic.APITimeoutError(request),
            _Response("tool_use", [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})]),
            _Response("end_turn", [_Block("text", text="{}")], request_id="req-invalid"),
            _Response("end_turn", [_Block("text", text=json.dumps(final))], request_id="req-final"),
        ])
        monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AnthropicGateway("test", settings.anthropic_model, client=client))

        runtime._execute(run["id"], "approver")

        completed = store.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded", completed and completed.get("error")
        cpdr_node = next(node for node in completed["nodes"] if node["module_id"] == "CP-DR")
        artifact = store.get_artifact(cpdr_node["artifact_id"])
        assert artifact is not None and artifact["filename"].endswith("_CP-DR_20260823.md")
        assert [line[3:] for line in artifact["markdown"].splitlines() if line.startswith("## ")] == ["Audit Summary", "Analysis", "Evidence Trace", "Source Registry", "Gaps & Conflicts", "QA Validation"]
        assert artifact["markdown"].split("## Analysis", 1)[1].lstrip().startswith("### Executive answer")
        assert len([item for item in store.artifacts.values() if item["run_id"] == run["id"] and item["module_id"] == "CP-DR"]) == 1
        assert completed["research"]["budget_used"]["provider_retries"] == 1
        assert completed["research"]["budget_used"]["repairs"] == 1
        assert completed["research"]["budget_used"]["turns"] == 4
        snapshot = runtime.accept_run(case["id"], run["id"], "analyst")
        assert any(item["module_id"] == "CP-DR" for item in snapshot["artifacts"])
        persisted = json.dumps({"run": completed, "events": store.events[run["id"]], "audit": store.audit})
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
    store = MemoryStore()
    runtime = WorkflowRuntime(store, DeployVBundle(DEPLOY_V), settings)
    case = store.create_case("CP-DR", "Issuer", "Testing", "analyst")
    store.sources["src"] = {"id": "src", "case_id": case["id"], "withdrawn": False, "blocks": [{"block_id": "b00001", "locator": {"line": 1}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}]}
    store.register_source_set({"id": "set", "case_id": case["id"], "version": 1, "source_ids": ["src"], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
    brief = {"research_question": "Question", "decision_context": "Context", "as_of_date": "2026-08-23", "time_horizon": "2029", "must_answer": [], "exclusions": []}
    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = store.get_run(run["id"])
        assert paused is not None
        runtime.approve_research_plan(run["id"], "analyst", paused["research"]["proposed_plan_hash"])
        runtime._execute(run["id"], "analyst")
        failed = store.get_run(run["id"])
        assert failed is not None and failed["error"]["code"] == expected
        assert not any(item["module_id"] == "CP-DR" for item in store.artifacts.values())
    finally:
        runtime.close()


def _approved_cpdr_case() -> tuple[MemoryStore, WorkflowRuntime, dict[str, Any], str]:
    store = MemoryStore()
    settings = Settings(
        environment="production",
        storage_dir=Path("/tmp/caos-cpdr-matrix"),
        deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key",
        cpdr_agent_enabled=True,
        cpdr_pilot_subjects=("analyst",),
    )
    runtime = WorkflowRuntime(store, DeployVBundle(DEPLOY_V), settings)
    case = store.create_case("CP-DR matrix", "Issuer", "Testing", "analyst")
    source_id = "src_matrix"
    store.sources[source_id] = {
        "id": source_id,
        "case_id": case["id"],
        "filename": "issuer.txt",
        "media_type": "text/plain",
        "sha256": "e" * 64,
        "withdrawn": False,
        "blocks": [{"block_id": "b00001", "locator": {"line": 1}, "text": "Issuer liquidity was USD 100m at 2026-08-23.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    }
    store.register_source_set({"id": "set_matrix", "case_id": case["id"], "version": 1, "source_ids": [source_id], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
    brief = {"research_question": "Can the issuer refinance?", "decision_context": "Underwrite risk.", "as_of_date": "2026-08-23", "time_horizon": "Through 2029", "must_answer": [], "exclusions": []}
    run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
    runtime._execute(run["id"], "analyst")
    paused = store.get_run(run["id"])
    assert paused is not None
    runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
    approved = store.get_run(run["id"])
    assert approved is not None
    return store, runtime, approved, source_id


def _approved_final(store: MemoryStore, approved: dict[str, Any], source_id: str) -> dict[str, Any]:
    cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
    cp0 = store.get_artifact(cp0_node["artifact_id"])
    assert cp0 is not None
    workstreams = approved["research"]["proposed_plan"]["workstreams"]
    return _cpdr_payload(
        run_id=approved["id"],
        case_id=approved["case_id"],
        source_set_id="set_matrix",
        approved_plan_hash=approved["research"]["approved_plan_hash"],
        upstream_digests=[cp0["digest"]],
        scope_key=approved["case_id"].replace("_", "-"),
        workstream_findings=[
            {"workstream_id": item["id"], "finding": "The lane is supported." if index == 0 else "No additional material claim was required.", "claim_ids": ["C-1"] if index == 0 else [], "status": "complete"}
            for index, item in enumerate(workstreams)
        ],
        material_claims=[{**_cpdr_payload()["material_claims"][0], "workstream_id": workstreams[0]["id"], "evidence_refs": [{"source_id": source_id, "block_id": "b00001"}]}],
        evidence=[{**_cpdr_payload()["evidence"][0], "source_id": source_id}],
    )


@pytest.mark.parametrize(
    "mutation",
    ["plan_hash", "model", "source_set", "cp0"],
)
def test_cpdr_authority_mismatches_fail_closed(mutation: str) -> None:
    store, runtime, approved, _ = _approved_cpdr_case()
    try:
        if mutation == "plan_hash":
            store.runs[approved["id"]]["research"]["approved_plan_hash"] = "sha256:" + "b" * 64
        elif mutation == "model":
            store.runs[approved["id"]]["research"]["model"] = "other-model"
        elif mutation == "source_set":
            store.source_sets[approved["case_id"]] = {**store.source_sets[approved["case_id"]], "id": "changed", "version": 2}
        else:
            cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
            store.artifacts[cp0_node["artifact_id"]]["payload"]["status"] = "BLOCKED"
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_AUTHORITY_MISMATCH"
        assert not any(item["module_id"] == "CP-DR" for item in store.artifacts.values())
    finally:
        runtime.close()


def test_cpdr_reclaimed_unresolved_inflight_fails_closed() -> None:
    store, runtime, approved, _ = _approved_cpdr_case()
    try:
        store.runs[approved["id"]]["research"]["inflight_request_digest"] = "unknown-spend"
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
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
def test_cpdr_evidence_reads_enforce_case_pin_withdrawal_and_block_identity(monkeypatch: pytest.MonkeyPatch, mode: str, expected: str) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    tool_source = source_id
    tool_block = "b00001"
    if mode == "cross_case":
        store.sources[source_id]["case_id"] = "other-case"
    elif mode == "unpinned":
        tool_source = "src_unpinned"
        store.sources[tool_source] = {**store.sources[source_id], "id": tool_source}
    elif mode == "withdrawn":
        store.sources[source_id]["withdrawn"] = True
    elif mode == "absent_block":
        tool_block = "missing"
    block_ids = [tool_block, tool_block] if mode == "duplicate_block" else [tool_block]
    client = _Client([_Response("tool_use", [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": tool_source, "block_ids": block_ids})])])
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AnthropicGateway("test", "claude-sonnet-4-6", client=client))
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == expected
    finally:
        runtime.close()


@pytest.mark.parametrize("budget", ["turns", "input_tokens", "output_tokens", "active_minutes", "evidence_reads", "evidence_bytes"])
def test_cpdr_runwide_budget_ceilings_fail_before_overspend(monkeypatch: pytest.MonkeyPatch, budget: str) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    store.runs[approved["id"]]["research"]["budget_limits"][budget] = 0 if budget != "evidence_bytes" else 1
    if budget in {"evidence_reads", "evidence_bytes"}:
        response = _Response("tool_use", [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})])
    else:
        response = _Response("end_turn", [_Block("text", text="{}")])
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AnthropicGateway("test", "claude-sonnet-4-6", client=_Client([response])))
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert not any(item["module_id"] == "CP-DR" for item in store.artifacts.values())
    finally:
        runtime.close()


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


def test_cpdr_failure_metadata_does_not_persist_secret_body_prompt_or_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, _ = _approved_cpdr_case()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    failure = anthropic.AuthenticationError("secret-provider-body", response=httpx2.Response(401, request=request), body={"secret": "provider-body"})
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AnthropicGateway("test-only-key", "claude-sonnet-4-6", client=_Client([failure])))
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_PROVIDER_REJECTED"
        persisted = json.dumps({"run": failed, "events": store.events[approved["id"]], "audit": store.audit})
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
