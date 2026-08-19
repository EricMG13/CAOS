# Candidate c1 — minimal-diff

The original `build_scorecard` is already optimal for every contract point, so the
honest minimal diff is the identity rewrite (zero behavioral change, zero textual
change over lines 20-38).

Why no edit is the right call:
- `round(mean)` is Python's banker's rounding on a float → int; it already yields
  58.5→58, 59.5→60, 32.5→32. Swapping in any other rounding breaks a golden.
- `>= _OVERWEIGHT` / `< _UNDERWEIGHT` reproduce the 60→OW, 40→NEUTRAL, 39→UW bands.
- `isinstance(x, (int, float))` intentionally admits `bool`, so `{True,False}`→0→UW;
  reading `c["percentile"]` (not a recomputed value) preserves int-vs-bool type.
- Optional `metric/label/issuer_value/peer_median` via `.get()` → `None`; `peer_scope`
  defaults `"peers"`. All present and correct.

A rewrite that "improves" anything (e.g. `statistics.mean`, a ternary refactor, or
guarding NaN) would either change types, alter half-even rounding, or add diff with
no contract benefit. Smallest equivalent change = no change.
