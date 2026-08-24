# Deploy V upstream defect — CP-1 admits non-finite figures into credit metrics

**Raised:** 2026-08-24 · **Component:** Deploy V, CP-1 Canonical Data Foundation
**Files (Deploy V `src/`, mirrored into 22 hashed files in the vendored bundle):**
`skills/cp-1-canonical-data-foundation/scripts/cp_tables.py`,
`skills/cp-1-canonical-data-foundation/scripts/credit_metrics.py`

**Fix upstream and re-vendor** via `build/build_package.py` (per
`DEPLOY_V_MANIFEST.json`: `"generated_from": "src/ (versioned Deploy V source)"`), so the
integrity hashes and `build_id` are regenerated together. The CAOS vendored copy is
deliberately left unmodified — patching it in place would either desynchronise
`DEPLOY_V_INTEGRITY_v1.json` or mint a `build_id` outside the build pipeline, and
`methodology_build_id` is baked into approved CP-DR plans and frozen artifact envelopes.

## Severity

**Latent in CAOS today, high if it lands.** CAOS only dynamically imports
`confidence_score` and `validate_handoff` (`caos/server/caos/methodology/bundle.py`
`_load_cpdr_script`); `credit_metrics.py` is not executed by the host. The defect matters
because CP-1 is the canonical figure authority and this is precisely the failure mode
CAOS's own engine convention exists to prevent.

## Defect

`parse_figure` admits non-finite values, and neither `ratio` nor `growth` rejects them.
NaN defeats every comparison guard: `NaN == 0` is `False` and `NaN <= 0` is `False`, so a
NaN sails through both the zero-denominator and the positive-denominator check.

Two entry routes:

1. `cp_tables.py:72-73` — `if isinstance(cell, (int, float)): return float(cell)` returns
   a float NaN or inf unchanged, with no finiteness check.
2. The string path — the figure regex `[-+]?[0-9][0-9.,]*(?:[eE][-+]?[0-9]+)?` matches
   `"1e999"`, and `float("1e999")` is `inf`.

## Verified behaviour

Executed against the vendored modules (Python 3.14):

```
parse_figure(nan)       -> nan      finite=False
parse_figure(inf)       -> inf      finite=False
parse_figure('1e999')   -> inf      finite=False
parse_figure('-1e999')  -> -inf     finite=False

ratio(100, nan, positive_denominator=True) -> nan
ratio(nan,  50, positive_denominator=True) -> nan
growth(100, nan)                           -> nan

compute_kpis({"total_debt": 1000.0, "cash_and_equivalents": 100.0,
              "ebitda": nan, "revenue": 500.0})
  total_leverage = nan
  net_leverage   = nan
```

**The dangerous case is not NaN — it is `inf`:**

```
ratio(100, inf, positive_denominator=True) -> 0.0
```

An infinite EBITDA yields **0.0x leverage**. NaN at least looks wrong on a tear sheet;
`0.0x` reads as a pristine credit and there is no artifact in the output to notice. That is
a silent wrong read on the leverage line.

## Proposed patch

Guard at both the parse boundary and the divide — the boundary stops the documented
routes, the divide stops any caller that constructs figures another way.

`cp_tables.py`, in `parse_figure`, replace lines 72-73:

```python
    if isinstance(cell, (int, float)):
        value = float(cell)
        if not math.isfinite(value):
            raise ValueError(f"{where}: {cell!r} is not a finite figure")
        return value
```

and guard the string path at the point it converts (after the separator
normalisation, where the function currently returns its parsed float):

```python
    value = -parsed if negative else parsed
    if not math.isfinite(value):
        # "1e999" satisfies the figure regex and float()s to inf. A figure that
        # cannot be represented is not a figure; refusing matches how this module
        # already refuses ambiguous decimal notation rather than guessing.
        raise ValueError(f"{where}: {cell!r} overflows the representable range")
    return value
```

(add `import math` at the top).

`credit_metrics.py`, defence in depth at the divide:

```python
def _finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def ratio(numerator, denominator, positive_denominator=False):
    if not _finite(numerator) or not _finite(denominator):
        return None
    if denominator == 0 or (positive_denominator and denominator <= 0):
        return None
    return numerator / denominator


def growth(current, prior):
    if not _finite(current) or not _finite(prior) or prior == 0:
        return None
    return current / prior - 1.0
```

Note `_finite` accepts `bool` and `0` (both legitimate figures) while rejecting NaN and
±inf. A plain `isinstance(x, (int, float))` check does not — that is the whole trap here.

## Regression checks worth adding upstream

```python
assert parse_figure_raises("1e999")            # overflow refused, not silently inf
assert ratio(100, float("inf"), True) is None  # never 0.0x leverage
assert ratio(100, float("nan"), True) is None
assert growth(100, float("nan")) is None
assert ratio(100, 50) == 2.0                   # ordinary figures unaffected
assert ratio(100, 0) is None                   # existing zero guard intact
```

## Patch status: verified, not applied

The patch above was applied to scratch copies of both modules and exercised — it is not
speculative. All 16 checks passed, and `compute_kpis` with a NaN EBITDA returned
`total_leverage=None, net_leverage=None` instead of `nan`.

Pre-existing behaviour was explicitly re-checked and is unaffected: ambiguous `"5,2"`
still raises `AmbiguousFigure`, `"5.2x"` still parses to `5.2`, `"(100)"` to `-100.0`,
`1e308` is still accepted as a legitimate large figure, and the zero and non-positive
denominator guards still return `None`.

Nothing in the CAOS vendored bundle was modified — no file under
`caos/server/caos/methodology/vendor/deploy_v/` is touched, and `build_id`
`a6f9859cec54dd1da765cac180d988ce0643698801db40fe5452ff0d56c36f2a` is unchanged.

## Related, already fixed in CAOS

The CAOS-side JSON ingest had the same class of gap and is fixed in
`caos/server/caos/sources/domain.py`: `parse_constant` only fires on the `NaN`/`Infinity`
literals, so `{"amount": 1e999}` was accepted as `inf` and re-serialised to a bare
`Infinity` that the same reader would then reject. A `parse_float` guard now rejects it.
Covered by `test_non_finite_json_values_are_rejected_before_source_set_creation`.

## Also worth reconciling (CAOS-side, not Deploy V)

`caos/server/caos/artifacts/calculations.py` defines `is_finite_number`, `safe_ratio`,
`leverage` and `variance_bridge` — all correct, and all with **zero callers**. `CLAUDE.md`
meanwhile instructs agents to gate figures through `engine.periods.is_finite_number`, but
there is no `engine/` package in the server tree. The convention as written points at a
module that does not exist and wraps helpers nothing calls.
