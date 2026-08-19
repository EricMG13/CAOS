# CAOS Applicable Updates — durable execution contract

Date: 2026-07-13. Status: **Phases 0 through 6 implemented; Phase 7 release
verification is in progress and production rollout remains operator-gated.**
The vendored `Modular OS/CP-2G/` and `Modular OS/CP-4D/` directories are the
source of truth for those analytical contracts; their checked manifests freeze
the supplied bytes.

## Non-negotiable architecture

Work ships as bounded, independently deployable phases. All migrations are
additive, backfillable, and rollback-safe. Lineage writes are transactional and
preserve authorization. XLSX processing is hostile-input, preview-first, and
fail-closed. There is one production model calculator. Overrides are typed,
audited, and recompute downstream outputs. Notifications are durable and scoped
to the analyst. Every interface meets WCAG 2.1 AA and never uses color alone.

## Approved-request traceability (27 items)

Phase 0 contract support does not complete a later request. Every request remains
pending except CC2, which was already complete when this contract was approved.

| ID | Request | Approved disposition | Phase | Dependencies | Flag | Acceptance test / evidence | Rollback | Status |
|---|---|---|---:|---|---|---|---|---|
| A1 | Remove standalone issuer search | Implement; preserve Alt+S through Command Palette | 5 | Shared command palette and issuer route | None | No standalone search; Alt+S opens palette and finds issuer | Restore prior search mount | [x] |
| A2 | Ticker/name opens issuer profile | Implement shared interaction contract | 5 | Canonical issuer link component | None | Keyboard/click tests across every ticker/name surface | Restore surface-local links | [x] |
| A3 | Consolidate data into vault | Implement canonical artifact lineage, not a duplicate store | 1 | Transactional lineage schema and authorization | `CAOS_LINEAGE_V2_ENABLED` | Atomic lineage, tenant denial, backfill and provenance E2E | Flag off; retain additive audit data | [x] |
| A4 | Small grey text | Role-based legibility remediation | 6 | Role views and token audit | None | Contrast, 200% zoom, role-view and axe checks | Revert token/component changes | [x] |
| A5 | Numerical chart visibility | Responsive charts and equivalent tables | 6 | Shared chart sizing/table fallback | None | Resize, keyboard, contrast and equivalent-data assertions | Restore current chart renderer | [x] |
| A6 | Key/action visibility | Promote decision-bearing actions; preserve progressive disclosure | 5-6 | Workflow hierarchy plus legibility tokens | None | Role-task usability, keyboard order and responsive checks | Revert action placement/tokens independently | [x] |
| A7 | Header-click collapse | Apply only to collapsible section shells | 5 | Shared collapsible section contract | None | Header/button keyboard, ARIA state and non-collapsible guard tests | Disable header activation | [x] |
| A8 | Information staleness | Central source-aware freshness policy | 1 | Canonical lineage timestamps/source classes | `CAOS_LINEAGE_V2_ENABLED` | Boundary-age, timezone, unknown-source and UI label tests | Flag off; use existing timestamps | [x] |
| A9 | Bloomberg `.xlsx` feed | Preview/commit into immutable market snapshots | 2 | Lineage v2 and price-feed specification | `CAOS_MARKET_XLSX_V2_ENABLED` | Hostile corpus, cached formula/as-of, auth and atomic commit tests | Flag off; preserve snapshots/audit | [x] |
| DD1 | Add 2G/3D | Add CP-2G and attached CP-4D; CP-3D already exists | 4 | Vendored contracts, lineage and adapters | `CAOS_CP_2G_ENABLED`, `CAOS_CP_4D_ENABLED` | Manifest/schema goldens, source gates and flag-off parity | Disable each module independently | [x] |
| DD2 | Summary readability | Sequential compact workflow list | 6 | Deep-Dive workflow semantics | None | Order, keyboard, reflow and 200% zoom tests | Restore current summary layout | [x] |
| DD3 | Dense text spill | Responsive grid and contained tables | 6 | Shared responsive panel/table primitives | None | Narrow viewport, long-content and horizontal-containment tests | Revert layout primitives | [x] |
| MB1 | Base rates/interest/debt math | Replace hard-coded values with canonical debt engine | 3 | One canonical calculator and debt inputs | `CAOS_MODEL_ENGINE_V2_ENABLED` | Golden debt/interest/base-rate parity and finite-number tests | Disable V2; live issuers fail closed and only Atlas reference may use the fixture calculator | [x] |
| MB2 | Key-account emphasis | Tune negative and decision-bearing totals | 6 | Model semantic row classes | None | Contrast and sign/total visual-regression assertions | Revert emphasis tokens | [x] |
| MB3 | Period separation | Verify and tune existing implementation | 6 | Stable period keys | None | Period grouping, scroll, print and responsive assertions | Revert gutter/rule tuning | [x] |
| MB4 | Scenario Builder/Network clarity | Separate into two named modes | 5 | Persisted mode and shared model state | None | Mode labels, state preservation and keyboard navigation tests | Restore combined view | [x] |
| MB5 | Unsaved-leave warning | Implement with user preference | 3 | Dirty-state model and analyst settings | `CAOS_MODEL_ENGINE_V2_ENABLED` | Navigation/browser-exit and preference persistence tests | Disable V2 route; retain drafts and analyst preference | [x] |
| MB6 | Edit any cell | Audited any-cell override layer | 3 | Typed keys, auth, lineage and calculator | `CAOS_MODEL_ENGINE_V2_ENABLED` | Type/auth/audit, undo and downstream recomputation tests | Disable V2 route; retain overrides/audit and never feed them to the fixture calculator | [x] |
| MB7 | Import model | Versioned preview/mapping/commit workflow | 3 | Model workbook spec, lineage and calculator | `CAOS_MODEL_ENGINE_V2_ENABLED` | Hostile workbook, mapping, no-write preview and atomic commit tests | Disable V2/import endpoints; retain versions and audit | [x] |
| PL1 | Upload to Execution Graph | Exact-run navigation and live polling | 5 | Run identity and durable execution state | None | Upload-to-run deep-link, reconnect and terminal polling tests | Restore prior upload destination | [x] |
| PL2 | Global completion toasts | Durable analyst-scoped events | 5 | Durable events and analyst identity | None | Restart, tenant isolation, dedupe and keyboard toast tests | Disable delivery; retain event ledger | [x] |
| PL3 | DAG responsiveness | Adaptive inspector and legible graph layout | 6 | Execution Graph semantics | None | Resize, dense DAG, keyboard inspector and reduced-motion tests | Restore current graph layout | [x] |
| CC1 | Coverage table | Bind positions to persisted portfolios; harmonize row behavior | 5 | Persisted portfolio positions and issuer links | None | Live binding, empty/error, row keyboard and tenant tests | Restore current adapter/table | [x] |
| CC2 | Remove ASK bar | Already complete; no product change | none | None | None | Regression assertion that removed bar stays absent | No rollback needed | [x] |
| CC3 | Posture above Watchtower | Bind posture to live portfolio first, then reorder | 5 | CC1 live portfolio posture | None | Live posture provenance, order and degraded-state tests | Restore current ordering/adapter | [x] |
| RB1 | Grey report text | Paper-specific legibility remediation | 6 | Report paper tokens | None | Print/PDF contrast and visual-regression checks | Revert paper token changes | [x] |
| RB2 | Appendix period/case spacing | Add column-group gutters/rules | 6 | Stable appendix period/case groups | None | Full-grid print snapshot and group-boundary assertions | Revert gutters/rules | [x] |

