from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any


class ModelInputError(ValueError):
    pass


_T5_HEADERS = {
    "T5.1": (
        "event_id",
        "source_document",
        "event_description",
        "event_category",
        "date_range",
        "evidence_quality",
        "source_reliability",
    ),
    "T5.2": (
        "date_window",
        "event_description",
        "event_category",
        "credit_relevance_summary",
        "source",
    ),
    "T5.3": (
        "event_id",
        "description",
        "probability",
        "credit_impact_channel_s",
        "impact_severity",
        "affected_metrics",
        "risk_direction",
        "source",
    ),
    "T5.4": ("event_id", "description", "probability", "impact", "p_i_classification"),
    "T5.5": (
        "event_id",
        "description",
        "priority",
        "monitoring_frequency",
        "trigger_condition",
        "responsible_module",
    ),
    "T5.6": (
        "event_id",
        "description",
        "priority",
        "receiving_module",
        "handoff_content",
        "timing",
        "rationale",
    ),
    "T5.7": (
        "gap_description",
        "affected_section",
        "downstream_impact",
        "severity",
        "recommended_action",
    ),
}
_T5_HEADING = re.compile(r"^###\s+(T5\.[1-7])\b.*$", re.MULTILINE)
_ANALYSIS_HEADING = re.compile(r"^## Analysis\s*$", re.MULTILINE)
_EVIDENCE_HEADING = re.compile(r"^## Evidence Trace\s*$", re.MULTILINE)
_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_LOAD_LOCK = threading.Lock()
_MISSING = object()


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _table_headers(block: str, table_id: str) -> tuple[str, ...]:
    lines = block.splitlines()
    for index in range(len(lines) - 2):
        if not lines[index].lstrip().startswith("|") or not lines[
            index + 1
        ].lstrip().startswith("|"):
            continue
        headers = tuple(
            _normalise_header(cell)
            for cell in lines[index].strip().strip("|").split("|")
        )
        separator = tuple(
            cell.strip().replace(" ", "")
            for cell in lines[index + 1].strip().strip("|").split("|")
        )
        if len(headers) == len(separator) and all(
            _SEPARATOR.fullmatch(cell) for cell in separator
        ):
            row_count = 0
            for row in lines[index + 2 :]:
                if not row.lstrip().startswith("|"):
                    break
                values = row.strip().strip("|").split("|")
                if len(values) != len(headers):
                    raise ModelInputError(
                        f"{table_id} row has {len(values)} cells; expected {len(headers)}"
                    )
                if all(_SEPARATOR.fullmatch(cell.strip()) for cell in values):
                    raise ModelInputError(
                        f"{table_id} contains a separator instead of data"
                    )
                row_count += 1
            if not row_count:
                raise ModelInputError(f"{table_id} must contain at least one row")
            return headers
    raise ModelInputError(f"{table_id} is missing its Markdown table")


def _t5_sections(markdown: str) -> list[str]:
    analysis_headings = list(_ANALYSIS_HEADING.finditer(markdown))
    evidence_headings = list(_EVIDENCE_HEADING.finditer(markdown))
    if (
        len(analysis_headings) != 1
        or len(evidence_headings) != 1
        or analysis_headings[0].end() >= evidence_headings[0].start()
    ):
        raise ModelInputError("CP-2A must contain one ordered Analysis section")
    analysis = markdown[analysis_headings[0].end() : evidence_headings[0].start()]
    matches = list(_T5_HEADING.finditer(analysis))
    observed = [match.group(1) for match in matches]
    expected = list(_T5_HEADERS)
    if observed != expected:
        raise ModelInputError(
            f"CP-2A must contain T5.1 through T5.7 exactly once in order; found {observed}"
        )
    sections: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(analysis)
        section = analysis[match.start() : end]
        table_id = match.group(1)
        headers = _table_headers(section, table_id)
        if headers != _T5_HEADERS[table_id]:
            raise ModelInputError(
                f"{table_id} headers do not match the canonical CP-2B schema"
            )
        sections.append(section)
    return sections


