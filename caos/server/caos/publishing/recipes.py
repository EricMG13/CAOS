from __future__ import annotations

from typing import Any


ALLOWED_KINDS = {"trend", "variance_bridge", "scenario_path", "rv_scatter", "debt_stack", "maturity_wall", "covenant_headroom", "recovery_waterfall", "risk_horizon", "dag"}
ALLOWED_UNITS = {"", "%", "USD", "USD m", "bps", "x", "governed source units"}
ALLOWED_POLARITIES = {"", "higher_is_better", "higher_is_worse", "neutral"}
FORBIDDEN_TOKENS = ("javascript", "<script", "</", "sql", "eval(", "http://", "https://", "url", "expression")


def validate_recipe(recipe: dict[str, Any], known_fields: set[str]) -> dict[str, Any]:
    if not isinstance(recipe, dict) or recipe.get("kind") not in ALLOWED_KINDS:
        raise ValueError("unknown visual kind")
    allowed_keys = {"kind", "schema_version", "fields", "units", "metric_ids", "polarity", "accessible_table"}
    if set(recipe) - allowed_keys:
        raise ValueError("recipe contains an unknown field")
    if recipe.get("schema_version") != "1.0" or recipe.get("accessible_table") is not True:
        raise ValueError("recipe must declare schema version and accessible table equivalence")
    fields = recipe.get("fields", [])
    if not isinstance(fields, list) or not fields or any(field not in known_fields for field in fields):
        raise ValueError("recipe field is not schema-known")
    units = recipe.get("units", "")
    polarity = recipe.get("polarity", "")
    metric_ids = recipe.get("metric_ids", [])
    if units not in ALLOWED_UNITS or polarity not in ALLOWED_POLARITIES or not isinstance(metric_ids, list) or len(metric_ids) > 20 or any(not isinstance(metric_id, str) or len(metric_id) > 120 for metric_id in metric_ids):
        raise ValueError("recipe units, polarity or metrics are not governed")
    serialized = repr(recipe).lower()
    if any(token in serialized for token in FORBIDDEN_TOKENS):
        raise ValueError("recipe contains executable or remote content")
    if len(fields) > 20 or len(serialized) > 8000:
        raise ValueError("recipe exceeds bounded visual grammar")
    return {"kind": recipe["kind"], "schema_version": "1.0", "fields": fields, "units": units, "metric_ids": metric_ids, "polarity": polarity, "accessible_table": True}
