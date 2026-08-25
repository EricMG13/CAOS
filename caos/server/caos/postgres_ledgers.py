"""Normalized PostgreSQL implementations of the four ledger ports."""

from __future__ import annotations

import copy
import hashlib
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import clean_json, digest
from .migrations import apply_migrations
from .store import (
    MAX_ACTIVE_JOBS,
    JobFencedError,
    _model_job_key,
    _remaining_finalization_seconds,
    _validated_model_result,
    now_iso,
)


Record = dict[str, Any]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return value


class _Database:
    def __init__(self, database_url: str, lease_seconds: float) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is required for normalized PostgreSQL ledgers"
            ) from exc
        self.psycopg = psycopg
        self.dict_row = dict_row
        self.jsonb = Jsonb
        self.dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
        self.lease_seconds = lease_seconds
        with self.connection() as connection:
            apply_migrations(connection, Path(__file__).parent.parent / "migrations")

    @contextmanager
    def connection(self) -> Iterator[Any]:
        with self.psycopg.connect(self.dsn, row_factory=self.dict_row) as connection:
            yield connection

    def j(self, value: Any) -> Any:
        return self.jsonb(copy.deepcopy(value))


class _Adapter:
    def __init__(self, database: _Database) -> None:
        self._db = database

    def _audit(self, cursor: Any, action: str, actor: str, **details: Any) -> None:
        case_id = details.pop("case_id", None)
        cursor.execute(
            "INSERT INTO audit_events(event_id, actor, action, case_id, payload, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (_id("aud"), actor, action, case_id, self._db.j(details), now_iso()),
        )


def _source_record(row: Record, *, public: bool = True) -> Record:
    if row.get("record"):
        record = copy.deepcopy(row["record"])
        record.update(withdrawn=row["withdrawn"])
        if row.get("withdrawn_at") is not None:
            record["withdrawn_at"] = _iso(row["withdrawn_at"])
        if public:
            record.pop("vault_path", None)
        return record
    record: Record = {
        "id": row["id"],
        "case_id": row["case_id"],
        "filename": row["filename"],
        "media_type": row["media_type"],
        "bytes": row["bytes"],
        "sha256": row["sha256"].strip(),
        "blocks": copy.deepcopy(row["blocks"]),
        "created_by": row["created_by"],
        "created_at": _iso(row["created_at"]),
        "withdrawn": row["withdrawn"],
    }
    if not public:
        record["vault_path"] = row["vault_path"]
    for key in ("withdrawn_at", "source_kind", "origin_family", "authority_class"):
        if row.get(key) is not None:
            record[key] = _iso(row[key])
    return record


def _source_set_record(row: Record) -> Record:
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "version": row["version"],
        "source_ids": copy.deepcopy(row["source_ids"]),
        "created_by": row["created_by"],
        "created_at": _iso(row["created_at"]),
    }


