from __future__ import annotations

import os
from pathlib import Path

from caos.migrations import apply_migrations, migration_files


def migrate() -> None:
    root = Path(__file__).parent / "migrations"
    url = os.getenv("DATABASE_URL")
    if not url:
        names = ", ".join(path.name for path in migration_files(root))
        print(f"DATABASE_URL not set; migration plan available at migrations/: {names}")
        return
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise SystemExit("DATABASE_URL must be a PostgreSQL URL")
    import psycopg

    with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        applied = apply_migrations(connection, root)
        connection.commit()
    print("CAOS migrations current" + (f": {', '.join(applied)}" if applied else ""))


if __name__ == "__main__":
    migrate()
