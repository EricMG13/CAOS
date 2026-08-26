from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from caos import ledgers
from caos.config import Settings
from caos.contracts import digest
from caos.http import create_app
from caos.migrations import apply_migrations
from caos.postgres_ledgers import PostgresLedgerSet
from migrate import migrate


def test_normalized_authority_migration_is_forward_only_and_complete() -> None:
    path = (
        Path(__file__).parents[1]
        / "server"
        / "migrations"
        / "006_normalized_authority.sql"
    )
    sql = path.read_text(encoding="utf-8").lower()

    assert "caos_state" not in sql
    assert "drop table" not in sql
    assert "delete from" not in sql
    for authority in (
        "current_source_set_id",
        "current_execution_id",
        "accepted_snapshot_id",
        "visible_snapshot_id",
        "workflow_events",
        "notes",
        "assumptions",
        "methodology_drafts",
        "rv_universes",
        "research jsonb",
        "stage integer",
        "record jsonb",
        "sources_active_case_sha256_idx",
        "where withdrawn = false",
    ):
        assert authority in sql


def test_normalized_authority_migration_applies_once_and_is_idempotent() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(
        database_url.replace("postgresql+psycopg://", "postgresql://")
    ) as connection:
        apply_migrations(connection, root)
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version = '006_normalized_authority'"
            )
        assert apply_migrations(connection, root) == ("006_normalized_authority",)
        assert apply_migrations(connection, root) == ()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE schemaname=current_schema() "
                "AND indexname='sources_active_case_sha256_idx'"
            )
            assert "WHERE (withdrawn = false)" in cursor.fetchone()[0]
            cursor.execute(
                "SELECT count(*) FROM pg_constraint WHERE conrelid='sources'::regclass "
                "AND contype='u' AND pg_get_constraintdef(oid) ILIKE '%case_id%sha256%'"
            )
            assert cursor.fetchone()[0] == 0
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE schemaname=current_schema() "
                "AND indexname='jobs_run_coordinator_idx'"
            )
            job_index = cursor.fetchone()[0].lower()
            assert "where" in job_index
            assert "node_id is null" in job_index
            assert "queued" in job_index and "claimed" in job_index
        connection.rollback()


