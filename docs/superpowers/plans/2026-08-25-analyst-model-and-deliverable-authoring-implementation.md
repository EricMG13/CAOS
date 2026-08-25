# Analyst Model and Deliverable Authoring Implementation Plan

> **Execution contract:** Implement phases consecutively. Re-read each phase’s documentation and run its impact checks before editing. Do not start product implementation until the normalized ledger prerequisite and methodology gates pass.

**Goal:** Restore legacy-grade analyst assumptions, sensitivities, Report Studio authoring, and committee-ready exports on the current immutable CP-MODEL v3 and exact publication foundations.

**Architecture:** An immutable application Model Build remains source authority. A methodology-owned Assumption Registry produces append-only shared Signed-Off Revisions and temporary Scenario Runs. Report Studio stores shared structured draft revisions, freezes exact pathway Deliverables, and serves stored PDF/XLSX bytes only after independent approval.

**Tech stack:** Python 3.11, FastAPI 0.139, Pydantic 2, PostgreSQL/psycopg 3, React 19, Next.js 16, openpyxl, ReportLab 4, pypdf, pytest, TypeScript, axe-core.

**Design authority:**

- `CONTEXT.md`
- `docs/adr/0001-preserve-model-build-authority-with-analyst-revisions.md`
- `docs/adr/0002-use-structured-pathway-deliverables.md`
- `docs/superpowers/specs/2026-08-25-analyst-model-and-deliverable-authoring-design.md`
- `.agent-reviews/redteam.md` section “2026-08-25 — Analyst model and deliverable-authoring architecture gate”

## Global constraints

- Preserve immutable Model Builds, accepted-snapshot authority, Deploy V integrity, exact digests, case authorization, worker-only LibreOffice, and independent report approval.
- Use current CP-MODEL v3 as the only calculation and workbook authority. Do not copy Model Engine v2 or legacy client-side scenario math.
- Never make worksheet/formula cells editable and never calculate financial outputs in React.
- Only registered assumptions are editable. Missing, non-finite, invalid, or unsupported financial values fail closed or degrade to explicit gaps; they never default to zero.
- Unsigned model drafts, Rebase Candidates, Scenario Runs, and sensitivity grids are not persisted.
- Shared Deliverable Drafts are persisted as append-only optimistic revisions.
- Store exact model/revision and Filed Deliverable XLSX/PDF bytes; never rebuild a historical approved artifact with a later renderer.
- Land forward-only migrations. Do not edit migrations `001`–`005` or import the legacy `caos_state` envelope.
- Before editing any function/class/method, run GitNexus upstream impact and report the blast radius. Stop and warn on HIGH/CRITICAL risk.
- Preserve unrelated work, use `apply_patch`, stage explicit paths only, and compare diffs against `origin/main`.

---

## Phase 0: Documentation discovery and allowed APIs

### Objective

Revalidate the exact APIs and patterns this plan is allowed to use. Documentation discovery is a release input, not background reading.

### Read completely

- Current model authority: `docs/superpowers/specs/2026-08-24-deploy-cp-model-design.md`
- Storage prerequisite: `docs/superpowers/plans/2026-08-24-ledger-storage.md`
- Current workbench: `docs/superpowers/specs/2026-08-22-application-workbench-ux-design.md`
- Current model: `caos/server/caos/models/domain.py`, `runtime.py`, `store.py`, `http.py`, `contracts.py`
- Current publishing: `caos/server/caos/publishing/domain.py`, `recipes.py`, `caos/server/caos/artifacts/domain.py`
- Current frontend: `caos/frontend/src/components/Workspace.tsx`, `FiledProof.tsx`, `filedMarkdown.ts`
- Vendored methodology: CP-2G skill/reference/schema plus CP-MODEL `domain.py`, `calculations.py`, `workbook.py`, `builder.py`, and `validate_cp_model_inputs.py`
- Legacy copy references listed below; treat them as interaction/test patterns only

### Allowed current APIs and copy-ready patterns

