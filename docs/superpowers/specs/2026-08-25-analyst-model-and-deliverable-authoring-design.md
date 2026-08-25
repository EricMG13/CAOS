---
meta:
  title: Restore analyst model and deliverable authorship
  navLabel: Analyst Model and Deliverables
  category: Architecture decisions
  contentType: Conceptual
---

# Restore analyst model and deliverable authorship

This design restores the analyst-controlled model assumptions, sensitivities, report composition, and filed-document quality present in legacy CAOS while preserving the current application’s stronger CP-MODEL v3 authority, lineage, QA, case isolation, and exact publication identity.

## Content plan

- **Goal**: let an analyst form, explain, share, and publish a house credit view without leaving CAOS
- **Audience**: buy-side analysts, PM/CIO reviewers, methodology owners, QA, and implementers
- **Outcome**: one immutable application Model Build can support recoverable signed-off analyst revisions, temporary sensitivities, six structured pathway Deliverables, and substantive filed PDF/XLSX output
- **Scope**: methodology contracts, model revisions, quarterly rebase, sensitivities, workbook output, report drafts, structured templates, evidence, freeze/approval, exports, migration, and verification
- **Non-goals**: legacy Model Engine v2, arbitrary cell/formula editing, browser calculations, direct workbook import into Model Builder, persistent custom scenario cases, a free-form word processor, or all nine legacy report archetypes

## Confirmed product decisions

1. CAOS builds and retains its own immutable Model Build.
2. Analysts change registered assumptions, never formulas or calculated outputs.
3. Every self-released change creates a recoverable Analyst Model Revision.
4. The working model is shared per case. Only signed-off revisions are retained; unsigned model work is temporary and author-only.
5. Sign-Off is self-release by an authorized case writer and is distinct from report approval.
6. One Sign-Off Note explains the entire revision; individual assumption notes are not required.
7. The latest Signed-Off Revision anchored to the current Model Build is the Active Analyst Model.
8. A new accepted Model Build makes the prior revision stale. Compatible assumptions may be carried into a temporary Rebase Candidate, but require a new Sign-Off.
9. Stored forecast cases are Base and Downside only.
10. The Assumption Registry covers the full accepted driver set, with analyst-adjustable sensitivity ranges inside methodology-owned guardrails.
11. One-way sensitivities and multi-driver Scenario Runs are both temporary.
12. Scenario values enter model history only through Apply to Draft followed by Sign-Off.
13. Signed-off model XLSX files include visible Assumptions and Revision Record sheets.
14. Report Studio produces six pathway Deliverables using structured templates, not a free-form editor.
15. Deliverable Drafts are shared, server-autosaved, revisioned, and actor-attributed.
16. New Deliverables default to the current Active Analyst Model, reject stale revisions, and require explicit acknowledgement when falling back to the application Model Build.
17. Frozen Deliverables bind exact model, source, evidence, scenario, template, renderer, and content identities. Independent approval remains required before filing.

The canonical language is maintained in `CONTEXT.md`. Architectural rationale is recorded in ADR-0001 and ADR-0002.

## Existing authority to preserve

The current implementation already has the correct foundation:

- `ModelReadinessService` resolves one accepted Full Credit authority and creates immutable, fingerprinted Model Builds.
- `ModelBuildRuntime` stores bounded structured worksheet output and a canonical payload digest.
- The browser renders server-calculated worksheet cells and never evaluates formulas.
- Optional XLSX export has a lifecycle separate from structured-model readiness.
- `model_report_identity`, report input fingerprints, exact preview digests, case-scoped authorization, and independent report approval provide strong publication controls.
- Current workbook output has three visible sheets and four hidden control/audit sheets generated from one CP-MODEL calculation.

These boundaries are extended, not replaced.

## Methodology authority and the Assumption Registry

### Current gap

The host does not currently supply CP-2G to CP-MODEL. The vendored bundle accepts an optional CP-2G handoff, but its stable driver table contains only segment growth, acquisitions/disposals, equity issuance/repurchase, dividends, and other investing/financing. The calculation engine rolls many forecast values from pro-forma ratios, fixes debt, and has no assumption-overlay argument.

