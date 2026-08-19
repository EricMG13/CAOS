# Candidate c3 — performance-first (honest)

There is no real performance win here. The function runs 3 scenarios with a
handful of divides + `round`s, once per issuer, in a deterministic non-LLM
module — not a hot path. Micro-tuning would be noise against the I/O and LLM
work that dominates a CAOS run.

So I made only two safe, near-zero changes that also read slightly cleaner:

1. Hoist the `isinstance(cov, ...)` check out of the loop into `cov_numeric`
   (the type of `cov` cannot change between iterations) — 3 checks become 1.
2. Reuse the already-computed `round(s * 100)` as `shock_pct` for both the
   scenario field and `shock_to_breach`, instead of rounding twice on breach.

Output is byte-identical to the original: same `lev/(1-s)` and `cov*(1-s)`
arithmetic, same rounding, same breach/fragility logic. No precomputation of
`1-s` or `s*100` constants that could perturb the rounded goldens. Verified by
inspection against all goldens (5.68/2.1 → MODERATE@20, 7.0 → HIGH, 6.3 →
HIGH@10, 5.0 → LOW@30, 4.0 → None, cov-missing → None coverage, lev str/None →
None). Honest verdict: this is the original, marginally de-duplicated.
