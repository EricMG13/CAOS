def assess_fit(cp3_rt: dict, leverage: Optional[float]) -> Optional[dict]:
    rec = cp3_rt.get("recommendation")
    fit = _FIT.get(rec)
    if fit is None:
        return None
    sleeve, sizing = fit
    flags = []
    if isinstance(leverage, (int, float)) and leverage >= 6.0:
        flags.append(f"High leverage ({leverage:g}x) — counts against the risk budget.")
    return {
        "sleeve_fit": sleeve, "suggested_sizing": sizing,
        "rv_recommendation": rec, "composite_percentile": cp3_rt.get("composite_percentile"),
        "risk_flags": flags,
        "note": "Concentration/correlation checks require a portfolio feed (not ingested).",
    }
