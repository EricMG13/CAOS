from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from caos.config import Settings
from caos.contracts import digest
from caos.http import create_app
from caos.memory_ledgers import MemoryLedgerSet
from caos.methodology.bundle import DeployVBundle
from caos.methodology.canonical import (
    CANONICAL_MODULES,
    CanonicalModuleRunner,
    CanonicalValidationError,
    canonical_generation_state,
)
from caos.models import CpModelBundle, ModelInputError, project_cp2b
from caos.models import runtime as model_runtime
from caos.models.runtime import (
    ModelBuildRuntime,
    ModelReadinessService,
    _serialize_worksheet,
)
from caos.workflows.domain import WorkflowRuntime
from caos.workflows.provider import (
    AgentError,
    ProviderBlock,
    ProviderMessage,
    ProviderRequest,
    ProviderUsage,
)


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
    "CP-2G": "cp2g.md",
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
            "| "
            + " | ".join(
                "SRC-1" if column.casefold() == "source_id" else "Verified"
                for column in columns
            )
            + " |"
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
    appendix = (
        "### Analytical appendix — complete canonical registers\n\n"
        + "\n\n".join(missing)
    )
    return markdown.replace(
        "\n## Evidence Trace", f"\n\n{appendix}\n\n## Evidence Trace", 1
    )


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


def test_deploy_v_regeneration_is_current_and_rejects_symlink_paths(
    tmp_path: Path,
) -> None:
    script = ROOT / "scripts" / "regenerate_deploy_v_integrity.py"
    checked = subprocess.run(
        [sys.executable, str(script), "--check", "--root", str(DEPLOY_V)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stderr

    spec = importlib.util.spec_from_file_location("deploy_v_regenerator", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    skills = tmp_path / "skills" / "cp-model"
    skills.mkdir(parents=True)
    target = tmp_path / "outside.md"
    target.write_text("outside", encoding="utf-8")
    (skills / "SKILL.md").symlink_to(target)
    with pytest.raises(module.RegenerationError, match="symlink"):
        module._safe_declared_file(tmp_path, "cp-model", "SKILL.md")


def test_cp_model_fixture_passes_vendor_validation() -> None:
    result = CpModelBundle(DEPLOY_V).validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
    )
    assert result.errors == ()


def _forecast_paths() -> dict[str, Path]:
    return {
        "CP-1": FIXTURES / "cp1.md",
        "CP-1A": FIXTURES / "cp1a.md",
        "CP-1B": FIXTURES / "cp1b.md",
        "CP-2": FIXTURES / "cp2.md",
        "CP-2B": FIXTURES / "cp2b.md",
        "CP-2G": FIXTURES / "cp2g.md",
    }


def _mutate_cp2g_assumption(
    markdown: str,
    assumption_id: str,
    *,
    case: str = "BASE",
    period_id: str = "FY2025",
    **updates: str,
) -> str:
    lines = markdown.splitlines()
    header: list[str] | None = None
    changed = False
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if "assumption_id" in cells and "period_id" in cells:
            header = cells
            continue
        if header is None or len(cells) != len(header):
            continue
        row = dict(zip(header, cells, strict=True))
        if (
            row.get("assumption_id") != assumption_id
            or row.get("case") != case
            or row.get("period_id") != period_id
        ):
            continue
        row.update(updates)
        lines[index] = "| " + " | ".join(row[column] for column in header) + " |"
        changed = True
        break
    assert changed, (assumption_id, case, period_id)
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else "")


def _forecast_paths_with_cp2g(tmp_path: Path, markdown: str) -> dict[str, Path]:
    cp2g = tmp_path / "cp2g.md"
    cp2g.write_text(markdown, encoding="utf-8")
    return {**_forecast_paths(), "CP-2G": cp2g}


def _empty_stable_table(markdown: str, table_id: str) -> str:
    lines = markdown.splitlines()
    marker = f"<!-- table-id: {table_id} -->"
    marker_index = lines.index(marker)
    body_start = marker_index + 3
    end = body_start
    while end < len(lines) and not lines[end].startswith("### "):
        end += 1
    del lines[body_start:end]
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else "")


def _without_stable_table(markdown: str, table_id: str) -> str:
    lines = markdown.splitlines()
    marker_index = lines.index(f"<!-- table-id: {table_id} -->")
    start = marker_index
    while start > 0 and not lines[start].startswith("### "):
        start -= 1
    end = marker_index + 1
    while end < len(lines) and not lines[end].startswith("### "):
        end += 1
    del lines[start:end]
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else "")


def _unsegmented_cp1() -> str:
    markdown = _empty_stable_table(
        _read("cp1.md"), "cp1.segment_revenue_schedule"
    )
    markdown = _without_stable_table(
        markdown, "cp1.cp_model_segment_allocation"
    )
    for quarter, revenue in enumerate((100, 110, 120, 130), 1):
        markdown = markdown.replace(
            f"| segment-q{quarter} | FY2024_Q{quarter} | SEGMENT_REVENUE | "
            f"{revenue} | {revenue} | 0 | 0 | PASS | Segment equals reported revenue | SRC-1 |",
            f"| segment-q{quarter} | FY2024_Q{quarter} | SEGMENT_REVENUE | "
            f"{revenue} | - | - | 0 | WARN | No disclosed segment schedule | SRC-1 |",
            1,
        )
    return markdown


def _unsegmented_cp2g() -> str:
    markdown = _read("cp2g.md")
    for case in ("BASE", "DOWNSIDE"):
        for fiscal_year in (2025, 2026, 2027):
            period_id = f"FY{fiscal_year}"
            markdown = _mutate_cp2g_assumption(
                markdown,
                "operating.revenue_growth.division_1",
                case=case,
                period_id=period_id,
                status="NOT_APPLICABLE",
                value="",
                source_id="",
                source_locator="",
                as_of="",
                gap_code="",
            )
            markdown = _mutate_cp2g_assumption(
                markdown,
                "operating.consolidated_revenue_growth",
                case=case,
                period_id=period_id,
                status="READY",
                value="0.05",
                source_id="SRC-1",
                source_locator="page:42",
                as_of="2025-02-15",
                gap_code="",
            )
    return markdown


def _cp2g_with_ready_covenant(limit: str = "1") -> str:
    markdown = _read("cp2g.md")
    for case in ("BASE", "DOWNSIDE"):
        for fiscal_year in (2025, 2026, 2027):
            markdown = _mutate_cp2g_assumption(
                markdown,
                "covenant.max_total_leverage",
                case=case,
                period_id=f"FY{fiscal_year}",
                status="READY",
                value=limit,
                source_id="SRC-1",
                source_locator="page:42",
                as_of="2025-02-15",
                gap_code="",
            )
    return markdown


