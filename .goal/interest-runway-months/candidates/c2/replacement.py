def _interest_runway_months(
    disclosed_liquidity: Optional[float], cp1: Optional[ModulePayload]
) -> Tuple[Optional[float], Optional[float]]:
    """Months the disclosed liquidity alone would service cash interest, from CP-1's
    canonical financials. A liquidity-stress lens (EBITDA→0), NOT a full
    months-to-empty — that needs amort/capex/maturity uses we don't source. Returns
    (annual_cash_interest_musd, months) or (None, None) when inputs are absent."""
    # Guard 1: liquidity must be a real number and CP-1 must exist. Anything else
    # (None, a numeric string, a missing module) means we can't compute a runway.
    if not isinstance(disclosed_liquidity, (int, float)) or cp1 is None:
        return None, None

    normalized_financials = (cp1.runtime_output or {}).get("normalized_financials") or {}
    latest_ebitda = latest(normalized_financials.get("adj_ebitda") or {})
    interest_coverage = normalized_financials.get("interest_coverage_ltm")

    # Guard 2: both inputs must be numeric, and coverage must be non-zero. A zero or
    # missing coverage would make the cash-interest division below blow up.
    ebitda_is_numeric = isinstance(latest_ebitda, (int, float))
    coverage_is_usable = isinstance(interest_coverage, (int, float)) and interest_coverage
    if not (ebitda_is_numeric and coverage_is_usable):
        return None, None

    # Back out annual cash interest from coverage: EBITDA / (EBITDA / interest).
    # Round to 0.1 musd FIRST, then divide by the rounded figure — callers see this
    # exact value, so the runway must be derived from it (not from raw EBITDA/coverage).
    annual_cash_interest = round(latest_ebitda / interest_coverage, 1)

    # Guard 3: if cash interest rounds to 0.0, dividing by it would blow up. (Note we
    # intentionally do NOT guard the sign — negative coverage/liquidity flow through to
    # a negative result, and zero liquidity yields 0.0 months, both by design.)
    if not annual_cash_interest:
        return None, None

    months = round(disclosed_liquidity * 12 / annual_cash_interest, 1)
    return annual_cash_interest, months
