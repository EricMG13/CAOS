# c5 — maximally-testable

Factored `compute_deltas` into three pure, independently-exercisable helpers, each
unit-testable in isolation with zero setup:

- `_margin(r, e)` — one period's EBITDA margin or None. Reproduces the original
  expression exactly: truthy-`r` guard (rejects 0/0.0 → no div-by-zero), numeric `e`,
  `round(100*e/r, 1)` half-even. Negative `r` still yields a negative margin.
- `_signals(rev_yoy, eb_yoy, margin_change)` — the deterioration strings in fixed
  rev→eb→margin order. Byte-identical f-strings (`:g`, `→`, `%`/`pp`); compresses on
  `<= -1.0` inclusive. Depends only on its args.
- `_margin_change(rows)` — YoY margin delta over the last two numeric margins, else None.

`compute_deltas` keeps the exact public signature and just composes these with the
existing `_yoy`. No hidden state, fully deterministic. Every contract clause and golden
case maps to a single helper, so a failure localizes immediately.
