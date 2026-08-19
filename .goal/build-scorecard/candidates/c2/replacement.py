def build_scorecard(cp1c_rt: dict) -> Optional[dict]:
    """Composite percentile + recommendation from CP-1C comparisons, or None when
    there are no scored peer metrics."""
    # Keep only comparisons that carry a numeric peer percentile; everything
    # else (missing key, "n/a" strings) can't contribute to the composite.
    # NB: bool is a subclass of int, so True/False count as 1/0 here by design.
    comparisons = cp1c_rt.get("comparisons") or []
    scored = [c for c in comparisons if isinstance(c.get("percentile"), (int, float))]
    if not scored:
        return None

    # Composite = mean of the per-metric percentiles, rounded to a whole number.
    # round() with no ndigits returns an int and uses banker's rounding, which is
    # load-bearing on the band boundary (e.g. 58.5 -> 58, 59.5 -> 60). Do not add
    # ndigits or swap in a different rounding rule.
    composite_percentile = round(sum(c["percentile"] for c in scored) / len(scored))

    # Map the composite onto the relative-value lean. Bands are half-open:
    # >= 60 OVERWEIGHT, < 40 UNDERWEIGHT, the 40-59 middle is NEUTRAL
    # (so exactly 60 -> OVERWEIGHT and exactly 40 -> NEUTRAL).
    if composite_percentile >= _OVERWEIGHT:
        recommendation = "OVERWEIGHT"
    elif composite_percentile < _UNDERWEIGHT:
        recommendation = "UNDERWEIGHT"
    else:
        recommendation = "NEUTRAL"

    # One scorecard row per scored metric. Preserve the percentile's original
    # value and type; the descriptive fields are optional and default to None.
    scorecard = [
        {
            "metric": c.get("metric"),
            "label": c.get("label"),
            "percentile": c["percentile"],
            "issuer_value": c.get("issuer_value"),
            "peer_median": c.get("peer_median"),
        }
        for c in scored
    ]

    return {
        "scorecard": scorecard,
        "composite_percentile": composite_percentile,
        "recommendation": recommendation,
        "metrics_scored": len(scored),
        "peer_scope": cp1c_rt.get("peer_scope", "peers"),
    }
