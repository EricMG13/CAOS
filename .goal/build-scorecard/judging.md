# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the relative-value scoring by reading? — (2) readability/
structure, (3) blast radius, (4) error handling, (5) testability & perf. All six
proven equivalent on the 18-case contract. Paths:
`.goal/build-scorecard/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) and c3 (performance-first) — eliminated
c1 is a byte-identical no-op; c3 folds the three passes over `scored` into one
loop (its own rationale: no measurable gain at <15 peer rows). Neither adds
analyst legibility. **Eliminated.**

### c5 (maximally-testable) vs c4 (defensive) → **c4**
c5 lifts the logic into pure `_scored` / `_composite` / `_recommend` (c5:1-31),
each with a docstring pinning the banker's-rounding and band-boundary facts —
genuinely good testability (criterion 5). c4 is a **one-line** crash fix:
`isinstance(..., (int,float))` → `is_finite_number(...)` (c4:15), which closes a
**run-aborting** `ValueError` (a NaN percentile crashes `round(sum/len)` and kills
the whole CP-3 run), while still scoring every valid bool/int/float (criterion 4),
at the smallest possible blast radius (criterion 3). A real run-abort fix at one
line beats a testability refactor. **c4 advances** — c5's helpers flagged as
optional graft.

c2 and c6 take byes into the final pair.

## Round 2 — final pair → final

### c6 (domain-legible) vs c2 (readability-first) → **c6**
c2 is strong: full-word names, an explicit if/elif/else band, and why-comments
pinning the three load-bearing facts (bool-as-int, bare banker's `round`, the
half-open 60/40 bands, c2:12-20). c6 goes further on the highest-weighted axis —
it names the CP-1C **polarity contract** ("percentiles arrive already
polarity-adjusted, higher = stronger; we never re-sign anything", c6:6-13),
frames the composite as the equal-weighted mean = "0-100 strength vs peers", and
captures the "a metric without a percentile is *not scored as zero*" nuance
(c6:11-13) — the subtle thing an analyst must trust. **c6 wins criterion 1**, at a
comparable blast radius. **c6 advances.**

### c6 (domain-legible) vs c4 (defensive) → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                       | c4 (defensive)                              | winner |
|-------------------------------|-----------------------------------------------------------|---------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | names the polarity contract, the equal-weighted-mean composite, the bands, and the not-scored-as-zero nuance (c6:1-61) | original + a docstring about the guard | **c6** |
| 2. readability/structure       | richly annotated single function | original structure | c6 (slight) |
| 3. blast radius                | comments + one rename | one line + inline import | c4 (slight) |
| 4. error handling              | preserves original (NaN still crashes) | **fixes the run-aborting NaN crash** | **c4** |
| 5. testability/perf            | same as original | same as original | tie |

**c6 wins domain legibility (highest).** But c4 wins criterion 4 with a *genuine*
one-line fix for a run-aborting crash that c6 lacks. Recommended outcome is the
**combination**: c6's analyst-legible body + c4's `is_finite_number` filter — best
legibility AND the crash closed, both tiny. **Runner-up c4** (the real fix). c5's
pure helpers are the best testability seam, flagged optional. See merge-notes.
