from __future__ import annotations

import copy
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from caos import ledgers
from caos.contracts import clean_json, digest
from caos.memory_ledgers import MemoryLedgerSet
from caos.store import JobFencedError


ACTOR = "analyst"
LEASE_SECONDS = 0.2


class CopyFailure(RuntimeError):
    pass


class _Uncopyable:
    def __deepcopy__(self, memo: dict[int, Any]) -> Any:
        raise CopyFailure("copy failed")


@pytest.fixture(params=[MemoryLedgerSet], ids=["memory"])
def ledger_set(request: pytest.FixtureRequest) -> Any:
    return request.param(lease_seconds=LEASE_SECONDS)


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


def test_pending_job_reads_are_authoritative(ledger_set: Any) -> None:
    _, run = _queued_run(ledger_set)
    build = _accepted_model_input(ledger_set)
    queued, _ = ledger_set.models.queue_build(build, ACTOR)

    assert ledger_set.runs.pending_runs() == [(run["id"], ACTOR)]
    assert ledger_set.models.pending_jobs() == [(queued["id"], ACTOR, "calculate")]
