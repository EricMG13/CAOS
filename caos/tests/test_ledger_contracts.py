from __future__ import annotations

import copy
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Protocol, cast

import pytest

from caos.contracts import clean_json, digest
from caos.ledgers import ModelLedger, PublicationLedger, RunLedger, SourceCatalog
from caos.memory_ledgers import MemoryLedgerSet
from caos.store import JobFencedError


ACTOR = "analyst"
LEASE_SECONDS = 0.2


class LedgerSet(Protocol):
    sources: SourceCatalog
    runs: RunLedger
    publications: PublicationLedger
    models: ModelLedger


@pytest.fixture(params=[MemoryLedgerSet], ids=["memory"])
def ledger_set(request: pytest.FixtureRequest) -> LedgerSet:
    return cast(LedgerSet, request.param(lease_seconds=LEASE_SECONDS))


def _case(ledger_set: LedgerSet) -> dict[str, Any]:
    return ledger_set.runs.create_case("Contract case", "Issuer", "Testing", ACTOR)


def _source(case_id: str, source_id: str = "src_contract") -> dict[str, Any]:
    return {
        "id": source_id,
        "case_id": case_id,
        "filename": "evidence.txt",
        "media_type": "text/plain",
        "bytes": 8,
        "sha256": "a" * 64,
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


def _queued_run(ledger_set: LedgerSet) -> tuple[dict[str, Any], dict[str, Any]]:
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


def _accepted_model_input(ledger_set: LedgerSet) -> dict[str, Any]:
    case = _case(ledger_set)
    ingested = ledger_set.sources.ingest(_source(case["id"]), ACTOR)
    source_set = ingested["source_set"]
    run = ledger_set.runs.create_run_with_nodes(
        case["id"],
        ACTOR,
        {"pathway": "EARNINGS_UPDATE", "source_set_id": source_set["id"]},
        [],
    )
    token = ledger_set.runs.claim(run["id"], "workflow-worker")
    assert token is not None
    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})
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
        {
            "id": f"snap_{run['id']}",
            **snapshot_payload,
            "digest": digest(snapshot_payload),
        },
    )
    return {
        "id": f"model_{run['id']}",
        "case_id": case["id"],
        "accepted_run_id": run["id"],
        "accepted_snapshot_id": snapshot["id"],
        "source_set_id": source_set["id"],
        "input_fingerprint": "c" * 64,
        "worksheet_schema_version": "caos.model.worksheet.v1",
    }


def test_source_duplicate_and_withdrawal_are_atomic(ledger_set: LedgerSet) -> None:
    case = _case(ledger_set)
    source = _source(case["id"])
    first = ledger_set.sources.ingest(source, ACTOR)
    assumption = ledger_set.publications.create_assumption(
        case["id"], ACTOR, "Debt is 100", [source["id"]], ["CP-1"]
    )
    before_sources = ledger_set.sources.list_sources(case["id"])
    before_set = ledger_set.sources.current_source_set(case["id"])

    with pytest.raises(ValueError, match="source content already active"):
        ledger_set.sources.ingest({**source, "id": "src_duplicate"}, ACTOR)

    assert ledger_set.sources.list_sources(case["id"]) == before_sources
    assert ledger_set.sources.current_source_set(case["id"]) == before_set
    assert ledger_set.sources.withdraw("case_missing", source["id"], ACTOR) is None
    assert ledger_set.sources.current_source_set(case["id"]) == before_set
    assert ledger_set.publications.list_assumptions(case["id"]) == [assumption]

    withdrawn = ledger_set.sources.withdraw(case["id"], source["id"], ACTOR)

    assert withdrawn is not None and withdrawn["withdrawn"] is True
    assert ledger_set.sources.list_sources(case["id"]) == []
    withdrawn_set = ledger_set.sources.current_source_set(case["id"])
    assert withdrawn_set is not None
    assert withdrawn_set["version"] == first["source_set"]["version"] + 1
    assert withdrawn_set["source_ids"] == []
    assert ledger_set.publications.list_assumptions(case["id"])[0]["status"] == "STALE"
    replacement = ledger_set.sources.ingest({**source, "id": "src_replacement"}, ACTOR)
    assert replacement["source_set"]["version"] == withdrawn_set["version"] + 1


