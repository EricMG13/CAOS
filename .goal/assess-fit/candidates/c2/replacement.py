def assess_fit(cp3_rt: dict, leverage: Optional[float]) -> Optional[dict]:
    """Map a CP-3 relative-value call to a portfolio sleeve, sizing, and risk flags.

    Returns ``None`` when CP-3 gave no recognised recommendation (nothing to size).
    Otherwise returns the sleeve fit, suggested sizing, the originating
    recommendation, CP-3's composite percentile (passed through), any risk-budget
    flags, and a constant note about checks that need a portfolio feed we lack.
    """
    recommendation = cp3_rt.get("recommendation")
    if recommendation not in _FIT:
        # No actionable relative-value call -> nothing to size against the book.
        return None
    sleeve, sizing = _FIT[recommendation]

    # Raise a risk-budget flag only for a real high-leverage reading. The explicit
    # isinstance + is_finite-style >= comparison keeps NaN and non-numbers out:
    # a NaN would pass isinstance but every comparison with it is False, and any
    # non-number (None, str) is excluded outright -> flags stays empty.
    risk_flags = []
    is_numeric_leverage = isinstance(leverage, (int, float))
    if is_numeric_leverage and leverage >= 6.0:
        risk_flags.append(f"High leverage ({leverage:g}x) — counts against the risk budget.")

    return {
        "sleeve_fit": sleeve,
        "suggested_sizing": sizing,
        "rv_recommendation": recommendation,
        "composite_percentile": cp3_rt.get("composite_percentile"),
        "risk_flags": risk_flags,
        "note": "Concentration/correlation checks require a portfolio feed (not ingested).",
    }
