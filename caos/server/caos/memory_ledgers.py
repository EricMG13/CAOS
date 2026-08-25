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
    MemoryStore,
    _model_job_key,
    now_iso,
)


Record = dict[str, Any]


class _MemoryState(MemoryStore):
    """One private state carrier shared by all four memory adapters."""

    def __init__(self, lease_seconds: float) -> None:
        super().__init__()
        self.lease_seconds = lease_seconds

    @staticmethod
    def new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    def _id(self, prefix: str) -> str:
        return self.new_id(prefix)


class _Adapter:
    __slots__ = ("_state",)

    def __init__(self, state: _MemoryState) -> None:
        self._state = state


def _public_source(source: Record) -> Record:
    return copy.deepcopy(
        {key: value for key, value in source.items() if key != "vault_path"}
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
        source_id = state.new_id("src-note")
        body = note["body"]
        body_bytes = body.encode()
        sha256 = hashlib.sha256(body_bytes).hexdigest()
        if any(
            source.get("case_id") == note["case_id"]
            and source.get("sha256") == sha256
            and not source.get("withdrawn")
            for source in state.sources.values()
        ):
            raise ValueError("source content already active")
        source = {
            "id": source_id,
            "case_id": note["case_id"],
            "filename": f"analyst-note-{note['id']}.md",
            "media_type": "text/markdown",
            "bytes": len(body_bytes),
            "sha256": sha256,
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
        with self._state.lock:
            return self._ingest_promoted_note_locked(note, actor)

    def withdraw(self, case_id: str, source_id: str, actor: str) -> Record | None:
        state = self._state
        with state.lock:
            source = state.sources.get(source_id)
            if (
                not source
                or source.get("case_id") != case_id
                or source.get("withdrawn")
            ):
                return None
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
    ) -> Record:
        state = self._state
        with state.lock:
            if case_id not in state.cases:
                raise ValueError("CASE_NOT_FOUND")
            created_at = now_iso()
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
                "status": "queued",
                "plan": copy.deepcopy(plan),
                "node_ids": [node["id"] for node in node_records],
                "current_node_id": None,
                "accepted_snapshot_id": None,
                "upgraded_from_run_id": upgraded_from_run_id,
                "error": None,
            }
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
            if run_id not in state.runs:
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
            stored = copy.deepcopy(candidate) if completed is None else None
            stored_research = copy.deepcopy(research) if research is not None else None
            run = state.runs[run_id] if research is not None else None
            event_payload = copy.deepcopy(event_data)
            item = {
                "id": len(state.events.get(run_id, [])) + 1,
                "event": "node.succeeded",
                "at": now_iso(),
                "data": {**event_payload, "artifact_id": candidate["id"]},
            }
            result = copy.deepcopy(candidate)

            if completed is None:
                state.artifacts[candidate["id"]] = stored
            node.update(status="succeeded", artifact_id=candidate["id"], error=None)
            if run is not None:
                run["research"] = stored_research
            state.events.setdefault(run_id, []).append(item)
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
        self._state.finalize_run_success_fenced(
            run_id,
            attempt_token,
            research,
            event_data,
            deadline=deadline,
        )

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

            accepted_id = run.get("accepted_snapshot_id")
            if accepted_id:
                return copy.deepcopy(state.snapshots[accepted_id])
            if run.get("status") != "succeeded":
                raise ValueError("RUN_NOT_READY")

            proposal = copy.deepcopy(snapshot)
            if proposal.get("case_id") != case_id or proposal.get("run_id") != run_id:
                raise ValueError("RUN_NOT_FOUND")

            source_set_id = proposal.get("source_set_id")
            source_set = state.source_set_history.get(source_set_id)
            current = state.source_sets.get(case_id)
            if (
                not source_set
                or source_set.get("case_id") != case_id
                or source_set_id != run.get("plan", {}).get("source_set_id")
                or proposal.get("source_set_version") != source_set.get("version")
                or not current
                or current.get("id") != source_set.get("id")
                or current.get("version") != source_set.get("version")
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
            or case.get("accepted_snapshot_id") != snapshot.get("id")
            or report.get("snapshot_digest") != snapshot_digest
            or snapshot_digest != digest(snapshot)
        ):
            raise ValueError("SNAPSHOT_REQUIRED")
        theses = state.theses.get(case_id, [])
        recommendations = state.recommendations.get(case_id, [])
        if not theses or not recommendations:
            raise ValueError("THESIS_AND_RECOMMENDATIONS_REQUIRED")

        thesis = theses[-1]
        recommendation = recommendations[-1]
        if (
            content.get("thesis_version") != thesis.get("version")
            or content.get("recommendation_version") != recommendation.get("version")
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
                author=actor,
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
