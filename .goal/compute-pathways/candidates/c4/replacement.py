def compute_pathways(nf: dict) -> Optional[dict]:
    """Leverage/coverage under EBITDA stress, or None if CP-1 gave no leverage.

    Net debt is held fixed under the EBITDA shock, so stressed leverage is just
    ``current / (1 - shock)`` — the standard first-order downside sensitivity.

    Defensive guards: a leverage that is non-numeric *or* non-finite (NaN/inf)
    is treated as "no leverage" and returns None, so an unknown-leverage issuer
    cannot leak NaN into ``current_net_leverage`` / ``stressed_net_leverage`` and
    be silently mislabeled LOW fragility downstream (CP-3D). Coverage gets the
    same finite check, yielding per-scenario None rather than a NaN/inf reading.
    """
    import math

    lev = nf.get("net_leverage_adj_ltm")
    # Guard 1: reject non-numeric leverage (existing missing-leverage path) AND
    # non-finite leverage (NaN/inf). A NaN would pass isinstance and every
    # downstream comparison (NaN >= 7.0 is False), leaking NaN into the output
    # and silently reading LOW fragility for an issuer whose leverage is unknown.
    if not isinstance(lev, (int, float)) or not math.isfinite(lev):
        return None
    cov = nf.get("interest_coverage_ltm")
    # Guard 2: coverage is only usable when it is a finite number; a non-numeric
    # OR non-finite (NaN/inf) coverage yields None per scenario, matching the
    # existing missing-coverage behaviour rather than leaking NaN/inf.
    cov_ok = isinstance(cov, (int, float)) and math.isfinite(cov)

    scenarios = []
    shock_to_breach: Optional[int] = None
    for s in _SHOCKS:
        sl = round(lev / (1 - s), 2)
        sc = round(cov * (1 - s), 2) if cov_ok else None
        scenarios.append({
            "ebitda_shock_pct": round(s * 100),
            "stressed_net_leverage": sl,
            "stressed_interest_coverage": sc,
        })
        if shock_to_breach is None and sl >= _BREACH_X:
            shock_to_breach = round(s * 100)

    if lev >= _BREACH_X or (shock_to_breach is not None and shock_to_breach <= 10):
        fragility = "HIGH"
    elif shock_to_breach is not None and shock_to_breach <= 20:
        fragility = "MODERATE"
    else:
        fragility = "LOW"

    return {
        "current_net_leverage": round(float(lev), 2),
        "breach_threshold_x": _BREACH_X,
        "scenarios": scenarios,
        "shock_to_breach_pct": shock_to_breach,
        "fragility": fragility,
    }
