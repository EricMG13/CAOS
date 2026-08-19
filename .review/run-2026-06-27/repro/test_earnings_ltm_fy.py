import sys
sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")
from engine.earnings import compute_deltas
from engine.periods import year, sort_key

# Same-year FY vs LTM stub. sort_key intends LTM_2025 > FY2025 (+0.5).
# earnings uses key=year, which TIES them (both 2025) -> order is set-hash dependent.
nf = {
    "revenue":    {"FY2024": 1000.0, "FY2025": 1100.0, "LTM_2025": 1150.0},
    "adj_ebitda": {"FY2024": 200.0,  "FY2025": 210.0,  "LTM_2025": 230.0},
}
out = compute_deltas(nf)
print("earnings period order:", [r["period"] for r in out["periods"]])
print("prior:", out["summary"]["prior_period"], "latest:", out["summary"]["latest_period"])
print("revenue_growth_pct:", out["summary"]["revenue_growth_pct"])

correct = sorted(set(nf["revenue"]) | set(nf["adj_ebitda"]), key=sort_key)
print("sort_key-correct order:", correct)
print("FY2025 sort_key", sort_key("FY2025"), " LTM_2025 sort_key", sort_key("LTM_2025"))
