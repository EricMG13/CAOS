# Merge notes — winner c6, + a NARROW NaN graft (write it; don't take c4's)

**Winner:** c6 (domain-legible). `winner.diff` applies to
`caos/server/engine/earnings.py:37-71`. **Comment/docstring-only** — zero logic
change, proven by the 13-case contract + 9 earnings tests. Its headline is the
pp-vs-percent conflation call-out (c6:11-14), the most error-prone thing in this
function for an analyst.

### NaN fix — RECOMMENDED, but write the narrow version (c4 was eliminated)
The bug is real: a NaN revenue/EBITDA passes `isinstance` and `bool(NaN)` is True,
so it leaks NaN into `ebitda_margin` and (via `_yoy`/`margins`) into
`revenue_growth_pct` / `ebitda_growth_pct` / `margin_change_pp` — poisoning the
CP-1B summary and the CP-2B "what changed" feed.

c4 tried to fix it but **failed the gate**: it used
`_finite(x) = isinstance(x,(int,float)) and math.isfinite(x)` and stored
`x if _finite(x) else None`, which also collapses the string `"n/a"` to `None`,
changing the `mixed_nonnumeric` valid golden (`revenue: "n/a"`).

**Correct graft** — collapse only non-finite NUMBERS, leave non-numerics alone:
```python
import math  # add to earnings.py imports (module currently has none)
...
for p in periods:
    r, e = rev.get(p), eb.get(p)
    if isinstance(r, (int, float)) and not math.isfinite(r):  # NaN/inf -> drop
        r = None
    if isinstance(e, (int, float)) and not math.isfinite(e):
        e = None
    # ... existing margin guard + row append, now on sanitized r, e
```
This maps NaN/inf→None (so the margin guard yields None and `_yoy`/`margins`
isinstance-filters skip the period) while a str like `"n/a"` passes through
unchanged (it's not a float). Result: NaN cases return None (not NaN) in margin
AND growth AND margin_change; every existing golden — including `mixed_nonnumeric`
and `negative_revenue` — stays identical. Verified against the contract.

This is the same NaN-divide class as the engine sweep ([[caos-finding-gate-hardening]]):
guard a CP-1 value before it divides/multiplies. The lesson c4 illustrates:
sanitize on `not math.isfinite(number)`, NOT on "fails an is-finite-number predicate",
or you silently drop legitimately-typed non-numeric placeholders.

### From c5 (maximally-testable) — optional
- Pure `_margin(r,e)` / `_signals(rev_yoy,eb_yoy,margin_change)` / `_margin_change(rows)`
  (c5:1-46): independently unit-testable; `_signals` is the natural home for
  exercising the exact deterioration strings. Graft if the signal set grows. Not now.

### Not recommended
- c1 (no-op); c3 (perf, honestly negligible); c2 (good, but c6 dominates legibility
  at smaller blast).
