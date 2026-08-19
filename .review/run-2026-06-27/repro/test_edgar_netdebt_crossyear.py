"""ADVOCATE/VERIFIER repro for: edgar-netdebt-crossyear-contamination.

Claim: build_cp1_payload's net-debt freshness gate (debt_fresh) only validates the
long-term-debt leg. A FRESH LongTermDebtNoncurrent (FY2025) lets the gate PASS, while
a STALE current-debt leg (LongTermDebtCurrent last tagged FY2021) and a STALE cash leg
(last tagged FY2021) silently contaminate a committee-cited 'FY2025' net-leverage figure.

True FY2025 net debt (only fresh leg present) ~= 1000m -> ~3.0x.
Contaminated figure picks up 4-year-stale 2021 current debt + 2021 cash -> ~18x.

Run:
  cd "<repo>/caos" && PYTHONPATH=server server/.venv/bin/python \
      -m pytest ../.review/run-2026-06-27/repro/test_edgar_netdebt_crossyear.py -q
"""
from __future__ import annotations

from engine.edgar_cp1 import build_cp1_payload


def _flow(name, rows):
    """rows: (start, end, val, fy, accn, filed)."""
    return {name: {"units": {"USD": [
        {"start": s, "end": e, "val": v, "fy": fy, "fp": "FY", "form": "10-K", "accn": a, "filed": f}
        for (s, e, v, fy, a, f) in rows]}}}


def _inst(name, rows):
    """rows: (end, val, fy, accn, filed)."""
    return {name: {"units": {"USD": [
        {"end": e, "val": v, "fy": fy, "fp": "FY", "form": "10-K", "accn": a, "filed": f}
        for (e, v, fy, a, f) in rows]}}}


def _contaminated_facts():
    us = {}
    # Income statement fresh through FY2025 -> ly = 2025, reported EBITDA = 300+30 = 330m.
    us.update(_flow("Revenues", [
        ("2025-01-01", "2025-12-31", 4_000_000_000, 2025, "a25", "2026-02-01")]))
    us.update(_flow("OperatingIncomeLoss", [
        ("2025-01-01", "2025-12-31", 300_000_000, 2025, "a25", "2026-02-01")]))
    us.update(_flow("DepreciationDepletionAndAmortization", [
        ("2025-01-01", "2025-12-31", 30_000_000, 2025, "a25", "2026-02-01")]))
    # FRESH long-term debt at FY2025 -> debt_fresh PASSES on this leg.
    us.update(_inst("LongTermDebtNoncurrent", [
        ("2025-12-31", 1_000_000_000, 2025, "a25", "2026-02-01")]))
    # STALE current-portion debt, last tagged FY2021 (4 years stale). NEVER gated.
    us.update(_inst("LongTermDebtCurrent", [
        ("2021-12-31", 5_000_000_000, 2021, "old21", "2022-02-01")]))
    # STALE cash, last tagged FY2021 (4 years stale). NEVER gated.
    us.update(_inst("CashAndCashEquivalentsAtCarryingValue", [
        ("2021-12-31", 50_000_000, 2021, "old21", "2022-02-01")]))
    return {"entityName": "Contaminated Co", "facts": {"us-gaap": us}}


def test_crossyear_netdebt_contaminates_fy2025_leverage():
    p = build_cp1_payload("Contaminated Co", _contaminated_facts())
    assert p is not None
    nf = p.runtime_output["normalized_financials"]

    net_debt = nf.get("net_debt_ltm")
    lev = nf.get("net_leverage_adj_ltm")
    print("\n--- REPRO OUTPUT ---")
    print("net_debt_ltm        =", net_debt)
    print("net_leverage_adj_ltm=", lev)
    lev_claim = next((c for c in p.claims if c.claim_id == "C-EDG-LEV"), None)
    print("C-EDG-LEV claim_text=", lev_claim.claim_text if lev_claim else None)
    print("limitation_flags     =", p.limitation_flags)

    # Demonstrate the DEFECT: leverage is emitted, and it is the contaminated figure.
    # If the gate validated all three legs, leverage would be ~3.0x (1000/330), or
    # the leverage would be suppressed entirely as it is for a stale single leg.
    assert lev is not None, "leverage suppressed (would mean the bug is NOT present)"

    # The contaminated value: total_debt = 1000(fresh) + 5000(stale 2021),
    # net_debt = 6000 - 50(stale 2021 cash) = 5950 -> 5950/330 ~= 18.03x.
    assert net_debt == 5950.0, f"expected contaminated net_debt 5950.0, got {net_debt}"
    assert round(lev, 2) == 18.03, f"expected contaminated 18.03x, got {lev}"

    # And the committee-facing claim is labelled FY2025 despite being driven by 2021 data.
    assert lev_claim is not None
    assert "at FY2025" in lev_claim.claim_text
    assert "18.03x" in lev_claim.claim_text

    # The true fresh-only net debt is ~1000 (1000 LT debt, current portion + cash
    # untagged for 2025) -> ~3.03x. The emitted figure is 6x that, purely from stale legs.
    true_fresh_only_lev = round(1000.0 / 330.0, 2)
    assert true_fresh_only_lev == 3.03
    assert abs(lev - true_fresh_only_lev) > 10.0  # the contamination is enormous
