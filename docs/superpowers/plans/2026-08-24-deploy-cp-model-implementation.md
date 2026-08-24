# Execute the CP-MODEL deployment

This plan implements the approved design in `docs/superpowers/specs/2026-08-24-deploy-cp-model-design.md`. Completion means an accepted Full Credit run can produce validated canonical handoffs, queue one immutable CP-MODEL calculation, persist its structured worksheet payload, display it in Model Builder, and optionally export a validated workbook.

## Phase 0: Use only verified repository and vendor APIs

### Objective

Freeze the callable surfaces and known gaps before editing symbols.

### Allowed APIs

Use these existing CAOS APIs:

- `accepted_snapshot(store, case_id)` from `caos/server/caos/artifacts/domain.py`
- `require_case(store, case_id, identity, write=False)` from `caos/server/caos/identity_cases/domain.py`
- `WorkflowRuntime.executor`, worker leases, and `_LeaseFence` from `caos/server/caos/workflows/domain.py`
- `PostgresStore._fenced_connection(...)`, `_merge_state(...)`, and `_persist_connection(...)` patterns from `caos/server/caos/store.py`
- `Vault`'s exclusive temporary-write and fsync pattern from `caos/server/caos/sources/domain.py`
- `request<T>(...)`, `LoadState`, `RunStatusBadge`, and native download links from `caos/frontend/src/components/Workspace.tsx`

Use these vendored CP-MODEL APIs:

```python
BundlePaths(cp1, cp1a, cp1b, cp2, cp2b, cp2g=None)
build_ir(bundle, quarter_count=None) -> CreditModelIR
calculate(ir) -> CalculationBook
BuildRequest(bundle, output_dir, quarter_count=None, soffice_path=None)
build_cp_model(request: BuildRequest) -> BuildResult
validate_cp_model_bundle(
    cp1_markdown,
    cp1a_markdown,
    cp1b_markdown,
    cp2_markdown,
    cp2b_markdown,
    cp2g_markdown=None,
    *,
    require_segment_allocation=True,
) -> ValidationResult
validate_text(
    text,
    *,
    filename=None,
    expected_module=None,
    expected_run_id=None,
    expected_period=None,
) -> ValidationResult
```

References:

- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-model/scripts/cp_model_v3/domain.py`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-model/scripts/cp_model_v3/builder.py`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-model/scripts/validate_cp_model_inputs.py`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-model/scripts/validate_handoff.py`

### Known gaps to implement

- The migration runner loads only `001_baseline.sql`
- Workflow jobs require a `runs` foreign key and cannot represent model jobs
- CP-MODEL is not exposed through `DeployVBundle`
- Renderer identity is private before a build
- The exporter cannot validate or adopt an existing workbook after metadata failure
- The current host has no serializer for CP-MODEL's typed IR/calculation results
- CP-2B has no standalone completeness validator
- No valid CP-MODEL handoff fixture exists
- The production image has no LibreOffice for optional XLSX export

### Anti-pattern guards

- Do not edit integrity-pinned vendored files
- Do not pass CP-2A Markdown as `BundlePaths.cp2b`
- Do not weaken `validate_cp_model_bundle`
- Do not invent a model from generic host placeholder artifacts
- Do not add a queue service, provider SDK, workbook library, or frontend dependency
- Do not accept output paths, filenames, commands, or artifact identity from a request

### Exit gate

Every later task cites a verified surface above or names the new concrete code it must add.

## Phase 1: Add a valid canonical handoff fixture and CP-2B projection gate

### Objective

Create the smallest real bundle that proves the existing validator and exporter can succeed before wiring runtime state.

### Files

- Add `caos/tests/fixtures/cp_model/` with valid CP-1, CP-1A, CP-1B, CP-2, and CP-2B Markdown
- Add `caos/server/caos/models/domain.py`
- Add `caos/tests/test_cp_model.py`

### Implementation

1. Run GitNexus impact before adding calls to vendored validator symbols and before modifying any shared helper.
2. Author fixture tables from the exact authorities:
   - CP-1: `cp-1-canonical-data-foundation/references/REF_CP-1_STEPS.md:307`
   - CP-1A: `cp-1a-business-transaction-fact-pack/references/REF_CP-1A_STEPS.md:63`
   - CP-1B: `cp-1b-earnings-delta/references/REF_CP-1B_STEPS.md:195`
   - CP-2: `cp-2-fundamental-credit-synthesizer/references/REF_CP-2_STEPS.md:154`
   - CP-2B: `cp-2a-downside-pathway/references/REF_CP-2B_STEPS.md:124`
   - Exact columns/enums: `cp-model/scripts/validate_cp_model_inputs.py:31`
