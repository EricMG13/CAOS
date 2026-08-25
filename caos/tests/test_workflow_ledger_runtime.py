from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from caos.config import Settings
from caos.contracts import digest
from caos.memory_ledgers import MemoryLedgerSet
from caos.postgres_ledgers import PostgresLedgerSet
from caos.workflows import domain as workflow_domain
from caos.workflows.domain import WorkflowRuntime


DEPLOY_V = (
    Path(__file__).parents[1]
    / "server"
    / "caos"
    / "methodology"
    / "vendor"
    / "deploy_v"
)
POSTGRES_URL = os.getenv("CAOS_TEST_DATABASE_URL")
WORKER_EVENTS = {
    "run.running",
    "node.running",
    "node.succeeded",
    "node.failed",
    "run.succeeded",
    "run.failed",
}


class _RunLedgerProxy:
    def __init__(self, ledger: Any) -> None:
        self.ledger = ledger

    def __getattr__(self, name: str) -> Any:
        return getattr(self.ledger, name)


class _ArtifactRuntime(WorkflowRuntime):
    def __init__(self, ledger_set: Any, runs: Any | None = None) -> None:
        super().__init__(
            runs or ledger_set.runs,
            ledger_set.sources,
            object(),  # type: ignore[arg-type]
            Settings(storage_dir=Path("/tmp/caos-ledger-runtime"), deploy_v_root=DEPLOY_V),
        )

    def _build_artifact_with_slot(
        self,
        run: dict[str, Any],
        node: dict[str, Any],
        actor: str,
        fenced_call: Any | None = None,
        lease_check: Any | None = None,
    ) -> dict[str, Any]:
        payload = {"module_id": node["module_id"], "result": "ok"}
        return {
            "case_id": run["case_id"],
            "run_id": run["id"],
            "module_id": node["module_id"],
            "created_by": actor,
            "payload": payload,
            "digest": digest(payload),
            "input_fingerprint": digest({"run": run["id"], "node": node["id"]}),
        }


def _queued_runtime_run(ledger_set: Any, *, with_node: bool = True) -> dict[str, Any]:
    case = ledger_set.runs.create_case("Runtime", "Issuer", "Testing", "analyst")
    nodes = [{"module_id": "CP-X", "dependencies": [], "stage": 1}] if with_node else []
    return ledger_set.runs.create_run_with_nodes(
        case["id"],
        "analyst",
        {"pathway": "EARNINGS_UPDATE", "source_set_id": None},
        nodes,
    )


