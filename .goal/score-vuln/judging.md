# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the LME-vulnerability rubric by reading? — (2) readability/
structure, (3) blast radius, (4) error handling, (5) testability & perf. All six
proven equivalent on the 25-case contract. Paths:
`.goal/score-vuln/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) and c3 (performance-first) — eliminated
c1 is a byte-identical no-op; c3 only rewrites `min(_MAX_SCORE, score)` as an
`if score > _MAX_SCORE` branch (behaviorally identical, and on a non-hot path).
Both preserve the status quo — including the original's lack of any docstring or
rubric commentary — and add nothing on the highest-weighted axis. **Eliminated.**

### c5 (maximally-testable) vs c4 (defensive) → **c5**
c4 adds explicit `bool` and NaN guards (`not isinstance(leverage, bool) and
leverage == leverage`, c4:13) with a clear comment on why each is safe. But the
guards are **behavioral no-ops** — the original already drops bool (True ≥ 6.0 is
False) and NaN (NaN ≥ 6.0 is False), and this function never divides, so there is
no NaN to poison anything. So c4's "error handling" is decoration over a
non-problem (criterion 4 carries little weight here). c5 lifts the two scoring
rules and the banding into pure `_leverage_points` / `_fragility_points` / `_band`
helpers (c5:1-29), each independently unit-testable, winning criteria 2 and 5.
**c5 advances.**

c2 and c6 take byes into the final pair.

## Round 2 — final pair → final

### c6 (domain-legible) vs c2 (readability-first) → **c6**
c2 is genuinely good: a docstring, named threshold/point constants (c2:1-13), and
two extracted contribution helpers. Its comments describe the *mechanics* ("the
two bands are mutually exclusive", c2:20). c6 instead — comment-only, over the
original's exact control flow — explains the *credit meaning*: why ≥6.0x is HIGH
LME exposure ("minimal cushion to defend", c6:14), what fragility implies for a
coercive exchange (c6:5/24), and what each band represents (c6:36-39). For the
highest-weighted criterion (an analyst verifying the rubric), c6's "why" beats
c2's "what", and c6 does it at a smaller blast radius (comments vs helpers +
8 constants). **c6 wins criteria 1 and 3.**

### c6 (domain-legible) vs c5 (maximally-testable) → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                  | c5 (maximally-testable)                     | winner |
|-------------------------------|-------------------------------------------------------|---------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | the full CP-3D rubric read as a credit rubric — each threshold's *meaning*, each band's interpretation, in place (c6:1-41) | helpers are clean but documented as mechanics; no rubric-level "why" | **c6** |
| 2. readability/structure       | single function, richly annotated | clean rule/band decomposition | c5 (slight) |
| 3. blast radius                | comment-only over the original's exact control flow | three new helpers + composed body | **c6** |
| 4. error handling              | preserves original (already safe; no division) | preserves original | tie |
| 5. testability/perf            | same as original | pure helpers, unit-testable | c5 |

**c6 wins domain legibility (highest) and blast radius.** For a credit-rubric
scoring function, a version that reads as the rubric an analyst already applies —
naming what each leverage/fragility threshold and band *means* for LME exposure —
while changing not one byte of the proven logic, is the most defensible result.
**Runner-up c5** (best testability seam). No defensive graft recommended this
time — see merge-notes (the function has no division, so there is no latent NaN
bug to close).
