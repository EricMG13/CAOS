# Candidate c1 — minimal-diff

The original `compute_deltas` is already optimal for this objective. Every line
is load-bearing and obviously correct, so the honest minimal-diff answer is a
verbatim drop-in (zero behavioral change, zero textual change).

- The dual `isinstance(r, ...) and r and isinstance(e, ...)` margin guard is
  necessary: `r` truthy blocks the zero-revenue ÷0, each `isinstance` blocks
  non-numeric coercion. Removing either would alter the contract.
- `_yoy` factoring, the `margins` numeric filter, `:g` formatting, the `→`
  arrow, and the signal ordering are all contractually fixed.
- Any rename, helper extraction, or comprehension-merge would enlarge the diff
  without buying equivalence-safety. So the smallest change is no change.

`diff.patch` is therefore empty.
