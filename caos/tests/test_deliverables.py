from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from caos.config import Settings
from caos.contracts import DeliverableDraftRequest, digest
from caos.http import create_app
from caos.migrations import apply_migrations
from caos.memory_ledgers import MemoryLedgerSet
from caos.postgres_ledgers import PostgresLedgerSet
from caos.publishing.domain import DeliverableService
from caos.publishing.templates import DELIVERABLE_TEMPLATES


ACTOR = "analyst"


class _ModelAuthority:
    def __init__(self, case_id: str) -> None:
        self.build = {
            "id": "model_current",
            "case_id": case_id,
            "accepted_snapshot_id": "snapshot",
            "input_fingerprint": "a" * 64,
            "payload_digest": "b" * 64,
            "status": "READY",
            "payload": {"tabs": []},
            "calculation_runtime": {
                "assumption_registry_version": "registry-v1",
                "assumption_registry_digest": "c" * 64,
                "calculation_contract_version": "calculation-v1",
            },
        }
        self.revision: dict[str, Any] | None = {
            "id": "revision_current",
            "case_id": case_id,
            "build_id": self.build["id"],
            "accepted_snapshot_id": self.build["accepted_snapshot_id"],
            "build_input_fingerprint": self.build["input_fingerprint"],
            "build_payload_digest": self.build["payload_digest"],
            "registry_version": "registry-v1",
            "registry_digest": "c" * 64,
            "calculation_contract_version": "calculation-v1",
            "assumptions_digest": "d" * 64,
            "outputs_digest": "e" * 64,
            "revision_number": 1,
            "signed_by": ACTOR,
            "signed_at": "2026-08-26T00:00:00+00:00",
            "outputs": {"BASE": {"FY2027": {"total_leverage": "4.2"}}},
        }

    def list_builds(self, case_id: str) -> list[dict[str, Any]]:
        return [self.build] if case_id == self.build["case_id"] else []

    def get_build(self, build_id: str) -> dict[str, Any] | None:
        return self.build if build_id == self.build["id"] else None

    def get_revision_head(self, case_id: str) -> dict[str, Any] | None:
        return (
            self.revision
            if self.revision is not None and case_id == self.revision["case_id"]
            else None
        )

    def get_revision(self, revision_id: str) -> dict[str, Any] | None:
        return (
            self.revision
            if self.revision is not None and revision_id == self.revision["id"]
            else None
        )


class _ScenarioAuthority:
    def __init__(self, scenario: dict[str, Any]) -> None:
        self.scenario_value = scenario

    def scenario(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "draft_generation": kwargs["draft_generation"],
            "baseline": {},
            "scenario": self.scenario_value,
            "scenario_digest": digest(self.scenario_value),
        }


class _ScenarioMustNotRun:
    def scenario(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("scenario calculation must not run")


def _ledger_value(label: str) -> dict[str, Any]:
    return {
        "template_id": "caos.full-credit.v1",
        "template_version": "caos.deliverable-template.v1",
        "digest": label * 64,
    }


def _draft_payload(pathway: str = "RELATIVE_VALUE") -> dict[str, Any]:
    template = DELIVERABLE_TEMPLATES[pathway]
    return {
        "expected_version": 0,
        "template_id": template["template_id"],
        "template_version": template["template_version"],
        "model_selection": None,
        "blocks": [
            {
                "kind": "NARRATIVE",
                "block_id": block["block_id"],
                "slot_id": block["slot_id"],
                "text": f"{block['title']} analyst conclusion.",
                "content_mode": "ANALYST_JUDGMENT",
                "citations": [],
            }
            if block["kind"] == "NARRATIVE"
            else {
                "kind": "EVIDENCE_REGISTER",
                "block_id": block["block_id"],
                "slot_id": block["slot_id"],
                "citations": [],
            }
            for block in template["blocks"]
        ],
    }


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                storage_dir=tmp_path / "vault",
                deploy_v_root=Path(__file__).parents[1]
                / "server"
                / "caos"
                / "methodology"
                / "vendor"
                / "deploy_v",
            ),
            MemoryLedgerSet(),
        )
    )


