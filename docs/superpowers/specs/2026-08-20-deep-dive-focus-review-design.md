# Deep-Dive Focus Review — Design Specification

**Date:** 2026-08-20
**Status:** Approved design
**Surface:** Deep-Dive
**Primary user:** Buy-side credit analyst

## Purpose

Deep-Dive is a review surface for governed module outputs. It presents the
module narrative and its visualisations, lets the analyst compare accepted
information, and keeps every material claim one interaction from its source.

The screen is not a portfolio workspace, coverage dashboard, research search
tool, or committee decision record.

## Design outcome

Use a full-width focus canvas. Narrative and visualisations occupy the resting
screen. Module navigation, QA, and source inspection remain immediately
reachable without reserving permanent columns.

The resting hierarchy is:

1. Case identity and compact QA/source controls.
2. Current module selector and optional comparison control.
3. Module title, authority, confidence, and observation date.
4. Conclusion-first narrative with inline evidence chips.
5. A restrained row of the few metrics needed to read the narrative.
6. Governed visualisations with accessible descriptions and source access.
7. Secondary module details on demand.

## Information architecture

### Global header

- Show the CAOS identity, active case, `QA` status, and source count.
- The global destination rail is collapsed behind a standard navigation
  control in this focused surface.
- `QA passed` and `Sources` are compact buttons, not persistent panels.
- Status always includes text or a glyph; colour never carries meaning alone.

### Module bar

- A single labelled selector replaces the persistent module column.
- The selector shows the module identifier and concise module name.
- Show position in the available module set, such as `1 of 7`.
- `Compare prior` is available but visually secondary.
- Do not show coverage concepts or portfolio concepts.

### Module header

- Show module identifier, canonical module title, status, confidence, and
  observation date.
- Authority metadata stays compact and aligned to the right on wide screens.
- On narrow screens, preserve the title and move secondary authority detail
  behind module details rather than compressing the narrative.

### Narrative

- Lead with the module takeaway in one concise paragraph.
- Follow with the basis, exceptions, and distinctions required to understand
  the conclusion.
- Keep prose to approximately 65–75 characters per line.
- Insert evidence chips directly after the claim they support.
- Do not add editing, thesis, recommendation, or decision controls.

### Key metrics

- Show only values needed to interpret the active narrative or visualisation.
- Use a flat divided row rather than individual metric cards.
- Values use tabular mono numerics; deltas include explicit signs.
- Semantic colour is permitted for direction only when the sign and value are
  also present.

### Visualisations

- Show governed module visual recipes only.
- Each visual includes a clear title, units/basis, accessible description or
  table, and direct evidence access.
- Avoid decorative charts, duplicate headline metrics, and charts without a
  narrative purpose.
- Comparison remains opt-in so the current accepted view stays primary.

## Legacy evidence-chip contract

Carry forward the legacy analytical evidence interaction:

- Render only the stable evidence identifier in the chip, for example
  `E-12`; keep filenames, pages, and section locators in the inspector.
- Use a compact mono chip with a blue outline for normal evidence.
- Use an amber outline plus a warning glyph for evidence with a QA concern.
- Hovering or focusing a chip cross-highlights every visible chip with the
  same evidence identifier and leaves unrelated chips unchanged.
- Activating a chip opens the exact cited source, locator, and excerpt in the
  contextual evidence drawer.
- Chip activation is keyboard-operable and focus remains visible.
- Closing the drawer returns focus to the activating chip.
- Evidence identifiers resolve within the pinned accepted snapshot and source
  set; the UI never substitutes a newer or similarly named source.

## QA and source drawers

QA and source inspection use contextual right-side drawers. They overlay the
canvas rather than shrinking it.

### Evidence drawer

- Open from an evidence chip, the source-count control, or a visual's evidence
  action.
- Show evidence ID, source title, immutable locator, source/snapshot identity,
  excerpt, and a control that opens the source at the cited location.
- Show the concise evidence trace needed to establish extraction, module use,
  and QA validation.
- The drawer content must update atomically for the selected evidence ID.

### QA drawer

- Open from the compact QA status in the header.
- Lead with the overall result and critical-finding count.
- Show checks and exceptions in a short scan list.
- Keep detailed QA evidence behind the individual check when needed.

Both drawers use native dialog behaviour: Escape closes, focus is trapped while
open, the backdrop distinguishes the transient state, and focus returns to the
trigger.

## Interaction states

- **Ready:** accepted module output, source set, and QA state are available.
- **Stale:** the visible accepted snapshot remains explicit; a newer run cannot
  silently relabel the content.
- **Partial:** unavailable narrative fields or visual recipes are named, not
  replaced with sample data.
- **QA warning:** the header status and affected evidence chips use a warning
  glyph and label.
- **Unavailable/error:** keep the module selector and case context, state what
  is unavailable, and offer the nearest recovery action.
- **Loading:** preserve the page geometry with restrained skeletons; do not
  replace the canvas with a central spinner.

## Responsive behaviour

- Desktop keeps the narrative and visualisations in one centered focus canvas.
- Visualisations collapse from two columns to one when their readable plotting
  width would be compromised.
- The module selector remains available at every width.
- Header labels may compact on phones, but QA and Sources remain named for
  assistive technology.
- Drawers use the available viewport width without horizontal overflow.
- Touch targets expand on touch layouts without enlarging desktop evidence
  chips inside prose.

## Accessibility

- Meet WCAG 2.1 AA contrast requirements, including muted metadata.
- Every chart has an accessible description and equivalent data table.
- Evidence synchronization works with pointer hover and keyboard focus.
- Warning and status meaning never depends on colour alone.
- Use visible focus rings and logical document/tab order.
- Respect `prefers-reduced-motion`; no decorative motion is required.

## Data and implementation boundaries

- Reuse the existing accepted snapshot, artifact narrative, evidence reference,
  authority, confidence, provenance, and visual-recipe contracts.
- Extend the visual payload only where actual governed series/category values
  are required; do not fabricate chart data in the client.
- Resolve evidence references through case-authorized, snapshot-pinned source
  detail routes.
- Reuse the existing dialog, status, typography, palette, and focus patterns.
- Do not add a new charting or modal dependency unless the existing stack
  cannot render an approved visual recipe accessibly.

## Explicit non-goals

- Portfolio holdings, sizing, monitoring, or posture.
- Coverage management or coverage-health dashboards.
- Committee decisions, approvals, thesis authoring, or recommendation editing.
- A research query composer or general source search experience.
- Persistent module, QA, or evidence sidebars.
- Manual editing of governed module output.

## Acceptance criteria

1. The resting desktop screen devotes no permanent column to modules, QA, or
   sources.
2. The analyst can change module, inspect QA, and open exact evidence in one
   interaction each.
3. Narrative and visualisations remain the dominant visual hierarchy.
4. Evidence chips match the legacy identifier, severity, synchronization, and
   exact-source behaviour.
5. QA and evidence drawers are keyboard-operable and do not lose reading
   position.
6. The surface contains no coverage, portfolio, or committee-decision concepts.
7. Desktop and narrow layouts have no horizontal page overflow.
8. The implemented route passes the project axe runner and focused interaction
   tests for evidence synchronization and drawer focus return.
