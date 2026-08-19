"""Golden-master (characterization) contract for
engine.refinancing.score_vulnerability.

Values hand-derived from the (deterministic integer/string) logic and CONFIRMED
by running this file against the unmodified function. Self-contained bootstrap.

Scoring (score starts 0, drivers []):
  leverage numeric: >= 6.0 -> +4 "high leverage {g}x"; elif >= 5.0 -> +2
    "elevated leverage {g}x"  (exclusive elif; < 5.0 or non-numeric -> nothing)
  fragility == "HIGH" -> +4 "high downside fragility"; elif == "MODERATE" -> +2
    "moderate downside fragility"  (exact, case-sensitive; else nothing)
  score = min(_MAX_SCORE=10, score)  [cap is dead: max reachable is 4+4=8]
  band  = "HIGH" if score >= 6 else "MODERATE" if score >= 3 else "LOW"
  returns (score:int, band:str, drivers:list) — leverage driver first.

Contract crux (what a rewrite MUST keep):
  1. Thresholds INCLUSIVE & exclusive-elif: 6.0 -> +4 only (NOT +6); 5.0 -> +2;
     5.99 -> +2; 4.99 -> 0.
  2. {leverage:g} formatting: 6.0->"6", 5.0->"5", 7.0->"7", 5.68->"5.68",
     6.5->"6.5". A f"{lev}x" or f"{lev:.1f}x" rewrite diverges.
  3. fragility match is EXACT and case-sensitive: "high"/""/"LOW" add nothing.
  4. non-numeric leverage (None, str) contributes nothing (bool note: True is an
     int subclass and >= 6.0 is False, so it adds nothing — not in goldens).
  5. Band cutoffs 6 (HIGH) and 3 (MODERATE); reachable scores are even
     {0,2,4,6,8}, so MODERATE = {4} and HIGH = {6,8} in practice.
  6. drivers order: leverage then fragility; both omitted when not triggered.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.refinancing import score_vulnerability


# (name, leverage, fragility, expected (score, band, drivers))
CASES = [
    # both drivers
    ("lev6_high", 6.0, "HIGH", (8, "HIGH", ["high leverage 6x", "high downside fragility"])),
    ("lev6_mod", 6.0, "MODERATE", (6, "HIGH", ["high leverage 6x", "moderate downside fragility"])),
    ("lev568_high", 5.68, "HIGH", (6, "HIGH", ["elevated leverage 5.68x", "high downside fragility"])),
    ("lev5_high", 5.0, "HIGH", (6, "HIGH", ["elevated leverage 5x", "high downside fragility"])),
    ("lev5_mod", 5.0, "MODERATE", (4, "MODERATE", ["elevated leverage 5x", "moderate downside fragility"])),
    ("lev65_mod", 6.5, "MODERATE", (6, "HIGH", ["high leverage 6.5x", "moderate downside fragility"])),
    ("lev7_high", 7.0, "HIGH", (8, "HIGH", ["high leverage 7x", "high downside fragility"])),
    ("lev_int6_high", 6, "HIGH", (8, "HIGH", ["high leverage 6x", "high downside fragility"])),
    ("lev55_mod", 5.5, "MODERATE", (4, "MODERATE", ["elevated leverage 5.5x", "moderate downside fragility"])),
    ("baseline_test_65_high", 6.5, "HIGH", (8, "HIGH", ["high leverage 6.5x", "high downside fragility"])),

    # leverage-only
    ("lev6_none", 6.0, None, (4, "MODERATE", ["high leverage 6x"])),
    ("lev5_none", 5.0, None, (2, "LOW", ["elevated leverage 5x"])),
    ("lev599_none", 5.99, None, (2, "LOW", ["elevated leverage 5.99x"])),
    ("lev4_none", 4.0, None, (0, "LOW", [])),
    ("lev_neg_high", -3.0, "HIGH", (4, "MODERATE", ["high downside fragility"])),  # neg lev: no lev driver
    ("lev499_high", 4.99, "HIGH", (4, "MODERATE", ["high downside fragility"])),   # 4.99 < 5.0: no lev driver

    # fragility-only / fragility mismatches
    ("no_lev_high", None, "HIGH", (4, "MODERATE", ["high downside fragility"])),
    ("no_lev_mod", None, "MODERATE", (2, "LOW", ["moderate downside fragility"])),
    ("no_lev_none", None, None, (0, "LOW", [])),
    ("str_lev_high", "6.0", "HIGH", (4, "MODERATE", ["high downside fragility"])),  # str leverage: no lev driver
    ("frag_low", 6.0, "LOW", (4, "MODERATE", ["high leverage 6x"])),               # "LOW" != HIGH/MODERATE
    ("frag_lowercase", 6.0, "high", (4, "MODERATE", ["high leverage 6x"])),        # case-sensitive
    ("frag_empty", 6.0, "", (4, "MODERATE", ["high leverage 6x"])),
]


@pytest.mark.parametrize("name,lev,frag,expected", CASES, ids=[c[0] for c in CASES])
def test_score_vulnerability_golden(name, lev, frag, expected):
    assert score_vulnerability(lev, frag) == expected


def test_returns_three_tuple_types():
    score, band, drivers = score_vulnerability(6.5, "HIGH")
    assert isinstance(score, int) and isinstance(band, str) and isinstance(drivers, list)


def test_drivers_is_fresh_list_each_call():
    a = score_vulnerability(6.0, "HIGH")[2]
    b = score_vulnerability(6.0, "HIGH")[2]
    assert a == b and a is not b  # no shared mutable default
