"""Golden-master contract for engine.portfoliofit.assess_fit.

Values captured from the live function (git a0b9880) and confirmed against the
unmodified function. Self-contained bootstrap.

CP-3C PortfolioFitAnalysis. Maps CP-3's relative-value recommendation to a
portfolio sleeve + sizing bucket, and raises a high-leverage risk flag.

Contract crux:
  1. None iff recommendation is not exactly one of OVERWEIGHT / NEUTRAL /
     UNDERWEIGHT (missing, None, lowercase, or any other value -> None).
  2. sleeve_fit / suggested_sizing from the _FIT map: OVERWEIGHT -> core / full
     target size; NEUTRAL -> satellite / half target size; UNDERWEIGHT ->
     tactical only / minimal / pass.
  3. risk_flags carries one "High leverage ({leverage:g}x) — counts against the
     risk budget." ONLY when leverage is numeric AND >= 6.0 (inclusive). A
     non-numeric, NaN (NaN >= 6.0 is False — no crash, no flag), or < 6.0
     leverage -> no flag. {leverage:g} formats 6.0->"6", 6.5->"6.5".
  4. composite_percentile is passed through from cp3_rt (None when absent).
  5. note is a constant string.

No division / no round() here, so there is no NaN-divide bug (a NaN leverage is
simply not >= 6.0). No defensive graft is warranted — same as score_vulnerability.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.portfoliofit import assess_fit

_NAN = float("nan")
_NOTE = "Concentration/correlation checks require a portfolio feed (not ingested)."


def _out(sleeve, sizing, rec, composite, flags):
    return {"sleeve_fit": sleeve, "suggested_sizing": sizing, "rv_recommendation": rec,
            "composite_percentile": composite, "risk_flags": flags, "note": _NOTE}


def _flag(g):
    return [f"High leverage ({g}x) — counts against the risk budget."]


CASES = [
    ("ow_high_lev", {"recommendation": "OVERWEIGHT", "composite_percentile": 80}, 7.0,
     _out("core", "full target size", "OVERWEIGHT", 80, _flag("7"))),
    ("neutral_low_lev", {"recommendation": "NEUTRAL", "composite_percentile": 55}, 3.0,
     _out("satellite", "half target size", "NEUTRAL", 55, [])),
    ("uw_no_lev", {"recommendation": "UNDERWEIGHT", "composite_percentile": 32}, None,
     _out("tactical only", "minimal / pass", "UNDERWEIGHT", 32, [])),

    # recommendation not in _FIT -> None
    ("rec_missing", {}, 7.0, None),
    ("rec_none", {"recommendation": None}, 7.0, None),
    ("rec_lowercase", {"recommendation": "overweight"}, 7.0, None),
    ("rec_garbage", {"recommendation": "BUY"}, 7.0, None),

    # leverage flag threshold (inclusive >= 6.0)
    ("lev_exactly_6", {"recommendation": "OVERWEIGHT"}, 6.0,
     _out("core", "full target size", "OVERWEIGHT", None, _flag("6"))),
    ("lev_599_no_flag", {"recommendation": "OVERWEIGHT"}, 5.99,
     _out("core", "full target size", "OVERWEIGHT", None, [])),
    ("lev_int_6", {"recommendation": "OVERWEIGHT"}, 6,
     _out("core", "full target size", "OVERWEIGHT", None, _flag("6"))),
    ("lev_65_format", {"recommendation": "OVERWEIGHT"}, 6.5,
     _out("core", "full target size", "OVERWEIGHT", None, _flag("6.5"))),

    # graceful non-flagging inputs (no crash, no flag)
    ("lev_nan_no_crash", {"recommendation": "OVERWEIGHT"}, _NAN,
     _out("core", "full target size", "OVERWEIGHT", None, [])),
    ("lev_str_no_flag", {"recommendation": "NEUTRAL"}, "7.0",
     _out("satellite", "half target size", "NEUTRAL", None, [])),
    ("lev_negative_no_flag", {"recommendation": "NEUTRAL"}, -5.0,
     _out("satellite", "half target size", "NEUTRAL", None, [])),

    ("no_composite_key", {"recommendation": "NEUTRAL"}, 3.0,
     _out("satellite", "half target size", "NEUTRAL", None, [])),
]


@pytest.mark.parametrize("name,cp3_rt,lev,expected", CASES, ids=[c[0] for c in CASES])
def test_assess_fit_golden(name, cp3_rt, lev, expected):
    assert assess_fit(cp3_rt, lev) == expected


def test_all_three_recommendations_map_distinctly():
    sleeves = {assess_fit({"recommendation": r}, None)["sleeve_fit"]
               for r in ("OVERWEIGHT", "NEUTRAL", "UNDERWEIGHT")}
    assert sleeves == {"core", "satellite", "tactical only"}
