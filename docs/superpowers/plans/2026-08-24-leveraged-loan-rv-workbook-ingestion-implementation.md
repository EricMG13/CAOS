# Implement leveraged-loan RV workbook ingestion

This plan implements `docs/superpowers/specs/2026-08-24-leveraged-loan-rv-workbook-ingestion-design.md`. Completion means an analyst can upload the fixed CP-3 XLSX, activate every valid visible sector table atomically, screen the source-reported loan metrics, and bind the same universe identity into CP-3 lineage.

## Phase 0: Use verified repository APIs

### Allowed APIs

- `POST /api/cases/{case_id}/sources` and `ingest_upload(...)` for authenticated scanning, archive checks, hashing, evidence extraction, and vault persistence
- `MemoryStore.lock`, `persist()`, `_id(...)`, and `audit_event(...)` for local atomic state
- `PostgresStore._snapshot()`, `_persist_connection(...)`, `_restore(...)`, and `_sync_normalized_runs(...)` for durable state-envelope and normalized-table parity
- Sorted migrations through `apply_migrations(...)`
- `openpyxl.load_workbook(..., read_only=True, data_only=True, keep_links=False)` from the existing server requirement
- Frontend `request<T>(...)`, native file inputs, `LoadState`, existing table styles, and case-scoped source links
- Workflow `WorkflowRuntime._build_artifact(...)` and its host-owned `input_fingerprint`, `lineage`, and `provenance` payload fields

### References

- `caos/server/caos/sources/domain.py`
- `caos/server/caos/store.py`
- `caos/server/caos/http.py`
- `caos/server/caos/workflows/domain.py`
- `caos/frontend/src/components/Workspace.tsx`
- `caos/frontend/app/globals.css`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-3-relative-value-security-selection/SKILL.md`

### Anti-pattern guards

- Do not reparse the workbook in the browser or CP-3
- Do not add a queue, service, parser package, flexible mapper, bond fields, or recommendation signal
- Do not execute formulas, follow external links, accept paths from requests, or partially activate a workbook
- Do not replace or relabel legacy generic RV records
- Do not sync 25,000 normalized rows on unrelated persistence writes

## Phase 1: Add the bounded workbook parser

### Files

- Add `caos/server/caos/artifacts/loan_universe.py`
- Add `caos/tests/test_loan_universe.py`

### Implementation

1. Define the exact 25-column template and explicit field/unit mapping
2. Reject macro, external-link, embedded-object, malformed, oversized, or over-limit packages
3. Find tables by exact ordered headers, detect partial signatures, and import all visible sector sheets
4. Read the fixed date field, require matching worksheet dates, and normalize Excel/string dates
5. Convert blanks and Excel errors to null, reject invalid or non-finite numbers, and preserve source units
6. Require borrower plus FIGI or Bloomberg ID
7. Collapse exact duplicates with all locators and reject identifier/value conflicts
8. Compute a stable universe digest and bounded findings

### Verification

- Generate anonymized XLSX bytes in tests using the installed `openpyxl`
- Cover multiple sector tabs, summaries, hidden sheets and rows, nulls, date formats, every metric, duplicates, conflicts, header drift, formula-cache gaps, and unsafe package parts

## Phase 2: Add immutable storage and migration

### Files

- Add `caos/server/migrations/003_rv_loan_universes.sql`
- Modify `caos/server/caos/store.py`
- Extend `caos/tests/test_loan_universe.py`
- Extend `caos/tests/test_migrate.py`

### Implementation

1. Add memory buckets for universe records, normalized rows, and active case pointers
2. Add idempotent lookup, rejection recording, atomic activation, active read, and source-withdrawal methods
3. Roll back buckets and audits when persistence fails
4. Include the buckets in PostgreSQL snapshots and restores
5. Add normalized universe and row tables, one active universe per case, and deterministic import uniqueness
6. Sync normalized tables only when the loan buckets changed in the authoritative state
7. Supersede the prior active version before inserting the next active record in one transaction

### Verification

- Prove idempotency, rollback, one active version, rejection retention, source withdrawal, restart restore, and migration replay
- Run the existing store/model persistence tests because `_snapshot` and `_persist_connection` are CRITICAL paths

## Phase 3: Add case-scoped API and CP-3 binding

### Files

- Modify `caos/server/caos/contracts.py`
- Modify `caos/server/caos/http.py`
- Modify `caos/server/caos/workflows/domain.py`
- Extend `caos/tests/test_loan_universe.py`

### Implementation

1. Add a strict request containing only `source_id`
2. Add authenticated import and active-read routes
3. Return HTTP `201` for activation and structured HTTP `422` findings for invalid workbooks
4. Preserve existing source upload and legacy RV routes
5. Deactivate the active universe atomically when its source is withdrawn
6. Add the matching active universe ID and digest to CP-3 input fingerprints and lineage only when its source belongs to the pinned run source set

### Verification

- Cover writer/reader/outsider access, cross-case sources, withdrawn sources, idempotent responses, active reads, structured findings, and withdrawal rollback
- Run a Relative Value workflow and assert CP-3 uses the matching universe identity while other nodes remain unchanged

## Phase 4: Replace manual RV entry with the loan screener

### Files

- Modify `caos/frontend/src/components/Workspace.tsx`
- Modify `caos/frontend/app/globals.css`
- Modify `caos/frontend/scripts/production-inventory.mjs`

### Implementation

1. Replace `RVRowDraft` and the manual form with typed loan-universe records
2. Upload through the source endpoint, then import the returned `source_id`
3. Show uploading/scanning, validating, active, rejected, and empty states
4. Render source authority, workbook date, version, digest, source link, and `SOURCE DATA · UNANALYZED`
5. Add approved text, categorical, date, margin, and discount-margin filters
6. Make every loan column sortable with the approved default ordering
7. Render explicit loan units, signed changes, nulls, source locators, and no recommendation
8. Preserve keyboard focus, table scrolling, reduced motion, and non-color sign meaning
9. Update production inventory expectations to the new endpoint and empty/upload controls while leaving the legacy endpoint covered by server tests

### Verification

- Run frontend type checking, lint, unit/contract scripts, production build, browser inventory where its deployment prerequisites are available, and the required axe-core runner against the combined app

## Phase 5: Completion and deployment audit

### Verification

1. Run focused parser, persistence, route, workflow, and frontend checks
2. Run the complete server suite in `caos/server/.venv`
3. Run migration checks and the production deployment verifier
4. Run `rewrite-tournament` on changed non-trivial functions and patch confirmed improvements
5. Run `confidence-review`, investigate every uncertainty to root cause, and patch confirmed bugs
6. Run GitNexus `detect_changes()` and review all affected flows
7. Append the implementation verification critic pass to `.agent-reviews/redteam.md`
8. Stage only implementation files and leave `CLAUDE.md` untouched

### Exit gate

Every acceptance criterion in the approved design has direct test or runtime evidence, the frontend production build passes, deployment remains on the existing stack, and no source-only row is presented as a CP-3 recommendation.
