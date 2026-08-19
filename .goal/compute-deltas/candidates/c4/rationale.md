# c4 — defensive / error-handling

**Bug:** A `NaN` (or `±inf`) revenue/EBITDA value passes `isinstance(x, (int, float))`
and `bool(NaN) is True`, so it leaks through the margin guard
(`round(100*e/r, 1)` = `NaN`) and through the unchanged `_yoy`/`margins`
`isinstance` filters into `revenue_growth_pct` / `ebitda_growth_pct` /
`margin_change_pp` — poisoning the CP-1B summary and the "what changed" feed to CP-2B.

**Fix:** Sanitize each period's revenue/EBITDA at row construction with a single
`_finite(x)` helper: keep the value iff it is a finite `int`/`float`, else store
`None`. `_yoy` is untouched — a sanitized `None` no longer passes its `isinstance`
filter, the margin guard naturally yields `None`, and `margins` skips it.
`math` is imported inline (not at module scope in earnings.py).

**Row presence:** The period KEY still contributes to the `periods` union, so the
row stays present (matching live behaviour); only its non-finite field is `None`.

**Goldens:** All valid-input goldens are byte-identical — `_finite` is an identity
on finite numbers (incl. `bool`, `0`, negatives) and a no-op on the existing `None`
/`"n/a"` paths. Deliberate divergence (the fix): NaN revenue → that period's
`revenue`/`ebitda_margin`/`revenue_growth_pct` are `None`, not `NaN`; NaN EBITDA →
`ebitda_margin`/`ebitda_growth_pct` are `None`.