def test_runtime_heartbeat_renews_and_joins_through_run_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger_set = MemoryLedgerSet()
    renewed = threading.Event()

    class HeartbeatLedger(_RunLedgerProxy):
        renewals = 0

        def renew(self, run_id: str, attempt_token: str) -> bool:
            self.renewals += 1
            renewed.set()
            return self.ledger.renew(run_id, attempt_token)

        def get_run(self, run_id: str) -> dict[str, Any] | None:
            assert renewed.wait(1)
            return self.ledger.get_run(run_id)

    real_thread = threading.Thread
    created: list[Any] = []

    class TrackingThread(real_thread):
        joined = False

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            created.append(self)

        def join(self, timeout: float | None = None) -> None:
            super().join(timeout)
            self.joined = True

    run = _queued_runtime_run(ledger_set, with_node=False)
    runs = HeartbeatLedger(ledger_set.runs)
    runtime = _ArtifactRuntime(ledger_set, runs)
    monkeypatch.setattr(workflow_domain, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(workflow_domain.threading, "Thread", TrackingThread)
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    assert runs.renewals >= 1
    assert len(created) == 1
    assert created[0].joined and not created[0].is_alive()


@pytest.mark.parametrize("renewal_error", [False, True])
def test_runtime_lease_loss_fails_closed_through_run_ledger(
    monkeypatch: pytest.MonkeyPatch, renewal_error: bool
) -> None:
    ledger_set = MemoryLedgerSet()
    renewal_attempted = threading.Event()

    class LostLeaseLedger(_RunLedgerProxy):
        def renew(self, run_id: str, attempt_token: str) -> bool:
            renewal_attempted.set()
            if renewal_error:
                raise RuntimeError("renewal failed")
            return False

        def get_run(self, run_id: str) -> dict[str, Any] | None:
            assert renewal_attempted.wait(1)
            return self.ledger.get_run(run_id)

    run = _queued_runtime_run(ledger_set)
    runtime = _ArtifactRuntime(ledger_set, LostLeaseLedger(ledger_set.runs))
    monkeypatch.setattr(workflow_domain, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    persisted = ledger_set.runs.get_run(run["id"])
    assert persisted is not None and persisted["status"] == "running"
    assert [event["event"] for event in persisted["events"]] == ["run.running"]


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (False, ["run.running", "node.running", "node.succeeded", "run.succeeded"]),
        (True, ["run.running", "node.running", "node.failed", "run.failed"]),
    ],
)
def test_runtime_lifecycle_and_terminal_events_are_fenced_through_ledgers(
    failure: bool, expected: list[str]
) -> None:
    ledger_set = MemoryLedgerSet()

    class FencedOnlyLedger(_RunLedgerProxy):
        def emit(self, run_id: str, event: str, data: dict[str, Any]) -> None:
            if event in WORKER_EVENTS:
                raise AssertionError(f"worker event escaped fencing: {event}")
            self.ledger.emit(run_id, event, data)

    class Runtime(_ArtifactRuntime):
        def _build_artifact_with_slot(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            if failure:
                raise RuntimeError("node failed")
            return super()._build_artifact_with_slot(*args, **kwargs)

    run = _queued_runtime_run(ledger_set)
    runtime = Runtime(ledger_set, FencedOnlyLedger(ledger_set.runs))
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    persisted = ledger_set.runs.get_run(run["id"])
    assert persisted is not None
    assert [event["event"] for event in persisted["events"]] == expected


@pytest.mark.parametrize("failure", [False, True])
def test_runtime_cannot_emit_terminal_event_after_ledger_fencing(failure: bool) -> None:
    ledger_set = MemoryLedgerSet()

    class ExpiringLedger(_RunLedgerProxy):
        def update_run_fenced(
            self, run_id: str, attempt_token: str, **changes: Any
        ) -> None:
            if changes.get("status") == "failed":
                self.ledger.finish(run_id, attempt_token)
            self.ledger.update_run_fenced(run_id, attempt_token, **changes)

        def finalize_success(
            self,
            run_id: str,
            attempt_token: str,
            research: dict[str, Any] | None,
            event_data: dict[str, Any],
            *,
            deadline: float | None = None,
        ) -> None:
            self.ledger.finish(run_id, attempt_token)
            self.ledger.finalize_success(
                run_id, attempt_token, research, event_data, deadline=deadline
            )

    class Runtime(_ArtifactRuntime):
        def _build_artifact_with_slot(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            if failure:
                raise RuntimeError("node failed")
            return super()._build_artifact_with_slot(*args, **kwargs)

    run = _queued_runtime_run(ledger_set)
    runtime = Runtime(ledger_set, ExpiringLedger(ledger_set.runs))
    try:
        runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    events = [event["event"] for event in ledger_set.runs.events_after(run["id"])]
    assert "run.succeeded" not in events and "run.failed" not in events


def test_runtime_atomic_success_rolls_back_run_and_event_on_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from caos import memory_ledgers

    ledger_set = MemoryLedgerSet()
    calls = 0
    original = memory_ledgers._remaining_finalization_seconds

    def expire_after_mutation(deadline: float | None) -> float | None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TimeoutError("finalization deadline exceeded")
        return original(deadline)

    class DeadlineLedger(_RunLedgerProxy):
        def finalize_success(
            self,
            run_id: str,
            attempt_token: str,
            research: dict[str, Any] | None,
            event_data: dict[str, Any],
            *,
            deadline: float | None = None,
        ) -> None:
            self.ledger.finalize_success(
                run_id,
                attempt_token,
                research,
                event_data,
                deadline=time.monotonic() + 10,
            )

    run = _queued_runtime_run(ledger_set, with_node=False)
    runtime = _ArtifactRuntime(ledger_set, DeadlineLedger(ledger_set.runs))
    monkeypatch.setattr(memory_ledgers, "_remaining_finalization_seconds", expire_after_mutation)
    try:
        with pytest.raises(TimeoutError, match="deadline"):
            runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    persisted = ledger_set.runs.get_run(run["id"])
    assert persisted is not None and persisted["status"] == "running"
    assert "run.succeeded" not in [event["event"] for event in persisted["events"]]


def test_runtime_expired_finalization_deadline_fails_before_success() -> None:
    ledger_set = MemoryLedgerSet()

    class ExpiredDeadlineLedger(_RunLedgerProxy):
        def finalize_success(
            self,
            run_id: str,
            attempt_token: str,
            research: dict[str, Any] | None,
            event_data: dict[str, Any],
            *,
            deadline: float | None = None,
        ) -> None:
            self.ledger.finalize_success(
                run_id,
                attempt_token,
                research,
                event_data,
                deadline=time.monotonic() - 1,
            )

    run = _queued_runtime_run(ledger_set, with_node=False)
    runtime = _ArtifactRuntime(ledger_set, ExpiredDeadlineLedger(ledger_set.runs))
    try:
        with pytest.raises(TimeoutError, match="deadline"):
            runtime._execute(run["id"], "analyst")
    finally:
        runtime.close()

    persisted = ledger_set.runs.get_run(run["id"])
    assert persisted is not None and persisted["status"] == "running"
    assert "run.succeeded" not in [event["event"] for event in persisted["events"]]


def test_open_postgres_event_stream_observes_worker_ledger_events() -> None:
    if not POSTGRES_URL:
        pytest.skip("CAOS_TEST_DATABASE_URL is not set")
    dsn = POSTGRES_URL.replace("postgresql+psycopg://", "postgresql://")
    api_ledgers = PostgresLedgerSet(dsn)
    worker_ledgers = PostgresLedgerSet(dsn)
    case = worker_ledgers.runs.create_case("SSE", "Issuer", "Testing", "analyst")
    run = worker_ledgers.runs.create_run_with_nodes(
        case["id"], "analyst", {"pathway": "EARNINGS_UPDATE"}, []
    )
    runtime = _ArtifactRuntime(api_ledgers)
    stream = runtime.stream_events(run["id"])
    try:
        assert next(stream) == ": keepalive\n\n"
        token = worker_ledgers.runs.claim(run["id"], "worker")
        assert token is not None
        worker_ledgers.runs.update_run_fenced(run["id"], token, status="running")
        worker_ledgers.runs.emit_fenced(
            run["id"], token, "run.running", {"run_id": run["id"]}
        )
        worker_ledgers.runs.finalize_success(
            run["id"], token, None, {"run_id": run["id"]}
        )
        delivered = [next(stream), *list(stream)]
    finally:
        runtime.close()

    assert [item.split("\n", 2)[1] for item in delivered] == [
        "event: run.running",
        "event: run.succeeded",
    ]
