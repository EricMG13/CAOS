# CAOS GitNexus Grouped Adversarial Rewrite Tournament

Date: 2026-07-15  
Branch baseline: `codex/112@7b16397`  
Mode: review-only; production source remains unchanged; candidates are verified on scratch copies.

## Index evidence

- `node .gitnexus/run.cjs status`: active branch index is up to date at `7b16397`.
- The flat MCP registry is stale (`main` is 322 commits behind and its cached
  `codex/112` row still points at `5c3466d`), so every graph query in this
  review is pinned to `branch: codex/112`.
- Pinned graph: 20,532 nodes: 5,311 functions, 4,133 sections, 3,371
  properties, 2,917 variables, 1,455 files, 1,189 constants, 504 communities,
  466 classes, 327 interfaces, 300 processes, 295 methods, 131 routes, 129
  folders, and 4 tools.
- The graph exposes 56 heuristic community labels. Generic labels and small
  Leiden clusters are assigned by their files and cross-community edges; they
  are not treated as product modules in their own right.
- Strongest cross-community edges include Routes → Server (111), Engine →
  Server (41), Server → Routes (39), Deepdive → Pipeline (17), Server → Engine
  (14), Command → Monitor (13), Model → Decisions (12), Routes → Engine (12),
  Command → Pipeline (10), and Model → Reports (9).
- Final freshness refresh after the parallel checkout advanced:
  `node .gitnexus/run.cjs analyze` indexed committed `83f6a7d` successfully at
  **20,647 nodes, 37,225 edges, 622 clusters, and 300 flows**; a following
  `status` reported **up-to-date**. The first refresh attempt could not update
  the user-level registry from the restricted sandbox (`EPERM`); the approved
  rerun completed in 12.9s. Impact sets below remain the pre-rewrite discovery
  record at the stated tournament baseline; scratch candidates never entered
  the production graph.

## Review groups

The classification is codebase-wide. Each group receives one representative,
high-leverage target tournament and target-specific adversarial findings; this
is not a claim that one symbol exhausts every line in its group.

| Group | Connected responsibilities | Dominant graph labels | Representative target |
|---|---|---|---|
| G1 Core CP engine | CP-0/CP-X routing, dependency layers, synthesis, QA gates, fact projection | Engine, Stress | `caos/server/engine/runner.py::execute_run` (190-572) |
| G2 Model/workbook projections | debt/PIK roll-forward, cash flow, overrides, checkpoints, workbook identity | Model plus model-engine Server/Routes | `caos/server/model_engine_v2.py::ModelEngine.calculate` (604-1416) |
| G3 API/auth/tenancy/persistence | identity, role gates, issuer/portfolio scope, database lifecycle | Routes, Server | `caos/server/identity.py::get_identity` (132-237) |
| G4 Ingestion/lineage/pipeline | uploads, vaulting, reconciliation, run lineage, pipeline execution | Upload, Pipeline plus ingestion/lineage Server/Routes | `caos/server/lineage_reconciliation.py::reconcile_lineage` (222-507) |
| G5 Query/research/LLM safety | retrieval, query planning/synthesis, evidence grounding, research jobs, Ask | Query, Research, Ask/deep-research clusters | `caos/server/nlquery.py::execute_synthesis` (608-768) |
| G6 Portfolio/desk decisions | exposures, stress, Command, Monitor, alerts, decisions, committee context | Portfolio, Command, Monitor, Alerts, Decisions, Cohort | `caos/server/engine/portfolio.py::compute_portfolio_analytics` (290-413) |
| G7 Issuer analysis surfaces | issuer profile, Deep-Dive, sector review, RV, sponsor context | Profile, Issuers, Deepdive, Sector, Rv, Sponsors | `caos/server/routes/issuers.py::get_issuer_profile` (677-787) |
| G8 Reports/exports/charts | report composition, XLSX/PDF export, paper rendering, chart payloads | Reports, Charts | `caos/server/report_exports.py::render_report_xlsx` (255-594) |
| G9 Shared frontend shell | auth state, navigation, unsaved-work guards, settings, shared composition | Settings, App, shared Cluster_163-192/262-263 | `caos/frontend/src/components/shared/NavigationGuardProvider.tsx::NavigationGuardProvider` (52-221) |
| G10 QA/bench/scripts/tooling | regression harnesses, corpus goldens, complexity and release checks | Scripts, Bench, Golden, Qa, Perf, Tools, Versions, Edgar | `caos/scripts/check_complexity_delta.py::main` (line range to confirm before tournament) |

## Repository financial invariants

1. CP-1-derived leverage, debt, EBITDA, coverage, and related multiplications or
   divisions are admitted only after `engine.periods.is_finite_number`; a zero
   or degenerate denominator degrades to `None`, never NaN/Inf or a crash.
2. Model debt schedules preserve `closing = opening + draws + PIK - repayments
   - scheduled amortization`; PIK toggles and overrides cannot silently change
   cash interest or closing balances.
3. Free cash flow preserves `adjusted EBITDA - cash interest - taxes - capex +
   working-capital change + other cash flow`, with missing required inputs
   remaining unavailable rather than coerced to zero.
4. Covenant headroom preserves actual-vs-threshold meaning, add-back caps,
   maintenance/cov-lite distinctions, and finite leverage guards.
5. Recovery preserves absolute priority between ranks and pari-passu allocation
   within a rank. An unsized senior tranche makes junior recovery indeterminate;
   non-finite claims never enter the waterfall.
6. QA-Blocked financial outputs cannot project facts, seed models/scenarios, or
   become Committee Ready through a downstream roll-up.
7. YTM and discount margin are ingested finite passthrough fields. This codebase
   does not implement a native yield solver or day-count convention, so the
   tournament must not invent or alter one.

## G1 — Core CP engine

### Target and impact set

Target: `caos/server/engine/runner.py::execute_run`, GitNexus lines 190-572.

- Exact direct caller: `caos/server/run_executor.py::execute_run_by_id`.
- Upstream blast radius: LOW, 16 symbols: d1=1, d2=13, d3=2. The d2/d3 set
  includes `InProcessExecutor._run_with_sem`, `QueueWorker._run_loop`,
  `InProcessExecutor.enqueue`, `QueueWorker.start`, and focused tests in
  `test_async_runs.py`, `test_budget.py`, `test_engine.py`, `test_retention.py`,
  `test_runner_fault_isolation.py`, and `test_specialized_modules.py`.
- Downstream blast radius: CRITICAL, 59 symbols: d1=23, d2=21, d3=15; 72
  affected processes across Engine and Server.
- Direct dependencies: `demo_fixture_finding`, `qa_status_from`,
  `committee_status_from`, `roll_up_qa_status`, `worst_confidence`,
  `validate_lineage`, `extract_facts`, `extract_cost_facts`,
  `build_route_plan`, `all_specs`, `_stamp_prompt_version`, `_now`,
  `_dependency_layers`, `_apply_blocked_upstream_cascade`, nested `_run_layer`,
  `_persist_cpx`, `_persist_cp5b`, `_persist_cp5c`, `_persist_cp5`,
  `get_synthesizer`, `build_issuer_index`, `get_settings`, and `get_reviewer`.
- Affected process names: `get_model_v2`, `restore_model_v2_checkpoint`,
  `create_stress_run`, `get_research_report`, `get_rv_screen`,
  `patch_agenda_item`, `finalize_agenda_item`,
  `mutate_model_v2_overrides_batch`, `replay_model_v2_event`, `create_run`,
  `get_analytics`, `create_insight`, `put_report_draft`,
  `preview_market_snapshot_import`, `preview_report_version`, both portfolio
  `get_portfolio` flows, `list_insights`, `reject_insight`, `get_agenda_item`,
  `get_run_freshness`, `create_decision`, `get_issuer_freshness`, `nl_query`,
  `get_autonomy_draft`, `ingestion_gaps`, `put_reporting_profile`,
  `patch_alert_event`, `reopen`, `get_chunk`, `get_watchlist`, `patch_context`,
  `get_positions`, `create_query_run`, `get_command_snapshot`, `vault_exhibit`,
  `create_finding`, `get_saved_model`, `daily_digest`, `create_agenda_item`,
  `export_report_version`, `get_context`, `calculate_model_v2`,
  `ratify_insight`, `get_report_draft`, `list_agenda`, `create_sector_review`,
  `patch_analyst_settings`, `commit_market_snapshot_import`, `put_model_v2`,
  `get_sector_review`, `get_report_version`, `create_model_v2_checkpoint`,
  `mutate_model_v2_override`, `get_issuer_profile`, `create_model_checkpoint`,
  `create_context`, `list_decisions`, `get_decision`, `get_reporting_profile`,
  `get_latest_research_report`, `commit_model_workbook_import`,
  `preview_model_workbook_import`, `get_context_lineage`, `get_taxonomy`,
  `get_capabilities`, `create_rv_screen`, `update_holdings`, `patch_finding`,
  `create_report_version`, `get_query_run`, and `get_cross_default_map`.

