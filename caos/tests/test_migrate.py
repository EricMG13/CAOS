from __future__ import annotations

import os
from pathlib import Path

import pytest

from caos.migrations import apply_migrations
from migrate import migrate


def test_migrate_rejects_non_postgresql_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "not-a-postgres-url")

    with pytest.raises(SystemExit, match="DATABASE_URL must be a PostgreSQL URL"):
        migrate()


def test_forward_migration_adds_planning_to_an_existing_runs_constraint() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schema_migrations WHERE version = '005_runs_planning_status'")
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


def test_loan_source_fk_migration_ignores_a_same_named_constraint_on_another_table() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schema_migrations WHERE version = '004_rv_loan_universe_source_fk'")
            cursor.execute("ALTER TABLE rv_loan_universes DROP CONSTRAINT rv_loan_universes_source_id_fkey")
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
            assert cursor.fetchone() == ("f", True, "FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT")
        connection.rollback()


def test_loan_source_fk_migration_fails_closed_on_a_wrong_same_named_fk() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable migration proof")
    import psycopg

    root = Path(__file__).parents[1] / "server" / "migrations"
    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schema_migrations WHERE version = '004_rv_loan_universe_source_fk'")
            cursor.execute("ALTER TABLE rv_loan_universes DROP CONSTRAINT rv_loan_universes_source_id_fkey")
            cursor.execute(
                "ALTER TABLE rv_loan_universes ADD CONSTRAINT rv_loan_universes_source_id_fkey "
                "FOREIGN KEY (id) REFERENCES sources(id) ON DELETE RESTRICT NOT VALID"
            )
        with pytest.raises(psycopg.errors.DuplicateObject):
            apply_migrations(connection, root)
        connection.rollback()
