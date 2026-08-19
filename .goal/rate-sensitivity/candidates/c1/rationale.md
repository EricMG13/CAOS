# Rationale — minimal-diff candidate (c1)

The existing `compute_rate_sensitivity` already satisfies every clause of the
contract and reproduces all golden cases exactly, so the minimal-diff change is
**no change**: the replacement is byte-identical to lines 37-60.

Why nothing should move:
- **None-guard** (`not isinstance(net_debt) or not isinstance(eb) or not eb`)
  already returns None iff net_debt non-numeric, latest(adj_ebitda) non-numeric,
  or EBITDA falsy (0) — covers the `"2000"` / missing / `eb=0` / `eb={}` cases.
- **base_interest** uses `isinstance(cov,...) and cov` (truthy) → None when cov is
  missing/`"2"`/0; the asymmetric `base_interest_coverage` keeps the
  isinstance-only check, so cov=0 yields base None but base_cov 0.
- Per-shock math rounds `add` (1dp) and `new_interest` (1dp) **before** reuse in
  the 2dp coverage, matching the 0.37→0.4 / 0.74→0.7 intermediate-rounding cases.
- `if base_interest`/`if new_interest` truthiness and `round(float(net_debt),1)`
  preserve the negative-net-debt / negative-EBITDA sign behaviour verbatim.

Any rewrite (e.g. swapping `if base_interest` for an `is not None` test, or
hoisting the shock loop into a comprehension) would either change a documented
truthiness edge or fail the "obviously-equivalent in a 10-second review" bar.
The assumption string is left untouched (byte-identical).
