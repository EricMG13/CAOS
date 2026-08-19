# Candidate c1 — minimal-diff

Objective: smallest possible change, obviously-equivalent in a 10-second review.

The original `compute_pathways` is already optimal for this objective. It is tight,
correct against every golden case, has no dead code, no redundant computation, and
no readability debt worth touching. Every plausible micro-edit (folding the two
`shock_to_breach is not None` guards, aliasing `round(s * 100)`) would *add* diff
surface or change the breach-detection structure, not shrink it.

So, honestly: the minimal-diff winner is a no-op. `replacement.py` reproduces the
function byte-for-byte; `diff.patch` is empty. Zero risk, zero behavioral change,
identical golden outputs.
