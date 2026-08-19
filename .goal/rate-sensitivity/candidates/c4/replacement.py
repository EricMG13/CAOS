def compute_rate_sensitivity(nf: dict) -> Optional[dict]:
    """Interest / coverage under base-rate shocks, or None if CP-1 lacks net debt."""
    import math  # macro.py does not import math at module scope; inline import is legal on splice.

    # GUARD A: a non-finite (NaN/inf) value passes isinstance(x, (int, float)) and
    # bool(nan) is True, so the original truthiness gate would let it through and
    # poison every divide into NaN/inf garbage. _finite() collapses those to None
    # so the existing "not numeric" rejection path also catches non-finite numbers.
    # bool() is unchanged for ordinary numbers, so valid inputs are untouched.
    def _finite(x):
        return x if isinstance(x, (int, float)) and math.isfinite(x) else None

    net_debt = _finite(nf.get("net_debt_ltm"))          # GUARD A: NaN/inf net_debt -> None -> return None below
    eb = _finite(latest(nf.get("adj_ebitda") or {}))    # GUARD A: NaN/inf EBITDA   -> None -> return None below
    if not isinstance(net_debt, (int, float)) or not isinstance(eb, (int, float)) or not eb:
        return None
    cov = _finite(nf.get("interest_coverage_ltm"))      # GUARD A: NaN/inf coverage -> None (treated as "no usable ratio")
    base_interest = round(eb / cov, 1) if isinstance(cov, (int, float)) and cov else None

    scenarios = []
    for bps in _SHOCKS_BPS:
        add = round(net_debt * bps / 10000, 1)  # $M incremental annual interest
        new_interest = round(base_interest + add, 1) if base_interest else None
        new_cov = round(eb / new_interest, 2) if new_interest else None
        scenarios.append({"rate_shock_bps": bps, "incremental_interest_musd": add,
                          "stressed_interest_coverage": new_cov})

    return {
        "net_debt_musd": round(float(net_debt), 1),
        "base_interest_musd": base_interest,
        "base_interest_coverage": cov if isinstance(cov, (int, float)) else None,
        "scenarios": scenarios,
        "assumption": "Assumes 100% floating-rate and unhedged (no hedge register ingested).",
    }
