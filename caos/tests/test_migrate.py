from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from caos.migrations import apply_migrations, migration_files
from migrate import migrate


MIGRATIONS = Path(__file__).parents[1] / "server" / "migrations"


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

    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schema_migrations WHERE version = '005_runs_planning_status'")
            cursor.execute("ALTER TABLE runs DROP CONSTRAINT runs_status_check")
            cursor.execute(
                "ALTER TABLE runs ADD CONSTRAINT runs_status_check "
                "CHECK (status IN ('queued', 'running', 'paused', 'succeeded', 'failed'))"
            )
        assert apply_migrations(connection, MIGRATIONS) == ("005_runs_planning_status",)
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

    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schema_migrations WHERE version = '004_rv_loan_universe_source_fk'")
            cursor.execute("ALTER TABLE rv_loan_universes DROP CONSTRAINT rv_loan_universes_source_id_fkey")
            cursor.execute(
                "CREATE TEMP TABLE migration_constraint_decoy("
                "id integer CONSTRAINT rv_loan_universes_source_id_fkey CHECK (id > 0))"
            )
        assert apply_migrations(connection, MIGRATIONS) == ("004_rv_loan_universe_source_fk",)
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

    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schema_migrations WHERE version = '004_rv_loan_universe_source_fk'")
            cursor.execute("ALTER TABLE rv_loan_universes DROP CONSTRAINT rv_loan_universes_source_id_fkey")
            cursor.execute(
                "ALTER TABLE rv_loan_universes ADD CONSTRAINT rv_loan_universes_source_id_fkey "
                "FOREIGN KEY (id) REFERENCES sources(id) ON DELETE RESTRICT NOT VALID"
            )
        with pytest.raises(psycopg.errors.DuplicateObject):
            apply_migrations(connection, MIGRATIONS)
        connection.rollback()


def test_run_generation_migration_is_next_and_non_destructive() -> None:
    paths = migration_files(MIGRATIONS)
    legacy_table = "caos_state"

    assert paths[-1].name == "006_run_canonical_generation.sql"
    sql = paths[-1].read_text(encoding="utf-8").lower()
    assert legacy_table not in sql
    assert "drop table" not in sql
    assert "delete from" not in sql
    assert "legacy" not in sql


def test_runtime_migrations_do_not_manage_removed_state_envelope() -> None:
    legacy_table = "caos_state"
    compatibility_migration = "004_rv_loan_universe_source_fk.sql"

    for path in migration_files(MIGRATIONS):
        if path.name == compatibility_migration:
            continue
        assert legacy_table not in path.read_text(encoding="utf-8").lower()


def test_run_generation_migration_applies_once() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is not set")

    import psycopg
    from psycopg import sql

    dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    schema = f"caos_migrate_{uuid.uuid4().hex}"
    with psycopg.connect(dsn) as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
                )
                cursor.execute(
                    sql.SQL("SET search_path TO {}, public").format(
                        sql.Identifier(schema)
                    )
                )
            first = apply_migrations(connection, MIGRATIONS)
            second = apply_migrations(connection, MIGRATIONS)
            connection.commit()
            assert first[-1] == "006_run_canonical_generation"
            assert second == ()
        finally:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(schema)
                    )
                )
            connection.commit()