- `CpModelBundle.validate(..., cp2g: str | None = None)` and `calculate(paths)` in `caos/server/caos/models/domain.py:234-255`
- `ModelReadinessService.queue/_resolve` in `caos/server/caos/models/runtime.py:101-238`
- `ModelBuildRuntime._execute`, `_serialize_worksheet`, and `_publish_export` in `runtime.py:279-345,459-653`
- Exact stored-result validation in `caos/server/caos/store.py:69-278`
- Version/CAS concepts in `store.py:1089-1104` and atomic paired writes in `caos/server/caos/artifacts/domain.py:97-157`
- `model_report_identity`, `report_input_fingerprint`, and `freeze_report` in `caos/server/caos/publishing/domain.py`
- `validate_recipe` in `caos/server/caos/publishing/recipes.py:12`
- Frontend case/generation fencing in `caos/frontend/src/components/Workspace.tsx:880-935,988-1025`
- Legacy stateless preview and stale-result guards in `ModelV2Workbench.tsx:748-818,1039-1075`
- Legacy assumption range/year UI in `AssumptionsPanel.tsx:20-60,156-252`
- Legacy shared serialized autosave in `reports/page.tsx:471-522`
- Legacy structured document types in `builders.ts:39-79` and bounded text editing in `ReportDoc.tsx:15-109`
- Legacy exact frozen preview/publish in `reports.py:373-557,649-835`
- Legacy frozen-only render/verification in `report_exports.py:341-610,907-988`

### Steps

- [ ] Refresh the GitNexus index if its context reports stale commits.
- [ ] Run GitNexus `query` for model authority, model export, report freeze, report approval, and report export flows.
- [ ] Run `context` on `ModelReadinessService`, `ModelBuildRuntime`, `ModelView`, `freeze_report`, `ReportView`, `render_pdf`, and `render_xlsx`.
- [ ] Record impacts before every later edit; do not treat this discovery list as a substitute for symbol impact.
- [ ] Confirm the planned ledger migration `006_normalized_authority` has or has not landed before assigning later migration numbers.
- [ ] Confirm exact installed dependency APIs; do not assume ReportLab is present until Phase 6 adds it.

### Verification

- [ ] A Phase 0 note lists current symbol locations, exact route shapes, migration head, dependency versions, and any drift from this plan.
- [ ] Every intended API call exists in direct source or is explicitly listed as a new contract to implement.

### Anti-pattern guards

- Do not invent methods from memory.
- Do not treat stale GitNexus processes as source authority.
- Do not copy legacy ownership, mutable drafts, arbitrary node overrides, Atlas fixtures, positional edit paths, or browser scenario formulas.

### Exit gate

Implementation starts only when the allowed API list and migration head are verified against the checked-out branch.

---

## Phase 1: Land the normalized ledger prerequisite

### Objective

Complete `docs/superpowers/plans/2026-08-24-ledger-storage.md` through removal of live `caos_state` reads/writes, so high-frequency model/report revisions do not require a second persistence rewrite.

### Files

- Follow the existing ledger plan exactly
- Amend before implementation: `caos/server/caos/ledgers.py`
- Amend contract tests: `caos/tests/test_ledger_contracts.py`

### Interfaces

- `ModelLedger` must remain extensible for append-only model revisions, active-head CAS, and revision exports.
- `PublicationLedger` must remain extensible for draft revisions, Frozen Deliverables, approvals/change requests, and stored exports.
- This phase does not add feature methods speculatively; it prevents protocols from exposing generic mutable buckets.

### Steps

- [ ] Execute the existing ledger plan’s contract, memory adapter, normalized PostgreSQL, caller migration, and envelope-removal tasks.
- [ ] Copy current atomic/fenced behavior into narrow ledger transitions; do not add a generic repository or mega-store protocol.
- [ ] Apply `006_normalized_authority` on a fresh database and prove the old envelope remains inert.
- [ ] Re-run all current model, report, source, run, migration, and PostgreSQL contract tests before this plan adds new tables.

### Verification

```bash
caos/server/.venv/bin/python -m pytest -q caos/tests/test_ledger_contracts.py caos/tests/test_migrate.py caos/tests/test_cp_model.py caos/tests/test_clean_slate.py
rg -n 'caos_state|_merge_state|_persist_connection|_adopt_persisted' caos/server/caos caos/server/worker.py
```

Expected: focused tests pass; no live application path reads or writes `caos_state`.

### Anti-pattern guards

- Do not implement new revision data inside the legacy envelope.
- Do not edit baseline migrations or add dual writes.
- Do not expose `get_bucket`, `save_record`, or other shallow storage APIs.

### Exit gate

Memory and PostgreSQL ledger contract suites pass and normalized storage is the only live authority.

---

## Phase 2: Extend CP-2G and CP-MODEL methodology authority

### Objective

Make the application-built Model Build complete and make every accepted Assumption Registry value calculate and export through one integrity-pinned CP-MODEL path.

### Files

