# System Route Map

## Overview

The Credit Operating System processes source documents through a layered pipeline. Each layer builds on the outputs of previous layers. Data flows strictly forward — no analytical module feeds back into an earlier analytical layer.

## Layer-by-Layer Flow

### 1. Source Readiness and Routing

```text
Source Documents -> CP-0 (SourceReadiness)
                       |
                       v
                    CP-X (PlannerRouter)
                       |
                       v
             Routes work to eligible modules
```

- **CP-0** assesses whether the uploaded source package is sufficient to begin analysis.
- **CP-X** routes the request to the appropriate analytical modules.
- CP-0 does **not** route directly to analytical modules; CP-X owns execution routing.

### 2. L1 Data Foundation

```text
CP-X -> CP-1  (Canonical financials)
CP-X -> CP-1A (Business / transaction facts)

CP-1 -> CP-1B (Earnings delta)
CP-1 -> CP-1C (Peer benchmark)
```

L1 produces the canonical data foundation required by later layers:

- **CP-1** normalises financials and KPIs.
- **CP-1A** extracts business, ownership, and transaction facts.
- **CP-1B** compares current vs prior period performance.
- **CP-1C** benchmarks the issuer against peers.

### 3. L2 Fundamental Credit Synthesis

```text
CP-1  ----\
CP-1A -----\
CP-1B ------> CP-2 (FundamentalCreditSynthesizer)
CP-1C -----/

CP-2 -> CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-2G, CP-3, CP-6A
```

**CP-2** is the L2 hub. It receives four upstream feeds: CP-1, CP-1A, CP-1B, and CP-1C.

Specialist L2 modules then branch from CP-2:

| Module | Purpose | Additional Inputs |
|--------|---------|------------------|
| CP-2B | Downside pathway analysis | CP-1, CP-1B, CP-2 |
| CP-2C | Event catalyst register | CP-2 |
| CP-2D | Governance / sponsor score | CP-1A, CP-2 |
| CP-2E | Liquidity and cash-flow bridge | CP-1, CP-2 |
| CP-2F | Macro / FX / hedging sensitivity | CP-2 |
| CP-2G | ESG / transition credit transmission and linked-debt mechanics | CP-1, CP-1A, CP-2 (soft; missing inputs limit rather than block) |

### 4. L3 Valuation, Portfolio, and Refinancing

```text
CP-1  ----\
CP-1C -----\
CP-2  ------> CP-3 (RelativeValueSecuritySelection)
CP-2E -----/

CP-3 -> CP-3B, CP-3C, CP-6A, CP-6E

CP-1  ----\
CP-2B ------> CP-3D (RefinancingLMERisk)
CP-2E -----/

CP-3D -> CP-4, CP-6A
```

L3 converts credit fundamentals into market, recovery, portfolio, and refinancing conclusions.

### 5. L4 Legal and Covenant Analysis

```text
CP-1  ----\
CP-3D -----> CP-4 (LegalCovenantInterpreter)

CP-4 ----\
CP-1 ----- > CP-4C (CovenantCapacityCalculator)

CP-1  ----\
CP-1A -----\
CP-4  ------> CP-4D (RestrictedGroupGuaranteeMap)

CP-4D -> CP-4C, CP-6A (optional handoffs)

CP-4  -> CP-4C, CP-6A
CP-4C -> CP-6A, CP-6E
```

- **CP-4** interprets legal/covenant documentation and scores covenant aggressiveness.
- **CP-4D** maps the restricted-group perimeter, guarantees, collateral, structural priority, leakage, and priming exposure. CP-3B consumes its nullable handoff on a later run.
- **CP-4C** calculates covenant capacity and headroom using the required calculation standard: formula, numerator, denominator, period, source trace, and normalisation.

### 6. L5 Quality Assurance Loop

```text
All analytical modules
        |
        v
CP-5B (EvidenceTraceValidator)
        |
        v
CP-5 (ResearchIntegrityQA)
        |
        v
Blocked / Restricted / Passed
        |
        v
Routing and committee-use decisions
```

