<!-- CP-1A Schema Reference (Tier 3) | 2026-06-02 -->
<schema_reference module="CP-1A" tier="3">
## Output Objects
| ID | Step | Purpose |
|----|------|---------|
| source_classification | 2 | Source quality |
| transaction_summary | 3 | Transaction terms |
| company_description | 4 | Business description |
| revenue_business_mix | 4 | Revenue breakdown |
| ownership_register | 5 | Ownership structure |
| operating_model | 6 | Operating metrics |
| events_timeline | 7 | Credit events |
| credit_translation | 8 | Risk synthesis |
| gaps_ledger | 9 | Data gaps |
| conflict_log | 9 | Source conflicts |
| downstream_readiness | 10 | Module readiness |
## Extraction Types (13): sourced_fact | quoted_text | table_value | calculated_metric | analyst_inference | upstream_artifact | user_instruction | documentary_fact | definition_conflict | gap | source_limitation | insufficient_information | not_available
## QA: Sources classified | Objects present | Chains complete | Separation maintained | No M-prefix | Appendices A-E | No silent reconciliation | Gaps inline+ledger | Mgmt language labelled
## Export: [Issuer]_CP-1A_[YYYYMMDD].docx
</schema_reference>
