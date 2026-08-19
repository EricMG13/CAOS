import sys
sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")
from engine.earnings import compute_deltas
from engine.periods import year, sort_key

# Two quarterly periods in the SAME year. sorted(key=year) ties them.
# A correct ordering (key=sort_key) puts Q1 before Q3.
nf = {
    "revenue":    {"Q3 2026": 120.0, "Q1 2026": 100.0},
    "adj_ebitda": {"Q3 2026": 30.0,  "Q1 2026": 25.0},
}
out = compute_deltas(nf)
print("period order:", [r["period"] for r in out["periods"]])
print("revenue_growth_pct:", out["summary"]["revenue_growth_pct"])
print("prior:", out["summary"]["prior_period"], "latest:", out["summary"]["latest_period"])

# year() ties:
print("year(Q1 2026)=", year("Q1 2026"), "year(Q3 2026)=", year("Q3 2026"))
print("sort_key(Q1 2026)=", sort_key("Q1 2026"), "sort_key(Q3 2026)=", sort_key("Q3 2026"))
