<!-- CP-COMMON PREAMBLE v3.4 | 2026-07-15 | CP-2G and CP-4D route metadata added; CAOS runtime overlay remains authoritative for export -->
<cp_common_preamble version="v3.4">
<priority_legend>
| Priority | Meaning | On Violation |
|----------|---------|--------------|
| critical | Must be satisfied | Output rejection |
| standard | Expected | QA flag + review |
| reference | As needed | No flag |
</priority_legend>
<module_manifest>
<!-- v2 Canonical taxonomy. Roles = module_name per MODULES_REFERENCE_v2. Feeds = downstream edges per SYSTEM_ROUTE_MAP_v2. -->
| Module | Layer | Role (module_name) | Feeds |
|--------|-------|--------------------|-------|
| CP-0 | L0 | SourceReadiness | CP-X |
| CP-X | LX | PlannerRouter | All analytical |
| CP-1 | L1 | CanonicalDataFoundation | CP-1B, CP-1C, CP-2, CP-2B, CP-2E, CP-3, CP-3D, CP-4, CP-4C |
| CP-1A | L1 | BusinessTransactionFactPack | CP-2, CP-2D |
| CP-1B | L1 | EarningsDelta | CP-2, CP-2B |
| CP-1C | L1 | PeerBenchmark | CP-2, CP-3 |
| CP-2 | L2 | FundamentalCreditSynthesizer | CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-3, CP-6A |
| CP-2B | L2 | DownsidePathway | CP-3D, CP-6A |
| CP-2C | L2 | EventCatalystRegister | CP-6A |
| CP-2D | L2 | GovernanceSponsorScore | CP-6A |
| CP-2E | L2 | LiquidityCashFlowBridge | CP-3, CP-3D, CP-6A |
| CP-2F | L2 | MacroFXHedgingSensitivity | CP-6A |
| CP-2G | L2 | ESGSustainabilityCreditRisk | CP-6A |
| CP-3 | L3 | RelativeValueSecuritySelection | CP-3B, CP-3C, CP-6A, CP-6E |
| CP-3B | L3 | RecoveryInstrumentPreference | CP-6A |
| CP-3C | L3 | PortfolioFitPositionSizing | CP-6E |
| CP-3D | L3 | RefinancingLMERisk | CP-4, CP-6A |
| CP-4 | L4 | LegalCovenantInterpreter | CP-4C, CP-6A |
| CP-4D | L4 | RestrictedGroupGuaranteeMap | CP-4C, CP-6A, CP-3B (next run) |
| CP-4C | L4 | CovenantCapacityCalculator | CP-6A, CP-6E |
| CP-5B | L5 | EvidenceTraceValidator | CP-5 |
| CP-5 | L5 | ResearchIntegrityQA | Gates upstream outputs |
| CP-6A | L6 | ICDebateChallenge | CP-6E |
| CP-6E | L6 | PortfolioDebateChallenge | Terminal |
| CP-SR | L7 | SectorReview | CP-5, CP-6A, CP-6E, CP-MON |
| CP-MON | L7 | CreditPulse | CP-X, CP-SR, CP-1, CP-3D |
| CP-RENDER | Infra | Report Renderer | Reports |
| CP-EXTRACT | Infra | Appendix Parser | CP-DB |
| CP-DB | Infra | Structured Store | — |
</module_manifest>
<common_rules priority="critical" enforcement="hard">
1. Source boundary enforcement 2. Evidence>Risk Mechanic>Credit Implication chain
3. [Insufficient Information] marking 4. Not Calculable from Provided Materials
5. Null != zero unless sourced 6. Preserve evidence/QA/downstream metadata
7. No silent QA repair 8. Renderer anti-fabrication 9. No fabrication
10. Upstream re-anchor: at input gate, re-import & verify the specific upstream values this module consumes; gate (do not improvise) if absent (see <upstream_reanchor>)
</common_rules>
<upstream_reanchor priority="critical" enforcement="hard">
## Upstream Re-Anchor Gate
Modular prompting runs in one accumulating context; do not assume an upstream module's output is
still in-window. At the start of every run, the module's source/input gate MUST re-anchor:
1. **Re-import** the specific upstream datapoints this module consumes (per `upstream_artifacts_used`
   and the module's declared Upstream) — restate them explicitly in the input gate. Examples:
   CP-1C re-imports the CP-1 KPI/calculation register values; CP-2 re-imports CP-1/CP-1A/CP-1B/CP-1C
   outputs; CP-6A re-imports the 11 analytical feeds; CP-4C re-imports CP-4 covenant definitions.
2. **Verify presence.** If a required upstream value is absent, unidentifiable, or its run_id/period
   does not match this run, mark `[Insufficient Information]` and gate the dependent step — do NOT
   re-derive, infer, or improvise the upstream value from memory.
3. **Carry provenance.** Each re-anchored value keeps its source module_id, run_id, and period so
   CP-5B can trace lineage and CP-5 can detect cross-module drift.
This makes shared-context deduplication safe under context drift / window truncation.
</upstream_reanchor>
<export_contract priority="critical">
Single .docx: sections + Appendix A-E (HANDOFF, EVIDENCE+SOURCE, QA, MANIFEST, GAPS).
Filename: [Issuer]_[Module]_[YYYYMMDD].docx. All 5 appendices required.
</export_contract>
<common_envelope>
module_id | run_id | issuer_name | issuer_id_or_key | reporting_period |
source_documents_used | upstream_artifacts_used | key_claims |
key_credit_mechanisms | evidence_trace | confidence_level | limitation_flags |
qa_status | validation_warnings | downstream_consumers | module_payload
</common_envelope>
</cp_common_preamble>
