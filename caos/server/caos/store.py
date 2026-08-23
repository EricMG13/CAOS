from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JobFencedError(RuntimeError):
    """Raised when a worker tries to write after its lease has expired."""


MAX_ACTIVE_JOBS = 20


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class MemoryStore:
    """Small deterministic store for the local app and contract tests.

    Production deployment supplies PostgreSQL for the records and jobs tables;
    keeping this adapter explicit makes the clean-slate vertical slice runnable
    without silently introducing SQLite production support.
    """

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.cases: dict[str, dict[str, Any]] = {}
        self.sources: dict[str, dict[str, Any]] = {}
        self.source_sets: dict[str, dict[str, Any]] = {}
        self.source_set_history: dict[str, dict[str, Any]] = {}
        self.runs: dict[str, dict[str, Any]] = {}
        self.nodes: dict[str, dict[str, Any]] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.theses: dict[str, list[dict[str, Any]]] = {}
        self.recommendations: dict[str, list[dict[str, Any]]] = {}
        self.notes: dict[str, list[dict[str, Any]]] = {}
        self.assumptions: dict[str, list[dict[str, Any]]] = {}
        self.reports: dict[str, dict[str, Any]] = {}
        self.methodology_drafts: dict[str, dict[str, Any]] = {}
        self.rv_universes: dict[str, dict[str, Any]] = {}
        self.audit: list[dict[str, Any]] = []
        self.events: dict[str, list[dict[str, Any]]] = {}
        self.event_conditions: dict[str, threading.Condition] = {}
        self.jobs: dict[str, dict[str, Any]] = {}

    def persist(self) -> None:
        """Persistence hook; the development adapter intentionally does nothing."""

    def refresh(self) -> None:
        """Persistence hook; the development adapter is already authoritative."""

    def _id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    def audit_event(self, action: str, actor: str, **details: Any) -> None:
        with self.lock:
            self.audit.append({"id": self._id("aud"), "action": action, "actor": actor, "at": now_iso(), **details})

    def create_case(self, name: str, issuer: str, sector: str, actor: str) -> dict[str, Any]:
        with self.lock:
            case = {
                "id": self._id("case"),
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
            self.cases[case["id"]] = case
            self.audit_event("case.created", actor, case_id=case["id"])
            self.persist()
            return copy.deepcopy(case)

    def list_cases(self, actor: str) -> list[dict[str, Any]]:
        with self.lock:
            return [copy.deepcopy(c) for c in self.cases.values() if actor in c["members"] or c["members"].get(actor) == "ADMIN"]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self.lock:
            case = self.cases.get(case_id)
            return copy.deepcopy(case) if case else None

    def is_member(self, case_id: str, actor: str, roles: set[str] | None = None) -> bool:
        with self.lock:
            case = self.cases.get(case_id)
            if not case:
                return False
            role = case["members"].get(actor)
            return role is not None and (roles is None or role in roles)

    def add_member(self, case_id: str, actor: str, member: str, role: str, actor_role: str | None = None) -> bool:
        with self.lock:
            case = self.cases.get(case_id)
            if not case or (actor_role != "ADMIN" and case["members"].get(actor) not in {"ADMIN", "APPROVER"}):
                return False
            case["members"][member] = role
            self.audit_event("case.member_added", actor, case_id=case_id, member=member, role=role)
            self.persist()
            return True

    def create_run(self, case_id: str, actor: str, plan: dict[str, Any], node_ids: list[str], upgraded_from_run_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            run = {
                "id": self._id("run"),
                "case_id": case_id,
                "created_by": actor,
                "created_at": now_iso(),
                "status": "planning",
                "plan": copy.deepcopy(plan),
                "node_ids": list(node_ids),
                "current_node_id": None,
                "accepted_snapshot_id": None,
                "upgraded_from_run_id": upgraded_from_run_id,
                "error": None,
            }
            self.runs[run["id"]] = run
            self.events[run["id"]] = []
            self.event_conditions[run["id"]] = threading.Condition(self.lock)
            self.audit_event("run.created", actor, case_id=case_id, run_id=run["id"])
            self.persist()
            return copy.deepcopy(run)

    def add_node(self, run_id: str, case_id: str, module_id: str, dependencies: list[str], stage: int) -> dict[str, Any]:
        with self.lock:
            node = {
                "id": self._id("node"),
                "run_id": run_id,
                "case_id": case_id,
                "module_id": module_id,
                "dependencies": list(dependencies),
                "stage": stage,
                "status": "pending",
                "attempt": 0,
                "artifact_id": None,
                "error": None,
            }
            self.nodes[node["id"]] = node
            self.persist()
            return copy.deepcopy(node)

    def register_source_set(self, source_set: dict[str, Any]) -> None:
        with self.lock:
            value = copy.deepcopy(source_set)
            self.source_sets[value["case_id"]] = value
            self.source_set_history[value["id"]] = value

    def source_set_by_id(self, source_set_id: str | None) -> dict[str, Any] | None:
        if not source_set_id:
            return None
        with self.lock:
            value = self.source_set_history.get(source_set_id)
            return copy.deepcopy(value) if value else None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.lock:
            run = self.runs.get(run_id)
            if not run:
                return None
            result = copy.deepcopy(run)
            result["nodes"] = [copy.deepcopy(self.nodes[node_id]) for node_id in run["node_ids"]]
            result["events"] = copy.deepcopy(self.events.get(run_id, []))
            return result

    def update_run(self, run_id: str, **changes: Any) -> None:
        with self.lock:
            self.runs[run_id].update(copy.deepcopy(changes))
            self.persist()

    def update_run_fenced(self, run_id: str, attempt_token: str, **changes: Any) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            self.runs[run_id].update(copy.deepcopy(changes))
            self.persist()

    def update_node(self, node_id: str, **changes: Any) -> None:
        with self.lock:
            self.nodes[node_id].update(copy.deepcopy(changes))
            self.persist()

    def update_node_fenced(self, run_id: str, attempt_token: str, node_id: str, **changes: Any) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            if self.nodes[node_id]["run_id"] != run_id:
                raise JobFencedError("node does not belong to run")
            self.nodes[node_id].update(copy.deepcopy(changes))
            self.persist()

    def pause_research_plan_fenced(self, run_id: str, attempt_token: str, node_id: str, research: dict[str, Any]) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            if self.nodes[node_id]["run_id"] != run_id:
                raise JobFencedError("node does not belong to run")
            prior_run = copy.deepcopy(self.runs[run_id])
            prior_node = copy.deepcopy(self.nodes[node_id])
            try:
                self.nodes[node_id].update(status="pending", error=None)
                self.runs[run_id].update(
                    status="paused",
                    current_node_id=None,
                    error={"code": "PLAN_APPROVAL_REQUIRED", "message": "Approve the proposed research plan before execution."},
                    research=copy.deepcopy(research),
                )
                self.persist()
            except Exception:
                self.runs[run_id] = prior_run
                self.nodes[node_id] = prior_node
                raise

    def claim_job(self, run_id: str, worker: str) -> str | None:
        with self.lock:
            job = self.jobs.get(run_id)
            if job and job["status"] == "running" and job["lease_until"] > time.monotonic():
                return None
            if sum(value["status"] == "running" and value["lease_until"] > time.monotonic() for value in self.jobs.values()) >= MAX_ACTIVE_JOBS:
                return None
            token = self._id("attempt")
            self.jobs[run_id] = {"status": "running", "worker": worker, "attempt_token": token, "lease_until": time.monotonic() + 60, "budget_reserved": 1}
            self.persist()
            return token

    def renew_job(self, run_id: str, attempt_token: str) -> bool:
        with self.lock:
            try:
                self._assert_job_locked(run_id, attempt_token)
            except JobFencedError:
                return False
            self.jobs[run_id]["lease_until"] = time.monotonic() + 60
            self.persist()
            return True

    def finish_job(self, run_id: str, attempt_token: str) -> None:
        with self.lock:
            if self._job_is_current_locked(run_id, attempt_token):
                self.jobs[run_id]["status"] = "finished"
                self.jobs[run_id]["budget_reserved"] = 0
                self.persist()

    def job_is_current(self, run_id: str, attempt_token: str) -> bool:
        with self.lock:
            return self._job_is_current_locked(run_id, attempt_token)

    def _job_is_current_locked(self, run_id: str, attempt_token: str) -> bool:
        job = self.jobs.get(run_id)
        return bool(job and job["status"] == "running" and job.get("attempt_token") == attempt_token and job["lease_until"] > time.monotonic())

    def _assert_job_locked(self, run_id: str, attempt_token: str) -> None:
        if not self._job_is_current_locked(run_id, attempt_token):
            raise JobFencedError("stale workflow attempt")

    def emit(self, run_id: str, event: str, data: dict[str, Any]) -> None:
        with self.lock:
            item = {"id": len(self.events.setdefault(run_id, [])) + 1, "event": event, "at": now_iso(), "data": copy.deepcopy(data)}
            self.events[run_id].append(item)
            self.persist()
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.notify_all()

    def emit_fenced(self, run_id: str, attempt_token: str, event: str, data: dict[str, Any]) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            item = {"id": len(self.events.setdefault(run_id, [])) + 1, "event": event, "at": now_iso(), "data": copy.deepcopy(data)}
            self.events[run_id].append(item)
            self.persist()
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.notify_all()

    def audit_event_fenced(self, run_id: str, attempt_token: str, action: str, actor: str, **details: Any) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            self.audit.append({"id": self._id("aud"), "action": action, "actor": actor, "at": now_iso(), "run_id": run_id, **details})
            self.persist()

    def events_after(self, run_id: str, cursor: int = 0) -> list[dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.events.get(run_id, [])[cursor:])

    def wait_for_events(self, run_id: str, cursor: int, timeout: float = 1.0) -> list[dict[str, Any]]:
        with self.lock:
            existing = self.events.get(run_id, [])[cursor:]
            if existing:
                return copy.deepcopy(existing)
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.wait(timeout)
            return copy.deepcopy(self.events.get(run_id, [])[cursor:])

    def put_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            existing = next((value for value in self.artifacts.values() if value["run_id"] == artifact["run_id"] and value["module_id"] == artifact["module_id"] and value["input_fingerprint"] == artifact["input_fingerprint"]), None)
            if existing:
                return copy.deepcopy(existing)
            self.artifacts[artifact["id"]] = copy.deepcopy(artifact)
            self.persist()
            return copy.deepcopy(artifact)

    def put_artifact_fenced(self, run_id: str, attempt_token: str, artifact: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            existing = next((value for value in self.artifacts.values() if value["run_id"] == artifact["run_id"] and value["module_id"] == artifact["module_id"] and value["input_fingerprint"] == artifact["input_fingerprint"]), None)
            if existing:
                return copy.deepcopy(existing)
            self.artifacts[artifact["id"]] = copy.deepcopy(artifact)
            self.persist()
            return copy.deepcopy(artifact)

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        with self.lock:
            value = self.artifacts.get(artifact_id)
            return copy.deepcopy(value) if value else None

    def accept_snapshot(self, case_id: str, run_id: str, actor: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            existing = self.cases[case_id].get("accepted_snapshot_id")
            snapshot["previous_snapshot_id"] = existing
            self.snapshots[snapshot["id"]] = copy.deepcopy(snapshot)
            self.cases[case_id]["accepted_snapshot_id"] = snapshot["id"]
            if not self.cases[case_id].get("visible_snapshot_id"):
                self.cases[case_id]["visible_snapshot_id"] = snapshot["id"]
            self.runs[run_id]["accepted_snapshot_id"] = snapshot["id"]
            self.audit_event("snapshot.accepted", actor, case_id=case_id, run_id=run_id, snapshot_id=snapshot["id"])
            self.persist()
            return copy.deepcopy(snapshot)

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with self.lock:
            value = self.snapshots.get(snapshot_id)
            return copy.deepcopy(value) if value else None

    def latest_run_for_case(self, case_id: str) -> dict[str, Any] | None:
        with self.lock:
            runs = [r for r in self.runs.values() if r["case_id"] == case_id]
            if not runs:
                return None
            return copy.deepcopy(max(runs, key=lambda r: r["created_at"]))

    def versioned(self, bucket: dict[str, list[dict[str, Any]]], case_id: str) -> list[dict[str, Any]]:
        return copy.deepcopy(bucket.get(case_id, []))

    def append_version(self, bucket: dict[str, list[dict[str, Any]]], case_id: str, expected_version: int, value: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
        with self.lock:
            versions = bucket.setdefault(case_id, [])
            current = versions[-1]["version"] if versions else 0
            if current != expected_version:
                raise ValueError("VERSION_CONFLICT")
            value = copy.deepcopy(value)
            value["version"] = current + 1
            value["created_at"] = now_iso()
            versions.append(value)
            if persist:
                self.persist()
            return copy.deepcopy(value)


STORE = MemoryStore()


def _merge_state(base: Any, local: Any, current: Any) -> Any:
    if local == base:
        return copy.deepcopy(current)
    if current == base:
        return copy.deepcopy(local)
    if isinstance(base, dict) and isinstance(local, dict) and isinstance(current, dict):
        sentinel = object()
        merged = copy.deepcopy(current)
        for key in set(base) | set(local) | set(current):
            before = base.get(key, sentinel)
            ours = local.get(key, sentinel)
            theirs = current.get(key, sentinel)
            if ours is sentinel:
                if before is not sentinel and theirs is sentinel:
                    merged.pop(key, None)
                elif before is not sentinel and theirs == before:
                    merged.pop(key, None)
            elif theirs is sentinel:
                if before is sentinel or ours != before:
                    merged[key] = copy.deepcopy(ours)
                else:
                    merged.pop(key, None)
            elif ours == before:
                merged[key] = copy.deepcopy(theirs)
            elif theirs == before:
                merged[key] = copy.deepcopy(ours)
            else:
                merged[key] = _merge_state(before, ours, theirs)
        return merged
    if isinstance(base, list) and isinstance(local, list) and isinstance(current, list) and local[: len(base)] == base and current[: len(base)] == base:
        merged = copy.deepcopy(base)
        # ponytail: append merge is O(n²); normalize audit/events before higher write volume.
        for item in current[len(base) :] + local[len(base) :]:
            if item not in merged:
                merged.append(copy.deepcopy(item))
        return merged
    return copy.deepcopy(local)


class PostgresStore(MemoryStore):
    """Durable adapter used by production processes.

    The state envelope is intentionally small and typed by the domain packages;
    PostgreSQL remains the record/job authority while the in-process mirrors
    provide the same API contract in local tests. The row is locked on every
    persistence write, and the migration also exposes normalized query tables
    for operational inspection and future scale-out.
    """

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self._state_revision = -1
        self._base_state = self._snapshot()
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required for production PostgreSQL storage") from exc
        self._psycopg = psycopg
        from psycopg.types.json import Jsonb

        self._jsonb = Jsonb
        self._dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
        with self._psycopg.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                migration = (Path(__file__).parent.parent / "migrations" / "001_baseline.sql").read_text()
                cursor.execute(migration)
                cursor.execute("CREATE TABLE IF NOT EXISTS caos_state (id boolean PRIMARY KEY DEFAULT true, revision bigint NOT NULL DEFAULT 0, state jsonb NOT NULL)")
                cursor.execute("SELECT revision, state FROM caos_state WHERE id = true")
                row = cursor.fetchone()
                if row:
                    self._state_revision = row[0]
                    self._restore(row[1])
                else:
                    cursor.execute("INSERT INTO caos_state(id, state) VALUES (true, %s)", (self._jsonb(self._snapshot()),))
                    self._state_revision = 0
            self._base_state = self._snapshot()
            connection.commit()

    def claim_job(self, run_id: str, worker: str) -> str | None:
        token = self._id("attempt")
        with self._psycopg.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                with self.lock:
                    run = copy.deepcopy(self.runs.get(run_id))
                    case = copy.deepcopy(self.cases.get(run["case_id"])) if run else None
                if not run or not case:
                    return None
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext('caos:workflow-budget'))")
                cursor.execute("SELECT count(*) FROM jobs WHERE state='claimed' AND lease_until > now()")
                if cursor.fetchone()[0] >= MAX_ACTIVE_JOBS:
                    return None
                cursor.execute(
                    "INSERT INTO cases(id, name, issuer, sector, created_by, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                    (case["id"], case["name"], case["issuer"], case["sector"], case["created_by"], case["created_at"]),
                )
                for subject, role in case["members"].items():
                    cursor.execute("INSERT INTO case_members(case_id, subject, role) VALUES (%s, %s, %s) ON CONFLICT (case_id, subject) DO UPDATE SET role=EXCLUDED.role", (case["id"], subject, role))
                cursor.execute(
                    "INSERT INTO runs(id, case_id, status, plan, accepted_snapshot_id, created_by, created_at, error) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, plan=EXCLUDED.plan, error=EXCLUDED.error",
                    (run["id"], run["case_id"], run["status"], self._jsonb(run["plan"]), run.get("accepted_snapshot_id"), run["created_by"], run["created_at"], self._jsonb(run.get("error"))),
                )
                cursor.execute("SELECT id, state, worker_id, attempt_token, lease_until FROM jobs WHERE run_id = %s AND state IN ('queued', 'claimed') ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1", (run_id,))
                row = cursor.fetchone()
                if row and row[1] == "claimed" and row[4] is not None:
                    cursor.execute("SELECT (%s > now())", (row[4],))
                    if cursor.fetchone()[0]:
                        return None
                if row:
                    job_id = row[0]
                    cursor.execute("UPDATE jobs SET state='claimed', worker_id=%s, attempt_token=%s, lease_until=now() + interval '60 seconds', budget_reserved=1 WHERE id=%s", (worker, token, job_id))
                else:
                    cursor.execute("INSERT INTO jobs(run_id, state, worker_id, attempt_token, lease_until, budget_reserved) VALUES (%s, 'claimed', %s, %s, now() + interval '60 seconds', 1)", (run_id, worker, token))
            connection.commit()
        with self.lock:
            self.jobs[run_id] = {"status": "running", "worker": worker, "attempt_token": token, "lease_until": time.monotonic() + 60}
        return token

    def renew_job(self, run_id: str, attempt_token: str) -> bool:
        with self._psycopg.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET lease_until = now() + interval '60 seconds' WHERE run_id = %s AND state = 'claimed' AND attempt_token = %s AND lease_until > now() RETURNING id",
                    (run_id, attempt_token),
                )
                renewed = cursor.fetchone() is not None
            connection.commit()
        if renewed:
            with self.lock:
                job = self.jobs.get(run_id)
                if job and job.get("attempt_token") == attempt_token:
                    job["lease_until"] = time.monotonic() + 60
        return renewed

    @contextmanager
    def _fenced_connection(self, run_id: str, attempt_token: str) -> Iterator[Any]:
        with self.lock:
            database_state = copy.deepcopy(self._base_state)
            database_revision = self._state_revision
            body_entered = False
            try:
                with self._psycopg.connect(self._dsn) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM jobs WHERE run_id=%s AND state='claimed' AND attempt_token=%s AND lease_until > now() FOR UPDATE", (run_id, attempt_token))
                        if cursor.fetchone() is None:
                            raise JobFencedError("stale workflow attempt")
                        body_entered = True
                        yield connection
                        state, revision, database_state, database_revision = self._persist_connection(connection)
                    connection.commit()
            except Exception:
                if body_entered:
                    self._adopt_persisted(database_state, database_revision)
                raise
            self._adopt_persisted(state, revision)

    def update_run_fenced(self, run_id: str, attempt_token: str, **changes: Any) -> None:
        with self._fenced_connection(run_id, attempt_token):
            self.runs[run_id].update(copy.deepcopy(changes))

    def update_node_fenced(self, run_id: str, attempt_token: str, node_id: str, **changes: Any) -> None:
        with self._fenced_connection(run_id, attempt_token):
            if self.nodes[node_id]["run_id"] != run_id:
                raise JobFencedError("node does not belong to run")
            self.nodes[node_id].update(copy.deepcopy(changes))

    def pause_research_plan_fenced(self, run_id: str, attempt_token: str, node_id: str, research: dict[str, Any]) -> None:
        with self._fenced_connection(run_id, attempt_token):
            if self.nodes[node_id]["run_id"] != run_id:
                raise JobFencedError("node does not belong to run")
            self.nodes[node_id].update(status="pending", error=None)
            self.runs[run_id].update(
                status="paused",
                current_node_id=None,
                error={"code": "PLAN_APPROVAL_REQUIRED", "message": "Approve the proposed research plan before execution."},
                research=copy.deepcopy(research),
            )

    def emit_fenced(self, run_id: str, attempt_token: str, event: str, data: dict[str, Any]) -> None:
        with self._fenced_connection(run_id, attempt_token):
            item = {"id": len(self.events.setdefault(run_id, [])) + 1, "event": event, "at": now_iso(), "data": copy.deepcopy(data)}
            self.events[run_id].append(item)
        with self.lock:
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.notify_all()

    def audit_event_fenced(self, run_id: str, attempt_token: str, action: str, actor: str, **details: Any) -> None:
        with self._fenced_connection(run_id, attempt_token):
            self.audit.append({"id": self._id("aud"), "action": action, "actor": actor, "at": now_iso(), "run_id": run_id, **details})

    def job_is_current(self, run_id: str, attempt_token: str) -> bool:
        with self._psycopg.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM jobs WHERE run_id=%s AND state='claimed' AND attempt_token=%s AND lease_until > now()", (run_id, attempt_token))
                return cursor.fetchone() is not None

    def put_artifact_fenced(self, run_id: str, attempt_token: str, artifact: dict[str, Any]) -> dict[str, Any]:
        with self._fenced_connection(run_id, attempt_token):
            existing = next((value for value in self.artifacts.values() if value["run_id"] == artifact["run_id"] and value["module_id"] == artifact["module_id"] and value["input_fingerprint"] == artifact["input_fingerprint"]), None)
            if existing:
                return copy.deepcopy(existing)
            self.artifacts[artifact["id"]] = copy.deepcopy(artifact)
            return copy.deepcopy(artifact)

    def finish_job(self, run_id: str, attempt_token: str) -> None:
        with self._psycopg.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE jobs SET state='succeeded', lease_until=NULL, budget_reserved=0 WHERE run_id=%s AND state='claimed' AND attempt_token=%s AND lease_until > now() RETURNING id", (run_id, attempt_token))
                finished = cursor.fetchone() is not None
            connection.commit()
        if finished:
            with self.lock:
                job = self.jobs.get(run_id)
                if job and job.get("attempt_token") == attempt_token:
                    job["status"] = "finished"

    def _snapshot(self) -> dict[str, Any]:
        return {name: copy.deepcopy(getattr(self, name)) for name in ("cases", "sources", "source_sets", "source_set_history", "runs", "nodes", "artifacts", "snapshots", "theses", "recommendations", "notes", "assumptions", "reports", "methodology_drafts", "rv_universes", "audit", "events", "jobs")}

    def _restore(self, state: dict[str, Any]) -> None:
        for name, value in state.items():
            if hasattr(self, name):
                setattr(self, name, value)
        for run_id in self.events:
            self.event_conditions.setdefault(run_id, threading.Condition(self.lock))

    def persist(self) -> None:
        with self.lock:
            database_state = copy.deepcopy(self._base_state)
            database_revision = self._state_revision
            try:
                with self._psycopg.connect(self._dsn) as connection:
                    state, revision, database_state, database_revision = self._persist_connection(connection)
                    connection.commit()
            except Exception:
                self._adopt_persisted(database_state, database_revision)
                raise
            self._adopt_persisted(state, revision)

    def _persist_connection(self, connection: Any) -> tuple[dict[str, Any], int, dict[str, Any], int]:
        state = self._snapshot()
        with connection.cursor() as cursor:
            cursor.execute("SELECT revision, state FROM caos_state WHERE id = true FOR UPDATE")
            row = cursor.fetchone()
            current_revision, current_state = row if row else (self._state_revision, state)
            if current_revision != self._state_revision:
                state = _merge_state(self._base_state, state, current_state)
            next_revision = current_revision + 1
            cursor.execute("UPDATE caos_state SET revision = %s, state = %s WHERE id = true", (next_revision, self._jsonb(json.loads(json.dumps(state)))))
        return state, next_revision, current_state, current_revision

    def _adopt_persisted(self, state: dict[str, Any], revision: int) -> None:
        self._restore(state)
        self._state_revision = revision
        self._base_state = self._snapshot()

    def refresh(self) -> None:
        with self.lock:
            with self._psycopg.connect(self._dsn) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT revision, state FROM caos_state WHERE id = true")
                    row = cursor.fetchone()
            if row and row[0] != self._state_revision:
                self._state_revision = row[0]
                self._restore(row[1])
                self._base_state = self._snapshot()
