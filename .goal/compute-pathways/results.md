# Verification Gate — results

Target: `compute_pathways` @ `caos/server/engine/downside.py:22-59`
Baseline: contract 21/21 green + 11 existing analytics tests green on the
unmodified unit. Gate per candidate: splice over lines 22-59 → `py_compile` →
21-case contract + `test_analytics.py` (11) → restore (byte-exact, asserted).

| cand | objective          | compiles | 21-case contract | analytics (11) | verdict |
|------|--------------------|----------|------------------|----------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 21/21         | ✅ 11/11       | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 21/21         | ✅ 11/11       | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 21/21         | ✅ 11/11       | **ADVANCE** (near no-op) |
| c4   | defensive          | ✅       | ✅ 21/21         | ✅ 11/11       | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 21/21         | ✅ 11/11       | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 21/21         | ✅ 11/11       | **ADVANCE** |

Contract covers the fragility ladder (breach@10→HIGH, @20→MODERATE, @30→LOW,
none→LOW, lev≥7→HIGH override), inclusive breach (`lev=6.3 → 6.3/0.9 = 7.0`),
first-breach capture, `round(s*100)` int shock pct, the `(1-s)` denominator/
multiplier directions, and cov-non-numeric → None. Golden values probe-verified.

NaN handling is **incidental, not gated** (documented): the live function leaks
NaN (a NaN leverage → NaN output, fragility silently "LOW"). c4 fixes it
(`math.isfinite` → None); the contract's NaN case allows either the leak or the
fix, so c4 passes. All six advance to judging.
