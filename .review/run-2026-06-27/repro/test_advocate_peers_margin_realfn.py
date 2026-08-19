"""ADVOCATE repro: call the REAL peers._own_values and assert the WRONG margin.

Claim under test: peers.py:52 picks the EBITDA-margin period with
`max(common, key=year)`. On a same-year tie (closed FY2025 vs live LTM_2025),
year('FY2025') == year('LTM_2025') == 2025, so max() keeps whichever the
iterator yields first instead of the more-recent LTM. The codebase already built
`periods.sort_key` (year, intra-year rank) precisely to break this tie with LTM
above the FY it trails, and fixed the sibling callsites in run-1 — but peers.py
still uses the weaker `year` key.

This drives _own_values['ebitda_margin'], which feeds _percentile (line 125) and
the bottom-quartile outlier flag (line 126) and the CP-1C-PEER finding.
"""
import sys
sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

from engine.peers import _own_values
from engine.periods import year, sort_key
from engine.schemas import ModulePayload


def _cp1(revenue, adj_ebitda):
    return ModulePayload(
        module_id="CP-1", module_name="FactPack", owned_object="fact_pack",
        runtime_output={"normalized_financials": {
            "revenue": revenue, "adj_ebitda": adj_ebitda,
        }},
    )


def test_stale_fy_margin_when_ltm_is_live():
    # Insertion order = chronological as a fact pack would build it:
    # FY2024, FY2025 (closed), LTM_2025 (live trailing). Live LTM margin = 20.9%.
    rev = {"FY2024": 1000.0, "FY2025": 1100.0, "LTM_2025": 1150.0}
    eb = {"FY2024": 200.0, "FY2025": 199.0, "LTM_2025": 240.0}

    out = _own_values(_cp1(rev, eb))

    # What sort_key (the canonical total order) WOULD pick = LTM_2025.
    correct_period = max(rev, key=sort_key)
    correct_margin = round(100 * eb[correct_period] / rev[correct_period], 1)

    print("year(FY2025)=", year("FY2025"), "year(LTM_2025)=", year("LTM_2025"),
          " -> tie:", year("FY2025") == year("LTM_2025"))
    print("sort_key(FY2025)=", sort_key("FY2025"), "sort_key(LTM_2025)=", sort_key("LTM_2025"))
    print("correct (sort_key) period:", correct_period, " margin=", correct_margin)
    print("_own_values returned ebitda_margin=", out["ebitda_margin"])

    # PROVE the defect: the real function returns the stale FY2025 margin (18.1),
    # not the live LTM_2025 margin (20.9) the canonical sort_key would select.
    assert out["ebitda_margin"] == 18.1, f"got {out['ebitda_margin']}"
    assert out["ebitda_margin"] != correct_margin, "no defect: matched sort_key"
    print("DEFECT CONFIRMED: returned stale FY margin 18.1, correct LTM margin 20.9 "
          f"(swing {round(correct_margin - out['ebitda_margin'],1)}pp)")


def test_ltm_q_above_q_same_year():
    # LTM_Q3_2025 should rank above FY2025 too; year() ties all three.
    rev = {"FY2025": 1100.0, "Q3_2025": 800.0, "LTM_Q3_2025": 1140.0}
    eb = {"FY2025": 199.0, "Q3_2025": 150.0, "LTM_Q3_2025": 238.0}
    out = _own_values(_cp1(rev, eb))
    print("multi-tie returned:", out["ebitda_margin"])
