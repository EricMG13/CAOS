from __future__ import annotations

import ast
import copy
import hashlib
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import ALL_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

import pytest

from caos import ledgers
from caos.contracts import clean_json, digest
from caos.memory_ledgers import MemoryLedgerSet
from caos.postgres_ledgers import PostgresLedgerSet
from caos.store import JobFencedError
from ledger_helpers import tamper_thesis_version


ACTOR = "analyst"
LEASE_SECONDS = 0.2
POSTGRES_URL = os.getenv("CAOS_TEST_DATABASE_URL")
PROTOCOL_METHOD_COUNT = 72
RACE_HARNESS_TIMEOUT_SECONDS = 12


class CopyFailure(RuntimeError):
    pass


class _Uncopyable:
    def __deepcopy__(self, memo: dict[int, Any]) -> Any:
        raise CopyFailure("copy failed")


def _shared_behavior_calls() -> dict[str, set[str]]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = {port: set() for port in ("sources", "runs", "publications", "models")}
    for function in (
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(argument.arg == "ledger_set" for argument in node.args.args)
    ):
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "ledger_set"
                and node.func.value.attr in calls
            ):
                calls[node.func.value.attr].add(node.func.attr)
    return calls


def _postgres_test_dsn() -> str:
    assert POSTGRES_URL is not None
    from psycopg.conninfo import make_conninfo

    dsn = POSTGRES_URL.replace("postgresql+psycopg://", "postgresql://")
    return make_conninfo(
        dsn,
        connect_timeout=3,
        options="-c lock_timeout=2s -c statement_timeout=5s",
    )


def _reset_postgres() -> None:
    if not POSTGRES_URL:
        return
    import psycopg

    dsn = _postgres_test_dsn()
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE TABLE cases, methodology_drafts, rv_universes, "
            "audit_events RESTART IDENTITY CASCADE"
        )


@pytest.fixture(params=["memory", "postgres"])
def ledger_set(request: pytest.FixtureRequest) -> Any:
    if request.param == "memory":
        return MemoryLedgerSet(lease_seconds=LEASE_SECONDS)
    if not POSTGRES_URL:
        pytest.skip("CAOS_TEST_DATABASE_URL is not set")
    _reset_postgres()
    return PostgresLedgerSet(_postgres_test_dsn(), lease_seconds=LEASE_SECONDS)


@pytest.fixture
def postgres_pair() -> tuple[Any, Any]:
    if not POSTGRES_URL:
        pytest.skip("CAOS_TEST_DATABASE_URL is not set")
    _reset_postgres()
    dsn = _postgres_test_dsn()
    return (
        PostgresLedgerSet(dsn, lease_seconds=LEASE_SECONDS),
        PostgresLedgerSet(dsn, lease_seconds=LEASE_SECONDS),
    )


def _bounded_parallel(*operations: Callable[[], Any]) -> list[Any]:
    executor = ThreadPoolExecutor(max_workers=len(operations))
    futures: list[Future[Any]] = []
    pending: set[Future[Any]] = set()
    try:
        futures = [executor.submit(operation) for operation in operations]
        _, pending = wait(
            futures,
            timeout=RACE_HARNESS_TIMEOUT_SECONDS,
            return_when=ALL_COMPLETED,
        )
    finally:
        # Worker SQL is independently bounded by connect/lock/statement timeouts,
        # so joining here cannot strand live connections in later tests.
        executor.shutdown(wait=True, cancel_futures=True)
    if pending:
        pytest.fail("PostgreSQL race exceeded its database and harness timeouts")
    return [future.result() for future in futures]


def _case(ledger_set: Any) -> dict[str, Any]:
    return ledger_set.runs.create_case("Contract case", "Issuer", "Testing", ACTOR)


def _source(case_id: str, *, sha256: str = "a" * 64) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "filename": "evidence.txt",
        "media_type": "text/plain",
        "bytes": 8,
        "sha256": sha256,
        "vault_path": "sources/aa/evidence.txt",
        "blocks": [
            {
                "block_id": "b00001",
                "locator": {"line": 1},
                "text": "Debt 100",
                "extractor_version": "contract-v1",
                "confidence": "HIGH",
                "untrusted_data": True,
            }
        ],
        "created_by": ACTOR,
        "created_at": "2026-08-24T00:00:00+00:00",
        "withdrawn": False,
    }


def _queued_run(ledger_set: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [
            {
                "module_id": "CP-1",
                "dependencies": [],
                "stage": 1,
            }
        ],
    )
    return case, run


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


def _export_result(build: dict[str, Any]) -> dict[str, Any]:
    sha256 = "e" * 64
    return {
        "vault_key": f"models/{build['case_id']}/{build['id']}/{sha256}.xlsx",
        "filename": "credit-model.xlsx",
        "sha256": sha256,
        "size": 1024,
        "formulas_validated": 0,
        "semantic_checks": 0,
        "renderer_version": "contract-v1",
        "renderer_sha256": "f" * 64,
        "calculation_engine": "LibreOffice",
    }


def _accept_empty_run(
    ledger_set: Any, case_id: str, source_set: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    run = ledger_set.runs.create_run_with_nodes(
        case_id,
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [],
    )
    token = ledger_set.runs.claim(run["id"], "workflow-worker")
    assert token is not None
    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})
    snapshot_payload = {
        "case_id": case_id,
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": [],
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }
    snapshot = ledger_set.runs.accept_snapshot(
        case_id,
        run["id"],
        ACTOR,
        {**snapshot_payload, "digest": digest(snapshot_payload)},
    )
    return run, snapshot


def _accepted_model_input(ledger_set: Any) -> dict[str, Any]:
    case = _case(ledger_set)
    ingested = ledger_set.sources.ingest(_source(case["id"]), ACTOR)
    source_set = ingested["source_set"]
    run, snapshot = _accept_empty_run(ledger_set, case["id"], source_set)
    return {
        "case_id": case["id"],
        "accepted_run_id": run["id"],
        "accepted_snapshot_id": snapshot["id"],
        "source_set_id": source_set["id"],
        "input_fingerprint": "c" * 64,
        "worksheet_schema_version": "caos.model.worksheet.v1",
    }


