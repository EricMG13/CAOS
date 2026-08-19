# Verification Gate — results

Target: `compute_rate_sensitivity` @ `caos/server/engine/macro.py:37-60`
Baseline: contract 18/18 green + 3 existing macro tests green on the unmodified
unit. Gate per candidate: splice over lines 37-60 → `py_compile` →
characterization contract (18, unfiltered) + full `test_overlays.py` (23, incl.
the 3 macro tests) → restore (byte-exact, asserted).

> Note: the first gate run filtered tests with `-k macro`, which silently
> deselected the whole contract (its ids are `test_rate_sensitivity_golden[…]`,
> no "macro" substring). Caught and re-run with the contract unfiltered — the
> table below is the corrected run.

| cand | objective          | compiles | contract (18) | full overlays (23) | verdict |
|------|--------------------|----------|---------------|--------------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 18/18      | ✅ 23/23           | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 18/18      | ✅ 23/23           | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 18/18      | ✅ 23/23           | **ADVANCE** |
| c4   | defensive          | ✅       | ✅ 18/18      | ✅ 23/23           | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 18/18      | ✅ 23/23           | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 18/18      | ✅ 23/23           | **ADVANCE** |

All six provably equivalent on the gated contract — including the cov=0
asymmetry, signed-negative scenarios, and the add-rounding cases. Notable:
- **c1** returned a byte-identical no-op (the original already satisfies the
  contract) — passes trivially but offers nothing in judging.
- **c3** hoists `net_debt/10000` out of the loop (`round(debt_per_bp*bps,1)`);
  the float-associativity reorder is **verified** byte-identical to
  `round(net_debt*bps/10000,1)` on every golden (incl. 2550→25.5/51.0,
  37→0.4/0.7), not merely asserted.
- **c4** adds a NaN/inf guard; its only divergence (NaN coverage →
  base_interest_coverage None) is outside the gated goldens.

No eliminations → all advance to judging.