@pytest.fixture(params=["memory", "postgres"])
def ledger_set(request: pytest.FixtureRequest) -> Any:
    if request.param == "memory":
        yield MemoryLedgerSet()
        return
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for PostgreSQL ledger proof")
    ledgers = PostgresLedgerSet(database_url)
    import psycopg

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE cases RESTART IDENTITY CASCADE")
    try:
        yield ledgers
    finally:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE cases RESTART IDENTITY CASCADE")


def test_six_pathway_templates_have_stable_identity_and_evidence_register() -> None:
    assert list(DELIVERABLE_TEMPLATES) == [
        "FULL_CREDIT",
        "EARNINGS_UPDATE",
        "COVENANT_REFINANCING",
        "RELATIVE_VALUE",
        "DISTRESSED_RESTRUCTURING",
        "DEEP_RESEARCH",
    ]
    assert {template["template_version"] for template in DELIVERABLE_TEMPLATES.values()} == {
        "caos.deliverable-template.v1"
    }
    for pathway, template in DELIVERABLE_TEMPLATES.items():
        assert template["pathway"] == pathway
        assert template["template_id"] == f"caos.{pathway.lower().replace('_', '-')}.v1"
        assert len({block["slot_id"] for block in template["blocks"]}) == len(
            template["blocks"]
        )
        assert any(block["kind"] == "EVIDENCE_REGISTER" for block in template["blocks"])


def test_deliverable_migration_is_forward_only_and_has_phase_six_placeholders() -> None:
    sql = (
        Path(__file__).parents[1]
        / "server"
        / "migrations"
        / "008_deliverables.sql"
    ).read_text(encoding="utf-8").lower()
    assert "drop table" not in sql
    assert "delete from" not in sql
    for authority in (
        "deliverable_draft_revisions",
        "unique (case_id, pathway, version)",
        "frozen_deliverables",
        "deliverable_exports",
        "renderer_identity",
    ):
        assert authority in sql


def test_deliverable_migration_applies_idempotently_on_postgres() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(database_url) as connection:
        apply_migrations(connection, root)
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version='008_deliverables'"
            )
        assert apply_migrations(connection, root) == ("008_deliverables",)
        assert apply_migrations(connection, root) == ()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=current_schema() AND table_name LIKE %s",
                ("%deliverable%",),
            )
            assert {row[0] for row in cursor.fetchall()} >= {
                "deliverable_draft_revisions",
                "frozen_deliverables",
                "deliverable_exports",
            }
        connection.rollback()


def test_deliverable_revisions_are_append_only_and_conflict_atomically(
    ledger_set: Any,
) -> None:
    case = ledger_set.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    first = ledger_set.publications.append_deliverable_revision(
        case["id"], "FULL_CREDIT", ACTOR, 0, _ledger_value("a")
    )
    assert first["version"] == 1
    assert ledger_set.publications.list_deliverable_revisions(
        case["id"], "FULL_CREDIT"
    ) == [first]

    def append(label: str) -> tuple[str, Any]:
        try:
            value = ledger_set.publications.append_deliverable_revision(
                case["id"],
                "FULL_CREDIT",
                f"{ACTOR}-{label}",
                1,
                _ledger_value(label),
            )
            return "saved", value
        except ValueError as exc:
            return "conflict", exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(append, ("b", "c")))
    assert [status for status, _ in results].count("saved") == 1
    assert [status for status, _ in results].count("conflict") == 1
    conflict = next(value for status, value in results if status == "conflict")
    assert str(conflict) == "DELIVERABLE_VERSION_CONFLICT"
    assert conflict.current["version"] == 2
    assert len(
        ledger_set.publications.list_deliverable_revisions(
            case["id"], "FULL_CREDIT"
        )
    ) == 2
    assert len(
        [
            event
            for event in ledger_set.publications.list_audit()
            if event["action"] == "deliverable.draft_versioned"
            and event["case_id"] == case["id"]
        ]
    ) == 2


def test_strict_draft_contract_rejects_client_generated_values() -> None:
    payload = _draft_payload()
    payload["blocks"].append(
        {
            "kind": "GENERATED_METRIC",
            "block_id": "rv.generated.leverage",
            "slot_id": "appendix.generated-metric.01",
            "metric_ids": ["total_leverage"],
            "values": {"total_leverage": "4.2"},
        }
    )
    with pytest.raises(ValidationError):
        DeliverableDraftRequest.model_validate(payload)


