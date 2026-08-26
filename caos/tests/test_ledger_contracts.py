from __future__ import annotations

import copy
import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from caos import ledgers
from caos import postgres_ledgers as postgres_ledgers_module
from caos.contracts import clean_json, digest
from caos.memory_ledgers import MemoryLedgerSet
from caos.postgres_ledgers import PostgresLedgerSet
from caos.store import JobFencedError


ACTOR = "analyst"
LEASE_SECONDS = 0.2


def _clear_postgres(database_url: str) -> None:
    import psycopg

    with psycopg.connect(
        database_url.replace("postgresql+psycopg://", "postgresql://")
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE methodology_drafts, rv_universes, audit_events, reports, "
                "assumptions, notes, workflow_events, model_build_jobs, model_builds, "
                "rv_loan_rows, rv_loan_universes, recommendation_versions, "
                "thesis_versions, accepted_snapshots, artifacts, jobs, workflow_nodes, "
                "runs, source_sets, sources, case_members, cases RESTART IDENTITY CASCADE"
            )


@pytest.fixture(params=["memory", "postgres"])
def ledger_set(request: pytest.FixtureRequest) -> Any:
    if request.param == "memory":
        yield MemoryLedgerSet(lease_seconds=LEASE_SECONDS)
        return
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for PostgreSQL ledger proof")
    durable = PostgresLedgerSet(database_url, lease_seconds=LEASE_SECONDS)
    _clear_postgres(database_url)
    try:
        yield durable
    finally:
        _clear_postgres(database_url)


@pytest.fixture
def postgres_ledger_set() -> PostgresLedgerSet:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for PostgreSQL ledger proof")
    durable = PostgresLedgerSet(database_url, lease_seconds=LEASE_SECONDS)
    _clear_postgres(database_url)
    try:
        yield durable
    finally:
        _clear_postgres(database_url)


class _CaseLockGate:
    def __init__(self) -> None:
        self.enabled = True
        self.acquired = threading.Event()
        self.release = threading.Event()


class _GatedCursor:
    def __init__(self, cursor: Any, gate: _CaseLockGate) -> None:
        self._cursor = cursor
        self._gate = gate

    def __enter__(self) -> _GatedCursor:
        self._cursor.__enter__()
        return self

    def __exit__(self, *args: object) -> Any:
        return self._cursor.__exit__(*args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)

    def execute(self, statement: Any, parameters: Any = None) -> _GatedCursor:
        self._cursor.execute(statement, parameters)
        normalized = " ".join(str(statement).split())
        if self._gate.enabled and normalized == (
            "SELECT 1 FROM cases WHERE id=%s FOR UPDATE"
        ):
            self._gate.enabled = False
            self._gate.acquired.set()
            if not self._gate.release.wait(timeout=15):
                raise TimeoutError("case-lock race gate was not released")
        return self


