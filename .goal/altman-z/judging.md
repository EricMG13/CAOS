# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify every Altman coefficient, term, and zone by reading? — (2)
readability/structure, (3) blast radius, (4) error handling, (5) testability &
perf. All six proven equivalent on the 28-case hardened contract. Paths:
`.goal/altman-z/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) and c3 (performance-first) — both byte-identical no-ops
Both returned the original verbatim (honest: the formula is already minimal and
has no hot path — 4 divides + a weighted sum, once per issuer). They preserve the
status quo and add nothing on any axis. **Both eliminated** — any candidate that
genuinely improves analyst-verifiability at zero behavioral cost beats "no change."

### c5 (maximally-testable) vs c4 (defensive) → **c5**
c4 fixes a *real latent bug* (the 4th unit this session to surface it): a NaN
input passes the `<= 0` denominator guard (NaN comparisons are False) and poisons
every divide into NaN garbage in the distress payload; c4's up-front
None/NaN/inf loop (`c4:25-35`, inline `import math`) routes those to None. It wins
criterion 4. But its comments are about defensiveness, not the Altman math, and it
carries the largest blast radius. c5 lifts the four ratios and the weighted sum
into pure `_z_double_prime_terms` / `_z_double_prime_score` helpers
(`c5:34-65`), each unit-testable on plain numbers, winning criteria 2/3/5.
Weighted, **c5 advances** — c4's NaN/None guard flagged for recommended graft.

c2 and c6 take byes into the final pair.

## Round 2 — final four → final

### c6 (domain-legible) vs c2 (readability-first) → **c6**
Both name the four ratios and both flag the X4=`/total_liabilities` gotcha
(c2:15-17 comment, c6:25/27-28). c2 stops at named locals + a multiline formula.
c6 goes further on the highest-weighted axis: its docstring writes out
`Z'' = 3.25 + 6.56·X1 + ...` with each X-term in balance-sheet language and a
plain-English role (liquidity / cumulative profitability / operating ROA /
solvency cushion, c6:17-28), and — uniquely — documents the **zone semantics
including the strict-inequality grey band** (`1.1 ≤ Z'' ≤ 2.6 → grey`, c6:30-31),
the exact thing the adversarial hunt showed is easy to get wrong. **c6 advances.**

### c6 (domain-legible) vs c5 (maximally-testable) → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                       | c5 (maximally-testable)                        | winner |
|-------------------------------|-----------------------------------------------------------|------------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | full Z'' formula + every term in balance-sheet language + X4=/TL gotcha + zone strictness, all in ONE place an analyst reads top-to-bottom (c6:11-43) | formula correct but split across two helpers; the X4=/TL note lives in the terms helper, away from the call site | **c6** |
| 2. readability/structure       | single well-documented function | clean math/score separation | c5 (slight) |
| 3. blast radius                | comments over the original's exact control flow | two new module-level helpers | **c6** |
| 4. error handling              | preserves original | preserves original | tie |
| 5. testability/perf            | same as original | pure term/score helpers, unit-testable | c5 |

**c6 wins the highest-weighted criterion (domain legibility) and blast radius.**
For a published distress model an analyst defends in committee, a single function
that writes out the Z'' polynomial, names every balance-sheet ratio, flags the
X4-denominator trap, and documents the grey-band strictness — while changing
nothing about the proven arithmetic — is the most defensible result. The
adversarial hunt's findings (coefficient swaps, X4 denominator, zone strictness)
are exactly the mistakes c6's commentary makes hardest to introduce later.
**Runner-up c5** (best testability seam). **c4's NaN/None guard = best error
handling, recommended graft (4th unit with this latent bug).**
