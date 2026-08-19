# Verification Gate — results

Target: `recovery_waterfall` @ `caos/server/engine/capstructure.py:53-76`
Baseline: git `e797760`, contract 19/19 green against the unmodified unit.
Gate per candidate: splice over lines 53-76 → `py_compile` → existing recovery
tests (`test_overlays.py -k recovery`) + characterization contract (18 hard +
1 incidental) + full `test_overlays.py` (23) → restore (byte-exact, asserted).

| cand | objective          | compiles | hard golden (18) | existing+overlays | incidental missing-key | verdict |
|------|--------------------|----------|------------------|-------------------|------------------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 18/18         | ✅ 23/23          | ✅ raises KeyError      | **ADVANCE** |
| c2   | readability-first  | ✅       | ✅ 18/18         | ✅ 23/23          | ✅ raises KeyError      | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 18/18         | ✅ 23/23          | ✅ raises KeyError      | **ADVANCE** |
| c4   | defensive          | ✅       | ✅ 18/18         | ✅ 23/23          | ⚠️ break (by design)   | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 18/18         | ✅ 23/23          | ✅ raises KeyError      | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 18/18         | ✅ 23/23          | ✅ raises KeyError      | **ADVANCE** |

All six are provably equivalent on the gated contract. c4's only "failure" in
the raw run was `test_missing_amount_key_currently_raises_keyerror` — the
explicitly **non-gated, incidental** case (it tolerates a missing `amount_musd`
key as an unsized break instead of raising, a documented safe improvement). It
passes all 18 hard golden cases, so it advances.

No candidate broke equivalence → all advance to pairwise judging (P4).
