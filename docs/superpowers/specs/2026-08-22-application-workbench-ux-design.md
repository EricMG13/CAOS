---
meta:
  contentType: Conceptual
  title: Make CAOS analysis faster to navigate and interpret
  audience: Product, design, frontend, backend, and quality engineering
---

# Make CAOS analysis faster to navigate and interpret

This specification defines an application-wide Analyst Workbench for CAOS. It combines Bloomberg-style speed and authority with Tableau-style linked visual analysis. The design keeps layouts curated so every analyst reads the same hierarchy.

## Goal

Enable an analyst to identify a material change, understand its credit implication, and verify its evidence within two minutes.

The design optimizes for a 1440 px or wider analyst desktop. Laptop and tablet layouts remain fully usable with simplified composition.

## Product decisions

The approved design uses these decisions:

- Start with issuer or case selection
- Organize primary navigation by analyst workflow
- Use curated layouts without dashboard construction
- Lead the Overview with material change and implication
- Combine visible navigation with a universal command palette
- Link selections across related content within the current view
- Keep one analyst-first interface for all roles
- Open evidence and quality assurance (QA) in contextual drawers
- Keep the latest accepted snapshot authoritative
- Lead analytical screens with narrative and selected visualisations
- Measure success through comprehension and verification time

## Analyst Workbench structure

The workbench uses one application shell across every workflow.

### Top context bar

The top bar preserves the active issuer and case while the analyst changes workflows. It shows:

- Issuer and case identity
- Accepted snapshot date
- Freshness or newer-analysis state
- Textual QA status
- Source count
- Access to the command palette

Changing issuer or case remains available from the top bar. A change clears incompatible local selections before loading the next authority.

### Workflow rail

The slim rail organizes work into six stages:

1. Overview
2. Sources
3. Analyse
4. Compare
5. Model
6. Publish

The rail names analyst tasks instead of internal product modules. It may compact at narrower widths but remains reachable.

### Main canvas

The main canvas contains one dominant reading or work region. Each workflow changes the content while retaining the same authority, narrative, evidence, visualisation, state, and detail patterns.

### Context drawer

The right drawer displays evidence, QA, filters, methodology, and supporting detail. It overlays the canvas instead of shrinking it.

The drawer uses native dialog behaviour. Escape closes it, focus stays inside while open, and focus returns to the trigger.

### Command palette

The command palette accelerates visible navigation. It supports:

- Issuer search
- Case switching
- Workflow navigation
- Evidence lookup within authorized scope
- Common workflow actions

Every palette command also has a visible point-and-click route. Keyboard use is optional.

## Workflow mapping

The current destinations map into analyst workflows:

| Workflow | Existing capabilities | Primary question |
| --- | --- | --- |
| Overview | Cases and Command Center summary | What changed and why does it matter? |
| Sources | Sources | What information supports this analysis? |
| Analyse | Run Console and Deep-Dive | What does the governed analysis conclude? |
| Compare | RV Screener and snapshot comparison | How does this differ across time, peers, and instruments? |
| Model | Model Builder | How do assumptions affect the credit profile? |
| Publish | Report Studio | What can be reviewed, approved, and frozen? |

Existing routes redirect to their corresponding workflows. Redirects preserve valid issuer, case, run, artifact, and source identifiers.

## Shared information hierarchy

Every analytical view follows this reading order:

1. **Change**: the material development since the accepted comparison point
2. **Implication**: the effect on credit quality, liquidity, downside, or valuation
3. **Evidence**: inline `E-xx` chips after supported claims
4. **Key measures**: only values required to interpret the conclusion
5. **Visual explanation**: one or two governed visualisations
6. **Detail**: reconciliations, tables, methods, and exceptions on demand

The conclusion-first narrative receives the strongest visual emphasis. Metrics use a flat divided row instead of separate cards. Visualisations answer a named analytical question and state units, basis, observation date, and evidence.

## Linked analysis

Tableau-style linked selection connects related information without changing governed data.

Selecting a period, instrument, scenario, chart mark, or table row highlights related:

- Narrative claims
- Metrics
- Chart marks
- Table rows
- Evidence chips

A visible context strip names the active selection and includes one **Clear** action. The selection remains local to the current view and does not become a hidden global filter.

Moving to another workflow clears transient analytical selections. Returning restores the last meaningful location, not previous transient filters.

## Evidence contract

Evidence uses the legacy analytical interaction across the application:

- Show only the stable identifier, such as `E-12`, in the chip
- Use a compact mono chip with a blue outline for normal evidence
- Use an amber outline and warning glyph for evidence with a QA concern
- Cross-highlight every visible matching chip on pointer hover or keyboard focus
- Leave unrelated evidence unchanged
- Open the exact source excerpt and immutable locator on activation
- Resolve the identifier within the active accepted snapshot and source set
- Return focus to the activating chip when the drawer closes

The evidence drawer shows:

- Evidence identifier
- Source title
- Immutable source locator
- Source and snapshot identity
- Extracted excerpt
- Evidence trace
- **Open full source** action

The interface never substitutes a newer or similarly named source.

## QA contract

The top bar always shows textual QA state. Passed QA uses little space. Warnings and critical findings remain visible in the resting view.

The QA drawer leads with:

- Critical and warning counts
- Affected conclusions
- Failed or incomplete checks
- Remediation status
- Passed checks after exceptions

A favourable summary cannot hide a material exception.

## Workflow designs

### Overview leads with material change

Overview helps the analyst resume work within ten seconds. It leads with material changes, implications, and evidence.

The secondary regions show:

- Current credit snapshot
- Unresolved risks
- Newer-analysis state
- Next useful action
- Compact workflow health

Overview does not become a grid of equal-weight cards.

### Sources keeps authority visible

Sources uses an issuer-level register with search, type and date filters, freshness, ingestion state, and source-set membership.

Selecting a source opens metadata and extracted blocks in the context drawer. Upload and withdrawal remain explicit governed actions.

### Analyse separates execution from review

Analyse contains two distinct tasks:

- Run Console shows progress, failures, exceptions, and acceptance
- Deep-Dive presents completed module narratives, metrics, evidence, and governed visualisations

Deep-Dive uses the approved focus view. Modules use one compact selector instead of a persistent column.

### Compare makes differences primary

Compare supports accepted-snapshot deltas and relative value. It leads with material differences before charts and tables.

Analysts may select peers, periods, and instruments from curated controls. They cannot construct dashboards.

### Model preserves editor space

Model retains a full-screen specialist editor. The surrounding shell compacts so the model receives the available space.

Evidence, source assumptions, and QA open contextually without covering the selected cell or schedule.

### Publish separates draft from authority

Publish retains the light paper workspace. It separates analytical inputs, draft state, validation, approval, and frozen output.

Navigation warns before discarding unsaved work. A frozen report preserves its exact analytical and evidence inputs.

## Authority and state model

The latest accepted snapshot remains the default authority. New completed analysis creates a visible comparison opportunity but does not replace the accepted view automatically.

Every surface distinguishes these states:

| State | Required presentation |
| --- | --- |
| Loading | Preserve geometry with restrained skeletons |
| Ready | Show accepted authority, observation time, and source-set identity |
| New analysis | Keep accepted content visible and offer comparison |
| Partial | Name missing fields, modules, or evidence |
| Stale | Explain why the content is stale and identify newer authority |
| Error | Preserve context and provide the nearest recovery action |
| Unavailable | Explain permission, methodology, or data constraints |

The interface never fills unavailable values with samples or older values.

## Responsive behaviour

The primary composition targets analyst desktops at 1440 px or wider.

At narrower widths:

- Two-column analytical layouts collapse to one column
- The workflow rail compacts without disappearing
- Drawers fit the viewport without page overflow
- Wide tables retain horizontal access and freeze identity columns
- Secondary metadata collapses before narrative, authority, or evidence
- Header labels compact while accessible names remain complete

Mobile supports review and navigation. Model and report editing may require a larger workspace when the interaction cannot remain safe or legible.

## Accessibility requirements

The workbench targets Web Content Accessibility Guidelines (WCAG) 2.1 AA.

Required behaviour includes:

- Small labels meet contrast requirements
- Status combines colour with text or a glyph
- Charts include descriptions and equivalent data tables
- Linked selections work with pointer and keyboard
- Focus remains visible
- Dialogs contain focus and return it to the trigger
- Zoom and reflow preserve access to content
- Reduced motion removes nonessential transitions
- Command-palette functions remain available through visible navigation

## Performance requirements

The shell must preserve analytical flow:

- Workflow navigation updates immediately from cached shell state
- Unchanged accepted authority is not refetched during every workflow change
- Large tables and source lists render incrementally
- Drawers load detail without blocking the main canvas
- Linked highlighting updates without a network request
- New authority invalidates only affected cached views

Performance budgets require measurement during implementation. The plan must define measurable targets from the current application baseline before changing production code.

## Data flow and boundaries

The shell owns issuer, case, workflow, accepted authority, and global drawer context. Each workflow owns its local selection and filters.

