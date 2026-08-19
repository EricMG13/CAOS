def compute_pathways(nf: dict) -> Optional[dict]:
    """Leverage/coverage under EBITDA stress, or None if CP-1 gave no leverage.

    Net debt is held fixed under the EBITDA shock, so stressed leverage is just
    ``current / (1 - shock)`` — the standard first-order downside sensitivity.
    """
    lev = nf.get("net_leverage_adj_ltm")
    if not isinstance(lev, (int, float)):
        return None
    cov = nf.get("interest_coverage_ltm")

    scenarios = []
    shock_to_breach: Optional[int] = None
    for s in _SHOCKS:
        sl = round(lev / (1 - s), 2)
        sc = round(cov * (1 - s), 2) if isinstance(cov, (int, float)) else None
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