def _report_record(
    snapshot: dict[str, Any],
    inputs: dict[str, Any],
    model_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_fingerprint = digest(
        clean_json(
            {
                "snapshot": snapshot,
                "thesis": inputs["thesis"],
                "recommendations": inputs["recommendations"],
                "model": model_identity,
            }
        )
    )
    content = {
        "case_id": snapshot["case_id"],
        "snapshot_id": snapshot["id"],
        "snapshot_digest": digest(snapshot),
        "thesis_version": inputs["thesis"]["version"],
        "recommendation_version": inputs["recommendations"]["version"],
        "include_model": model_identity is not None,
        "model": model_identity,
        "input_fingerprint": input_fingerprint,
    }
    preview_digest = digest(content)
    return {
        "case_id": snapshot["case_id"],
        "status": "PENDING_APPROVAL",
        "preview_digest": preview_digest,
        "digest": preview_digest,
        "input_fingerprint": input_fingerprint,
        "snapshot_digest": content["snapshot_digest"],
        "content": content,
        "markdown": "# Frozen report\n",
    }


def test_protocol_inventory_is_exact(ledger_set: Any) -> None:
    assert {
        name
        for name, value in vars(ledgers).items()
        if getattr(value, "_is_protocol", False)
        and getattr(value, "__module__", None) == ledgers.__name__
    } == {"SourceCatalog", "RunLedger", "PublicationLedger", "ModelLedger"}
    ports = (
        ("sources", ledgers.SourceCatalog),
        ("runs", ledgers.RunLedger),
        ("publications", ledgers.PublicationLedger),
        ("models", ledgers.ModelLedger),
    )
    shared_calls = _shared_behavior_calls()
    method_count = 0
    for port_name, protocol in ports:
        adapter = getattr(ledger_set, port_name)
        methods = {
            name
            for name, value in vars(protocol).items()
            if callable(value) and not name.startswith("_")
        }
        method_count += len(methods)
        assert all(callable(getattr(adapter, name, None)) for name in methods)
        assert shared_calls[port_name] == methods
    assert method_count == PROTOCOL_METHOD_COUNT


def test_source_duplicate_and_withdrawal_are_atomic(ledger_set: Any) -> None:
    case = _case(ledger_set)
    source = _source(case["id"])
    assert "id" not in source
    first = ledger_set.sources.ingest(source, ACTOR)
    source_id = first["id"]
    assumption = ledger_set.publications.create_assumption(
        case["id"], ACTOR, "Debt is 100", [source_id], ["CP-1"]
    )
    loan, created = ledger_set.sources.save_loan_universe_import(
        {
            "case_id": case["id"],
            "source_id": source_id,
            "source_filename": first["filename"],
            "source_sha256": first["sha256"],
            "workbook_date": "2026-08-24",
            "template_version": "contract-template-v1",
            "importer_version": "contract-importer-v1",
            "universe_digest": "f" * 64,
            "row_count": 1,
            "status": "ACTIVE",
            "findings": [],
        },
        [{"instrument_key": "loan-1", "borrower": "Issuer"}],
        ACTOR,
    )
    assert created is True
    before_sources = ledger_set.sources.list_sources(case["id"])
    before_set = ledger_set.sources.current_source_set(case["id"])
    historical_set = copy.deepcopy(first["source_set"])

    with pytest.raises(ValueError, match="source content already active"):
        ledger_set.sources.ingest(source, ACTOR)

    assert ledger_set.sources.list_sources(case["id"]) == before_sources
    assert ledger_set.sources.current_source_set(case["id"]) == before_set
    assert ledger_set.sources.withdraw("case_missing", source_id, ACTOR) is None
    assert ledger_set.sources.current_source_set(case["id"]) == before_set
    assert ledger_set.publications.list_assumptions(case["id"]) == [assumption]
    assert ledger_set.sources.active_loan_universe(case["id"])["id"] == loan["id"]

    withdrawn = ledger_set.sources.withdraw(case["id"], source_id, ACTOR)

    assert withdrawn is not None and withdrawn["withdrawn"] is True
    assert ledger_set.sources.list_sources(case["id"]) == []
    withdrawn_set = ledger_set.sources.current_source_set(case["id"])
    assert withdrawn_set is not None
    assert withdrawn_set["version"] == first["source_set"]["version"] + 1
    assert withdrawn_set["source_ids"] == []
    assert ledger_set.sources.source_set(historical_set["id"]) == historical_set
    assert ledger_set.publications.list_assumptions(case["id"])[0]["status"] == "STALE"
    assert ledger_set.sources.active_loan_universe(case["id"]) is None
    withdrawn_loan = ledger_set.sources.find_loan_universe_import(
        case["id"],
        first["sha256"],
        "contract-template-v1",
        "contract-importer-v1",
    )
    assert withdrawn_loan is not None and withdrawn_loan["status"] == "WITHDRAWN"
    assert ledger_set.sources.withdraw(case["id"], source_id, ACTOR) == withdrawn
    assert ledger_set.sources.current_source_set(case["id"]) == withdrawn_set
    replacement = ledger_set.sources.ingest(source, ACTOR)
    assert replacement["source_set"]["version"] == withdrawn_set["version"] + 1
    assert ledger_set.sources.source_set(historical_set["id"]) == historical_set


def test_pinned_evidence_is_validated_in_one_catalog_read(ledger_set: Any) -> None:
    case = _case(ledger_set)
    first = ledger_set.sources.ingest(_source(case["id"]), ACTOR)
    pinned = first["source_set"]
    second = ledger_set.sources.ingest(_source(case["id"], sha256="b" * 64), ACTOR)

    evidence = ledger_set.sources.read_pinned_evidence(
        case["id"], pinned["id"], first["id"], ["b00001"]
    )
    assert evidence == [
        {
            "source_id": first["id"],
            "source_digest": first["sha256"],
            "origin_family": first["sha256"],
            "authority_class": "unclassified",
            "block_id": "b00001",
            "locator": {"line": 1},
            "extractor_version": "contract-v1",
            "confidence": "HIGH",
            "text": "Debt 100",
        }
    ]

    with pytest.raises(ValueError, match="AGENT_AUTHORITY_MISMATCH"):
        ledger_set.sources.read_pinned_evidence(
            case["id"], pinned["id"], second["id"], ["b00001"]
        )
    with pytest.raises(ValueError, match="AGENT_AUTHORITY_MISMATCH"):
        ledger_set.sources.read_pinned_evidence(
            "case_foreign", pinned["id"], first["id"], ["b00001"]
        )
    with pytest.raises(ValueError, match="AGENT_OUTPUT_INVALID"):
        ledger_set.sources.read_pinned_evidence(
            case["id"], pinned["id"], first["id"], ["missing"]
        )

    ledger_set.sources.withdraw(case["id"], first["id"], ACTOR)
    with pytest.raises(ValueError, match="AGENT_AUTHORITY_MISMATCH"):
        ledger_set.sources.read_pinned_evidence(
            case["id"], pinned["id"], first["id"], ["b00001"]
        )


def test_run_and_nodes_are_created_as_one_pending_transition(
    ledger_set: Any,
) -> None:
    case, run = _queued_run(ledger_set)

    assert run["case_id"] == case["id"]
    assert run["status"] == "queued"
    assert [node["module_id"] for node in run["nodes"]] == ["CP-1"]
    assert run["node_ids"] == [run["nodes"][0]["id"]]
    assert ledger_set.runs.get_case(case["id"])["current_execution_id"] == run["id"]
    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]


def test_run_creation_persists_initial_state_and_only_queues_schedulable_runs(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    error = {
        "code": "SOURCE_SET_EMPTY",
        "message": "Upload and version source material before execution.",
    }
    research = {"phase": "planning", "budget_used": {"turns": 0}}
    canonical_generation = {
        "phase": "generating",
        "completed_modules": [],
        "reporting_period": "1900-01-01",
    }

    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "DEEP_RESEARCH", "source_set_id": None},
        [{"module_id": "CP-DR", "dependencies": [], "stage": 1}],
        initial_status="paused",
        initial_error=error,
        initial_research=research,
        canonical_generation=canonical_generation,
    )

    assert run["status"] == "paused"
    assert run["error"] == error
    assert run["research"] == research
    assert run["canonical_generation"] == {
        **canonical_generation,
        "reporting_period": run["created_at"][:10],
    }
    assert ledger_set.runs.get_run(run["id"]) == run
    assert ledger_set.runs.pending_runs() == []


def test_run_claim_has_one_winner(ledger_set: Any) -> None:
    _, run = _queued_run(ledger_set)

    with ThreadPoolExecutor(max_workers=2) as executor:
        tokens = list(
            executor.map(
                lambda worker: ledger_set.runs.claim(run["id"], worker),
                ("worker-a", "worker-b"),
            )
        )

    assert sum(token is not None for token in tokens) == 1


