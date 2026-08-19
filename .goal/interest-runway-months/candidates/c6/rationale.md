# c6 — domain-legible rewrite of `_interest_runway_months`

**What an analyst can now verify by reading:**
- The named concepts are stated up front — *disclosed liquidity* (undrawn revolver + cash), *implied annual cash interest*, *interest coverage*, *months of runway*, and the *EBITDA→0 stress lens* — so the credit question ("how long can interest be paid if cash flow stops?") is explicit, not inferred from variables named `eb`/`cov`.
- The formula is laid out as algebra the analyst can re-derive: `coverage = EBITDA / interest ⇒ interest = EBITDA / coverage`, then `runway = liquidity × 12 / annual interest`, with a worked example (421, 2.1x → ~200.5; 500 → ~29.9 months).
- The rounding order is flagged as load-bearing: annual cash interest is rounded to 1dp **first**, then runway divides by that rounded figure — so the reported interest reconciles with the months. The half-even behaviour is named.
- Each guard says *why* it exists in credit terms (liquidity not quantified / no CP-1 EBITDA-coverage / 0x coverage = divide-by-zero & no interest burden / implied interest rounds to 0.0), framed as "degrade to Insufficient, don't invent a runway."

**Why behaviour is preserved (exact):**
- Same three guards, same order; same `latest(adj_ebitda or {})` and `interest_coverage_ltm` reads; same `(cp1.runtime_output or {})...or {}` chain.
- `annual_cash_interest = round(ebitda / coverage, 1)`; months `= round(liquidity * 12 / annual_cash_interest, 1)` — divides by the **rounded** interest, identical to the original `cash_interest`.
- No output guards: 0 liquidity → 0.0; negative liquidity/coverage flow through signed. Renames (`eb`→`ebitda`, `cov`→`coverage`, `cash_interest`→`annual_cash_interest`) are cosmetic; added `-> Tuple[...]` uses the already-imported `Tuple`.
- All 13 golden cases reproduce exactly (verified in isolation; repo test suite not run).