## Phase 0 program deliverables

- [x] Vendored byte-exact CP-2G and CP-4D sources with checked manifests.
- [x] Added synthetic non-production source-gate contract fixtures.
- [x] Added price-feed and model-workbook specifications.
- [x] Added five independently default-off rollout flags and focused tests.
- [x] Recorded the critic pass and this decision-complete execution contract.

## Phases, flags, dependencies, rollback

- [x] **Phase 0 — contract freeze:** program deliverables above. No runtime
  behavior change and no later user request marked complete.
- [x] **Phase 1 — lineage and freshness:** A3, A8 under
  `CAOS_LINEAGE_V2_ENABLED`; additive schema/backfill, transactional writes and
  authorization-preserving reads. Roll back by flagging reads/writes off while
  retaining audit data.
- [x] **Phase 2 — immutable market snapshots:** A9 under
  `CAOS_MARKET_XLSX_V2_ENABLED`; depends on Phase 1. Roll back upload/commit via
  flag without deleting committed snapshots.
- [x] **Phase 3 — canonical model engine:** MB1, MB5, MB6, MB7 under
  `CAOS_MODEL_ENGINE_V2_ENABLED`; depends on lineage and workbook contracts.
  Roll back by disabling V2. Live issuers then fail closed; only the explicit
  Atlas reference fixture may use the legacy calculator. Retain all V2 drafts,
  overrides, imports, checkpoints and audit evidence; never run two production
  calculators.