def test_research_approval_requeues_the_finished_planning_job(ledger_set: Any) -> None:
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    proposed_plan = {
        "source_set": {"id": source_set["id"], "version": source_set["version"]},
        "workstreams": [],
    }
    plan_hash = f"sha256:{digest(proposed_plan)}"
    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "DEEP_RESEARCH", "source_set_id": source_set["id"]},
        [{"module_id": "CP-DR", "dependencies": [], "stage": 1}],
        initial_research={"phase": "planning"},
    )
    token = ledger_set.runs.claim(run["id"], "planning-worker")
    assert token is not None
    ledger_set.runs.pause_research_plan(
        run["id"],
        token,
        run["nodes"][0]["id"],
        {
            "phase": "awaiting_approval",
            "proposed_plan": proposed_plan,
            "proposed_plan_hash": plan_hash,
        },
    )
    ledger_set.runs.finish(run["id"], token)

    approved = ledger_set.runs.approve_research_plan(run["id"], ACTOR, plan_hash)

    assert approved["status"] == "queued"
    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]
    assert ledger_set.runs.claim(run["id"], "research-worker") is not None


def test_expired_run_claim_recovers_running_nodes_and_fences_old_worker(
    ledger_set: Any,
) -> None:
    _, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    stale = ledger_set.runs.claim(run["id"], "stale-worker")
    assert stale is not None
    ledger_set.runs.update_node_fenced(
        run["id"], stale, node["id"], status="running", artifact_id="partial"
    )

    time.sleep(LEASE_SECONDS + 0.1)
    replacement = ledger_set.runs.claim(run["id"], "replacement-worker")

    assert replacement is not None and replacement != stale
    assert ledger_set.runs.is_current(run["id"], stale) is False
    recovered = ledger_set.runs.get_run(run["id"])
    assert recovered["nodes"][0]["status"] == "pending"
    assert recovered["nodes"][0]["artifact_id"] is None

    artifact_payload = {"debt": 100}
    artifact_digest = digest(artifact_payload)
    artifact = {
        "case_id": run["case_id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "created_by": ACTOR,
        "payload": artifact_payload,
        "markdown": "# CP-1\n\nDebt: 100\n",
        "digest": artifact_digest,
        "input_fingerprint": "fingerprint",
        "created_at": "2026-08-24T00:00:00+00:00",
    }
    assert "id" not in artifact
    event_data = {"node_id": node["id"], "module_id": node["module_id"]}
    before_events = ledger_set.runs.events_after(run["id"])
    with pytest.raises(JobFencedError, match="stale workflow attempt"):
        ledger_set.runs.complete_node(
            run["id"],
            stale,
            node["id"],
            artifact,
            research=None,
            event_data=event_data,
        )
    assert ledger_set.runs.events_after(run["id"]) == before_events
    assert ledger_set.runs.get_run(run["id"])["nodes"][0]["status"] == "pending"
    assert (
        ledger_set.runs.artifact_for_fingerprint(
            run["id"], node["module_id"], artifact["input_fingerprint"]
        )
        is None
    )

    ledger_set.runs.update_node_fenced(
        run["id"], replacement, node["id"], status="running"
    )
    with pytest.raises(ValueError, match="ARTIFACT_INVALID"):
        ledger_set.runs.complete_node(
            run["id"],
            replacement,
            node["id"],
            artifact,
            research=None,
            event_data=event_data,
            artifact_validator=lambda _: False,
        )
    rolled_back = ledger_set.runs.get_run(run["id"])
    assert rolled_back["nodes"][0]["status"] == "running"
    assert rolled_back["nodes"][0]["artifact_id"] is None
    assert ledger_set.runs.events_after(run["id"]) == before_events
    assert (
        ledger_set.runs.artifact_for_fingerprint(
            run["id"], node["module_id"], artifact["input_fingerprint"]
        )
        is None
    )

    completed = ledger_set.runs.complete_node(
        run["id"],
        replacement,
        node["id"],
        artifact,
        research=None,
        event_data=event_data,
    )
    completed_run = ledger_set.runs.get_run(run["id"])
    assert completed["id"] == completed_run["nodes"][0]["artifact_id"]
    assert completed["payload"] == artifact_payload
    assert completed["digest"] == artifact_digest
    assert ledger_set.runs.get_artifact(completed["id"]) == completed
    assert completed_run["nodes"][0]["status"] == "succeeded"
    events = ledger_set.runs.events_after(run["id"])
    assert events[:-1] == before_events
    assert events[-1]["id"] == len(before_events) + 1
    assert events[-1]["event"] == "node.succeeded"
    assert events[-1]["data"] == {**event_data, "artifact_id": completed["id"]}


@pytest.mark.parametrize("failing_argument", ["research", "event_data"])
def test_memory_complete_node_copy_failure_is_atomic(failing_argument: str) -> None:
    ledger_set = MemoryLedgerSet(lease_seconds=LEASE_SECONDS)
    _, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    ledger_set.runs.update_node_fenced(run["id"], token, node["id"], status="running")
    artifact = {
        "case_id": run["case_id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "payload": {"debt": 100},
        "digest": digest({"debt": 100}),
        "input_fingerprint": "copy-failure",
    }
    research: dict[str, Any] | None = {"phase": "complete"}
    event_data: dict[str, Any] = {"node_id": node["id"]}
    if failing_argument == "research":
        research = {"value": _Uncopyable()}
    else:
        event_data["value"] = _Uncopyable()
    before_run = ledger_set.runs.get_run(run["id"])
    before_events = ledger_set.runs.events_after(run["id"])
    validator_calls = 0

    def accept_artifact(candidate: dict[str, Any]) -> bool:
        nonlocal validator_calls
        validator_calls += 1
        return True

    with pytest.raises(CopyFailure, match="copy failed"):
        ledger_set.runs.complete_node(
            run["id"],
            token,
            node["id"],
            artifact,
            research,
            event_data,
            artifact_validator=accept_artifact,
        )

    assert validator_calls == 1
    assert ledger_set.runs.get_run(run["id"]) == before_run
    assert ledger_set.runs.events_after(run["id"]) == before_events
    assert (
        ledger_set.runs.artifact_for_fingerprint(
            run["id"], node["module_id"], artifact["input_fingerprint"]
        )
        is None
    )


def test_snapshot_acceptance_updates_case_and_run_together(
    ledger_set: Any,
) -> None:
    case, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    ledger_set.runs.update_node_fenced(run["id"], token, node["id"], status="running")
    artifact_payload = {"debt": 100}
    artifact = ledger_set.runs.complete_node(
        run["id"],
        token,
        node["id"],
        {
            "case_id": case["id"],
            "run_id": run["id"],
            "module_id": node["module_id"],
            "input_fingerprint": "snapshot-fingerprint",
            "payload": artifact_payload,
            "digest": digest(artifact_payload),
        },
        research=None,
        event_data={"node_id": node["id"], "module_id": node["module_id"]},
    )
    assert set(artifact) == {
        "id",
        "case_id",
        "run_id",
        "module_id",
        "input_fingerprint",
        "payload",
        "digest",
    }
    source_set = ledger_set.sources.source_set(run["plan"]["source_set_id"])
    assert source_set is not None
    artifact_ref = {
        "id": artifact["id"],
        "module_id": artifact["module_id"],
        "digest": artifact["digest"],
    }
    base_payload = {
        "case_id": case["id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": [artifact_ref],
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }
    assert "id" not in base_payload

    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        ledger_set.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {**base_payload, "digest": digest(base_payload)},
        )
    assert ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] is None
    assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] is None

    ledger_set.runs.update_run_fenced(run["id"], token, status="succeeded")
    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        ledger_set.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {**base_payload, "digest": digest(base_payload)},
        )

    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})

    invalid_payloads = [
        ("RUN_NOT_FOUND", {**base_payload, "case_id": "case_foreign"}),
        ("RUN_NOT_FOUND", {**base_payload, "run_id": "run_foreign"}),
        (
            "SOURCE_SET_CHANGED",
            {**base_payload, "source_set_version": source_set["version"] + 1},
        ),
        (
            "SOURCE_SET_CHANGED",
            {**base_payload, "source_set_id": "source_set_missing"},
        ),
        (
            "RUN_NOT_READY",
            {
                **base_payload,
                "artifacts": [{**artifact_ref, "digest": "0" * 64}],
            },
        ),
    ]
    for error, payload in invalid_payloads:
        with pytest.raises(ValueError, match=error):
            ledger_set.runs.accept_snapshot(
                case["id"],
                run["id"],
                ACTOR,
                {**payload, "digest": digest(payload)},
            )
        assert ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] is None
        assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] is None

    foreign_case, foreign_run = _queued_run(ledger_set)
    foreign_node = foreign_run["nodes"][0]
    foreign_token = ledger_set.runs.claim(foreign_run["id"], "foreign-worker")
    assert foreign_token is not None
    ledger_set.runs.update_node_fenced(
        foreign_run["id"], foreign_token, foreign_node["id"], status="running"
    )
    foreign_payload = {"debt": 200}
    foreign_artifact = ledger_set.runs.complete_node(
        foreign_run["id"],
        foreign_token,
        foreign_node["id"],
        {
            "case_id": foreign_case["id"],
            "run_id": foreign_run["id"],
            "module_id": foreign_node["module_id"],
            "input_fingerprint": "foreign-fingerprint",
            "payload": foreign_payload,
            "digest": digest(foreign_payload),
        },
        research=None,
        event_data={
            "node_id": foreign_node["id"],
            "module_id": foreign_node["module_id"],
        },
    )
    foreign_ref = {
        "id": foreign_artifact["id"],
        "module_id": foreign_artifact["module_id"],
        "digest": foreign_artifact["digest"],
    }
    foreign_artifact_payload = {**base_payload, "artifacts": [foreign_ref]}
    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        ledger_set.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {
                **foreign_artifact_payload,
                "digest": digest(foreign_artifact_payload),
            },
        )
    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        ledger_set.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {**base_payload, "digest": "0" * 64},
        )

    assert ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] is None
    assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] is None

    accepted = ledger_set.runs.accept_snapshot(
        case["id"],
        run["id"],
        ACTOR,
        {**base_payload, "digest": digest(base_payload)},
    )

    assert accepted["previous_snapshot_id"] is None
    assert ledger_set.runs.get_snapshot(accepted["id"]) == accepted
    assert (
        ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] == accepted["id"]
    )
    assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] == accepted["id"]