Contract: keep the async `(session: AsyncSession, run: Run) -> None` interface,
caller-owned commit boundary, Run/DB mutations, exact gate and persistence
ordering, deterministic result order, failure propagation, and all externally
observable status/error/token/model/prompt/fact side effects.

### G1 invariants

- CP-0 runs first; CP-X is persisted before routed analytical modules.
- Registry hard and soft edges both constrain dependency layers.
- Session-bound synthesizers are serial; pure modules may fan out, but results
  are persisted in deterministic module order on one `AsyncSession`.
- Synthesis and unexpected module failures isolate to that module's Blocked
  gate; they do not discard successful same-layer peers.
- CP-5B lineage, CP-5C council, deterministic CP-5, and CP-5D blocked-upstream
  cascade remain in that order.
- Structural findings are included in the CP-5 clearance payload.
- Blocked CP-1/CP-2 outputs do not project metric facts; prior facts are deleted
  only when the same module actually wrote replacements.
- Run-level roll-up uses only `run_blocking` modules. Budget spend is cumulative
  across attempts and remains recoverable after rollback.

### Baseline verification

- Wrong interpreter diagnostic: `caos/server/.venv/bin/python -m pytest ... -q`
  used Python 3.9.6 and failed on `typing.TypeAlias` before app collection; this
  is an environment mismatch, not a candidate result.
- Real focused command:
  `caos/server/.venv311/bin/python -m pytest caos/tests/server/test_runner_layers.py caos/tests/server/test_runner_fault_isolation.py caos/tests/server/test_retention.py caos/tests/server/test_async_runs.py caos/tests/server/test_budget.py caos/tests/server/test_specialized_modules.py caos/tests/server/test_engine.py -q`
- Baseline result: **79 passed, 2 skipped, 1 warning in 5.41s**.
- Financial-invariant command:
  `caos/server/.venv311/bin/python -m pytest caos/tests/server/test_recovery_waterfall_contract.py caos/tests/server/test_nan_guards.py caos/tests/server/test_covenants.py caos/tests/server/test_model_engine_v2.py -q`
- Financial-invariant baseline: **164 passed, 1 warning in 2.18s**.

### Tournament result

Anonymous bracket (the Arbiter received no role labels):

1. Speed (A) defeated Memory (B).
   - A removes the repeated per-module scan by building one findings index,
     whereas B's generator-heavy version saves allocations without improving
     the dominant `O(modules * findings)` roll-up.
   - A preserves concrete lists at API boundaries; B adds iterator lifetime and
     exhaustion risks around helper calls and persistence.
   - A's single retention delete reduces database round-trips while retaining
     the incumbent's module-specific replacement gate.
2. Speed (A) defeated Readability (B).
   - A is shorter without fragmenting the orchestrator into extra indirection.
   - A improves the actual hot paths: one layer partition, one findings index,
     and one retention delete.
   - B improves naming and factoring but leaves more intermediate collection
     construction and repeated work.
3. Speed (A) defeated Incumbent (B).
   - A keeps the exact async signature, caller-owned transaction, persistence
     order, and deterministic side effects.
   - Its time bound improves findings roll-up from `O(M * F)` to `O(M + F)` and
     reduces one database round-trip.
   - The extra dictionaries/lists are bounded by the existing module and finding
     sets and materially improve maintainability of the roll-up path.

**Winner: Snippet A (Speed)**, replacing
`caos/server/engine/runner.py:190-572`. The repository source remains unchanged;
the winning code is applied only at
`/tmp/caos-g1-speed-019f67d3/engine/runner.py` pending any later remediation
authorization.

### Orchestrator verification

- Scratch import proof: `engine.runner.__file__` resolved to
  `/tmp/caos-g1-speed-019f67d3/engine/runner.py`, not the repository copy.
- Focused + financial command:
  `PYTHONPATH=/tmp/caos-g1-speed-019f67d3 caos/server/.venv311/bin/python -m pytest caos/tests/server/test_runner_layers.py caos/tests/server/test_runner_fault_isolation.py caos/tests/server/test_retention.py caos/tests/server/test_async_runs.py caos/tests/server/test_budget.py caos/tests/server/test_specialized_modules.py caos/tests/server/test_engine.py caos/tests/server/test_recovery_waterfall_contract.py caos/tests/server/test_nan_guards.py caos/tests/server/test_covenants.py caos/tests/server/test_model_engine_v2.py -q`
- Result: **243 passed, 2 skipped, 1 warning in 6.25s**.
- Full server command:
  `PYTHONPATH=/tmp/caos-g1-speed-019f67d3 caos/server/.venv311/bin/python -m pytest caos/tests/server -q`
- Result in the restricted sandbox: **1,829 passed, 9 skipped, 7 failed in
  75.71s**; all seven failures were loopback socket `PermissionError` cases in
  `test_avscan.py`, not candidate assertions.
- Sandbox-control rerun:
  `caos/server/.venv311/bin/python -m pytest caos/tests/server/test_avscan.py -q`
  outside the restricted sandbox: **8 passed in 0.17s**.
- Caller re-check: `run_executor.py::execute_run_by_id` still awaits the same
  two-argument coroutine, emits the same terminal notification, commits after
  return, and retains the same exception/rollback boundary; its focused tests
  are included above.
- Waterfall spot-check: EV 150 against two pari-passu rank-1 claims of 100 and a
  rank-2 claim of 100 returned recoveries `75 / 75 / 0` and percentages
  `75% / 75% / 0%`, preserving pari-passu allocation and absolute priority.
- CP-5B side-effect audit: `_persist_cp5b` reduces `findings` to scalar counts in
  a new `runtime_output` dict before council findings are appended. The winning
  in-place `findings.extend(council)` therefore cannot mutate a retained CP-5B
  list reference.

Final replacement code is preserved at
`.agent-reviews/adversarial-candidates/g1_execute_run_speed.py`; it is not
applied to production source by this review.

## G2 — Model/workbook projections

### Target and impact set

Target region: `caos/server/model_engine_v2.py:774-1229`, the debt-instrument
opening, roll-forward, PIK, interest, fee, FX, state-propagation, and result
construction region inside `ModelEngineV2.calculate` (method lines 604-1416).
The whole 813-line method was read, but a wholesale rewrite is disqualified as
too broad to verify as one financial change.

- GitNexus resolves the exact method as
  `Method:caos/server/model_engine_v2.py:ModelEngineV2.calculate#2`.
- Method-downstream impact: MEDIUM, 14 dependencies (13 direct, 1 at depth 2)
  in Server: `_period_order_key`, `_shift_months`, `_decimal`, `_number`,
  `_safe_div`, `_canonical_hash`, `source_fingerprint`, and the nested
  `apply_node`, `input_value`, `input_is_overridden`, `debt_value`,
  `add_missing`, and `override_value`; `is_finite_number` is depth 2.
- GitNexus does not resolve the dynamic `ModelEngineV2().calculate` method call
  as an incoming edge. The actual public boundary is therefore mapped through
  `calculate_model` at lines 1419-1420 plus exhaustive text search.
- Public-boundary upstream impact: **CRITICAL**, 84 symbols: 46 direct, 36 at
  depth 2, and 2 at depth 3; 10 API/workbook processes in Server and Routes.
- Direct production callers include `model_v2_checkpoint_snapshot`,
  `render_model_workbook`, `preview_workbook`, `_create_or_update`,
  `get_model_v2`, `calculate_model_v2`, both override mutation paths,
  `replay_model_v2_event`, both checkpoint paths, `_with_import_authority`, and
  `export_model_workbook`. Exhaustive search also identifies all 14 production
  call sites in `routes/model_v2.py`, `routes/model_workbook.py`,
  `model_service.py`, and `model_workbook.py`.
- Affected GitNexus processes: `preview_model_workbook_import`,
  `commit_model_workbook_import`, `get_model_v2`,
  `mutate_model_v2_override`, `replay_model_v2_event`,
  `restore_model_v2_checkpoint`, `calculate_model_v2`,
  `create_model_v2_checkpoint`, `put_model_v2`, and
  `mutate_model_v2_overrides_batch`.

Contract: preserve `calculate(payload, *, evaluated_at=None) ->
ModelCalculation`, the pure/no-mutable-state behavior, exact output schema and
hash identity, node append order, gap/warning order, override precedence,
period/instrument ordering, and all debt/interest/FX calculations.

### G2 invariants

- Contiguous forecast/pro-forma periods inherit the prior effective closing;
  actual/LTM periods preserve sourced openings and expose discontinuities.
- Forecast closing solves the average-balance PIK circularity with
  `(base_close + pik_factor * opening / 2) / (1 - pik_factor / 2)` and must
  reject a negative base close or non-positive denominator.
- Derived override precedence remains closing, expected close, PIK interest,
  average balance, then formula close; an explicit null remains unavailable,
  never zero.
