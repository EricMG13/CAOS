# P4 — Pairwise judging (survivors: c1–c6)

Rubric, weighted: **(1) domain-logic legibility [highest]** — can a credit
analyst verify the math by reading? — (2) readability/structure, (3) blast
radius (smaller, safer diffs win at *equal* quality), (4) error handling,
(5) testability & performance. All six are already proven equivalent, so these
are pure design verdicts. Paths are `.goal/recovery-waterfall/candidates/<id>/replacement.py`.

## Round 1 — cull

### c1 (minimal-diff) vs c6 (domain-legible) → **c6**
c1 is semantically identical to the original: its only change reflows the final
`out.append({...})` to one-key-per-line (c1:22-26). It gives an analyst nothing
new on criterion 1. c6 keeps the *same* control flow but names the finance
(`remaining_ev`, `claim`, `indeterminate`, c6:42/44/46) and adds a worked
numeric check in the docstring (c6:25-27). c1's only edge is blast radius
(criterion 3), which only breaks ties "at equal quality" — quality is not equal
on the highest-weighted axis. **c6 advances; c1 out.**

### c3 (performance-first) vs c5 (maximally-testable) → **c5**
c3 trades the original's clean sticky-`broken` flag for an early-return
tail-drain: on break it emits the current row, then re-loops the remainder with a
shadowed loop variable `t` (c3:18-21) and returns. Its own rationale concedes the
gain is negligible at the real <10-tranche scale. That is more control-flow
surface for no real benefit — worse on criteria 2 (structure) and 3 (blast
radius), neutral on 1. c5 keeps a clean orchestrator (c5:33-59) and lifts the
per-tranche math into a pure, independently-testable `_settle_tranche`
(c5:12-30). **c5 advances; c3 out.**

c2 and c4 take byes into the semifinals.

## Round 2 — semifinals

### c6 (domain-legible) vs c2 (readability-first) → **c6**
Both are clear. c2 frames for a *programmer*: a `_is_sized_claim` predicate
(c2:1-10) and renamed locals (`claim`/`recovered`/`waterfall_broken`). c6 frames
for an *analyst*: it names the **absolute-priority rule** and the
**indeterminate cascade** in credit terms in the docstring, and — decisively —
embeds a worked example (c6:25-27) that lets a reader confirm the waterfall
arithmetic without trusting the coder. c6 also has the smaller semantic blast
radius: it preserves the original's exact control flow (sticky flag + single
loop, c6:46-66), where c2 introduces a helper. c6 wins criteria 1 and 3.
**c6 advances.**

### c5 (maximally-testable) vs c4 (defensive) → **c5**
c4 has the best error handling in the field — an up-front finite/numeric EV guard
(c4:34-40) and a NaN/inf/bool-rejecting `_is_valid_amount` (c4:69-90) — and wins
criterion 4 outright. But its docstring is about defensiveness, not the finance,
and it carries the largest blast radius (two new `raise` paths an analyst must
reason about, plus the missing-key divergence). c5 wins criterion 1 (slight — no
new control paths to reason about), criterion 3 (zero behavior change), and
criterion 5 (pure helpers). Weighted, **c5 advances** — but flag c4's EV guard
for cherry-pick (see merge-notes).

## Final — c6 vs c5 → **WINNER: c6**

| criterion (weight)            | c6 (domain-legible)                              | c5 (maximally-testable)                       | winner |
|-------------------------------|--------------------------------------------------|-----------------------------------------------|--------|
| 1. domain-logic legibility ▲▲ | worked example + finance vocabulary + named absolute-priority/indeterminate-cascade, all readable top-to-bottom in ONE function (c6:1-68) | math is correct but split into `_settle_tranche` (c5:12-30) — an analyst reads two functions to verify one waterfall | **c6** |
| 2. readability/structure       | single well-commented function | cleaner separation of concerns | c5 (slight) |
| 3. blast radius                | comments + renames over the original's exact control flow → equivalence obvious by eye | two new helpers re-route the math | **c6** |
| 4. error handling              | preserves original (no new guards) | preserves original (no new guards) | tie |
| 5. testability/perf            | same as original | pure `_is_sized` + `_settle_tranche` are unit-testable in isolation | c5 |

**c6 wins the highest-weighted criterion (domain-logic legibility) and blast
radius.** For financial code whose entire purpose is "can an analyst stand behind
this number in committee?", a single function that names the absolute-priority
rule and shows a worked recovery check (c6:25-27) — while changing nothing about
the proven control flow — is the most defensible outcome. c5 is the runner-up;
its `_settle_tranche` pure helper is the best testability artifact in the field.
