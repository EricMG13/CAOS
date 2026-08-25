from __future__ import annotations

import copy
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import digest


class JobFencedError(RuntimeError):
    """Raised when a worker tries to write after its lease has expired."""


MAX_ACTIVE_JOBS = 20
MODEL_JOB_KINDS = {"calculate", "export"}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _remaining_finalization_seconds(deadline: float | None) -> float | None:
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("finalization deadline exceeded")
    return remaining


def _model_job_key(build_id: str, kind: str) -> str:
    if kind not in MODEL_JOB_KINDS:
        raise ValueError("MODEL_JOB_KIND_INVALID")
    return f"{build_id}:{kind}"


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _finite_number(value: Any) -> bool:
    try:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    except OverflowError:
        return False


def _sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validated_model_result(
    build: dict[str, Any], result: dict[str, Any], kind: str
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("MODEL_RESULT_INVALID")
    if kind == "calculate":
        if set(result) != {"payload", "payload_digest", "qa"}:
            raise ValueError("MODEL_RESULT_INVALID")
        payload, qa = result["payload"], result["qa"]
        identity = payload.get("identity") if isinstance(payload, dict) else None
        tabs = payload.get("tabs") if isinstance(payload, dict) else None
        if (
            not isinstance(payload, dict)
            or set(payload) != {"schema_version", "identity", "tabs"}
            or payload.get("schema_version") != build.get("worksheet_schema_version")
            or not isinstance(identity, dict)
            or set(identity) != {"issuer_id", "issuer_name", "analysis_date"}
            or any(not isinstance(value, str) or not value for value in identity.values())
            or not isinstance(tabs, list)
            or not tabs
            or not isinstance(qa, dict)
        ):
            raise ValueError("MODEL_RESULT_INVALID")
        tab_keys = {
            "id", "name", "max_row", "max_column", "freeze_panes",
            "merged_cells", "columns", "cells",
        }
        if any(
            not isinstance(tab, dict)
            or set(tab) != tab_keys
            or not isinstance(tab["id"], str)
            or not tab["id"]
            or not isinstance(tab["name"], str)
            or not tab["name"]
            or not _nonnegative_int(tab["max_row"])
            or tab["max_row"] < 1
            or not _nonnegative_int(tab["max_column"])
            or tab["max_column"] < 1
            or not isinstance(tab["freeze_panes"], str)
            or not isinstance(tab["merged_cells"], list)
            or not isinstance(tab["columns"], list)
            or not isinstance(tab["cells"], list)
            for tab in tabs
        ):
            raise ValueError("MODEL_RESULT_INVALID")
        column_keys = {"column", "letter", "width", "hidden"}
        cell_keys = {
            "address", "row", "column", "value", "value_type", "formula",
            "semantic_id", "owner", "write_class", "period_id", "source_refs",
            "number_format", "style",
        }
        style_keys = {"bold", "italic", "fill", "align", "wrap"}
        formula_count = 0
        for tab in tabs:
            columns = tab["columns"]
            cells = tab["cells"]
            if (
                any(not isinstance(item, str) or not item for item in tab["merged_cells"])
                or len(columns) != tab["max_column"]
                or any(
                    not isinstance(column, dict)
                    or set(column) != column_keys
                    or not _nonnegative_int(column["column"])
                    or column["column"] < 1
                    or column["column"] > tab["max_column"]
                    or not isinstance(column["letter"], str)
                    or not column["letter"]
                    or column["width"] is not None
                    and (not _finite_number(column["width"]) or column["width"] <= 0)
                    or not isinstance(column["hidden"], bool)
                    for column in columns
                )
                or {column["column"] for column in columns}
                != set(range(1, tab["max_column"] + 1))
            ):
                raise ValueError("MODEL_RESULT_INVALID")
            positions: set[tuple[int, int]] = set()
            addresses: set[str] = set()
            for cell in cells:
                if not isinstance(cell, dict) or set(cell) != cell_keys:
                    raise ValueError("MODEL_RESULT_INVALID")
                style = cell["style"]
                value = cell["value"]
                value_type = cell["value_type"]
                formula = cell["formula"]
                optional_strings = (
                    cell["semantic_id"], cell["owner"], cell["write_class"],
                    cell["period_id"], cell["source_refs"],
                )
                if (
                    not isinstance(cell["address"], str)
                    or not cell["address"]
                    or not _nonnegative_int(cell["row"])
                    or not 1 <= cell["row"] <= tab["max_row"]
                    or not _nonnegative_int(cell["column"])
                    or not 1 <= cell["column"] <= tab["max_column"]
                    or not (
                        value is None
                        or isinstance(value, (str, bool))
                        or _finite_number(value)
                    )
                    or value_type not in {"formula", "boolean", "number", "date", "text"}
                    or (value_type == "formula") != (
                        isinstance(formula, str) and formula.startswith("=")
                    )
                    or any(item is not None and not isinstance(item, str) for item in optional_strings)
                    or not isinstance(cell["number_format"], str)
                    or not isinstance(style, dict)
                    or set(style) != style_keys
                    or not isinstance(style["bold"], bool)
                    or not isinstance(style["italic"], bool)
                    or style["fill"] is not None and not isinstance(style["fill"], str)
                    or style["align"] is not None and not isinstance(style["align"], str)
                    or not isinstance(style["wrap"], bool)
                ):
                    raise ValueError("MODEL_RESULT_INVALID")
                position = (cell["row"], cell["column"])
                if position in positions or cell["address"] in addresses:
                    raise ValueError("MODEL_RESULT_INVALID")
                positions.add(position)
                addresses.add(cell["address"])
                formula_count += value_type == "formula"
        if len({tab["id"] for tab in tabs}) != len(tabs):
            raise ValueError("MODEL_RESULT_INVALID")
        qa_keys = {
            "status", "semantic_checks", "semantic_check_count", "formula_count",
            "worksheet_cell_count", "limitation_flags", "validation_warnings",
            "source_manifest",
        }
        cell_count = sum(len(tab["cells"]) for tab in tabs)
        check_keys = {
            "check_id", "status", "period_id", "difference", "tolerance", "detail",
        }
        manifest_keys = {"module_id", "filename", "sha256"}
        if (
            set(qa) != qa_keys
            or qa["status"] != "PASS"
            or not isinstance(qa["semantic_checks"], list)
            or any(
                not isinstance(check, dict)
                or set(check) != check_keys
                or any(
                    not isinstance(check[field], str) or not check[field]
                    for field in ("check_id", "status", "period_id", "detail")
                )
                or not _finite_number(check["difference"])
                or not _finite_number(check["tolerance"])
                for check in qa["semantic_checks"]
            )
            or not _nonnegative_int(qa["semantic_check_count"])
            or qa["semantic_check_count"] != len(qa["semantic_checks"])
            or not _nonnegative_int(qa["formula_count"])
            or qa["formula_count"] != formula_count
            or not _nonnegative_int(qa["worksheet_cell_count"])
            or qa["worksheet_cell_count"] != cell_count
            or not isinstance(qa["limitation_flags"], list)
            or any(not isinstance(item, str) for item in qa["limitation_flags"])
            or not isinstance(qa["validation_warnings"], list)
            or any(not isinstance(item, str) for item in qa["validation_warnings"])
            or not isinstance(qa["source_manifest"], list)
            or any(
                not isinstance(item, dict)
                or set(item) != manifest_keys
                or not isinstance(item["module_id"], str)
                or not item["module_id"]
                or not isinstance(item["filename"], str)
                or not item["filename"]
                or not _sha256_hex(item["sha256"])
                for item in qa["source_manifest"]
            )
        ):
            raise ValueError("MODEL_RESULT_INVALID")
        try:
            payload_matches = result["payload_digest"] == digest(payload)
        except (TypeError, ValueError):
            payload_matches = False
        if not payload_matches:
            raise ValueError("MODEL_RESULT_INVALID")
        return copy.deepcopy(result)

    export_keys = {
        "vault_key", "filename", "sha256", "size", "formulas_validated",
        "semantic_checks", "renderer_version", "renderer_sha256",
        "calculation_engine",
    }
    if set(result) != export_keys:
        raise ValueError("MODEL_RESULT_INVALID")
    path = Path(result["vault_key"]) if isinstance(result["vault_key"], str) else Path()
    sha256 = result["sha256"]
    renderer_sha256 = result["renderer_sha256"]
    if (
        len(path.parts) != 4
        or path.parts[0] != "models"
        or any(part in {"", ".", ".."} for part in path.parts)
        or not _sha256_hex(sha256)
        or path.name != f"{sha256}.xlsx"
        or not isinstance(result["filename"], str)
        or not result["filename"]
        or not _nonnegative_int(result["size"])
        or result["size"] < 1
        or not _nonnegative_int(result["formulas_validated"])
        or not _nonnegative_int(result["semantic_checks"])
        or not isinstance(result["renderer_version"], str)
        or not result["renderer_version"]
        or not _sha256_hex(renderer_sha256)
        or not isinstance(result["calculation_engine"], str)
        or not result["calculation_engine"]
    ):
        raise ValueError("MODEL_RESULT_INVALID")
    return copy.deepcopy(result)
