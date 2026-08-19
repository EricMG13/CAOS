def compute_rate_sensitivity(nf: dict) -> Optional[dict]:
    """Stress a borrower's cash interest burden against a rise in the base rate.

    Credit read (conservative): treat ALL net debt as floating-rate and unhedged,
    so a base-rate move (SOFR / EURIBOR) flows straight through to cash interest.
    Output is the incremental annual interest and the resulting stressed interest
    coverage at each shock; returns None when CP-1 gives us no net debt to stress.

    The math an analyst can check by eye:
      * Base cash interest is BACKED OUT of CP-1, not re-modelled:
            interest coverage = EBITDA / cash interest  =>  cash interest = EBITDA / coverage
      * A shock of `bps` basis points adds, per year:
            incremental interest = net debt * (bps / 10000)
        (bps / 10000 converts basis points to a decimal rate; e.g. 100bps -> 0.01;
         x net debt = the extra annual interest dollars). Shocks are +100bps, +200bps.
      * Stressed coverage = EBITDA / (base interest + incremental interest).
      * Symmetric and intentionally UNGUARDED: a negative net debt (a net-cash
        borrower, the only way a "rate cut" arises here) yields negative incremental
        interest -> interest falls and coverage IMPROVES; a negative EBITDA yields a
        negative base interest. Neither sign is clamped.

    Reporting precision: interest in $M to 1dp ($0.1M); coverage ratios to 2dp (0.01x).
    Stressed coverage divides by the ALREADY-ROUNDED stressed interest, so the printed
    interest and the printed coverage reconcile to the cent the analyst would see.
    """
    # Stress inputs from CP-1: net debt ($M, signed) and latest adjusted EBITDA ($M).
    net_debt = nf.get("net_debt_ltm")
    eb = latest(nf.get("adj_ebitda") or {})
    # No net debt or no usable EBITDA (missing, non-numeric, or 0 -> coverage undefined):
    # nothing to stress, so caller treats this issuer as "rate sensitivity not computed".
    if not isinstance(net_debt, (int, float)) or not isinstance(eb, (int, float)) or not eb:
        return None

    # Back base cash interest out of reported coverage: interest = EBITDA / coverage.
    # Requires coverage to be numeric AND non-zero (else the division is undefined).
    cov = nf.get("interest_coverage_ltm")
    base_interest = round(eb / cov, 1) if isinstance(cov, (int, float)) and cov else None

    scenarios = []
    for bps in _SHOCKS_BPS:
        # Incremental annual interest from the shock: net debt x (bps / 10000), $M to 1dp.
        add = round(net_debt * bps / 10000, 1)  # $M incremental annual interest
        # Stressed interest = base + incremental; coverage = EBITDA / stressed interest.
        # Both fall through to None when base interest was not derivable (no coverage input).
        # Note: stressed coverage divides by the ROUNDED stressed interest so the two reconcile.
        new_interest = round(base_interest + add, 1) if base_interest else None
        new_cov = round(eb / new_interest, 2) if new_interest else None
        scenarios.append({"rate_shock_bps": bps, "incremental_interest_musd": add,
                          "stressed_interest_coverage": new_cov})

    return {
        "net_debt_musd": round(float(net_debt), 1),
        "base_interest_musd": base_interest,
        # ASYMMETRY (intentional): this echoes the RAW coverage input and does NOT require
        # truthiness, whereas base_interest above DOES (it divides by coverage). So a
        # reported coverage of 0 surfaces base_interest_coverage == 0 while base_interest_musd
        # is None — coverage 0 is a real disclosed read, but it can't back out an interest figure.
        "base_interest_coverage": cov if isinstance(cov, (int, float)) else None,
        "scenarios": scenarios,
        "assumption": "Assumes 100% floating-rate and unhedged (no hedge register ingested).",
    }
