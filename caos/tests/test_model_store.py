from __future__ import annotations

from pathlib import Path


from caos.migrations import apply_migrations, migration_files


def test_migration_runner_applies_ordered_files_once(tmp_path: Path) -> None:
    (tmp_path / "002_second.sql").write_text("SELECT 2", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1", encoding="utf-8")
    (tmp_path / "notes.sql").write_text("SELECT 0", encoding="utf-8")

    class Cursor:
        def __init__(self) -> None:
            self.applied: set[str] = set()
            self.result: tuple[int] | None = None

        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, statement: str, parameters: tuple[str] | None = None) -> None:
            if statement.startswith("SELECT 1 FROM schema_migrations"):
                self.result = (
                    (1,) if parameters and parameters[0] in self.applied else None
                )
            elif statement.startswith("INSERT INTO schema_migrations") and parameters:
                self.applied.add(parameters[0])

        def fetchone(self) -> tuple[int] | None:
            return self.result

    class Connection:
        cursor_value = Cursor()

        def cursor(self) -> Cursor:
            return self.cursor_value

    connection = Connection()
    assert [path.name for path in migration_files(tmp_path)] == [
        "001_first.sql",
        "002_second.sql",
    ]
    assert apply_migrations(connection, tmp_path) == ("001_first", "002_second")
    assert apply_migrations(connection, tmp_path) == ()


def test_model_job_actor_migration_backfills_creator_and_enforces_not_null() -> None:
    migration = (
        Path(__file__).parents[1]
        / "server"
        / "migrations"
        / "004_model_build_job_actor.sql"
    ).read_text(encoding="utf-8")

    assert "ADD COLUMN actor text" in migration
    assert "SET actor = build.created_by" in migration
    assert "FROM model_builds AS build" in migration
    assert "WHERE job.build_id = build.id" in migration
    assert "ALTER COLUMN actor SET NOT NULL" in migration
    assert "caos_state" not in migration
    assert (
        migration.index("ADD COLUMN actor text")
        < migration.index("SET actor = build.created_by")
        < migration.index("ALTER COLUMN actor SET NOT NULL")
    )


def test_model_revision_migration_is_append_only_with_separate_head_and_export() -> None:
    migration = (
        Path(__file__).parents[1]
        / "server"
        / "migrations"
        / "007_model_revisions.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS model_revisions" in migration
    assert "CREATE TABLE IF NOT EXISTS model_revision_heads" in migration
    assert "CREATE TABLE IF NOT EXISTS model_revision_exports" in migration
    assert "UNIQUE (case_id, revision_number)" in migration
    assert "parent_revision_id text REFERENCES model_revisions(id) ON DELETE RESTRICT" in migration
    assert "build_id text NOT NULL REFERENCES model_builds(id) ON DELETE RESTRICT" in migration
    assert "active boolean" not in migration.lower()
    assert "UPDATE model_revisions" not in migration
    assert "ADD COLUMN authority_order bigint" in migration
    assert "row_number() OVER (ORDER BY queued_at, id)" in migration
    assert "ADD GENERATED ALWAYS AS IDENTITY" in migration
    assert "max_authority_order + 1" in migration
    assert "ctid" not in migration.lower()
    assert "xmin" not in migration.lower()
    assert "model_builds_authority_order_idx" in migration