def test_domain_validates_template_order_and_saves_complete_shared_draft() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    service = DeliverableService(
        ledgers.publications, ledgers.sources, ledgers.models
    )
    payload = DeliverableDraftRequest.model_validate(_draft_payload())
    saved = service.save(case["id"], "RELATIVE_VALUE", ACTOR, payload)
    assert saved["current"]["version"] == 1
    assert saved["current"]["author"] == ACTOR
    assert saved["current"]["digest"] == digest(saved["current"]["content"])
    assert saved["history"] == [saved["current"]]

    reordered = _draft_payload()
    reordered["blocks"][0], reordered["blocks"][1] = (
        reordered["blocks"][1],
        reordered["blocks"][0],
    )
    with pytest.raises(ValueError, match="DELIVERABLE_TEMPLATE_ORDER_INVALID"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(reordered),
        )


def test_restore_creates_a_new_revision_without_mutating_history() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    service = DeliverableService(
        ledgers.publications, ledgers.sources, ledgers.models
    )
    first_request = DeliverableDraftRequest.model_validate(_draft_payload())
    first = service.save(case["id"], "RELATIVE_VALUE", ACTOR, first_request)

    changed_payload = _draft_payload()
    changed_payload["expected_version"] = 1
    changed_payload["blocks"][0]["text"] = "A changed analyst conclusion."
    second = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(changed_payload),
    )

    first_content = first["current"]["content"]
    restore_payload = {
        "expected_version": 2,
        "template_id": first_content["template_id"],
        "template_version": first_content["template_version"],
        "model_selection": first_content["model_selection"],
        "blocks": first_content["blocks"],
    }
    restored = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(restore_payload),
    )

    assert restored["current"]["version"] == 3
    assert restored["current"]["content"] == first_content
    assert [revision["version"] for revision in restored["history"]] == [1, 2, 3]
    assert restored["history"][0] == first["current"]
    assert restored["history"][1] == second["current"]


def test_evidence_citations_reject_cross_case_withdrawn_and_unknown_blocks() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    other = ledgers.runs.create_case("Other", "Other", "Testing", ACTOR)

    def source(case_id: str, suffix: str) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "filename": f"source-{suffix}.txt",
            "media_type": "text/plain",
            "bytes": 6,
            "sha256": suffix * 64,
            "vault_path": f"sources/{suffix}/source.txt",
            "blocks": [
                {
                    "block_id": "b00001",
                    "locator": {"line": 1},
                    "text": "Evidence",
                    "extractor_version": "test-v1",
                    "confidence": "HIGH",
                    "untrusted_data": True,
                }
            ],
            "created_by": ACTOR,
            "created_at": "2026-08-26T00:00:00+00:00",
            "withdrawn": False,
        }

    own_source = ledgers.sources.ingest(source(case["id"], "a"), ACTOR)
    other_source = ledgers.sources.ingest(source(other["id"], "b"), ACTOR)
    service = DeliverableService(
        ledgers.publications, ledgers.sources, ledgers.models
    )

    def cited(source_id: str, block_id: str = "b00001") -> DeliverableDraftRequest:
        payload = _draft_payload()
        payload["blocks"][0].update(
            content_mode="EVIDENCE",
            citations=[
                {
                    "source_id": source_id,
                    "block_ids": [block_id],
                    "claim": "Supported conclusion",
                }
            ],
        )
        return DeliverableDraftRequest.model_validate(payload)

    with pytest.raises(ValueError, match="EVIDENCE_CASE_MISMATCH"):
        service.save(case["id"], "RELATIVE_VALUE", ACTOR, cited(other_source["id"]))
    with pytest.raises(ValueError, match="EVIDENCE_BLOCK_MISMATCH"):
        service.save(case["id"], "RELATIVE_VALUE", ACTOR, cited(own_source["id"], "missing"))
    ledgers.sources.withdraw(case["id"], own_source["id"], ACTOR)
    with pytest.raises(ValueError, match="EVIDENCE_SOURCE_WITHDRAWN"):
        service.save(case["id"], "RELATIVE_VALUE", ACTOR, cited(own_source["id"]))


