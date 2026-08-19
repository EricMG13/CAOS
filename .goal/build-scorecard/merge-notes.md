# Merge notes — winner c6, + c4's one-line crash fix (RECOMMENDED)

**Winner:** c6 (domain-legible). `winner.diff` applies to
`caos/server/engine/relval.py:20-38`. Comments + one rename (`scored`→`ranked`),
zero logic change — proven by the 18-case contract + 3 relval tests. Names the
CP-1C polarity contract, the equal-weighted-mean composite, the 60/40 bands, and
the not-scored-as-zero nuance.

### From c4 (defensive) — RECOMMENDED graft (real run-aborting crash)
- **`isinstance(percentile, (int,float))` → `is_finite_number(percentile)`**
  (`c4/replacement.py:15`). A NaN percentile is a float, so it passes the
  `isinstance` filter, enters `scored`, and `round(sum/len)` raises
  `ValueError: cannot convert float NaN to integer` — which **aborts the whole
  CP-3 run** (the caller `synthesize_relative_value` has no try/except; the
  run-level except marks the run failed). This is a CRASH, worse than the silent
  NaN leaks in earlier units. `is_finite_number` rejects NaN/±inf while accepting
  bool/int/0/float, so every valid percentile (including the bool and int golden
  cases) still scores; a NaN/inf is treated as unscored. All-NaN → None.
  **Recommend grafting.** Add `from engine.periods import is_finite_number` to
  relval.py's import block (not inline) and swap the one filter line.

### From c5 (maximally-testable) — optional
- Pure `_scored` / `_composite` / `_recommend` (`c5/replacement.py:1-31`): the
  band map and the mean→int are independently unit-testable. Graft if the bands
  or the composite formula grow (e.g. metric weighting). Not now.

### Combined recommendation
**c6 + c4's one-line `is_finite_number` filter** = best legibility AND the
run-aborting crash closed, both tiny. Same NaN-divide/round class as the engine
sweep ([[caos-finding-gate-hardening]]): guard a CP-1-derived value before it
feeds round()/division.

### Not recommended
- c1 (no-op); c3 (single-pass fold, honestly negligible); c2 (good, but c6
  dominates legibility at comparable blast).
