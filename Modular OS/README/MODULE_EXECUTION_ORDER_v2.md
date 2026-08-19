# Module Execution Order

## Canonical Execution Order

| Order | Module | Name | Why It Runs Here |
|-------|--------|------|------------------|
| 1 | CP-0 | SourceReadiness | Entry point; determines source sufficiency |
| 2 | CP-X | PlannerRouter | Routes to eligible modules after CP-0 |
| 3 | CP-1 | CanonicalDataFoundation | Financial base for most downstream modules |
| 4 | CP-1A | BusinessTransactionFactPack | Business and ownership facts; can run with CP-1 |
| 5 | CP-1B | EarningsDelta | Requires CP-1 canonical financials |
| 6 | CP-1C | PeerBenchmark | Requires CP-1 canonical financials |
| 7 | CP-2 | FundamentalCreditSynthesizer | Requires all L1 outputs |
| 8 | CP-2G | ESGSustainabilityCreditRisk | Optional; soft-ordered after CP-1, CP-1A, and CP-2 |
| 9 | CP-2B | DownsidePathway | Requires CP-1, CP-1B, CP-2 |
| 10 | CP-2C | EventCatalystRegister | Requires CP-2 |
| 11 | CP-2D | GovernanceSponsorScore | Requires CP-1A and CP-2 |
| 12 | CP-2E | LiquidityCashFlowBridge | Requires CP-1 and CP-2 |
| 13 | CP-2F | MacroFXHedgingSensitivity | Requires CP-2 |
| 14 | CP-3 | RelativeValueSecuritySelection | Requires CP-1, CP-1C, CP-2, CP-2E |
| 15 | CP-3D | RefinancingLMERisk | Requires CP-1, CP-2B, CP-2E |
| 16 | CP-3B | RecoveryInstrumentPreference | Requires CP-3 and capital structure gates; CP-4D handoff is next-run nullable |
| 17 | CP-3C | PortfolioFitPositionSizing | Requires CP-3 |
| 18 | CP-4 | LegalCovenantInterpreter | Requires CP-1 and CP-3D |
| 19 | CP-4D | RestrictedGroupGuaranteeMap | Optional; soft-ordered after CP-1, CP-1A, and CP-4 |
| 20 | CP-4C | CovenantCapacityCalculator | Requires CP-1; consumes CP-4D only when available |
| 21 | CP-5B | EvidenceTraceValidator | Requires module evidence traces |
| 22 | CP-5 | ResearchIntegrityQA | Requires CP-5B and module outputs |
| 23 | CP-6A | ICDebateChallenge | Consumes CP-2G/CP-4D handoffs only when available |
| 24 | CP-6E | PortfolioDebateChallenge | Requires CP-3, CP-3C, CP-4C, CP-6A |
| 25 | CP-SR | SectorReview | Sector-level analysis; runs independently or after CP-1/CP-MON |
| 26 | CP-MON | CreditPulse | Continuous monitoring; runs independently, feeds CP-X and CP-SR |

## Why Order Matters

1. **Evidence integrity** — Downstream modules must not invent data that upstream modules have not produced.
2. **Calculation consistency** — CP-1 financial definitions propagate into all later calculations.
3. **Dependency enforcement** — Modules such as CP-3B and CP-2B have explicit gates and hard stops.
4. **QA traceability** — CP-5B and CP-5 require completed outputs to validate evidence and research integrity.
5. **Debate completeness** — CP-6A and CP-6E require upstream analytical perspectives before final recommendation.

## Parallel Execution Opportunities

| Parallel Set | Modules | Condition |
|--------------|---------|-----------|
| L1 base | CP-1 and CP-1A | Both can run after CP-0/CP-X |
| L1 follow-on | CP-1B and CP-1C | Both can run after CP-1 |
| L2 submodules | CP-2G, CP-2B, CP-2C, CP-2D, CP-2E, CP-2F | Run after CP-2 and their specific additional inputs |
| L3 branches | CP-3 and CP-3D | Run after respective inputs are complete |
| L3 follow-on | CP-3B and CP-3C | Run after CP-3 |

## Variations by Use Case

| Use Case | Recommended Execution |
|----------|-----------------------|
| Full new credit | Canonical order, all modules |
| Earnings update | CP-0 -> CP-1 -> CP-1B -> CP-2 -> CP-5B -> CP-5 |
| Covenant review | CP-0 -> CP-1 -> CP-3D -> CP-4 -> CP-4C |
| Portfolio sizing | CP-3 -> CP-3C -> CP-6E |
| IC memo only | CP-5B -> CP-5 -> CP-6A, assuming upstream modules already exist |
| Distressed/LME review | CP-1 -> CP-2B -> CP-2E -> CP-3D -> CP-4 -> CP-4C -> CP-6A |

## Non-Contiguous Numbering

Some apparent module numbers are intentionally skipped:

- CP-2A does not exist.
- CP-3A does not exist.
- CP-4A and CP-4B do not exist.
- CP-5A does not exist.
- CP-6B, CP-6C, and CP-6D do not exist.

This is by design and does not indicate missing files.


## Sector & Monitoring Execution Notes

CP-SR and CP-MON sit outside the issuer-level L0–L6 pipeline and can be executed:
- **Independently** — CP-SR runs a standalone sector review without requiring a full issuer-level workflow.
- **In parallel** — CP-SR and CP-MON can run concurrently with any issuer-level module.
- **As upstream triggers** — CP-MON alerts can trigger CP-X to route to issuer-level modules (CP-1 refresh, CP-3D update, CP-6A debate).
- **As downstream consumers** — CP-SR consumes CP-1 issuer profiles and CP-MON alert feeds; CP-MON consumes early warning dashboards from CP-SR.

### Additional Parallel Execution Opportunities

| Parallel Set | Modules | Condition |
|---|---|---|
| Sector & Monitoring | CP-SR and CP-MON | Both can run in parallel with any issuer-level module |
| Sector + Issuer Intake | CP-SR and CP-1 | CP-SR sector context enriches CP-1 issuer intake |
| Monitoring + Full Pipeline | CP-MON alongside L1–L6 | CP-MON provides real-time alerts while issuer analysis runs |

### Additional Variations by Use Case

| Use Case | Recommended Execution |
|---|---|
| Sector credit review | CP-SR (standalone) or CP-SR -> CP-1 for issuer deep-dives |
| Monitoring-driven refresh | CP-MON alert -> CP-X -> relevant module refresh |
| Email-enriched full analysis | CP-MON (email intake) -> CP-0 -> CP-X -> full L1–L6 pipeline with email intelligence feeding CP-SR, CP-5, CP-6A |
| Sector + portfolio allocation | CP-SR -> CP-5 -> CP-6A -> CP-6E |

### Updated Non-Contiguous Numbering Note

Some apparent module numbers are intentionally skipped:
- CP-2A does not exist.
- CP-3A does not exist.
- CP-4A and CP-4B do not exist.
- CP-5A does not exist.
- CP-6B, CP-6C, and CP-6D do not exist.
- CP-SR and CP-MON use descriptive IDs rather than numeric suffixes.

This is by design and does not indicate missing files.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-18 | Initial execution order (22 modules) |
| 2.0 | 2026-06-08 | Added CP-SR and CP-MON, sector/monitoring execution notes, new parallel sets and use case variations |
| 2.1 | 2026-07-15 | Added independently flagged CP-2G and CP-4D with soft downstream handoffs |
