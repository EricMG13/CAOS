from __future__ import annotations

import copy
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Iterator

from ..artifacts.domain import build_snapshot_payload
from ..config import Settings
from ..contracts import Depth, digest
from ..methodology.bundle import DeployVBundle
from ..sources.domain import Vault, current_source_set
from ..store import JobFencedError, MemoryStore, now_iso


HEARTBEAT_INTERVAL_SECONDS = 20


class _LeaseFence:
    def __init__(self) -> None:
        self.lost = threading.Event()
        self.lock = threading.Lock()

    def call(self, method: Any, *args: Any, **kwargs: Any) -> Any:
        with self.lock:
            if self.lost.is_set():
                raise JobFencedError("lost workflow lease")
            return method(*args, **kwargs)

    def lose(self) -> None:
        with self.lock:
            self.lost.set()


class WorkflowError(ValueError):
    pass


@dataclass(frozen=True)
class _PlanningPause(Exception):
    research: dict[str, Any]


class WorkflowRuntime:
    def __init__(self, store: MemoryStore, bundle: DeployVBundle, settings: Settings) -> None:
        self.store = store
        self.bundle = bundle
        self.settings = settings
        self.vault = Vault(settings)
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="caos-worker")
        # ponytail: process-local cap; add a DB reservation when multi-worker capacity needs a measured global budget.
        self._node_slots = threading.BoundedSemaphore(4)
        self._futures: dict[str, Future[Any]] = {}
        self._futures_lock = threading.Lock()

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def start_run(self, case_id: str, actor: str, pathway: str, depth: Depth, focus_questions: list[str], research_brief: dict[str, Any] | None = None, upgraded_from_run_id: str | None = None) -> dict[str, Any]:
        source_set = current_source_set(self.store, case_id)
        plan = self.bundle.compile(pathway, depth, source_set["id"] if source_set else None, focus_questions, source_set["version"] if source_set else None)
        run = self.store.create_run(case_id, actor, plan, [], upgraded_from_run_id)
        if pathway == "DEEP_RESEARCH":
            case = self.store.get_case(case_id)
            if not case or research_brief is None:
                raise WorkflowError("RESEARCH_BRIEF_REQUIRED")
            brief = {
                **copy.deepcopy(research_brief),
                "scope_type": "issuer",
                "scope_key": case_id.replace("_", "-"),
                "subject_name": case["issuer"],
                "source_mode": "supplied_only",
                "research_budget": "standard",
                "plan_approval": "required",
            }
            budget_limits = {"turns": 8, "evidence_reads": 12, "evidence_bytes": 1024 * 1024, "input_tokens": 100_000, "output_tokens": 8_000, "active_minutes": 3, "provider_retries": 1, "repairs": 1}
            self.store.update_run(run["id"], research={
                "brief": brief,
                "phase": "planning",
                "proposed_plan": None,
                "proposed_plan_hash": None,
                "approved_plan_hash": None,
                "approved_by": None,
                "approved_at": None,
                "model": self.settings.anthropic_model,
                "budget_limits": budget_limits,
                "budget_used": {key: 0 for key in budget_limits},
                "inflight_request_digest": None,
                "attempts": [],
            })
        node_records = []
        logical_ids: dict[str, str] = {}
        for plan_node in plan["nodes"]:
            node = self.store.add_node(run["id"], case_id, plan_node["module_id"], plan_node["dependencies"], plan_node["stage"])
            node_records.append(node)
            logical_ids[plan_node["module_id"]] = node["id"]
        runnable = bool(source_set and source_set["source_ids"])
        empty_source_error = None if runnable else {"code": "SOURCE_SET_EMPTY", "message": "Upload and version source material before execution."}
        self.store.update_run(run["id"], node_ids=[node["id"] for node in node_records], status="queued" if runnable else "paused", error=empty_source_error)
        with self.store.lock:
            self.store.cases[case_id]["current_execution_id"] = run["id"]
            self.store.persist()
        self.store.emit(run["id"], "run.created", {"run_id": run["id"], "plan_digest": plan["plan_digest"], "profile_id": plan["profile_id"], "selection_id": plan["selection_id"]})
        if not runnable:
            self.store.emit(run["id"], "run.paused", {"code": "SOURCE_SET_EMPTY"})
        elif self.settings.environment != "production":
            future = self.executor.submit(self._execute, run["id"], actor)
            with self._futures_lock:
                self._futures[run["id"]] = future
        return self.store.get_run(run["id"]) or run

    def _execute(self, run_id: str, actor: str) -> None:
        worker = threading.current_thread().name
        attempt_token = self.store.claim_job(run_id, worker)
        if not attempt_token:
            return
        heartbeat_stop = threading.Event()
        lease_fence = _LeaseFence()

        def fenced_call(method: Any, *args: Any, **kwargs: Any) -> Any:
            return lease_fence.call(method, run_id, attempt_token, *args, **kwargs)

        def heartbeat() -> None:
            while not heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
                try:
                    if self.store.renew_job(run_id, attempt_token):
                        continue
                except Exception:
                    pass
                lease_fence.lose()
                return

        heartbeat_thread = threading.Thread(target=heartbeat, name=f"{worker}-heartbeat", daemon=True)
        heartbeat_thread.start()
        try:
            fenced_call(self.store.update_run_fenced, status="running", error=None)
            fenced_call(self.store.emit_fenced, "run.running", {"run_id": run_id, "worker": worker})
            while True:
                if lease_fence.lost.is_set() or not self.store.job_is_current(run_id, attempt_token):
                    return
                run = self.store.get_run(run_id)
                if lease_fence.lost.is_set() or not run:
                    return
                pending = [node for node in run["nodes"] if node["status"] in {"pending", "ready"}]
                completed = {node["module_id"] for node in run["nodes"] if node["status"] == "succeeded"}
                if not pending:
                    fenced_call(self.store.update_run_fenced, status="succeeded", current_node_id=None)
                    fenced_call(self.store.emit_fenced, "run.succeeded", {"run_id": run_id})
                    return
                ready = [node for node in pending if set(node["dependencies"]).issubset(completed)]
                if not ready:
                    fenced_call(self.store.update_run_fenced, status="failed", error={"code": "DAG_BLOCKED", "message": "No dependency-safe ready nodes remain."})
                    fenced_call(self.store.emit_fenced, "run.failed", {"code": "DAG_BLOCKED"})
                    return
                for node in ready:
                    fenced_call(self.store.update_node_fenced, node["id"], status="running", attempt=node["attempt"] + 1)
                    fenced_call(self.store.emit_fenced, "node.running", {"node_id": node["id"], "module_id": node["module_id"]})
                with ThreadPoolExecutor(max_workers=min(4, len(ready)), thread_name_prefix="caos-node") as pool:
                    futures = {pool.submit(self._build_artifact_with_slot, run, node, actor): node for node in ready}
                    for future, node in ((future, futures[future]) for future in futures):
                        try:
                            artifact_data = future.result()
                            if lease_fence.lost.is_set():
                                return
                            artifact = fenced_call(self.store.put_artifact_fenced, artifact_data)
                        except JobFencedError:
                            return
                        except _PlanningPause as outcome:
                            if lease_fence.lost.is_set():
                                return
                            try:
                                fenced_call(self.store.pause_research_plan_fenced, node["id"], outcome.research)
                                fenced_call(self.store.emit_fenced, "research.plan_ready", {"plan_hash": outcome.research["proposed_plan_hash"]})
                                fenced_call(self.store.emit_fenced, "run.paused", {"code": "PLAN_APPROVAL_REQUIRED"})
                            except JobFencedError:
                                return
                            return
                        except Exception as exc:
                            if lease_fence.lost.is_set():
                                return
                            try:
                                fenced_call(self.store.update_node_fenced, node["id"], status="failed", error={"code": "NODE_ERROR", "message": str(exc)})
                                fenced_call(self.store.update_run_fenced, status="failed", error={"code": "NODE_ERROR", "module_id": node["module_id"], "message": str(exc)})
                            except JobFencedError:
                                return
                            fenced_call(self.store.emit_fenced, "node.failed", {"node_id": node["id"], "module_id": node["module_id"], "message": str(exc)})
                            fenced_call(self.store.emit_fenced, "run.failed", {"code": "NODE_ERROR", "module_id": node["module_id"]})
                            return
                        fenced_call(self.store.update_node_fenced, node["id"], status="succeeded", artifact_id=artifact["id"], error=None)
                        fenced_call(self.store.emit_fenced, "node.succeeded", {"node_id": node["id"], "module_id": node["module_id"], "artifact_id": artifact["id"]})
        except JobFencedError:
            return
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join()
            if not lease_fence.lost.is_set():
                self.store.finish_job(run_id, attempt_token)

    def _build_artifact_with_slot(self, run: dict[str, Any], node: dict[str, Any], actor: str) -> dict[str, Any]:
        with self._node_slots:
            return self._build_artifact(run, node, actor)

    def _build_artifact(self, run: dict[str, Any], node: dict[str, Any], actor: str) -> dict[str, Any]:
        plan = run["plan"]
        source_set = self.store.source_set_by_id(plan.get("source_set_id"))
        if not source_set:
            raise WorkflowError("SOURCE_SET_CHANGED")
        source_ids = list(source_set["source_ids"])
        upstream_artifacts = []
        for dependency in node["dependencies"]:
            dependency_node = next((candidate for candidate in run["nodes"] if candidate["module_id"] == dependency), None)
            dependency_artifact = self.store.get_artifact(dependency_node["artifact_id"]) if dependency_node and dependency_node.get("artifact_id") else None
            if not dependency_artifact:
                raise WorkflowError("UPSTREAM_ARTIFACT_MISSING")
            upstream_artifacts.append({"module_id": dependency, "artifact_id": dependency_artifact["id"], "digest": dependency_artifact["digest"]})
        input_fingerprint = digest({"plan": plan["plan_digest"], "module": node["module_id"], "source_set": source_set, "source_ids": source_ids, "upstream_artifacts": upstream_artifacts})
        if node["module_id"] == "CP-DR":
            research = copy.deepcopy(run.get("research"))
            if not research:
                raise WorkflowError("RESEARCH_BRIEF_REQUIRED")
            if research.get("phase") == "planning":
                proposed_plan, proposed_plan_hash = self.bundle.plan_research(research["brief"], source_set["id"], source_set["version"], upstream_artifacts)
                research.update(phase="awaiting_approval", proposed_plan=proposed_plan, proposed_plan_hash=proposed_plan_hash)
                raise _PlanningPause(research)
            if research.get("phase") == "approved":
                raise WorkflowError("CP_DR_RESEARCH_EXECUTION_UNAVAILABLE")
            raise WorkflowError("CP_DR_RESEARCH_PHASE_INVALID")
        model_blocked = node["module_id"] in {"CP-2G", "CP-MODEL"}
        visual_kind = {
            "CP-L10": "variance_bridge",
            "CP-1": "trend",
            "CP-1B": "variance_bridge",
            "CP-2A": "scenario_path",
            "CP-2G": "scenario_path",
            "CP-3": "rv_scatter",
            "CP-4": "covenant_headroom",
            "CP-4C": "recovery_waterfall",
            "CP-5": "dag",
        }.get(node["module_id"], "table")
        summary = {
            "CP-PARSE": "Prepared source blocks and minted the immutable profile selection.",
            "CP-0": "Source coverage is ready for the selected pathway; pathway fit is not a readiness conclusion.",
            "CP-L10": "The screen identified the governed financial-change deltas for analyst review.",
            "CP-1": "Canonical credit facts are organized by period and source locator.",
            "CP-1B": "Earnings deltas are tied to the accepted source set.",
            "CP-2": "System analysis frames the credit posture without writing analyst recommendations.",
            "CP-2G": "Forward credit model output is blocked pending the signed Deploy V CP-MODEL correction.",
            "CP-3": "Relative-value comparability remains separate from instrument recommendation authority.",
            "CP-4": "Legal and covenant observations remain evidence-bound and provisional.",
            "CP-4C": "Recovery and restructuring observations remain scenario disclosures, not probabilities.",
            "CP-5": "Evidence trace validation completed for the preceding analytical artifacts.",
        }.get(node["module_id"], f"{node['module_id']} completed with governed source lineage.")
        payload = {
            "module_id": node["module_id"],
            "schema_version": "deploy-v-host-v1",
            "status": "BLOCKED" if model_blocked else "COMPLETE",
            "authority": "SYSTEM_ANALYSIS",
            "confidence": {"value": 40, "label": "Low", "method_version": "deploy-v-confidence-v1"},
            "provenance": {"methodology_build_id": plan["build_id"], "profile_id": plan["profile_id"], "selection_id": plan["selection_id"], "upstream_artifact_digests": upstream_artifacts},
            "summary": summary,
            "evidence_refs": source_ids,
            "lineage": {"case_id": run["case_id"], "run_id": run["id"], "source_set_id": source_set["id"], "input_fingerprint": input_fingerprint, "upstream_artifacts": upstream_artifacts},
            "narrative": {"takeaway": summary, "basis": "Typed payload generated from the pinned Deploy V route and immutable source-set identity.", "exceptions": "Signed Deploy V CP-MODEL correction required; no model values are emitted." if model_blocked else "No model provider call is required for this deterministic host slice."},
            "visual": {"kind": visual_kind, "accessible_table": True, "period": "LTM", "units": "governed source units", "freshness": "source-set pinned", "takeaway": summary, "basis": "Typed artifact and pinned source lineage", "evidence_refs": source_ids, "input_fingerprint": input_fingerprint},
        }
        payload = self.bundle.validate_payload(payload, node["module_id"])
        markdown = self.bundle.render_markdown(payload)
        artifact = {
            "id": self.store._id("art"),
            "case_id": run["case_id"],
            "run_id": run["id"],
            "module_id": node["module_id"],
            "created_by": actor,
            "payload": copy.deepcopy(payload),
            "markdown": markdown,
            "digest": digest(payload),
            "input_fingerprint": input_fingerprint,
            "created_at": run["created_at"],
        }
        return artifact

    def approve_research_plan(self, run_id: str, actor: str, plan_hash: str) -> dict[str, Any]:
        with self.store.lock:
            run = self.store.runs.get(run_id)
            if not run:
                raise WorkflowError("RUN_NOT_FOUND")
            research = run.get("research")
            if not research or research.get("phase") != "awaiting_approval" or (run.get("error") or {}).get("code") != "PLAN_APPROVAL_REQUIRED":
                raise WorkflowError("PLAN_APPROVAL_NOT_AVAILABLE")
            pending_hash = research.get("proposed_plan_hash")
            if pending_hash != f"sha256:{digest(research.get('proposed_plan'))}" or plan_hash != pending_hash:
                raise WorkflowError("PLAN_HASH_MISMATCH")
            current = self.store.source_sets.get(run["case_id"])
            pinned = research["proposed_plan"]["source_set"]
            if not current or (current["id"], current["version"]) != (pinned["id"], pinned["version"]):
                raise WorkflowError("SOURCE_SET_CHANGED")
            prior_run = copy.deepcopy(run)
            audit_start = len(self.store.audit)
            research.update(approved_plan_hash=plan_hash, approved_by=actor, approved_at=now_iso(), phase="approved")
            run.update(status="queued", error=None)
            self.store.audit_event("research.plan_approved", actor, case_id=run["case_id"], run_id=run_id, plan_hash=plan_hash)
            try:
                self.store.persist()
            except Exception:
                self.store.runs[run_id] = prior_run
                del self.store.audit[audit_start:]
                raise
        self.store.emit(run_id, "research.plan_approved", {"plan_hash": plan_hash, "approved_by": actor})
        if self.settings.environment != "production":
            future = self.executor.submit(self._execute, run_id, actor)
            with self._futures_lock:
                self._futures[run_id] = future
        return self.store.get_run(run_id) or copy.deepcopy(run)

    def accept_run(self, case_id: str, run_id: str, actor: str) -> dict[str, Any]:
        with self.store.lock:
            run = self.store.runs.get(run_id)
            if not run or run["case_id"] != case_id:
                raise WorkflowError("RUN_NOT_FOUND")
            if run.get("accepted_snapshot_id"):
                return copy.deepcopy(self.store.snapshots[run["accepted_snapshot_id"]])
            if run["status"] != "succeeded":
                raise WorkflowError("RUN_NOT_READY")
            full_run = self.store.get_run(run_id)
            assert full_run is not None
            try:
                payload = build_snapshot_payload(self.store, full_run)
            except ValueError as exc:
                raise WorkflowError(str(exc)) from exc
            snapshot = {
                "id": self.store._id("snap"),
                **payload,
                "digest": digest(payload),
            }
            previous_id = self.store.cases[case_id].get("accepted_snapshot_id")
            snapshot["previous_snapshot_id"] = previous_id
            self.store.snapshots[snapshot["id"]] = copy.deepcopy(snapshot)
            self.store.cases[case_id]["accepted_snapshot_id"] = snapshot["id"]
            if not self.store.cases[case_id].get("visible_snapshot_id"):
                self.store.cases[case_id]["visible_snapshot_id"] = snapshot["id"]
            run["accepted_snapshot_id"] = snapshot["id"]
            self.store.audit_event("snapshot.accepted", actor, case_id=case_id, run_id=run_id, snapshot_id=snapshot["id"])
            self.store.persist()
        self.store.emit(run_id, "snapshot.accepted", {"snapshot_id": snapshot["id"], "digest": snapshot["digest"]})
        return copy.deepcopy(snapshot)

    def stream_events(self, run_id: str, cursor: int = 0) -> Iterator[str]:
        while True:
            events = self.store.wait_for_events(run_id, cursor, timeout=1.0)
            if not events:
                run = self.store.get_run(run_id)
                if run and run["status"] in {"paused", "succeeded", "failed"}:
                    return
                yield ": keepalive\n\n"
                continue
            for event in events:
                cursor = event["id"]
                yield f"id: {event['id']}\nevent: {event['event']}\ndata: {json.dumps(event['data'], sort_keys=True)}\n\n"
            run = self.store.get_run(run_id)
            if run and run["status"] in {"paused", "succeeded", "failed"}:
                return