def test_model_revision_migration_backfills_immutable_build_authority_order(
    tmp_path: Path,
) -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from psycopg.types.json import Jsonb

    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    schema = f"build_authority_{uuid.uuid4().hex}"
    root = Path(__file__).parents[1] / "server" / "migrations"
    staged = tmp_path / "migrations"
    staged.mkdir()
    for migration in sorted(root.glob("00[1-6]_*.sql")):
        shutil.copy2(migration, staged / migration.name)
    with psycopg.connect(database_url) as admin:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    scoped_url = make_conninfo(database_url, options=f"-c search_path={schema}")
    try:
        with psycopg.connect(scoped_url) as connection:
            assert apply_migrations(connection, staged)
            older_time = "2026-08-25T00:00:00+00:00"
            same_time = "2026-08-26T00:00:00+00:00"
            runtime = {
                "assumption_registry_version": "cp-model.assumptions.v1",
                "assumption_registry_digest": "a" * 64,
                "calculation_contract_version": "cp-model.calculation.v1",
            }
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cases(id, name, issuer, sector, created_by) "
                    "VALUES ('case-order', 'Order', 'Issuer', 'Testing', 'analyst')"
                )
                cursor.execute(
                    "INSERT INTO source_sets(id, case_id, version, source_ids, created_by) "
                    "VALUES ('source-set', 'case-order', 1, %s, 'analyst')",
                    (Jsonb([]),),
                )
                cursor.execute(
                    "INSERT INTO runs(id, case_id, status, plan, accepted_snapshot_id, "
                    "created_by) VALUES ('run-order', 'case-order', 'succeeded', %s, "
                    "'snapshot-order', 'analyst')",
                    (Jsonb({}),),
                )
                cursor.execute(
                    "INSERT INTO accepted_snapshots(id, case_id, run_id, digest, "
                    "source_set_id, source_set_version, artifact_refs) VALUES "
                    "('snapshot-order', 'case-order', 'run-order', %s, 'source-set', 1, %s)",
                    ("9" * 64, Jsonb([])),
                )
                cursor.execute(
                    "UPDATE cases SET accepted_snapshot_id='snapshot-order' "
                    "WHERE id='case-order'"
                )
                for build_id, fingerprint, queued_at in (
                    ("model_m_old", "c" * 64, older_time),
                    ("model_z_equal", "d" * 64, same_time),
                    ("model_a_equal", "e" * 64, same_time),
                ):
                    record = {
                        "id": build_id,
                        "case_id": "case-order",
                        "accepted_run_id": "run-order",
                        "accepted_snapshot_id": "snapshot-order",
                        "source_set_id": "source-set",
                        "input_fingerprint": fingerprint,
                        "worksheet_schema_version": "caos.model.worksheet.v1",
                        "calculation_runtime": runtime,
                        "status": "READY",
                        "payload_digest": "b" * 64,
                        "queued_at": queued_at,
                    }
                    cursor.execute(
                        "INSERT INTO model_builds(id, case_id, accepted_run_id, "
                        "accepted_snapshot_id, source_set_id, input_fingerprint, status, "
                        "record, created_by, queued_at) VALUES (%s, 'case-order', "
                        "'run-order', 'snapshot-order', 'source-set', %s, 'READY', %s, "
                        "'analyst', %s)",
                        (build_id, fingerprint, Jsonb(record), queued_at),
                    )
                cursor.execute(
                    "UPDATE model_builds SET record=record || %s "
                    "WHERE id='model_m_old'",
                    (Jsonb({"heap_update": True}),),
                )
            shutil.copy2(root / "007_model_revisions.sql", staged / "007_model_revisions.sql")
            assert apply_migrations(connection, staged) == ("007_model_revisions",)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, authority_order FROM model_builds "
                    "ORDER BY authority_order"
                )
                first_orders = cursor.fetchall()
                cursor.execute(
                    "SELECT is_identity, identity_generation FROM information_schema.columns "
                    "WHERE table_schema=current_schema() AND table_name='model_builds' "
                    "AND column_name='authority_order'"
                )
                assert cursor.fetchone() == ("YES", "ALWAYS")
            assert first_orders == [
                ("model_m_old", 1),
                ("model_a_equal", 2),
                ("model_z_equal", 3),
            ]
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM schema_migrations WHERE version='007_model_revisions'"
                )
            assert apply_migrations(connection, staged) == ("007_model_revisions",)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, authority_order FROM model_builds "
                    "ORDER BY authority_order"
                )
                assert cursor.fetchall() == first_orders
            connection.commit()

            durable = PostgresLedgerSet(scoped_url)
            listed = durable.models.list_builds("case-order")
            assert [build["id"] for build in listed] == [
                "model_z_equal",
                "model_a_equal",
                "model_m_old",
            ]
            oldest = listed[-1]
            assumptions: list[dict[str, object]] = []
            outputs: dict[str, object] = {}
            proposal = {
                "case_id": "case-order",
                "build_id": oldest["id"],
                "accepted_snapshot_id": "snapshot-order",
                "build_input_fingerprint": oldest["input_fingerprint"],
                "build_payload_digest": oldest["payload_digest"],
                "registry_version": runtime["assumption_registry_version"],
                "registry_digest": runtime["assumption_registry_digest"],
                "calculation_contract_version": runtime[
                    "calculation_contract_version"
                ],
                "effective_assumptions": assumptions,
                "assumptions_digest": digest(assumptions),
                "outputs": outputs,
                "outputs_digest": digest(outputs),
                "preview_digest": "f" * 64,
                "parent_revision_id": None,
                "note": "Legacy order proof",
            }
            before_audit = durable.publications.list_audit()
            with pytest.raises(ledgers.RevisionConflictError) as conflict:
                durable.models.sign_off_revision(
                    proposal,
                    "analyst",
                    expected_head_revision_id=None,
                    expected_current_build_id=oldest["id"],
                    expected_current_input_fingerprint=oldest["input_fingerprint"],
                )
            assert conflict.value.current is None
            assert conflict.value.current_build["id"] == "model_z_equal"
            assert durable.models.list_revisions("case-order") == []
            assert durable.models.get_revision_head("case-order") is None
            assert durable.models.pending_revision_exports() == []
            assert durable.publications.list_audit() == before_audit

        with psycopg.connect(scoped_url) as connection:
            latest_record = {
                **listed[0],
                "id": "model_0_latest",
                "input_fingerprint": "1" * 64,
                "queued_at": older_time,
            }
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO model_builds(id, case_id, accepted_run_id, "
                    "accepted_snapshot_id, source_set_id, input_fingerprint, status, "
                    "record, created_by, queued_at) VALUES ('model_0_latest', "
                    "'case-order', 'run-order', 'snapshot-order', 'source-set', %s, "
                    "'READY', %s, 'analyst', %s) RETURNING authority_order",
                    ("1" * 64, Jsonb(latest_record), older_time),
                )
                latest_order = cursor.fetchone()[0]
                assert latest_order > first_orders[-1][1]
            with pytest.raises(psycopg.errors.GeneratedAlways):
                with connection.transaction():
                    connection.execute(
                        "UPDATE model_builds SET authority_order=%s "
                        "WHERE id='model_m_old'",
                        (latest_order + 1,),
                    )
        post_migration = PostgresLedgerSet(scoped_url)
        post_migration_builds = post_migration.models.list_builds("case-order")
        assert post_migration_builds[0]["id"] == "model_0_latest"
        assert all(
            "authority_order" not in build for build in post_migration_builds
        )
    finally:
        with psycopg.connect(database_url) as admin:
            with admin.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                )


