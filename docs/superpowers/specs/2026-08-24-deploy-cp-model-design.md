---
meta:
  title: Deploy CP-MODEL from accepted Full Credit runs
  navLabel: Deploying CP-MODEL
  category: Architecture decisions
  contentType: Conceptual
---

# Deploy CP-MODEL from accepted Full Credit runs

This design replaces the Model Builder authority placeholder with a case-scoped path that calculates, validates, stores, and displays CP-MODEL v3 worksheet data. A model build uses one accepted Full Credit snapshot and fails closed unless its canonical handoffs satisfy the vendored CP-MODEL contract. LibreOffice is required only when an analyst explicitly requests an XLSX export.

## Content plan

- **Goal**: deploy CP-MODEL without the obsolete signed-correction requirement while preserving every input, calculation, lineage, and publication gate
- **Audience**: CAOS engineers, methodology owners, deployment operators, and QA reviewers
- **Outcome**: an analyst can build and inspect one immutable worksheet model from a model-ready accepted snapshot, with an optional XLSX export
- **Scope**: canonical Full Credit handoffs, model readiness, asynchronous export, persistence, API access, UI states, deployment dependencies, and verification
- **Open questions**: none; the approved decisions appear in this design

## Approved product contract

CP-MODEL builds only from an accepted `FULL_CREDIT` run at `Full` depth. The accepted snapshot, not the latest run, supplies model authority. Screen runs and other pathways remain visible but return `NOT_READY` with exact missing prerequisites. The primary CAOS model is the immutable structured output of CP-MODEL's Python IR and calculation engine, displayed as a read-only worksheet in Model Builder. A validated XLSX is an optional export of that model, not the model's identity or availability gate.

Builds run in the background. A build fingerprint combines the accepted snapshot digest, required handoff digests, Deploy V build identity, and CP-MODEL renderer digest. Repeating the request with the same fingerprint returns the existing queued, running, failed, or successful build. Accepting a different snapshot creates a new immutable build.

The product retains all successful builds. It never overwrites a model or optional export, or relabels an older build as current. Model Builder identifies which build matches the visible accepted snapshot.

## Authority boundary

The vendored Deploy V bundle remains immutable and integrity-checked. CAOS removes only the host-level hard-coded block that requires a future signed correction.

The current bundle contains an absorbed CP-2B phase inside CP-2A, while CP-MODEL requires a distinct CP-2B handoff. CAOS resolves that mismatch with a host-owned projection:

- Execute CP-2A's binding workflow, including all absorbed CP-2B tables
- Extract only the complete CP-2B registers and `cp2b.cp_model_catalysts` table
- Wrap the projection with CP-2B identity, source lineage, and the accepted run envelope
- Record the CP-2A artifact digest as `derived_from_artifact_digest`
- Validate the projected handoff with the CP-2B and CP-MODEL validators

The projection performs no analysis, inference, table repair, or value substitution. A missing or invalid CP-2B section makes the snapshot `NOT_READY`. CAOS does not alias CP-2A as CP-2B and does not change vendored files.

## Canonical upstream handoffs

Full Credit execution replaces generic host placeholders for CP-1, CP-1A, CP-1B, CP-2, and CP-2A with canonical Markdown handoffs. CP-2A also produces the validated CP-2B projection described above. CP-0 remains the accepted source-readiness and identity gate.

Each activated module follows one host execution contract:

1. Pin the run, source set, upstream artifact digests, Deploy V build, and module skill identity
2. Expose only pinned evidence blocks and named methodology sections to the provider
3. Require the complete canonical Markdown output defined by the module skill
4. Run module-owned deterministic scripts and validators in the worker
5. Canonicalize host-owned identity, evidence lineage, provenance, and hashes
6. Persist the artifact only when every module gate passes

The worker reuses the bounded provider, evidence-tool, lease, timeout, telemetry, and sanitization controls already used by the hybrid agent runtime. The activation generalizes that infrastructure instead of adding a second provider client. Provider output cannot declare its own source set, evidence family, confidence provenance, or artifact identity.

The run fails when a required module cannot author a valid handoff. It does not save a generic fallback artifact. Snapshot acceptance continues to require every run node and artifact to pass host validation.

The activation does not override provider-processing governance. A deployment must still authorize external processing of case evidence and keep the provider key in the worker. Without that authority or key, canonical Full Credit execution fails before any model can become ready.

Three focused components own the new behavior. `CanonicalModuleRunner` authors and validates the five upstream handoffs. `ModelReadinessService` resolves one accepted snapshot and its immutable fingerprint. `ModelBuildRuntime` claims jobs, persists worksheet payloads, and optionally publishes XLSX exports. Existing workflow, store, and HTTP modules call these concrete components without adding provider or storage interfaces.

## Model readiness resolver

One server-side resolver determines readiness for status, queueing, report inclusion, and tests. Clients cannot override it.

The resolver checks:

- An accepted snapshot exists and belongs to the requested case
- Its run used `FULL_CREDIT_32`, `FULL_CREDIT_ASSESSMENT`, and `Full`
- CP-0 passed with matching case, issuer, source set, dates, currency, and units
- CP-1, CP-1A, CP-1B, CP-2, and the CP-2B projection exist in the accepted run boundary
- Every handoff names CP-MODEL as a downstream consumer where required
- Artifact digests and upstream lineage match the accepted snapshot
- `validate_cp_model_inputs.py` accepts the complete handoff set
- The vendored CP-MODEL IR/calculation runtime is available

The resolver returns one of these states:

- `NOT_READY`: a prerequisite is absent or invalid
- `READY_TO_BUILD`: the accepted snapshot passes every input and calculation-runtime gate
- `QUEUED`: one model calculation waits for a worker
- `BUILDING`: one calculation worker owns an unexpired lease
- `READY`: the immutable structured model passed semantic and persistence QA
- `FAILED`: the worker reached a bounded input or calculation failure

XLSX export is a nested lifecycle on a ready model: `NOT_REQUESTED`, `QUEUED`, `EXPORTING`, `READY`, or `FAILED`. Export failure never demotes the structured model.

`NOT_READY` includes stable error codes and safe details such as missing module IDs or validator messages. It never includes source text, provider responses, credentials, filesystem paths, or stack traces.

## Build API

The API adds these case-scoped routes:

- `GET /api/cases/{case_id}/models`: return readiness, the current build, and immutable build history
- `POST /api/cases/{case_id}/models`: return the existing fingerprint match or create one queued calculation
- `GET /api/cases/{case_id}/models/{build_id}`: return one build's bounded status and QA metadata
- `POST /api/cases/{case_id}/models/{build_id}/exports`: idempotently queue the optional XLSX export
- `GET /api/cases/{case_id}/models/{build_id}/download`: stream one ready XLSX export

Every route calls the existing case membership gate. Queueing also requires case write authority. Build IDs never select filesystem paths directly.

Downloads use the governed filename, the XLSX media type, attachment disposition, `X-Content-Type-Options: nosniff`, and `Cache-Control: no-store`. A download request fails unless the build belongs to the case, the model and its export both have status `READY`, and the recorded file hash and size still match the vault object.

The old singular `GET /api/cases/{case_id}/model` route can delegate to the list/readiness service for one compatibility release. It no longer returns `BLOCKED` or mentions signed authority.

## Persistent model state

Migration `002` adds immutable model records and separately leased model jobs. Workflow jobs remain unchanged because their `run_id` foreign key and recovery semantics belong to analytical runs.

Each model record stores:

- Build, case, accepted run, accepted snapshot, and source-set identities
- Deploy V build ID and renderer version/hash
- Required artifact IDs, artifact digests, and the CP-2A to CP-2B derivation link
- Input fingerprint and lifecycle status
- Actor and queued, started, completed, or failed timestamps
- Bounded error code and detail
- Structured model payload, payload SHA-256, worksheet schema version, and bounded cell/lineage inventory
- CP-MODEL QA payload, semantic-check count, warnings, and limitations
- Optional export lifecycle, governed filename, relative vault key, byte size, workbook SHA-256, formula count, and recalculation engine

The database enforces one row per input fingerprint and case. The model job table supports queued, claimed, succeeded, and failed states with a worker ID, attempt token, and lease expiry.

MemoryStore mirrors the same behavior for local execution and contract tests. PostgresStore claims, renews, finalizes, and recovers model jobs through database transactions. A stale worker cannot change model state or publish metadata.

## Model calculation and optional workbook publication

The model worker performs these steps without LibreOffice:

1. Claim the queued build with a fenced lease
2. Re-read the pinned model record and accepted artifacts from durable state
3. Recompute and compare every input and renderer digest
4. Write canonical handoffs into a unique private temporary directory
5. Call vendored `build_ir` and `calculate`
6. Serialize Credit Snapshot, Model, and KPI worksheet cells from the typed IR/calculation book, including semantic IDs and source lineage
7. Hash the bounded structured payload
8. Commit `READY` model metadata, payload, and audit event through the fenced model-job transaction

An explicit export job re-reads the same ready model and canonical inputs, calls vendored `build_cp_model` with the worker-resolved `soffice`, validates formulas and cached values against the independent Python expectations, then publishes exclusively under `models/{case_id}/{build_id}/`. It commits export metadata separately through the same model-job fence.

The final filename remains `[IssuerID]_CP-MODEL-v3_[FirstPeriod]-[LastPeriod]_[YYYYMMDD].xlsx`. The worker never accepts a filename, output directory, or LibreOffice command from an API request.

If XLSX publication succeeds but final export metadata fails, the structured model remains ready while the unreferenced file is inaccessible through the API. A retry with the same export identity verifies and adopts that exact file or fails on a mismatch. It never overwrites it.

## Model Builder interface

Model Builder replaces the authority placeholder with one focused workspace:

