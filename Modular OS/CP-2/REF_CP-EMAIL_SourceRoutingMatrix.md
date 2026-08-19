# REF_CP-EMAIL | Source Routing Matrix
# Version: 2.0 | Date: 2026-06-08
# Parent System: CP Agents — Credit Analysis Co-Pilot
# Purpose: Standardize how email-derived intelligence routes into existing CP modules

---

## 1. Purpose

`REF_CP-EMAIL_SourceRoutingMatrix.md` defines how email-derived intelligence should be used across the CP modular credit operating system. It establishes:

1. Which email categories are permitted for each module
2. Whether emails may be used as **Evidence**, **Context**, **Trigger**, or **Routing Signal**
3. Applicable source tier and confidence treatment
4. Email-specific staleness rules
5. Guardrails to prevent emails from replacing primary documents where primary evidence is required

This reference file is intended to work alongside:

- `REF_CP-SR_G_EmailSourceClassification.md`
- `REF_CP-SR_A_InputSchema.md`
- `CP-SR_SectorReview.schema.md`
- CP-MON alert logic
- CP-X execution routing logic

> **v2.0 taxonomy note (Audit F-2 resolved):** This matrix has been re-pointed to the **v2 Canonical** module taxonomy (`MODULES_REFERENCE_v2.md` + the `02_SCHEMA/MODULE_PAYLOADS/` `const module_name` values). Section headers and per-module rules now reflect each module's true v2 function. Key corrections vs. v1.0: CP-3 = RelativeValueSecuritySelection (was "Capital Structure"); CP-3C = PortfolioFitPositionSizing (was "Maturity Profile"); CP-2E = LiquidityCashFlowBridge (was "EBITDA Quality"); CP-5 = ResearchIntegrityQA (was "Relative Value"); CP-5B = EvidenceTraceValidator (was "Market Context"). See `README/TAXONOMY_RECONCILIATION.md`.

---

## 2. Core Principle

Emails are a powerful source of **timely institutional intelligence**, but they should not be treated uniformly across modules.

Use emails as:

| Use Type | Definition | Examples |
|---|---|---|
| Evidence | Email content can directly support a conclusion, subject to tier and confidence rules | Rating action alert, internal analyst write-up, forwarded agency rationale |
| Context | Email enriches interpretation but does not independently prove the conclusion | Sell-side view, event invite, market color |
| Trigger | Email initiates a module run, refresh, or alert | Downgrade alert, new issue launch, M&A headline |
| Routing Signal | Email tells CP-X which module should run next | LME alert routes to CP-3D + CP-6A + CP-4 |

Emails should **augment, not replace**, primary documentation.

---

## 3. Email Category Reference

| Email Category | Default Tier | Typical Use | Staleness Rule |
|---|---:|---|---|
| RATING_ACTION | 1.5 | Evidence / Trigger | Permanent for rating history; refresh if superseded |
| INTERNAL_RESEARCH | 1.5 | Evidence / Context | Review after 90 days unless reaffirmed |
| SELL_SIDE_RESEARCH | 2.0 | Evidence / Context | Stale after 90 days unless updated |
| SELL_SIDE_NEWS | 2.0 | Trigger / Context | Event-specific; refresh if superseded |
| TRADING_DESK | 2.5 | Context / Trigger | Stale after 5 business days for pricing |
| MARKET_DATA | 2.5 | Context / Trigger | Stale after 5–10 business days depending on data type |
| EVENT_INVITE | 3.0 | Context / Trigger | Stale after event date |
| INTERNAL_COMMS | 3.0 | Context / Routing Signal | Stale after purpose is resolved |

---

## 4. Module Routing Matrix

> Section headers use the v2 Canonical `module_name`. Module IDs are authoritative; the parenthetical names match `MODULES_REFERENCE_v2.md`.

### 4.1 CP-0 — SourceReadiness (Intake Gate)