- Modify: `caos/server/caos/methodology/canonical.py`
- Modify: `caos/server/caos/workflows/domain.py`
- Modify: `caos/server/caos/models/domain.py`
- Modify: `caos/server/caos/models/runtime.py`
- Modify CP-2G: `caos/server/caos/methodology/vendor/deploy_v/skills/cp-2g-forward-credit-model/SKILL.md`
- Modify CP-2G references/schema under `.../cp-2g-forward-credit-model/references/`
- Modify CP-MODEL validator/domain/calculation/workbook/builder under `.../cp-model/scripts/`
- Update: `caos/server/caos/methodology/vendor/deploy_v/DEPLOY_V_MANIFEST.json`
- Update: `caos/server/caos/methodology/vendor/deploy_v/DEPLOY_V_INTEGRITY_v1.json`
- Add/modify fixtures under `caos/tests/fixtures/cp_model/`
- Modify: `caos/tests/test_cp_model.py`, `caos/tests/test_clean_slate.py`

### Documentation references

- Copy Base/Downside and exact three-year validation from `validate_cp_model_inputs.py:1561-1653`.
- Copy immutable bundle parsing from `cp_model_v3/domain.py:742-915`.
- Extend the single calculation path in `calculations.py:768-1008`; do not wrap it with host formulas.
- Extend the single workbook path in `workbook.py:1703-2008` and verification path in `builder.py:349-438`.
- Copy canonical module execution/validation patterns for CP-1–CP-2A from `caos/server/caos/methodology/canonical.py`.

### Steps

- [ ] Impact `CANONICAL_MODULES`, `CanonicalModuleRunner`, `CpModelBundle.validate`, `ModelReadinessService._resolve`, CP-MODEL `build_ir`, `calculate`, `_forecast_column`, `render_workbook`, and `build_cp_model`; warn before HIGH/CRITICAL edits.
- [ ] Write failing fixtures for a real canonical CP-2G handoff, full registry definitions, Base/Downside completeness, three years, units, bounds, lineage, and unavailable values.
- [ ] Promote CP-2G from the generic placeholder to the verified canonical runner and make model readiness require its validated handoff for forecast-ready builds.
- [ ] Define the versioned `AssumptionDefinition` registry in the vendored methodology with stable IDs, cases, periods, units, defaults, sensitivity defaults, hard bounds, and affected outputs.
- [ ] Add the accepted operating, cash-flow, rates, capital, and liquidity families. Where an upstream definition is unavailable, return an explicit gap rather than a default.
- [ ] Extend the IR and calculation call to accept one validated effective Assumption Set.
- [ ] Calculate revenue, EBITDA/margin, FCF/cumulative FCF, cash/liquidity/headroom, debt/net debt, leverage, coverage, covenant headroom, and first breach. Guard every CP-1-derived multiply/divide with `is_finite_number` and zero-denominator checks.
- [ ] Define accessible-liquidity, minimum-cash, and covenant test semantics in CP-2G/CP-MODEL references before enabling their registry entries.
- [ ] Extend worksheet formulas, `_INPUTS`, `_MAP`, `_CHECKS`, and `_AUDIT` so independent workbook caches match Python expectations.
- [ ] Update Deploy V manifest/integrity files through the repository’s verified bundle-generation path; never hand-wave a digest mismatch.
- [ ] Bind registry version/digest and calculation contract version into Model Build fingerprints and stored payloads.
- [ ] After a model-ready Full Credit snapshot acceptance commits, trigger the existing idempotent Model Build queue. Queue failure must not roll back acceptance; expose retryable readiness instead.

### Verification

```bash
caos/server/.venv/bin/python -m pytest -q caos/tests/test_cp_model.py caos/tests/test_clean_slate.py -k 'cp2g or forecast or assumption or liquidity or covenant or model'
caos/server/.venv/bin/python run_sec_audit.py
```

- [ ] Application builds contain ready Base/Downside forecast columns for complete fixtures.
- [ ] All registry values round-trip through Python calculation and workbook formulas.
- [ ] Non-finite, out-of-bounds, incomplete, wrong-unit, and unsupported inputs fail closed.
- [ ] Missing covenant/liquidity authority produces named gaps and null outputs.

### Anti-pattern guards

- Do not add only driver IDs; validator, IR, calculation, workbook, QA, and integrity artifacts change together.
- Do not calculate in host code outside the verified methodology.
- Do not treat generic CP-2G Markdown as model data.
- Do not make model readiness depend on a user’s historical visible-snapshot pointer; use latest accepted authority.

### Exit gate

One verified CP-MODEL call produces complete application Base/Downside results and a formula-verified workbook from canonical CP-2G.

---

## Phase 3: Add append-only Analyst Model Revisions and transient calculations

### Objective

Persist only exact signed-off analyst revisions while supporting stateless preview, quarterly rebase, one-way sensitivity, and multi-driver Scenario Runs.

### Files