The UI must not precede the methodology. A field is editable only after the integrity-pinned CP-2G/CP-MODEL contract defines and validates it.

### Required registry families

The methodology-owned registry must support, where applicable:

- Segment and consolidated revenue growth
- EBITDA margin and identified add-backs
- Capex, working capital, cash taxes, and lease cash flows
- Base rates, instrument spreads/coupons, and cash interest
- Contractual amortization, debt issuance/repayment, and refinancing
- Minimum operating cash and accessible liquidity
- Acquisitions/disposals, equity issuance/repurchase, dividends, and other investing/financing

Each `AssumptionDefinition` declares:

- Stable assumption ID and label
- Driver family and description
- Value type and canonical unit
- Applicable Base/Downside cases
- Applicable forecast periods and instrument/segment slot, when relevant
- Default value source and lineage rule
- Default sensitivity range and step
- Hard minimum and maximum
- Required upstream authority and degradation behavior
- Affected output IDs
- Registry version and digest

Calculated outputs, formula cells, historical actuals, and accepted-source values are never registry assumptions. Missing liquidity or covenant definitions return `null` with a named gap; they never become zero.

### Forecast shape

Every revision contains a complete Base and Downside assumption set for exactly the three CP-2G forecast years. The UI may broadcast a value across all three years, but the signed request always contains explicit period values.

## Analyst Model Revision lifecycle

### Preview

Unsigned assumption work remains in the author’s browser session. A preview request sends the complete effective Base/Downside assumption set to the server. The server validates the registry version, bounds, finite values, build identity, and complete periods, then calculates through CP-MODEL and returns:

- Model Build and accepted-snapshot identity
- Registry/methodology/runtime versions and digests
- Assumption digest
- Calculation/output digest
- Annual decision outputs
- Changed-output deltas versus the application Model Build or parent revision
- Warnings, gaps, and invalid assumptions

Late preview results are discarded when the case, Model Build, parent revision, or local draft generation changes.

### Sign-Off

Sign-Off submits the exact preview digest, complete assumptions, required Sign-Off Note, parent Model Build, and expected active revision. The server recalculates and atomically:

1. Revalidates current accepted authority and registry version.
2. Rejects stale Model Builds or a changed active revision with `409` and the intervening delta.
3. Inserts one immutable Analyst Model Revision containing the full calculation envelope.
4. Advances the case’s active revision head.
5. Writes an actor-attributed audit event.
6. Queues exact XLSX publication for that revision.

There is no server draft, mutable revision row, or direct `Apply to Draft` endpoint.

### Revision states

- **ACTIVE**: latest Signed-Off Revision on the current Model Build
- **SUPERSEDED**: older Signed-Off Revision on the current Model Build
- **STALE**: Signed-Off Revision anchored to a non-current Model Build

State is derived from the current Model Build and active head rather than stored as mutable flags on historical revisions.

### Quarterly refresh

Accepting a model-ready Full Credit snapshot triggers a new idempotent Model Build after snapshot acceptance commits. A model-queue failure never rolls back the accepted snapshot; readiness exposes the failure and permits retry. Any prior Active Analyst Model immediately becomes stale for new analysis and publication.

CAOS computes a Rebase Candidate on demand:

- **Compatible** assumptions map unchanged to the new registry/build.
- **Changed** assumptions map but their default/source context changed.
- **Invalidated** assumptions no longer map or violate new guardrails.

The review compares new actuals, carried assumptions, invalidations, and output deltas. No rebase is stored or activated until Sign-Off.

## Sensitivities and Scenario Runs

### One-way sensitivity

The analyst chooses one assumption, case, period or all-year scope, and range. The registry supplies the default range and step; the analyst may adjust both within hard bounds. The server caps the number of points and returns sorted values, output deltas, and first Breakpoint.

### Multi-driver Scenario Run

The analyst changes multiple registered assumptions in one temporary request and receives Base, Downside, scenario, and delta results.

Both modes:

- Reuse the same server-side CP-MODEL calculation path as previews and Sign-Off.
- Never create shared model history.
- Bind to exact Model Build, optional base revision, registry, and methodology identities.
- Return no result after a case/build/draft generation becomes stale.
- May be copied into the browser Draft Revision through Apply to Draft.
- May be captured as a reproducible Scenario Exhibit in a Deliverable Draft without becoming model history.

Authorized case readers may run temporary scenarios; only case writers may Sign Off revisions or edit shared Deliverables.

### Mandatory annual decision outputs

- Revenue
- Adjusted EBITDA and EBITDA margin
- FCF and cumulative FCF
- Ending cash, accessible liquidity, and Liquidity Headroom
- Total debt and net debt
- Total leverage and net leverage
- Interest coverage
- Covenant Headroom
- First breached threshold and breach period

The methodology must define accessible liquidity, minimum cash, covenant source/test/threshold, and degradation behavior before those outputs can be `READY`.

## Model Builder experience

Model Builder retains the read-only worksheet and adds a separate authoring surface. Its dominant work region has:

1. **Model** — current Active Analyst Model by default, with explicit comparison to the application Model Build.
2. **Assumptions** — registry-driven Base/Downside editor with periods, units, guardrails, dirty state, and preview deltas.
3. **Sensitivities** — one-way and multi-driver temporary calculations with breakpoint and tornado/comparison views.
4. **History** — application builds and recoverable Signed-Off Revisions, including actor, time, note, parent, state, and exact identity.

The page shows one primary action appropriate to state: Build Model, Preview Changes, or Sign Off Revision. Export and comparison controls remain utilities. Unsigned changes warn on case switch, internal navigation, and unload.

## Signed-off model workbook

The existing CP-MODEL workbook renderer remains the only workbook implementation. A revision render context adds:

- **Assumptions**: Base/Downside values, periods, units, guardrails, source/default values, and deltas from the application Model Build.
- **Revision Record**: revision ID, parent Model Build, parent revision, author, sign-off time, Sign-Off Note, registry/methodology/runtime versions, and all relevant digests.

Existing Credit Snapshot, Model, KPIs, `_INPUTS`, `_MAP`, `_CHECKS`, and `_AUDIT` sheets remain. Formula/cache verification and semantic checks cover the new inputs and outputs. XLSX publication is nested under the signed revision; export failure never demotes the structured revision.

## Structured Deliverables

### Pathway templates

| Pathway | Deliverable | Required core sections |
|---|---|---|
| Full Credit | Investment Committee Credit Memo | Credit Snapshot; recommendation; thesis/variant view; business and industry; capital structure; Base/Downside model; liquidity/covenants; risks/catalysts/falsifiers; monitoring |
| Earnings Update | Earnings Update | Credit Snapshot; what changed; reported-versus-prior bridge; model impact; leverage/liquidity; thesis and recommendation impact; risks/catalysts/monitoring |
| Covenant & Refinancing | Covenant and Refinancing Brief | Credit Snapshot; capital structure/maturity wall; covenant definitions/headroom; liquidity; refinancing options; Base/Downside breakpoints; actions/monitoring |
| Relative Value | Relative Value Note | Credit Snapshot; instrument comparison; structure/seniority; relative compensation; catalysts/risks; recommendation and trade gates; market freshness |
| Distressed & Restructuring | Scenario and Recovery Pack | Credit Snapshot; capital structure/priority; liquidity runway; Base/Downside and Scenario Exhibits; recovery; covenant/default/refinancing milestones; catalysts/process risks; recommendation |
| Deep Research | Evidence-Bound Research Memorandum | Research question/scope; executive findings; evidence synthesis; counterevidence/gaps; implications for thesis/model/recommendation; unresolved questions |

Evidence Register is required for every Deliverable. Model, Scenario, and detailed evidence appendices are reusable and included when relevant rather than exposed as separate report types.

Each server-owned Pathway Template has a stable template ID/version, stable block IDs, required/optional sections, permitted order slots, allowed appendices, Generated Block builders, and freeze validation.

### Canonical block model

The structured document JSON is canonical; Markdown is an export, not the domain model.

Allowed block kinds are:

