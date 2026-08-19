# Candidate c1 — minimal-diff

Honest assessment: the original `altman_z_double_prime` is already optimal for the
minimal-diff objective. It is correct against every golden case, uses clear
intermediate `x1..x4` bindings, guards both denominators, applies `round(..., 2)`,
and delegates zone classification to the shared `zone_for` helper (so the strict
`> 2.6` / `< 1.1` boundaries and constants live in exactly one place).

Any structural rewrite (inlining ratios, folding zone logic, reordering the guard)
would *add* diff, not reduce it, and risk a boundary or X4-denominator regression
— precisely the traps the contract calls out. So this candidate is a byte-for-byte
reproduction of lines 36–55. Smallest possible change = no change; diff.patch is
empty. A 10-second review sees identical code.