| Email Category | Allowed Use | Confidence Treatment | Routing / Output Impact |
|---|---|---|---|
| RATING_ACTION | Trigger / Context | Tier 1.5 | Adds rating report to missing-source checklist |
| INTERNAL_RESEARCH | Context / Evidence | Tier 1.5 | Identifies existing analyst work; may reduce duplicated intake work |
| SELL_SIDE_RESEARCH | Context | Tier 2 | Adds potential source to source register |
| SELL_SIDE_NEWS | Trigger | Tier 2 | Flags need for updated document pack |
| TRADING_DESK | Context | Tier 2.5 | Flags market data gap if pricing mentioned |
| MARKET_DATA | Context | Tier 2.5 | Flags need for market pricing source |
| EVENT_INVITE | Context | Tier 3 | Adds possible event follow-up item |
| INTERNAL_COMMS | Routing Signal | Tier 3 | Helps locate attachments, prior reviews, or team context |

**Guardrail:** CP-0 may use emails to discover documents, but should not mark a source as processed unless the attachment or linked document has actually been ingested.

---

### 4.2 CP-X — PlannerRouter (Execution Router)

| Email Category | Allowed Use | Routing Logic |
|---|---|---|
| RATING_ACTION | Trigger / Routing Signal | Route to CP-MON, CP-1 refresh, CP-6A if adverse |
| INTERNAL_RESEARCH | Routing Signal | Route to relevant analytical module based on issuer/topic |
| SELL_SIDE_RESEARCH | Routing Signal | Route to CP-SR, CP-3, CP-6A depending on content |
| SELL_SIDE_NEWS | Trigger / Routing Signal | Route based on event type: M&A, new issue, default, LME |
| TRADING_DESK | Trigger | Route to CP-3 / CP-MON |
| MARKET_DATA | Trigger | Route to CP-MON / CP-3 |
| EVENT_INVITE | Routing Signal | Route to watchlist / calendar context only |
| INTERNAL_COMMS | Routing Signal | Route to requested module if explicit |

**Guardrail:** CP-X should route based on email classification and extracted event type, not infer unsupported analytical conclusions. CP-X consumes only CP-0 output and the routing index — it does not perform analysis on email content.

---

### 4.3 CP-1 — CanonicalDataFoundation (Issuer / Financial Intake)

| Email Category | Allowed Use | Evidence Status | Typical Fields Updated |
|---|---|---|---|
| RATING_ACTION | Evidence / Trigger | Allowed | rating, outlook, rating rationale, date |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | issuer description, credit direction, business risk summary |
| SELL_SIDE_RESEARCH | Context / Evidence | Allowed with citation | operating issues, catalysts, peer views |
| SELL_SIDE_NEWS | Trigger / Context | Allowed for event log | recent events, transactions, M&A, ratings |
| TRADING_DESK | Context | Not primary evidence | market sentiment, liquidity comments |
| MARKET_DATA | Context | Not primary evidence unless direct market quote | price move, spread context |
| EVENT_INVITE | Context | Not evidence | upcoming issuer event |
| INTERNAL_COMMS | Context | Not final evidence | team context, source location |

**Guardrail:** CP-1 canonical financials must come from filings, lender reports, or OMs — never from email summaries. Emails can update the event log and identify required sources. (Business/ownership/transaction facts are owned by CP-1A; route those email items there.)

---

### 4.4 CP-2 — FundamentalCreditSynthesizer (Financial Synthesis)

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Context / Evidence | Allowed for agency-adjusted metrics | leverage thresholds, rating sensitivities |
| INTERNAL_RESEARCH | Context / Evidence | Allowed if calculations shown | preliminary earnings interpretation |
| SELL_SIDE_RESEARCH | Context | Use with caution | EBITDA bridge commentary, guidance views |
| SELL_SIDE_NEWS | Trigger | Not core evidence | earnings release alert, restatement alert |
| TRADING_DESK | Not recommended | Not evidence | none except market reaction note |
| MARKET_DATA | Context | Not financial evidence | price reaction to earnings |
| EVENT_INVITE | Not recommended | Not evidence | none |
| INTERNAL_COMMS | Context | Not evidence | locating financial attachments |

**Guardrail:** CP-2 final numbers must come from CP-1 canonical financials, filings, lender reports, or extracted source documents. Emails may explain interpretation but are never the primary basis for calculations.

---

