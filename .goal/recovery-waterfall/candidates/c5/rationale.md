# Candidate c5 — maximally-testable

The cascade's two distinct decisions are split into pure, side-effect-free helpers,
leaving the public function a thin orchestrator. No hidden state, no I/O, deterministic.

- `_is_sized(amount)` — owns *only* the break predicate (numeric & strictly positive),
  so the None/0/negative/non-numeric edge of contract 4 is exercisable without building
  a whole tranche list or a cascade.
- `_settle_tranche(amount, remaining)` — pure, returns
  `(recovery_musd, recovery_pct, new_remaining)`. Recovery, own-claim percentage, and
  the floored remainder (contracts 2 & 3) are now testable in isolation against scalar
  inputs, including the half-even cases.
- `recovery_waterfall` — only walks the list in order, threads `remaining`, latches the
  sticky break, and emits `{**t, ...}` fresh dicts (contracts 1, 4, 6).

**Behavior preserved exactly.** The math is unchanged: percentage is still derived from the
*unrounded* `recov`, `round(x, 1)` (half-even) is reused verbatim (250/800 → 31.2),
`float(distressed_ev)` coercion and the `remaining > 0` / `max(0.0, ...)` guards are
identical, inputs are never mutated, and `t["amount_musd"]` is still read directly so a
missing key raises `KeyError` (contract 7). The orchestrator's branching order is line-for-line
equivalent to the original loop.

**Unit tests now enabled in isolation (not written here):**
- `_is_sized`: True for `1`, `0.5`, `0.0001`; False for `None`, `0`, `-5`, `"x"`, `[]`.
- `_settle_tranche`: `(800, 250) -> (250.0, 31.2, 0.0)` (half-even); `(0.0001, 1) -> (0.0, 100.0, ...)`;
  full claim `(200, 1000) -> (200.0, 100.0, 800.0)`; exhausted `(200, 0.0) -> (0.0, 0.0, 0.0)`.
- `recovery_waterfall`: the six golden cases (order, cascade, sticky break, fresh-dict/no-mutation, `[] -> []`).