def test_active_revision_and_acknowledged_fallback_model_eligibility() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    saved = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(payload),
    )
    assert saved["model_eligibility"]["active_revision"]["revision_id"] == models.revision["id"]
    assert saved["model_eligibility"]["default_model_selection"] == {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }

    assert models.revision is not None
    models.revision = {**models.revision, "id": "revision_newer"}
    payload["expected_version"] = 1
    with pytest.raises(ValueError, match="DELIVERABLE_MODEL_REVISION_STALE"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )
    payload["model_selection"] = {
        "kind": "APPLICATION_BUILD",
        "build_id": models.build["id"],
        "fallback_acknowledged": True,
    }
    with pytest.raises(
        ValueError, match="DELIVERABLE_APPLICATION_BUILD_FALLBACK_NOT_ELIGIBLE"
    ):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )

    models.revision = None
    fallback = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(payload),
    )
    assert fallback["current"]["content"]["model_selection"]["kind"] == "APPLICATION_BUILD"
    assert fallback["current"]["content"]["model_identity"] == {
        "kind": "APPLICATION_BUILD",
        "build_id": models.build["id"],
        "accepted_snapshot_id": models.build["accepted_snapshot_id"],
        "build_input_fingerprint": models.build["input_fingerprint"],
        "build_payload_digest": models.build["payload_digest"],
        "calculation_runtime": models.build["calculation_runtime"],
    }


def test_selected_model_must_resolve_to_exact_pinned_record() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    models.get_revision = lambda _revision_id: None  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="DELIVERABLE_MODEL_REVISION_STALE"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )

    models.revision = None
    payload["model_selection"] = {
        "kind": "APPLICATION_BUILD",
        "build_id": models.build["id"],
        "fallback_acknowledged": True,
    }
    models.get_build = lambda _build_id: None  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="DELIVERABLE_MODEL_BUILD_STALE"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )


@pytest.mark.parametrize(
    "block",
    [
        {
            "kind": "GENERATED_METRIC",
            "block_id": "rv.generated.metric",
            "slot_id": "appendix.generated-metric.01",
            "metric_ids": ["total_leverage"],
        },
        {
            "kind": "GENERATED_TABLE",
            "block_id": "rv.generated.table",
            "slot_id": "appendix.generated-table.01",
            "table_id": "annual_model",
            "field_ids": ["total_leverage"],
        },
        {
            "kind": "GENERATED_CHART",
            "block_id": "rv.generated.chart",
            "slot_id": "appendix.generated-chart.01",
            "recipe": {
                "kind": "trend",
                "schema_version": "1.0",
                "fields": ["total_leverage"],
                "units": "x",
                "metric_ids": [],
                "polarity": "neutral",
                "accessible_table": True,
            },
        },
        {
            "kind": "MODEL_APPENDIX",
            "block_id": "rv.model-appendix",
            "slot_id": "appendix.model-appendix.01",
        },
    ],
    ids=["metric", "table", "chart", "model-appendix"],
)
def test_all_model_dependent_optional_blocks_require_and_pin_selected_model(
    block: dict[str, Any],
) -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    without_model = _draft_payload()
    without_model["blocks"].append(block)
    with pytest.raises(ValueError, match="DELIVERABLE_MODEL_REQUIRED_FOR_BLOCK"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(without_model),
        )

    with_model = _draft_payload()
    with_model["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    with_model["blocks"].append(block)
    saved = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(with_model),
    )
    generated = saved["current"]["content"]["generated_blocks"][block["block_id"]]
    assert generated["model_digest"] == digest(
        saved["current"]["content"]["model_identity"]
    )


def test_template_owns_exact_optional_slot_kind_and_order_policy() -> None:
    template = DELIVERABLE_TEMPLATES["RELATIVE_VALUE"]
    assert template["optional_blocks"] == [
        {
            "kind": "GENERATED_METRIC",
            "slot_stem": "appendix.generated-metric",
            "max_items": 20,
            "order": 1,
            "model_dependent": True,
        },
        {
            "kind": "GENERATED_TABLE",
            "slot_stem": "appendix.generated-table",
            "max_items": 20,
            "order": 2,
            "model_dependent": True,
        },
        {
            "kind": "GENERATED_CHART",
            "slot_stem": "appendix.generated-chart",
            "max_items": 20,
            "order": 3,
            "model_dependent": True,
        },
        {
            "kind": "SCENARIO_EXHIBIT",
            "slot_stem": "appendix.scenario",
            "max_items": 20,
            "order": 4,
            "model_dependent": True,
        },
        {
            "kind": "MODEL_APPENDIX",
            "slot_stem": "appendix.model-appendix",
            "max_items": 1,
            "order": 5,
            "model_dependent": True,
        },
        {
            "kind": "LIMITATIONS",
            "slot_stem": "appendix.limitations",
            "max_items": 1,
            "order": 6,
            "model_dependent": False,
        },
    ]
    assert template["allowed_appendices"] == [
        policy["kind"] for policy in template["optional_blocks"]
    ]


