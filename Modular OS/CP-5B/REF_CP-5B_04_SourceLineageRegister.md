<!-- REF_CP-5B_04 (T2) | 2026-06-03 -->
<step_reference module="CP-5B" step="04" name="Source Lineage Register">
<input>T5B.3; all source files and module outputs.</input>
<gate>Step 3 complete.</gate>

## Instructions
1. Build a source-lineage register connecting each material statement to its full provenance chain.
2. For each statement: record Statement, Source Path, Source File, Source Document ID, Page/Section, Module Section, Type (Sourced/Calculated/Assumption/Inference/Weak Lineage/Untraced/Conflicting), Source Quality, and Notes.
3. Granularity: statement-level (not section-level). Each distinct factual claim, metric, legal assertion, or market datapoint = one row.
4. If source file is not available → record [Source Not Provided] and note in Notes column.

## Output
T5B.4: `Statement`|`Source Path`|`Source File`|`Source Document ID`|`Page / Section`|`Module Section`|`Type`|`Source Quality`|`Notes`
</step_reference>
