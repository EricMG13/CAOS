def build_scorecard(cp1c_rt: dict) -> Optional[dict]:
    """Composite percentile + recommendation from CP-1C comparisons, or None when
    there are no scored peer metrics.

    A percentile only scores when it is a *finite* number. ``is_finite_number``
    accepts ``bool``/``int``/``0``/``float`` but rejects ``NaN``/``±inf`` — so a
    poisoned ``NaN`` percentile (which is a ``float`` and would slip past a plain
    ``isinstance`` check, then crash ``round`` with ``ValueError: cannot convert
    float NaN to integer`` and abort the whole CP-3 run) is now treated as
    unscored, exactly like a missing or non-numeric one.
    """
    from engine.periods import is_finite_number

    comps = cp1c_rt.get("comparisons") or []
    scored = [c for c in comps if is_finite_number(c.get("percentile"))]
    if not scored:
        return None
    composite = round(sum(c["percentile"] for c in scored) / len(scored))
    rec = ("OVERWEIGHT" if composite >= _OVERWEIGHT
           else "UNDERWEIGHT" if composite < _UNDERWEIGHT else "NEUTRAL")
    scorecard = [{
        "metric": c.get("metric"), "label": c.get("label"), "percentile": c["percentile"],
        "issuer_value": c.get("issuer_value"), "peer_median": c.get("peer_median"),
    } for c in scored]
    return {
        "scorecard": scorecard, "composite_percentile": composite,
        "recommendation": rec, "metrics_scored": len(scored),
        "peer_scope": cp1c_rt.get("peer_scope", "peers"),
    }