- Actual periods preserve sourced close, calculate expected close separately,
  and surface a residual beyond `_TOLERANCE` as both warning and gap.
- Fixed debt has no benchmark or margin interest; floating debt has no coupon;
  hybrid debt includes benchmark, margin, and coupon exactly once.
- Fees preserve `max(0, commitment - average) * commitment fee * months / 12
  + cash fees`; a non-zero fee with missing commitment is unavailable.
- Same-currency FX defaults to one; cross-currency FX is required. Cash interest
  and closing debt convert through the effective FX node and cannot publish a
  negative expense or debt balance.
- Prior-closing state and instrument results are updated in deterministic
  priority/instrument order. Output node formulas and overrides remain fully
  auditable.
- This path has no native yield solver or day-count basis. `period.months / 12`
  is the only interest annualization convention and must remain unchanged.

### Baseline verification

Command:
`caos/server/.venv311/bin/python -m pytest caos/tests/server/test_model_engine_v2.py caos/tests/server/test_model_workbook.py caos/tests/server/test_model_workbook_api.py caos/tests/server/test_model_v2_api.py caos/tests/server/test_model_v2_report_identity.py caos/tests/server/test_report_exports.py -q`

Baseline result: **169 passed, 7 warnings in 10.69s**.

### Tournament result

Anonymous bracket:

1. Speed (A) defeated Memory (B).
   - A resolves derived overrides lazily in precedence order, avoiding lower
     priority conversions after a winner is known.
   - A removes transient missing-field, cash-component, and derived-field
     collections while retaining their observable order.
   - A is shorter and has the stronger time/space profile; B's additional
     unrolling grows the review surface without a compensating contract gain.
2. Readability (B) defeated the first-round winner (A).
   - B's local `calculated` helper removes repeated node-prefix and node-list
     plumbing while keeping node construction local to the method.
   - It unifies the duplicated forecast/actual average, PIK, and expected-close
     sequence without hiding the override ladder.
   - At 427 versus 513 lines, B is substantially easier to review and maintain
     despite modest helper-call overhead.
3. Ultimate challenger (A) defeated Incumbent (B).
   - A reduces the region from 456 to 427 lines and centralizes derived-node
     construction without introducing a public helper or API.
   - Override precedence, formula text, debt equations, warning/gap order, and
     output-node order remain unchanged.
   - The incumbent has lower constant-factor overhead, but the candidate's
     verified contract equivalence and smaller review surface win on
     maintainability.

**Winner: Snippet A (Readability)**, replacing
`caos/server/model_engine_v2.py:774-1229`. Production source remains unchanged;
the winning review artifact is
`.agent-reviews/adversarial-candidates/g2_model_debt_readability.py` and the
scratch splice is `/tmp/caos-g2-readability-019f67d3/model_engine_v2.py`.

### Orchestrator verification

- Scratch import proof: `model_engine_v2.__file__` resolved to
  `/tmp/caos-g2-readability-019f67d3/model_engine_v2.py`.
- Engine-focused command:
  `PYTHONPATH=/tmp/caos-g2-readability-019f67d3 caos/server/.venv311/bin/python -m pytest caos/tests/server/test_model_engine_v2.py -q`
  → **60 passed in 0.39s**.
- Remaining caller command:
  `PYTHONPATH=/tmp/caos-g2-readability-019f67d3 caos/server/.venv311/bin/python -m pytest caos/tests/server/test_model_workbook.py caos/tests/server/test_model_workbook_api.py caos/tests/server/test_model_v2_api.py caos/tests/server/test_model_v2_report_identity.py caos/tests/server/test_report_exports.py -q`
  → **109 passed, 7 warnings in 12.56s**.
- Combined caller result: **169 passed**; this covers every production caller
  family in the impact set: routes, checkpoints, workbook import/export,
  calculation identity, and report export.
- Six-month PIK spot-check at 12%: opening 200, draws 0, PIK
  `12.061855670103093`, repayment 10, amortization 0 produced closing
  `202.06185567010309`; the independently computed identity RHS was exactly
  `202.06185567010309`.
- Interest annualization remained `months / 12` (6/12). No yield solver or
  day-count basis exists in this path, so none was changed or invented.
- Five-process, 1,000-calculation microbenchmark medians were 0.378548s
  incumbent and 0.397215s candidate (candidate about 4.9% slower). This is a
  disclosed constant-factor trade-off; the accepted merit is the 29-line,
  duplication-reducing maintainability improvement, not a speed claim.

## G3 — API/auth/tenancy/persistence

### Target and impact set

Target: `caos/server/identity.py::get_identity`, source lines 133-238
(GitNexus symbol envelope 132-237).

- GitNexus exact UID: `Function:caos/server/identity.py:get_identity`.
- Upstream impact: **CRITICAL**, 162 symbols: 122 direct and 40 at depth 2;
  75 affected processes across Routes and Server.
- Downstream impact: **CRITICAL**, 7 symbols (5 direct, 2 at depth 2) but 76
  affected process memberships. Direct dependencies are `sanitize_field`,
  `get_settings`, `is_deployed`, `get_db`, and `read_session_token`; `_sig` and
  the transaction cleanup path are depth 2.
- The direct set spans virtually every authenticated analytical surface:
  alerts, analysis/findings, insights, autonomy, chat, committee, decisions,
  digest, ingestion, market import, Model Builder/workbook, portfolios, Query,
  Reports, Research, runs, sectors, issuer profiles, settings, sponsors,
  thesis, and auth profile routes.
- Highest-fan-out affected processes include `patch_alert_event`,
  `patch_context`, `create_rv_screen`, `create_context`,
  `patch_analyst_settings`, `patch_finding`, `get_report_version`,
  `create_query_run`, `vault_exhibit`, `create_model_checkpoint`,
  `create_sector_review`, `create_run`, `export_report_version`, and
  `put_reporting_profile`.

Contract: preserve the exact FastAPI dependency signature, `CallerIdentity`
fields/defaults, query count and query conditions for each branch, exception
status/detail, security-check order, sanitization boundary, source label, role,
team scope, and local-development fallback.

### G3 invariants

- In a deployed context with an edge secret, the constant-time edge credential
  check runs before cookie or forwarded identity resolution; a cookie cannot
  bypass origin proof.
- A profile cookie must pass HMAC, mandatory expiry, analyst-row existence, and
  `token_version`; a revoked or erased profile falls through rather than
  authenticating.
- In deployed mode, a valid cookie whose bound email differs from the current
  forwarded principal is ignored; same-user SSO and unproxied development
  retain the documented behavior.
- Header-less deployed requests fail 401. Only genuine development may return
  `_LOCAL_DEV`.
- Cookie and forwarded identity fields are sanitized before persistence/log
  exposure. Persisted analyst roles and `team_id` remain authoritative where a
  matching row exists.
- The proxy email lookup remains case-insensitive and optional for compatible
  lightweight test DB doubles.
- This function performs no yield, day-count, covenant, or waterfall math.
  Its financial invariant is authorization: an unverified, revoked, or
  cross-team principal must never acquire access to the analytical records
  protected by its 122 direct route dependents.

### Baseline verification

Command:
`caos/server/.venv311/bin/python -m pytest caos/tests/server/test_identity.py caos/tests/server/test_auth_profile.py caos/tests/server/test_auth_password.py caos/tests/server/test_tenancy.py caos/tests/server/test_write_role_matrix.py caos/tests/server/test_access_log.py -q`

Baseline result: **53 passed, 2 warnings in 5.98s**.

### Tournament result

Anonymous bracket:

1. Speed (A) defeated Memory (B).
   - A retains edge-first authentication, revocation, SSO fallthrough, proxy
     lookup, sanitization, roles, teams, and deployed/local behavior.
   - It removes repeated header-attribute lookups and extensive inline prose
     while B is byte-for-byte the incumbent.
   - Both have the same asymptotic profile; A is the smaller review surface.
2. Readability (B) defeated the first-round winner (A).
   - B names the cross-user decision positively as `same_principal`, making the
     cookie acceptance rule easier to audit.
   - It retains the conditional persisted-analyst query and exact proxy
     fallbacks with fewer branches and locals.
   - B is shorter and clearer without changing query count, returned fields,
     exceptions, or sanitization.
3. Ultimate challenger (A) defeated Incumbent (B).
   - A preserves every tested security boundary and identity precedence while
     reducing the function from 106 to 67 lines.
   - Revocation, same-principal validation, proxy persistence, and fallback
     behavior remain directly legible.
   - Resource complexity is unchanged; the verified concision and
     maintainability gain beats the comment-heavy incumbent.

**Winner: Snippet A (Readability)**, replacing
`caos/server/identity.py:133-238`. Production source remains unchanged. The
winning artifact is
`.agent-reviews/adversarial-candidates/g3_get_identity_readability.py`; the
scratch splice is `/tmp/caos-g3-readability-019f67d3/identity.py`.

### Orchestrator verification

