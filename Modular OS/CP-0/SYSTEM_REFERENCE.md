<!-- CP-0 System Reference (Tier 4) | 2026-06-02 -->
<system_reference module="CP-0" tier="4">
## Identity: CP-0 | SourceReadiness | L0 | v2.1 | DOWN: CP-X only
## Anti-Pattern: Entity from filename
BAD: "Issuer is Acme Corp based on filename." GOOD: "Issuer = Acme Corporation Ltd from FS header (p.1)."
## Fail: Unsupported claim | Missing trace | Unresolved conflict | Malformed schema | QA-blocked upstream | Filename-only w/o flag
## Version: 2026-06-02 | tiered + renamed (REF_CP-0_X_Name.md)
</system_reference>
