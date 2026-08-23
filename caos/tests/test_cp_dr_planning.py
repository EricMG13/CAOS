from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

import pytest
from caos.config import Settings
from caos.contracts import ApproveResearchPlanRequest, ResearchBrief, StartRunRequest, digest
from caos.http import create_app
from caos.methodology.bundle import DeployVBundle
from caos.store import MemoryStore, PostgresStore
from caos.workflows.domain import WorkflowError, WorkflowRuntime
from fastapi.testclient import TestClient
from pydantic import ValidationError


DEPLOY_V = Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v"
BRIEF = {
    "research_question": "Can Northstar refinance its 2028 maturities?",
    "decision_context": "Underwrite a first-lien position.",
    "as_of_date": "2026-08-23",
    "time_horizon": "Through 2029",
    "must_answer": ["What is the liquidity runway?", "Which downside breaks refinancing?"],
    "exclusions": ["Do not opine on equity valuation."],
}


def _runtime(store: MemoryStore, *, environment: str = "production") -> WorkflowRuntime:
    return WorkflowRuntime(store, DeployVBundle(DEPLOY_V), Settings(environment=environment, storage_dir=Path("/tmp/caos-cp-dr-planning"), deploy_v_root=DEPLOY_V))


def _start_research(runtime: WorkflowRuntime) -> tuple[dict[str, Any], dict[str, Any]]:
    store = runtime.store
    case = store.create_case("Deep research", "Northstar", "Services", "analyst")
    source_id = store._id("src")
    store.sources[source_id] = {"id": source_id, "case_id": case["id"], "withdrawn": False}
    source_set = {"id": store._id("set"), "case_id": case["id"], "version": 1, "source_ids": [source_id], "created_by": "analyst", "created_at": "2026-08-23T00:00:00+00:00"}
    store.register_source_set(source_set)
    run = runtime.start_run(case["id"], "analyst", "DEEP_RESEARCH", "full", [], ResearchBrief.model_validate(BRIEF).model_dump(mode="json"))
    return run, source_set


def _pause_research(runtime: WorkflowRuntime) -> tuple[dict[str, Any], dict[str, Any]]:
    run, source_set = _start_research(runtime)
    runtime._execute(run["id"], "analyst")
    paused = runtime.store.get_run(run["id"])
    assert paused is not None
    return paused, source_set


@pytest.mark.parametrize(
    "change",
    [
        {"research_question": ""},
        {"research_question": "   "},
        {"research_question": "x" * 401},
        {"decision_context": "\t"},
        {"time_horizon": "\n"},
        {"must_answer": [""]},
        {"must_answer": [" "]},
        {"must_answer": ["x" * 201]},
        {"exclusions": [""]},
        {"exclusions": ["\t"]},
        {"exclusions": ["x" * 201]},
        {"must_answer": [str(index) for index in range(6)], "exclusions": [str(index) for index in range(5)]},
    ],
)
def test_research_brief_rejects_invalid_bounds(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ResearchBrief.model_validate({**BRIEF, **change})


@pytest.mark.parametrize(
    "payload",
    [
        {"pathway": "DEEP_RESEARCH", "depth": "screen", "research_brief": BRIEF},
        {"pathway": "DEEP_RESEARCH", "depth": "full"},
        {"pathway": "FULL_CREDIT", "depth": "full", "research_brief": BRIEF},
    ],
)
def test_start_run_enforces_deep_research_brief_and_full_depth(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        StartRunRequest.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "scope_type",
        "scope_key",
        "subject_name",
        "source_mode",
        "research_budget",
        "plan_approval",
        "model",
        "tools",
        "proposed_plan_hash",
        "approved_plan_hash",
        "approved_by",
        "approved_at",
    ],
)
def test_research_brief_rejects_caller_owned_authority_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        StartRunRequest.model_validate({"pathway": "DEEP_RESEARCH", "depth": "full", "research_brief": {**BRIEF, field: "forged"}})


@pytest.mark.parametrize("plan_hash", ["", "sha256:ABC", "sha256:" + "0" * 63, "md5:" + "0" * 64])
def test_plan_approval_request_requires_exact_canonical_hash(plan_hash: str) -> None:
    with pytest.raises(ValidationError):
        ApproveResearchPlanRequest(plan_hash=plan_hash)

    valid = "sha256:" + "0" * 64
    assert ApproveResearchPlanRequest(plan_hash=valid).plan_hash == valid


