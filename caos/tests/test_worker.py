from __future__ import annotations

from typing import Any

from caos.store import MemoryStore, PostgresStore
from caos.workflows.domain import WorkflowRuntime
from worker import dispatch_pending


class _Future:
    def __init__(self, *, done: bool = False, error: Exception | None = None) -> None:
        self._done = done
        self._error = error

    def done(self) -> bool:
        return self._done

    def result(self) -> None:
        if self._error is not None:
            raise self._error


def test_dispatch_pending_uses_public_interfaces_and_reaps_failures() -> None:
    class Store:
        def pending_runs(self) -> list[tuple[str, str]]:
            return [("run-active", "analyst"), ("run-new", "reviewer")]

        def pending_model_jobs(self) -> list[tuple[str, str, str]]:
            return [
                ("build-failed", "analyst", "calculate"),
                ("build-new", "reviewer", "calculate"),
                ("build-export", "approver", "export"),
            ]

    class Runtime:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def schedule(self, run_id: str, actor: str) -> _Future:
            self.calls.append((run_id, actor))
            return _Future()

    class ModelRuntime:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []

        def schedule(self, build_id: str, actor: str) -> _Future:
            self.calls.append((build_id, actor, "calculate"))
            return _Future()

        def schedule_export(self, build_id: str, actor: str) -> _Future:
            self.calls.append((build_id, actor, "export"))
            return _Future()

    runtime = Runtime()
    model_runtime = ModelRuntime()
    futures: dict[tuple[str, str], Any] = {
        ("workflow", "run-active"): _Future(),
        ("model", "build-failed:calculate"): _Future(
            done=True, error=RuntimeError("failed")
        ),
    }

    dispatch_pending(Store(), runtime, model_runtime, futures)

    assert runtime.calls == [("run-new", "reviewer")]
    assert model_runtime.calls == [
        ("build-new", "reviewer", "calculate"),
        ("build-export", "approver", "export"),
    ]
    assert ("workflow", "run-active") in futures
    assert ("model", "build-failed:calculate") not in futures


def test_memory_pending_reads_return_only_schedulable_identities() -> None:
    store = MemoryStore()
    store.runs = {
        "queued": {"id": "queued", "created_by": "analyst", "status": "queued"},
        "running": {"id": "running", "created_by": "reviewer", "status": "running"},
        "paused": {"id": "paused", "created_by": "analyst", "status": "paused"},
    }
    store.model_builds = {
        "build-a": {"id": "build-a", "created_by": "fallback"},
        "build-b": {"id": "build-b", "created_by": "builder"},
    }
    store.model_jobs = {
        "build-a:calculate": {
            "build_id": "build-a",
            "actor": "reviewer",
            "kind": "calculate",
            "status": "queued",
        },
        "build-b:export": {
            "build_id": "build-b",
            "actor": "",
            "kind": "export",
            "status": "claimed",
        },
        "build-b:failed": {
            "build_id": "build-b",
            "actor": "builder",
            "kind": "calculate",
            "status": "failed",
        },
    }

    assert store.pending_runs() == [("queued", "analyst"), ("running", "reviewer")]
    assert store.pending_model_jobs() == [
        ("build-a", "reviewer", "calculate"),
        ("build-b", "builder", "export"),
    ]


def test_workflow_schedule_submits_the_runtime_executor() -> None:
    submitted: list[tuple[Any, tuple[str, str]]] = []
    future = object()

    class Executor:
        def submit(self, function: Any, *args: str) -> object:
            submitted.append((function, args))
            return future

    runtime = WorkflowRuntime.__new__(WorkflowRuntime)
    runtime.executor = Executor()

    assert runtime.schedule("run-1", "analyst") is future
    assert submitted == [(runtime._execute, ("run-1", "analyst"))]


def test_postgres_pending_reads_use_normalized_tables() -> None:
    class Cursor:
        def __init__(self) -> None:
            self.rows: list[tuple[str, ...]] = []

        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, statement: str) -> None:
            if "FROM runs" in statement:
                assert "status IN ('queued', 'running')" in statement
                assert "ORDER BY created_at, id" in statement
                self.rows = [("run-1", "analyst")]
            elif "FROM model_build_jobs" in statement:
                assert "jsonb_extract_path_text" in statement
                assert "build.created_by" in statement
                assert "JOIN model_builds" in statement
                assert "JOIN caos_state" in statement
                assert "job.state IN ('queued', 'claimed')" in statement
                self.rows = [("build-1", "reviewer", "calculate")]
            else:
                raise AssertionError(f"unexpected query: {statement}")

        def fetchall(self) -> list[tuple[str, ...]]:
            return self.rows

    class Connection:
        def __enter__(self) -> Connection:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def cursor(self) -> Cursor:
            return Cursor()

    class Psycopg:
        def connect(self, dsn: str) -> Connection:
            assert dsn == "postgresql://test"
            return Connection()

    store = PostgresStore.__new__(PostgresStore)
    store._dsn = "postgresql://test"
    store._psycopg = Psycopg()

    assert store.pending_runs() == [("run-1", "analyst")]
    assert store.pending_model_jobs() == [("build-1", "reviewer", "calculate")]
