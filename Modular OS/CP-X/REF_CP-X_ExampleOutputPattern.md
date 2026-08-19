<!-- REF_CP-X_ExampleOutputPattern.md (T2 Example Library) | 2026-06-10 | Ported from Agent Files: CP-X__SUPPORT__Example_Output.txt -->


================================================================================
FILE: CP-X__SUPPORT__Example_Output.txt
MODULE: CP-X — PlannerRouter
STATUS: UPDATED (vNext)
MECHANICAL CHANGES APPLIED: MC-1, MC-2
GOVERNING CONTRACT: CP_GLOBAL_AGENT_INSTRUCTIONS_v3.2.txt
PURPOSE: Example route_plan output format.
================================================================================

EXAMPLE_OUTPUT_PATTERN

Purpose: Provide standard formatting templates for CP-X route_plan output.
All examples are illustrative only — do not use as production routing data.

1. Example Module Execution Sequence

| Order | Module ID | Module Name | Layer | Readiness | Depends On |
|---:|---|---|---|---|---|
| 1 | CP-0 | SourceReadiness | L0 | Complete (input) | User source package |
| 2 | CP-X | PlannerRouter | Orch | Full Run | CP-0 |
| 3 | CP-1 | CanonicalDataFoundation | L1 | Full Run | CP-0 |
| 4 | CP-1A | BusinessTransactionFactPack | L1 | Full Run | CP-0 |
| 5 | CP-1B | EarningsDelta | L1 | Ready with Limitations | CP-0 |
| 6 | CP-2 | FundamentalCreditSynthesizer | L2 | Full Run | CP-1 |
| 7 | CP-2B | DownsidePathway | L2 | Full Run | CP-1, CP-2 |
| 8 | CP-4 | LegalCovenantInterpreter | L4 | Ready with Limitations | CP-0 |
| 9 | CP-6A | ICDebateChallenge | L6 | Ready with Limitations | CP-1, CP-2, CP-2B, CP-4 |
| — | CP-3 | RelativeValueSecuritySelection | L3 | Blocked | Missing: current market data |
| — | CP-6E | PortfolioDebateChallenge | L6 | Blocked | CP-3 Blocked |

2. Example Module Readiness Register Entry

| Module ID | Module Name | Readiness Status | Source Dependencies Met | Limitation Flags | Blocking Reason |
|---|---|---|---|---|---|
| CP-1B | EarningsDelta | Ready with Limitations | Partial | Interim report is unaudited draft; Q3 only | Source quality: Limited (draft, unaudited) |
| CP-3 | RelativeValueSecuritySelection | Blocked | No | N/A | No current market data provided in source package |

3. Example One-Owner-Per-Object Validation

| owned_object | Owning Module | Conflict Detected | Resolution |
|---|---|---|---|
| canonical_data_foundation | CP-1 | No | N/A |
| fundamental_credit_synthesis | CP-2 | No | N/A |
| ic_debate_challenge | CP-6A | No | N/A |

4. Example Route Plan Summary

"Route plan includes 9 modules for execution (7 Full Run, 2 Ready with
Limitations, 2 Blocked). The execution sequence begins with CP-1 and
terminates with CP-6A. 9 one-owner-per-object validations passed with no
conflicts. 2 limitations propagated from CP-0: CP-1B source quality
(unaudited draft) and CP-4 source quality (unsigned credit agreement).
CP-3 and CP-6E are Blocked due to missing current market data."