### 4.5 CP-2E — LiquidityCashFlowBridge

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Context / Evidence | Allowed | agency liquidity assessment, refinancing-runway view |
| INTERNAL_RESEARCH | Evidence / Context | Allowed if based on a schedule | liquidity runway notes, RCF-draw tracking |
| SELL_SIDE_RESEARCH | Context | Allowed with caveat | cash-burn / liquidity commentary |
| SELL_SIDE_NEWS | Trigger | Not core evidence | RCF draw, dividend suspension, covenant waiver affecting liquidity |
| TRADING_DESK | Context | Not evidence | liquidity/tradability color |
| MARKET_DATA | Context | Not evidence | market access signal |
| EVENT_INVITE | Not recommended | Not evidence | none |
| INTERNAL_COMMS | Context | Not evidence | locating cash-flow / treasury attachments |

**Guardrail:** Cash-flow bridge and liquidity figures (cash on hand, RCF availability, near-term maturities, FCF) require filings, lender reports, or credit-agreement schedules. Email may flag a liquidity event but never sizes the bridge.

---

### 4.6 CP-3 — RelativeValueSecuritySelection

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence / Context | Allowed | instrument ratings, recovery ratings, rating-driven RV |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | internal RV recommendation logic |
| SELL_SIDE_RESEARCH | Evidence / Context | Allowed with citation | recommendations, trade ideas, RV views |
| SELL_SIDE_NEWS | Trigger / Context | Allowed | new issue, M&A, ratings event |
| TRADING_DESK | Context / Evidence for market color | Allowed with staleness | axes, bids/offers, pricing, flow skew |
| MARKET_DATA | Context / Evidence for market levels | Allowed with staleness | spreads, CDS, bond/loan prices |
| EVENT_INVITE | Context | Not evidence | upcoming catalyst |
| INTERNAL_COMMS | Context | Not evidence | team view, routing |

**Guardrail:** CP-3 may use trading-desk and market-data emails for spread/RV color but must flag date/time and staleness, and reconcile security-selection conclusions with independent market data where available.

---

### 4.7 CP-3C — PortfolioFitPositionSizing

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence / Trigger | Allowed | mandate fit, rating constraint, watchlist status |
| INTERNAL_RESEARCH | Context / Evidence | Allowed | internal positioning / sizing view |
| SELL_SIDE_RESEARCH | Context | Allowed with citation | sector allocation views |
| SELL_SIDE_NEWS | Trigger / Context | Allowed | event risk affecting position |
| TRADING_DESK | Context | Allowed with staleness | liquidity, tradability, flow skew |
| MARKET_DATA | Context | Allowed with staleness | liquidity indicators, position-level pricing |
| EVENT_INVITE | Not recommended | Not evidence | none |
| INTERNAL_COMMS | Context | Not evidence | PM / team sizing constraints |

**Guardrail:** Sizing requires the 5-input evidence gate (portfolio constraints, liquidity, mandate, rating, RV). Emails supplement the gate and must never be the sole basis for a sizing or allocation decision.

---

### 4.8 CP-3D — RefinancingLMERisk (Refinancing & LME Pathway)

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence / Trigger | Allowed | default, distressed exchange, downgrade rationale |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | analyst pathway classification, maturity-wall notes |
| SELL_SIDE_RESEARCH | Context / Evidence | Allowed with citation | LME interpretation, restructuring view |
| SELL_SIDE_NEWS | Trigger / Evidence | Allowed | amend-and-extend, tender, exchange, recap, sale process, refi launch |
| TRADING_DESK | Context / Trigger | Not final evidence | distressed pricing, loan levels, creditor sentiment |
| MARKET_DATA | Context / Trigger | Not final evidence | bond/loan price stress |
| EVENT_INVITE | Trigger only | Not evidence | lender call, restructuring call |
| INTERNAL_COMMS | Context | Not evidence | internal escalation |

**Guardrail:** CP-3D can classify a provisional pathway and maturity-wall view from emails, but final classification and maturity-wall calculations require transaction documents, company announcements, or formal debt schedules.

---

### 4.9 CP-4 — LegalCovenantInterpreter (Covenant Analysis)

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Context | Not covenant evidence | agency covenant comments |
| INTERNAL_RESEARCH | Context | Not final evidence | issue spotting |
| SELL_SIDE_RESEARCH | Context | Not final evidence | covenant concern flag |
| SELL_SIDE_NEWS | Trigger | Not final evidence | amendment, waiver, consent solicitation |
| TRADING_DESK | Not recommended | Not evidence | none |
| MARKET_DATA | Not recommended | Not evidence | none |
| EVENT_INVITE | Trigger only | Not evidence | lender call |
| INTERNAL_COMMS | Context | Not evidence | locating legal docs |

