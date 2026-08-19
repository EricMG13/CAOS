# Suggested Prompts

Each module has a basic prompt for first-time users and an advanced prompt for deeper analysis.

## CP-0 SourceReadiness

**Basic:**

> I have uploaded the available source documents for issuer. Please assess source readiness and tell me which modules can run.

**Advanced:**

> Assess source readiness for the uploaded \[issuer name] source documents. Classify each source by quality, identify gaps, and recommend the route plan for a full credit workflow. with full appendix.

## CP-1 CanonicalDataFoundation

**Basic:**

> Please normalise the uploaded financial statements into the CP-1 canonical financial format.

**Advanced:**

> Build the CP-1 canonical data foundation for the issuer using LTM, FY2025, FY2024 and FY2023 financials. Populate the KPI dashboard, calculation register, and downstream readiness table. Flag unsupported or not calculable metrics. with full appendix.

## CP-1A BusinessTransactionFactPack

**Basic:**

> Extract the business description, transaction summary, and ownership information from the uploaded offering memorandum.

**Advanced:**

> Build the full CP-1A fact pack. Include transaction structure, sponsor ownership history, operating model, source classification, and credit translation summary. Flag any missing or conflicting facts. with full appendix.

## CP-1B EarningsDelta

**Basic:**

> Compare the latest period financial results against the prior period.

**Advanced:**

> Produce the 27-column earnings delta table using CP-1 financials. Identify the largest movements in revenue, EBITDA, cash conversion, leverage, and liquidity. Explain each movement using Evidence → Risk Mechanic → Credit Implication. with full appendix.

## CP-1C PeerBenchmark

**Basic:**

> Benchmark this issuer against its peers.

**Advanced:**

> Apply the 6-level peer selection hierarchy and run all 15 comparative formulas. Identify outliers, valuation gaps, and peer-relative strengths or weaknesses. with full appendix.

## CP-2 FundamentalCreditSynthesizer

**Basic:**

> Produce the fundamental credit synthesis using available L1 outputs.

**Advanced:**

> Generate the 21-section CP-2 synthesis. Build the credit mechanism map, score the 9 financial profile dimensions, and produce a committee memo with canonical credit implications. with full appendix.

## CP-2B DownsidePathway

**Basic:**

> Identify the main downside pathways for this issuer.

**Advanced:**

> Build the CP-2B downside pathway register. Use the 8 fragility driver groups and map each causal chain from operating driver to credit consequence. Identify the first break point and any conditional hard stops. with full appendix.

## CP-2C EventCatalystRegister

**Basic:**

> Identify the key event catalysts for this issuer.

**Advanced:**

> Build the event catalyst register with timing, trigger condition, evidence, risk mechanic, and credit implication for each catalyst. with full appendix.

## CP-2D GovernanceSponsorScore

**Basic:**

> Assess sponsor and governance quality for this issuer.

**Advanced:**

> Evaluate sponsor track record, management alignment, governance structure, board oversight, and any related-party risks. Translate each finding into a credit implication. with full appendix.

## CP-2E LiquidityCashFlowBridge

**Basic:**

> Build the liquidity and cash flow bridge.

**Advanced:**

> Construct the CP-2E cash flow bridge from EBITDA to FCF. Assess liquidity sources and uses, revolver availability, working capital pressure, and refinancing dependence. with full appendix.

## CP-2F MacroFXHedgingSensitivity

**Basic:**

> Assess macro and FX sensitivity.

**Advanced:**

> Analyse exposure to rates, FX, commodity inputs, and macro demand cycles. Evaluate hedging arrangements and identify unhedged risk channels.with full appendix.

## CP-3 RelativeValueSecuritySelection

**Basic:**

> Run relative value analysis for this issuer's debt instruments.

**Advanced:**

> Compare the issuer's spreads, yields, and security selection options against peers. Identify whether the instrument is cheap, fair, or rich relative to fundamentals and liquidity. with full appendix.

## CP-3B RecoveryInstrumentPreference

**Basic:**

> Build a recovery waterfall and estimate LGD.

**Advanced:**

> Apply the recovery waterfall methodology using capital structure seniority. Estimate LGD by instrument and rank instrument preference based on recovery, spread, and covenant protection. with full appendix.

