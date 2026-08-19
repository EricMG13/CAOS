# c5 — maximally-testable factoring

Splits the monolith into three pure, independently-exercisable helpers so each
scoring rule and the banding can be unit-tested in isolation without driving the
full public function:

- `_leverage_points(leverage) -> (points, driver_or_None)` — exclusive >=6.0/>=5.0
  ladder; non-numeric scores 0/None. `{leverage:g}` preserved.
- `_fragility_points(fragility) -> (points, driver_or_None)` — exact, case-sensitive
  HIGH/MODERATE match.
- `_band(score) -> str` — HIGH/MODERATE/LOW thresholds, no other coupling.

`score_vulnerability` only composes them: it concatenates drivers in
leverage-then-fragility order, sums points, applies `min(_MAX_SCORE, ...)` BEFORE
banding (cap preserved), and returns `(score, band, drivers)`. No hidden state,
no I/O, fully deterministic; public signature unchanged. All five golden cases
hold, including the cap interaction and the case-sensitive `"high"` miss.
