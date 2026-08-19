# c3 — performance-first rationale

Goal: minimize per-iteration work/allocations for large tranche lists, without
touching any contract point or golden value.

Changes (real vs negligible at this scale):

- **Hoist `out.append` into a local `append`.** Drops one attribute lookup per
  row. *Real* in CPython for hot loops, but **negligible here** (<10 tranches).
- **Short-circuit after break.** Once an unsized claim is hit we stop running the
  `broken`/`if broken` branch test on every later row: emit the current row, drain
  the tail (`tranches[i+1:]`) in a tight loop, and `return`. Removes one boolean
  test + branch per remaining row and skips the per-row recovery math entirely
  (contract pt 3). *Real* win for long lists with an early break; the `[i+1:]`
  slice is one extra allocation, paid once, dwarfed by the per-row dict copies.
- **Inline the `max(0.0, ...)` floor** as a compare-and-set (`if remaining < 0.0`).
  Avoids a `max()` call per sized row. *Negligible* — pure micro-tidy, kept only
  because it reads as cheap as the original.

Honest note: the dominant cost is the unavoidable `{**t, ...}` copy per row
(contract pt 6 — fresh dicts, no input mutation), which none of these touch. At
the real workload (<10 tranches) every gain above is immeasurable; the rewrite
is performance-flavored but its true value is identical behavior with no
regressions. Rounding stays `round(x, 1)` (half-even, e.g. 250/800=31.25→31.2),
`float()` coercion, sticky break, and KeyError-on-missing all preserved.
