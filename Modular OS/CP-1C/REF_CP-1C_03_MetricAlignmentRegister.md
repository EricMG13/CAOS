<!-- REF_CP-1C_03 (T2) | 2026-06-02 -->
<step_reference module="CP-1C" step="03" name="Metric Alignment Register">
<input>T4.1 + CP-1 data</input>
<gate>T4.1 complete</gate>

## Instructions
For every planned comparison, apply 11-point alignment standard. Assign comparability status. Log limitations. Web-scraped vs audited = provenance gap flag.

Apply the 9 Non-Comparability Triggers in REF_CP-1C_ValuationAndOutlierRules.md when assigning Not Comparable / Comparable with Limitations.

## Output
T4.2: `Metric`|`Borrower Value`|`Borrower Period`|`Peer Entity`|`Peer Value`|`Peer Period`|`AP1-AP11`|`Comparability Status`|`Limitation Notes`
</step_reference>