3. Make the fixture use one issuer, one run ID, one source set, at least four quarters, reconciled model accounts, one segment, one add-back, one debt facility, and source locators.
4. Add a concrete `CpModelBundle` loader in `models/domain.py`. Follow `DeployVBundle._load_cpdr_script` rather than changing global `sys.path` permanently.
5. Add `project_cp2b(cp2a_markdown: str, *, run_id: str, cp2a_artifact_digest: str) -> str`. It must:
   - require the complete T5.1 through T5.7 tables and `cp2b.cp_model_catalysts`
   - preserve every row and source locator
   - create the canonical six-H2 CP-2B envelope
   - record the supplied host-owned CP-2A artifact digest as derivation provenance; never try to derive the artifact digest from Markdown
   - perform no inference or repair
6. Validate the projection with common handoff validation and the full CP-MODEL bundle validator.
7. Leave one negative fixture proving incomplete T5 registers fail before model readiness.

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_cp_model.py -q -k 'fixture or projection or validation'
```

If local LibreOffice exists, run one exporter integration test. Otherwise keep the fixture validator test mandatory and reserve external recalculation for Phase 7's image test.

### Anti-pattern guards

- Do not snapshot a generated workbook into git
- Do not mock `validate_cp_model_bundle`
- Do not copy CP-2A frontmatter into CP-2B unchanged
- Do not call CP-2A's completeness script as proof of CP-2B completeness

### Exit gate

The complete fixture passes `validate_cp_model_bundle`, incomplete projection tests fail, and the vendored bundle remains byte-identical.

## Phase 2: Activate canonical upstream artifacts for Full Credit

### Objective

Replace generic placeholders for CP-1, CP-1A, CP-1B, CP-2, and CP-2A with host-validated canonical Markdown.

### Files

- Modify `caos/server/caos/workflows/provider.py`
- Modify `caos/server/caos/workflows/domain.py`
- Modify `caos/server/caos/methodology/bundle.py`
- Modify `caos/server/caos/config.py` only if a bounded module budget cannot reuse an existing constant
- Modify `caos/tests/test_cp_dr_runtime.py`
- Extend `caos/tests/test_cp_model.py`

### Implementation

1. Run GitNexus context and upstream impact for `AnthropicGateway`, `WorkflowRuntime._build_artifact_with_slot`, `WorkflowRuntime._build_artifact`, `DeployVBundle`, `build_snapshot_payload`, and any signature changed. Warn before a HIGH or CRITICAL edit.
2. Extract the existing provider turn, retry, token, telemetry, evidence-tool, lease, and sanitization mechanics into one shared concrete helper. Keep CP-DR behavior and tests unchanged.
3. Initialize a persisted `canonical_generation` budget on Full Credit runs. Store per-module fixed output-token ceilings for the five activated modules, derive the aggregate output allowance from those ceilings plus one bounded repair, and persist aggregate turns, evidence reads/bytes, input/output tokens, active time, retries, repairs, in-flight request digest, and attempts. Reserve and reconcile against this state through fenced run updates; never borrow or alias the CP-DR `research` budget.
4. Add `CanonicalModuleRunner` for exactly `CP-1`, `CP-1A`, `CP-1B`, `CP-2`, and `CP-2A` on `FULL_CREDIT_32/FULL_CREDIT_ASSESSMENT` runs.
5. Load each module's complete `SKILL.md` and mandatory references from the verified Deploy V root. Expose only pinned case evidence and already validated upstream artifact Markdown.
6. Require structured provider output containing one complete canonical Markdown string. Recompute host identity, source-set lineage, evidence references, provenance, and digests before validation.
7. Run the module's common handoff and semantic/completeness checks. Reject a provider response that omits a required table or workflow output.
8. For CP-2A, create and validate the CP-2B projection from Phase 1 using the host artifact digest and store it as a derived payload on the CP-2A artifact with its own digest and derivation identity.
9. Extend `build_snapshot_payload` so acceptance re-runs canonical common and module completeness validation for CP-1, CP-1A, CP-1B, CP-2, and CP-2A, verifies the CP-2B projection against the current CP-2A digest, and runs the full CP-MODEL bundle validator before minting a snapshot.
10. Keep all other analytical nodes on their existing deterministic host behavior. Do not broaden provider activation beyond the five required modules.
11. Fail the node and run with bounded `AGENT_*` or `CANONICAL_HANDOFF_INVALID` codes. Never fall back to a generic artifact.
12. Add fake-provider end-to-end tests proving exact evidence access, canonical validation, acceptance-time revalidation, lease loss, provider failure, and generic-placeholder rejection.

### Copy-ready references

- Provider loop: `caos/server/caos/workflows/provider.py:49`
- Lease fence and heartbeat: `caos/server/caos/workflows/domain.py:191`
- Canonical host-owned artifact fixture: `caos/tests/test_cp_dr_runtime.py:1586`
- Provider-to-canonical-artifact flow: `caos/tests/test_cp_dr_runtime.py:1369`
- Vendored module skills and `REF_CP-*_STEPS.md` paths listed in Phase 1

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_cp_model.py caos/tests/test_cp_dr_runtime.py -q -k 'canonical or cp_model or provider or lease or artifact'
caos/server/.venv/bin/python -m pytest caos/tests/test_cp_dr_planning.py -q
```

