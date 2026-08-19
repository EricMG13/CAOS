<!-- CP-5 System Reference (T4) | 2026-06-03 -->

## Identity
module_id: CP-5 | module_name: ResearchIntegrityQA | schema_family: Nested | layer: L5

## Dependencies
UP: CP-5B (evidence trace), all analytical modules (CP-1 through CP-4C, CP-6A, CP-6E) | DOWN (Analytical): None (gates upstream modules) | DOWN (Infra): CP-5B, CP-RENDER, CP-EXTRACT

## Governance Rules
1. CP-5 gates ALL upstream module outputs — no module output reaches committee, CP-DB, or downstream consumers without CP-5 clearance.
2. Severity Engine is deterministic: Critical → Blocked, Material → Restricted, Minor → Passed. No override of Blocked within CP-5.
3. Every QA finding must state: what is wrong, why it matters, what fix is required, and whether output can be used before correction.
4. Do not rewrite analysis — audit only. Provide remediation instructions, not corrected analysis.
5. All severity values must be exactly CRITICAL, MATERIAL, or MINOR — no other scale permitted.

## Evidence Support Classification (5)
Supported | Partially Supported | Unsupported | Conflicting | Insufficient Information

## Exception Severity Values (3)
CRITICAL | MATERIAL | MINOR

## qa_status Values (3)
Blocked | Restricted | Passed

## Committee Clearance Values (3)
Pass | Pass with Remediation | Fail

## Committee Use Values (3)
Approved | Restricted | Blocked

## Defect Categories (23)
Unsupported Claim | Partially Supported Claim | Conflicting Evidence | Citation Gap | Source Quality Limitation | Calculation Error | Formula / Definition Drift | Period Mismatch | Entity / Perimeter Mismatch | Legal Support Gap | Covenant / Basket Overreach | Recovery / Ranking Overreach | Market Data Gap | Relative Value Unsupported | Cross-Module Inconsistency | Version Conflict | Duplicative / Immaterial Content | Promotional or Non-Credit Language | Structured Export Defect | Evidence Trace Defect | Master Index Defect | Gate Compliance Breach | Safety / Scope Breach

## Clearance Impact Labels (9)
Blocks Committee Use | Restricts Committee Use | Blocks CP-DB / Database Ingestion | Requires Legal Review | Requires Market Data Refresh | Requires Calculation Rebuild | Requires Source Reconciliation | Monitoring Follow-Up | Formatting / Hygiene Only

## 8 Audit Lanes
1. Unsupported Claim | 2. Calculation | 3. Legal / Covenant | 4. Market / RV | 5. Cross-Module Consistency | 6. Evidence Trace | 7. Schema | 8. Export

> **As shipped (CAOS engine).** Deterministic, always-on coverage = the severity gate (`engine/gate.py`) + claim→source lineage (`engine/lineage.py`, CP-5B) + per-module finding gates, emitting findings in lanes **1 (orphan claims), 2 (Calculation), 3 (Legal/Covenant), 6 (Evidence Trace), 7 (Schema)**. The **opt-in LLM council** (`engine/council.py`, API key required, off by default) adds lanes **2, 3, 4, 5**. **No deterministic lane-5 sweep exists** (only the leverage plausibility spot-check) and **lane 8 (Export) is assessed by nothing under any configuration** — treat unexercised lanes as *not assessed*, not *passed* (audit 2026-07-10 QA-5).

## Severity Escalation Triggers
- **→ Critical:** Changes credit conclusion, investment recommendation, legal meaning, recovery ranking, economics, leverage, liquidity, FCF, maturity, refinancing, or contains fabricated/materially misleading claim.
- **→ Material:** Affects evidence traceability, cross-module consistency, export integrity, monitoring triggers, or source-quality disclosure.
- **→ Minor:** Formatting, duplication, clarity, table hygiene, or non-core presentation.

## Override Protocol
- No override of Blocked status within CP-5.
- Blocked module → unblocked only after remediation and re-audit.
- Restricted status may be maintained if authorized reviewer accepts Material issues with explicit limitation disclosure.

## Fail/Restrict
- **Blocked (CP-5):** No completed module outputs available for audit → CP-5 Module Status = Blocked, STOP.
- **Blocked (Audited Module):** ≥1 Critical issue found → audited module qa_status = Blocked, committee use prohibited.
- **Restricted (Audited Module):** ≥1 Material issue (no Critical) → audited module qa_status = Restricted, committee use with explicit limitations only.
- **Fail (Clearance):** ≥1 unresolved Critical, missing auditable output, or inability to identify issuer/entity.

## Version: 2026-06-03
