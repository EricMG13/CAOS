# Verification Gate — results

Target: `_interest_runway_months` @ `caos/server/engine/liquidity.py:38-52`
Baseline: contract 19/19 green + 4 existing liquidity tests green on the
unmodified unit. Gate per candidate: splice over lines 38-52 → `py_compile` →
existing liquidity/runway tests + characterization contract (19) + full
`test_overlays.py` (23) → restore (byte-exact, asserted).

| cand | objective          | compiles | contract+existing (23) | full overlays (23) | verdict |
|------|--------------------|----------|------------------------|--------------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 23/23               | ✅ 23/23           | **ADVANCE** |
| c2   | readability-first  | ✅       | ✅ 23/23               | ✅ 23/23           | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 23/23               | ✅ 23/23           | **ADVANCE** |
| c4   | defensive          | ✅       | ✅ 23/23               | ✅ 23/23           | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 23/23               | ✅ 23/23           | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 23/23               | ✅ 23/23           | **ADVANCE** |

All six provably equivalent on the gated contract (incl. the rounded-denominator
killer `(100, eb=10, cov=3) → (3.3, 363.6)` and the three divide-by-zero guards).
c3's guard reorder (coverage-check before the `latest()` scan) and c4's added
NaN/inf rejection both preserve every golden value. No eliminations → all advance.
