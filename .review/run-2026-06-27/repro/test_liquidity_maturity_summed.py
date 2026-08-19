import sys, asyncio
sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")
from engine.liquidity import scan_liquidity, synthesize_liquidity

# One chunk discloses cash, undrawn RCF, AND a maturity wall, each with a $ amount.
text = (
    "The company had cash and cash equivalents of $300 million. "
    "It has $200 million of undrawn capacity under its revolving credit facility. "
    "A total of $800 million of debt matures in 2027."
)
chunks = [("D-1", text)]
found = scan_liquidity(chunks)
for f in found:
    print(f)

quantified = [f for f in found if isinstance(f["amount_musd"], (int, float))]
total = round(sum(f["amount_musd"] for f in quantified), 1)
print("disclosed_liquidity_musd (as summed by synthesize_liquidity):", total)
print("  -> true available liquidity (cash+RCF) should be 500, not", total)

# Drive the full module to show the inflated total flows into the payload.
class Hit:
    def __init__(self, cid, txt): self.chunk_id, self.text = cid, txt
async def retrieve(q, k):
    return [Hit("D-1", text)]

class CP1:
    runtime_output = {"normalized_financials": {
        "adj_ebitda": {"LTM_2025": 400.0},
        "interest_coverage_ltm": 4.0,   # -> annual interest = 100
    }}

out = asyncio.get_event_loop().run_until_complete(synthesize_liquidity(retrieve, CP1()))
ro = out.runtime_output
print("payload disclosed_liquidity_musd:", ro["disclosed_liquidity_musd"])
print("payload annual_cash_interest_musd:", ro["annual_cash_interest_musd"])
print("payload months_liquidity_covers_interest:", ro["months_liquidity_covers_interest"])
print("  -> runway w/ maturity wrongly in liquidity:", ro["months_liquidity_covers_interest"])
print("  -> correct runway (500*12/100):", round(500*12/100, 1))
