def build_scorecard(cp1c_rt: dict) -> Optional[dict]:
    """Composite percentile + recommendation from CP-1C comparisons, or None when
    there are no scored peer metrics."""
    comps = cp1c_rt.get("comparisons") or []
    # Single pass: build the scorecard rows and accumulate the percentile sum
    # together instead of iterating `scored` three times (filter+sum, comprehension,
    # len). Equivalent result; only filtered rows (numeric percentile) contribute.
    scorecard = []
    total = 0.0
    for c in comps:
        pct = c.get("percentile")
        if not isinstance(pct, (int, float)):
            continue
        total += pct
        scorecard.append({
            "metric": c.get("metric"), "label": c.get("label"), "percentile": pct,
            "issuer_value": c.get("issuer_value"), "peer_median": c.get("peer_median"),
        })
    n = len(scorecard)
    if not n:
        return None
    composite = round(total / n)
    rec = ("OVERWEIGHT" if composite >= _OVERWEIGHT
           else "UNDERWEIGHT" if composite < _UNDERWEIGHT else "NEUTRAL")
    return {
        "scorecard": scorecard, "composite_percentile": composite,
        "recommendation": rec, "metrics_scored": n,
        "peer_scope": cp1c_rt.get("peer_scope", "peers"),
    }
