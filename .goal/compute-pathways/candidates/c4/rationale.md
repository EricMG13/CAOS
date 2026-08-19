# c4 — defensive / error-handling

Fixes a latent NaN-leak in `compute_pathways`. A NaN `net_leverage_adj_ltm`
passes `isinstance(lev, (int, float))` (NaN *is* a float), and `NaN >= 7.0` is
False, so the function leaked NaN into `current_net_leverage` and every
`stressed_net_leverage`, while `fragility` silently read "LOW" — an
unknown-leverage issuer mislabeled low-fragility, feeding garbage downstream
(CP-3D).

- **Guard 1 (leverage):** widened the existing reject to
  `not isinstance(lev, (int, float)) or not math.isfinite(lev)`. Non-finite
  (NaN/inf) leverage now returns `None`, identical to the missing-leverage path.
- **Guard 2 (coverage):** `cov_ok = isinstance(cov, (int, float)) and math.isfinite(cov)`.
  A NaN/inf coverage now yields `stressed_interest_coverage = None` per scenario,
  consistent with the existing non-numeric-coverage behaviour (no NaN leak).
- `import math` added inline (math was not imported in downside.py).
- All valid-input goldens are byte-identical: finite numbers pass `isfinite`, so
  the leverage path, scenario math, breach/fragility logic, and output dict are
  untouched. Negatives stay un-clamped (isfinite is True for -5.0/-2.1).
- **Deliberate divergence (the fix):** `{NaN,2.0}` -> `None` (was: NaN leak);
  `{5.68, NaN}` -> stressed coverage `None` each (was: NaN leak). `inf` handled
  the same way. `bool` left as-is (out of scope).
