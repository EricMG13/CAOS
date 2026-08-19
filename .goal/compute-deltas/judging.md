# P4 — Pairwise judging (survivors c1, c2, c3, c5, c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the delta math by reading? — (2) readability/structure, (3) blast
radius, (4) error handling, (5) testability & perf. c4 was eliminated at the gate
(over-broad NaN fix broke a valid case). Paths:
`.goal/compute-deltas/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) and c3 (performance-first) — eliminated
c1 is a byte-identical no-op. c3 folds the `margins` re-scan into the row loop and
uses `rev.keys() | eb.keys()` — its own rationale calls the gain negligible at
2-4 periods, and it adds no analyst legibility. Both preserve the status quo.
**Eliminated.**

## Round 2 — final three (c6, c5, c2)

### c6 (domain-legible) vs c2 (readability-first) → **c6**
Both extract/annotate well — c2 adds a clean `_ebitda_margin` helper (c2:1-14) and
names the ÷0 guard and signal order. But c6's standout is the **pp-vs-percent**
explanation (c6:11-14): *"a margin moving 25.0% → 22.2% is a 2.8pp compression,
not an 11% drop. Points vs. percent must never be conflated on a credit desk."*
That names the single most error-prone thing in this function for an analyst —
exactly the highest-weighted criterion — and c6 does it comment-only over the
original control flow (smaller blast than c2's helper). **c6 wins 1 and 3.**

### c5 (maximally-testable) vs c6 → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                      | c5 (maximally-testable)                       | winner |
|-------------------------------|----------------------------------------------------------|-----------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | names EBITDA margin, YoY-percent vs margin-pp (with the conflation trap), and the tear-sheet signal order, in place (c6:1-107) | correct, but the math is spread across `_margin`/`_signals`/`_margin_change`; the pp-vs-percent distinction isn't called out | **c6** |
| 2. readability/structure       | single annotated function | clean 3-helper decomposition | c5 (slight) |
| 3. blast radius                | comment-only over exact control flow | three new top-level helpers | **c6** |
| 4. error handling              | preserves original (NaN leak remains) | preserves original | tie |
| 5. testability/perf            | same as original | `_margin`/`_signals`/`_margin_change` unit-testable in isolation | c5 |

**c6 wins domain legibility (highest) and blast radius.** For the "what changed"
module an analyst reads first, the pp-vs-percent call-out is the most valuable
single line in the field. **Runner-up c5** (best testability: the three pure
helpers, esp. `_signals` for exercising the exact deterioration strings).

**NaN fix:** no surviving candidate carries it (c4, the only one that tried, was
eliminated for over-reaching). Graft the NARROW version onto c6 —
`None if isinstance(x,(int,float)) and not math.isfinite(x) else x` at row build —
which fixes the leak without touching the `"n/a"` valid case. See merge-notes.