def test_normalized_app_never_reads_or_writes_a_post_migration_legacy_row(
    tmp_path: Path,
) -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for legacy-row inertness proof")
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from psycopg.types.json import Jsonb

    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    schema = f"task5_envelope_{uuid.uuid4().hex}"
    migrations = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(database_url) as admin:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    scoped_url = make_conninfo(database_url, options=f"-c search_path={schema}")
    try:
        with psycopg.connect(scoped_url) as connection:
            assert apply_migrations(connection, migrations)
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE TABLE caos_state ("
                    "id boolean PRIMARY KEY, revision bigint NOT NULL, state jsonb NOT NULL)"
                )
                cursor.execute(
                    "INSERT INTO caos_state(id, revision, state) VALUES (true, %s, %s)",
                    (37, Jsonb({"owner": "unrelated-system", "payload": [1, 2, 3]})),
                )
                cursor.execute(
                    "SELECT revision, convert_to(state::text, 'UTF8') "
                    "FROM caos_state WHERE id=true"
                )
                legacy_before = cursor.fetchone()

        settings = Settings(
            database_url=scoped_url,
            storage_dir=tmp_path / "vault",
            deploy_v_root=Path(__file__).parents[1]
            / "server"
            / "caos"
            / "methodology"
            / "vendor"
            / "deploy_v",
        )
        ledgers = PostgresLedgerSet(scoped_url)
        with TestClient(create_app(settings, ledgers)) as client:
            case = client.post(
                "/api/cases",
                json={
                    "name": "Envelope inertness",
                    "issuer": "Issuer",
                    "sector": "Testing",
                },
            )
            assert case.status_code == 201
            case_id = case.json()["id"]
            source = client.post(
                f"/api/cases/{case_id}/sources",
                files={"file": ("earnings.txt", b"Revenue 100", "text/plain")},
            )
            assert source.status_code == 201
            source_id = source.json()["id"]
            run = client.app.state.ledgers.runs.create_run_with_nodes(
                case_id,
                "local-analyst",
                {
                    "pathway": "EARNINGS_UPDATE",
                    "source_set_id": source.json()["source_set"]["id"],
                },
                [],
            )
            run_id = run["id"]

        with psycopg.connect(scoped_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT revision, convert_to(state::text, 'UTF8') "
                    "FROM caos_state WHERE id=true"
                )
                assert cursor.fetchone() == legacy_before
                cursor.execute(
                    "SELECT "
                    "EXISTS(SELECT 1 FROM cases WHERE id=%s), "
                    "EXISTS(SELECT 1 FROM sources WHERE id=%s), "
                    "EXISTS(SELECT 1 FROM runs WHERE id=%s)",
                    (case_id, source_id, run_id),
                )
                assert cursor.fetchone() == (True, True, True)
    finally:
        with psycopg.connect(database_url) as admin:
            with admin.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                )


def test_migrate_rejects_non_postgresql_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "not-a-postgres-url")

    with pytest.raises(SystemExit, match="DATABASE_URL must be a PostgreSQL URL"):
        migrate()


def test_forward_migration_adds_planning_to_an_existing_runs_constraint() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(
        database_url.replace("postgresql+psycopg://", "postgresql://")
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version = '005_runs_planning_status'"
            )
            cursor.execute("ALTER TABLE runs DROP CONSTRAINT runs_status_check")
            cursor.execute(
                "ALTER TABLE runs ADD CONSTRAINT runs_status_check "
                "CHECK (status IN ('queued', 'running', 'paused', 'succeeded', 'failed'))"
            )
        assert apply_migrations(connection, root) == ("005_runs_planning_status",)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'runs'::regclass AND conname = 'runs_status_check'"
            )
            definition = cursor.fetchone()[0]
        assert "planning" in definition
        connection.rollback()


def test_loan_source_fk_migration_ignores_a_same_named_constraint_on_another_table() -> (
    None
):
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(
        database_url.replace("postgresql+psycopg://", "postgresql://")
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version = '004_rv_loan_universe_source_fk'"
            )
            cursor.execute(
                "ALTER TABLE rv_loan_universes DROP CONSTRAINT rv_loan_universes_source_id_fkey"
            )
            cursor.execute(
                "CREATE TEMP TABLE migration_constraint_decoy("
                "id integer CONSTRAINT rv_loan_universes_source_id_fkey CHECK (id > 0))"
            )
        assert apply_migrations(connection, root) == ("004_rv_loan_universe_source_fk",)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT contype, confrelid = 'sources'::regclass, pg_get_constraintdef(oid) "
                "FROM pg_constraint WHERE conrelid = 'rv_loan_universes'::regclass "
                "AND conname = 'rv_loan_universes_source_id_fkey'"
            )
            assert cursor.fetchone() == (
                "f",
                True,
                "FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT",
            )
        connection.rollback()


def test_loan_source_fk_migration_fails_closed_on_a_wrong_same_named_fk() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(
        database_url.replace("postgresql+psycopg://", "postgresql://")
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version = '004_rv_loan_universe_source_fk'"
            )
            cursor.execute(
                "ALTER TABLE rv_loan_universes DROP CONSTRAINT rv_loan_universes_source_id_fkey"
            )
            cursor.execute(
                "ALTER TABLE rv_loan_universes ADD CONSTRAINT rv_loan_universes_source_id_fkey "
                "FOREIGN KEY (id) REFERENCES sources(id) ON DELETE RESTRICT NOT VALID"
            )
        with pytest.raises(psycopg.errors.DuplicateObject):
            apply_migrations(connection, root)
        connection.rollback()
