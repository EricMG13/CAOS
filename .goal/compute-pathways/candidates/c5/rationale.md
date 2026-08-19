# c5 — maximally-testable

Factored into three pure, deterministic helpers the public function composes:

- `_stress_scenario(lev, cov, shock) -> dict` builds one scenario row; exercisable
  in isolation for the lev/(1-s) and cov*(1-s) rounding plus the `cov`-missing → None path.
- `_shock_to_breach(scenarios) -> Optional[int]` reads the **already-rounded**
  `stressed_net_leverage` off each row, so the breach test uses the exact `sl`
  shown (contract pt 3 — e.g. nf{6.3} → 7.0 @10). No raw `lev/(1-s)` recompute.
- `_fragility(lev, shock_to_breach) -> str` is the pure band map (pt 4),
  testable across its three branches without constructing any `nf`.

No hidden state; helpers take all inputs as args and return values only. Public
signature `compute_pathways(nf: dict) -> Optional[dict]` is unchanged and merely
orchestrates. All contract clauses (None gate, rounding, breach, fragility,
current/threshold fields) and every golden case preserved.
