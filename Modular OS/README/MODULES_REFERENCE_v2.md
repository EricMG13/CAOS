# Modules Reference

## L0 — Source Readiness

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-0 SourceReadiness | Assess source quality and readiness before analysis begins | Source documents: PDF, Word, or text files. Example: annual report, offering memorandum, credit agreement | Source readiness assessment, source quality labels, routing recommendation, source gaps | Upstream: none. Downstream: CP-X |

## Orchestration

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-X PlannerRouter | Route user requests and CP-0 readiness results to the correct modules | CP-0 readiness output, user workflow objective | Route plan, module activation plan, blocked-module list | Upstream: CP-0. Downstream: all analytical modules |

## L1 — Data Foundation

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-1 CanonicalDataFoundation | Normalise financial statements into canonical financial data and KPIs | Financial statements. Example: FY2024/FY2023 income statement, balance sheet, cash flow statement | Canonical financials, KPI dashboard, calculation register, downstream readiness | Upstream: CP-0/CP-X. Downstream: CP-1B, CP-1C, CP-2, CP-2B, CP-2E, CP-3, CP-3D, CP-4, CP-4C |
| CP-1A BusinessTransactionFactPack | Extract business, transaction, ownership, and operating-model facts | Offering memorandum, prospectus, company filings. Example: sponsor acquisition memorandum | Transaction summary, company description, ownership/sponsor register, credit translation summary | Upstream: CP-0/CP-X. Downstream: CP-2, CP-2D |
| CP-1B EarningsDelta | Compare current vs prior period performance | CP-1 canonical financials for at least two periods | Multi-period financial performance table (19 required line items), delta summary, monitoring signals | Upstream: CP-1. Downstream: CP-2, CP-2B |
| CP-1C PeerBenchmark | Compare issuer to peers using 15 core formulas and 6-level peer hierarchy | CP-1 canonical data plus peer company data | Peer selection register, metric comparison, outlier analysis | Upstream: CP-1. Downstream: CP-2, CP-3 |

## L2 — Fundamental Credit Synthesis

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-2 FundamentalCreditSynthesizer | Produce integrated 21-section credit synthesis | CP-1, CP-1A, CP-1B, CP-1C outputs | Credit mechanism map, 9-dimension financial profile, committee memo, credit implications | Upstream: CP-1, CP-1A, CP-1B, CP-1C. Downstream: CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-3, CP-6A |
| CP-2B DownsidePathway | Model stress transmission from operating drivers to credit consequences | CP-1, CP-1B, CP-2 outputs | Causal chains, pathway register, sensitivity matrix, 8 fragility groups, 11 pathway labels | Upstream: CP-1, CP-1B, CP-2. Downstream: CP-3D, CP-6A |
| CP-2C EventCatalystRegister | Identify event catalysts and trigger events | CP-2 output | Catalyst register with timing and credit implications | Upstream: CP-2. Downstream: CP-6A |
| CP-2D GovernanceSponsorScore | Assess governance quality and sponsor / management strength | CP-1A and CP-2 outputs | Governance score, sponsor assessment | Upstream: CP-1A, CP-2. Downstream: CP-6A |
| CP-2E LiquidityCashFlowBridge | Build liquidity assessment and cash-flow bridge | CP-1 and CP-2 outputs | Cash-flow bridge, liquidity assessment | Upstream: CP-1, CP-2. Downstream: CP-3, CP-3D, CP-6A |
| CP-2F MacroFXHedgingSensitivity | Assess macro sensitivity, FX exposure, and hedging | CP-2 output plus any FX / hedging disclosures | Macro sensitivity, FX exposure, hedging assessment | Upstream: CP-2. Downstream: CP-6A |

## L3 — Valuation, Portfolio, and Refinancing

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-3 RelativeValueSecuritySelection | Analyse spread, relative value, and security selection | CP-1, CP-1C, CP-2, CP-2E outputs plus market pricing | RV analysis, spread analysis, security selection | Upstream: CP-1, CP-1C, CP-2, CP-2E. Downstream: CP-3B, CP-3C, CP-6A, CP-6E |
| CP-3B RecoveryInstrumentPreference | Build recovery waterfall and LGD estimates | CP-3 output; capital structure with seniority/subordination | Recovery waterfall, instrument preference, LGD estimates | Upstream: CP-3. Downstream: CP-6A |
| CP-3C PortfolioFitPositionSizing | Assess portfolio fit and size recommendation | CP-3 output plus portfolio constraints | Portfolio fit, sizing posture, 5-input evidence gate, constraint register | Upstream: CP-3. Downstream: CP-6E |
| CP-3D RefinancingLMERisk | Assess refinancing risk, LME risk, and maturity wall | CP-1, CP-2B, CP-2E outputs | Refinancing risk register, LME risk register, maturity wall, 7 path types | Upstream: CP-1, CP-2B, CP-2E. Downstream: CP-4, CP-6A |

