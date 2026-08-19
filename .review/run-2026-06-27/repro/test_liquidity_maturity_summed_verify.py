"""ADVOCATE VERIFICATION repro for liq-maturity-wall-summed-as-liquidity.

Imports the REAL engine functions and asserts the WRONG output: the
'Maturity wall' scanned amount (a USE of liquidity / debt obligation) is summed
into disclosed_liquidity_musd alongside cash + undrawn RCF (the SOURCES),
inflating both the headline liquidity figure and the interest-runway months.
"""
import sys
import asyncio

sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

from engine.liquidity import scan_liquidity, synthesize_liquidity

# One chunk: cash $300M (source), undrawn RCF $200M (source), $800M debt
# maturing in 2027 (a USE — a debt obligation, NOT available liquidity).
TEXT = (
    "The company had cash and cash equivalents of $300 million. "
    "It has $200 million of undrawn capacity under its revolving credit facility. "
    "A total of $800 million of debt matures in 2027."
)
CHUNKS = [("D-1", TEXT)]


def test_scan_captures_maturity_as_a_quantified_source():
    found = scan_liquidity(CHUNKS)
    labels = {f["source"]: f["amount_musd"] for f in found}
    print("scanned sources:", labels)
    # All three sources fire, each with a $ amount.
    assert labels["Cash and cash equivalents"] == 300.0
    assert labels["Undrawn revolving credit facility"] == 200.0
    # The defect: the maturity WALL is captured as a quantified "source".
    assert labels["Maturity wall"] == 800.0


def test_synth_sums_maturity_into_disclosed_liquidity_and_runway():
    class Hit:
        def __init__(self, cid, txt):
            self.chunk_id, self.text = cid, txt

    async def retrieve(_q, _k):
        return [Hit("D-1", TEXT)]

    class CP1:
        runtime_output = {
            "normalized_financials": {
                "adj_ebitda": {"LTM_2025": 400.0},
                "interest_coverage_ltm": 4.0,  # -> annual interest = 400/4 = 100
            }
        }

    out = asyncio.get_event_loop().run_until_complete(synthesize_liquidity(retrieve, CP1()))
    ro = out.runtime_output
    print("payload disclosed_liquidity_musd:", ro["disclosed_liquidity_musd"])
    print("payload annual_cash_interest_musd:", ro["annual_cash_interest_musd"])
    print("payload months_liquidity_covers_interest:", ro["months_liquidity_covers_interest"])
    print("CORRECT disclosed_liquidity (cash+RCF):", 500.0)
    print("CORRECT runway (500*12/100):", round(500 * 12 / 100, 1))

    # WRONG (current behaviour): 300 + 200 + 800 = 1300 reported as liquidity.
    assert ro["disclosed_liquidity_musd"] == 1300.0
    # And the runway is inflated: 1300 * 12 / 100 = 156.0 instead of 60.0.
    assert ro["months_liquidity_covers_interest"] == 156.0
    # Confirm the correct figures are NOT what the engine reports.
    assert ro["disclosed_liquidity_musd"] != 500.0
    assert ro["months_liquidity_covers_interest"] != 60.0
