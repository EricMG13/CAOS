<!-- REF_CP-X_06 (T2) | 2026-06-03 -->
<step_reference module="CP-X" step="06" name="Limitation Propagation Register">
<input>CP-0 limitation flags; TX.3 readiness register; TX.5 source routing map.</input>
<gate>Step 5 complete.</gate>

## Instructions
1. For each CP-0 limitation (Conditional or Not Usable source flag), identify ALL downstream modules affected.
2. Record: Limitation description, Source document, Affected Modules (module ID list), Impact description (how the limitation constrains the module's output), and Propagated Flag (the flag label carried forward).
3. Trace propagation through dependency chains — if a limitation affects CP-1 and CP-2 depends on CP-1, CP-2 is also affected.
4. Every CP-0 limitation must appear here. If no limitations exist, state "No limitations to propagate."

## Output
TX.6: `Limitation`|`Source`|`Affected Modules`|`Impact`|`Propagated Flag`
</step_reference>
