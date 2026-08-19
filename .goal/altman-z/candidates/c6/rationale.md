# Candidate c6 — domain-legible

- Every X-term gets a balance-sheet name in the docstring AND an inline comment:
  X1 liquidity (working capital / TA), X2 cumulative profitability (RE / TA),
  X3 operating return on assets (EBIT / TA), X4 solvency cushion (book equity / TL).
- Explicit `working_capital = current_assets - current_liabilities` makes X1
  readable as a desk concept, not a raw subtraction inside a divide.
- The X4 = / total_liabilities (not / total_assets) gotcha is called out in prose
  as the double-prime variant's distinguishing equity-to-debt cushion — an analyst
  can confirm the one term that breaks if mis-coded.
- All five coefficients (3.25, 6.56, 3.26, 6.72, 1.05) sit verbatim in the formula,
  matching the docstring's published Z'' equation line-for-line.
- Cutoffs named in the docstring with strict-inequality boundaries spelled out
  (2.6 and 1.1 both grey); zone logic delegated to `zone_for` to keep one source
  of truth and the published constants unaltered.
- Math, rounding (round(..., 2), half-even), None guard, and signature byte-identical
  to the original — only legibility is added.
