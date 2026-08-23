from __future__ import annotations

import copy
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

import pytest
from caos.config import Settings
from caos.store import JobFencedError, MemoryStore, PostgresStore
from caos.workflows import domain as workflow_domain
from caos.workflows.domain import WorkflowRuntime, _LeaseFence


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
        def _build_artifact_with_slot(self, run: dict[str, Any], node: dict[str, Any], actor: str) -> dict[str, Any]:
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
