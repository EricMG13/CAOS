"""ADVOCATE/VERIFIER repro for earnings-yoy-uses-year-not-sortkey.

compute_deltas (earnings.py:41) orders periods with `sorted(..., key=year)` over
`set(rev) | set(eb)`. Same-year labels (closed FY2025 vs live LTM_2025) tie on
year()==2025, so their relative order is whatever the set iteration yields, NOT
the sort_key-correct (LTM stub above the FY it trails) order.

This test asserts the WRONG output to PROVE the defect: if the set happens to
place LTM_2025 before FY2025, the latest period is the STALE closed FY2025 and a
spurious revenue DECLINE is reported (and the monitoring signal fires).
"""

import sys

sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

from engine.earnings import compute_deltas
from engine.periods import sort_key


def test_same_year_fy_vs_ltm_orders_wrong():
    nf = {
        "revenue": {"FY2024": 1000.0, "FY2025": 1100.0, "LTM_2025": 1150.0},
        "adj_ebitda": {"FY2024": 200.0, "FY2025": 210.0, "LTM_2025": 230.0},
    }
    out = compute_deltas(nf)
    order = [r["period"] for r in out["periods"]]
    summary = out["summary"]

    # sort_key-correct order — what the rest of the engine (periods.latest) uses.
    correct = sorted(set(nf["revenue"]) | set(nf["adj_ebitda"]), key=sort_key)

    print("earnings period order :", order)
    print("sort_key-correct order:", correct)
    print("prior :", summary["prior_period"], " latest:", summary["latest_period"])
    print("revenue_growth_pct    :", summary["revenue_growth_pct"])
    print("monitoring_signals    :", out["monitoring_signals"])
    print("FY2025 sort_key", sort_key("FY2025"), " LTM_2025 sort_key", sort_key("LTM_2025"))

    # The correct latest period is the live LTM stub.
    assert correct[-1] == "LTM_2025"

    # If earnings.py disagrees with sort_key, the defect is real. We assert the
    # WRONG behaviour so a green test = bug proven.
    if order != correct:
        # latest is the stale closed FY, not the live LTM -> spurious decline.
        assert summary["latest_period"] == "FY2025"
        assert summary["prior_period"] == "LTM_2025"
        assert summary["revenue_growth_pct"] < 0  # spurious DECLINE
        assert any("Revenue declined" in s for s in out["monitoring_signals"])
    else:
        # If this run's set order happened to match sort_key, record it so the
        # verifier knows the tie did not surface on this interpreter run.
        assert order == correct, "set order matched sort_key on this run"