- Create: `caos/server/migrations/007_model_revisions.sql`
- Extend: `caos/server/caos/ledgers.py`
- Extend memory/PostgreSQL ledger adapters and `caos/tests/test_ledger_contracts.py`
- Create: `caos/server/caos/models/revisions.py`
- Modify: `caos/server/caos/contracts.py`
- Modify: `caos/server/caos/http.py`
- Modify: `caos/server/caos/models/runtime.py`
- Modify: `caos/tests/test_model_store.py`, `caos/tests/test_cp_model.py`, `caos/tests/test_clean_slate.py`

### New records

- `model_revisions`: immutable build/parent/registry/assumption/calculation/output identities, full effective assumptions and result payload, actor, note, timestamps
- `model_revision_heads`: one case-scoped active revision pointer plus current build identity
- `model_revision_exports`: revision, status, vault key, SHA-256, size, renderer identity

### New contracts and routes

```text
GET  /api/cases/{case_id}/models/assumption-registry?build_id=...
POST /api/cases/{case_id}/models/previews
GET  /api/cases/{case_id}/model-revisions
POST /api/cases/{case_id}/model-revisions/sign-off
POST /api/cases/{case_id}/model-revisions/rebase-preview
POST /api/cases/{case_id}/models/scenarios
POST /api/cases/{case_id}/models/sensitivities/one-way
POST /api/cases/{case_id}/model-revisions/{revision_id}/export
GET  /api/cases/{case_id}/model-revisions/{revision_id}/download
```

### Documentation references

- Copy current immutable build public identity from `models/runtime.py:34-56`.
- Copy exact result/digest validation from `store.py:69-278` into the ModelLedger transition.
- Copy the legacy local-edit → preview → exact-hash commit protocol from `ModelV2Workbench.tsx:1039-1075` and `model_v2.py:901-1013`, but insert an immutable revision instead of mutating a draft.
- Copy stale sensitivity request guards from legacy `ModelV2Workbench.tsx:748-818`.
- Copy safe export publication from `models/runtime.py:459-510`.

### Steps

- [ ] Impact every ledger, HTTP, runtime, and contract symbol before editing.
- [ ] Add migration constraints/FKs, unique revision ordering, active-head CAS, and export integrity metadata; migration follows `006` and never changes `model_builds` history.
- [ ] Add strict Pydantic contracts for assumption values, preview, sign-off, rebase, shocks, one-way ranges, and output envelopes. Reuse no prose `AssumptionRequest` type.
- [ ] Implement one shared `ModelRevisionService` that validates registry/build/revision identity and invokes the Phase 2 calculation path for every preview/scenario/sign-off.
- [ ] Bound assumption counts, one-way points, payload size, concurrent calculations, and execution time.
- [ ] Allow any case member to read and run temporary calculations. Require existing case-write authority for Sign-Off and revision export retry.
- [ ] Implement Sign-Off as one ledger transaction: compare current build and expected head, insert immutable revision, advance head, append audit. Return `409` with current revision metadata on conflict.
- [ ] Derive ACTIVE/SUPERSEDED/STALE state at read time.
- [ ] Compute Rebase Candidate compatibility/changed/invalidated groups without persistence.
- [ ] Queue exact revision XLSX immediately after Sign-Off and reuse the existing model export lifecycle. Add visible Assumptions and Revision Record sheets through the single workbook renderer.
- [ ] Ensure export failure does not demote the structured revision.

### Verification

- [ ] Memory and real-PostgreSQL contract tests prove one winning concurrent Sign-Off and no partial insert/head/audit state.
- [ ] Every signed revision can be reopened and reproduces its stored output digest.
- [ ] Unsigned previews, Rebase Candidates, Scenario Runs, and sensitivity points create no durable rows or audit events.
- [ ] A new accepted Model Build makes prior revisions stale and prevents stale sign-off/report use.
- [ ] One-way sensitivity respects registry defaults, adjusted ranges, hard bounds, point cap, and breakpoints.
- [ ] Multi-driver results match direct CP-MODEL calculations.
- [ ] Revision XLSX contains all existing sheets plus Assumptions and Revision Record; hashes and caches verify.

### Anti-pattern guards

- No mutable revision rows or `ACTIVE` flags on history.
- No server draft/autosave endpoint and no `Apply to Draft` endpoint.
- No formula/output overrides.
- No client math or legacy scenario formulas.
- No new generic queue abstraction.

### Exit gate

API and ledger tests prove exact preview/sign-off identity, atomic shared history, quarterly staleness/rebase, temporary sensitivities, and signed workbook fidelity.

---

## Phase 4: Restore Model Builder analyst workflows

### Objective

Add assumption, revision, rebase, and sensitivity workflows around the existing read-only worksheet without turning it into an editable spreadsheet.

### Files

