"""Review run-2026-06-26 #2/#3 — originally PROVED that periods.latest() and
metrics._headline_period() returned a STALE intra-year value on same-year labels.
Now asserts the FIXED behaviour (total order: quarter, with the LTM stub above the
full year it trails), so the artifact stays a runnable regression guard.

Run:
  cd caos && PYTHONPATH=server server/.venv/bin/python -m pytest \
    ../.review/run-2026-06-26/repro/test_period_selection.py -q
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "caos", "server"))
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

from engine.periods import latest, year  # noqa: E402
from engine.metrics import _headline_period  # noqa: E402


def test_year_still_ties_same_year_quarters():
    # year() is unchanged — both 2026. The fix lives in the intra-year tie-break.
    assert year("Q1 2026") == year("Q3 2026") == 2026


def test_latest_returns_most_recent_quarter():
    # Was 100.0 (stale Q1) before the fix; now 120.0 (Q3).
    assert latest({"Q1 2026": 100.0, "Q3 2026": 120.0}) == 120.0


def test_latest_fy_vs_ltm_same_year_picks_ltm_stub():
    # Was 500.0 (annual) before the fix; now 560.0 (the live LTM stub).
    assert latest({"FY2025": 500.0, "LTM_2025": 560.0}) == 560.0


def test_headline_period_multiple_ltm_returns_most_recent():
    # Was LTM_Q1_2025 (first) before the fix; now LTM_Q3_2025 (most recent).
    assert _headline_period(["LTM_Q1_2025", "LTM_Q3_2025"]) == "LTM_Q3_2025"