### Anti-pattern guards

- Do not send the entire vault or unpinned source blocks to the provider
- Do not trust provider-authored lineage, confidence provenance, filenames, or module identity
- Do not enable canonical provider execution for Screen or non-Full-Credit pathways
- Do not add a second Anthropic client

### Exit gate

A fake-provider Full Credit run persists validated canonical artifacts and a complete CP-2B projection; malformed or generic output cannot succeed or become acceptable.

## Phase 3: Add ordered migrations and durable model state

### Objective

Persist immutable structured model payloads, optional export metadata, and separately leased jobs in memory and PostgreSQL.

### Files

- Add `caos/server/migrations/002_cp_model.sql`
- Modify `caos/server/migrate.py`
- Modify `caos/server/caos/store.py`
- Modify `caos/tests/test_migrate.py`
- Extend `caos/tests/test_cp_model.py`

### Implementation

1. Run GitNexus impact for `MemoryStore`, `PostgresStore`, `_snapshot`, `_restore`, `_merge_state`, `_persist_connection`, and migration entry points.
2. Generalize migration discovery to apply sorted numeric SQL files once through `schema_migrations`. Keep `001` idempotent and test repeated execution.
3. Add `model_builds` and `model_build_jobs` with:
   - case, run, snapshot, source set, artifact, calculation-runtime, fingerprint, status, actor, timestamps, QA, and bounded error fields
   - structured worksheet payload, payload hash, worksheet schema version, and bounded lineage inventory
   - nested optional export status, governed vault metadata, workbook hash, formula QA, and recalculation engine
   - unique `(case_id, input_fingerprint)`
   - model-job state, attempt token, worker, lease, and claim index
4. Add `model_builds` and `model_jobs` buckets to MemoryStore and PostgresStore snapshot/restore/merge.
5. Add concrete methods for queue/idempotency, list/get, claim, renew, current-token check, and fenced success/failure finalization.
6. Copy the workflow lease's database-time, advisory-lock, `FOR UPDATE SKIP LOCKED`, takeover, and rollback behavior, but query the model-job table.
7. Commit `READY` or `FAILED` model state plus audit in one fenced transaction; update export state separately without demoting a ready model.
8. Prove concurrent identical queue requests converge on one build in memory and real PostgreSQL.

### Copy-ready references