def test_success_finalization_retires_claim_before_finish_and_fences_snapshot(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [],
    )
    token = ledger_set.runs.claim(run["id"], "final-worker")
    assert token is not None
    assert ledger_set.runs.renew(run["id"], token) is True

    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})
    ledger_set.runs.finalize_success(
        run["id"],
        token,
        None,
        {"ignored": "retry"},
        deadline=time.monotonic() - 1,
    )

    finalized = ledger_set.runs.get_run(run["id"])
    assert finalized is not None
    assert "final_attempt_token" not in finalized
    assert set(finalized) == set(run)
    assert ledger_set.runs.is_current(run["id"], token) is False
    assert ledger_set.runs.pending_runs() == []
    time.sleep(LEASE_SECONDS + 0.1)
    assert ledger_set.runs.claim(run["id"], "takeover-worker") is None
    ledger_set.runs.finish(run["id"], token)
    ledger_set.runs.finish(run["id"], token)

    snapshot_payload = {
        "case_id": case["id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": [],
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }
    snapshot = ledger_set.runs.accept_snapshot(
        case["id"],
        run["id"],
        ACTOR,
        {**snapshot_payload, "digest": digest(snapshot_payload)},
    )
    assert snapshot["run_id"] == run["id"]
    assert [event["event"] for event in ledger_set.runs.events_after(run["id"])] == [
        "run.succeeded",
        "snapshot.accepted",
    ]


def test_generic_success_update_cannot_establish_snapshot_authority(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [],
    )
    token = ledger_set.runs.claim(run["id"], "generic-worker")
    assert token is not None
    ledger_set.runs.update_run_fenced(run["id"], token, status="succeeded")
    ledger_set.runs.finish(run["id"], token)
    events_before = ledger_set.runs.events_after(run["id"])
    snapshot_payload = {
        "case_id": case["id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": [],
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }

    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        ledger_set.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {**snapshot_payload, "digest": digest(snapshot_payload)},
        )

    assert ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] is None
    assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] is None
    assert ledger_set.runs.events_after(run["id"]) == events_before == []


def test_case_run_membership_research_events_and_visible_snapshot_contracts(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    assert ledger_set.runs.list_cases(ACTOR) == [case]
    assert ledger_set.runs.list_cases("outsider") == []
    assert ledger_set.runs.get_case("case_missing") is None
    assert ledger_set.runs.is_member(case["id"], ACTOR) is True
    assert ledger_set.runs.is_member(case["id"], ACTOR, {"APPROVER"}) is False
    assert (
        ledger_set.runs.add_member(
            case["id"], ACTOR, "approver", "APPROVER", actor_role="ADMIN"
        )
        is True
    )
    assert ledger_set.runs.is_member(case["id"], "approver", {"APPROVER"}) is True
    assert (
        ledger_set.runs.add_member(case["id"], "outsider", "other", "VIEWER") is False
    )

    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "DEEP_RESEARCH", "source_set_id": source_set["id"]},
        [{"module_id": "CP-DR", "dependencies": [], "stage": 1}],
    )
    with pytest.raises(ValueError, match="CASE_NOT_FOUND"):
        ledger_set.runs.create_run_with_nodes(
            "case_missing", ACTOR, {"source_set_id": source_set["id"]}, []
        )
    assert ledger_set.runs.list_runs(case["id"]) == [run]
    assert ledger_set.runs.latest_run(case["id"]) == run

    ledger_set.runs.emit(run["id"], "contract.manual", {"step": 1})
    assert ledger_set.runs.events_after(run["id"])[-1]["event"] == "contract.manual"
    assert ledger_set.runs.wait_for_events(run["id"], 1, timeout=0.01) == []

    token = ledger_set.runs.claim(run["id"], "research-worker")
    assert token is not None
    ledger_set.runs.emit_fenced(
        run["id"], token, "contract.fenced", {"worker": "research-worker"}
    )
    fenced_events = ledger_set.runs.events_after(run["id"], 1)
    assert len(fenced_events) == 1
    assert fenced_events[0]["event"] == "contract.fenced"
    assert fenced_events[0]["data"] == {"worker": "research-worker"}
    node = run["nodes"][0]
    ledger_set.runs.update_run_fenced(run["id"], token, status="running")
    proposed_plan = {
        "source_set": {"id": source_set["id"], "version": source_set["version"]}
    }
    plan_hash = f"sha256:{digest(proposed_plan)}"
    research = {
        "phase": "awaiting_approval",
        "proposed_plan": proposed_plan,
        "proposed_plan_hash": plan_hash,
    }
    ledger_set.runs.pause_research_plan(run["id"], token, node["id"], research)
    with pytest.raises(ValueError, match="PLAN_HASH_MISMATCH"):
        ledger_set.runs.approve_research_plan(run["id"], ACTOR, "sha256:wrong")
    approved = ledger_set.runs.approve_research_plan(run["id"], ACTOR, plan_hash)
    assert approved["status"] == "queued"
    ledger_set.runs.finish(run["id"], token)
    with pytest.raises(JobFencedError, match="stale workflow attempt"):
        ledger_set.runs.emit_fenced(run["id"], token, "contract.stale", {})

    first_run, first_snapshot = _accept_empty_run(ledger_set, case["id"], source_set)
    second_run, second_snapshot = _accept_empty_run(ledger_set, case["id"], source_set)
    assert ledger_set.runs.latest_run(case["id"])["id"] == second_run["id"]
    assert ledger_set.runs.get_run(first_run["id"])["id"] == first_run["id"]
    assert ledger_set.runs.switch_visible_snapshot(case["id"], "missing", ACTOR) is None
    assert (
        ledger_set.runs.switch_visible_snapshot(
            case["id"], second_snapshot["id"], ACTOR
        )
        == second_snapshot
    )
    assert (
        ledger_set.runs.get_case(case["id"])["visible_snapshot_id"]
        == second_snapshot["id"]
    )
    assert first_snapshot["id"] != second_snapshot["id"]


