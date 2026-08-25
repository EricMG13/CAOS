from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
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
from caos.contracts import digest
from caos.artifacts.domain import build_snapshot_payload, cpdr_artifact_is_valid, create_note, promote_note
from caos.methodology.bundle import DeployVBundle, MethodologyError
from caos.methodology.cpdr import CPDRPayload, CPDRValidationError, confidence_inputs, validate_cpdr_payload
from caos.methodology.prompt import compile_cpdr_prompts
from caos.store import JobFencedError, MemoryStore, PostgresStore
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


def test_memory_takeover_recovers_running_node_and_atomic_completion() -> None:
    store = MemoryStore()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    source_set = {"id": f"set-{run['id']}", "case_id": run["case_id"], "version": 1, "source_ids": []}
    store.register_source_set(source_set)
    store.runs[run["id"]]["plan"]["source_set_id"] = source_set["id"]
    store.update_run(run["id"], status="running")
    store.update_node(node["id"], status="running", attempt=1)
    first = store.claim_job(run["id"], "first")
    assert first is not None
    store.jobs[run["id"]]["lease_until"] = time.monotonic() - 1

    replacement = store.claim_job(run["id"], "replacement")

    assert replacement is not None
    assert store.nodes[node["id"]]["status"] == "pending"
    artifact = store.complete_node_fenced(run["id"], replacement, node["id"], _artifact(run["id"]), None)
    assert store.nodes[node["id"]] == {**store.nodes[node["id"]], "status": "succeeded", "artifact_id": artifact["id"], "error": None}
    assert store.artifacts[artifact["id"]]["input_fingerprint"] == "fingerprint"
    retry = _artifact(run["id"])
    retry["id"] = "art-retry"
    assert store.complete_node_fenced(run["id"], replacement, node["id"], retry, None)["id"] == artifact["id"]
    assert len(store.artifacts) == 1


def test_memory_atomic_completion_rolls_back_artifact_node_and_research() -> None:
    class FailingStore(MemoryStore):
        fail_completion = False

        def persist(self) -> None:
            if self.fail_completion:
                raise RuntimeError("completion persistence failed")

    store = FailingStore()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    store.runs[run["id"]]["research"] = {"phase": "researching"}
    token = store.claim_job(run["id"], "worker")
    assert token is not None
    before = copy.deepcopy((store.artifacts, store.nodes[node["id"]], store.runs[run["id"]]))
    store.fail_completion = True

    with pytest.raises(RuntimeError, match="completion persistence failed"):
        store.complete_node_fenced(run["id"], token, node["id"], _artifact(run["id"]), {"phase": "complete"})

    assert (store.artifacts, store.nodes[node["id"]], store.runs[run["id"]]) == before


def test_replacement_finishes_run_after_atomic_completion_preceded_terminal_events() -> None:
    store = MemoryStore()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    token = store.claim_job(run["id"], "first")
    assert token is not None
    store.complete_node_fenced(run["id"], token, node["id"], _artifact(run["id"]), None)
    store.finish_job(run["id"], token)
    runtime = WorkflowRuntime(store, object(), Settings(environment="production", storage_dir=Path("/tmp/caos-terminal-recovery"), deploy_v_root=DEPLOY_V))  # type: ignore[arg-type]
    try:
        runtime._execute(run["id"], "replacement")
        completed = store.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert [item["event"] for item in store.events[run["id"]]][-1] == "run.succeeded"
    finally:
        runtime.close()


@pytest.mark.parametrize("forgery", ["running_node", "missing_artifact", "wrong_artifact"])
def test_snapshot_payload_rejects_forged_succeeded_run(forgery: str) -> None:
    store = MemoryStore()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    source_set = {"id": f"set-{run['id']}", "case_id": run["case_id"], "version": 1, "source_ids": []}
    store.register_source_set(source_set)
    store.runs[run["id"]]["plan"]["source_set_id"] = source_set["id"]
    artifact = _artifact(run["id"])
    store.artifacts[artifact["id"]] = artifact
    store.nodes[node["id"]].update(status="succeeded", artifact_id=artifact["id"])
    store.runs[run["id"]]["status"] = "succeeded"
    if forgery == "running_node":
        store.nodes[node["id"]]["status"] = "running"
    elif forgery == "missing_artifact":
        store.artifacts.pop(artifact["id"])
    else:
        store.artifacts[artifact["id"]]["module_id"] = "OTHER"

    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        build_snapshot_payload(store, store.get_run(run["id"]) or {})


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
            if changes.get("status") == "failed":
                with self.lock:
                    self.jobs[run_id]["lease_until"] = time.monotonic() - 1
            super().update_run_fenced(run_id, attempt_token, **changes)

        def finalize_run_success_fenced(
            self, run_id: str, attempt_token: str, research: dict[str, Any] | None, event_data: dict[str, Any],
        ) -> None:
            with self.lock:
                self.jobs[run_id]["lease_until"] = time.monotonic() - 1
            super().finalize_run_success_fenced(run_id, attempt_token, research, event_data)

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


def test_postgres_takeover_recovers_running_node_and_completion_is_durable() -> None:
    store = _postgres_store()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    store.update_run(run["id"], status="running")
    store.update_node(node["id"], status="running", attempt=1)
    first = store.claim_job(run["id"], "first")
    assert first is not None
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run["id"],))
        connection.commit()

    replacement = store.claim_job(run["id"], "replacement")
    assert replacement is not None
    assert store.nodes[node["id"]]["status"] == "pending"
    artifact = store.complete_node_fenced(run["id"], replacement, node["id"], _artifact(run["id"]), None)
    retry = _artifact(run["id"])
    retry["id"] = "art-retry"
    assert store.complete_node_fenced(run["id"], replacement, node["id"], retry, None)["id"] == artifact["id"]

    reloaded = PostgresStore(store._dsn)
    restored = reloaded.get_run(run["id"])
    assert restored is not None
    restored_node = next(item for item in restored["nodes"] if item["id"] == node["id"])
    assert restored_node["status"] == "succeeded" and restored_node["artifact_id"] == artifact["id"]
    assert reloaded.get_artifact(artifact["id"]) is not None
    assert len([item for item in reloaded.artifacts.values() if item.get("run_id") == run["id"]]) == 1


