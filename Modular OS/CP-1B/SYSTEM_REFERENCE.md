<!-- CP-1B System Reference (T4) | 2026-06-02 -->
## Identity
module_id: CP-1B | module_name: EarningsDelta | schema_family: Nested | layer: L1

## Dependencies
UP: CP-1 | DOWN (Analytical): CP-2, CP-2B | DOWN (Infra): CP-5B, CP-5, CP-RENDER, CP-EXTRACT

## Metric Governance
ALL inherited from CP-1. EBITDA priority: Credit-agreement > CP-1 canonical > Adjusted > Reported. Def switching prohibited w/o Conflict Log. FCF: CP-1 canonical. 8 calc status values.

## Evidence Hierarchy
Audited FS > Unaudited w/auditor > Unaudited > Lender/Sponsor > Rating > Internal > External

## Fail/Restrict
Unsupported claim | Missing trace | Undocumented calc | Def switch w/o log | Null→zero | QA-blocked upstream | Currency switch

## Version: 2026-06-02