def _load_module(
    name: str, path: Path, aliases: dict[str, ModuleType] | None = None
) -> ModuleType:
    module_name = (
        f"caos_deploy_v_{name}_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
    )
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ModelInputError(f"cannot load CP-MODEL authority script: {name}")
    module = importlib.util.module_from_spec(spec)
    prior = {alias: sys.modules.get(alias, _MISSING) for alias in aliases or {}}
    prior_dont_write_bytecode = sys.dont_write_bytecode
    sys.modules[module_name] = module
    try:
        sys.modules.update(aliases or {})
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    finally:
        sys.dont_write_bytecode = prior_dont_write_bytecode
        for alias, previous in prior.items():
            if previous is _MISSING:
                sys.modules.pop(alias, None)
            else:
                sys.modules[alias] = previous
    return module


class CpModelBundle:
    """Load the integrity-pinned CP-MODEL validators without a permanent sys.path edit."""

    def __init__(self, deploy_v_root: Path) -> None:
        self.deploy_v_root = deploy_v_root.resolve()
        scripts = self.deploy_v_root / "skills" / "cp-model" / "scripts"
        with _LOAD_LOCK:
            self._handoff = _load_module(
                "cp_model_validate_handoff", scripts / "validate_handoff.py"
            )
            self._inputs = _load_module(
                "cp_model_validate_inputs",
                scripts / "validate_cp_model_inputs.py",
                {"validate_handoff": self._handoff},
            )
            package = _load_module(
                "cp_model_v3",
                scripts / "cp_model_v3" / "__init__.py",
                {
                    "validate_handoff": self._handoff,
                    "validate_cp_model_inputs": self._inputs,
                },
            )
            self._domain = sys.modules[f"{package.__name__}.domain"]
            self._calculations = sys.modules[f"{package.__name__}.calculations"]
            self._workbook = sys.modules[f"{package.__name__}.workbook"]
            self._builder = sys.modules[f"{package.__name__}.builder"]
        runtime_hash = hashlib.sha256()
        for path in (
            scripts / "cp_model_v3" / "domain.py",
            scripts / "cp_model_v3" / "calculations.py",
            scripts / "cp_model_v3" / "workbook.py",
            scripts / "validate_cp_model_inputs.py",
            scripts / "validate_handoff.py",
        ):
            runtime_hash.update(path.name.encode("utf-8"))
            runtime_hash.update(path.read_bytes())
        self.calculation_runtime = {
            "name": "cp_model_v3_python",
            "version": self._domain.V3_CONTRACT_VERSION,
            "sha256": runtime_hash.hexdigest(),
            "assumption_registry_version": self._inputs.ASSUMPTION_REGISTRY_VERSION,
            "assumption_registry_digest": self._inputs.ASSUMPTION_REGISTRY_DIGEST,
            "calculation_contract_version": self._calculations.CALCULATION_CONTRACT_VERSION,
        }
        self.assumption_registry = self._inputs.assumption_registry()

    def validate_handoff(
        self, markdown: str, *, module_id: str, run_id: str | None = None
    ) -> Any:
        return self._handoff.validate_text(
            markdown, expected_module=module_id, expected_run_id=run_id
        )

    def validate(
        self,
        cp1: str,
        cp1a: str,
        cp1b: str,
        cp2: str,
        cp2b: str,
        cp2g: str | None = None,
    ) -> Any:
        return self._inputs.validate_cp_model_bundle(cp1, cp1a, cp1b, cp2, cp2b, cp2g)

    def calculate(
        self,
        paths: dict[str, Path],
        *,
        effective_assumptions: list[dict[str, Any]] | None = None,
    ) -> tuple[Any, Any]:
        bundle_paths = self._domain.BundlePaths(
            cp1=paths["CP-1"],
            cp1a=paths["CP-1A"],
            cp1b=paths["CP-1B"],
            cp2=paths["CP-2"],
            cp2b=paths["CP-2B"],
            cp2g=paths.get("CP-2G"),
        )
        model = self._domain.build_ir(
            bundle_paths, effective_assumptions=effective_assumptions
        )
        return model, self._calculations.calculate(model)

    def render_workbook(
        self, model: Any, calculations: Any, output_path: Path
    ) -> Any:
        return self._workbook.render_workbook(
            model,
            calculations,
            self._workbook.RenderMetadata(
                renderer_hash=self.calculation_runtime["sha256"],
                calculation_engine="CP-MODEL Python calculations",
            ),
            output_path,
        )

    def export(self, paths: dict[str, Path], output_dir: Path) -> Any:
        return self._builder.build_cp_model(
            self._builder.BuildRequest(
                bundle=self._domain.BundlePaths(
                    cp1=paths["CP-1"],
                    cp1a=paths["CP-1A"],
                    cp1b=paths["CP-1B"],
                    cp2=paths["CP-2"],
                    cp2b=paths["CP-2B"],
                    cp2g=paths.get("CP-2G"),
                ),
                output_dir=output_dir,
            )
        )

    def export_revision(
        self,
        paths: dict[str, Path],
        output_dir: Path,
        *,
        effective_assumptions: list[dict[str, Any]],
        default_assumptions: list[dict[str, Any]],
        revision: dict[str, Any],
    ) -> Any:
        return self._builder.build_cp_model(
            self._builder.BuildRequest(
                bundle=self._domain.BundlePaths(
                    cp1=paths["CP-1"],
                    cp1a=paths["CP-1A"],
                    cp1b=paths["CP-1B"],
                    cp2=paths["CP-2"],
                    cp2b=paths["CP-2B"],
                    cp2g=paths.get("CP-2G"),
                ),
                output_dir=output_dir,
                effective_assumptions=effective_assumptions,
                revision=self._workbook.RevisionRenderContext(
                    assumptions=effective_assumptions,
                    defaults=default_assumptions,
                    definitions=self.assumption_registry["definitions"],
                    record=revision,
                ),
            )
        )