def test_research_plan_is_deterministic_complete_and_identity_bound() -> None:
    bundle = DeployVBundle(DEPLOY_V)
    brief = {
        **BRIEF,
        "as_of_date": "2026-08-23",
        "scope_type": "issuer",
        "scope_key": "case-123",
        "subject_name": "Northstar",
        "source_mode": "supplied_only",
        "research_budget": "standard",
        "plan_approval": "required",
    }
    upstream = [{"module_id": "CP-0", "artifact_id": "art_cp0", "digest": "cp0-digest"}]

    plan, plan_hash = bundle.plan_research(brief, "set_1", 7, upstream)

    assert bundle.plan_research(brief, "set_1", 7, upstream) == (plan, plan_hash)
    assert plan_hash == f"sha256:{digest(plan)}"
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", plan_hash)
    assert plan["methodology_build_id"] == bundle.build_id
    assert plan["source_set"] == {"id": "set_1", "version": 7}
    assert plan["upstream_artifacts"] == upstream
    workstreams = plan["workstreams"]
    assert 3 <= len(workstreams) <= 5
    required = {"id", "question", "perspective", "hypothesis", "evidence_needs", "source_classes", "disconfirming_test", "completion_test", "effort_cap"}
    assert all(required <= row.keys() for row in workstreams)
    assigned = [question for row in workstreams for question in row.get("assigned_questions", [])]
    assert assigned == brief["must_answer"]
    assert sum(row["kind"] == "synthesis" for row in workstreams) == 1
    assert sum(row["kind"] == "adversarial" for row in workstreams) == 1
    assert all(row["source_classes"] == ["supplied_case_sources"] for row in workstreams)

    changed = copy.deepcopy(upstream)
    changed[0]["digest"] = "changed"
    assert bundle.plan_research(brief, "set_1", 7, changed)[1] != plan_hash
    changed_brief = {**brief, "decision_context": "Monitor an existing first-lien position."}
    assert bundle.plan_research(changed_brief, "set_1", 7, upstream)[1] != plan_hash


def test_research_plan_uses_main_question_when_must_answer_is_empty() -> None:
    bundle = DeployVBundle(DEPLOY_V)
    brief = {**BRIEF, "must_answer": []}

    plan, _ = bundle.plan_research(brief, "set_1", 1, [{"module_id": "CP-0", "artifact_id": "art", "digest": "digest"}])

    topical = [row for row in plan["workstreams"] if row["kind"] == "topical"]
    assert topical[0]["assigned_questions"] == [brief["research_question"]]


def test_runtime_durably_pauses_after_cp0_with_server_owned_brief_and_plan() -> None:
    class OrderingStore(MemoryStore):
        pause_persisted = False

        def persist(self) -> None:
            self.pause_persisted = any(run.get("research", {}).get("phase") == "awaiting_approval" and run["status"] == "paused" for run in self.runs.values())

        def emit_fenced(self, run_id: str, attempt_token: str, event: str, data: dict[str, Any]) -> None:
            if event in {"research.plan_ready", "run.paused"}:
                assert self.pause_persisted
            super().emit_fenced(run_id, attempt_token, event, data)

    store = OrderingStore()
    runtime = _runtime(store)
    try:
        paused, source_set = _pause_research(runtime)
    finally:
        runtime.close()

    assert paused["status"] == "paused"
    assert paused["error"] == {"code": "PLAN_APPROVAL_REQUIRED", "message": "Approve the proposed research plan before execution."}
    research = paused["research"]
    assert research["phase"] == "awaiting_approval"
    assert research["brief"] == {
        **ResearchBrief.model_validate(BRIEF).model_dump(mode="json"),
        "scope_type": "issuer",
        "scope_key": paused["case_id"].replace("_", "-"),
        "subject_name": "Northstar",
        "source_mode": "supplied_only",
        "research_budget": "standard",
        "plan_approval": "required",
    }
    assert research["model"] == "claude-sonnet-4-6"
    assert research["budget_limits"] == {"turns": 8, "evidence_reads": 12, "evidence_bytes": 1024 * 1024, "input_tokens": 100_000, "output_tokens": 8_000, "active_minutes": 3, "provider_retries": 1, "repairs": 1}
    assert {key: value for key, value in research["budget_used"].items() if key != "active_minutes"} == {
        key: 0 for key in research["budget_limits"] if key != "active_minutes"
    }
    assert 0 <= research["budget_used"]["active_minutes"] < research["budget_limits"]["active_minutes"]
    assert research["inflight_request_digest"] is None
    assert research["attempts"] == []
    assert research["proposed_plan_hash"] == f"sha256:{digest(research['proposed_plan'])}"
    assert research["proposed_plan"]["source_set"] == {"id": source_set["id"], "version": source_set["version"]}
    cp0 = next(node for node in paused["nodes"] if node["module_id"] == "CP-0")
    cp_dr = next(node for node in paused["nodes"] if node["module_id"] == "CP-DR")
    assert cp0["status"] == "succeeded" and cp0["artifact_id"]
    assert cp_dr["status"] == "pending" and cp_dr["artifact_id"] is None
    assert research["proposed_plan"]["upstream_artifacts"] == [{"module_id": "CP-0", "artifact_id": cp0["artifact_id"], "digest": store.artifacts[cp0["artifact_id"]]["digest"]}]
    events = [event["event"] for event in paused["events"]]
    assert events[-2:] == ["research.plan_ready", "run.paused"]
    assert "node.failed" not in events


