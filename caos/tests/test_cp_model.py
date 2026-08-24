from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from caos.config import Settings
from caos.contracts import digest
from caos.methodology.bundle import DeployVBundle
from caos.methodology.canonical import CanonicalModuleRunner, CanonicalValidationError
from caos.models import CpModelBundle, ModelInputError, project_cp2b
from caos.store import MemoryStore
from caos.workflows import domain as workflow_domain
from caos.workflows.domain import WorkflowRuntime
from caos.workflows.provider import AgentError


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "cp_model"
DEPLOY_V = ROOT / "server" / "caos" / "methodology" / "vendor" / "deploy_v"
RUN_ID = "run-cp-model-fixture"
DIGEST = "a" * 64
FIXTURE_BY_MODULE = {
    "CP-1": "cp1.md",
    "CP-1A": "cp1a.md",
    "CP-1B": "cp1b.md",
    "CP-2": "cp2.md",
    "CP-2A": "cp2a.md",
}


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _complete_provider_markdown(runner: CanonicalModuleRunner, module_id: str) -> str:
    markdown = _read(FIXTURE_BY_MODULE[module_id])
    folder, _name, _references = runner._module(module_id)
    _handoff, completeness, _confidence = runner._load_scripts(module_id)
    skill = (folder / "SKILL.md").read_text(encoding="utf-8")
    contract = completeness.load_contract(skill, module_id)
    present = completeness.find_registers(markdown, contract["registers"])
    missing = []
    for register_id, spec in sorted(contract["registers"].items()):
        if register_id in present:
            continue
        columns = spec["columns"] or ["Value"]
        rows = [
            "| " + " | ".join("Verified" for _column in columns) + " |"
            for _row in range(spec["minimum_body_rows"])
        ]
        missing.append(
            "\n".join(
                (
                    f"### {register_id} — test contract row",
                    "",
                    "| " + " | ".join(columns) + " |",
                    "|" + "|".join("---" for _column in columns) + "|",
                    *rows,
                )
            )
        )
    appendix = "### Analytical appendix — complete canonical registers\n\n" + "\n\n".join(missing)
    return markdown.replace("\n## Evidence Trace", f"\n\n{appendix}\n\n## Evidence Trace", 1)


def _canonicalize_fixture(
    runner: CanonicalModuleRunner,
    module_id: str,
    *,
    markdown: str | None = None,
) -> dict[str, object]:
    returned = {
        ("SRC-1", "block-1"): {
            "source_digest": "b" * 64,
            "origin_family": "b" * 64,
            "authority_class": "primary",
            "locator": '{"page":42}',
            "extractor_version": "builtin-v1",
            "confidence": "HIGH",
        }
    }
    return runner.canonicalize(
        module_id,
        {
            "markdown": markdown or _complete_provider_markdown(runner, module_id),
            "evidence_refs": [{"source_id": "SRC-1", "block_id": "block-1"}],
            "lineage_counts": {"Directly Sourced": 1},
            "fields_present": 1,
            "fields_total": 1,
            "source_gate": "pass",
            "findings": {},
        },
        run={
            "id": RUN_ID,
            "case_id": "case-acme",
            "created_at": "2025-02-15T00:00:00+00:00",
            "canonical_generation": {"reporting_period": "FY2024"},
        },
        case={"issuer": "Acme Credit Ltd"},
        source_set={"id": "set-1", "version": 1},
        upstream_artifacts=[],
        returned_evidence=returned,
        authority_digest="c" * 64,
    )


def test_cp_model_loader_restores_interpreter_state() -> None:
    prior_alias = sys.modules.get("validate_handoff")
    prior_bytecode = sys.dont_write_bytecode

    CpModelBundle(DEPLOY_V)

    assert sys.dont_write_bytecode is prior_bytecode
    assert sys.modules.get("validate_handoff") is prior_alias


def test_cp_model_fixture_passes_vendor_validation() -> None:
    result = CpModelBundle(DEPLOY_V).validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
    )
    assert result.errors == ()


def test_cp2b_projection_preserves_complete_registers_and_validates() -> None:
    bundle = CpModelBundle(DEPLOY_V)
    cp2a = _read("cp2a.md")
    projected = project_cp2b(
        cp2a, run_id=RUN_ID, cp2a_artifact_digest=DIGEST, bundle=bundle
    )

    assert DIGEST in projected
    source_region = cp2a[cp2a.index("### T5.1") : cp2a.index("## Evidence Trace")]
    assert source_region in projected
    for table_id in ("T5.1", "T5.2", "T5.3", "T5.4", "T5.5", "T5.6", "T5.7"):
        assert projected.count(f"### {table_id}") == 1
    assert "Annual report 2024 note 12" in projected
    result = bundle.validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        projected,
    )
    assert result.errors == ()


