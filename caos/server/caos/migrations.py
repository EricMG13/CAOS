from __future__ import annotations

from pathlib import Path
from typing import Any


def migration_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.glob("[0-9][0-9][0-9]_*.sql")))


def apply_migrations(connection: Any, root: Path) -> tuple[str, ...]:
    applied: list[str] = []
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        for path in migration_files(root):
            version = path.stem
            cursor.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,))
            if cursor.fetchone() is not None:
                continue
            cursor.execute(path.read_text(encoding="utf-8"))
            cursor.execute(
                "INSERT INTO schema_migrations(version) VALUES (%s) ON CONFLICT DO NOTHING",
                (version,),
            )
            applied.append(version)
    return tuple(applied)
