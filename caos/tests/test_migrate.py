from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from caos.config import Settings
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
