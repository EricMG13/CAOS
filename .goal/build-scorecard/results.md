# Verification Gate — results

Target: `build_scorecard` @ `caos/server/engine/relval.py:20-38`. Baseline:
18-case contract + 3 existing relval tests green on the unmodified unit. Gate per
candidate: splice over lines 20-38 → `py_compile` → contract (18) + relval tests
(3) → restore (byte-exact, asserted).

| cand | objective          | compiles | contract (18) | relval (3) | verdict |
|------|--------------------|----------|---------------|------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 18/18      | ✅ 3/3     | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 18/18      | ✅ 3/3     | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 18/18      | ✅ 3/3     | **ADVANCE** (negligible) |
| c4   | defensive          | ✅       | ✅ 18/18      | ✅ 3/3     | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 18/18      | ✅ 3/3     | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 18/18      | ✅ 3/3     | **ADVANCE** |

Contract locks: None-when-unscored, composite = round(mean) to INT with banker's
rounding (58.5→58, the band-boundary killer), the 60/40 bands (incl. exact-60→OW,
exact-40→NEUTRAL), percentile value+type preservation (int/float/bool), peer_scope
default. Golden values probe-verified.

NaN handling is **incidental, not gated**: a NaN percentile passes `isinstance`,
so `round(sum/len)` raises `ValueError: cannot convert float NaN to integer` and
ABORTS the CP-3 run (a CRASH, not a silent leak — worse than prior units). c4
fixes it (one-line `isinstance` → `is_finite_number`); the contract's NaN case
permits either the crash or the fix, so c4 passes. All six advance to judging.
