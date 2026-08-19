def _stressed_scenario(current_leverage: float, current_coverage, shock: float) -> dict:
    """One EBITDA-decline scenario.

    Net debt is held fixed under the shock, so an EBITDA drop of ``shock`` (a
    fraction, e.g. 0.10 for -10%) scales leverage UP by ``1 / (1 - shock)`` and
    coverage DOWN by ``(1 - shock)`` — the standard first-order sensitivity.
    Coverage is only stressed when CP-1 actually gave us a number.
    """
    stressed_leverage = round(current_leverage / (1 - shock), 2)
    if isinstance(current_coverage, (int, float)):
        stressed_coverage = round(current_coverage * (1 - shock), 2)
    else:
        stressed_coverage = None
    return {
        "ebitda_shock_pct": round(shock * 100),
        "stressed_net_leverage": stressed_leverage,
        "stressed_interest_coverage": stressed_coverage,
    }


def compute_pathways(nf: dict) -> Optional[dict]:
    """Leverage/coverage under EBITDA stress, or None if CP-1 gave no leverage.

    Net debt is held fixed under the EBITDA shock, so stressed leverage is just
    ``current / (1 - shock)`` — the standard first-order downside sensitivity.
    """
    # No usable leverage figure from CP-1 means there is nothing to stress.
    current_leverage = nf.get("net_leverage_adj_ltm")
    if not isinstance(current_leverage, (int, float)):
        return None
    current_coverage = nf.get("interest_coverage_ltm")

    # Build each shocked scenario and record the FIRST shock (smallest decline)
    # at which stressed leverage reaches the distress threshold — that shock is
    # the headline "how much room before breach" read.
    scenarios = []
    shock_to_breach_pct: Optional[int] = None
    for shock in _SHOCKS:
        scenario = _stressed_scenario(current_leverage, current_coverage, shock)
        scenarios.append(scenario)
        breached = scenario["stressed_net_leverage"] >= _BREACH_X
        if shock_to_breach_pct is None and breached:
            shock_to_breach_pct = scenario["ebitda_shock_pct"]

    # Fragility buckets the breach distance. Already at/above the threshold today,
    # or breaching on only a small (<=10%) shock, is HIGH; a 20% shock is MODERATE;
    # anything more resilient is LOW. (The `lev >= _BREACH_X` clause is redundant —
    # a credit already at the threshold also breaches at the 10% shock — but it is
    # kept explicit so the HIGH condition reads as "distressed now OR soon".)
    breaches_by = shock_to_breach_pct  # None means "no breach across any shock"
    if current_leverage >= _BREACH_X or (breaches_by is not None and breaches_by <= 10):
        fragility = "HIGH"
    elif breaches_by is not None and breaches_by <= 20:
        fragility = "MODERATE"
    else:
        fragility = "LOW"

    return {
        "current_net_leverage": round(float(current_leverage), 2),
        "breach_threshold_x": _BREACH_X,
        "scenarios": scenarios,
        "shock_to_breach_pct": shock_to_breach_pct,
        "fragility": fragility,
    }