def test_publication_versions_conflict_without_partial_append(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    thesis = {"expected_version": 0, "core_thesis": "Defensible", "evidence_ids": []}
    recommendations = {
        "expected_version": 0,
        "market_snapshot_id": "market-1",
        "rows": [
            {
                "instrument_id": "bond",
                "instrument": "Bond",
                "recommendation": "N/A",
                "rationale": "Insufficient basis",
                "primary": True,
            }
        ],
        "analytical_dependency_ids": [],
    }
    saved = ledger_set.publications.save_report_inputs(
        case["id"], ACTOR, thesis, recommendations, accepted_snapshot_id=None
    )
    before = copy.deepcopy(
        (
            ledger_set.publications.list_theses(case["id"]),
            ledger_set.publications.list_recommendations(case["id"]),
        )
    )

    with pytest.raises(ValueError, match="VERSION_CONFLICT"):
        ledger_set.publications.save_report_inputs(
            case["id"], ACTOR, thesis, recommendations, accepted_snapshot_id=None
        )

    assert saved["thesis"]["version"] == saved["recommendations"]["version"] == 1
    assert (
        ledger_set.publications.list_theses(case["id"]),
        ledger_set.publications.list_recommendations(case["id"]),
    ) == before


def test_note_promotion_changes_source_authority_once(ledger_set: Any) -> None:
    case = _case(ledger_set)
    note = ledger_set.publications.create_note(case["id"], ACTOR, "Debt remains 100")

    promoted = ledger_set.publications.promote_note(case["id"], note["id"], ACTOR)
    promoted_set = ledger_set.sources.current_source_set(case["id"])
    assert promoted_set is not None
    repeated = ledger_set.publications.promote_note(case["id"], note["id"], ACTOR)

    source_id = promoted["promoted_source_id"]
    source = ledger_set.sources.get_source(source_id)
    source_set = ledger_set.sources.current_source_set(case["id"])
    assert promoted["promoted"] is True
    assert repeated["promoted_source_id"] == source_id
    assert source is not None and source["source_kind"] == "analyst_note"
    assert source_set is not None and source_set["source_ids"] == [source_id]
    assert source_set["version"] == promoted_set["version"]


def test_promoted_note_duplicate_digest_rolls_back_all_authority(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    body = "Debt remains 100"
    ledger_set.sources.ingest(
        _source(case["id"], sha256=hashlib.sha256(body.encode()).hexdigest()), ACTOR
    )
    note = ledger_set.publications.create_note(case["id"], ACTOR, body)
    before = (
        ledger_set.publications.list_notes(case["id"]),
        ledger_set.sources.list_sources(case["id"]),
        ledger_set.sources.current_source_set(case["id"]),
    )

    for promote in (
        lambda: ledger_set.sources.ingest_promoted_note(note, ACTOR),
        lambda: ledger_set.publications.promote_note(case["id"], note["id"], ACTOR),
    ):
        with pytest.raises(ValueError, match="^DUPLICATE_SOURCE$"):
            promote()
        assert (
            ledger_set.publications.list_notes(case["id"]),
            ledger_set.sources.list_sources(case["id"]),
            ledger_set.sources.current_source_set(case["id"]),
        ) == before


def test_publication_methodology_rv_and_audit_contracts(ledger_set: Any) -> None:
    case = _case(ledger_set)
    thesis = ledger_set.publications.append_thesis(
        case["id"], ACTOR, 0, {"core_thesis": "Defensible", "evidence_ids": []}
    )
    assert thesis["version"] == 1
    assert ledger_set.publications.list_theses(case["id"]) == [thesis]
    with pytest.raises(ValueError, match="VERSION_CONFLICT"):
        ledger_set.publications.append_thesis(
            case["id"], ACTOR, 0, {"core_thesis": "Stale", "evidence_ids": []}
        )
    recommendations = ledger_set.publications.append_recommendations(
        case["id"],
        ACTOR,
        0,
        {"market_snapshot_id": "market-1", "rows": [], "analytical_dependency_ids": []},
    )
    assert ledger_set.publications.list_recommendations(case["id"]) == [recommendations]

    universe = ledger_set.publications.save_rv_universe(
        case["id"], ACTOR, {"market_snapshot_id": "market-1", "rows": []}
    )
    assert universe["version"] == 1
    assert universe["created_by"] == ACTOR
    assert "author" not in universe
    assert ledger_set.publications.get_rv_universe(case["id"]) == universe
    assert ledger_set.publications.get_rv_universe("case_missing") is None

    invalid = ledger_set.publications.create_methodology_draft(
        {"module_id": "CP-1", "before": {"x": 1}, "after": {"x": 1}}, ACTOR
    )
    with pytest.raises(ValueError, match="draft does not validate"):
        ledger_set.publications.validate_methodology_draft(invalid["id"], "reviewer")

    draft = ledger_set.publications.create_methodology_draft(
        {"module_id": "CP-1", "before": {"x": 1}, "after": {"x": 2}}, ACTOR
    )
    drafts = ledger_set.publications.list_methodology_drafts()
    assert len(drafts) == 2
    assert {item["id"] for item in drafts} == {invalid["id"], draft["id"]}
    with pytest.raises(ValueError, match="validated draft required"):
        ledger_set.publications.confirm_methodology_draft(
            draft["id"], "approver", "signature"
        )
    validated = ledger_set.publications.validate_methodology_draft(
        draft["id"], "reviewer"
    )
    confirmed = ledger_set.publications.confirm_methodology_draft(
        draft["id"], "approver", "signature"
    )
    assert validated["status"] == "VALIDATED"
    assert confirmed["status"] == "CONFIRMED_PENDING_SIGNED_AUTHORITY"
    assert confirmed["signature"] == "signature"
    assert any(
        event["action"] == "methodology.draft_confirmed"
        for event in ledger_set.publications.list_audit()
    )


def test_memory_promoted_note_ingress_uses_canonical_state_without_aliasing() -> None:
    ledger_set = MemoryLedgerSet()
    case = _case(ledger_set)
    foreign_case = _case(ledger_set)
    note = ledger_set.publications.create_note(case["id"], ACTOR, "Debt remains 100")
    caller_note = copy.deepcopy(note)
    caller_note["body"] = "forged caller body"
    submitted = copy.deepcopy(caller_note)

    promoted = ledger_set.sources.ingest_promoted_note(caller_note, ACTOR)

    assert caller_note == submitted
    assert promoted["body"] == note["body"]
    assert ledger_set.publications.list_notes(case["id"]) == [promoted]
    source = ledger_set.sources.get_source(promoted["promoted_source_id"])
    assert source is not None and source["blocks"][0]["text"] == note["body"]
    caller_note["body"] = "caller mutation"
    assert ledger_set.publications.list_notes(case["id"]) == [promoted]
    before = (
        ledger_set.publications.list_notes(case["id"]),
        ledger_set.sources.list_sources(case["id"]),
        ledger_set.sources.current_source_set(case["id"]),
    )
    for invalid in (
        {**note, "id": "note_missing"},
        {**note, "case_id": foreign_case["id"]},
    ):
        with pytest.raises(KeyError, match="NOTE_NOT_FOUND"):
            ledger_set.sources.ingest_promoted_note(invalid, ACTOR)
        assert (
            ledger_set.publications.list_notes(case["id"]),
            ledger_set.sources.list_sources(case["id"]),
            ledger_set.sources.current_source_set(case["id"]),
        ) == before


def test_report_freeze_and_approval_require_exact_preview(
    ledger_set: Any,
) -> None:
    model_input = _accepted_model_input(ledger_set)
    case_id = model_input["case_id"]
    previous_snapshot = ledger_set.runs.get_snapshot(
        model_input["accepted_snapshot_id"]
    )
    source_set = ledger_set.sources.source_set(model_input["source_set_id"])
    assert previous_snapshot is not None and source_set is not None
    thesis_request = {
        "expected_version": 0,
        "core_thesis": "Defensible",
        "drivers": [],
        "risks": [],
        "catalysts": [],
        "unresolved_questions": [],
        "evidence_ids": [],
    }
    recommendation_request = {
        "expected_version": 0,
        "market_snapshot_id": "market-1",
        "rows": [
            {
                "instrument_id": "bond",
                "instrument": "Bond",
                "recommendation": "N/A",
                "rationale": "Insufficient basis",
                "primary": True,
            }
        ],
        "analytical_dependency_ids": [],
    }
    first_inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        thesis_request,
        recommendation_request,
        accepted_snapshot_id=previous_snapshot["id"],
    )
    current_run, current_snapshot = _accept_empty_run(ledger_set, case_id, source_set)
    assert ledger_set.runs.switch_visible_snapshot(
        case_id, previous_snapshot["id"], ACTOR
    ) == previous_snapshot
    inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        {**thesis_request, "expected_version": 1},
        {**recommendation_request, "expected_version": 1},
        accepted_snapshot_id=current_snapshot["id"],
    )

    explicit_first = ledger_set.publications.freeze_report(
        case_id, ACTOR, _report_record(previous_snapshot, first_inputs)
    )
    approved_first = ledger_set.publications.approve_report(
        case_id,
        "approver",
        "PENDING_APPROVAL",
        explicit_first["preview_digest"],
        explicit_first["input_fingerprint"],
        "Visible v1 remains authoritative",
    )
    assert approved_first["status"] == "APPROVED"

    assert ledger_set.runs.switch_visible_snapshot(
        case_id, current_snapshot["id"], ACTOR
    ) == current_snapshot
    stale_versions_report = _report_record(current_snapshot, inputs)
    stale_versions_report["content"]["thesis_version"] = 0
    stale_versions_report["content"]["recommendation_version"] = 0
    stale_versions_report["preview_digest"] = digest(stale_versions_report["content"])
    stale_versions_report["digest"] = stale_versions_report["preview_digest"]
    with pytest.raises(ValueError, match="THESIS_AND_RECOMMENDATIONS_REQUIRED"):
        ledger_set.publications.freeze_report(case_id, ACTOR, stale_versions_report)
    assert ledger_set.publications.get_report(case_id) == approved_first

    invalid_model = {
        "build_id": "model_missing",
        "accepted_snapshot_id": current_snapshot["id"],
        "payload_digest": "0" * 64,
        "input_fingerprint": "0" * 64,
    }
    with pytest.raises(ValueError, match="MODEL_SNAPSHOT_MISMATCH"):
        ledger_set.publications.freeze_report(
            case_id,
            ACTOR,
            _report_record(current_snapshot, inputs, invalid_model),
        )
    assert ledger_set.publications.get_report(case_id) == approved_first

    queued, created = ledger_set.models.queue_build(
        {
            **model_input,
            "accepted_run_id": current_run["id"],
            "accepted_snapshot_id": current_snapshot["id"],
            "input_fingerprint": "d" * 64,
        },
        ACTOR,
    )
    assert created is True
    model_token = ledger_set.models.claim(queued["id"], "model-worker")
    assert model_token is not None
    ready = ledger_set.models.complete(
        queued["id"], model_token, _model_result(), "model-worker"
    )
    model_identity = {
        "build_id": ready["id"],
        "accepted_snapshot_id": ready["accepted_snapshot_id"],
        "payload_digest": ready["payload_digest"],
        "input_fingerprint": ready["input_fingerprint"],
    }
    invalid_export = {
        **model_identity,
        "export": {
            "sha256": "0" * 64,
            "size": 1,
            "filename": "foreign.xlsx",
        },
    }
    with pytest.raises(ValueError, match="MODEL_EXPORT_MISMATCH"):
        ledger_set.publications.freeze_report(
            case_id,
            ACTOR,
            _report_record(current_snapshot, inputs, invalid_export),
        )
    assert ledger_set.publications.get_report(case_id) == approved_first

    model_report = _report_record(current_snapshot, inputs, model_identity)
    frozen = ledger_set.publications.freeze_report(case_id, ACTOR, model_report)
    assert "id" not in model_report
    assert frozen["id"]

    with pytest.raises(ValueError, match="report changed or missing"):
        ledger_set.publications.approve_report(
            case_id,
            "approver",
            "APPROVED",
            frozen["preview_digest"],
            frozen["input_fingerprint"],
            None,
        )
    assert ledger_set.publications.get_report(case_id)["status"] == "PENDING_APPROVAL"

    with pytest.raises(ValueError, match="STALE_PREVIEW"):
        ledger_set.publications.approve_report(
            case_id,
            "approver",
            "PENDING_APPROVAL",
            frozen["preview_digest"],
            "wrong-input-fingerprint",
            None,
        )
    assert ledger_set.publications.get_report(case_id)["status"] == "PENDING_APPROVAL"

    with pytest.raises(ValueError, match="STALE_PREVIEW"):
        ledger_set.publications.approve_report(
            case_id,
            "approver",
            "PENDING_APPROVAL",
            "wrong-preview",
            frozen["input_fingerprint"],
            None,
        )

    assert ledger_set.publications.get_report(case_id)["status"] == "PENDING_APPROVAL"

    updated_inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        {**thesis_request, "expected_version": 2},
        {**recommendation_request, "expected_version": 2},
        accepted_snapshot_id=current_snapshot["id"],
    )
    approved_model_report = ledger_set.publications.approve_report(
        case_id,
        "approver",
        "PENDING_APPROVAL",
        frozen["preview_digest"],
        frozen["input_fingerprint"],
        None,
    )
    assert approved_model_report["status"] == "APPROVED"

    publication_current = ledger_set.publications.freeze_report(
        case_id,
        ACTOR,
        _report_record(current_snapshot, updated_inputs, model_identity),
    )
    _, next_snapshot = _accept_empty_run(ledger_set, case_id, source_set)
    approved = ledger_set.publications.approve_report(
        case_id,
        "approver",
        "PENDING_APPROVAL",
        publication_current["preview_digest"],
        publication_current["input_fingerprint"],
        "Reviewed",
    )
    assert approved["status"] == "APPROVED"
    assert approved["approved_by"] == "approver"
    assert approved["approval_comment"] == "Reviewed"

    tampered_inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        {**thesis_request, "expected_version": 3},
        {**recommendation_request, "expected_version": 3},
        accepted_snapshot_id=current_snapshot["id"],
    )
    tampered_report = ledger_set.publications.freeze_report(
        case_id, ACTOR, _report_record(current_snapshot, tampered_inputs)
    )
    tamper_thesis_version(
        ledger_set,
        case_id,
        tampered_inputs["thesis"]["version"],
        postgres_dsn=_postgres_test_dsn() if POSTGRES_URL else None,
    )
    with pytest.raises(ValueError, match="STALE_PREVIEW"):
        ledger_set.publications.approve_report(
            case_id,
            "approver",
            "PENDING_APPROVAL",
            tampered_report["preview_digest"],
            tampered_report["input_fingerprint"],
            None,
        )
    assert ledger_set.publications.get_report(case_id) == tampered_report


