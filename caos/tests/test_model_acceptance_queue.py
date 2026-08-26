from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from caos.config import Settings
from caos.http import create_app
from caos.memory_ledgers import MemoryLedgerSet
from test_cp_model import DEPLOY_V, _CanonicalProvider, _canonical_runtime_case


HEADERS = {"x-forwarded-user": "analyst", "x-caos-role": "ANALYST"}


def _completed_case(pathway: str, depth: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    provider = _CanonicalProvider() if pathway == "FULL_CREDIT" else None
    ledgers, runtime, case = _canonical_runtime_case(provider)
    try:
        run = runtime.start_run(case["id"], "analyst", pathway, depth, [])
        runtime._execute(run["id"], "analyst")
        completed = ledgers.runs.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded"
        return ledgers, case, completed
    finally:
        runtime.close()


def _app(ledgers: Any, storage_dir: Path) -> Any:
    return create_app(
        Settings(
            environment="test",
            storage_dir=storage_dir,
            deploy_v_root=DEPLOY_V,
        ),
        ledgers,
    )


def test_manual_model_request_reschedules_existing_queued_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Retry", "Issuer", "Testing", "analyst")
    app = _app(ledgers, tmp_path)
    queued = {
        "id": "model-retry",
        "case_id": case["id"],
        "accepted_run_id": "run-retry",
        "accepted_snapshot_id": "snapshot-retry",
        "source_set_id": "sources-retry",
        "input_fingerprint": "a" * 64,
        "status": "QUEUED",
        "queued_at": "2026-08-25T00:00:00+00:00",
        "started_at": None,
        "completed_at": None,
        "error": None,
        "export": {"status": "NOT_REQUESTED", "error": None},
        "worksheet_schema_version": "caos.model.worksheet.v1",
            "calculation_runtime": {
                "name": "cp-model",
                "version": "3.0",
                "sha256": "b" * 64,
                "assumption_registry_version": "cp-model-assumptions.v1",
                "assumption_registry_digest": "c" * 64,
                "calculation_contract_version": "cp-model-calculations.v4",
            },
    }
    scheduled: list[str] = []
    monkeypatch.setattr(
        app.state.model_readiness,
        "queue",
        lambda _case_id, _actor: (queued, False),
    )
    monkeypatch.setattr(
        app.state.model_runtime,
        "schedule",
        lambda build_id, _actor: scheduled.append(build_id),
    )

    client = TestClient(app)
    try:
        response = client.post(f"/api/cases/{case['id']}/models", headers=HEADERS)
    finally:
        client.close()

    assert response.status_code == 202 and response.json()["created"] is False
    assert scheduled == [queued["id"]]


def test_accepting_model_ready_full_credit_queues_after_commit_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledgers, case, run = _completed_case("FULL_CREDIT", "full")
    app = _app(ledgers, tmp_path)
    queue = app.state.model_readiness.queue
    scheduled: list[str] = []

    def queue_after_commit(case_id: str, actor: str) -> tuple[dict[str, Any], bool]:
        accepted = ledgers.runs.get_run(run["id"])
        assert accepted is not None and accepted["accepted_snapshot_id"] is not None
        return queue(case_id, actor)

    monkeypatch.setattr(app.state.model_readiness, "queue", queue_after_commit)
    monkeypatch.setattr(
        app.state.model_runtime,
        "schedule",
        lambda build_id, _actor: scheduled.append(build_id),
    )

    with TestClient(app) as client:
        first = client.post(f"/api/runs/{run['id']}/accept", headers=HEADERS)
        duplicate = client.post(
            f"/api/runs/{run['id']}/accept", headers=HEADERS
        )

    builds = ledgers.models.list_builds(case["id"])
    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == first.json()["id"]
    assert len(builds) == 1
    assert scheduled == [builds[0]["id"]]


def test_acceptance_survives_queue_failure_and_manual_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledgers, case, run = _completed_case("FULL_CREDIT", "full")
    app = _app(ledgers, tmp_path)
    queue = app.state.model_readiness.queue

    def fail_after_commit(_case_id: str, _actor: str) -> None:
        accepted = ledgers.runs.get_run(run["id"])
        assert accepted is not None and accepted["accepted_snapshot_id"] is not None
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(app.state.model_readiness, "queue", fail_after_commit)
    monkeypatch.setattr(app.state.model_runtime, "schedule", lambda *_args: None)

    with TestClient(app) as client:
        accepted = client.post(
            f"/api/runs/{run['id']}/accept", headers=HEADERS
        )
        monkeypatch.setattr(app.state.model_readiness, "queue", queue)
        readiness = client.get(
            f"/api/cases/{case['id']}/model", headers=HEADERS
        )
        retry = client.post(f"/api/cases/{case['id']}/models", headers=HEADERS)

    assert accepted.status_code == 200
    assert ledgers.runs.get_run(run["id"])["accepted_snapshot_id"] == accepted.json()["id"]
    assert readiness.json()["status"] == "READY_TO_BUILD"
    assert retry.status_code == 202 and retry.json()["created"] is True


def test_acceptance_survives_schedule_failure_with_retryable_queued_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledgers, case, run = _completed_case("FULL_CREDIT", "full")
    app = _app(ledgers, tmp_path)

    def fail_schedule(_build_id: str, _actor: str) -> None:
        raise RuntimeError("executor unavailable")

    monkeypatch.setattr(app.state.model_runtime, "schedule", fail_schedule)

    with TestClient(app) as client:
        accepted = client.post(
            f"/api/runs/{run['id']}/accept", headers=HEADERS
        )
        readiness = client.get(
            f"/api/cases/{case['id']}/model", headers=HEADERS
        )
        scheduled: list[str] = []
        monkeypatch.setattr(
            app.state.model_runtime,
            "schedule",
            lambda build_id, _actor: scheduled.append(build_id),
        )
        retry = client.post(f"/api/cases/{case['id']}/models", headers=HEADERS)

    builds = ledgers.models.list_builds(case["id"])
    assert accepted.status_code == 200
    assert len(builds) == 1 and builds[0]["status"] == "QUEUED"
    assert readiness.json()["status"] == "QUEUED"
    assert retry.status_code == 202 and retry.json()["created"] is False
    assert scheduled == [builds[0]["id"]]
    assert ledgers.models.pending_jobs() == [(builds[0]["id"], "analyst", "calculate")]


def test_acceptance_does_not_queue_non_full_credit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledgers, case, run = _completed_case("EARNINGS_UPDATE", "screen")
    app = _app(ledgers, tmp_path)
    queue_calls: list[str] = []

    monkeypatch.setattr(
        app.state.model_readiness,
        "queue",
        lambda case_id, _actor: queue_calls.append(case_id),
    )
    with TestClient(app) as client:
        response = client.post(
            f"/api/runs/{run['id']}/accept", headers=HEADERS
        )

    assert response.status_code == 200
    assert queue_calls == []
    assert ledgers.models.list_builds(case["id"]) == []


def test_acceptance_does_not_queue_not_ready_full_credit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledgers, case, run = _completed_case("FULL_CREDIT", "full")
    app = _app(ledgers, tmp_path / "not-ready")
    monkeypatch.setattr(
        app.state.model_readiness,
        "readiness",
        lambda _case_id: app.state.model_readiness._not_ready(
            "CANONICAL_MODEL_INPUTS_INVALID", "invalid"
        ),
    )
    monkeypatch.setattr(
        app.state.model_readiness,
        "queue",
        lambda *_args: pytest.fail("a non-ready snapshot must not be queued"),
    )
    with TestClient(app) as client:
        response = client.post(
            f"/api/runs/{run['id']}/accept", headers=HEADERS
        )

    assert response.status_code == 200
    assert ledgers.models.list_builds(case["id"]) == []