def test_memory_planning_pause_rolls_back_if_persistence_fails() -> None:
    class FailingStore(MemoryStore):
        fail = False

        def persist(self) -> None:
            if self.fail:
                raise RuntimeError("database unavailable")

    store = FailingStore()
    case = store.create_case("Pause rollback", "Issuer", "Testing", "analyst")
    run = store.create_run(case["id"], "analyst", {"nodes": []}, [])
    node = store.add_node(run["id"], case["id"], "CP-DR", [], 1)
    store.update_run(run["id"], node_ids=[node["id"]], status="running", research={"phase": "planning"})
    store.update_node(node["id"], status="running")
    token = store.claim_job(run["id"], "worker")
    assert token
    before = copy.deepcopy((store.runs[run["id"]], store.nodes[node["id"]], store.events[run["id"]]))
    store.fail = True

    with pytest.raises(RuntimeError, match="database unavailable"):
        store.pause_research_plan_fenced(run["id"], token, node["id"], {"phase": "awaiting_approval"})

    assert (store.runs[run["id"]], store.nodes[node["id"]], store.events[run["id"]]) == before


def test_runtime_emits_no_plan_events_when_pause_persistence_fails() -> None:
    class FailingPauseStore(MemoryStore):
        def pause_research_plan_fenced(self, run_id: str, attempt_token: str, node_id: str, research: dict[str, Any]) -> None:
            raise RuntimeError("database unavailable")

    store = FailingPauseStore()
    runtime = _runtime(store)
    try:
        run, _ = _start_research(runtime)
        with pytest.raises(RuntimeError, match="database unavailable"):
            runtime._execute(run["id"], "analyst")
        assert not {"research.plan_ready", "run.paused"} & {event["event"] for event in store.events[run["id"]]}
    finally:
        runtime.close()


