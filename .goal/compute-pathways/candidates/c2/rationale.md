# Candidate c2 — readability-first

- Renamed terse locals to intent-revealing names (`lev`/`cov`/`sl`/`sc` →
  `current_leverage` / `current_coverage` / `stressed_leverage` / `stressed_coverage`)
  so the math reads as finance, not algebra.
- Extracted a small private helper `_stressed_scenario(...)` so the loop body says
  *what* it does (one scenario) and the helper carries the *how* (the (1-shock) math
  and the coverage-numeric guard), flattening the per-iteration nesting.
- Added why-comments at the three decision points: the None guard, the
  first-breach capture, and each fragility bucket — including an explicit note that
  the `lev >= _BREACH_X` clause is intentionally redundant (kept, per contract).
- Behaviour is byte-for-byte identical: same `round(lev/(1-s),2)` (denominator),
  same `round(cov*(1-s),2)` else None, same `round(s*100)`, same first `>= 7.0`
  breach, same 10/20 cutoffs, same output keys. Golden cases (5.68/2.1→MODERATE@20,
  7.0→HIGH@10, 6.3→HIGH@10, 5.0→LOW breach@30, 4.0→LOW no breach) all preserved.
- `_stressed_scenario` is module-private and self-contained; it relies only on the
  passed args, so no new imports or globals are introduced.
