def compute_pathways(nf: dict) -> Optional[dict]:
    """Stressed leverage/coverage under EBITDA-decline shocks, or None if no leverage.

    Credit model (held-flat-debt sensitivity, NOT a cash-sweep path)
    ----------------------------------------------------------------
    Net debt is held FLAT while EBITDA is shocked down by ``s`` (10/20/30%).
    Because net leverage = net debt / EBITDA, holding the numerator fixed and
    cutting the denominator by ``(1 - s)`` scales leverage UP by ``1/(1 - s)``:

        stressed_net_leverage = current_leverage / (1 - s)

    This is the standard FIRST-ORDER downside sensitivity — it deliberately
    ignores cash sweeps, amortization, and debt paydown, so it reads as the
    immediate leverage shock, not a forward-modelled trajectory. By the same
    logic, interest coverage = EBITDA / interest scales DOWN by ``(1 - s)``:

        stressed_interest_coverage = current_coverage * (1 - s)

    Breach threshold (the distress marker)
    --------------------------------------
    ``_BREACH_X`` = 7.0x net leverage is the conventional leveraged-loan
    distress marker — the level at/above which the credit is treated as
    distressed. ``shock_to_breach_pct`` is the SMALLEST EBITDA decline (10/20/30)
    whose stressed leverage first reaches 7.0x (inclusive); None if even a 30%
    decline keeps leverage under 7.0x.

    Fragility ladder (how little EBITDA loss tips into distress)
    -----------------------------------------------------------
    Reads off how soon a moderate EBITDA decline pushes the credit to >=7.0x:
        HIGH     — already distressed (lev >= 7.0x) OR breaches by a 10% shock
        MODERATE — breaches by a 20% shock (but not 10%)
        LOW      — survives a 30% shock without breaching
    (``lev >= 7.0`` is logically redundant with breach-by-10% — a credit already
    at/above 7.0x trivially clears 7.0x at the first 10% shock — but both are
    kept to state the "already distressed" intent explicitly.)
    """
    lev = nf.get("net_leverage_adj_ltm")
    if not isinstance(lev, (int, float)):
        return None  # CP-1 gave no leverage figure — nothing to stress.
    cov = nf.get("interest_coverage_ltm")

    scenarios = []
    shock_to_breach: Optional[int] = None
    for s in _SHOCKS:
        # EBITDA down by s, net debt flat -> leverage UP (divide by 1 - s),
        # coverage DOWN (multiply by 1 - s).
        sl = round(lev / (1 - s), 2)
        sc = round(cov * (1 - s), 2) if isinstance(cov, (int, float)) else None
        scenarios.append({
            "ebitda_shock_pct": round(s * 100),  # 0.10 -> 10, 0.20 -> 20, 0.30 -> 30
            "stressed_net_leverage": sl,
            "stressed_interest_coverage": sc,
        })
        # First shock whose stressed leverage reaches the 7.0x distress marker.
        if shock_to_breach is None and sl >= _BREACH_X:
            shock_to_breach = round(s * 100)

    # Fragility ladder: already-distressed or breaches by 10% -> HIGH; by 20% ->
    # MODERATE; survives a 30% shock -> LOW.
    if lev >= _BREACH_X or (shock_to_breach is not None and shock_to_breach <= 10):
        fragility = "HIGH"
    elif shock_to_breach is not None and shock_to_breach <= 20:
        fragility = "MODERATE"
    else:
        fragility = "LOW"

    return {
        "current_net_leverage": round(float(lev), 2),
        "breach_threshold_x": _BREACH_X,  # 7.0x leveraged-loan distress marker
        "scenarios": scenarios,
        "shock_to_breach_pct": shock_to_breach,
        "fragility": fragility,
    }