class _PostgresSourceCatalog(_Adapter):
    def _current_set(self, cursor: Any, case_id: str) -> Record | None:
        cursor.execute(
            "SELECT source_set.* FROM cases AS c "
            "LEFT JOIN source_sets AS source_set ON source_set.id=c.current_source_set_id "
            "WHERE c.id=%s",
            (case_id,),
        )
        row = cursor.fetchone()
        return _source_set_record(row) if row and row.get("id") else None

    def _append_source_set(
        self, cursor: Any, case_id: str, actor: str, source_ids: list[str]
    ) -> Record:
        cursor.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM source_sets "
            "WHERE case_id=%s",
            (case_id,),
        )
        version = cursor.fetchone()["version"] + 1
        source_set = {
            "id": _id("set"),
            "case_id": case_id,
            "version": version,
            "source_ids": list(source_ids),
            "created_by": actor,
            "created_at": now_iso(),
        }
        cursor.execute(
            "INSERT INTO source_sets(id, case_id, version, source_ids, created_by, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                source_set["id"],
                case_id,
                version,
                self._db.j(source_ids),
                actor,
                source_set["created_at"],
            ),
        )
        cursor.execute(
            "UPDATE cases SET current_source_set_id=%s WHERE id=%s",
            (source_set["id"], case_id),
        )
        return source_set

    def _insert_source(
        self, cursor: Any, source: Record, actor: str, source_id: str
    ) -> Record:
        saved = copy.deepcopy(source)
        saved.update(
            id=source_id,
            created_by=saved.get("created_by", actor),
            created_at=saved.get("created_at", now_iso()),
            withdrawn=saved.get("withdrawn", False),
        )
        cursor.execute(
            "INSERT INTO sources(id, case_id, filename, media_type, sha256, vault_path, "
            "bytes, blocks, withdrawn, withdrawn_at, source_kind, origin_family, "
            "authority_class, created_by, created_at, record) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                source_id,
                saved["case_id"],
                saved["filename"],
                saved["media_type"],
                saved["sha256"],
                saved.get("vault_path"),
                saved["bytes"],
                self._db.j(saved.get("blocks", [])),
                saved["withdrawn"],
                saved.get("withdrawn_at"),
                saved.get("source_kind"),
                saved.get("origin_family"),
                saved.get("authority_class"),
                saved["created_by"],
                saved["created_at"],
                self._db.j(saved),
            ),
        )
        return saved

    def ingest(self, source: Record, actor: str) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM cases WHERE id=%s FOR UPDATE", (source["case_id"],)
            )
            if cursor.fetchone() is None:
                raise ValueError("CASE_NOT_FOUND")
            cursor.execute(
                "SELECT 1 FROM sources WHERE case_id=%s AND sha256=%s "
                "AND withdrawn=false",
                (source["case_id"], source["sha256"]),
            )
            if cursor.fetchone() is not None:
                raise ValueError("source content already active")
            current = self._current_set(cursor, source["case_id"])
            saved = self._insert_source(cursor, source, actor, _id("src"))
            source_ids = list(current["source_ids"] if current else [])
            source_ids.append(saved["id"])
            source_set = self._append_source_set(
                cursor, saved["case_id"], actor, source_ids
            )
            self._audit(
                cursor,
                "source.ingested",
                actor,
                case_id=saved["case_id"],
                source_id=saved["id"],
                sha256=saved.get("sha256"),
            )
            saved.pop("vault_path", None)
            return {**saved, "source_set": source_set}

    def _ingest_promoted_note(
        self, cursor: Any, note_id: str, case_id: str, actor: str
    ) -> Record:
        cursor.execute(
            "SELECT * FROM notes WHERE id=%s AND case_id=%s FOR UPDATE",
            (note_id, case_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError("NOTE_NOT_FOUND")
        if row["author"] != actor:
            raise PermissionError("only note author can promote")
        if row["promoted"] and row["promoted_source_id"]:
            cursor.execute(
                "SELECT withdrawn FROM sources WHERE id=%s",
                (row["promoted_source_id"],),
            )
            source_row = cursor.fetchone()
            if source_row and not source_row["withdrawn"]:
                return _note_record(row)

        cursor.execute("SELECT id FROM cases WHERE id=%s FOR UPDATE", (case_id,))
        body = row["body"]
        source_digest = hashlib.sha256(body.encode()).hexdigest()
        cursor.execute(
            "SELECT 1 FROM sources WHERE case_id=%s AND sha256=%s AND withdrawn=false",
            (case_id, source_digest),
        )
        if cursor.fetchone() is not None:
            raise ValueError("DUPLICATE_SOURCE")
        source_id = _id("src-note")
        source = {
            "case_id": case_id,
            "filename": f"analyst-note-{note_id}.md",
            "media_type": "text/markdown",
            "bytes": len(body.encode()),
            "sha256": source_digest,
            "vault_path": None,
            "blocks": [
                {
                    "block_id": "b00001",
                    "locator": {"note_id": note_id},
                    "text": body,
                    "extractor_version": "analyst-note-v1",
                    "confidence": "HIGH",
                    "untrusted_data": True,
                }
            ],
            "created_by": actor,
            "created_at": now_iso(),
            "withdrawn": False,
            "source_kind": "analyst_note",
        }
        try:
            self._insert_source(cursor, source, actor, source_id)
        except self._db.psycopg.errors.UniqueViolation as exc:
            raise ValueError("DUPLICATE_SOURCE") from exc
        current = self._current_set(cursor, case_id)
        source_ids = list(current["source_ids"] if current else [])
        source_ids.append(source_id)
        self._append_source_set(cursor, case_id, actor, source_ids)
        cursor.execute(
            "UPDATE notes SET promoted=true, promoted_source_id=%s WHERE id=%s "
            "RETURNING *",
            (source_id, note_id),
        )
        promoted = _note_record(cursor.fetchone())
        self._audit(
            cursor,
            "note.promoted",
            actor,
            case_id=case_id,
            note_id=note_id,
            source_id=source_id,
        )
        return promoted

    def ingest_promoted_note(self, note: Record, actor: str) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            return self._ingest_promoted_note(
                cursor, note.get("id"), note.get("case_id"), actor
            )

    def withdraw(self, case_id: str, source_id: str, actor: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM cases WHERE id=%s FOR UPDATE", (case_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                "SELECT * FROM sources WHERE id=%s AND case_id=%s FOR UPDATE",
                (source_id, case_id),
            )
            row = cursor.fetchone()
            if row is None or row["withdrawn"]:
                return None
            withdrawn_at = now_iso()
            stored = _source_record(row, public=False)
            stored.update(withdrawn=True, withdrawn_at=withdrawn_at)
            cursor.execute(
                "UPDATE sources SET withdrawn=true, withdrawn_at=%s, record=%s WHERE id=%s "
                "RETURNING *",
                (withdrawn_at, self._db.j(stored), source_id),
            )
            withdrawn = _source_record(cursor.fetchone())
            current = self._current_set(cursor, case_id)
            if current:
                self._append_source_set(
                    cursor,
                    case_id,
                    actor,
                    [item for item in current["source_ids"] if item != source_id],
                )
            cursor.execute(
                "UPDATE assumptions SET stale=true, status='STALE' "
                "WHERE case_id=%s AND evidence_ids @> %s",
                (case_id, self._db.j([source_id])),
            )
            cursor.execute(
                "SELECT id, record FROM rv_loan_universes "
                "WHERE case_id=%s AND source_id=%s AND status='ACTIVE' FOR UPDATE",
                (case_id, source_id),
            )
            universe = cursor.fetchone()
            if universe:
                record = copy.deepcopy(universe["record"])
                record.update(status="WITHDRAWN", withdrawn_at=withdrawn_at)
                cursor.execute(
                    "UPDATE rv_loan_universes SET status='WITHDRAWN', withdrawn_at=%s, "
                    "record=%s WHERE id=%s",
                    (withdrawn_at, self._db.j(record), universe["id"]),
                )
                self._audit(
                    cursor,
                    "rv.loan_universe.withdrawn",
                    actor,
                    case_id=case_id,
                    source_id=source_id,
                    universe_id=universe["id"],
                )
            self._audit(
                cursor,
                "source.withdrawn",
                actor,
                case_id=case_id,
                source_id=source_id,
            )
            return withdrawn

    def list_sources(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM sources WHERE case_id=%s AND withdrawn=false "
                "ORDER BY created_at, id",
                (case_id,),
            )
            return [_source_record(row) for row in cursor.fetchall()]

    def get_source(self, source_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM sources WHERE id=%s", (source_id,))
            row = cursor.fetchone()
            return _source_record(row) if row else None

    def current_source_set(self, case_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            return self._current_set(cursor, case_id)

    def source_set(self, source_set_id: str | None) -> Record | None:
        if not source_set_id:
            return None
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM source_sets WHERE id=%s", (source_set_id,))
            row = cursor.fetchone()
            return _source_set_record(row) if row else None

    def read_pinned_evidence(
        self,
        case_id: str,
        source_set_id: str,
        source_id: str,
        block_ids: list[str],
    ) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM source_sets WHERE id=%s", (source_set_id,))
            source_set = cursor.fetchone()
            cursor.execute("SELECT * FROM sources WHERE id=%s", (source_id,))
            source = cursor.fetchone()
            if (
                not source_set
                or source_set["case_id"] != case_id
                or source_id not in source_set["source_ids"]
                or not source
                or source["case_id"] != case_id
                or source["withdrawn"]
            ):
                raise ValueError("AGENT_AUTHORITY_MISMATCH")
            blocks = {block.get("block_id"): block for block in source["blocks"]}
            if any(block_id not in blocks for block_id in block_ids):
                raise ValueError("AGENT_OUTPUT_INVALID")
            return [
                {
                    "source_id": source_id,
                    "source_digest": source["sha256"].strip(),
                    "origin_family": source.get("origin_family")
                    or source["sha256"].strip(),
                    "authority_class": source.get("authority_class") or "unclassified",
                    "block_id": block_id,
                    "locator": copy.deepcopy(blocks[block_id].get("locator")),
                    "extractor_version": blocks[block_id].get("extractor_version"),
                    "confidence": blocks[block_id].get("confidence"),
                    "text": blocks[block_id].get("text"),
                }
                for block_id in block_ids
            ]

    def find_loan_universe_import(
        self,
        case_id: str,
        source_sha256: str,
        template_version: str,
        importer_version: str,
    ) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT record FROM rv_loan_universes WHERE case_id=%s "
                "AND source_sha256=%s AND template_version=%s AND importer_version=%s",
                (case_id, source_sha256, template_version, importer_version),
            )
            row = cursor.fetchone()
            return copy.deepcopy(row["record"]) if row else None

    def save_loan_universe_import(
        self, record: Record, rows: list[Record], actor: str
    ) -> tuple[Record, bool]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM cases WHERE id=%s FOR UPDATE", (record["case_id"],)
            )
            cursor.execute(
                "SELECT record FROM rv_loan_universes WHERE case_id=%s "
                "AND source_sha256=%s AND template_version=%s AND importer_version=%s",
                (
                    record["case_id"],
                    record["source_sha256"],
                    record["template_version"],
                    record["importer_version"],
                ),
            )
            existing = cursor.fetchone()
            if existing:
                return copy.deepcopy(existing["record"]), False
            if record.get("status") not in {"ACTIVE", "REJECTED"}:
                raise ValueError("RV_UNIVERSE_STATUS_INVALID")
            cursor.execute(
                "SELECT 1 FROM sources WHERE id=%s AND case_id=%s AND withdrawn=false",
                (record.get("source_id"), record.get("case_id")),
            )
            if cursor.fetchone() is None:
                raise ValueError("RV_SOURCE_NOT_ACTIVE")
            if record["status"] == "ACTIVE":
                if record.get("row_count") != len(rows) or len(
                    {row.get("instrument_key") for row in rows}
                ) != len(rows):
                    raise ValueError("RV_UNIVERSE_ROWS_INVALID")
            elif rows:
                raise ValueError("RV_REJECTED_UNIVERSE_HAS_ROWS")

            saved = copy.deepcopy(record)
            saved.update(
                id=_id("rvloan"),
                created_at=saved.get("created_at", now_iso()),
                created_by=saved.get("created_by", actor),
                activated_at=None,
                superseded_at=None,
                withdrawn_at=None,
            )
            if saved["status"] == "ACTIVE":
                cursor.execute(
                    "SELECT COALESCE(MAX(version), 0) AS version FROM rv_loan_universes "
                    "WHERE case_id=%s",
                    (saved["case_id"],),
                )
                saved["version"] = cursor.fetchone()["version"] + 1
                saved["activated_at"] = now_iso()
                cursor.execute(
                    "SELECT id, record FROM rv_loan_universes WHERE case_id=%s "
                    "AND status='ACTIVE' FOR UPDATE",
                    (saved["case_id"],),
                )
                previous = cursor.fetchone()
                if previous:
                    prior = copy.deepcopy(previous["record"])
                    prior.update(
                        status="SUPERSEDED", superseded_at=saved["activated_at"]
                    )
                    cursor.execute(
                        "UPDATE rv_loan_universes SET status='SUPERSEDED', "
                        "superseded_at=%s, record=%s WHERE id=%s",
                        (
                            saved["activated_at"],
                            self._db.j(prior),
                            previous["id"],
                        ),
                    )
                action = "rv.loan_universe.activated"
            else:
                saved["version"] = None
                action = "rv.loan_universe.rejected"
            cursor.execute(
                "INSERT INTO rv_loan_universes(id, case_id, source_id, source_sha256, "
                "workbook_date, template_version, importer_version, universe_digest, "
                "row_count, version, status, record, created_by, created_at, activated_at, "
                "superseded_at, withdrawn_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    saved["id"],
                    saved["case_id"],
                    saved["source_id"],
                    saved["source_sha256"],
                    saved.get("workbook_date"),
                    saved["template_version"],
                    saved["importer_version"],
                    saved.get("universe_digest"),
                    saved.get("row_count", 0),
                    saved.get("version"),
                    saved["status"],
                    self._db.j(saved),
                    saved["created_by"],
                    saved["created_at"],
                    saved.get("activated_at"),
                    saved.get("superseded_at"),
                    saved.get("withdrawn_at"),
                ),
            )
            for position, row in enumerate(rows):
                cursor.execute(
                    "INSERT INTO rv_loan_rows(universe_id, instrument_key, record, position) "
                    "VALUES (%s, %s, %s, %s)",
                    (
                        saved["id"],
                        row["instrument_key"],
                        self._db.j(row),
                        position,
                    ),
                )
            self._audit(
                cursor,
                action,
                actor,
                case_id=saved["case_id"],
                source_id=saved["source_id"],
                universe_id=saved["id"],
            )
            return saved, True

    def active_loan_universe(
        self, case_id: str, *, include_rows: bool = True
    ) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, record FROM rv_loan_universes WHERE case_id=%s "
                "AND status='ACTIVE'",
                (case_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            record = copy.deepcopy(row["record"])
            if include_rows:
                cursor.execute(
                    "SELECT record FROM rv_loan_rows WHERE universe_id=%s "
                    "ORDER BY position",
                    (row["id"],),
                )
                record["rows"] = [
                    copy.deepcopy(item["record"]) for item in cursor.fetchall()
                ]
            return record


def _note_record(row: Record) -> Record:
    note = {
        "id": row["id"],
        "case_id": row["case_id"],
        "author": row["author"],
        "body": row["body"],
        "promoted": row["promoted"],
        "created_at": _iso(row["created_at"]),
    }
    if row.get("promoted_source_id") is not None:
        note["promoted_source_id"] = row["promoted_source_id"]
    return note


def _case_record(cursor: Any, row: Record) -> Record:
    cursor.execute(
        "SELECT subject, role FROM case_members WHERE case_id=%s ORDER BY subject",
        (row["id"],),
    )
    return {
        "id": row["id"],
        "name": row["name"],
        "issuer": row["issuer"],
        "sector": row["sector"],
        "created_by": row["created_by"],
        "created_at": _iso(row["created_at"]),
        "members": {item["subject"]: item["role"] for item in cursor.fetchall()},
        "accepted_snapshot_id": row.get("accepted_snapshot_id"),
        "visible_snapshot_id": row.get("visible_snapshot_id"),
        "current_execution_id": row.get("current_execution_id"),
    }


def _node_record(row: Record) -> Record:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "case_id": row["case_id"],
        "module_id": row["module_id"],
        "dependencies": copy.deepcopy(row["dependencies"]),
        "stage": row["stage"],
        "status": row["status"],
        "attempt": row["attempt"],
        "artifact_id": row.get("artifact_id"),
        "error": copy.deepcopy(row.get("error")),
    }


def _event_record(row: Record) -> Record:
    return {
        "id": row["sequence"],
        "event": row["event"],
        "at": _iso(row["created_at"]),
        "data": copy.deepcopy(row["data"]),
    }


def _run_record(cursor: Any, row: Record) -> Record:
    cursor.execute(
        "SELECT * FROM workflow_nodes WHERE run_id=%s ORDER BY position", (row["id"],)
    )
    nodes = [_node_record(item) for item in cursor.fetchall()]
    cursor.execute(
        "SELECT * FROM workflow_events WHERE run_id=%s ORDER BY sequence", (row["id"],)
    )
    events = [_event_record(item) for item in cursor.fetchall()]
    record = {
        "id": row["id"],
        "case_id": row["case_id"],
        "created_by": row["created_by"],
        "created_at": _iso(row["created_at"]),
        "status": row["status"],
        "plan": copy.deepcopy(row["plan"]),
        "node_ids": [node["id"] for node in nodes],
        "current_node_id": row.get("current_node_id"),
        "accepted_snapshot_id": row.get("accepted_snapshot_id"),
        "upgraded_from_run_id": row.get("upgraded_from_run_id"),
        "error": copy.deepcopy(row.get("error")),
        "nodes": nodes,
        "events": events,
    }
    if row.get("research") is not None:
        record["research"] = copy.deepcopy(row["research"])
    return record


def _artifact_record(row: Record) -> Record:
    if row.get("record"):
        return copy.deepcopy(row["record"])
    record = {
        "id": row["id"],
        "run_id": row["run_id"],
        "module_id": row["module_id"],
        "digest": row["digest"].strip(),
        "payload": copy.deepcopy(row["payload"]),
        "markdown": row["markdown"],
        "input_fingerprint": row["input_fingerprint"],
        "created_at": _iso(row["created_at"]),
    }
    if row.get("case_id") is not None:
        record["case_id"] = row["case_id"]
    if row.get("created_by") is not None:
        record["created_by"] = row["created_by"]
    return record


def _snapshot_record(row: Record) -> Record:
    if row.get("record"):
        return copy.deepcopy(row["record"])
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "run_id": row["run_id"],
        "source_set_id": row["source_set_id"],
        "source_set_version": row["source_set_version"],
        "artifacts": copy.deepcopy(row["artifact_refs"]),
        "accepted_at": _iso(row["accepted_at"]),
        "digest": row["digest"].strip(),
        "previous_snapshot_id": row.get("previous_snapshot_id"),
    }


