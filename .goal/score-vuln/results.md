# Verification Gate — results

Target: `score_vulnerability` @ `caos/server/engine/refinancing.py:19-37`
Baseline: contract 25/25 green + 2 existing refinancing tests green on the
unmodified unit. Gate per candidate: splice over lines 19-37 → `py_compile` →
25-case contract + existing refinancing/vulnerability tests → restore
(byte-exact, asserted).

| cand | objective          | compiles | 25-case contract | existing (2) | verdict |
|------|--------------------|----------|------------------|--------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 25/25         | ✅ 2/2       | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 25/25         | ✅ 2/2       | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 25/25         | ✅ 2/2       | **ADVANCE** (near no-op) |
| c4   | defensive          | ✅       | ✅ 25/25         | ✅ 2/2       | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 25/25         | ✅ 2/2       | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 25/25         | ✅ 2/2       | **ADVANCE** |

The 25-case contract isolates every realistic mutation for this unit: both
leverage thresholds (6.0/5.0 inclusive), elif-exclusivity (6.0 → +4 only),
the `{leverage:g}` driver formatting (6.0→"6", 5.68→"5.68"), case-sensitive
fragility match, and both band cutoffs (6→HIGH, 3→MODERATE). Golden values were
probe-verified against the live function before gating.

Notes:
- c1 = byte-identical no-op; c3 = only `min()` → `if` branch (behaviorally a no-op).
- c4 adds explicit `bool` + NaN guards — but they are **behavioral no-ops**: the
  original already falls through on bool (True ≥ 6.0 is False) and NaN
  (NaN ≥ 6.0 is False). Unlike the prior 4 units, this function does NO division,
  so there is no NaN-poisoning bug to fix here.

All six provably equivalent → all advance to judging.