- Heading
- Narrative
- Generated metric
- Generated table
- Generated chart recipe
- Scenario Exhibit
- Evidence Register
- Model Appendix
- Limitations

Generated Blocks are rebuilt and validated server-side. The client may not submit calculated values. Narrative Blocks support bounded plain text and structured citations, not arbitrary HTML or layout.

Every material Narrative Block claim must carry an Evidence Citation or explicit `ANALYST JUDGMENT`. Withdrawn or cross-case evidence is rejected. Stable block IDs survive reordering and template upgrades; positional edit paths are prohibited.

## Deliverable Draft lifecycle

One shared Deliverable Draft exists per case and pathway. It is server-autosaved as append-only, actor-attributed revisions using optimistic `expected_version` comparison.

- Autosave sends the complete structured draft after a short debounce.
- Concurrent conflicts return the current version and a stable conflict code; clients never claim a stale save succeeded.
- Restoring history creates a new revision from old content rather than mutating history.
- Generated Blocks are regenerated from current authority during validation.
- Draft status is visibly distinct from Frozen and Filed content.

## Model and scenario identity in Deliverables

New Deliverables use the current Active Analyst Model by default. A Stale Revision is never eligible. If no current Signed-Off Revision exists, the author may select the application Model Build only after an acknowledgement stored in the draft and frozen version.

Full Credit, Earnings Update, Covenant & Refinancing, and Distressed & Restructuring require an eligible model before Freeze. Relative Value and Deep Research treat the model as optional; when omitted, the Frozen Deliverable records that no model was included and omits model-dependent Generated Blocks.

A Scenario Exhibit captures exact shock inputs, outputs, registry/methodology/runtime identities, base model/revision, and calculation digest. Capturing an exhibit does not create a model revision.

## Freeze, approval, changes, and filing

Freeze validates the exact draft version, pathway/template, current accepted authority, model eligibility, citations, required blocks, generated content, and Scenario Exhibits. It materializes an immutable Frozen Deliverable containing:

- Ordered structured blocks and canonical digest
- Exact accepted snapshot/source-set identity
- Exact model/revision and optional model-XLSX identity
- Exact evidence and withdrawn-state checks
- Exact Scenario Exhibits
- Template, methodology, and renderer versions/digests
- PDF, XLSX, and Markdown bytes with SHA-256 and size
- Preview digest and input fingerprint

An `APPROVER` or `ADMIN` approves only that exact Frozen Deliverable. They may instead request changes with a required comment; this creates a new editable draft revision while preserving the rejected Frozen Deliverable. Approval changes status to Filed and never rerenders output.

Later drafts, models, templates, or deployments cannot mutate a Filed Deliverable. A subsequent filing supersedes it without deleting prior versions.

## Filed exports

### PDF

PDF is a print-ready, multi-page paper document. It contains the selected pathway sections, narrative, analytical tables, citations/footnotes, authority/freshness, Base/Downside results where relevant, evidence/limitations, and model/scenario appendices. It uses the Report Studio paper design contract and never browser print as the authoritative renderer.

### XLSX

XLSX contains only relevant sheets, drawn from:

- Cover
- Reviewed Deliverable
- Section/Module Summary
- Analytical detail sheets
- Base/Downside and Scenario Analysis
- Assumptions
- Model
- Debt Schedule
- Model/QA Gaps and Warnings
- Evidence Register / Sources-Audit
- Revision Record

Cells beginning with spreadsheet formula markers are neutralized unless they are trusted formulas emitted by the model workbook renderer. Tests reopen exports and verify typed values, sheet contracts, identity, and substantive content.

### Markdown and JSON

Markdown remains a compatible, human-readable export. Canonical structured JSON remains available through the exact Deliverable API for QA and integrations; it is not exposed as an authoring escape hatch.

Exports are materialized at Freeze, stored atomically in the governed vault, and served only after filing. Download verifies path containment, size, and SHA-256. Approved exports are never regenerated with a later renderer.

## Persistence and concurrency

