"""Golden-master (characterization) contract for
engine.distress.altman_z_double_prime.

Freezes the CURRENT observable behaviour so a best-of-N rewrite can be proven
equivalent. Every expected value captured from the live unmodified function at
git e797760+. Self-contained: bootstraps sys.path so it runs standalone
(`pytest .goal/altman-z/contract/test_contract.py`).

Altman Z'' (private-firm / non-manufacturer "double-prime" variant):
    Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
      X1 = (current_assets - current_liabilities) / total_assets   (working capital / TA)
      X2 = retained_earnings / total_assets
      X3 = ebit / total_assets
      X4 = book_equity / total_liabilities                          (NOT / total_assets)
    Zones: z > 2.6 safe ; z < 1.1 distress ; else grey (2.6 and 1.1 are GREY).

Contract crux (what a rewrite MUST keep):
  1. KEYWORD-ONLY signature with EXACT param names — the caller unpacks
     `altman_z_double_prime(ebit=ebit, **bs)` (edgar_cp1.py:295), so renaming any
     parameter breaks production.
  2. Returns None iff total_assets <= 0 OR total_liabilities <= 0 (== 0 also None).
  3. The five constants (3.25, 6.56, 3.26, 6.72, 1.05) and each X-term definition,
     EXACTLY. X1 uses working capital (CA - CL); X4 divides by total_liabilities.
  4. z = round(<formula>, 2) — half-even over the float repr.
  5. Zone via strict inequalities: z > 2.6 safe, z < 1.1 distress, boundaries
     2.6 and 1.1 are GREY (a >= / <= rewrite flips the boundary cases below).
  6. Ratios are scale-free: tiny and 1e9-scaled canonical inputs both give 5.67.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.distress import altman_z_double_prime


def _z(**kw):
    return altman_z_double_prime(**kw)


_CANON = dict(current_assets=1500, current_liabilities=800, total_assets=5000,
              retained_earnings=1000, ebit=300, total_liabilities=3500, book_equity=1500)


# (name, kwargs, expected tuple-or-None) — expected captured from the live function.
CASES = [
    # canonical 5.67 safe — also locks X4 = BE/total_liabilities (=/TA would give 5.53)
    ("canonical", _CANON, (5.67, "safe")),

    # None guards: total_assets / total_liabilities <= 0
    ("ta_zero", dict(current_assets=0, current_liabilities=0, total_assets=0,
                     retained_earnings=0, ebit=0, total_liabilities=0, book_equity=0), None),
    ("ta_negative", dict(current_assets=100, current_liabilities=50, total_assets=-5000,
                         retained_earnings=0, ebit=0, total_liabilities=3500, book_equity=0), None),
    ("tl_zero", dict(current_assets=100, current_liabilities=50, total_assets=5000,
                     retained_earnings=0, ebit=0, total_liabilities=0, book_equity=0), None),
    ("tl_negative", dict(current_assets=100, current_liabilities=50, total_assets=5000,
                         retained_earnings=0, ebit=0, total_liabilities=-100, book_equity=0), None),

    # all X-terms zero -> pure constant 3.25
    ("all_zero_terms", dict(current_assets=0, current_liabilities=0, total_assets=5000,
                            retained_earnings=0, ebit=0, total_liabilities=3500, book_equity=0),
     (3.25, "safe")),

    # negative working capital (CA < CL) -> locks X1 = (CA - CL)/TA, not CA/TA
    ("neg_working_cap", dict(current_assets=200, current_liabilities=900, total_assets=5000,
                             retained_earnings=100, ebit=50, total_liabilities=3500, book_equity=1000),
     (2.76, "safe")),

    # distress
    ("distressed", dict(current_assets=300, current_liabilities=900, total_assets=5000,
                        retained_earnings=-2000, ebit=-400, total_liabilities=4800, book_equity=200),
     (0.66, "distress")),
    # insolvent: negative book equity -> negative Z
    ("insolvent_neg_equity", dict(current_assets=300, current_liabilities=900, total_assets=5000,
                                  retained_earnings=-3000, ebit=-500, total_liabilities=6000, book_equity=-1000),
     (-0.34, "distress")),

    # ZONE BOUNDARIES (strict inequalities) — CA=0, vary CL, TA=5000, others 0
    # z rounds to exactly 2.6 -> GREY (2.6 is NOT safe)
    ("boundary_safe_is_grey", dict(current_assets=0, current_liabilities=495, total_assets=5000,
                                   retained_earnings=0, ebit=0, total_liabilities=3500, book_equity=0),
     (2.6, "grey")),
    ("grey_mid", dict(current_assets=0, current_liabilities=1000, total_assets=5000,
                      retained_earnings=0, ebit=0, total_liabilities=3500, book_equity=0),
     (1.94, "grey")),
    # z rounds to exactly 1.1 -> GREY (1.1 is NOT distress)
    ("boundary_distress_is_grey", dict(current_assets=0, current_liabilities=1635, total_assets=5000,
                                       retained_earnings=0, ebit=0, total_liabilities=3500, book_equity=0),
     (1.1, "grey")),
    # just below 1.1 -> distress
    ("just_below_distress", dict(current_assets=0, current_liabilities=1645, total_assets=5000,
                                 retained_earnings=0, ebit=0, total_liabilities=3500, book_equity=0),
     (1.09, "distress")),

    # rounding sample
    ("rounding_sample", dict(current_assets=1234, current_liabilities=567, total_assets=8900,
                             retained_earnings=345, ebit=123, total_liabilities=6700, book_equity=2200),
     (4.31, "safe")),

    # scale-invariance: 1e9-scaled and tiny canonical both = 5.67
    ("extreme_large", dict(current_assets=1.5e9, current_liabilities=8e8, total_assets=5e9,
                           retained_earnings=1e9, ebit=3e8, total_liabilities=3.5e9, book_equity=1.5e9),
     (5.67, "safe")),
    ("tiny", dict(current_assets=1.5, current_liabilities=0.8, total_assets=5.0,
                  retained_earnings=1.0, ebit=0.3, total_liabilities=3.5, book_equity=1.5),
     (5.67, "safe")),

    # ── Mutation-isolating cases (added after an adversarial gap-hunt found the
    #    original 18 left these coefficient/rounding/denominator mistakes uncovered;
    #    every value below was VERIFIED against the live function, not hand-math) ──

    # Each isolates ONE coefficient-position swap (other X-terms driven to 0) so a
    # transposed weight / swapped numerator can no longer ship silently.
    # X2<->X3 (3.26<->6.72): X1=0, X4=0, X2=0.5, X3=0.1
    ("iso_x2_x3", dict(current_assets=100, current_liabilities=100, total_assets=100,
                       retained_earnings=50, ebit=10, total_liabilities=80, book_equity=0),
     (5.55, "safe")),
    # X3<->X4 (6.72<->1.05): X1=0, X2=0, X3=0.1, X4=0.8
    ("iso_x3_x4", dict(current_assets=100, current_liabilities=100, total_assets=100,
                       retained_earnings=0, ebit=10, total_liabilities=50, book_equity=40),
     (4.76, "safe")),
    # X1<->X3 (6.56<->6.72, near-equal weights): X2=0, X4=0, X1=0.4, X3=0.05
    ("iso_x1_x3", dict(current_assets=140, current_liabilities=100, total_assets=100,
                       retained_earnings=0, ebit=5, total_liabilities=80, book_equity=0),
     (6.21, "safe")),
    # X1<->X2 (6.56<->3.26): X3=0, X4=0, X1=0.5, X2=0.1
    ("iso_x1_x2", dict(current_assets=150, current_liabilities=100, total_assets=100,
                       retained_earnings=10, ebit=0, total_liabilities=80, book_equity=0),
     (6.86, "safe")),

    # ROUNDING MODE: raw z = 3.775 -> Python round() gives 3.77 (NOT 3.78); a
    # half-up / Decimal-HALF_UP rewrite would return 3.78. (X4=0.5, others 0.)
    ("rounding_halfeven_3775", dict(current_assets=0, current_liabilities=0, total_assets=10,
                                    retained_earnings=0, ebit=0, total_liabilities=10, book_equity=5),
     (3.77, "safe")),
    # INTERMEDIATE ROUNDING at a zone boundary: X4=0.025 (5/200); rounding x4 first
    # to 0.03 flips 2.6 grey -> 2.61 safe. Raw z = 2.60425 -> 2.6 grey.
    ("intermediate_round_boundary", dict(current_assets=10, current_liabilities=10, total_assets=50,
                                         retained_earnings=0, ebit=-5, total_liabilities=200, book_equity=5),
     (2.6, "grey")),
    # FINAL PRECISION: raw z = 2.645 -> round(.,2)=2.64 safe; a round(.,1) rewrite
    # gives 2.6 grey (a silent safe->grey demotion at the boundary).
    ("precision_2dp_not_1dp", dict(current_assets=5, current_liabilities=0, total_assets=10,
                                   retained_earnings=0, ebit=-5, total_liabilities=10, book_equity=-5),
     (2.64, "safe")),

    # X4 DENOMINATOR = total_liabilities (NOT total_assets), isolated with TA != TL.
    # boundary: BE=-100/TL=100 -> X4=-1.0 -> z=2.2 grey; BE/TA(-100/300) would give 2.9 safe.
    ("x4_denom_is_TL_boundary", dict(current_assets=0, current_liabilities=0, total_assets=300,
                                     retained_earnings=0, ebit=0, total_liabilities=100, book_equity=-100),
     (2.2, "grey")),
    # value: BE=200/TL=400 -> X4=0.5 -> z=3.77; BE/TA(200/100=2.0) would give 5.35.
    # (Same z=3.775->3.77 as the half-even case — agent hand-math claimed 3.78; live is 3.77.)
    ("x4_denom_is_TL_value", dict(current_assets=0, current_liabilities=0, total_assets=100,
                                  retained_earnings=0, ebit=0, total_liabilities=400, book_equity=200),
     (3.77, "safe")),
    # unit isolator: BE=100/TL=100 -> X4=1.0 -> z=4.3; BE/TA(100/200=0.5) would give 3.78.
    ("x4_denom_is_TL_unit", dict(current_assets=0, current_liabilities=0, total_assets=200,
                                 retained_earnings=0, ebit=0, total_liabilities=100, book_equity=100),
     (4.3, "safe")),
]


@pytest.mark.parametrize("name,kw,expected", CASES, ids=[c[0] for c in CASES])
def test_altman_z_golden(name, kw, expected):
    assert altman_z_double_prime(**kw) == expected


def test_is_keyword_only():
    """Positional call must fail — the caller relies on **bs keyword unpacking."""
    with pytest.raises(TypeError):
        altman_z_double_prime(1500, 800, 5000, 1000, 300, 3500, 1500)  # type: ignore


def test_returns_tuple_of_float_and_zone():
    r = altman_z_double_prime(**_CANON)
    assert isinstance(r, tuple) and len(r) == 2
    assert isinstance(r[0], float) and r[1] in ("safe", "grey", "distress")
