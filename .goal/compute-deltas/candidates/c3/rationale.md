# Candidate c3 — performance-first (honest)

**Honest verdict: no meaningful runtime gain exists here.** `compute_deltas`
runs once per issuer over a handful of periods (typically 2-4). It is not a hot
path; at N≤4 every "pass" is free. Anyone claiming a measurable speedup on this
input would be inventing it.

What this candidate *does* change, defensibly:
- Folds the post-hoc `margins = [... for r in rows ...]` re-scan into the
  row-building loop, tracking the last two numeric margins in two O(1) locals
  (`prev_margin`/`last_margin`). Removes one full pass over `rows` and one list
  allocation. Real but negligible at this N — the value is fewer passes, not
  wall-clock.
- `rev.keys() | eb.keys()` instead of `set(rev) | set(eb)`: dict views union
  directly, skipping two intermediate `set()` constructions. Micro, not load-bearing.

`_yoy` is left untouched (out-of-scope helper, already cheap). Output verified
byte-identical to the original across all 9 goldens, including non-adjacent
numeric margins, prev=0, zero/negative revenue, and the -1.0 compression edge.
**If forced to rank: this is a wash on performance; pick c3 only for the
marginally tighter single-pass structure, not for speed.**
