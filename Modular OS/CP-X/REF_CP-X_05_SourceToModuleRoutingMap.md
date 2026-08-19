<!-- REF_CP-X_05 (T2) | 2026-06-03 -->
<step_reference module="CP-X" step="05" name="Source-to-Module Routing Map">
<input>CP-0 Source Register; TX.2 execution sequence; TX.3 readiness register.</input>
<gate>Step 4 complete.</gate>

## Instructions
1. Map each source document from CP-0's Source Register to the modules it supports.
2. For each source: record Source Document name, Source Quality (from CP-0 quality label), list of Modules Supported (module IDs), and Limitation (from CP-0 flags, or "None").
3. Source Quality labels come from CP-0 — do not reassess quality.
4. If a source supports a Blocked module, still list the mapping but note the module is Blocked.

## Output
TX.5: `Source Document`|`Source Quality`|`Modules Supported`|`Limitation`
</step_reference>
