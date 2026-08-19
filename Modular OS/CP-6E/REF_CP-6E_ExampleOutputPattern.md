<!-- REF_CP-6E_ExampleOutputPattern.md (T2 Example Library) | 2026-06-10 | Ported from Agent Files: CP-6E__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt -->


================================================================================
FILE: CP-6E__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt
MODULE: CP-6E — PortfolioDebateChallenge
STATUS: UPDATED (vNext)
MECHANICAL CHANGES APPLIED: MC-1, MC-2, MC-3, MC-5
GOVERNING CONTRACT: CP_GLOBAL_AGENT_INSTRUCTIONS_v3.2.txt
PURPOSE: Example portfolio debate output patterns for CP-6E.
================================================================================

EXAMPLE_OUTPUT_PATTERN

Purpose: Provide standard formatting templates for CP-6E portfolio debate
output elements. Execution rules and posture definitions are defined in
CP-6E__SUPPORT__ANALYTICAL_STANDARD.txt. Allocation rubric and constraint
taxonomy are defined in CP-6E__SUPPORT__PORTFOLIO_DEBATE_PLAYBOOK.txt.

All examples are illustrative only — do not use as issuer data.

1. Example RV Trader Pitch Format

RV Bullet 1 — Spread Compensation
Evidence: TLB currently trades at E+475 / 96.5 (CP-3, Pricing Run dated
  [Date]), versus BB-rated European HY leveraged loan cohort median of E+400
  (CP-3C, Peer RV Table). 75bp pickup.
Risk Mechanic: Spread premium compensates for single-name concentration and
  below-median liquidity score, while fundamental credit quality (4.8x net
  leverage, CP-2) is in line with cohort median of 4.9x.
Credit Implication: Portfolio yield enhancement of ~8bp on notional allocation
  of [X]bp of AUM. Compensation exceeds downside-adjusted spread loss under
  CP-2B base stress by ~120bp.
Monitoring Signal: Spread compression below E+400 or loss of pickup versus
  cohort median.

2. Example Compliance Officer Attack Format

| RV Bullet Attacked | Compliance Counter-Evidence | Constraint Vector | Risk Mechanic | Credit Implication | What Would Prove Compliance Wrong |
|---|---|---|---|---|---|
| Bullet 1: Spread compensation | Issuer would bring sector exposure to 14.2% vs 15% internal limit (Mandate Report, [Date]); next-largest issuer in sector is 3.5% | Sector concentration limit consumption: 95% of capacity after allocation | Near-limit concentration reduces portfolio flexibility; any sector downgrade or additional allocation would breach | Negative — concentration risk limits ability to add to defensive positions in same sector if opportunities arise | Sector exposure below 12% after allocation or internal limit raised above 15% |

3. Example CIO Scoring Format

| Dimension | Score (1–5) | RV Evidence | Compliance Evidence | CIO Assessment |
|---|---:|---|---|---|
| Spread / YTW Benefit | 2 | 75bp pickup vs cohort; current data (CP-3) | Spread partially explained by lower liquidity score | RV modestly ahead; pickup is real but liquidity discount accounts for ~20bp. Net benefit ~55bp. |
| Concentration Risk | 4 | Below hard limit | 95% of sector capacity consumed | Compliance ahead; near-limit position restricts future flexibility. Binding constraint candidate. |

4. Example Final Sizing Posture Determination

Final Sizing Posture: Include. The decision is driven by 55bp net spread
pickup versus BB cohort (CP-3, Pricing Run dated [Date]) after adjusting for
liquidity discount, because this compensation exceeds CP-2B base-case
downside-adjusted loss and supports portfolio yield targets, which implies
positive portfolio yield contribution with manageable downside budget
consumption. The main factor preventing a higher-conviction recommendation is
sector concentration at 95% of internal limit, which constrains position size
to [X]bp of AUM and eliminates incremental allocation capacity.

5. Example Exact Portfolio Constraint

Exact Portfolio Constraint: Concentration.
Evidence: Sector exposure would reach 14.2% vs 15% internal limit (Mandate
  Report, [Date]).
Risk Mechanic: Near-limit allocation consumes 95% of sector capacity,
  eliminating flexibility to add defensive positions in the same sector.
Credit / Portfolio Implication: Position size must be capped at [X]bp to
  preserve minimum 1% sector headroom; any additional same-sector opportunity
  would require reducing this position first.
Evidence Needed to Resolve: Updated sector exposure report confirming
  post-trade headroom; internal limit review outcome.

PORTFOLIO POSTURE (6-value CP-6E subset):
Include | Avoid | Resize-Reduce | Resize-Increase |
Maintain-Hold | Requires More Work

TRANSLATION TO CANONICAL 9:
Include → Starter Position, Core Hold, Add / Increase
Avoid → Avoid, Exit
Resize-Reduce → Reduce / Trim
Resize-Increase → Add / Increase
Maintain-Hold → Hold Existing Only, Core Hold
Requires More Work → Requires More Work

9-ITEM CONSTRAINT TAXONOMY:
Mandate | Concentration | Rating | Geography | Liquidity |
Correlation | Downside | Legal / Recovery | Data quality

9-DIMENSION ALLOCATION RUBRIC:
Spread | Peers | Downside | Liquidity | Legal protection |
CCC risk | Concentration | Mandate fit | Implementation liquidity

THREE PERSONAS:
RV Trader           — argues inclusion from RV evidence
Compliance Officer  — challenges via constraints
CIO                 — final posture and binding constraint

CANONICAL CREDIT IMPLICATION (13 values):
Positive — Deleveraging | Positive — Margin Expansion |
Positive — Revenue Growth | Positive — Liquidity Improvement |
Positive — Covenant Headroom Expansion | Neutral — Stable |
Negative — Leverage Increase | Negative — Margin Compression |
Negative — Revenue Decline | Negative — Liquidity Deterioration |
Negative — Covenant Erosion | Negative — Refinancing Risk |
Insufficient Information
