<!-- CP-X System Reference (T4) | 2026-06-03 -->

## Identity
module_id: CP-X | module_name: PlannerRouter | schema_family: Nested | layer: Orch

## Dependencies
UP: CP-0 | DOWN (Analytical): CP-1, CP-1A, CP-1B, CP-1C, CP-2, CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-2G, CP-3, CP-3B, CP-3C, CP-3D, CP-4, CP-4D, CP-4C, CP-6A, CP-6E | DOWN (QA, L5): CP-5B, CP-5 | DOWN (Sector/Monitor, L7): CP-SR, CP-MON | DOWN (Infra): CP-RENDER, CP-EXTRACT

## Governance Rules
1. CP-X routes by CP-0 content-based readiness — never by filename or assumption.
2. One-owner-per-object is enforced per CP_GLOBAL_AGENT_INSTRUCTIONS_v3.2 SEC2; conflict = VE-009 (OWNERSHIP_VIOLATION), conflicting module excluded.
3. CP-X does not perform credit analysis, legal interpretation, RV assessment, or portfolio sizing — routing and governance enforcement only.
4. All CP-0 limitations (Conditional / Not Usable) must be propagated to every downstream module in the dependency chain.
5. CP-X consumes only CP-0 output and CP_ROUTING_INDEX_v2.2 — no source documents, financial data, or analytical module outputs.

## Input Sources (2)
1. CP-0 output (readiness assessment, source registry, per-module readiness verdicts)
2. CP_ROUTING_INDEX_v2.2 (authoritative ownership registry: module → owned_object mapping)

## Module Readiness Status Values (3)
Full Run | Ready with Limitations | Blocked

## Source Dependencies Met Values (3)
Yes | Partial | No

## Conflict Detection
- VE-009: OWNERSHIP_VIOLATION — two modules claim the same owned_object → exclude conflicting module

## Layer Ordering (execution precedence)
L0 → Orch → L1 → L2 → L3 → L4 → L5 → L6 → L7 → Infrastructure
CP-5B before CP-5 | CP-6A before CP-6E | L7 (CP-SR, CP-MON) after L6 | Infrastructure after all analytical modules

## Route Graph — All Modules
<!-- Module names are canonical Taxonomy A (per MODULES_REFERENCE_v2 + module ACTIVE_PROMPTs + payload-schema consts). Re-synced 2026-06-20 to finish TAXONOMY_RECONCILIATION.md §5. -->
| Module ID | Module Name | Layer |
|-----------|------------|-------|
| CP-0 | SourceReadiness | L0 |
| CP-X | PlannerRouter | Orch |
| CP-1 | CanonicalDataFoundation | L1 |
| CP-1A | BusinessTransactionFactPack | L1 |
| CP-1B | EarningsDelta | L1 |
| CP-1C | PeerBenchmark | L1 |
| CP-2 | FundamentalCreditSynthesizer | L2 |
| CP-2B | DownsidePathway | L2 |
| CP-2C | EventCatalystRegister | L2 |
| CP-2D | GovernanceSponsorScore | L2 |
| CP-2E | LiquidityCashFlowBridge | L2 |
| CP-2F | MacroFXHedgingSensitivity | L2 |
| CP-2G | ESGSustainabilityCreditRisk | L2 |
| CP-3 | RelativeValueSecuritySelection | L3 |
| CP-3B | RecoveryInstrumentPreference | L3 |
| CP-3C | PortfolioFitPositionSizing | L3 |
| CP-3D | RefinancingLMERisk | L3 |
| CP-4 | LegalCovenantInterpreter | L4 |
| CP-4D | RestrictedGroupGuaranteeMap | L4 |
| CP-4C | CovenantCapacityCalculator | L4 |
| CP-5B | EvidenceTraceValidator | L5 |
| CP-5 | ResearchIntegrityQA | L5 |
| CP-6A | ICDebateChallenge | L6 |
| CP-6E | PortfolioDebateChallenge | L6 |
| CP-SR | SectorReview | L7 |
| CP-MON | CreditPulse | L7 |

## Fail/Restrict
- **Blocked:** CP-0 unavailable or critically incomplete → CP-X Status = Blocked, STOP. No route_plan produced.
- **Ready with Limitations:** CP-0 available but some sources flagged Conditional or Not Usable → proceed with limitation propagation.
- **Ownership Conflict:** VE-009 detected → exclude conflicting module, flag violation, continue with remaining modules.

## Version: 2026-06-03