The normalized ledger foundation in `docs/superpowers/plans/2026-08-24-ledger-storage.md` lands first. Analyst revisions extend `ModelLedger`; Deliverable drafts/versions/exports extend `PublicationLedger`. New migrations are forward-only and follow the ledger plan’s `006_normalized_authority` migration.

Required normalized records are:

- `model_revisions`
- `model_revision_heads`
- `model_revision_exports`
- `deliverable_draft_revisions`
- `frozen_deliverables`
- `deliverable_exports`

Sign-Off atomically compares build and active-head identity, inserts the revision, advances the head, and appends audit. Draft autosave atomically compares `(case, pathway, expected_version)` and inserts the next revision. Freeze never replaces prior Frozen or Filed versions.

The existing single `reports[case_id]` shape becomes read-only compatibility input during migration and is never the new authority.

## Security, resilience, and accessibility

- Case membership gates every read and calculation. Existing writer roles gate Sign-Off and Deliverable edits; `READER` may view and run non-persistent sensitivities.
- Assumption values are finite, bounded, typed, and unit-checked. No missing financial input becomes zero.
- Scenario and preview requests have bounded assumptions/points, calculation concurrency, payload size, and execution time.
- Draft narrative and evidence references are bounded and treated as untrusted data.
- XLSX formula injection, path traversal, stale identity, duplicate requests, cross-case IDs, and tampered export bytes fail closed.
- Every asynchronous frontend result is fenced by case, build/revision/draft identity, and generation.
- Assumption grids, scenario controls, section composition, citations, preview, conflicts, and history are fully keyboard-operable with visible focus and semantic labels.
- Status and deltas never rely on color alone. Reduced motion remains honored.

## Migration and compatibility

1. Land the normalized ledger plan first and extend its protocols before adapter implementation hardens.
2. Add analyst revision tables without modifying Model Build records or migration `002`.
3. Add Deliverable tables without modifying baseline migration `001`.
4. Backfill each existing current report as one immutable legacy Frozen/Filed Deliverable where its status and content permit; retain the original row for rollback/read compatibility.
5. Dual-read during a bounded cutover; all new writes use normalized revisions only.
6. Remove old frontend report writes only after the new API and migration restore tests pass.

## Acceptance criteria

### Model Builder

- A writer can edit all registry assumptions for Base/Downside, preview exact deltas, and self-release one recoverable Signed-Off Revision with one note.
- A reader sees the same Active Analyst Model but cannot sign off.
- Two writers cannot overwrite each other; stale sign-off returns a recoverable conflict.
- A new accepted quarterly Model Build makes the old revision stale and produces a reviewable, non-persistent Rebase Candidate.
- One-way and multi-driver sensitivities are temporary, bounded, methodology-calculated, and stale-request safe.
- Required annual decision outputs and breakpoints are exact or explicitly unavailable with gaps.
- Signed-off XLSX contains the full existing workbook plus Assumptions and Revision Record, and passes formula/cache/semantic verification.

### Report Studio

- Each pathway produces its defined structured Deliverable with required sections and appendices.
- Shared draft autosave, revision history, conflict recovery, stable block editing, citations, and analyst-judgment labeling work across writers.
- Generated Blocks cannot be client-mutated.
- Freeze rejects stale models, invalid evidence, missing required blocks, and mismatched preview identity.
- Approval or change request applies to one immutable Frozen Deliverable.
- Filed PDF/XLSX are substantive, stored bytes whose hashes match the exact previewed version.
- Historical Frozen/Filed versions remain viewable and downloadable after later work.

### Verification

- Unit and contract tests cover methodology registry/calculations, finite/bounds validation, CAS, staleness, rebase, scenarios, templates, citations, freeze, approval, export, and migration.
- PDF tests extract substantive text and verify representative multi-page output.
- XLSX tests reopen every required sheet and verify typed analytical values, audit content, and formula-injection handling.
- Browser journeys cover quarterly rebase, draft loss warning, sign-off conflict, sensitivity staleness, shared report autosave/conflict, exact preview, change request, approval, case switching, narrow widths, and keyboard use.
- Combined-app axe runs report zero violations on populated Model Builder and Report Studio fixtures.