- Scratch import proof: `identity.__file__` resolved to the scratch file.
- The first combined attempt exposed a harness error, not a candidate error:
  importing scratch `identity` in `sitecustomize` also imported `database`
  before `conftest.py` could set its temporary `DATABASE_URL`, producing a
  stale-schema `no such column: lease_expires_at` startup failure.
- Corrected focused command pins a fresh database before Python startup:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g3verify-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g3verify-vault-019f67d3 CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g3-readability-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_identity.py caos/tests/server/test_auth_profile.py caos/tests/server/test_auth_password.py caos/tests/server/test_tenancy.py caos/tests/server/test_write_role_matrix.py caos/tests/server/test_access_log.py -q`
  → **53 passed, 3 warnings in 15.68s**.
- Full-server command with an independent fresh DB and the same scratch import:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g3full-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g3full-vault-019f67d3 CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g3-readability-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server -q`
  → **1,829 passed, 9 skipped, 7 failed in 83.16s**. All failures were the
  sandbox's loopback-socket denial in `test_avscan.py`.
- Outside-sandbox control using the same scratch import:
  `... python -m pytest caos/tests/server/test_avscan.py -q`
  → **8 passed, 1 warning in 0.03s**.
- Security spot-checks in the focused suite prove that a valid cookie cannot
  bypass the edge secret, a revoked token falls through, Alice's cookie under
  Bob's forwarded principal resolves as Bob/proxy, and Team B cannot enumerate
  Team A's analytical records.
- No financial formula is present. Caller preservation is established by the
  full server suite across all 122 direct route dependents.

## G4 — Ingestion/lineage/pipeline

### Target and impact set

Target: `caos/server/lineage_reconciliation.py::reconcile_lineage`, source
lines 223-508 (GitNexus symbol envelope 222-507).

- Exact UID: `Function:caos/server/lineage_reconciliation.py:reconcile_lineage`.
- Upstream impact: LOW, 5 symbols: 3 direct, 1 at depth 2, 1 at depth 3.
  Direct callers are the reconciliation CLI `_run` and two focused reconciliation
  tests in `test_phase1b_lineage.py`.
- Downstream impact: **CRITICAL**, 19 symbols: 14 direct and 5 at depth 2;
  73 affected processes across Routes and Server.
- Direct dependencies: `typed_refs_from_artifacts`,
  `bind_context_artifacts`, `_owner_identity`, `_fallback_owner_identity`,
  `_ref_status`, `_edge_exists`, nested `add_ref`/`add_edge`,
  `canonical_artifact_id`, `lineage_idempotency_key`, `write_lineage_edge`,
  `tenancy_enabled`, `issuer_visible`, and `portfolio_visible`.
- Those dependencies participate in model/checkpoint, portfolio, issuer,
  committee, Query, Report, Research, run, market-import, ingestion, and
  decision processes; lineage correctness therefore propagates far beyond the
  single CLI caller.

Contract: preserve the keyword-only mode/limit/cursor interface,
`ReconciliationResult` schema and counter meanings, stable ordering, database
query and transaction visibility, dry-run/apply/verify behavior, exact
idempotency/canonicalization semantics, and non-destructive restartability.

### G4 invariants

- Mode and bounded page size fail before I/O; pagination is stable by context
  ID and `next_cursor` names the last returned context only when another row
  exists.
- Missing persisted owners fail closed when tenancy is enabled. Context issuer
  and portfolio scope must be visible before any proposal becomes valid.
- Every persisted v2 edge is verified even if it cannot be reconstructed as a
  proposal. Canonical prefixes, versions, transform version, analyst ID, and
  v2 idempotency key must tie exactly; malformed rows increment both malformed
  and integrity-failure counts.
- Explicit typed versions win. Legacy scalar adaptation may add an unversioned
  reference only when no exact/authoritative reference exists for that kind/ID.
- Historical uncertainty is surfaced as unresolved; the reconciler never
  invents run-input edges or a source manifest that history cannot prove.
- Dangling and unauthorized refs never enter `valid_refs`; an edge is proposed
  only when both endpoints remain valid and an exact edge does not already
  exist.
- Apply mode writes idempotent v2 edges, binds valid typed refs, and commits once
  per context. Dry-run and verify perform no writes and roll back before return.
- There is no yield/day-count/covenant/waterfall math here. The financial
  invariant is audit provenance: model, report, run, market, insight, document,
  and decision relationships must remain attributable and tenant-authorized.

### Baseline verification

Command:
`caos/server/.venv311/bin/python -m pytest caos/tests/server/test_phase1b_lineage.py caos/tests/server/test_lineage_v2.py caos/tests/server/test_tenancy.py -q`

Baseline result: **59 passed, 2 skipped, 2 warnings in 9.78s**.

### Tournament result

Anonymous bracket:

1. Speed (A) defeated Memory (B).
   - A replaces repeated linear legacy-ref and valid-edge membership scans with
     version-aware set lookups, improving dense-context worst cases from
     quadratic toward linear.
   - It preserves typed-version precedence, insertion order, counters,
     authorization, SQL calls, and transaction boundaries.
   - Its additional linear key sets have a clear purpose and a smaller overall
     cost than B's primarily allocation-focused changes.
2. First-round winner (A) defeated Readability (B).
   - A avoids reparsing persisted typed refs and uses one canonical key shape
     for binding, validation, and apply accounting.
   - It materially improves edge-filtering complexity while retaining sorted
     ref processing and insertion-ordered proposals.
   - B conceded to the incumbent and retains the repeated equality scans and
     temporary collections.
3. Ultimate challenger (A) defeated Incumbent (B).
   - A preserves cursor behavior, every counter, tenancy enforcement,
     integrity checks, version precedence, database order, commits, and rollback.
   - Constant-time base-ref and valid-ref membership is the strongest verified
     algorithmic improvement in the bracket.
   - The bounded linear indexes cost auxiliary space but improve time complexity
     and make membership intent explicit without contract drift.

**Winner: Snippet A (Speed)**, replacing
`caos/server/lineage_reconciliation.py:223-508`. Production remains unchanged.
Artifact:
`.agent-reviews/adversarial-candidates/g4_reconcile_lineage_speed.py`.
Scratch splice: `/tmp/caos-g4-speed-019f67d3/lineage_reconciliation.py`.

### Orchestrator verification

