<!-- REF_CP-5_09 (T2) | 2026-06-03 -->
<step_reference module="CP-5" step="09" name="Consolidated Issue Log">
<input>All findings from Steps 2–8 (T5.2–T5.8).</input>
<gate>Steps 2–8 complete.</gate>

## Instructions
1. Consolidate ALL findings from Steps 2–8 into a single sequenced issue log.
2. Assign sequential Issue IDs: CP5-001, CP5-002, CP5-003, etc.
3. For each issue: record Issue ID, Severity (CRITICAL/MATERIAL/MINOR), Module, Issue Type (from 23 Defect Categories), Description, Required Fix, Clearance Impact (from 9 Clearance Impact Labels), and Status (Open).
4. Ensure every finding from T5.2–T5.8 appears exactly once.
5. Order by severity (Critical first, then Material, then Minor).
6. This log is the single source of truth for the Remediation Priority Map and Clearance Decision.

## Output
T5.9: `Issue ID`|`Severity`|`Module`|`Issue Type`|`Description`|`Required Fix`|`Clearance Impact`|`Status`
</step_reference>
