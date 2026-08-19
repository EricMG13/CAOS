<!-- REF_CP-5_01 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="01" name="QA Source Gate and Input Module Register">
<input>All completed module outputs (.docx files with appendices), CP-5B evidence trace outputs, all source materials referenced by audited modules.</input>
<gate>Always executes. This IS the gate check. BLOCKING: At least one completed module output must be available for audit. If no auditable outputs: Module Status = Blocked, STOP.</gate>

## Instructions
1. Inventory all completed module outputs available for QA.
2. For each module: record Module, Document/Output, Scope, Source Quality, Appendix Status, QA Status (pre-audit), and Notes.
3. Confirm CP-5B evidence trace is available.
4. Assess source quality and appendix completeness for each module.
5. Assign Module Status:
   - **Completed:** All target modules available with appendices.
   - **Ready with Limitations:** Some modules available but missing appendices, incomplete source packages, or CP-5B trace unavailable.
   - **Blocked:** No completed module outputs available for audit. Output blocked message and STOP.
6. State missing required inputs, external-source usage status, and citation discipline requirement.

## Output
T5.1: `Module`|`Document / Output`|`Scope`|`Source Quality`|`Appendix Status`|`QA Status`|`Notes`
+ Module Status: Completed / Ready with Limitations / Blocked
<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (per declared Upstream); restate the exact datapoints/run_id/period used. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
</step_reference>
