from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError

import caos.http as http_module
from caos.config import Settings
from caos.contracts import digest
from caos.http import create_app
from caos.memory_ledgers import MemoryLedgerSet
from caos.responses import (
    ArtifactResponse,
    AuditEventResponse,
    CanonicalRunResponse,
    CaseResponse,
    IdentityResponse,
    LoanUniverseResponse,
    MethodologyDraftResponse,
    ModelBuildResponse,
    ModelReadinessResponse,
    ReportResponse,
    ResearchRunResponse,
    RunResponse,
    SnapshotDiffResponse,
    SnapshotResponse,
    SourceResponse,
    SourceSetResponse,
)


DEPLOY_V = (
    Path(__file__).parents[1]
    / "server"
    / "caos"
    / "methodology"
    / "vendor"
    / "deploy_v"
)

AUDIT_ACTION_DETAILS = {
    "case.member_added": {"case_id": "case", "member": "member", "role": "READER"},
    "source.withdrawn": {"case_id": "case", "source_id": "source"},
    "snapshot.visible_switched": {"case_id": "case", "snapshot_id": "snapshot"},
    "model.retried": {"case_id": "case", "build_id": "model"},
    "model.calculate.succeeded": {"case_id": "case", "build_id": "model"},
    "model.export.succeeded": {"case_id": "case", "build_id": "model"},
    "model.export.queued": {"case_id": "case", "build_id": "model"},
    "model.export.failed": {
        "case_id": "case",
        "build_id": "model",
        "code": "MODEL_EXPORT_FAILED",
    },
    "model.export.downloaded": {"case_id": "case", "build_id": "model"},
    "report.approved": {"case_id": "case", "report_id": "report"},
    "research.plan_approved": {
        "case_id": "case",
        "run_id": "run",
        "plan_hash": "a" * 64,
    },
    "note.created": {"case_id": "case", "note_id": "note"},
    "note.promoted": {"case_id": "case", "note_id": "note", "source_id": "source"},
    "assumption.created": {"case_id": "case", "assumption_id": "assumption"},
    "rv.universe_versioned": {"case_id": "case", "version": 1},
}


class _PublicationLedgerDouble:
    def __init__(self, ledger: object) -> None:
        self.ledger = ledger
        self.extra_audit: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.ledger, name)

    def append_test_audit(self, action: str, actor: str, **details: Any) -> None:
        self.extra_audit.append(
            {
                "id": f"aud-contract-{len(self.extra_audit) + 1}",
                "action": action,
                "actor": actor,
                "at": "2026-08-25T00:00:00+00:00",
                **details,
            }
        )

    def list_audit(self) -> list[dict[str, Any]]:
        return [*self.ledger.list_audit(), *self.extra_audit]


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


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        storage_dir=tmp_path / "vault",
        deploy_v_root=DEPLOY_V,
    )
    ledgers = MemoryLedgerSet()
    ledgers.publications = _PublicationLedgerDouble(ledgers.publications)  # type: ignore[assignment]
    with TestClient(create_app(settings, ledgers)) as test_client:
        yield test_client


def _succeeded_run(client: TestClient, run_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] == "succeeded":
            return run
        time.sleep(0.05)
    pytest.fail("run did not finish within five seconds")


