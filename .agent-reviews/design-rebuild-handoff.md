# CAOS Design Rebuild — Session Handoff

**Date:** 2026-07-11  
**Branch / HEAD:** `main` at `6bf73a1a`  
**Remote state at export:** `main` is 15 commits behind `origin/main`

## Purpose

Resume the persona-led CAOS application redesign developed in this session. The work so far is critique, product design, wireframing, and prioritization only. No product implementation was performed.

## Existing user WIP — preserve

These files were already modified at export time and were not changed by this design session:

- `caos/docs/PRE_DEPLOYMENT_PLAN.md`
- `caos/docs/PRE_DEPLOYMENT_SKILLS_SHORTLIST.md`

Do not stage, revert, overwrite, or fold these files into future design work without explicit user direction.

## Primary artifacts

1. **Full Impeccable critique:**
   `.impeccable/critique/2026-07-11T10-21-11Z__caos-frontend-src-app.md`
2. **Generated high-fidelity wireframe board:**
   `/Users/ericguei/.codex/generated_images/019f5065-931b-7633-ae66-557fdb17500d/exec-6dbed030-8564-4995-b279-01101bc78d3e.png`
3. **This handoff:**
   `.agent-reviews/design-rebuild-handoff.md`

## Critique outcome

- Collective application score: **29/40**.
- Strongest surfaces: Upload 35, Model 34, Pipeline/Reports 31.
- Lowest surfaces: Sector RV 24, Sector Review 25, Query 26, Command 27.
- System strengths: domain fluency, evidence lineage, status honesty, failure recovery, committee-specific output language.
- Systemic weaknesses: equal-weight control accretion, partial responsive bodies, fragmented provenance vocabulary, weak contextual help, ambiguous persistence/authority, and hidden expert gestures.
- Detector result: 22 advisories — 17 design-system colors and 5 radii. Most are governance drift; hierarchy and responsive behavior are materially more important.

## Product decisions already made

Treat these as locked defaults unless the user explicitly revises them:

1. **Evolve the existing design language; do not replace it.**
   - Preserve the dark institutional terminal, Inter/JetBrains Mono, compact density, signal-only color, 6px geometry, evidence-first panels, and paper deliverables.
   - Improve hierarchy, workflow grouping, role views, and responsive behavior.
2. **Workflow-grouped navigation.**
   - Intake: Issuers, Upload.
   - Analyze: Research, Query, Sector Review, Sector RV.
   - Decide: Command, Deep-Dive, Model.
   - Publish: Report Studio.
   - Monitor: Pipeline, Monitor.
   - Issuer Profile remains contextual and reachable from any stage.
3. **Explicit role views:** Analyst, PM, and QA.
   - A presentation preference, never an authorization claim.
   - Persist in the existing analyst settings JSON; default old profiles to Analyst.
4. **Phone triage only.**
   - Phone supports reading, alerts, evidence, acknowledgement, assignment, approved decisions, and desktop handoff.
   - Deep modeling, graph authoring, and report editing remain tablet/desktop workflows.

## Target shell and layout

The rebuilt shell has:

- Workflow groups instead of ten equal-weight concept chips.
- A persistent but secondary Analyst / PM / QA selector.
- One surface-level primary action.
- A decision header on analytical surfaces: **What changed / Why it matters / Required action / Evidence health**.
- Named layout regions: navigation or module finder, dominant active work, contextual evidence, and phone triage.
- Secondary controls collapsed into the existing accessible `MoreDrawer`.

## Persona red-flag resolutions

### Alex — power user

- One Query composer with an explainable, reversible intent router.
- Global command palette for modules, issuers, saved views, actions, and navigation.
- Recent and pinned Deep-Dive modules.
- Shared batch action bars for Issuers, Monitor, Sector Review, and QA.
- Model undo/redo, checkpoints, and multi-cell paste.
- Visible Pipeline open action; double-click remains only as an accelerator.

### Sam — keyboard / low vision

- Remove global clipping as a responsive strategy.
- Explicit table scrollers, rail-to-drawer behavior, and phone sequencing.
- Roving focus in graphs, grids, tabs, and module launchers.
- Region skip links.
- Minimum critical-action targets: 32px desktop, 44px touch.
- Remove Sector Review nested interactive controls.
- Use shared modal primitives for every dialog and slide-over.

### Buy-side analyst

- One provenance grammar:
  - Origin: LIVE / REFERENCE / DEMO.
  - Freshness: CURRENT / STALE / UNKNOWN.
  - Method: REPORTED / DERIVED / MODELLED.
- On-document authority labels for Reports and Research.
- Decision-first openings for Deep-Dive and Sector RV.
- Evidence follows the selected conclusion, model cell, graph node, or report claim.