@pytest.mark.parametrize(
    "block",
    [
        {
            "kind": "HEADING",
            "block_id": "client.heading",
            "slot_id": "appendix.heading.01",
            "text": "Client invented heading",
        },
        {
            "kind": "NARRATIVE",
            "block_id": "client.narrative",
            "slot_id": "appendix.narrative.01",
            "text": "Client invented narrative",
            "content_mode": "ANALYST_JUDGMENT",
            "citations": [],
        },
        {
            "kind": "GENERATED_METRIC",
            "block_id": "client.metric",
            "slot_id": "appendix.client-invented.01",
            "metric_ids": ["total_leverage"],
        },
    ],
    ids=["heading", "narrative", "invented-slot"],
)
def test_template_rejects_client_invented_optional_kind_or_slot(
    block: dict[str, Any],
) -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    payload["blocks"].append(block)
    with pytest.raises(ValueError, match="DELIVERABLE_SLOT_INVALID"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )


def test_template_rejects_invalid_optional_order() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    payload["blocks"].extend(
        [
            {
                "kind": "GENERATED_TABLE",
                "block_id": "rv.generated.table",
                "slot_id": "appendix.generated-table.01",
                "table_id": "annual_model",
                "field_ids": ["total_leverage"],
            },
            {
                "kind": "GENERATED_METRIC",
                "block_id": "rv.generated.metric",
                "slot_id": "appendix.generated-metric.01",
                "metric_ids": ["total_leverage"],
            },
        ]
    )
    with pytest.raises(ValueError, match="DELIVERABLE_TEMPLATE_ORDER_INVALID"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )


def test_template_accepts_declared_non_model_limitations_slot() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    service = DeliverableService(
        ledgers.publications, ledgers.sources, ledgers.models
    )
    payload = _draft_payload()
    payload["blocks"].append(
        {
            "kind": "LIMITATIONS",
            "block_id": "rv.limitations",
            "slot_id": "appendix.limitations.01",
            "text": "No current signed model is included.",
            "citations": [],
        }
    )
    saved = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(payload),
    )
    assert saved["current"]["content"]["model_identity"] is None
    assert saved["current"]["content"]["blocks"][-1]["kind"] == "LIMITATIONS"


def test_generated_metric_and_scenario_are_rebuilt_from_exact_current_model() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    payload["blocks"].append(
        {
            "kind": "GENERATED_METRIC",
            "block_id": "rv.generated.leverage",
            "slot_id": "appendix.generated-metric.01",
            "metric_ids": ["total_leverage"],
        }
    )
    scenario = {
        "case_id": case["id"],
        "build_id": models.build["id"],
        "base_revision_id": models.revision["id"],
        "registry_version": "registry-v1",
        "registry_digest": "c" * 64,
        "draft_generation": 7,
        "effective_assumptions": [
            {"assumption_id": "operating.revenue_growth.consolidated"}
        ],
        "assumptions_digest": digest(
            [{"assumption_id": "operating.revenue_growth.consolidated"}]
        ),
        "outputs": {"BASE": {"FY2027": {"total_leverage": "4.8"}}},
        "outputs_digest": digest(
            {"BASE": {"FY2027": {"total_leverage": "4.8"}}}
        ),
        "deltas": {"BASE": {"FY2027": {"total_leverage": "0.6"}}},
    }
    payload["blocks"].append(
        {
            "kind": "SCENARIO_EXHIBIT",
            "block_id": "rv.scenario.01",
            "slot_id": "appendix.scenario.01",
            "title": "Downside stress",
            "shocks": [
                {
                    "assumption_id": "operating.revenue_growth.consolidated",
                    "case": "BASE",
                    "period_id": "FY2027",
                    "value": -0.05,
                }
            ],
            "scenario": scenario,
            "scenario_digest": digest(scenario),
        }
    )
    service.scenario_service = _ScenarioAuthority(scenario)
    saved = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(payload),
    )
    generated = saved["current"]["content"]["generated_blocks"]
    assert generated["rv.generated.leverage"]["outputs"] == {
        "BASE": {"FY2027": {"total_leverage": "4.2"}}
    }
    assert generated["rv.scenario.01"]["scenario_digest"] == digest(scenario)
    assert generated["rv.scenario.01"]["model_digest"] == digest(
        saved["current"]["content"]["model_identity"]
    )
    assert generated["rv.scenario.01"]["model_identity"] == {
        "accepted_snapshot_id": models.build["accepted_snapshot_id"],
        "build_input_fingerprint": models.build["input_fingerprint"],
        "build_payload_digest": models.build["payload_digest"],
        "calculation_contract_version": "calculation-v1",
    }
    forged = {**scenario, "outputs": {"BASE": {"FY2027": {"total_leverage": "1.0"}}}}
    service.scenario_service = _ScenarioAuthority(forged)
    payload["expected_version"] = 1
    with pytest.raises(ValueError, match="SCENARIO_EXHIBIT_CALCULATION_MISMATCH"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )


