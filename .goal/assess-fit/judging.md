# P4 — Pairwise judging (survivors c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a PM/analyst
verify the sizing logic by reading? — (2) readability/structure, (3) blast
radius, (4) error handling, (5) testability & perf. All six proven equivalent on
the 16-case contract. Paths: `.goal/assess-fit/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff), c3 (performance-first), c4 (defensive) — eliminated
c1 is a no-op; c3 collapses `rec not in _FIT` + `_FIT[rec]` into `_FIT.get(rec)`
(one hash, negligible); c4 honestly adds only a comment (no guard is warranted —
no division/round, so a NaN leverage is simply not `>= 6.0`). None add analyst
legibility over the status quo (which had no docstring at all). **Eliminated.**

## Round 2 — final three (c6, c2, c5)

### c6 (domain-legible) vs c2 (readability-first) → **c6**
Both add the docstring the original lacked. c2's is a clean mechanical summary
(c2:2-8) with good renames. c6's *teaches the allocation logic to a PM*: it names
what each sleeve/sizing bucket MEANS — OVERWEIGHT → core/full = "high conviction",
NEUTRAL → satellite/half = "carry, not a bet", UNDERWEIGHT → tactical/minimal =
"trade, or skip" (c6:9-11) — and frames the leverage flag as an "additive
risk-budget overlay … independent of how attractive the relative value looks; the
lean still stands — the flag tells the PM what it costs" (c6:14-17). That is the
domain insight an allocator needs. **c6 wins criterion 1.**

### c6 (domain-legible) vs c5 (maximally-testable) → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                                        | c5 (maximally-testable)                  | winner |
|-------------------------------|------------------------------------------------------------|------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | names each sleeve/sizing bucket's meaning + the risk-budget-overlay framing + flag-don't-invent rationale (c6:1-43) | correct, but no allocation-level "why" | **c6** |
| 2. readability/structure       | single well-documented function | clean `_risk_flags` extraction | c5 (slight) |
| 3. blast radius                | docstring/comments over exact body | one small helper | c6 (slight) |
| 4. error handling              | preserves original (already safe) | preserves original | tie |
| 5. testability/perf            | same as original | pure `_risk_flags` unit-testable | c5 |

**c6 wins domain legibility (highest) and blast radius.** For the portfolio-fit
module a PM reads to size a name, a docstring that explains *why* each lean maps
to its sleeve and what the leverage flag costs — over the original's exact body —
is the most defensible result. **Runner-up c5** (`_risk_flags` testability seam).
No defensive graft: this unit has no latent bug (no division/round).
