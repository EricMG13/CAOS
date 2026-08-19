def _scored(cp1c_rt: dict) -> list[dict]:
    """The CP-1C comparisons carrying a numeric percentile, in source order.

    Pure and deterministic: filters on the percentile type only (a bool is an
    int, so `True`/`False` are kept and treated as 1/0 downstream, matching the
    `round(mean)` contract). Returns [] when nothing scores, which the public
    function maps to None."""
    comps = cp1c_rt.get("comparisons") or []
    return [c for c in comps if isinstance(c.get("percentile"), (int, float))]


def _composite(scored: list[dict]) -> int:
    """Mean of the scored percentiles, rounded to the nearest int.

    Pure. `round` with no ndigits returns an int and uses banker's (half-even)
    rounding: 58.5 -> 58, 59.5 -> 60. Caller guarantees `scored` is non-empty,
    so there is no zero-division."""
    return round(sum(c["percentile"] for c in scored) / len(scored))


def _recommend(composite: float) -> str:
    """Map a composite percentile to a relative-value lean.

    Pure band map: >= 60 OVERWEIGHT, < 40 UNDERWEIGHT, else NEUTRAL. The
    boundaries are inclusive-low / exclusive-high exactly: 60 -> OVERWEIGHT,
    40 -> NEUTRAL, 39 -> UNDERWEIGHT."""
    if composite >= _OVERWEIGHT:
        return "OVERWEIGHT"
    if composite < _UNDERWEIGHT:
        return "UNDERWEIGHT"
    return "NEUTRAL"


def build_scorecard(cp1c_rt: dict) -> Optional[dict]:
    """Composite percentile + recommendation from CP-1C comparisons, or None when
    there are no scored peer metrics.

    Composes three pure helpers — `_scored` (extract), `_composite` (mean->int),
    `_recommend` (band map) — so each decision is independently exercisable."""
    scored = _scored(cp1c_rt)
    if not scored:
        return None
    composite = _composite(scored)
    scorecard = [{
        "metric": c.get("metric"), "label": c.get("label"), "percentile": c["percentile"],
        "issuer_value": c.get("issuer_value"), "peer_median": c.get("peer_median"),
    } for c in scored]
    return {
        "scorecard": scorecard, "composite_percentile": composite,
        "recommendation": _recommend(composite), "metrics_scored": len(scored),
        "peer_scope": cp1c_rt.get("peer_scope", "peers"),
    }