- Create: `caos/frontend/src/components/model/ModelBuilder.tsx`
- Modify: `caos/frontend/src/components/Workspace.tsx`
- Modify: `caos/frontend/app/globals.css`
- Add focused component tests under `caos/frontend/src/components/model/`
- Modify: `caos/frontend/scripts/workbench-smoke.mjs`
- Modify: `caos/frontend/scripts/a11y-axe.mjs`
- Modify: `caos/frontend/scripts/production-inventory.mjs`

### Documentation references

- Copy current worksheet keyboard/lineage behavior from `Workspace.tsx:800-968` unchanged in semantics.
- Copy current case/generation/cache fencing from `Workspace.tsx:880-935`.
- Adapt registry-driven Base/Downside and all-year/year-specific interaction from legacy `AssumptionsPanel.tsx:20-60,156-252`.
- Adapt temporary sensitivity and pending-generation guards from legacy `ModelV2Workbench.tsx:748-818`.
- Follow `DESIGN.md` utility-drawer, Evidence Atlas, focus, status, and editor-overflow contracts.

### Steps

- [ ] Impact `ModelView`, `WorksheetGrid`, shared request helpers, and workspace routing before extraction.
- [ ] Move existing ModelView behavior into `ModelBuilder.tsx` without changing route/API semantics; keep a thin call site in Workspace.
- [ ] Add Model, Assumptions, Sensitivities, and History views with one primary action based on readiness/dirty/preview state.
- [ ] Default to Active Analyst Model when current; keep application Model Build comparison/download explicit.
- [ ] Keep unsigned assumptions only in component/session memory. Warn on case switch, internal navigation, and unload; never use localStorage or server autosave.
- [ ] Require preview before Sign-Off and one non-empty Sign-Off Note. Disable Sign-Off when preview/draft/build/head identity differs.
- [ ] Display CAS conflict with the intervening revision and offer a review/rebase path rather than overwrite.
- [ ] Implement quarterly Rebase Candidate comparison for compatible, changed, and invalidated assumptions.
- [ ] Implement one-way range/table/tornado/breakpoint and multi-driver comparison views from server results.
- [ ] `Apply to Draft` merges values locally only.
- [ ] Preserve keyboard semantics, focus after tab/panel changes, visible status text/glyphs, reduced motion, and narrow horizontal regions.

### Verification

```bash
cd caos/frontend
npm run lint
npx tsc --noEmit
npm run test
npm run build
npm run test:workbench
```

- [ ] Browser fixtures cover Base/Downside edits, broadcast/year edit, preview staleness, failed preview preservation, Sign-Off, conflict, history, stale quarterly revision, rebase, both sensitivity modes, Apply to Draft, roles, case switching, and export.
- [ ] Populated desktop/tablet/mobile axe fixtures report zero violations.

### Anti-pattern guards

- Do not make `WorksheetGrid` editable.
- Do not evaluate or format authoritative calculations in React.
- Do not duplicate the current worksheet/export implementation.
- Do not hide authority, stale state, units, or warnings at narrow widths.

### Exit gate

An analyst can complete the full shared model workflow inside CAOS; a reader can inspect and run temporary scenarios but cannot Sign Off.

---

## Phase 5: Add structured pathway templates and shared Deliverable Drafts

### Objective

Replace the four-field session draft with six server-owned structured templates and one shared optimistic draft per case/pathway.

### Files

- Create: `caos/server/migrations/008_deliverables.sql`
- Extend: `caos/server/caos/ledgers.py` and its memory/PostgreSQL adapters
- Create: `caos/server/caos/publishing/templates.py`
- Modify: `caos/server/caos/publishing/domain.py`
- Modify: `caos/server/caos/contracts.py`
- Modify: `caos/server/caos/http.py`
- Add: `caos/tests/test_deliverables.py`
- Extend: `caos/tests/test_ledger_contracts.py`, `test_clean_slate.py`

### Records

- `deliverable_draft_revisions(case_id, pathway, version, template_id/version, value, digest, author, created_at)`
- `frozen_deliverables(id, case_id, pathway, draft_version, authority/model/template/render identities, value, status, approval fields)`
- `deliverable_exports(deliverable_id, format, vault_key, sha256, size, renderer identity)`

Keep block content/citations inside bounded revision JSON until a demonstrated query requires normalization.

### Routes

```text
GET /api/cases/{case_id}/deliverables/{pathway}
PUT /api/cases/{case_id}/deliverables/{pathway}/draft
GET /api/cases/{case_id}/deliverables/{deliverable_id}
```

Freeze/approval/export routes land in Phase 6.

### Documentation references

