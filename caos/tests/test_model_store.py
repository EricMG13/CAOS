from __future__ import annotations

import copy
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from caos.contracts import digest
from caos.migrations import apply_migrations, migration_files
from caos.store import JobFencedError, MAX_ACTIVE_JOBS, MemoryStore, PostgresStore


def _accepted_build(store: MemoryStore, *, build_id: str | None = None) -> dict[str, Any]:
    case = store.create_case("Model test", f"Issuer-{uuid.uuid4().hex}", "Testing", "analyst")
    source_set = {
        "id": store._id("set"),
        "case_id": case["id"],
        "version": 1,
        "source_ids": [],
        "created_by": "analyst",
        "created_at": "2026-08-24T00:00:00+00:00",
    }
    store.register_source_set(source_set)
    run = store.create_run(case["id"], "analyst", {"source_set_id": source_set["id"]}, [])
    store.update_run(run["id"], status="succeeded")
    snapshot = store.accept_snapshot(
        case["id"],
        run["id"],
        "analyst",
        {
            "id": store._id("snap"),
            "case_id": case["id"],
            "run_id": run["id"],
            "source_set_id": source_set["id"],
            "source_set_version": 1,
            "artifacts": [],
            "accepted_at": "2026-08-24T00:00:00+00:00",
            "digest": "b" * 64,
        },
    )
    return {
        "id": build_id or store._id("model"),
        "case_id": case["id"],
        "accepted_run_id": run["id"],
        "accepted_snapshot_id": snapshot["id"],
        "source_set_id": source_set["id"],
        "input_fingerprint": "a" * 64,
        "worksheet_schema_version": "caos.model.worksheet.v1",
    }


def _model_result() -> dict[str, Any]:
    payload = {
        "schema_version": "caos.model.worksheet.v1",
        "identity": {
            "issuer_id": "issuer",
            "issuer_name": "Issuer",
            "analysis_date": "2026-08-24",
        },
        "tabs": [
            {
                "id": "MODEL",
                "name": "Model",
                "max_row": 1,
                "max_column": 1,
                "freeze_panes": "",
                "merged_cells": [],
                "columns": [
                    {"column": 1, "letter": "A", "width": 12.0, "hidden": False}
                ],
                "cells": [],
            }
        ],
    }
    return {
        "payload": payload,
        "payload_digest": digest(payload),
        "qa": {
            "status": "PASS",
            "semantic_checks": [],
            "semantic_check_count": 0,
            "formula_count": 0,
            "worksheet_cell_count": 0,
            "limitation_flags": [],
            "validation_warnings": [],
            "source_manifest": [],
        },
    }


def test_memory_model_build_lifecycle_is_idempotent_fenced_and_export_independent() -> None:
    store = MemoryStore()
    build = _accepted_build(store)

    queued, created = store.queue_model_build({**build, "export": {"status": "READY"}}, "analyst")
    duplicate, duplicate_created = store.queue_model_build({**build, "id": "model-duplicate"}, "analyst")
    token = store.claim_model_job(build["id"], "worker")

    assert created is True and duplicate_created is False and duplicate["id"] == queued["id"]
    assert queued["export"] == {"status": "NOT_REQUESTED", "error": None}
    assert token is not None and store.claim_model_job(build["id"], "other") is None
    assert store.renew_model_job(build["id"], token) is True
    ready = store.complete_model_job(build["id"], token, _model_result(), "worker")

    assert ready["status"] == "READY"
    assert ready["export"]["status"] == "NOT_REQUESTED"
    assert store.get_model_build(build["id"]) == ready
    assert store.list_model_builds(build["case_id"]) == [ready]
    assert store.model_job_is_current(build["id"], token) is False

    exporting, queued_export = store.queue_model_export(build["id"], "approver")
    export_token = store.claim_model_job(build["id"], "export-worker", "export")
    assert queued_export is True and exporting["status"] == "READY" and export_token is not None
    assert store.model_jobs[f"{build['id']}:export"]["actor"] == "approver"
    export_failed = store.fail_model_job(
        build["id"],
        export_token,
        {"code": "MODEL_EXPORT_FAILED", "detail": "LibreOffice unavailable"},
        "export-worker",
        "export",
    )
    assert export_failed["status"] == "READY" and export_failed["export"]["status"] == "FAILED"
    retried, retry_queued = store.queue_model_export(build["id"], "analyst")
    assert retry_queued is True and retried["status"] == "READY" and retried["export"]["status"] == "QUEUED"