## CP-3C PortfolioFitPositionSizing

**Basic:**

> Assess portfolio fit and recommend a sizing posture.

**Advanced:**

> Run the 5-input sizing evidence gate. Assess mandate fit, concentration, rating, downside, liquidity, and portfolio constraints. Produce a sizing posture and identify binding constraints, with full appendix.

## CP-3D RefinancingLMERisk

**Basic:**

> Assess refinancing and LME risk.

**Advanced:**

> Build the maturity wall, evaluate refinancing capacity, and classify the most likely path among the 7 refinancing/LME types. Assess vulnerability to uptier, drop-down, or priming debt, with full appendix.

## CP-4 LegalCovenantInterpreter

**Basic:**

> Interpret the key covenants in the uploaded credit agreement.

**Advanced:**

> Produce the 12-table legal covenant interpretation. Score covenant aggressiveness, identify permissive baskets, and map each covenant conclusion to the 8-value Legal/Covenant credit implication subset, with full appendix.

## CP-4C CovenantCapacityCalculator

**Basic:**

> Calculate covenant capacity and headroom.

**Advanced:**

> Calculate all relevant covenant capacities using the required 6-element calculation standard. Project headroom under base case and downside stress scenarios. with full appendix.

## CP-5B EvidenceTraceValidator

**Basic:**

> Validate the evidence traces for all module outputs.

**Advanced:**

> Run CP-5B lineage validation across all evidence traces. Classify each claim using the 8-value lineage taxonomy and flag orphan claims requiring VE-015. with full appendix.

## CP-5 ResearchIntegrityQA

**Basic:**

> Run the research integrity QA audit.

**Advanced:**

> Audit all module outputs across the 8 CP-5 lanes. Classify each finding as CRITICAL, MATERIAL, or MINOR and assign qa\_status as Blocked, Restricted, or Passed. with full appendix.

## CP-6A ICDebateChallenge

**Basic:**

> Run the IC debate and determine the action bias.

**Advanced:**

> Conduct the full CP-6A adversarial debate. Have the Bull Analyst argue durability, the Bear Analyst attack through the Zero-Bound Chain, and the IC Chair determine IC Action Bias, final memo, and single greatest uncertainty. with full appendix.

## CP-6E PortfolioDebateChallenge

**Basic:**

> Run the portfolio debate and determine portfolio posture.

**Advanced:**

> Conduct the full CP-6E portfolio debate. Have the RV Trader argue inclusion, the Compliance Officer challenge via the 9 constraint taxonomy, and the CIO score the 9 allocation dimensions to determine final Portfolio Posture and binding constraint. with full appendix.



## CP-SR SectorReview

**Basic:**
Run a sector review for [sector name, e.g. European HY Telecoms]. Assess the key credit drivers, produce a comparative peer table, and assign a sector credit posture.

**Advanced:**
Execute the full CP-SR sector review for [sector name] covering [geography] for [timeframe, e.g. LTM to Q1 2026 + 12-month forward]. Include all 6 investigation dimensions scored 1–5. Populate the 15-column comparative table per REF_CP-SR_D. Run the 10-indicator early warning dashboard per REF_CP-SR_E. Map all findings to the canonical credit implication taxonomy per REF_CP-SR_F. Enable email intelligence intake per REF_CP-SR_G. If prior_review_id is available, include delta analysis. Assign sector credit posture with confidence level. with full appendix.

## CP-MON CreditPulse

**Basic:**
Set up monitoring for [issuer or sector]. Flag any rating actions, spread moves, or material events from recent emails and market data.

**Advanced:**
Configure CP-MON CreditPulse for [issuer/sector watchlist]. Ingest email intelligence per REF_CP-SR_G classification (rating actions, sell-side research, trading desk commentary, market data alerts). Evaluate all 10 early warning indicators per REF_CP-SR_E thresholds. Classify each as Green/Amber/Red with trend direction. Generate routing signals for CP-X where thresholds are breached. Produce alert log, watchlist state update, and recommended module refresh triggers. with full appendix.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-18 | Initial suggested prompts (22 modules) |
| 2.0 | 2026-06-08 | Added CP-SR (SectorReview) and CP-MON (CreditPulse) prompts |