def test_assumption_registry_is_versioned_complete_and_explicit_about_gaps() -> None:
    registry = CpModelBundle(DEPLOY_V).assumption_registry

    assert registry["version"] == "cp-model-assumptions.v1"
    assert len(registry["digest"]) == 64
    definitions = registry["definitions"]
    assert isinstance(definitions, list)
    assert len({item["assumption_id"] for item in definitions}) == len(definitions)
    assert {item["family"] for item in definitions} == {
        "OPERATING",
        "CASH_FLOW",
        "RATES",
        "CAPITAL",
        "LIQUIDITY",
        "COVENANT",
    }
    assert all(item["cases"] == ["BASE", "DOWNSIDE"] for item in definitions)
    assert all(
        {
            "unit",
            "hard_min",
            "hard_max",
            "sensitivity_default",
            "required_authority",
            "allowed_statuses",
            "degradation",
            "affected_outputs",
        }
        <= item.keys()
        for item in definitions
    )
    covenant = next(
        item
        for item in definitions
        if item["assumption_id"] == "covenant.max_total_leverage"
    )
    assert covenant["degradation"]["gap_code"] == "COVENANT_DEFINITION_UNAVAILABLE"


def test_assumption_registry_copies_do_not_mutate_methodology_authority() -> None:
    bundle = CpModelBundle(DEPLOY_V)
    exposed = bundle.assumption_registry
    original = exposed["definitions"][0]["degradation"]["gap_code"]
    try:
        exposed["definitions"][0]["degradation"]["gap_code"] = "MUTATED"
        fresh = bundle._inputs.assumption_registry()
        assert fresh["definitions"][0]["degradation"]["gap_code"] == original
        assert fresh["digest"] == bundle.calculation_runtime[
            "assumption_registry_digest"
        ]
    finally:
        bundle._inputs.ASSUMPTION_DEFINITIONS[0]["degradation"][
            "gap_code"
        ] = original


def test_cp2g_methodology_contracts_publish_one_registry_interface() -> None:
    header = (
        "driver_id | slot_id | case | period_id | fiscal_year | value | unit | "
        "assumption_id | status | source_id | source_locator | as_of | gap_code"
    )
    cp2g = DEPLOY_V / "skills" / "cp-2g-forward-credit-model"
    cp_model = DEPLOY_V / "skills" / "cp-model"
    documents = (
        cp2g / "SKILL.md",
        cp2g / "references" / "REF_CP-2G_STEPS.md",
        cp2g / "references" / "CP-2G_ForwardCreditModel.schema.md",
    )

    for document in documents:
        text = document.read_text(encoding="utf-8")
        assert header in text, document
        assert "cp-model-assumptions.v1" in text, document
        assert "exactly three forecast years" in text.casefold(), document
        assert "COVENANT_DEFINITION_UNAVAILABLE" in text, document

    cp_model_skill = (cp_model / "SKILL.md").read_text(encoding="utf-8")
    assert "**Required upstream:** CP-1, CP-1A, CP-1B, CP-2, CP-2B, CP-2G" in cp_model_skill
    assert "**Optional upstream:** CP-2G" not in cp_model_skill


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            "| PERCENT_DECIMAL | operating.revenue_growth.division_1 |",
            "| CURRENCY_MM | operating.revenue_growth.division_1 |",
            "unit",
        ),
        (
            "| 0.05 | PERCENT_DECIMAL | operating.revenue_growth.division_1 |",
            "| NaN | PERCENT_DECIMAL | operating.revenue_growth.division_1 |",
            "finite",
        ),
        (
            "| 0.05 | PERCENT_DECIMAL | operating.revenue_growth.division_1 |",
            "| 9 | PERCENT_DECIMAL | operating.revenue_growth.division_1 |",
            "bounds",
        ),
    ],
)
def test_assumption_registry_inputs_fail_closed(
    old: str, new: str, message: str
) -> None:
    result = CpModelBundle(DEPLOY_V).validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        _read("cp2g.md").replace(old, new, 1),
    )

    assert any(message in error.casefold() for error in result.errors)


@pytest.mark.parametrize(
    ("assumption_id", "status", "gap_code"),
    [
        ("operating.adjusted_ebitda_margin", "NOT_APPLICABLE", ""),
        (
            "capital.contractual_amortization",
            "UNAVAILABLE",
            "ASSUMPTION_AUTHORITY_UNAVAILABLE",
        ),
    ],
)
def test_required_forecast_assumptions_reject_non_ready_statuses(
    assumption_id: str,
    status: str,
    gap_code: str,
) -> None:
    cp2g = _mutate_cp2g_assumption(
        _read("cp2g.md"),
        assumption_id,
        status=status,
        value="",
        source_id="",
        source_locator="",
        as_of="",
        gap_code=gap_code,
    )
    result = CpModelBundle(DEPLOY_V).validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        cp2g,
    )

    assert any("status" in error and "allowed" in error for error in result.errors)


def test_segmented_forecast_rejects_na_active_slot_before_calculation(
    tmp_path: Path,
) -> None:
    cp2g = _mutate_cp2g_assumption(
        _read("cp2g.md"),
        "operating.revenue_growth.division_1",
        status="NOT_APPLICABLE",
        value="",
        source_id="",
        source_locator="",
        as_of="",
        gap_code="",
    )
    bundle = CpModelBundle(DEPLOY_V)
    validation = bundle.validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        cp2g,
    )

    assert any("active slot DIVISION_1 must be READY" in error for error in validation.errors)
    with pytest.raises(bundle._domain.CpModelV3Error, match="active slot DIVISION_1"):
        bundle.calculate(_forecast_paths_with_cp2g(tmp_path, cp2g))