def test_model_completion_rejects_incomplete_or_mismatched_results() -> None:
    store = MemoryStore()
    build = _accepted_build(store)
    store.queue_model_build(build, "analyst")
    token = store.claim_model_job(build["id"], "worker")
    assert token is not None
    valid = _model_result()
    incomplete_cell = copy.deepcopy(valid)
    incomplete_cell["payload"]["tabs"][0]["cells"] = [{"address": "A1"}]
    incomplete_cell["qa"]["worksheet_cell_count"] = 1
    incomplete_cell["payload_digest"] = digest(incomplete_cell["payload"])
    nonfinite_column = copy.deepcopy(valid)
    nonfinite_column["payload"]["tabs"][0]["columns"][0]["width"] = float("nan")
    nonfinite_column["payload_digest"] = digest(nonfinite_column["payload"])
    invalid_results = [
        {"payload": valid["payload"], "payload_digest": valid["payload_digest"]},
        {**valid, "payload_digest": "0" * 64},
        {**valid, "unexpected": True},
        incomplete_cell,
        nonfinite_column,
    ]

    for result in invalid_results:
        with pytest.raises(ValueError, match="MODEL_RESULT_INVALID"):
            store.complete_model_job(build["id"], token, result, "worker")
        assert store.get_model_build(build["id"])["status"] == "BUILDING"

    ready = store.complete_model_job(build["id"], token, valid, "worker")
    valid["payload"]["identity"]["issuer_name"] = "mutated after completion"
    assert ready["status"] == "READY"
    assert store.get_model_build(build["id"])["payload"]["identity"]["issuer_name"] == "Issuer"


def test_memory_model_takeover_fences_stale_worker_and_bounds_errors() -> None:
    store = MemoryStore()
    build = _accepted_build(store)
    store.queue_model_build(build, "analyst")
    stale = store.claim_model_job(build["id"], "stale")
    assert stale is not None
    store.model_jobs[f"{build['id']}:calculate"]["lease_until"] = time.monotonic() - 1

    replacement = store.claim_model_job(build["id"], "replacement")

    assert replacement is not None
    with pytest.raises(JobFencedError):
        store.complete_model_job(build["id"], stale, {"payload": {}}, "stale")
    with pytest.raises(ValueError, match="MODEL_ERROR_INVALID"):
        store.fail_model_job(build["id"], replacement, {"code": "X", "detail": "x" * 501}, "replacement")
    failed = store.fail_model_job(
        build["id"], replacement, {"code": "MODEL_CALCULATION_FAILED", "detail": "bounded"}, "replacement"
    )
    assert failed["status"] == "FAILED" and failed["export"]["status"] == "NOT_REQUESTED"


def test_failed_model_build_can_be_retried_without_changing_identity() -> None:
    store = MemoryStore()
    build = _accepted_build(store)
    queued, _created = store.queue_model_build(build, "analyst")
    token = store.claim_model_job(queued["id"], "worker")
    assert token is not None
    store.fail_model_job(
        queued["id"],
        token,
        {"code": "MODEL_CALCULATION_FAILED", "detail": "bounded"},
        "worker",
    )

    retried = store.retry_model_build(queued["id"], "approver")

    assert retried["id"] == queued["id"]
    assert retried["input_fingerprint"] == queued["input_fingerprint"]
    assert retried["status"] == "QUEUED" and retried["error"] is None
    assert store.model_jobs[f"{queued['id']}:calculate"]["actor"] == "approver"
    assert store.claim_model_job(queued["id"], "replacement") is not None


