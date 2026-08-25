"""Private, atomic in-memory implementations of the ledger ports."""

from __future__ import annotations

import copy
import hashlib
import threading
import time
import uuid
from typing import Any

from .contracts import clean_json, digest
from .ledgers import SourceCatalog
from .store import (
    MAX_ACTIVE_JOBS,
    JobFencedError,
    MODEL_JOB_KINDS,
    _model_job_key,
    _remaining_finalization_seconds,
    _validated_model_result,
    now_iso,
)


Record = dict[str, Any]


class _MemoryState:
    """One private state carrier shared by all four memory adapters."""

    def __init__(self, lease_seconds: float) -> None:
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
        self.rv_loan_universes: dict[str, dict[str, Any]] = {}
        self.rv_loan_rows: dict[str, list[dict[str, Any]]] = {}
        self.rv_active_loan_universes: dict[str, str] = {}
        self.audit: list[dict[str, Any]] = []
        self.events: dict[str, list[dict[str, Any]]] = {}
        self.event_conditions: dict[str, threading.Condition] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.model_builds: dict[str, dict[str, Any]] = {}
        self.model_jobs: dict[str, dict[str, Any]] = {}
        self.lease_seconds = lease_seconds
        self._final_attempt_tokens: dict[str, str] = {}

    @staticmethod
    def new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    def _id(self, prefix: str) -> str:
        return self.new_id(prefix)

    def pending_runs(self) -> list[tuple[str, str]]:
        with self.lock:
            return [
                (run["id"], run["created_by"])
                for run in self.runs.values()
                if run["status"] in {"queued", "running"}
            ]

    def pending_model_jobs(self) -> list[tuple[str, str, str]]:
        with self.lock:
            return [
                (
                    job["build_id"],
                    job.get("actor")
                    or self.model_builds[job["build_id"]]["created_by"],
                    job["kind"],
                )
                for job in self.model_jobs.values()
                if job.get("kind") in MODEL_JOB_KINDS
                and job.get("status") in {"queued", "claimed"}
                and job.get("build_id") in self.model_builds
            ]

    def audit_event(self, action: str, actor: str, **details: Any) -> None:
        with self.lock:
            self.audit.append(
                {
                    "id": self._id("aud"),
                    "action": action,
                    "actor": actor,
                    "at": now_iso(),
                    **details,
                }
            )

    def create_case(
        self, name: str, issuer: str, sector: str, actor: str
    ) -> dict[str, Any]:
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
            return copy.deepcopy(case)

    def list_cases(self, actor: str) -> list[dict[str, Any]]:
        with self.lock:
            return [
                copy.deepcopy(c)
                for c in self.cases.values()
                if actor in c["members"] or c["members"].get(actor) == "ADMIN"
            ]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self.lock:
            case = self.cases.get(case_id)
            return copy.deepcopy(case) if case else None

    def is_member(
        self, case_id: str, actor: str, roles: set[str] | None = None
    ) -> bool:
        with self.lock:
            case = self.cases.get(case_id)
            if not case:
                return False
            role = case["members"].get(actor)
            return role is not None and (roles is None or role in roles)

    def add_member(
        self,
        case_id: str,
        actor: str,
        member: str,
        role: str,
        actor_role: str | None = None,
    ) -> bool:
        with self.lock:
            case = self.cases.get(case_id)
            if not case or (
                actor_role != "ADMIN"
                and case["members"].get(actor) not in {"ADMIN", "APPROVER"}
            ):
                return False
            case["members"][member] = role
            self.audit_event(
                "case.member_added", actor, case_id=case_id, member=member, role=role
            )
            return True

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.lock:
            run = self.runs.get(run_id)
            if not run:
                return None
            result = copy.deepcopy(run)
            result["nodes"] = [
                copy.deepcopy(self.nodes[node_id]) for node_id in run["node_ids"]
            ]
            result["events"] = copy.deepcopy(self.events.get(run_id, []))
            return result

    def update_run_fenced(
        self, run_id: str, attempt_token: str, **changes: Any
    ) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            self.runs[run_id].update(copy.deepcopy(changes))

    def update_node_fenced(
        self, run_id: str, attempt_token: str, node_id: str, **changes: Any
    ) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            if self.nodes[node_id]["run_id"] != run_id:
                raise JobFencedError("node does not belong to run")
            self.nodes[node_id].update(copy.deepcopy(changes))

    def pause_research_plan_fenced(
        self, run_id: str, attempt_token: str, node_id: str, research: dict[str, Any]
    ) -> None:
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
                    error={
                        "code": "PLAN_APPROVAL_REQUIRED",
                        "message": "Approve the proposed research plan before execution.",
                    },
                    research=copy.deepcopy(research),
                )
            except Exception:
                self.runs[run_id] = prior_run
                self.nodes[node_id] = prior_node
                raise

    def _recover_running_nodes_locked(self, run_id: str) -> None:
        run = self.runs.get(run_id)
        if not run:
            return
        for node_id in run.get("node_ids", []):
            node = self.nodes.get(node_id)
            if node and node.get("status") == "running":
                node.update(status="pending", artifact_id=None, error=None)
        run["current_node_id"] = None

    def finish_job(self, run_id: str, attempt_token: str) -> None:
        with self.lock:
            if self._job_is_current_locked(run_id, attempt_token):
                self.jobs[run_id]["status"] = "finished"
                self.jobs[run_id]["budget_reserved"] = 0

    def job_is_current(self, run_id: str, attempt_token: str) -> bool:
        with self.lock:
            return self._job_is_current_locked(run_id, attempt_token)

    def _job_is_current_locked(self, run_id: str, attempt_token: str) -> bool:
        job = self.jobs.get(run_id)
        return bool(
            job
            and job["status"] == "running"
            and job.get("attempt_token") == attempt_token
            and job["lease_until"] > time.monotonic()
        )

    def _assert_job_locked(self, run_id: str, attempt_token: str) -> None:
        if not self._job_is_current_locked(run_id, attempt_token):
            raise JobFencedError("stale workflow attempt")

    def queue_model_build(
        self,
        build: dict[str, Any],
        actor: str,
    ) -> tuple[dict[str, Any], bool]:
        with self.lock:
            prior = (
                self.model_builds.copy(),
                self.model_jobs.copy(),
                self.audit.copy(),
            )
            try:
                record, created = self._queue_model_build_locked(build, actor)
            except Exception:
                self.model_builds, self.model_jobs, self.audit = prior
                raise
            return copy.deepcopy(record), created

    def _queue_model_build_locked(
        self,
        build: dict[str, Any],
        actor: str,
    ) -> tuple[dict[str, Any], bool]:
        existing = next(
            (
                value
                for value in self.model_builds.values()
                if value.get("case_id") == build.get("case_id")
                and value.get("input_fingerprint") == build.get("input_fingerprint")
            ),
            None,
        )
        if existing is not None:
            return copy.deepcopy(existing), False
        fingerprint = build.get("input_fingerprint")
        run = self.runs.get(build.get("accepted_run_id"))
        snapshot = self.snapshots.get(build.get("accepted_snapshot_id"))
        source_set = self.source_set_history.get(build.get("source_set_id"))
        if (
            not isinstance(build.get("id"), str)
            or build["id"] in self.model_builds
            or build.get("case_id") not in self.cases
            or not run
            or run.get("case_id") != build.get("case_id")
            or run.get("status") != "succeeded"
            or run.get("accepted_snapshot_id") != build.get("accepted_snapshot_id")
            or not snapshot
            or snapshot.get("case_id") != build.get("case_id")
            or snapshot.get("run_id") != build.get("accepted_run_id")
            or snapshot.get("source_set_id") != build.get("source_set_id")
            or not source_set
            or source_set.get("case_id") != build.get("case_id")
            or not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in fingerprint)
        ):
            raise ValueError("MODEL_BUILD_INVALID")
        record = copy.deepcopy(build)
        record.update(
            status="QUEUED",
            created_by=actor,
            queued_at=record.get("queued_at") or now_iso(),
            started_at=None,
            completed_at=None,
            error=None,
        )
        record["export"] = {"status": "NOT_REQUESTED", "error": None}
        key = _model_job_key(record["id"], "calculate")
        self.model_builds[record["id"]] = record
        self.model_jobs[key] = {
            "build_id": record["id"],
            "kind": "calculate",
            "actor": actor,
            "status": "queued",
            "worker": None,
            "attempt_token": None,
            "lease_until": 0.0,
            "error": None,
        }
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": "model.queued",
                "actor": actor,
                "at": now_iso(),
                "case_id": record["case_id"],
                "build_id": record["id"],
            }
        )
        return copy.deepcopy(record), True

    def get_model_build(self, build_id: str) -> dict[str, Any] | None:
        with self.lock:
            value = self.model_builds.get(build_id)
            return copy.deepcopy(value) if value else None

    def retry_model_build(self, build_id: str, actor: str) -> dict[str, Any]:
        with self.lock:
            prior = copy.deepcopy((self.model_builds, self.model_jobs, self.audit))
            try:
                build = self._retry_model_build_locked(build_id, actor)
            except Exception:
                self.model_builds, self.model_jobs, self.audit = prior
                raise
            return build

    def _retry_model_build_locked(self, build_id: str, actor: str) -> dict[str, Any]:
        build = self.model_builds.get(build_id)
        key = _model_job_key(build_id, "calculate")
        job = self.model_jobs.get(key)
        if (
            not build
            or build.get("status") != "FAILED"
            or not job
            or job.get("status") != "failed"
        ):
            raise ValueError("MODEL_RETRY_INVALID")
        build.update(status="QUEUED", started_at=None, completed_at=None, error=None)
        job.update(
            actor=actor,
            status="queued",
            worker=None,
            attempt_token=None,
            lease_until=0.0,
            error=None,
        )
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": "model.retried",
                "actor": actor,
                "at": now_iso(),
                "case_id": build["case_id"],
                "build_id": build_id,
            }
        )
        return copy.deepcopy(build)

    def list_model_builds(self, case_id: str) -> list[dict[str, Any]]:
        with self.lock:
            values = [
                value
                for value in self.model_builds.values()
                if value.get("case_id") == case_id
            ]
            return copy.deepcopy(
                sorted(values, key=lambda value: value["queued_at"], reverse=True)
            )

    def queue_model_export(
        self, build_id: str, actor: str
    ) -> tuple[dict[str, Any], bool]:
        with self.lock:
            prior = copy.deepcopy((self.model_builds, self.model_jobs, self.audit))
            try:
                build, queued = self._queue_model_export_locked(build_id, actor)
                if not queued:
                    return build, False
            except Exception:
                self.model_builds, self.model_jobs, self.audit = prior
                raise
            return build, True

    def _queue_model_export_locked(
        self, build_id: str, actor: str
    ) -> tuple[dict[str, Any], bool]:
        build = self.model_builds.get(build_id)
        if not build or build.get("status") != "READY":
            raise ValueError("MODEL_EXPORT_NOT_READY")
        key = _model_job_key(build_id, "export")
        job = self.model_jobs.get(key)
        if job and job.get("status") in {"queued", "claimed", "succeeded"}:
            return copy.deepcopy(build), False
        self.model_jobs[key] = {
            "build_id": build_id,
            "kind": "export",
            "actor": actor,
            "status": "queued",
            "worker": None,
            "attempt_token": None,
            "lease_until": 0.0,
            "error": None,
        }
        build["export"] = {"status": "QUEUED", "error": None}
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": "model.export.queued",
                "actor": actor,
                "at": now_iso(),
                "case_id": build["case_id"],
                "build_id": build_id,
            }
        )
        return copy.deepcopy(build), True

    def model_job_is_current(
        self, build_id: str, attempt_token: str, kind: str = "calculate"
    ) -> bool:
        with self.lock:
            return self._model_job_is_current_locked(
                _model_job_key(build_id, kind), attempt_token
            )

    def _model_job_is_current_locked(self, key: str, attempt_token: str) -> bool:
        job = self.model_jobs.get(key)
        return bool(
            job
            and job["status"] == "claimed"
            and job.get("attempt_token") == attempt_token
            and job["lease_until"] > time.monotonic()
        )

    def _assert_model_job_locked(
        self, build_id: str, attempt_token: str, kind: str
    ) -> str:
        key = _model_job_key(build_id, kind)
        if not self._model_job_is_current_locked(key, attempt_token):
            raise JobFencedError("stale model attempt")
        return key

    def complete_model_job(
        self,
        build_id: str,
        attempt_token: str,
        result: dict[str, Any],
        actor: str,
        kind: str = "calculate",
    ) -> dict[str, Any]:
        with self.lock:
            key = self._assert_model_job_locked(build_id, attempt_token, kind)
            prior = copy.deepcopy(
                (self.model_builds[build_id], self.model_jobs[key], self.audit)
            )
            try:
                completed = self._complete_model_job_locked(
                    build_id, key, result, actor, kind
                )
            except Exception:
                self.model_builds[build_id], self.model_jobs[key], self.audit = prior
                raise
            return completed

    def _complete_model_job_locked(
        self,
        build_id: str,
        key: str,
        result: dict[str, Any],
        actor: str,
        kind: str,
    ) -> dict[str, Any]:
        build = self.model_builds[build_id]
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
        self.model_jobs[key].update(status="succeeded", lease_until=0.0)
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": f"model.{kind}.succeeded",
                "actor": actor,
                "at": now_iso(),
                "case_id": build["case_id"],
                "build_id": build_id,
            }
        )
        return copy.deepcopy(build)

    def fail_model_job(
        self,
        build_id: str,
        attempt_token: str,
        error: dict[str, Any],
        actor: str,
        kind: str = "calculate",
    ) -> dict[str, Any]:
        with self.lock:
            key = self._assert_model_job_locked(build_id, attempt_token, kind)
            prior = copy.deepcopy(
                (self.model_builds[build_id], self.model_jobs[key], self.audit)
            )
            try:
                failed = self._fail_model_job_locked(build_id, key, error, actor, kind)
            except Exception:
                self.model_builds[build_id], self.model_jobs[key], self.audit = prior
                raise
            return failed

    def _fail_model_job_locked(
        self,
        build_id: str,
        key: str,
        error: dict[str, Any],
        actor: str,
        kind: str,
    ) -> dict[str, Any]:
        if (
            not isinstance(error, dict)
            or set(error) != {"code", "detail"}
            or not isinstance(error["code"], str)
            or len(error["code"]) > 80
            or not isinstance(error["detail"], str)
            or len(error["detail"]) > 500
        ):
            raise ValueError("MODEL_ERROR_INVALID")
        build = self.model_builds[build_id]
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
        self.model_jobs[key].update(
            status="failed", lease_until=0.0, error=copy.deepcopy(error)
        )
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": f"model.{kind}.failed",
                "actor": actor,
                "at": now_iso(),
                "case_id": build["case_id"],
                "build_id": build_id,
                "code": error["code"],
            }
        )
        return copy.deepcopy(build)

    def emit(self, run_id: str, event: str, data: dict[str, Any]) -> None:
        with self.lock:
            item = {
                "id": len(self.events.setdefault(run_id, [])) + 1,
                "event": event,
                "at": now_iso(),
                "data": copy.deepcopy(data),
            }
            self.events[run_id].append(item)
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.notify_all()

    def emit_fenced(
        self, run_id: str, attempt_token: str, event: str, data: dict[str, Any]
    ) -> None:
        with self.lock:
            self._assert_job_locked(run_id, attempt_token)
            item = {
                "id": len(self.events.setdefault(run_id, [])) + 1,
                "event": event,
                "at": now_iso(),
                "data": copy.deepcopy(data),
            }
            self.events[run_id].append(item)
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.notify_all()

    def _assert_run_artifacts_ready_locked(self, run_id: str) -> None:
        run = self.runs[run_id]
        for node_id in run.get("node_ids", []):
            node = self.nodes.get(node_id)
            artifact = self.artifacts.get(node.get("artifact_id")) if node else None
            if (
                not node
                or node.get("run_id") != run_id
                or node.get("status") != "succeeded"
                or not artifact
                or artifact.get("run_id") != run_id
                or artifact.get("module_id") != node.get("module_id")
            ):
                raise ValueError("RUN_NOT_READY")

    def events_after(self, run_id: str, cursor: int = 0) -> list[dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.events.get(run_id, [])[cursor:])

    def wait_for_events(
        self, run_id: str, cursor: int, timeout: float = 1.0
    ) -> list[dict[str, Any]]:
        with self.lock:
            existing = self.events.get(run_id, [])[cursor:]
            if existing:
                return copy.deepcopy(existing)
            condition = self.event_conditions.get(run_id)
            if condition:
                condition.wait(timeout)
            return copy.deepcopy(self.events.get(run_id, [])[cursor:])

    def artifact_for_fingerprint(
        self, run_id: str, module_id: str, input_fingerprint: str
    ) -> dict[str, Any] | None:
        with self.lock:
            existing = next(
                (
                    value
                    for value in self.artifacts.values()
                    if value.get("run_id") == run_id
                    and value.get("module_id") == module_id
                    and value.get("input_fingerprint") == input_fingerprint
                ),
                None,
            )
            return copy.deepcopy(existing) if existing else None

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        with self.lock:
            value = self.artifacts.get(artifact_id)
            return copy.deepcopy(value) if value else None

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with self.lock:
            value = self.snapshots.get(snapshot_id)
            return copy.deepcopy(value) if value else None

    @staticmethod
    def _loan_import_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            record["case_id"],
            record["source_sha256"],
            record["template_version"],
            record["importer_version"],
        )

    def find_loan_universe_import(
        self,
        case_id: str,
        source_sha256: str,
        template_version: str,
        importer_version: str,
    ) -> dict[str, Any] | None:
        key = (case_id, source_sha256, template_version, importer_version)
        with self.lock:
            for record in self.rv_loan_universes.values():
                if self._loan_import_key(record) == key:
                    return copy.deepcopy(record)
        return None

    def save_loan_universe_import(
        self,
        record: dict[str, Any],
        rows: list[dict[str, Any]],
        actor: str,
    ) -> tuple[dict[str, Any], bool]:
        with self.lock:
            universes = self.rv_loan_universes.copy()
            previous_id = self.rv_active_loan_universes.get(record.get("case_id"))
            previous = universes.get(previous_id)
            if previous:
                universes[previous_id] = previous.copy()

            prior = (
                universes,
                self.rv_loan_rows.copy(),
                self.rv_active_loan_universes.copy(),
                self.audit.copy(),
            )
            try:
                saved, created = self._save_loan_universe_import_locked(
                    record, rows, actor
                )
            except Exception:
                (
                    self.rv_loan_universes,
                    self.rv_loan_rows,
                    self.rv_active_loan_universes,
                    self.audit,
                ) = prior
                raise
            return copy.deepcopy(saved), created

    def _save_loan_universe_import_locked(
        self,
        record: dict[str, Any],
        rows: list[dict[str, Any]],
        actor: str,
    ) -> tuple[dict[str, Any], bool]:
        if record.get("status") not in {"ACTIVE", "REJECTED"}:
            raise ValueError("RV_UNIVERSE_STATUS_INVALID")
        source = self.sources.get(record.get("source_id"))
        if (
            not source
            or source.get("case_id") != record.get("case_id")
            or source.get("withdrawn")
        ):
            raise ValueError("RV_SOURCE_NOT_ACTIVE")
        key = self._loan_import_key(record)
        for existing in self.rv_loan_universes.values():
            if self._loan_import_key(existing) == key:
                return copy.deepcopy(existing), False
        if record["status"] == "ACTIVE":
            if record.get("row_count") != len(rows) or len(
                {row.get("instrument_key") for row in rows}
            ) != len(rows):
                raise ValueError("RV_UNIVERSE_ROWS_INVALID")
        elif rows:
            raise ValueError("RV_REJECTED_UNIVERSE_HAS_ROWS")

        saved = copy.deepcopy(record)
        saved.setdefault("created_at", now_iso())
        saved.setdefault("created_by", actor)
        if saved["status"] == "ACTIVE":
            versions = [
                value.get("version", 0) or 0
                for value in self.rv_loan_universes.values()
                if value.get("case_id") == saved["case_id"]
            ]
            saved["version"] = max(versions, default=0) + 1
            saved["activated_at"] = now_iso()
            saved["superseded_at"] = None
            saved["withdrawn_at"] = None
            previous_id = self.rv_active_loan_universes.get(saved["case_id"])
            previous = self.rv_loan_universes.get(previous_id) if previous_id else None
            if previous:
                previous["status"] = "SUPERSEDED"
                previous["superseded_at"] = saved["activated_at"]
            self.rv_active_loan_universes[saved["case_id"]] = saved["id"]
            self.rv_loan_rows[saved["id"]] = copy.deepcopy(rows)
            action = "rv.loan_universe.activated"
        else:
            saved["version"] = None
            saved["activated_at"] = None
            saved["superseded_at"] = None
            saved["withdrawn_at"] = None
            self.rv_loan_rows[saved["id"]] = []
            action = "rv.loan_universe.rejected"
        self.rv_loan_universes[saved["id"]] = saved
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": action,
                "actor": actor,
                "at": now_iso(),
                "case_id": saved["case_id"],
                "source_id": saved["source_id"],
                "universe_id": saved["id"],
            }
        )
        return copy.deepcopy(saved), True

    def active_loan_universe(
        self, case_id: str, *, include_rows: bool = True
    ) -> dict[str, Any] | None:
        with self.lock:
            universe_id = self.rv_active_loan_universes.get(case_id)
            record = self.rv_loan_universes.get(universe_id) if universe_id else None
            if not record or record.get("status") != "ACTIVE":
                return None
            result = copy.deepcopy(record)
            if include_rows:
                result["rows"] = copy.deepcopy(self.rv_loan_rows.get(universe_id, []))
            return result

    def _withdraw_loan_universe_for_source_locked(
        self, case_id: str, source_id: str, actor: str
    ) -> str | None:
        universe_id = self.rv_active_loan_universes.get(case_id)
        record = self.rv_loan_universes.get(universe_id) if universe_id else None
        if not record or record.get("source_id") != source_id:
            return None
        record["status"] = "WITHDRAWN"
        record["withdrawn_at"] = now_iso()
        self.rv_active_loan_universes.pop(case_id, None)
        self.audit.append(
            {
                "id": self._id("aud"),
                "action": "rv.loan_universe.withdrawn",
                "actor": actor,
                "at": now_iso(),
                "case_id": case_id,
                "source_id": source_id,
                "universe_id": universe_id,
            }
        )
        return universe_id