- Copy six current pathway IDs from `contracts.py:PATHWAYS`.
- Adapt the small legacy structured-section union from `builders.ts:39-79`, adding stable block IDs, content mode, citations, and slot constraints.
- Copy optimistic append behavior from `store.py:1089-1104` into `PublicationLedger` SQL/memory transitions.
- Copy legacy serialized autosave generation guards from `reports/page.tsx:471-522`.
- Copy case-scoped/withdrawn evidence validation from `artifacts/domain.py:23-39`.
- Reuse `validate_recipe` for generated visual recipes.

### Steps

- [ ] Impact `PATHWAYS`, thesis/recommendation versioning, `PublicationLedger`, report routes, and evidence validation.
- [ ] Add forward-only tables and PostgreSQL CAS insert using `(case_id, pathway, expected_version)`; never use generic whole-state merge.
- [ ] Define stable, versioned templates and required sections exactly as the design spec. Derive default pathway from accepted run authority.
- [ ] Encode each template’s model requirement: required for Full Credit, Earnings Update, Covenant & Refinancing, and Distressed & Restructuring; optional for Relative Value and Deep Research.
- [ ] Define strict canonical block types: heading, narrative, generated metric/table/chart, Scenario Exhibit, evidence register, model appendix, limitations.
- [ ] Generate calculated blocks server-side and reject client-supplied generated values.
- [ ] Require stable block IDs and permitted order slots. Reject positional edit paths and invalid omission/reorder.
- [ ] Validate Narrative Block bounds plus Evidence Citation or `ANALYST JUDGMENT` for material claims.
- [ ] Implement full-draft optimistic replacement and actor-attributed history. Conflict returns current version/content digest.
- [ ] Restore historical content by writing a new revision; add no restore endpoint.
- [ ] Add model eligibility data to draft reads: Active Analyst Model first, application Model Build fallback with required acknowledgement, stale revisions rejected.
- [ ] Allow a Scenario Run response to be copied into a reproducible Scenario Exhibit with exact identities/digest.

### Verification

- [ ] Six templates validate required/optional sections, ordering, blocks, and appendices.
- [ ] Two-writer draft race has one winner and a recoverable conflict.
- [ ] Generated Block mutation, invalid evidence, withdrawn evidence, cross-case IDs, stale model, and unacknowledged fallback fail closed.
- [ ] History is append-only and actor-attributed in memory and PostgreSQL.

### Anti-pattern guards

- Do not use Markdown as canonical document state.
- Do not add arbitrary HTML, rich-text layout, or client-calculated tables.
- Do not keep one report per case or overwrite frozen/filed history.
- Do not create one table per block/citation without a query requirement.

### Exit gate

API and ledger tests prove collaborative structured drafts, six pathway contracts, evidence governance, model selection, and Scenario Exhibit identity.

---

## Phase 6: Materialize exact Frozen and Filed Deliverables

### Objective

Replace current PDF/XLSX stubs with substantive, stored, verified artifacts while preserving exact preview and independent approval.

### Files

- Modify: `caos/server/requirements.txt`
- Add: `reportlab>=4,<5`
- Create: `caos/server/caos/publishing/renderers.py`
- Modify: `caos/server/caos/publishing/domain.py`
- Modify: `caos/server/caos/http.py`
- Add/modify: `caos/tests/test_deliverable_exports.py`, `test_clean_slate.py`, `test_migrate.py`

### Routes

```text
POST /api/cases/{case_id}/deliverables/{pathway}/freeze
POST /api/cases/{case_id}/deliverables/{deliverable_id}/approve
POST /api/cases/{case_id}/deliverables/{deliverable_id}/request-changes
GET  /api/cases/{case_id}/deliverables/{deliverable_id}/export/{md|pdf|xlsx}
```

### Documentation references

- Copy exact content/input fingerprint patterns from current `publishing/domain.py:11-139`.
- Copy approval-time identity recomputation from `http.py:600-646`.
- Copy safe atomic hash-addressed publication from `models/runtime.py:459-510`; extract only the smallest shared file-publication helper if two consumers genuinely need it.
- Adapt legacy formula-injection guards and workbook verification from `report_exports.py:48-68,341-610`.
- Adapt legacy ReportLab rendering and frozen-only boundary from `report_exports.py:907-988`.
- Copy semantic export assertions from legacy `test_report_exports.py:246-478`.

### Steps