def test_cp2b_projection_rejects_incomplete_registers() -> None:
    cp2a = _read("cp2a.md")
    start = cp2a.index("### T5.6")
    end = cp2a.index("### T5.7")
    with pytest.raises(ModelInputError, match="T5.1 through T5.7"):
        project_cp2b(
            cp2a[:start] + cp2a[end:],
            run_id=RUN_ID,
            cp2a_artifact_digest=DIGEST,
            bundle=CpModelBundle(DEPLOY_V),
        )


def test_cp2b_projection_rejects_malformed_rows() -> None:
    cp2a = _read("cp2a.md").replace(
        "| EVT-1 | Covenant test | Medium | High | Medium High |",
        "| EVT-1 | Covenant test | Medium | High |",
    )
    with pytest.raises(ModelInputError, match="row has 4 cells; expected 5"):
        project_cp2b(
            cp2a,
            run_id=RUN_ID,
            cp2a_artifact_digest=DIGEST,
            bundle=CpModelBundle(DEPLOY_V),
        )


def test_cp2b_projection_does_not_escalate_restricted_qa() -> None:
    cp2a = (
        _read("cp2a.md")
        .replace("confidence_score: 85", "confidence_score: 50", 1)
        .replace("confidence_band: High", "confidence_band: Low", 1)
        .replace("qa_status: Passed", "qa_status: Restricted", 1)
    )
    with pytest.raises(ModelInputError, match="not ready for CP-MODEL"):
        project_cp2b(
            cp2a,
            run_id=RUN_ID,
            cp2a_artifact_digest=DIGEST,
            bundle=CpModelBundle(DEPLOY_V),
        )


def test_canonical_runner_host_owns_identity_lineage_and_bundle_validation() -> None:
    runner = CanonicalModuleRunner(DeployVBundle(DEPLOY_V))
    artifacts = {}

    for module_id in FIXTURE_BY_MODULE:
        built = _canonicalize_fixture(runner, module_id)
        payload = built["payload"]
        artifact = {
            **built,
            "module_id": module_id,
            "digest": digest(payload),
        }
        artifacts[module_id] = artifact
        assert f"module_id: {module_id}" in built["markdown"]
        assert 'run_id: "run-cp-model-fixture"' in built["markdown"]
        assert "source_id | block_id | source_digest" in built["markdown"]
        assert built["confidence"]["qa_status"] == "Passed"

    runner.validate_bundle(artifacts, RUN_ID)


def test_canonical_runner_rejects_unreturned_model_table_source() -> None:
    runner = CanonicalModuleRunner(DeployVBundle(DEPLOY_V))
    markdown = _complete_provider_markdown(runner, "CP-1").replace("SRC-1", "FORGED-SOURCE")

    with pytest.raises(CanonicalValidationError, match="outside returned pinned sources"):
        _canonicalize_fixture(runner, "CP-1", markdown=markdown)


def _canonical_runtime_case() -> tuple[MemoryStore, WorkflowRuntime, dict[str, object]]:
    store = MemoryStore()
    runtime = WorkflowRuntime(
        store,
        DeployVBundle(DEPLOY_V),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-canonical-full-credit"),
            deploy_v_root=DEPLOY_V,
            anthropic_api_key="test-only-key",
            canonical_agent_enabled=True,
        ),
    )
    case = store.create_case("Canonical run", "Acme Credit Ltd", "Testing", "analyst")
    store.sources["SRC-1"] = {
        "id": "SRC-1",
        "case_id": case["id"],
        "filename": "annual-report.txt",
        "media_type": "text/plain",
        "sha256": "b" * 64,
        "withdrawn": False,
        "blocks": [
            {
                "block_id": "block-1",
                "locator": {"page": 42},
                "text": "Pinned test evidence for the canonical model input.",
                "extractor_version": "builtin-v1",
                "confidence": "HIGH",
            }
        ],
    }
    store.register_source_set(
        {
            "id": "set-canonical",
            "case_id": case["id"],
            "version": 1,
            "source_ids": ["SRC-1"],
            "created_by": "analyst",
            "created_at": "2025-02-15T00:00:00+00:00",
        }
    )
    return store, runtime, case