class _Adapter:
    __slots__ = ("_state",)

    def __init__(self, state: _MemoryState) -> None:
        self._state = state


def _public_source(source: Record) -> Record:
    return copy.deepcopy(
        {
            key: value
            for key, value in source.items()
            if key not in {"vault_path", "withdrawn_at"}
        }
    )


class _MemorySourceCatalog(_Adapter):
    def ingest(self, source: Record, actor: str) -> Record:
        state = self._state
        with state.lock:
            if any(
                item.get("case_id") == source.get("case_id")
                and item.get("sha256") == source.get("sha256")
                and not item.get("withdrawn")
                for item in state.sources.values()
            ):
                raise ValueError("source content already active")
            saved = copy.deepcopy(source)
            saved["id"] = state.new_id("src")
            saved.setdefault("created_by", actor)
            saved.setdefault("created_at", now_iso())
            saved.setdefault("withdrawn", False)
            current = state.source_sets.get(saved["case_id"])
            source_set = {
                "id": state.new_id("set"),
                "case_id": saved["case_id"],
                "version": current["version"] + 1 if current else 1,
                "source_ids": [
                    *(
                        [
                            source_id
                            for source_id in current["source_ids"]
                            if not state.sources.get(source_id, {}).get("withdrawn")
                        ]
                        if current
                        else []
                    ),
                    saved["id"],
                ],
                "created_by": actor,
                "created_at": now_iso(),
            }
            state.sources[saved["id"]] = saved
            state.source_sets[saved["case_id"]] = copy.deepcopy(source_set)
            state.source_set_history[source_set["id"]] = copy.deepcopy(source_set)
            state.audit_event(
                "source.ingested",
                actor,
                case_id=saved["case_id"],
                source_id=saved["id"],
                sha256=saved.get("sha256"),
            )
            return {**_public_source(saved), "source_set": copy.deepcopy(source_set)}

    def _ingest_promoted_note_locked(self, note: Record, actor: str) -> Record:
        state = self._state
        promoted = state.sources.get(note.get("promoted_source_id"))
        if note.get("promoted") and promoted and not promoted.get("withdrawn"):
            return copy.deepcopy(note)
        body = note["body"]
        source_digest = hashlib.sha256(body.encode()).hexdigest()
        if any(
            source.get("case_id") == note.get("case_id")
            and source.get("sha256") == source_digest
            and not source.get("withdrawn")
            for source in state.sources.values()
        ):
            raise ValueError("DUPLICATE_SOURCE")
        source_id = state.new_id("src-note")
        source = {
            "id": source_id,
            "case_id": note["case_id"],
            "filename": f"analyst-note-{note['id']}.md",
            "media_type": "text/markdown",
            "bytes": len(body.encode()),
            "sha256": source_digest,
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
        current = state.source_sets.get(note["case_id"])
        source_set = {
            "id": state.new_id("set"),
            "case_id": note["case_id"],
            "version": current["version"] + 1 if current else 1,
            "source_ids": [
                *(
                    [
                        existing_id
                        for existing_id in current["source_ids"]
                        if not state.sources.get(existing_id, {}).get("withdrawn")
                    ]
                    if current
                    else []
                ),
                source_id,
            ],
            "created_by": actor,
            "created_at": now_iso(),
        }
        note.update(promoted=True, promoted_source_id=source_id)
        state.sources[source_id] = source
        state.source_sets[note["case_id"]] = copy.deepcopy(source_set)
        state.source_set_history[source_set["id"]] = copy.deepcopy(source_set)
        state.audit_event(
            "note.promoted",
            actor,
            case_id=note["case_id"],
            note_id=note["id"],
            source_id=source_id,
        )
        return copy.deepcopy(note)

    def ingest_promoted_note(self, note: Record, actor: str) -> Record:
        proposal = copy.deepcopy(note)
        state = self._state
        with state.lock:
            canonical = next(
                (
                    item
                    for item in state.notes.get(proposal.get("case_id"), [])
                    if item.get("id") == proposal.get("id")
                ),
                None,
            )
            if not canonical:
                raise KeyError("NOTE_NOT_FOUND")
            if canonical.get("author") != actor:
                raise PermissionError("only note author can promote")
            return self._ingest_promoted_note_locked(canonical, actor)

    def withdraw(self, case_id: str, source_id: str, actor: str) -> Record | None:
        state = self._state
        with state.lock:
            source = state.sources.get(source_id)
            if not source or source.get("case_id") != case_id:
                return None
            if source.get("withdrawn"):
                return _public_source(source)
            current = state.source_sets.get(case_id)
            source["withdrawn"] = True
            source["withdrawn_at"] = now_iso()
            if current:
                source_set = {
                    "id": state.new_id("set"),
                    "case_id": case_id,
                    "version": current["version"] + 1,
                    "source_ids": [
                        item
                        for item in current["source_ids"]
                        if item != source_id
                        and not state.sources.get(item, {}).get("withdrawn")
                    ],
                    "created_by": actor,
                    "created_at": now_iso(),
                }
                state.source_sets[case_id] = copy.deepcopy(source_set)
                state.source_set_history[source_set["id"]] = copy.deepcopy(source_set)
            for assumption in state.assumptions.get(case_id, []):
                if source_id in assumption.get("evidence_ids", []):
                    assumption.update(stale=True, status="STALE")
            state._withdraw_loan_universe_for_source_locked(case_id, source_id, actor)
            state.audit_event(
                "source.withdrawn", actor, case_id=case_id, source_id=source_id
            )
            return _public_source(source)

    def list_sources(self, case_id: str) -> list[Record]:
        with self._state.lock:
            return [
                _public_source(source)
                for source in self._state.sources.values()
                if source.get("case_id") == case_id and not source.get("withdrawn")
            ]

    def get_source(self, source_id: str) -> Record | None:
        with self._state.lock:
            source = self._state.sources.get(source_id)
            return _public_source(source) if source else None

    def current_source_set(self, case_id: str) -> Record | None:
        with self._state.lock:
            value = self._state.source_sets.get(case_id)
            return copy.deepcopy(value) if value else None

    def source_set(self, source_set_id: str | None) -> Record | None:
        if not source_set_id:
            return None
        with self._state.lock:
            value = self._state.source_set_history.get(source_set_id)
            return copy.deepcopy(value) if value else None

    def read_pinned_evidence(
        self,
        case_id: str,
        source_set_id: str,
        source_id: str,
        block_ids: list[str],
    ) -> list[Record]:
        state = self._state
        with state.lock:
            source_set = state.source_set_history.get(source_set_id)
            source = state.sources.get(source_id)
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
                    "authority_class": source.get("authority_class", "unclassified"),
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
        return self._state.find_loan_universe_import(
            case_id, source_sha256, template_version, importer_version
        )

    def save_loan_universe_import(
        self, record: Record, rows: list[Record], actor: str
    ) -> tuple[Record, bool]:
        proposal = copy.deepcopy(record)
        proposal["id"] = self._state.new_id("rvloan")
        return self._state.save_loan_universe_import(proposal, rows, actor)

    def active_loan_universe(
        self, case_id: str, *, include_rows: bool = True
    ) -> Record | None:
        return self._state.active_loan_universe(case_id, include_rows=include_rows)


class _MemoryRunLedger(_Adapter):
    def create_case(self, name: str, issuer: str, sector: str, actor: str) -> Record:
        return self._state.create_case(name, issuer, sector, actor)

    def list_cases(self, actor: str) -> list[Record]:
        return self._state.list_cases(actor)

    def get_case(self, case_id: str) -> Record | None:
        return self._state.get_case(case_id)

    def is_member(
        self, case_id: str, actor: str, roles: set[str] | None = None
    ) -> bool:
        return self._state.is_member(case_id, actor, roles)

    def add_member(
        self,
        case_id: str,
        actor: str,
        member: str,
        role: str,
        actor_role: str | None = None,
    ) -> bool:
        return self._state.add_member(case_id, actor, member, role, actor_role)

    def create_run_with_nodes(
        self,
        case_id: str,
        actor: str,
        plan: Record,
        nodes: list[Record],
        upgraded_from_run_id: str | None = None,
        *,
        initial_status: str = "queued",
        initial_error: Record | None = None,
        initial_research: Record | None = None,
        canonical_generation: Record | None = None,
    ) -> Record:
        if initial_status not in {"queued", "paused"}:
            raise ValueError("invalid initial run status")
        stored_plan = copy.deepcopy(plan)
        stored_error = copy.deepcopy(initial_error)
        stored_research = copy.deepcopy(initial_research)
        stored_generation = copy.deepcopy(canonical_generation)
        state = self._state
        with state.lock:
            if case_id not in state.cases:
                raise ValueError("CASE_NOT_FOUND")
            created_at = now_iso()
            if (
                stored_generation is not None
                and "reporting_period" in stored_generation
            ):
                stored_generation["reporting_period"] = created_at[:10]
            run_id = state.new_id("run")
            node_records = [
                {
                    "id": state.new_id("node"),
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
            run = {
                "id": run_id,
                "case_id": case_id,
                "created_by": actor,
                "created_at": created_at,
                "status": initial_status,
                "plan": stored_plan,
                "node_ids": [node["id"] for node in node_records],
                "current_node_id": None,
                "accepted_snapshot_id": None,
                "upgraded_from_run_id": upgraded_from_run_id,
                "error": stored_error,
            }
            if stored_research is not None:
                run["research"] = stored_research
            if stored_generation is not None:
                run["canonical_generation"] = stored_generation
            state.runs[run_id] = run
            state.nodes.update({node["id"]: node for node in node_records})
            state.events[run_id] = []
            state.event_conditions[run_id] = threading.Condition(state.lock)
            state.cases[case_id]["current_execution_id"] = run_id
            state.audit_event("run.created", actor, case_id=case_id, run_id=run_id)
            return self.get_run(run_id) or copy.deepcopy(run)

    def list_runs(self, case_id: str) -> list[Record]:
        with self._state.lock:
            return [
                self.get_run(run["id"])
                for run in self._state.runs.values()
                if run.get("case_id") == case_id
            ]

    def get_run(self, run_id: str) -> Record | None:
        return self._state.get_run(run_id)

    def latest_run(self, case_id: str) -> Record | None:
        runs = self.list_runs(case_id)
        return runs[-1] if runs else None

    def pending_runs(self) -> list[tuple[str, str]]:
        return self._state.pending_runs()

    def claim(self, run_id: str, worker: str) -> str | None:
        state = self._state
        with state.lock:
            run = state.runs.get(run_id)
            if not run or run.get("status") not in {"queued", "running"}:
                return None
            now = time.monotonic()
            job = state.jobs.get(run_id)
            if job and job["status"] == "running" and job["lease_until"] > now:
                return None
            active = sum(
                job["status"] == "running" and job["lease_until"] > now
                for job in state.jobs.values()
            ) + sum(
                job["status"] == "claimed" and job["lease_until"] > now
                for job in state.model_jobs.values()
            )
            if active >= MAX_ACTIVE_JOBS:
                return None
            token = state.new_id("attempt")
            state.jobs[run_id] = {
                "status": "running",
                "worker": worker,
                "attempt_token": token,
                "lease_until": now + state.lease_seconds,
                "budget_reserved": 1,
            }
            state._recover_running_nodes_locked(run_id)
            return token

    def renew(self, run_id: str, attempt_token: str) -> bool:
        state = self._state
        with state.lock:
            if not state._job_is_current_locked(run_id, attempt_token):
                return False
            state.jobs[run_id]["lease_until"] = time.monotonic() + state.lease_seconds
            return True

    def is_current(self, run_id: str, attempt_token: str) -> bool:
        return self._state.job_is_current(run_id, attempt_token)

    def finish(self, run_id: str, attempt_token: str) -> None:
        self._state.finish_job(run_id, attempt_token)

    def update_run_fenced(
        self, run_id: str, attempt_token: str, **changes: Any
    ) -> None:
        self._state.update_run_fenced(run_id, attempt_token, **changes)

    def update_node_fenced(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        **changes: Any,
    ) -> None:
        self._state.update_node_fenced(run_id, attempt_token, node_id, **changes)

    def pause_research_plan(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        research: Record,
    ) -> None:
        self._state.pause_research_plan_fenced(run_id, attempt_token, node_id, research)

    def approve_research_plan(self, run_id: str, actor: str, plan_hash: str) -> Record:
        state = self._state
        with state.lock:
            run = state.runs.get(run_id)
            if not run:
                raise ValueError("RUN_NOT_FOUND")
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
            current = state.source_sets.get(run["case_id"])
            pinned = research["proposed_plan"]["source_set"]
            if not current or (current["id"], current["version"]) != (
                pinned["id"],
                pinned["version"],
            ):
                raise ValueError("SOURCE_SET_CHANGED")
            job = state.jobs.get(run_id)
            if job is None:
                state.jobs[run_id] = {
                    "status": "queued",
                    "worker": None,
                    "attempt_token": None,
                    "lease_until": 0.0,
                    "budget_reserved": 0,
                }
            else:
                job.update(
                    status="queued",
                    worker=None,
                    attempt_token=None,
                    lease_until=0.0,
                    budget_reserved=0,
                )
            research.update(
                approved_plan_hash=plan_hash,
                approved_by=actor,
                approved_at=now_iso(),
                phase="approved",
            )
            run.update(status="queued", error=None)
            state.audit_event(
                "research.plan_approved",
                actor,
                case_id=run["case_id"],
                run_id=run_id,
                plan_hash=plan_hash,
            )
            self.emit(
                run_id,
                "research.plan_approved",
                {"plan_hash": plan_hash, "approved_by": actor},
            )
            return self.get_run(run_id) or copy.deepcopy(run)

    def emit(self, run_id: str, event: str, data: Record) -> None:
        self._state.emit(run_id, event, data)

    def emit_fenced(
        self, run_id: str, attempt_token: str, event: str, data: Record
    ) -> None:
        self._state.emit_fenced(run_id, attempt_token, event, data)

    def artifact_for_fingerprint(
        self, run_id: str, module_id: str, input_fingerprint: str
    ) -> Record | None:
        return self._state.artifact_for_fingerprint(
            run_id, module_id, input_fingerprint
        )

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
        state = self._state
        with state.lock:
            state._assert_job_locked(run_id, attempt_token)
            node = state.nodes.get(node_id)
            if (
                not node
                or node.get("run_id") != run_id
                or artifact.get("run_id") != run_id
                or artifact.get("module_id") != node.get("module_id")
            ):
                raise JobFencedError("artifact does not match the fenced node")
            completed = next(
                (
                    value
                    for value in state.artifacts.values()
                    if value.get("run_id") == run_id
                    and value.get("module_id") == node["module_id"]
                    and value.get("input_fingerprint")
                    == artifact.get("input_fingerprint")
                ),
                None,
            )
            candidate = copy.deepcopy(completed or artifact)
            if completed is None:
                candidate["id"] = state.new_id("art")
            if artifact_validator is not None and not artifact_validator(candidate):
                raise ValueError("ARTIFACT_INVALID")
            stored_artifact = copy.deepcopy(candidate)
            stored_research = copy.deepcopy(research) if research is not None else None
            stored_event_data = copy.deepcopy(event_data)
            result = copy.deepcopy(candidate)
            events = state.events[run_id]
            item = {
                "id": len(events) + 1,
                "event": "node.succeeded",
                "at": now_iso(),
                "data": {**stored_event_data, "artifact_id": candidate["id"]},
            }
            if completed is None:
                state.artifacts[candidate["id"]] = stored_artifact
            node.update(status="succeeded", artifact_id=candidate["id"], error=None)
            if research is not None:
                state.runs[run_id]["research"] = stored_research
            events.append(item)
            condition = state.event_conditions.get(run_id)
            if condition:
                condition.notify_all()
            return result

    def finalize_success(
        self,
        run_id: str,
        attempt_token: str,
        research: Record | None,
        event_data: Record,
        *,
        deadline: float | None = None,
    ) -> None:
        state = self._state
        with state.lock:
            run = state.runs.get(run_id)
            job = state.jobs.get(run_id)
            if (
                run
                and run.get("status") == "succeeded"
                and state._final_attempt_tokens.get(run_id) == attempt_token
                and job
                and job.get("status") == "finished"
                and job.get("attempt_token") == attempt_token
            ):
                return
            state._assert_job_locked(run_id, attempt_token)
            _remaining_finalization_seconds(deadline)
            state._assert_run_artifacts_ready_locked(run_id)
            stored_research = copy.deepcopy(research) if research is not None else None
            stored_event_data = copy.deepcopy(event_data)
            prior_run = copy.deepcopy(state.runs[run_id])
            prior_job = copy.deepcopy(state.jobs[run_id])
            prior_events = copy.deepcopy(state.events.get(run_id, []))
            had_prior_final_token = run_id in state._final_attempt_tokens
            prior_final_token = state._final_attempt_tokens.get(run_id)
            try:
                _remaining_finalization_seconds(deadline)
                run_changes: Record = {
                    "status": "succeeded",
                    "current_node_id": None,
                    "error": None,
                }
                if stored_research is not None:
                    run_changes["research"] = stored_research
                state.runs[run_id].update(run_changes)
                state._final_attempt_tokens[run_id] = attempt_token
                state.jobs[run_id].update(
                    status="finished", lease_until=0.0, budget_reserved=0
                )
                events = state.events.setdefault(run_id, [])
                events.append(
                    {
                        "id": len(events) + 1,
                        "event": "run.succeeded",
                        "at": now_iso(),
                        "data": stored_event_data,
                    }
                )
                _remaining_finalization_seconds(deadline)
            except Exception:
                state.runs[run_id] = prior_run
                state.jobs[run_id] = prior_job
                state.events[run_id] = prior_events
                if had_prior_final_token:
                    assert prior_final_token is not None
                    state._final_attempt_tokens[run_id] = prior_final_token
                else:
                    state._final_attempt_tokens.pop(run_id, None)
                raise
            condition = state.event_conditions.get(run_id)
            if condition:
                condition.notify_all()

    def get_artifact(self, artifact_id: str) -> Record | None:
        return self._state.get_artifact(artifact_id)

    def accept_snapshot(
        self, case_id: str, run_id: str, actor: str, snapshot: Record
    ) -> Record:
        state = self._state
        with state.lock:
            run = state.runs.get(run_id)
            case = state.cases.get(case_id)
            if not run or run.get("case_id") != case_id or case is None:
                raise ValueError("RUN_NOT_FOUND")

            final_attempt_token = state._final_attempt_tokens.get(run_id)
            final_job = state.jobs.get(run_id)
            if (
                run.get("status") != "succeeded"
                or not final_attempt_token
                or not final_job
                or final_job.get("status") != "finished"
                or final_job.get("attempt_token") != final_attempt_token
            ):
                raise ValueError("RUN_NOT_READY")

            accepted_id = run.get("accepted_snapshot_id")
            if accepted_id:
                return copy.deepcopy(state.snapshots[accepted_id])

            proposal = copy.deepcopy(snapshot)
            if proposal.get("case_id") != case_id or proposal.get("run_id") != run_id:
                raise ValueError("RUN_NOT_FOUND")

            source_set_id = proposal.get("source_set_id")
            source_set = state.source_set_history.get(source_set_id)
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

            nodes = state.nodes
            expected_ids = {
                nodes[node_id].get("artifact_id") for node_id in run.get("node_ids", [])
            }
            if (
                len(artifact_refs) != len(expected_ids)
                or any(not isinstance(item, dict) for item in artifact_refs)
                or {item.get("id") for item in artifact_refs} != expected_ids
            ):
                raise ValueError("RUN_NOT_READY")

            get_artifact = state.artifacts.get
            for item in artifact_refs:
                if not isinstance(item, dict):
                    raise ValueError("RUN_NOT_READY")
                artifact = get_artifact(item.get("id"))
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
                valid_snapshot_digest = proposal.get("digest") == digest(payload)
            except (TypeError, ValueError):
                valid_snapshot_digest = False
            if not valid_snapshot_digest:
                raise ValueError("RUN_NOT_READY")

            saved_id = state.new_id("snap")
            proposal["id"] = saved_id
            proposal["previous_snapshot_id"] = case.get("accepted_snapshot_id")
            state.snapshots[saved_id] = proposal
            case["accepted_snapshot_id"] = saved_id
            if not case.get("visible_snapshot_id"):
                case["visible_snapshot_id"] = saved_id
            run["accepted_snapshot_id"] = saved_id

            state.audit_event(
                "snapshot.accepted",
                actor,
                case_id=case_id,
                run_id=run_id,
                snapshot_id=saved_id,
            )
            self.emit(
                run_id,
                "snapshot.accepted",
                {"snapshot_id": saved_id, "digest": proposal["digest"]},
            )
            return copy.deepcopy(proposal)

    def get_snapshot(self, snapshot_id: str) -> Record | None:
        return self._state.get_snapshot(snapshot_id)

    def switch_visible_snapshot(
        self, case_id: str, snapshot_id: str, actor: str
    ) -> Record | None:
        state = self._state
        with state.lock:
            case = state.cases.get(case_id)
            snapshot = state.snapshots.get(snapshot_id)
            if not case or not snapshot or snapshot.get("case_id") != case_id:
                return None
            case["visible_snapshot_id"] = snapshot_id
            state.audit_event(
                "snapshot.visible_switched",
                actor,
                case_id=case_id,
                snapshot_id=snapshot_id,
            )
            return copy.deepcopy(snapshot)

    def events_after(self, run_id: str, cursor: int = 0) -> list[Record]:
        return self._state.events_after(run_id, cursor)

    def wait_for_events(
        self, run_id: str, cursor: int, timeout: float = 1.0
    ) -> list[Record]:
        return self._state.wait_for_events(run_id, cursor, timeout)


class _MemoryPublicationLedger(_Adapter):
    def __init__(self, state: _MemoryState, sources: SourceCatalog) -> None:
        super().__init__(state)
        self._sources = sources

    def _validate_refs(
        self, case_id: str, refs: list[str], *, artifacts_only: bool = False
    ) -> None:
        state = self._state
        for ref in refs:
            artifact = state.artifacts.get(ref)
            if artifact and artifact.get("case_id") == case_id:
                continue
            if not artifacts_only:
                source = state.sources.get(ref)
                snapshot = state.snapshots.get(ref)
                if source and source.get("case_id") == case_id:
                    if source.get("withdrawn"):
                        raise ValueError("EVIDENCE_SOURCE_WITHDRAWN")
                    continue
                if snapshot and snapshot.get("case_id") == case_id:
                    continue
            raise ValueError("EVIDENCE_CASE_MISMATCH")

    @staticmethod
    def _current_version(bucket: dict[str, list[Record]], case_id: str) -> int:
        versions = bucket.get(case_id, [])
        return versions[-1]["version"] if versions else 0

    def append_thesis(
        self, case_id: str, actor: str, expected_version: int, thesis: Record
    ) -> Record:
        state = self._state
        with state.lock:
            self._validate_refs(case_id, list(thesis.get("evidence_ids", [])))
            current = self._current_version(state.theses, case_id)
            if current != expected_version:
                raise ValueError("VERSION_CONFLICT")
            saved = copy.deepcopy(thesis)
            saved.update(
                id=state.new_id("thesis"),
                case_id=case_id,
                author=actor,
                version=current + 1,
                created_at=now_iso(),
            )
            state.theses.setdefault(case_id, []).append(saved)
            state.audit_event(
                "thesis.versioned", actor, case_id=case_id, version=saved["version"]
            )
            return copy.deepcopy(saved)

    def list_theses(self, case_id: str) -> list[Record]:
        with self._state.lock:
            return copy.deepcopy(self._state.theses.get(case_id, []))

    def append_recommendations(
        self,
        case_id: str,
        actor: str,
        expected_version: int,
        recommendations: Record,
    ) -> Record:
        state = self._state
        with state.lock:
            refs = list(recommendations.get("analytical_dependency_ids", []))
            self._validate_refs(case_id, refs, artifacts_only=True)
            current = self._current_version(state.recommendations, case_id)
            if current != expected_version:
                raise ValueError("VERSION_CONFLICT")
            saved = copy.deepcopy(recommendations)
            saved.update(
                id=state.new_id("rec"),
                case_id=case_id,
                author=actor,
                accepted_snapshot_id=recommendations.get("accepted_snapshot_id"),
                stale=False,
                stale_reasons=[],
                version=current + 1,
                created_at=now_iso(),
            )
            state.recommendations.setdefault(case_id, []).append(saved)
            state.audit_event(
                "recommendation.versioned",
                actor,
                case_id=case_id,
                version=saved["version"],
            )
            return copy.deepcopy(saved)

    def list_recommendations(self, case_id: str) -> list[Record]:
        with self._state.lock:
            return copy.deepcopy(self._state.recommendations.get(case_id, []))

    def save_report_inputs(
        self,
        case_id: str,
        actor: str,
        thesis: Record,
        recommendations: Record,
        accepted_snapshot_id: str | None,
    ) -> Record:
        state = self._state
        with state.lock:
            self._validate_refs(case_id, list(thesis.get("evidence_ids", [])))
            self._validate_refs(
                case_id,
                list(recommendations.get("analytical_dependency_ids", [])),
                artifacts_only=True,
            )
            thesis_version = self._current_version(state.theses, case_id)
            recommendation_version = self._current_version(
                state.recommendations, case_id
            )
            if thesis_version != thesis.get(
                "expected_version"
            ) or recommendation_version != recommendations.get("expected_version"):
                raise ValueError("VERSION_CONFLICT")
            saved_thesis = {
                key: copy.deepcopy(value)
                for key, value in thesis.items()
                if key != "expected_version"
            }
            saved_thesis.update(
                id=state.new_id("thesis"),
                case_id=case_id,
                author=actor,
                version=thesis_version + 1,
                created_at=now_iso(),
            )
            saved_recommendations = {
                key: copy.deepcopy(value)
                for key, value in recommendations.items()
                if key != "expected_version"
            }
            saved_recommendations.update(
                id=state.new_id("rec"),
                case_id=case_id,
                author=actor,
                accepted_snapshot_id=accepted_snapshot_id,
                stale=False,
                stale_reasons=[],
                version=recommendation_version + 1,
                created_at=now_iso(),
            )
            state.theses.setdefault(case_id, []).append(saved_thesis)
            state.recommendations.setdefault(case_id, []).append(saved_recommendations)
            state.audit_event(
                "thesis.versioned",
                actor,
                case_id=case_id,
                version=saved_thesis["version"],
            )
            state.audit_event(
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
        state = self._state
        with state.lock:
            note = {
                "id": state.new_id("note"),
                "case_id": case_id,
                "author": actor,
                "body": body,
                "promoted": False,
                "created_at": now_iso(),
            }
            state.notes.setdefault(case_id, []).append(note)
            state.audit_event(
                "note.created", actor, case_id=case_id, note_id=note["id"]
            )
            return copy.deepcopy(note)

    def list_notes(self, case_id: str) -> list[Record]:
        with self._state.lock:
            return copy.deepcopy(self._state.notes.get(case_id, []))

    def promote_note(self, case_id: str, note_id: str, actor: str) -> Record:
        state = self._state
        with state.lock:
            note = next(
                (
                    item
                    for item in state.notes.get(case_id, [])
                    if item["id"] == note_id
                ),
                None,
            )
            if not note:
                raise KeyError("NOTE_NOT_FOUND")
            if note["author"] != actor:
                raise PermissionError("only note author can promote")
            before = copy.deepcopy(
                (
                    note,
                    state.sources,
                    state.source_sets,
                    state.source_set_history,
                    state.audit,
                )
            )
            try:
                return self._sources.ingest_promoted_note(note, actor)
            except Exception:
                note.clear()
                note.update(before[0])
                (
                    state.sources,
                    state.source_sets,
                    state.source_set_history,
                    state.audit,
                ) = before[1:]
                raise

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
        state = self._state
        with state.lock:
            self._validate_refs(case_id, evidence_ids)
            assumption = {
                "id": state.new_id("assumption"),
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
            state.assumptions.setdefault(case_id, []).append(assumption)
            state.audit_event(
                "assumption.created",
                actor,
                case_id=case_id,
                assumption_id=assumption["id"],
            )
            return copy.deepcopy(assumption)

    def list_assumptions(self, case_id: str) -> list[Record]:
        with self._state.lock:
            return copy.deepcopy(self._state.assumptions.get(case_id, []))

    def _model_identity(
        self, requested: Record | None, snapshot: Record
    ) -> Record | None:
        if requested is None:
            return None
        if not isinstance(requested, dict):
            raise ValueError("MODEL_SNAPSHOT_MISMATCH")
        build = self._state.model_builds.get(requested.get("build_id"))
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

    def _validate_report_authority(self, case_id: str, report: Record) -> None:
        state = self._state
        content = report.get("content")
        if not isinstance(content, dict):
            raise ValueError("SNAPSHOT_REQUIRED")
        case = state.cases.get(case_id)
        snapshot = state.snapshots.get(content.get("snapshot_id"))
        snapshot_digest = content.get("snapshot_digest")
        if (
            not case
            or not snapshot
            or snapshot.get("case_id") != case_id
            or report.get("snapshot_digest") != snapshot_digest
            or snapshot_digest != digest(snapshot)
        ):
            raise ValueError("SNAPSHOT_REQUIRED")
        visible_snapshot_id = case.get("visible_snapshot_id") or case.get(
            "accepted_snapshot_id"
        )
        if visible_snapshot_id != snapshot.get("id"):
            raise ValueError("STALE_PREVIEW")
        theses = state.theses.get(case_id, [])
        recommendations = state.recommendations.get(case_id, [])
        thesis = next(
            (
                row
                for row in theses
                if row.get("version") == content.get("thesis_version")
            ),
            None,
        )
        recommendation = next(
            (
                row
                for row in recommendations
                if row.get("version") == content.get("recommendation_version")
            ),
            None,
        )
        if (
            not thesis
            or not recommendation
            or recommendation.get("accepted_snapshot_id") != snapshot.get("id")
        ):
            raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")
        model = self._model_identity(content.get("model"), snapshot)
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
        state = self._state
        with state.lock:
            self._validate_report_authority(case_id, report)
            saved = copy.deepcopy(report)
            saved.update(
                id=state.new_id("report"),
                case_id=case_id,
                created_by=actor,
                created_at=now_iso(),
                status="PENDING_APPROVAL",
            )
            state.reports[case_id] = saved
            state.audit_event(
                "report.frozen", actor, case_id=case_id, report_id=saved["id"]
            )
            return copy.deepcopy(saved)

    def get_report(self, case_id: str) -> Record | None:
        with self._state.lock:
            report = self._state.reports.get(case_id)
            return copy.deepcopy(report) if report else None

    def approve_report(
        self,
        case_id: str,
        actor: str,
        expected_status: str,
        preview_digest: str,
        input_fingerprint: str,
        comment: str | None,
    ) -> Record:
        state = self._state
        with state.lock:
            report = state.reports.get(case_id)
            if not report or report.get("status") != expected_status:
                raise ValueError("report changed or missing")
            if preview_digest != report.get(
                "preview_digest"
            ) or input_fingerprint != report.get("input_fingerprint"):
                raise ValueError("STALE_PREVIEW")
            try:
                self._validate_report_authority(case_id, report)
            except ValueError as exc:
                raise ValueError("STALE_PREVIEW") from exc
            report.update(
                status="APPROVED",
                approved_by=actor,
                approved_at=now_iso(),
                approval_comment=comment,
            )
            state.audit_event(
                "report.approved", actor, case_id=case_id, report_id=report["id"]
            )
            return copy.deepcopy(report)

    def save_rv_universe(self, case_id: str, actor: str, universe: Record) -> Record:
        state = self._state
        with state.lock:
            current = state.rv_universes.get(case_id)
            saved = copy.deepcopy(universe)
            saved.update(
                id=state.new_id("rv"),
                case_id=case_id,
                created_by=actor,
                version=current.get("version", 0) + 1 if current else 1,
                created_at=now_iso(),
            )
            state.rv_universes[case_id] = saved
            state.audit_event(
                "rv.universe_versioned",
                actor,
                case_id=case_id,
                version=saved["version"],
            )
            return copy.deepcopy(saved)

    def get_rv_universe(self, case_id: str) -> Record | None:
        with self._state.lock:
            value = self._state.rv_universes.get(case_id)
            return copy.deepcopy(value) if value else None

    def list_audit(self) -> list[Record]:
        with self._state.lock:
            return copy.deepcopy(self._state.audit)

    def create_methodology_draft(self, draft: Record, actor: str) -> Record:
        state = self._state
        with state.lock:
            saved = copy.deepcopy(draft)
            saved.update(
                id=state.new_id("draft"),
                status="DRAFT",
                created_by=actor,
                created_at=now_iso(),
            )
            saved.setdefault(
                "semantic_diff",
                {"before": saved.get("before"), "after": saved.get("after")},
            )
            saved["digest"] = digest(saved)
            state.methodology_drafts[saved["id"]] = saved
            state.audit_event(
                "methodology.draft_created",
                actor,
                draft_id=saved["id"],
                module_id=saved.get("module_id"),
            )
            return copy.deepcopy(saved)

    def list_methodology_drafts(self) -> list[Record]:
        with self._state.lock:
            return copy.deepcopy(list(self._state.methodology_drafts.values()))

    def validate_methodology_draft(self, draft_id: str, actor: str) -> Record:
        state = self._state
        with state.lock:
            draft = state.methodology_drafts.get(draft_id)
            if not draft:
                raise KeyError("draft not found")
            if draft.get("before") == draft.get("after"):
                raise ValueError(
                    "draft does not validate against the current authority"
                )
            draft.update(status="VALIDATED", validated_by=actor, validated_at=now_iso())
            state.audit_event("methodology.draft_validated", actor, draft_id=draft_id)
            return copy.deepcopy(draft)

    def confirm_methodology_draft(
        self, draft_id: str, actor: str, signature: str
    ) -> Record:
        state = self._state
        with state.lock:
            draft = state.methodology_drafts.get(draft_id)
            if not draft:
                raise KeyError("draft not found")
            if draft.get("status") != "VALIDATED":
                raise ValueError("validated draft required")
            draft.update(
                status="CONFIRMED_PENDING_SIGNED_AUTHORITY",
                confirmed_by=actor,
                confirmed_at=now_iso(),
                signature=signature,
            )
            state.audit_event(
                "methodology.draft_confirmed",
                actor,
                draft_id=draft_id,
                signature=signature,
            )
            return copy.deepcopy(draft)


class _MemoryModelLedger(_Adapter):
    def queue_build(self, build: Record, actor: str) -> tuple[Record, bool]:
        proposal = copy.deepcopy(build)
        proposal["id"] = self._state.new_id("model")
        return self._state.queue_model_build(proposal, actor)

    def retry_build(self, build_id: str, actor: str) -> Record:
        return self._state.retry_model_build(build_id, actor)

    def get_build(self, build_id: str) -> Record | None:
        return self._state.get_model_build(build_id)

    def list_builds(self, case_id: str) -> list[Record]:
        return self._state.list_model_builds(case_id)

    def queue_export(self, build_id: str, actor: str) -> tuple[Record, bool]:
        return self._state.queue_model_export(build_id, actor)

    def pending_jobs(self) -> list[tuple[str, str, str]]:
        return self._state.pending_model_jobs()

    def claim(self, build_id: str, worker: str, kind: str = "calculate") -> str | None:
        state = self._state
        with state.lock:
            key = _model_job_key(build_id, kind)
            job = state.model_jobs.get(key)
            build = state.model_builds.get(build_id)
            if not job or not build:
                return None
            now = time.monotonic()
            if job["status"] == "claimed" and job["lease_until"] > now:
                return None
            if job["status"] not in {"queued", "claimed"}:
                return None
            active = sum(
                job["status"] == "running" and job["lease_until"] > now
                for job in state.jobs.values()
            ) + sum(
                job["status"] == "claimed" and job["lease_until"] > now
                for job in state.model_jobs.values()
            )
            if active >= MAX_ACTIVE_JOBS:
                return None
            token = state.new_id("attempt")
            job.update(
                status="claimed",
                worker=worker,
                attempt_token=token,
                lease_until=now + state.lease_seconds,
                error=None,
            )
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
            return token

    def renew(self, build_id: str, attempt_token: str, kind: str = "calculate") -> bool:
        state = self._state
        with state.lock:
            key = _model_job_key(build_id, kind)
            if not state._model_job_is_current_locked(key, attempt_token):
                return False
            state.model_jobs[key]["lease_until"] = (
                time.monotonic() + state.lease_seconds
            )
            return True

    def is_current(
        self, build_id: str, attempt_token: str, kind: str = "calculate"
    ) -> bool:
        return self._state.model_job_is_current(build_id, attempt_token, kind)

    def complete(
        self,
        build_id: str,
        attempt_token: str,
        result: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record:
        return self._state.complete_model_job(
            build_id, attempt_token, result, actor, kind
        )

    def fail(
        self,
        build_id: str,
        attempt_token: str,
        error: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record:
        return self._state.fail_model_job(build_id, attempt_token, error, actor, kind)

    def record_export_download(self, build_id: str, case_id: str, actor: str) -> None:
        state = self._state
        with state.lock:
            build = state.model_builds.get(build_id)
            if (
                not build
                or build.get("case_id") != case_id
                or (build.get("export") or {}).get("status") != "READY"
            ):
                raise ValueError("MODEL_EXPORT_NOT_READY")
            state.audit_event(
                "model.export.downloaded",
                actor,
                case_id=case_id,
                build_id=build_id,
            )


class MemoryLedgerSet:
    """Four narrow adapters sharing one private state object and one RLock."""

    __slots__ = ("sources", "runs", "publications", "models")

    def __init__(self, *, lease_seconds: float = 60.0) -> None:
        state = _MemoryState(lease_seconds)
        sources = _MemorySourceCatalog(state)
        self.sources = sources
        self.runs = _MemoryRunLedger(state)
        self.publications = _MemoryPublicationLedger(state, sources)
        self.models = _MemoryModelLedger(state)