def test_scenario_exhibit_requires_selected_model_before_calculation() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    payload = _draft_payload()
    scenario = {
        "case_id": case["id"],
        "build_id": models.build["id"],
        "base_revision_id": models.revision["id"],
        "registry_version": "registry-v1",
        "registry_digest": "c" * 64,
        "draft_generation": 1,
        "effective_assumptions": [{"assumption_id": "operating.revenue_growth.consolidated"}],
        "assumptions_digest": digest(
            [{"assumption_id": "operating.revenue_growth.consolidated"}]
        ),
        "outputs": {"BASE": {"FY2027": {"total_leverage": "4.8"}}},
        "outputs_digest": digest(
            {"BASE": {"FY2027": {"total_leverage": "4.8"}}}
        ),
        "deltas": {"BASE": {"FY2027": {"total_leverage": "0.6"}}},
    }
    payload["blocks"].append(
        {
            "kind": "SCENARIO_EXHIBIT",
            "block_id": "rv.scenario.01",
            "slot_id": "appendix.scenario.01",
            "title": "Downside stress",
            "shocks": [
                {
                    "assumption_id": "operating.revenue_growth.consolidated",
                    "case": "BASE",
                    "period_id": "FY2027",
                    "value": -0.05,
                }
            ],
            "scenario": scenario,
            "scenario_digest": digest(scenario),
        }
    )
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="DELIVERABLE_MODEL_REQUIRED_FOR_BLOCK"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )


