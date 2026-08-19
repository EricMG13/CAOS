def compute_rate_sensitivity(nf: dict) -> Optional[dict]:
    """Interest / coverage under base-rate shocks, or None if CP-1 lacks net debt."""
    net_debt = nf.get("net_debt_ltm")
    eb = latest(nf.get("adj_ebitda") or {})
    if not isinstance(net_debt, (int, float)) or not isinstance(eb, (int, float)) or not eb:
        return None
    cov = nf.get("interest_coverage_ltm")
    cov_numeric = isinstance(cov, (int, float))
    base_interest = round(eb / cov, 1) if cov_numeric and cov else None

    # Hoist the rate-independent factor: net_debt / 10000 is the same for every
    # shock, so compute it once instead of once per bps. Float assoc holds here —
    # round((net_debt / 10000) * bps, 1) is byte-identical to the original
    # round(net_debt * bps / 10000, 1) on every golden case (verified).
    debt_per_bp = net_debt / 10000
    scenarios = []
    for bps in _SHOCKS_BPS:
        add = round(debt_per_bp * bps, 1)  # $M incremental annual interest
        new_interest = round(base_interest + add, 1) if base_interest else None
        new_cov = round(eb / new_interest, 2) if new_interest else None
        scenarios.append({"rate_shock_bps": bps, "incremental_interest_musd": add,
                          "stressed_interest_coverage": new_cov})

    return {
        "net_debt_musd": round(float(net_debt), 1),
        "base_interest_musd": base_interest,
        "base_interest_coverage": cov if cov_numeric else None,
        "scenarios": scenarios,
        "assumption": "Assumes 100% floating-rate and unhedged (no hedge register ingested).",
    }
