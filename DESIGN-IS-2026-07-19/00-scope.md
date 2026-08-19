# CAOS Frontend Design Audit — Scope Lock

## Target

- Repository surface: `caos/frontend`
- Stable critique target: `caos/frontend/src/app`
- Impeccable target slug: `caos-frontend-src-app`
- Platform/register: Next.js 16 web product UI
- Evidence modes: source inspection, deterministic design detector, rendered browser inspection, local accessibility/performance tooling where runnable

## Audited surfaces

The audit covers every routed frontend surface and the shared chrome they depend on.

### Core six-concept journey

1. `/command` — Command Center / portfolio posture
2. `/pipeline` — execution graph and module progress
3. `/deepdive` — issuer/deal analytical object
4. `/model` — Model Builder / cash-flow authoring
5. `/reports` — Report Studio / committee deliverables
6. `/monitor` — alert routing, email intelligence, and QA/governance

### Supporting analyst surfaces

7. `/issuers` — issuer directory/worklist
8. `/issuers/profile` — issuer profile and evidence-linked notes
9. `/upload` — document intake wizard
10. `/query` — cross-issuer query and evidence graph
11. `/research` — deep research workspace
12. `/sector` — sector review
13. `/sector-rv` — relative-value screener
14. `/sponsors` — sponsor track records
15. `/portfolios` — portfolio lab
16. `/settings` — analyst, model, source, and portfolio configuration
17. `/decisions` — decision register
18. `/` — persona-aware entry redirect

### Cross-cutting surfaces and states

- Global concept navigation, workflow rail, compact navigation, role-view switcher, and Ask `⌘K` launcher
- Shared enterprise page frame, panel shell, workbench toolbar, decision header, evidence inspector, utilities drawer, dialogs, popovers, tables, and forms
- Loading, observed-empty, stale, partial, offline, unavailable, success, validation, error-boundary, not-found, focus, disabled, and narrow/mobile variants
- Report Studio light-paper/print output and the full-model appendix

## Primary users and tasks

- **Primary:** buy-side credit analyst. Primary task: turn source documents, market marks, model assumptions, and evidence trails into a defensible, committee-ready credit view while keeping every material conclusion one interaction from its source.
- **Secondary:** PM/CIO. Primary task: scan portfolio posture and material changes quickly, then drill into the names that require judgment.
- **Secondary:** Head of Research/QA. Primary task: identify coverage, evidence, freshness, and governance failures and route corrective work.

## Constraints

- Preserve the existing CAOS design identity: dark institutional workspace, light filed-output paper, restrained signal-only color, Inter + JetBrains Mono, compact 6px geometry, and the 32px panel-header structural unit.
- Optimize for specialist accuracy and evidence traceability over consumer-style simplicity.
- WCAG 2.1 AA floor; status and tranche meaning may not rely on color alone; all primary workflows must remain keyboard-operable and usable with reduced motion.
- Treat dense information as legitimate intrinsic task complexity, but reject extraneous complexity, duplicated controls, weak hierarchy, illegible microtype, and concealed capability.
- This is a critique and planning handoff only. No implementation code is authorized in this run.
- No delivery deadline was supplied.

## Reference frame

- Product and design contracts: `PRODUCT.md`, `DESIGN.md`, `.impeccable.md`, and `AGENTS.md`
- Impeccable product-register criteria and critique heuristics
- Dieter Rams' ten principles via design-is
- No external competitor benchmark was supplied. Familiar institutional patterns (Bloomberg/FactSet/Capital IQ-style desk density and modern expert tools such as Linear/Figma/Raycast) are used only as category calibration, not as implementation targets.

## Known evidence limitations at scope lock

- GitNexus semantic query returned no processes because its FTS indexes are missing; route inventory therefore uses deterministic filesystem and source references.
- Live rendered coverage depends on the local API/demo fixtures and browser availability. Any route not renderable will be marked as source-inferred rather than silently treated as visually verified.