- DDL conventions: `caos/server/migrations/001_baseline.sql`
- Workflow claim/renew: `caos/server/caos/store.py:577`
- Fenced transaction: `caos/server/caos/store.py:635`
- State merge/persist: `caos/server/caos/store.py:499`, `:813`
- Real PostgreSQL fixtures: `caos/tests/test_cp_dr_runtime.py:35`

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_migrate.py caos/tests/test_cp_model.py -q -k 'migration or model_store or claim or lease or idempotent or postgres'
```

Run the PostgreSQL subset with `CAOS_TEST_DATABASE_URL` when available.

### Anti-pattern guards

- Do not reuse `jobs.run_id`
- Do not use an in-memory scan as the production uniqueness gate
- Do not omit model buckets from `_snapshot`
- Do not let stale workers finalize a build

### Exit gate

Both stores implement the same lifecycle, ordered migrations apply twice without drift, and concurrency/fencing tests pass.

## Phase 4: Implement readiness and asynchronous Python model execution

### Objective

Resolve one accepted snapshot, queue its immutable fingerprint, and persist one validated structured worksheet model without LibreOffice.

### Files

- Extend `caos/server/caos/models/domain.py`
- Add `caos/server/caos/models/runtime.py`
- Modify `caos/server/caos/http.py`
- Modify `caos/server/worker.py`
- Extend `caos/tests/test_cp_model.py`

### Implementation

1. Run GitNexus impact for `accepted_snapshot`, `create_app`, `worker.main`, and executor ownership before edits.
2. Implement `ModelReadinessService` as the only readiness source. Check visible accepted snapshot, exact Full Credit identities, CP-0/source-set lineage, required artifacts, CP-2B derivation, full input validation, and Python calculation-runtime identity. Do not check LibreOffice.
3. Return stable states and bounded blockers: `NOT_READY`, `READY_TO_BUILD`, `QUEUED`, `BUILDING`, `READY`, or `FAILED`.
4. Compute the fingerprint from case, accepted run/snapshot/source set, required artifact digests, Deploy V build ID, Python calculation-runtime version/hash, worksheet schema version, and optional CP-2G digest.
5. Add `ModelBuildRuntime` on the existing executor. Claim/heartbeat/fence like analytical runs.
6. Call vendored `build_ir` and `calculate` directly. Serialize only the three visible workbook views—Credit Snapshot, Model, and KPIs—from typed IR/calculation results with semantic cell IDs, formats, and source lineage.
7. Hash and persist the bounded structured payload and semantic QA in the fenced model transaction. The database payload is the model authority; no model file is required.
8. On metadata-finalization failure, safely rerun the deterministic calculation from the same immutable inputs. There is no orphan file to adopt on the core model path.
9. Extend the production worker loop to submit analytical and model work with typed future keys. Catch completed-future exceptions so one failed task cannot terminate polling.
10. In development, schedule the model runtime immediately after durable queue creation, matching run behavior.

### Copy-ready references

- Accepted visible snapshot: `caos/server/caos/artifacts/domain.py:499`
- Runtime scheduling and heartbeat: `caos/server/caos/workflows/domain.py:122`, `:191`
- Worker polling: `caos/server/worker.py:10`
- Vendored IR and calculation: `cp_model_v3/builder.py`, `cp_model_v3/calculations.py`

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_cp_model.py -q -k 'readiness or fingerprint or runtime or worksheet or payload or worker'
```

### Anti-pattern guards

- Do not treat the latest unaccepted run as model authority
- Do not rebuild an identical ready fingerprint
- Do not mark metadata ready before Python calculation and semantic validation complete
- Do not expose absolute paths or raw exceptions
- Do not make LibreOffice or a generated file a model-readiness dependency

### Exit gate

One accepted canonical snapshot progresses through queue/build/ready, identical requests reuse it, stale workers fail silently, and its worksheet payload is available without LibreOffice.

## Phase 5: Add case-scoped model/export API and report inclusion

### Objective

Expose model worksheet data and optional immutable XLSX export, then bind ready model payloads into frozen reports.

### Files

- Modify `caos/server/caos/contracts.py`
- Modify `caos/server/caos/http.py`
- Modify `caos/server/caos/publishing/domain.py`
- Extend `caos/tests/test_cp_model.py`
- Modify `caos/tests/test_clean_slate.py`

### Implementation

1. Run API impact for the existing singular model route and symbol impact for `freeze_report`, `approve`, and `render_xlsx`.
2. Add plural list/queue/status, worksheet payload, export queue, and download routes from the approved design. Keep singular GET as a compatibility readiness alias.
3. Apply `require_case(..., write=True)` to model queue/retry and export queue/retry; apply read membership to list/status/payload/download.
4. Resolve only database-recorded relative vault keys under `settings.storage_dir`. Reject traversal, symlinks outside the root, wrong case/build, non-ready status, missing file, size mismatch, or SHA-256 mismatch.
5. Stream XLSX with governed disposition, correct media type, `nosniff`, and `no-store`. Record a bounded download audit event.
6. Replace `FreezeReportRequest.include_model` with an optional `model_build_id` while retaining compatible false/no-model input if needed by existing clients.
7. Freeze only a `READY` model matching the accepted snapshot. Persist model build ID, payload hash, and input fingerprint into report content and report fingerprint. Persist workbook identity only when the report explicitly includes a ready export.
8. Recompute the same model identity at approval. A newer snapshot or build cannot mutate the frozen report.
9. Replace the XLSX signed-authority appendix row with included model identity/hash or an explicit not-included row.
10. Test reader/write roles, outsiders, cross-case build IDs, tampered files, stale models, freeze rollback, approval mismatch, and export.