The data flow is:

1. Select issuer or case
2. Resolve authorized accepted authority
3. Load the workflow summary
4. Load detail on demand
5. Keep linked selection local in the browser
6. Resolve evidence through case-authorized, snapshot-pinned routes
7. Compare new analysis before changing accepted authority

The implementation reuses existing snapshot, artifact, evidence, provenance, visual recipe, status, dialog, and focus contracts.

The client renders only governed visual data. If an artifact lacks series or category values, the server contract must supply them before the visualisation ships.

## Security and privacy gates

The universal palette and contextual drawers must not broaden data access.

Implementation must prove:

- Issuer and case searches enforce the caller's authorized scope
- Direct identifiers cannot retrieve another case's evidence or source blocks
- Redirects preserve identifiers only after authorization
- Source excerpts render as text and cannot inject markup
- URLs do not contain sensitive excerpts or search results
- Cached workflow data clears on identity or authorization changes
- Palette actions use the same permission checks as visible actions

## Rollout plan

The application-wide design ships in five bounded phases:

1. **Foundation**: shell, workflow navigation, command palette, authority header, drawer, evidence chips, linked selection, and shared states
2. **Overview and Sources**: issuer entry, change-led overview, and source authority
3. **Analyse and Compare**: Run Console, Deep-Dive, snapshot comparison, and relative value
4. **Model and Publish**: specialist editor integration and report workflow
5. **Consolidation**: remove duplicate navigation, status, evidence, and panel patterns

Each phase must leave the application coherent and usable. Existing routes remain valid during migration.

This document is the umbrella interaction contract. The first implementation plan covers the Foundation phase only. Each later phase receives its own implementation plan after the previous phase passes its acceptance checks.

## Test strategy

### Contract tests

Verify:

- Accepted authority remains stable
- Source and evidence resolution stays snapshot-pinned
- Issuer and case authorization applies to search and direct identifiers
- Partial, stale, error, and unavailable states remain distinct
- Frozen reports retain exact inputs

### Interaction tests

Verify:

- Issuer and case switching clears incompatible state
- Workflow navigation restores meaningful location
- Command palette matches visible navigation permissions
- Linked highlighting includes related content only
- Evidence chips synchronize by identifier
- Drawers close with Escape and return focus
- Comparison precedes accepted-authority switching
- Unsaved-work guards prevent accidental loss

### Visual and accessibility tests

Verify:

- 1440 px desktop and 1024 px laptop layouts
- 200% browser zoom
- Keyboard-only navigation
- Reduced motion
- Chart descriptions and data equivalents
- Wide-table access
- Project axe runner across all workflows
- Screenshots for ready, stale, partial, warning, and error states

## Adversarial implementation gates

The design review identified these high-impact risks:

1. A stale issuer or case context could bind analysis to the wrong authority. Every workflow request must include and validate explicit authority identifiers.
2. Linked highlighting could imply causation or filtering that the data does not support. Every link requires a typed relationship from the governed payload.
3. The command palette could bypass visible permission guards. Palette and visible actions must call the same authorized action path.
4. A compact QA summary could hide a material exception. Critical and warning states remain visible outside the drawer.
5. Route migration could break deep links. Redirect tests must cover issuer, case, run, artifact, and source identifiers.
6. Universal search could expose unauthorized issuer or source names. Search results must apply authorization before returning labels.
7. A single workspace component could become harder to maintain. The plan must divide the shell, workflow surfaces, and contextual inspectors by responsibility without speculative abstractions.

## Non-goals

This design does not add:

- User-built dashboards
- Draggable or resizable analytical layouts
- Persistent global analytical filters
- A command-only interface
- Separate applications for Analyst, portfolio manager (PM), and QA roles
- Decorative charts
- Sample data in unavailable states
- A new charting, modal, or state-management dependency without measured need

## Acceptance criteria

The redesign succeeds when:

1. An analyst can select an issuer or case and identify the material change, implication, and evidence within two minutes
2. Primary navigation uses Overview, Sources, Analyse, Compare, Model, and Publish
3. Every analytical view follows the shared reading hierarchy
4. Linked selection affects related content within the current view only
5. Evidence chips preserve legacy identifier, severity, synchronization, and exact-source behaviour
6. QA and evidence remain one interaction away without permanent sidebars
7. The accepted snapshot remains authoritative until an explicit switch
8. Existing deep links continue to resolve within authorized scope
9. Desktop, laptop, keyboard, zoom, and reduced-motion checks pass
10. The project axe runner reports no violations on migrated workflows
