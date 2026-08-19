"""Golden-master (characterization) contract for
engine.macro.compute_rate_sensitivity.

Freezes the CURRENT observable behaviour so a best-of-N rewrite can be proven
equivalent. Every expected dict was captured from the live unmodified function
at git e797760+. Self-contained: bootstraps sys.path so it runs standalone
(`pytest .goal/rate-sensitivity/contract/test_contract.py`).

Contract crux (what a rewrite MUST keep):
  1. Returns None iff net_debt_ltm is not numeric, OR latest(adj_ebitda) is not
     numeric, OR EBITDA is falsy (0). Otherwise returns the full dict.
  2. base_interest = round(EBITDA / coverage, 1) ONLY when coverage is numeric &
     truthy; else None. When base_interest is None, every scenario's
     stressed_interest_coverage is None — but incremental_interest is still computed.
  3. ASYMMETRY (frozen): base_interest_coverage = ``cov if isinstance(cov, num)
     else None`` — it does NOT check truthiness. So coverage == 0 yields
     base_interest_musd=None (the round() guard checks truthy) but
     base_interest_coverage=0.
  4. Two shocks, ALWAYS (100, 200) bps. Per shock:
       incremental_interest = round(net_debt * bps / 10000, 1)   # 1 decimal
       new_interest = round(base_interest + incremental, 1)  (None if base None)
       stressed_coverage = round(EBITDA / new_interest, 2)  (None if new_interest falsy)  # 2 decimals
     Intermediates are rounded BEFORE reuse: new_interest sums the rounded base +
     rounded incremental; stressed_coverage divides by the rounded new_interest.
  5. No sign guard: negative net_debt -> negative incremental (rate cut, coverage
     IMPROVES); negative EBITDA -> negative base_interest. Frozen as-is.
  6. net_debt_musd = round(float(net_debt), 1). assumption string is constant.
  7. Rounding is Python round() — half-even over the float repr.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.macro import compute_rate_sensitivity

_ASSUMPTION = "Assumes 100% floating-rate and unhedged (no hedge register ingested)."


def _nf(net_debt=2000.0, cov=2.0, eb=400.0, eb_dict=None):
    d = {}
    if net_debt is not None:
        d["net_debt_ltm"] = net_debt
    if cov is not None:
        d["interest_coverage_ltm"] = cov
    d["adj_ebitda"] = eb_dict if eb_dict is not None else (
        {"LTM_Q1_26": eb} if eb is not None else {})
    return d


def _scen(bps, add, cov):
    return {"rate_shock_bps": bps, "incremental_interest_musd": add,
            "stressed_interest_coverage": cov}


def _out(net_debt_musd, base_int, base_cov, scenarios):
    return {"net_debt_musd": net_debt_musd, "base_interest_musd": base_int,
            "base_interest_coverage": base_cov, "scenarios": scenarios,
            "assumption": _ASSUMPTION}


# (name, nf, expected) — expected is the FROZEN golden dict or None.
CASES = [
    ("typical", _nf(),
     _out(2000.0, 200.0, 2.0, [_scen(100, 20.0, 1.82), _scen(200, 40.0, 1.67)])),

    # None paths (whole function returns None)
    ("no_net_debt", _nf(net_debt=None), None),
    ("net_debt_str", _nf(net_debt="2000"), None),
    ("eb_zero", _nf(eb=0.0), None),
    ("eb_empty", _nf(eb_dict={}), None),

    # coverage missing/non-numeric -> base_interest None, base_cov None, add present
    ("cov_missing", _nf(cov=None),
     _out(2000.0, None, None, [_scen(100, 20.0, None), _scen(200, 40.0, None)])),
    ("cov_str", _nf(cov="2"),
     _out(2000.0, None, None, [_scen(100, 20.0, None), _scen(200, 40.0, None)])),

    # ASYMMETRY: coverage == 0 -> base_interest_musd None BUT base_interest_coverage 0
    ("cov_zero", _nf(cov=0),
     _out(2000.0, None, 0, [_scen(100, 20.0, None), _scen(200, 40.0, None)])),

    # sign: negative net debt = rate CUT, coverage improves; add negative
    ("net_debt_negative", _nf(net_debt=-2000.0),
     _out(-2000.0, 200.0, 2.0, [_scen(100, -20.0, 2.22), _scen(200, -40.0, 2.5)])),

    # sign: negative EBITDA -> negative base_interest (double-negative cov stays +)
    ("eb_negative", _nf(eb=-400.0),
     _out(2000.0, -200.0, 2.0, [_scen(100, 20.0, 2.22), _scen(200, 40.0, 2.5)])),

    # add rounded to 1dp: 37*100/10000 = 0.37 -> 0.4; 0.74 -> 0.7
    ("small_net_debt_add_rounding", _nf(net_debt=37.0, cov=2.1, eb=421.0),
     _out(37.0, 200.5, 2.1, [_scen(100, 0.4, 2.1), _scen(200, 0.7, 2.09)])),

    # add 25.5 / 51.0 exact
    ("rounding_add", _nf(net_debt=2550.0),
     _out(2550.0, 200.0, 2.0, [_scen(100, 25.5, 1.77), _scen(200, 51.0, 1.59)])),

    # base_interest rounds 140.333 -> 140.3; add 12.3/24.7; cov 2.76/2.55
    ("rounding_chain", _nf(net_debt=1234.0, cov=3.0, eb=421.0),
     _out(1234.0, 140.3, 3.0, [_scen(100, 12.3, 2.76), _scen(200, 24.7, 2.55)])),

    # base_interest rounds 200.476 -> 200.5
    ("base_interest_rounds", _nf(net_debt=2000.0, cov=2.1, eb=421.0),
     _out(2000.0, 200.5, 2.1, [_scen(100, 20.0, 1.91), _scen(200, 40.0, 1.75)])),

    # int net_debt coerced via float()
    ("net_debt_int", _nf(net_debt=2000),
     _out(2000.0, 200.0, 2.0, [_scen(100, 20.0, 1.82), _scen(200, 40.0, 1.67)])),

    # latest() picks largest trailing-year period (LTM_Q1_26 -> 400)
    ("multi_period_eb", _nf(eb_dict={"FY22": 999.0, "FY24": 100.0, "LTM_Q1_26": 400.0}),
     _out(2000.0, 200.0, 2.0, [_scen(100, 20.0, 1.82), _scen(200, 40.0, 1.67)])),

    # extreme magnitude
    ("extreme_large", _nf(net_debt=1e7, cov=2.0, eb=2e6),
     _out(1e7, 1e6, 2.0, [_scen(100, 1e5, 1.82), _scen(200, 2e5, 1.67)])),
]


@pytest.mark.parametrize("name,nf,expected", CASES, ids=[c[0] for c in CASES])
def test_rate_sensitivity_golden(name, nf, expected):
    assert compute_rate_sensitivity(nf) == expected


def test_always_two_scenarios_at_100_200_bps():
    """A non-None result always carries exactly the (100, 200) bps shocks, in order."""
    s = compute_rate_sensitivity(_nf())
    assert [x["rate_shock_bps"] for x in s["scenarios"]] == [100, 200]
