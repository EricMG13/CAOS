# Candidate c2 — readability-first

- Added a docstring stating the return contract: `None` iff the recommendation is
  unrecognised, plus what each output key carries (incl. percentile passthrough).
- Renamed locals for self-documentation: `rec` -> `recommendation`,
  `flags` -> `risk_flags`, and named the guard `is_numeric_leverage`.
- Why-comments explain the two non-obvious decisions: the early `None` return, and
  *why* the isinstance+`>= 6.0` guard correctly rejects NaN/non-numbers (NaN passes
  isinstance but `NaN >= 6.0` is `False`, so `risk_flags` stays `[]` — no crash).
- Expanded the return dict to one key per line so the shape reads top-to-bottom.
- Behaviour is byte-identical to the original: same guard, inclusive `>= 6.0`,
  `{leverage:g}` format, and the note + flag strings (em-dash) kept verbatim.
- Golden cases hold: lev 6.0 -> "(6x)", 5.99/NaN -> `[]`, 6.5 -> "(6.5x)", `{}`/`None`/lowercase -> `None`.
