# Candidate c2 — readability-first

- Renamed `comps`/`rec` to full words (`comparisons`, `recommendation`,
  `composite_percentile`) so each line reads as a sentence, not an abbreviation.
- Replaced the nested ternary chain with an explicit `if/elif/else`; the three
  recommendation outcomes now read top-to-bottom in band order.
- Added why-comments that pin the three load-bearing facts: bool counts as int,
  bare `round()` uses banker's rounding on the boundary, and the bands are
  half-open (60 -> OW, 40 -> NEUTRAL). Future edits won't silently break these.
- Expanded the dict/list comprehensions across lines so each scorecard field
  sits on its own line — easier to scan and diff.
- No behavioural change: same filter, same banker's `round`, same band cutoffs,
  same `.get` defaults, same `peer_scope` fallback. Structure over cleverness.
