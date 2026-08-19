# c3 — performance-first rewrite of `_interest_runway_months`

Honest framing: this runs **once per liquidity synth** and does a few dict lookups
plus two scalar divides. There is no hot path. The only real micro-saving available
is avoiding `latest()`'s dict scan when it can't matter; everything else is wash.

- **REAL (tiny): defer `latest(adj_ebitda)` behind the coverage guard.** Original
  computes `eb = latest(...)` eagerly (line 46) before the guard. `latest()` iterates
  the period dict to find the max trailing-year key; `interest_coverage_ltm` is a flat
  `dict.get`. By checking coverage is numeric-and-nonzero **first**, a bad/absent/zero
  coverage now short-circuits and never pays for the `latest()` scan. Coverage being
  bad is exactly the case where the scan would have been wasted.
- **Equivalence preserved.** `latest()` is a pure read (no side effects), so deferring
  it only avoids work — every golden return value is byte-identical. The `cov`
  numeric+truthy test and the `eb` numeric test are the same two predicates as the
  original `and`-chain, just split so the cheaper one (and the one that gates the scan)
  is evaluated first.
- **Unchanged on purpose:** guard (a) order, `round(eb/cov,1)` then divide-by-rounded
  `cash_interest`, the falsy-`cash_interest` guard, and the no-output-clamp behaviour
  (zero/negative liquidity and negative coverage flow straight through). Touching any
  of these would be a correctness change, not a perf win.
- **NEGLIGIBLE / not done:** caching lookups in locals, micro-reordering the scalar
  math, or hoisting `isinstance` tuples — pure theatre at this call frequency. Skipped.

Net: ~identical to the original with one defensible reorder; no correctness or clarity
traded.
