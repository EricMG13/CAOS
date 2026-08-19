# Candidate c2 — readability-first

- Added a docstring to `score_vulnerability` (and to two helpers) explaining inputs,
  the cap, the band mapping, and driver ordering — the original had none.
- Named every magic number: leverage turns (6.0/5.0), per-band points (+4/+2), and
  the band thresholds (6/3). Constant names state *why* each value matters.
- Split the two structural drivers into `_leverage_contribution` and
  `_fragility_contribution`. Each returns `(points, driver_or_None)`, so the scoring
  rule for each driver lives in one obvious place and reads top-to-bottom.
- The main function now just sums contributions in evaluation order (leverage first),
  caps, and maps to a band via an explicit if/elif/else instead of a nested ternary.
- Behaviour is byte-for-byte identical: same constants, same exclusive elif logic,
  same exact/case-sensitive fragility labels, and the load-bearing `{leverage:g}`
  driver strings are unchanged. Leverage driver is still appended before fragility.