- Focused command with a fresh DB and scratch import:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g4verify-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g4verify-vault-019f67d3 CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g4-speed-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_phase1b_lineage.py caos/tests/server/test_lineage_v2.py caos/tests/server/test_tenancy.py -q`
  → **59 passed, 2 skipped, 3 warnings in 7.84s**.
- Exact CLI caller compiled and `reconcile_lineage.py --help` returned the
  expected dry-run/apply/verify interface, limit, and cursor arguments.
- Full-server scratch command with an independent fresh DB:
  `... python -m pytest caos/tests/server -q`
  → **1,829 passed, 9 skipped, 7 sandbox socket failures in 77.96s**.
- Same scratch environment, AV-only outside-sandbox control:
  `... python -m pytest caos/tests/server/test_avscan.py -q`
  → **8 passed, 1 warning in 0.03s**.
- The focused reconciliation test spot-check covers dry-run no mutation,
  first apply, repeated apply with zero new edges/refs, verify rollback, stable
  cursor restart, malformed/idempotency detection, missing-owner behavior, and
  foreign-portfolio rejection.
- No financial formula changed. The protected invariant is provenance and
  tenant authorization for financial artifacts.

## G5 — Query/research/LLM safety

### Target and impact set

Target: `caos/server/nlquery.py::execute_synthesis`, source lines 609-769
(GitNexus envelope 608-768).

- Exact UID: `Function:caos/server/nlquery.py:execute_synthesis`.
- Upstream impact: LOW, 2 direct callers and 2 affected processes:
  `routes/query.py::nl_query` and `create_query_run`, spanning Server and Routes.
- Downstream impact: **CRITICAL**, 12 symbols (2 direct, 6 at depth 2, 4 at
  depth 3) and 73 process memberships in Server. The exact direct graph
  dependency is `retrieval.bm25_rank`; GitNexus also reports unresolved generic
  `execute` call edges, so SQL/model construction is verified by native reads.
- Native caller search confirms the live immediate and persisted query-run
  paths at `routes/query.py:645` and `routes/query.py:812`.

Contract: preserve the async `(AsyncSession, SynthesisSpec) -> dict` boundary,
SQL filters/order/limits, scan and text-size resource bounds, corpus/key/text
order, metadata/excerpt schema, BM25 invocation, issuer grouping/ranking,
rounding, result limit, interpretation, and exact caveats.

### G5 invariants

- Each module, claim, and QA-finding scan is newest-first and independently
  capped at 2,000 rows. Unfiltered run history cannot create unbounded in-request
  BM25 work.
- An issuer filter matching no rows becomes `['__none__']`, never an unfiltered
  scan. Module filters apply identically to modules, claims, and findings.
- Module runtime output is JSON serialized with `ensure_ascii=False` and sliced
  to 2,000 characters before tokenization; large CP-1 payloads cannot defeat the
  row cap.
- Corpus insertion order remains modules, claims, findings in database order;
  BM25 receives exactly that bounded corpus and `k=spec.limit`.
- Search metadata retains issuer ID/name/ticker/industry/country, result kind,
  title, sub-label, and the exact analyst-visible excerpt text.
- Each issuer exposes at most two excerpts, in hit order; issuer score is the
  maximum hit score, rounded to three decimals after issuer resolution.
- Rows sort descending by score and apply the validated result limit. Empty and
  non-empty caveats remain distinguishable and exact.
- This path is qualitative. It must not invent yield/day-count/covenant/
  waterfall calculations or present QA findings as quantitative financial
  scores; the caveat explicitly describes BM25 relevance.

### Baseline verification

Command:
`caos/server/.venv311/bin/python -m pytest caos/tests/server/test_nlquery.py caos/tests/server/test_query_watchlist.py caos/tests/server/test_query_answer.py caos/tests/server/test_query_overlay.py caos/tests/server/test_query_insights.py caos/tests/server/test_query_accepted_links.py -q`

Baseline result: **64 passed, 2 warnings in 3.40s**.

### Tournament result

Incumbent: defended the exact three-query ordering, 2,000-row scan bounds,
2,000-character JSON head, BM25 input order, two-excerpt cap, stable score
ordering, and two public Query routes. The principal risk was changing ranked
text or resource bounds while apparently only reorganizing local variables.

Anonymous bracket:

1. **Speed A vs Memory B — B won.** B preserves the literal
   `json.dumps(..., ensure_ascii=False)[:2000]` path, processes capped result
   sets sequentially instead of retaining all three ORM row sets, and avoids
   the streamed-encoder prefix-equivalence risk introduced by A.
2. **Memory A vs Readability B — A won.** B was shorter, but retained the three
   row collections and repeated unused `setdefault` allocations; A had similar
   clarity with materially lower peak retention and exact query/text behavior.
3. **Memory A vs Incumbent B — A won.** A changes no public contract or ranked
   text, preserves module/claim/finding and hit order, and reduces peak live
   data with modest, locally obvious lifecycle changes.

**Winner: Snippet A (Memory)**, replacing
`caos/server/nlquery.py:609-769`.

Justification:

- It never holds modules, claims, and findings concurrently with their complete
  corpus/meta projections; each capped query is consumed before the next.
- It preserves exact JSON serialization, SQL filters/order/limits, BM25 corpus,
  issuer grouping, scores, excerpts, and caveat strings.
- The resource improvement is maintainable: one statement variable, explicit
  segment order, and prompt release of corpus/meta/hit intermediates.

### Orchestrator verification

- Scratch file: `/tmp/caos-g5-memory-019f67d3/nlquery.py`; production source was
  not changed.
- Syntax and scratch diff were inspected; the replacement is confined to the
  target function.
- Focused/caller command:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g5-memory-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g5-memory-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g5-memory-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_nlquery.py caos/tests/server/test_query_watchlist.py caos/tests/server/test_query_answer.py caos/tests/server/test_query_overlay.py caos/tests/server/test_query_insights.py caos/tests/server/test_query_accepted_links.py -q`
- Result: **64 passed, 2 warnings in 3.47s**.
- Full server command:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g5-full-rerun-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g5-full-rerun-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g5-memory-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server -q`
- Result in the restricted sandbox: **1,829 passed, 9 skipped, 7 failed in
  76.96s**. All seven failures were the known loopback-bind `PermissionError`
  cases in `test_avscan.py`; no candidate or caller assertion failed.
- Sandbox-control rerun with the same scratch `PYTHONPATH`, outside the socket
  restriction: `caos/server/.venv311/bin/python -m pytest caos/tests/server/test_avscan.py -q`
  returned **8 passed in 0.18s**.
- Live route spot-check: a fresh SQLite database created and completed a real
  Atlas Forge run, then `POST /api/query/nl` with `what did the CP-1 module
  conclude` returned `mode=synthesis`, one issuer row, two excerpts, and the
  exact qualitative BM25 caveat. This exercises `routes/query.py::nl_query` and
  the executor against persisted module output.
- Financial-invariant check: the qualitative path still emits no yield,
  day-count, covenant, or waterfall value; it labels ranking as BM25 relevance
  and maintains the explicit two-excerpt/eight-row bounds.

Final replacement code is preserved at
`.agent-reviews/adversarial-candidates/g5_execute_synthesis_memory.py`; it is
not applied to production source by this review.

## G6 — Portfolio/desk decisions

### Target and impact set

Target: `caos/server/engine/portfolio.py::compute_portfolio_analytics`, source
lines 291-414 (GitNexus envelope 290-413).

- Exact UID: `Function:caos/server/engine/portfolio.py:compute_portfolio_analytics`.
- GitNexus upstream impact: LOW, no resolved incoming symbols. Native search is
  authoritative for the graph miss and finds two live callers:
  `routes/portfolios.py:657` (Portfolio Lab analytics) and
  `routes/committee.py:747` (committee evidence snapshot), plus direct tests at
  `test_portfolio_lab_backend.py:106` and `:176`.
- Downstream impact: MEDIUM, 21 symbols (12 direct, 8 at depth 2, 1 at depth 3)
  across Engine and Server. Direct dependencies include
  `is_finite_number`, `checked_add`, `checked_multiply`, `checked_divide`,
  `_rounded`, `_is_positive_number`, `_bounded_missing`,
  `normalize_portfolio_as_of`, `portfolio_authority`,
  `position_market_value`, `compute_exposure`, and `check_constraints`.

Contract: preserve the exact four-argument boundary and dict schema; checked
arithmetic/failure propagation; position, rating, maturity, and compliance
ordering; missing-dependency append/deduplication semantics; distribution and
response caps; authority and as-of linkage; and caller-visible NAV/liquidity
meaning.

### G6 financial invariants

- Every CP-1-derived or holding-derived multiplication/division is finite-guarded
  through checked helpers; zero or failed NAV degrades to `None` and names the
  missing denominator instead of emitting `NaN`/infinity.
- `finite_nav` includes every finite market value (par when price is absent),
  while `priced_nav` includes only holdings with a positive finite price. These
  denominators cannot be merged.
- Rating exposure prefers Moody's, then S&P, then `Unrated`; percentages use the
  same finite NAV, round to eight decimals, sort descending, and retain the
  bounded `Other` remainder.
- Maturity buckets accept the first four-digit 20xx year, preserve checked-add
  overflow reporting, sort chronologically, and expose at most 20 years.
- Constraint results preserve Breach/Watch/Pass/Info counts, first-50 headroom,
  first-100 compliance, and the same current/limit/headroom values.
- Portfolio authority and normalized `as_of` describe exactly the holdings and
  constraints aggregated. Unsupported history remains explicit at the route.
- This aggregate performs no yield/day-count/cashflow-waterfall calculation;
  its relevant covenant invariant is that constraint compliance and headroom are
  computed once from the same exposure snapshot returned to both callers.

### Baseline verification

Command:
`DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g6-baseline-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g6-baseline-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_portfolio.py caos/tests/server/test_portfolio_run.py caos/tests/server/test_portfolios.py caos/tests/server/test_portfolio_lab_backend.py caos/tests/server/golden/test_golden_portfolio.py caos/tests/server/test_ic_book.py -q`

Baseline result: **46 passed, 2 warnings in 4.75s**.

### Tournament result

Incumbent: defended the separate finite/priced NAV accumulators, checked
arithmetic degradation, rating and maturity ordering, compliance/headroom caps,
authority/as-of coupling, and explicit missing-dependency contract used by both
Portfolio Lab and committee snapshot callers.

Anonymous bracket:

1. **A vs B — B won.** B eliminated the second position scan and duplicate
   as-of normalization, used in-place rating truncation, and avoided A's dense
   hot-helper aliasing while preserving the checked-operation order.
2. **Prior winner A vs Readability B — A won.** A kept NAV, priced NAV, rating,
   and maturity transitions explicit; B's nested mutation helper was shorter but
   harder to audit and allocated more slices.
3. **Challenger A vs Incumbent B — A won.** A matched failure propagation,
   missing-dependency order, bounded schema, and authority while removing the
   redundant normalization, second scan, and common temporary collections.

**Winner: Snippet A (Memory)**, replacing
`caos/server/engine/portfolio.py:291-414`.

Justification:

- It counts unpriced positions during the required holdings pass and normalizes
  `as_of` once, reducing work without changing any financial operation.
- It truncates rating rows in place and avoids common headroom/maturity/
  compliance slice allocations while preserving observable value order.
- Checked math, zero-denominator degradation, compliance/headroom, authority,
  and missing-dependency semantics stay explicit and reviewable.

### Orchestrator verification

- Scratch file: `/tmp/caos-g6-memory-019f67d3/engine/portfolio.py`; production
  source was not changed. `py_compile` passed and the scratch diff is confined
  to the target function.
- Focused/caller command:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g6-memory-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g6-memory-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g6-memory-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_portfolio.py caos/tests/server/test_portfolio_run.py caos/tests/server/test_portfolios.py caos/tests/server/test_portfolio_lab_backend.py caos/tests/server/golden/test_golden_portfolio.py caos/tests/server/test_ic_book.py -q`
- Result: **46 passed, 2 warnings in 4.57s**. This includes both native callers,
  supported/unsupported as-of behavior, JSON-safe overflow degradation,
  distribution bounds, and committee snapshot behavior.
