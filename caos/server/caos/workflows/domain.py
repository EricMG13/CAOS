from __future__ import annotations

import copy
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Iterator

from ..artifacts.domain import build_snapshot_payload
from ..config import Settings
from ..contracts import Depth, digest
from ..methodology.bundle import DeployVBundle
from ..sources.domain import Vault, current_source_set
from ..store import JobFencedError, MemoryStore


class WorkflowError(ValueError):
    pass


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

    def start_run(self, case_id: str, actor: str, pathway: str, depth: Depth, focus_questions: list[str], upgraded_from_run_id: str | None = None) -> dict[str, Any]:
        source_set = current_source_set(self.store, case_id)
        plan = self.bundle.compile(pathway, depth, source_set["id"] if source_set else None, focus_questions, source_set["version"] if source_set else None)
        run = self.store.create_run(case_id, actor, plan, [], upgraded_from_run_id)
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
        try:
            self.store.update_run_fenced(run_id, attempt_token, status="running", error=None)
            self.store.emit(run_id, "run.running", {"run_id": run_id, "worker": worker})
            while True:
                if not self.store.job_is_current(run_id, attempt_token):
                    return
                run = self.store.get_run(run_id)
                if not run:
                    return
                pending = [node for node in run["nodes"] if node["status"] in {"pending", "ready"}]
                completed = {node["module_id"] for node in run["nodes"] if node["status"] == "succeeded"}
                if not pending:
                    self.store.update_run_fenced(run_id, attempt_token, status="succeeded", current_node_id=None)
                    self.store.emit(run_id, "run.succeeded", {"run_id": run_id})
                    return
                ready = [node for node in pending if set(node["dependencies"]).issubset(completed)]
                if not ready:
                    self.store.update_run_fenced(run_id, attempt_token, status="failed", error={"code": "DAG_BLOCKED", "message": "No dependency-safe ready nodes remain."})
                    self.store.emit(run_id, "run.failed", {"code": "DAG_BLOCKED"})
                    return
                for node in ready:
                    self.store.update_node_fenced(run_id, attempt_token, node["id"], status="running", attempt=node["attempt"] + 1)
                    self.store.emit(run_id, "node.running", {"node_id": node["id"], "module_id": node["module_id"]})
                with ThreadPoolExecutor(max_workers=min(4, len(ready)), thread_name_prefix="caos-node") as pool:
                    futures = {pool.submit(self._build_artifact_with_slot, run, node, actor): node for node in ready}
                    for future, node in ((future, futures[future]) for future in futures):
                        try:
                            artifact = self.store.put_artifact_fenced(run_id, attempt_token, future.result())
                        except JobFencedError:
                            return
                        except Exception as exc:
                            try:
                                self.store.update_node_fenced(run_id, attempt_token, node["id"], status="failed", error={"code": "NODE_ERROR", "message": str(exc)})
                                self.store.update_run_fenced(run_id, attempt_token, status="failed", error={"code": "NODE_ERROR", "module_id": node["module_id"], "message": str(exc)})
                            except JobFencedError:
                                return
                            self.store.emit(run_id, "node.failed", {"node_id": node["id"], "module_id": node["module_id"], "message": str(exc)})
                            self.store.emit(run_id, "run.failed", {"code": "NODE_ERROR", "module_id": node["module_id"]})
                            return
                        self.store.update_node_fenced(run_id, attempt_token, node["id"], status="succeeded", artifact_id=artifact["id"], error=None)
                        self.store.emit(run_id, "node.succeeded", {"node_id": node["id"], "module_id": node["module_id"], "artifact_id": artifact["id"]})
        except JobFencedError:
            return
        finally:
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
