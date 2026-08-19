# c4 — defensive / error-handling rewrite of `compute_rate_sensitivity`

Objective: stop malformed `nf` shapes from poisoning the output with NaN/inf,
while keeping every valid-input number byte-identical.

## The bug being closed
`NaN`/`inf` are Python `float`s, so they pass `isinstance(x, (int, float))`,
and `bool(nan) is True` — so the original truthiness gates wave them straight
through and the divides (`eb/cov`, `eb/new_interest`, `net_debt*bps`) emit
`NaN`/`inf`, which then serialize into the analyst-facing payload as garbage.

## Guards (all collapse a non-finite to `None` via one helper)
- **`_finite(x)`** — returns `x` only when it is a real `int`/`float` **and**
  `math.isfinite(x)`; otherwise `None`. `math` is not imported at module scope,
  so an inline `import math` is added inside the function (legal on a mid-module
  splice). For ordinary finite numbers `_finite` is a pure pass-through.
- **GUARD A — net_debt:** `_finite(nf.get("net_debt_ltm"))`. A `NaN`/`inf`
  net debt becomes `None`, so the existing `not isinstance(net_debt, …)` line
  returns `None` — same exit path as the already-handled non-numeric case.
- **GUARD A — EBITDA:** `_finite(latest(...))`. `NaN`/`inf` EBITDA → `None` →
  same `return None`. (`0` and empty dict still return `None` as before.)
- **GUARD A — coverage:** `_finite(nf.get("interest_coverage_ltm"))`. A
  `NaN`/`inf` coverage → `None`, so `base_interest` is `None` and the per-shock
  divides never run on a poisoned base. No `NaN`/`inf` can reach the output.

## Why every valid input is unchanged
For all gated goldens, cov/net_debt/EBITDA are ordinary finite numbers or
non-numeric (None/str/dict), and `_finite` is identity on finite numbers and
`None` on non-numbers — so each gate evaluates exactly as before. The cov=0
**asymmetry is preserved**: `_finite(0)` = `0` (0 is finite), so
`base_interest_musd` is `None` but `base_interest_coverage` is `0`. Signed
negatives (negative net_debt / negative EBITDA) flow through untouched — they
are valid frozen outputs, not "fixed". Intermediates are still rounded before
reuse; assumption string is byte-identical.

## Deliberate NaN divergence (NOT in the gated goldens)
A `NaN` coverage now maps `base_interest_coverage` → `None` instead of echoing
`NaN`. This diverges from the literal `cov if isinstance(cov,(int,float))`
rule **only for NaN**, by design: `NaN` is not a usable coverage ratio, and the
contract explicitly permits this so no `NaN` leaks downstream (e.g. into the
`:g` format in `synthesize_macro`). All finite cov values keep the exact
asymmetry.
