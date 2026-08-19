<!-- REF_CP-6A_01 (T2) | 2026-06-03 -->
<step_reference module="CP-6A" step="01" name="IC Debate Source Gate">
<input>CP-0 registry, all upstream module outputs (.docx with appendices), source files, market data, portfolio/mandate inputs.</input>
<gate>Always executes. This IS the gate check. BLOCKING: If CP-1 AND CP-2 are both unavailable → Module Status = Blocked, STOP (Bull opening cannot be evidence-led).</gate>

## Instructions
1. Confirm availability of all upstream module outputs, source materials, market data, portfolio/mandate inputs, and structured-export feasibility.
2. Determine gate status:
   - **Full Run:** CP-1, CP-2, CP-2B, CP-4, and market data available.
   - **Ready with Limitations:** CP-1 and CP-2 available but CP-2B, CP-4, CP-3, CP-2E, CP-3D, CP-3B, or CP-4C missing. Carry each limitation forward.
   - **Blocked:** CP-1 AND CP-2 unavailable → STOP.
3. Apply limitation rules:
   - CP-2B missing → Bear cannot fully map Zero-Bound downside.
   - CP-4 missing → lender control, leakage, recovery mechanics cannot be fully tested.
   - CP-3/market data missing → RV conclusions = [Insufficient Information].
   - CP-2E missing → quantified liquidity runway = [Insufficient Information] unless directly supported by CP-1/CP-1B.
   - CP-4C missing → basket/covenant-capacity headroom must not be inferred.
   - CP-3D missing → refinancing/LME path must not be claimed.
   - CP-3B missing → instrument preference/recovery conclusion must not be claimed.
4. Record files and modules available, missing inputs, and limitations carried forward.

## Output
Gate status: Full Run / Ready with Limitations / Blocked
Source register: modules available, modules missing, limitations carried forward.
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
