"""Golden-master contract for engine.earnings.compute_deltas.

Values captured from the live function (git 5fcecd8) and confirmed by running
this file against the unmodified function. Self-contained bootstrap.

CP-1B EarningsDelta. Builds per-period rows (revenue, adj_ebitda, ebitda_margin),
a YoY summary, and monitoring signals — all pure from CP-1's multi-period series.

Contract crux:
  1. periods = sorted(union of revenue+adj_ebitda keys, key=sort_key).
  2. ebitda_margin = round(100*e/r, 1) ONLY when r is numeric AND truthy AND e is
     numeric; else None. (r truthy guards zero-revenue ÷0; NEGATIVE r gives a
     negative margin.)
  3. *_growth_pct via _yoy: round(100*(last-prev)/prev, 1) over the last two
     periods carrying a numeric value; None when <2 such periods OR prev is falsy
     (0). margin_change_pp = round(last_margin - prior_margin, 1) over the last
     two numeric margins, else None.
  4. signals (in order): revenue declined if rev_yoy<0; adj EBITDA declined if
     eb_yoy<0; margin compressed if margin_change <= -1.0 (inclusive).
  5. round() is half-even. Non-numeric period values are skipped, not coerced.

NOT gated (incidental): a NaN revenue/EBITDA currently LEAKS NaN into
ebitda_margin / *_growth_pct / margin_change_pp (NaN passes isinstance and
`bool(NaN)` is True). A defensive rewrite may sanitize non-finite values to None;
that divergence is allowed and asserted separately, not in the equivalence gate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.earnings import compute_deltas


def _nf(rev, eb):
    return {"revenue": rev, "adj_ebitda": eb}


def _row(p, r, e, m):
    return {"period": p, "revenue": r, "adj_ebitda": e, "ebitda_margin": m}


def _sum(rg, eg, mc, lp, pp):
    return {"revenue_growth_pct": rg, "ebitda_growth_pct": eg, "margin_change_pp": mc,
            "latest_period": lp, "prior_period": pp}


def _out(rows, summary, signals):
    return {"periods": rows, "summary": summary, "monitoring_signals": signals}


CASES = [
    ("growth_2p", _nf({"FY23": 100.0, "FY24": 120.0}, {"FY23": 20.0, "FY24": 30.0}),
     _out([_row("FY23", 100.0, 20.0, 20.0), _row("FY24", 120.0, 30.0, 25.0)],
          _sum(20.0, 50.0, 5.0, "FY24", "FY23"), [])),

    ("decline_2p", _nf({"FY23": 100.0, "FY24": 90.0}, {"FY23": 25.0, "FY24": 20.0}),
     _out([_row("FY23", 100.0, 25.0, 25.0), _row("FY24", 90.0, 20.0, 22.2)],
          _sum(-10.0, -20.0, -2.8, "FY24", "FY23"),
          ["Revenue declined 10% YoY (FY23→FY24).",
           "Adjusted EBITDA declined 20% YoY (FY23→FY24).",
           "EBITDA margin compressed 2.8pp YoY."])),

    ("single_period", _nf({"FY24": 100.0}, {"FY24": 20.0}),
     _out([_row("FY24", 100.0, 20.0, 20.0)],
          _sum(None, None, None, "FY24", None), [])),

    ("empty", {}, _out([], _sum(None, None, None, None, None), [])),

    # revenue absent -> margins None, rev_yoy None, but eb_yoy still computes
    ("no_revenue_key", {"adj_ebitda": {"FY23": 20.0, "FY24": 22.0}},
     _out([_row("FY23", None, 20.0, None), _row("FY24", None, 22.0, None)],
          _sum(None, 10.0, None, "FY24", "FY23"), [])),

    # zero revenue -> margin None (no ÷0); eb_yoy 300%; one numeric margin -> margin_change None
    ("zero_revenue_margin_none", _nf({"FY23": 0.0, "FY24": 100.0}, {"FY23": 5.0, "FY24": 20.0}),
     _out([_row("FY23", 0.0, 5.0, None), _row("FY24", 100.0, 20.0, 20.0)],
          _sum(None, 300.0, None, "FY24", "FY23"), [])),

    # prev value 0 -> _yoy returns None for both
    ("prev_zero_yoy_none", _nf({"FY23": 0.0, "FY24": 100.0}, {"FY23": 0.0, "FY24": 20.0}),
     _out([_row("FY23", 0.0, 0.0, None), _row("FY24", 100.0, 20.0, 20.0)],
          _sum(None, None, None, "FY24", "FY23"), [])),

    # three periods: YoY/margin_change use the LAST two only
    ("three_periods", _nf({"FY22": 80.0, "FY23": 100.0, "FY24": 90.0},
                          {"FY22": 16.0, "FY23": 25.0, "FY24": 20.0}),
     _out([_row("FY22", 80.0, 16.0, 20.0), _row("FY23", 100.0, 25.0, 25.0),
           _row("FY24", 90.0, 20.0, 22.2)],
          _sum(-10.0, -20.0, -2.8, "FY24", "FY23"),
          ["Revenue declined 10% YoY (FY23→FY24).",
           "Adjusted EBITDA declined 20% YoY (FY23→FY24).",
           "EBITDA margin compressed 2.8pp YoY."])),

    # margin compression exactly 1.0pp -> signal fires (<=)
    ("margin_compress_exactly_1pp", _nf({"FY23": 100.0, "FY24": 100.0}, {"FY23": 21.0, "FY24": 20.0}),
     _out([_row("FY23", 100.0, 21.0, 21.0), _row("FY24", 100.0, 20.0, 20.0)],
          _sum(0.0, -4.8, -1.0, "FY24", "FY23"),
          ["Adjusted EBITDA declined 4.8% YoY (FY23→FY24).",
           "EBITDA margin compressed 1pp YoY."])),

    # non-numeric value skipped (not coerced)
    ("mixed_nonnumeric", _nf({"FY23": "n/a", "FY24": 120.0}, {"FY23": 20.0, "FY24": 30.0}),
     _out([_row("FY23", "n/a", 20.0, None), _row("FY24", 120.0, 30.0, 25.0)],
          _sum(None, 50.0, None, "FY24", "FY23"), [])),

    # negative revenue -> negative margin; rev_yoy positive (double negative)
    ("negative_revenue", _nf({"FY23": -100.0, "FY24": -120.0}, {"FY23": 20.0, "FY24": 30.0}),
     _out([_row("FY23", -100.0, 20.0, -20.0), _row("FY24", -120.0, 30.0, -25.0)],
          _sum(20.0, 50.0, -5.0, "FY24", "FY23"),
          ["EBITDA margin compressed 5pp YoY."])),

    # margin rounding: 100/300=33.3, 200/700=28.6
    ("rounding_margin", _nf({"FY23": 300.0, "FY24": 700.0}, {"FY23": 100.0, "FY24": 200.0}),
     _out([_row("FY23", 300.0, 100.0, 33.3), _row("FY24", 700.0, 200.0, 28.6)],
          _sum(133.3, 100.0, -4.7, "FY24", "FY23"),
          ["EBITDA margin compressed 4.7pp YoY."])),
]


@pytest.mark.parametrize("name,nf,expected", CASES, ids=[c[0] for c in CASES])
def test_compute_deltas_golden(name, nf, expected):
    assert compute_deltas(nf) == expected


def test_nan_currently_leaks(  # INCIDENTAL — not the equivalence gate
):
    """Live (buggy) behaviour: a NaN revenue leaks NaN into ebitda_margin and the
    growth summary. A defensive rewrite may sanitize non-finite to None — allowed."""
    import math
    d = compute_deltas(_nf({"FY23": 100.0, "FY24": float("nan")}, {"FY23": 20.0, "FY24": 30.0}))
    m = d["periods"][-1]["ebitda_margin"]
    rg = d["summary"]["revenue_growth_pct"]
    assert (m is None and rg is None) or (math.isnan(m) and math.isnan(rg))  # fixed OR documented leak