def test_run_and_nodes_are_created_as_one_pending_transition(
    ledger_set: LedgerSet,
) -> None:
    case, run = _queued_run(ledger_set)

    assert run["case_id"] == case["id"]
    assert run["status"] == "queued"
    assert [node["module_id"] for node in run["nodes"]] == ["CP-1"]
    assert run["node_ids"] == [run["nodes"][0]["id"]]
    assert ledger_set.runs.get_case(case["id"])["current_execution_id"] == run["id"]
    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]


def test_run_claim_has_one_winner(ledger_set: LedgerSet) -> None:
    _, run = _queued_run(ledger_set)

    with ThreadPoolExecutor(max_workers=2) as executor:
        tokens = list(
            executor.map(
                lambda worker: ledger_set.runs.claim(run["id"], worker),
                ("worker-a", "worker-b"),
            )
        )

    assert sum(token is not None for token in tokens) == 1


def test_expired_run_claim_recovers_running_nodes_and_fences_old_worker(
    ledger_set: LedgerSet,
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

    artifact = {
        "id": "art_contract",
        "case_id": run["case_id"],
        "run_id": run["id"],
        "module_id": node["module_id"],
        "input_fingerprint": "fingerprint",
    }
    with pytest.raises(JobFencedError, match="stale workflow attempt"):
        ledger_set.runs.complete_node(
            run["id"], stale, node["id"], artifact, research=None
        )

    ledger_set.runs.update_node_fenced(
        run["id"], replacement, node["id"], status="running"
    )
    completed = ledger_set.runs.complete_node(
        run["id"], replacement, node["id"], artifact, research=None
    )
    assert completed["id"] == artifact["id"]
    assert ledger_set.runs.get_run(run["id"])["nodes"][0]["status"] == "succeeded"


def test_snapshot_acceptance_updates_case_and_run_together(
    ledger_set: LedgerSet,
) -> None:
    case, run = _queued_run(ledger_set)
    node = run["nodes"][0]
    token = ledger_set.runs.claim(run["id"], "worker")
    assert token is not None
    ledger_set.runs.update_node_fenced(run["id"], token, node["id"], status="running")
    artifact = ledger_set.runs.complete_node(
        run["id"],
        token,
        node["id"],
        {
            "id": "art_snapshot",
            "case_id": case["id"],
            "run_id": run["id"],
            "module_id": node["module_id"],
            "input_fingerprint": "snapshot-fingerprint",
            "digest": "f" * 64,
        },
        research=None,
    )
    ledger_set.runs.finalize_success(run["id"], token, None, {"run_id": run["id"]})
    source_set = ledger_set.sources.source_set(run["plan"]["source_set_id"])
    assert source_set is not None
    snapshot_payload = {
        "case_id": case["id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"],
        "source_set_version": source_set["version"],
        "artifacts": [artifact],
        "accepted_at": "2026-08-24T00:00:00+00:00",
    }
    snapshot = {
        "id": "snap_contract",
        **snapshot_payload,
        "digest": digest(snapshot_payload),
    }

    accepted = ledger_set.runs.accept_snapshot(case["id"], run["id"], ACTOR, snapshot)

    assert accepted["previous_snapshot_id"] is None
    assert ledger_set.runs.get_snapshot(accepted["id"]) == accepted
    assert (
        ledger_set.runs.get_case(case["id"])["accepted_snapshot_id"] == accepted["id"]
    )
    assert ledger_set.runs.get_run(run["id"])["accepted_snapshot_id"] == accepted["id"]


def test_publication_versions_conflict_without_partial_append(
    ledger_set: LedgerSet,
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


def test_note_promotion_changes_source_authority_once(ledger_set: LedgerSet) -> None:
    case = _case(ledger_set)
    note = ledger_set.publications.create_note(case["id"], ACTOR, "Debt remains 100")

    promoted = ledger_set.publications.promote_note(case["id"], note["id"], ACTOR)
    repeated = ledger_set.publications.promote_note(case["id"], note["id"], ACTOR)

    source_id = promoted["promoted_source_id"]
    source = ledger_set.sources.get_source(source_id)
    source_set = ledger_set.sources.current_source_set(case["id"])
    assert promoted["promoted"] is True
    assert repeated["promoted_source_id"] == source_id
    assert source is not None and source["source_kind"] == "analyst_note"
    assert source_set is not None and source_set["source_ids"] == [source_id]


def test_report_freeze_and_approval_require_exact_preview(
    ledger_set: LedgerSet,
) -> None:
    build = _accepted_model_input(ledger_set)
    case_id = build["case_id"]
    snapshot = ledger_set.runs.get_snapshot(build["accepted_snapshot_id"])
    assert snapshot is not None
    inputs = ledger_set.publications.save_report_inputs(
        case_id,
        ACTOR,
        {
            "expected_version": 0,
            "core_thesis": "Defensible",
            "drivers": [],
            "risks": [],
            "catalysts": [],
            "unresolved_questions": [],
            "evidence_ids": [],
        },
        {
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
        },
        accepted_snapshot_id=snapshot["id"],
    )
    input_fingerprint = digest(
        clean_json(
            {
                "snapshot": snapshot,
                "thesis": inputs["thesis"],
                "recommendations": inputs["recommendations"],
                "model": None,
            }
        )
    )
    content = {
        "case_id": case_id,
        "snapshot_id": snapshot["id"],
        "snapshot_digest": digest(snapshot),
        "thesis_version": inputs["thesis"]["version"],
        "recommendation_version": inputs["recommendations"]["version"],
        "include_model": False,
        "model": None,
        "input_fingerprint": input_fingerprint,
    }
    preview_digest = digest(content)
    report = {
        "id": "report_contract",
        "case_id": case_id,
        "created_by": ACTOR,
        "created_at": "2026-08-24T00:00:00+00:00",
        "status": "PENDING_APPROVAL",
        "preview_digest": preview_digest,
        "digest": preview_digest,
        "input_fingerprint": input_fingerprint,
        "snapshot_digest": content["snapshot_digest"],
        "content": content,
        "markdown": "# Frozen report\n",
    }
    frozen = ledger_set.publications.freeze_report(case_id, ACTOR, report)

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
    approved = ledger_set.publications.approve_report(
        case_id,
        "approver",
        "PENDING_APPROVAL",
        frozen["preview_digest"],
        frozen["input_fingerprint"],
        "Reviewed",
    )
    assert approved["status"] == "APPROVED"
    assert approved["approved_by"] == "approver"
    assert approved["approval_comment"] == "Reviewed"


def test_model_jobs_claim_complete_and_fail(ledger_set: LedgerSet) -> None:
    build = _accepted_model_input(ledger_set)
    queued, created = ledger_set.models.queue_build(build, ACTOR)
    token = ledger_set.models.claim(build["id"], "model-worker")

    assert created is True
    assert queued["status"] == "QUEUED"
    assert token is not None
    assert ledger_set.models.claim(build["id"], "other-worker") is None
    ready = ledger_set.models.complete(
        build["id"], token, _model_result(), "model-worker"
    )
    assert ready["status"] == "READY"
    assert ledger_set.models.is_current(build["id"], token) is False

    failed_input = {
        **build,
        "id": f"{build['id']}_failed",
        "input_fingerprint": "e" * 64,
    }
    ledger_set.models.queue_build(failed_input, ACTOR)
    failed_token = ledger_set.models.claim(failed_input["id"], "model-worker")
    assert failed_token is not None
    failed = ledger_set.models.fail(
        failed_input["id"],
        failed_token,
        {"code": "MODEL_CALCULATION_FAILED", "detail": "bounded"},
        "model-worker",
    )
    assert failed["status"] == "FAILED"


def test_pending_job_reads_are_authoritative(ledger_set: LedgerSet) -> None:
    _, run = _queued_run(ledger_set)
    build = _accepted_model_input(ledger_set)
    ledger_set.models.queue_build(build, ACTOR)

    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]
    assert ledger_set.models.pending_jobs() == [(build["id"], ACTOR, "calculate")]