**Guardrail:** Covenant analysis must rely on credit agreements, indentures, amendments, compliance certificates, and legal source documents.

---

### 4.10 CP-4C — CovenantCapacityCalculator (Capacity / Headroom)

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Context | Not calculation evidence | rating sensitivity / covenant mention |
| INTERNAL_RESEARCH | Context | Not calculation evidence unless source calculations included | analyst concern flag |
| SELL_SIDE_RESEARCH | Context | Not calculation evidence | third-party capacity discussion |
| SELL_SIDE_NEWS | Trigger | Not calculation evidence | amendment / waiver / RP issue |
| TRADING_DESK | Not recommended | Not evidence | none |
| MARKET_DATA | Not recommended | Not evidence | none |
| EVENT_INVITE | Not recommended | Not evidence | none |
| INTERNAL_COMMS | Context | Not evidence | source location |

**Guardrail:** Never calculate baskets, RP capacity, debt capacity, liens, or investments from email summaries alone.

---

### 4.11 CP-5 — ResearchIntegrityQA

CP-5 audits research integrity and gates outputs; it does **not** introduce new analytical evidence. Email is used here mainly to **audit** whether upstream modules applied this matrix correctly (tier, citation, staleness), and as a **trigger** to re-audit when a source is superseded.

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Context / Trigger | Not new evidence | verify rating claims are tiered/cited; trigger re-audit if superseded |
| INTERNAL_RESEARCH | Context | Not new evidence | check internal-email citations in module outputs |
| SELL_SIDE_RESEARCH | Context | Not new evidence | check sell-side email is labelled Context, not Evidence, where required |
| SELL_SIDE_NEWS | Trigger | Not new evidence | trigger re-audit on material event |
| TRADING_DESK | Context | Not evidence | verify staleness flags on market-color emails |
| MARKET_DATA | Context | Not evidence | verify staleness window compliance |
| EVENT_INVITE | Not recommended | Not evidence | none |
| INTERNAL_COMMS | Context | Not evidence | audit trail / process notes |

**Guardrail:** CP-5 must not add email-derived analytical conclusions. Its email use is limited to the **email source-audit lane** — confirming downstream modules cited email evidence within the permissions of this matrix — and to triggering re-audit.

---

### 4.12 CP-5B — EvidenceTraceValidator

CP-5B validates claim-to-source lineage. Email-derived claims are validated, not authored.

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Context | Not new evidence | confirm rating claim resolves to a cited rating email/report |
| INTERNAL_RESEARCH | Context | Not new evidence | confirm internal-email claim carries required metadata |
| SELL_SIDE_RESEARCH | Context | Not new evidence | confirm citation present for sell-side-derived claims |
| SELL_SIDE_NEWS | Context | Not new evidence | confirm event claim links to a real email/source |
| TRADING_DESK | Context | Not evidence | confirm date/time stamp present |
| MARKET_DATA | Context | Not evidence | confirm staleness metadata present |
| EVENT_INVITE | Not recommended | Not evidence | none |
| INTERNAL_COMMS | Context | Not evidence | none |

**Guardrail:** An email-derived claim with only a hyperlink and no substantive content, or missing required metadata (sender/date/category/tier), is an **orphan-claim candidate** and must be flagged to CP-5.

---

### 4.13 CP-6A — ICDebateChallenge (Adversarial Debate)

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence / Context | Allowed | agency bull/bear rationale |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | internal debate setup |
| SELL_SIDE_RESEARCH | Evidence / Context | Allowed | external bull/bear arguments |
| SELL_SIDE_NEWS | Trigger / Context | Allowed | event-risk setup |
| TRADING_DESK | Context | Allowed with caveat | market skepticism or support |
| MARKET_DATA | Context | Allowed | price reaction, spread widening |
| EVENT_INVITE | Context | Not evidence | pending catalyst |
| INTERNAL_COMMS | Context | Not evidence | internal controversy or PM concern |

