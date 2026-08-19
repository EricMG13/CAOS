# Candidate c4 — defensive / error-handling

**Bug:** `NaN` is a `float`, so it passes the old
`isinstance(c.get("percentile"), (int, float))` filter and enters `scored`.
`round(sum(...)/len(...))` then raises `ValueError: cannot convert float NaN to
integer`, aborting the whole CP-3 run — the caller has no try/except, so the
crash is total, not degraded.

**Fix:** swap the membership test for `engine.periods.is_finite_number`, which
rejects `NaN`/`±inf` while still accepting `bool`/`int`/`0`/`float`. A non-finite
percentile is now treated as unscored, identical to a missing or non-numeric one.
The import is inline so the splice over lines 20-38 is self-contained (no need to
add a module-level import).

**Goldens preserved:** every valid percentile still scores (bool `True/False`,
ints, plain floats), so `{70,80,90}→80 OW`, `{55}→55 NEUTRAL`, `bool→0 UW`,
default scope `"peers"`, and all-`None` cases are unchanged. Per the contract's
deliberate divergence, `[{NaN},{80.0}]` now yields composite 80 / OVERWEIGHT /
`metrics_scored 1` instead of crashing; all-`NaN` returns `None`.
