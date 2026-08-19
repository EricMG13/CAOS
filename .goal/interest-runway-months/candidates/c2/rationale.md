# Candidate c2 — readability-first

**What changed (structure & names, not behavior):**

- Expanded the cryptic locals `nf`, `eb`, `cov`, `cash_interest` into
  `normalized_financials`, `latest_ebitda`, `interest_coverage`,
  `annual_cash_interest` so the code reads as plain finance, not abbreviations.
- Split the one-line packed Guard 2 (`isinstance(eb, ...) and isinstance(cov,
  ...) and cov`) into two named booleans (`ebitda_is_numeric`,
  `coverage_is_usable`). Same truth value — `not (A and B)` is preserved — but a
  reader sees *why* each clause is there.
- Pulled the two `nf.get(...)` lookups onto their own lines so the EBITDA and
  coverage sources are obvious.
- Added a `-> Tuple[Optional[float], Optional[float]]` return annotation
  (allowed; `Tuple`/`Optional` already imported) documenting the 2-tuple contract.
- Added why-comments for each of the three guards, calling out explicitly that
  they are divide-by-zero guards, that cash interest is rounded *before* the
  runway divide, and that the sign is *intentionally* left unguarded (negative
  coverage/liquidity → negative result; zero liquidity → 0.0 months).

**Why behavior is identical:** every computation, rounding (`round(x, 1)`,
half-even), comparison, and the order of the three `(None, None)` guards is
unchanged. `months` still divides by the already-rounded `annual_cash_interest`,
so the 100/eb=10/cov=3 → 363.6 case (not 360.0) is preserved. No new branches,
no output guards added — the refactor is pure renaming, line-splitting, and
commentary.
