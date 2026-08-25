from __future__ import annotations

import os
from pathlib import Path

import pytest

from caos.migrations import apply_migrations
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