def test_model_jobs_retry_renew_takeover_and_fencing(ledger_set: Any) -> None:
    build = _accepted_model_input(ledger_set)
    queued, created = ledger_set.models.queue_build(build, ACTOR)
    build_id = queued["id"]
    stale = ledger_set.models.claim(build_id, "model-worker")

    assert created is True
    assert "id" not in build
    assert queued["status"] == "QUEUED"
    assert stale is not None
    assert ledger_set.models.renew(build_id, stale) is True
    assert ledger_set.models.is_current(build_id, stale) is True
    assert ledger_set.models.claim(build_id, "other-worker") is None

    time.sleep(LEASE_SECONDS + 0.1)
    assert ledger_set.models.pending_jobs() == [(build_id, ACTOR, "calculate")]
    replacement = ledger_set.models.claim(build_id, "replacement-worker")
    assert replacement is not None and replacement != stale
    assert ledger_set.models.renew(build_id, stale) is False
    assert ledger_set.models.is_current(build_id, stale) is False
    before_stale_writes = copy.deepcopy(ledger_set.models.get_build(build_id))
    assert before_stale_writes is not None

    for stale_write in (
        lambda: ledger_set.models.complete(
            build_id, stale, _model_result(), "model-worker"
        ),
        lambda: ledger_set.models.fail(
            build_id,
            stale,
            {"code": "MODEL_CALCULATION_FAILED", "detail": "stale"},
            "model-worker",
        ),
    ):
        with pytest.raises(JobFencedError, match="stale model attempt"):
            stale_write()
        assert ledger_set.models.get_build(build_id) == before_stale_writes

    invalid_result = _model_result()
    invalid_result["payload_digest"] = "0" * 64
    with pytest.raises(ValueError, match="MODEL_RESULT_INVALID"):
        ledger_set.models.complete(
            build_id, replacement, invalid_result, "replacement-worker"
        )
    assert ledger_set.models.is_current(build_id, replacement) is True
    assert ledger_set.models.get_build(build_id)["status"] == "BUILDING"

    failed = ledger_set.models.fail(
        build_id,
        replacement,
        {"code": "MODEL_CALCULATION_FAILED", "detail": "bounded"},
        "replacement-worker",
    )
    assert failed["status"] == "FAILED"
    assert ledger_set.models.pending_jobs() == []

    retried = ledger_set.models.retry_build(build_id, "reviewer")
    assert retried["id"] == build_id
    assert retried["status"] == "QUEUED"
    assert retried["error"] is None
    assert ledger_set.models.pending_jobs() == [(build_id, "reviewer", "calculate")]
    retry_token = ledger_set.models.claim(build_id, "retry-worker")
    assert retry_token is not None
    ready = ledger_set.models.complete(
        build_id, retry_token, _model_result(), "retry-worker"
    )
    assert ready["status"] == "READY"
    assert ledger_set.models.is_current(build_id, retry_token) is False


