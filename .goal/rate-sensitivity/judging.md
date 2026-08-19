# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the rate-shock math + the asymmetry by reading? — (2)
readability/structure, (3) blast radius, (4) error handling, (5) testability &
perf. All six proven equivalent. Paths:
`.goal/rate-sensitivity/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff, no-op) vs c6 (domain-legible) → **c6**
c1 is byte-identical to the original — zero blast radius, but it leaves the terse
docstring ("…or None if CP-1 lacks net debt") that explains neither the bps math,
the rounded-intermediate chain, nor the cov=0 asymmetry. c6 keeps the same
arithmetic while making all of that analyst-verifiable. The "do nothing" option
only wins if every rival is worse; they are not. **c6 advances; c1 out.**

### c3 (performance-first) vs c5 (maximally-testable) → **c5**
c3's changes (hoist `net_debt/10000`, cache `cov_numeric`, c3:8-18) are honest
but negligible at this once-per-synth/2-scenario scale, and add no analyst
legibility — the only new comment is about float associativity. c5 lifts the
per-shock math into a pure `_shock_scenario(net_debt, base_interest, eb, bps)`
(c5:1-17), winning structure (criterion 2) and testability (5). **c5 advances; c3 out.**

c2 and c4 take byes into the semifinals.

## Round 2 — semifinals

### c6 (domain-legible) vs c2 (readability-first) → **c6**
Both handle the subtle parts well — each names the cov=0 asymmetry in a comment
(c2:70-75, c6:54-57) and the round-before-reuse chain. c2 frames for a
programmer: a `_shock_scenario` helper + renamed locals. c6 frames for an
analyst: it derives the base interest (`coverage = EBITDA/interest ⇒ interest =
EBITDA/coverage`, c6:10-11), explains the basis-point conversion with a worked
example (`100bps → 0.01`, c6:12-15), states the symmetric-unguarded sign
behaviour for a net-cash borrower (c6:17-20), and notes the 1dp-interest /
2dp-coverage precision reconciliation (c6:22-24). It also keeps the original's
exact control flow (smaller semantic blast than c2's extraction). c6 wins
criteria 1 and 3. **c6 advances.**

### c5 (maximally-testable) vs c4 (defensive) → **c5**
c4 fixes a *real latent bug* (same class as the interest-runway one): a NaN
`interest_coverage_ltm` passes `isinstance` and `bool(NaN)` is True, so the
original would divide `EBITDA/NaN` and emit NaN garbage into the CP-2F payload.
c4's `_finite` helper (c4:10-11) routes NaN/inf net_debt·EBITDA·coverage to the
existing None paths. It wins criterion 4 — but carries the largest blast radius
(inline `import math`, helper, three wrapped reads) and comments about
defensiveness, not finance. c5 wins criteria 2 (clean split), 3 (smaller diff),
and 5 (pure helper unit-testable on plain numbers). Weighted, **c5 advances** —
c4's NaN guard flagged for cherry-pick (recommended; real fix).

## Final — c6 vs c5 → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                       | c5 (maximally-testable)                       | winner |
|-------------------------------|-----------------------------------------------------------|-----------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | derives the formula, works a bps example, names the sign behaviour AND the cov=0 asymmetry — all in one readable place (c6:1-61) | math correct, but split across `_shock_scenario` (c5:1-17) and the orchestrator; the asymmetry has no explanatory comment | **c6** |
| 2. readability/structure       | single function, richly documented | cleaner math/extraction separation | c5 (slight) |
| 3. blast radius                | docstring/comments over the original's exact control flow | new top-level helper + comprehension | **c6** |
| 4. error handling              | preserves original | preserves original | tie |
| 5. testability/perf            | same as original | pure `_shock_scenario` testable on plain numbers | c5 |

**c6 wins the highest-weighted criterion (domain-logic legibility) and blast
radius.** For a rate-stress table an analyst defends in committee, a single
function that derives base interest from coverage, works the basis-point
arithmetic, and explicitly names the cov=0 asymmetry (the one genuinely
surprising line) — while changing nothing about the proven math — is the most
defensible result. **Runner-up c5** (best testability seam: `_shock_scenario`).
**c4's `_finite` NaN/inf guard is the best error handling and a real latent-bug
fix — recommended graft.**