class _GatedConnection:
    def __init__(self, connection: Any, gate: _CaseLockGate) -> None:
        self._connection = connection
        self._gate = gate

    def __enter__(self) -> _GatedConnection:
        self._connection.__enter__()
        return self

    def __exit__(self, *args: object) -> Any:
        return self._connection.__exit__(*args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def cursor(self, *args: object, **kwargs: object) -> _GatedCursor:
        return _GatedCursor(self._connection.cursor(*args, **kwargs), self._gate)


class _GatedPostgresLedgerSet(PostgresLedgerSet):
    def __init__(self, database_url: str) -> None:
        self._case_lock_gate: _CaseLockGate | None = None
        super().__init__(database_url)

    def gate_next_case_lock(self) -> _CaseLockGate:
        gate = _CaseLockGate()
        self._case_lock_gate = gate
        return gate

    def _connect(self) -> Any:
        connection = super()._connect()
        gate = self._case_lock_gate
        return _GatedConnection(connection, gate) if gate is not None else connection


class _ObservedPostgresLedgerSet(PostgresLedgerSet):
    def __init__(self, database_url: str) -> None:
        self._observe_next_connection = False
        self._connection_opened = threading.Event()
        self.observed_pid: int | None = None
        super().__init__(database_url)

    def observe_next_connection(self) -> None:
        self.observed_pid = None
        self._connection_opened.clear()
        self._observe_next_connection = True

    def wait_for_observed_connection(self) -> int:
        assert self._connection_opened.wait(timeout=5)
        assert self.observed_pid is not None
        return self.observed_pid

    def _connect(self) -> Any:
        connection = super()._connect()
        if self._observe_next_connection:
            self._observe_next_connection = False
            self.observed_pid = connection.info.backend_pid
            self._connection_opened.set()
        return connection


def _wait_for_postgres_blocker(database_url: str, backend_pid: int) -> None:
    import psycopg

    deadline = time.monotonic() + 10
    observed: list[tuple[Any, ...]] = []
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            while time.monotonic() < deadline:
                cursor.execute(
                    "SELECT state, wait_event_type, wait_event, pg_blocking_pids(pid) "
                    "FROM pg_stat_activity WHERE pid=%s",
                    (backend_pid,),
                )
                observed = list(cursor.fetchall())
                if any(row[3] for row in observed):
                    return
                time.sleep(0.01)
    raise AssertionError(
        f"follower connection never blocked on the production case lock: {observed!r}"
    )


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


def _ready_model_build(ledger_set: Any) -> dict[str, Any]:
    queued, created = ledger_set.models.queue_build(
        {
            **_accepted_model_input(ledger_set),
            "calculation_runtime": {
                "assumption_registry_version": "cp-model.assumptions.v1",
                "assumption_registry_digest": "a" * 64,
                "calculation_contract_version": "cp-model.calculation.v1",
            },
        },
        ACTOR,
    )
    assert created is True
    token = ledger_set.models.claim(queued["id"], "model-worker")
    assert token is not None
    return ledger_set.models.complete(
        queued["id"], token, _model_result(), "model-worker"
    )


def _newer_ready_model_build(
    ledger_set: Any, prior: dict[str, Any]
) -> dict[str, Any]:
    queued, created = ledger_set.models.queue_build(
        {
            "case_id": prior["case_id"],
            "accepted_run_id": prior["accepted_run_id"],
            "accepted_snapshot_id": prior["accepted_snapshot_id"],
            "source_set_id": prior["source_set_id"],
            "input_fingerprint": "d" * 64,
            "worksheet_schema_version": prior["worksheet_schema_version"],
            "calculation_runtime": copy.deepcopy(prior["calculation_runtime"]),
        },
        ACTOR,
    )
    assert created is True
    token = ledger_set.models.claim(queued["id"], "new-model-worker")
    assert token is not None
    return ledger_set.models.complete(
        queued["id"], token, _model_result(), "new-model-worker"
    )


def _model_revision(build: dict[str, Any], *, preview_digest: str = "b" * 64) -> dict[str, Any]:
    assumptions = [
        {
            "assumption_id": "operating.revenue_growth.consolidated",
            "case": "BASE",
            "period_id": "FY2025",
            "unit": "PERCENT",
            "status": "READY",
            "value": 0.03,
            "gap_code": None,
        }
    ]
    outputs = {
        "BASE": {"FY2025": {"revenue": 103.0}},
        "DOWNSIDE": {"FY2025": {"revenue": 97.0}},
    }
    return {
        "case_id": build["case_id"],
        "build_id": build["id"],
        "accepted_snapshot_id": build["accepted_snapshot_id"],
        "build_input_fingerprint": build["input_fingerprint"],
        "build_payload_digest": build["payload_digest"],
        "registry_version": build["calculation_runtime"][
            "assumption_registry_version"
        ],
        "registry_digest": build["calculation_runtime"][
            "assumption_registry_digest"
        ],
        "calculation_contract_version": build["calculation_runtime"][
            "calculation_contract_version"
        ],
        "effective_assumptions": assumptions,
        "assumptions_digest": digest(assumptions),
        "outputs": outputs,
        "outputs_digest": digest(outputs),
        "preview_digest": preview_digest,
        "parent_revision_id": None,
        "note": "Quarterly earnings review",
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


def test_protocol_inventory_is_exact() -> None:
    assert {
        name
        for name, value in vars(ledgers).items()
        if getattr(value, "_is_protocol", False)
        and getattr(value, "__module__", None) == ledgers.__name__
    } == {"SourceCatalog", "RunLedger", "PublicationLedger", "ModelLedger"}


def test_memory_ledger_set_keeps_one_private_state() -> None:
    ledger_set = MemoryLedgerSet(lease_seconds=LEASE_SECONDS)
    adapters = (
        ledger_set.sources,
        ledger_set.runs,
        ledger_set.publications,
        ledger_set.models,
    )
    assert {name for name in dir(ledger_set) if not name.startswith("_")} == {
        "sources",
        "runs",
        "publications",
        "models",
    }
    assert len({id(adapter._state) for adapter in adapters}) == 1
    assert len({id(adapter._state.lock) for adapter in adapters}) == 1

    case = _case(ledger_set)
    case["name"] = "mutated outside the ledger"
    assert ledger_set.runs.get_case(case["id"])["name"] == "Contract case"


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
    replacement = ledger_set.sources.ingest(source, ACTOR)
    assert replacement["source_set"]["version"] == withdrawn_set["version"] + 1
    assert ledger_set.sources.source_set(historical_set["id"]) == historical_set


def test_assumption_creation_and_withdrawal_orders_match_portably(
    ledger_set: Any,
) -> None:
    create_first_case = _case(ledger_set)
    create_first_source = ledger_set.sources.ingest(
        _source(create_first_case["id"]), ACTOR
    )
    assumption = ledger_set.publications.create_assumption(
        create_first_case["id"],
        ACTOR,
        "Debt is 100",
        [create_first_source["id"]],
        ["CP-1"],
    )
    assert ledger_set.sources.withdraw(
        create_first_case["id"], create_first_source["id"], ACTOR
    )
    stored = ledger_set.publications.list_assumptions(create_first_case["id"])
    assert stored == [{**assumption, "status": "STALE", "stale": True}]

    withdraw_first_case = _case(ledger_set)
    withdraw_first_source = ledger_set.sources.ingest(
        _source(withdraw_first_case["id"], sha256="b" * 64), ACTOR
    )
    assert ledger_set.sources.withdraw(
        withdraw_first_case["id"], withdraw_first_source["id"], ACTOR
    )
    with pytest.raises(ValueError, match="EVIDENCE_SOURCE_WITHDRAWN"):
        ledger_set.publications.create_assumption(
            withdraw_first_case["id"],
            ACTOR,
            "Debt is 100",
            [withdraw_first_source["id"]],
            ["CP-1"],
        )
    assert ledger_set.publications.list_assumptions(withdraw_first_case["id"]) == []


def test_loan_universe_versions_supersede_reject_and_withdraw_portably(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    sources = [
        ledger_set.sources.ingest(_source(case["id"], sha256=character * 64), ACTOR)
        for character in ("a", "b", "c")
    ]

    def proposal(
        index: int, digest_character: str, *, status: str = "ACTIVE"
    ) -> dict[str, Any]:
        return {
            "case_id": case["id"],
            "source_id": sources[index]["id"],
            "source_filename": sources[index]["filename"],
            "source_sha256": sources[index]["sha256"],
            "workbook_date": "2026-08-24",
            "template_version": "contract-template-v1",
            "importer_version": "contract-importer-v1",
            "universe_digest": (
                None if status == "REJECTED" else digest_character * 64
            ),
            "row_count": 0 if status == "REJECTED" else 1,
            "status": status,
            "findings": [] if status == "ACTIVE" else [{"code": "RV_TEMPLATE_PARTIAL"}],
        }

    first, created = ledger_set.sources.save_loan_universe_import(
        proposal(0, "d"),
        [{"instrument_key": "loan-1", "borrower": "Issuer"}],
        ACTOR,
    )
    replay, replay_created = ledger_set.sources.save_loan_universe_import(
        proposal(0, "d"),
        [{"instrument_key": "loan-1", "borrower": "Issuer"}],
        ACTOR,
    )
    assert created is True and first["version"] == 1
    assert replay_created is False and replay["id"] == first["id"]

    second, second_created = ledger_set.sources.save_loan_universe_import(
        proposal(1, "e"),
        [{"instrument_key": "loan-2", "borrower": "Issuer"}],
        ACTOR,
    )
    superseded = ledger_set.sources.find_loan_universe_import(
        case["id"], sources[0]["sha256"], "contract-template-v1", "contract-importer-v1"
    )
    assert second_created is True and second["version"] == 2
    assert superseded is not None and superseded["status"] == "SUPERSEDED"
    assert ledger_set.sources.active_loan_universe(case["id"])["id"] == second["id"]

    rejected, rejected_created = ledger_set.sources.save_loan_universe_import(
        proposal(2, "f", status="REJECTED"), [], ACTOR
    )
    assert rejected_created is True
    assert rejected["status"] == "REJECTED" and rejected["version"] is None
    assert ledger_set.sources.active_loan_universe(case["id"])["id"] == second["id"]

    assert ledger_set.sources.withdraw(case["id"], sources[1]["id"], ACTOR)
    assert ledger_set.sources.active_loan_universe(case["id"]) is None
    withdrawn = ledger_set.sources.find_loan_universe_import(
        case["id"], sources[1]["sha256"], "contract-template-v1", "contract-importer-v1"
    )
    assert withdrawn is not None and withdrawn["status"] == "WITHDRAWN"
    invalid = proposal(1, "e")
    invalid["template_version"] = "contract-template-after-withdrawal"
    with pytest.raises(ValueError, match="RV_SOURCE_NOT_ACTIVE"):
        ledger_set.sources.save_loan_universe_import(
            invalid, [{"instrument_key": "loan-3", "borrower": "Issuer"}], ACTOR
        )


def test_source_reads_hide_adapter_fields_and_private_bytes_are_explicit(
    ledger_set: Any, tmp_path: Path
) -> None:
    case = _case(ledger_set)
    content = b"Debt 100"
    vault_path = tmp_path / "stored-source"
    vault_path.write_bytes(content)
    proposal = _source(case["id"], sha256=hashlib.sha256(content).hexdigest())
    proposal.update(vault_path=str(vault_path), bytes=len(content))

    ingested = ledger_set.sources.ingest(proposal, ACTOR)
    public = ledger_set.sources.get_source(ingested["id"])

    assert public is not None
    assert "vault_path" not in public
    assert "withdrawn_at" not in public
    assert (
        ledger_set.sources.read_source_bytes(ingested["id"], len(content) + 1)
        == content
    )

    ledger_set.sources.withdraw(case["id"], ingested["id"], ACTOR)
    withdrawn = ledger_set.sources.get_source(ingested["id"])
    assert withdrawn is not None and withdrawn["withdrawn"] is True
    assert "vault_path" not in withdrawn
    assert "withdrawn_at" not in withdrawn


def test_governed_writes_commit_state_and_audit_together(ledger_set: Any) -> None:
    case = _case(ledger_set)
    source = ledger_set.sources.ingest(_source(case["id"]), ACTOR)
    note = ledger_set.publications.create_note(case["id"], ACTOR, "Watch leverage")
    assumption = ledger_set.publications.create_assumption(
        case["id"], ACTOR, "Debt is 100", [source["id"]], ["CP-1"]
    )
    universe = ledger_set.publications.save_rv_universe(
        case["id"], ACTOR, {"instruments": []}
    )
    draft = ledger_set.publications.create_methodology_draft(
        {"module_id": "CP-1", "before": 1, "after": 2}, ACTOR
    )
    validated = ledger_set.publications.validate_methodology_draft(
        draft["id"], "reviewer"
    )
    confirmed = ledger_set.publications.confirm_methodology_draft(
        draft["id"], "reviewer", "signed"
    )

    audit = ledger_set.publications.list_audit()
    actions = [event["action"] for event in audit]
    assert {
        "source.ingested",
        "note.created",
        "assumption.created",
        "rv.universe_versioned",
        "methodology.draft_created",
        "methodology.draft_validated",
        "methodology.draft_confirmed",
    }.issubset(actions)
    source_event = next(
        event for event in audit if event["action"] == "source.ingested"
    )
    assert source_event["case_id"] == case["id"]
    assert source_event["source_id"] == source["id"]
    assert source_event["sha256"] == source["sha256"]
    assert ledger_set.publications.list_notes(case["id"]) == [note]
    assert ledger_set.publications.list_assumptions(case["id"]) == [assumption]
    assert ledger_set.publications.get_rv_universe(case["id"]) == universe
    assert validated["status"] == "VALIDATED"
    assert confirmed["status"] == "CONFIRMED_PENDING_SIGNED_AUTHORITY"

    before_failure = copy.deepcopy(ledger_set.publications.list_audit())
    with pytest.raises(ValueError, match="EVIDENCE_CASE_MISMATCH"):
        ledger_set.publications.create_assumption(
            case["id"], ACTOR, "Unsupported", ["source_missing"], ["CP-1"]
        )
    assert ledger_set.publications.list_audit() == before_failure


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


def test_duplicate_run_modules_and_collapsed_snapshot_cardinality_are_rejected(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    duplicate_nodes = [
        {"module_id": "CP-1", "dependencies": [], "stage": 1},
        {"module_id": "CP-1", "dependencies": [], "stage": 2},
    ]
    before_case = ledger_set.runs.get_case(case["id"])
    before_audit = ledger_set.publications.list_audit()

    with pytest.raises(ValueError, match="^DUPLICATE_RUN_MODULE$"):
        ledger_set.runs.create_run_with_nodes(
            case["id"],
            ACTOR,
            {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
            duplicate_nodes,
        )

    assert ledger_set.runs.list_runs(case["id"]) == []
    assert ledger_set.runs.pending_runs() == []
    assert ledger_set.runs.get_case(case["id"]) == before_case
    assert ledger_set.publications.list_audit() == before_audit

    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [
            {"module_id": "CP-1", "dependencies": [], "stage": 1},
            {"module_id": "CP-2", "dependencies": ["CP-1"], "stage": 2},
        ],
    )
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    artifact_refs = []
    for node in run["nodes"]:
        payload = {"module_id": node["module_id"]}
        artifact = ledger_set.runs.complete_node(
            run["id"],
            token,
            node["id"],
            {
                "case_id": case["id"],
                "run_id": run["id"],
                "module_id": node["module_id"],
                "input_fingerprint": f"cardinality-{node['module_id']}",
                "payload": payload,
                "digest": digest(payload),
                "markdown": f"# {node['module_id']}\n",
                "created_by": ACTOR,
                "created_at": "2026-08-24T00:00:00+00:00",
            },
            research=None,
            event_data={"node_id": node["id"], "module_id": node["module_id"]},
        )
        artifact_refs.append(
            {
                "id": artifact["id"],
                "module_id": artifact["module_id"],
                "digest": artifact["digest"],
            }
        )
    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})

    for invalid_refs in ([artifact_refs[0]], [artifact_refs[0], artifact_refs[0]]):
        invalid_payload = {
            "case_id": case["id"],
            "run_id": run["id"],
            "source_set_id": source_set["id"],
            "source_set_version": source_set["version"],
            "artifacts": invalid_refs,
            "accepted_at": "2026-08-24T00:00:00+00:00",
        }
        with pytest.raises(ValueError, match="RUN_NOT_READY"):
            ledger_set.runs.accept_snapshot(
                case["id"],
                run["id"],
                ACTOR,
                {**invalid_payload, "digest": digest(invalid_payload)},
            )
        assert ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] is None
        assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] is None

    valid_payload = {
        "case_id": case["id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": artifact_refs,
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }
    accepted = ledger_set.runs.accept_snapshot(
        case["id"],
        run["id"],
        ACTOR,
        {**valid_payload, "digest": digest(valid_payload)},
    )
    assert accepted["artifacts"] == artifact_refs


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


def test_run_claim_respects_the_shared_active_job_limit(
    ledger_set: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("caos.memory_ledgers.MAX_ACTIVE_JOBS", 2)
    monkeypatch.setattr("caos.postgres_ledgers.MAX_ACTIVE_JOBS", 2)
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    runs = [
        ledger_set.runs.create_run_with_nodes(
            case["id"],
            ACTOR,
            {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
            [],
        )
        for _ in range(3)
    ]

    first = ledger_set.runs.claim(runs[0]["id"], "worker-a")
    second = ledger_set.runs.claim(runs[1]["id"], "worker-b")
    assert first is not None and second is not None
    assert ledger_set.runs.claim(runs[2]["id"], "worker-c") is None

    ledger_set.runs.finish(runs[0]["id"], first)
    assert ledger_set.runs.claim(runs[2]["id"], "worker-c") is not None


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
    assert completed_run["nodes"][0]["status"] == "succeeded"
    events = ledger_set.runs.events_after(run["id"])
    assert events[:-1] == before_events
    assert events[-1]["id"] == len(before_events) + 1
    assert events[-1]["event"] == "node.succeeded"
    assert events[-1]["data"] == {**event_data, "artifact_id": completed["id"]}


def test_node_completion_copy_failure_is_atomic_and_retryable(ledger_set: Any) -> None:
    class CopyFailure:
        def __deepcopy__(self, memo: dict[int, Any]) -> None:
            raise RuntimeError("forced research copy failure")

    _, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    ledger_set.runs.update_node_fenced(run["id"], token, node["id"], status="running")
    payload = {"debt": 100}
    artifact = {
        "case_id": run["case_id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "created_by": ACTOR,
        "payload": payload,
        "markdown": "# CP-1\n\nDebt: 100\n",
        "digest": digest(payload),
        "input_fingerprint": "copy-failure",
        "created_at": "2026-08-24T00:00:00+00:00",
    }
    event_data = {"node_id": node["id"], "module_id": node["module_id"]}
    before_run = ledger_set.runs.get_run(run["id"])
    before_events = ledger_set.runs.events_after(run["id"])

    with pytest.raises(RuntimeError, match="forced research copy failure"):
        ledger_set.runs.complete_node(
            run["id"],
            token,
            node["id"],
            artifact,
            research={"value": CopyFailure()},
            event_data=event_data,
        )

    assert ledger_set.runs.get_run(run["id"]) == before_run
    assert ledger_set.runs.events_after(run["id"]) == before_events
    assert ledger_set.runs.is_current(run["id"], token) is True
    assert (
        ledger_set.runs.artifact_for_fingerprint(
            run["id"], node["module_id"], artifact["input_fingerprint"]
        )
        is None
    )

    completed = ledger_set.runs.complete_node(
        run["id"],
        token,
        node["id"],
        artifact,
        research={"phase": "complete"},
        event_data=event_data,
    )
    completed_run = ledger_set.runs.get_run(run["id"])
    assert completed_run["nodes"][0]["artifact_id"] == completed["id"]
    assert completed_run["research"] == {"phase": "complete"}
    assert ledger_set.runs.events_after(run["id"])[-1]["event"] == "node.succeeded"


def test_finalization_copy_failure_is_atomic_and_retryable(ledger_set: Any) -> None:
    class CopyFailure:
        def __deepcopy__(self, memo: dict[int, Any]) -> None:
            raise RuntimeError("forced finalization copy failure")

    _, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    artifact_payload = {"debt": 100}
    ledger_set.runs.complete_node(
        run["id"],
        token,
        node["id"],
        {
            "case_id": run["case_id"],
            "run_id": run["id"],
            "module_id": node["module_id"],
            "created_by": ACTOR,
            "payload": artifact_payload,
            "markdown": "# CP-1\n\nDebt: 100\n",
            "digest": digest(artifact_payload),
            "input_fingerprint": "finalization-copy-failure",
            "created_at": "2026-08-24T00:00:00+00:00",
        },
        research=None,
        event_data={"node_id": node["id"], "module_id": node["module_id"]},
    )
    before_run = ledger_set.runs.get_run(run["id"])
    before_events = ledger_set.runs.events_after(run["id"])

    with pytest.raises(RuntimeError, match="forced finalization copy failure"):
        ledger_set.runs.finalize_success(
            run["id"],
            token,
            {"value": CopyFailure()},
            {"run_id": run["id"]},
        )

    assert ledger_set.runs.get_run(run["id"]) == before_run
    assert ledger_set.runs.events_after(run["id"]) == before_events
    assert ledger_set.runs.is_current(run["id"], token) is True

    ledger_set.runs.finalize_success(
        run["id"], token, {"phase": "complete"}, {"run_id": run["id"]}
    )
    completed = ledger_set.runs.get_run(run["id"])
    assert completed["status"] == "succeeded"
    assert completed["research"] == {"phase": "complete"}
    assert ledger_set.runs.events_after(run["id"])[-1]["event"] == "run.succeeded"


def test_snapshot_acceptance_updates_case_and_run_together(
    ledger_set: Any,
) -> None:
    case, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    ledger_set.runs.update_node_fenced(run["id"], token, node["id"], status="running")
    artifact_payload = {"debt": 100}
    artifact_proposal = {
        "case_id": case["id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "input_fingerprint": "snapshot-fingerprint",
        "payload": artifact_payload,
        "digest": digest(artifact_payload),
        "markdown": "# CP-1\n\nDebt: 100\n",
        "created_by": ACTOR,
        "created_at": "2026-08-24T00:00:00+00:00",
    }
    assert "id" not in artifact_proposal
    artifact = ledger_set.runs.complete_node(
        run["id"],
        token,
        node["id"],
        artifact_proposal,
        research=None,
        event_data={"node_id": node["id"], "module_id": node["module_id"]},
    )
    assert artifact["payload"] == artifact_payload
    assert artifact["digest"] == artifact_proposal["digest"]
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

    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})

    foreign_case, foreign_run = _queued_run(ledger_set)
    foreign_source_set = ledger_set.sources.source_set(
        foreign_run["plan"]["source_set_id"]
    )
    assert foreign_source_set is not None
    assert foreign_source_set["case_id"] == foreign_case["id"]

    invalid_payloads = [
        ("RUN_NOT_FOUND", {**base_payload, "case_id": "case_foreign"}),
        ("RUN_NOT_FOUND", {**base_payload, "run_id": "run_foreign"}),
        (
            "SOURCE_SET_CHANGED",
            {**base_payload, "source_set_version": source_set["version"] + 1},
        ),
        (
            "SOURCE_SET_CHANGED",
            {
                **base_payload,
                "source_set_id": foreign_source_set["id"],
                "source_set_version": foreign_source_set["version"],
            },
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

    foreign_node = foreign_run["nodes"][0]
    foreign_token = ledger_set.runs.claim(foreign_run["id"], "foreign-worker")
    assert foreign_token is not None
    ledger_set.runs.update_node_fenced(
        foreign_run["id"], foreign_token, foreign_node["id"], status="running"
    )
    foreign_payload = {"debt": 200}
    foreign_artifact_proposal = {
        "case_id": foreign_case["id"],
        "run_id": foreign_run["id"],
        "module_id": foreign_node["module_id"],
        "input_fingerprint": "foreign-fingerprint",
        "payload": foreign_payload,
        "digest": digest(foreign_payload),
        "markdown": "# CP-1\n\nDebt: 200\n",
        "created_by": ACTOR,
        "created_at": "2026-08-24T00:00:00+00:00",
    }
    assert "id" not in foreign_artifact_proposal
    foreign_artifact = ledger_set.runs.complete_node(
        foreign_run["id"],
        foreign_token,
        foreign_node["id"],
        foreign_artifact_proposal,
        research=None,
        event_data={
            "node_id": foreign_node["id"],
            "module_id": foreign_node["module_id"],
        },
    )
    assert foreign_artifact["payload"] == foreign_payload
    assert foreign_artifact["digest"] == foreign_artifact_proposal["digest"]
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


def test_deliverable_revision_lookup_preserves_immutable_history(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    first_value = {
        "template_id": "caos.full-credit.v1",
        "template_version": "caos.deliverable-template.v1",
        "digest": "a" * 64,
        "content": {"blocks": []},
    }
    first = ledger_set.publications.append_deliverable_revision(
        case["id"], "FULL_CREDIT", ACTOR, 0, first_value
    )
    first_value["content"]["blocks"].append({"forged": True})
    second = ledger_set.publications.append_deliverable_revision(
        case["id"],
        "FULL_CREDIT",
        "second-analyst",
        1,
        {**first_value, "digest": "b" * 64},
    )

    assert ledger_set.publications.get_deliverable_revision(first["id"]) == first
    assert ledger_set.publications.get_deliverable_revision(second["id"]) == second
    assert first["content"]["blocks"] == []


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


def test_note_promotion_delegation_rolls_back_on_source_failure(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    note = ledger_set.publications.create_note(case["id"], ACTOR, "Debt remains 100")
    real_sources = ledger_set.publications._sources

    class FailingSourceCatalog:
        calls = 0
        failed_source_id: str | None = None
        failed_source_set_id: str | None = None

        def ingest_promoted_note(self, candidate: dict[str, Any], actor: str) -> None:
            self.calls += 1
            promoted = real_sources.ingest_promoted_note(candidate, actor)
            source_set = real_sources.current_source_set(case["id"])
            self.failed_source_id = promoted["promoted_source_id"]
            self.failed_source_set_id = source_set["id"]
            raise RuntimeError("forced downstream failure")

    failing_sources = FailingSourceCatalog()
    ledger_set.publications._sources = failing_sources
    before_audit = ledger_set.publications.list_audit()

    with pytest.raises(RuntimeError, match="forced downstream failure"):
        ledger_set.publications.promote_note(case["id"], note["id"], ACTOR)

    assert failing_sources.calls == 1
    assert ledger_set.publications.list_notes(case["id"]) == [note]
    assert ledger_set.sources.list_sources(case["id"]) == []
    assert ledger_set.sources.current_source_set(case["id"]) is None
    assert failing_sources.failed_source_id is not None
    assert failing_sources.failed_source_set_id is not None
    assert ledger_set.sources.get_source(failing_sources.failed_source_id) is None
    assert ledger_set.sources.source_set(failing_sources.failed_source_set_id) is None
    assert ledger_set.publications.list_audit() == before_audit

    ledger_set.publications._sources = real_sources
    promoted = ledger_set.publications.promote_note(case["id"], note["id"], ACTOR)
    assert promoted["promoted"] is True
    assert ledger_set.sources.current_source_set(case["id"])["version"] == 1


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
    current_run, current_snapshot = _accept_empty_run(ledger_set, case_id, source_set)
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
    inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        thesis_request,
        recommendation_request,
        accepted_snapshot_id=current_snapshot["id"],
    )

    with pytest.raises(ValueError, match="SNAPSHOT_REQUIRED"):
        ledger_set.publications.freeze_report(
            case_id, ACTOR, _report_record(previous_snapshot, inputs)
        )
    assert ledger_set.publications.get_report(case_id) is None

    stale_versions_report = _report_record(current_snapshot, inputs)
    stale_versions_report["content"]["thesis_version"] = 0
    stale_versions_report["content"]["recommendation_version"] = 0
    stale_versions_report["preview_digest"] = digest(stale_versions_report["content"])
    stale_versions_report["digest"] = stale_versions_report["preview_digest"]
    with pytest.raises(ValueError, match="THESIS_AND_RECOMMENDATIONS_REQUIRED"):
        ledger_set.publications.freeze_report(case_id, ACTOR, stale_versions_report)
    assert ledger_set.publications.get_report(case_id) is None

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
    assert ledger_set.publications.get_report(case_id) is None

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
    assert ledger_set.publications.get_report(case_id) is None

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
        {**thesis_request, "expected_version": 1},
        {**recommendation_request, "expected_version": 1},
        accepted_snapshot_id=current_snapshot["id"],
    )
    with pytest.raises(ValueError, match="STALE_PREVIEW"):
        ledger_set.publications.approve_report(
            case_id,
            "approver",
            "PENDING_APPROVAL",
            frozen["preview_digest"],
            frozen["input_fingerprint"],
            None,
        )
    assert ledger_set.publications.get_report(case_id) == frozen

    publication_current = ledger_set.publications.freeze_report(
        case_id,
        ACTOR,
        _report_record(current_snapshot, updated_inputs, model_identity),
    )
    _, next_snapshot = _accept_empty_run(ledger_set, case_id, source_set)
    with pytest.raises(ValueError, match="STALE_PREVIEW"):
        ledger_set.publications.approve_report(
            case_id,
            "approver",
            "PENDING_APPROVAL",
            publication_current["preview_digest"],
            publication_current["input_fingerprint"],
            None,
        )
    assert ledger_set.publications.get_report(case_id) == publication_current

    final_inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        {**thesis_request, "expected_version": 2},
        {**recommendation_request, "expected_version": 2},
        accepted_snapshot_id=next_snapshot["id"],
    )
    final_report = ledger_set.publications.freeze_report(
        case_id, ACTOR, _report_record(next_snapshot, final_inputs)
    )
    approved = ledger_set.publications.approve_report(
        case_id,
        "approver",
        "PENDING_APPROVAL",
        final_report["preview_digest"],
        final_report["input_fingerprint"],
        "Reviewed",
    )
    assert approved["status"] == "APPROVED"
    assert approved["approved_by"] == "approver"
    assert approved["approval_comment"] == "Reviewed"


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


def test_model_result_validation_matrix_and_copy_isolation(ledger_set: Any) -> None:
    queued, _ = ledger_set.models.queue_build(_accepted_model_input(ledger_set), ACTOR)
    token = ledger_set.models.claim(queued["id"], "model-worker")
    assert token is not None
    valid = _model_result()
    missing_qa = {
        "payload": copy.deepcopy(valid["payload"]),
        "payload_digest": valid["payload_digest"],
    }
    mismatched_digest = {**copy.deepcopy(valid), "payload_digest": "0" * 64}
    unexpected_field = {**copy.deepcopy(valid), "unexpected": True}
    malformed_tabs = copy.deepcopy(valid)
    malformed_tabs["payload"]["tabs"] = {}
    malformed_tabs["payload_digest"] = digest(malformed_tabs["payload"])
    incomplete_cell = copy.deepcopy(valid)
    incomplete_cell["payload"]["tabs"][0]["cells"] = [{"address": "A1"}]
    incomplete_cell["qa"]["worksheet_cell_count"] = 1
    incomplete_cell["payload_digest"] = digest(incomplete_cell["payload"])
    nonfinite_width = copy.deepcopy(valid)
    nonfinite_width["payload"]["tabs"][0]["columns"][0]["width"] = float("nan")
    nonfinite_width["payload_digest"] = digest(nonfinite_width["payload"])

    for invalid in (
        missing_qa,
        mismatched_digest,
        unexpected_field,
        malformed_tabs,
        incomplete_cell,
        nonfinite_width,
    ):
        assert ledger_set.models.renew(queued["id"], token) is True
        with pytest.raises(ValueError, match="MODEL_RESULT_INVALID"):
            ledger_set.models.complete(queued["id"], token, invalid, "model-worker")
        assert ledger_set.models.is_current(queued["id"], token) is True
        assert ledger_set.models.get_build(queued["id"])["status"] == "BUILDING"

    assert ledger_set.models.renew(queued["id"], token) is True
    ready = ledger_set.models.complete(queued["id"], token, valid, "model-worker")
    valid["payload"]["identity"]["issuer_name"] = "mutated after completion"
    assert ready["status"] == "READY"
    assert (
        ledger_set.models.get_build(queued["id"])["payload"]["identity"]["issuer_name"]
        == "Issuer"
    )


def test_model_errors_and_export_failure_requeue_are_bounded(ledger_set: Any) -> None:
    queued, _ = ledger_set.models.queue_build(_accepted_model_input(ledger_set), ACTOR)
    calculate = ledger_set.models.claim(queued["id"], "model-worker")
    assert calculate is not None
    with pytest.raises(ValueError, match="MODEL_ERROR_INVALID"):
        ledger_set.models.fail(
            queued["id"],
            calculate,
            {"code": "X", "detail": "x" * 501},
            "model-worker",
        )
    assert ledger_set.models.is_current(queued["id"], calculate) is True
    calculation_error = {
        "code": "MODEL_CALCULATION_FAILED",
        "detail": "bounded",
    }
    failed = ledger_set.models.fail(
        queued["id"], calculate, calculation_error, "model-worker"
    )
    calculation_error["detail"] = "mutated after failure"
    assert failed["status"] == "FAILED"
    assert ledger_set.models.get_build(queued["id"])["error"]["detail"] == "bounded"

    ledger_set.models.retry_build(queued["id"], "reviewer")
    retry = ledger_set.models.claim(queued["id"], "retry-worker")
    assert retry is not None
    ledger_set.models.complete(queued["id"], retry, _model_result(), "retry-worker")
    exporting, created = ledger_set.models.queue_export(queued["id"], "approver")
    assert created is True and exporting["export"]["status"] == "QUEUED"
    assert ledger_set.models.pending_jobs() == [(queued["id"], "approver", "export")]
    export = ledger_set.models.claim(queued["id"], "export-worker", kind="export")
    assert export is not None
    with pytest.raises(ValueError, match="MODEL_ERROR_INVALID"):
        ledger_set.models.fail(
            queued["id"],
            export,
            {"code": "X" * 81, "detail": "bounded"},
            "export-worker",
            kind="export",
        )
    export_error = {"code": "MODEL_EXPORT_FAILED", "detail": "bounded"}
    export_failed = ledger_set.models.fail(
        queued["id"], export, export_error, "export-worker", kind="export"
    )
    export_error["detail"] = "mutated after failure"
    assert export_failed["status"] == "READY"
    assert export_failed["export"] == {
        "status": "FAILED",
        "error": {"code": "MODEL_EXPORT_FAILED", "detail": "bounded"},
    }
    retried, requeued = ledger_set.models.queue_export(queued["id"], "analyst")
    assert requeued is True and retried["export"]["status"] == "QUEUED"
    assert ledger_set.models.pending_jobs() == [(queued["id"], "analyst", "export")]


def test_model_revision_signoff_is_append_only_atomic_and_cas_guarded(
    ledger_set: Any,
) -> None:
    build = _ready_model_build(ledger_set)
    proposal = _model_revision(build)
    before_audit = ledger_set.publications.list_audit()

    signed = ledger_set.models.sign_off_revision(
        proposal,
        ACTOR,
        expected_head_revision_id=None,
        expected_current_build_id=build["id"],
        expected_current_input_fingerprint=build["input_fingerprint"],
    )

    assert "id" not in proposal
    assert signed["revision_number"] == 1
    assert signed["signed_by"] == ACTOR
    assert signed["export"] == {"status": "QUEUED", "error": None}
    assert ledger_set.models.get_revision(signed["id"]) == signed
    assert ledger_set.models.list_revisions(build["case_id"]) == [signed]
    assert ledger_set.models.get_revision_head(build["case_id"]) == signed
    assert ledger_set.models.pending_revision_exports() == [(signed["id"], ACTOR)]
    assert len(ledger_set.publications.list_audit()) == len(before_audit) + 1

    competing = _model_revision(build, preview_digest="c" * 64)
    with pytest.raises(ledgers.RevisionConflictError) as conflict:
        ledger_set.models.sign_off_revision(
            competing,
            "second-analyst",
            expected_head_revision_id=None,
            expected_current_build_id=build["id"],
            expected_current_input_fingerprint=build["input_fingerprint"],
        )
    assert conflict.value.current["id"] == signed["id"]
    assert ledger_set.models.list_revisions(build["case_id"]) == [signed]
    assert ledger_set.models.get_revision_head(build["case_id"]) == signed
    assert len(ledger_set.publications.list_audit()) == len(before_audit) + 1

    successor = ledger_set.models.sign_off_revision(
        {**competing, "parent_revision_id": signed["id"]},
        "second-analyst",
        expected_head_revision_id=signed["id"],
        expected_current_build_id=build["id"],
        expected_current_input_fingerprint=build["input_fingerprint"],
    )
    assert successor["revision_number"] == 2
    assert [item["id"] for item in ledger_set.models.list_revisions(build["case_id"])] == [
        signed["id"],
        successor["id"],
    ]
    assert ledger_set.models.get_revision_head(build["case_id"]) == successor


def test_model_revision_signoff_validates_exact_current_build_identity(
    ledger_set: Any,
) -> None:
    build = _ready_model_build(ledger_set)
    proposal = _model_revision(build)
    before_audit = ledger_set.publications.list_audit()

    invalid_changes = (
        {"build_input_fingerprint": "0" * 64},
        {"build_payload_digest": "0" * 64},
        {"registry_digest": "0" * 64},
        {"accepted_snapshot_id": "snap_foreign"},
        {"assumptions_digest": "0" * 64},
        {"outputs_digest": "0" * 64},
    )
    for change in invalid_changes:
        with pytest.raises(ValueError, match="MODEL_REVISION_INVALID"):
            ledger_set.models.sign_off_revision(
                {**proposal, **change},
                ACTOR,
                expected_head_revision_id=None,
                expected_current_build_id=build["id"],
                expected_current_input_fingerprint=build["input_fingerprint"],
            )
    assert ledger_set.models.list_revisions(build["case_id"]) == []
    assert ledger_set.models.get_revision_head(build["case_id"]) is None
    assert ledger_set.publications.list_audit() == before_audit


def test_model_revision_signoff_cas_rejects_newer_ready_build_without_partial_state(
    ledger_set: Any,
) -> None:
    previewed_build = _ready_model_build(ledger_set)
    proposal = _model_revision(previewed_build)
    current_build = _newer_ready_model_build(ledger_set, previewed_build)
    before_audit = ledger_set.publications.list_audit()

    with pytest.raises(ledgers.RevisionConflictError) as conflict:
        ledger_set.models.sign_off_revision(
            proposal,
            ACTOR,
            expected_head_revision_id=None,
            expected_current_build_id=previewed_build["id"],
            expected_current_input_fingerprint=previewed_build["input_fingerprint"],
        )

    assert conflict.value.current is None
    assert conflict.value.current_build == {
        "id": current_build["id"],
        "input_fingerprint": current_build["input_fingerprint"],
        "accepted_snapshot_id": current_build["accepted_snapshot_id"],
        "status": "READY",
    }
    assert ledger_set.models.list_revisions(previewed_build["case_id"]) == []
    assert ledger_set.models.get_revision_head(previewed_build["case_id"]) is None
    assert ledger_set.models.pending_revision_exports() == []
    assert ledger_set.publications.list_audit() == before_audit


def test_model_build_authority_order_ignores_equal_timestamps_and_opposed_ids(
    ledger_set: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted = _accepted_model_input(ledger_set)
    controlled_ids = iter(("model_z_older", "model_a_newer"))
    if isinstance(ledger_set, MemoryLedgerSet):
        state = ledger_set.models._state
        original_new_id = state.new_id

        def controlled_new_id(prefix: str) -> str:
            return next(controlled_ids) if prefix == "model" else original_new_id(prefix)

        monkeypatch.setattr(state, "new_id", controlled_new_id)
    else:
        original_new_id = postgres_ledgers_module._new_id

        def controlled_new_id(prefix: str) -> str:
            return next(controlled_ids) if prefix == "model" else original_new_id(prefix)

        monkeypatch.setattr(postgres_ledgers_module, "_new_id", controlled_new_id)

    queued_at = "2026-08-26T00:00:00+00:00"
    builds: list[dict[str, Any]] = []
    for fingerprint, worker in (("c" * 64, "older-worker"), ("d" * 64, "newer-worker")):
        queued, created = ledger_set.models.queue_build(
            {
                **accepted,
                "input_fingerprint": fingerprint,
                "queued_at": queued_at,
                "calculation_runtime": {
                    "assumption_registry_version": "cp-model.assumptions.v1",
                    "assumption_registry_digest": "a" * 64,
                    "calculation_contract_version": "cp-model.calculation.v1",
                },
            },
            ACTOR,
        )
        assert created is True
        token = ledger_set.models.claim(queued["id"], worker)
        assert token is not None
        builds.append(
            ledger_set.models.complete(queued["id"], token, _model_result(), worker)
        )
    older, newer = builds

    listed = ledger_set.models.list_builds(older["case_id"])
    assert [build["id"] for build in listed] == [newer["id"], older["id"]]
    assert all("authority_order" not in build for build in listed)
    before_audit = ledger_set.publications.list_audit()
    with pytest.raises(ledgers.RevisionConflictError) as conflict:
        ledger_set.models.sign_off_revision(
            _model_revision(older),
            ACTOR,
            expected_head_revision_id=None,
            expected_current_build_id=older["id"],
            expected_current_input_fingerprint=older["input_fingerprint"],
        )

    assert conflict.value.current is None
    assert conflict.value.current_build == {
        "id": newer["id"],
        "input_fingerprint": newer["input_fingerprint"],
        "accepted_snapshot_id": newer["accepted_snapshot_id"],
        "status": "READY",
    }
    assert ledger_set.models.list_revisions(older["case_id"]) == []
    assert ledger_set.models.get_revision_head(older["case_id"]) is None
    assert ledger_set.models.pending_revision_exports() == []
    assert ledger_set.publications.list_audit() == before_audit


def test_model_build_authority_order_rejects_caller_supplied_values(
    ledger_set: Any,
) -> None:
    accepted = _accepted_model_input(ledger_set)
    before_audit = ledger_set.publications.list_audit()

    with pytest.raises(ValueError, match="MODEL_BUILD_INVALID"):
        ledger_set.models.queue_build(
            {
                **accepted,
                "authority_order": 999,
                "calculation_runtime": {
                    "assumption_registry_version": "cp-model.assumptions.v1",
                    "assumption_registry_digest": "a" * 64,
                    "calculation_contract_version": "cp-model.calculation.v1",
                },
            },
            ACTOR,
        )

    assert ledger_set.models.list_builds(accepted["case_id"]) == []
    assert ledger_set.publications.list_audit() == before_audit


def test_postgres_model_revision_signoff_serializes_with_newer_build_completion(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    database_url = postgres_ledger_set._database_url
    previewed_build = _ready_model_build(postgres_ledger_set)
    proposal = _model_revision(previewed_build)
    queued, created = postgres_ledger_set.models.queue_build(
        {
            "case_id": previewed_build["case_id"],
            "accepted_run_id": previewed_build["accepted_run_id"],
            "accepted_snapshot_id": previewed_build["accepted_snapshot_id"],
            "source_set_id": previewed_build["source_set_id"],
            "input_fingerprint": "e" * 64,
            "worksheet_schema_version": previewed_build["worksheet_schema_version"],
            "calculation_runtime": copy.deepcopy(
                previewed_build["calculation_runtime"]
            ),
        },
        ACTOR,
    )
    assert created is True
    token = postgres_ledger_set.models.claim(queued["id"], "new-model-worker")
    assert token is not None
    before_audit = postgres_ledger_set.publications.list_audit()

    completing = _GatedPostgresLedgerSet(database_url)
    signing = _ObservedPostgresLedgerSet(database_url)
    gate = completing.gate_next_case_lock()
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            completed = executor.submit(
                completing.models.complete,
                queued["id"],
                token,
                _model_result(),
                "new-model-worker",
            )
            assert gate.acquired.wait(timeout=5)
            signing.observe_next_connection()
            signed = executor.submit(
                signing.models.sign_off_revision,
                proposal,
                ACTOR,
                expected_head_revision_id=None,
                expected_current_build_id=previewed_build["id"],
                expected_current_input_fingerprint=previewed_build[
                    "input_fingerprint"
                ],
            )
            signing_pid = signing.wait_for_observed_connection()
            _wait_for_postgres_blocker(database_url, signing_pid)
            gate.release.set()
            current_build = completed.result(timeout=15)
            with pytest.raises(ledgers.RevisionConflictError) as conflict:
                signed.result(timeout=15)
    finally:
        gate.release.set()

    assert conflict.value.current is None
    assert conflict.value.current_build == {
        "id": current_build["id"],
        "input_fingerprint": current_build["input_fingerprint"],
        "accepted_snapshot_id": current_build["accepted_snapshot_id"],
        "status": "READY",
    }
    assert postgres_ledger_set.models.list_revisions(previewed_build["case_id"]) == []
    assert postgres_ledger_set.models.get_revision_head(previewed_build["case_id"]) is None
    assert postgres_ledger_set.models.pending_revision_exports() == []
    added_audit = postgres_ledger_set.publications.list_audit()[len(before_audit) :]
    assert [event["action"] for event in added_audit] == ["model.calculate.succeeded"]


def test_model_revision_export_failure_is_retryable_without_demoting_revision(
    ledger_set: Any,
) -> None:
    build = _ready_model_build(ledger_set)
    signed = ledger_set.models.sign_off_revision(
        _model_revision(build),
        ACTOR,
        expected_head_revision_id=None,
        expected_current_build_id=build["id"],
        expected_current_input_fingerprint=build["input_fingerprint"],
    )
    token = ledger_set.models.claim_revision_export(signed["id"], "export-worker")
    assert token is not None
    assert ledger_set.models.renew_revision_export(signed["id"], token) is True
    assert ledger_set.models.revision_export_is_current(signed["id"], token) is True

    failed = ledger_set.models.fail_revision_export(
        signed["id"],
        token,
        {"code": "MODEL_REVISION_EXPORT_FAILED", "detail": "bounded"},
        "export-worker",
    )
    assert failed["signed_by"] == ACTOR
    assert failed["export"]["status"] == "FAILED"
    assert ledger_set.models.get_revision_head(build["case_id"])["id"] == signed["id"]
    retried, queued = ledger_set.models.queue_revision_export(
        signed["id"], "reviewer"
    )
    assert queued is True and retried["export"]["status"] == "QUEUED"
    assert ledger_set.models.pending_revision_exports() == [(signed["id"], "reviewer")]


def test_model_build_rejects_cross_case_and_superseded_authority(
    ledger_set: Any,
) -> None:
    build = _accepted_model_input(ledger_set)
    other = _accepted_model_input(ledger_set)
    with pytest.raises(ValueError, match="MODEL_BUILD_INVALID"):
        ledger_set.models.queue_build(
            {**build, "source_set_id": other["source_set_id"]}, ACTOR
        )

    source_set = ledger_set.sources.source_set(build["source_set_id"])
    assert source_set is not None
    current_run, current_snapshot = _accept_empty_run(
        ledger_set, build["case_id"], source_set
    )
    with pytest.raises(ValueError, match="MODEL_BUILD_INVALID"):
        ledger_set.models.queue_build(build, ACTOR)

    current, created = ledger_set.models.queue_build(
        {
            **build,
            "accepted_run_id": current_run["id"],
            "accepted_snapshot_id": current_snapshot["id"],
            "input_fingerprint": "d" * 64,
        },
        ACTOR,
    )
    assert created is True and current["accepted_snapshot_id"] == current_snapshot["id"]


def test_model_and_workflow_claims_share_one_active_job_budget(
    ledger_set: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("caos.memory_ledgers.MAX_ACTIVE_JOBS", 2)
    monkeypatch.setattr("caos.postgres_ledgers.MAX_ACTIVE_JOBS", 2)
    queued, _ = ledger_set.models.queue_build(_accepted_model_input(ledger_set), ACTOR)
    time.sleep(LEASE_SECONDS + 0.1)
    model_token = ledger_set.models.claim(queued["id"], "model-worker")
    assert model_token is not None
    _, first_run = _queued_run(ledger_set)
    _, blocked_run = _queued_run(ledger_set)
    workflow_token = ledger_set.runs.claim(first_run["id"], "workflow-worker")
    assert workflow_token is not None
    assert ledger_set.runs.claim(blocked_run["id"], "blocked-worker") is None

    ledger_set.models.fail(
        queued["id"],
        model_token,
        {"code": "MODEL_CALCULATION_FAILED", "detail": "bounded"},
        "model-worker",
    )
    assert ledger_set.runs.claim(blocked_run["id"], "replacement-worker") is not None


def test_pending_job_reads_are_authoritative(ledger_set: Any) -> None:
    _, run = _queued_run(ledger_set)
    build = _accepted_model_input(ledger_set)
    queued, _ = ledger_set.models.queue_build(build, ACTOR)

    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]
    assert ledger_set.models.pending_jobs() == [(queued["id"], ACTOR, "calculate")]


def test_postgres_two_connection_uniqueness_and_claim_races(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    case = _case(postgres_ledger_set)
    source = _source(case["id"])

    def ingest() -> str:
        try:
            postgres_ledger_set.sources.ingest(source, ACTOR)
            return "created"
        except ValueError as exc:
            assert str(exc) == "source content already active"
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: ingest(), range(2))) == [
            "conflict",
            "created",
        ]
    assert "current_source_set_id" not in postgres_ledger_set.runs.get_case(case["id"])

    thesis = {"core_thesis": "Defensible", "evidence_ids": []}

    def append() -> str:
        try:
            postgres_ledger_set.publications.append_thesis(case["id"], ACTOR, 0, thesis)
            return "created"
        except ValueError as exc:
            assert str(exc) == "VERSION_CONFLICT"
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: append(), range(2))) == [
            "conflict",
            "created",
        ]
    with pytest.raises(ValueError, match="VERSION_CONFLICT"):
        postgres_ledger_set.publications.append_thesis(
            case["id"],
            ACTOR,
            None,
            thesis,  # type: ignore[arg-type]
        )

    run = postgres_ledger_set.runs.create_run_with_nodes(
        case["id"], ACTOR, {"pathway": "EARNINGS_UPDATE"}, []
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        tokens = list(
            executor.map(
                lambda worker: postgres_ledger_set.runs.claim(run["id"], worker),
                ("worker-a", "worker-b"),
            )
        )
    assert sum(token is not None for token in tokens) == 1


def test_postgres_loan_import_and_withdrawal_serialize_without_deadlock(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    database_url = postgres_ledger_set._database_url
    for leader_kind in ("import", "withdraw"):
        case = _case(postgres_ledger_set)
        source = postgres_ledger_set.sources.ingest(_source(case["id"]), ACTOR)
        record = {
            "case_id": case["id"],
            "source_id": source["id"],
            "source_filename": source["filename"],
            "source_sha256": source["sha256"],
            "workbook_date": "2026-08-24",
            "template_version": f"race-template-{leader_kind}",
            "importer_version": "race-importer-v1",
            "universe_digest": "e" * 64,
            "row_count": 1,
            "status": "ACTIVE",
            "findings": [],
        }
        rows = [{"instrument_key": "loan-1", "borrower": "Issuer"}]
        leader = _GatedPostgresLedgerSet(database_url)
        follower = _ObservedPostgresLedgerSet(database_url)
        gate = leader.gate_next_case_lock()

        def import_loan(ledgers: PostgresLedgerSet) -> str:
            try:
                _saved, created = ledgers.sources.save_loan_universe_import(
                    record, rows, ACTOR
                )
                assert created is True
                return "imported"
            except ValueError as exc:
                assert str(exc) == "RV_SOURCE_NOT_ACTIVE"
                return "source-inactive"

        def withdraw_source(ledgers: PostgresLedgerSet) -> str:
            withdrawn = ledgers.sources.withdraw(case["id"], source["id"], ACTOR)
            assert withdrawn is not None and withdrawn["withdrawn"] is True
            return "withdrawn"

        leader_operation = import_loan if leader_kind == "import" else withdraw_source
        follower_operation = withdraw_source if leader_kind == "import" else import_loan
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(leader_operation, leader)
                assert gate.acquired.wait(timeout=5)
                follower.observe_next_connection()
                second = executor.submit(follower_operation, follower)
                follower_pid = follower.wait_for_observed_connection()
                _wait_for_postgres_blocker(database_url, follower_pid)
                gate.release.set()
                outcomes = {first.result(timeout=15), second.result(timeout=15)}
        finally:
            gate.release.set()

        expected = (
            {"imported", "withdrawn"}
            if leader_kind == "import"
            else {"source-inactive", "withdrawn"}
        )
        assert outcomes == expected
        assert postgres_ledger_set.sources.list_sources(case["id"]) == []
        withdrawn_source = postgres_ledger_set.sources.get_source(source["id"])
        assert withdrawn_source is not None and withdrawn_source["withdrawn"] is True
        assert postgres_ledger_set.sources.active_loan_universe(case["id"]) is None


def test_postgres_assumption_creation_and_withdrawal_serialize_by_case_lock(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    database_url = postgres_ledger_set._database_url
    for leader_kind in ("create", "withdraw"):
        case = _case(postgres_ledger_set)
        source = postgres_ledger_set.sources.ingest(
            _source(case["id"], sha256=("c" if leader_kind == "create" else "d") * 64),
            ACTOR,
        )
        leader = _GatedPostgresLedgerSet(database_url)
        follower = _ObservedPostgresLedgerSet(database_url)
        gate = leader.gate_next_case_lock()

        def create_assumption(ledgers: PostgresLedgerSet) -> str:
            try:
                created = ledgers.publications.create_assumption(
                    case["id"],
                    ACTOR,
                    "Debt is 100",
                    [source["id"]],
                    ["CP-1"],
                )
                assert created["status"] == "PROVISIONAL"
                assert created["stale"] is False
                return "created"
            except ValueError as exc:
                assert str(exc) == "EVIDENCE_SOURCE_WITHDRAWN"
                return "source-withdrawn"

        def withdraw_source(ledgers: PostgresLedgerSet) -> str:
            withdrawn = ledgers.sources.withdraw(case["id"], source["id"], ACTOR)
            assert withdrawn is not None and withdrawn["withdrawn"] is True
            return "withdrawn"

        leader_operation = (
            create_assumption if leader_kind == "create" else withdraw_source
        )
        follower_operation = (
            withdraw_source if leader_kind == "create" else create_assumption
        )
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(leader_operation, leader)
                assert gate.acquired.wait(timeout=5)
                follower.observe_next_connection()
                second = executor.submit(follower_operation, follower)
                follower_pid = follower.wait_for_observed_connection()
                _wait_for_postgres_blocker(database_url, follower_pid)
                gate.release.set()
                outcomes = {first.result(timeout=15), second.result(timeout=15)}
        finally:
            gate.release.set()

        stored = postgres_ledger_set.publications.list_assumptions(case["id"])
        if leader_kind == "create":
            assert outcomes == {"created", "withdrawn"}
            assert len(stored) == 1
            assert stored[0]["status"] == "STALE"
            assert stored[0]["stale"] is True
        else:
            assert outcomes == {"source-withdrawn", "withdrawn"}
            assert stored == []
        withdrawn_source = postgres_ledger_set.sources.get_source(source["id"])
        assert withdrawn_source is not None and withdrawn_source["withdrawn"] is True


def test_postgres_concurrent_model_queue_is_idempotent_and_preserves_actor(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    build = _accepted_model_input(postgres_ledger_set)
    actors = ("requester-a", "requester-b")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda actor: (
                    actor,
                    *postgres_ledger_set.models.queue_build(build, actor),
                ),
                actors,
            )
        )

    assert sum(created for _actor, _record, created in results) == 1
    assert len({record["id"] for _actor, record, _created in results}) == 1
    winner, queued, _ = next(item for item in results if item[2])
    assert queued["created_by"] == winner
    assert postgres_ledger_set.models.pending_jobs() == [
        (queued["id"], winner, "calculate")
    ]


def test_postgres_two_writer_revision_cas_has_one_atomic_winner(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    build = _ready_model_build(postgres_ledger_set)
    proposal = _model_revision(build)

    def sign(actor: str) -> tuple[str, str]:
        try:
            revision = postgres_ledger_set.models.sign_off_revision(
                proposal,
                actor,
                expected_head_revision_id=None,
                expected_current_build_id=build["id"],
                expected_current_input_fingerprint=build["input_fingerprint"],
            )
            return "signed", revision["id"]
        except ledgers.RevisionConflictError as exc:
            assert exc.current is not None
            return "conflict", exc.current["id"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(sign, ("analyst-a", "analyst-b")))

    assert sorted(status for status, _revision_id in outcomes) == [
        "conflict",
        "signed",
    ]
    assert len({revision_id for _status, revision_id in outcomes}) == 1
    revisions = postgres_ledger_set.models.list_revisions(build["case_id"])
    assert len(revisions) == 1
    assert postgres_ledger_set.models.get_revision_head(build["case_id"]) == revisions[0]
    signed_audits = [
        event
        for event in postgres_ledger_set.publications.list_audit()
        if event["action"] == "model.revision.signed"
    ]
    assert len(signed_audits) == 1


def test_postgres_stale_attempt_cannot_change_fenced_authority(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    case, run = _queued_run(postgres_ledger_set)
    node = run["nodes"][0]
    stale = postgres_ledger_set.runs.claim(run["id"], "stale-worker")
    assert stale is not None
    postgres_ledger_set.runs.update_node_fenced(
        run["id"], stale, node["id"], status="running"
    )
    time.sleep(LEASE_SECONDS + 0.1)
    replacement = postgres_ledger_set.runs.claim(run["id"], "replacement-worker")
    assert replacement is not None
    before_run = postgres_ledger_set.runs.get_run(run["id"])
    before_events = postgres_ledger_set.runs.events_after(run["id"])
    proposal = {
        "case_id": case["id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "created_by": ACTOR,
        "payload": {"debt": 100},
        "markdown": "# CP-1\n",
        "digest": digest({"debt": 100}),
        "input_fingerprint": "stale-proof",
        "created_at": "2026-08-24T00:00:00+00:00",
    }
    stale_writes = (
        lambda: postgres_ledger_set.runs.update_run_fenced(
            run["id"], stale, status="failed"
        ),
        lambda: postgres_ledger_set.runs.update_node_fenced(
            run["id"], stale, node["id"], status="succeeded"
        ),
        lambda: postgres_ledger_set.runs.emit_fenced(
            run["id"], stale, "stale.event", {}
        ),
        lambda: postgres_ledger_set.runs.complete_node(
            run["id"], stale, node["id"], proposal, None, {}
        ),
        lambda: postgres_ledger_set.runs.finalize_success(run["id"], stale, None, {}),
    )
    for stale_write in stale_writes:
        with pytest.raises(JobFencedError, match="stale workflow attempt"):
            stale_write()
    assert postgres_ledger_set.runs.get_run(run["id"]) == before_run
    assert postgres_ledger_set.runs.events_after(run["id"]) == before_events
    assert (
        postgres_ledger_set.runs.artifact_for_fingerprint(
            run["id"], node["module_id"], proposal["input_fingerprint"]
        )
        is None
    )
    with pytest.raises(ValueError, match="RUN_NOT_READY"):
        postgres_ledger_set.runs.accept_snapshot(
            case["id"],
            run["id"],
            ACTOR,
            {
                "case_id": case["id"],
                "run_id": run["id"],
                "source_set_id": run["plan"]["source_set_id"],
                "source_set_version": 1,
                "artifacts": [],
                "accepted_at": "2026-08-24T00:00:00+00:00",
                "digest": "0" * 64,
            },
        )
    assert postgres_ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] is None

    model_input = _accepted_model_input(postgres_ledger_set)
    build, _ = postgres_ledger_set.models.queue_build(model_input, ACTOR)
    stale_model = postgres_ledger_set.models.claim(build["id"], "stale-model")
    assert stale_model is not None
    time.sleep(LEASE_SECONDS + 0.1)
    assert postgres_ledger_set.models.claim(build["id"], "replacement-model")
    before_build = postgres_ledger_set.models.get_build(build["id"])
    with pytest.raises(JobFencedError, match="stale model attempt"):
        postgres_ledger_set.models.complete(
            build["id"], stale_model, _model_result(), "stale-model"
        )
    assert postgres_ledger_set.models.get_build(build["id"]) == before_build


def test_postgres_remaining_protocol_surface(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    case = _case(postgres_ledger_set)
    assert postgres_ledger_set.runs.add_member(
        case["id"], ACTOR, "reviewer", "APPROVER", actor_role="ADMIN"
    )
    assert postgres_ledger_set.runs.is_member(case["id"], "reviewer", {"APPROVER"})
    assert postgres_ledger_set.runs.list_cases("reviewer")[0]["id"] == case["id"]
    source = postgres_ledger_set.sources.ingest(_source(case["id"]), ACTOR)
    run = postgres_ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source["source_set"]["id"]},
        [],
    )
    postgres_ledger_set.runs.emit(run["id"], "manual.check", {"ok": True})
    assert postgres_ledger_set.runs.wait_for_events(run["id"], 0)[0]["event"] == (
        "manual.check"
    )
    thesis = postgres_ledger_set.publications.append_thesis(
        case["id"],
        ACTOR,
        0,
        {"core_thesis": "Defensible", "evidence_ids": [source["id"]]},
    )
    recommendation = postgres_ledger_set.publications.append_recommendations(
        case["id"],
        ACTOR,
        0,
        {"rows": [], "analytical_dependency_ids": []},
    )
    assert thesis["version"] == recommendation["version"] == 1
    rv = postgres_ledger_set.publications.save_rv_universe(
        case["id"], ACTOR, {"instruments": []}
    )
    assert postgres_ledger_set.publications.get_rv_universe(case["id"]) == rv
    draft = postgres_ledger_set.publications.create_methodology_draft(
        {"module_id": "CP-1", "before": 1, "after": 2}, ACTOR
    )
    validated = postgres_ledger_set.publications.validate_methodology_draft(
        draft["id"], "reviewer"
    )
    confirmed = postgres_ledger_set.publications.confirm_methodology_draft(
        draft["id"], "reviewer", "signed"
    )
    assert validated["status"] == "VALIDATED"
    assert confirmed["status"] == "CONFIRMED_PENDING_SIGNED_AUTHORITY"

    model_input = _accepted_model_input(postgres_ledger_set)
    build, _ = postgres_ledger_set.models.queue_build(model_input, ACTOR)
    calculate_token = postgres_ledger_set.models.claim(build["id"], "model-worker")
    assert calculate_token
    postgres_ledger_set.models.complete(
        build["id"], calculate_token, _model_result(), "model-worker"
    )
    _, queued = postgres_ledger_set.models.queue_export(build["id"], ACTOR)
    assert queued
    export_token = postgres_ledger_set.models.claim(
        build["id"], "export-worker", kind="export"
    )
    assert export_token
    sha256 = "e" * 64
    exported = postgres_ledger_set.models.complete(
        build["id"],
        export_token,
        {
            "vault_key": f"models/case/build/{sha256}.xlsx",
            "filename": "model.xlsx",
            "sha256": sha256,
            "size": 1,
            "formulas_validated": 0,
            "semantic_checks": 0,
            "renderer_version": "contract-v1",
            "renderer_sha256": "f" * 64,
            "calculation_engine": "contract-v1",
        },
        "export-worker",
        kind="export",
    )
    assert exported["export"]["status"] == "READY"
    postgres_ledger_set.models.record_export_download(
        build["id"], model_input["case_id"], ACTOR
    )


def test_run_public_shape_includes_ordered_nodes_and_events(ledger_set: Any) -> None:
    case = _case(ledger_set)
    source_set = ledger_set.sources.ingest(_source(case["id"]), ACTOR)["source_set"]
    created = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [
            {"module_id": "CP-B", "dependencies": [], "stage": 1},
            {"module_id": "CP-A", "dependencies": [], "stage": 1},
        ],
    )

    assert [node["module_id"] for node in created["nodes"]] == ["CP-B", "CP-A"]
    assert created["events"] == []
    ledger_set.runs.emit(created["id"], "manual.check", {"ok": True})
    events = ledger_set.runs.events_after(created["id"])
    fetched = ledger_set.runs.get_run(created["id"])

    assert fetched is not None
    assert fetched["nodes"] == created["nodes"]
    assert fetched["events"] == events
    assert ledger_set.runs.list_runs(case["id"]) == [fetched]
    assert ledger_set.runs.latest_run(case["id"]) == fetched


def test_distinct_same_body_note_promotion_rejects_active_duplicate(
    ledger_set: Any,
) -> None:
    case = _case(ledger_set)
    first_note = ledger_set.publications.create_note(
        case["id"], ACTOR, "Debt remains 100"
    )
    second_note = ledger_set.publications.create_note(
        case["id"], ACTOR, "Debt remains 100"
    )
    first = ledger_set.publications.promote_note(case["id"], first_note["id"], ACTOR)
    source_set = ledger_set.sources.current_source_set(case["id"])

    with pytest.raises(ValueError) as exc_info:
        ledger_set.publications.promote_note(case["id"], second_note["id"], ACTOR)

    assert str(exc_info.value) == "source content already active"
    notes = {
        note["id"]: note for note in ledger_set.publications.list_notes(case["id"])
    }
    assert notes == {first["id"]: first, second_note["id"]: second_note}
    assert ledger_set.sources.current_source_set(case["id"]) == source_set
    assert [source["id"] for source in ledger_set.sources.list_sources(case["id"])] == [
        first["promoted_source_id"]
    ]
    replay = ledger_set.publications.promote_note(case["id"], first_note["id"], ACTOR)
    assert replay["promoted_source_id"] == first["promoted_source_id"]
    assert ledger_set.sources.current_source_set(case["id"]) == source_set


def test_postgres_claim_ignores_completed_coordinator_history(
    postgres_ledger_set: PostgresLedgerSet,
) -> None:
    import psycopg

    case, run = _queued_run(postgres_ledger_set)
    database_url = os.environ["CAOS_TEST_DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE jobs SET state='succeeded' WHERE run_id=%s AND node_id IS NULL",
                (run["id"],),
            )
            cursor.execute(
                "INSERT INTO jobs(run_id, node_id, state, actor, budget_reserved) "
                "VALUES (%s, NULL, 'queued', %s, 0)",
                (run["id"], ACTOR),
            )

    assert (run["id"], ACTOR) in postgres_ledger_set.runs.pending_runs()
    with ThreadPoolExecutor(max_workers=2) as executor:
        tokens = list(
            executor.map(
                lambda worker: postgres_ledger_set.runs.claim(run["id"], worker),
                ("history-worker-a", "history-worker-b"),
            )
        )

    assert sum(token is not None for token in tokens) == 1
    with psycopg.connect(database_url) as connection:
        states = [
            row[0]
            for row in connection.execute(
                "SELECT state FROM jobs WHERE run_id=%s AND node_id IS NULL ORDER BY id",
                (run["id"],),
            ).fetchall()
        ]
    assert states == ["succeeded", "claimed"]
