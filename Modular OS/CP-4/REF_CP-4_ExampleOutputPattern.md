<!-- REF_CP-4_ExampleOutputPattern.md (T2 Example Library) | 2026-06-10 | Ported from Agent Files: CP-4__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt -->


================================================================================
FILE: CP-4__SUPPORT__EXAMPLE_OUTPUT_PATTERN.txt
MODULE: CP-4 — LegalCovenantInterpreter
STATUS: UPDATED (vNext)
MECHANICAL CHANGES APPLIED: MC-1, MC-2, MC-3, MC-4, MC-5
GOVERNING CONTRACT: CP_GLOBAL_AGENT_INSTRUCTIONS_v3.2.txt
PURPOSE: Example finding format for CP-4 covenant / legal analysis.
================================================================================

EXAMPLE_OUTPUT_PATTERN

Purpose: Provide a standard finding format for CP-4 provision-level analysis.
Each material covenant finding should follow this structure.

1. Standard Finding Format

Provision: [Exact clause / section reference from governing document]
Source: [Document name | version / date | authority rank]
Summary: [What the provision permits / restricts / conditions]
Risk Mechanic: [How this affects creditor position under stress or borrower
  action]
PD Effect: [Impact on default probability, covenant pressure, operating
  flexibility, or refinancing risk]
LGD / Recovery Effect: [Impact on collateral value, claim priority, guarantor
  coverage, structural subordination, or value leakage]
Monitoring Implication: [Observable data, reporting item, legal event,
  utilization, or borrower action to track]
Credit Implication: [8-value subset label]
Confidence: [High / Medium / Low / Provisional / Not Scorable]
Evidence ID: [Trace ID]

2. Example (Illustrative Only — Do Not Use as Issuer Data)

Provision: Section 7.03(b)(iv) — Incremental Facility
Source: Credit Agreement dated [Date] | Executed | Authority Rank 1
Summary: Permits up to the greater of $200m and 100% of LTM Consolidated
  EBITDA in incremental first-lien pari debt, subject to pro forma first-lien
  net leverage ratio not exceeding 4.25x. No MFN protection after 12-month
  sunset.
Risk Mechanic: Grower basket tied to EBITDA means capacity expands with
  add-back-inflated EBITDA. MFN sunset permits repricing of incremental debt
  without economics protection for existing lenders after 12 months.
PD Effect: Moderate — capacity permits releveraging under stress if EBITDA
  add-backs inflate denominator.
LGD / Recovery Effect: High — pari secured incremental debt directly dilutes
  recovery for existing first-lien creditors.
Monitoring Implication: Track incremental facility utilization, EBITDA add-back
  trajectory, and MFN sunset date.
Credit Implication: Negative — Leverage Increase
Confidence: High
Evidence ID: [CP4-EV-001]

CREDIT IMPLICATION (8-value Legal/Covenant subset):
Positive — Covenant Headroom Expansion | Positive — Deleveraging |
Neutral — Stable | Negative — Covenant Erosion |
Negative — Leverage Increase | Negative — Refinancing Risk |
Negative — Liquidity Deterioration | Insufficient Information