def test_model_export_queue_claim_completion_and_download_contracts(
    ledger_set: Any,
) -> None:
    build_input = _accepted_model_input(ledger_set)
    queued, created = ledger_set.models.queue_build(build_input, ACTOR)
    assert created is True
    calculate_token = ledger_set.models.claim(queued["id"], "model-worker")
    assert calculate_token is not None
    ready = ledger_set.models.complete(
        queued["id"], calculate_token, _model_result(), "model-worker"
    )
    assert ledger_set.models.list_builds(ready["case_id"]) == [ready]
    with pytest.raises(ValueError, match="MODEL_EXPORT_NOT_READY"):
        ledger_set.models.queue_export("model_missing", ACTOR)

    export_queued, export_created = ledger_set.models.queue_export(ready["id"], ACTOR)
    repeated, repeated_created = ledger_set.models.queue_export(ready["id"], ACTOR)
    assert export_created is True
    assert repeated_created is False
    assert repeated == export_queued
    export_token = ledger_set.models.claim(ready["id"], "export-worker", "export")
    assert export_token is not None
    exported = ledger_set.models.complete(
        ready["id"],
        export_token,
        _export_result(ready),
        "export-worker",
        "export",
    )
    assert exported["export"]["status"] == "READY"
    ledger_set.models.record_export_download(ready["id"], ready["case_id"], ACTOR)
    with pytest.raises(ValueError, match="MODEL_EXPORT_NOT_READY"):
        ledger_set.models.record_export_download(ready["id"], "case_foreign", ACTOR)


def test_pending_job_reads_are_authoritative(ledger_set: Any) -> None:
    _, run = _queued_run(ledger_set)
    build = _accepted_model_input(ledger_set)
    queued, _ = ledger_set.models.queue_build(build, ACTOR)

    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]
    assert ledger_set.models.pending_jobs() == [(queued["id"], ACTOR, "calculate")]


def test_postgres_duplicate_ingest_has_one_winner(
    postgres_pair: tuple[Any, Any],
) -> None:
    first, second = postgres_pair
    case = _case(first)
    source = _source(case["id"])
    barrier = threading.Barrier(2)

    def ingest(ledger_set: Any) -> str:
        barrier.wait(timeout=5)
        try:
            ledger_set.sources.ingest(source, ACTOR)
        except ValueError as exc:
            return str(exc)
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(ingest, (first, second)))

    assert sorted(outcomes) == ["created", "source content already active"]
    assert len(first.sources.list_sources(case["id"])) == 1


