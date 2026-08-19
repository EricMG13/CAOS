<!-- CP-3D System Reference (T4) | 2026-06-03 -->

## Identity
module_id: CP-3D | module_name: RefinancingLMERisk | schema_family: Nested | layer: L3

## Dependencies
UP: CP-1, CP-1A, CP-2B, CP-2E | DOWN (Analytical): CP-4, CP-6A | DOWN (Infra): CP-5B, CP-5, CP-RENDER, CP-EXTRACT

## Governance Rules
1. Do not infer LME intent from maturity pressure alone — pressure, legal capacity, and incentive/willingness must all be present for High vulnerability.
2. Legal capacity must be source-supported (governing executed documents outrank drafts/summaries) — do not infer from market convention.
3. Every material conclusion must complete: Evidence → Risk Mechanic → Credit Implication.
4. Use directional probability labels only — never fabricate numerical probabilities.
5. If CP-4C unavailable, do not infer exact legal capacity; if CP-2D unavailable, do not infer sponsor willingness from identity alone.

## Evidence Hierarchy
Governing Executed Legal Document > Draft / Term Sheet / Posting Memorandum > Lender Presentation > Third-Party Covenant Review > Market Convention / Analyst Inference > Insufficient Information

## Prime / LME Vulnerability Score Labels
Low | Medium | High | Insufficient Information

## Dimension Scoring Labels
Low | Medium | High | Insufficient Information

## Probability Direction Labels
Low | Medium | High | Increasing | Stable | Decreasing | Insufficient Information

## Evidence Confidence Labels
High | Medium | Low | Formula Only | Insufficient Information

## Refinancing / LME Path Types (7 canonical)
Consensual Refinancing | Amend-and-Extend | Exchange Offer | Distressed Exchange | Uptier | Drop-Down | Priming Debt

## Refinancing / LME Path Types (12 detailed)
Consensual refinancing | Amend & Extend | Open-market repurchase | Exchange offer | Distressed exchange | Uptier | Drop-down | J.Crew-style transfer | Serta-style non-pro-rata exchange | Priming debt | Asset sale / partial paydown | Sponsor equity injection

## Legal-Capacity Indicators (14)
Incremental debt capacity | Lien capacity | Unrestricted subsidiary capacity | Investment capacity | RP/junior debt payment capacity | Collateral release | Guarantor release | Amendment thresholds | Sacred rights | Open-market purchase provisions | MFN protection | Intercreditor terms | Class voting | Pro rata sharing provisions

## Refinancing Pressure Indicators (10)
Near-term maturity relative to liquidity | Distressed trading | Negative FCF/cash burn | High cash interest burden | Covenant headroom compression | Ratings downgrade/negative outlook | Revolver draw | Sponsor support | Asset sale proceeds | Improving EBITDA/deleveraging

## Downstream Handoffs
CP-1/CP-1B: maturity/cash-interest data needs | CP-2: fundamental outlook constraints | CP-2B: downside mechanics | CP-2D: sponsor evidence | CP-2E: liquidity runway | CP-3: RV impact | CP-3B: exposed creditor class | CP-3C: sizing constraints | CP-4/CP-4C: legal capacity gaps | CP-6A/CP-6E: debate evidence

## Structured Output Records
cp3d_maturity_wall_item | cp3d_lme_legal_capacity | cp3d_refinancing_path | cp3d_prime_lme_score | cp3d_creditor_class_exposure | cp3d_monitoring_trigger | cp3d_gap_item

## Fail/Restrict
- **Blocked:** No maturity/debt-schedule data available. Module produces blocked statement only.
- **Restricted (Legal):** CP-4C unavailable → legal capacity flagged [Insufficient Information], exact basket availability not inferred.
- **Restricted (Sponsor):** CP-2D unavailable → sponsor willingness flagged [Insufficient Information], not inferred from identity.
- **Restricted (Market):** Market data missing → market access/RV conclusions marked [Market Data Not Provided] or [Insufficient Information].
- **Score Restricted:** Path not labelled High unless pressure, feasibility, and incentive ALL supported.
- **Probability Restricted:** No fabricated numerical probabilities — directional labels only.

## Version: 2026-06-03
