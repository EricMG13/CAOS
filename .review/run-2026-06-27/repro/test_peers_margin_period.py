import sys
sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")
from engine.periods import year, sort_key

# peers._own_values picks the margin period via max(common, key=year).
# Same-year tie: FY2025 (closed) vs LTM_2025 (live trailing). max(key=year) ties
# -> returns the FIRST max encountered in set-iteration order, which can be the
# stale closed FY rather than the live LTM.
rev = {"FY2024": 1000.0, "FY2025": 1100.0, "LTM_2025": 1150.0}
eb  = {"FY2024": 200.0,  "FY2025": 199.0,  "LTM_2025": 240.0}
common = [p for p in rev if p in eb and rev[p]]

picked_year = max(common, key=year)
picked_sortkey = max(common, key=sort_key)
print("common:", common)
print("max(key=year)    ->", picked_year, " margin=", round(100*eb[picked_year]/rev[picked_year],1))
print("max(key=sort_key)->", picked_sortkey, " margin=", round(100*eb[picked_sortkey]/rev[picked_sortkey],1))
print("year(FY2025)=", year("FY2025"), "year(LTM_2025)=", year("LTM_2025"))