def test_segmented_forecast_requires_inactive_slots_and_consolidated_to_be_na(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(_forecast_paths())
    assert calculations.for_column("BASE::FY2025").values
    assert model.segment_forecast_slots == {"services": "DIVISION_1"}

    cp2g = _mutate_cp2g_assumption(
        _read("cp2g.md"),
        "operating.revenue_growth.division_2",
        status="READY",
        value="0",
        source_id="SRC-1",
        source_locator="page:42",
        as_of="2025-02-15",
        gap_code="",
    )
    validation = bundle.validate(
        _read("cp1.md"),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        cp2g,
    )

    assert any("inactive slot DIVISION_2 must be NOT_APPLICABLE" in error for error in validation.errors)
    with pytest.raises(bundle._domain.CpModelV3Error, match="inactive slot DIVISION_2"):
        bundle.calculate(_forecast_paths_with_cp2g(tmp_path, cp2g))


def test_unsegmented_forecast_requires_consolidated_growth_and_calculates(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    cp1 = _unsegmented_cp1()
    cp2g = _unsegmented_cp2g()
    validation = bundle.validate(
        cp1,
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        cp2g,
    )
    assert validation.errors == ()
    cp1_path = tmp_path / "cp1-unsegmented.md"
    cp1_path.write_text(cp1, encoding="utf-8")
    paths = _forecast_paths_with_cp2g(tmp_path, cp2g)
    paths["CP-1"] = cp1_path

    model, calculations = bundle.calculate(paths)

    assert model.segments == ()
    assert calculations.for_column("BASE::FY2025").values["revenue"] > 0


def test_unsegmented_forecast_rejects_division_growth_and_na_consolidated(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    cp1 = _unsegmented_cp1()
    cp2g = _read("cp2g.md")
    validation = bundle.validate(
        cp1,
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        cp2g,
    )

    assert any("inactive slot DIVISION_1 must be NOT_APPLICABLE" in error for error in validation.errors)
    assert any("unsegmented issuer requires READY consolidated growth" in error for error in validation.errors)
    cp1_path = tmp_path / "cp1-unsegmented-invalid.md"
    cp1_path.write_text(cp1, encoding="utf-8")
    paths = _forecast_paths_with_cp2g(tmp_path, cp2g)
    paths["CP-1"] = cp1_path
    with pytest.raises(bundle._domain.CpModelV3Error, match="unsegmented issuer"):
        bundle.calculate(paths)


@pytest.mark.parametrize("mutation", ["missing", "not_ready", "non_finite"])
def test_direct_calculation_rejects_invalid_active_segment_growth(
    mutation: str,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, _calculations = bundle.calculate(_forecast_paths())
    target = "operating.revenue_growth.division_1"
    forecast_drivers = []
    for driver in model.forecast_drivers:
        if (
            driver.assumption_id == target
            and driver.case == "BASE"
            and driver.period_id == "FY2025"
        ):
            if mutation == "missing":
                continue
            driver = dataclasses.replace(
                driver,
                status="NOT_APPLICABLE" if mutation == "not_ready" else "READY",
                value=None if mutation == "not_ready" else Decimal("NaN"),
            )
        forecast_drivers.append(driver)
    invalid = dataclasses.replace(model, forecast_drivers=tuple(forecast_drivers))

    with pytest.raises(
        bundle._domain.CpModelV3Error,
        match=r"active forecast growth.*DIVISION_1.*BASE/FY2025",
    ):
        bundle._calculations.calculate(invalid)


@pytest.mark.parametrize("mutation", ["missing", "not_ready", "non_finite"])
def test_direct_calculation_rejects_invalid_active_consolidated_growth(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    cp1_path = tmp_path / "cp1-unsegmented-direct.md"
    cp1_path.write_text(_unsegmented_cp1(), encoding="utf-8")
    paths = _forecast_paths_with_cp2g(tmp_path, _unsegmented_cp2g())
    paths["CP-1"] = cp1_path
    model, _calculations = bundle.calculate(paths)
    target = "operating.consolidated_revenue_growth"
    forecast_drivers = []
    for driver in model.forecast_drivers:
        if (
            driver.assumption_id == target
            and driver.case == "BASE"
            and driver.period_id == "FY2025"
        ):
            if mutation == "missing":
                continue
            driver = dataclasses.replace(
                driver,
                status="NOT_APPLICABLE" if mutation == "not_ready" else "READY",
                value=None if mutation == "not_ready" else Decimal("Infinity"),
            )
        forecast_drivers.append(driver)
    invalid = dataclasses.replace(model, forecast_drivers=tuple(forecast_drivers))

    with pytest.raises(
        bundle._domain.CpModelV3Error,
        match=r"active forecast growth.*CONSOLIDATED.*BASE/FY2025",
    ):
        bundle._calculations.calculate(invalid)


def test_allowed_unavailable_liquidity_degrades_to_named_null_outputs(
    tmp_path: Path,
) -> None:
    cp2g = _mutate_cp2g_assumption(
        _read("cp2g.md"),
        "liquidity.minimum_operating_cash",
        status="UNAVAILABLE",
        value="",
        source_id="",
        source_locator="",
        as_of="",
        gap_code="MINIMUM_CASH_DEFINITION_UNAVAILABLE",
    )
    bundle = CpModelBundle(DEPLOY_V)
    paths = _forecast_paths_with_cp2g(tmp_path, cp2g)
    validation = bundle.validate(*(_read(name) for name in ("cp1.md", "cp1a.md", "cp1b.md", "cp2.md", "cp2b.md")), cp2g)
    assert validation.errors == ()

    model, calculations = bundle.calculate(paths)
    forecast = calculations.for_column("BASE::FY2025")

    assert "MINIMUM_CASH_DEFINITION_UNAVAILABLE" in model.assumption_gaps
    assert forecast.values["minimum_operating_cash"] is None
    assert forecast.values["accessible_liquidity"] is None
    assert forecast.values["liquidity_headroom"] is None
    rendered = bundle.render_workbook(
        model, calculations, tmp_path / "unavailable-liquidity.xlsx"
    )
    assert ("minimum_operating_cash", "BASE::FY2025") not in rendered.model_cells
    assert ("accessible_liquidity", "BASE::FY2025") not in rendered.model_cells
    assert ("liquidity_headroom", "BASE::FY2025") not in rendered.model_cells


def test_forecast_missing_required_driver_raises_typed_input_error() -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(_forecast_paths())
    drivers = bundle._calculations._forecast_driver_lookup(model)
    del drivers[("BASE", "FY2025", "adjusted_ebitda_margin", "")]

    with pytest.raises(bundle._domain.CpModelV3Error, match="adjusted_ebitda_margin"):
        bundle._calculations._forecast_column(
            model,
            next(
                column
                for column in calculations.columns
                if column.column_id == "BASE::FY2025"
            ),
            calculations.for_column("PF_FY2024_Q4"),
            calculations.for_column("PF_FY2024_Q4"),
            drivers,
        )


def test_effective_assumption_overlay_recalculates_all_decision_outputs() -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, baseline = bundle.calculate(_forecast_paths())
    effective = [dataclasses.asdict(item) for item in model.effective_assumptions]
    for item in effective:
        if (
            item["assumption_id"] == "operating.adjusted_ebitda_margin"
            and item["case"] == "BASE"
            and item["period_id"] == "FY2025"
        ):
            item["value"] = Decimal("0.30")
        if (
            item["assumption_id"] == "liquidity.minimum_operating_cash"
            and item["case"] == "BASE"
            and item["period_id"] == "FY2025"
        ):
            item["value"] += Decimal("10")

    adjusted_model, adjusted = bundle.calculate(
        _forecast_paths(), effective_assumptions=effective
    )
    base = baseline.for_column("BASE::FY2025")
    changed = adjusted.for_column("BASE::FY2025")

    assert len(adjusted_model.effective_assumptions) == len(effective)
    assert changed.values["revenue"] == base.values["revenue"]
    assert changed.values["adjusted_ebitda_calc"] > base.values["adjusted_ebitda_calc"]
    assert changed.values["fcf"] > base.values["fcf"]
    assert changed.values["cumulative_fcf"] > base.values["cumulative_fcf"]
    assert changed.values["liquidity_headroom"] == (
        base.values["liquidity_headroom"]
        + changed.values["fcf"]
        - base.values["fcf"]
        - 10
    )
    assert changed.values["net_debt"] < base.values["net_debt"]
    assert changed.credit_metrics["total_leverage"] < base.credit_metrics["total_leverage"]
    assert changed.credit_metrics["interest_coverage"] > base.credit_metrics["interest_coverage"]
    assert changed.credit_metrics["covenant_headroom"] is None
    assert "COVENANT_DEFINITION_UNAVAILABLE" in adjusted_model.assumption_gaps


def test_forecast_ratios_and_nonfinite_cp1_operands_fail_closed(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, _calculations = bundle.calculate(_forecast_paths())
    effective = [dataclasses.asdict(item) for item in model.effective_assumptions]
    for item in effective:
        if (
            item["assumption_id"] == "operating.adjusted_ebitda_margin"
            and item["case"] == "BASE"
            and item["period_id"] == "FY2025"
        ):
            item["value"] = Decimal("0")
        if (
            item["assumption_id"] in {"rates.base_rate", "rates.debt_spread"}
            and item["case"] == "BASE"
            and item["period_id"] == "FY2025"
        ):
            item["value"] = Decimal("0")

    zero_model, zero_calculations = bundle.calculate(
        _forecast_paths(), effective_assumptions=effective
    )
    zero = zero_calculations.for_column("BASE::FY2025")
    assert zero.values["adjusted_ebitda_calc"] == Decimal("0")
    assert zero.credit_metrics["total_leverage"] is None
    assert zero.credit_metrics["net_leverage"] is None
    assert zero.credit_metrics["interest_coverage"] is None
    assert zero.values["accessible_liquidity"] == (
        max(
            zero.values["cash_and_equivalents"]
            - zero.values["minimum_operating_cash"],
            Decimal("0"),
        )
        + zero.values["undrawn_revolver"]
    )
    output = tmp_path / "zero-denominator.xlsx"
    rendered = bundle.render_workbook(zero_model, zero_calculations, output)
    for metric in ("total_leverage", "net_leverage", "interest_coverage"):
        assert (metric, "BASE::FY2025") not in rendered.model_cells

    pro_forma = zero_calculations.for_column("PF_FY2024_Q4")
    zero_revenue_pro_forma = dataclasses.replace(
        pro_forma,
        values={**pro_forma.values, "revenue": Decimal("0")},
    )
    forecast_column = next(
        column
        for column in zero_calculations.columns
        if column.column_id == "BASE::FY2025"
    )
    with pytest.raises(
        bundle._domain.CpModelV3Error,
        match="pro-forma revenue denominator",
    ):
        bundle._calculations._forecast_column(
            zero_model,
            forecast_column,
            zero_revenue_pro_forma,
            zero_revenue_pro_forma,
            bundle._calculations._forecast_driver_lookup(zero_model),
        )

    workbook = model_runtime.load_workbook(output, data_only=False, read_only=False)
    try:
        for key in (
            "cogs",
            "depreciation_amortization",
            "net_accounts_receivable",
            "inventory",
            "accounts_payable",
        ):
            formula = workbook["Model"][
                rendered.model_cells[(key, "BASE::FY2025")]
            ].value
            assert isinstance(formula, str) and "IFERROR" not in formula
    finally:
        workbook.close()

    invalid = bundle.validate(
        _read("cp1.md").replace(
            "| adjusted_ebitda | FY2024_Q4 | 27 |",
            "| adjusted_ebitda | FY2024_Q4 | NaN |",
            1,
        ),
        _read("cp1a.md"),
        _read("cp1b.md"),
        _read("cp2.md"),
        _read("cp2b.md"),
        _read("cp2g.md"),
    )
    assert any("finite" in error.casefold() for error in invalid.errors)


def test_forecast_calculation_boundary_rejects_nonfinite_operands_locally() -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(_forecast_paths())
    column = next(
        item for item in calculations.columns if item.column_id == "BASE::FY2025"
    )
    pro_forma = calculations.for_column("PF_FY2024_Q4")
    drivers = bundle._calculations._forecast_driver_lookup(model)
    segment_id = model.segments[0].series_id

    cases = (
        (
            dataclasses.replace(
                pro_forma,
                segment_values={
                    **pro_forma.segment_values,
                    segment_id: Decimal("NaN"),
                },
            ),
            pro_forma,
            drivers,
            "segment revenue",
        ),
        (
            dataclasses.replace(
                pro_forma,
                values={
                    **pro_forma.values,
                    "total_debt_reported": Decimal("Infinity"),
                },
            ),
            pro_forma,
            drivers,
            "total_debt_reported",
        ),
        (
            pro_forma,
            dataclasses.replace(
                pro_forma,
                values={**pro_forma.values, "ffo_other": Decimal("-Infinity")},
            ),
            drivers,
            "ffo_other",
        ),
        (
            pro_forma,
            dataclasses.replace(
                pro_forma,
                values={**pro_forma.values, "cogs": Decimal("0")},
            ),
            drivers,
            "denominator",
        ),
        (
            pro_forma,
            pro_forma,
            {
                **drivers,
                ("BASE", "FY2025", "working_capital_pct_revenue", ""): Decimal("NaN"),
            },
            "working_capital_pct_revenue",
        ),
        (
            pro_forma,
            pro_forma,
            {
                **drivers,
                ("BASE", "FY2025", "adjusted_ebitda_margin", ""): Decimal("Infinity"),
            },
            "adjusted_ebitda_margin",
        ),
        (
            pro_forma,
            pro_forma,
            {
                **drivers,
                ("BASE", "FY2025", "base_rate", ""): Decimal("-Infinity"),
            },
            "base_rate",
        ),
    )
    for prior, ratio_source, test_drivers, message in cases:
        with pytest.raises(bundle._domain.CpModelV3Error, match=message):
            bundle._calculations._forecast_column(
                model, column, prior, ratio_source, test_drivers
            )

    nonfinite_metrics = dataclasses.replace(
        pro_forma,
        values={
            **pro_forma.values,
            "adjusted_ebitda_calc": Decimal("NaN"),
        },
    )
    with pytest.raises(bundle._domain.CpModelV3Error, match="adjusted EBITDA"):
        bundle._calculations._column_credit_metrics(nonfinite_metrics)


def test_first_breach_preserves_threshold_identity_for_each_breach_family(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    covenant_paths = _forecast_paths_with_cp2g(
        tmp_path, _cp2g_with_ready_covenant()
    )
    scenarios = []
    for paths, minimum_cash in (
        (_forecast_paths(), Decimal("1000")),
        (covenant_paths, None),
        (covenant_paths, Decimal("1000")),
    ):
        model, _ = bundle.calculate(paths)
        effective = [dataclasses.asdict(item) for item in model.effective_assumptions]
        if minimum_cash is not None:
            for item in effective:
                if (
                    item["assumption_id"] == "liquidity.minimum_operating_cash"
                    and item["case"] == "BASE"
                    and item["period_id"] == "FY2025"
                ):
                    item["value"] = minimum_cash
        _, calculations = bundle.calculate(paths, effective_assumptions=effective)
        scenarios.append(calculations.first_breaches["BASE"])

    assert {item.threshold_id for item in scenarios[0]} == {
        "liquidity.minimum_operating_cash"
    }
    assert {item.threshold_id for item in scenarios[1]} == {
        "covenant.max_total_leverage"
    }
    assert {item.threshold_id for item in scenarios[2]} == {
        "liquidity.minimum_operating_cash",
        "covenant.max_total_leverage",
    }
    for scenario in scenarios:
        assert all(item.case == "BASE" and item.period_id == "BASE::FY2025" for item in scenario)
        assert all(
            item.headroom
            == (
                item.actual - item.limit
                if item.threshold_id == "liquidity.minimum_operating_cash"
                else item.limit - item.actual
            )
            for item in scenario
        )


def test_forecast_identified_addbacks_are_independent_of_historical_series(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(_forecast_paths())
    column = next(
        item for item in calculations.columns if item.column_id == "BASE::FY2025"
    )
    pro_forma = calculations.for_column("PF_FY2024_Q4")
    drivers = bundle._calculations._forecast_driver_lookup(model)
    identified = drivers[("BASE", "FY2025", "identified_addbacks", "")]
    existing = model.addbacks[0]
    extra = dataclasses.replace(
        existing,
        series_id="secondary_historical_addback",
        label="Secondary historical add-back",
        display_priority=existing.display_priority + 1,
        values={
            period_id: dataclasses.replace(point, value=Decimal("0"))
            for period_id, point in existing.values.items()
        },
    )

    for index, addbacks in enumerate(((), (existing,), (existing, extra))):
        variant_model = dataclasses.replace(model, addbacks=addbacks)
        forecast = bundle._calculations._forecast_column(
            variant_model,
            column,
            pro_forma,
            pro_forma,
            drivers,
        )
        assert forecast.addback_values["forecast::identified_addbacks"] == identified
        assert all(forecast.addback_values[item.series_id] == 0 for item in addbacks)
        assert forecast.values["total_addbacks"] == identified
        assert forecast.values["adjusted_ebitda_variance"] == 0

        forecast = dataclasses.replace(
            forecast,
            credit_metrics=calculations.for_column("BASE::FY2025").credit_metrics,
        )
        latest_period_id = model.quarters[-1].period_id
        latest_period = calculations.for_period(latest_period_id)
        variant_calculations = dataclasses.replace(
            calculations,
            periods={
                **calculations.periods,
                latest_period_id: dataclasses.replace(
                    latest_period,
                    addback_values={
                        **latest_period.addback_values,
                        **(
                            {extra.series_id: Decimal("0")}
                            if extra in addbacks
                            else {}
                        ),
                    },
                ),
            },
            column_calculations={
                **calculations.column_calculations,
                "BASE::FY2025": forecast,
            },
        )
        output = tmp_path / f"forecast-addbacks-{index}.xlsx"
        rendered = bundle.render_workbook(
            variant_model, variant_calculations, output
        )
        assert (
            "addback::forecast::identified_addbacks",
            "BASE::FY2025",
        ) in rendered.model_cells
        expectation = next(
            item
            for item in rendered.formulas
            if item.semantic_id == "total_addbacks"
            and item.expected == identified
            and item.cell
            == rendered.model_cells[("total_addbacks", "BASE::FY2025")]
        )
        assert expectation.expected == forecast.values["total_addbacks"]


def test_first_breach_is_visible_and_audited_for_base_and_downside(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    paths = _forecast_paths_with_cp2g(tmp_path, _cp2g_with_ready_covenant())
    model, _calculations = bundle.calculate(paths)
    effective = [dataclasses.asdict(item) for item in model.effective_assumptions]
    for item in effective:
        if (
            item["assumption_id"] == "liquidity.minimum_operating_cash"
            and item["period_id"] == "FY2025"
        ):
            item["value"] = Decimal("1000")
        if (
            item["assumption_id"] == "liquidity.undrawn_revolver"
            and item["period_id"] == "FY2025"
        ):
            item["value"] = Decimal("0")

    breach_model, breach_calculations = bundle.calculate(
        paths, effective_assumptions=effective
    )
    assert all(len(breach_calculations.first_breaches[case]) == 2 for case in ("BASE", "DOWNSIDE"))

    output = tmp_path / "first-breach.xlsx"
    rendered = bundle.render_workbook(breach_model, breach_calculations, output)
    workbook = model_runtime.load_workbook(output, data_only=False, read_only=False)
    try:
        snapshot_values = {
            cell.value
            for row in workbook["Credit Snapshot"].iter_rows()
            for cell in row
            if cell.value is not None
        }
        audit = {
            row[0]: row[1]
            for row in workbook["_AUDIT"].iter_rows(min_row=2, values_only=True)
        }
        checks = list(workbook["_CHECKS"].iter_rows(min_row=2, values_only=True))
        assert "Base first breach" in snapshot_values
        assert "Downside first breach" in snapshot_values
        assert any("liquidity.minimum_operating_cash" in str(value) for value in snapshot_values)
        assert any("covenant.max_total_leverage" in str(value) for value in snapshot_values)
        assert "liquidity.minimum_operating_cash" in audit["first_breach::BASE"]
        assert "covenant.max_total_leverage" in audit["first_breach::DOWNSIDE"]
        assert any(
            row[0] == "first_breach"
            and row[2] == "BASE::FY2025"
            and "liquidity.minimum_operating_cash" in row[7]
            for row in checks
        )
        payload, _qa = _serialize_worksheet(
            output, rendered, breach_model, breach_calculations
        )
        snapshot_payload = next(tab for tab in payload["tabs"] if tab["name"] == "Credit Snapshot")
        assert any(
            "covenant.max_total_leverage" in str(cell["value"])
            for cell in snapshot_payload["cells"]
        )
    finally:
        workbook.close()


def test_registry_workbook_inputs_formulas_checks_and_audit_match_python(
    tmp_path: Path,
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(_forecast_paths())
    output = tmp_path / "forecast-model.xlsx"
    rendered = bundle.render_workbook(model, calculations, output)
    workbook = model_runtime.load_workbook(output, data_only=False, read_only=False)
    try:
        inputs = workbook["_INPUTS"]
        input_rows = list(inputs.iter_rows(values_only=True))
        input_header = input_rows[0]
        assumption_rows = [
            row for row in input_rows[1:] if row[1] and str(row[1]).startswith("assumption::")
        ]
        mapping_ids = {
            row[0]
            for row in workbook["_MAP"].iter_rows(min_row=2, values_only=True)
            if row[0]
        }
        audit = {
            row[0]: row[1]
            for row in workbook["_AUDIT"].iter_rows(min_row=2, values_only=True)
        }
        checks = list(workbook["_CHECKS"].iter_rows(min_row=2, values_only=True))

        assert "gap_code" in input_header
        assert len(assumption_rows) == len(model.effective_assumptions)
        assert all(
            f"assumption::{item.assumption_id}" in mapping_ids
            for item in model.effective_assumptions
            if item.status == "READY"
        )
        assert audit["assumption_registry_version"] == bundle.assumption_registry["version"]
        assert audit["assumption_registry_digest"] == bundle.assumption_registry["digest"]
        assert audit["calculation_contract_version"] == bundle.calculation_runtime[
            "calculation_contract_version"
        ]
        assert audit["first_breach::BASE"] == "NONE"
        assert audit["first_breach::DOWNSIDE"] == "NONE"
        assert any(row[0] == "assumption_set_completeness" and row[1] == "PASS" for row in checks)
        assert any(
            row[0] == "assumption_gap"
            and row[1] == "WARN"
            and "COVENANT_DEFINITION_UNAVAILABLE" in row[7]
            for row in checks
        )
        decision_outputs = {
            "revenue",
            "adjusted_ebitda_calc",
            "fcf",
            "cumulative_fcf",
            "cash_and_equivalents",
            "accessible_liquidity",
            "liquidity_headroom",
            "total_debt_reported",
            "net_debt",
            "total_leverage",
            "interest_coverage",
        }
        for case in ("BASE", "DOWNSIDE"):
            for year in (2025, 2026, 2027):
                column_id = f"{case}::FY{year}"
                expected = calculations.for_column(column_id)
                for output_id in decision_outputs:
                    assert (output_id, column_id) in rendered.model_cells
                    expectation = next(
                        item
                        for item in rendered.formulas
                        if item.cell == rendered.model_cells[(output_id, column_id)]
                        and item.semantic_id == output_id
                    )
                    source = (
                        expected.credit_metrics
                        if output_id in {"total_leverage", "interest_coverage"}
                        else expected.values
                    )
                    assert expectation.expected == source[output_id]
        assert ("covenant_headroom", "BASE::FY2025") not in rendered.model_cells
    finally:
        workbook.close()


def test_python_runtime_serializes_visible_worksheets_without_libreoffice(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", "")
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(
        {
            "CP-1": FIXTURES / "cp1.md",
            "CP-1A": FIXTURES / "cp1a.md",
            "CP-1B": FIXTURES / "cp1b.md",
            "CP-2": FIXTURES / "cp2.md",
            "CP-2B": FIXTURES / "cp2b.md",
        }
    )
    draft = tmp_path / "model.xlsx"
    rendered = bundle.render_workbook(model, calculations, draft)
    payload, qa = _serialize_worksheet(draft, rendered, model, calculations)

    assert [tab["name"] for tab in payload["tabs"]] == [
        "Credit Snapshot",
        "Model",
        "KPIs",
    ]
    assert qa["status"] == "PASS"
    assert qa["worksheet_cell_count"] == sum(
        len(tab["cells"]) for tab in payload["tabs"]
    )
    assert qa["formula_count"] > 0
    assert all(check["status"] == "PASS" for check in qa["semantic_checks"])
    formula = next(
        cell
        for tab in payload["tabs"]
        for cell in tab["cells"]
        if cell["formula"] is not None
    )
    sourced = next(
        cell for tab in payload["tabs"] for cell in tab["cells"] if cell["source_refs"]
    )
    assert formula["semantic_id"] and formula["value"] is not None
    assert sourced["semantic_id"] and "SRC-1" in sourced["source_refs"]


def test_worksheet_serializer_closes_workbook_when_cell_limit_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle = CpModelBundle(DEPLOY_V)
    model, calculations = bundle.calculate(
        {
            "CP-1": FIXTURES / "cp1.md",
            "CP-1A": FIXTURES / "cp1a.md",
            "CP-1B": FIXTURES / "cp1b.md",
            "CP-2": FIXTURES / "cp2.md",
            "CP-2B": FIXTURES / "cp2b.md",
        }
    )
    draft = tmp_path / "model.xlsx"
    rendered = bundle.render_workbook(model, calculations, draft)
    workbook = model_runtime.load_workbook(draft, data_only=False, read_only=False)

    class CloseTrackingWorkbook:
        closed = False

        def __getitem__(self, key: str):
            return workbook[key]

        def close(self) -> None:
            self.closed = True
            workbook.close()

    tracked = CloseTrackingWorkbook()
    monkeypatch.setattr(model_runtime, "load_workbook", lambda *args, **kwargs: tracked)
    monkeypatch.setattr(model_runtime, "MAX_WORKSHEET_CELLS", 0)

    with pytest.raises(ValueError, match="worksheet cell limit exceeded"):
        _serialize_worksheet(draft, rendered, model, calculations)

    assert tracked.closed is True


def test_json_value_rejects_decimal_that_overflows_float() -> None:
    with pytest.raises(ValueError, match="non-finite worksheet value"):
        model_runtime._json_value(Decimal("1e9999"))


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
    markdown = _complete_provider_markdown(runner, "CP-1").replace(
        "SRC-1", "FORGED-SOURCE"
    )

    with pytest.raises(
        CanonicalValidationError, match="outside returned pinned sources"
    ):
        _canonicalize_fixture(runner, "CP-1", markdown=markdown)


def test_canonical_turn_budget_covers_all_bounded_interactions() -> None:
    limits = canonical_generation_state("test-model", "2026-08-24")["budget_limits"]

    assert limits["turns"] >= (
        limits["evidence_reads"] + len(CANONICAL_MODULES) + limits["repairs"]
    )


class _CanonicalProvider:
    def __init__(self, failure: BaseException | None = None) -> None:
        self.runner = CanonicalModuleRunner(DeployVBundle(DEPLOY_V))
        self.failure = failure
        self.source_id = "SRC-1"
        self.calls: list[ProviderRequest] = []

    def count_tokens(self, request: ProviderRequest) -> int:
        return 1

    def create_message(self, request: ProviderRequest) -> ProviderMessage:
        self.calls.append(copy.deepcopy(request))
        if self.failure is not None:
            raise self.failure
        module_id = json.loads(str(request.messages[0]["content"]).split("\n", 1)[1])[
            "host_identity"
        ]["module_id"]
        if len(request.messages) == 1:
            content = [
                ProviderBlock(
                    type="tool_use",
                    id=f"tool-{module_id}",
                    name="read_evidence",
                    input={"source_id": self.source_id, "block_ids": ["block-1"]},
                )
            ]
            stop_reason = "tool_use"
        else:
            content = [
                ProviderBlock(
                    type="text",
                    text=json.dumps(
                        {
                            "markdown": _complete_provider_markdown(
                                self.runner, module_id
                            ).replace("SRC-1", self.source_id),
                            "evidence_refs": [
                                {"source_id": self.source_id, "block_id": "block-1"}
                            ],
                            "lineage_counts": {"Directly Sourced": 1},
                            "fields_present": 1,
                            "fields_total": 1,
                            "source_gate": "pass",
                            "findings": {},
                        }
                    ),
                )
            ]
            stop_reason = "end_turn"
        return ProviderMessage(content, stop_reason, ProviderUsage(1, 1))


def _canonical_runtime_case(
    provider: _CanonicalProvider | None = None,
) -> tuple[MemoryLedgerSet, WorkflowRuntime, dict[str, object]]:
    ledgers = MemoryLedgerSet()
    runtime = WorkflowRuntime(
        ledgers.runs,
        ledgers.sources,
        DeployVBundle(DEPLOY_V),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-canonical-full-credit"),
            deploy_v_root=DEPLOY_V,
            anthropic_api_key="test-only-key",
            canonical_agent_enabled=True,
        ),
        provider=provider,
    )
    case = ledgers.runs.create_case(
        "Canonical run", "Acme Credit Ltd", "Testing", "analyst"
    )
    source = ledgers.sources.ingest(
        {
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
        },
        "analyst",
    )
    if provider is not None:
        provider.source_id = source["id"]
    return ledgers, runtime, case


def _accepted_model_case() -> tuple[
    MemoryLedgerSet, WorkflowRuntime, dict[str, object]
]:
    ledgers, runtime, case = _canonical_runtime_case(_CanonicalProvider())
    run = runtime.start_run(case["id"], "analyst", "FULL_CREDIT", "full", [])
    runtime._execute(run["id"], "analyst")
    runtime.accept_run(case["id"], run["id"], "analyst")
    return ledgers, runtime, case


def test_accepted_full_credit_queues_and_builds_idempotent_python_model() -> None:
    ledgers, workflow, case = _accepted_model_case()
    model_bundle = CpModelBundle(DEPLOY_V)
    readiness = ModelReadinessService(
        ledgers.runs, ledgers.sources, ledgers.models, workflow.bundle, model_bundle
    )
    model_runtime = ModelBuildRuntime(
        ledgers.models,
        readiness,
        model_bundle,
        workflow.executor,
        workflow.settings.storage_dir,
    )
    try:
        ready_to_build = readiness.readiness(case["id"])
        queued, created = readiness.queue(case["id"], "analyst")
        duplicate, duplicate_created = readiness.queue(case["id"], "analyst")
        model_runtime._execute(queued["id"], "analyst")
        built = ledgers.models.get_build(queued["id"])

        assert ready_to_build["status"] == "READY_TO_BUILD"
        assert created is True and duplicate_created is False
        assert duplicate["id"] == queued["id"]
        assert built is not None and built["status"] == "READY"
        assert built["payload_digest"] == digest(built["payload"])
        assert built["qa"]["status"] == "PASS"
        assert readiness.readiness(case["id"])["status"] == "READY"
    finally:
        workflow.close()


def test_latest_accepted_full_credit_uses_validated_canonical_cp2g() -> None:
    ledgers, workflow, case = _accepted_model_case()
    first_visible = ledgers.runs.get_case(case["id"])["visible_snapshot_id"]
    second_run = workflow.start_run(
        case["id"], "analyst", "FULL_CREDIT", "full", []
    )
    workflow._execute(second_run["id"], "analyst")
    latest = workflow.accept_run(case["id"], second_run["id"], "analyst")
    readiness = ModelReadinessService(
        ledgers.runs,
        ledgers.sources,
        ledgers.models,
        workflow.bundle,
        CpModelBundle(DEPLOY_V),
    )
    try:
        state = readiness.readiness(case["id"])

        assert first_visible != latest["id"]
        assert ledgers.runs.get_case(case["id"])["visible_snapshot_id"] == first_visible
        assert state["status"] == "READY_TO_BUILD"
        assert state["accepted_snapshot"]["id"] == latest["id"]
        assert next(
            item for item in state["requirements"] if item["module_id"] == "CP-2G"
        )["status"] == "READY"
    finally:
        workflow.close()


def test_model_api_is_case_scoped_downloads_verified_export_and_freezes_identity(
    tmp_path: Path,
) -> None:
    ledgers, workflow, case = _accepted_model_case()
    model_bundle = CpModelBundle(DEPLOY_V)
    readiness = ModelReadinessService(
        ledgers.runs, ledgers.sources, ledgers.models, workflow.bundle, model_bundle
    )
    model_runtime = ModelBuildRuntime(
        ledgers.models, readiness, model_bundle, workflow.executor, tmp_path
    )
    try:
        queued, _created = readiness.queue(case["id"], "analyst")
        model_runtime._execute(queued["id"], "analyst")
        ready = ledgers.models.get_build(queued["id"])
        assert ready is not None and ready["status"] == "READY"

        ledgers.models.queue_export(ready["id"], "analyst")
        export_token = ledgers.models.claim(ready["id"], "test-export", "export")
        assert export_token is not None
        content = b"verified-test-workbook"
        checksum = hashlib.sha256(content).hexdigest()
        relative = Path("models") / case["id"] / ready["id"] / f"{checksum}.xlsx"
        export_path = tmp_path / relative
        export_path.parent.mkdir(parents=True)
        export_path.write_bytes(content)
        ledgers.models.complete(
            ready["id"],
            export_token,
            {
                "vault_key": relative.as_posix(),
                "filename": "model.xlsx",
                "sha256": checksum,
                "size": len(content),
                "formulas_validated": ready["qa"]["formula_count"],
                "semantic_checks": ready["qa"]["semantic_check_count"],
                "renderer_version": "3.0",
                "renderer_sha256": ready["calculation_runtime"]["sha256"],
                "calculation_engine": "test",
            },
            "test-export",
            "export",
        )
        settings = Settings(
            environment="test", storage_dir=tmp_path, deploy_v_root=DEPLOY_V
        )
        app = create_app(settings, ledgers)
        analyst = {"x-forwarded-user": "analyst", "x-caos-role": "ANALYST"}
        outsider = {"x-forwarded-user": "outsider", "x-caos-role": "ANALYST"}
        with TestClient(app) as client:
            models = client.get(f"/api/cases/{case['id']}/models", headers=analyst)
            worksheet = client.get(
                f"/api/cases/{case['id']}/models/{ready['id']}/worksheet",
                headers=analyst,
            )
            download = client.get(
                f"/api/cases/{case['id']}/models/{ready['id']}/download",
                headers=analyst,
            )
            denied = client.get(
                f"/api/cases/{case['id']}/models/{ready['id']}", headers=outsider
            )
            other = ledgers.runs.create_case(
                "Other", "Other issuer", "Testing", "analyst"
            )
            cross_case = client.get(
                f"/api/cases/{other['id']}/models/{ready['id']}", headers=analyst
            )

            assert models.status_code == 200
            assert "payload" not in models.json()["builds"][0]
            assert worksheet.status_code == 200 and worksheet.json()["payload"]["tabs"]
            assert download.status_code == 200 and download.content == content
            assert download.headers["cache-control"] == "no-store"
            assert denied.status_code == 404 and cross_case.status_code == 404

            thesis = client.post(
                f"/api/cases/{case['id']}/thesis",
                headers=analyst,
                json={
                    "expected_version": 0,
                    "core_thesis": "Defensible",
                    "drivers": [],
                    "risks": [],
                    "catalysts": [],
                    "unresolved_questions": [],
                    "evidence_ids": [],
                },
            ).json()
            recommendations = client.post(
                f"/api/cases/{case['id']}/recommendations",
                headers=analyst,
                json={
                    "expected_version": 0,
                    "market_snapshot_id": "market",
                    "rows": [
                        {
                            "instrument_id": "bond",
                            "instrument": "Bond",
                            "recommendation": "MARKET WEIGHT",
                            "rationale": "Model-backed",
                            "primary": True,
                        }
                    ],
                    "analytical_dependency_ids": [],
                },
            ).json()
            model_only = client.post(
                f"/api/cases/{case['id']}/reports/freeze",
                headers=analyst,
                json={
                    "thesis_version": thesis["version"],
                    "recommendation_version": recommendations["version"],
                    "model_build_id": ready["id"],
                },
            )
            assert model_only.status_code == 201
            assert "export" not in model_only.json()["content"]["model"]
            frozen = client.post(
                f"/api/cases/{case['id']}/reports/freeze",
                headers=analyst,
                json={
                    "thesis_version": thesis["version"],
                    "recommendation_version": recommendations["version"],
                    "model_build_id": ready["id"],
                    "include_model_export": True,
                },
            )
            assert frozen.status_code == 201
            report = frozen.json()
            assert report["content"]["model"]["build_id"] == ready["id"]
            assert report["content"]["model"]["export"]["sha256"] == checksum
            approved = client.post(
                f"/api/cases/{case['id']}/reports/approve",
                headers={"x-forwarded-user": "analyst", "x-caos-role": "APPROVER"},
                json={
                    "preview_digest": report["preview_digest"],
                    "input_fingerprint": report["input_fingerprint"],
                },
            )
            assert approved.status_code == 200

            export_path.write_bytes(b"tampered")
            tampered = client.get(
                f"/api/cases/{case['id']}/models/{ready['id']}/download",
                headers=analyst,
            )
            assert tampered.status_code == 409
            assert tampered.json()["detail"] == "MODEL_EXPORT_INTEGRITY_FAILED"
    finally:
        workflow.close()


def test_full_credit_fake_provider_run_is_accepted_with_canonical_model_inputs() -> (
    None
):
    provider = _CanonicalProvider()
    ledgers, runtime, case = _canonical_runtime_case(provider)
    try:
        run = runtime.start_run(case["id"], "analyst", "FULL_CREDIT", "full", [])
        runtime._execute(run["id"], "analyst")

        completed = ledgers.runs.get_run(run["id"])
        assert completed is not None and completed["status"] == "succeeded", (
            completed and completed.get("error")
        )
        assert completed["canonical_generation"]["phase"] == "complete"
        assert completed["canonical_generation"]["completed_modules"] == sorted(
            FIXTURE_BY_MODULE
        )
        assert {
            json.loads(str(request.messages[0]["content"]).split("\n", 1)[1])[
                "host_identity"
            ]["module_id"]
            for request in provider.calls
        } == set(FIXTURE_BY_MODULE)
        snapshot = runtime.accept_run(case["id"], run["id"], "analyst")
        assert snapshot["run_id"] == run["id"]
        assert {item["module_id"] for item in snapshot["artifacts"]} >= set(
            FIXTURE_BY_MODULE
        )
    finally:
        runtime.close()


def test_canonical_provider_failure_uses_bounded_run_error() -> None:
    ledgers, runtime, case = _canonical_runtime_case(
        _CanonicalProvider(RuntimeError("provider-secret-body"))
    )
    try:
        run = runtime.start_run(case["id"], "analyst", "FULL_CREDIT", "full", [])
        runtime._execute(run["id"], "analyst")

        failed = ledgers.runs.get_run(run["id"])
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
    ledgers = MemoryLedgerSet()
    case = ledgers.runs.create_case("Dispatcher", "Issuer", "Testing", "analyst")
    plan = {"nodes": [{"module_id": "CP-1", "dependencies": [], "stage": 1}]}
    initial: dict[str, object] = {"status": "queued"}
    if canonical:
        initial["canonical_generation"] = {"phase": "generating"}
    run = ledgers.runs.create_run_with_nodes(
        case["id"], "analyst", plan, plan["nodes"], initial=initial
    )
    runtime = WorkflowRuntime(
        ledgers.runs,
        ledgers.sources,
        DeployVBundle(DEPLOY_V),
        Settings(
            environment="production",
            storage_dir=Path("/tmp/caos-dispatcher"),
            deploy_v_root=DEPLOY_V,
        ),
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
        failed = ledgers.runs.get_run(run["id"])
        assert failed is not None and failed["status"] == "failed"
        assert failed["error"]["code"] == expected_code
    finally:
        runtime.close()