**Guardrail:** Debate modules may use emails to enrich arguments, but the IC Chair conclusion must distinguish source-backed evidence from market opinion.

---

### 4.14 CP-6E — PortfolioDebateChallenge (Allocation Challenge)

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence / Trigger | Allowed | mandate fit, rating constraint, watchlist |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | internal positioning view |
| SELL_SIDE_RESEARCH | Context / Evidence | Allowed with citation | sector allocation views |
| SELL_SIDE_NEWS | Trigger / Context | Allowed | event risk, supply, M&A, default |
| TRADING_DESK | Context | Allowed with staleness | liquidity, flow skew, tradability |
| MARKET_DATA | Context / Evidence | Allowed | spreads, prices, liquidity indicators |
| EVENT_INVITE | Context | Not evidence | catalyst calendar |
| INTERNAL_COMMS | Context | Not evidence | PM / team concerns |

**Guardrail:** Sizing and allocation should not be based solely on emails. Emails supplement the 5-input sizing evidence gate carried from CP-3C.

---

### 4.15 CP-SR — SectorReview

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence / Trigger | Allowed | rating drift, downgrade momentum |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | internal sector views |
| SELL_SIDE_RESEARCH | Evidence / Context | Allowed | sector outlook, trade ideas |
| SELL_SIDE_NEWS | Trigger / Evidence | Allowed | M&A, LME, default, new issue events |
| TRADING_DESK | Context / Evidence for market color | Allowed with staleness | pricing, stress, flow commentary |
| MARKET_DATA | Context / Evidence | Allowed | index levels, spreads, price moves |
| EVENT_INVITE | Context / Trigger | Not final evidence | upcoming sector catalyst |
| INTERNAL_COMMS | Context | Not evidence | sector review preparation |

**Guardrail:** CP-SR may integrate emails formally via Step A.2, but conclusions must show confidence levels and source tiers.

---

### 4.16 CP-MON — CreditPulse Monitoring

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Trigger / Evidence | Allowed | rating action alert, outlook change |
| INTERNAL_RESEARCH | Trigger / Context | Allowed | internal escalation |
| SELL_SIDE_RESEARCH | Trigger / Context | Allowed | recommendation changes, sector stress |
| SELL_SIDE_NEWS | Trigger / Evidence | Allowed | default, LME, M&A, new issue |
| TRADING_DESK | Trigger / Context | Allowed with short staleness | price stress, distressed axes |
| MARKET_DATA | Trigger / Evidence | Allowed | spread/price threshold breach |
| EVENT_INVITE | Trigger / Context | Not evidence | upcoming event monitoring |
| INTERNAL_COMMS | Trigger / Routing Signal | Context only | internal watchlist instruction |

**Guardrail:** CP-MON should preserve the triggering email but route substantive analysis to the relevant downstream module.

---

### 4.17 Infrastructure — CP-RENDER / CP-EXTRACT / Reporting Appendices

| Email Category | Allowed Use | Evidence Status | Typical Use |
|---|---|---|---|
| RATING_ACTION | Evidence | Allowed | appendix event log |
| INTERNAL_RESEARCH | Evidence / Context | Allowed | internal evidence register |
| SELL_SIDE_RESEARCH | Context | Allowed with citation | external views appendix |
| SELL_SIDE_NEWS | Context / Evidence | Allowed | event timeline |
| TRADING_DESK | Context | Allowed with date/time | market color appendix |
| MARKET_DATA | Context / Evidence | Allowed | pricing timeline |
| EVENT_INVITE | Context | Not evidence | catalyst calendar |
| INTERNAL_COMMS | Context | Not evidence | process trail |

**Guardrail:** Reporting/rendering modules must label email-derived content clearly as email-derived, preserve sender/date metadata, and never fabricate beyond the validated module payloads.

---

## 5. Standard Routing Signals

> Module IDs below are v2 Canonical. (CP-3 = RelativeValue, CP-3C = sizing, CP-3D = refinancing/LME, CP-5/5B = QA.)

