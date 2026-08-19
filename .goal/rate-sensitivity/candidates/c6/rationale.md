# c6 — domain-legible rationale

An analyst can now verify the whole stress without trusting the coder:

- **Named the inputs**: net debt ($M, signed) and latest adjusted EBITDA — the two CP-1 figures the stress consumes.
- **Backing-out is explicit**: the docstring states `coverage = EBITDA / interest ⇒ interest = EBITDA / coverage`, so the reader sees base cash interest is *recovered from CP-1*, not re-modelled.
- **The shock formula is spelled out and unit-checked**: `incremental = net debt × (bps/10000)`, with `bps/10000` called out as the basis-points→decimal conversion (100bps→0.01), and the shocks (+100, +200bps) named.
- **Stressed coverage is shown**: `EBITDA / (base interest + incremental interest)`, and the comment flags that it divides by the **already-rounded** stressed interest so printed interest and printed coverage reconcile.
- **Guards/assumptions are stated, not hidden**: the None-return condition (no net debt / no usable EBITDA / coverage 0) is annotated; the deliberate **no sign guard** (net-cash → rate cut → coverage improves; negative EBITDA → negative interest) is named as intentional and symmetric.
- **The asymmetry is documented inline**: `base_interest_coverage` echoes raw coverage (no truthiness), while `base_interest` requires non-zero coverage — so reported coverage 0 yields `base_interest_coverage == 0` but `base_interest_musd == None`.

**Behavior preserved**: every executable token (expressions, rounding to 1dp/2dp, `_SHOCKS_BPS`, the `if base_interest` / `cov and` truthiness gates, key order, the assumption string) is unchanged from lines 37–60. Only the docstring and comments were added. Re-checked against all 12 golden cases (main, four None paths, cov missing/string/0, negative net debt, negative EBITDA, the 37/2.1/421 rounding case, and 2550) — all match.
