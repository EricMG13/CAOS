from __future__ import annotations

import pytest

from migrate import migrate


def test_migrate_rejects_non_postgresql_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "not-a-postgres-url")

    with pytest.raises(SystemExit, match="DATABASE_URL must be a PostgreSQL URL"):
        migrate()
