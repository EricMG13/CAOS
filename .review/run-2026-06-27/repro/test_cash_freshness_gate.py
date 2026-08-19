"""Repro for: edgar-stale-cash-no-freshness-gate (edgar_cp1.py:218).

The leverage path gates DEBT on freshness (debt_fresh, line 222) but subtracts
CASH (cash_at, line 213/218) with NO freshness check. So when a filer's
LT-debt tag is fresh (2025) but its cash tag was last tagged years ago (2021),
net_debt = fresh_debt - STALE_cash, understating net leverage, and NO
limitation flag warns the committee.

Mirrors the existing test fixture builders in tests/server/test_edgar_cp1.py.
Asserts the WRONG (understated) output to PROVE the defect.
"""

from __future__ import annotations

import os
import sys

# Offline determinism — no key, no network.
for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(k, None)

sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

from engine.edgar_cp1 import build_cp1_payload  # noqa: E402


def _flow(name, rows):
    return {name: {"units": {"USD": [
        {"start": s, "end": e, "val": v, "fy": fy, "fp": "FY", "form": "10-K", "accn": a, "filed": f}
        for (s, e, v, fy, a, f) in rows]}}}


def _inst(name, rows):
    return {name: {"units": {"USD": [
        {"end": e, "val": v, "fy": fy, "fp": "FY", "form": "10-K", "accn": a, "filed": f}
        for (e, v, fy, a, f) in rows]}}}


def _facts_stale_cash():
    """EBITDA period = FY2025. LT debt fresh (2025, $1000m). Cash last tagged
    2021 ($900m) under CashAndCashEquivalentsAtCarryingValue — the filer stopped
    tagging cash after 2021 (no fallback _CASH tag present either)."""
    us = {}
    us.update(_flow("Revenues", [
        ("2023-01-01", "2023-12-31", 2_000_000_000, 2023, "a23", "2024-02-01"),
        ("2024-01-01", "2024-12-31", 2_000_000_000, 2024, "a24", "2025-02-01"),
        ("2025-01-01", "2025-12-31", 2_000_000_000, 2025, "a25", "2026-02-01"),
    ]))
    us.update(_flow("OperatingIncomeLoss", [
        ("2025-01-01", "2025-12-31", 400_000_000, 2025, "a25", "2026-02-01")]))
    us.update(_flow("DepreciationDepletionAndAmortization", [
        ("2025-01-01", "2025-12-31", 100_000_000, 2025, "a25", "2026-02-01")]))
    # LT debt: FRESH at 2025 = $1000m
    us.update(_inst("LongTermDebtNoncurrent", [
        ("2025-12-31", 1_000_000_000, 2025, "a25", "2026-02-01")]))
    # Cash: STALE — last tagged 2021 = $900m, never tagged 2022..2025
    us.update(_inst("CashAndCashEquivalentsAtCarryingValue", [
        ("2021-12-31", 900_000_000, 2021, "a21", "2022-02-01")]))
    return {"entityName": "StaleCash Co", "facts": {"us-gaap": us}}


def test_stale_cash_understates_leverage_with_no_flag():
    p = build_cp1_payload("StaleCash Co", _facts_stale_cash())
    assert p is not None
    nf = p.runtime_output["normalized_financials"]

    ebitda = nf["adj_ebitda"]["FY2025"]            # 400 + 100 = 500
    net_debt = nf.get("net_debt_ltm")
    lev = nf.get("net_leverage_adj_ltm")

    print(f"\nEBITDA FY2025      = {ebitda}m")
    print(f"net_debt_ltm       = {net_debt}m   (1000 fresh debt - 900 STALE 2021 cash)")
    print(f"net_leverage_adj   = {lev}x")
    print(f"limitation_flags   = {p.limitation_flags}")

    cash_concept = p.runtime_output.get("xbrl_concepts", {}).get("cash")
    print(f"cash concept cited = us-gaap:{cash_concept} (year not surfaced)")

    # ── PROVE the bug: leverage IS emitted off stale cash ──
    # True FY2025 net leverage with the 2025 cash untagged should be ~2.0x
    # (1000m debt / 500m EBITDA, treating unknown current cash as not-derivable).
    # Instead the stale 2021 cash collapses net debt to 100m → 0.2x.
    assert net_debt == 100.0, f"expected stale-cash net_debt 100.0, got {net_debt}"
    assert lev == 0.2, f"expected understated 0.2x, got {lev}"

    # And NO flag warns the cash leg is stale (debt/interest/Z'' all have such flags).
    cash_stale_flag = any(
        ("cash" in f.lower() and ("stale" in f.lower() or "predate" in f.lower()))
        for f in p.limitation_flags
    )
    assert not cash_stale_flag, (
        "a cash-staleness flag exists — bug would be fixed"
    )
    print("\nBUG CONFIRMED: 0.2x net leverage emitted off 4-year-stale cash, no flag.")