def test_full_credit_fake_provider_run_is_accepted_with_canonical_model_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, runtime, case = _canonical_runtime_case()
    provider_runner = CanonicalModuleRunner(runtime.bundle)

    class FakeCanonicalGateway:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def run(self, **kwargs: object) -> dict[str, object]:
            user = str(kwargs["user"])
            module_id = json.loads(user.split("\n", 1)[1])["host_identity"]["module_id"]
            request_digest = digest({"module_id": module_id})
            kwargs["reserve"](request_digest, 1, 1, False)
            kwargs["read_evidence"]("SRC-1", ["block-1"])
            built = kwargs["validate"](
                {
                    "markdown": _complete_provider_markdown(provider_runner, module_id),
                    "evidence_refs": [{"source_id": "SRC-1", "block_id": "block-1"}],
                    "lineage_counts": {"Directly Sourced": 1},
                    "fields_present": 1,
                    "fields_total": 1,
                    "source_gate": "pass",
                    "findings": {},
                }
            )
            kwargs["reconcile"](request_digest, 1, 1, 1, 1)
            return built

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", FakeCanonicalGateway)
    try:
        run = runtime.start_run(case["id"], "analyst", "FULL_CREDIT", "full", [])
        runtime._execute(run["id"], "analyst")

        completed = store.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded", completed and completed.get("error")
        assert completed["canonical_generation"]["phase"] == "complete"
        assert completed["canonical_generation"]["completed_modules"] == sorted(FIXTURE_BY_MODULE)
        cp1_node = next(node for node in completed["nodes"] if node["module_id"] == "CP-1")
        cp1_artifact = store.artifacts[cp1_node["artifact_id"]]
        original_cp1 = copy.deepcopy(cp1_artifact)
        cp1_artifact["markdown"] = cp1_artifact["markdown"].replace("SRC-1", "FORGED-SOURCE", 1)
        cp1_artifact["payload"]["canonical_output"]["markdown_sha256"] = hashlib.sha256(
            cp1_artifact["markdown"].encode("utf-8")
        ).hexdigest()
        cp1_artifact["digest"] = digest(cp1_artifact["payload"])
        with pytest.raises(ValueError, match="RUN_NOT_READY"):
            runtime.accept_run(case["id"], run["id"], "analyst")
        store.artifacts[cp1_node["artifact_id"]] = original_cp1
        cp2a_node = next(node for node in completed["nodes"] if node["module_id"] == "CP-2A")
        cp2a_artifact = store.artifacts[cp2a_node["artifact_id"]]
        cp2a_artifact["derived"]["CP-2B"]["digest"] = "0" * 64
        with pytest.raises(ValueError, match="RUN_NOT_READY"):
            runtime.accept_run(case["id"], run["id"], "analyst")
        cp2a_artifact["derived"]["CP-2B"]["digest"] = digest(
            {
                "module_id": "CP-2B",
                "parent_artifact_digest": cp2a_artifact["digest"],
                "markdown_sha256": hashlib.sha256(
                    cp2a_artifact["derived"]["CP-2B"]["markdown"].encode("utf-8")
                ).hexdigest(),
            }
        )
        snapshot = runtime.accept_run(case["id"], run["id"], "analyst")
        assert snapshot["run_id"] == run["id"]
        assert {item["module_id"] for item in snapshot["artifacts"]} >= set(FIXTURE_BY_MODULE)
    finally:
        runtime.close()


def test_canonical_provider_failure_uses_bounded_run_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, runtime, case = _canonical_runtime_case()

    class FailingGateway:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def run(self, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("provider-secret-body")

    monkeypatch.setattr(workflow_domain, "AnthropicGateway", FailingGateway)
    try:
        run = runtime.start_run(case["id"], "analyst", "FULL_CREDIT", "full", [])
        runtime._execute(run["id"], "analyst")

        failed = store.get_run(run["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"] == {
            "code": "CANONICAL_GENERATION_FAILED",
            "module_id": "CP-1",
            "message": "Canonical Full Credit generation failed.",
        }
        assert failed["canonical_generation"]["phase"] == "failed"
        assert "provider-secret-body" not in json.dumps(failed)
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("canonical", "completion_error", "expected_code"),
    [
        (True, AgentError("AGENT_BUDGET_EXCEEDED"), "CANONICAL_GENERATION_FAILED"),
        (False, RuntimeError("legacy-node-error"), "NODE_ERROR"),
    ],
)
def test_dispatcher_scopes_canonical_completion_failures(
    monkeypatch: pytest.MonkeyPatch,
    canonical: bool,
    completion_error: Exception,
    expected_code: str,
) -> None:
    store = MemoryStore()
    case = store.create_case("Dispatcher", "Issuer", "Testing", "analyst")
    run = store.create_run(case["id"], "analyst", {"nodes": []}, [])
    node = store.add_node(run["id"], case["id"], "CP-1", [], 1)
    updates: dict[str, object] = {"node_ids": [node["id"]], "status": "queued"}
    if canonical:
        updates["canonical_generation"] = {"phase": "generating"}
    store.update_run(run["id"], **updates)
    runtime = WorkflowRuntime(
        store,
        DeployVBundle(DEPLOY_V),
        Settings(environment="production", storage_dir=Path("/tmp/caos-dispatcher"), deploy_v_root=DEPLOY_V),
    )

    def build(*_args: object, **_kwargs: object) -> dict[str, object]:
        payload = {"status": "test"}

        def fail_completion(_elapsed: float) -> None:
            raise completion_error

        return {
            "id": "artifact-dispatcher",
            "case_id": case["id"],
            "run_id": run["id"],
            "module_id": "CP-1",
            "payload": payload,
            "digest": digest(payload),
            "input_fingerprint": "test",
            "_completion_active_time": fail_completion,
        }

    monkeypatch.setattr(runtime, "_build_artifact_with_slot", build)
    try:
        runtime._execute(run["id"], "analyst")
        failed = store.get_run(run["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == expected_code
    finally:
        runtime.close()