def test_memory_model_writes_roll_back_and_share_the_workflow_budget() -> None:
    class FailingStore(MemoryStore):
        fail = False

        def persist(self) -> None:
            if self.fail:
                raise RuntimeError("database unavailable")

    store = FailingStore()
    build = _accepted_build(store)
    before = copy.deepcopy((store.model_builds, store.model_jobs, store.audit))
    store.fail = True
    with pytest.raises(RuntimeError, match="database unavailable"):
        store.queue_model_build(build, "analyst")
    assert (store.model_builds, store.model_jobs, store.audit) == before

    store.fail = False
    store.queue_model_build(build, "analyst")
    assert store.claim_model_job(build["id"], "model-worker") is not None
    workflow_tokens = [store.claim_job(f"run-{index}", "worker") for index in range(MAX_ACTIVE_JOBS)]
    assert sum(token is not None for token in workflow_tokens) == MAX_ACTIVE_JOBS - 1


def test_model_build_rejects_unaccepted_or_cross_case_inputs() -> None:
    store = MemoryStore()
    build = _accepted_build(store)
    other = _accepted_build(store)

    with pytest.raises(ValueError, match="MODEL_BUILD_INVALID"):
        store.queue_model_build({**build, "source_set_id": other["source_set_id"]}, "analyst")
    store.runs[build["accepted_run_id"]]["accepted_snapshot_id"] = None
    with pytest.raises(ValueError, match="MODEL_BUILD_INVALID"):
        store.queue_model_build(build, "analyst")


def test_migration_runner_applies_ordered_files_once(tmp_path: Path) -> None:
    (tmp_path / "002_second.sql").write_text("SELECT 2", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1", encoding="utf-8")
    (tmp_path / "notes.sql").write_text("SELECT 0", encoding="utf-8")

    class Cursor:
        def __init__(self) -> None:
            self.applied: set[str] = set()
            self.result: tuple[int] | None = None

        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, statement: str, parameters: tuple[str] | None = None) -> None:
            if statement.startswith("SELECT 1 FROM schema_migrations"):
                self.result = (1,) if parameters and parameters[0] in self.applied else None
            elif statement.startswith("INSERT INTO schema_migrations") and parameters:
                self.applied.add(parameters[0])

        def fetchone(self) -> tuple[int] | None:
            return self.result

    class Connection:
        cursor_value = Cursor()

        def cursor(self) -> Cursor:
            return self.cursor_value

    connection = Connection()
    assert [path.name for path in migration_files(tmp_path)] == ["001_first.sql", "002_second.sql"]
    assert apply_migrations(connection, tmp_path) == ("001_first", "002_second")
    assert apply_migrations(connection, tmp_path) == ()


def test_postgres_model_queue_is_unique_and_takeover_is_fenced() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable model job proof")
    first = PostgresStore(database_url)
    build = _accepted_build(first)
    second = PostgresStore(database_url)
    competing = {**build, "id": first._id("model")}

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda item: item[0].queue_model_build(item[1], "analyst"),
                ((first, build), (second, competing)),
            )
        )
    assert sum(created for _record, created in results) == 1
    build_id = results[0][0]["id"]
    assert results[1][0]["id"] == build_id

    worker = PostgresStore(database_url)
    stale = worker.claim_model_job(build_id, "stale")
    assert stale is not None
    with worker._psycopg.connect(worker._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE model_build_jobs SET lease_until=now() - interval '1 second' WHERE build_id=%s",
                (build_id,),
            )
        connection.commit()
    replacement_store = PostgresStore(database_url)
    replacement = replacement_store.claim_model_job(build_id, "replacement")
    assert replacement is not None
    assert replacement_store.model_jobs[f"{build_id}:calculate"]["actor"] == "analyst"
    with pytest.raises(JobFencedError):
        worker.complete_model_job(build_id, stale, {"payload": {}}, "stale")
    ready = replacement_store.complete_model_job(build_id, replacement, _model_result(), "replacement")
    assert ready["status"] == "READY" and ready["export"]["status"] == "NOT_REQUESTED"
    with replacement_store._psycopg.connect(replacement_store._dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, record, (SELECT count(*) FROM model_builds "
                "WHERE case_id=%s AND input_fingerprint=%s) FROM model_builds WHERE id=%s",
                (build["case_id"], build["input_fingerprint"], build_id),
            )
            row = cursor.fetchone()
    assert row is not None and row[0] == "READY" and row[1] == ready and row[2] == 1
