def _shock_scenario(net_debt: float, base_interest: Optional[float], eb: float, bps: int) -> dict:
    """Pure per-shock row math + guards.

    `base_interest` is the ALREADY-ROUNDED base interest ($M, 1dp) or None.
    Intermediates are rounded before reuse (incremental → new_interest →
    stressed coverage). Mirrors the live truthiness guards exactly:
      * incremental: round(net_debt * bps / 10000, 1)  [1dp]
      * new_interest: round(base_interest + add, 1) only if base_interest truthy
      * stressed: round(eb / new_interest, 2) only if new_interest truthy
    Returns the row dict {rate_shock_bps, incremental_interest_musd,
    stressed_interest_coverage}. No hidden state; deterministic.
    """
    add = round(net_debt * bps / 10000, 1)  # $M incremental annual interest
    new_interest = round(base_interest + add, 1) if base_interest else None
    new_cov = round(eb / new_interest, 2) if new_interest else None
    return {"rate_shock_bps": bps, "incremental_interest_musd": add,
            "stressed_interest_coverage": new_cov}


def compute_rate_sensitivity(nf: dict) -> Optional[dict]:
    """Interest / coverage under base-rate shocks, or None if CP-1 lacks net debt."""
    net_debt = nf.get("net_debt_ltm")
    eb = latest(nf.get("adj_ebitda") or {})
    if not isinstance(net_debt, (int, float)) or not isinstance(eb, (int, float)) or not eb:
        return None
    cov = nf.get("interest_coverage_ltm")
    base_interest = round(eb / cov, 1) if isinstance(cov, (int, float)) and cov else None

    scenarios = [_shock_scenario(net_debt, base_interest, eb, bps) for bps in _SHOCKS_BPS]

    return {
        "net_debt_musd": round(float(net_debt), 1),
        "base_interest_musd": base_interest,
        "base_interest_coverage": cov if isinstance(cov, (int, float)) else None,
        "scenarios": scenarios,
        "assumption": "Assumes 100% floating-rate and unhedged (no hedge register ingested).",
    }
