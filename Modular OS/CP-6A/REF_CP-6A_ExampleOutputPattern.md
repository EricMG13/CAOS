<!-- REF_CP-6A_ExampleOutputPattern.md (T2 Example Library) | 2026-06-10 | Ported from Agent Files: CP-6A__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt -->


================================================================================
FILE: CP-6A__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt
MODULE: CP-6A — ICDebateChallenge
STATUS: UPDATED (vNext)
MECHANICAL CHANGES APPLIED: MC-1, MC-2, MC-3, MC-5
GOVERNING CONTRACT: CP_GLOBAL_AGENT_INSTRUCTIONS_v3.2.txt
PURPOSE: Example debate output pattern for CP-6A IC Debate.
================================================================================

EXAMPLE_OUTPUT_PATTERN

Purpose: Provide a standard format for CP-6A debate output elements. Action
bias definitions are defined in CP-6A__SUPPORT__ANALYTICAL_STANDARD.txt.

1. Example Bull Claim Format (Illustrative Only — Do Not Use as Issuer Data)

Bull Claim 1 — Cash-Flow Conversion Durability
Evidence: LTM FCF conversion of 62% (CP-1B, Period: FY2025), supported by
  85% recurring revenue base (CP-1A, Lender Presentation dated [Date]).
Risk Mechanic: High revenue visibility and limited working-capital volatility
  support durable FCF generation through cycle, reducing refinancing dependence
  and supporting debt service capacity.
Credit Implication: Positive — supports current leverage trajectory and reduces
  PD under base case. FCF coverage of mandatory cash uses is 1.8x (CP-2E).
Monitoring Signal: Quarterly FCF conversion below 40% for two consecutive
  quarters.

2. Example Bear Counter Format

| Bull Claim Attacked | Bear Counter-Evidence | Fragility Vector | Legal / Covenant Exploit | Risk Mechanic | Credit Implication | What Would Prove Bear Wrong |
|---|---|---|---|---|---|---|
| Bull Claim 1: FCF conversion durability | LTM capex is 60% maintenance (CP-1B); management has guided 15% capex increase for FY2026 (Lender Presentation) | Maintenance capex inflexibility compresses discretionary FCF under revenue stress | Ratio debt capacity expands with add-back-inflated EBITDA (CP-4C, Section 5.03(b)), permitting incremental leverage even as true FCF declines | Rising mandatory capex absorbs FCF headroom; add-back-inflated EBITDA masks deterioration in covenant tests | Negative — FCF conversion overstated by ~8pp when capex normalization is applied; leverage headroom is narrower than reported metrics suggest | Two consecutive quarters of >65% FCF conversion after capex normalization |

3. Example Chair Scoring Format

| Dimension | Score (1–5) | Bull Evidence | Bear Evidence | Chair Assessment |
|---|---:|---|---|---|
| Cash-flow durability | 2 | 62% LTM FCF conversion, 85% recurring revenue | Maintenance capex rising, normalization reduces conversion to ~54% | Bull has superior base-case evidence; Bear capex risk is credible but bounded by contractual pass-through. Score: Bull modestly ahead. |

4. Example Action Bias Determination

Final Action Bias: Starter Position. The decision is driven by durable base-
case FCF conversion and accessible liquidity runway of 18+ months (CP-2E),
because these support debt service and reduce near-term PD, which implies
manageable downside under base case. The main factor preventing a higher-
conviction recommendation is unresolved legal leakage capacity (CP-4C Section
6.04) and missing current market pricing for relative-value confirmation.

IC ACTION BIAS (8-value subset of canonical decision taxonomy):
Avoid | Watchlist | Starter Position | Core Hold | Add / Increase |
Reduce / Trim | Exit | Requires More Work

NOTE: "Add / Increase" is ONE value (resolves S4).

ZERO-BOUND CHAIN:
Operating Stress → EBITDA/FCF Impact → Liquidity/Leverage Result →
Legal/Refinancing Consequence → Credit Outcome

THREE PERSONAS:
Bull Analyst    — argues durability from source-supported evidence
Bear Analyst    — attacks Bull's claims via Zero-Bound chain
IC Chair        — adjudicates evidence, determines final action bias

CANONICAL CREDIT IMPLICATION (13 values):
Positive — Deleveraging | Positive — Margin Expansion |
Positive — Revenue Growth | Positive — Liquidity Improvement |
Positive — Covenant Headroom Expansion | Neutral — Stable |
Negative — Leverage Increase | Negative — Margin Compression |
Negative — Revenue Decline | Negative — Liquidity Deterioration |
Negative — Covenant Erosion | Negative — Refinancing Risk |
Insufficient Information
