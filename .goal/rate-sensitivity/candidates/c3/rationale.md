# c3 — performance-first rewrite of `compute_rate_sensitivity`

Honest framing: this runs ONCE per CP-2F synth over exactly 2 scenarios. There is
no hot path and no allocation pressure. None of these changes are measurable. The
edits below are defensible-but-negligible invariant hoists, not real speedups.

1. **Hoist `net_debt / 10000` out of the loop** (REAL but negligible). The factor
   is shock-independent, so `debt_per_bp = net_debt / 10000` is computed once and
   the loop multiplies by `bps`. Saves one division over 2 iterations — immaterial.
   Float-assoc check: `round((net_debt / 10000) * bps, 1)` is **byte-identical**
   (same `repr`) to the original `round(net_debt * bps / 10000, 1)` on every golden
   (2000, -2000, 37, 2550 × {100,200}). Verified before writing; safe to reorder.

2. **Cache `isinstance(cov, (int, float))` once as `cov_numeric`** (REAL but
   negligible). The original calls `isinstance` on `cov` twice (base_interest guard
   + base_interest_coverage). Now called once. Trivial.

3. **ASYMMETRY preserved exactly.** `base_interest` still requires `cov_numeric and
   cov` (truthiness); `base_interest_coverage` is `cov if cov_numeric else None`
   (NO truthiness). cov==0 → base_interest_musd=None but base_interest_coverage=0.
   Caching the predicate does not change this — `cov_numeric` only replaces the
   `isinstance` half, the `and cov` truthiness check is untouched.

4. **Everything else byte-for-byte unchanged:** None-iff guards, intermediates
   rounded before reuse (`add` → `new_interest` → `new_cov`), 1dp/2dp rounding,
   no sign guard, `round(float(net_debt), 1)`, and the assumption string.

Verdict: correctness-preserving; "perf" gains are theatre at this call volume. The
hoist is justified only as a cleaner expression of a loop invariant, not as speed.
