def _runway(
    disclosed_liquidity: float,
    adj_ebitda: Optional[float],
    coverage: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """Pure arithmetic core: given a numeric liquidity figure plus the raw
    EBITDA and interest-coverage operands, compute (annual_cash_interest_musd,
    months) or (None, None). No CP-1 / payload knowledge — deterministic, no
    hidden state — so it is unit-testable on plain numbers.

    Cash interest is derived as adj_ebitda / coverage (coverage = EBITDA / cash
    interest), rounded to one decimal. Months then divides by that ALREADY-ROUNDED
    cash interest, never the raw quotient. Outputs are intentionally unguarded:
    zero liquidity -> 0.0 months, negative liquidity -> negative months, negative
    coverage -> negative cash interest & months.

    Guards (None, None) for: (b) EBITDA not numeric, coverage not numeric, or
    coverage falsy (0); (c) cash interest rounds to 0.0.
    """
    if not (isinstance(adj_ebitda, (int, float))
            and isinstance(coverage, (int, float)) and coverage):
        return None, None
    cash_interest = round(adj_ebitda / coverage, 1)
    if not cash_interest:
        return None, None
    return cash_interest, round(disclosed_liquidity * 12 / cash_interest, 1)


def _interest_runway_months(disclosed_liquidity: Optional[float], cp1: Optional[ModulePayload]):
    """Months the disclosed liquidity alone would service cash interest, from CP-1's
    canonical financials. A liquidity-stress lens (EBITDA→0), NOT a full
    months-to-empty — that needs amort/capex/maturity uses we don't source. Returns
    (annual_cash_interest_musd, months) or (None, None) when inputs are absent."""
    if not isinstance(disclosed_liquidity, (int, float)) or cp1 is None:
        return None, None
    nf = (cp1.runtime_output or {}).get("normalized_financials") or {}
    return _runway(disclosed_liquidity, latest(nf.get("adj_ebitda") or {}),
                   nf.get("interest_coverage_ltm"))
