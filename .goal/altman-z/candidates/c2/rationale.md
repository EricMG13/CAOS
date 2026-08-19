# Candidate c2 — readability-first

- Named each X-term (`working_capital_to_assets`, `retained_earnings_to_assets`,
  `ebit_to_assets`, `equity_to_liabilities`) so the formula reads as accounting
  ratios rather than positional `x1..x4`.
- Added a why-comment flagging the easy-to-miss gotcha: X4 divides by
  **total liabilities**, not total assets like the other three terms.
- Split the polynomial across lines with each coefficient beside its term, so a
  reviewer can eyeball-check 3.25 / 6.56 / 3.26 / 6.72 / 1.05 against Altman.
- Kept the exact signature (keyword-only `*`, every param name), the early-None
  guard (`total_assets <= 0 or total_liabilities <= 0`), `round(..., 2)`
  half-even, and delegated zoning to `zone_for(z)` to preserve the strict
  `> 2.6` / `< 1.1` boundaries (2.6 and 1.1 stay grey).
- Pure rename/reformat: arithmetic and control flow are byte-for-byte equivalent
  to the original, so every golden case is unchanged.
