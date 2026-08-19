# c4 — defensive / error-handling

Objective: harden `_interest_runway_months` against malformed inputs while keeping
every golden (valid-input) output byte-identical.

## Guards added (all route malformed shapes to `(None, None)`)

1. **NaN/inf liquidity** — guard (a) now requires `math.isfinite(disclosed_liquidity)`
   in addition to `isinstance(..., (int, float))`. Previously NaN/inf liquidity
   passed `isinstance` and produced a NaN/inf month count. Every frozen liquidity
   (500, 100, 0, -500, `False`) is finite, so each still passes unchanged.
2. **Missing `runtime_output` attribute** — read it via `getattr(cp1, "runtime_output", None)`
   instead of attribute access, so a malformed `cp1` lacking the attribute degrades
   instead of raising `AttributeError`. The live caller always passes a real
   `ModulePayload`, and `... or {}` preserves the original `runtime_output=None → {}`
   behaviour, so valid inputs are unchanged.
3. **NaN/inf ebitda or coverage** — guard (b) now requires `math.isfinite(eb)` and
   `math.isfinite(cov)` (the `isinstance` + truthiness checks are kept). This closes
   the documented hole where NaN coverage passes `isinstance`, `bool(NaN)` is truthy,
   and `eb / NaN` yields NaN garbage. All frozen `eb`/`cov` values are finite.

## Why valid-input behaviour is unchanged

- A finite-number predicate (`_finite_number`) is the only widening: it rejects
  *strictly* the previously-leaking non-finite values. Every golden case (positive,
  zero, negative, and `False` liquidity; positive and negative coverage) is finite,
  so none is rerouted.
- `bool` is deliberately retained (int subclass) so `liquidity=False → (200.5, 0.0)`.
- Arithmetic is untouched: `cash_interest = round(eb/cov, 1)`; months divides by the
  already-rounded `cash_interest`, so `100/eb=10/cov=3 → (3.3, 363.6)`.
- No output guard is added — zero/negative liquidity and negative coverage stay as
  valid signed outputs (not "fixed").

## Deliberate divergence

None that changes a golden number. The only behavioural delta vs. the original is
that malformed inputs (NaN/inf liquidity, NaN/inf ebitda or coverage, a `cp1` with no
`runtime_output` attribute) now return `(None, None)` instead of crashing or emitting
NaN — strictly a hardening of the error path.
