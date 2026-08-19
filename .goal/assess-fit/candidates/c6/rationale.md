# Candidate c6 — domain-legible `assess_fit`

Objective: make the portfolio-fit logic provable to a credit analyst / PM. The
function had no docstring; the *why* lived only in the module header.

- Added a docstring that names the chain in desk language: CP-3's relative-value
  **lean** picks a **sleeve** and a **sizing bucket** (OVERWEIGHT -> core / full
  target size; NEUTRAL -> satellite / half; UNDERWEIGHT -> tactical only /
  minimal-or-pass), with the conviction read spelled out per bucket.
- Explained each branch where the credit judgement lives, not the mechanics:
  an unknown lean **can't be sized** (-> None, degrade not guess); >= 6.0x net
  leverage is an **additive risk-budget caution** that stands alongside the lean,
  not instead of it; the NaN/non-numeric path is "not >= 6.0, no flag, no crash."
- Kept the flag-don't-invent contract legible: concentration/correlation need the
  **live book** the engine doesn't ingest, so `note` flags the gap. Names CP-6E
  as the consumer.
- Behaviour untouched: signature, `_FIT` mapping, `>= 6.0` threshold, `{leverage:g}`,
  the em-dash flag string, and the `note` constant are all byte-for-byte identical.
  Comments and docstring only.