class _PostgresRunLedger(_Adapter):
    def create_case(self, name: str, issuer: str, sector: str, actor: str) -> Record:
        case = {
            "id": _id("case"),
            "name": name,
            "issuer": issuer,
            "sector": sector,
            "created_by": actor,
            "created_at": now_iso(),
            "members": {actor: "ANALYST"},
            "accepted_snapshot_id": None,
            "visible_snapshot_id": None,
            "current_execution_id": None,
        }
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO cases(id, name, issuer, sector, created_by, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (case["id"], name, issuer, sector, actor, case["created_at"]),
            )
            cursor.execute(
                "INSERT INTO case_members(case_id, subject, role) VALUES (%s, %s, 'ANALYST')",
                (case["id"], actor),
            )
            self._audit(cursor, "case.created", actor, case_id=case["id"])
        return case

    def list_cases(self, actor: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT c.* FROM cases AS c JOIN case_members AS member "
                "ON member.case_id=c.id WHERE member.subject=%s ORDER BY c.created_at, c.id",
                (actor,),
            )
            return [_case_record(cursor, row) for row in cursor.fetchall()]

    def get_case(self, case_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM cases WHERE id=%s", (case_id,))
            row = cursor.fetchone()
            return _case_record(cursor, row) if row else None

    def is_member(
        self, case_id: str, actor: str, roles: set[str] | None = None
    ) -> bool:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT role FROM case_members WHERE case_id=%s AND subject=%s",
                (case_id, actor),
            )
            row = cursor.fetchone()
            return bool(row and (roles is None or row["role"] in roles))

    def add_member(
        self,
        case_id: str,
        actor: str,
        member: str,
        role: str,
        actor_role: str | None = None,
    ) -> bool:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM cases WHERE id=%s FOR UPDATE", (case_id,))
            if cursor.fetchone() is None:
                return False
            cursor.execute(
                "SELECT role FROM case_members WHERE case_id=%s AND subject=%s",
                (case_id, actor),
            )
            row = cursor.fetchone()
            if actor_role != "ADMIN" and (
                not row or row["role"] not in {"ADMIN", "APPROVER"}
            ):
                return False
            cursor.execute(
                "INSERT INTO case_members(case_id, subject, role) VALUES (%s, %s, %s) "
                "ON CONFLICT (case_id, subject) DO UPDATE SET role=EXCLUDED.role",
                (case_id, member, role),
            )
            self._audit(
                cursor,
                "case.member_added",
                actor,
                case_id=case_id,
                member=member,
                role=role,
            )
            return True

    def create_run_with_nodes(
        self,
        case_id: str,
        actor: str,
        plan: Record,
        nodes: list[Record],
        upgraded_from_run_id: str | None = None,
    ) -> Record:
        run_id = _id("run")
        created_at = now_iso()
        node_records = [
            {
                "id": _id("node"),
                "run_id": run_id,
                "case_id": case_id,
                "module_id": node["module_id"],
                "dependencies": list(node.get("dependencies", [])),
                "stage": node["stage"],
                "status": "pending",
                "attempt": 0,
                "artifact_id": None,
                "error": None,
            }
            for node in nodes
        ]
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM cases WHERE id=%s FOR UPDATE", (case_id,))
            if cursor.fetchone() is None:
                raise ValueError("CASE_NOT_FOUND")
            cursor.execute(
                "INSERT INTO runs(id, case_id, status, plan, current_node_id, "
                "accepted_snapshot_id, upgraded_from_run_id, created_by, created_at, error) "
                "VALUES (%s, %s, 'queued', %s, NULL, NULL, %s, %s, %s, NULL)",
                (
                    run_id,
                    case_id,
                    self._db.j(plan),
                    upgraded_from_run_id,
                    actor,
                    created_at,
                ),
            )
            for position, node in enumerate(node_records):
                cursor.execute(
                    "INSERT INTO workflow_nodes(id, run_id, case_id, module_id, "
                    "dependencies, stage, position, status, attempt) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', 0)",
                    (
                        node["id"],
                        run_id,
                        case_id,
                        node["module_id"],
                        self._db.j(node["dependencies"]),
                        node["stage"],
                        position,
                    ),
                )
            cursor.execute(
                "INSERT INTO jobs(run_id, state, budget_reserved) VALUES (%s, 'queued', 0)",
                (run_id,),
            )
            cursor.execute(
                "UPDATE cases SET current_execution_id=%s WHERE id=%s",
                (run_id, case_id),
            )
            self._audit(cursor, "run.created", actor, case_id=case_id, run_id=run_id)
            cursor.execute("SELECT * FROM runs WHERE id=%s", (run_id,))
            return _run_record(cursor, cursor.fetchone())

    def list_runs(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM runs WHERE case_id=%s ORDER BY created_at, id",
                (case_id,),
            )
            return [_run_record(cursor, row) for row in cursor.fetchall()]

    def get_run(self, run_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM runs WHERE id=%s", (run_id,))
            row = cursor.fetchone()
            return _run_record(cursor, row) if row else None

    def latest_run(self, case_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM runs WHERE case_id=%s ORDER BY created_at DESC, id DESC LIMIT 1",
                (case_id,),
            )
            row = cursor.fetchone()
            return _run_record(cursor, row) if row else None

    def pending_runs(self) -> list[tuple[str, str]]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, created_by FROM runs WHERE status IN ('queued', 'running') "
                "ORDER BY created_at, id"
            )
            return [(row["id"], row["created_by"]) for row in cursor.fetchall()]

    def claim(self, run_id: str, worker: str) -> str | None:
        token = _id("attempt")
        lease = self._db.lease_seconds
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext('caos:workflow-budget'))"
            )
            cursor.execute(
                "SELECT (SELECT count(*) FROM jobs WHERE state='claimed' AND lease_until > now()) + "
                "(SELECT count(*) FROM model_build_jobs WHERE state='claimed' AND lease_until > now()) AS active"
            )
            if cursor.fetchone()["active"] >= MAX_ACTIVE_JOBS:
                return None
            cursor.execute(
                "SELECT job.id FROM jobs AS job JOIN runs AS run ON run.id=job.run_id "
                "WHERE job.run_id=%s AND run.status IN ('queued', 'running') AND "
                "(job.state='queued' OR (job.state='claimed' AND job.lease_until <= now())) "
                "FOR UPDATE OF job SKIP LOCKED",
                (run_id,),
            )
            job = cursor.fetchone()
            if not job:
                return None
            cursor.execute(
                "UPDATE jobs SET state='claimed', worker_id=%s, attempt_token=%s, "
                "lease_until=now() + (%s * interval '1 second'), budget_reserved=1 "
                "WHERE id=%s AND (state='queued' OR (state='claimed' AND lease_until <= now())) "
                "RETURNING id",
                (worker, token, lease, job["id"]),
            )
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                "UPDATE workflow_nodes SET status='pending', artifact_id=NULL, error=NULL, "
                "last_attempt_token=%s WHERE run_id=%s AND status='running'",
                (token, run_id),
            )
            cursor.execute(
                "UPDATE runs SET current_node_id=NULL WHERE id=%s", (run_id,)
            )
            return token

    def renew(self, run_id: str, attempt_token: str) -> bool:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE jobs SET lease_until=now() + (%s * interval '1 second') "
                "WHERE run_id=%s AND state='claimed' AND attempt_token=%s "
                "AND lease_until > now() RETURNING id",
                (self._db.lease_seconds, run_id, attempt_token),
            )
            return cursor.fetchone() is not None

    def is_current(self, run_id: str, attempt_token: str) -> bool:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM jobs WHERE run_id=%s AND state='claimed' "
                "AND attempt_token=%s AND lease_until > now()",
                (run_id, attempt_token),
            )
            return cursor.fetchone() is not None

    def _assert_fenced(self, cursor: Any, run_id: str, attempt_token: str) -> None:
        cursor.execute(
            "SELECT id FROM jobs WHERE run_id=%s AND state='claimed' "
            "AND attempt_token=%s AND lease_until > now() FOR UPDATE",
            (run_id, attempt_token),
        )
        if cursor.fetchone() is None:
            raise JobFencedError("stale workflow attempt")

    def finish(self, run_id: str, attempt_token: str) -> None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE jobs SET state='succeeded', lease_until=NULL, budget_reserved=0 "
                "WHERE run_id=%s AND state='claimed' AND attempt_token=%s "
                "AND lease_until > now()",
                (run_id, attempt_token),
            )

    def update_run_fenced(
        self, run_id: str, attempt_token: str, **changes: Any
    ) -> None:
        columns = {
            "status": "status",
            "current_node_id": "current_node_id",
            "error": "error",
            "research": "research",
        }
        if any(key not in columns for key in changes):
            raise ValueError("unsupported run update")
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._assert_fenced(cursor, run_id, attempt_token)
            for key, value in changes.items():
                if key in {"error", "research"}:
                    value = self._db.j(value) if value is not None else None
                cursor.execute(
                    f"UPDATE runs SET {columns[key]}=%s WHERE id=%s",
                    (value, run_id),
                )
            if changes.get("status") == "succeeded":
                cursor.execute(
                    "UPDATE runs SET final_attempt_token=%s WHERE id=%s",
                    (attempt_token, run_id),
                )

    def update_node_fenced(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        **changes: Any,
    ) -> None:
        columns = {
            "status": "status",
            "attempt": "attempt",
            "artifact_id": "artifact_id",
            "error": "error",
        }
        if any(key not in columns for key in changes):
            raise ValueError("unsupported node update")
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._assert_fenced(cursor, run_id, attempt_token)
            cursor.execute(
                "SELECT run_id FROM workflow_nodes WHERE id=%s FOR UPDATE", (node_id,)
            )
            row = cursor.fetchone()
            if not row or row["run_id"] != run_id:
                raise JobFencedError("node does not belong to run")
            for key, value in changes.items():
                if key == "error":
                    value = self._db.j(value) if value is not None else None
                cursor.execute(
                    f"UPDATE workflow_nodes SET {columns[key]}=%s, last_attempt_token=%s "
                    "WHERE id=%s",
                    (value, attempt_token, node_id),
                )

    def pause_research_plan(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        research: Record,
    ) -> None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._assert_fenced(cursor, run_id, attempt_token)
            cursor.execute(
                "UPDATE workflow_nodes SET status='pending', error=NULL, "
                "last_attempt_token=%s WHERE id=%s AND run_id=%s RETURNING id",
                (attempt_token, node_id, run_id),
            )
            if cursor.fetchone() is None:
                raise JobFencedError("node does not belong to run")
            cursor.execute(
                "UPDATE runs SET status='paused', current_node_id=NULL, error=%s, research=%s "
                "WHERE id=%s",
                (
                    self._db.j(
                        {
                            "code": "PLAN_APPROVAL_REQUIRED",
                            "message": "Approve the proposed research plan before execution.",
                        }
                    ),
                    self._db.j(research),
                    run_id,
                ),
            )

    def approve_research_plan(self, run_id: str, actor: str, plan_hash: str) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM runs WHERE id=%s FOR UPDATE", (run_id,))
            run = cursor.fetchone()
            if not run:
                raise ValueError("RUN_NOT_FOUND")
            research = copy.deepcopy(run.get("research"))
            if (
                not research
                or research.get("phase") != "awaiting_approval"
                or (run.get("error") or {}).get("code") != "PLAN_APPROVAL_REQUIRED"
            ):
                raise ValueError("PLAN_APPROVAL_NOT_AVAILABLE")
            pending_hash = research.get("proposed_plan_hash")
            if (
                pending_hash != f"sha256:{digest(research.get('proposed_plan'))}"
                or plan_hash != pending_hash
            ):
                raise ValueError("PLAN_HASH_MISMATCH")
            cursor.execute(
                "SELECT source_set.* FROM cases AS c JOIN source_sets AS source_set "
                "ON source_set.id=c.current_source_set_id WHERE c.id=%s",
                (run["case_id"],),
            )
            current = cursor.fetchone()
            pinned = research["proposed_plan"]["source_set"]
            if not current or (current["id"], current["version"]) != (
                pinned["id"],
                pinned["version"],
            ):
                raise ValueError("SOURCE_SET_CHANGED")
            research.update(
                approved_plan_hash=plan_hash,
                approved_by=actor,
                approved_at=now_iso(),
                phase="approved",
            )
            cursor.execute(
                "UPDATE runs SET status='queued', error=NULL, research=%s WHERE id=%s",
                (self._db.j(research), run_id),
            )
            self._audit(
                cursor,
                "research.plan_approved",
                actor,
                case_id=run["case_id"],
                run_id=run_id,
                plan_hash=plan_hash,
            )
            self._append_event(
                cursor,
                run_id,
                "research.plan_approved",
                {"plan_hash": plan_hash, "approved_by": actor},
            )
            cursor.execute("SELECT * FROM runs WHERE id=%s", (run_id,))
            return _run_record(cursor, cursor.fetchone())

    def _append_event(
        self,
        cursor: Any,
        run_id: str,
        event: str,
        data: Record,
        attempt_token: str | None = None,
    ) -> None:
        cursor.execute("SELECT id FROM runs WHERE id=%s FOR UPDATE", (run_id,))
        if cursor.fetchone() is None:
            raise KeyError(run_id)
        cursor.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS sequence FROM workflow_events "
            "WHERE run_id=%s",
            (run_id,),
        )
        sequence = cursor.fetchone()["sequence"] + 1
        cursor.execute(
            "INSERT INTO workflow_events(run_id, sequence, event, data, attempt_token, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (run_id, sequence, event, self._db.j(data), attempt_token, now_iso()),
        )

    def emit(self, run_id: str, event: str, data: Record) -> None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._append_event(cursor, run_id, event, data)

    def emit_fenced(
        self, run_id: str, attempt_token: str, event: str, data: Record
    ) -> None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._assert_fenced(cursor, run_id, attempt_token)
            self._append_event(cursor, run_id, event, data, attempt_token)

    def artifact_for_fingerprint(
        self, run_id: str, module_id: str, input_fingerprint: str
    ) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM artifacts WHERE run_id=%s AND module_id=%s "
                "AND input_fingerprint=%s",
                (run_id, module_id, input_fingerprint),
            )
            row = cursor.fetchone()
            return _artifact_record(row) if row else None

    def complete_node(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        artifact: Record,
        research: Record | None,
        event_data: Record,
        artifact_validator: Callable[[Record], bool] | None = None,
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._assert_fenced(cursor, run_id, attempt_token)
            cursor.execute(
                "SELECT * FROM workflow_nodes WHERE id=%s FOR UPDATE", (node_id,)
            )
            node = cursor.fetchone()
            if (
                not node
                or node["run_id"] != run_id
                or artifact.get("run_id") != run_id
                or artifact.get("module_id") != node["module_id"]
            ):
                raise JobFencedError("artifact does not match the fenced node")
            cursor.execute(
                "SELECT * FROM artifacts WHERE run_id=%s AND module_id=%s "
                "AND input_fingerprint=%s",
                (run_id, node["module_id"], artifact.get("input_fingerprint")),
            )
            existing = cursor.fetchone()
            candidate = (
                _artifact_record(existing) if existing else copy.deepcopy(artifact)
            )
            if not existing:
                candidate["id"] = _id("art")
            if artifact_validator is not None and not artifact_validator(candidate):
                raise ValueError("ARTIFACT_INVALID")
            if not existing:
                created_at = candidate.get("created_at", now_iso())
                cursor.execute(
                    "INSERT INTO artifacts(id, case_id, run_id, module_id, digest, payload, "
                    "markdown, input_fingerprint, created_by, attempt_token, created_at, record) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        candidate["id"],
                        candidate.get("case_id"),
                        run_id,
                        candidate["module_id"],
                        candidate["digest"],
                        self._db.j(candidate["payload"]),
                        candidate.get("markdown", ""),
                        candidate["input_fingerprint"],
                        candidate.get("created_by"),
                        attempt_token,
                        created_at,
                        self._db.j(candidate),
                    ),
                )
            cursor.execute(
                "UPDATE workflow_nodes SET status='succeeded', artifact_id=%s, error=NULL, "
                "last_attempt_token=%s WHERE id=%s",
                (candidate["id"], attempt_token, node_id),
            )
            if research is not None:
                cursor.execute(
                    "UPDATE runs SET research=%s WHERE id=%s",
                    (self._db.j(research), run_id),
                )
            self._append_event(
                cursor,
                run_id,
                "node.succeeded",
                {**copy.deepcopy(event_data), "artifact_id": candidate["id"]},
                attempt_token,
            )
            return candidate

    def finalize_success(
        self,
        run_id: str,
        attempt_token: str,
        research: Record | None,
        event_data: Record,
        *,
        deadline: float | None = None,
    ) -> None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT *, lease_until > now() AS lease_current FROM jobs "
                "WHERE run_id=%s FOR UPDATE",
                (run_id,),
            )
            job = cursor.fetchone()
            cursor.execute("SELECT * FROM runs WHERE id=%s FOR UPDATE", (run_id,))
            run = cursor.fetchone()
            if (
                run
                and run["status"] == "succeeded"
                and run.get("final_attempt_token") == attempt_token
                and job
                and job["state"] == "succeeded"
                and job.get("attempt_token") == attempt_token
            ):
                return
            if (
                not job
                or job["state"] != "claimed"
                or job.get("attempt_token") != attempt_token
                or not job["lease_current"]
            ):
                raise JobFencedError("stale workflow attempt")
            _remaining_finalization_seconds(deadline)
            cursor.execute(
                "SELECT node.id FROM workflow_nodes AS node "
                "LEFT JOIN artifacts AS artifact ON artifact.id=node.artifact_id "
                "WHERE node.run_id=%s AND (node.status<>'succeeded' OR artifact.id IS NULL "
                "OR artifact.run_id<>%s OR artifact.module_id<>node.module_id) LIMIT 1",
                (run_id, run_id),
            )
            if cursor.fetchone() is not None:
                raise ValueError("RUN_NOT_READY")
            _remaining_finalization_seconds(deadline)
            cursor.execute(
                "UPDATE runs SET status='succeeded', current_node_id=NULL, error=NULL, "
                "research=COALESCE(%s, research), final_attempt_token=%s WHERE id=%s",
                (
                    self._db.j(research) if research is not None else None,
                    attempt_token,
                    run_id,
                ),
            )
            cursor.execute(
                "UPDATE jobs SET state='succeeded', lease_until=NULL, budget_reserved=0 "
                "WHERE run_id=%s AND state='claimed' AND attempt_token=%s",
                (run_id, attempt_token),
            )
            self._append_event(
                cursor, run_id, "run.succeeded", event_data, attempt_token
            )
            _remaining_finalization_seconds(deadline)

    def get_artifact(self, artifact_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM artifacts WHERE id=%s", (artifact_id,))
            row = cursor.fetchone()
            return _artifact_record(row) if row else None

    def accept_snapshot(
        self, case_id: str, run_id: str, actor: str, snapshot: Record
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_token FROM jobs WHERE run_id=%s FOR UPDATE",
                (run_id,),
            )
            final_job = cursor.fetchone()
            cursor.execute("SELECT * FROM cases WHERE id=%s FOR UPDATE", (case_id,))
            case = cursor.fetchone()
            cursor.execute("SELECT * FROM runs WHERE id=%s FOR UPDATE", (run_id,))
            run = cursor.fetchone()
            if not run or run["case_id"] != case_id or case is None:
                raise ValueError("RUN_NOT_FOUND")
            if (
                run["status"] != "succeeded"
                or not run.get("final_attempt_token")
                or not final_job
                or final_job["state"] != "succeeded"
                or final_job.get("attempt_token") != run["final_attempt_token"]
            ):
                raise ValueError("RUN_NOT_READY")
            if run.get("accepted_snapshot_id"):
                cursor.execute(
                    "SELECT * FROM accepted_snapshots WHERE id=%s",
                    (run["accepted_snapshot_id"],),
                )
                return _snapshot_record(cursor.fetchone())
            proposal = copy.deepcopy(snapshot)
            if proposal.get("case_id") != case_id or proposal.get("run_id") != run_id:
                raise ValueError("RUN_NOT_FOUND")
            cursor.execute(
                "SELECT * FROM source_sets WHERE id=%s",
                (proposal.get("source_set_id"),),
            )
            source_set = cursor.fetchone()
            cursor.execute(
                "SELECT source_set.* FROM cases AS c LEFT JOIN source_sets AS source_set "
                "ON source_set.id=c.current_source_set_id WHERE c.id=%s",
                (case_id,),
            )
            current = cursor.fetchone()
            if (
                not source_set
                or source_set["case_id"] != case_id
                or source_set["id"] != run["plan"].get("source_set_id")
                or proposal.get("source_set_version") != source_set["version"]
                or not current
                or current.get("id") != source_set["id"]
                or current.get("version") != source_set["version"]
            ):
                raise ValueError("SOURCE_SET_CHANGED")
            artifact_refs = proposal.get("artifacts")
            if not isinstance(artifact_refs, list):
                raise ValueError("RUN_NOT_READY")
            cursor.execute(
                "SELECT artifact_id FROM workflow_nodes WHERE run_id=%s", (run_id,)
            )
            expected_ids = {row["artifact_id"] for row in cursor.fetchall()}
            if (
                len(artifact_refs) != len(expected_ids)
                or any(not isinstance(item, dict) for item in artifact_refs)
                or {item.get("id") for item in artifact_refs} != expected_ids
            ):
                raise ValueError("RUN_NOT_READY")
            for item in artifact_refs:
                cursor.execute("SELECT * FROM artifacts WHERE id=%s", (item.get("id"),))
                artifact = cursor.fetchone()
                try:
                    valid = bool(
                        artifact
                        and artifact.get("case_id") in {None, case_id}
                        and artifact["run_id"] == run_id
                        and item.get("module_id") == artifact["module_id"]
                        and item.get("digest") == artifact["digest"].strip()
                        and artifact["digest"].strip() == digest(artifact["payload"])
                    )
                except (TypeError, ValueError):
                    valid = False
                if not valid:
                    raise ValueError("RUN_NOT_READY")
            payload = proposal.copy()
            payload.pop("digest", None)
            try:
                valid_digest = proposal.get("digest") == digest(payload)
            except (TypeError, ValueError):
                valid_digest = False
            if not valid_digest:
                raise ValueError("RUN_NOT_READY")
            saved_id = _id("snap")
            proposal.update(
                id=saved_id,
                previous_snapshot_id=case.get("accepted_snapshot_id"),
            )
            cursor.execute(
                "INSERT INTO accepted_snapshots(id, case_id, run_id, digest, source_set_id, "
                "source_set_version, artifact_refs, previous_snapshot_id, accepted_by, "
                "attempt_token, accepted_at, record) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    saved_id,
                    case_id,
                    run_id,
                    proposal["digest"],
                    proposal["source_set_id"],
                    proposal["source_set_version"],
                    self._db.j(artifact_refs),
                    proposal["previous_snapshot_id"],
                    actor,
                    run["final_attempt_token"],
                    proposal.get("accepted_at", now_iso()),
                    self._db.j(proposal),
                ),
            )
            cursor.execute(
                "UPDATE cases SET accepted_snapshot_id=%s, "
                "visible_snapshot_id=COALESCE(visible_snapshot_id, %s) WHERE id=%s",
                (saved_id, saved_id, case_id),
            )
            cursor.execute(
                "UPDATE runs SET accepted_snapshot_id=%s WHERE id=%s",
                (saved_id, run_id),
            )
            self._audit(
                cursor,
                "snapshot.accepted",
                actor,
                case_id=case_id,
                run_id=run_id,
                snapshot_id=saved_id,
            )
            self._append_event(
                cursor,
                run_id,
                "snapshot.accepted",
                {"snapshot_id": saved_id, "digest": proposal["digest"]},
                run["final_attempt_token"],
            )
            return proposal

    def get_snapshot(self, snapshot_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM accepted_snapshots WHERE id=%s", (snapshot_id,)
            )
            row = cursor.fetchone()
            return _snapshot_record(row) if row else None

    def switch_visible_snapshot(
        self, case_id: str, snapshot_id: str, actor: str
    ) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM cases WHERE id=%s FOR UPDATE", (case_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                "SELECT * FROM accepted_snapshots WHERE id=%s AND case_id=%s",
                (snapshot_id, case_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute(
                "UPDATE cases SET visible_snapshot_id=%s WHERE id=%s",
                (snapshot_id, case_id),
            )
            self._audit(
                cursor,
                "snapshot.visible_switched",
                actor,
                case_id=case_id,
                snapshot_id=snapshot_id,
            )
            return _snapshot_record(row)

    def events_after(self, run_id: str, cursor: int = 0) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as db_cursor:
            db_cursor.execute(
                "SELECT * FROM workflow_events WHERE run_id=%s AND sequence>%s "
                "ORDER BY sequence",
                (run_id, cursor),
            )
            return [_event_record(row) for row in db_cursor.fetchall()]

    def wait_for_events(
        self, run_id: str, cursor: int, timeout: float = 1.0
    ) -> list[Record]:
        deadline = time.monotonic() + timeout
        while True:
            events = self.events_after(run_id, cursor)
            if events or time.monotonic() >= deadline:
                return events
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


def _version_record(row: Record) -> Record:
    value = copy.deepcopy(row["value"])
    value.update(
        case_id=row["case_id"],
        version=row["version"],
        author=row["author"],
        created_at=_iso(row["created_at"]),
    )
    return value


def _assumption_record(row: Record) -> Record:
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "author": row["author"],
        "statement": row["statement"],
        "supporting_claim": row["supporting_claim"],
        "conflicting_claim": row["conflicting_claim"],
        "evidence_ids": copy.deepcopy(row["evidence_ids"]),
        "affected_module_ids": copy.deepcopy(row["affected_module_ids"]),
        "status": row["status"],
        "stale": row["stale"],
        "created_at": _iso(row["created_at"]),
    }


