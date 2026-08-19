<!-- REF_CP-1A_BusinessFactTaxonomy (T2 Library) | 2026-06-20 | Restored from CP-1A_BusinessTransactionFactPack__Role_Scope_and_Analytical_Standard §Business-Fact Taxonomy + Core Analytical Standard -->
<library_reference module="CP-1A" name="Business-Fact Taxonomy and Credit-Relevance Mapping">
<consumers>REF_CP-1A_03 (Transaction Summary); REF_CP-1A_04 (Business Description); REF_CP-1A_05 (Ownership Register); REF_CP-1A_06 (Operating Model); REF_CP-1A_07 (History/Timeline); REF_CP-1A_08 (Credit Translation)</consumers>

# CP-1A Business-Fact Taxonomy

Each numbered step captures facts in one or more fact areas. This library defines, per area, the
source-supported facts to capture **and why each matters for credit** — so every extracted fact is
translated to a creditor dimension, never left as a neutral description.

## Fact Area → Capture → Credit Relevance

| Fact Area | Source-Supported Facts to Capture | Credit Relevance |
|---|---|---|
| **Business Description** (Step 04) | Core activities, products, services, end markets, geography, customers, revenue model | Cash-flow visibility, business risk, refinancing confidence |
| **Transaction Context** (Step 03) | Transaction type, buyer/seller/sponsor, use of proceeds, sources and uses, purchase price, valuation, debt raised, pro forma leverage, liquidity impact | Leverage tolerance, liquidity, refinancing capacity, sponsor alignment, PD / LGD |
| **Ownership / Sponsor** (Step 05) | Current owner, prior ownership, sponsor history, ownership percentage, control rights, dividend-recap history | Governance risk, creditor alignment, debt-funded distribution risk |
| **Operating Model** (Step 06) | Revenue streams, pricing, volume drivers, cost structure, fixed/variable cost mix, capex, working capital | Revenue durability, margin resilience, FCF conversion, downside sensitivity |
| **Timeline** (Step 07) | Founding, acquisitions, disposals, ownership changes, refinancings, carve-outs, strategic shifts | Business evolution, event risk, leverage history, monitoring focus |
| **Gaps / Conflicts** (Step 09) | Missing transaction source, missing revenue mix, missing customer concentration, conflicting descriptions | Limits committee readiness and downstream modules |

## Evidence → Risk Mechanic → Credit Implication (expanded for CP-1A)

- **Evidence** — a specific source file, document clause, transaction table, company-description
  statement, financial figure, ownership disclosure, operating metric, revenue mix, cost item, or
  factual source statement.
- **Risk Mechanic** — how that evidence affects business risk, revenue visibility, margin resilience,
  operating leverage, FCF durability, liquidity, refinancing capacity, governance risk, sponsor
  alignment, PD, LGD, or downstream credit work.
- **Credit Implication** — the impact on PD, LGD, liquidity, debt service capacity, FCF durability,
  leverage tolerance, refinancing capacity, recovery prospects, monitoring posture, committee
  readiness, or relative value.

## Capture Discipline
- Every captured fact in Steps 03–07 must carry its credit relevance (the third column), or be marked
  `[Insufficient Information]` with the specific missing datapoint and why it matters.
- Do **not** fabricate LBO entry multiples, valuation, sources and uses, sponsor economics, ownership
  percentages, purchase price, leverage, maturity profile, debt quantum, revenue mix, customer
  concentration, operating KPIs, ownership dates, or transaction terms.
- Do not silently harmonize source-defined operating/financial metrics with CP-1. If definitions
  differ, show both and log the comparability issue for CP-2.
</library_reference>
