# CP Module Taxonomy Reconciliation
Version: 1.0 | Created: 2026-06-08
Resolves: Audit F-2 (conflicting module taxonomies)
Status: **RESOLVED 2026-06-08; FULLY APPLIED 2026-06-20.** Owner ratified Taxonomy A (v2 Canonical). 2026-06-08 rewrite covered the email matrix (24 `REF_CP-EMAIL_SourceRoutingMatrix.md` copies → v2.0) and `CP-COMMON_PREAMBLE.md` module_manifest (v3.3, L7 + infra, `Feeds:TBD` resolved) — but it **did not reach `CP-X/SYSTEM_REFERENCE.md` (the route graph), `CP-X/REF_CP-X_ExampleOutputPattern.md`, or `CP_ONBOARDING_DOCUMENTATION_v2.txt`**, which still carried legacy names for ~18 modules (incl. lane-swaps CP-3B/CP-3D/CP-4C). 2026-06-20: those three files re-synced to Taxonomy A, CP-1A schema `module_name` corrected (`BusinessTransactionSummary` → `BusinessTransactionFactPack`), and L5/L7 rows added to the CP-X route graph. Verified by `tools/check_module_consistency.py` (24/24, 0 drift across schema / ACTIVE_PROMPT / CP-X route / onboarding). Recommendation and mapping retained below for the record.

## 1. The conflict

Two different module taxonomies coexist in the v2 corpus and disagree on what several CP-IDs *are*:

- **Taxonomy A — v2 Canonical** (used by `MODULES_REFERENCE_v2.md`, `SYSTEM_ROUTE_MAP_v2.md`, `MODULE_EXECUTION_ORDER_v2.md`, and the 22 files in `KNOWLEDGE SOURCES/02_SCHEMA/MODULE_PAYLOADS/`). All dated v2.0 / 2026-06-08.
- **Taxonomy B — Legacy** (embedded in `KNOWLEDGE SOURCES/00_GOVERNANCE/CP-COMMON_PREAMBLE.md` `module_manifest` and in all 24 copies of `REF_CP-EMAIL_SourceRoutingMatrix.md`).

Because `REF_CP-EMAIL` is referenced by **every** module, its labels determine where email-derived intelligence is routed. Under Taxonomy A numbering, those routes point at the **wrong modules**.

## 2. Point-by-point disagreement

| CP-ID | Taxonomy A — v2 Canonical (authoritative) | Taxonomy B — Legacy (in REF_CP-EMAIL / preamble) | Severity |
|---|---|---|---|
| CP-2 | FundamentalCreditSynthesizer | "Earnings & Cash Flow" | Label drift (same lane) |
| CP-2D | GovernanceSponsorScore | "Downside Scenario" | **Wrong lane** (downside = CP-2B in A) |
| CP-2E | LiquidityCashFlowBridge | "EBITDA Quality / Addback Review" | **Wrong lane** |
| CP-3 | RelativeValueSecuritySelection | "Capital Structure" | **Wrong lane** |
| CP-3C | PortfolioFitPositionSizing | "Maturity Profile" | **Wrong lane** |
| CP-3D | RefinancingLMERisk | "Debt Dynamics / Refinancing & LME" | Aligned (label only) |
| CP-4 | LegalCovenantInterpreter | "Covenant Analysis" | Aligned (label only) |
| CP-5 | ResearchIntegrityQA | "Relative Value" | **Wrong lane** |
| CP-5B | EvidenceTraceValidator | "Market Context" | **Wrong lane** |
| CP-6A | ICDebateChallenge | "Legal / Structural" | **Wrong lane** |

CP-0, CP-1, CP-1A, CP-X, CP-6E are consistent across both.

## 3. Recommendation — adopt Taxonomy A (v2 Canonical) as authoritative

Rationale:
1. **Corroboration.** Taxonomy A is asserted independently by three v2.0 artifacts (modules reference, route map, execution order) **and** hard-coded as `const` values in the 22 payload schemas (e.g. `CP-3.module_name = "RelativeValueSecuritySelection"`, `CP-5.module_name = "ResearchIntegrityQA"`). Taxonomy B appears only in two cross-cutting files that were not re-synced to v2.
2. **Internal consistency.** The route map's dependency edges (e.g. CP-5B→CP-5 as the QA loop; CP-3→CP-3B/3C; CP-6A convergence on 11 analytical feeds) only make sense under Taxonomy A.
3. **Schema enforcement.** The payload-schema `const module_name` values will *reject* any output using Taxonomy B names, so A is already the enforced contract.

**Therefore:** `REF_CP-EMAIL` and `CP-COMMON_PREAMBLE.module_manifest` carry stale labels and must be re-synced to Taxonomy A.

## 4. Corrected email-routing intent (Taxonomy A)

The *semantics* of each email matrix section should be re-pointed to the correct v2 module. Key corrections:

| REF_CP-EMAIL section (current) | Should govern (v2 module) | Note |
|---|---|---|
| §4.5 "CP-2E EBITDA Quality" | **CP-2E LiquidityCashFlowBridge** | EBITDA-quality guidance belongs under CP-2/CP-1; liquidity email rules belong here |
| §4.6 "CP-3 Capital Structure" | **CP-3 RelativeValueSecuritySelection** | Capital-structure email rules belong under CP-1/CP-1A; RV/pricing email rules belong here |
| §4.7 "CP-3C Maturity Profile" | **CP-3C PortfolioFitPositionSizing** | Maturity-wall email rules belong under CP-3D |
| §4.11 "CP-5 Relative Value" | **CP-5 ResearchIntegrityQA** | RV email rules belong under CP-3; CP-5 is QA (mostly Context/Trigger, not Evidence) |
| §4.12 "CP-5B Market Context" | **CP-5B EvidenceTraceValidator** | Market-context email rules belong under CP-3; CP-5B validates lineage |

**Implication:** this is not a find-replace of labels — several sections' *content* (allowed Evidence/Context/Trigger rules) was written for the legacy lane and must be re-authored for the correct v2 lane. The "Relative Value" email rules, for instance, are analytically correct but currently attached to CP-5 (QA) — they should move to CP-3.

## 5. Required corrective actions (pending ratification)

1. Rewrite `CP-COMMON_PREAMBLE.md` `module_manifest` to Taxonomy A (and add L7: CP-SR, CP-MON). Replace the `Feeds: TBD` placeholders.
2. Re-author `REF_CP-EMAIL_SourceRoutingMatrix.md` section headers **and** per-section rules to Taxonomy A, then re-sync all 24 module copies from the single canonical source in `02_SCHEMA/REF_CP-EMAIL_CANONICAL_LOCATION.md`.
3. Add a CI check: assert every `module_name` in prose matches the `const` in the corresponding payload schema.

## 6. Decision needed from owner

> Confirm Taxonomy A (v2 Canonical) is authoritative. On confirmation, the §5 corrective rewrite of `REF_CP-EMAIL` (×24) and `CP-COMMON_PREAMBLE` can proceed. If Taxonomy B is in fact intended, the conflict is far larger (the route map, execution order, and 22 payload schemas would all need reversion) and should be escalated.
