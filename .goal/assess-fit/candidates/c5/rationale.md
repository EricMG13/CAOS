# c5 — maximally-testable

- Extracts the high-leverage caution into a pure `_risk_flags(leverage) -> list[str]`
  so the flag decision is exercisable in isolation, with no need to construct a CP-3
  recommendation or assert on the surrounding dict.
- `assess_fit` keeps its exact public signature and now *composes* the helper —
  recommendation→sleeve/sizing routing and flag derivation become two independent
  units a test can target separately.
- No hidden state, no I/O, deterministic. `_risk_flags` is total: non-numeric, NaN
  (since `NaN >= 6.0` is False), and `< 6.0` all return `[]`.
- Behaviour is byte-identical to the original: same `{leverage:g}` format, same flag
  and note strings, same `None`-iff-not-in-`_FIT` gate, same `composite_percentile`
  passthrough. Golden cases (7.0→"(7x)", 6.0→"(6x)", 6.5→"(6.5x)", 5.99/NaN/None→[],
  NEUTRAL/UNDERWEIGHT/`{}`/`None`/"overweight") all hold.
- Helper splices in directly above the public function (lines 22-35), needing only
  the already-present `Optional` import and `from __future__ import annotations`.