- Full server command:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g6-full-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g6-full-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g6-memory-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server -q`
- Result in the restricted sandbox: **1,829 passed, 9 skipped, 7 failed in
  78.09s**; all seven failures were the known AV loopback-bind restriction.
  The external control rerun with the same scratch path returned **8 passed in
  0.18s**.
- Financial spot-check: three holdings produced NAV `520.0`, B3 exposure
  `34.61538462%` (`180 / 520`), maturity wall
  `{'2027': 100.0, '2028': 180.0}`, priced NAV `100%`, and a single-name
  covenant current value `46.15%` against a `45%` cap, correctly classified
  `Breach` with `-1.15` headroom.
- Scope check: neither caller signature nor response schema changed; Portfolio
  Lab and committee remain on the same deterministic analytics snapshot.

Final replacement code is preserved at
`.agent-reviews/adversarial-candidates/g6_compute_portfolio_analytics_memory.py`;
it is not applied to production source by this review.

## G7 — Issuer analysis surfaces

### Target and impact set

Target: `caos/server/routes/issuers.py::get_issuer_profile`, source lines
678-788 (GitNexus envelope 677-787).

- Exact UID: `Function:caos/server/routes/issuers.py:get_issuer_profile`.
- GitNexus upstream impact: LOW, no resolved incoming symbols. This is an HTTP
  graph miss: native search confirms the public route, the frontend client at
  `caos/frontend/src/lib/api.ts:303`, focused issuer-profile tests, and the
  cross-tenant 404 assertion at `test_tenancy.py:117`.
- Downstream impact: **CRITICAL**, 19 symbols (7 direct, 9 at depth 2, 3 at
  depth 3), 76 affected process memberships, and Routes/Engine/Server modules.
  Direct dependencies are `get_db`, `better_fact`, `_profile_signals`,
  `_strengths_weaknesses`, `require_issuer`, `get_identity`, and
  `IssuerResponse.model_validate`.

Contract: preserve the async FastAPI signature and `IssuerProfileResponse`;
tenant-safe issuer resolution; bounded newest-run, latest-complete, and metric
fact queries; retained last-good facts with source-run as-of; run- and
module-level QA blocking; CP-0/1A/1B/2D surfaces; QA findings; `better_fact`
precedence; response/list order; and empty-state behavior.

### G7 financial invariants

- `latest_run` reports current workflow state, while `latest_complete` is the
  only run allowed to back signals and QA. They must not be collapsed.
- A newer blocked run suppresses raw module signals but does not erase retained
  QA-passed metric facts. Every retained point remains labeled with its own
  `run_id` and `source_run_as_of`.
- Whole-run QA/committee blocking suppresses all modules; otherwise individually
  blocked modules are excluded before any liquidity, covenant, RV, sponsor, or
  earnings field is read.
- Headline ratios use shared `better_fact` provenance and recency precedence so
  strengths/weaknesses agree with Query instead of allowing stale seed facts to
  shadow run/fixture facts.
- CP-0 coverage, CP-1A business facts, CP-1B earnings, CP-2D sponsor data, and
  QA findings all describe the exact selected complete run or degrade to empty
  structures. No cross-run synthesis is hidden.
- No yield/day-count/waterfall calculation occurs here. Relevant financial
  controls are provenance-preserving leverage/coverage inputs and fail-closed
  covenant/liquidity signal suppression.

### Baseline verification

Command:
`DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g7-baseline-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g7-baseline-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_issuer_profile.py caos/tests/server/test_tenancy.py -q`

Baseline result: **16 passed, 2 warnings in 2.28s**.

### Tournament result

Incumbent: defended tenant authorization, the deliberately separate newest and
latest-complete run semantics, last-good fact retention, run/module QA blocking,
source-run as-of labeling, shared `better_fact` precedence, bounded queries, and
the complete response schema used by the issuer UI.

Anonymous bracket:

1. **A vs B — B won.** B kept validation order and exact queries while avoiding
   redundant result-list copies, streaming module/finding/source-as-of rows, and
   making object lifetimes explicit.
2. **Prior winner A vs Readability B — A won.** B was shorter but retained the
   redundant materializations; A had better peak-space behavior without changing
   CP outputs, fact precedence, signal-run selection, or response order.
3. **Challenger A vs Incumbent B — A won.** A preserved the complete external
   contract while reducing intermediate collections and releasing ORM objects
   before final response construction.

**Winner: Snippet A (Memory)**, replacing
`caos/server/routes/issuers.py:678-788` (the existing route decorator at line
677 remains unchanged).

Justification:

- It removes duplicate bounded-result copies and consumes one-use module,
  finding, and source-date results as iterables.
- It preserves tenant resolution, SQL ordering/limits, current-versus-usable run
  separation, blocked-signal suppression, last-good facts, and provenance.
- The prebuilt response rows and explicit release points reduce peak retention
  without hiding the financially sensitive selection rules.

### Orchestrator verification

- Scratch file: `/tmp/caos-g7-memory-019f67d3/routes/issuers.py`; production
  source was not changed. `py_compile` passed and the scratch diff is confined
  to the target function. A namespace-package shim let the scratch route replace
  only `routes.issuers` while all other route modules came from production.
- Focused/caller command:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g7-memory-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g7-memory-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g7-memory-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_issuer_profile.py caos/tests/server/test_tenancy.py -q`
- Result: **16 passed, 2 warnings in 2.34s**. This covers public HTTP behavior,
  tenant 404s, no-run empties, completed-run rollups, blocked-signal exclusion,
  retained fact source dates, ratings ingestion, and deterministic covenant/
  strength rules.
- Full server result with the scratch path: **1,826 passed, 9 skipped, 10
  failed in 81.16s**. Seven were the known AV loopback restriction; the external
  AV control returned **8 passed in 0.17s**. Three additional failures were
  differentially audited rather than attributed to the candidate.
- Differential control command ran the FUN golden plus two CP-1 grounding cases
  once with production `PYTHONPATH` and once with the scratch path on fresh
  databases. Both environments returned the identical result: the two grounding
  cases passed and FUN failed because current code reports
  `qa_status=Restricted` while the golden expects `Passed`. Thus the candidate
  introduced no additional failing assertion.
- Financial/provenance spot-check: the focused last-good test retained an
  accepted FY2025 leverage fact (`4.2x`) with its accepted run ID and
  `source_run_as_of=2025-12-31`, while a newer blocked complete run remained the
  signal-run ID and its one-month liquidity output was suppressed to `None`.

Final replacement code is preserved at
`.agent-reviews/adversarial-candidates/g7_get_issuer_profile_memory.py`; it is
not applied to production source by this review.

## G8 — Reports/exports/charts

### Target and impact set

Target: `caos/server/report_exports.py::render_report_xlsx`, source lines
256-595 (GitNexus envelope 255-594).

- Exact UID: `Function:caos/server/report_exports.py:render_report_xlsx`.
- Upstream impact: MEDIUM, 9 direct dependants and one process: the live
  `routes/reports.py::export_report_version` route plus eight focused XLSX tests.
- Downstream impact: MEDIUM, 12 dependencies (11 direct, 1 at depth 2).
  Direct helpers are `_display`, `_xlsx_text`, `_xlsx_scalar`,
  `_model_reporting_metadata`, `_instrument_currencies`,
  `_model_override_rows`, `_rows`, `_safe_sheet_name`, `_reviewed_report`,
  `_reviewed_rows`, and `_style_xlsx_header`.

Contract: preserve the keyword-only signature and returned workbook bytes;
sheet names/order, cell values/types/styles, model and debt fields, currencies
and units, override event-time status, immutable authority/hashes, reviewed
composition precedence, audit sources, formula-injection neutralization,
formula-free structural reopen, and route content/hash headers.

### G8 financial invariants

- The renderer copies one frozen report payload; it never recalculates revenue,
  EBITDA, interest, debt, cash, leverage, coverage, FCF, or debt roll-forwards.
- Model cells preserve exact typed values. Debt opening/closing/average,
  benchmark/margin/coupon/fee/PIK/hedge/FX/cash-interest components and
  roll-forward residual remain in the labeled reporting unit, while converted
  debt is separately labeled with reporting currency/scale.
