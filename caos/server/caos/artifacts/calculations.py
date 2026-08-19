from __future__ import annotations

import math


def is_finite_number(value: object) -> bool:
    if not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def safe_ratio(numerator: object, denominator: object) -> float | None:
    if not is_finite_number(numerator) or not is_finite_number(denominator) or float(denominator) == 0:
        return None
    return float(numerator) / float(denominator)


def leverage(net_debt: object, ebitda: object) -> float | None:
    return safe_ratio(net_debt, ebitda)


def variance_bridge(actual: object, prior: object) -> dict[str, float | None]:
    if not is_finite_number(actual) or not is_finite_number(prior):
        return {"actual": None, "prior": None, "delta": None, "delta_pct": None}
    delta = float(actual) - float(prior)
    return {"actual": float(actual), "prior": float(prior), "delta": delta, "delta_pct": safe_ratio(delta, prior)}
