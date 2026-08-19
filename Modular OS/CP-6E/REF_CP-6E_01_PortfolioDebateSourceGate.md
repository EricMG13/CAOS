<!-- REF_CP-6E_01 (T2) | 2026-06-03 -->
<step_reference module="CP-6E" step="01" name="Portfolio Debate Source Gate">
<input>CP-0 registry, all upstream module outputs (.docx with appendices), CP-6A debate output, source files, market data, portfolio/mandate inputs, exposure reports.</input>
<gate>Always executes. This IS the gate check. BLOCKING: If CP-3 is unavailable → Module Status = Blocked, STOP (RV Trader cannot make evidence-led pitch).</gate>

## Instructions
1. Confirm availability of all upstream module outputs, source materials, market data, portfolio/mandate inputs, and structured-export feasibility.
2. Determine gate status:
   - **Full Run:** CP-3, CP-3C, CP-2B, and market data/mandate inputs available.
   - **Ready with Limitations:** CP-3 available but CP-3C, CP-2B, mandate data, exposure data, or other modules missing. Carry each limitation forward.
   - **Blocked:** CP-3 unavailable → STOP.
3. Apply limitation rules:
   - CP-3C missing → mandate fit and sizing cannot be fully tested.
   - CP-2B missing → downside path cannot be fully tested.
   - Current market pricing missing → RV conclusions = [Insufficient Information].
   - Mandate/portfolio constraints missing → exact constraint = [Insufficient Information].
   - Ratings/downgrade trajectory missing → CCC-basket/downgrade arguments = [Insufficient Information].
4. Record files and modules available, missing inputs, and limitations carried forward.

## Output
Gate status: Full Run / Ready with Limitations / Blocked
Source register: modules available, modules missing, limitations carried forward.
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