def test_postgres_cross_process_takeover_adopts_authoritative_state_before_recovery() -> None:
    first = _postgres_store()
    run, node = _queued_run(first, dependencies=[])
    assert node is not None
    replacement_process = PostgresStore(first._dsn)
    token = first.claim_job(run["id"], "first-process")
    assert token is not None
    authoritative_plan = {"nodes": [], "authority_marker": "current-database-state"}
    authoritative_error = {"code": "AUTHORITY_SENTINEL", "message": "current error"}
    first.update_run_fenced(
        run["id"], token, status="running", plan=authoritative_plan,
        accepted_snapshot_id="snap-authoritative", error=authoritative_error,
    )
    first.update_node_fenced(run["id"], token, node["id"], status="running", attempt=1)
    with first._psycopg.connect(first._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run["id"],))
        connection.commit()

    replacement = replacement_process.claim_job(run["id"], "replacement-process")

    assert replacement is not None
    recovered = replacement_process.get_run(run["id"])
    recovered_node = next(item for item in recovered["nodes"] if item["id"] == node["id"]) if recovered else None
    assert recovered_node is not None and recovered_node["status"] == "pending"
    with replacement_process._psycopg.connect(replacement_process._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status, error, plan, accepted_snapshot_id FROM runs WHERE id = %s", (run["id"],))
            normalized = cursor.fetchone()
    assert normalized == ("running", authoritative_error, authoritative_plan, "snap-authoritative")
    artifact = replacement_process.complete_node_fenced(run["id"], replacement, node["id"], _artifact(run["id"]), None)
    durable = PostgresStore(first._dsn).get_run(run["id"])
    durable_node = next(item for item in durable["nodes"] if item["id"] == node["id"]) if durable else None
    assert durable_node is not None and durable_node["status"] == "succeeded" and durable_node["artifact_id"] == artifact["id"]
    with replacement_process._psycopg.connect(replacement_process._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status, error, plan, accepted_snapshot_id FROM runs WHERE id = %s", (run["id"],))
            normalized_after_completion = cursor.fetchone()
    assert normalized_after_completion == normalized


def _assert_normalized_run_matches_authoritative(store: PostgresStore, run_id: str) -> None:
    authoritative = store.get_run(run_id)
    assert authoritative is not None
    with store._psycopg.connect(store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT case_id, status, error, plan, accepted_snapshot_id, created_by, created_at "
                "FROM runs WHERE id = %s",
                (run_id,),
            )
            row = cursor.fetchone()
    assert row is not None
    assert row[:6] == (
        authoritative["case_id"],
        authoritative["status"],
        authoritative.get("error"),
        authoritative["plan"],
        authoritative.get("accepted_snapshot_id"),
        authoritative["created_by"],
    )
    assert row[6].isoformat() == authoritative["created_at"]


def test_postgres_normalized_run_tracks_takeover_completion_updates_finalization_and_acceptance() -> None:
    first = _postgres_store()
    run, node = _queued_run(first, dependencies=[])
    assert node is not None
    source_set = {
        "id": f"set-{run['id']}", "case_id": run["case_id"], "version": 1, "source_ids": [],
        "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00",
    }
    first.register_source_set(source_set)
    initial_plan = {"nodes": [], "source_set_id": source_set["id"], "marker": "initial"}
    first.update_run(run["id"], plan=initial_plan, status="queued", error=None)
    replacement_process = PostgresStore(first._dsn)
    token = first.claim_job(run["id"], "first-normalized")
    assert token is not None
    first.update_run_fenced(
        run["id"], token, status="running", plan={**initial_plan, "marker": "authoritative"},
        error={"code": "RUNNING_SENTINEL", "message": "current"},
    )
    first.update_node_fenced(run["id"], token, node["id"], status="running", attempt=1)
    with first._psycopg.connect(first._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s", (run["id"],))
        connection.commit()

    replacement = replacement_process.claim_job(run["id"], "replacement-normalized")
    assert replacement is not None
    _assert_normalized_run_matches_authoritative(replacement_process, run["id"])

    payload = {"result": "durable"}
    artifact = {
        **_artifact(run["id"]), "case_id": run["case_id"], "payload": payload, "digest": digest(payload),
    }
    replacement_process.complete_node_fenced(run["id"], replacement, node["id"], artifact, None)
    _assert_normalized_run_matches_authoritative(replacement_process, run["id"])

    final_plan = {**initial_plan, "marker": "final-authoritative"}
    replacement_process.update_run_fenced(
        run["id"], replacement, status="running", plan=final_plan,
        error={"code": "FINAL_SENTINEL", "message": "bounded"},
    )
    _assert_normalized_run_matches_authoritative(replacement_process, run["id"])

    replacement_process.finalize_run_success_fenced(
        run["id"], replacement, None, {"run_id": run["id"]},
    )
    _assert_normalized_run_matches_authoritative(replacement_process, run["id"])

    runtime = WorkflowRuntime(
        replacement_process, object(),
        Settings(environment="production", storage_dir=Path("/tmp/caos-normalized-run"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    try:
        snapshot = runtime.accept_run(run["case_id"], run["id"], "analyst")
    finally:
        runtime.close()
    assert snapshot["run_id"] == run["id"]
    _assert_normalized_run_matches_authoritative(replacement_process, run["id"])


def test_postgres_atomic_completion_rolls_back_artifact_node_and_research(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _postgres_store()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    store.update_run(run["id"], research={"phase": "researching"})
    token = store.claim_job(run["id"], "worker")
    assert token is not None

    def fail_persist(_connection: Any) -> Any:
        raise RuntimeError("completion transaction failed")

    monkeypatch.setattr(store, "_persist_connection", fail_persist)
    with pytest.raises(RuntimeError, match="completion transaction failed"):
        store.complete_node_fenced(run["id"], token, node["id"], _artifact(run["id"]), {"phase": "complete"})

    reloaded = PostgresStore(store._dsn)
    restored = reloaded.get_run(run["id"])
    assert restored is not None and restored["research"]["phase"] == "researching"
    restored_node = next(item for item in restored["nodes"] if item["id"] == node["id"])
    assert restored_node["status"] != "succeeded" and restored_node.get("artifact_id") is None
    assert not any(item.get("run_id") == run["id"] for item in reloaded.artifacts.values())


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
    store = MemoryStore()
    case = store.create_case("Origin", "Issuer", "Testing", "analyst")
    note = create_note(store, case["id"], "analyst", "canonical note bytes")
    promoted = promote_note(store, case["id"], note["id"], "analyst")
    source = store.sources[promoted["promoted_source_id"]]
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
    store.sources["src_cpdr_2"] = {
        "id": "src_cpdr_2", "case_id": case["id"], "filename": "facility.txt", "media_type": "text/plain",
        "sha256": "f" * 64, "withdrawn": False,
        "blocks": [{"block_id": "b00002", "locator": {"line": 2}, "text": "Facility availability extends through 2029.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    }
    store.register_source_set({"id": "set_cpdr", "case_id": case["id"], "version": 1, "source_ids": [source_id, "src_cpdr_2"], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
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
            material_claims=[{**_cpdr_payload()["material_claims"][0], "workstream_id": workstreams[0]["id"], "evidence_refs": [{"source_id": source_id, "block_id": "b00001"}, {"source_id": "src_cpdr_2", "block_id": "b00002"}]}],
            evidence=[
                {**_cpdr_payload()["evidence"][0], "source_id": source_id, "block_id": "b00001"},
                {**_cpdr_payload()["evidence"][0], "evidence_id": "E-2", "source_id": "src_cpdr_2", "source_digest": "f" * 64, "block_id": "b00002", "locator": "{\"line\":2}"},
            ],
        )
        provider = _FakeProvider([
            AgentError("AGENT_PROVIDER_TIMEOUT"),
            ProviderMessage(
                content=[ProviderBlock(type="tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})],
                stop_reason="tool_use", usage=ProviderUsage(20, 30),
            ),
            ProviderMessage(
                content=[ProviderBlock(type="tool_use", id="tool-2", name="read_evidence", input={"source_id": "src_cpdr_2", "block_ids": ["b00002"]})],
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
        monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AgentLoop(provider))

        runtime._execute(run["id"], "approver")

        completed = store.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded", completed and completed.get("error")
        cpdr_node = next(node for node in completed["nodes"] if node["module_id"] == "CP-DR")
        artifact = store.get_artifact(cpdr_node["artifact_id"])
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
        assert len([item for item in store.artifacts.values() if item["run_id"] == run["id"] and item["module_id"] == "CP-DR"]) == 1
        assert completed["research"]["budget_used"]["provider_retries"] == 1
        assert completed["research"]["budget_used"]["repairs"] == 1
        assert completed["research"]["budget_used"]["turns"] == 5
        original_artifact = copy.deepcopy(store.artifacts[artifact["id"]])
        mutations = [
            lambda item: item["payload"]["host_confidence"].update(confidence_score=99),
            lambda item: item["payload"]["canonical_output"].update(filename="forged.md"),
            lambda item: item.update(markdown=item["markdown"] + "\nforged"),
            lambda item: item["payload"]["methodology"].update(approved_plan_hash="sha256:forged"),
            lambda item: item["payload"]["source_set"].update(version=999),
            lambda item: item["payload"].update(upstream_artifacts=[]),
        ]
        for mutate in mutations:
            store.artifacts[artifact["id"]] = copy.deepcopy(original_artifact)
            mutate(store.artifacts[artifact["id"]])
            with pytest.raises(ValueError, match="RUN_NOT_READY"):
                build_snapshot_payload(store, store.get_run(run["id"]) or {}, runtime.bundle)
        store.artifacts[artifact["id"]] = original_artifact
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


def _approved_cpdr_case(store: MemoryStore | None = None) -> tuple[MemoryStore, WorkflowRuntime, dict[str, Any], str]:
    store = store or MemoryStore()
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
    store.sources["src_matrix_2"] = {
        "id": "src_matrix_2",
        "case_id": case["id"],
        "filename": "facility.txt",
        "media_type": "text/plain",
        "sha256": "f" * 64,
        "withdrawn": False,
        "blocks": [{"block_id": "b00002", "locator": {"line": 2}, "text": "The facility remains available through 2029.", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    }
    store.register_source_set({"id": "set_matrix", "case_id": case["id"], "version": 1, "source_ids": [source_id, "src_matrix_2"], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
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
        material_claims=[{**_cpdr_payload()["material_claims"][0], "workstream_id": workstreams[0]["id"], "evidence_refs": [{"source_id": source_id, "block_id": "b00001"}, {"source_id": "src_matrix_2", "block_id": "b00002"}]}],
        evidence=[
            {**_cpdr_payload()["evidence"][0], "source_id": source_id},
            {**_cpdr_payload()["evidence"][0], "evidence_id": "E-2", "source_id": "src_matrix_2", "source_digest": "f" * 64, "block_id": "b00002", "locator": "{\"line\":2}"},
        ],
    )


def _canonical_cpdr_artifact(store: MemoryStore, runtime: WorkflowRuntime, approved: dict[str, Any], source_id: str) -> dict[str, Any]:
    cp0_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-0")
    cp0 = store.get_artifact(cp0_node["artifact_id"])
    source_set = store.source_set_by_id(approved["plan"]["source_set_id"])
    assert cp0 is not None and source_set is not None
    upstream = [{"module_id": "CP-0", "artifact_id": cp0["id"], "digest": cp0["digest"]}]
    raw = _approved_final(store, approved, source_id)
    returned = {
        (source_id, "b00001"): {
            "source_digest": "e" * 64, "origin_family": "e" * 64, "authority_class": "unclassified",
            "locator": "{\"line\":1}", "extractor_version": "builtin-v1", "confidence": "HIGH",
        },
        ("src_matrix_2", "b00002"): {
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


def test_cpdr_reconciled_attempt_without_artifact_restarts_with_remaining_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    store.runs[approved["id"]]["research"]["phase"] = "researching"
    store.runs[approved["id"]]["research"]["inflight_request_digest"] = None
    final = _approved_final(store, approved, source_id)
    client = _Client([
        _Response("tool_use", [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})]),
        _Response("tool_use", [_Block("tool_use", id="tool-2", name="read_evidence", input={"source_id": "src_matrix_2", "block_ids": ["b00002"]})]),
        _Response("end_turn", [_Block("text", text=json.dumps(final))]),
    ])
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AnthropicGateway("test", "claude-sonnet-4-6", client=client))
    try:
        runtime._execute(approved["id"], "replacement")
        completed = store.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert completed["research"]["phase"] == "complete"
    finally:
        runtime.close()


def test_cpdr_existing_fingerprint_is_relinked_without_provider_call(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    recovered = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    assert cpdr_artifact_is_valid(store, approved, cpdr_node, recovered, runtime.bundle)
    store.artifacts[recovered["id"]] = recovered
    store.runs[approved["id"]]["research"]["phase"] = "researching"
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("provider called")))
    try:
        runtime._execute(approved["id"], "replacement")
        completed = store.get_run(approved["id"])
        linked = next(node for node in completed["nodes"] if node["id"] == cpdr_node["id"]) if completed else None
        assert completed is not None and completed["status"] == "succeeded"
        assert linked is not None and linked["artifact_id"] == recovered["id"]
        assert len([item for item in store.artifacts.values() if item.get("module_id") == "CP-DR"]) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "mutation", ["markdown", "transport", "confidence", "filename", "digest", "fingerprint", "plan_hash", "withdrawn"]
)
def test_strict_cpdr_artifact_validator_rejects_noncanonical_artifacts(mutation: str) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(store, runtime, approved, source_id)
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
        store.runs[approved["id"]]["research"]["approved_plan_hash"] = "sha256:" + "0" * 64
        approved = store.get_run(approved["id"]) or approved
    else:
        store.sources["src_matrix_2"]["withdrawn"] = True
    try:
        assert not cpdr_artifact_is_valid(store, approved, cpdr_node, invalid, runtime.bundle)
        store.artifacts[invalid["id"]] = invalid
        store.nodes[cpdr_node["id"]].update(status="succeeded", artifact_id=invalid["id"])
        store.runs[approved["id"]]["status"] = "succeeded"
        with pytest.raises(ValueError, match="RUN_NOT_READY"):
            build_snapshot_payload(store, store.get_run(approved["id"]) or {}, runtime.bundle)
    finally:
        runtime.close()


def test_strict_cpdr_artifact_validator_requires_real_vendored_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    monkeypatch.setattr(
        runtime.bundle,
        "validate_cpdr_handoff",
        lambda *_args, **_kwargs: type("InvalidHandoff", (), {"identity_mismatches": [], "errors": ["invalid"], "exit_code": 1})(),
    )
    try:
        assert not cpdr_artifact_is_valid(store, approved, cpdr_node, canonical, runtime.bundle)
    finally:
        runtime.close()


@pytest.mark.parametrize("entrypoint", ["reuse", "run_success", "snapshot"])
def test_strict_cpdr_artifact_entrypoints_require_current_bundle_integrity(
    monkeypatch: pytest.MonkeyPatch, entrypoint: str,
) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    canonical = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    store.artifacts[canonical["id"]] = canonical

    def fail_integrity() -> Any:
        raise MethodologyError("forced current integrity failure")

    monkeypatch.setattr(runtime.bundle, "verify", fail_integrity)
    try:
        assert not cpdr_artifact_is_valid(store, approved, cpdr_node, canonical, runtime.bundle)
        if entrypoint == "reuse":
            store.runs[approved["id"]]["research"]["phase"] = "researching"
            runtime._execute(approved["id"], "replacement")
            failed = store.get_run(approved["id"])
            assert failed is not None and failed["status"] == "failed"
            assert failed["error"]["code"] == "AGENT_AUTHORITY_MISMATCH"
        elif entrypoint == "run_success":
            store.nodes[cpdr_node["id"]].update(status="succeeded", artifact_id=canonical["id"])
            runtime._execute(approved["id"], "final-validator")
            failed = store.get_run(approved["id"])
            assert failed is not None and failed["status"] == "failed"
            assert failed["error"]["code"] == "DAG_BLOCKED"
        else:
            store.nodes[cpdr_node["id"]].update(status="succeeded", artifact_id=canonical["id"])
            store.runs[approved["id"]]["status"] = "succeeded"
            with pytest.raises(ValueError, match="RUN_NOT_READY"):
                build_snapshot_payload(store, store.get_run(approved["id"]) or {}, runtime.bundle)
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_atomic_completion_replaces_invalid_same_fingerprint_artifact(backend: str) -> None:
    store: MemoryStore = _postgres_store() if backend == "postgres" else MemoryStore()
    store, runtime, approved, source_id = _approved_cpdr_case(store)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    valid = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    valid["id"] = f"art-valid-{backend}"
    invalid = copy.deepcopy(valid)
    invalid["id"] = f"art-invalid-{backend}"
    invalid["markdown"] += "forged\n"
    store.artifacts[invalid["id"]] = invalid
    store.persist()
    token = store.claim_job(approved["id"], "collision-worker")
    assert token is not None
    full_run = store.get_run(approved["id"])
    assert full_run is not None
    def validator(candidate: dict[str, Any]) -> bool:
        return cpdr_artifact_is_valid(store, full_run, cpdr_node, candidate, runtime.bundle)
    try:
        completed = store.complete_node_fenced(
            approved["id"], token, cpdr_node["id"], valid, {**approved["research"], "phase": "complete"}, validator
        )
        assert completed["id"] == valid["id"]
        assert invalid["id"] not in store.artifacts
        durable = PostgresStore(store._dsn) if isinstance(store, PostgresStore) else store
        durable_run = durable.get_run(approved["id"])
        durable_node = next(node for node in durable_run["nodes"] if node["id"] == cpdr_node["id"]) if durable_run else None
        assert durable_node is not None and durable_node["artifact_id"] == valid["id"]
        assert cpdr_artifact_is_valid(durable, durable_run or {}, durable_node, completed, runtime.bundle)
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


@pytest.mark.parametrize("limit", ["blocks", "bytes"])
def test_cpdr_manifest_ceiling_fails_before_provider_construction(monkeypatch: pytest.MonkeyPatch, limit: str) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    if limit == "blocks":
        store.sources[source_id]["blocks"] = [
            {"block_id": f"b{index:05d}", "locator": {"line": index}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}
            for index in range(2_001)
        ]
    else:
        store.sources[source_id]["blocks"][0]["locator"] = {"section": "x" * (256 * 1_024)}
    constructed: list[bool] = []

    def forbidden_gateway(*_args: Any, **_kwargs: Any) -> Any:
        constructed.append(True)
        raise AssertionError("provider must not be constructed")

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", forbidden_gateway)
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert constructed == []
    finally:
        runtime.close()


@pytest.mark.parametrize("field", ["filename", "media_type", "locator", "extractor_version", "confidence"])
def test_cpdr_manifest_rejects_oversized_fields_before_encoding(monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    source = store.sources[source_id]
    sentinel = "manifest-sentinel-" + "x" * (512 * 1_024)
    if field in {"filename", "media_type"}:
        source[field] = sentinel
    elif field == "locator":
        source["blocks"][0][field] = {"nested": sentinel}
    else:
        source["blocks"][0][field] = sentinel
    original_dumps = workflow_domain.json.dumps

    def guarded_dumps(value: Any, *args: Any, **kwargs: Any) -> str:
        if isinstance(value, dict):
            assert sentinel not in value.values()
            locator = value.get("locator")
            assert not isinstance(locator, dict) or sentinel not in locator.values()
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(workflow_domain.json, "dumps", guarded_dumps)
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: pytest.fail("provider constructed"))
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
    finally:
        runtime.close()


def test_cpdr_manifest_rejects_many_short_locator_nodes_before_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    locator = {"groups": [list(range(100)) for _ in range(6)]}
    store.sources[source_id]["blocks"][0]["locator"] = locator
    original_dumps = workflow_domain.json.dumps

    def guarded_dumps(value: Any, *args: Any, **kwargs: Any) -> str:
        assert not isinstance(value, dict) or value.get("locator") is not locator
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(workflow_domain.json, "dumps", guarded_dumps)
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: pytest.fail("provider constructed"))
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
    finally:
        runtime.close()


def test_cpdr_manifest_exact_block_and_encoded_byte_boundaries_are_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    expected_manifest = []
    for manifest_source_id in (source_id, "src_matrix_2"):
        source = store.sources[manifest_source_id]
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
    constructed: list[bool] = []

    def reached_gateway(*_args: Any, **_kwargs: Any) -> Any:
        constructed.append(True)
        raise ProviderUnavailable("boundary reached provider")

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", reached_gateway)
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_PROVIDER_UNAVAILABLE"
        assert constructed == [True]
    finally:
        runtime.close()


def test_cpdr_unexpected_post_provider_failure_is_sanitized_and_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    final = _approved_final(store, approved, source_id)
    client = _Client([
        _Response("tool_use", [_Block("tool_use", id="tool-1", name="read_evidence", input={"source_id": source_id, "block_ids": ["b00001"]})]),
        _Response("tool_use", [_Block("tool_use", id="tool-2", name="read_evidence", input={"source_id": "src_matrix_2", "block_ids": ["b00002"]})]),
        _Response("end_turn", [_Block("text", text=json.dumps(final))]),
    ])
    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: AnthropicGateway("test", "claude-sonnet-4-6", client=client))
    monkeypatch.setattr(workflow_domain, "render_cpdr_markdown", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("secret-post-provider")))
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert failed["research"]["phase"] == "failed"
        assert any(item.get("terminal_code") == "AGENT_OUTPUT_INVALID" for item in failed["research"]["attempts"])
        assert "secret-post-provider" not in json.dumps({"run": failed, "events": store.events[approved["id"]]})
    finally:
        runtime.close()


def test_cpdr_prior_179_seconds_caps_next_operation_to_one_second(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, _source_id = _approved_cpdr_case()
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 179 / 60
    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: 1_000.0)
    remaining: list[float] = []

    class CaptureGateway:
        def run(self, **kwargs: Any) -> Any:
            remaining.append(kwargs["remaining_time"]())
            raise ProviderUnavailable("captured")

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: CaptureGateway())
    try:
        runtime._execute(approved["id"], "approver")
        assert remaining and 0 < remaining[0] <= 1.0
        assert not any(item.get("module_id") == "CP-DR" for item in store.artifacts.values())
    finally:
        runtime.close()


def test_cpdr_approval_wait_is_excluded_while_planning_time_is_charged(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MemoryStore()
    settings = Settings(
        environment="production", storage_dir=Path("/tmp/caos-cpdr-approval-time"), deploy_v_root=DEPLOY_V,
        anthropic_api_key="test-only-key", cpdr_agent_enabled=True, cpdr_pilot_subjects=("analyst",),
    )
    bundle = DeployVBundle(DEPLOY_V)
    runtime = WorkflowRuntime(store, bundle, settings)
    case = store.create_case("Approval time", "Issuer", "Testing", "analyst")
    source_id = "src_approval_time"
    store.sources[source_id] = {
        "id": source_id, "case_id": case["id"], "filename": "issuer.txt", "media_type": "text/plain",
        "sha256": "a" * 64, "withdrawn": False,
        "blocks": [{"block_id": "b00001", "locator": {"line": 1}, "text": "x", "extractor_version": "builtin-v1", "confidence": "HIGH"}],
    }
    store.register_source_set({"id": "set_approval_time", "case_id": case["id"], "version": 1, "source_ids": [source_id], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"})
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

    class StopGateway:
        def run(self, **kwargs: Any) -> Any:
            kwargs["remaining_time"]()
            raise ProviderUnavailable("stop after timing check")

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: StopGateway())
    try:
        run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], "analyst")
        paused = store.get_run(run["id"])
        assert paused is not None and paused["research"]["budget_used"]["active_minutes"] == pytest.approx(2 / 60)
        Clock.now += 10_000
        runtime.approve_research_plan(run["id"], "approver", paused["research"]["proposed_plan_hash"])
        runtime._execute(run["id"], "approver")
        failed = store.get_run(run["id"])
        assert failed is not None and failed["research"]["budget_used"]["active_minutes"] == pytest.approx(2 / 60)
    finally:
        runtime.close()


def test_cpdr_slow_render_is_charged_before_artifact_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 179 / 60
    final = _approved_final(store, approved, source_id)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    class LocalGateway:
        def run(self, **kwargs: Any) -> Any:
            kwargs["remaining_time"]()
            kwargs["read_evidence"](source_id, ["b00001"])
            kwargs["read_evidence"]("src_matrix_2", ["b00002"])
            return kwargs["validate"](final)

    original_render = workflow_domain.render_cpdr_markdown

    def slow_render(*args: Any, **kwargs: Any) -> Any:
        rendered = original_render(*args, **kwargs)
        Clock.now += 2.0
        return rendered

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: LocalGateway())
    monkeypatch.setattr(workflow_domain, "render_cpdr_markdown", slow_render)
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert not any(item.get("module_id") == "CP-DR" for item in store.artifacts.values())
    finally:
        runtime.close()


@pytest.mark.parametrize("operation", ["scorer", "renderer", "validator", "envelope"])
def test_cpdr_throwing_host_operations_charge_active_time(monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    final = _approved_final(store, approved, source_id)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    class LocalGateway:
        def run(self, **kwargs: Any) -> Any:
            kwargs["read_evidence"](source_id, ["b00001"])
            kwargs["read_evidence"]("src_matrix_2", ["b00002"])
            return kwargs["validate"](final)

    def throwing(*_args: Any, **_kwargs: Any) -> Any:
        Clock.now += 2.0
        raise RuntimeError("host operation failed")

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: LocalGateway())
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
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert failed["research"]["budget_used"]["active_minutes"] >= 2 / 60
    finally:
        runtime.close()


def test_cpdr_slow_atomic_completion_crosses_ceiling_and_cannot_succeed(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 179 / 60
    final = _approved_final(store, approved, source_id)

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)

    class LocalGateway:
        def run(self, **kwargs: Any) -> Any:
            kwargs["read_evidence"](source_id, ["b00001"])
            kwargs["read_evidence"]("src_matrix_2", ["b00002"])
            return kwargs["validate"](final)

    original_completion = store.complete_node_fenced

    def slow_completion(*args: Any, **kwargs: Any) -> Any:
        Clock.now += 2.0
        return original_completion(*args, **kwargs)

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", lambda *_args, **_kwargs: LocalGateway())
    monkeypatch.setattr(store, "complete_node_fenced", slow_completion)
    try:
        runtime._execute(approved["id"], "approver")
        failed = store.get_run(approved["id"])
        cpdr_node = next(node for node in failed["nodes"] if node["module_id"] == "CP-DR") if failed else None
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 181 / 60
        assert cpdr_node is not None and cpdr_node["status"] == "failed"
    finally:
        runtime.close()


def test_cpdr_no_pending_final_validation_is_charged_before_run_success(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, source_id = _approved_cpdr_case()
    artifact = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    store.artifacts[artifact["id"]] = artifact
    store.nodes[cpdr_node["id"]].update(status="succeeded", artifact_id=artifact["id"])
    store.runs[approved["id"]]["research"].update(phase="complete")
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 179 / 60

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
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 181 / 60
        assert not any(item["event"] == "run.succeeded" for item in store.events[approved["id"]])
    finally:
        runtime.close()


def _ready_cpdr_finalization() -> tuple[MemoryStore, WorkflowRuntime, dict[str, Any], dict[str, Any], dict[str, Any]]:
    store, runtime, approved, source_id = _approved_cpdr_case()
    artifact = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    store.artifacts[artifact["id"]] = artifact
    store.nodes[cpdr_node["id"]].update(status="succeeded", artifact_id=artifact["id"])
    store.runs[approved["id"]]["research"].update(phase="complete")
    return store, runtime, approved, cpdr_node, artifact


def _assert_run_cannot_be_accepted(runtime: WorkflowRuntime, run: dict[str, Any]) -> None:
    with pytest.raises(WorkflowError, match="RUN_NOT_READY"):
        runtime.accept_run(run["case_id"], run["id"], "approver")


def test_cpdr_finalization_allowance_is_fixed_and_ponytail_bounded() -> None:
    assert 2.0 < workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS <= 5.0


def test_cpdr_179_seconds_cannot_enter_atomic_success_finalization() -> None:
    store, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 179 / 60
    try:
        runtime._execute(approved["id"], "final-reserve")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 180 / 60
        assert not any(item["event"] == "run.succeeded" for item in store.events[approved["id"]])
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()


def test_cpdr_finalization_reservation_failure_is_sanitized_before_success(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    original_update = store.update_run_fenced
    research_writes = 0

    def fail_reservation(run_id: str, attempt_token: str, **changes: Any) -> None:
        nonlocal research_writes
        if set(changes) == {"research"}:
            research_writes += 1
            if research_writes == 2:
                raise RuntimeError("secret-final-reservation")
        original_update(run_id, attempt_token, **changes)

    monkeypatch.setattr(store, "update_run_fenced", fail_reservation)
    try:
        runtime._execute(approved["id"], "reservation-failure")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert not any(item["event"] == "run.succeeded" for item in store.events[approved["id"]])
        assert "secret-final-reservation" not in json.dumps({"run": failed, "events": store.events[approved["id"]]})
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()


def test_cpdr_atomic_success_persistence_failure_rolls_back_and_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    original_persist = store.persist
    fail_once = True

    def fail_terminal_persist() -> None:
        nonlocal fail_once
        if (
            fail_once
            and store.runs[approved["id"]]["status"] == "succeeded"
            and any(item["event"] == "run.succeeded" for item in store.events[approved["id"]])
        ):
            fail_once = False
            raise RuntimeError("secret-atomic-finalization")
        original_persist()

    monkeypatch.setattr(store, "persist", fail_terminal_persist)
    try:
        runtime._execute(approved["id"], "atomic-failure")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_OUTPUT_INVALID"
        assert not any(item["event"] == "run.succeeded" for item in store.events[approved["id"]])
        assert "secret-atomic-finalization" not in json.dumps({"run": failed, "events": store.events[approved["id"]]})
        _assert_run_cannot_be_accepted(runtime, failed)
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_atomic_success_store_operation_rolls_back_run_and_event(
    monkeypatch: pytest.MonkeyPatch, backend: str,
) -> None:
    store: MemoryStore = _postgres_store() if backend == "postgres" else MemoryStore()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    token = store.claim_job(run["id"], "atomic-worker")
    assert token is not None
    store.complete_node_fenced(run["id"], token, node["id"], _artifact(run["id"]), None)
    original_persist = store._persist_connection if isinstance(store, PostgresStore) else store.persist

    if isinstance(store, PostgresStore):
        def fail_terminal_connection(connection: Any) -> Any:
            if store.runs[run["id"]]["status"] == "succeeded":
                raise RuntimeError("terminal transaction failed")
            return original_persist(connection)

        monkeypatch.setattr(store, "_persist_connection", fail_terminal_connection)
    else:
        def fail_terminal_memory() -> None:
            if store.runs[run["id"]]["status"] == "succeeded":
                raise RuntimeError("terminal persistence failed")
            original_persist()

        monkeypatch.setattr(store, "persist", fail_terminal_memory)

    with pytest.raises(RuntimeError, match="terminal"):
        store.finalize_run_success_fenced(run["id"], token, None, {"run_id": run["id"]})

    assert store.runs[run["id"]]["status"] != "succeeded"
    assert not any(item["event"] == "run.succeeded" for item in store.events[run["id"]])
    if isinstance(store, PostgresStore):
        restored = PostgresStore(store._dsn).get_run(run["id"])
        assert restored is not None and restored["status"] != "succeeded"
        assert not any(item["event"] == "run.succeeded" for item in restored["events"])


def test_cpdr_success_finalization_is_single_terminal_run_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, cpdr_node, artifact = _ready_cpdr_finalization()
    finalized = False
    post_final_updates: list[dict[str, Any]] = []
    original_finalize = store.finalize_run_success_fenced
    original_update = store.update_run_fenced

    def track_finalize(*args: Any, **kwargs: Any) -> None:
        nonlocal finalized
        original_finalize(*args, **kwargs)
        finalized = True

    def track_update(run_id: str, attempt_token: str, **changes: Any) -> None:
        if finalized:
            post_final_updates.append(copy.deepcopy(changes))
        original_update(run_id, attempt_token, **changes)

    monkeypatch.setattr(store, "finalize_run_success_fenced", track_finalize)
    monkeypatch.setattr(store, "update_run_fenced", track_update)
    try:
        runtime._execute(approved["id"], "atomic-success")
        completed = store.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert completed["research"]["budget_used"]["active_minutes"] >= (
            workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS / 60
        )
        completed_node = next(item for item in completed["nodes"] if item["id"] == cpdr_node["id"])
        assert completed_node["status"] == "succeeded" and completed_node["artifact_id"] == artifact["id"]
        assert store.get_artifact(artifact["id"])["digest"] == artifact["digest"]  # type: ignore[index]
        assert [item["event"] for item in completed["events"]].count("run.succeeded") == 1
        assert post_final_updates == []
    finally:
        runtime.close()


def test_cpdr_two_second_atomic_finalization_is_covered_by_fixed_reserve(monkeypatch: pytest.MonkeyPatch) -> None:
    store, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization()
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 170 / 60

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)
    original_finalize = store.finalize_run_success_fenced
    finalization_seconds: list[float] = []

    def slow_finalize(*args: Any, **kwargs: Any) -> None:
        started = Clock.now
        Clock.now += 2.0
        original_finalize(*args, **kwargs)
        finalization_seconds.append(Clock.now - started)

    monkeypatch.setattr(store, "finalize_run_success_fenced", slow_finalize)
    try:
        runtime._execute(approved["id"], "slow-atomic-success")
        completed = store.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert finalization_seconds == [2.0]
        assert finalization_seconds[0] <= workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS
        assert completed["research"]["budget_used"]["active_minutes"] >= (
            (170 + workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS) / 60
        )
    finally:
        runtime.close()


def _ready_cpdr_finalization_on(
    store: MemoryStore,
) -> tuple[MemoryStore, WorkflowRuntime, dict[str, Any], dict[str, Any], dict[str, Any]]:
    store, runtime, approved, source_id = _approved_cpdr_case(store)
    artifact = _canonical_cpdr_artifact(store, runtime, approved, source_id)
    cpdr_node = next(node for node in approved["nodes"] if node["module_id"] == "CP-DR")
    store.artifacts[artifact["id"]] = artifact
    store.nodes[cpdr_node["id"]].update(status="succeeded", artifact_id=artifact["id"])
    store.runs[approved["id"]]["research"].update(phase="complete")
    store.persist()
    return store, runtime, approved, cpdr_node, artifact


@pytest.mark.parametrize("backend", ["memory", "postgres"])
@pytest.mark.parametrize("delay_site", ["before_entry", "during_persistence"])
def test_cpdr_174_plus_ten_second_finalization_never_commits_success(
    monkeypatch: pytest.MonkeyPatch, backend: str, delay_site: str,
) -> None:
    selected_store: MemoryStore = _postgres_store() if backend == "postgres" else MemoryStore()
    store, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization_on(selected_store)
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 174 / 60
    store.persist()

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)
    if delay_site == "before_entry":
        original_finalize = store.finalize_run_success_fenced

        def delayed_finalize(*args: Any, **kwargs: Any) -> None:
            Clock.now += 10.0
            original_finalize(*args, **kwargs)

        monkeypatch.setattr(store, "finalize_run_success_fenced", delayed_finalize)
    elif isinstance(store, PostgresStore):
        original_persist_connection = store._persist_connection

        def delayed_persist_connection(connection: Any) -> Any:
            if store.runs[approved["id"]]["status"] == "succeeded":
                Clock.now += 10.0
            return original_persist_connection(connection)

        monkeypatch.setattr(store, "_persist_connection", delayed_persist_connection)
    else:
        original_persist = store.persist

        def delayed_persist() -> None:
            if store.runs[approved["id"]]["status"] == "succeeded":
                Clock.now += 10.0
            original_persist()

        monkeypatch.setattr(store, "persist", delayed_persist)

    try:
        runtime._execute(approved["id"], f"deadline-{backend}-{delay_site}")
        failed = store.get_run(approved["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert failed["research"]["budget_used"]["active_minutes"] >= 179 / 60
        assert not any(item["event"] == "run.succeeded" for item in failed["events"])
        _assert_run_cannot_be_accepted(runtime, failed)
        if isinstance(store, PostgresStore):
            restored = PostgresStore(store._dsn).get_run(approved["id"])
            assert restored is not None and restored["status"] == "failed"
            assert not any(item["event"] == "run.succeeded" for item in restored["events"])
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_cpdr_two_second_finalization_commits_inside_absolute_deadline(
    monkeypatch: pytest.MonkeyPatch, backend: str,
) -> None:
    selected_store: MemoryStore = _postgres_store() if backend == "postgres" else MemoryStore()
    store, runtime, approved, _cpdr_node, _artifact_row = _ready_cpdr_finalization_on(selected_store)
    store.runs[approved["id"]]["research"]["budget_used"]["active_minutes"] = 170 / 60
    store.persist()

    class Clock:
        now = 1_000.0

    monkeypatch.setattr(workflow_domain.time, "monotonic", lambda: Clock.now)
    original_finalize = store.finalize_run_success_fenced

    def delayed_finalize(*args: Any, **kwargs: Any) -> None:
        Clock.now += 2.0
        original_finalize(*args, **kwargs)

    monkeypatch.setattr(store, "finalize_run_success_fenced", delayed_finalize)
    try:
        runtime._execute(approved["id"], f"within-deadline-{backend}")
        completed = store.get_run(approved["id"])
        assert completed is not None and completed["status"] == "succeeded"
        assert [item["event"] for item in completed["events"]].count("run.succeeded") == 1
        if isinstance(store, PostgresStore):
            restored = PostgresStore(store._dsn).get_run(approved["id"])
            assert restored is not None and restored["status"] == "succeeded"
            assert [item["event"] for item in restored["events"]].count("run.succeeded") == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_expired_finalization_deadline_does_not_mask_job_fencing(backend: str) -> None:
    store: MemoryStore = _postgres_store() if backend == "postgres" else MemoryStore()
    run, node = _queued_run(store, dependencies=[])
    assert node is not None
    token = store.claim_job(run["id"], f"fenced-deadline-{backend}")
    assert token is not None
    store.complete_node_fenced(run["id"], token, node["id"], _artifact(run["id"]), None)
    if isinstance(store, PostgresStore):
        with store._psycopg.connect(store._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET lease_until = now() - interval '1 second' WHERE run_id = %s",
                    (run["id"],),
                )
            connection.commit()
    else:
        store.jobs[run["id"]]["lease_until"] = time.monotonic() - 1

    with pytest.raises(JobFencedError):
        store.finalize_run_success_fenced(
            run["id"], token, None, {"run_id": run["id"]}, deadline=time.monotonic() - 1,
        )


def test_open_postgres_event_stream_refreshes_worker_events_without_reconnect() -> None:
    api_store = _postgres_store("cpdr-sse-api")
    worker_store = _postgres_store("cpdr-sse-worker")
    run, node = _queued_run(worker_store, dependencies=[])
    assert node is not None
    runtime = WorkflowRuntime(
        api_store,
        object(),
        Settings(environment="production", storage_dir=Path("/tmp/caos-sse-refresh"), deploy_v_root=DEPLOY_V),
    )  # type: ignore[arg-type]
    stream = runtime.stream_events(run["id"])
    try:
        assert next(stream) == ": keepalive\n\n"
        token = worker_store.claim_job(run["id"], "sse-worker")
        assert token is not None
        worker_store.update_run_fenced(run["id"], token, status="running")
        worker_store.emit_fenced(run["id"], token, "run.running", {"run_id": run["id"]})
        artifact = worker_store.complete_node_fenced(
            run["id"], token, node["id"], _artifact(run["id"]), None,
        )
        worker_store.emit_fenced(
            run["id"], token, "node.succeeded",
            {"node_id": node["id"], "module_id": node["module_id"], "artifact_id": artifact["id"]},
        )
        worker_store.finalize_run_success_fenced(
            run["id"], token, None, {"run_id": run["id"]},
            deadline=time.monotonic() + workflow_domain.CPDR_FINALIZATION_ALLOWANCE_SECONDS,
        )

        delivered = [next(stream), *list(stream)]
        assert [item.split("\n", 2)[0] for item in delivered] == ["id: 1", "id: 2", "id: 3"]
        assert [item.split("\n", 2)[1] for item in delivered] == [
            "event: run.running", "event: node.succeeded", "event: run.succeeded",
        ]
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
