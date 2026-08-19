# Candidate c6 — domain-legible relative-value scorecard

Objective: make the scorecard provable to a credit analyst, byte-identical behavior.

- Docstring names the load-bearing CP-1C contract up front: percentiles arrive
  **already polarity-adjusted** (higher = stronger vs peers, e.g. lower leverage ->
  higher percentile), so we never re-sign — that is why a high composite = strong.
- States the composite is the **equal-weighted mean** percentile = a 0-100
  "strength versus peers," and that an un-percentiled metric is *excluded* (can't be
  ranked), not scored as zero.
- Bands annotated inline in analyst terms: `>=60 OVERWEIGHT` (rich/strong),
  `<40 UNDERWEIGHT` (weak), `40-59 NEUTRAL` (in line) — and notes `round()` is
  banker's rounding *by design*, so the half-even golden cases read as intentional.
- Behavior is untouched: same `(int, float)` gate, same `round(mean)` int, same
  `>=_OVERWEIGHT / <_UNDERWEIGHT` thresholds, same keys/types, same `"peers"`
  default. `if/elif/else` replaces the nested ternary purely for readability — the
  branch order/comparisons match, so every golden (incl. 60->OW, 40->NEUTRAL,
  39->UW, bool {True,False}->0 UW, mixed-numeric, int-preserving) is reproduced.