class _PostgresPublicationLedger(_Adapter):
    def __init__(self, database: _Database, sources: _PostgresSourceCatalog) -> None:
        super().__init__(database)
        self._sources = sources

    def _lock_case(self, cursor: Any, case_id: str) -> None:
        cursor.execute("SELECT id FROM cases WHERE id=%s FOR UPDATE", (case_id,))
        if cursor.fetchone() is None:
            raise ValueError("CASE_NOT_FOUND")

    def _validate_refs(
        self,
        cursor: Any,
        case_id: str,
        refs: list[str],
        *,
        artifacts_only: bool = False,
    ) -> None:
        for ref in refs:
            cursor.execute(
                "SELECT 1 FROM artifacts WHERE id=%s AND case_id=%s", (ref, case_id)
            )
            if cursor.fetchone() is not None:
                continue
            if not artifacts_only:
                cursor.execute(
                    "SELECT withdrawn FROM sources WHERE id=%s AND case_id=%s",
                    (ref, case_id),
                )
                source = cursor.fetchone()
                if source:
                    if source["withdrawn"]:
                        raise ValueError("EVIDENCE_SOURCE_WITHDRAWN")
                    continue
                cursor.execute(
                    "SELECT 1 FROM accepted_snapshots WHERE id=%s AND case_id=%s",
                    (ref, case_id),
                )
                if cursor.fetchone() is not None:
                    continue
            raise ValueError("EVIDENCE_CASE_MISMATCH")

    def _append_version(
        self,
        cursor: Any,
        table: str,
        case_id: str,
        actor: str,
        expected_version: int,
        value: Record,
    ) -> Record:
        cursor.execute(
            f"INSERT INTO {table}(case_id, version, value, author, created_at) "
            f"SELECT %s, %s, %s, %s, %s WHERE "
            f"(SELECT COALESCE(MAX(version), 0) FROM {table} WHERE case_id=%s)=%s "
            "RETURNING *",
            (
                case_id,
                expected_version + 1,
                self._db.j(value),
                actor,
                now_iso(),
                case_id,
                expected_version,
            ),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("VERSION_CONFLICT")
        return _version_record(row)

    def append_thesis(
        self, case_id: str, actor: str, expected_version: int, thesis: Record
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            self._validate_refs(cursor, case_id, list(thesis.get("evidence_ids", [])))
            saved = copy.deepcopy(thesis)
            saved["id"] = _id("thesis")
            record = self._append_version(
                cursor,
                "thesis_versions",
                case_id,
                actor,
                expected_version,
                saved,
            )
            self._audit(
                cursor,
                "thesis.versioned",
                actor,
                case_id=case_id,
                version=record["version"],
            )
            return record

    def list_theses(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM thesis_versions WHERE case_id=%s ORDER BY version",
                (case_id,),
            )
            return [_version_record(row) for row in cursor.fetchall()]

    def append_recommendations(
        self,
        case_id: str,
        actor: str,
        expected_version: int,
        recommendations: Record,
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            self._validate_refs(
                cursor,
                case_id,
                list(recommendations.get("analytical_dependency_ids", [])),
                artifacts_only=True,
            )
            saved = copy.deepcopy(recommendations)
            saved.update(
                id=_id("rec"),
                accepted_snapshot_id=recommendations.get("accepted_snapshot_id"),
                stale=False,
                stale_reasons=[],
            )
            record = self._append_version(
                cursor,
                "recommendation_versions",
                case_id,
                actor,
                expected_version,
                saved,
            )
            self._audit(
                cursor,
                "recommendation.versioned",
                actor,
                case_id=case_id,
                version=record["version"],
            )
            return record

    def list_recommendations(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM recommendation_versions WHERE case_id=%s ORDER BY version",
                (case_id,),
            )
            return [_version_record(row) for row in cursor.fetchall()]

    def save_report_inputs(
        self,
        case_id: str,
        actor: str,
        thesis: Record,
        recommendations: Record,
        accepted_snapshot_id: str | None,
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            self._validate_refs(cursor, case_id, list(thesis.get("evidence_ids", [])))
            self._validate_refs(
                cursor,
                case_id,
                list(recommendations.get("analytical_dependency_ids", [])),
                artifacts_only=True,
            )
            saved_thesis = {
                key: copy.deepcopy(value)
                for key, value in thesis.items()
                if key != "expected_version"
            }
            saved_thesis["id"] = _id("thesis")
            thesis_record = self._append_version(
                cursor,
                "thesis_versions",
                case_id,
                actor,
                thesis["expected_version"],
                saved_thesis,
            )
            saved_recommendations = {
                key: copy.deepcopy(value)
                for key, value in recommendations.items()
                if key != "expected_version"
            }
            saved_recommendations.update(
                id=_id("rec"),
                accepted_snapshot_id=accepted_snapshot_id,
                stale=False,
                stale_reasons=[],
            )
            recommendation_record = self._append_version(
                cursor,
                "recommendation_versions",
                case_id,
                actor,
                recommendations["expected_version"],
                saved_recommendations,
            )
            cursor.execute(
                "INSERT INTO report_inputs(id, case_id, thesis_version, "
                "recommendation_version, accepted_snapshot_id, created_by, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    _id("inputs"),
                    case_id,
                    thesis_record["version"],
                    recommendation_record["version"],
                    accepted_snapshot_id,
                    actor,
                    now_iso(),
                ),
            )
            self._audit(
                cursor,
                "thesis.versioned",
                actor,
                case_id=case_id,
                version=thesis_record["version"],
            )
            self._audit(
                cursor,
                "recommendation.versioned",
                actor,
                case_id=case_id,
                version=recommendation_record["version"],
            )
            return {
                "thesis": thesis_record,
                "recommendations": recommendation_record,
            }

    def create_note(self, case_id: str, actor: str, body: str) -> Record:
        note = {
            "id": _id("note"),
            "case_id": case_id,
            "author": actor,
            "body": body,
            "promoted": False,
            "created_at": now_iso(),
        }
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            cursor.execute(
                "INSERT INTO notes(id, case_id, author, body, promoted, created_at) "
                "VALUES (%s, %s, %s, %s, false, %s)",
                (note["id"], case_id, actor, body, note["created_at"]),
            )
            self._audit(
                cursor, "note.created", actor, case_id=case_id, note_id=note["id"]
            )
        return note

    def list_notes(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM notes WHERE case_id=%s ORDER BY created_at, id",
                (case_id,),
            )
            return [_note_record(row) for row in cursor.fetchall()]

    def promote_note(self, case_id: str, note_id: str, actor: str) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            return self._sources._ingest_promoted_note(cursor, note_id, case_id, actor)

    def create_assumption(
        self,
        case_id: str,
        actor: str,
        statement: str,
        evidence_ids: list[str],
        affected_module_ids: list[str],
        supporting_claim: str = "",
        conflicting_claim: str = "",
    ) -> Record:
        assumption = {
            "id": _id("assumption"),
            "case_id": case_id,
            "author": actor,
            "statement": statement,
            "supporting_claim": supporting_claim,
            "conflicting_claim": conflicting_claim,
            "evidence_ids": list(evidence_ids),
            "affected_module_ids": list(affected_module_ids),
            "status": "PROVISIONAL",
            "stale": False,
            "created_at": now_iso(),
        }
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            self._validate_refs(cursor, case_id, evidence_ids)
            cursor.execute(
                "INSERT INTO assumptions(id, case_id, author, statement, supporting_claim, "
                "conflicting_claim, evidence_ids, affected_module_ids, status, stale, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PROVISIONAL', false, %s)",
                (
                    assumption["id"],
                    case_id,
                    actor,
                    statement,
                    supporting_claim,
                    conflicting_claim,
                    self._db.j(evidence_ids),
                    self._db.j(affected_module_ids),
                    assumption["created_at"],
                ),
            )
            self._audit(
                cursor,
                "assumption.created",
                actor,
                case_id=case_id,
                assumption_id=assumption["id"],
            )
        return assumption

    def list_assumptions(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM assumptions WHERE case_id=%s ORDER BY created_at, id",
                (case_id,),
            )
            return [_assumption_record(row) for row in cursor.fetchall()]

    def _model_identity(
        self, cursor: Any, requested: Record | None, snapshot: Record
    ) -> Record | None:
        if requested is None:
            return None
        if not isinstance(requested, dict):
            raise ValueError("MODEL_SNAPSHOT_MISMATCH")
        cursor.execute(
            "SELECT record FROM model_builds WHERE id=%s", (requested.get("build_id"),)
        )
        row = cursor.fetchone()
        build = copy.deepcopy(row["record"]) if row else None
        if (
            not build
            or build.get("status") != "READY"
            or build.get("case_id") != snapshot.get("case_id")
            or build.get("accepted_snapshot_id") != snapshot.get("id")
            or requested.get("accepted_snapshot_id")
            != build.get("accepted_snapshot_id")
            or requested.get("payload_digest") != build.get("payload_digest")
            or requested.get("input_fingerprint") != build.get("input_fingerprint")
        ):
            raise ValueError("MODEL_SNAPSHOT_MISMATCH")
        identity = {
            "build_id": build["id"],
            "accepted_snapshot_id": build["accepted_snapshot_id"],
            "payload_digest": build["payload_digest"],
            "input_fingerprint": build["input_fingerprint"],
        }
        if "export" in requested:
            export = build.get("export") or {}
            expected = {
                "sha256": export.get("sha256"),
                "size": export.get("size"),
                "filename": export.get("filename"),
            }
            if export.get("status") != "READY" or requested["export"] != expected:
                raise ValueError("MODEL_EXPORT_MISMATCH")
            identity["export"] = expected
        return identity

    def _latest_version(self, cursor: Any, table: str, case_id: str) -> Record | None:
        cursor.execute(
            f"SELECT * FROM {table} WHERE case_id=%s ORDER BY version DESC LIMIT 1",
            (case_id,),
        )
        row = cursor.fetchone()
        return _version_record(row) if row else None

    def _validate_report_authority(
        self, cursor: Any, case_id: str, report: Record
    ) -> None:
        content = report.get("content")
        if not isinstance(content, dict):
            raise ValueError("SNAPSHOT_REQUIRED")
        cursor.execute("SELECT * FROM cases WHERE id=%s", (case_id,))
        case = cursor.fetchone()
        cursor.execute(
            "SELECT * FROM accepted_snapshots WHERE id=%s",
            (content.get("snapshot_id"),),
        )
        row = cursor.fetchone()
        snapshot = _snapshot_record(row) if row else None
        snapshot_digest = content.get("snapshot_digest")
        if (
            not case
            or not snapshot
            or snapshot.get("case_id") != case_id
            or case.get("accepted_snapshot_id") != snapshot.get("id")
            or report.get("snapshot_digest") != snapshot_digest
            or snapshot_digest != digest(snapshot)
        ):
            raise ValueError("SNAPSHOT_REQUIRED")
        thesis = self._latest_version(cursor, "thesis_versions", case_id)
        recommendation = self._latest_version(
            cursor, "recommendation_versions", case_id
        )
        if not thesis or not recommendation:
            raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")
        if (
            content.get("thesis_version") != thesis.get("version")
            or content.get("recommendation_version") != recommendation.get("version")
            or recommendation.get("accepted_snapshot_id") != snapshot.get("id")
        ):
            raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")
        model = self._model_identity(cursor, content.get("model"), snapshot)
        expected_fingerprint = digest(
            clean_json(
                {
                    "snapshot": snapshot,
                    "thesis": thesis,
                    "recommendations": recommendation,
                    "model": model,
                }
            )
        )
        preview_digest = report.get("preview_digest")
        if (
            content.get("case_id") != case_id
            or content.get("include_model") != (model is not None)
            or content.get("input_fingerprint") != expected_fingerprint
            or report.get("input_fingerprint") != expected_fingerprint
            or report.get("digest") != preview_digest
            or preview_digest != digest(content)
        ):
            raise ValueError("STALE_PREVIEW")

    def freeze_report(self, case_id: str, actor: str, report: Record) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            self._validate_report_authority(cursor, case_id, report)
            saved = copy.deepcopy(report)
            saved.update(
                id=_id("report"),
                case_id=case_id,
                created_by=actor,
                created_at=now_iso(),
                status="PENDING_APPROVAL",
            )
            cursor.execute("SELECT id FROM reports WHERE case_id=%s", (case_id,))
            previous = cursor.fetchone()
            if previous:
                cursor.execute("DELETE FROM reports WHERE id=%s", (previous["id"],))
            cursor.execute(
                "INSERT INTO reports(id, case_id, status, digest, snapshot_digest, value, "
                "created_by, created_at, preview_digest, input_fingerprint) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    saved["id"],
                    case_id,
                    saved["status"],
                    saved["digest"],
                    saved["snapshot_digest"],
                    self._db.j(saved),
                    actor,
                    saved["created_at"],
                    saved["preview_digest"],
                    saved["input_fingerprint"],
                ),
            )
            self._audit(
                cursor,
                "report.frozen",
                actor,
                case_id=case_id,
                report_id=saved["id"],
            )
            return saved

    def get_report(self, case_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT value FROM reports WHERE case_id=%s", (case_id,))
            row = cursor.fetchone()
            return copy.deepcopy(row["value"]) if row else None

    def approve_report(
        self,
        case_id: str,
        actor: str,
        expected_status: str,
        preview_digest: str,
        input_fingerprint: str,
        comment: str | None,
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            cursor.execute(
                "SELECT * FROM reports WHERE case_id=%s FOR UPDATE", (case_id,)
            )
            row = cursor.fetchone()
            report = copy.deepcopy(row["value"]) if row else None
            if not report or report.get("status") != expected_status:
                raise ValueError("report changed or missing")
            if preview_digest != report.get(
                "preview_digest"
            ) or input_fingerprint != report.get("input_fingerprint"):
                raise ValueError("STALE_PREVIEW")
            try:
                self._validate_report_authority(cursor, case_id, report)
            except ValueError as exc:
                raise ValueError("STALE_PREVIEW") from exc
            approved_at = now_iso()
            report.update(
                status="APPROVED",
                approved_by=actor,
                approved_at=approved_at,
                approval_comment=comment,
            )
            cursor.execute(
                "UPDATE reports SET status='APPROVED', value=%s, approved_by=%s, "
                "approved_at=%s, approval_comment=%s WHERE id=%s",
                (self._db.j(report), actor, approved_at, comment, report["id"]),
            )
            cursor.execute(
                "INSERT INTO report_approvals(report_id, actor, preview_digest, "
                "input_fingerprint, comment, approved_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    report["id"],
                    actor,
                    preview_digest,
                    input_fingerprint,
                    comment,
                    approved_at,
                ),
            )
            self._audit(
                cursor,
                "report.approved",
                actor,
                case_id=case_id,
                report_id=report["id"],
            )
            return report

    def save_rv_universe(self, case_id: str, actor: str, universe: Record) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._lock_case(cursor, case_id)
            cursor.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM rv_universes "
                "WHERE case_id=%s",
                (case_id,),
            )
            version = cursor.fetchone()["version"] + 1
            saved = copy.deepcopy(universe)
            saved.update(
                id=_id("rv"),
                case_id=case_id,
                author=actor,
                version=version,
                created_at=now_iso(),
            )
            cursor.execute(
                "INSERT INTO rv_universes(case_id, version, id, value, author, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    case_id,
                    version,
                    saved["id"],
                    self._db.j(saved),
                    actor,
                    saved["created_at"],
                ),
            )
            self._audit(
                cursor,
                "rv.universe_versioned",
                actor,
                case_id=case_id,
                version=version,
            )
            return saved

    def get_rv_universe(self, case_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM rv_universes WHERE case_id=%s ORDER BY version DESC LIMIT 1",
                (case_id,),
            )
            row = cursor.fetchone()
            return copy.deepcopy(row["value"]) if row else None

    def list_audit(self) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM audit_events ORDER BY id")
            records = []
            for row in cursor.fetchall():
                record = {
                    "id": row.get("event_id") or f"aud_{row['id']}",
                    "action": row["action"],
                    "actor": row["actor"],
                    "at": _iso(row["created_at"]),
                    **copy.deepcopy(row["payload"]),
                }
                if row.get("case_id") is not None:
                    record["case_id"] = row["case_id"]
                records.append(record)
            return records

    def create_methodology_draft(self, draft: Record, actor: str) -> Record:
        saved = copy.deepcopy(draft)
        saved.update(
            id=_id("draft"),
            status="DRAFT",
            created_by=actor,
            created_at=now_iso(),
        )
        saved.setdefault(
            "semantic_diff",
            {"before": saved.get("before"), "after": saved.get("after")},
        )
        saved["digest"] = digest(saved)
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO methodology_drafts(id, status, module_id, value, digest, "
                "created_by, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    saved["id"],
                    saved["status"],
                    saved.get("module_id"),
                    self._db.j(saved),
                    saved["digest"],
                    actor,
                    saved["created_at"],
                ),
            )
            self._audit(
                cursor,
                "methodology.draft_created",
                actor,
                draft_id=saved["id"],
                module_id=saved.get("module_id"),
            )
        return saved

    def list_methodology_drafts(self) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM methodology_drafts ORDER BY created_at, id"
            )
            return [copy.deepcopy(row["value"]) for row in cursor.fetchall()]

    def validate_methodology_draft(self, draft_id: str, actor: str) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM methodology_drafts WHERE id=%s FOR UPDATE",
                (draft_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise KeyError("draft not found")
            draft = copy.deepcopy(row["value"])
            if draft.get("before") == draft.get("after"):
                raise ValueError(
                    "draft does not validate against the current authority"
                )
            draft.update(status="VALIDATED", validated_by=actor, validated_at=now_iso())
            cursor.execute(
                "UPDATE methodology_drafts SET status='VALIDATED', value=%s, "
                "validated_by=%s, validated_at=%s WHERE id=%s",
                (
                    self._db.j(draft),
                    actor,
                    draft["validated_at"],
                    draft_id,
                ),
            )
            self._audit(cursor, "methodology.draft_validated", actor, draft_id=draft_id)
            return draft

    def confirm_methodology_draft(
        self, draft_id: str, actor: str, signature: str
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM methodology_drafts WHERE id=%s FOR UPDATE",
                (draft_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise KeyError("draft not found")
            draft = copy.deepcopy(row["value"])
            if draft.get("status") != "VALIDATED":
                raise ValueError("validated draft required")
            draft.update(
                status="CONFIRMED_PENDING_SIGNED_AUTHORITY",
                confirmed_by=actor,
                confirmed_at=now_iso(),
                signature=signature,
            )
            cursor.execute(
                "UPDATE methodology_drafts SET status=%s, value=%s, confirmed_by=%s, "
                "confirmed_at=%s, signature=%s WHERE id=%s",
                (
                    draft["status"],
                    self._db.j(draft),
                    actor,
                    draft["confirmed_at"],
                    signature,
                    draft_id,
                ),
            )
            self._audit(
                cursor,
                "methodology.draft_confirmed",
                actor,
                draft_id=draft_id,
                signature=signature,
            )
            return draft


class _PostgresModelLedger(_Adapter):
    def _build(
        self, cursor: Any, build_id: str, *, lock: bool = False
    ) -> Record | None:
        cursor.execute(
            "SELECT record FROM model_builds WHERE id=%s"
            + (" FOR UPDATE" if lock else ""),
            (build_id,),
        )
        row = cursor.fetchone()
        return copy.deepcopy(row["record"]) if row else None

    def _save_build(
        self, cursor: Any, build: Record, attempt_token: str | None = None
    ) -> None:
        cursor.execute(
            "UPDATE model_builds SET status=%s, record=%s, started_at=%s, "
            "completed_at=%s, last_attempt_token=COALESCE(%s, last_attempt_token), "
            "updated_at=now() WHERE id=%s",
            (
                build["status"],
                self._db.j(build),
                build.get("started_at"),
                build.get("completed_at"),
                attempt_token,
                build["id"],
            ),
        )

    def queue_build(self, build: Record, actor: str) -> tuple[Record, bool]:
        proposal = copy.deepcopy(build)
        proposal["id"] = _id("model")
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM cases WHERE id=%s FOR UPDATE",
                (proposal.get("case_id"),),
            )
            if cursor.fetchone() is None:
                raise ValueError("MODEL_BUILD_INVALID")
            cursor.execute(
                "SELECT record FROM model_builds WHERE case_id=%s AND input_fingerprint=%s",
                (proposal.get("case_id"), proposal.get("input_fingerprint")),
            )
            existing = cursor.fetchone()
            if existing:
                return copy.deepcopy(existing["record"]), False
            cursor.execute(
                "SELECT * FROM runs WHERE id=%s", (proposal.get("accepted_run_id"),)
            )
            run = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM accepted_snapshots WHERE id=%s",
                (proposal.get("accepted_snapshot_id"),),
            )
            snapshot = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM source_sets WHERE id=%s",
                (proposal.get("source_set_id"),),
            )
            source_set = cursor.fetchone()
            fingerprint = proposal.get("input_fingerprint")
            if (
                not run
                or run["case_id"] != proposal.get("case_id")
                or run["status"] != "succeeded"
                or run.get("accepted_snapshot_id")
                != proposal.get("accepted_snapshot_id")
                or not snapshot
                or snapshot["case_id"] != proposal.get("case_id")
                or snapshot["run_id"] != proposal.get("accepted_run_id")
                or snapshot["source_set_id"] != proposal.get("source_set_id")
                or not source_set
                or source_set["case_id"] != proposal.get("case_id")
                or not isinstance(fingerprint, str)
                or len(fingerprint) != 64
                or any(character not in "0123456789abcdef" for character in fingerprint)
            ):
                raise ValueError("MODEL_BUILD_INVALID")
            proposal.update(
                status="QUEUED",
                created_by=actor,
                queued_at=proposal.get("queued_at", now_iso()),
                started_at=None,
                completed_at=None,
                error=None,
                export={"status": "NOT_REQUESTED", "error": None},
            )
            cursor.execute(
                "INSERT INTO model_builds(id, case_id, accepted_run_id, accepted_snapshot_id, "
                "source_set_id, input_fingerprint, status, record, created_by, queued_at, "
                "started_at, completed_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL)",
                (
                    proposal["id"],
                    proposal["case_id"],
                    proposal["accepted_run_id"],
                    proposal["accepted_snapshot_id"],
                    proposal["source_set_id"],
                    proposal["input_fingerprint"],
                    proposal["status"],
                    self._db.j(proposal),
                    actor,
                    proposal["queued_at"],
                ),
            )
            cursor.execute(
                "INSERT INTO model_build_jobs(build_id, kind, actor, state) "
                "VALUES (%s, 'calculate', %s, 'queued')",
                (proposal["id"], actor),
            )
            self._audit(
                cursor,
                "model.queued",
                actor,
                case_id=proposal["case_id"],
                build_id=proposal["id"],
            )
            return proposal, True

    def retry_build(self, build_id: str, actor: str) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM model_build_jobs WHERE build_id=%s AND kind='calculate' FOR UPDATE",
                (build_id,),
            )
            job = cursor.fetchone()
            build = self._build(cursor, build_id, lock=True)
            if (
                not build
                or build.get("status") != "FAILED"
                or not job
                or job["state"] != "failed"
            ):
                raise ValueError("MODEL_RETRY_INVALID")
            build.update(
                status="QUEUED", started_at=None, completed_at=None, error=None
            )
            self._save_build(cursor, build)
            cursor.execute(
                "UPDATE model_build_jobs SET actor=%s, state='queued', worker_id=NULL, "
                "attempt_token=NULL, lease_until=NULL, error=NULL, updated_at=now() "
                "WHERE build_id=%s AND kind='calculate'",
                (actor, build_id),
            )
            self._audit(
                cursor,
                "model.retried",
                actor,
                case_id=build["case_id"],
                build_id=build_id,
            )
            return build

    def get_build(self, build_id: str) -> Record | None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            return self._build(cursor, build_id)

    def list_builds(self, case_id: str) -> list[Record]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT record FROM model_builds WHERE case_id=%s "
                "ORDER BY queued_at DESC, id DESC",
                (case_id,),
            )
            return [copy.deepcopy(row["record"]) for row in cursor.fetchall()]

    def queue_export(self, build_id: str, actor: str) -> tuple[Record, bool]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"caos:model-build:{build_id}",),
            )
            cursor.execute(
                "SELECT state FROM model_build_jobs WHERE build_id=%s AND kind='export' FOR UPDATE",
                (build_id,),
            )
            job = cursor.fetchone()
            build = self._build(cursor, build_id, lock=True)
            if not build or build.get("status") != "READY":
                raise ValueError("MODEL_EXPORT_NOT_READY")
            if job and job["state"] in {"queued", "claimed", "succeeded"}:
                return build, False
            build["export"] = {"status": "QUEUED", "error": None}
            self._save_build(cursor, build)
            cursor.execute(
                "INSERT INTO model_build_jobs(build_id, kind, actor, state) "
                "VALUES (%s, 'export', %s, 'queued') ON CONFLICT (build_id, kind) "
                "DO UPDATE SET actor=EXCLUDED.actor, state='queued', worker_id=NULL, "
                "attempt_token=NULL, lease_until=NULL, error=NULL, updated_at=now()",
                (build_id, actor),
            )
            self._audit(
                cursor,
                "model.export.queued",
                actor,
                case_id=build["case_id"],
                build_id=build_id,
            )
            return build, True

    def pending_jobs(self) -> list[tuple[str, str, str]]:
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT job.build_id, job.actor, job.kind FROM model_build_jobs AS job "
                "JOIN model_builds AS build ON build.id=job.build_id "
                "WHERE job.kind IN ('calculate', 'export') "
                "AND job.state IN ('queued', 'claimed') "
                "ORDER BY job.created_at, job.build_id, job.kind"
            )
            return [
                (row["build_id"], row["actor"], row["kind"])
                for row in cursor.fetchall()
            ]

    def claim(self, build_id: str, worker: str, kind: str = "calculate") -> str | None:
        _model_job_key(build_id, kind)
        token = _id("attempt")
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext('caos:workflow-budget'))"
            )
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"caos:model-build:{build_id}",),
            )
            cursor.execute(
                "SELECT (SELECT count(*) FROM jobs WHERE state='claimed' AND lease_until > now()) + "
                "(SELECT count(*) FROM model_build_jobs WHERE state='claimed' AND lease_until > now()) AS active"
            )
            if cursor.fetchone()["active"] >= MAX_ACTIVE_JOBS:
                return None
            cursor.execute(
                "SELECT build_id FROM model_build_jobs WHERE build_id=%s AND kind=%s "
                "AND (state='queued' OR (state='claimed' AND lease_until <= now())) "
                "FOR UPDATE SKIP LOCKED",
                (build_id, kind),
            )
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                "UPDATE model_build_jobs SET state='claimed', worker_id=%s, attempt_token=%s, "
                "lease_until=now() + (%s * interval '1 second'), error=NULL, updated_at=now() "
                "WHERE build_id=%s AND kind=%s AND (state='queued' OR "
                "(state='claimed' AND lease_until <= now())) RETURNING build_id",
                (worker, token, self._db.lease_seconds, build_id, kind),
            )
            if cursor.fetchone() is None:
                return None
            build = self._build(cursor, build_id, lock=True)
            if not build:
                return None
            if kind == "calculate":
                build.update(
                    status="BUILDING", started_at=build.get("started_at") or now_iso()
                )
            else:
                build["export"] = {
                    **build["export"],
                    "status": "EXPORTING",
                    "error": None,
                }
            self._save_build(cursor, build, token)
            return token

    def renew(self, build_id: str, attempt_token: str, kind: str = "calculate") -> bool:
        _model_job_key(build_id, kind)
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE model_build_jobs SET lease_until=now() + (%s * interval '1 second'), "
                "updated_at=now() WHERE build_id=%s AND kind=%s AND state='claimed' "
                "AND attempt_token=%s AND lease_until > now() RETURNING build_id",
                (self._db.lease_seconds, build_id, kind, attempt_token),
            )
            return cursor.fetchone() is not None

    def is_current(
        self, build_id: str, attempt_token: str, kind: str = "calculate"
    ) -> bool:
        _model_job_key(build_id, kind)
        with self._db.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM model_build_jobs WHERE build_id=%s AND kind=%s "
                "AND state='claimed' AND attempt_token=%s AND lease_until > now()",
                (build_id, kind, attempt_token),
            )
            return cursor.fetchone() is not None

    def _fenced_job(
        self, cursor: Any, build_id: str, attempt_token: str, kind: str
    ) -> Record:
        _model_job_key(build_id, kind)
        cursor.execute(
            "SELECT * FROM model_build_jobs WHERE build_id=%s AND kind=%s "
            "AND state='claimed' AND attempt_token=%s AND lease_until > now() FOR UPDATE",
            (build_id, kind, attempt_token),
        )
        row = cursor.fetchone()
        if not row:
            raise JobFencedError("stale model attempt")
        return row

    def complete(
        self,
        build_id: str,
        attempt_token: str,
        result: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._fenced_job(cursor, build_id, attempt_token, kind)
            build = self._build(cursor, build_id, lock=True)
            if not build:
                raise JobFencedError("stale model attempt")
            validated = _validated_model_result(build, result, kind)
            if kind == "calculate":
                build.update(validated)
                build.update(status="READY", completed_at=now_iso(), error=None)
            else:
                build["export"] = {
                    **build["export"],
                    **validated,
                    "status": "READY",
                    "error": None,
                }
            self._save_build(cursor, build, attempt_token)
            cursor.execute(
                "UPDATE model_build_jobs SET state='succeeded', lease_until=NULL, "
                "updated_at=now() WHERE build_id=%s AND kind=%s AND attempt_token=%s",
                (build_id, kind, attempt_token),
            )
            self._audit(
                cursor,
                f"model.{kind}.succeeded",
                actor,
                case_id=build["case_id"],
                build_id=build_id,
            )
            return build

    def fail(
        self,
        build_id: str,
        attempt_token: str,
        error: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record:
        with self._db.connection() as connection, connection.cursor() as cursor:
            self._fenced_job(cursor, build_id, attempt_token, kind)
            if (
                not isinstance(error, dict)
                or set(error) != {"code", "detail"}
                or not isinstance(error["code"], str)
                or len(error["code"]) > 80
                or not isinstance(error["detail"], str)
                or len(error["detail"]) > 500
            ):
                raise ValueError("MODEL_ERROR_INVALID")
            build = self._build(cursor, build_id, lock=True)
            if not build:
                raise JobFencedError("stale model attempt")
            if kind == "calculate":
                build.update(
                    status="FAILED", completed_at=now_iso(), error=copy.deepcopy(error)
                )
            else:
                build["export"] = {
                    **build["export"],
                    "status": "FAILED",
                    "error": copy.deepcopy(error),
                }
            self._save_build(cursor, build, attempt_token)
            cursor.execute(
                "UPDATE model_build_jobs SET state='failed', lease_until=NULL, error=%s, "
                "updated_at=now() WHERE build_id=%s AND kind=%s AND attempt_token=%s",
                (self._db.j(error), build_id, kind, attempt_token),
            )
            self._audit(
                cursor,
                f"model.{kind}.failed",
                actor,
                case_id=build["case_id"],
                build_id=build_id,
                code=error["code"],
            )
            return build

    def record_export_download(self, build_id: str, case_id: str, actor: str) -> None:
        with self._db.connection() as connection, connection.cursor() as cursor:
            build = self._build(cursor, build_id, lock=True)
            if (
                not build
                or build.get("case_id") != case_id
                or (build.get("export") or {}).get("status") != "READY"
            ):
                raise ValueError("MODEL_EXPORT_NOT_READY")
            self._audit(
                cursor,
                "model.export.downloaded",
                actor,
                case_id=case_id,
                build_id=build_id,
            )


class PostgresLedgerSet:
    """Four normalized PostgreSQL adapters sharing one database configuration."""

    __slots__ = ("sources", "runs", "publications", "models")

    def __init__(self, database_url: str, *, lease_seconds: float = 60.0) -> None:
        database = _Database(database_url, lease_seconds)
        sources = _PostgresSourceCatalog(database)
        self.sources = sources
        self.runs = _PostgresRunLedger(database)
        self.publications = _PostgresPublicationLedger(database, sources)
        self.models = _PostgresModelLedger(database)
