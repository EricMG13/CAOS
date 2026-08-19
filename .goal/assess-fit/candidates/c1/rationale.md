# minimal-diff rationale

The original `assess_fit` is already optimal for its contract, so the honest
minimal-diff answer is byte-for-byte identical to lines 22-35.

Why no change is the right call:
- The NaN/non-numeric guard is already correct: `NaN >= 6.0` is `False`, so the
  `isinstance(...) and leverage >= 6.0` chain drops NaN, strings, and `<6.0`
  without crashing — no `is_finite_number` needed here (the comparison already
  does the rejecting that CLAUDE.md's guard would).
- `composite_percentile` flows through `cp3_rt.get(...)` → `None` when absent.
- The two surfaced strings (em-dash note, `{leverage:g}` flag) are preserved
  exactly.

Any rewrite (early-return restructuring, dict comprehension, extracted helper)
would add diff surface with zero behavioral or readability gain. Smallest
change = no change.
