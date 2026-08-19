<!-- REF_CP-X_04 (T2) | 2026-06-03 -->
<step_reference module="CP-X" step="04" name="One-Owner-Per-Object Validation">
<input>TX.2 execution sequence; CP_ROUTING_INDEX_v2.2 ownership registry.</input>
<gate>Step 3 complete.</gate>

## Instructions
1. For each module in the execution plan, look up its `owned_object` from CP_ROUTING_INDEX_v2.2.
2. Validate that no two modules produce the same `owned_object`.
3. Record each owned_object, its owning module, conflict status (Yes/No), and resolution.
4. If conflict detected:
   - Flag VE-009 (OWNERSHIP_VIOLATION).
   - Exclude the conflicting module from the execution sequence.
   - Record the resolution action.
5. Include only modules in the active execution plan (not Blocked modules).

## Output
TX.4: `owned_object`|`Owning Module`|`Conflict Detected`|`Resolution`
</step_reference>