### Copy-ready references

- Case auth: `caos/server/caos/identity_cases/domain.py:43`
- Current model route: `caos/server/caos/http.py:421`
- Report freeze/rollback: `caos/server/caos/publishing/domain.py:11`
- Approval fingerprint: `caos/server/caos/http.py:445`
- Binary response: `caos/server/caos/http.py:478`

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_cp_model.py caos/tests/test_clean_slate.py -q -k 'model or report or export or download or authorization'
caos/server/.venv/bin/python run_sec_audit.py
```

### Anti-pattern guards

- Do not authorize by build ID alone
- Do not trust a stored path without root containment and integrity checks
- Do not include a model from a different snapshot
- Do not preserve `CP_MODEL_AUTHORITY_BLOCKED`

### Exit gate

API and report tests prove case isolation, immutable payload identity, optional integrity-checked download, idempotent queueing, and exact report/model snapshot identity.

## Phase 6: Replace the Model Builder placeholder

### Objective

Expose readiness, worksheet tabs, build progress, QA, optional export, and immutable history without adding frontend dependencies.

### Files

- Modify `caos/frontend/src/components/Workspace.tsx`
- Modify `caos/frontend/app/globals.css` only for missing model-specific layout
- Modify `caos/frontend/scripts/workbench-smoke.mjs`
- Modify `caos/frontend/scripts/a11y-axe.mjs`
- Modify `caos/frontend/scripts/production-inventory.mjs`

### Implementation

1. Run GitNexus impact for `ModelView` and any shared frontend helper before edits.
2. Replace singular blocked-state loading with plural model readiness/history.
3. Use case/request identity guards so a late response from another case cannot replace the visible model.
4. Poll only while status is `QUEUED` or `BUILDING`; clear timers on terminal state, case switch, and unmount.
5. Disable duplicate queue actions, rely on server idempotency, and refresh after POST.
6. Render accepted snapshot/source set, required handoff checklist, exact safe blockers, current build status, QA metadata, and immutable history.
7. For a ready model, render read-only Credit Snapshot, Model, and KPI tabs from server-calculated cells. Preserve aligned numbers, sticky row/column labels, keyboard access, and one-interaction source lineage. Do not evaluate formulas in React.
8. Keep one primary model action: **Build model** or **Retry build**. After readiness, expose a separate **Export XLSX**, **Retry export**, or **Download XLSX** control.
9. Use text plus glyph/status, polite atomic live updates, visible focus, responsive table regions, and reduced-motion behavior already present in CSS.
10. Add routed browser fixtures for all model and export states, worksheet tab/navigation/lineage, polling termination, duplicate submit, history, cross-case stale response, narrow overflow, and reduced motion.
11. Add a dynamic ready-state axe fixture and replace production inventory's blocked-state assertion and singular endpoint probe.

### Copy-ready references

- JSON requests: `caos/frontend/src/components/Workspace.tsx:46`
- Stale-response guard: `Workspace.tsx:171`
- Poll cleanup: `Workspace.tsx:310`
- Status/live region: `Workspace.tsx:532`
- Pending actions: `Workspace.tsx:796`
- Download links: `Workspace.tsx:853`
- Browser route fixture: `caos/frontend/scripts/workbench-smoke.mjs:664`
- Dynamic axe fixture: `caos/frontend/scripts/a11y-axe.mjs:38`
- Production binary proof: `caos/frontend/scripts/production-inventory.mjs:374`

### Verification

```bash
cd caos/frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:workbench
```

Run the combined FastAPI build for axe and production inventory according to `CLAUDE.md`.

### Anti-pattern guards

- Do not use the JSON request helper for XLSX bytes
- Do not add a browser formula engine or editable spreadsheet surface
- Do not keep polling in `READY`, `FAILED`, or `NOT_READY`
- Do not use color alone or add decorative motion
- Do not rewrite historical QA proof files as current evidence

### Exit gate

All states and actions work against routed fixtures, build/type/lint pass, and rendered Model Builder has zero axe violations.

## Phase 7: Isolate optional LibreOffice export and verify production

### Objective

Keep the API and core model path LibreOffice-free, execute optional XLSX export under production hardening, and preserve model payloads and exports through backup and restore.

### Files

- Modify `caos/deploy/Dockerfile`
- Modify `caos/deploy/verify_image_resources.py`
- Copy `caos/tests/fixtures/cp_model/` into the runtime image as a build-smoke fixture
- Modify `caos/deploy/restore_drill.sh`
- Modify `caos/tests/test_backup_integrity.py`
- Modify `.github/workflows/ci.yml` and `.github/workflows/nightly.yml` only where required to separate source and image checks
- Modify `README.md`, `caos/README.md`, and current QA inventory documentation

### Implementation

1. Run impact analysis for deployment verifier symbols and inspect current image CI before editing.
2. Install the minimum headless LibreOffice packages only in the worker image. Record the exact installed package/version evidence; do not claim apt repositories are version-pinned unless they are.
3. Copy the canonical CP-MODEL fixture into an explicit image-only fixture directory, then extend image verification to locate and execute `soffice --version`, import `openpyxl`, load the vendored CP-MODEL package, and run that fixture export. Do not assume the server-only Docker copy contains `caos/tests`.
4. Make the Python-only model verifier mandatory on every supported host. Give XLSX verification an explicit worker-image mode; host checks and the API image do not require LibreOffice.
5. Assert the image runs as UID 10001 and preserve read-only root, dropped capabilities, no-new-privileges, private `/tmp`, shared `/vault`, and worker-only provider key.
6. Prove backup includes database model payloads and any optional export bytes. Extend restore verification to compare restored payload hashes and, when present, workbook hash/size with model metadata; perform worksheet-read and authenticated-download smokes when the disposable stack is available.
7. Remove signed-authority prose from current product/runtime documentation. Preserve historical proof artifacts and add a superseding current validation record.

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_backup_integrity.py caos/tests/test_clean_slate.py -q -k 'backup or restore or compose or image or model'
docker build -f caos/deploy/Dockerfile -t caos:cp-model .
docker run --rm --entrypoint python caos:cp-model verify_image_resources.py --runtime
docker run --rm --entrypoint id caos:cp-model -u
```

