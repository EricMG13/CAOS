# Candidate c4 — defensive hardening

- Objective: harden against malformed inputs while keeping valid-input behaviour byte-identical.
- The original `total_assets <= 0 or total_liabilities <= 0` guard is silently bypassed by `NaN` (every `NaN` comparison is `False`), so a `NaN` denominator slips through and `NaN`/`inf` numerators propagate through the divides into the score. None inputs would raise `TypeError`.
- Fix: before any arithmetic, reject any input that is `None` or not finite (`NaN`, `+/-inf`) via `math.isfinite`, returning `None` (the function's existing "unusable" sentinel). The `None` check is ordered first because `math.isfinite(None)` raises.
- `import math` is added inline (math is not imported in distress.py); cheap and local, no module-level change required.
- The `<= 0` denominator guard, the formula (all five constants and each term), `round(..., 2)`, and `zone_for` with its strict inequalities are untouched — every golden case scores exactly as before. The added guards only ever return `None`, and never for finite inputs, so no golden case changes.
- Net effect on the contract: golden cases identical; the previously-undefined malformed cases (None / NaN / inf) now map cleanly onto the existing `None` "unusable" return instead of crashing or emitting a poisoned NaN score.
