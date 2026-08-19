# Verification Gate — results

Target: `assess_fit` @ `caos/server/engine/portfoliofit.py:22-35`. Baseline:
16-case contract + 4 existing portfolio tests green on the unmodified unit. Gate
per candidate: splice over lines 22-35 → `py_compile` → contract (16) + portfolio
tests (4) → restore (byte-exact, asserted).

| cand | objective          | compiles | contract (16) | portfolio (4) | verdict |
|------|--------------------|----------|---------------|---------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 16/16      | ✅ 4/4        | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 16/16      | ✅ 4/4        | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 16/16      | ✅ 4/4        | **ADVANCE** (`_FIT.get` collapse) |
| c4   | defensive          | ✅       | ✅ 16/16      | ✅ 4/4        | **ADVANCE** (no guard — honest) |
| c5   | maximally-testable | ✅       | ✅ 16/16      | ✅ 4/4        | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 16/16      | ✅ 4/4        | **ADVANCE** |

Contract locks: None-when-recommendation-unknown, the _FIT sleeve/sizing map, the
inclusive `>= 6.0` leverage flag with `{leverage:g}` format, composite passthrough,
the constant note. Golden values probe-verified.

**No bug here, and c4 said so.** Unlike the division/round units, assess_fit has
no NaN-crash or NaN-leak: a NaN leverage simply fails `NaN >= 6.0` (no flag, no
crash), a non-numeric fails isinstance, an unknown recommendation returns None.
c4 (defensive) correctly declined to add a guard for a non-problem — same posture
as score_vulnerability. All six advance to judging.