def project_cp2b(
    cp2a_markdown: str,
    *,
    run_id: str,
    cp2a_artifact_digest: str,
    bundle: CpModelBundle,
) -> str:
    if not _HEX_DIGEST.fullmatch(cp2a_artifact_digest):
        raise ModelInputError(
            "CP-2A artifact digest must be 64 lowercase hex characters"
        )
    validation = bundle.validate_handoff(
        cp2a_markdown, module_id="CP-2A", run_id=run_id
    )
    if validation.errors or validation.identity_mismatches or validation.fields is None:
        raise ModelInputError("CP-2A canonical handoff is invalid")
    fields = validation.fields
    if fields.get("qa_status") != "Passed" or "CP-MODEL" not in fields.get(
        "downstream_consumers", []
    ):
        raise ModelInputError("CP-2A is not ready for CP-MODEL")
    sections = _t5_sections(cp2a_markdown)

    def quoted(value: object) -> str:
        return json.dumps(str(value), ensure_ascii=True)

    projected = "\n".join(
        [
            "---",
            "module_id: CP-2B",
            'module_name: "Catalyst and Event-Risk Projection"',
            f"run_id: {quoted(run_id)}",
            f"reporting_period: {quoted(fields['reporting_period'])}",
            f"analysis_date: {quoted(fields['analysis_date'])}",
            f"confidence_score: {fields['confidence_score']}",
            f"confidence_band: {quoted(fields['confidence_band'])}",
            "qa_status: Passed",
            f"committee_status: {quoted(fields['committee_status'])}",
            f"limitation_flags: {json.dumps(fields['limitation_flags'])}",
            f"validation_warnings: {json.dumps(fields['validation_warnings'])}",
            "upstream_artifacts_used:",
            "  - module_id: CP-2A",
            f"    run_id: {quoted(run_id)}",
            f"    period: {quoted(fields['reporting_period'])}",
            f"    artifact_digest: {quoted(cp2a_artifact_digest)}",
            "downstream_consumers: [CP-MODEL]",
            f"issuer_name: {quoted(fields['issuer_name'])}",
            f"issuer_id: {quoted(fields['issuer_id'])}",
            "---",
            "",
            "## Audit Summary",
            "",
            f"Host projection of CP-2A artifact `{cp2a_artifact_digest}`; no rows were inferred or repaired.",
            "",
            "## Analysis",
            "",
            "".join(sections),
            "",
            "## Evidence Trace",
            "",
            "All evidence rows and source locators are preserved verbatim from the accepted CP-2A handoff.",
            "",
            "## Source Registry",
            "",
            "See T5.1 and the preserved source columns in the analytical registers.",
            "",
            "## Gaps & Conflicts",
            "",
            "See T5.7; this projection adds no gap resolution.",
            "",
            "## QA Validation",
            "",
            "The host verified the complete T5.1-T5.7 register sequence and canonical table headers.",
            "",
        ]
    )
    projected_validation = bundle.validate_handoff(
        projected, module_id="CP-2B", run_id=run_id
    )
    if projected_validation.errors or projected_validation.identity_mismatches:
        raise ModelInputError("projected CP-2B canonical handoff is invalid")
    return projected