- [x] **Phase 4 — analytical modules:** DD1 adds both CP-4D and CP-2G under
  independent `CAOS_CP_4D_ENABLED` and `CAOS_CP_2G_ENABLED` flags; depends on
  lineage and exact prompt/schema compatibility. CP-3D already exists.
- [x] **Phase 5 — workflow and navigation:** A1, A2, A6 workflow scope, A7,
  MB4, PL1, PL2, CC1 and CC3; CC2 remains already complete. Each interaction
  change is independently revertible.
- [x] **Phase 6 — legibility and responsive density:** A4, A5, A6 visual scope,
  DD2, DD3, MB2, MB3, PL3, RB1 and RB2; depends on stable semantics from prior
  phases and must pass accessibility/print/reflow gates.
- [ ] **Phase 7 — verification and controlled rollout:** run the complete gate
  matrix, backfill and rollback drills, then enable one flag/cohort at a time.
  Use forward corrective migrations; never destructively remove analyst evidence.

## Phase 1 implementation evidence

- [x] Added migrations 0052–0054 for lineage metadata, reporting profiles,
  source-period metadata, and fail-closed report freshness authority.
- [x] Added bounded typed artifact refs, transactional/idempotent producer
  lineage, authorized context traversal, and restartable dry-run/apply/verify
  reconciliation without duplicating domain payloads or raw files.
- [x] Added the shared four-state freshness policy with distinct clocks for
  filings, legal documents, market prices, ratings, runs, and derived outputs;
  absent or unproved evidence is UNKNOWN, never CURRENT.
- [x] Adapted Digest, Command, Issuer Profile, Pipeline, Model Builder, Reports,
  PDF and XLSX authority to exact source identities. Artifact-revision changes
  cancel and refetch reads even when context/run IDs are unchanged.
- [x] Preserved scalar-only v1 shape and explicit typed-ref unbinds while making
  stale non-empty client patches union-safe against transactionally bound refs.
- [x] Independent review approved transactional lineage, authorization,
  historical-run evaluation, report/checkpoint rebinding, migrations, binary
  authority, and rendered state transitions across all five product adapters.
- [x] Verification: Phase 1 backend focus **40 passed, 1 skipped**; full backend
  excluding seven sandbox-denied loopback AV cases **1569 passed, 9 skipped**;
  full frontend **143 files / 766 tests**; TypeScript, ESLint, production build,
  PostgreSQL 0053↔0054 offline SQL, and `git diff --check` passed. The build
  retained only the established static-export/custom-rewrite warnings.

## Phase 2 implementation evidence

- [x] Added `.xlsx`-only, preview-first market intake. Preview is stateless;
  commit verifies an analyst-bound signed token, re-scans and re-parses the
  original bytes, then atomically persists the raw workbook, source manifest,
  immutable snapshot, normalized instruments, warning/rejection ledger and
  lineage. Duplicate imports are idempotent within analyst scope.
- [x] Added fail-closed OOXML controls for macros, external links/formulas,
  embedded/query content, unsafe members, expansion ratios, dimensions and
  cell/formula limits. Required formulas use finite cached values only; CAOS
  never evaluates workbook formulas or invents market as-of from upload time.
- [x] Added exact FIGI or explicit analyst issuer mapping, private snapshot and
  source ownership, foreign-object 404s, freshness/source labels in RV output,
  and the collapsed RV utility import flow. Removed misleading legacy `.xls`
  acceptance from upload controls and the spreadsheet sniffer.