@pytest.fixture
def response_payloads(client: TestClient) -> dict[str, Any]:
    identity = client.get("/api/me").json()
    case = client.post(
        "/api/cases",
        json={"name": "Contract case", "issuer": "Issuer", "sector": "Services"},
    ).json()
    case_id = case["id"]
    source = client.post(
        f"/api/cases/{case_id}/sources",
        files={"file": ("evidence.txt", b"Revenue 1,160\nEBITDA 222", "text/plain")},
    ).json()
    run = client.post(
        f"/api/cases/{case_id}/runs",
        json={"pathway": "EARNINGS_UPDATE", "depth": "screen"},
    ).json()
    run = _succeeded_run(client, run["id"])
    artifact_id = next(
        node["artifact_id"] for node in run["nodes"] if node["artifact_id"]
    )
    artifact = client.get(f"/api/cases/{case_id}/artifacts/{artifact_id}").json()
    snapshot = client.post(f"/api/runs/{run['id']}/accept").json()
    ledgers = client.app.state.ledgers
    build, _ = ledgers.models.queue_build(
        {
            "case_id": case_id,
            "accepted_run_id": run["id"],
            "accepted_snapshot_id": snapshot["id"],
            "source_set_id": snapshot["source_set_id"],
            "input_fingerprint": "0" * 64,
            "worksheet_schema_version": "caos.model.worksheet.v1",
            "calculation_runtime": client.app.state.model_readiness.model.calculation_runtime,
        },
        "local-analyst",
    )
    model_build = client.get(f"/api/cases/{case_id}/models/{build['id']}").json()
    failed_build, _ = ledgers.models.queue_build(
        {
            **build,
            "input_fingerprint": "1" * 64,
        },
        "local-analyst",
    )
    failed_token = ledgers.models.claim(failed_build["id"], "contract-test")
    assert failed_token is not None
    ledgers.models.fail(
        failed_build["id"],
        failed_token,
        {"code": "MODEL_CALCULATION_FAILED", "detail": "Contract failure."},
        "contract-test",
    )
    failed_model_build = client.get(
        f"/api/cases/{case_id}/models/{failed_build['id']}"
    ).json()
    ready_build, _ = ledgers.models.queue_build(
        {
            **build,
            "input_fingerprint": "2" * 64,
        },
        "local-analyst",
    )
    ready_token = ledgers.models.claim(ready_build["id"], "contract-test")
    assert ready_token is not None
    ledgers.models.complete(
        ready_build["id"], ready_token, _model_result(), "contract-test"
    )
    ready_model_build = client.get(
        f"/api/cases/{case_id}/models/{ready_build['id']}"
    ).json()
    readiness = client.get(f"/api/cases/{case_id}/model").json()
    thesis = client.post(
        f"/api/cases/{case_id}/thesis",
        json={
            "expected_version": 0,
            "core_thesis": "Defensible",
            "drivers": [],
            "risks": [],
            "catalysts": [],
            "unresolved_questions": [],
            "evidence_ids": [],
        },
    ).json()
    recommendations = client.post(
        f"/api/cases/{case_id}/recommendations",
        json={
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
    ).json()
    report = client.post(
        f"/api/cases/{case_id}/reports/freeze",
        json={
            "thesis_version": thesis["version"],
            "recommendation_version": recommendations["version"],
            "include_model": False,
        },
    ).json()
    admin_headers = {
        "x-forwarded-user": "admin",
        "x-caos-role": "ADMIN",
        "x-oidc-step-up": client.app.state.settings.session_secret,
    }
    audit = client.get("/api/admin/audit", headers=admin_headers).json()[-1]
    draft = client.post(
        "/api/admin/drafts",
        headers=admin_headers,
        json={
            "expected_build_id": client.app.state.bundle.build_id,
            "module_id": "CP-0",
            "field": "reader_question",
            "before": "Old question",
            "after": "New question",
            "rationale": "Contract coverage",
        },
    ).json()
    validated_draft = client.post(
        f"/api/admin/drafts/{draft['id']}/validate", headers=admin_headers
    ).json()
    confirmed_draft = client.post(
        f"/api/admin/drafts/{draft['id']}/confirm",
        headers=admin_headers,
        json={"confirmation": "CONFIRM_DRAFT"},
    ).json()
    source_detail = client.get(f"/api/cases/{case_id}/sources/{source['id']}").json()
    note = client.post(
        f"/api/cases/{case_id}/notes", json={"body": "Promoted note"}
    ).json()
    promoted = client.post(f"/api/cases/{case_id}/notes/{note['id']}/promote").json()
    promoted_source_detail = client.get(
        f"/api/cases/{case_id}/sources/{promoted['promoted_source_id']}"
    ).json()
    for action, details in AUDIT_ACTION_DETAILS.items():
        ledgers.publications.append_test_audit(  # type: ignore[attr-defined]
            action, "contract-test", **details
        )
    audit_events = client.get("/api/admin/audit", headers=admin_headers).json()
    return {
        "identity": identity,
        "case": case,
        "source": source,
        "source_detail": source_detail,
        "promoted_source_detail": promoted_source_detail,
        "source_set": source["source_set"],
        "run": run,
        "snapshot": snapshot,
        "artifact": artifact,
        "model_readiness": readiness,
        "model_build": model_build,
        "failed_model_build": failed_model_build,
        "ready_model_build": ready_model_build,
        "report": report,
        "audit": audit,
        "audit_events": audit_events,
        "methodology_draft": draft,
        "validated_methodology_draft": validated_draft,
        "confirmed_methodology_draft": confirmed_draft,
    }


def _assert_key_sets(payload: dict[str, Any], expected: dict[str, Any]) -> None:
    assert set(payload) == set(expected)
    for key, child in expected.items():
        if child is None:
            continue
        value = payload[key]
        if isinstance(child, list):
            assert isinstance(value, list)
            assert value
            for item in value:
                _assert_key_sets(item, child[0])
        else:
            _assert_key_sets(value, child)


KEY_SETS = {
    "identity": {"subject": None, "email": None, "role": None, "destinations": None},
    "case": {
        "id": None,
        "name": None,
        "issuer": None,
        "sector": None,
        "created_by": None,
        "created_at": None,
        "members": None,
        "accepted_snapshot_id": None,
        "visible_snapshot_id": None,
        "current_execution_id": None,
    },
    "source": {
        "id": None,
        "case_id": None,
        "filename": None,
        "media_type": None,
        "bytes": None,
        "sha256": None,
        "created_by": None,
        "created_at": None,
        "blocks": [
            {
                "block_id": None,
                "text": None,
                "locator": {"line": None},
                "confidence": None,
                "untrusted_data": None,
                "extractor_version": None,
            }
        ],
        "withdrawn": None,
        "source_set": {
            "id": None,
            "case_id": None,
            "version": None,
            "source_ids": None,
            "created_by": None,
            "created_at": None,
        },
    },
    "source_set": {
        "id": None,
        "case_id": None,
        "version": None,
        "source_ids": None,
        "created_by": None,
        "created_at": None,
    },
    "run": {
        "id": None,
        "case_id": None,
        "status": None,
        "plan": None,
        "node_ids": None,
        "nodes": [
            {
                "id": None,
                "run_id": None,
                "case_id": None,
                "module_id": None,
                "stage": None,
                "dependencies": None,
                "status": None,
                "attempt": None,
                "artifact_id": None,
                "error": None,
            }
        ],
        "events": [{"id": None, "event": None, "at": None, "data": None}],
        "current_node_id": None,
        "accepted_snapshot_id": None,
        "upgraded_from_run_id": None,
        "created_by": None,
        "created_at": None,
        "error": None,
    },
    "snapshot": {
        "id": None,
        "case_id": None,
        "run_id": None,
        "source_set_id": None,
        "source_set_version": None,
        "artifacts": [{"id": None, "module_id": None, "digest": None}],
        "digest": None,
        "previous_snapshot_id": None,
        "accepted_at": None,
    },
    "artifact": {
        "id": None,
        "case_id": None,
        "run_id": None,
        "module_id": None,
        "payload": None,
        "markdown": None,
        "digest": None,
        "input_fingerprint": None,
        "created_by": None,
        "created_at": None,
    },
    "model_readiness": {
        "status": None,
        "module_id": None,
        "accepted_snapshot": None,
        "source_set": None,
        "requirements": [{"module_id": None, "status": None}],
        "calculation_runtime": None,
        "worksheet_schema_version": None,
        "blockers": [{"code": None, "detail": None}],
        "build": None,
    },
    "model_build": {
        "id": None,
        "case_id": None,
        "accepted_run_id": None,
        "accepted_snapshot_id": None,
        "source_set_id": None,
        "input_fingerprint": None,
        "status": None,
        "queued_at": None,
        "started_at": None,
        "completed_at": None,
        "error": None,
        "export": {"status": None, "error": None},
        "worksheet_schema_version": None,
        "calculation_runtime": {"name": None, "version": None, "sha256": None},
    },
    "report": {
        "id": None,
        "case_id": None,
        "status": None,
        "created_by": None,
        "created_at": None,
        "content": {
            "case_id": None,
            "snapshot_id": None,
            "snapshot_digest": None,
            "thesis_version": None,
            "recommendation_version": None,
            "include_model": None,
            "model": None,
            "input_fingerprint": None,
        },
        "snapshot_digest": None,
        "input_fingerprint": None,
        "preview_digest": None,
        "digest": None,
        "markdown": None,
    },
    "audit": {
        "id": None,
        "action": None,
        "actor": None,
        "at": None,
        "case_id": None,
        "report_id": None,
    },
    "methodology_draft": {
        "id": None,
        "status": None,
        "expected_build_id": None,
        "module_id": None,
        "field": None,
        "before": None,
        "after": None,
        "rationale": None,
        "created_by": None,
        "created_at": None,
        "semantic_diff": {"before": None, "after": None},
        "digest": None,
    },
}


RESPONSE_MODELS = {
    "identity": IdentityResponse,
    "case": CaseResponse,
    "source": SourceResponse,
    "source_set": SourceSetResponse,
    "run": RunResponse,
    "snapshot": SnapshotResponse,
    "artifact": ArtifactResponse,
    "model_readiness": ModelReadinessResponse,
    "model_build": ModelBuildResponse,
    "report": ReportResponse,
    "audit": AuditEventResponse,
    "methodology_draft": MethodologyDraftResponse,
}


VOLATILE_KEYS = {
    "id",
    "case_id",
    "run_id",
    "source_id",
    "source_set_id",
    "accepted_snapshot_id",
    "previous_snapshot_id",
    "visible_snapshot_id",
    "current_execution_id",
    "artifact_id",
    "report_id",
    "draft_id",
    "build_id",
}


def _normalize_volatile_values(value: Any, key: str | None = None) -> Any:
    if key in VOLATILE_KEYS or key in {"at", "accepted_at", "created_at", "queued_at"}:
        return "<volatile>"
    if isinstance(value, dict):
        return {
            item_key: _normalize_volatile_values(item, item_key)
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_volatile_values(item) for item in value]
    return value


@pytest.mark.parametrize("family", KEY_SETS)
def test_representative_response_payloads_preserve_exact_key_sets(
    response_payloads: dict[str, dict[str, Any]], family: str
) -> None:
    payload = response_payloads[family]
    _assert_key_sets(_normalize_volatile_values(payload), KEY_SETS[family])
    assert (
        RESPONSE_MODELS[family].model_validate(payload).model_dump(mode="json")
        == payload
    )


def test_model_build_rejects_unknown_calculation_runtime_fields(
    response_payloads: dict[str, Any],
) -> None:
    payload = {
        **response_payloads["model_build"],
        "calculation_runtime": {"engine": "not-a-runtime-contract"},
    }
    with pytest.raises(ValidationError):
        ModelBuildResponse.model_validate(payload)


def test_model_readiness_uses_the_shared_model_build_shape(
    response_payloads: dict[str, Any],
) -> None:
    payload = {
        **response_payloads["model_readiness"],
        "build": response_payloads["model_build"],
    }
    assert (
        ModelReadinessResponse.model_validate(payload).model_dump(mode="json")
        == payload
    )


def test_audit_event_model_validates_every_captured_event(
    response_payloads: dict[str, Any],
) -> None:
    for payload in response_payloads["audit_events"]:
        assert (
            AuditEventResponse.model_validate(payload).model_dump(mode="json")
            == payload
        )


def test_model_build_response_validates_each_lifecycle_shape(
    response_payloads: dict[str, Any],
) -> None:
    for name in ("model_build", "failed_model_build", "ready_model_build"):
        payload = response_payloads[name]
        assert (
            ModelBuildResponse.model_validate(payload).model_dump(mode="json")
            == payload
        )


def test_methodology_draft_response_validates_each_lifecycle_shape(
    response_payloads: dict[str, Any],
) -> None:
    for name in (
        "methodology_draft",
        "validated_methodology_draft",
        "confirmed_methodology_draft",
    ):
        payload = response_payloads[name]
        assert (
            MethodologyDraftResponse.model_validate(payload).model_dump(mode="json")
            == payload
        )


def test_source_response_validates_upload_and_stored_source_shapes(
    response_payloads: dict[str, Any],
) -> None:
    for name in ("source", "source_detail", "promoted_source_detail"):
        payload = response_payloads[name]
        assert SourceResponse.model_validate(payload).model_dump(mode="json") == payload


def test_withdrawn_source_detail_remains_retrievable_with_strict_public_shape(
    client: TestClient,
) -> None:
    case = client.post(
        "/api/cases",
        json={"name": "Withdrawn detail", "issuer": "Issuer", "sector": "Services"},
    ).json()
    source = client.post(
        f"/api/cases/{case['id']}/sources",
        files={"file": ("evidence.txt", b"Debt 100", "text/plain")},
    ).json()
    withdrawn = client.post(f"/api/cases/{case['id']}/sources/{source['id']}/withdraw")
    detail = client.get(f"/api/cases/{case['id']}/sources/{source['id']}")

    assert withdrawn.status_code == 200
    assert detail.status_code == 200
    assert detail.json() == withdrawn.json()
    assert set(detail.json()) == {
        "id",
        "case_id",
        "filename",
        "media_type",
        "bytes",
        "sha256",
        "created_by",
        "created_at",
        "blocks",
        "withdrawn",
    }
    assert detail.json()["withdrawn"] is True
    assert (
        SourceResponse.model_validate(detail.json()).model_dump(mode="json")
        == detail.json()
    )


def test_distinct_duplicate_note_promotion_is_a_structured_source_conflict(
    client: TestClient,
) -> None:
    case = client.post(
        "/api/cases",
        json={"name": "Note conflict", "issuer": "Issuer", "sector": "Services"},
    ).json()
    first = client.post(
        f"/api/cases/{case['id']}/notes", json={"body": "Same analyst view"}
    ).json()
    second = client.post(
        f"/api/cases/{case['id']}/notes", json={"body": "Same analyst view"}
    ).json()

    promoted = client.post(f"/api/cases/{case['id']}/notes/{first['id']}/promote")
    replay = client.post(f"/api/cases/{case['id']}/notes/{first['id']}/promote")
    conflict = client.post(f"/api/cases/{case['id']}/notes/{second['id']}/promote")

    assert promoted.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["promoted_source_id"] == promoted.json()["promoted_source_id"]
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "source content already active"}
    notes = {
        note["id"]: note for note in client.get(f"/api/cases/{case['id']}/notes").json()
    }
    assert notes[first["id"]]["promoted"] is True
    assert notes[second["id"]]["promoted"] is False


