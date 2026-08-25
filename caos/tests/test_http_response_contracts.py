from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from caos.config import Settings
from caos.http import create_app
from caos.responses import (
    ArtifactResponse,
    AuditEventResponse,
    CaseResponse,
    IdentityResponse,
    MethodologyDraftResponse,
    ModelBuildResponse,
    ModelReadinessResponse,
    ReportResponse,
    RunResponse,
    SnapshotResponse,
    SourceResponse,
    SourceSetResponse,
)
from caos.store import MemoryStore


DEPLOY_V = Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v"

AUDIT_ACTION_DETAILS = {
    "case.member_added": {"case_id": "case", "member": "member", "role": "READER"},
    "source.withdrawn": {"case_id": "case", "source_id": "source"},
    "snapshot.visible_switched": {"case_id": "case", "snapshot_id": "snapshot"},
    "model.retried": {"case_id": "case", "build_id": "model"},
    "model.calculate.succeeded": {"case_id": "case", "build_id": "model"},
    "model.export.succeeded": {"case_id": "case", "build_id": "model"},
    "model.export.queued": {"case_id": "case", "build_id": "model"},
    "model.export.failed": {"case_id": "case", "build_id": "model", "code": "MODEL_EXPORT_FAILED"},
    "model.export.downloaded": {"case_id": "case", "build_id": "model"},
    "report.approved": {"case_id": "case", "report_id": "report"},
    "research.plan_approved": {"case_id": "case", "run_id": "run", "plan_hash": "a" * 64},
    "note.created": {"case_id": "case", "note_id": "note"},
    "note.promoted": {"case_id": "case", "note_id": "note", "source_id": "source"},
    "assumption.created": {"case_id": "case", "assumption_id": "assumption"},
    "rv.universe_versioned": {"case_id": "case", "version": 1},
}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        storage_dir=tmp_path / "vault",
        deploy_v_root=DEPLOY_V,
    )
    with TestClient(create_app(settings, MemoryStore())) as test_client:
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
    artifact = next(
        item
        for item in client.app.state.store.artifacts.values()
        if item["run_id"] == run["id"]
    )
    artifact = client.get(f"/api/cases/{case_id}/artifacts/{artifact['id']}").json()
    snapshot = client.post(f"/api/runs/{run['id']}/accept").json()
    store = client.app.state.store
    build, _ = store.queue_model_build(
        {
            "id": store._id("model"),
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
    failed_build, _ = store.queue_model_build(
        {
            **build,
            "id": store._id("model"),
            "input_fingerprint": "1" * 64,
        },
        "local-analyst",
    )
    failed_token = store.claim_model_job(failed_build["id"], "contract-test")
    assert failed_token is not None
    store.fail_model_job(
        failed_build["id"],
        failed_token,
        {"code": "MODEL_CALCULATION_FAILED", "detail": "Contract failure."},
        "contract-test",
    )
    failed_model_build = client.get(f"/api/cases/{case_id}/models/{failed_build['id']}").json()
    ready_build, _ = store.queue_model_build(
        {
            **build,
            "id": store._id("model"),
            "input_fingerprint": "2" * 64,
        },
        "local-analyst",
    )
    store.model_builds[ready_build["id"]].update(
        status="READY",
        completed_at="2026-08-25T00:00:00+00:00",
        error=None,
        payload_digest="a" * 64,
        qa={
            "status": "PASS",
            "semantic_checks": [],
            "semantic_check_count": 0,
            "formula_count": 0,
            "worksheet_cell_count": 0,
            "limitation_flags": [],
            "validation_warnings": [],
            "source_manifest": [],
        },
    )
    ready_model_build = client.get(f"/api/cases/{case_id}/models/{ready_build['id']}").json()
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
    validated_draft = client.post(f"/api/admin/drafts/{draft['id']}/validate", headers=admin_headers).json()
    confirmed_draft = client.post(
        f"/api/admin/drafts/{draft['id']}/confirm",
        headers=admin_headers,
        json={"confirmation": "CONFIRM_DRAFT"},
    ).json()
    source_detail = client.get(f"/api/cases/{case_id}/sources/{source['id']}").json()
    note = client.post(f"/api/cases/{case_id}/notes", json={"body": "Promoted note"}).json()
    promoted = client.post(f"/api/cases/{case_id}/notes/{note['id']}/promote").json()
    promoted_source_detail = client.get(
        f"/api/cases/{case_id}/sources/{promoted['promoted_source_id']}"
    ).json()
    for action, details in AUDIT_ACTION_DETAILS.items():
        store.audit_event(action, "contract-test", **details)
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
        return {item_key: _normalize_volatile_values(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_volatile_values(item) for item in value]
    return value


@pytest.mark.parametrize("family", KEY_SETS)
def test_representative_response_payloads_preserve_exact_key_sets(
    response_payloads: dict[str, dict[str, Any]], family: str
) -> None:
    payload = response_payloads[family]
    _assert_key_sets(_normalize_volatile_values(payload), KEY_SETS[family])
    assert RESPONSE_MODELS[family].model_validate(payload).model_dump(mode="json") == payload


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
    payload = {**response_payloads["model_readiness"], "build": response_payloads["model_build"]}
    assert ModelReadinessResponse.model_validate(payload).model_dump(mode="json") == payload


def test_audit_event_model_validates_every_captured_event(
    response_payloads: dict[str, Any],
) -> None:
    for payload in response_payloads["audit_events"]:
        assert AuditEventResponse.model_validate(payload).model_dump(mode="json") == payload


def test_model_build_response_validates_each_lifecycle_shape(
    response_payloads: dict[str, Any],
) -> None:
    for name in ("model_build", "failed_model_build", "ready_model_build"):
        payload = response_payloads[name]
        assert ModelBuildResponse.model_validate(payload).model_dump(mode="json") == payload


def test_methodology_draft_response_validates_each_lifecycle_shape(
    response_payloads: dict[str, Any],
) -> None:
    for name in (
        "methodology_draft",
        "validated_methodology_draft",
        "confirmed_methodology_draft",
    ):
        payload = response_payloads[name]
        assert MethodologyDraftResponse.model_validate(payload).model_dump(mode="json") == payload


def test_source_response_validates_upload_and_stored_source_shapes(
    response_payloads: dict[str, Any],
) -> None:
    for name in ("source", "source_detail", "promoted_source_detail"):
        payload = response_payloads[name]
        assert SourceResponse.model_validate(payload).model_dump(mode="json") == payload
