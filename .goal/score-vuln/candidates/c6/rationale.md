# c6 — domain-legible rubric

Objective: make the LME/refinancing rubric provable to a credit analyst by naming
what each threshold *means* at the line it fires, so the file reads like a scored
credit rubric rather than arithmetic.

- States the two CP-3D drivers up front: CP-1 leverage and CP-2B downside fragility,
  the structural inputs to coercive liability management (uptier / drop-down) risk.
- Annotates each threshold with its meaning + points: `>=6.0x = HIGH LME exposure -> +4`,
  `>=5.0x = ELEVATED -> +2`, fragility `HIGH -> +4` / `MODERATE -> +2`.
- Documents the band cutoffs as a rubric: `>=6 HIGH`, `>=3 MODERATE`, else `LOW`.
- Calls out the load-bearing invariants: exclusive elif (6.0x adds 4 only), exact
  case-sensitive fragility labels, `{leverage:g}` formatting (6.0->"6", 5.68->"5.68"),
  and why `_MAX_SCORE` is kept though the cap never binds (8 < 10).

Behavior is byte-identical: same thresholds, same point values, same driver strings
(surfaced verbatim downstream), same band logic, leverage driver first. Only comments
added — all six golden cases unchanged.
