# c2 — readability-first rationale

- Extracted a `_shock_scenario` helper so the per-shock pipeline (incremental
  interest -> stressed interest -> stressed coverage) reads top-to-bottom as
  three named steps instead of three terse ternaries inside a loop.
- Renamed `eb`->`ebitda`, `cov`->`coverage`, `add`->`incremental_interest`,
  `new_*`->`stressed_*` so each value says what it is; the loop became a list
  comprehension over `_SHOCKS_BPS`.
- Why-comments mark the three contract traps: the EBITDA-falsy gate (it is the
  divisor), the round-before-reuse precision ladder (1dp interest, 2dp
  coverage, each rounded value feeding the next), and the no-sign-guard intent
  for negative net debt / EBITDA.
- **cov=0 asymmetry preserved and documented:** `base_interest` still requires
  `isinstance(coverage,...) and coverage` (truthy), so coverage 0 yields
  `base_interest_musd = None`. But `base_interest_coverage` is left as
  `coverage if isinstance(coverage,(int,float)) else None` — numeric-only, NOT
  truthiness-gated — so coverage 0 surfaces as `0`. A comment explains the two
  fields answer different questions (input echo vs. computed value), so a future
  reader does not "fix" it into matching.
- Behaviour is byte-for-byte identical: traced all golden cases (g1, the four
  None inputs, cov missing/str, cov=0, negative net debt, negative EBITDA,
  37/2.1/421, 2550) — every field matches. Assumption string unchanged.
