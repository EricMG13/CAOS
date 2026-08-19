import math


def _finite_number(x) -> bool:
    """True only for a real, finite int/float. bool is intentionally kept (it is an
    int subclass, and False→0 is a valid liquidity that must yield 0.0 months).
    Rejects NaN and +/-inf, which `isinstance` alone lets through and which would
    otherwise propagate into the division as garbage. `math.isfinite` accepts any
    int/float (and bool) and returns False for NaN/inf."""
    return isinstance(x, (int, float)) and math.isfinite(x)


def _interest_runway_months(disclosed_liquidity: Optional[float], cp1: Optional[ModulePayload]):
    """Months the disclosed liquidity alone would service cash interest, from CP-1's
    canonical financials. A liquidity-stress lens (EBITDA→0), NOT a full
    months-to-empty — that needs amort/capex/maturity uses we don't source. Returns
    (annual_cash_interest_musd, months) or (None, None) when inputs are absent."""
    # Guard (a): liquidity must be a finite number; cp1 must exist. The original
    # `isinstance(disclosed_liquidity, (int, float))` is widened only by also
    # requiring finiteness — every valid (finite) liquidity, including 0, -500 and
    # False, still passes; NaN/inf liquidity now degrades to (None, None) instead of
    # producing a NaN/inf month count.
    if not _finite_number(disclosed_liquidity) or cp1 is None:
        return None, None
    # Tolerate a cp1 with no `runtime_output` attribute (getattr, not attribute
    # access). The single live caller passes a real ModulePayload, whose
    # runtime_output is always present, so this never alters valid-input behaviour;
    # it only prevents an AttributeError on a malformed payload shape. `... or {}`
    # preserves the original None-handling (cp1.runtime_output=None → {}).
    nf = (getattr(cp1, "runtime_output", None) or {}).get("normalized_financials") or {}
    eb, cov = latest(nf.get("adj_ebitda") or {}), nf.get("interest_coverage_ltm")
    # Guard (b): eb and cov must both be finite numbers and cov must be truthy
    # (non-zero). Original used isinstance + truthiness of cov; finiteness is the
    # only addition. NaN coverage previously passed isinstance and `NaN` truthiness
    # (bool(NaN) is True) and yielded eb/NaN = NaN garbage — now it is rejected.
    # Every frozen case (eb=421/cov=2.1, eb=10/cov=3, cov=-2.1, …) is finite and
    # unaffected; cov=0/cov=None/adj_ebitda={} (→ eb None) still hit this guard.
    if not (_finite_number(eb) and _finite_number(cov) and cov):
        return None, None
    cash_interest = round(eb / cov, 1)
    # Guard (c): cash_interest falsy → (None, None). With eb and cov finite and cov
    # non-zero, cash_interest is always a finite number here, so this is the same
    # falsy-zero check as the original (e.g. eb=0.04/cov=1 → round(0.04,1)=0.0).
    if not cash_interest:
        return None, None
    # months divides by the ALREADY-ROUNDED cash_interest, not raw eb/cov — kept
    # exactly. cash_interest is finite and non-zero and disclosed_liquidity is
    # finite, so the result cannot be NaN/inf; no output guard is added (zero /
    # negative liquidity and negative coverage remain valid signed outputs).
    return cash_interest, round(disclosed_liquidity * 12 / cash_interest, 1)
