<!-- REF_CP-X_01 (T2) | 2026-06-03 -->
<step_reference module="CP-X" step="01" name="Route Plan Source Gate">
<input>CP-0 output (.docx with appendices): readiness assessment, source registry, readiness verdicts per module.</input>
<gate>Always executes. This IS the gate check. BLOCKING: If CP-0 is unavailable or critically incomplete → CP-X Status = Blocked, STOP. No route_plan produced.</gate>

## Instructions
1. Confirm CP-0 output is available and complete (readiness assessment, source registry, per-module readiness verdicts).
2. Determine CP-X gate status:
   - **Full Run:** CP-0 available with complete readiness assessment for all modules.
   - **Ready with Limitations:** CP-0 available but some sources flagged as Conditional or Not Usable.
   - **Blocked:** CP-0 unavailable or critically incomplete → STOP after blocked message.
3. Record CP-0 status, completeness assessment, and any source-level flags.

## Output
Gate status: Full Run / Ready with Limitations / Blocked.
CP-0 completeness assessment and source-level flags (if any).
</step_reference>
