from __future__ import annotations

from typing import Any

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
    class Runs:
        def pending_runs(self) -> list[tuple[str, str]]:
            return [("run-active", "analyst"), ("run-new", "reviewer")]

    class Models:
        def pending_jobs(self) -> list[tuple[str, str, str]]:
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

    dispatch_pending(Runs(), Models(), runtime, model_runtime, futures)

    assert runtime.calls == [("run-new", "reviewer")]
    assert model_runtime.calls == [
        ("build-new", "reviewer", "calculate"),
        ("build-export", "approver", "export"),
    ]
    assert ("workflow", "run-active") in futures
    assert ("model", "build-failed:calculate") not in futures


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
