from __future__ import annotations

import os
from pathlib import Path


def migrate() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set; migration plan available at migrations/001_baseline.sql")
        return
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise SystemExit("DATABASE_URL must be a PostgreSQL URL")
    import psycopg

    sql = (Path(__file__).parent / "migrations" / "001_baseline.sql").read_text()
    with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://")) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()
    print("CAOS baseline migration applied")


if __name__ == "__main__":
    migrate()