- [ ] Impact `freeze_report`, `model_report_identity`, `report_input_fingerprint`, `approve`, `render_pdf`, `render_xlsx`, and `_publish_export`; warn on HIGH/CRITICAL impact.
- [ ] Add ReportLab 4 to runtime requirements and validate the dependency/transitive set in a clean Python 3.11 environment.
- [ ] Implement template-aware PDF and XLSX renderers that accept only one immutable canonical Frozen Deliverable payload and never query mutable state.
- [ ] PDF must render pathway sections, narrative, tables, citations, freshness/authority, Base/Downside data, limitations, and selected appendices using the paper design contract.
- [ ] XLSX must render the relevant Cover, Reviewed Deliverable, analytical, scenario, assumptions/model/debt, gaps/warnings, evidence, and revision sheets with typed values and injection protection.
- [ ] Freeze validates exact draft version/digest, current accepted authority, eligible model, citations, generated blocks, Scenario Exhibits, and template version.
- [ ] Materialize canonical JSON/Markdown/PDF/XLSX, verify them, publish bytes atomically to the vault, and persist renderer/version/hash/size before returning a Frozen Deliverable.
- [ ] Preserve current distinct approver/admin role. `approve` files the exact version; `request-changes` requires a comment and creates a new draft revision from frozen content without deleting the frozen record.
- [ ] Serve stored bytes only after filing, rechecking case, path containment, size, and SHA-256. Never rerender at download.
- [ ] Backfill any normalized legacy report row as a read-only legacy Frozen/Filed Deliverable when possible; do not import `caos_state` or mutate the original row.
- [ ] Keep old report endpoints only as a bounded compatibility read during frontend cutover; remove new writes through them once Phase 7 passes.

### Verification

```bash
caos/server/.venv/bin/python -m pytest -q caos/tests/test_deliverables.py caos/tests/test_deliverable_exports.py caos/tests/test_clean_slate.py caos/tests/test_migrate.py
```

- [ ] Reopen each XLSX with openpyxl and assert required sheets, typed financial values, narrative, model/revision identity, evidence, limitations, and no untrusted formulas.
- [ ] Reopen each PDF with pypdf and assert pathway title, narrative, analytical tables/values, identities, limitations, and representative multi-page output.
- [ ] Stored bytes match persisted size/SHA-256 and remain identical after process restart or later renderer changes.
- [ ] Approval fails after any draft/model/evidence/template/fingerprint mismatch.
- [ ] Historical frozen/filed versions remain downloadable after later drafts and filings.

### Anti-pattern guards

- No magic-byte-only export tests.
- No download-time rendering.
- No browser print as authoritative PDF.
- No unescaped narrative in XLSX formula positions.
- No approval of a separately reconstructed preview.

### Exit gate

All six representative pathway fixtures produce substantive, immutable, verified PDF/XLSX artifacts and exact approval/history behavior.

---

## Phase 7: Restore Report Studio authoring and exact review

### Objective

Replace the four-field ReportView with collaborative structured composition, paper preview, version history, exact approval, and filed downloads.

### Files

- Create: `caos/frontend/src/components/report/ReportStudio.tsx`
- Create: `caos/frontend/src/components/report/DeliverableDocument.tsx`
- Modify: `caos/frontend/src/components/Workspace.tsx`
- Modify: `caos/frontend/app/globals.css`
- Modify: `caos/frontend/scripts/workbench-smoke.mjs`
- Modify: `caos/frontend/scripts/a11y-axe.mjs`
- Modify: `caos/frontend/scripts/production-inventory.mjs`
- Add focused frontend tests under `caos/frontend/src/components/report/`

### Documentation references

- Copy current ReportView case abort/generation fencing, evidence fault isolation, model consent, and approver gating from `Workspace.tsx:977-1110`.
- Adapt legacy serialized autosave and accurate save-state messaging from `reports/page.tsx:471-522`.
- Adapt bounded plain-text inline editing and typed rendering from `ReportDoc.tsx:15-263`.
- Adapt legacy exact frozen-preview flow from `reports/page.tsx:753-840`; retain current approval terminology.
- Preserve safe React output: no `dangerouslySetInnerHTML` and no general Markdown/HTML editor.

### Steps

- [ ] Impact `ReportView`, `FiledProof`, request helpers, evidence picker, and workspace routing.
- [ ] Extract current behavior into `ReportStudio.tsx`, preserving load/error/case-switch/role gates before adding functionality.
- [ ] Render a three-region workbench: section/composition rail, structured editor, and light paper preview with contextual evidence inspector.
- [ ] Derive the Pathway Template from current accepted authority and show required/optional sections and appendices.
- [ ] Implement bounded Narrative Block editing, stable reorder/omit controls, citation picker, analyst-judgment label, Generated Block read-only state, and Scenario Exhibit insertion.
- [ ] Implement 850ms serialized autosave with `Saving`, `Saved vN`, and `Conflict` states; never let an older request claim a newer generation was saved.
- [ ] Show revision/frozen/filed history and restore by writing a new draft revision.
- [ ] Default current Active Analyst Model, reject stale revisions, and require explicit application-build fallback acknowledgement.
- [ ] Freeze only an exact saved draft version; replace the editable preview with the exact Frozen Deliverable review surface.
- [ ] Gate approve/request-changes by role and exact preview identity. Restore focus and announce state transitions.
- [ ] Download stored Filed bytes and expose all historical Filed versions.
- [ ] Remove sessionStorage and the old hard-coded empty arrays/rationale only after routed fixtures prove migration/cutover.

