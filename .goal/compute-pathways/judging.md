# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the stress math + fragility call by reading? — (2) readability/
structure, (3) blast radius, (4) error handling, (5) testability & perf. All six
proven equivalent on the 21-case contract. Paths:
`.goal/compute-pathways/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) and c3 (performance-first) — eliminated
c1 is a byte-identical no-op; c3 hoists the `cov` isinstance check out of the loop
and reuses `round(s*100)` (behaviorally identical, honestly flagged as a cold
path). Neither adds analyst value over the status quo. **Eliminated.**

### c5 (maximally-testable) vs c4 (defensive) → **c4**
This is the close one. c5 lifts the body into three clean pure helpers —
`_stress_scenario` / `_shock_to_breach` / `_fragility` (c5:1-40) — and correctly
preserves the subtle contract point that the breach test reads the *already-
rounded* stressed leverage off each row (c5:24-26). Excellent testability
(criterion 5). c4 keeps the structure and adds `math.isfinite` guards (c4:20/26)
that fix a **real latent bug**: a NaN leverage currently passes `isinstance`,
`NaN ≥ 7.0` is False, and the function leaks NaN into the output while silently
reading fragility "LOW" for an issuer whose leverage is unknown — which then
feeds CP-3D. Because this function actually divides/multiplies CP-1 values, the
guard is a correctness fix, not decoration (criterion 4, and it *matters* here).
A real bug fix edges a testability refactor. **c4 advances** — but c5's helpers
are flagged as a strong optional graft.

c2 and c6 take byes into the final pair.

## Round 2 — final pair → final

### c6 (domain-legible) vs c2 (readability-first) → **c6**
c2 is strong: a `_stressed_scenario` helper, finance-named locals, and a good
comment on the redundant `lev >= 7.0` clause (c2:45-49). But c6 — comment/
docstring-only, over the original's exact control flow — *derives* the model for
an analyst: why holding net debt flat scales leverage by `1/(1-s)` and coverage
by `(1-s)` (c6:6-17), names the 7.0x leveraged-loan distress marker, and lays out
the fragility ladder with the "how little EBITDA loss tips into distress" framing
(c6:27-35). Criterion 1 → c6; and c6 has the smaller blast radius (comments vs a
helper). **c6 wins criteria 1 and 3.**

### c6 (domain-legible) vs c4 (defensive) → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                       | c4 (defensive)                              | winner |
|-------------------------------|-----------------------------------------------------------|---------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | derives the held-flat-debt stress model, the 7.0x marker, and the fragility ladder in place (c6:1-73) | clear guard docstring, but about defensiveness not the stress model | **c6** |
| 2. readability/structure       | single richly-annotated function | original structure + guards | c6 (slight) |
| 3. blast radius                | comment-only over exact control flow | inline import + 2 guard changes | **c6** |
| 4. error handling              | preserves original (leaves the NaN leak) | **fixes the real NaN-leak bug** | **c4** |
| 5. testability/perf            | same as original | same as original | tie |

**c6 wins domain legibility (highest) and blast radius.** But c4 wins criterion 4
with a *genuine* fix that c6 does not have. So the recommended outcome is the
**combination**: c6's analyst-legible body + c4's `math.isfinite` NaN guard — best
legibility AND the bug closed. **Runner-up c4** (real fix). c5's pure helpers are
the best testability seam, flagged for optional graft. See merge-notes.