- [x] A sanitized real Bloomberg workbook previewed with hash
  `77c4bf63d89938af949329c1d4d27588d96cbccc2e718be95829c8c2af9d9980`:
  **588 inspected, 586 accepted, 2 rejected, 0 blocking, 6 warnings**, market
  as-of 2026-07-13. The flag remains default-off for controlled rollout.
- [x] Verification: Phase 2 focused server gate **48 passed** (including commit
  re-scan and the 0055 rollback guard); full server without the socket-bound AV test file
  **1598 passed, 9 skipped**; the unrestricted full run's only remaining seven
  failures are the sandbox-denied loopback ClamAV cases. Full frontend **144
  files / 768 tests**, TypeScript, ESLint and production build passed. Migration
  0055 upgrades, downgrades empty, re-upgrades, matches the ORM, and refuses a
  destructive downgrade once imported evidence exists.

## Phase 3 implementation evidence

- [x] Added one pure server-side calculation authority with versioned debt
  schedules, average-balance interest, separate benchmark/margin/fees/PIK/
  hedges/FX components, finite-number and zero-denominator guards, debt
  roll-forward/discontinuity gaps, and explicit degradation when live issuer
  inputs are absent or invalid. Reporting currency and unit are explicit,
  validated identities rather than USD/millions defaults.
- [x] Added additive ModelDraftV2, debt instrument, typed override, immutable
  calculation, checkpoint and workbook-import persistence. Revision saves use
  atomic CAS; checkpoints reserve exact revisions; report previews,
  publications, PDF/XLSX exports and workbook exports bind the same engine,
  source fingerprint and calculation hash.
- [x] Added audited any-cell graph-node replacement with original values and
  formulas retained, required derived-cell reason/source/future expiry,
  downstream recomputation, undo/redo, checkpoint/restore, scenario-isolated
  reset, invariant warnings, and an analyst-visible history ledger. Expired
  effective overrides fail closed for recalculation and new report publication.
- [x] Added Cover, Model, Assumptions, Debt Schedule, Overrides and
  Sources/Audit workbook export/import. Preview is no-write and hostile-input
  bounded; close-format mapping uses stable/normalized row and period identities,
  requires explicit currency/unit, retains ambiguous bytes for analyst mapping,
  treats imported formulas as informational only, and commits atomically under
  revision CAS.
- [x] Routed live Model Builder through V2 only when enabled. Flag-off live
  issuers fail closed; Atlas Forge remains the sole reference-fixture exception.
  Added browser/internal-route unsaved guards with a persisted preference,
  server-authoritative scenario review/reset, bounded graph rendering, and
  import/checkpoint/report controls.
- [x] Verification: Phase 3 focused server gate **173 passed**; full server
  excluding the socket-bound AV file **1766 passed, 9 skipped**; full frontend
  **151 files / 827 tests**. TypeScript, ESLint, targeted Ruff/Python compile,
  production build, migrations 0056/0057 upgrade-downgrade-reupgrade/ORM checks,
  and `git diff --check` passed. Built `/model`, `/reports` and `/settings`
  returned zero axe violations for WCAG 2.1/2.2 AA. Seven AV loopback tests
  remain environment-limited and must run in the unrestricted release gate. A
  strict mocked-API Chromium smoke of the built live V2 route verified any-cell
  dirty state, sensitivity review/reset isolation, workbook-import controls,
  zero unknown API fallthrough and zero page/console errors.

## Phase 4 implementation evidence

- [x] Added literal CP-2G and CP-4D runtime support behind independent,
  default-off flags. CP-4D runs after CP-1/CP-1A/CP-4 and before CP-4C;
  CP-2G runs after CP-1/CP-1A/CP-2 and cannot by itself block the overall run.
- [x] Added closed versioned payload schemas, deterministic source gates and
  explicit unavailable fallbacks. Missing evidence produces Blocked or
  Completed with Limitations output with gaps; Not Applicable requires
  affirmative sourced CP-2G materiality evidence and never follows from
  retrieval silence.
