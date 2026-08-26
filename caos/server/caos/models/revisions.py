"""Append-only Analyst Model Revisions and transient CP-MODEL calculations."""

from __future__ import annotations

import copy
import tempfile
import threading
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..contracts import digest
from ..ledgers import ModelLedger
from ..store import JobFencedError
from ..workflows.domain import HEARTBEAT_INTERVAL_SECONDS, _LeaseFence
from .domain import CpModelBundle, ModelInputError
from .runtime import (
    ModelBuildRuntime,
    ModelReadinessService,
    WORKSHEET_SCHEMA_VERSION,
    _publish_export,
)


Record = dict[str, Any]
MAX_EFFECTIVE_ASSUMPTIONS = 256
MAX_SENSITIVITY_POINTS = 41
MAX_CALCULATION_SECONDS = 30.0


class ModelCalculationTimeout(ValueError):
    def __init__(self) -> None:
        super().__init__("MODEL_CALCULATION_TIMEOUT")


class ModelRevisionRuntimeUnavailable(ModelInputError):
    code = "MODEL_REVISION_EXPORT_RUNTIME_UNAVAILABLE"
    detail = "The signed revision's pinned calculation runtime is unavailable."


def _request_deadline() -> float:
    return time.monotonic() + MAX_CALCULATION_SECONDS