- Read-only worksheet tabs for Credit Snapshot, Model, and KPIs using server-calculated values
- Keyboard-operable row/column navigation, sticky headers, aligned numeric cells, and one-interaction evidence lineage
- Accepted snapshot identity and source-set version
- Required handoff checklist with module, status, digest, and blocker
- Current build state and concise worker progress
- QA identity with renderer hash, recalculation engine, formula count, semantic-check count, warnings, and limitations
- One primary model action: **Build model** or **Retry build**, plus an explicit **Export XLSX** / **Download XLSX** control after the model is ready
- Compact immutable history with snapshot digest, completion time, payload hash, and optional export identity/action

The page polls while the build is queued or running and stops in a terminal state. It disables duplicate submission while preserving server-side idempotency. Text and glyphs accompany every status color, focus remains visible, and live updates use a polite status region. Reduced-motion preferences disable any running-state pulse.

Model Builder never presents `READY_TO_BUILD` as a completed model. Failed and not-ready states retain direct links to the accepted run and Deep-Dive evidence.

## Report integration

Report freezing may include a model only when the selected model build is `READY` and matches the report's accepted snapshot. The frozen report stores the model build ID, model payload hash, and input fingerprint. If the report explicitly includes a ready XLSX export, it additionally stores the export ID and workbook hash.

Approval recomputes the report fingerprint with the same model identity. A newer model or snapshot does not mutate a frozen report. The XLSX report appendix names and hashes the included CP-MODEL build instead of displaying the signed-authority placeholder.

## Deployment changes

The production worker image installs headless LibreOffice from the pinned Debian base repositories for optional XLSX export. Core model calculation and the API do not require `soffice`. Image verification separately checks the Python-only model path and the worker export path.

The app and worker continue to share the `/vault` volume. Only the worker needs the Anthropic key and invokes LibreOffice. The API never receives provider credentials. The read-only root filesystem, dropped capabilities, no-new-privileges setting, and private `/tmp` mount remain unchanged.

The worker loop polls analytical runs and model builds. It uses the existing bounded executor rather than a second service or queue dependency.

## Failure behavior

The system fails closed at every boundary:

- Invalid or missing canonical handoff: `NOT_READY`
- Missing provider configuration during upstream execution: the Full Credit run fails with `AGENT_PROVIDER_UNAVAILABLE`
- Missing LibreOffice: the ready model remains available; only export becomes `FAILED` with `MODEL_EXPORT_RUNTIME_UNAVAILABLE`
- Lease loss: the stale worker stops without committing state
- CP-MODEL input or calculation failure: model `FAILED` with the governed diagnostic code
- XLSX formula, recalculation, or binary failure: export `FAILED` while the model remains `READY`
- Existing output collision or hash mismatch: `FAILED` without overwrite
- Model finalization failure: no ready model metadata
- Export finalization failure: no downloadable workbook; the ready model remains available
- Missing or changed vault file: download fails closed and records an integrity failure

Logs, API errors, audit events, and model records exclude source text, prompts, provider bodies, credentials, absolute paths, and raw exception strings.

## Verification plan

Backend checks cover:

- Accepted snapshot and Full Credit readiness gates
- CP-2A to CP-2B projection completeness, lineage, and rejection cases
- Canonical module validation and generic-placeholder rejection
- Fingerprint stability and changed-snapshot versioning
- Concurrent identical queue requests
- Memory and PostgreSQL claim, lease renewal, takeover, fencing, and recovery
- Temporary-file cleanup, exclusive publication, orphan adoption, and collision failure
- Cross-case access, write authority, and download integrity
- Report freeze and approval with matching and stale model builds

One real integration fixture builds the governed `.xlsx` with LibreOffice, reloads formula and cached-value views, and asserts the workbook hash, sheet registry, formula count, semantic checks, and hidden control sheets.

Frontend checks cover all six states, duplicate-click prevention, polling termination, immutable history, exact blockers, keyboard operation, focus visibility, reduced motion, narrow-layout overflow, and rendered axe-core validation.

Deployment checks cover migration, image build, `soffice` availability, non-root execution, shared-vault publication, worker recovery, backup inclusion, restore download, and the absence of provider credentials from the app container.

## Removal inventory

The implementation removes signed-authority blocking language and behavior from:

- The case model endpoint
- Model Builder
- CP-2G and CP-MODEL workflow placeholder narratives
- Report model inclusion and XLSX appendix text
- README files and product QA inventory expectations

The implementation retains Deploy V integrity verification, canonical module validation, CP-MODEL's hard gate, exclusive workbook publication, and all case authorization boundaries.

## Delivery sequence

1. Activate and validate canonical Full Credit handoffs, including the CP-2B projection
2. Add readiness resolution, model records, leased jobs, and worker execution
3. Add model worksheet API and optional immutable export/download
4. Replace the Model Builder placeholder with worksheet tabs
5. Enable report inclusion for matching ready model payloads
6. Isolate LibreOffice to the export worker and run deployment verification

Each stage leaves the prior fail-closed behavior intact until its tests pass. The final stage removes the signed-authority placeholder only after the complete end-to-end path succeeds.
