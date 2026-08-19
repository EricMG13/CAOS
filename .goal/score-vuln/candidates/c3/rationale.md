# Candidate c3 — performance-first (honest)

There is no real optimization here. This function runs once per issuer during
CP-3D synthesis — a few comparisons and at most two string appends. It is not a
hot path, has no loops, no allocation pressure, and no measurable cost.

The only micro-change: `min(_MAX_SCORE, score)` is replaced with an inline
`if score > _MAX_SCORE` branch, which skips a function-call/tuple-build on the
common (already-clamped) path. The saving is sub-nanosecond and statistically
invisible at this call frequency — I am stating that plainly rather than
inventing a benefit.

Behaviour is byte-identical to the original: same clamp result, same band
thresholds, same driver order, `{leverage:g}` preserved. All five golden cases
hold. The honest answer is near-identical source; I did not sacrifice clarity
or correctness chasing gains that do not exist.