CP-5B validates claim-to-source lineage. CP-5 audits outputs across eight lanes:

1. Unsupported Claim
2. Calculation
3. Legal / Covenant
4. Market / RV
5. Cross-Module Consistency
6. Evidence Trace
7. Schema
8. Export

### 7. L6 Debate and Decision

#### CP-6A: IC Debate

CP-6A receives from 11 upstream modules:

```text
CP-2, CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-2G (optional),
CP-3, CP-3B, CP-3D, CP-4, CP-4D (optional), CP-4C
        |
        v
CP-6A (ICDebateChallenge)
```

CP-6A uses three personas:

- **Bull Analyst** — argues durability from source-supported evidence.
- **Bear Analyst** — attacks the Bull case using the Zero-Bound Chain.
- **IC Chair** — adjudicates evidence and determines IC Action Bias.

#### CP-6E: Portfolio Debate — Terminal Module

```text
CP-3  ----\
CP-3C -----\
CP-4C ------> CP-6E (PortfolioDebateChallenge) -> TERMINAL
CP-6A -----/
```

CP-6E is the terminal analytical module. It determines final Portfolio Posture through three personas:

- **RV Trader** — argues inclusion from relative value evidence.
- **Compliance Officer** — challenges via portfolio constraints.
- **CIO** — scores allocation dimensions and determines the final posture.

## Key Convergence Points

| Module | Upstream Count | Upstream Modules | Why It Matters |
|--------|----------------|------------------|----------------|
| CP-2 | 4 | CP-1, CP-1A, CP-1B, CP-1C | First full synthesis of financials, business facts, earnings, and peers |
| CP-3 | 4 | CP-1, CP-1C, CP-2, CP-2E | Converts fundamentals into valuation and security selection |
| CP-6A | 11 core + 2 optional | Core feeds plus nullable CP-2G and CP-4D handoffs | Maximum analytical convergence for IC decision-making without optional-module input gating |
| CP-6E | 4 | CP-3, CP-3C, CP-4C, CP-6A | Terminal portfolio-level decision point |

## Complete Edge Reference

| Source Module | Downstream Destinations |
|---------------|-------------------------|
| CP-0 | CP-X |
| CP-1 | CP-1B, CP-1C, CP-2, CP-2B, CP-2E, CP-2G, CP-3, CP-3D, CP-4, CP-4D, CP-4C |
| CP-1A | CP-2, CP-2D, CP-2G, CP-4D |
| CP-1B | CP-2, CP-2B |
| CP-1C | CP-2, CP-3 |
| CP-2 | CP-2B, CP-2C, CP-2D, CP-2E, CP-2F, CP-2G, CP-3, CP-6A |
| CP-2B | CP-3D, CP-6A |
| CP-2C | CP-6A |
| CP-2D | CP-6A |
| CP-2E | CP-3, CP-3D, CP-6A |
| CP-2F | CP-6A |
| CP-2G | CP-6A |
| CP-3 | CP-3B, CP-3C, CP-6A, CP-6E |
| CP-3B | CP-6A |
| CP-3C | CP-6E |
| CP-3D | CP-4, CP-6A |
| CP-4 | CP-4D, CP-4C, CP-6A |
| CP-4D | CP-4C, CP-6A; CP-3B next run |
| CP-4C | CP-6A, CP-6E |
| CP-6A | CP-6E |
| All analytical modules | CP-5B |
| CP-5B | CP-5 |

## Infrastructure Services

| Service | Role |
|---------|------|
| CP-DB | Stores validated structured data extracted from module outputs |
| CP-RENDER | Renders committee-ready reports from validated outputs |
| CP-EXTRACT | Sole authorised parser of .docx JSON appendices |

## Decision Gates and Hard Stops