- [x] Added manifest-verified full prompt bundles covering the Active Prompt,
  every REF, schema/system references, shared preamble and CAOS runtime overlay.
  The overlay preserves CAOS structured-output, storage and governance contracts
  while the vendored methodology files remain byte-locked.
- [x] Extended registry/planning, live synthesis, CP-6A bounded handoffs,
  research reports, Pipeline, Deep-Dive, module adapters, route maps,
  onboarding, payload references and consistency checks. Missing live output is
  rendered as unavailable; no rich synthetic findings enter product surfaces.
- [x] Verification: Phase 4 focused server **171 passed, 2 skipped**; focused
  frontend **33 passed**; full server excluding the sandbox-bound antivirus
  file **1788 passed, 9 skipped**; full frontend **151 files / 831 tests**.
  TypeScript, ESLint, Python compile, production build, prompt manifests,
  module consistency (**26 modules, 0 drift**) and `git diff --check` passed.
  The seven loopback antivirus cases remain environment-limited and unchanged.

## Phase 5 implementation evidence

- [x] Removed the standalone issuer-search mount and remapped Alt+S to the
  unified Command Palette. Applied the exact-ID `IssuerLink` contract across
  ticker/name surfaces with propagation guards so issuer links open profiles
  while keyboard-operable row remainders open local detail strips.
- [x] Replaced Command Center sample holdings with an authorized persisted-
  portfolio snapshot. Position posture is derived from the latest completed
  run bound to both portfolio and issuer; missing portfolios, empty holdings,
  unavailable data and unauthorized IDs render honest states rather than demo
  values. Portfolio posture now precedes Ranked Changes / Watchtower.
- [x] Routed successful uploads to the exact Pipeline execution graph and added
  visibility-aware queued/running polling through terminal state. Added durable
  analyst-scoped completion/failure events with idempotent terminal writes,
  cursor delivery, seen state, no initial-history replay, linked deduplicated
  toasts and foreign-object 404 behavior. Model imports remain synchronous, so
  no asynchronous model-import event is emitted by the current contract.
- [x] Split Scenario into independently retained `Model scenario` and
  `Cross-module propagation` modes, promoted frequent intake/import/model/report
  actions, and made genuine collapsible section headers keyboard buttons with
  `aria-expanded` without changing sortable/filterable table headers.
- [x] Verification: focused command, notification, upload/polling, scenario,
  link and collapsible tests passed; full server excluding the sandbox-bound AV
  file **1790 passed, 9 skipped**; full frontend **153 files / 837 tests**.
  TypeScript, clean ESLint, production build, migration 0058 upgrade-downgrade-
  reupgrade/ORM check and `git diff --check` passed. The built Command Center
  Playwright verifier passed at 1440x900, 1024x768 and 390x844 with preserved
  URL state, one dominant table, restored drawer focus, no region overlap and
  no document overflow.

## Phase 6 implementation evidence

- [x] Strengthened decision-bearing text, table headings, action controls and
  report-paper ink by semantic role without globally inflating the muted token.
  Secondary metadata remains muted; primary figures, labels and actions do not.
- [x] Routed analytical charts through `SemanticVisualization` with titles,
  accessible summaries, source IDs, direct legible labels and equivalent data
  tables. Deep-Dive workflow Summary is an ordered compact sequence; Report and
  Dense use responsive auto-fit cards, wrap long content and reserve horizontal
  scrolling for real tables.
- [x] Preserved Pipeline graph label size while adding a focusable two-axis
  navigation region and stacking the inspector before labels would need to
  shrink. Model key accounts remain bold when negative and stable period-group
  metadata drives slightly stronger gutters.
- [x] Added stable Q, YTD, Historic, LTM, PF, Base and Downside column groups to
  the report DSL and renderer. The appendix uses narrow group-start gutters and
  rules plus stronger paper ink while retaining the full-grid, one-page US
  Letter landscape contract.
