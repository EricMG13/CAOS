"""Golden-master (characterization) contract for
engine.downside.compute_pathways.

Values captured from the live function at git e797760+ and CONFIRMED by running
this file against the unmodified function. Self-contained bootstrap.

CP-2B downside pathway. Net debt held fixed under an EBITDA shock, so:
    stressed_net_leverage   = round(lev / (1 - shock), 2)
    stressed_interest_cov   = round(cov * (1 - shock), 2)  (None if cov non-numeric)
  Shocks = (0.10, 0.20, 0.30); ebitda_shock_pct = round(shock * 100) = 10/20/30.
  shock_to_breach_pct = the FIRST shock pct at which stressed leverage >= 7.0
    (_BREACH_X), else None.
  fragility = "HIGH"  if lev >= 7.0 OR shock_to_breach <= 10
              "MODERATE" elif shock_to_breach <= 20
              "LOW"   else
  Returns the dict, or None when net_leverage_adj_ltm is not numeric.

Contract crux (what a rewrite MUST keep):
  1. None iff net_leverage_adj_ltm not int/float.
  2. stressed leverage uses (1 - shock) in the DENOMINATOR (current/(1-shock));
     stressed coverage MULTIPLIES by (1 - shock). Don't swap.
  3. Breach test is >= 7.0 (inclusive): lev=6.3 -> 6.3/0.9 = 7.0 -> breaches at 10%.
  4. shock_to_breach captures the FIRST breaching shock only.
  5. Fragility band cutoffs on shock_to_breach: <=10 HIGH, <=20 MODERATE, else
     LOW; plus the lev >= 7.0 -> HIGH override.
  6. ebitda_shock_pct is round(shock*100) (int 10/20/30, not 10.0).
  7. round(.., 2) half-even; current_net_leverage = round(float(lev), 2).
  8. cov non-numeric (None/str) -> stressed coverage None in every scenario, but
     fragility/leverage still computed.

NOT gated (incidental): a NaN leverage/coverage currently LEAKS NaN into the
output (NaN >= 7.0 is False, so fragility silently reads "LOW"). A defensive
rewrite may map NaN to None; that divergence is allowed and is asserted
separately, not in the equivalence gate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.downside import compute_pathways


def _scen(pct, sl, sc):
    return {"ebitda_shock_pct": pct, "stressed_net_leverage": sl,
            "stressed_interest_coverage": sc}


def _out(current, scenarios, shock_to_breach, fragility):
    return {"current_net_leverage": current, "breach_threshold_x": 7.0,
            "scenarios": scenarios, "shock_to_breach_pct": shock_to_breach,
            "fragility": fragility}


CASES = [
    ("canonical", {"net_leverage_adj_ltm": 5.68, "interest_coverage_ltm": 2.1},
     _out(5.68, [_scen(10, 6.31, 1.89), _scen(20, 7.1, 1.68), _scen(30, 8.11, 1.47)], 20, "MODERATE")),

    # None guard
    ("no_lev", {"interest_coverage_ltm": 2.1}, None),
    ("lev_none", {"net_leverage_adj_ltm": None, "interest_coverage_ltm": 2.1}, None),
    ("lev_str", {"net_leverage_adj_ltm": "5.68", "interest_coverage_ltm": 2.1}, None),

    # fragility ladder + breach detection
    ("lev7_high", {"net_leverage_adj_ltm": 7.0, "interest_coverage_ltm": 2.0},
     _out(7.0, [_scen(10, 7.78, 1.8), _scen(20, 8.75, 1.6), _scen(30, 10.0, 1.4)], 10, "HIGH")),
    # lev=6.3 -> 6.3/0.9 = 7.0 exactly -> breach at 10% (inclusive >=)
    ("lev63_breach10", {"net_leverage_adj_ltm": 6.3, "interest_coverage_ltm": 2.0},
     _out(6.3, [_scen(10, 7.0, 1.8), _scen(20, 7.87, 1.6), _scen(30, 9.0, 1.4)], 10, "HIGH")),
    ("lev629_breach20", {"net_leverage_adj_ltm": 6.29, "interest_coverage_ltm": 2.0},
     _out(6.29, [_scen(10, 6.99, 1.8), _scen(20, 7.86, 1.6), _scen(30, 8.99, 1.4)], 20, "MODERATE")),
    # lev=5.6 -> 5.6/0.8 = 7.0 -> breach at 20%
    ("lev56_breach20", {"net_leverage_adj_ltm": 5.6, "interest_coverage_ltm": 2.0},
     _out(5.6, [_scen(10, 6.22, 1.8), _scen(20, 7.0, 1.6), _scen(30, 8.0, 1.4)], 20, "MODERATE")),
    # breach first at 30% -> LOW (30 is not <= 20)
    ("lev50_breach30", {"net_leverage_adj_ltm": 5.0, "interest_coverage_ltm": 2.0},
     _out(5.0, [_scen(10, 5.56, 1.8), _scen(20, 6.25, 1.6), _scen(30, 7.14, 1.4)], 30, "LOW")),
    # lev=4.9 -> 4.9/0.7 = 7.0 -> breach at 30% -> LOW
    ("lev49_breach30", {"net_leverage_adj_ltm": 4.9, "interest_coverage_ltm": 2.0},
     _out(4.9, [_scen(10, 5.44, 1.8), _scen(20, 6.12, 1.6), _scen(30, 7.0, 1.4)], 30, "LOW")),
    ("lev40_nobreach", {"net_leverage_adj_ltm": 4.0, "interest_coverage_ltm": 2.0},
     _out(4.0, [_scen(10, 4.44, 1.8), _scen(20, 5.0, 1.6), _scen(30, 5.71, 1.4)], None, "LOW")),
    ("lev10_high", {"net_leverage_adj_ltm": 10.0, "interest_coverage_ltm": 3.0},
     _out(10.0, [_scen(10, 11.11, 2.7), _scen(20, 12.5, 2.4), _scen(30, 14.29, 2.1)], 10, "HIGH")),

    # coverage missing / non-numeric -> stressed coverage None, fragility unchanged
    ("cov_missing", {"net_leverage_adj_ltm": 5.68},
     _out(5.68, [_scen(10, 6.31, None), _scen(20, 7.1, None), _scen(30, 8.11, None)], 20, "MODERATE")),
    ("cov_str", {"net_leverage_adj_ltm": 5.68, "interest_coverage_ltm": "2.1"},
     _out(5.68, [_scen(10, 6.31, None), _scen(20, 7.1, None), _scen(30, 8.11, None)], 20, "MODERATE")),
    # negative coverage flows through (no sign guard)
    ("cov_negative", {"net_leverage_adj_ltm": 5.68, "interest_coverage_ltm": -2.1},
     _out(5.68, [_scen(10, 6.31, -1.89), _scen(20, 7.1, -1.68), _scen(30, 8.11, -1.47)], 20, "MODERATE")),
    ("cov_zero", {"net_leverage_adj_ltm": 5.68, "interest_coverage_ltm": 0.0},
     _out(5.68, [_scen(10, 6.31, 0.0), _scen(20, 7.1, 0.0), _scen(30, 8.11, 0.0)], 20, "MODERATE")),

    # sign / zero edges on leverage (no guard)
    ("lev_negative", {"net_leverage_adj_ltm": -5.0, "interest_coverage_ltm": 2.0},
     _out(-5.0, [_scen(10, -5.56, 1.8), _scen(20, -6.25, 1.6), _scen(30, -7.14, 1.4)], None, "LOW")),
    ("lev_zero", {"net_leverage_adj_ltm": 0.0, "interest_coverage_ltm": 2.0},
     _out(0.0, [_scen(10, 0.0, 1.8), _scen(20, 0.0, 1.6), _scen(30, 0.0, 1.4)], None, "LOW")),
    # int leverage coerced; 6 -> 6/0.8 = 7.5 at 20% -> breach@20
    ("lev_int", {"net_leverage_adj_ltm": 6, "interest_coverage_ltm": 2},
     _out(6.0, [_scen(10, 6.67, 1.8), _scen(20, 7.5, 1.6), _scen(30, 8.57, 1.4)], 20, "MODERATE")),
]


@pytest.mark.parametrize("name,nf,expected", CASES, ids=[c[0] for c in CASES])
def test_compute_pathways_golden(name, nf, expected):
    assert compute_pathways(nf) == expected


def test_shock_pct_is_int_not_float():
    """ebitda_shock_pct is round(shock*100) -> exact int 10/20/30 (not 10.000…)."""
    pcts = [s["ebitda_shock_pct"] for s in compute_pathways({"net_leverage_adj_ltm": 5.0})["scenarios"]]
    assert pcts == [10, 20, 30] and all(isinstance(p, int) for p in pcts)


def test_nan_leverage_currently_leaks(  # INCIDENTAL, not part of the equivalence gate
):
    """Documents the live (buggy) behaviour: a NaN leverage is not guarded, so it
    leaks NaN into the output and fragility silently reads 'LOW'. A defensive
    rewrite may instead return None / drop the NaN — that is an allowed change."""
    import math
    r = compute_pathways({"net_leverage_adj_ltm": float("nan"), "interest_coverage_ltm": 2.0})
    assert r is None or math.isnan(r["current_net_leverage"])  # either fixed, or the documented leak
