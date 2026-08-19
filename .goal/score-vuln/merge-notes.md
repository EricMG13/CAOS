# Merge notes — winner c6, cherry-picks

**Winner:** c6 (domain-legible). `winner.diff` applies to
`caos/server/engine/refinancing.py:19-37`. **Comment-only** rewrite — not one byte
of logic, control flow, or the driver/band expressions changed. Proven by the
25-case contract + 2 existing refinancing tests. It turns the (previously
undocumented) function into a readable CP-3D LME-vulnerability rubric: each
leverage/fragility threshold's credit meaning, each band's interpretation, and a
note on why the `_MAX_SCORE` cap currently never binds.

### No defensive graft recommended (deliberate — different from prior units)
The previous four units each had a real latent NaN bug (a NaN ratio survived an
`isinstance` guard and poisoned a **division**). **This function does no
division.** A NaN or bool `leverage` already falls through harmlessly (NaN ≥ 6.0
and True ≥ 6.0 are both False → no points, no driver). c4's explicit
`bool`/NaN guard is therefore decoration over a non-problem — grafting it adds
code and a reader's "why is this here?" for zero behavioral gain. **Do not graft.**
(c4's *comment* explaining why bool/NaN are already safe has some teaching value;
if you want it, fold the one-line comment into c6, not the guard.)

### Optional, low priority
- **c2's named threshold constants** (`_HIGH_LEVERAGE_TURNS = 6.0` etc.): worth
  extracting only if these cutoffs get reused or tuned per sector. Today they
  appear once; inlined-with-a-comment (c6) is the lazier, equally-clear choice.
- **c5's pure helpers** (`_leverage_points`/`_fragility_points`/`_band`): graft if
  the rubric grows a third driver (e.g. the maturity-wall term the module docstring
  flags as out-of-scope) and you want each rule unit-tested in isolation. Not now.

### Not recommended
- c1 (minimal-diff) byte-identical no-op; c3 (perf) `min()`→`if` no-op — neither
  adds analyst value.