Run the disposable Compose migration, app, worker, build, download, backup, and restore drill when Docker and PostgreSQL are available.

### Anti-pattern guards

- Do not put `ANTHROPIC_API_KEY` in the app or proxy
- Do not weaken container hardening for LibreOffice
- Do not treat a nonempty restored vault as model integrity proof
- Do not rewrite historical inventory JSON

### Exit gate

The production API/model path succeeds without LibreOffice; the worker image performs one real recalculated workbook export as non-root; backup/restore preserves model payloads and any exact export bytes; no current signed-authority blocker remains.

## Phase 8: Required post-edit reviews and completion audit

### Objective

Prove every approved requirement against current code and runtime evidence.

### Verification

1. Run the server suite with the project virtual environment.
2. Run frontend lint, typecheck, production build, workbench browser checks, and combined-app axe.
3. Run the route security audit and Deploy V integrity/taxonomy checks.
4. Run real PostgreSQL model job, fencing, and migration tests.
5. Run the Python-only worksheet fixture without LibreOffice and the real XLSX fixture in the worker image.
6. Run backup/restore, worksheet payload, and optional authenticated download integrity proof.
7. Search current source and docs for obsolete blockers:

```bash
rg -n 'signed Deploy V CP-MODEL correction|required|CP_MODEL_AUTHORITY_BLOCKED|Official CP-MODEL blocked' README.md caos --glob '!server/caos/methodology/vendor/deploy_v/**' --glob '!outputs/qa-validation/**'
```

8. Run `rewrite-tournament` in post-edit mode on the two most material changed symbols.
9. Run GitNexus `detect_changes({scope: "compare", base_ref: "origin/main"})` and inspect every affected flow.
10. Run `confidence-review`, reproduce every suspected issue, and patch confirmed defects.
11. Re-run focused checks after every patch, then re-run the full relevant suites.
12. Review `git diff` and stage only files created or changed for CP-MODEL. Preserve the user's existing `CLAUDE.md` edit.

### Completion evidence

Completion requires direct proof for:

- Canonical accepted Full Credit artifacts and CP-2B projection
- Full validator success and Python-only worksheet QA
- Optional real LibreOffice workbook QA isolated to export
- Immutable/idempotent build persistence
- Memory and PostgreSQL lease/fencing recovery
- Case-safe status/payload access and optional integrity-checked download
- Matching report freeze/approval identity
- All six Model Builder states and accessibility
- Production image/runtime hardening
- Backup and restore of model payloads and any optional exact workbook bytes
- Absence of current signed-authority blocks
- Clean focused and broad regression suites

### Exit gate

Mark the goal complete only after every item above has current authoritative evidence. A passing narrow suite cannot substitute for an unavailable image, PostgreSQL, browser, or restore proof.
