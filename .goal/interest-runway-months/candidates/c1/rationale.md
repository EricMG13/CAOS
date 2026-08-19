# Rationale — minimal-diff

The only change: the single line that bound two locals at once

```python
eb, cov = latest(nf.get("adj_ebitda") or {}), nf.get("interest_coverage_ltm")
```

is split into two separate assignments

```python
eb = latest(nf.get("adj_ebitda") or {})
cov = nf.get("interest_coverage_ltm")
```

Tuple-unpack assignment and two sequential assignments are exactly equivalent in
Python: the right-hand expressions are evaluated left-to-right in both forms, and
`eb`/`cov` end up bound to the identical values. No control flow, guards,
rounding, division order, or signatures change. Every other line — all three
`(None, None)` guards (in order), `round(eb / cov, 1)`, the falsy `cash_interest`
short-circuit, and `round(liquidity * 12 / cash_interest, 1)` dividing by the
already-rounded `cash_interest` — is byte-for-byte identical to the original.

All golden cases (200.5/29.9; 3.3/363.6 via the rounded divisor; the `None`,
`cov=0`, `eb=0.04`, zero/negative-liquidity, negative-coverage, and
`runtime_output=None` paths) therefore produce identical output. A reviewer
confirms equivalence at a glance.