@pytest.mark.parametrize(
    ("selection_kind", "base_mode"),
    [
        ("ANALYST_REVISION", "NULL"),
        ("APPLICATION_BUILD", "HISTORICAL_REVISION"),
        ("ANALYST_REVISION", "SAME_BUILD_WRONG_REVISION"),
    ],
    ids=[
        "selected-revision-requires-same-base",
        "application-build-requires-null-base",
        "selected-revision-rejects-same-build-wrong-base",
    ],
)
def test_scenario_base_binds_exactly_to_selected_model_without_persistence(
    selection_kind: str, base_mode: str, ledger_set: Any
) -> None:
    ledgers = ledger_set
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    assert models.revision is not None
    selected_revision = models.revision
    wrong_revision = {**selected_revision, "id": "revision_same_build_wrong"}

    if selection_kind == "APPLICATION_BUILD":
        models.revision = None
        model_selection = {
            "kind": "APPLICATION_BUILD",
            "build_id": models.build["id"],
            "fallback_acknowledged": True,
        }
    else:
        model_selection = {
            "kind": "ANALYST_REVISION",
            "build_id": models.build["id"],
            "revision_id": selected_revision["id"],
        }

    if base_mode == "NULL":
        base_revision_id = None
    elif base_mode == "HISTORICAL_REVISION":
        base_revision_id = selected_revision["id"]
    else:
        base_revision_id = wrong_revision["id"]

    models.get_revision = lambda revision_id: (  # type: ignore[method-assign]
        selected_revision
        if revision_id == selected_revision["id"]
        else wrong_revision
        if revision_id == wrong_revision["id"]
        else None
    )
    scenario = {
        "case_id": case["id"],
        "build_id": models.build["id"],
        "base_revision_id": base_revision_id,
        "registry_version": "registry-v1",
        "registry_digest": "c" * 64,
        "draft_generation": 2,
        "effective_assumptions": [
            {"assumption_id": "operating.revenue_growth.consolidated"}
        ],
        "assumptions_digest": digest(
            [{"assumption_id": "operating.revenue_growth.consolidated"}]
        ),
        "outputs": {"BASE": {"FY2027": {"total_leverage": "4.8"}}},
        "outputs_digest": digest(
            {"BASE": {"FY2027": {"total_leverage": "4.8"}}}
        ),
        "deltas": {"BASE": {"FY2027": {"total_leverage": "0.6"}}},
    }
    payload = _draft_payload()
    payload["model_selection"] = model_selection
    payload["blocks"].append(
        {
            "kind": "SCENARIO_EXHIBIT",
            "block_id": "rv.scenario.01",
            "slot_id": "appendix.scenario.01",
            "title": "Downside stress",
            "shocks": [
                {
                    "assumption_id": "operating.revenue_growth.consolidated",
                    "case": "BASE",
                    "period_id": "FY2027",
                    "value": -0.05,
                }
            ],
            "scenario": scenario,
            "scenario_digest": digest(scenario),
        }
    )
    service = DeliverableService(
        ledgers.publications,
        ledgers.sources,
        models,  # type: ignore[arg-type]
        scenario_service=_ScenarioMustNotRun(),
    )

    with pytest.raises(ValueError, match="SCENARIO_EXHIBIT_IDENTITY_INVALID"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )

    assert ledgers.publications.list_deliverable_revisions(
        case["id"], "RELATIVE_VALUE"
    ) == []
    assert not [
        event
        for event in ledgers.publications.list_audit()
        if event["action"] == "deliverable.draft_versioned"
        and event.get("case_id") == case["id"]
    ]


def test_application_build_scenario_accepts_null_base_revision() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    models.revision = None
    scenario = {
        "case_id": case["id"],
        "build_id": models.build["id"],
        "base_revision_id": None,
        "registry_version": "registry-v1",
        "registry_digest": "c" * 64,
        "draft_generation": 3,
        "effective_assumptions": [
            {"assumption_id": "operating.revenue_growth.consolidated"}
        ],
        "assumptions_digest": digest(
            [{"assumption_id": "operating.revenue_growth.consolidated"}]
        ),
        "outputs": {"BASE": {"FY2027": {"total_leverage": "4.8"}}},
        "outputs_digest": digest(
            {"BASE": {"FY2027": {"total_leverage": "4.8"}}}
        ),
        "deltas": {"BASE": {"FY2027": {"total_leverage": "0.6"}}},
    }
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "APPLICATION_BUILD",
        "build_id": models.build["id"],
        "fallback_acknowledged": True,
    }
    payload["blocks"].append(
        {
            "kind": "SCENARIO_EXHIBIT",
            "block_id": "rv.scenario.01",
            "slot_id": "appendix.scenario.01",
            "title": "Downside stress",
            "shocks": [
                {
                    "assumption_id": "operating.revenue_growth.consolidated",
                    "case": "BASE",
                    "period_id": "FY2027",
                    "value": -0.05,
                }
            ],
            "scenario": scenario,
            "scenario_digest": digest(scenario),
        }
    )
    service = DeliverableService(
        ledgers.publications,
        ledgers.sources,
        models,  # type: ignore[arg-type]
        scenario_service=_ScenarioAuthority(scenario),
    )
    saved = service.save(
        case["id"],
        "RELATIVE_VALUE",
        ACTOR,
        DeliverableDraftRequest.model_validate(payload),
    )
    assert saved["current"]["content"]["model_identity"]["kind"] == "APPLICATION_BUILD"
    assert saved["current"]["content"]["generated_blocks"]["rv.scenario.01"][
        "scenario"
    ]["base_revision_id"] is None


