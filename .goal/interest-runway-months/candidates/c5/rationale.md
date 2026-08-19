# c5 — maximally-testable

The arithmetic (cash-interest derivation, months division, and guards (b)/(c)) is
extracted into a pure `_runway(liquidity, ebitda, coverage)` taking plain numbers.
The public `_interest_runway_months` keeps its exact name/signature and now does
only the I/O-shaped work: guard (a) (liquidity type + cp1 None), unwrap
`runtime_output -> normalized_financials`, pull `latest(adj_ebitda)` and
`interest_coverage_ltm`, then delegate. No hidden state; both halves deterministic.

Behaviour is byte-identical: same operands flow to the same expressions in the same
order, cash interest is rounded once and that rounded value is reused as the months
denominator (case `100/10/3 -> 3.3 -> 363.6`, not raw `360.0`), and outputs stay
unguarded (zero/negative liquidity, negative coverage). Guard (b) tests `coverage`
truthiness, so `0` short-circuits but `-2.1` passes through unchanged.

New unit tests this split unlocks (math, no CP-1 fixtures needed):
- `_runway(500, 421, 2.1) == (200.5, 29.9)`; `_runway(100, 10, 3) == (3.3, 363.6)`
  (locks rounded-denominator behaviour directly).
- guard (b): `_runway(500, None, 2.1)`, `_runway(500, 421, 0)`,
  `_runway(500, 421, None)` all `(None, None)`.
- guard (c): `_runway(500, 0.04, 1) == (None, None)`.
- unguarded outputs: `_runway(0, 421, 2.1) == (200.5, 0.0)`,
  `_runway(-500, 421, 2.1) == (200.5, -29.9)`, `_runway(500, 421, -2.1) == (-200.5, -29.9)`.
- public-fn guard (a) + unwrap, with a minimal `cp1` stub:
  `disclosed_liquidity="500"`, `cp1=None`, `runtime_output=None`, `adj_ebitda={}`.
