# Merge notes — winner c6, recommended graft c4

**Winner:** c6 (domain-legible). `winner.diff` applies to
`caos/server/engine/downside.py:22-59`. **Comment/docstring-only** — not one byte
of logic changed. Proven by the 21-case contract + 11 analytics tests. It derives
the held-flat-debt stress model (`leverage × 1/(1-s)`, `coverage × (1-s)`), names
the 7.0x distress marker, and lays out the fragility ladder for an analyst.

### From c4 (defensive) — RECOMMENDED graft (real latent bug, division present)
- **NaN/inf guard via `math.isfinite`** (`c4/replacement.py:20, 26`). Unlike the
  score_vulnerability unit (no division → no NaN bug), `compute_pathways`
  **divides and multiplies** CP-1 values (`lev/(1-s)`, `cov*(1-s)`), so a NaN
  leverage leaks NaN into `current_net_leverage` and every `stressed_net_leverage`,
  and — because `NaN >= 7.0` is False — fragility silently reads **"LOW"** for an
  issuer whose leverage is actually unknown. That wrong "LOW" then feeds CP-3D
  (`score_vulnerability`). The fix: non-finite leverage → None (same as the
  existing missing-leverage path); non-finite coverage → per-scenario None (same
  as the existing non-numeric-cov path). **Recommend grafting** onto the c6 winner
  (move `import math` to downside.py's import block, not inline). Verified: the
  contract's incidental NaN case already permits the fix.

### From c5 (maximally-testable) — optional
- **Pure `_stress_scenario` / `_shock_to_breach` / `_fragility`**
  (`c5/replacement.py:1-40`): each step independently unit-testable on plain
  numbers; `_shock_to_breach` correctly reads the already-rounded leverage off
  each row. Worth grafting if the scenario set or the fragility ladder grows.
  Not now — the 21-case contract exercises the whole pipeline.

### Combined recommendation
**c6 + c4's `math.isfinite` guard** = best legibility AND the NaN bug closed.

### Not recommended
- c1 (minimal-diff) no-op; c3 (perf) honest near-no-op — neither adds value.
- c2 (readability): good, but c6 dominates legibility at a smaller blast radius.

### Pattern note (5th unit)
NaN-divide bug now seen in 4 of 6 units (recovery_waterfall: no CP-1-ratio divide;
score_vulnerability: no divide). Rule of thumb confirmed: **graft the finite guard
iff the unit divides/multiplies a CP-1 value that could be NaN.** A shared
`_finite` helper or a CLAUDE.md note is increasingly justified.