def _remaining_calculation_time(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ModelCalculationTimeout()
    return remaining


def _json_number(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ModelInputError("non-finite model output")
        return format(value, "f")
    raise ModelInputError("unexpected model output type")


def _assumption_rows(model: Any) -> list[Record]:
    rows = [
        {
            "assumption_id": driver.assumption_id,
            "case": driver.case,
            "period_id": driver.period_id,
            "unit": driver.unit,
            "status": driver.status,
            "value": _json_number(driver.value),
            "gap_code": driver.gap_code,
            "default_value": _json_number(driver.value),
            "default_status": driver.status,
            "default_gap_code": driver.gap_code,
            "source_context": {
                "authority_module": "CP-2G",
                "gap_code": driver.gap_code,
                "provenance": [
                    {
                        "source_id": item.source_id,
                        "source_locator": item.source_locator,
                        "as_of": item.as_of,
                    }
                    for item in driver.provenance
                ],
            },
        }
        for driver in model.effective_assumptions
    ]
    for row in rows:
        row["source_context_digest"] = digest(row["source_context"])
    return sorted(
        rows,
        key=lambda row: (row["case"], row["period_id"], row["assumption_id"]),
    )


def _with_default_context(
    effective: list[Record], defaults: list[Record]
) -> list[Record]:
    default_by_key = {
        (row["assumption_id"], row["case"], row["period_id"]): row
        for row in defaults
    }
    if len(default_by_key) != len(defaults):
        raise ValueError("MODEL_ASSUMPTION_DEFAULT_INVALID")
    result = copy.deepcopy(effective)
    for row in result:
        key = (row["assumption_id"], row["case"], row["period_id"])
        default = default_by_key.get(key)
        if default is None:
            raise ValueError("MODEL_ASSUMPTION_DEFAULT_INVALID")
        row.update(
            default_value=default["value"],
            default_status=default["status"],
            default_gap_code=default["gap_code"],
            source_context=copy.deepcopy(default["source_context"]),
            source_context_digest=default["source_context_digest"],
        )
    return result


def _annual_outputs(calculations: Any) -> Record:
    result: Record = {}
    value_ids = (
        "revenue",
        "adjusted_ebitda_calc",
        "fcf",
        "cumulative_fcf",
        "cash_and_equivalents",
        "accessible_liquidity",
        "liquidity_headroom",
        "total_debt_reported",
        "net_debt",
    )
    metric_ids = (
        "adjusted_ebitda_margin",
        "total_leverage",
        "net_leverage",
        "interest_coverage",
        "covenant_headroom",
    )
    for case in ("BASE", "DOWNSIDE"):
        periods: Record = {}
        for column in calculations.columns:
            if column.group != case:
                continue
            calculation = calculations.for_column(column.column_id)
            periods[column.column_id] = {
                **{
                    output_id: _json_number(calculation.values.get(output_id))
                    for output_id in value_ids
                },
                **{
                    output_id: _json_number(
                        calculation.credit_metrics.get(output_id)
                    )
                    for output_id in metric_ids
                },
            }
        result[case] = periods
        result[f"{case}_first_breaches"] = [
            {
                "period_id": breach.period_id,
                "threshold_id": breach.threshold_id,
                "metric_id": breach.metric_id,
                "limit": _json_number(breach.limit),
                "actual": _json_number(breach.actual),
                "headroom": _json_number(breach.headroom),
            }
            for breach in calculations.first_breaches[case]
        ]
    return result


def _output_deltas(baseline: Record, changed: Record) -> Record:
    result: Record = {}
    for case in ("BASE", "DOWNSIDE"):
        result[case] = {}
        for period_id, values in changed.get(case, {}).items():
            base_values = baseline.get(case, {}).get(period_id, {})
            result[case][period_id] = {}
            for output_id, value in values.items():
                base = base_values.get(output_id)
                result[case][period_id][output_id] = (
                    format(Decimal(value) - Decimal(base), "f")
                    if value is not None and base is not None
                    else None
                )
    return result


class ModelRevisionService:
    """One authority boundary for previews, scenarios, sensitivity, and Sign-Off."""

    def __init__(
        self,
        models: ModelLedger,
        readiness: ModelReadinessService,
        model: CpModelBundle,
    ) -> None:
        self.models = models
        self.readiness = readiness
        self.model = model
        self._calculation_slots = threading.BoundedSemaphore(4)

    def _build(self, case_id: str, build_id: str, *, current: bool = True) -> Record:
        build = self.models.get_build(build_id)
        if (
            build is None
            or build.get("case_id") != case_id
            or build.get("status") != "READY"
        ):
            raise ValueError("MODEL_BUILD_NOT_READY")
        if current:
            state = self.readiness.readiness(case_id)
            current_build = state.get("build") or {}
            if current_build.get("id") != build_id or state.get("status") != "READY":
                raise ValueError("MODEL_BUILD_STALE")
        return build

    def _validate_registry(
        self, registry_version: str, registry_digest: str
    ) -> None:
        registry = self.model.assumption_registry
        if (
            registry_version != registry["version"]
            or registry_digest != registry["digest"]
        ):
            raise ValueError("MODEL_REGISTRY_STALE")

    def _calculate(
        self,
        build: Record,
        effective_assumptions: list[Record] | None,
        *,
        deadline: float,
    ) -> tuple[Any, Any, list[Record], Record]:
        if (
            effective_assumptions is not None
            and len(effective_assumptions) > MAX_EFFECTIVE_ASSUMPTIONS
        ):
            raise ValueError("MODEL_ASSUMPTION_LIMIT")
        remaining = _remaining_calculation_time(deadline)
        if not self._calculation_slots.acquire(timeout=min(1.0, remaining)):
            if deadline - time.monotonic() <= 0:
                raise ModelCalculationTimeout()
            raise ValueError("MODEL_CALCULATION_BUSY")
        try:
            _remaining_calculation_time(deadline)
            resolved = self.readiness.inputs_for_build(build)
            with tempfile.TemporaryDirectory(prefix="caos-model-revision-") as temporary:
                paths = ModelBuildRuntime._write_inputs(
                    Path(temporary), resolved["markdown"]
                )
                model, calculations = self.model.calculate(
                    paths, effective_assumptions=effective_assumptions
                )
            _remaining_calculation_time(deadline)
            rows = _assumption_rows(model)
            return model, calculations, rows, _annual_outputs(calculations)
        finally:
            self._calculation_slots.release()

    def assumption_registry(self, case_id: str, build_id: str) -> Record:
        build = self._build(case_id, build_id)
        _model, _calculations, defaults, _outputs = self._calculate(
            build, None, deadline=_request_deadline()
        )
        registry = copy.deepcopy(self.model.assumption_registry)
        return {
            **registry,
            "build_id": build_id,
            "accepted_snapshot_id": build["accepted_snapshot_id"],
            "input_fingerprint": build["input_fingerprint"],
            "defaults": defaults,
        }

    def _parent(self, case_id: str, parent_revision_id: str | None) -> Record | None:
        if parent_revision_id is None:
            return None
        parent = self.models.get_revision(parent_revision_id)
        if parent is None or parent.get("case_id") != case_id:
            raise ValueError("MODEL_REVISION_NOT_FOUND")
        return parent

    def preview(
        self,
        case_id: str,
        build_id: str,
        registry_version: str,
        registry_digest: str,
        assumptions: list[Record],
        *,
        parent_revision_id: str | None,
        draft_generation: int,
        _deadline: float | None = None,
    ) -> Record:
        deadline = _deadline if _deadline is not None else _request_deadline()
        build = self._build(case_id, build_id)
        self._validate_registry(registry_version, registry_digest)
        parent = self._parent(case_id, parent_revision_id)
        if parent is not None and parent.get("build_id") != build_id:
            raise ValueError("MODEL_REVISION_STALE")
        _model, _calculations, normalized, outputs = self._calculate(
            build, copy.deepcopy(assumptions), deadline=deadline
        )
        _baseline_model, _baseline_calculations, _defaults, default_outputs = (
            self._calculate(build, None, deadline=deadline)
        )
        normalized = _with_default_context(normalized, _defaults)
        baseline = parent["outputs"] if parent is not None else default_outputs
        envelope = {
            "case_id": case_id,
            "build_id": build_id,
            "accepted_snapshot_id": build["accepted_snapshot_id"],
            "build_input_fingerprint": build["input_fingerprint"],
            "build_payload_digest": build["payload_digest"],
            "registry_version": registry_version,
            "registry_digest": registry_digest,
            "calculation_contract_version": build["calculation_runtime"][
                "calculation_contract_version"
            ],
            "parent_revision_id": parent_revision_id,
            "draft_generation": draft_generation,
            "effective_assumptions": normalized,
            "assumptions_digest": digest(normalized),
            "outputs": outputs,
            "outputs_digest": digest(outputs),
            "deltas": _output_deltas(baseline, outputs),
        }
        envelope["preview_digest"] = digest(envelope)
        return envelope

    def sign_off(
        self,
        case_id: str,
        build_id: str,
        registry_version: str,
        registry_digest: str,
        assumptions: list[Record],
        *,
        parent_revision_id: str | None,
        expected_head_revision_id: str | None,
        preview_digest: str,
        note: str,
        actor: str,
        draft_generation: int,
    ) -> Record:
        deadline = _request_deadline()
        preview = self.preview(
            case_id,
            build_id,
            registry_version,
            registry_digest,
            assumptions,
            parent_revision_id=parent_revision_id,
            draft_generation=draft_generation,
            _deadline=deadline,
        )
        if preview["preview_digest"] != preview_digest:
            raise ValueError("MODEL_PREVIEW_STALE")
        revision = {
            key: preview[key]
            for key in (
                "case_id",
                "build_id",
                "accepted_snapshot_id",
                "build_input_fingerprint",
                "build_payload_digest",
                "registry_version",
                "registry_digest",
                "calculation_contract_version",
                "effective_assumptions",
                "assumptions_digest",
                "outputs",
                "outputs_digest",
                "preview_digest",
                "parent_revision_id",
            )
        }
        revision["note"] = note
        return self.models.sign_off_revision(
            revision,
            actor,
            expected_head_revision_id,
            expected_current_build_id=build_id,
            expected_current_input_fingerprint=preview["build_input_fingerprint"],
        )

    def list_revisions(self, case_id: str) -> list[Record]:
        current = (self.readiness.readiness(case_id).get("build") or {}).get("id")
        head = self.models.get_revision_head(case_id)
        head_id = head.get("id") if head else None
        return [
            {
                **revision,
                "state": (
                    "STALE"
                    if revision.get("build_id") != current
                    else "ACTIVE"
                    if revision.get("id") == head_id
                    else "SUPERSEDED"
                ),
            }
            for revision in self.models.list_revisions(case_id)
        ]

    def rebase_preview(
        self,
        case_id: str,
        revision_id: str,
        build_id: str,
        *,
        draft_generation: int,
    ) -> Record:
        deadline = _request_deadline()
        source = self._parent(case_id, revision_id)
        if source is None:
            raise ValueError("MODEL_REVISION_NOT_FOUND")
        build = self._build(case_id, build_id)
        _new_model, _new_calculations, new_defaults, _new_outputs = self._calculate(
            build, None, deadline=deadline
        )
        source_by_key = {
            (row["assumption_id"], row["case"], row["period_id"]): row
            for row in source["effective_assumptions"]
        }
        definitions = {
            item["assumption_id"]: item
            for item in self.model.assumption_registry["definitions"]
        }
        candidate = copy.deepcopy(new_defaults)
        compatible: list[Record] = []
        changed: list[Record] = []
        invalidated: list[Record] = []
        candidate_by_key = {
            (row["assumption_id"], row["case"], row["period_id"]): row
            for row in candidate
        }
        for key in sorted(set(source_by_key).difference(candidate_by_key)):
            invalidated.append(
                {"identity": list(key), "reason": "ASSUMPTION_NO_LONGER_MAPS"}
            )
        for row in candidate:
            key = (row["assumption_id"], row["case"], row["period_id"])
            prior = source_by_key.get(key)
            definition = definitions.get(row["assumption_id"])
            invalid_reason = None
            if prior is None:
                invalid_reason = "ASSUMPTION_ADDED"
            elif definition is None:
                invalid_reason = "ASSUMPTION_NO_LONGER_MAPS"
            elif prior["unit"] != row["unit"] or prior["status"] != row["status"]:
                invalid_reason = "ASSUMPTION_METADATA_CHANGED"
            elif not isinstance(prior.get("source_context_digest"), str):
                invalid_reason = "ASSUMPTION_CONTEXT_UNAVAILABLE"
            elif prior["status"] == "READY":
                value = Decimal(str(prior["value"]))
                if value < Decimal(definition["hard_min"]) or value > Decimal(
                    definition["hard_max"]
                ):
                    invalid_reason = "ASSUMPTION_OUTSIDE_NEW_BOUNDS"
            if invalid_reason:
                invalidated.append({"identity": list(key), "reason": invalid_reason})
                continue
            row["value"] = prior["value"]
            row["gap_code"] = prior.get("gap_code", "")
            item = {"identity": list(key), "value": prior["value"]}
            if any(
                prior.get(field) != row.get(field)
                for field in (
                    "default_value",
                    "default_status",
                    "default_gap_code",
                    "source_context_digest",
                )
            ):
                changed.append(item)
            else:
                compatible.append(item)
        preview = None
        if not invalidated:
            preview = self.preview(
                case_id,
                build_id,
                self.model.assumption_registry["version"],
                self.model.assumption_registry["digest"],
                candidate,
                parent_revision_id=None,
                draft_generation=draft_generation,
                _deadline=deadline,
            )
        return {
            "case_id": case_id,
            "source_revision_id": revision_id,
            "source_build_id": source["build_id"],
            "build_id": build_id,
            "draft_generation": draft_generation,
            "compatible": compatible,
            "changed": changed,
            "invalidated": invalidated,
            "candidate_assumptions": candidate,
            "preview": preview,
        }

    def scenario(
        self,
        case_id: str,
        build_id: str,
        registry_version: str,
        registry_digest: str,
        shocks: list[Record],
        *,
        base_revision_id: str | None,
        draft_generation: int,
    ) -> Record:
        deadline = _request_deadline()
        build = self._build(case_id, build_id)
        self._validate_registry(registry_version, registry_digest)
        parent = self._parent(case_id, base_revision_id)
        if parent is not None and parent.get("build_id") != build_id:
            raise ValueError("MODEL_REVISION_STALE")
        _model, _calculations, defaults, default_outputs = self._calculate(
            build, None, deadline=deadline
        )
        baseline_assumptions = copy.deepcopy(
            parent["effective_assumptions"] if parent else defaults
        )
        baseline_outputs = parent["outputs"] if parent else default_outputs
        by_key = {
            (row["assumption_id"], row["case"], row["period_id"]): row
            for row in baseline_assumptions
        }
        if len(shocks) > MAX_EFFECTIVE_ASSUMPTIONS:
            raise ValueError("MODEL_ASSUMPTION_LIMIT")
        seen: set[tuple[str, str, str]] = set()
        for shock in shocks:
            key = (
                shock.get("assumption_id"),
                shock.get("case"),
                shock.get("period_id"),
            )
            if key in seen or key not in by_key or by_key[key]["status"] != "READY":
                raise ValueError("MODEL_SCENARIO_INVALID")
            seen.add(key)
            by_key[key]["value"] = shock.get("value")
        _scenario_model, _scenario_calc, normalized, outputs = self._calculate(
            build, baseline_assumptions, deadline=deadline
        )
        normalized = _with_default_context(normalized, defaults)
        scenario = {
            "case_id": case_id,
            "build_id": build_id,
            "base_revision_id": base_revision_id,
            "registry_version": registry_version,
            "registry_digest": registry_digest,
            "draft_generation": draft_generation,
            "effective_assumptions": normalized,
            "assumptions_digest": digest(normalized),
            "outputs": outputs,
            "outputs_digest": digest(outputs),
            "deltas": _output_deltas(baseline_outputs, outputs),
        }
        return {
            "draft_generation": draft_generation,
            "baseline": baseline_outputs,
            "scenario": scenario,
            "scenario_digest": digest(scenario),
        }

    def one_way(
        self,
        case_id: str,
        build_id: str,
        registry_version: str,
        registry_digest: str,
        assumption_id: str,
        case: str,
        period_scope: str,
        *,
        minimum: float | None,
        maximum: float | None,
        step: float | None,
        output_id: str,
        base_revision_id: str | None,
        draft_generation: int,
    ) -> Record:
        deadline = _request_deadline()
        build = self._build(case_id, build_id)
        self._validate_registry(registry_version, registry_digest)
        parent = self._parent(case_id, base_revision_id)
        if parent is not None and parent.get("build_id") != build_id:
            raise ValueError("MODEL_REVISION_STALE")
        _model, _calculations, defaults, default_outputs = self._calculate(
            build, None, deadline=deadline
        )
        baseline_assumptions = copy.deepcopy(
            parent["effective_assumptions"] if parent else defaults
        )
        baseline_outputs = parent["outputs"] if parent else default_outputs
        definition = next(
            (
                item
                for item in self.model.assumption_registry["definitions"]
                if item["assumption_id"] == assumption_id
            ),
            None,
        )
        selected = [
            row
            for row in baseline_assumptions
            if row["assumption_id"] == assumption_id
            and row["case"] == case
            and (period_scope == "ALL" or row["period_id"] == period_scope)
        ]
        if definition is None or not selected or any(row["status"] != "READY" for row in selected):
            raise ValueError("MODEL_SENSITIVITY_INVALID")
        base_value = Decimal(str(selected[0]["value"]))
        default_range = Decimal(definition["sensitivity_default"]["range"])
        chosen_step = Decimal(str(step)) if step is not None else Decimal(
            definition["sensitivity_default"]["step"]
        )
        lower = Decimal(str(minimum)) if minimum is not None else base_value - default_range
        upper = Decimal(str(maximum)) if maximum is not None else base_value + default_range
        hard_min = Decimal(definition["hard_min"])
        hard_max = Decimal(definition["hard_max"])
        if chosen_step <= 0 or lower > upper or lower < hard_min or upper > hard_max:
            raise ValueError("MODEL_SENSITIVITY_INVALID")
        point_count = int((upper - lower) / chosen_step) + 1
        if point_count > MAX_SENSITIVITY_POINTS or lower + chosen_step * (point_count - 1) != upper:
            raise ValueError("MODEL_SENSITIVITY_POINT_LIMIT")
        points: list[Record] = []
        breakpoint: Record | None = None
        for index in range(point_count):
            value = lower + chosen_step * index
            effective = copy.deepcopy(baseline_assumptions)
            for row in effective:
                if row in selected:
                    row["value"] = format(value, "f")
            _point_model, _point_calc, _normalized, outputs = self._calculate(
                build, effective, deadline=deadline
            )
            point = {
                "value": format(value, "f"),
                "outputs": outputs,
                "deltas": _output_deltas(baseline_outputs, outputs),
            }
            points.append(point)
            breaches = outputs.get(f"{case}_first_breaches", [])
            if breakpoint is None and breaches:
                breakpoint = {
                    "value": point["value"],
                    "threshold": breaches[0],
                }
        return {
            "case_id": case_id,
            "build_id": build_id,
            "base_revision_id": base_revision_id,
            "registry_version": registry_version,
            "registry_digest": registry_digest,
            "assumption_id": assumption_id,
            "case": case,
            "period_scope": period_scope,
            "output_id": output_id,
            "draft_generation": draft_generation,
            "points": points,
            "breakpoint": breakpoint,
        }


class ModelRevisionRuntime:
    """Worker-only exact XLSX publication for immutable signed revisions."""

    def __init__(
        self,
        models: ModelLedger,
        service: ModelRevisionService,
        model: CpModelBundle,
        executor: Any,
        storage_dir: Path,
    ) -> None:
        self.models = models
        self.service = service
        self.model = model
        self.executor = executor
        self.storage_dir = storage_dir

    def schedule_export(self, revision_id: str, actor: str) -> Any:
        return self.executor.submit(self._execute_export, revision_id, actor)

    def _require_pinned_runtime(self, build: Record) -> None:
        if (
            build.get("methodology_build_id")
            != self.service.readiness.methodology.build_id
            or build.get("worksheet_schema_version") != WORKSHEET_SCHEMA_VERSION
            or build.get("calculation_runtime") != self.model.calculation_runtime
        ):
            raise ModelRevisionRuntimeUnavailable()

    def _execute_export(self, revision_id: str, actor: str) -> None:
        token = self.models.claim_revision_export(
            revision_id, threading.current_thread().name
        )
        if token is None:
            return
        heartbeat_stop = threading.Event()
        fence = _LeaseFence()

        def heartbeat() -> None:
            while not heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
                try:
                    if self.models.renew_revision_export(revision_id, token):
                        continue
                except Exception:
                    pass
                fence.lose()
                return

        thread = threading.Thread(
            target=heartbeat,
            name=f"{revision_id}-revision-export-heartbeat",
            daemon=True,
        )
        thread.start()
        published: Path | None = None
        try:
            revision = self.models.get_revision(revision_id)
            if revision is None:
                raise ModelInputError("model revision is unavailable")
            build = self.service._build(
                revision["case_id"], revision["build_id"], current=False
            )
            self._require_pinned_runtime(build)
            resolved = self.service.readiness.inputs_for_build(build)
            _model, _calculations, defaults, _outputs = self.service._calculate(
                build, None, deadline=_request_deadline()
            )
            with tempfile.TemporaryDirectory(
                prefix="caos-model-revision-export-"
            ) as temporary:
                directory = Path(temporary)
                paths = ModelBuildRuntime._write_inputs(
                    directory, resolved["markdown"]
                )
                result = self.model.export_revision(
                    paths,
                    directory,
                    effective_assumptions=revision["effective_assumptions"],
                    default_assumptions=defaults,
                    revision=revision,
                )
                published, vault_key, size = _publish_export(
                    self.storage_dir, revision, result.output, result.sha256
                )
            if fence.lost.is_set() or not self.models.revision_export_is_current(
                revision_id, token
            ):
                raise JobFencedError("lost model revision export lease")
            fence.call(
                self.models.complete_revision_export,
                revision_id,
                token,
                {
                    "vault_key": vault_key,
                    "filename": result.output.name,
                    "sha256": result.sha256,
                    "size": size,
                    "formulas_validated": result.formulas_validated,
                    "semantic_checks": result.semantic_checks,
                    "renderer_version": result.renderer_version,
                    "renderer_sha256": result.renderer_sha256,
                    "calculation_engine": result.calculation_engine,
                },
                actor,
            )
        except JobFencedError:
            if published is not None:
                published.unlink(missing_ok=True)
        except Exception as exc:
            error = (
                {"code": exc.code, "detail": exc.detail}
                if isinstance(exc, ModelRevisionRuntimeUnavailable)
                else {
                    "code": "MODEL_REVISION_EXPORT_FAILED",
                    "detail": "The signed revision XLSX export did not complete.",
                }
            )
            try:
                fence.call(
                    self.models.fail_revision_export,
                    revision_id,
                    token,
                    error,
                    actor,
                )
            except JobFencedError:
                pass
            else:
                if published is not None:
                    published.unlink(missing_ok=True)
        finally:
            heartbeat_stop.set()
            thread.join(timeout=1)
