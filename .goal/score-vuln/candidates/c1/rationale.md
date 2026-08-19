# Rationale — minimal-diff candidate

Honestly: the original `score_vulnerability` is already optimal for the stated
contract. Every branch maps 1:1 to a golden case, the `{leverage:g}` format is
load-bearing and correct, the exclusive `elif` ladders are intentional, and
`min(_MAX_SCORE, score)` plus the band ternary are clean.

There is no defect to fix and no safe simplification that survives a 10-second
review (e.g. table-driving the thresholds would *add* diff and obscure the
exclusive-elif semantics). The smallest correct change is therefore the
**identity rewrite**: this `replacement.py` is byte-for-byte equivalent to lines
19–37. `diff.patch` is empty, confirming a zero-line change. All five golden
cases pass by construction since the logic is unchanged.