- Override rows are evaluated at the report event and retain active/inactive
  state, value, reason, scope, source, expiry, displaced formula, and displaced
  value. The renderer does not replay an override.
- Reviewed report composition replaces superseded raw module prose but never
  removes the independently frozen model, debt, gap/warning, or source audit.
- Version ID, document SHA-256, authority, freshness, model fingerprints/hash,
  draft revision, and source IDs remain visible and tied to the exact export.
- Every analyst-controlled text surface is formula-neutralized, numeric/boolean
  cells stay typed, and a reopened workbook must contain Cover and Module
  Summary and no formula cells.
- Yield/day-count conventions are not recalculated here. Any such fields are
  inert frozen values; the protected cashflow invariant is exact debt and
  interest component round-trip, including PIK and roll-forward residual.

### Baseline verification

Command:
`DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g8-baseline-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g8-baseline-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_report_exports.py caos/tests/server/test_model_v2_report_identity.py -q`

Baseline result: **18 passed, 4 warnings in 3.21s**.

### Tournament result

Incumbent: defended mutation order, immutable report identity, reviewed-prose
precedence, exact typed model/debt/override values, sheet order and safe names,
formula neutralization, audit sources, and the save/reopen/formula scan.

Anonymous bracket:

1. **A vs B — B won.** B kept the established control flow, streamed module
   summaries, deferred/released auxiliary structures, and avoided the duplicate
   XLSX buffer; A's method aliases were less direct despite its speed evidence.
2. **Prior winner A vs Readability B — A won.** B was byte-identical to the
   incumbent and offered no improvement; A lowered allocation without changing
   workbook structure or the keyword/bytes contract.
3. **Challenger A vs Incumbent B — A won.** A removed repeated style-object and
   flattened-row allocations while preserving all identity, financial, audit,
   and formula-free validation behavior.

**Winner: Snippet A (Memory)**, replacing
`caos/server/report_exports.py:256-595`.

Justification:

- It streams `_rows`, shares immutable OpenPyXL style objects, defers the debt
  currency map, and releases the rendered override ledger.
- It reopens the existing output buffer rather than cloning the complete XLSX
  package, while retaining the mandatory-sheet and no-formula checks.
- Exact model/debt/override values, sheet order, styles, authority, hashes,
  security neutralization, and returned bytes are preserved.

### Orchestrator verification

- Scratch file: `/tmp/caos-g8-memory-019f67d3/report_exports.py`; production
  source was not changed. `py_compile` passed and the diff is confined to the
  target function.
- Focused/caller command:
  `DATABASE_URL=sqlite+aiosqlite:////tmp/caos-g8-memory-019f67d3.db CAOS_STORAGE_DIR=/tmp/caos-g8-memory-019f67d3-vault CAOS_TEST=1 CAOS_DEMO_SEED=true PYTHONPATH=/tmp/caos-g8-memory-019f67d3:caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_report_exports.py caos/tests/server/test_model_v2_report_identity.py -q`
- Result: **18 passed, 4 warnings in 8.14s**. Direct rendering, live export
  route, immutable hash, tenant/tamper controls, reviewed composition, exact
  model identity, partial/gap output, and formula-injection cases all passed.
- Same-process orchestrator comparison on the model-v2 payload produced exactly
  equal bytes (`13,434` each) and the same SHA-256
  `7528c6d5440990d68179f5f985a5fed4740cd08afe52f81e58062063218a607b`.
  Five five-render samples gave a median candidate/incumbent runtime ratio of
  **0.689**.
- Full server result with the scratch path: **1,824 passed, 9 skipped, 15 failed
  in 84.19s** during active parallel WIP. The candidate-target tests remained
  clean. A fresh differential control reran the six still-existing non-AV failed
  selectors with production and scratch paths: both returned the identical four
  current failures and two passes. Two full-run test names disappeared/changed
  before the control, further confirming concurrent test edits rather than a
  report-renderer regression. The current external AV control returned **9
  passed in 0.18s**.
- Financial spot-check: the model-v2 XLSX retained GBP/millions headers; exact
  opening, closing, average, benchmark, margin, PIK, converted debt and
  roll-forward residual cells; active/inactive event-time overrides; calculation
  hash; and zero formula cells after reopening.

Final replacement code is preserved at
`.agent-reviews/adversarial-candidates/g8_render_report_xlsx_memory.py`; it is
not applied to production source by this review.

## G9 — Shared frontend shell

### Target and impact set

Target: `caos/frontend/src/components/shared/NavigationGuardProvider.tsx::NavigationGuardProvider`,
source lines 53-222 (GitNexus envelope 52-221).

- Exact UID:
  `Function:caos/frontend/src/components/shared/NavigationGuardProvider.tsx:NavigationGuardProvider`.
- Upstream impact: **HIGH**, 8 dependants (6 direct, 2 at depth 2), one affected
  RootLayout process, and four frontend modules. Direct graph/native callers
  include `app/layout.tsx::RootLayout` and the model, hotkey, navigation-guard,
  and command-palette test harnesses.
- Downstream impact: LOW, 6 symbols (3 direct, 2 at depth 2, 1 at depth 3), one
  RootLayout process, and two modules. Direct dependencies are `historyIndex`,
  `withHistoryIndex`, and `NavigationConfirmDialog`; the function also owns the
  browser-history wrappers and pending-navigation state.
- Native consumers outside the function graph are
  `ModelV2Workbench.tsx::useNavigationGuard`, `ConceptHotkeys` and
  `CommandPalette` via `useNavigationAttempt`, plus root layout installation.

Contract: preserve the exported component/context boundary; guard registration
and snapshot semantics; synchronous discard callbacks; pending-attempt
exclusivity; `beforeunload` lifecycle; same-origin anchor exclusions and pushed
URL; Back/Forward index tagging, bounce, resume, and forward-stack preservation;
history cleanup/restoration; and modal focus/Escape/ARIA behavior.

### G9 invariants

- Clean or disabled guards never install `beforeunload` and programmatic
  navigation proceeds synchronously. Dirty enabled guards always require a
  user-owned confirmation; no autosave occurs.
- A queued request snapshots its active guards. A transient rerender/unmount
  during history bounce cannot erase the discard callback that owned the
  original navigation attempt.
- Discard callbacks run before navigation, synchronously and independently; one
  faulty callback cannot trap the user or suppress other discards.
- Modified clicks, downloads, non-self targets, cross-origin links, and
  same-document pathname/search links retain native behavior. Ordinary
  same-origin route links preserve pathname, search, and hash in `router.push`.
- SPA history entries retain caller state plus a monotonic internal index. Back
  and Forward are bounced to the current entry before the dialog opens and are
  resumed exactly once only after discard, preserving the forward stack.
- Cleanup removes listeners and restores `pushState`/`replaceState` only if the
  provider still owns those wrappers.
- The confirmation is an accessible modal: labeled/described dialog, focus
  trap, visible actions, Escape/backdrop means Stay, and focus restoration.
- No financial calculation occurs here. The financially relevant invariant is
  that unsaved model/report overrides are never silently saved or discarded.

### Baseline verification

Command from `caos/frontend`:
`npm test -- src/components/shared/NavigationGuardProvider.test.tsx src/components/shared/ConceptHotkeys.test.tsx src/components/shared/CommandPalette.navigation-guard.test.tsx src/app/model/model-v2-workbench.test.tsx`

Baseline result: **4 files passed, 40 tests passed in 3.87s**.

### Tournament result

Incumbent: defended the deliberately coupled history-index/bounce state
machine, insertion-ordered guard snapshots, synchronous isolated discards,
pending-attempt exclusivity, and ownership-safe restoration of patched History
methods. These behaviors protect unsaved model state across native anchors,
palette/hotkey navigation, and Back/Forward traversal.

Anonymous bracket:

1. **A vs B — A won.** A collects one insertion-ordered guard snapshot for an
   intercepted anchor and passes it through the queued attempt; B scans again
   inside its attempt helper, making the event decision and dialog snapshot
   vulnerable to different render-time states.
2. **Prior winner A vs Readability B — A won.** B was shorter, but it retained
   the double scan; A's explicit snapshot parameter better preserves the exact
   guards that caused interception.
3. **Challenger A vs Incumbent B — A won.** Both preserve the complete history
   state machine and cleanup contract, while A eliminates the incumbent's
   second anchor-path guard scan and avoids `Array.from(...).filter(...)`.

**Winner: Snippet A (Speed)**, replacing
`caos/frontend/src/components/shared/NavigationGuardProvider.tsx:53-222`.

Justification:

- It takes one insertion-ordered active-guard snapshot per intercepted anchor
  and uses that same snapshot for the pending dialog and discard callbacks.
- It removes `Array.from(...).filter(...)` and avoids allocating a guard array
  merely to synchronize the active count.
- It preserves the exported one-argument context contract, all native-link
  exclusions, pending exclusivity, discard isolation, and the incumbent's
  history-index/bounce/cleanup state machine.

### Orchestrator verification

