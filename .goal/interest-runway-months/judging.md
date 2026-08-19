# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the formula + guards by reading? — (2) readability/structure,
(3) blast radius, (4) error handling, (5) testability & perf. All six are proven
equivalent, so these are design verdicts. Paths:
`.goal/interest-runway-months/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) vs c6 (domain-legible) → **c6**
c1's only change splits `eb, cov = ...` into two assignment lines (c1:9-10) —
correct, trivially equivalent, but it gives an analyst nothing new on the
highest-weighted axis. c6 keeps the same arithmetic and control flow while
deriving the formula in the docstring and adding a worked numeric check
(c6:18-24). c1's lone edge is blast radius (criterion 3), which only breaks ties
at equal quality. **c6 advances; c1 out.**

### c3 (performance-first) vs c5 (maximally-testable) → **c5**
c3 reorders the coverage guard ahead of the `latest()` scan (c3:11-16) so a bad
coverage skips the dict iteration. Its own rationale concedes the gain is
negligible at this scale, and the reorder costs a reviewer a moment to confirm
equivalence (it is — bad-cov and bad-eb both yield `(None,None)`). c5 instead
lifts the math + guards (b)/(c) into a pure `_runway(liquidity, ebitda,
coverage)` (c5:1-26), winning structure (criterion 2) and testability (5) with no
behavioral-order question. **c5 advances; c3 out.**

c2 and c4 take byes into the semifinals.

## Round 2 — semifinals

### c6 (domain-legible) vs c2 (readability-first) → **c6**
Both are strong and — crucially — both call out the load-bearing rounding order
(c2:24-26, c6:26-29: round cash interest FIRST, then divide). c2 frames for a
programmer: renamed locals and two named guard booleans (c2:19-20). c6 frames for
an analyst: it derives the algebra an analyst already knows
(`coverage = EBITDA/interest ⇒ interest = EBITDA/coverage ⇒ runway =
liquidity×12/interest`, c6:18-21) and embeds a worked check (c6:23-24) that lets
a reader confirm the math without trusting the code. Criterion 1 → c6; roughly
tied elsewhere. **c6 advances.**

### c5 (maximally-testable) vs c4 (defensive) → **c5**
c4 has the best error handling in the field and fixes a *real latent bug*: a NaN
`interest_coverage_ltm` passes the original `isinstance` test and `bool(NaN)` is
True, so the old code would divide `EBITDA/NaN = NaN` and emit garbage. c4's
`_finite_number` helper (c4:4-10) routes NaN/inf to `(None,None)`, and `getattr`
tolerates a payload lacking `runtime_output` (c4:30). It wins criterion 4 — but
carries the largest blast radius (mid-file `import math`, new helper) and its
comments are about defensiveness, not the finance. c5 wins criteria 2 (cleaner
split), 3 (smaller diff), and 5 (pure helper unit-testable on plain numbers).
Weighted, **c5 advances** — but c4's NaN guard is a genuine fix, flagged for
cherry-pick (see merge-notes; recommended, not optional).

## Final — c6 vs c5 → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                   | c5 (maximally-testable)                          | winner |
|-------------------------------|-------------------------------------------------------|--------------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | derived algebra + worked check + degrade-don't-invent framing, all readable in ONE place (c6:4-33); names every guard in credit terms | math correct but split into `_runway` (c5:1-26) — analyst reads two functions, and the helper takes raw operands stripped of CP-1 context | **c6** |
| 2. readability/structure       | single well-documented function | cleaner separation of math vs extraction | c5 (slight) |
| 3. blast radius                | docstring/comments over the original's exact control flow → equivalence obvious | new top-level helper + delegation | **c6** |
| 4. error handling              | preserves original (no new guards) | preserves original (no new guards) | tie |
| 5. testability/perf            | same as original | pure `_runway` testable on plain numbers | c5 |

**c6 wins the highest-weighted criterion (domain-logic legibility) and blast
radius.** For a liquidity-runway number an analyst defends in committee, a single
function that derives the formula, shows a worked check, and explains why each
guard degrades to "Insufficient" — while changing nothing about the proven
arithmetic — is the most defensible result. **Runner-up c5** (best testability
seam: `_runway`). **c4's `_finite_number` NaN/inf guard is the best error
handling and a real latent-bug fix — recommended graft.**