def test_exact_plan_approval_preserves_identity_and_phase4_fails_closed() -> None:
    store = MemoryStore()
    runtime = WorkflowRuntime(
        store,
        DeployVBundle(DEPLOY_V),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-cp-dr-planning"),
            deploy_v_root=DEPLOY_V,
            anthropic_api_key="test-only-key",
            cpdr_agent_enabled=True,
            cpdr_pilot_subjects=("analyst",),
        ),
    )
    try:
        paused, _ = _pause_research(runtime)
        store.runs[paused["id"]]["research"]["budget_used"]["turns"] = 2
        store.runs[paused["id"]]["research"]["inflight_request_digest"] = "sha256:reserved"
        store.runs[paused["id"]]["research"]["attempts"].append({"attempt": 1, "status": "reserved"})
        paused = store.get_run(paused["id"])
        assert paused is not None
        identity = copy.deepcopy({
            "id": paused["id"],
            "brief": paused["research"]["brief"],
            "plan": paused["research"]["proposed_plan"],
            "source_set": paused["research"]["proposed_plan"]["source_set"],
            "budget_limits": paused["research"]["budget_limits"],
            "budget_used": paused["research"]["budget_used"],
            "inflight_request_digest": paused["research"]["inflight_request_digest"],
            "attempts": paused["research"]["attempts"],
            "upstream_artifacts": paused["research"]["proposed_plan"]["upstream_artifacts"],
        })

        approved = runtime.approve_research_plan(paused["id"], "approver", paused["research"]["proposed_plan_hash"])

        assert approved["id"] == identity["id"]
        assert approved["status"] == "queued" and approved["error"] is None
        assert approved["research"]["phase"] == "approved"
        assert approved["research"]["approved_plan_hash"] == paused["research"]["proposed_plan_hash"]
        assert approved["research"]["approved_by"] == "approver"
        assert approved["research"]["approved_at"]
        assert approved["research"]["brief"] == identity["brief"]
        assert approved["research"]["proposed_plan"] == identity["plan"]
        assert approved["research"]["proposed_plan"]["source_set"] == identity["source_set"]
        assert approved["research"]["budget_limits"] == identity["budget_limits"]
        assert approved["research"]["budget_used"] == identity["budget_used"]
        assert approved["research"]["inflight_request_digest"] == identity["inflight_request_digest"]
        assert approved["research"]["attempts"] == identity["attempts"]
        assert approved["research"]["proposed_plan"]["upstream_artifacts"] == identity["upstream_artifacts"]
        assert store.audit[-1]["action"] == "research.plan_approved"
        assert store.events[paused["id"]][-1]["event"] == "research.plan_approved"

        runtime._execute(paused["id"], "approver")
        failed = store.get_run(paused["id"])
        assert failed is not None
        assert failed["status"] == "failed"
        assert failed["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
        assert not any(artifact["module_id"] == "CP-DR" for artifact in store.artifacts.values())
    finally:
        runtime.close()


def test_plan_approval_rejects_wrong_double_wrong_phase_and_changed_source_set() -> None:
    store = MemoryStore()
    runtime = _runtime(store)
    try:
        paused, source_set = _pause_research(runtime)
        with pytest.raises(WorkflowError, match="PLAN_HASH_MISMATCH"):
            runtime.approve_research_plan(paused["id"], "approver", "sha256:" + "0" * 64)
        store.register_source_set({**source_set, "id": store._id("set"), "version": 2})
        with pytest.raises(WorkflowError, match="SOURCE_SET_CHANGED"):
            runtime.approve_research_plan(paused["id"], "approver", paused["research"]["proposed_plan_hash"])
        store.source_sets[paused["case_id"]] = copy.deepcopy(source_set)
        runtime.approve_research_plan(paused["id"], "approver", paused["research"]["proposed_plan_hash"])
        with pytest.raises(WorkflowError, match="PLAN_APPROVAL_NOT_AVAILABLE"):
            runtime.approve_research_plan(paused["id"], "approver", paused["research"]["proposed_plan_hash"])

        ordinary, _ = _start_research(runtime)
        store.runs[ordinary["id"]]["research"]["phase"] = "planning"
        with pytest.raises(WorkflowError, match="PLAN_APPROVAL_NOT_AVAILABLE"):
            runtime.approve_research_plan(ordinary["id"], "approver", "sha256:" + "0" * 64)
    finally:
        runtime.close()


def test_plan_approval_rejects_a_post_hash_plan_change_and_missing_pause() -> None:
    store = MemoryStore()
    runtime = _runtime(store)
    try:
        paused, _ = _pause_research(runtime)
        plan_hash = paused["research"]["proposed_plan_hash"]
        store.runs[paused["id"]]["research"]["proposed_plan"]["scope"]["key"] = "changed-after-hash"
        with pytest.raises(WorkflowError, match="PLAN_HASH_MISMATCH"):
            runtime.approve_research_plan(paused["id"], "approver", plan_hash)

        store.runs[paused["id"]]["error"] = None
        with pytest.raises(WorkflowError, match="PLAN_APPROVAL_NOT_AVAILABLE"):
            runtime.approve_research_plan(paused["id"], "approver", plan_hash)
    finally:
        runtime.close()


def test_plan_approval_rolls_back_run_audit_and_event_on_persistence_failure() -> None:
    class FailingStore(MemoryStore):
        fail = False

        def persist(self) -> None:
            if self.fail:
                raise RuntimeError("database unavailable")

    store = FailingStore()
    runtime = _runtime(store)
    try:
        paused, _ = _pause_research(runtime)
        before = copy.deepcopy((store.runs[paused["id"]], store.audit, store.events[paused["id"]]))
        store.fail = True
        with pytest.raises(RuntimeError, match="database unavailable"):
            runtime.approve_research_plan(paused["id"], "approver", paused["research"]["proposed_plan_hash"])
        assert (store.runs[paused["id"]], store.audit, store.events[paused["id"]]) == before
    finally:
        runtime.close()


def test_development_approval_resubmits_the_same_run() -> None:
    store = MemoryStore()
    runtime = _runtime(store)
    try:
        paused, _ = _pause_research(runtime)
    finally:
        runtime.close()
    submissions: list[tuple[str, str]] = []

    class ResubmitRuntime(WorkflowRuntime):
        def _execute(self, run_id: str, actor: str) -> None:
            submissions.append((run_id, actor))

    runtime = ResubmitRuntime(store, DeployVBundle(DEPLOY_V), Settings(environment="development", storage_dir=Path("/tmp/caos-cp-dr-resubmit"), deploy_v_root=DEPLOY_V))
    try:
        runtime.approve_research_plan(paused["id"], "approver", paused["research"]["proposed_plan_hash"])
        runtime._futures[paused["id"]].result(timeout=1)
        assert submissions == [(paused["id"], "approver")]
    finally:
        runtime.close()


def test_research_planning_requires_upstream_artifact_identity() -> None:
    store = MemoryStore()
    runtime = _runtime(store)
    try:
        run, _ = _start_research(runtime)
        full = store.get_run(run["id"])
        assert full is not None
        cp_dr = next(node for node in full["nodes"] if node["module_id"] == "CP-DR")
        with pytest.raises(WorkflowError, match="UPSTREAM_ARTIFACT_MISSING"):
            runtime._build_artifact(full, cp_dr, "analyst")
    finally:
        runtime.close()


def test_postgres_research_pause_and_approval_survive_reload() -> None:
    database_url = os.getenv("CAOS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CAOS_TEST_DATABASE_URL is required for durable CP-DR planning proof")
    store = PostgresStore(database_url)
    runtime = _runtime(store)
    try:
        paused, _ = _pause_research(runtime)
        run_id = paused["id"]
        plan_hash = paused["research"]["proposed_plan_hash"]
    finally:
        runtime.close()

    reloaded = PostgresStore(database_url)
    durable_pause = reloaded.get_run(run_id)
    assert durable_pause is not None
    assert durable_pause["status"] == "paused" and durable_pause["research"]["phase"] == "awaiting_approval"
    durable_identity = copy.deepcopy({key: durable_pause["research"][key] for key in ("brief", "proposed_plan", "budget_limits", "budget_used", "inflight_request_digest", "attempts")})
    runtime = _runtime(reloaded)
    try:
        runtime.approve_research_plan(run_id, "approver", plan_hash)
    finally:
        runtime.close()

    durable_approval = PostgresStore(database_url).get_run(run_id)
    assert durable_approval is not None
    assert durable_approval["status"] == "queued"
    assert durable_approval["research"]["phase"] == "approved"
    assert durable_approval["research"]["approved_plan_hash"] == plan_hash
    assert {key: durable_approval["research"][key] for key in durable_identity} == durable_identity


def _production_client(
    tmp_path: Path,
    store: MemoryStore,
    *,
    cpdr_agent_enabled: bool = False,
    cpdr_pilot_case_ids: tuple[str, ...] = (),
    cpdr_pilot_subjects: tuple[str, ...] = (),
) -> TestClient:
    settings = Settings(
        environment="production",
        database_url="postgresql://unused/test",
        edge_proxy_secret="test-edge",
        session_secret="test-session",
        clamav_host="clamav",
        storage_dir=tmp_path / "vault",
        deploy_v_root=DEPLOY_V,
        cpdr_agent_enabled=cpdr_agent_enabled,
        cpdr_pilot_case_ids=cpdr_pilot_case_ids,
        cpdr_pilot_subjects=cpdr_pilot_subjects,
    )
    return TestClient(create_app(settings, store))


def _headers(subject: str, role: str) -> dict[str, str]:
    return {"x-edge-authorization": "test-edge", "x-forwarded-user": subject, "x-forwarded-groups": f"caos-{role.lower()}"}


def _case_with_source(store: MemoryStore, name: str, actor: str = "owner") -> dict[str, Any]:
    case = store.create_case(name, "Northstar", "Services", actor)
    source_id = store._id("src")
    store.sources[source_id] = {"id": source_id, "case_id": case["id"], "withdrawn": False}
    store.register_source_set({"id": store._id("set"), "case_id": case["id"], "version": 1, "source_ids": [source_id], "created_by": actor, "created_at": "2026-08-23T00:00:00+00:00"})
    return case


def _approval_run(store: MemoryStore, case_id: str, actor: str = "owner") -> tuple[str, str]:
    brief = ResearchBrief.model_validate(BRIEF).model_dump(mode="json")
    runtime = _runtime(store)
    try:
        run = runtime.start_run(case_id, actor, "DEEP_RESEARCH", "full", [], brief)
        runtime._execute(run["id"], actor)
    finally:
        runtime.close()
    paused = store.get_run(run["id"])
    assert paused is not None and paused["status"] == "paused"
    assert paused["error"]["code"] == "PLAN_APPROVAL_REQUIRED"
    research = paused["research"]
    assert research["phase"] == "awaiting_approval"
    expected_brief = {**brief, "scope_type": "issuer", "scope_key": case_id.replace("_", "-"), "subject_name": store.cases[case_id]["issuer"], "source_mode": "supplied_only", "research_budget": "standard", "plan_approval": "required"}
    expected_limits = {"turns": 8, "evidence_reads": 12, "evidence_bytes": 1024 * 1024, "input_tokens": 100_000, "output_tokens": 8_000, "active_minutes": 3, "provider_retries": 1, "repairs": 1}
    assert research["brief"] == expected_brief
    assert research["budget_limits"] == expected_limits
    assert {key: value for key, value in research["budget_used"].items() if key != "active_minutes"} == {
        key: 0 for key in research["budget_limits"] if key != "active_minutes"
    }
    assert 0 <= research["budget_used"]["active_minutes"] < research["budget_limits"]["active_minutes"]
    assert research["proposed_plan"] and re.fullmatch(r"sha256:[0-9a-f]{64}", research["proposed_plan_hash"])
    cp0 = next(node for node in paused["nodes"] if node["module_id"] == "CP-0")
    cp_dr = next(node for node in paused["nodes"] if node["module_id"] == "CP-DR")
    assert cp0["status"] == "succeeded" and cp0["artifact_id"]
    assert cp_dr["status"] == "pending" and cp_dr["artifact_id"] is None
    cp0_artifact = store.get_artifact(cp0["artifact_id"])
    assert cp0_artifact is not None
    assert research["proposed_plan"]["upstream_artifacts"] == [{"module_id": "CP-0", "artifact_id": cp0_artifact["id"], "digest": cp0_artifact["digest"]}]
    return run["id"], research["proposed_plan_hash"]


def test_research_plan_approval_route_validates_hash_and_maps_conflicts(tmp_path: Path) -> None:
    store = MemoryStore()
    case = _case_with_source(store, "Approval route")
    run_id, plan_hash = _approval_run(store, case["id"])

    with _production_client(tmp_path, store) as client:
        headers = _headers("owner", "ANALYST")
        malformed = client.post(f"/api/runs/{run_id}/research-plan/approve", headers=headers, json={"plan_hash": "not-a-hash"})
        assert malformed.status_code == 422
        wrong = client.post(f"/api/runs/{run_id}/research-plan/approve", headers=headers, json={"plan_hash": "sha256:" + "0" * 64})
        assert wrong.status_code == 409 and wrong.json()["detail"] == "PLAN_HASH_MISMATCH"
        approved = client.post(f"/api/runs/{run_id}/research-plan/approve", headers=headers, json={"plan_hash": plan_hash})
        assert approved.status_code == 200
        assert approved.json()["id"] == run_id and approved.json()["research"]["phase"] == "approved"


def test_research_plan_route_denies_cross_case_outsider_and_stored_reader(tmp_path: Path) -> None:
    store = MemoryStore()
    case = _case_with_source(store, "Target")
    other = store.create_case("Other", "Other", "Services", "cross-case")
    assert store.add_member(case["id"], "owner", "stored-reader", "READER", "ADMIN")
    assert other["id"]

    with _production_client(tmp_path, store) as client:
        run_id, plan_hash = _approval_run(store, case["id"])
        outsider = client.post(f"/api/runs/{run_id}/research-plan/approve", headers=_headers("cross-case", "ADMIN"), json={"plan_hash": plan_hash})
        assert outsider.status_code == 404
        for global_role in ("ANALYST", "APPROVER", "ADMIN"):
            run_id, plan_hash = _approval_run(store, case["id"])
            reader = client.post(f"/api/runs/{run_id}/research-plan/approve", headers=_headers("stored-reader", global_role), json={"plan_hash": plan_hash})
            assert reader.status_code == 403


def test_all_case_writer_role_combinations_can_approve_research_plan(tmp_path: Path) -> None:
    store = MemoryStore()
    case = _case_with_source(store, "Writer matrix")
    with _production_client(tmp_path, store) as client:
        for stored_role in ("ANALYST", "APPROVER", "ADMIN"):
            for global_role in ("ANALYST", "APPROVER", "ADMIN"):
                subject = f"{stored_role.lower()}-{global_role.lower()}"
                assert store.add_member(case["id"], "owner", subject, stored_role, "ADMIN")
                run_id, plan_hash = _approval_run(store, case["id"])
                response = client.post(f"/api/runs/{run_id}/research-plan/approve", headers=_headers(subject, global_role), json={"plan_hash": plan_hash})
                assert response.status_code == 200, response.text


def test_deep_research_start_route_passes_validated_brief_to_runtime(tmp_path: Path) -> None:
    store = MemoryStore()
    case = _case_with_source(store, "Start route")
    with _production_client(tmp_path, store, cpdr_agent_enabled=True, cpdr_pilot_subjects=("owner",)) as client:
        response = client.post(f"/api/cases/{case['id']}/runs", headers=_headers("owner", "ANALYST"), json={"pathway": "DEEP_RESEARCH", "depth": "full", "research_brief": BRIEF})
        assert response.status_code == 202, response.text
        research = response.json()["research"]
        assert research["brief"]["subject_name"] == "Northstar"
        assert research["phase"] == "planning"


def test_deep_research_availability_and_start_recheck(tmp_path: Path) -> None:
    store = MemoryStore()
    case = _case_with_source(store, "Availability")
    next(source for source in store.sources.values() if source["case_id"] == case["id"])["filename"] = "availability.txt"
    headers = _headers("owner", "ANALYST")

    with _production_client(tmp_path, store) as client:
        detail = client.get(f"/api/cases/{case['id']}", headers=headers).json()
        assert detail["deep_research_available"] is False
        assert detail["deep_research_unavailable_reason"] == "Deep Research is disabled for this deployment."

    with _production_client(tmp_path, store, cpdr_agent_enabled=True) as client:
        detail = client.get(f"/api/cases/{case['id']}", headers=headers).json()
        assert detail["deep_research_available"] is False
        assert detail["deep_research_unavailable_reason"] == "Deep Research is outside the pilot allowlist."
        denied = client.post(f"/api/cases/{case['id']}/runs", headers=headers, json={"pathway": "DEEP_RESEARCH", "depth": "full", "research_brief": BRIEF})
        assert denied.status_code == 403
        assert denied.json()["detail"] == detail["deep_research_unavailable_reason"]

    with _production_client(tmp_path, store, cpdr_agent_enabled=True, cpdr_pilot_subjects=("owner",)) as client:
        detail = client.get(f"/api/cases/{case['id']}", headers=headers).json()
        assert detail["deep_research_available"] is True
        assert detail["deep_research_unavailable_reason"] is None

    with _production_client(tmp_path, store, cpdr_agent_enabled=True, cpdr_pilot_case_ids=(case["id"],)) as client:
        detail = client.get(f"/api/cases/{case['id']}", headers=headers).json()
        assert detail["deep_research_available"] is True
        assert detail["deep_research_unavailable_reason"] is None
