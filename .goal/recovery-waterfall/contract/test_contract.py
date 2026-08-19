"""Golden-master (characterization) contract for engine.capstructure.recovery_waterfall.

Freezes the CURRENT observable behaviour of the unsplit function so a best-of-N
rewrite can be proven equivalent. These are not aspirational tests — every
expected value below was captured from the live unmodified function at
git e797760. If a "cleaner" rewrite changes any of them, that is a regression,
not an improvement, unless explicitly re-pinned by a human.

Self-contained: bootstraps sys.path so it runs from anywhere
(`pytest .goal/recovery-waterfall/contract/test_contract.py`), independent of
the repo conftest. To graduate into the suite, drop the bootstrap block and move
the file under caos/tests/server/ (conftest there handles the path).

Contract crux (what a rewrite MUST keep):
  1. Absolute-priority cascade in LIST ORDER. The function does NOT sort; it
     ignores ``seniority_rank`` entirely — the caller pre-orders senior->junior.
  2. Each sized tranche recovers ``min(claim, remaining)``; consumed claim
     reduces ``remaining``, floored at 0 (never negative).
  3. ``recovery_pct`` denominator is the tranche's own ``amount_musd`` (claim),
     not the remaining EV.
  4. Rounding is Python ``round(x, 1)`` — banker's/half-even over the float
     representation. 31.25 -> 31.2, NOT 31.3. Do not swap in Decimal half-up.
  5. An unsized OR non-positive ``amount_musd`` (None, 0, negative) sets a sticky
     BREAK: that tranche AND every tranche after it get recovery_musd=None,
     recovery_pct=None (an unknown senior claim makes juniors indeterminate).
  6. ``distressed_ev`` is coerced with ``float()``; negative/zero EV -> 0.0
     recovery for all sized tranches.
  7. Output rows are fresh dicts preserving ALL original keys (``{**t}``) plus
     the two recovery keys.

NOT gated here (incidental behaviour, documented in contract.md): a missing
``amount_musd`` key currently raises KeyError. The defensive candidate may
legitimately guard it; that divergence is allowed, so it is asserted in a
separate xfail-tolerant block, not the equivalence gate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# --- bootstrap: put the server dir on sys.path, neutralise the API key ---
_SERVER = Path(__file__).resolve().parents[3] / "caos" / "server"
sys.path.insert(0, str(_SERVER))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest

from engine.capstructure import recovery_waterfall


def _t(code, rank, amt):
    """A tranche dict with an extra key, to prove non-recovery keys survive."""
    return {"code": code, "seniority_rank": rank, "amount_musd": amt, "extra": "keepme"}


# (name, tranches, distressed_ev, expected_rows) — expected_rows are the FROZEN
# golden outputs captured from the live function. Each expected row is the input
# tranche plus recovery_musd / recovery_pct.
def _row(code, rank, amt, musd, pct):
    return {"code": code, "seniority_rank": rank, "amount_musd": amt,
            "extra": "keepme", "recovery_musd": musd, "recovery_pct": pct}


CASES = [
    # typical: $1000M EV over 200/800/200 -> seniors whole, 2L wiped
    ("typical_full_recovery",
     [_t("RCF", 0, 200.0), _t("1L", 1, 800.0), _t("2L", 3, 200.0)], 1000.0,
     [_row("RCF", 0, 200.0, 200.0, 100.0),
      _row("1L", 1, 800.0, 800.0, 100.0),
      _row("2L", 3, 200.0, 0.0, 0.0)]),

    # partial: EV 500 -> RCF whole, 1L gets min(800,300)=300 -> 37.5%
    ("partial_recovery_500",
     [_t("RCF", 0, 200.0), _t("1L", 1, 800.0)], 500.0,
     [_row("RCF", 0, 200.0, 200.0, 100.0),
      _row("1L", 1, 800.0, 300.0, 37.5)]),

    # boundary: EV exactly equals the senior claim -> junior gets exactly 0
    ("boundary_ev_eq_senior",
     [_t("RCF", 0, 200.0), _t("1L", 1, 800.0)], 200.0,
     [_row("RCF", 0, 200.0, 200.0, 100.0),
      _row("1L", 1, 800.0, 0.0, 0.0)]),

    # degenerate: zero EV -> everyone 0.0 (the ``remaining > 0`` guard)
    ("ev_zero",
     [_t("RCF", 0, 200.0), _t("1L", 1, 800.0)], 0.0,
     [_row("RCF", 0, 200.0, 0.0, 0.0),
      _row("1L", 1, 800.0, 0.0, 0.0)]),

    # sign: negative EV must not produce negative recovery -> 0.0 for all
    ("ev_negative",
     [_t("RCF", 0, 200.0), _t("1L", 1, 800.0)], -50.0,
     [_row("RCF", 0, 200.0, 0.0, 0.0),
      _row("1L", 1, 800.0, 0.0, 0.0)]),

    # type coercion: int EV is float()-coerced, recovers normally
    ("ev_int_coercion",
     [_t("RCF", 0, 100.0)], 250,
     [_row("RCF", 0, 100.0, 100.0, 100.0)]),

    # unsized senior breaks the cascade: 1L (None) and everything junior -> None
    ("unsized_senior_breaks",
     [_t("RCF", 0, 200.0), _t("1L", 1, None), _t("2L", 3, 200.0)], 1000.0,
     [_row("RCF", 0, 200.0, 200.0, 100.0),
      _row("1L", 1, None, None, None),
      _row("2L", 3, 200.0, None, None)]),

    # zero amount is treated as unsized -> breaks the same way
    ("zero_amount_breaks",
     [_t("RCF", 0, 200.0), _t("1L", 1, 0.0), _t("2L", 3, 200.0)], 1000.0,
     [_row("RCF", 0, 200.0, 200.0, 100.0),
      _row("1L", 1, 0.0, None, None),
      _row("2L", 3, 200.0, None, None)]),

    # negative amount is also non-positive -> breaks
    ("negative_amount_breaks",
     [_t("RCF", 0, 200.0), _t("1L", 1, -100.0), _t("2L", 3, 200.0)], 1000.0,
     [_row("RCF", 0, 200.0, 200.0, 100.0),
      _row("1L", 1, -100.0, None, None),
      _row("2L", 3, 200.0, None, None)]),

    # empty stack -> empty list
    ("empty", [], 1000.0, []),

    # ROUNDING half-even, the killer case: 250/800 = 31.25 -> round(.,1) = 31.2
    # (NOT 31.3). A Decimal-half-up rewrite fails here.
    ("rounding_halfeven_3125",
     [_t("1L", 1, 800.0)], 250.0,
     [_row("1L", 1, 800.0, 250.0, 31.2)]),

    # rounding: 100/3 = 33.33.. -> 33.3 pct, recov 1.0
    ("rounding_pct_third",
     [_t("X", 0, 3.0)], 1.0,
     [_row("X", 0, 3.0, 1.0, 33.3)]),

    # rounding: clean 62.5 stays 62.5
    ("rounding_pct_625",
     [_t("X", 0, 80.0)], 50.0,
     [_row("X", 0, 80.0, 50.0, 62.5)]),

    # rounding musd: recov 333.333 -> 333.3 musd, 33.3 pct
    ("rounding_musd_third",
     [_t("X", 0, 1000.0)], 333.333,
     [_row("X", 0, 1000.0, 333.3, 33.3)]),

    # extreme large magnitudes round-trip exactly
    ("extreme_large",
     [_t("RCF", 0, 1e9), _t("1L", 1, 5e8)], 2e9,
     [_row("RCF", 0, 1e9, 1e9, 100.0),
      _row("1L", 1, 5e8, 5e8, 100.0)]),

    # extreme tiny: recov 0.0001 -> musd rounds to 0.0 BUT pct = 100.0
    ("extreme_tiny",
     [_t("X", 0, 0.0001)], 1.0,
     [_row("X", 0, 0.0001, 0.0, 100.0)]),
]


@pytest.mark.parametrize("name,tranches,ev,expected", CASES, ids=[c[0] for c in CASES])
def test_recovery_waterfall_golden(name, tranches, ev, expected):
    assert recovery_waterfall(tranches, ev) == expected


def test_does_not_mutate_input():
    """Rows are fresh dicts; the caller's tranches are untouched."""
    tranches = [_t("RCF", 0, 200.0), _t("1L", 1, 800.0)]
    before = [dict(t) for t in tranches]
    recovery_waterfall(tranches, 500.0)
    assert tranches == before


def test_ignores_seniority_rank_uses_list_order():
    """seniority_rank is NOT used; pure list order drives the cascade. Here the
    'junior' rank sits first in the list and is paid first."""
    rows = recovery_waterfall(
        [_t("JUNIOR", 99, 200.0), _t("SENIOR", 0, 800.0)], 200.0)
    assert rows[0]["code"] == "JUNIOR" and rows[0]["recovery_pct"] == 100.0
    assert rows[1]["code"] == "SENIOR" and rows[1]["recovery_pct"] == 0.0


def test_missing_amount_key_currently_raises_keyerror():
    """INCIDENTAL behaviour, NOT part of the equivalence gate. The live function
    indexes t['amount_musd'] and raises KeyError when absent. Documented so a
    reviewer knows a defensive candidate that guards this is an allowed change,
    not a regression."""
    with pytest.raises(KeyError):
        recovery_waterfall([{"code": "X", "seniority_rank": 0}], 100.0)
