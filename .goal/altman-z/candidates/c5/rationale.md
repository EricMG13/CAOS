# c5 — maximally-testable

- Splits the body into two pure helpers so every piece is exercisable on plain numbers:
  - `_z_double_prime_terms(...)` returns `(X1, X2, X3, X4)` — each ratio testable in isolation,
    including the load-bearing `X4 = book_equity / total_liabilities` (not /TA) and
    `X1 = (CA - CL) / TA`.
  - `_z_double_prime_score(x1, x2, x3, x4)` is the weighted sum + `round(..., 2)`, so the
    five constants (3.25/6.56/3.26/6.72/1.05) and half-even rounding can be checked without
    constructing a balance sheet.
- Zone decision stays in `zone_for` (strict `>`/`<`, 2.6 and 1.1 → grey), independently testable.
- Public signature, keyword-only `*`, every parameter name, and the `None` guard
  (`total_assets <= 0 or total_liabilities <= 0`) are byte-for-byte unchanged — the
  `altman_z_double_prime(ebit=ebit, **bs)` caller is untouched.
- No hidden state; helpers are module-level, pure, and deterministic.
