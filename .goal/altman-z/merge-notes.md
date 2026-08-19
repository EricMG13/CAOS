# Merge notes — winner c6, cherry-picks

**Winner:** c6 (domain-legible). `winner.diff` applies to
`caos/server/engine/distress.py:36-55`. Docstring-and-comments rewrite over the
**identical formula and control flow** — zero behavioral change, proven by the
28-case hardened contract (incl. all 10 adversarial mutation isolators) + 7
existing distress tests.

### From c4 (defensive) — RECOMMENDED graft (real latent bug, 4th occurrence)
- **None/NaN/inf rejection** (`c4/replacement.py:19-35`): an up-front loop over
  all seven inputs returning None on `v is None or not math.isfinite(v)`. This is
  the same bug class already fixed in `_interest_runway_months`,
  `compute_rate_sensitivity` (NaN ratios), now here: a NaN `total_assets` (or any
  NaN input) **passes** the `<= 0` guard because NaN comparisons are False, then
  poisons every divide → a NaN Z'' and a wrong/garbage zone into the CP-1 distress
  block. Inputs originate from XBRL facts (edgar_cp1.py:295 via `**bs`); a
  malformed/degenerate filing can produce non-finite values. **Recommend grafting**
  (move `import math` to distress.py's import block, not inline). Order matters:
  the `None` check must precede `math.isfinite` (isfinite(None) raises).
- Note for the contract: with the guard, a NaN/None input returns None — add a
  few NaN/None cases to the suite to lock it (mirrors what we did for the runway
  and rate-sensitivity units).

### From c5 (maximally-testable) — optional, later
- **Pure `_z_double_prime_terms` + `_z_double_prime_score`**
  (`c5/replacement.py:34-65`): the four ratios and the weighted sum as pure
  functions on plain numbers, unit-testable without the keyword-only wrapper.
  Worth grafting if the model gains variants (e.g. the classic Z or Z' with the
  market-value/sales terms) and you want to share the scoring spine. Not now — the
  28-case contract already exercises the math end-to-end (YAGNI).

### Not recommended
- c1 (minimal-diff) and c3 (performance-first): byte-identical no-ops. Honest, but
  add nothing.
- c2 (readability-first): solid — names the ratios and flags X4=/TL — but c6
  dominates on analyst legibility (full Z'' polynomial + zone-strictness
  documentation) at the same blast radius.
