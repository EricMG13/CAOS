"""Normalized PostgreSQL implementations of the four ledger ports."""

from __future__ import annotations

import copy
import hashlib
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .contracts import clean_json, digest
from .ledgers import _validate_run_nodes
from .migrations import apply_migrations
from .store import (
    MAX_ACTIVE_JOBS,
    JobFencedError,
    _remaining_finalization_seconds,
    _validated_model_result,
    now_iso,
)


Record = dict[str, Any]


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _public_source(source: Record) -> Record:
    return copy.deepcopy(
        {
            key: value
            for key, value in source.items()
            if key not in {"vault_path", "withdrawn_at"}
        }
    )


class _Adapter:
    __slots__ = ("_owner",)

    def __init__(self, owner: PostgresLedgerSet) -> None:
        self._owner = owner

    def _audit(self, cursor: Any, action: str, actor: str, **details: Any) -> Record:
        record = {
            "id": _new_id("aud"),
            "action": action,
            "actor": actor,
            "at": now_iso(),
            **copy.deepcopy(details),
        }
        cursor.execute(
            "INSERT INTO audit_events(actor, action, case_id, payload) "
            "VALUES (%s, %s, %s, %s)",
            (actor, action, details.get("case_id"), Jsonb(record)),
        )
        return record


class _PostgresSourceCatalog(_Adapter):
    def _append_source_set(
        self,
        cursor: Any,
        case_id: str,
        actor: str,
        *,
        add_id: str | None = None,
        remove_id: str | None = None,
    ) -> Record:
        cursor.execute(
            "SELECT current_source_set_id, record FROM cases WHERE id=%s FOR UPDATE",
            (case_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("CASE_NOT_FOUND")
        current_id, case_record = row
        current = None
        if current_id:
            cursor.execute("SELECT record FROM source_sets WHERE id=%s", (current_id,))
            current_row = cursor.fetchone()
            current = current_row[0] if current_row else None
        source_ids = list((current or {}).get("source_ids", []))
        if source_ids:
            cursor.execute(
                "SELECT id FROM sources WHERE id = ANY(%s) AND withdrawn=false",
                (source_ids,),
            )
            active = {item[0] for item in cursor.fetchall()}
            source_ids = [item for item in source_ids if item in active]
        if remove_id is not None:
            source_ids = [item for item in source_ids if item != remove_id]
        if add_id is not None and add_id not in source_ids:
            source_ids.append(add_id)
        source_set = {
            "id": _new_id("set"),
            "case_id": case_id,
            "version": (current or {}).get("version", 0) + 1,
            "source_ids": source_ids,
            "created_by": actor,
            "created_at": now_iso(),
        }
        cursor.execute(
            "INSERT INTO source_sets(id, case_id, version, source_ids, created_by, "
            "created_at, record) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                source_set["id"],
                case_id,
                source_set["version"],
                Jsonb(source_ids),
                actor,
                source_set["created_at"],
                Jsonb(source_set),
            ),
        )
        cursor.execute(
            "UPDATE cases SET current_source_set_id=%s, record=%s WHERE id=%s",
            (source_set["id"], Jsonb(case_record), case_id),
        )
        return source_set

    def ingest(self, source: Record, actor: str) -> Record:
        saved = copy.deepcopy(source)
        saved["id"] = _new_id("src")
        saved.setdefault("created_by", actor)
        saved.setdefault("created_at", now_iso())
        saved.setdefault("withdrawn", False)
        try:
            with self._owner._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM cases WHERE id=%s FOR UPDATE",
                        (saved.get("case_id"),),
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("CASE_NOT_FOUND")
                    cursor.execute(
                        "INSERT INTO sources(id, case_id, filename, media_type, sha256, "
                        "vault_path, bytes, blocks, withdrawn, created_by, created_at, "
                        "source_kind, withdrawn_at, record) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            saved["id"],
                            saved["case_id"],
                            saved["filename"],
                            saved["media_type"],
                            saved["sha256"],
                            saved.get("vault_path"),
                            saved["bytes"],
                            Jsonb(saved.get("blocks", [])),
                            bool(saved.get("withdrawn")),
                            saved["created_by"],
                            saved["created_at"],
                            saved.get("source_kind"),
                            saved.get("withdrawn_at"),
                            Jsonb(saved),
                        ),
                    )
                    source_set = self._append_source_set(
                        cursor, saved["case_id"], actor, add_id=saved["id"]
                    )
                    self._audit(
                        cursor,
                        "source.ingested",
                        actor,
                        case_id=saved["case_id"],
                        source_id=saved["id"],
                        sha256=saved.get("sha256"),
                    )
            return {**_public_source(saved), "source_set": source_set}
        except psycopg.errors.UniqueViolation as exc:
            raise ValueError("source content already active") from exc

    def _ingest_promoted_note(
        self, connection: Any, note: Record, actor: str
    ) -> Record:
        with connection.cursor() as cursor:
            promoted_id = note.get("promoted_source_id")
            if note.get("promoted") and promoted_id:
                cursor.execute(
                    "SELECT record FROM sources WHERE id=%s AND withdrawn=false",
                    (promoted_id,),
                )
                if cursor.fetchone() is not None:
                    return copy.deepcopy(note)
            body = note["body"]
            source = {
                "id": _new_id("src-note"),
                "case_id": note["case_id"],
                "filename": f"analyst-note-{note['id']}.md",
                "media_type": "text/markdown",
                "bytes": len(body.encode()),
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                "vault_path": None,
                "blocks": [
                    {
                        "block_id": "b00001",
                        "locator": {"note_id": note["id"]},
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
            cursor.execute(
                "INSERT INTO sources(id, case_id, filename, media_type, sha256, "
                "vault_path, bytes, blocks, withdrawn, created_by, created_at, "
                "source_kind, record) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "
                "false, %s, %s, %s, %s)",
                (
                    source["id"],
                    source["case_id"],
                    source["filename"],
                    source["media_type"],
                    source["sha256"],
                    None,
                    source["bytes"],
                    Jsonb(source["blocks"]),
                    actor,
                    source["created_at"],
                    source["source_kind"],
                    Jsonb(source),
                ),
            )
            source_set = self._append_source_set(
                cursor, note["case_id"], actor, add_id=source["id"]
            )
            promoted = copy.deepcopy(note)
            promoted.update(promoted=True, promoted_source_id=source["id"])
            cursor.execute(
                "UPDATE notes SET promoted_source_id=%s, record=%s WHERE id=%s",
                (source["id"], Jsonb(promoted), note["id"]),
            )
            self._audit(
                cursor,
                "note.promoted",
                actor,
                case_id=note["case_id"],
                note_id=note["id"],
                source_id=source["id"],
                source_set_id=source_set["id"],
            )
            return promoted

    def ingest_promoted_note(self, note: Record, actor: str) -> Record:
        try:
            connection = self._owner._transaction.get()
            if connection is not None:
                return self._ingest_promoted_note(connection, note, actor)
            with self._owner._connect() as own_connection:
                return self._ingest_promoted_note(own_connection, note, actor)
        except psycopg.errors.UniqueViolation as exc:
            raise ValueError("source content already active") from exc

    def withdraw(self, case_id: str, source_id: str, actor: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM cases WHERE id=%s FOR UPDATE",
                    (case_id,),
                )
                if cursor.fetchone() is None:
                    return None
                cursor.execute(
                    "SELECT record FROM sources WHERE id=%s AND case_id=%s FOR UPDATE",
                    (source_id, case_id),
                )
                row = cursor.fetchone()
                if row is None or row[0].get("withdrawn"):
                    return None
                source = copy.deepcopy(row[0])
                source.update(withdrawn=True, withdrawn_at=now_iso())
                cursor.execute(
                    "UPDATE sources SET withdrawn=true, withdrawn_at=%s, record=%s "
                    "WHERE id=%s",
                    (source["withdrawn_at"], Jsonb(source), source_id),
                )
                self._append_source_set(cursor, case_id, actor, remove_id=source_id)
                cursor.execute(
                    "SELECT id, record FROM assumptions WHERE case_id=%s FOR UPDATE",
                    (case_id,),
                )
                for assumption_id, record in cursor.fetchall():
                    if source_id in record.get("evidence_ids", []):
                        updated = copy.deepcopy(record)
                        updated.update(stale=True, status="STALE")
                        cursor.execute(
                            "UPDATE assumptions SET status='STALE', record=%s WHERE id=%s",
                            (Jsonb(updated), assumption_id),
                        )
                cursor.execute(
                    "SELECT id, record FROM rv_loan_universes WHERE case_id=%s "
                    "AND source_id=%s AND status='ACTIVE' FOR UPDATE",
                    (case_id, source_id),
                )
                loan = cursor.fetchone()
                if loan:
                    loan_record = copy.deepcopy(loan[1])
                    loan_record.update(status="WITHDRAWN", withdrawn_at=now_iso())
                    cursor.execute(
                        "UPDATE rv_loan_universes SET status='WITHDRAWN', "
                        "withdrawn_at=%s, record=%s WHERE id=%s",
                        (
                            loan_record["withdrawn_at"],
                            Jsonb(loan_record),
                            loan[0],
                        ),
                    )
                    self._audit(
                        cursor,
                        "rv.loan_universe.withdrawn",
                        actor,
                        case_id=case_id,
                        source_id=source_id,
                        universe_id=loan[0],
                    )
                self._audit(
                    cursor,
                    "source.withdrawn",
                    actor,
                    case_id=case_id,
                    source_id=source_id,
                )
                return _public_source(source)

    def list_sources(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM sources WHERE case_id=%s AND withdrawn=false "
                    "ORDER BY created_at, id",
                    (case_id,),
                )
                return [_public_source(row[0]) for row in cursor.fetchall()]

    def get_source(self, source_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT record FROM sources WHERE id=%s", (source_id,))
                row = cursor.fetchone()
                return _public_source(row[0]) if row else None

    def read_source_bytes(self, source_id: str, limit: int) -> bytes:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT vault_path FROM sources WHERE id=%s", (source_id,)
                )
                row = cursor.fetchone()
        path = Path(row[0]) if row and isinstance(row[0], str) else None
        if path is None or not path.is_file():
            raise FileNotFoundError("SOURCE_BYTES_UNAVAILABLE")
        with path.open("rb") as stored:
            return stored.read(limit)

    def current_source_set(self, case_id: str) -> Record | None:
        connection = self._owner._transaction.get()
        if connection is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT source_sets.record FROM cases JOIN source_sets ON "
                    "source_sets.id=cases.current_source_set_id WHERE cases.id=%s",
                    (case_id,),
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None
        with self._owner._connect() as own_connection:
            with own_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT source_sets.record FROM cases JOIN source_sets ON "
                    "source_sets.id=cases.current_source_set_id WHERE cases.id=%s",
                    (case_id,),
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def source_set(self, source_set_id: str | None) -> Record | None:
        if not source_set_id:
            return None
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM source_sets WHERE id=%s", (source_set_id,)
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def read_pinned_evidence(
        self,
        case_id: str,
        source_set_id: str,
        source_id: str,
        block_ids: list[str],
    ) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT source_sets.record, sources.record FROM source_sets "
                    "LEFT JOIN sources ON sources.id=%s WHERE source_sets.id=%s",
                    (source_id, source_set_id),
                )
                row = cursor.fetchone()
                source_set, source = row if row else (None, None)
                if (
                    not source_set
                    or source_set.get("case_id") != case_id
                    or source_id not in source_set.get("source_ids", [])
                    or not source
                    or source.get("case_id") != case_id
                    or source.get("withdrawn")
                ):
                    raise ValueError("AGENT_AUTHORITY_MISMATCH")
                blocks = {
                    block.get("block_id"): block for block in source.get("blocks", [])
                }
                if any(block_id not in blocks for block_id in block_ids):
                    raise ValueError("AGENT_OUTPUT_INVALID")
                return [
                    {
                        "source_id": source_id,
                        "source_digest": source["sha256"],
                        "origin_family": source.get("origin_family", source["sha256"]),
                        "authority_class": source.get(
                            "authority_class", "unclassified"
                        ),
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
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM rv_loan_universes WHERE case_id=%s AND "
                    "source_sha256=%s AND template_version=%s AND importer_version=%s",
                    (case_id, source_sha256, template_version, importer_version),
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def save_loan_universe_import(
        self, record: Record, rows: list[Record], actor: str
    ) -> tuple[Record, bool]:
        proposal = copy.deepcopy(record)
        proposal["id"] = _new_id("rvloan")
        stored_rows = copy.deepcopy(rows)
        if proposal.get("status") not in {"ACTIVE", "REJECTED"}:
            raise ValueError("RV_UNIVERSE_STATUS_INVALID")
        if proposal["status"] == "ACTIVE":
            if proposal.get("row_count") != len(stored_rows) or len(
                {row.get("instrument_key") for row in stored_rows}
            ) != len(stored_rows):
                raise ValueError("RV_UNIVERSE_ROWS_INVALID")
        elif stored_rows:
            raise ValueError("RV_REJECTED_UNIVERSE_HAS_ROWS")
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM cases WHERE id=%s FOR UPDATE",
                    (proposal.get("case_id"),),
                )
                cursor.execute(
                    "SELECT record FROM sources WHERE id=%s AND case_id=%s "
                    "AND withdrawn=false FOR UPDATE",
                    (proposal.get("source_id"), proposal.get("case_id")),
                )
                if cursor.fetchone() is None:
                    raise ValueError("RV_SOURCE_NOT_ACTIVE")
                cursor.execute(
                    "SELECT record FROM rv_loan_universes WHERE case_id=%s AND "
                    "source_sha256=%s AND template_version=%s AND importer_version=%s",
                    (
                        proposal["case_id"],
                        proposal["source_sha256"],
                        proposal["template_version"],
                        proposal["importer_version"],
                    ),
                )
                existing = cursor.fetchone()
                if existing:
                    return copy.deepcopy(existing[0]), False
                proposal.setdefault("created_at", now_iso())
                proposal.setdefault("created_by", actor)
                if proposal["status"] == "ACTIVE":
                    cursor.execute(
                        "SELECT id, record FROM rv_loan_universes WHERE case_id=%s "
                        "AND status='ACTIVE' FOR UPDATE",
                        (proposal["case_id"],),
                    )
                    previous = cursor.fetchone()
                    cursor.execute(
                        "SELECT COALESCE(MAX(version), 0) FROM rv_loan_universes "
                        "WHERE case_id=%s",
                        (proposal["case_id"],),
                    )
                    proposal.update(
                        version=cursor.fetchone()[0] + 1,
                        activated_at=now_iso(),
                        superseded_at=None,
                        withdrawn_at=None,
                    )
                    if previous:
                        previous_record = copy.deepcopy(previous[1])
                        previous_record.update(
                            status="SUPERSEDED",
                            superseded_at=proposal["activated_at"],
                        )
                        cursor.execute(
                            "UPDATE rv_loan_universes SET status='SUPERSEDED', "
                            "superseded_at=%s, record=%s WHERE id=%s",
                            (
                                proposal["activated_at"],
                                Jsonb(previous_record),
                                previous[0],
                            ),
                        )
                    action = "rv.loan_universe.activated"
                else:
                    proposal.update(
                        version=None,
                        activated_at=None,
                        superseded_at=None,
                        withdrawn_at=None,
                    )
                    action = "rv.loan_universe.rejected"
                cursor.execute(
                    "INSERT INTO rv_loan_universes(id, case_id, source_id, "
                    "source_sha256, workbook_date, template_version, importer_version, "
                    "universe_digest, row_count, version, status, record, created_by, "
                    "created_at, activated_at, superseded_at, withdrawn_at) VALUES "
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        proposal["id"],
                        proposal["case_id"],
                        proposal["source_id"],
                        proposal["source_sha256"],
                        proposal.get("workbook_date"),
                        proposal["template_version"],
                        proposal["importer_version"],
                        proposal.get("universe_digest"),
                        proposal.get("row_count", 0),
                        proposal.get("version"),
                        proposal["status"],
                        Jsonb(proposal),
                        proposal["created_by"],
                        proposal["created_at"],
                        proposal.get("activated_at"),
                        proposal.get("superseded_at"),
                        proposal.get("withdrawn_at"),
                    ),
                )
                for row in stored_rows:
                    cursor.execute(
                        "INSERT INTO rv_loan_rows(universe_id, instrument_key, record) "
                        "VALUES (%s, %s, %s)",
                        (proposal["id"], row["instrument_key"], Jsonb(row)),
                    )
                self._audit(
                    cursor,
                    action,
                    actor,
                    case_id=proposal["case_id"],
                    source_id=proposal["source_id"],
                    universe_id=proposal["id"],
                )
                return copy.deepcopy(proposal), True

    def active_loan_universe(
        self, case_id: str, *, include_rows: bool = True
    ) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, record FROM rv_loan_universes WHERE case_id=%s "
                    "AND status='ACTIVE'",
                    (case_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                result = copy.deepcopy(row[1])
                if include_rows:
                    cursor.execute(
                        "SELECT record FROM rv_loan_rows WHERE universe_id=%s "
                        "ORDER BY instrument_key",
                        (row[0],),
                    )
                    result["rows"] = [item[0] for item in cursor.fetchall()]
                return result


class _PostgresRunLedger(_Adapter):
    def _save_case(self, cursor: Any, case: Record) -> None:
        cursor.execute(
            "UPDATE cases SET current_execution_id=%s, accepted_snapshot_id=%s, "
            "visible_snapshot_id=%s, record=%s WHERE id=%s",
            (
                case.get("current_execution_id"),
                case.get("accepted_snapshot_id"),
                case.get("visible_snapshot_id"),
                Jsonb(case),
                case["id"],
            ),
        )

    def _save_run(self, cursor: Any, run: Record) -> None:
        cursor.execute(
            "UPDATE runs SET status=%s, plan=%s, accepted_snapshot_id=%s, "
            "current_node_id=%s, research=%s, error=%s, record=%s WHERE id=%s",
            (
                run["status"],
                Jsonb(run.get("plan", {})),
                run.get("accepted_snapshot_id"),
                run.get("current_node_id"),
                Jsonb(run.get("research")),
                Jsonb(run.get("error")),
                Jsonb(run),
                run["id"],
            ),
        )

    def _save_node(self, cursor: Any, node: Record) -> None:
        cursor.execute(
            "UPDATE workflow_nodes SET status=%s, attempt=%s, attempt_token=%s, "
            "lease_until=%s, artifact_id=%s, error=%s, stage=%s, record=%s WHERE id=%s",
            (
                node["status"],
                node.get("attempt", 0),
                node.get("attempt_token"),
                node.get("lease_until"),
                node.get("artifact_id"),
                Jsonb(node.get("error")),
                node.get("stage", 0),
                Jsonb(node),
                node["id"],
            ),
        )

    def _emit(self, cursor: Any, run_id: str, event: str, data: Record) -> Record:
        cursor.execute("SELECT 1 FROM runs WHERE id=%s FOR UPDATE", (run_id,))
        if cursor.fetchone() is None:
            raise ValueError("RUN_NOT_FOUND")
        cursor.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM workflow_events WHERE run_id=%s",
            (run_id,),
        )
        sequence = cursor.fetchone()[0]
        record = {
            "id": sequence,
            "event": event,
            "at": now_iso(),
            "data": copy.deepcopy(data),
        }
        cursor.execute(
            "INSERT INTO workflow_events(run_id, sequence, event, record, created_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (run_id, sequence, event, Jsonb(record), record["at"]),
        )
        return record

    def _assert_job(self, cursor: Any, run_id: str, attempt_token: str) -> None:
        cursor.execute(
            "SELECT id FROM jobs WHERE run_id=%s AND node_id IS NULL "
            "AND state='claimed' AND attempt_token=%s AND lease_until > now() FOR UPDATE",
            (run_id, attempt_token),
        )
        if cursor.fetchone() is None:
            raise JobFencedError("stale workflow attempt")

    def create_case(self, name: str, issuer: str, sector: str, actor: str) -> Record:
        case = {
            "id": _new_id("case"),
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
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cases(id, name, issuer, sector, created_by, created_at, "
                    "record) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        case["id"],
                        name,
                        issuer,
                        sector,
                        actor,
                        case["created_at"],
                        Jsonb(case),
                    ),
                )
                cursor.execute(
                    "INSERT INTO case_members(case_id, subject, role) VALUES (%s, %s, 'ANALYST')",
                    (case["id"], actor),
                )
                self._audit(cursor, "case.created", actor, case_id=case["id"])
        return copy.deepcopy(case)

    def list_cases(self, actor: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT cases.record FROM cases JOIN case_members ON "
                    "case_members.case_id=cases.id WHERE case_members.subject=%s "
                    "ORDER BY cases.created_at, cases.id",
                    (actor,),
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def get_case(self, case_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT record FROM cases WHERE id=%s", (case_id,))
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def is_member(
        self, case_id: str, actor: str, roles: set[str] | None = None
    ) -> bool:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT role FROM case_members WHERE case_id=%s AND subject=%s",
                    (case_id, actor),
                )
                row = cursor.fetchone()
                return bool(row and (roles is None or row[0] in roles))

    def add_member(
        self,
        case_id: str,
        actor: str,
        member: str,
        role: str,
        actor_role: str | None = None,
    ) -> bool:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM cases WHERE id=%s FOR UPDATE", (case_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return False
                case = copy.deepcopy(row[0])
                if actor_role != "ADMIN" and case.get("members", {}).get(actor) not in {
                    "ADMIN",
                    "APPROVER",
                }:
                    return False
                case.setdefault("members", {})[member] = role
                cursor.execute(
                    "INSERT INTO case_members(case_id, subject, role) VALUES (%s, %s, %s) "
                    "ON CONFLICT (case_id, subject) DO UPDATE SET role=EXCLUDED.role",
                    (case_id, member, role),
                )
                self._save_case(cursor, case)
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
        initial: Record | None = None,
    ) -> Record:
        _validate_run_nodes(nodes)
        initial = copy.deepcopy(initial or {})
        created_at = initial.pop("created_at", now_iso())
        run_id = _new_id("run")
        node_records = [
            {
                "id": _new_id("node"),
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
            for node in copy.deepcopy(nodes)
        ]
        run = {
            "id": run_id,
            "case_id": case_id,
            "created_by": actor,
            "created_at": created_at,
            "status": "queued",
            "plan": copy.deepcopy(plan),
            "node_ids": [node["id"] for node in node_records],
            "current_node_id": None,
            "accepted_snapshot_id": None,
            "upgraded_from_run_id": upgraded_from_run_id,
            "error": None,
            **initial,
        }
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM cases WHERE id=%s FOR UPDATE", (case_id,)
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("CASE_NOT_FOUND")
                case = copy.deepcopy(row[0])
                cursor.execute(
                    "INSERT INTO runs(id, case_id, status, plan, accepted_snapshot_id, "
                    "created_by, created_at, error, current_node_id, upgraded_from_run_id, "
                    "research, record) VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, "
                    "NULL, %s, %s, %s)",
                    (
                        run_id,
                        case_id,
                        run["status"],
                        Jsonb(run["plan"]),
                        actor,
                        created_at,
                        Jsonb(run.get("error")),
                        upgraded_from_run_id,
                        Jsonb(run.get("research")),
                        Jsonb(run),
                    ),
                )
                for node in node_records:
                    cursor.execute(
                        "INSERT INTO workflow_nodes(id, run_id, module_id, dependencies, "
                        "status, attempt, artifact_id, error, stage, record) VALUES "
                        "(%s, %s, %s, %s, %s, 0, NULL, NULL, %s, %s)",
                        (
                            node["id"],
                            run_id,
                            node["module_id"],
                            Jsonb(node["dependencies"]),
                            node["status"],
                            node["stage"],
                            Jsonb(node),
                        ),
                    )
                cursor.execute(
                    "INSERT INTO jobs(run_id, node_id, state, actor, budget_reserved) "
                    "VALUES (%s, NULL, 'queued', %s, 0)",
                    (run_id, actor),
                )
                case["current_execution_id"] = run_id
                self._save_case(cursor, case)
                self._audit(
                    cursor, "run.created", actor, case_id=case_id, run_id=run_id
                )
        return {
            **copy.deepcopy(run),
            "nodes": copy.deepcopy(node_records),
            "events": [],
        }

    def list_runs(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM runs WHERE case_id=%s ORDER BY created_at, id",
                    (case_id,),
                )
                ids = [row[0] for row in cursor.fetchall()]
        return [run for run_id in ids if (run := self.get_run(run_id)) is not None]

    def get_run(self, run_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT record FROM runs WHERE id=%s", (run_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                run = copy.deepcopy(row[0])
                cursor.execute(
                    "SELECT id, record FROM workflow_nodes WHERE run_id=%s",
                    (run_id,),
                )
                nodes = {item[0]: item[1] for item in cursor.fetchall()}
                run["nodes"] = [
                    copy.deepcopy(nodes[node_id]) for node_id in run.get("node_ids", [])
                ]
                cursor.execute(
                    "SELECT record FROM workflow_events WHERE run_id=%s ORDER BY sequence",
                    (run_id,),
                )
                run["events"] = [copy.deepcopy(item[0]) for item in cursor.fetchall()]
                return run

    def latest_run(self, case_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM runs WHERE case_id=%s ORDER BY created_at DESC, id DESC LIMIT 1",
                    (case_id,),
                )
                row = cursor.fetchone()
        return self.get_run(row[0]) if row else None

    def pending_runs(self) -> list[tuple[str, str]]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, created_by FROM runs WHERE status IN ('queued', 'running') "
                    "ORDER BY created_at, id"
                )
                return list(cursor.fetchall())

    def claim(self, run_id: str, worker: str) -> str | None:
        token = _new_id("attempt")
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM jobs WHERE run_id=%s AND node_id IS NULL AND "
                    "(state='queued' OR (state='claimed' AND lease_until <= now())) "
                    "ORDER BY CASE state WHEN 'queued' THEN 0 ELSE 1 END, id "
                    "LIMIT 1 FOR UPDATE SKIP LOCKED",
                    (run_id,),
                )
                job = cursor.fetchone()
                if not job:
                    return None
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext('caos:workflow-budget'))"
                )
                cursor.execute(
                    "SELECT (SELECT count(*) FROM jobs WHERE state='claimed' AND lease_until > now()) + "
                    "(SELECT count(*) FROM model_build_jobs WHERE state='claimed' AND lease_until > now())"
                )
                if cursor.fetchone()[0] >= MAX_ACTIVE_JOBS:
                    return None
                cursor.execute(
                    "UPDATE jobs SET state='claimed', worker_id=%s, attempt_token=%s, "
                    "lease_until=now() + (%s * interval '1 second'), budget_reserved=1 "
                    "WHERE id=%s",
                    (worker, token, self._owner._lease_seconds, job[0]),
                )
                cursor.execute(
                    "SELECT id, record FROM workflow_nodes WHERE run_id=%s "
                    "AND status='running' FOR UPDATE",
                    (run_id,),
                )
                for node_id, record in cursor.fetchall():
                    node = copy.deepcopy(record)
                    node.update(status="pending", artifact_id=None, error=None)
                    self._save_node(cursor, node)
                return token

    def renew(self, run_id: str, attempt_token: str) -> bool:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET lease_until=now() + (%s * interval '1 second') "
                    "WHERE run_id=%s AND node_id IS NULL AND state='claimed' "
                    "AND attempt_token=%s AND lease_until > now() RETURNING id",
                    (self._owner._lease_seconds, run_id, attempt_token),
                )
                return cursor.fetchone() is not None

    def is_current(self, run_id: str, attempt_token: str) -> bool:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM jobs WHERE run_id=%s AND node_id IS NULL "
                    "AND state='claimed' AND attempt_token=%s AND lease_until > now()",
                    (run_id, attempt_token),
                )
                return cursor.fetchone() is not None

    def finish(self, run_id: str, attempt_token: str) -> None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET state='succeeded', lease_until=NULL, budget_reserved=0 "
                    "WHERE run_id=%s AND node_id IS NULL AND state='claimed' "
                    "AND attempt_token=%s AND lease_until > now()",
                    (run_id, attempt_token),
                )

    def update_run_fenced(
        self, run_id: str, attempt_token: str, **changes: Any
    ) -> None:
        updates = copy.deepcopy(changes)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._assert_job(cursor, run_id, attempt_token)
                cursor.execute(
                    "SELECT record FROM runs WHERE id=%s FOR UPDATE", (run_id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise JobFencedError("stale workflow attempt")
                run = copy.deepcopy(row[0])
                run.update(updates)
                self._save_run(cursor, run)

    def update_node_fenced(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        **changes: Any,
    ) -> None:
        updates = copy.deepcopy(changes)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._assert_job(cursor, run_id, attempt_token)
                cursor.execute(
                    "SELECT record FROM workflow_nodes WHERE id=%s AND run_id=%s FOR UPDATE",
                    (node_id, run_id),
                )
                row = cursor.fetchone()
                if not row:
                    raise JobFencedError("node does not belong to run")
                node = copy.deepcopy(row[0])
                node.update(updates)
                self._save_node(cursor, node)

    def pause_research_plan(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        research: Record,
    ) -> None:
        stored_research = copy.deepcopy(research)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._assert_job(cursor, run_id, attempt_token)
                cursor.execute(
                    "SELECT record FROM workflow_nodes WHERE id=%s AND run_id=%s FOR UPDATE",
                    (node_id, run_id),
                )
                node_row = cursor.fetchone()
                cursor.execute(
                    "SELECT record FROM runs WHERE id=%s FOR UPDATE", (run_id,)
                )
                run_row = cursor.fetchone()
                if not node_row or not run_row:
                    raise JobFencedError("node does not belong to run")
                node = copy.deepcopy(node_row[0])
                run = copy.deepcopy(run_row[0])
                node.update(status="pending", error=None)
                run.update(
                    status="paused",
                    current_node_id=None,
                    error={
                        "code": "PLAN_APPROVAL_REQUIRED",
                        "message": "Approve the proposed research plan before execution.",
                    },
                    research=stored_research,
                )
                self._save_node(cursor, node)
                self._save_run(cursor, run)

    def approve_research_plan(self, run_id: str, actor: str, plan_hash: str) -> Record:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM runs WHERE id=%s FOR UPDATE", (run_id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError("RUN_NOT_FOUND")
                run = copy.deepcopy(row[0])
                research = run.get("research")
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
                    "SELECT source_sets.record FROM cases LEFT JOIN source_sets ON "
                    "source_sets.id=cases.current_source_set_id WHERE cases.id=%s FOR UPDATE OF cases",
                    (run["case_id"],),
                )
                current_row = cursor.fetchone()
                current = current_row[0] if current_row else None
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
                run.update(status="queued", error=None, research=research)
                self._save_run(cursor, run)
                cursor.execute(
                    "UPDATE jobs SET state='queued', worker_id=NULL, attempt_token=NULL, "
                    "lease_until=NULL, budget_reserved=0 WHERE run_id=%s AND node_id IS NULL",
                    (run_id,),
                )
                self._audit(
                    cursor,
                    "research.plan_approved",
                    actor,
                    case_id=run["case_id"],
                    run_id=run_id,
                    plan_hash=plan_hash,
                )
                self._emit(
                    cursor,
                    run_id,
                    "research.plan_approved",
                    {"plan_hash": plan_hash, "approved_by": actor},
                )
        return self.get_run(run_id) or run

    def emit(self, run_id: str, event: str, data: Record) -> None:
        payload = copy.deepcopy(data)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._emit(cursor, run_id, event, payload)

    def emit_fenced(
        self, run_id: str, attempt_token: str, event: str, data: Record
    ) -> None:
        payload = copy.deepcopy(data)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._assert_job(cursor, run_id, attempt_token)
                self._emit(cursor, run_id, event, payload)

    def artifact_for_fingerprint(
        self, run_id: str, module_id: str, input_fingerprint: str
    ) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM artifacts WHERE run_id=%s AND module_id=%s "
                    "AND input_fingerprint=%s",
                    (run_id, module_id, input_fingerprint),
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def complete_node(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        artifact: Record,
        research: Record | None,
        event_data: Record,
        artifact_validator: Any = None,
    ) -> Record:
        proposal = copy.deepcopy(artifact)
        stored_research = copy.deepcopy(research) if research is not None else None
        event_payload = copy.deepcopy(event_data)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._assert_job(cursor, run_id, attempt_token)
                cursor.execute(
                    "SELECT record FROM workflow_nodes WHERE id=%s AND run_id=%s FOR UPDATE",
                    (node_id, run_id),
                )
                row = cursor.fetchone()
                if (
                    not row
                    or proposal.get("run_id") != run_id
                    or proposal.get("module_id") != row[0].get("module_id")
                ):
                    raise JobFencedError("artifact does not match the fenced node")
                node = copy.deepcopy(row[0])
                cursor.execute(
                    "SELECT record FROM artifacts WHERE run_id=%s AND module_id=%s "
                    "AND input_fingerprint=%s FOR UPDATE",
                    (run_id, node["module_id"], proposal.get("input_fingerprint")),
                )
                completed_row = cursor.fetchone()
                candidate = copy.deepcopy(
                    completed_row[0] if completed_row else proposal
                )
                replacing_invalid = bool(
                    completed_row is not None
                    and artifact_validator is not None
                    and not artifact_validator(candidate)
                )
                if replacing_invalid:
                    candidate = copy.deepcopy(proposal)
                if completed_row is None or replacing_invalid:
                    candidate["id"] = _new_id("art")
                if artifact_validator is not None and not artifact_validator(candidate):
                    raise ValueError("ARTIFACT_INVALID")
                if replacing_invalid:
                    cursor.execute(
                        "DELETE FROM artifacts WHERE id=%s",
                        (completed_row[0]["id"],),
                    )
                if completed_row is None or replacing_invalid:
                    cursor.execute(
                        "INSERT INTO artifacts(id, run_id, module_id, digest, payload, "
                        "markdown, input_fingerprint, created_at, record) VALUES "
                        "(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            candidate["id"],
                            run_id,
                            candidate["module_id"],
                            candidate["digest"],
                            Jsonb(candidate.get("payload")),
                            candidate.get("markdown", ""),
                            candidate["input_fingerprint"],
                            candidate.get("created_at", now_iso()),
                            Jsonb(candidate),
                        ),
                    )
                node.update(status="succeeded", artifact_id=candidate["id"], error=None)
                self._save_node(cursor, node)
                if research is not None:
                    cursor.execute(
                        "SELECT record FROM runs WHERE id=%s FOR UPDATE", (run_id,)
                    )
                    run = copy.deepcopy(cursor.fetchone()[0])
                    run["research"] = stored_research
                    self._save_run(cursor, run)
                self._emit(
                    cursor,
                    run_id,
                    "node.succeeded",
                    {**event_payload, "artifact_id": candidate["id"]},
                )
                return copy.deepcopy(candidate)

    def finalize_success(
        self,
        run_id: str,
        attempt_token: str,
        research: Record | None,
        event_data: Record,
        *,
        deadline: float | None = None,
    ) -> None:
        stored_research = copy.deepcopy(research) if research is not None else None
        event_payload = copy.deepcopy(event_data)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                self._assert_job(cursor, run_id, attempt_token)
                remaining = _remaining_finalization_seconds(deadline)
                if remaining is not None:
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        (f"{max(1, int(remaining * 1000 + 0.999))}ms",),
                    )
                cursor.execute(
                    "SELECT record FROM runs WHERE id=%s FOR UPDATE", (run_id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise JobFencedError("stale workflow attempt")
                run = copy.deepcopy(row[0])
                cursor.execute(
                    "SELECT node.record, artifact.record FROM workflow_nodes AS node "
                    "LEFT JOIN artifacts AS artifact ON artifact.id=node.artifact_id "
                    "WHERE node.run_id=%s FOR UPDATE OF node",
                    (run_id,),
                )
                for node, artifact in cursor.fetchall():
                    if (
                        node.get("status") != "succeeded"
                        or not artifact
                        or artifact.get("run_id") != run_id
                        or artifact.get("module_id") != node.get("module_id")
                    ):
                        raise ValueError("RUN_NOT_READY")
                _remaining_finalization_seconds(deadline)
                run.update(status="succeeded", current_node_id=None, error=None)
                if research is not None:
                    run["research"] = stored_research
                self._save_run(cursor, run)
                self._emit(cursor, run_id, "run.succeeded", event_payload)
                _remaining_finalization_seconds(deadline)

    def get_artifact(self, artifact_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM artifacts WHERE id=%s", (artifact_id,)
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def accept_snapshot(
        self, case_id: str, run_id: str, actor: str, snapshot: Record
    ) -> Record:
        proposal = copy.deepcopy(snapshot)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record, current_source_set_id FROM cases WHERE id=%s FOR UPDATE",
                    (case_id,),
                )
                case_row = cursor.fetchone()
                cursor.execute(
                    "SELECT record FROM runs WHERE id=%s AND case_id=%s FOR UPDATE",
                    (run_id, case_id),
                )
                run_row = cursor.fetchone()
                if not case_row or not run_row:
                    raise ValueError("RUN_NOT_FOUND")
                case = copy.deepcopy(case_row[0])
                run = copy.deepcopy(run_row[0])
                accepted_id = run.get("accepted_snapshot_id")
                if accepted_id:
                    cursor.execute(
                        "SELECT record FROM accepted_snapshots WHERE id=%s",
                        (accepted_id,),
                    )
                    return copy.deepcopy(cursor.fetchone()[0])
                if run.get("status") != "succeeded":
                    raise ValueError("RUN_NOT_READY")
                if (
                    proposal.get("case_id") != case_id
                    or proposal.get("run_id") != run_id
                ):
                    raise ValueError("RUN_NOT_FOUND")
                source_set_id = proposal.get("source_set_id")
                cursor.execute(
                    "SELECT record FROM source_sets WHERE id=%s", (source_set_id,)
                )
                source_row = cursor.fetchone()
                source_set = source_row[0] if source_row else None
                if (
                    not source_set
                    or source_set.get("case_id") != case_id
                    or source_set_id != run.get("plan", {}).get("source_set_id")
                    or proposal.get("source_set_version") != source_set.get("version")
                ):
                    raise ValueError("SOURCE_SET_CHANGED")
                artifact_refs = proposal.get("artifacts")
                if not isinstance(artifact_refs, list):
                    raise ValueError("RUN_NOT_READY")
                cursor.execute(
                    "SELECT record FROM workflow_nodes WHERE run_id=%s ORDER BY id",
                    (run_id,),
                )
                nodes = [row[0] for row in cursor.fetchall()]
                expected_ids = [node.get("artifact_id") for node in nodes]
                reference_ids = [
                    item.get("id") if isinstance(item, dict) else None
                    for item in artifact_refs
                ]
                if (
                    len(artifact_refs) != len(expected_ids)
                    or any(not isinstance(item, dict) for item in artifact_refs)
                    or len(set(reference_ids)) != len(reference_ids)
                    or set(reference_ids) != set(expected_ids)
                ):
                    raise ValueError("RUN_NOT_READY")
                artifact_ids = [item.get("id") for item in artifact_refs]
                artifacts: dict[str, Record] = {}
                if artifact_ids:
                    cursor.execute(
                        "SELECT id, record FROM artifacts WHERE id = ANY(%s)",
                        (artifact_ids,),
                    )
                    artifacts = {row[0]: row[1] for row in cursor.fetchall()}
                for item in artifact_refs:
                    artifact = artifacts.get(item.get("id"))
                    if (
                        not artifact
                        or artifact.get("case_id") not in {None, case_id}
                        or artifact.get("run_id") != run_id
                        or item.get("module_id") != artifact.get("module_id")
                        or item.get("digest") != artifact.get("digest")
                    ):
                        raise ValueError("RUN_NOT_READY")
                    try:
                        if artifact["digest"] != digest(artifact.get("payload")):
                            raise ValueError("RUN_NOT_READY")
                    except (KeyError, TypeError, ValueError):
                        raise ValueError("RUN_NOT_READY") from None
                payload = proposal.copy()
                payload.pop("digest", None)
                try:
                    valid_digest = proposal.get("digest") == digest(payload)
                except (TypeError, ValueError):
                    valid_digest = False
                if not valid_digest:
                    raise ValueError("RUN_NOT_READY")
                proposal["id"] = _new_id("snap")
                proposal["previous_snapshot_id"] = case.get("accepted_snapshot_id")
                cursor.execute(
                    "INSERT INTO accepted_snapshots(id, case_id, run_id, digest, "
                    "source_set_id, source_set_version, artifact_refs, previous_snapshot_id, "
                    "accepted_at, record) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        proposal["id"],
                        case_id,
                        run_id,
                        proposal["digest"],
                        source_set_id,
                        proposal.get("source_set_version"),
                        Jsonb(artifact_refs),
                        proposal.get("previous_snapshot_id"),
                        proposal.get("accepted_at", now_iso()),
                        Jsonb(proposal),
                    ),
                )
                case["accepted_snapshot_id"] = proposal["id"]
                if not case.get("visible_snapshot_id"):
                    case["visible_snapshot_id"] = proposal["id"]
                run["accepted_snapshot_id"] = proposal["id"]
                self._save_case(cursor, case)
                self._save_run(cursor, run)
                self._audit(
                    cursor,
                    "snapshot.accepted",
                    actor,
                    case_id=case_id,
                    run_id=run_id,
                    snapshot_id=proposal["id"],
                )
                self._emit(
                    cursor,
                    run_id,
                    "snapshot.accepted",
                    {"snapshot_id": proposal["id"], "digest": proposal["digest"]},
                )
                return copy.deepcopy(proposal)

    def get_snapshot(self, snapshot_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM accepted_snapshots WHERE id=%s", (snapshot_id,)
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def switch_visible_snapshot(
        self, case_id: str, snapshot_id: str, actor: str
    ) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM cases WHERE id=%s FOR UPDATE", (case_id,)
                )
                case_row = cursor.fetchone()
                cursor.execute(
                    "SELECT record FROM accepted_snapshots WHERE id=%s AND case_id=%s",
                    (snapshot_id, case_id),
                )
                snapshot_row = cursor.fetchone()
                if not case_row or not snapshot_row:
                    return None
                case = copy.deepcopy(case_row[0])
                case["visible_snapshot_id"] = snapshot_id
                self._save_case(cursor, case)
                self._audit(
                    cursor,
                    "snapshot.visible_switched",
                    actor,
                    case_id=case_id,
                    snapshot_id=snapshot_id,
                )
                return copy.deepcopy(snapshot_row[0])

    def events_after(self, run_id: str, cursor: int = 0) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as db_cursor:
                db_cursor.execute(
                    "SELECT record FROM workflow_events WHERE run_id=%s AND sequence>%s "
                    "ORDER BY sequence",
                    (run_id, cursor),
                )
                return [copy.deepcopy(row[0]) for row in db_cursor.fetchall()]

    def wait_for_events(
        self, run_id: str, cursor: int, timeout: float = 1.0
    ) -> list[Record]:
        deadline = time.monotonic() + timeout
        while True:
            events = self.events_after(run_id, cursor)
            if events or time.monotonic() >= deadline:
                return events
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


class _PostgresPublicationLedger(_Adapter):
    __slots__ = ("_sources",)

    def __init__(
        self, owner: PostgresLedgerSet, sources: _PostgresSourceCatalog
    ) -> None:
        super().__init__(owner)
        self._sources = sources

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
                "SELECT 1 FROM artifacts WHERE id=%s AND record->>'case_id'=%s",
                (ref, case_id),
            )
            if cursor.fetchone():
                continue
            if not artifacts_only:
                cursor.execute(
                    "SELECT withdrawn FROM sources WHERE id=%s AND case_id=%s",
                    (ref, case_id),
                )
                source = cursor.fetchone()
                if source:
                    if source[0]:
                        raise ValueError("EVIDENCE_SOURCE_WITHDRAWN")
                    continue
                cursor.execute(
                    "SELECT 1 FROM accepted_snapshots WHERE id=%s AND case_id=%s",
                    (ref, case_id),
                )
                if cursor.fetchone():
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
        if not isinstance(expected_version, int):
            raise ValueError("VERSION_CONFLICT")
        saved = copy.deepcopy(value)
        saved.update(
            id=_new_id("thesis" if table == "thesis_versions" else "rec"),
            case_id=case_id,
            author=actor,
            version=expected_version + 1,
            created_at=now_iso(),
        )
        query = (
            f"INSERT INTO {table}(case_id, version, value, author, created_at) "
            f"SELECT %s, %s, %s, %s, %s WHERE "
            f"(SELECT COALESCE(MAX(version), 0) FROM {table} WHERE case_id=%s)=%s "
            "RETURNING version"
        )
        cursor.execute(
            query,
            (
                case_id,
                saved["version"],
                Jsonb(saved),
                actor,
                saved["created_at"],
                case_id,
                expected_version,
            ),
        )
        if cursor.fetchone() is None:
            raise ValueError("VERSION_CONFLICT")
        return saved

    def append_thesis(
        self, case_id: str, actor: str, expected_version: int, thesis: Record
    ) -> Record:
        proposal = copy.deepcopy(thesis)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM cases WHERE id=%s FOR UPDATE", (case_id,))
                self._validate_refs(
                    cursor, case_id, list(proposal.get("evidence_ids", []))
                )
                saved = self._append_version(
                    cursor,
                    "thesis_versions",
                    case_id,
                    actor,
                    expected_version,
                    proposal,
                )
                self._audit(
                    cursor,
                    "thesis.versioned",
                    actor,
                    case_id=case_id,
                    version=saved["version"],
                )
                return copy.deepcopy(saved)

    def list_theses(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT value FROM thesis_versions WHERE case_id=%s ORDER BY version",
                    (case_id,),
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def append_recommendations(
        self,
        case_id: str,
        actor: str,
        expected_version: int,
        recommendations: Record,
    ) -> Record:
        proposal = copy.deepcopy(recommendations)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM cases WHERE id=%s FOR UPDATE", (case_id,))
                self._validate_refs(
                    cursor,
                    case_id,
                    list(proposal.get("analytical_dependency_ids", [])),
                    artifacts_only=True,
                )
                proposal.update(
                    accepted_snapshot_id=proposal.get("accepted_snapshot_id"),
                    stale=False,
                    stale_reasons=[],
                )
                saved = self._append_version(
                    cursor,
                    "recommendation_versions",
                    case_id,
                    actor,
                    expected_version,
                    proposal,
                )
                self._audit(
                    cursor,
                    "recommendation.versioned",
                    actor,
                    case_id=case_id,
                    version=saved["version"],
                )
                return copy.deepcopy(saved)

    def list_recommendations(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT value FROM recommendation_versions WHERE case_id=%s ORDER BY version",
                    (case_id,),
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def save_report_inputs(
        self,
        case_id: str,
        actor: str,
        thesis: Record,
        recommendations: Record,
        accepted_snapshot_id: str | None,
    ) -> Record:
        thesis_proposal = copy.deepcopy(thesis)
        recommendation_proposal = copy.deepcopy(recommendations)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM cases WHERE id=%s FOR UPDATE", (case_id,))
                self._validate_refs(
                    cursor,
                    case_id,
                    list(thesis_proposal.get("evidence_ids", [])),
                )
                self._validate_refs(
                    cursor,
                    case_id,
                    list(recommendation_proposal.get("analytical_dependency_ids", [])),
                    artifacts_only=True,
                )
                thesis_expected = thesis_proposal.pop("expected_version", None)
                recommendation_expected = recommendation_proposal.pop(
                    "expected_version", None
                )
                saved_thesis = self._append_version(
                    cursor,
                    "thesis_versions",
                    case_id,
                    actor,
                    thesis_expected,
                    thesis_proposal,
                )
                recommendation_proposal.update(
                    accepted_snapshot_id=accepted_snapshot_id,
                    stale=False,
                    stale_reasons=[],
                )
                saved_recommendations = self._append_version(
                    cursor,
                    "recommendation_versions",
                    case_id,
                    actor,
                    recommendation_expected,
                    recommendation_proposal,
                )
                self._audit(
                    cursor,
                    "thesis.versioned",
                    actor,
                    case_id=case_id,
                    version=saved_thesis["version"],
                )
                self._audit(
                    cursor,
                    "recommendation.versioned",
                    actor,
                    case_id=case_id,
                    version=saved_recommendations["version"],
                )
                return {
                    "thesis": copy.deepcopy(saved_thesis),
                    "recommendations": copy.deepcopy(saved_recommendations),
                }

    def create_note(self, case_id: str, actor: str, body: str) -> Record:
        note = {
            "id": _new_id("note"),
            "case_id": case_id,
            "author": actor,
            "body": body,
            "promoted": False,
            "created_at": now_iso(),
        }
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO notes(id, case_id, author, promoted_source_id, record, "
                    "created_at) VALUES (%s, %s, %s, NULL, %s, %s)",
                    (
                        note["id"],
                        case_id,
                        actor,
                        Jsonb(note),
                        note["created_at"],
                    ),
                )
                self._audit(
                    cursor,
                    "note.created",
                    actor,
                    case_id=case_id,
                    note_id=note["id"],
                )
        return copy.deepcopy(note)

    def list_notes(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM notes WHERE case_id=%s ORDER BY created_at, id",
                    (case_id,),
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def promote_note(self, case_id: str, note_id: str, actor: str) -> Record:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM notes WHERE id=%s AND case_id=%s FOR UPDATE",
                    (note_id, case_id),
                )
                row = cursor.fetchone()
                if not row:
                    raise KeyError("NOTE_NOT_FOUND")
                note = copy.deepcopy(row[0])
                if note["author"] != actor:
                    raise PermissionError("only note author can promote")
                context = self._owner._transaction.set(connection)
                try:
                    return self._sources.ingest_promoted_note(note, actor)
                finally:
                    self._owner._transaction.reset(context)

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
        stored_evidence = list(evidence_ids)
        assumption = {
            "id": _new_id("assumption"),
            "case_id": case_id,
            "author": actor,
            "statement": statement,
            "supporting_claim": supporting_claim,
            "conflicting_claim": conflicting_claim,
            "evidence_ids": stored_evidence,
            "affected_module_ids": list(affected_module_ids),
            "status": "PROVISIONAL",
            "stale": False,
            "created_at": now_iso(),
        }
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM cases WHERE id=%s FOR UPDATE", (case_id,))
                self._validate_refs(cursor, case_id, stored_evidence)
                cursor.execute(
                    "INSERT INTO assumptions(id, case_id, status, evidence_ids, record, "
                    "created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        assumption["id"],
                        case_id,
                        assumption["status"],
                        Jsonb(stored_evidence),
                        Jsonb(assumption),
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
        return copy.deepcopy(assumption)

    def list_assumptions(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM assumptions WHERE case_id=%s ORDER BY created_at, id",
                    (case_id,),
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

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
        build = row[0] if row else None
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

    def _validate_report_authority(
        self, cursor: Any, case_id: str, report: Record
    ) -> None:
        content = report.get("content")
        if not isinstance(content, dict):
            raise ValueError("SNAPSHOT_REQUIRED")
        cursor.execute(
            "SELECT record, accepted_snapshot_id FROM cases WHERE id=%s", (case_id,)
        )
        case_row = cursor.fetchone()
        cursor.execute(
            "SELECT record FROM accepted_snapshots WHERE id=%s",
            (content.get("snapshot_id"),),
        )
        snapshot_row = cursor.fetchone()
        snapshot = snapshot_row[0] if snapshot_row else None
        snapshot_digest = content.get("snapshot_digest")
        if (
            not case_row
            or not snapshot
            or snapshot.get("case_id") != case_id
            or case_row[1] != snapshot.get("id")
            or report.get("snapshot_digest") != snapshot_digest
            or snapshot_digest != digest(snapshot)
        ):
            raise ValueError("SNAPSHOT_REQUIRED")
        cursor.execute(
            "SELECT value FROM thesis_versions WHERE case_id=%s ORDER BY version DESC LIMIT 1",
            (case_id,),
        )
        thesis_row = cursor.fetchone()
        cursor.execute(
            "SELECT value FROM recommendation_versions WHERE case_id=%s "
            "ORDER BY version DESC LIMIT 1",
            (case_id,),
        )
        recommendation_row = cursor.fetchone()
        if not thesis_row or not recommendation_row:
            raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")
        thesis = thesis_row[0]
        recommendation = recommendation_row[0]
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
        proposal = copy.deepcopy(report)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM cases WHERE id=%s FOR UPDATE", (case_id,))
                self._validate_report_authority(cursor, case_id, proposal)
                saved = copy.deepcopy(proposal)
                saved.update(
                    id=_new_id("report"),
                    case_id=case_id,
                    created_by=actor,
                    created_at=now_iso(),
                    status="PENDING_APPROVAL",
                )
                cursor.execute(
                    "INSERT INTO reports(id, case_id, status, digest, snapshot_digest, "
                    "value, created_by, created_at, preview_digest, input_fingerprint, "
                    "record) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (case_id) DO UPDATE SET id=EXCLUDED.id, "
                    "status=EXCLUDED.status, digest=EXCLUDED.digest, "
                    "snapshot_digest=EXCLUDED.snapshot_digest, value=EXCLUDED.value, "
                    "created_by=EXCLUDED.created_by, created_at=EXCLUDED.created_at, "
                    "preview_digest=EXCLUDED.preview_digest, "
                    "input_fingerprint=EXCLUDED.input_fingerprint, approved_by=NULL, "
                    "approved_at=NULL, approval_comment=NULL, record=EXCLUDED.record",
                    (
                        saved["id"],
                        case_id,
                        saved["status"],
                        saved["digest"],
                        saved["snapshot_digest"],
                        Jsonb(saved),
                        actor,
                        saved["created_at"],
                        saved.get("preview_digest"),
                        saved.get("input_fingerprint"),
                        Jsonb(saved),
                    ),
                )
                self._audit(
                    cursor,
                    "report.frozen",
                    actor,
                    case_id=case_id,
                    report_id=saved["id"],
                )
                return copy.deepcopy(saved)

    def get_report(self, case_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM reports WHERE case_id=%s", (case_id,)
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def approve_report(
        self,
        case_id: str,
        actor: str,
        expected_status: str,
        preview_digest: str,
        input_fingerprint: str,
        comment: str | None,
    ) -> Record:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM reports WHERE case_id=%s FOR UPDATE", (case_id,)
                )
                row = cursor.fetchone()
                report = copy.deepcopy(row[0]) if row else None
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
                report.update(
                    status="APPROVED",
                    approved_by=actor,
                    approved_at=now_iso(),
                    approval_comment=comment,
                )
                cursor.execute(
                    "UPDATE reports SET status='APPROVED', approved_by=%s, "
                    "approved_at=%s, approval_comment=%s, value=%s, record=%s "
                    "WHERE case_id=%s",
                    (
                        actor,
                        report["approved_at"],
                        comment,
                        Jsonb(report),
                        Jsonb(report),
                        case_id,
                    ),
                )
                self._audit(
                    cursor,
                    "report.approved",
                    actor,
                    case_id=case_id,
                    report_id=report["id"],
                )
                return copy.deepcopy(report)

    def save_rv_universe(self, case_id: str, actor: str, universe: Record) -> Record:
        proposal = copy.deepcopy(universe)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM cases WHERE id=%s FOR UPDATE", (case_id,))
                if cursor.fetchone() is None:
                    raise ValueError("CASE_NOT_FOUND")
                cursor.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM rv_universes WHERE case_id=%s",
                    (case_id,),
                )
                proposal.update(
                    id=_new_id("rv"),
                    case_id=case_id,
                    version=cursor.fetchone()[0] + 1,
                    created_at=now_iso(),
                )
                cursor.execute(
                    "INSERT INTO rv_universes(id, case_id, version, record, created_by, "
                    "created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        proposal["id"],
                        case_id,
                        proposal["version"],
                        Jsonb(proposal),
                        actor,
                        proposal["created_at"],
                    ),
                )
                self._audit(
                    cursor,
                    "rv.universe_versioned",
                    actor,
                    case_id=case_id,
                    version=proposal["version"],
                )
                return copy.deepcopy(proposal)

    def get_rv_universe(self, case_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM rv_universes WHERE case_id=%s "
                    "ORDER BY version DESC LIMIT 1",
                    (case_id,),
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def list_audit(self) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT payload FROM audit_events ORDER BY id")
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def create_methodology_draft(self, draft: Record, actor: str) -> Record:
        saved = copy.deepcopy(draft)
        saved.update(
            id=_new_id("draft"),
            status="DRAFT",
            created_by=actor,
            created_at=now_iso(),
        )
        saved.setdefault(
            "semantic_diff",
            {"before": saved.get("before"), "after": saved.get("after")},
        )
        saved["digest"] = digest(saved)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO methodology_drafts(id, status, record, created_by, "
                    "created_at) VALUES (%s, %s, %s, %s, %s)",
                    (
                        saved["id"],
                        saved["status"],
                        Jsonb(saved),
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
        return copy.deepcopy(saved)

    def list_methodology_drafts(self) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM methodology_drafts ORDER BY created_at, id"
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def validate_methodology_draft(self, draft_id: str, actor: str) -> Record:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM methodology_drafts WHERE id=%s FOR UPDATE",
                    (draft_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise KeyError("draft not found")
                draft = copy.deepcopy(row[0])
                if draft.get("before") == draft.get("after"):
                    raise ValueError(
                        "draft does not validate against the current authority"
                    )
                draft.update(
                    status="VALIDATED", validated_by=actor, validated_at=now_iso()
                )
                cursor.execute(
                    "UPDATE methodology_drafts SET status=%s, record=%s WHERE id=%s",
                    (draft["status"], Jsonb(draft), draft_id),
                )
                self._audit(
                    cursor, "methodology.draft_validated", actor, draft_id=draft_id
                )
                return copy.deepcopy(draft)

    def confirm_methodology_draft(
        self, draft_id: str, actor: str, signature: str
    ) -> Record:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM methodology_drafts WHERE id=%s FOR UPDATE",
                    (draft_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise KeyError("draft not found")
                draft = copy.deepcopy(row[0])
                if draft.get("status") != "VALIDATED":
                    raise ValueError("validated draft required")
                draft.update(
                    status="CONFIRMED_PENDING_SIGNED_AUTHORITY",
                    confirmed_by=actor,
                    confirmed_at=now_iso(),
                    signature=signature,
                )
                cursor.execute(
                    "UPDATE methodology_drafts SET status=%s, record=%s WHERE id=%s",
                    (draft["status"], Jsonb(draft), draft_id),
                )
                self._audit(
                    cursor,
                    "methodology.draft_confirmed",
                    actor,
                    draft_id=draft_id,
                    signature=signature,
                )
                return copy.deepcopy(draft)


class _PostgresModelLedger(_Adapter):
    def _save_build(self, cursor: Any, build: Record) -> None:
        cursor.execute(
            "UPDATE model_builds SET status=%s, record=%s, started_at=%s, "
            "completed_at=%s, updated_at=now() WHERE id=%s",
            (
                build["status"],
                Jsonb(build),
                build.get("started_at"),
                build.get("completed_at"),
                build["id"],
            ),
        )

    def _assert_job(
        self, cursor: Any, build_id: str, attempt_token: str, kind: str
    ) -> tuple[Record, str]:
        cursor.execute(
            "SELECT build.record, job.worker_id FROM model_build_jobs AS job "
            "JOIN model_builds AS build ON build.id=job.build_id "
            "WHERE job.build_id=%s AND job.kind=%s AND job.state='claimed' "
            "AND job.attempt_token=%s AND job.lease_until > now() FOR UPDATE OF job, build",
            (build_id, kind, attempt_token),
        )
        row = cursor.fetchone()
        if not row:
            raise JobFencedError("stale model attempt")
        return copy.deepcopy(row[0]), row[1]

    def queue_build(self, build: Record, actor: str) -> tuple[Record, bool]:
        case_id = build.get("case_id")
        run_id = build.get("accepted_run_id")
        snapshot_id = build.get("accepted_snapshot_id")
        source_set_id = build.get("source_set_id")
        fingerprint = build.get("input_fingerprint")
        fingerprint_is_valid = (
            isinstance(fingerprint, str)
            and len(fingerprint) == 64
            and all(character in "0123456789abcdef" for character in fingerprint)
        )
        proposal = copy.deepcopy(build)
        proposal["id"] = _new_id("model")
        with self._owner._connect() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT record FROM model_builds WHERE case_id=%s AND "
                        "input_fingerprint=%s",
                        (case_id, fingerprint),
                    )
                    existing = cursor.fetchone()
                    if existing:
                        return copy.deepcopy(existing[0]), False
                    cursor.execute(
                        "SELECT record FROM cases WHERE id=%s FOR UPDATE",
                        (case_id,),
                    )
                    case_row = cursor.fetchone()
                    case = case_row[0] if case_row else None
                    cursor.execute(
                        "SELECT record FROM runs WHERE id=%s",
                        (run_id,),
                    )
                    run_row = cursor.fetchone()
                    cursor.execute(
                        "SELECT record FROM accepted_snapshots WHERE id=%s",
                        (snapshot_id,),
                    )
                    snapshot_row = cursor.fetchone()
                    cursor.execute(
                        "SELECT record FROM source_sets WHERE id=%s",
                        (source_set_id,),
                    )
                    source_set_row = cursor.fetchone()
                    run = run_row[0] if run_row else None
                    snapshot = snapshot_row[0] if snapshot_row else None
                    source_set = source_set_row[0] if source_set_row else None
                    if (
                        not case
                        or case.get("accepted_snapshot_id") != snapshot_id
                        or not run
                        or run.get("case_id") != case_id
                        or run.get("status") != "succeeded"
                        or run.get("accepted_snapshot_id") != snapshot_id
                        or not snapshot
                        or snapshot.get("case_id") != case_id
                        or snapshot.get("run_id") != run_id
                        or snapshot.get("source_set_id") != source_set_id
                        or not source_set
                        or source_set.get("case_id") != case_id
                        or not fingerprint_is_valid
                    ):
                        raise ValueError("MODEL_BUILD_INVALID")
                    proposal.update(
                        status="QUEUED",
                        created_by=actor,
                        queued_at=proposal.get("queued_at") or now_iso(),
                        started_at=None,
                        completed_at=None,
                        error=None,
                        export={"status": "NOT_REQUESTED", "error": None},
                    )
                    cursor.execute(
                        "INSERT INTO model_builds(id, case_id, accepted_run_id, "
                        "accepted_snapshot_id, source_set_id, input_fingerprint, status, "
                        "record, created_by, queued_at, started_at, completed_at) VALUES "
                        "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL)",
                        (
                            proposal["id"],
                            case_id,
                            run_id,
                            snapshot_id,
                            source_set_id,
                            fingerprint,
                            proposal["status"],
                            Jsonb(proposal),
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
                        case_id=case_id,
                        build_id=proposal["id"],
                    )
                    return copy.deepcopy(proposal), True
            except psycopg.errors.UniqueViolation:
                connection.rollback()
        existing = self.get_build_for_fingerprint(case_id, fingerprint)
        if existing is None:
            raise RuntimeError("concurrent model build was not committed")
        return existing, False

    def get_build_for_fingerprint(
        self, case_id: str, input_fingerprint: str
    ) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM model_builds WHERE case_id=%s AND input_fingerprint=%s",
                    (case_id, input_fingerprint),
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def retry_build(self, build_id: str, actor: str) -> Record:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT build.record, job.state FROM model_builds AS build JOIN "
                    "model_build_jobs AS job ON job.build_id=build.id AND job.kind='calculate' "
                    "WHERE build.id=%s FOR UPDATE OF build, job",
                    (build_id,),
                )
                row = cursor.fetchone()
                if not row or row[0].get("status") != "FAILED" or row[1] != "failed":
                    raise ValueError("MODEL_RETRY_INVALID")
                build = copy.deepcopy(row[0])
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
                return copy.deepcopy(build)

    def get_build(self, build_id: str) -> Record | None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM model_builds WHERE id=%s", (build_id,)
                )
                row = cursor.fetchone()
                return copy.deepcopy(row[0]) if row else None

    def list_builds(self, case_id: str) -> list[Record]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM model_builds WHERE case_id=%s "
                    "ORDER BY queued_at DESC, id DESC",
                    (case_id,),
                )
                return [copy.deepcopy(row[0]) for row in cursor.fetchall()]

    def queue_export(self, build_id: str, actor: str) -> tuple[Record, bool]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM model_builds WHERE id=%s FOR UPDATE",
                    (build_id,),
                )
                row = cursor.fetchone()
                if not row or row[0].get("status") != "READY":
                    raise ValueError("MODEL_EXPORT_NOT_READY")
                build = copy.deepcopy(row[0])
                cursor.execute(
                    "SELECT state FROM model_build_jobs WHERE build_id=%s AND kind='export' "
                    "FOR UPDATE",
                    (build_id,),
                )
                job = cursor.fetchone()
                if job and job[0] in {"queued", "claimed", "succeeded"}:
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
                return copy.deepcopy(build), True

    def pending_jobs(self) -> list[tuple[str, str, str]]:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT job.build_id, job.actor, job.kind FROM model_build_jobs AS job "
                    "JOIN model_builds AS build ON build.id=job.build_id WHERE "
                    "job.state IN ('queued', 'claimed') ORDER BY job.created_at, "
                    "job.build_id, job.kind"
                )
                return list(cursor.fetchall())

    def claim(self, build_id: str, worker: str, kind: str = "calculate") -> str | None:
        token = _new_id("attempt")
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT job.state, job.lease_until > now(), build.record FROM "
                    "model_build_jobs AS job JOIN model_builds AS build ON "
                    "build.id=job.build_id WHERE job.build_id=%s AND job.kind=%s "
                    "FOR UPDATE OF job, build SKIP LOCKED",
                    (build_id, kind),
                )
                row = cursor.fetchone()
                if (
                    not row
                    or (row[0] == "claimed" and row[1])
                    or row[0]
                    not in {
                        "queued",
                        "claimed",
                    }
                ):
                    return None
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext('caos:workflow-budget'))"
                )
                cursor.execute(
                    "SELECT (SELECT count(*) FROM jobs WHERE state='claimed' AND lease_until > now()) + "
                    "(SELECT count(*) FROM model_build_jobs WHERE state='claimed' AND lease_until > now())"
                )
                if cursor.fetchone()[0] >= MAX_ACTIVE_JOBS:
                    return None
                build = copy.deepcopy(row[2])
                cursor.execute(
                    "UPDATE model_build_jobs SET state='claimed', worker_id=%s, "
                    "attempt_token=%s, lease_until=now() + (%s * interval '1 second'), "
                    "error=NULL, updated_at=now() WHERE build_id=%s AND kind=%s",
                    (worker, token, self._owner._lease_seconds, build_id, kind),
                )
                if kind == "calculate":
                    build.update(
                        status="BUILDING",
                        started_at=build.get("started_at") or now_iso(),
                    )
                else:
                    build["export"] = {
                        **build["export"],
                        "status": "EXPORTING",
                        "error": None,
                    }
                self._save_build(cursor, build)
                return token

    def renew(self, build_id: str, attempt_token: str, kind: str = "calculate") -> bool:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE model_build_jobs SET lease_until=now() + "
                    "(%s * interval '1 second'), updated_at=now() WHERE build_id=%s "
                    "AND kind=%s AND state='claimed' AND attempt_token=%s "
                    "AND lease_until > now() RETURNING build_id",
                    (self._owner._lease_seconds, build_id, kind, attempt_token),
                )
                return cursor.fetchone() is not None

    def is_current(
        self, build_id: str, attempt_token: str, kind: str = "calculate"
    ) -> bool:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM model_build_jobs WHERE build_id=%s AND kind=%s "
                    "AND state='claimed' AND attempt_token=%s AND lease_until > now()",
                    (build_id, kind, attempt_token),
                )
                return cursor.fetchone() is not None

    def complete(
        self,
        build_id: str,
        attempt_token: str,
        result: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record:
        proposal = copy.deepcopy(result)
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                build, _ = self._assert_job(cursor, build_id, attempt_token, kind)
                validated = _validated_model_result(build, proposal, kind)
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
                self._save_build(cursor, build)
                cursor.execute(
                    "UPDATE model_build_jobs SET state='succeeded', lease_until=NULL, "
                    "updated_at=now() WHERE build_id=%s AND kind=%s",
                    (build_id, kind),
                )
                self._audit(
                    cursor,
                    f"model.{kind}.succeeded",
                    actor,
                    case_id=build["case_id"],
                    build_id=build_id,
                )
                return copy.deepcopy(build)

    def fail(
        self,
        build_id: str,
        attempt_token: str,
        error: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record:
        stored_error = copy.deepcopy(error)
        if (
            not isinstance(stored_error, dict)
            or set(stored_error) != {"code", "detail"}
            or not isinstance(stored_error["code"], str)
            or len(stored_error["code"]) > 80
            or not isinstance(stored_error["detail"], str)
            or len(stored_error["detail"]) > 500
        ):
            raise ValueError("MODEL_ERROR_INVALID")
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                build, _ = self._assert_job(cursor, build_id, attempt_token, kind)
                if kind == "calculate":
                    build.update(
                        status="FAILED",
                        completed_at=now_iso(),
                        error=stored_error,
                    )
                else:
                    build["export"] = {
                        **build["export"],
                        "status": "FAILED",
                        "error": stored_error,
                    }
                self._save_build(cursor, build)
                cursor.execute(
                    "UPDATE model_build_jobs SET state='failed', lease_until=NULL, "
                    "error=%s, updated_at=now() WHERE build_id=%s AND kind=%s",
                    (Jsonb(stored_error), build_id, kind),
                )
                self._audit(
                    cursor,
                    f"model.{kind}.failed",
                    actor,
                    case_id=build["case_id"],
                    build_id=build_id,
                    code=stored_error["code"],
                )
                return copy.deepcopy(build)

    def record_export_download(self, build_id: str, case_id: str, actor: str) -> None:
        with self._owner._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record FROM model_builds WHERE id=%s AND case_id=%s",
                    (build_id, case_id),
                )
                row = cursor.fetchone()
                if not row or (row[0].get("export") or {}).get("status") != "READY":
                    raise ValueError("MODEL_EXPORT_NOT_READY")
                self._audit(
                    cursor,
                    "model.export.downloaded",
                    actor,
                    case_id=case_id,
                    build_id=build_id,
                )


class PostgresLedgerSet:
    """Four narrow adapters backed only by normalized PostgreSQL tables."""

    __slots__ = (
        "_database_url",
        "_lease_seconds",
        "_transaction",
        "sources",
        "runs",
        "publications",
        "models",
    )

    def __init__(self, database_url: str, *, lease_seconds: float = 60.0) -> None:
        self._database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://"
        )
        self._lease_seconds = lease_seconds
        self._transaction: ContextVar[Any | None] = ContextVar(
            f"postgres-ledger-transaction-{id(self)}", default=None
        )
        with self._connect() as connection:
            apply_migrations(connection, Path(__file__).parent.parent / "migrations")
        sources = _PostgresSourceCatalog(self)
        self.sources = sources
        self.runs = _PostgresRunLedger(self)
        self.publications = _PostgresPublicationLedger(self, sources)
        self.models = _PostgresModelLedger(self)

    def _connect(self) -> Any:
        return psycopg.connect(self._database_url)