def test_snapshot_diff_accepts_added_artifacts_without_snapshot_ids() -> None:
    payload = {
        "changed": True,
        "added": [{"module_id": "CP-1", "digest": "added"}],
        "removed": [{"module_id": "CP-0", "digest": "removed"}],
        "modified": [],
        "source_set_changed": False,
    }

    assert (
        SnapshotDiffResponse.model_validate(payload).model_dump(mode="json") == payload
    )


def test_openapi_declares_strict_models_for_every_json_success_response(
    client: TestClient,
) -> None:
    exempt = {
        ("get", "/api/runs/{run_id}/events"),
        ("get", "/api/cases/{case_id}/models/{build_id}/download"),
        ("get", "/api/cases/{case_id}/reports/export/{format_name}"),
    }
    paths = client.app.openapi()["paths"]

    for path, operations in paths.items():
        if not path.startswith("/api/"):
            continue
        for method, operation in operations.items():
            if (method, path) in exempt or method == "parameters":
                continue
            for status, response in operation["responses"].items():
                if not status.startswith("2"):
                    continue
                schema = response["content"]["application/json"]["schema"]
                assert "#/components/schemas/" in json.dumps(schema), (
                    method,
                    path,
                    status,
                    schema,
                )

    assert paths["/api/me"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/IdentityResponse"}
    assert paths["/api/cases"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["items"] == {"$ref": "#/components/schemas/CaseResponse"}
    assert "#/components/schemas/ReportResponse" in json.dumps(
        paths["/api/cases/{case_id}/reports"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
    )
    schemas = client.app.openapi()["components"]["schemas"]
    for name in (
        "HealthResponse",
        "CaseDetailResponse",
        "CanonicalGenerationResponse",
        "CanonicalGenerationProgressResponse",
        "ResearchStateResponse",
        "ResearchPlanResponse",
        "ThesisResponse",
        "LoanUniverseResponse",
        "LoanUniverseFindingResponse",
        "ModelListResponse",
        "VisualRecipeValidationResponse",
    ):
        assert schemas[name]["additionalProperties"] is False
    loan_import_responses = paths["/api/cases/{case_id}/rv/loan-universes"]["post"][
        "responses"
    ]
    assert loan_import_responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoanUniverseResponse"
    }
    assert loan_import_responses["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoanUniverseResponse"
    }


def _run_payload(extension: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "run",
        "case_id": "case",
        "status": "queued",
        "plan": {},
        "node_ids": [],
        "nodes": [],
        "events": [],
        "current_node_id": None,
        "accepted_snapshot_id": None,
        "upgraded_from_run_id": None,
        "created_by": "analyst",
        "created_at": "2026-08-25T00:00:00+00:00",
        "error": None,
        **extension,
    }


def _budgets(active_minutes: float | int = 0) -> dict[str, float | int]:
    return {
        "turns": 0,
        "evidence_reads": 0,
        "evidence_bytes": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "active_minutes": active_minutes,
        "provider_retries": 0,
        "repairs": 0,
    }


def test_canonical_generation_is_strict_and_preserves_completed_module_omission() -> (
    None
):
    generation = {
        "phase": "generating",
        "model": "model",
        "reporting_period": "2026-08-25",
        "module_output_tokens": {
            "CP-1": 32_000,
            "CP-1A": 12_000,
            "CP-1B": 12_000,
            "CP-2": 16_000,
            "CP-2A": 16_000,
        },
        "budget_limits": {**_budgets(), "turns": 66, "evidence_reads": 60},
        "budget_used": _budgets(),
        "inflight_request_digest": None,
        "attempts": [],
    }
    payload = _run_payload({"canonical_generation": generation})

    assert (
        CanonicalRunResponse.model_validate(payload).model_dump(mode="json") == payload
    )
    progressed = _run_payload(
        {"canonical_generation": {**generation, "completed_modules": ["CP-1"]}}
    )
    assert (
        CanonicalRunResponse.model_validate(progressed).model_dump(mode="json")
        == progressed
    )
    with pytest.raises(ValidationError):
        CanonicalRunResponse.model_validate(
            _run_payload({"canonical_generation": {**generation, "unexpected": True}})
        )


def test_research_state_is_strict_and_preserves_plan_variant_omissions() -> None:
    brief = {
        "research_question": "Can the issuer refinance?",
        "decision_context": "Underwrite first lien.",
        "as_of_date": "2026-08-25",
        "time_horizon": "Through 2029",
        "must_answer": ["What is liquidity?"],
        "exclusions": [],
        "scope_type": "issuer",
        "scope_key": "case",
        "subject_name": "Issuer",
        "source_mode": "supplied_only",
        "research_budget": "standard",
        "plan_approval": "required",
    }
    workstream = {
        "id": "WS-1",
        "kind": "synthesis",
        "question": "What follows?",
        "perspective": "Cross-workstream synthesis",
        "hypothesis": "Evidence supports a conclusion.",
        "evidence_needs": ["Completed workstreams."],
        "source_classes": ["supplied_case_sources"],
        "disconfirming_test": "Reconcile contradictions.",
        "completion_test": "State the answer and gaps.",
        "effort_cap": "One pass.",
    }
    plan = {
        "methodology_build_id": "build",
        "brief_digest": "digest",
        "source_set": {"id": "set", "version": 1},
        "upstream_artifacts": [
            {"module_id": "CP-0", "artifact_id": "artifact", "digest": "digest"}
        ],
        "scope": {"type": "issuer", "key": "case", "source_mode": "supplied_only"},
        "workstreams": [workstream],
    }
    research = {
        "brief": brief,
        "phase": "awaiting_approval",
        "proposed_plan": plan,
        "proposed_plan_hash": "sha256:digest",
        "approved_plan_hash": None,
        "approved_by": None,
        "approved_at": None,
        "model": "model",
        "budget_limits": {**_budgets(), "turns": 8, "evidence_reads": 12},
        "budget_used": _budgets(),
        "inflight_request_digest": None,
        "attempts": [],
    }
    payload = _run_payload({"research": research})

    assert (
        ResearchRunResponse.model_validate(payload).model_dump(mode="json") == payload
    )
    assert (
        "assigned_questions"
        not in payload["research"]["proposed_plan"]["workstreams"][0]
    )
    topical = {
        **workstream,
        "kind": "topical",
        "assigned_questions": ["What is liquidity?"],
    }
    retry_terminal = {
        "run_id": "run",
        "node_id": "node",
        "attempt": 1,
        "model": "model",
        "approved_plan_hash": "sha256:digest",
        "authority_digest": "digest",
        "prompt_digest": "digest",
        "source_set_digest": "digest",
        "upstream_digest": "digest",
        "kind": "provider_retry",
        "operation": "create",
        "terminal_code": "AGENT_BUDGET_EXCEEDED",
    }
    handoff_terminal = {
        **{
            key: value
            for key, value in retry_terminal.items()
            if key not in {"kind", "operation"}
        },
        "kind": "handoff",
        "output_digest": "digest",
        "filename": "CP-DR.md",
        "confidence_score": 0.75,
    }
    variant = _run_payload(
        {
            "research": {
                **research,
                "proposed_plan": {**plan, "workstreams": [topical]},
                "attempts": [retry_terminal, handoff_terminal],
            }
        }
    )
    assert (
        ResearchRunResponse.model_validate(variant).model_dump(mode="json") == variant
    )
    with pytest.raises(ValidationError):
        ResearchRunResponse.model_validate(
            _run_payload({"research": {**research, "unexpected": True}})
        )


def _loan_universe_payload() -> dict[str, Any]:
    return {
        "id": "rvloan",
        "case_id": "case",
        "source_id": "source",
        "source_filename": "loans.xlsx",
        "source_sha256": "a" * 64,
        "workbook_date": None,
        "template_version": "cp3-sector-rv-v1",
        "importer_version": "loan-rv-importer-v1",
        "universe_digest": None,
        "row_count": 0,
        "status": "REJECTED",
        "findings": [
            {
                "code": "RV_TEMPLATE_MISSING",
                "detail": "Missing template.",
                "sheet": None,
                "row": None,
                "column": None,
            }
        ],
        "created_at": "2026-08-25T00:00:00+00:00",
        "created_by": "analyst",
        "version": None,
        "activated_at": None,
        "superseded_at": None,
        "withdrawn_at": None,
    }


def test_loan_universe_findings_are_strict() -> None:
    payload = _loan_universe_payload()
    assert (
        LoanUniverseResponse.model_validate(payload).model_dump(mode="json") == payload
    )
    payload["findings"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        LoanUniverseResponse.model_validate(payload)


def test_idempotent_loan_import_uses_fastapi_response_validation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_id = client.post(
        "/api/cases", json={"name": "Loans", "issuer": "Issuer", "sector": "Services"}
    ).json()["id"]
    invalid = {**_loan_universe_payload(), "case_id": case_id, "unexpected": True}
    monkeypatch.setattr(
        http_module, "import_loan_source", lambda *_args: (invalid, False)
    )

    with pytest.raises(ResponseValidationError):
        client.post(
            f"/api/cases/{case_id}/rv/loan-universes", json={"source_id": "source"}
        )