| Email-Derived Event | Primary Module | Secondary Modules |
|---|---|---|
| Rating downgrade | CP-MON | CP-1, CP-3, CP-6A, CP-6E |
| Negative outlook / CreditWatch | CP-MON | CP-1, CP-6A |
| New issue launch | CP-3 | CP-3C, CP-MON |
| Tender / exchange offer | CP-3D | CP-3, CP-6A, CP-4 |
| Amend-and-extend | CP-3D | CP-4, CP-6A |
| Distressed exchange / default | CP-MON | CP-3D, CP-6A, CP-6E |
| M&A / asset sale | CP-1 | CP-3, CP-6A, CP-SR |
| Trading price drop | CP-MON | CP-3, CP-6A |
| Sector outlook / strategy note | CP-SR | CP-3, CP-6E |
| Internal analyst write-up | CP-1 | CP-2, CP-3, CP-6A |
| Covenant amendment alert | CP-4 | CP-4C, CP-3D |
| Liquidity / RCF-draw alert | CP-MON | CP-2E, CP-3D |
| Lender call invite | CP-3D | CP-MON, CP-1 |

---

## 6. Confidence Treatment

| Email Tier | Confidence Handling |
|---|---|
| Tier 1.5 | Can support High confidence if internally authored or directly quotes agency/company data and is corroborated |
| Tier 2 | Can support Medium or High confidence when corroborated by another Tier 1/2 source |
| Tier 2.5 | Usually Medium for market color; Low if stale or uncorroborated |
| Tier 3 | Context only unless supported by higher-tier evidence |
| Tier 4 | Unverified; cannot support final conclusions |

---

## 7. Prohibited Uses

Emails must **not** be used as the sole basis for:

1. Covenant basket capacity calculations (CP-4C)
2. Restricted payment capacity (CP-4C)
3. Debt incurrence capacity (CP-4C)
4. Legal interpretation of indentures or credit agreements (CP-4)
5. Final financial statement metrics if primary financials are available (CP-1, CP-2)
6. Liquidity / cash-flow bridge figures where schedules are required (CP-2E)
7. Recovery analysis where legal/source documents are required (CP-3B)
8. Final sizing decisions without portfolio, liquidity, mandate, and rating evidence (CP-3C, CP-6E)
9. New analytical evidence introduced at the QA layer (CP-5, CP-5B)
10. Claims where the email only contains a hyperlink but no substantive content

---

## 8. Required Metadata for Email-Derived Evidence

Every email-derived data point should preserve:

```json
{
  "email_subject": "string",
  "sender": "string",
  "received_or_sent_date": "date",
  "email_category": "string",
  "source_tier": "number",
  "issuer_refs": ["string"],
  "sector_refs": ["string"],
  "data_point": "string",
  "allowed_use": "Evidence|Context|Trigger|Routing Signal",
  "staleness_rule": "string",
  "confidence": "High|Medium|Low"
}
```

---

## 9. Implementation Notes

1. Email ingestion should occur before source scoring, but after runtime config validation.
2. CP-X should use email categories as routing signals.
3. CP-MON should preserve the original email reference for auditability.
4. Analytical modules should cite email-derived evidence only when permitted by this matrix.
5. If an email contains an attachment, the attachment must be separately ingested and classified under the standard source hierarchy.
6. If an email forwards a rating action or research alert, classify based on the underlying content, not just the forwarder.
7. If multiple emails describe the same event, deduplicate before analytical use.

---

## 10. Summary Priority

| Priority | Modules | Rationale |
|---|---|---|
| Phase 1 | CP-MON, CP-1, CP-3, CP-3C, CP-3D, CP-SR | Highest real-time credit intelligence benefit (monitoring, RV, sizing, refinancing, sector) |
| Phase 2 | CP-6A, CP-6E, CP-X, CP-2, CP-2E | Strong analytical enrichment but requires guardrails |
| Phase 3 | CP-4, CP-4C, CP-5, CP-5B, Reporting | Use mainly as triggers, context, audit, or evidence appendix |

---

## 11. Version History

| Version | Date | Notes |
|---|---|---|
| 1.0 | 2026-06-08 | Initial module-wide email source routing matrix |
| 2.0 | 2026-06-08 | Audit F-2: re-pointed all §4 sections and §5/§7/§10 to the v2 Canonical taxonomy (CP-3=RelativeValue, CP-3C=Sizing, CP-2E=Liquidity, CP-5=QA, CP-5B=EvidenceTrace). Added liquidity routing signal. See README/TAXONOMY_RECONCILIATION.md |
