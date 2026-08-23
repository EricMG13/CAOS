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
from ..methodology.bundle import DeployVBundle, MethodologyError
from ..methodology.cpdr import CPDRValidationError, confidence_inputs, render_cpdr_markdown, validate_cpdr_payload
from ..methodology.prompt import compile_cpdr_prompts
from ..sources.domain import Vault, current_source_set
from ..store import JobFencedError, MemoryStore, now_iso
from .provider import AgentError, AnthropicGateway, ProviderUnavailable


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
        # ponytail: process-local cap; add a durable global reservation before running more than one worker process.
        self._cpdr_provider_slots = threading.BoundedSemaphore(2)
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

        def lease_check() -> None:
            if lease_fence.lost.is_set() or not self.store.job_is_current(run_id, attempt_token):
                raise JobFencedError("lost workflow lease")

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
                    futures = {pool.submit(self._build_artifact_with_slot, run, node, actor, fenced_call, lease_check): node for node in ready}
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
                        except AgentError as exc:
                            if lease_fence.lost.is_set():
                                return
                            research = copy.deepcopy((self.store.get_run(run_id) or {}).get("research") or {})
                            research["phase"] = "failed"
                            error = {"code": exc.code, "module_id": node["module_id"], "message": "CP-DR agent execution failed."}
                            try:
                                fenced_call(self.store.update_node_fenced, node["id"], status="failed", error=error)
                                fenced_call(self.store.update_run_fenced, status="failed", error=error, research=research)
                                fenced_call(self.store.emit_fenced, "node.failed", {"node_id": node["id"], "module_id": node["module_id"], "code": exc.code})
                                fenced_call(self.store.emit_fenced, "run.failed", {"code": exc.code, "module_id": node["module_id"]})
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
                        if node["module_id"] == "CP-DR":
                            research = copy.deepcopy((self.store.get_run(run_id) or {}).get("research") or {})
                            research["phase"] = "complete"
                            fenced_call(self.store.update_run_fenced, research=research)
                        fenced_call(self.store.update_node_fenced, node["id"], status="succeeded", artifact_id=artifact["id"], error=None)
                        fenced_call(self.store.emit_fenced, "node.succeeded", {"node_id": node["id"], "module_id": node["module_id"], "artifact_id": artifact["id"]})
        except JobFencedError:
            return
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join()
            if not lease_fence.lost.is_set():
                self.store.finish_job(run_id, attempt_token)

    def _build_artifact_with_slot(self, run: dict[str, Any], node: dict[str, Any], actor: str, fenced_call: Any | None = None, lease_check: Any | None = None) -> dict[str, Any]:
        with self._node_slots:
            return self._build_artifact(run, node, actor, fenced_call, lease_check)

    def _build_artifact(self, run: dict[str, Any], node: dict[str, Any], actor: str, fenced_call: Any | None = None, lease_check: Any | None = None) -> dict[str, Any]:
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
                if fenced_call is None or lease_check is None:
                    raise JobFencedError("missing fenced CP-DR execution context")
                return self._execute_cpdr(run, node, actor, source_set, source_ids, upstream_artifacts, input_fingerprint, research, fenced_call, lease_check)
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

    def _execute_cpdr(
        self,
        run: dict[str, Any],
        node: dict[str, Any],
        actor: str,
        source_set: dict[str, Any],
        source_ids: list[str],
        upstream_artifacts: list[dict[str, Any]],
        input_fingerprint: str,
        research: dict[str, Any],
        fenced_call: Any,
        lease_check: Any,
    ) -> dict[str, Any]:
        def persist_research() -> None:
            lease_check()
            fenced_call(self.store.update_run_fenced, research=copy.deepcopy(research))

        def fail(code: str, message: str) -> None:
            raise AgentError(code, message)

        try:
            self.bundle.verify()
        except MethodologyError as exc:
            raise AgentError("AGENT_AUTHORITY_MISMATCH", "Deploy V integrity failure") from exc
        if not self.settings.cpdr_agent_enabled:
            fail("AGENT_PROVIDER_UNAVAILABLE", "CP-DR agent is disabled")
        if run["case_id"] not in self.settings.cpdr_pilot_case_ids and run["created_by"] not in self.settings.cpdr_pilot_subjects:
            fail("AGENT_PROVIDER_UNAVAILABLE", "CP-DR run is outside the pilot allowlist")
        if not self.settings.anthropic_api_key:
            fail("AGENT_PROVIDER_UNAVAILABLE", "ANTHROPIC_API_KEY is not configured")
        if research.get("inflight_request_digest"):
            fail("AGENT_BUDGET_EXCEEDED", "unresolved provider request from a prior lease")
        approved_plan = research.get("proposed_plan")
        approved_hash = research.get("approved_plan_hash")
        if not isinstance(approved_plan, dict) or approved_hash != f"sha256:{digest(approved_plan)}" or approved_hash != research.get("proposed_plan_hash"):
            fail("AGENT_AUTHORITY_MISMATCH", "approved plan hash mismatch")
        expected_upstream = [
            {"module_id": item["module_id"], "artifact_id": item["artifact_id"], "digest": item["digest"]}
            for item in upstream_artifacts
        ]
        expected_scope = {
            "type": research["brief"].get("scope_type"),
            "key": research["brief"].get("scope_key"),
            "source_mode": research["brief"].get("source_mode"),
        }
        if (
            approved_plan.get("methodology_build_id") != self.bundle.build_id
            or approved_plan.get("brief_digest") != digest(research["brief"])
            or approved_plan.get("scope") != expected_scope
            or approved_plan.get("upstream_artifacts") != expected_upstream
        ):
            fail("AGENT_AUTHORITY_MISMATCH", "approved plan authority changed")
        if research.get("model") != self.settings.anthropic_model:
            fail("AGENT_AUTHORITY_MISMATCH", "model identity mismatch")
        current = current_source_set(self.store, run["case_id"])
        planned_source = approved_plan.get("source_set")
        if not current or not isinstance(planned_source, dict) or (current.get("id"), current.get("version")) != (source_set.get("id"), source_set.get("version")) or (source_set.get("id"), source_set.get("version")) != (planned_source.get("id"), planned_source.get("version")):
            fail("AGENT_AUTHORITY_MISMATCH", "source-set identity mismatch")
        cp0 = next((item for item in upstream_artifacts if item["module_id"] == "CP-0"), None)
        cp0_artifact = self.store.get_artifact(cp0["artifact_id"]) if cp0 else None
        cp0_payload = (cp0_artifact or {}).get("payload") or {}
        cp0_lineage = cp0_payload.get("lineage") or {}
        if not cp0_artifact or cp0_payload.get("status") != "COMPLETE" or cp0_lineage.get("run_id") != run["id"] or cp0_lineage.get("source_set_id") != source_set["id"]:
            fail("AGENT_AUTHORITY_MISMATCH", "accepted CP-0 lineage is missing or mismatched")

        limits = research["budget_limits"]
        used = research["budget_used"]
        returned_evidence: dict[tuple[str, str], dict[str, str]] = {}
        authority_digest = ""
        prompt_digest = ""

        def check_budget() -> None:
            lease_check()
            if used.get("active_minutes", 0) >= limits["active_minutes"]:
                fail("AGENT_BUDGET_EXCEEDED", "active worker time exhausted")

        def add_active_time(elapsed: float) -> None:
            lease_check()
            used["active_minutes"] = used.get("active_minutes", 0) + elapsed / 60
            persist_research()
            if used["active_minutes"] > limits["active_minutes"]:
                fail("AGENT_BUDGET_EXCEEDED", "active worker time exhausted")

        base_attempt = {
            "run_id": run["id"],
            "node_id": node["id"],
            "attempt": node["attempt"] + 1,
            "model": research["model"],
            "approved_plan_hash": approved_hash,
            "authority_digest": authority_digest,
            "prompt_digest": prompt_digest,
            "source_set_digest": digest(source_set),
            "upstream_digest": digest([item["digest"] for item in upstream_artifacts]),
        }

        def record(kind: str, **details: Any) -> None:
            check_budget()
            if kind == "provider_retry":
                if used["provider_retries"] + 1 > limits["provider_retries"]:
                    fail("AGENT_BUDGET_EXCEEDED", "provider retry budget exhausted")
                used["provider_retries"] += 1
            if kind == "repair_reserve":
                if used["repairs"] + 1 > limits["repairs"]:
                    fail("AGENT_BUDGET_EXCEEDED", "repair budget exhausted")
                used["repairs"] += 1
            allowed: dict[str, Any] = {}
            for key, value in details.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    allowed[key] = value[:200] if isinstance(value, str) else value
                elif isinstance(value, list) and len(value) <= 50 and all(isinstance(item, str) and len(item) <= 160 for item in value):
                    allowed[key] = list(value)
            if len(research["attempts"]) >= 50:
                fail("AGENT_BUDGET_EXCEEDED", "attempt metadata budget exhausted")
            research["attempts"].append({**base_attempt, "kind": kind[:40], **allowed})
            persist_research()

        def reserve(request_digest: str, input_tokens: int, output_tokens: int, retry: bool) -> None:
            check_budget()
            inflight = research.get("inflight_request_digest")
            if inflight and (not retry or inflight != request_digest):
                fail("AGENT_BUDGET_EXCEEDED", "unresolved or changed in-flight request")
            for key, amount in (("turns", 1), ("input_tokens", input_tokens), ("output_tokens", output_tokens)):
                if used[key] + amount > limits[key]:
                    fail("AGENT_BUDGET_EXCEEDED", f"{key} budget exhausted")
            used["turns"] += 1
            used["input_tokens"] += input_tokens
            used["output_tokens"] += output_tokens
            research["inflight_request_digest"] = request_digest
            persist_research()

        def reconcile(request_digest: str, reserved_input: int, reserved_output: int, actual_input: int, actual_output: int) -> None:
            lease_check()
            if research.get("inflight_request_digest") != request_digest:
                fail("AGENT_AUTHORITY_MISMATCH", "in-flight request digest mismatch")
            used["input_tokens"] += actual_input - reserved_input
            used["output_tokens"] += actual_output - reserved_output
            research["inflight_request_digest"] = None
            persist_research()
            if used["input_tokens"] > limits["input_tokens"] or used["output_tokens"] > limits["output_tokens"]:
                fail("AGENT_BUDGET_EXCEEDED", "actual token usage exceeded the run budget")

        source_manifest: list[dict[str, Any]] = []
        with self.store.lock:
            for source_id in source_ids:
                source = self.store.sources.get(source_id)
                if not source or source.get("case_id") != run["case_id"] or source.get("withdrawn"):
                    fail("AGENT_AUTHORITY_MISMATCH", "pinned source is unavailable")
                blocks = source.get("blocks") or []
                source_digest = source.get("sha256") or digest({"source_id": source_id, "blocks": blocks})
                source_manifest.append(
                    {
                        "source_id": source_id,
                        "digest": source_digest,
                        "filename": source.get("filename", source_id),
                        "media_type": source.get("media_type", "application/octet-stream"),
                        "blocks": [
                            {
                                "block_id": block.get("block_id"),
                                "locator": block.get("locator"),
                                "extractor_version": block.get("extractor_version"),
                                "confidence": block.get("confidence"),
                            }
                            for block in blocks
                        ],
                    }
                )

        def read_evidence(source_id: str, block_ids: list[str]) -> list[dict[str, Any]]:
            check_budget()
            if not block_ids or len(block_ids) > 50 or len(block_ids) != len(set(block_ids)):
                fail("AGENT_OUTPUT_INVALID", "evidence block IDs must be unique and bounded")
            if used["evidence_reads"] + 1 > limits["evidence_reads"]:
                fail("AGENT_BUDGET_EXCEEDED", "evidence read budget exhausted")
            with self.store.lock:
                pinned = self.store.source_set_by_id(source_set["id"])
                source = self.store.sources.get(source_id)
                if not pinned or source_id not in pinned["source_ids"]:
                    fail("AGENT_AUTHORITY_MISMATCH", "source is not pinned to this run")
                if not source or source.get("case_id") != run["case_id"]:
                    fail("AGENT_AUTHORITY_MISMATCH", "cross-case evidence read")
                if source.get("withdrawn"):
                    fail("AGENT_AUTHORITY_MISMATCH", "withdrawn evidence source")
                source_blocks = source.get("blocks") or []
                by_id = {block.get("block_id"): block for block in source_blocks}
                if len(by_id) != len(source_blocks) or any(block_id not in by_id for block_id in block_ids):
                    fail("AGENT_OUTPUT_INVALID", "evidence block is absent")
                source_digest = source.get("sha256") or digest({"source_id": source_id, "blocks": source_blocks})
                result = [
                    {
                        "source_id": source_id,
                        "source_digest": source_digest,
                        "block_id": block_id,
                        "locator": by_id[block_id].get("locator"),
                        "extractor_version": by_id[block_id].get("extractor_version"),
                        "confidence": by_id[block_id].get("confidence"),
                        "text": by_id[block_id].get("text", ""),
                    }
                    for block_id in block_ids
                ]
            returned_bytes = len(json.dumps(result, sort_keys=True).encode("utf-8"))
            if used["evidence_bytes"] + returned_bytes > limits["evidence_bytes"]:
                fail("AGENT_BUDGET_EXCEEDED", "evidence byte budget exhausted")
            used["evidence_reads"] += 1
            used["evidence_bytes"] += returned_bytes
            returned_evidence.update(
                {
                    (source_id, item["block_id"]): {
                        "source_digest": source_digest,
                        "locator": json.dumps(item["locator"], sort_keys=True, separators=(",", ":")),
                        "extractor_version": str(item["extractor_version"]),
                        "confidence": str(item["confidence"]),
                    }
                    for item in result
                }
            )
            persist_research()
            record("evidence", tool_name="read_evidence", source_id=source_id, block_ids=block_ids)
            return result

        host_identity = {
            "module_id": "CP-DR",
            "run_id": run["id"],
            "case_id": run["case_id"],
            "profile_id": run["plan"]["profile_id"],
            "selection_id": run["plan"]["selection_id"],
            "source_set_id": source_set["id"],
            "source_set_version": source_set["version"],
            "approved_plan_hash": approved_hash,
            "upstream_digests": [item["digest"] for item in upstream_artifacts],
            "scope_type": research["brief"]["scope_type"],
            "scope_key": research["brief"]["scope_key"],
            "subject_name": research["brief"]["subject_name"],
            "research_question": research["brief"]["research_question"],
            "reporting_period": research["brief"]["as_of_date"],
            "source_mode": "supplied_only",
        }
        system, user = compile_cpdr_prompts(host_identity, approved_plan, source_manifest, upstream_artifacts)
        authority_digest = digest(system)
        prompt_digest = digest(user)
        base_attempt["authority_digest"] = authority_digest
        base_attempt["prompt_digest"] = prompt_digest
        approved_workstreams = {item["id"] for item in approved_plan["workstreams"]}

        def validate(value: dict[str, Any]) -> Any:
            try:
                return validate_cpdr_payload(value, host_identity, approved_workstreams, returned_evidence)
            except CPDRValidationError as exc:
                if str(exc).startswith("host identity mismatch"):
                    raise AgentError("AGENT_AUTHORITY_MISMATCH", "provider identity mismatch") from exc
                raise

        research["phase"] = "researching"
        persist_research()
        try:
            gateway = AnthropicGateway(
                self.settings.anthropic_api_key,
                self.settings.anthropic_model,
                self.settings.anthropic_timeout_seconds,
            )
        except ProviderUnavailable:
            raise
        payload = gateway.run(
            system=system,
            user=user,
            read_evidence=read_evidence,
            validate=validate,
            lease_check=check_budget,
            reserve=reserve,
            reconcile=reconcile,
            record=record,
            active_time=add_active_time,
            semaphore=self._cpdr_provider_slots,
        )
        confidence = self.bundle.cpdr_confidence(confidence_inputs(payload))
        filename, markdown = render_cpdr_markdown(payload, confidence, run["created_at"][:10], upstream_artifacts)
        validation = self.bundle.validate_cpdr_handoff(markdown, filename, run["id"], research["brief"]["as_of_date"])
        if validation.identity_mismatches:
            fail("AGENT_AUTHORITY_MISMATCH", "canonical handoff identity mismatch")
        if validation.errors or validation.exit_code != 0:
            fail("AGENT_OUTPUT_INVALID", "canonical handoff validation failed")
        typed_payload = payload.model_dump(mode="json")
        record("handoff", output_digest=digest(typed_payload), filename=filename, confidence_score=confidence["confidence_score"])
        return {
            "id": self.store._id("art"),
            "case_id": run["case_id"],
            "run_id": run["id"],
            "module_id": "CP-DR",
            "created_by": actor,
            "payload": typed_payload,
            "markdown": markdown,
            "filename": filename,
            "digest": digest(typed_payload),
            "input_fingerprint": input_fingerprint,
            "created_at": run["created_at"],
        }

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
