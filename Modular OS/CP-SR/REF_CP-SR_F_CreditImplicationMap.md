# REF_CP-SR_F | Credit Implication Taxonomy Mapping
# Version: 1.0

## CANONICAL CREDIT IMPLICATION VALUES
1. `LEVERAGE_PRESSURE` — Sector dynamics that increase or sustain elevated leverage.
2. `MARGIN_EROSION` — Competitive or structural forces compressing profitability.
3. `CASH_FLOW_STRESS` — Factors reducing FCF generation or conversion.
4. `REFINANCING_RISK` — Maturity wall, spread widening, or capital market access concerns.
5. `REGULATORY_OVERHANG` — Policy or regulatory actions that could impair credit quality.
6. `STRUCTURAL_SUBORDINATION` — Capital structure dynamics that weaken creditor positioning.
7. `EVENT_RISK` — M&A, LME, litigation, or exogenous shocks.
8. `CREDIT_IMPROVEMENT` — Positive dynamics supporting deleveraging or upgrade potential.

## MAPPING RULES
- Each key credit driver must map to at least one implication.
- Each risk item must map to at least one implication.
- Implications flow to downstream modules: CP-2, CP-5, CP-6A, CP-6E, CP-MON.
- Use only canonical values; do not create ad-hoc implications.

## EXAMPLE MAPPINGS
| Sector Finding | Credit Implication(s) |
|---|---|
| Capex declining and FCF improving | CREDIT_IMPROVEMENT |
| Altnet competition driving ARPU pressure | MARGIN_EROSION |
| Concentrated maturity wall | REFINANCING_RISK |
| TowerCo contract renegotiations | EVENT_RISK; MARGIN_EROSION |
| Regulatory approval of in-market consolidation | CREDIT_IMPROVEMENT; EVENT_RISK |
| Downgrade driven by sustained high leverage | LEVERAGE_PRESSURE |
| NetCo / ServCo separation weakens restricted group | STRUCTURAL_SUBORDINATION |
| Rising energy costs reduce cash generation | CASH_FLOW_STRESS |
