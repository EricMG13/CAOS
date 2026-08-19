# Final audit scope

## Audited product

CAOS — Credit Agent OS, implemented in `caos/frontend` and exercised through
the production Next.js build with deterministic authenticated browser fixtures.

Audited routes:

1. `/`
2. `/command`
3. `/decisions`
4. `/deepdive`
5. `/issuers`
6. `/issuers/profile?id=iss-1`
7. `/model`
8. `/monitor`
9. `/pipeline`
10. `/portfolios`
11. `/query`
12. `/reports`
13. `/research`
14. `/sector`
15. `/sector-rv`
16. `/settings`
17. `/sponsors`
18. `/upload`

Representative populated interactions are additionally exercised by the
retained Task 4A, Task 4B, and Task 4C workflow harnesses rather than inferred
from cold routes.

## Users and primary tasks

- Primary: buy-side credit analyst. Build a defensible issuer view across
  Deep-Dive, Model Builder, and Report Studio with every material conclusion
  traceable to governed evidence.
- Secondary: PM/CIO. Scan posture, changes, and portfolio impact without losing
  access to the underlying analytical work.
- Secondary: Head of Research/QA. Inspect gates, exceptions, freshness,
  ownership, and evidence health while retaining the shared data and authority
  model.

## Constraints

- Supported acceptance target: desktop and tablet at 1440, 1280, 1024, and
  768 CSS pixels; keyboard operation; reduced motion; real 200% browser zoom.
- Phone-specific redesign is excluded. Retain a mount, landmark, crash,
  existing-axe, and shared-semantics smoke only.
- WCAG 2.1 AA is the accessibility floor.
- Preserve the institutional dark terminal, Report paper identity,
  DecisionHeader, source authority, immutable publication gates, tabular
  numerics, and one shared permission/data inventory.
- Live is the default data mode. Seeded fixtures are allowed only in explicit,
  URL-addressable Reference mode and must remain visibly labelled.
- The repository is a dirty parallel worktree. No staging, committing, broad
  cleanup, or unrelated modification is authorized.

## Input materials and references

- Original 77-fault register:
  `DESIGN-IS-2026-07-19/05-all-faults-and-personas.md`
- Remediation ledger:
  `DESIGN-IS-2026-07-19/06-remediation-ledger.md`
- Product design context: `AGENTS.md`, `.impeccable.md`, `PRODUCT.md`, and
  `DESIGN.md`
- Established anti-references: friendly consumer SaaS, marketing dashboards,
  decorative gradients/glow, raw terminal dumps, and color-only status.
- Category references are principles rather than visual templates: dense
  institutional credit terminals, exact analytical workbenches, and filed
  committee documents.

## Acceptance

- Zero unresolved in-scope findings.
- Rams score at least 25/30, with no zero.
- Nielsen score at least 35/40.
- Analyst, PM, and QA primary walks pass.
- All required regression, build, accessibility, responsive, zoom, truth,
  and performance gates pass or are explicitly shown not applicable to the
  locked scope.
