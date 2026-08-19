# Merge notes — winner c6, no graft

**Winner:** c6 (domain-legible). `winner.diff` applies to
`caos/server/engine/portfoliofit.py:22-35`. Docstring + comments over the
original's exact body — zero logic change, proven by the 16-case contract + 4
portfolio tests. Gives the previously-undocumented function a PM-level read: each
sleeve/sizing bucket's meaning (high conviction / carry-not-a-bet / trade-or-skip)
and the leverage flag as an additive risk-budget overlay.

### No defensive graft — deliberate (2nd no-bug unit, after score_vulnerability)
assess_fit does NO division and NO round(): a NaN leverage simply fails
`NaN >= 6.0` (no flag, no crash), a non-numeric fails isinstance, an unknown
recommendation returns None. There is no latent bug, so there is nothing to graft
— c4 (defensive) correctly declined to add a guard for a non-problem. The "graft
the finite guard iff the unit divides/round()s a CP-1 value" rule says skip here.

### Optional
- c5's pure `_risk_flags(leverage)` helper: graft if the risk-flag set grows
  (more than the single high-leverage caution). Not now — one flag.

### Not recommended
- c1 (no-op); c3 (`_FIT.get` collapse, negligible); c2 (good docstring, but c6
  dominates on allocation-level legibility).
