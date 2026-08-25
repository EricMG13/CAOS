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


def test_normalized_authority_migration_is_next_and_non_destructive() -> None:
    paths = migration_files(MIGRATIONS)

    assert paths[-1].name == "005_normalized_authority.sql"
    sql = paths[-1].read_text(encoding="utf-8").lower()
    assert "caos_state" not in sql
    assert "drop table" not in sql
    assert "delete from" not in sql
    assert "legacy" not in sql


def test_normalized_authority_migration_applies_once() -> None:
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
            assert first[-1] == "005_normalized_authority"
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
