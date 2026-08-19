"""Golden-master (characterization) contract for
engine.liquidity._interest_runway_months.

Freezes the CURRENT observable behaviour so a best-of-N rewrite can be proven
equivalent. Every expected tuple was captured from the live unmodified function
at git e797760+c6. Self-contained: bootstraps sys.path so it runs standalone
(`pytest .goal/interest-runway-months/contract/test_contract.py`).

Contract crux (what a rewrite MUST keep):
  1. Always returns a 2-tuple ``(annual_cash_interest_musd, months)`` or
     ``(None, None)``. cash_interest = ``round(latest(adj_ebitda) / coverage, 1)``
     (implied annual cash interest); months = ``round(liquidity * 12 / cash_interest, 1)``.
  2. months divides by the ALREADY-ROUNDED cash_interest, NOT the raw eb/cov.
     Killer case: eb=10, cov=3 -> cash_interest=round(3.333,1)=3.3; with liq=100,
     months=round(100*12/3.3,1)=363.6. A raw-denominator rewrite gives 360.0.
  3. Three (None, None) guards, in order:
       a. ``disclosed_liquidity`` not int/float, OR ``cp1 is None``.
       b. ``latest(adj_ebitda)`` not numeric, OR ``interest_coverage_ltm`` not
          numeric, OR coverage is FALSY (0 / 0.0) — the divide-by-zero guard.
       c. cash_interest is FALSY (rounded to 0.0) — guards the months divide.
  4. ``latest()`` picks the value at the largest trailing-year period key.
  5. NO sign/zero guard on the OUTPUTS: zero liquidity -> 0.0 months;
     negative liquidity -> negative months; negative coverage passes the truthy
     guard -> negative cash_interest and negative months. These are frozen as-is.
  6. ``bool`` is an int subclass: False passes the numeric guard and yields 0.0
     months (frozen, matching the live ``isinstance`` test).
  7. ``cp1.runtime_output`` may be None -> treated as {} -> (None, None).
  8. Rounding is Python ``round(x, 1)`` — half-even over the float repr.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.liquidity import _interest_runway_months
from engine.schemas import ModulePayload


def _cp1(eb=421.0, cov=2.1, eb_dict=None, ro="default"):
    """Mirror the production CP-1 shape the function reads (``runtime_output
    .normalized_financials`` with ``adj_ebitda`` period dict + coverage)."""
    if ro == "none":
        return ModulePayload("CP-1", "X", "canonical_financials", None)
    nf = {"interest_coverage_ltm": cov,
          "adj_ebitda": eb_dict if eb_dict is not None
          else {"FY24": eb - 6, "LTM_Q1_26": eb}}
    return ModulePayload("CP-1", "X", "canonical_financials",
                         {"normalized_financials": nf})


# (name, disclosed_liquidity, cp1, expected_tuple)
CASES = [
    # typical: 421/2.1 = 200.476 -> ci 200.5; 500*12/200.5 = 29.925 -> 29.9
    ("typical_500", 500.0, _cp1(), (200.5, 29.9)),
    ("typical_1000", 1000.0, _cp1(), (200.5, 59.9)),

    # guard (a): missing cp1 / non-numeric liquidity
    ("cp1_none", 500.0, None, (None, None)),
    ("liq_none", None, _cp1(), (None, None)),
    ("liq_str", "500", _cp1(), (None, None)),
    ("ro_none", 500.0, _cp1(ro="none"), (None, None)),

    # guard (b): coverage falsy / missing, or no ebitda
    ("cov_zero", 500.0, _cp1(cov=0), (None, None)),
    ("cov_missing", 500.0, _cp1(cov=None), (None, None)),
    ("ebitda_empty", 500.0, _cp1(eb_dict={}), (None, None)),

    # guard (c): cash_interest rounds to 0.0 -> (None, None) (months divide guard)
    ("cash_interest_rounds_zero", 500.0, _cp1(eb=0.04, cov=1.0), (None, None)),

    # KILLER: months divides by the ROUNDED cash_interest (3.3), not raw 3.333
    ("rounded_denominator", 100.0, _cp1(eb=10.0, cov=3.0), (3.3, 363.6)),

    # half-even / clean: ci=120.0; 1000*12/120 = 100.0
    ("clean_120", 1000.0, _cp1(eb=240.0, cov=2.0), (120.0, 100.0)),

    # sign + zero edges (NO output guard — frozen as-is)
    ("liq_zero", 0.0, _cp1(), (200.5, 0.0)),
    ("liq_negative", -500.0, _cp1(), (200.5, -29.9)),
    ("cov_negative", 500.0, _cp1(cov=-2.1), (-200.5, -29.9)),
    ("liq_bool_false", False, _cp1(), (200.5, 0.0)),

    # latest() picks the largest trailing-year period (LTM_Q1_26 -> 421.0)
    ("ebitda_multi_period", 500.0,
     _cp1(eb_dict={"FY22": 999.0, "FY24": 100.0, "LTM_Q1_26": 421.0}), (200.5, 29.9)),

    # extreme magnitude
    ("extreme_large", 1e6, _cp1(eb=5e5, cov=2.0), (250000.0, 48.0)),
]


@pytest.mark.parametrize("name,liq,cp1,expected", CASES, ids=[c[0] for c in CASES])
def test_interest_runway_golden(name, liq, cp1, expected):
    assert _interest_runway_months(liq, cp1) == expected


def test_always_returns_two_tuple():
    """Every path returns a length-2 tuple, never a bare None or scalar."""
    for liq, cp1 in [(500.0, _cp1()), (None, None), (500.0, _cp1(cov=0))]:
        r = _interest_runway_months(liq, cp1)
        assert isinstance(r, tuple) and len(r) == 2