def test_generated_blocks_reject_ungoverned_metric_and_recipe_fields() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    payload["blocks"].append(
        {
            "kind": "GENERATED_METRIC",
            "block_id": "rv.generated.unknown",
            "slot_id": "appendix.generated-metric.01",
            "metric_ids": ["client_computed_alpha"],
        }
    )
    with pytest.raises(ValueError, match="DELIVERABLE_GENERATED_FIELD_INVALID"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )

    payload["blocks"][-1] = {
        "kind": "GENERATED_CHART",
        "block_id": "rv.generated.chart",
        "slot_id": "appendix.generated-chart.01",
        "recipe": {
            "kind": "trend",
            "schema_version": "1.0",
            "fields": ["client_computed_alpha"],
            "units": "x",
            "metric_ids": [],
            "polarity": "neutral",
            "accessible_table": True,
        },
    }
    with pytest.raises(ValueError, match="recipe field is not schema-known"):
        service.save(
            case["id"],
            "RELATIVE_VALUE",
            ACTOR,
            DeliverableDraftRequest.model_validate(payload),
        )


def test_scenario_exhibit_requires_exact_server_calculation_digest() -> None:
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Draft", "Issuer", "Testing", ACTOR)
    models = _ModelAuthority(case["id"])
    service = DeliverableService(ledgers.publications, ledgers.sources, models)  # type: ignore[arg-type]
    payload = _draft_payload()
    payload["model_selection"] = {
        "kind": "ANALYST_REVISION",
        "build_id": models.build["id"],
        "revision_id": models.revision["id"],
    }
    scenario = {
        "case_id": case["id"],
        "build_id": models.build["id"],
        "base_revision_id": models.revision["id"],
        "registry_version": "registry-v1",
        "registry_digest": "c" * 64,
        "draft_generation": 0,
        "effective_assumptions": [
            {"assumption_id": "operating.revenue_growth.consolidated"}
        ],
        "assumptions_digest": digest(
            [{"assumption_id": "operating.revenue_growth.consolidated"}]
        ),
        "outputs": {},
        "outputs_digest": digest({}),
        "deltas": {},
    }
    payload["blocks"].append(
        {
            "kind": "SCENARIO_EXHIBIT",
            "block_id": "rv.scenario.01",
            "slot_id": "appendix.scenario.01",
            "title": "Downside stress",
            "shocks": [
                {
                    "assumption_id": "operating.revenue_growth.consolidated",
                    "case": "BASE",
                    "period_id": "FY2027",
                    "value": -0.05,
                }
            ],
            "scenario": scenario,
            "scenario_digest": "0" * 64,
        }
    )
    request = DeliverableDraftRequest.model_validate(payload)
    with pytest.raises(ValueError, match="SCENARIO_EXHIBIT_DIGEST_INVALID"):
        service.save(case["id"], "RELATIVE_VALUE", ACTOR, request)


def test_http_deliverable_current_history_by_id_and_recoverable_conflict(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        case_id = client.post(
            "/api/cases",
            json={"name": "Draft", "issuer": "Issuer", "sector": "Testing"},
        ).json()["id"]
        route = f"/api/cases/{case_id}/deliverables/RELATIVE_VALUE"
        empty = client.get(route)
        assert empty.status_code == 200
        assert empty.json()["current"] is None
        assert empty.json()["template"]["title"] == "Relative Value Note"

        saved = client.put(f"{route}/draft", json=_draft_payload())
        assert saved.status_code == 200, saved.text
        current = saved.json()["current"]
        assert current["version"] == 1
        assert client.get(
            f"/api/cases/{case_id}/deliverables/by-id/{current['id']}"
        ).json() == current

        conflict = client.put(f"{route}/draft", json=_draft_payload())
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == {
            "code": "DELIVERABLE_VERSION_CONFLICT",
            "current": current,
        }


def test_http_case_reader_can_read_but_cannot_write_deliverable(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        case_id = client.post(
            "/api/cases",
            json={"name": "Draft", "issuer": "Issuer", "sector": "Testing"},
        ).json()["id"]
        headers = {"x-caos-role": "READER"}
        route = f"/api/cases/{case_id}/deliverables/RELATIVE_VALUE"
        assert client.get(route, headers=headers).status_code == 200
        assert client.put(
            f"{route}/draft", json=_draft_payload(), headers=headers
        ).status_code == 403
