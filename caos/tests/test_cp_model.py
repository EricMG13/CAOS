from __future__ import annotations

import sys
from pathlib import Path

import pytest

from caos.models import CpModelBundle, ModelInputError, project_cp2b


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "cp_model"
DEPLOY_V = ROOT / "server" / "caos" / "methodology" / "vendor" / "deploy_v"
RUN_ID = "run-cp-model-fixture"
DIGEST = "a" * 64


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


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