## L4 — Legal and Covenant

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-4 LegalCovenantInterpreter | Interpret legal covenants, covenant aggressiveness, and legal/covenant credit implications | CP-1, CP-3D outputs plus credit agreement or indenture | 12 required covenant tables, legal covenant interpretation, aggressiveness rubric | Upstream: CP-1, CP-3D. Downstream: CP-4C, CP-6A |
| CP-4C CovenantCapacityCalculator | Calculate covenant capacity and headroom | CP-4 and CP-1 outputs | Covenant capacity calculations, headroom analysis; each calculation requires formula, numerator, denominator, period, source trace, normalisation | Upstream: CP-4, CP-1. Downstream: CP-6A, CP-6E |

## L5 — Quality Assurance

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-5B EvidenceTraceValidator | Validate evidence lineage and identify orphan claims | Appendix B from all analytical modules | Lineage validation using 8-value taxonomy, orphan claim register | Upstream: all analytical modules. Downstream: CP-5 |
| CP-5 ResearchIntegrityQA | Audit research integrity and gate module outputs | All analytical outputs plus CP-5B trace validation | QA audit across 8 lanes, severity classification, qa_status: Blocked / Restricted / Passed | Upstream: all analytical modules, CP-5B. Downstream: gates upstream outputs |

## L6 — Debate and Decision

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-6A ICDebateChallenge | Run adversarial IC debate and determine action bias | CP-2, CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-3, CP-3B, CP-3D, CP-4, CP-4C | IC action bias, debate resolution matrix, final memo, single greatest uncertainty | Upstream: 11 analytical modules. Downstream: CP-6E |
| CP-6E PortfolioDebateChallenge | Run portfolio debate and determine final portfolio posture | CP-3, CP-3C, CP-4C, CP-6A | Portfolio posture, CIO memo, 9-dimension CIO scoring, binding constraint | Upstream: CP-3, CP-3C, CP-4C, CP-6A. Downstream: terminal |

## Infrastructure

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-DB | Store structured extracted data | CP-EXTRACT JSONL envelopes | Database records | Upstream: CP-EXTRACT |
| CP-RENDER | Render committee-ready reports | Validated module outputs | Full Committee Report, IC Summary, Portfolio Summary | Upstream: all relevant analytical outputs |
| CP-EXTRACT | Parse .docx JSON appendices | Module .docx files | JSONL extraction envelopes for CP-DB | Upstream: analytical module .docx files. Downstream: CP-DB |


## L7 — Sector & Monitoring

| Module | Purpose | Required Inputs | Outputs | Dependencies |
|--------|---------|-----------------|---------|--------------|
| CP-SR SectorReview | Produce sector-level credit review with 7-section output, 6 investigation dimensions, comparative peer table, early warning dashboard, and email intelligence integration | Sector definition, source package, email intelligence (optional), prior review (optional), CP-MON alert feed (optional) | 7-section sector review (executive summary, sector overview, key credit drivers, risk assessment, comparative table, early warning dashboard, strategic implications), sector credit posture enum, dimension scores, credit implication mappings, master index state | Upstream: CP-1, CP-MON, Email Intelligence, Market Data. Downstream: CP-5, CP-6A, CP-6E, CP-MON |
| CP-MON CreditPulse | Continuous credit monitoring, alert generation, rating action tracking, email-driven trigger detection, and early warning flag management | Issuer watchlist, alert thresholds (per REF_CP-SR_E), email feed (per REF_CP-SR_G), market data feeds, CP-SR early warning dashboard | Alert triggers, rating action log, early warning flags, sector stress signals, routing signals for CP-X, watchlist state updates | Upstream: all analytical modules, Email Intelligence, Market Data. Downstream: CP-X, CP-SR, CP-1, CP-3D |

## Cross-Module References

| Reference | Purpose | Scope | Dependencies |
|-----------|---------|-------|--------------|
| REF_CP-EMAIL SourceRoutingMatrix | Standardise email-derived intelligence routing across all CP modules | Defines allowed email categories, use types (Evidence / Context / Trigger / Routing Signal), confidence treatment, staleness rules, and guardrails per module | Referenced by: all modules. Governed by: REF_CP-SR_G (email classification), REF_CP-SR_A (source hierarchy) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-18 | Initial modules reference (22 analytical modules + 3 infrastructure) |
| 2.0 | 2026-06-08 | Added CP-SR (SectorReview), CP-MON (CreditPulse), L7 layer, REF_CP-EMAIL cross-module reference |