def test_postgres_optimistic_append_has_one_winner(
    postgres_pair: tuple[Any, Any],
) -> None:
    first, second = postgres_pair
    case = _case(first)
    thesis = {"core_thesis": "Defensible", "evidence_ids": []}
    barrier = threading.Barrier(2)

    def append(ledger_set: Any) -> str:
        barrier.wait(timeout=5)
        try:
            ledger_set.publications.append_thesis(case["id"], ACTOR, 0, thesis)
        except ValueError as exc:
            return str(exc)
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(append, (first, second)))

    assert sorted(outcomes) == ["VERSION_CONFLICT", "created"]
    assert len(first.publications.list_theses(case["id"])) == 1


def test_postgres_job_claim_has_one_winner_across_connections(
    postgres_pair: tuple[Any, Any],
) -> None:
    first, second = postgres_pair
    _, run = _queued_run(first)
    barrier = threading.Barrier(2)

    def claim(item: tuple[Any, str]) -> str | None:
        barrier.wait(timeout=5)
        return item[0].runs.claim(run["id"], item[1])

    with ThreadPoolExecutor(max_workers=2) as executor:
        tokens = list(
            executor.map(
                claim,
                ((first, "worker-a"), (second, "worker-b")),
            )
        )

    assert sum(token is not None for token in tokens) == 1


def test_postgres_model_export_queue_and_claim_do_not_deadlock(
    postgres_pair: tuple[Any, Any],
) -> None:
    first, second = postgres_pair
    build_input = _accepted_model_input(first)
    queued, _ = first.models.queue_build(build_input, ACTOR)
    calculate_token = first.models.claim(queued["id"], "model-worker")
    assert calculate_token is not None
    ready = first.models.complete(
        queued["id"], calculate_token, _model_result(), "model-worker"
    )
    first.models.queue_export(ready["id"], ACTOR)
    failed_token = first.models.claim(ready["id"], "failed-export", "export")
    assert failed_token is not None
    first.models.fail(
        ready["id"],
        failed_token,
        {"code": "MODEL_EXPORT_FAILED", "detail": "retryable"},
        "failed-export",
        "export",
    )
    barrier = threading.Barrier(2)

    def requeue() -> tuple[str, bool]:
        barrier.wait(timeout=5)
        _, created = first.models.queue_export(ready["id"], ACTOR)
        return "queue", created

    def claim() -> tuple[str, str | None]:
        barrier.wait(timeout=5)
        return "claim", second.models.claim(ready["id"], "racing-export", "export")

    outcomes = _bounded_parallel(requeue, claim)

    assert outcomes[0] == ("queue", True)
    assert outcomes[1][0] == "claim"
    final_first = first.models.get_build(ready["id"])
    final_second = second.models.get_build(ready["id"])
    assert final_first == final_second
    assert final_first is not None
    assert final_first["export"]["status"] in {"QUEUED", "EXPORTING"}


def test_postgres_model_retry_and_fail_do_not_deadlock(
    postgres_pair: tuple[Any, Any],
) -> None:
    first, second = postgres_pair
    build_input = _accepted_model_input(first)
    queued, _ = first.models.queue_build(build_input, ACTOR)
    token = first.models.claim(queued["id"], "failing-worker")
    assert token is not None
    barrier = threading.Barrier(2)

    def retry() -> tuple[str, str]:
        barrier.wait(timeout=5)
        try:
            retried = first.models.retry_build(queued["id"], "reviewer")
        except ValueError as exc:
            return "retry", str(exc)
        return "retry", retried["status"]

    def fail() -> tuple[str, str]:
        barrier.wait(timeout=5)
        failed = second.models.fail(
            queued["id"],
            token,
            {"code": "MODEL_CALCULATION_FAILED", "detail": "bounded"},
            "failing-worker",
        )
        return "fail", failed["status"]

    outcomes = _bounded_parallel(retry, fail)

    assert outcomes[0] in {("retry", "MODEL_RETRY_INVALID"), ("retry", "QUEUED")}
    assert outcomes[1] == ("fail", "FAILED")
    final_first = first.models.get_build(queued["id"])
    final_second = second.models.get_build(queued["id"])
    assert final_first == final_second
    assert final_first is not None
    assert final_first["status"] in {"FAILED", "QUEUED"}


def test_postgres_stale_tokens_cannot_publish_any_authority(
    postgres_pair: tuple[Any, Any],
) -> None:
    # Deliberately sequential: this proof targets deterministic fencing after takeover,
    # while the three claim/uniqueness proofs above establish synchronized overlap.
    first, second = postgres_pair
    case, run = _queued_run(first)
    node = run["nodes"][0]
    stale = first.runs.claim(run["id"], "stale-worker")
    assert stale is not None
    first.runs.update_node_fenced(run["id"], stale, node["id"], status="running")
    time.sleep(LEASE_SECONDS + 0.1)
    replacement = second.runs.claim(run["id"], "replacement-worker")
    assert replacement is not None
    payload = {"debt": 100}
    artifact = {
        "case_id": case["id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "input_fingerprint": "stale-race",
        "payload": payload,
        "digest": digest(payload),
    }
    before_run = first.runs.get_run(run["id"])
    before_events = first.runs.events_after(run["id"])
    for stale_write in (
        lambda: first.runs.update_node_fenced(
            run["id"], stale, node["id"], status="succeeded"
        ),
        lambda: first.runs.emit_fenced(run["id"], stale, "stale", {}),
        lambda: first.runs.complete_node(
            run["id"], stale, node["id"], artifact, None, {}
        ),
        lambda: first.runs.finalize_success(run["id"], stale, None, {}),
    ):
        with pytest.raises(JobFencedError):
            stale_write()
    assert first.runs.get_run(run["id"]) == before_run
    assert first.runs.events_after(run["id"]) == before_events
    assert (
        first.runs.artifact_for_fingerprint(
            run["id"], node["module_id"], artifact["input_fingerprint"]
        )
        is None
    )

    source_set = first.sources.source_set(run["plan"]["source_set_id"])
    assert source_set is not None
    snapshot_payload = {
        "case_id": case["id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": [],
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }
    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        first.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {**snapshot_payload, "digest": digest(snapshot_payload)},
        )
    assert first.runs.get_case(case["id"])["accepted_snapshot_id"] is None

    second.runs.update_node_fenced(run["id"], replacement, node["id"], status="running")
    completed = second.runs.complete_node(
        run["id"], replacement, node["id"], artifact, None, {}
    )
    second.runs.finalize_success(run["id"], replacement, None, {})
    accepted_payload = {
        **snapshot_payload,
        "artifacts": [
            {
                "id": completed["id"],
                "module_id": completed["module_id"],
                "digest": completed["digest"],
            }
        ],
    }
    snapshot = second.runs.accept_snapshot(
        case["id"],
        run["id"],
        ACTOR,
        {**accepted_payload, "digest": digest(accepted_payload)},
    )
    build, created = first.models.queue_build(
        {
            "case_id": case["id"],
            "accepted_run_id": run["id"],
            "accepted_snapshot_id": snapshot["id"],
            "source_set_id": source_set["id"],
            "input_fingerprint": "d" * 64,
            "worksheet_schema_version": "caos.model.worksheet.v1",
        },
        ACTOR,
    )
    assert created is True
    stale_model = first.models.claim(build["id"], "stale-model-worker")
    assert stale_model is not None
    time.sleep(LEASE_SECONDS + 0.1)
    replacement_model = second.models.claim(build["id"], "replacement-model-worker")
    assert replacement_model is not None
    before_build = first.models.get_build(build["id"])
    with pytest.raises(JobFencedError):
        first.models.complete(build["id"], stale_model, _model_result(), ACTOR)
    assert first.models.get_build(build["id"]) == before_build
