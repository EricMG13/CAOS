<!-- CP-3C System Reference (T4) | 2026-06-03 -->

## Identity
module_id: CP-3C | module_name: PortfolioFitPositionSizing | schema_family: Nested | layer: L3

## Dependencies
UP: CP-3 | DOWN (Analytical): CP-6A, CP-6E | DOWN (Infra): CP-5B, CP-5, CP-RENDER, CP-EXTRACT

## Governance Rules
1. CP-3C does not replace CP-3 security-selection logic — it refines implementation posture after a security-selection conclusion exists.
2. Core Hold requires source-supported evidence for all 7 minimum evidence items; missing any → cannot assign Core unless labelled hypothetical framework-only.
3. Credit attractiveness alone is never sufficient for Core Hold — portfolio capacity, liquidity, concentration, and downside-budget support are required.
4. Yield alone cannot override adverse portfolio mechanics (concentration, liquidity, downside, legal, mandate).
5. Every material sizing conclusion must complete: Evidence → Risk Mechanic → Portfolio / Credit Implication.

## Evidence Hierarchy
Source Fact > Calculation > Analyst Inference > Directional Only > Insufficient Information > Not Assessable

## Sizing Posture Taxonomy (7 values)
Avoid | Watchlist | Starter Position | Core Hold | Hold Existing Only | Reduce / Trim | Requires More Work

## Confidence Labels
High | Medium | Low | Not Assessable

## Fit Categories
Mandate fit | RV fit | Liquidity fit | Risk-budget fit | Not fit | Not assessable

## Portfolio Roles
Yield carry | Spread duration | Convexity | Defensive senior secured | Catalyst | RV switch | Recovery-sensitive upside | Watchlist / monitoring only

## Portfolio-Action Labels
Add / Initiate | Hold / Maintain | Trim / Reduce | Avoid | Monitor / Escalate

## Caution Levels (Risk Budget Flags)
High | Medium | Low | Not Assessable

## Downside Status Labels
Calculated | Directional Only | Not Calculable

## Concentration Dimensions (7)
Issuer/group | Sector/subsector | Sponsor/ownership | Rating bucket | Maturity year/wall | Capital-structure layer | Correlated holdings/common factor

## Input Gate
CP-3 output required (blocking). If missing: qa_status = Blocked.

## Fail/Restrict
- **Blocked:** CP-3 output unavailable. Module produces blocked statement only.
- **Restricted (Generic):** Mandate/portfolio data unavailable. Output is generic portfolio-fit logic, not mandate-specific sizing.
- **Core Restricted:** Core Hold cannot be assigned without all 7 minimum evidence items.
- **Sizing Restricted:** No numeric size expressed without user-provided size and available portfolio constraints.
- **Liquidity Restricted:** Exit risk not assessable when liquidity data missing.
- **Scaling Restricted:** No assumption of scaling without price impact unless trading evidence supports it.

## Version: 2026-06-03
