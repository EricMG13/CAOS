<!-- CP-0 System Reference (Tier 4) | 2026-08-02 -->
<system_reference module="CP-0" tier="4">
## Identity: CP-0 | SourceReadiness | L0 | v3.1 | UPSTREAM: CP-PARSE | OWNED OBJECT: source_readiness_register | PRIMARY DOWN: CP-X | OPTIONAL ADVISORY REUSE: CP-DR
## Boundary: source sufficiency, effective-source assessment and downstream readiness; CP-PARSE exclusively owns triage, extraction, fidelity and packaging.
## Representation: consume CP-PARSE's frozen one-active-representation catalog; never change a preparation decision inside CP-0.
## Anti-Pattern: Entity from filename
BAD: "Issuer is Acme Corp based on filename." GOOD: "Issuer = Acme Corporation Ltd from FS header (p.1)."
## Fail: Unsupported claim | Missing trace | Unresolved conflict | Malformed schema | Mutated original | Double-active representation | Blocked parse fallback | QA-blocked upstream | Filename-only w/o flag
## CP-DR rule: Passed/Restricted may seed source provenance; Blocked may seed gaps only; never seed analytical claims.
## Remediation: incomplete inventory, changed hashes, failed package or blocked preparation routes back to Run CP-PARSE.
## Version: 2026-08-04 | standalone readiness after CP-PARSE
</system_reference>
