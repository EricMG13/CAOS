# c2 — readability-first

- Extracted the unsized-claim test into a named `_is_sized_claim(amount)` helper so the
  break condition reads as intent (`if not _is_sized_claim(claim)`) instead of an inline
  boolean puzzle. Same predicate: `isinstance(amount, (int, float)) and amount > 0`.
- Renamed locals for the reader: `out`→`results`, `broken`→`waterfall_broken`, `t`→`tranche`,
  `amt`→`claim`, `recov`→`recovered`. No behavioural change — pure naming.
- Kept the cascade in list order (no sort, `seniority_rank` untouched), the `min(claim, remaining)`
  recovery, the `max(0.0, remaining - claim)` floor, and the EV `float()` coercion exactly as-is.
- Comments now explain the *why*: why an unsized claim breaks the cascade, why the break is sticky,
  why `round(.., 1)` is half-even (250/800 → 31.2, not 31.3), and that the `KeyError` on a missing
  `amount_musd` is intentional per contract.
- Output rows stay fresh `{**tranche, ...}` dicts that preserve every original key and never mutate
  the input. All six golden cases (incl. the half-even `[1L 800]@250` and the unsized-break case)
  follow from unchanged arithmetic.
