# CP Agents — Extension Guide v2.0
Updated: 08 June 2026
Resolves: Audit L-2

## Purpose
This guide provides the specification for extending the CP Agents Credit Operating System with new modules, layers, or infrastructure services.

---

## 1. Adding a New Analytical Module

### 1.1 Required Artefacts
For each new module CP-[ID], create:
1. `CP-[ID]_ACTIVE_PROMPT.md` — Active Prompt
2. `CP-[ID]_PAYLOAD.schema.txt` — Payload schema extending BASE
3. `REF_CP-[ID]_[Step]_[Name].md` — Step reference files
4. Entry in `MODULES_REFERENCE_v2.md`
5. Entry in `MODULE_EXECUTION_ORDER_v2.md`
6. Edges in `SYSTEM_ROUTE_MAP_v2.md`
7. Entry in `CP_ONBOARDING_DOCUMENTATION_v3.txt` Section 6

### 1.2 Active Prompt Structure
Every Active Prompt MUST contain identity, upstream/downstream, role, analytical focus, Evidence → Risk Mechanic → Credit Implication chain, prohibited behaviours, content distinctions, workflow steps, FINAL_OUTPUT_STRUCTURE, style guidelines, and export contract.

### 1.3 Payload Schema Rules
- MUST use `allOf/$ref` to `CP_MODULE_PAYLOAD_BASE.schema.txt`.
- `module_id`, `module_name`, `owned_object` MUST match `MODULES_REFERENCE`.
- `schema_family` MUST be `Nested` or `Infrastructure`.
- `source_basis` MUST NOT appear — deprecated per Update U2.
- `runtime_output` MUST contain module-specific fields matching Active Prompt FINAL_OUTPUT_STRUCTURE.
- All enum values MUST come from canonical taxonomy files.

### 1.4 Naming Convention
- Active Prompt: `CP-[ID]_ACTIVE_PROMPT.md`
- REFs: `REF_CP-[ID]_[Step]_[Name].md`
- Schema: `CP-[ID]_PAYLOAD.schema.txt`
- No M-prefix anywhere.

---

## 2. Adding a New Layer
1. Assign layer code.
2. Update execution order, route map, onboarding documentation, and modules reference.
3. Ensure no circular dependencies except the sanctioned CP-SR ↔ CP-MON loop.

---

## 3. Adding Infrastructure Services
Infrastructure modules are exempt from single-.docx export contract and analytical payload schemas. They must be registered in MODULES_REFERENCE and have explicit boundary documentation.

---

## 4. Email Intelligence Integration (NEW in v2.0)
The email intelligence layer enables modules to consume classified email signals via `REF_CP-EMAIL_SourceRoutingMatrix.md`.

Requirements:
- 8 email categories with tiered confidence scoring.
- Per-module routing matrix.
- Staleness limitations for older emails.
- Source attribution for every email-derived claim.

Modules currently using email intelligence include CP-SR, CP-MON, CP-0, CP-1A, CP-2C, CP-2B, CP-4, and CP-5.

---

## 5. L7 Monitoring Layer (NEW in v2.0)
L7 contains:
- CP-SR (SectorReview): sector-level thematic analysis.
- CP-MON (CreditPulse): issuer-level credit monitoring.

CP-SR ↔ CP-MON is the only sanctioned bidirectional data flow. Cycle termination is governed by `CP_SYSTEM_QA_GATES_v2.txt` Gate X7.

---

## 6. Governance Checklist
- [ ] Active Prompt follows structural template
- [ ] Payload schema extends BASE and passes S1–S7
- [ ] All enums from canonical taxonomy files
- [ ] Upstream/downstream declared and consistent
- [ ] Export contract compliant
- [ ] Entry in MODULES_REFERENCE, EXECUTION_ORDER, ROUTE_MAP, and ONBOARDING
- [ ] REF files use canonical naming convention
- [ ] QA audit confirms no VE exceptions

---

## 7. Version History
| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-05-29 | Initial release |
| 2.0 | 2026-06-08 | Added L7, email intelligence, cycle termination, naming convention update |
