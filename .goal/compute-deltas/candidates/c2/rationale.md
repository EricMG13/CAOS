# Candidate c2 — readability-first

- Extracted the margin calc into a named `_ebitda_margin` helper so the per-row
  loop reads as data, and the divide-by-zero / negative-revenue reasoning lives
  in one documented place instead of an inline ternary.
- Renamed locals to full words (`revenue_by_period`, `valued_margins`,
  `revenue_yoy`) — flow is now obvious top-to-bottom: rows → YoY → summary → signals.
- Unpacked each `_yoy` tuple (`_, prior_period, latest_period`) so the f-strings
  name what they interpolate rather than indexing `[1]`/`[2]`.
- Why-comments mark the non-obvious bits: truthy-revenue ÷0 guard, intentional
  negative margin, half-even rounding, point-difference (pp) vs YoY %, the
  fixed verbatim signal order, and the inclusive `<=` compression boundary.
- Behaviour is unchanged: same union/sort, same guards, same signal strings and
  ordering, same `round` half-even, non-numeric values skipped not coerced.