### PM / CIO

- Command opens with ranked changes, reasons, required actions, ownership, and portfolio posture.
- Profile gets PM and Analyst views with sticky section navigation.
- PM view must answer posture, change, risk, evidence health, and action within ten seconds.

### Head of Research / QA

- Shared Governance Queue containing source gaps, stale conclusions, failed gates, mixed-origin content, and overdue refreshes.
- Each finding exposes issuer, severity, age, owner, origin, downstream consumers, and remediation route.
- QA queues become visible from Command and Monitor.

## Ranked net-new product additions

Do not add these as seven new peer-level navigation concepts; embed them in the workflow above.

1. **Portfolio Decision Lab** — current/proposed position, trade action, sizing, constraints, scenario loss, evidence health, rationale, and IC submission.
2. **Live Watchtower** — wire the existing autonomy engine into a real alert inbox and event→impact→owner→action→resolution loop.
3. **Scenario Network** — propagate one shock through model columns, liquidity, covenants, recovery, RV, portfolio loss, recommendation, and report status.
4. **IC Decision Room** — agenda, approvals, dissent, conditions, decision snapshot, expiry, and automatic reopen on material change.
5. **Thesis Memory** — versioned thesis, evidence changes, model overrides, alerts, decisions, predictions, and realized outcomes.
6. **Covenant & Sponsor Network** — cross-default dominoes, basket capacity, sponsor exposure/behavior, security structure, and maturity overlap.
7. **Coverage Control Plane** — source freshness, OCR/ingestion gaps, mixed origins, entitlements, QA failures, analyst ownership, and audit history.

## Recommended delivery order

### Phase 0 — critic and current-state gate

- Refresh from `origin/main` without touching the two WIP docs.
- Reconcile this handoff against the current tree; the branch was 15 commits behind when exported.
- Add a new proposal-specific critic entry to `.agent-reviews/redteam.md` before committing to the architecture.
- Challenge workflow grouping, role-mode complexity, phone limitations, and whether Decision Lab should precede Watchtower.

### Phase 1 — shared foundations

- Workflow-grouped navigation and shortcut map.
- Analyst / PM / QA preference in the existing `/api/settings/analyst` JSON contract.
- Shared provenance type and visual grammar.
- Rebuilt compound workspace layout and decision header.
- Responsive region behavior, keyboard region navigation, and target-size standards.

### Phase 2 — existing-surface restructuring

- Command and Profile role compositions.
- One-lane Query composer.
- Searchable Deep-Dive module finder.
- Sector RV actionable-dislocation opening.
- Reports/Research authority banners.
- Settings scope labels and removal/disablement of stored-but-inactive controls.
- Shared batch-selection interaction where backend actions already exist.

### Phase 3 — decision operating loop

- Portfolio Decision Lab.
- Live Watchtower.
- Scenario Network.
- IC Decision Room.
- Thesis Memory.

### Phase 4 — specialist intelligence and governance

- Covenant & Sponsor Network.
- Coverage Control Plane.
- Per-issuer authorization and entitlement visibility before restricted/Bloomberg data.

## Verification evidence from this session

- Server suite: **1369 passed / 2 skipped** after rerunning sandbox-blocked loopback AV cases with permission.
- AV test file: **8/8 passed** with loopback binding allowed.
- No product code was edited.
- Critique-only static/API servers were stopped cleanly.
- Browser automation could not complete hydrated localhost inspection because the browser safety policy rejected both local preview ports; do not claim visual browser verification from this session.
- Starting the local API during critique applied the existing SQLite migration `0033 → 0034` before shutdown.

## Exact resume sequence

```bash
cd "/Users/ericguei/Claude/Projects/Credit Operating System"
git status --short --branch
git fetch origin
git log --oneline --decorate HEAD..origin/main
```

Then:

1. Read this handoff, the critique snapshot, and inspect the generated wireframe image.
2. Inspect current `ConceptNav`, `SubHeader`, `ResponsiveShell`, analyst settings, Command, Profile, and Query before changing shared contracts.
3. Record the proposal-specific red-team gate.
4. Produce a refreshed, decision-complete implementation plan against the updated tree.
5. Implement Phase 1 first; do not begin with isolated page restyling or a net-new feature screen.

## Non-goals

- Do not replace the CAOS brand or palette.
- Do not add another generic dashboard, chatbot, or report generator.
- Do not create parallel duplicate concepts for PM or QA; role views share underlying data.
- Do not make phone modeling/report authoring a requirement.
- Do not relabel seeded, reference, or fallback output as live.
- Do not use persona selection as an entitlement mechanism.
