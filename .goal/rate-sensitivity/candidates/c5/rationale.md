# c5 — maximally-testable split

The single loop is extracted into a pure free function `_shock_scenario(net_debt,
base_interest, eb, bps) -> dict`. The public `compute_rate_sensitivity` keeps the
nf-extraction concerns (the two `.get`s, the `latest(adj_ebitda)` unwrap, the
None-guard, and the `base_interest` calc) and simply maps the helper over
`_SHOCKS_BPS` via a list comprehension.

Why testability improves:
- The per-shock arithmetic (incremental, new_interest, stressed, and the two
  truthiness guards) is now a standalone, side-effect-free function. It can be
  unit-tested across the bps grid without constructing an `nf` dict or touching
  `latest` — pass `net_debt`, the already-rounded `base_interest`, and `eb`
  directly.
- The extraction/guard half (None-iff rules, `base_interest` truthiness vs. the
  `base_interest_coverage` asymmetry, `net_debt_musd` float-cast) is tested
  independently through the public surface.
- No hidden state, no closures over loop variables; deterministic and pure.

Why behavior is preserved: the helper receives the ALREADY-ROUNDED `base_interest`
and reuses the identical rounded intermediates in the identical order
(`add` → `new_interest` → `new_cov`), so every rounding boundary is byte-for-byte
the original. The public function's guard, asymmetry, `float()` cast, and
byte-identical assumption string are unchanged. Verified equal on all 12 golden
cases (incl. cov=0 asymmetry, negative net_debt, negative EBITDA, fractional 200.5).

Unit tests now enabled (NOT written/run here):
- `_shock_scenario` with base_interest=200.0 → (100→20.0,1.82), (200→40.0,1.67).
- `_shock_scenario` with base_interest=None → incremental computed, stressed None.
- `_shock_scenario` guard: base_interest=0.0 → new_interest None → stressed None.
- `_shock_scenario` sign cases: negative net_debt and/or negative eb.
- `compute_rate_sensitivity` None-iff cases (net_debt non-numeric, eb non-numeric, eb==0).
- `compute_rate_sensitivity` cov asymmetry: cov=0 → base_interest_musd None but base_interest_coverage 0.
