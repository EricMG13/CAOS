def _interest_runway_months(disclosed_liquidity: Optional[float], cp1: Optional[ModulePayload]):
    """Months the disclosed liquidity alone would service cash interest, from CP-1's
    canonical financials. A liquidity-stress lens (EBITDA→0), NOT a full
    months-to-empty — that needs amort/capex/maturity uses we don't source. Returns
    (annual_cash_interest_musd, months) or (None, None) when inputs are absent."""
    if not isinstance(disclosed_liquidity, (int, float)) or cp1 is None:
        return None, None
    nf = (cp1.runtime_output or {}).get("normalized_financials") or {}
    eb = latest(nf.get("adj_ebitda") or {})
    cov = nf.get("interest_coverage_ltm")
    if not (isinstance(eb, (int, float)) and isinstance(cov, (int, float)) and cov):
        return None, None
    cash_interest = round(eb / cov, 1)
    if not cash_interest:
        return None, None
    return cash_interest, round(disclosed_liquidity * 12 / cash_interest, 1)
