# Impeccable Assessment A — Design Review (2026-07-13)

Target: `caos/frontend` Workbench + Atlas remediation. Assessment completed before deterministic detector input.

## Verdict

AI slop: **Pass**. The interface is recognizably CAOS rather than a generic SaaS dashboard: dense table/editor instruments, evidence-first language, restrained color and the paper Report Studio counterpoint are domain-earned.

## Nielsen score (pre-final-fix)

1. Visibility of system status — 4/4
2. Match to the real world — 4/4
3. User control and freedom — 3/4
4. Consistency and standards — 4/4
5. Error prevention — 4/4
6. Recognition rather than recall — 3/4
7. Flexibility and efficiency — 4/4
8. Aesthetic and minimalist design — 4/4
9. Error diagnosis and recovery — 3/4
10. Help and documentation — 2/4

**Total: 35/40.**

## Strengths

- Explicit decision-state and authority grammar prevents failed responses from masquerading as calm portfolio conclusions.
- Shared page/worklist anatomy creates predictable scanning without flattening Model, Query or Report Studio into generic tables.
- The institutional terminal hierarchy remains coherent: color signals state, dense numerics stay aligned, and evidence is contextual rather than permanently stealing workspace width.

## Priority issues

- **P1 — Sector Review error leakage:** the static/offline state exposes raw Axios copy (`Request failed with status code 404`) and the empty evidence inspector still shows `DEMO / DERIVED / DRAFT`, implying authority where no observation exists. Replace it with a constructive recovery state and suppress authority until data exists.
- **P2 — Phone reachability:** page-level primary actions remain top-right. Monitor is correctly triage-only, but acknowledge/assign actions should remain sticky near the thumb zone when live alerts exist.
- **P2 — Utility discoverability:** moving layout/simulation/export controls into drawers improves hierarchy but increases recall cost. Current labels are adequate; retain direct keyboard accelerators and direct Model history controls.
- **P3 — Repeated authority chips:** four identical authority rows in decision context are defensible but visually repetitive. Consider a single shared authority footer only if claim-level authority never diverges.

## Persona red flags

- **Alex, power analyst:** direct Model checkpoints must not disappear into utilities; retained inline after regression review.
- **Sam, keyboard/low-vision analyst:** phone and 200% reflow must not inherit an off-canvas concept strip; the responsive matrix caught and remediated this.
- **Buy-side analyst:** any empty evidence pane that implies source/method/approval without an observation is unacceptable; Sector Review requires the P1 correction above.
- **PM/CIO:** unavailable portfolio feeds must remain visibly unavailable rather than being replaced by demo posture in the decision strip; current decision-state contract passes.
- **Head of Research/QA:** role composition must never read as approval authority; `View` labeling and approval chips remain separate.

## Emotional journey

The strongest moment is the immediate decision-context read on analytical surfaces, followed by confidence from one-click evidence. The main valley is an offline worklist that exposes transport jargon or an authority-looking empty evidence pane. Recovery language should reassure the user that filters/selections are preserved and no conclusion was drawn.