- [x] Verification: focused Phase 6 frontend **9 files / 70 tests**; full
  frontend **157 files / 857 tests**; TypeScript, ESLint, production build and
  `git diff --check` passed. Axe found **0 violations** on Command, Deep-Dive,
  Pipeline, Model and Reports. The responsive gate passed **40/40** route checks
  at 390, 700, 900, 1024, 1100, 1280 and 1440px plus synthetic 200% zoom; focus,
  reduced-motion and keyboard graph-navigation smoke checks passed. Visual
  inspection covered Summary/Dense, Pipeline, Model and Report Studio; Chromium
  and `pdfinfo` confirmed the full appendix prints as exactly **1 landscape
  Letter page**. The build retained only the established static-export rewrite
  warnings.

## Phase 7 implementation evidence

- [x] Recorded the Phase 7 critic gate and created an operator-facing release
  record with immutable prompt manifests, endpoint authorization matrix,
  environment limitations, sequential flag dependencies, abort thresholds and
  evidence-preserving rollback instructions.
- [x] Added one explicitly synthetic integrated journey from source and market
  upload through the exact run, CP-4D/CP-2G, Model Engine v2, checkpoint,
  frozen report and XLSX. The test asserts artifact IDs, representative market
  figures, prompt fingerprints, notification idempotency and calculation hash.
- [x] Closed release-audit gaps: exact run selection is honored by Deep-Dive,
  Pipeline, Model v2 and Reports; market snapshots become typed run parents;
  workbook preview/commit require write role; module bulk/single reads enforce
  the team boundary; notification-rendering faults fall back to a minimal
  terminal event without stranding the run.
- [x] Local release evidence: Phase 7 focused server **76 passed, 2 skipped**;
  integrated journey **1 passed**; migrations **3 passed**; module consistency
  **26 modules / 0 drift**; full frontend **157 files / 861 tests**; TypeScript,
  ESLint, production build, Ruff and Python compilation passed. Axe found **0
  violations** and the responsive verifier passed **32/32** Deep-Dive,
  Pipeline, Model and Reports checks including 200% zoom. The full server
  completed **1808 passed, 9 skipped** outside the seven unchanged ClamAV
  loopback cases denied by the controller sandbox.
- [ ] Complete the full local/CI command matrix and the unrestricted AV,
  PostgreSQL, restored-snapshot, Docker/OAuth and production observation gates.
  No production flag has been enabled and compatibility paths remain intact.

## Acceptance gates

Every phase requires: flag-off behavior parity; focused unit/contract tests;
authorization and transaction failure tests; additive migration plus resumable
backfill proof where applicable; prompt/schema golden compatibility for CP
modules; keyboard, visible focus, semantic status labels, reduced-motion and axe
checks for UI; `git diff --check`; regression evidence interpreted with explicit
environment limitations; and documented operator rollback. Phase 0 accepts the
controller-session baseline recorded below plus its focused contract tests; it
does not represent unrestricted all-green execution. Later release gates must
rerun the full frontend/server suites and execute the sandbox-denied AV tests in
an environment that permits loopback sockets. A phase is independently deployable
only when all of its applicable gates pass without enabling any later phase.

## Reopen conditions

Reopen the critic pass if a phase cannot deploy or roll back independently; a
lineage write can diverge from its source transaction or cross authorization
scope; XLSX parsing evaluates formulas or accepts ambiguous/stale caches; a
second production calculator appears; an override is untyped, unaudited, or
does not recompute dependencies; a prompt/schema version changes without a
compatibility gate and flag; a migration becomes destructive or a backfill is
not resumable; a notification is ephemeral or crosses analyst scope; or an
interactive flow fails WCAG 2.1 AA.

## Phase 0 environment-limited acceptance evidence

- In this controller session, the frontend full suite completed **733/734**.
  Its sole non-passing PortfolioLab virtualization case passed **14/14** in an
  isolated rerun.
- In this controller session, the server suite completed **1498 passed, 7
  skipped**. A further **7 AV loopback tests** could not execute because the
  sandbox denied loopback sockets with `PermissionError`.

Phase 0 explicitly accepts this environment-limited baseline together with its
focused contract tests. This is not a claim of all-green unrestricted execution:
the isolated frontend rerun and sandbox-denied AV tests remain visible exceptions.
An unrestricted release environment must rerun and pass those AV loopback tests.
