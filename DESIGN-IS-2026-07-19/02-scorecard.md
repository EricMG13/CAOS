# Dieter Rams scorecard — CAOS frontend

The audit scores the worst representative instance across all 18 surfaces, not
the average. Scores use the exact 0–3 anchors from the `design-is` skill.

1. **Good design is innovative — Score: 2/3**
   Evidence: The evidence-authority decision brief, role-workbench concept, and dark-desk/light-paper pairing refresh familiar terminal/editor patterns ([01-evidence.md](01-evidence.md#evidence-by-rams-principle)).
   Justification: This is a clear improvement on standard specialist dashboards, but no pattern was shown to be absent from five or more peers, so 3 is not supportable.

2. **Good design makes a product useful — Score: 2/3**
   Evidence: Sixteen route entries expose reachable primary actions, while persona composition and narrow Report/Pipeline/Model modes add task friction ([01-evidence.md](01-evidence.md#accessibility-and-responsive-evidence)).
   Justification: The primary workflows are directly supported, but adjacent chrome and capability-preserving compression add steps and lateral discovery, so the “fewest possible steps” anchor for 3 is not met.

3. **Good design is aesthetic — Score: 1/3**
   Evidence: The coherent token system is interrupted by under-hierarchical route titles, 5.3–7 px appendix type, Portfolio micro-styling/stripes, sparse empty canvases, and clipped narrow artifacts ([01-evidence.md](01-evidence.md#visual-evidence)).
   Justification: More than five inconsistencies and at least one jarring violation are present, which matches 1 rather than the ≤2-minor-inconsistency ceiling for 2.

4. **Good design makes a product understandable — Score: 1/3**
   Evidence: Persona promises do not change the declared density/columns, Report uses two verbs for one drawer action, internal policy copy is exposed, and multiple compact/overflow controls require learned context ([01-evidence.md](01-evidence.md#copy-and-honesty-evidence)).
   Justification: More than three controls or labels are unclear and jargon is present, but primary actions remain generally identifiable, so 1—not 0—is the correct anchor.

5. **Good design is unobtrusive — Score: 2/3**
   Evidence: Hairline chrome, support drawers, and restrained color usually recede, although the global rail, 102 shared interaction sites, Ask dock, and crowded bands remain visible ([01-evidence.md](01-evidence.md#structural-evidence)).
   Justification: The chrome is visible but quiet; it adds attention cost without becoming decoration that consistently competes with analytical content.

6. **Good design is honest — Score: 1/3**
   Evidence: Provenance and readiness labels are strong, but the persona contract, Report action wording, and live/demo Monitor co-location break strict label-to-behavior mapping ([01-evidence.md](01-evidence.md#copy-and-honesty-evidence)).
   Justification: There are multiple material mismatches but no deceptive dark pattern, placing the product at 1 rather than 0 or the ≤1-minor-mismatch level implied by 2.

7. **Good design is long-lasting — Score: 3/3**
   Evidence: Flat tonal surfaces, standard table/editor forms, restrained motion, and signal-only color avoid gradients, glow, skeuomorphism, and trend typography ([01-evidence.md](01-evidence.md#visual-evidence)).
   Justification: No dated trend marker was identified, so the visual language should remain current over the rubric's three-year horizon.

8. **Good design is thorough down to the last detail — Score: 2/3**
   Evidence: Empty/loading/error/success/focus/disabled states exist, phone axe is clean, but desktop Report has one serious focusability violation and success closure is not unified ([01-evidence.md](01-evidence.md#accessibility-and-responsive-evidence)).
   Justification: One state class is rough rather than absent across multiple categories, matching 2; the verified accessibility defect prevents 3.

9. **Good design is environmentally friendly — Score: 2/3**
   Evidence: `/command` starts with 271.7 KB gzip-estimated JS, zero idle animations, and reduced-motion gating ([01-evidence.md](01-evidence.md#weight-and-attention-evidence)).
   Justification: This exactly matches the `<500KB, motion gated` anchor for 2 and is well above the `<100KB` ceiling required for 3.

10. **Good design is as little design as possible — Score: 1/3**
    Evidence: The audit found 19 excess same-purpose affordances, 15 global destinations, repeated evidence/decision chrome, and many five-plus option bands ([01-evidence.md](01-evidence.md#structural-evidence)).
    Justification: More than five removable/repeated elements exist, but analytical content—not decoration—still dominates, so 1 is more accurate than 0.

## Total

**17/30**
