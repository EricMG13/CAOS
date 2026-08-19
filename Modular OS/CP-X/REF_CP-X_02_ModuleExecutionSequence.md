<!-- REF_CP-X_02 (T2) | 2026-06-03 -->
<step_reference module="CP-X" step="02" name="Module Execution Sequence">
<input>CP-0 readiness verdicts; CP_ROUTING_INDEX_v2.2; gate status from Step 1.</input>
<gate>Step 1 complete; CP-X Status ≠ Blocked.</gate>

## Instructions
1. Build a dependency-ordered execution sequence for all modules that CP-0 supports with Ready or Ready with Limitations verdicts.
2. Apply Layer Ordering Rules (Active Prompt):
   - L0 → Orch → L1 → L2 → L3 → L4 → L5/L6 → Infrastructure.
   - CP-5B before CP-5. CP-6A before CP-6E.
   - Infrastructure (CP-RENDER, CP-EXTRACT, CP-DB) after all analytical modules.
3. Within a layer, modules with no inter-dependency may execute in parallel.
4. Blocked modules: list separately with "—" for Order, include blocking reason in Depends On column.
5. Do not skip Ready/Ready with Limitations modules. Do not add modules without CP-0 readiness evidence.

## Output
TX.2: `Order`|`Module ID`|`Module Name`|`Layer`|`Readiness`|`Depends On`
Blocked modules listed at bottom with Order = "—".
</step_reference>