### Verification

```bash
cd caos/frontend
npm run lint
npx tsc --noEmit
npm run test
npm run build
npm run test:workbench
```

- [ ] Browser journeys cover all six templates, autosave/reload, two-writer conflict, section validation, citations/judgment, generated-block protection, model fallback/stale rejection, Scenario Exhibit, exact freeze, change request, approval, filed history/download, case switch, narrow layouts, keyboard use, and reduced motion.
- [ ] Combined-app populated Report Studio axe fixtures report zero violations.

### Anti-pattern guards

- Do not turn `filedMarkdown.ts` into a general editor.
- Do not duplicate generated data in editable text fields.
- Do not make paper preview and Frozen preview separate calculation paths.
- Do not hide save/conflict/authority state at narrow widths.

### Exit gate

An analyst can collaboratively author, freeze, revise, and file each pathway Deliverable without leaving CAOS, and the downloaded bytes match the reviewed identity.

---

## Phase 8: Migration, production verification, and closeout

### Objective

Prove the complete workflow against memory, real PostgreSQL, combined production-like frontend/API, stored exports, and adversarial review.

### Steps

- [ ] Run migration `006` → `007` → `008` on a clean PostgreSQL database and a restored representative normalized database. Verify idempotence, FKs, constraints, rollback, and inert old tables.
- [ ] Run two-connection races for active model Sign-Off and Deliverable autosave/freeze/approval.
- [ ] Create a deterministic populated case with accepted Full Credit + CP-2G, one Signed-Off Revision, sensitivities, and all six Deliverable fixtures.
- [ ] Build the static frontend and serve it through FastAPI; run production inventory and the mandated axe runner with `CAOS_CASE_ID`.
- [ ] Verify model/revision and every Filed PDF/XLSX path, size, hash, content, and identity after restart/restore.
- [ ] Run dependency review in a fresh Python 3.11 environment and confirm FastAPI remains `0.139.*`.
- [ ] Run full server/frontend/security gates.
- [ ] Run `rewrite-tournament` in post-edit mode on changed non-trivial functions.
- [ ] Run `confidence-review`; investigate every uncertainty to root cause and patch confirmed issues.
- [ ] Run GitNexus `detect_changes(scope="compare", base_ref="origin/main")`; investigate unexpected symbols or flows.
- [ ] Append a new dated implementation-verification section to `.agent-reviews/redteam.md`; never edit this plan’s existing architecture gate.

### Verification commands

```bash
caos/server/.venv/bin/python -m pytest -q caos/tests
caos/server/.venv/bin/python run_sec_audit.py
cd caos/frontend && npm run lint && npx tsc --noEmit && npm run test && npm run build && npm run test:workbench
```

Then run `caos/scripts/build_frontend.sh`, the combined FastAPI app, `node caos/frontend/scripts/a11y-axe.mjs`, and `node caos/frontend/scripts/production-inventory.mjs` with the documented populated-case environment.

### Final anti-pattern grep

```bash
rg -n 'dangerouslySetInnerHTML|reports\[case_id\] =|sessionStorage.*report|calculate.*(ts|tsx)|editable.*WorksheetGrid|caos_state' caos/frontend caos/server/caos
```

Investigate matches; allow only documented safe/compatibility occurrences.

### Exit gate

- Full non-environment-gated server and frontend suites pass.
- Real-PostgreSQL concurrency/migration tests pass when configured.
- Populated Model Builder and Report Studio axe runs are clean.
- Signed model and Filed Deliverable bytes are semantically verified and hash-stable.
- No unexpected GitNexus impact remains.
- Red-team and confidence gates accept the implementation.

## Deliberately deferred

- Direct workbook import into Model Builder
- Persistent named/upside cases
- Arbitrary cell/formula/calculated-output overrides
- Per-assumption rationale requirements
- Server-persisted unsigned model drafts
- Model branches/forks per analyst
- A general rich-text/WYSIWYG editor
- Legacy standalone monitoring, trade-ticket, evidence-control, or model-appendix report types
- Browser-authoritative PDF or client-side financial calculations

Add any deferred item only after a demonstrated workflow requires it and a new authority/security review accepts the expanded boundary.
