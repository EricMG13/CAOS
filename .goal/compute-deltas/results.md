# Verification Gate — results

Target: `compute_deltas` @ `caos/server/engine/earnings.py:37-71` (helper `_yoy`
at 25-34 stays in the prefix). Baseline: 13-case contract + 9 existing earnings
tests green on the unmodified unit. Gate per candidate: splice over lines 37-71 →
`py_compile` → contract (13) + `test_earnings.py` (9) → restore (byte-exact).

| cand | objective          | compiles | contract (13)  | earnings (9) | verdict |
|------|--------------------|----------|----------------|--------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 13/13       | ✅ 9/9       | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 13/13       | ✅ 9/9       | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 13/13       | ✅ 9/9       | **ADVANCE** (negligible) |
| c4   | defensive          | ✅       | ❌ 12/13       | ✅ 9/9       | **ELIMINATED** |
| c5   | maximally-testable | ✅       | ✅ 13/13       | ✅ 9/9       | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 13/13       | ✅ 9/9       | **ADVANCE** |

**c4 ELIMINATED — the gate caught an over-broad fix.** c4 targeted the real NaN
leak (NaN revenue/EBITDA → NaN margin/growth) but sanitized with
`_finite(x) = isinstance(x,(int,float)) and math.isfinite(x)` and stored
`x if _finite(x) else None` in the row (c4:18,22). That collapses the *string*
`"n/a"` to `None` too, breaking the `mixed_nonnumeric` golden (which freezes
`revenue: "n/a"` in the row) — a divergence on a VALID input, not the permitted
NaN divergence. The correct fix collapses only NON-FINITE NUMBERS:
`None if isinstance(x,(int,float)) and not math.isfinite(x) else x`
(maps NaN/inf→None, leaves "n/a" untouched). The bug is real; c4's implementation
over-reached. I'll graft the narrow version onto the winner.

c1/c2/c3/c5/c6 are provably equivalent → advance to judging.
