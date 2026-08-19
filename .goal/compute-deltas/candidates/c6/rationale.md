# Candidate c6 — domain-legible rewrite of `compute_deltas`

- **Names the credit concepts.** The docstring and inline comments spell out the
  three quantities an analyst reads off a tear sheet: per-period **EBITDA margin**
  (adj EBITDA / revenue), **YoY growth** (percent change over the last two
  comparable periods), and **margin change in percentage points (pp)**.
- **Calls out the pp-vs-percent trap explicitly** (25.0% → 22.2% is a 2.8pp
  compression, not an 11% drop) — the single most common unit error on a credit
  desk, now documented at the point of computation.
- **Labels the three deterioration signals** in tear-sheet order: declining
  revenue, declining adjusted EBITDA, and ≥1.0pp margin compression (the watch
  threshold), each tagged with a one-line comment.
- **Behavior is byte-identical.** Same operand order (`100 * e / r`), same
  `round(.,1)` half-even ties, same `isinstance ... and r and isinstance`
  ÷0/None guard (zero-rev → None, negative-rev → negative margin kept), same
  inclusive `<= -1.0` compression test, same `:g`/`→`/`%`/`pp` strings. Verbose
  locals (`revenue_by_period`, `margin_change_pp`) only rename — no logic moves.
- Implicit f-string concatenation preserves the exact single space before the
  `(prior→latest)` clause; golden cases (20/50/5.0 → []; -10/-20/-2.8 → 3
  signals; single/empty → []; zero-rev → None) all reproduce unchanged.
