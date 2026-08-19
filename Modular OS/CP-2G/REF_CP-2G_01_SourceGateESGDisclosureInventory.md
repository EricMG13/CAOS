<!-- REF_CP-2G_01 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-2G" step="01" name="Source Gate and ESG Disclosure Inventory">
<input>Issuer ESG / sustainability reports, annual-report ESG sections, regulatory and transition / emissions disclosures, sustainability-linked debt documents (SLL / SLB term sheets, second-party opinions); CP-1, CP-1A, CP-2 outputs; CP-SR ESG investigation criteria (optional).</input>
<gate>Always executes. A valid outcome is **Not Applicable** — no credit-material ESG exposure and no sustainability-linked debt. BLOCKING only where assessment is requested but zero source exists; then Blocked. Never infer materiality from sector reputation.</gate>

## Instructions
1. Inventory ESG / transition disclosures and any sustainability-linked debt terms.
2. Assess reliability: audited / assured vs self-reported / promotional; flag greenwashing or disclosure-quality risk affecting any ESG claim used downstream.
3. Assign Module Status:
   - **Completed:** issuer ESG/transition disclosures and/or sustainability-linked terms available and credit-relevant.
   - **Completed with Limitations:** partial disclosure.
   - **Not Applicable:** no credit-material exposure and no sustainability-linked debt — state with brief basis.
   - **Blocked:** insufficient source to assess. Do not infer from sector reputation.

## Output
T2G.1: ESG disclosure inventory + reliability assessment + Module Status: Completed / Completed with Limitations / Not Applicable / Blocked
<!-- Upstream re-anchor (common_rules #10): re-import and verify the specific upstream outputs consumed (CP-1, CP-1A, CP-2); restate exact run_id/period. If a required upstream value is absent or mismatched, mark [Insufficient Information] and gate the dependent step — do not infer it. -->
</step_reference>