| Module | Gate | Condition | Result if Failed |
|--------|------|-----------|------------------|
| CP-2B | Conditional hard stop | CP-1 and CP-2 both unavailable | Module does not execute |
| CP-3B | Input Gate 1 | CP-3 RV analysis unavailable | qa_status = Blocked |
| CP-3B | Input Gate 2 | Capital structure lacks seniority/subordination | qa_status = Blocked |
| CP-5 | Severity gate | Any CRITICAL finding | qa_status = Blocked |
| CP-5 | Severity gate | Any MATERIAL finding, no CRITICAL | qa_status = Restricted |
| CP-5 | Severity gate | Only MINOR or no findings | qa_status = Passed |


### 8. L7 — Sector Review & Continuous Monitoring

```text
Email Intelligence ──┐
Market Data ─────────┤
CP-1 (Issuer Data) ──┼──> CP-SR (SectorReview)
CP-MON (Alerts) ─────┘         |
                               v
                    7-Section Sector Review
                    Sector Credit Posture
                    Early Warning Dashboard
                    Comparative Peer Table
                               |
                    ┌──────────┼──────────┐
                    v          v          v
                 CP-5       CP-6A      CP-6E
              (RelValue)  (Debate)  (Portfolio)
```

```text
All Analytical Modules ──┐
Email Intelligence ───────┤
Market Data ──────────────┼──> CP-MON (CreditPulse)
CP-SR (Early Warnings) ──┘         |
                                   v
                         Alert Triggers
                         Rating Action Log
                         Watchlist State
                                   |
                         ┌─────────┼─────────┐
                         v         v         v
                      CP-X      CP-SR      CP-1
                    (Router)  (Refresh)  (Refresh)
```

- **CP-SR** produces sector-level reviews consuming issuer data, email intelligence, and CP-MON alerts.
- **CP-MON** monitors continuously and triggers module refreshes via CP-X when thresholds are breached.
- CP-SR and CP-MON form a bidirectional loop: CP-SR feeds early warning thresholds to CP-MON; CP-MON feeds alert triggers back to CP-SR.
- This is the only sanctioned bidirectional data flow in the system. All other flows are strictly unidirectional.

### 9. Email Intelligence Layer

```text
Mailbox / Email Feed
        |
        v
REF_CP-SR_G (Email Classification)
        |
        v
REF_CP-EMAIL (Source Routing Matrix)
        |
        ├──> CP-MON (Trigger / Evidence)
        ├──> CP-SR  (Evidence / Context)
        ├──> CP-1   (Evidence / Context)
        ├──> CP-3   (Context / Trigger)
        ├──> CP-3D  (Trigger / Context)
        ├──> CP-5   (Context / Evidence)
        ├──> CP-6A  (Context / Evidence)
        ├──> CP-6E  (Context)
        └──> CP-X   (Routing Signal)
```

- Emails are classified into 8 categories per REF_CP-SR_G.
- Each category has a default tier (1.5, 2.0, 2.5, or 3.0) and staleness rule.
- REF_CP-EMAIL defines per-module permissions: Evidence, Context, Trigger, or Routing Signal.
- Email integration is optional per module but strongly recommended for CP-MON and CP-SR.

### Updated Complete Edge Reference (additions to existing table)

| Source Module | Downstream Destinations |
|---|---|
| CP-SR | CP-5, CP-6A, CP-6E, CP-MON |
| CP-MON | CP-X, CP-SR, CP-1, CP-3D |
| Email Intelligence | CP-MON, CP-SR, CP-1, CP-3, CP-3D, CP-5, CP-6A, CP-6E, CP-X |

### Updated Infrastructure Services (additions to existing table)

| Service | Role |
|---|---|
| REF_CP-EMAIL | Governs email-derived intelligence routing across all CP modules |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-18 | Initial system route map (L0–L6 + infrastructure) |
| 2.0 | 2026-06-08 | Added L7 Sector & Monitoring (CP-SR, CP-MON), Email Intelligence Layer, REF_CP-EMAIL, updated edge reference |
