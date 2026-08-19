"""Golden-master contract for engine.relval.build_scorecard.

Values captured from the live function (git 1aa9558) and confirmed against the
unmodified function. Self-contained bootstrap.

CP-3 RelativeValueAnalysis. Aggregates CP-1C per-metric peer percentiles into a
composite and maps it to OVERWEIGHT / NEUTRAL / UNDERWEIGHT.

Contract crux:
  1. None iff no comparison carries a numeric percentile (comparisons missing/
     empty, or none numeric).
  2. composite_percentile = round(mean(percentiles)) — rounded to an INT (no
     decimals), Python half-even: 58.5 -> 58 (NOT 59), 59.5 -> 60.
  3. recommendation: composite >= 60 OVERWEIGHT; composite < 40 UNDERWEIGHT;
     else (40..59) NEUTRAL. Exactly 60 -> OW; exactly 40 -> NEUTRAL.
  4. scorecard preserves each scored comparison's percentile VALUE AND TYPE
     (int stays int, float stays float); optional metric/label/issuer_value/
     peer_median via .get -> None when absent.
  5. peer_scope default "peers".

NOT gated (incidental): a NaN percentile passes the `isinstance` filter, so
`round(sum/len)` raises ValueError ("cannot convert float NaN to integer") and
ABORTS the run. A defensive rewrite may filter non-finite percentiles (treat as
unscored); that divergence is allowed and asserted separately, not in the gate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.relval import build_scorecard


def _c(pct, **extra):
    d = {"percentile": pct}
    d.update(extra)
    return d


def _sc(pct, metric=None, label=None, iv=None, pm=None):
    return {"metric": metric, "label": label, "percentile": pct,
            "issuer_value": iv, "peer_median": pm}


def _out(scorecard, composite, rec, n, scope="peers"):
    return {"scorecard": scorecard, "composite_percentile": composite,
            "recommendation": rec, "metrics_scored": n, "peer_scope": scope}


CASES = [
    ("three_ow",
     {"comparisons": [_c(70.0, metric="lev", label="Net Leverage", issuer_value=5.0, peer_median=6.0),
                      _c(80.0, metric="cov"), _c(90.0)], "peer_scope": "BB peers"},
     _out([_sc(70.0, "lev", "Net Leverage", 5.0, 6.0), _sc(80.0, "cov"), _sc(90.0)],
          80, "OVERWEIGHT", 3, "BB peers")),

    ("single_neutral", {"comparisons": [_c(55.0)]},
     _out([_sc(55.0)], 55, "NEUTRAL", 1)),

    ("uw", {"comparisons": [_c(30.0), _c(35.0)]},
     _out([_sc(30.0), _sc(35.0)], 32, "UNDERWEIGHT", 2)),   # mean 32.5 -> 32 (half-even)

    ("empty_comparisons", {"comparisons": []}, None),
    ("no_comparisons_key", {"peer_scope": "x"}, None),
    ("none_numeric", {"comparisons": [_c("n/a"), _c(None)]}, None),

    ("mixed_numeric", {"comparisons": [_c(70.0), _c("n/a"), _c(90.0)]},
     _out([_sc(70.0), _sc(90.0)], 80, "OVERWEIGHT", 2)),

    # band boundaries
    ("boundary_ow_60", {"comparisons": [_c(60.0)]}, _out([_sc(60.0)], 60, "OVERWEIGHT", 1)),
    ("boundary_uw_40", {"comparisons": [_c(40.0)]}, _out([_sc(40.0)], 40, "NEUTRAL", 1)),
    ("boundary_39_uw", {"comparisons": [_c(39.0)]}, _out([_sc(39.0)], 39, "UNDERWEIGHT", 1)),
    ("boundary_59_neutral", {"comparisons": [_c(59.0)]}, _out([_sc(59.0)], 59, "NEUTRAL", 1)),

    # banker's rounding at the .5 — 58.5 -> 58 is the killer (half-up would give 59)
    ("round_595_to_60", {"comparisons": [_c(59.0), _c(60.0)]},
     _out([_sc(59.0), _sc(60.0)], 60, "OVERWEIGHT", 2)),
    ("round_585_to_58", {"comparisons": [_c(58.0), _c(59.0)]},
     _out([_sc(58.0), _sc(59.0)], 58, "NEUTRAL", 2)),
    ("round_395_to_40", {"comparisons": [_c(39.0), _c(40.0)]},
     _out([_sc(39.0), _sc(40.0)], 40, "NEUTRAL", 2)),

    # int percentiles preserved as int
    ("int_percentiles", {"comparisons": [_c(70), _c(80)]},
     _out([_sc(70), _sc(80)], 75, "OVERWEIGHT", 2)),

    # bool counts (True=1/False=0) and is preserved as bool — frozen current behaviour
    ("bool_percentile", {"comparisons": [_c(True), _c(False)]},
     _out([_sc(True), _sc(False)], 0, "UNDERWEIGHT", 2)),

    ("default_scope", {"comparisons": [_c(70.0)]}, _out([_sc(70.0)], 70, "OVERWEIGHT", 1)),
]


@pytest.mark.parametrize("name,rt,expected", CASES, ids=[c[0] for c in CASES])
def test_build_scorecard_golden(name, rt, expected):
    assert build_scorecard(rt) == expected


def test_nan_percentile_currently_crashes(  # INCIDENTAL — not the equivalence gate
):
    """Live (buggy) behaviour: a NaN percentile passes isinstance, so round(sum/len)
    raises ValueError and aborts the run. A defensive rewrite may instead filter it
    (treat as unscored) — that change is allowed."""
    rt = {"comparisons": [{"percentile": float("nan")}, {"percentile": 80.0}]}
    try:
        r = build_scorecard(rt)
    except ValueError:
        return  # documented current crash
    # if it didn't crash, the fix must have filtered the NaN -> composite from 80 only
    assert r is not None and r["composite_percentile"] == 80 and r["metrics_scored"] == 1