- Scratch module:
  `caos/frontend/src/components/shared/NavigationGuardProvider.g9scratch.tsx`
  during verification; a temporary Vitest alias redirected only the relative
  provider import. Both harness files were deleted after the run. Production
  source was not changed.
- Focused/caller command from `caos/frontend`:
  `./node_modules/.bin/vitest run --config .scratch-g9-vitest.config.ts src/components/shared/NavigationGuardProvider.test.tsx src/components/shared/ConceptHotkeys.test.tsx src/components/shared/CommandPalette.navigation-guard.test.tsx src/app/model/model-v2-workbench.test.tsx`
- Focused result: **4 files passed, 40 tests passed in 5.94s**. This covers
  direct navigation, dirty/disabled guards, same-origin anchor filtering,
  discard failures, pending exclusivity, palette/hotkey callers, Back/Forward
  bounce/resume, and unsaved Model Builder state.
- Full scratch command:
  `./node_modules/.bin/vitest run --config .scratch-g9-vitest.config.ts`
- Full result: **163 files passed, 891 tests passed in 21.44s**.
- Type command: `./node_modules/.bin/tsc --noEmit --incremental false` returned
  exit **2** with six missing-`AnalysisContext.revision` errors confined to
  `components/upload/context.test.ts` and
  `UploadWizard-context-order.test.tsx`. Removing the candidate alias and
  scratch module produced the exact same six errors, so the differential
  control attributes none to the winner.
- Caller re-check: RootLayout installation, ModelV2Workbench registration,
  `ConceptHotkeys`, and `CommandPalette` all retained the same exported context
  types and passed their focused tests. The full suite additionally exercised
  every frontend consumer under the scratch alias.
- Financial-state spot-check: the Model Builder caller test kept local input
  and derived overrides uncommitted until an explicit atomic commit; navigation
  remained blocked while that local state was dirty, so the rewrite did not
  introduce autosave or silent discard.

Final replacement code is preserved at
`.agent-reviews/adversarial-candidates/g9_navigation_guard_speed.tsx`; it is not
applied to production source by this review.

## G10 — QA/bench/scripts/tooling

### Target and impact set

Target: `caos/scripts/check_complexity_delta.py::main`, source lines 209-229
(GitNexus envelope 208-228).

- Exact UID: `Function:caos/scripts/check_complexity_delta.py:main`.
- Upstream impact: LOW, one direct file entry-point caller.
- Downstream impact: MEDIUM, 10 symbols (5 direct, 4 at depth 2, 1 at depth 3)
  in Scripts. Direct dependencies are `_arguments`, `_changed_python_paths`,
  `_load_baseline`, `_run_ruff`, and `_assess_findings`.
- Native callers add `.github/workflows/ci.yml:80`, where pull requests invoke
  the script after a full-history checkout, and focused unit tests in
  `caos/tests/server/test_complexity_delta.py`.

Contract: preserve argument parsing, base-ref diff scope, baseline path
resolution, fail-closed exception handling, helper call order/data flow, exact
stdout/stderr messages, and exit codes: `0` clean, `1` policy findings, `2`
unsafe inputs/tool errors.

### G10 invariants

- Only Python paths changed between the requested base and `HEAD` are assessed;
  `.venv` and `.goal` remain excluded and paths with spaces remain atomic.
- The schema-validated baseline is exact path+symbol debt, not a blanket waiver:
  new, worse, lower/stale, and removed findings are all reported as policy
  problems.
- Ruff output is accepted only for return codes 0/1, valid JSON-list C901
  findings, the configured threshold, repository-contained paths, and unique
  path/symbol keys. Ambiguity fails closed with exit 2.
- The ordered helper pipeline and outputs are CI contracts. A findings result
  must print the heading plus every problem and return 1; a clean result reports
  bounded finding and changed-path counts and returns 0.
- No financial math occurs here. The financial safety invariant is indirect:
  this gate must not silently waive new complexity in engine functions that
  implement yields, covenants, finite guards, or cashflow waterfalls.

### Baseline verification

- Unit command:
  `PYTHONPATH=caos/server caos/server/.venv311/bin/python -m pytest caos/tests/server/test_complexity_delta.py -q`
  returned **2 passed in 0.02s**.
- Real CI-equivalent command:
  `caos/server/.venv311/bin/python caos/scripts/check_complexity_delta.py --base-ref origin/main --ruff caos/server/.venv311/bin/ruff`
  returned exit **1** and the exact current-WIP policy finding:
  `complexity increased: caos/server/routes/runs.py::create_run (13 > 12)`.

### Tournament result

Incumbent: defended the compact, load-bearing helper sequence, deliberately
uncaught `_arguments()`/`SystemExit`, fail-closed exception boundary, exact CI
messages, and tri-state return contract. Moving argument parsing or changing
helper order would alter observable failure behavior; broader streaming would
require changing helper contracts in the impact set.

Anonymous bracket:

1. **A vs B — A won.** A was byte-for-byte and AST-equivalent to the incumbent;
   B's manual `del` statements did not reduce the unavoidable assessment peak
   and made local lifetimes fragile.
2. **Prior winner A vs Readability B — A won.** B preserved behavior but grew a
   direct 21-line pipeline to 32 lines without a complexity or maintenance win.
3. **Challenger A vs Incumbent B — B won.** The two snippets were identical, so
   the challenger supplied no measurable merit and a no-op replacement was
   rejected.

**Winner: Snippet B (Incumbent)** — retain
`caos/scripts/check_complexity_delta.py:209-229` unchanged.

Justification:

- It is already the shortest clear expression of the ordered five-helper
  pipeline and its clean/policy/error exit paths.
- No challenger improved asymptotic time or peak space without either being
  identical or adding manual lifetime management and visual weight.
- Keeping the original preserves argparse propagation, helper order, exact
  stdout/stderr, and exit codes without a meaningless source diff.

### Orchestrator verification

- Scratch copy:
  `/tmp/caos-g10-incumbent-019f67d3/caos/scripts/check_complexity_delta.py`.
  Its SHA-256 and the production file's SHA-256 were both
  `d125c9b38efe2719f97dd8362868415d2ccc5e39102cbce12a8e409da947c526`.
- Focused command:
  `caos/server/.venv311/bin/python -m pytest caos/tests/server/test_complexity_delta.py -q`
  returned **2 passed in 0.02s**.
- Orchestrator scratch harness:
  `caos/server/.venv311/bin/python /tmp/g10_orchestrator_verify.py` returned
  **pass** for clean, policy-finding, gate-error, and uncaught-argparse paths,
  including exact helper order, streams, and 0/1/2 results. It also spot-checked
  bounded, new, worse, lower, and removed/stale assessment cases.
- Live CI-equivalent command:
  `caos/server/.venv311/bin/python caos/scripts/check_complexity_delta.py --base-ref origin/main --ruff caos/server/.venv311/bin/ruff`
  returned exit **0** with
  `Complexity delta gate passed: 20 bounded finding(s) across 102 changed Python path(s).`
  The earlier baseline's exit-1 `create_run (13 > 12)` finding disappeared after
  the parallel checkout advanced; the final verification records current state.
- Caller re-check: the file entrypoint still passes `main()` directly to
  `sys.exit`, and the GitHub workflow invokes the same script and arguments.
  No yield/day-count/covenant/waterfall implementation is called or altered;
  the live gate's 20 bounded findings confirm the financial-engine complexity
  debt remains explicitly assessed rather than silently waived.

The retained code is mirrored at
`.agent-reviews/adversarial-candidates/g10_check_complexity_delta_incumbent.py`
for the requested final-code output. Production remains unchanged.

## Overall disposition

| Group | Verified winner | Production action |
|---|---|---|
| G1 Core CP engine | Snippet A — Speed | Candidate only |
| G2 Model/workbook projections | Snippet A — Readability | Candidate only |
| G3 API/auth/tenancy/persistence | Snippet A — Readability | Candidate only |
| G4 Ingestion/lineage/pipeline | Snippet A — Speed | Candidate only |
| G5 Query/research/LLM safety | Snippet A — Memory | Candidate only |
| G6 Portfolio/desk decisions | Snippet A — Memory | Candidate only |
| G7 Issuer analysis surfaces | Snippet A — Memory | Candidate only |
| G8 Reports/exports/charts | Snippet A — Memory | Candidate only |
| G9 Shared frontend shell | Snippet A — Speed | Candidate only |
| G10 QA/bench/scripts/tooling | Snippet B — Incumbent | Keep original |

The complete verified replacement code, including the retained G10 incumbent,
is in [`adversarial-final-code.md`](adversarial-final-code.md), with one fenced
block per group. Individual raw candidates remain under
`adversarial-candidates/` for machine-readable follow-up.

No candidate was applied to production. A future remediation pass should be
separately authorized and should re-run current-HEAD GitNexus impact because
the checkout advanced during this review. The reported scratch tests are the
correctness authority for these candidates; the code graph is discovery
authority only.
