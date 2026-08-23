# Hybrid CP-DR Phase 4 implementation report

Date: 2026-08-23

Scope: bounded issuer-only CP-DR provider execution, host validation, and canonical vendored handoff

Base: `78abc14` — `fix(frontend): ship Inter and JetBrains Mono via next/font`

Implementation commit: `ae0400a` — `feat(server): execute bounded CP-DR research`

Remediation commit: `be242e1` — `fix(server): harden CP-DR execution boundaries`

Second remediation commit: `2bb8af6` — `fix(server): close CP-DR second review gaps`

Third remediation commit: `131713e` — `fix(server): close Phase 4 third review gaps`

Fourth remediation commit: `1f400d8` — `fix(server): make CP-DR finalization atomic`

## Status

Corrected after four independent review rejections. Commits `ae0400a..a8005f3`
and the first three remediation passes were rejected because their
verification missed critical cross-process recovery, canonical-artifact,
host-provenance, completion-time, terminal-telemetry, manifest-allocation, and
installed-SDK roots, followed by final-success atomicity, normalized-row drift,
and incomplete post-interaction terminalization. Earlier implementation/test
narratives below are historical evidence only; the fourth-remediation addendum
at the end is the current result and is pending fresh independent review.

After `be242e1`, an approved FULL issuer CP-DR run executes through one concrete
Anthropic Messages/client-tool loop only when the server flag, original run
case/creator pilot allowlist, exact plan/source/model/methodology identity, and
accepted CP-0 lineage all pass. The host owns evidence access, durable spend,
typed validation, confidence, canonical Markdown, vendored handoff validation,
fencing, and persistence. No live provider or external document was used.

The corrected deterministic end-to-end test produces exactly one cited,
fenced, envelope-bound, vendored-validator-passing CP-DR artifact and accepts
its snapshot. Covered forced failures store a stable sanitized agent code and
create no fallback artifact; the complete corrected matrix is recorded below.

## Impact and architecture gate

Pre-edit GitNexus impact was run before every existing symbol edit:

- `Settings`: MEDIUM, five direct dependents; `Settings.from_env`: LOW.
- `DeployVBundle`: LOW; `DeployVBundle.__init__`: LOW.
- `AnthropicGateway`: LOW.
- `WorkflowRuntime`, `__init__`, `_execute`, `_build_artifact_with_slot`, and
  `_build_artifact`: LOW.
- New Phase-4 symbols were absent from the pre-change index. Live callers were
  checked in the repository; attempt-local callbacks flow only through
  `_execute` → `_build_artifact_with_slot` → `_build_artifact` → `_execute_cpdr`.
- No HIGH or CRITICAL indexed symbol was edited.

The architecture remains Ponytail-full: one concrete gateway, one evidence
tool, the existing runtime/store/fence machinery, one process-local provider
semaphore, one existing durable research ledger, and no provider interface,
factory, framework, dynamic DAG, or generic fallback.

## Implementation

- Added strict nested `CPDRPayload` transport models with forbidden extras,
  finite and type-strict numbers, bounded strings/lists, exact host identity,
  unique workstream/claim/evidence identities, claim-to-finding integrity,
  numeric-context enforcement, evidence independence, host coverage arithmetic,
  visible conflicts, and coherent gap/status/stop semantics.
- Evidence rows and citations must match blocks actually returned in this run,
  including source digest, canonical locator, extractor version, and source
  confidence. A valid source/block pair cannot carry fabricated metadata.
- Added host-derived confidence inputs and canonical CP-DR Markdown with the
  required filename, frontmatter, and six H2 sections. The runtime calls the
  actual vendored `confidence_score.py::compute` and
  `validate_handoff.py::validate_text`; provider-authored Markdown is never
  persisted.
- Added safe Python 3.14-compatible dynamic vendored-script loading: stable
  path-derived module names are registered before execution, removed on failure,
  and cached only after a successful load.
- Added immutable CP-DR research authority and separate explicitly untrusted
  bounded user content containing only the brief/identity, exact approved plan,
  upstream digests, and source metadata manifest.
- Rewrote the concrete `AnthropicGateway` against the verified 1.0.0 API:
  top-level system, one strict `read_evidence` client tool, disabled parallel
  tools, transformed strict output schema under `output_config`, complete
  assistant-content preservation, immediate tool-result ordering, exact request
  hashing, and one tool-disabled bounded repair.
- The gateway checks the lease before and immediately after every SDK call,
  acquires the semaphore before charging tokens, records every returned/rejected
  interaction without bodies, validates integer non-negative token counts, and
  permits one application-owned identical-request retry only for documented
  timeout/connection/rate/retryable status exceptions.
- Runtime authority binds the approved plan hash, Deploy V build, brief, scope,
  upstream artifacts, configured model, current exact pinned source set/version,
  and accepted CP-0 run/source lineage. Pilot eligibility uses the original run
  creator, never the approval/worker actor.
- Attempt-local fenced callbacks are passed explicitly down the node call chain;
  there is no shared run-ID callback map that a replacement claimant can
  overwrite. Lost leases remain silent and stale results cannot reconcile,
  record, or persist.
- The existing durable ledger enforces eight turns, twelve evidence reads, 1 MiB
  returned evidence, 100,000 input tokens, 8,000 output tokens, three active
  minutes, one provider retry, one repair, and two process-local concurrent
  calls. Counted input and requested output reserve before send; successful
  usage reconciles; unknown usage remains charged; reclaimed unresolved
  in-flight spend fails closed.
- The sole evidence executor validates case ownership, exact pin/version,
  withdrawal, unique bounded block IDs, block existence, and read/byte/time
  budgets before returning source/block metadata and text. It never returns or
  persists `vault_path`.
- Operational persistence is limited to bounded identifiers, digests, request
  IDs, source/block IDs, counts, latency, retry, stop reason, and stable terminal
  code. Prompts, transcripts, evidence/tool-result text, exception bodies, hidden
  reasoning, and the key are excluded.
- Added safe-default settings and strict environment parsing. Execution defaults
  off; empty allowlists deny all; missing key is explicit. Ordinary pathways are
  unchanged.

## Exact implementation files

- `.agent-reviews/redteam.md` — Phase-4 append only; the adjacent frontend team
  entry remained unstaged.
- `caos/server/caos/config.py`
- `caos/server/caos/methodology/bundle.py`
- `caos/server/caos/methodology/cpdr.py`
- `caos/server/caos/methodology/prompt.py`
- `caos/server/caos/workflows/domain.py`
- `caos/server/caos/workflows/provider.py`
- `caos/server/requirements.txt`
- `caos/tests/test_cp_dr_planning.py`
- `caos/tests/test_cp_dr_runtime.py`
- `caos/tests/test_run_launcher.py`

Deliberately untouched/unstaged: controller-owned
`.superpowers/sdd/progress.md` and all concurrent frontend work under
`caos/frontend/`.

## TDD red/green evidence

1. Initial Phase-4 collection was RED with `ModuleNotFoundError:
   caos.methodology.cpdr`; production transport/runtime code did not exist.
2. The first focused implementation gate became GREEN at 42 passed, 5 skipped,
   then the expanded planning/settings/runtime gate reached 55 passed, 5 skipped.
3. The explicit exit matrix for authority changes, unresolved in-flight spend,
   source/block eligibility, every durable ceiling, in-flight lease loss,
   locator/gap/coverage/conflict semantics, and persistence secrecy reached 119
   passed, 6 skipped.
4. Negative provider token values were RED at 3 failures, then GREEN at 3 passed
   after fail-closed validation.
5. Concatenated numeric notation, unknown HTTP status, and fractional token usage
   produced the expected RED (3 failures, 3 passes), then all six cases were
   GREEN after the fixes.
6. Type coercion was RED when `coverage_score="100"` and boolean numeric values
   were accepted; strict transport configuration made the regression GREEN.
7. Final required CP-DR runtime gate: 67 passed, 5 PostgreSQL-gated skips. The
   full DSN-backed suite has no skips: 200 passed.

Tests use the smallest local fake client/block types and exercise the real host
validation, vendored scorer/validator, store, workflow, snapshot, and failure
records. No test contacts Anthropic.

## Dependency review

- Added `anthropic>=1,<2`; installed/verified version is `1.0.0`.
- Official local signatures used: `messages.count_tokens`, `messages.create`,
  top-level `system`, `transform_schema`, `output_config`, strict client tools,
  `_request_id`, `usage`, and `stop_reason`.
- Direct runtime requirements reported by package metadata: `anyio<5,>=3.5.0`,
  `docstring-parser<1,>=0.15`, `httpx2<3,>=2.0.0`, `jiter<1,>=0.4.0`,
  `pydantic<3,>=1.9.0`, `sniffio<2,>=1`, and
  `typing-extensions<5,>=4.14` (optional extras were not enabled).
- `pip check` returned `No broken requirements found.` No FastAPI pin was
  changed, and the security audit reported no dependency/code findings.

## Rewrite tournament

No-argument post-edit tournaments were run inline across every non-trivial
changed function, in two-symbol brackets as required by the skill:

- Configuration/prompt: `_strict_bool`, `_bounded_csv`, `Settings.from_env`,
  and `compile_cpdr_prompts`.
- Vendored authority: `DeployVBundle._load_cpdr_script`, `cpdr_confidence`, and
  `validate_cpdr_handoff`.
- Typed handoff: both numeric validators, `validate_cpdr_payload`,
  `confidence_inputs`, and `render_cpdr_markdown`.
- Provider: `AnthropicGateway.__init__` and `AnthropicGateway.run` (including
  its attempt-local provider-call logic).
- Runtime: `WorkflowRuntime.__init__`, `_execute`,
  `_build_artifact_with_slot`, `_build_artifact`, and `_execute_cpdr` with its
  fenced budget/evidence closures.

Each bracket included incumbent defense, speed, memory, and
readability/minimality challengers followed by an arbiter. Results:

- **Provider winner: challenger.** Treat SDK counts/usage as untrusted ledger
  inputs and reject negative, fractional, or boolean values. This was the only
  measured semantic improvement, applied with failing regressions first.
- **All other winners: incumbents hold.** Proposed helper extraction saved no
  provider calls or persistence boundaries, increased parameters across fenced
  state, or obscured ordering. The large `_execute_cpdr` remains intentionally
  cohesive because its closures share one attempt-local ledger and returned-
  evidence map; splitting them would recreate the callback/state ambiguity the
  implementation removes.
- No speculative abstraction or cosmetic rewrite was applied. Relevant focused
  tests and the full suite passed after the tournament.

GitNexus could not resolve the newly introduced `_execute_cpdr` or rewritten
gateway `run` in its pre-change index, so the tournament used the previously
reported LOW class/caller impacts plus live caller search and the deterministic
runtime matrix.

## Confidence review

Least-confident points, ranked and investigated to root cause:

1. **Durable usage could be reduced by malformed SDK numbers.** Adversarial
   negative/fractional values proved coercion/undercharging was possible.
   **Confirmed and fixed:** require integer, non-boolean, non-negative counted
   and actual usage before reservation/reconciliation.
2. **A material number could evade context when attached to a unit.**
   `USD100m` bypassed the prior token-boundary expression. **Confirmed and
   fixed:** any decimal digit in claim text requires explicit numeric value and
   entity/period/unit/perimeter; regression added.
3. **Unknown API status could be mislabeled as timeout.** A synthetic 302
   entered the non-retryable timeout tail. **Confirmed and fixed:** documented
   4xx map to rejection, documented retryable statuses/5xx map to timeout, and
   other status errors fail as output-invalid without body persistence.
4. **Strict schema might still coerce provider-authored types.** String coverage
   and boolean numeric values validated under default Pydantic coercion.
   **Confirmed and fixed:** strict nested model configuration; nested extras and
   oversize values are also exercised.
5. **Old/new claimants could share fenced callbacks.** Traced the full runtime
   call chain and replaced the earlier shared run-ID context with explicit
   attempt-local arguments. Replacement and SDK-return lease-loss tests prove
   stale work records nothing. **Verified fixed.**
6. **Plausible citations could carry fabricated metadata.** Replaced pair-only
   membership with a returned-evidence metadata map and adversarially changed
   locator/digest fields. **Verified fixed.**
7. **Provider-declared adequate/Complete state could bypass evidence, gaps, or
   conflicts.** Host arithmetic, independence families, gapped findings, and
   conflict visibility are each forced through failing cases. **Verified fine.**
8. **Python 3.14 dynamic dataclass loading could fail before handoff.** Reproduced
   the `sys.modules` registration failure, then verified safe register/remove/
   cache behavior and real vendored validation. **Verified fixed.**
9. **Secrets or analytical content could survive a rejected call.** Forced an
   authentication exception containing sentinel body text, then searched run,
   event, and audit persistence for the key, prompt, evidence, and body.
   **Verified absent.**
10. **Memory-only success could hide durable regressions.** Re-ran every backend
    test with the controller PostgreSQL DSN. **Verified: 200 passed.**

No unresolved correctness issue remained after the review.

## Red-team gate

Appended RT-2026-08-23-063 through 069 without editing prior entries. Critical
objections cover claimant replacement, in-flight lease loss, unknown spend,
source/citation forgery, host/vendored authority, operational secrecy, rollout
eligibility, Python 3.14 loading, and SDK compatibility. Every critical/high
objection is resolved and verified. The decision accepts only the bounded
single-worker issuer pilot.

## GitNexus staged result

Staged `detect_changes()` reported MEDIUM: 36 changed indexed symbols, five
affected flows, and the expected 11 implementation files. The index predates
the new CP-DR symbols and over-attributed shifted lines to unchanged later
methods (`accept_run`, `stream_events`, and the removed old gateway `complete`),
but identified the live `_build_artifact_with_slot` path. Exact cached-diff
inspection confirmed only the 11 Phase-4 paths. All workflow/artifact/acceptance
paths are covered by the 200-pass PostgreSQL suite. No HIGH/CRITICAL staged risk
was reported.

The shared red-team file was split at the index: cached diff contained only the
22-line Phase-4 append, while the adjacent frontend RT-057..062 entry remained
entirely unstaged. `git diff --cached --check` was clean.

## Verification

- `PYTHONPATH=caos/server caos/server/.venv/bin/python -m pytest
  caos/tests/test_cp_dr_runtime.py -q` → **67 passed, 5 skipped in 1.52s**.
- Expanded focused planning/runtime/settings matrix → **119 passed, 6 skipped
  in 3.90s** before the final confidence additions; the required runtime gate
  subsequently increased to 67 passed.
- `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  PYTHONPATH=caos/server caos/server/.venv/bin/python -m pytest caos/tests -q`
  → **200 passed in 13.48s**. The password is the controller's documented
  local-test-only credential; no production secret was used.
- Vendored `confidence_score.py --self-check` → **OK**.
- `caos/server/.venv/bin/python -m ruff check caos/server/caos caos/tests` →
  **All checks passed**.
- `caos/server/.venv/bin/python -m pip check` → **No broken requirements
  found**.
- `caos/server/.venv/bin/python run_sec_audit.py` → **`[]`**.
- `git diff --cached --check` → clean before commit.

The brief names `caos/server/scripts/run_sec_audit.py`, but that path does not
exist in this repository. The authoritative root `run_sec_audit.py` was run with
the server environment and passed.

## Remaining concerns

- The two-call provider semaphore is process-local by approved design. A durable
  global reservation is required before adding multiple worker processes.
- Reclaimed unresolved in-flight spend deliberately has no automatic reclaim;
  it fails closed for operator resolution rather than risking duplicate spend.
- Live provider behavior and external-document retrieval were intentionally not
  exercised. Rollout remains disabled/deny-all by default and depends on the
  separately approved pilot/evaluation gates.
- LITE, sector/theme research, web access, other providers, managed agents,
  dynamic DAGs, and horizontal scale-out remain out of scope.

## Independent-rejection remediation addendum

### Scope and commit

The independent rejection was remediated in `be242e1` (`fix(server): harden
CP-DR execution boundaries`), based on frontend-preserving HEAD `619d968`.
No live provider, web access, external document, or external MCP was used.
`.superpowers/sdd/progress.md` and concurrent frontend history were preserved.

Exact implementation/test paths in the remediation commit:

- `.agent-reviews/redteam.md` — append-only RT-070..076 corrective critic pass.
- `caos/server/caos/artifacts/domain.py` — canonical note content digest,
  strict CP-DR envelope verification, and independent snapshot guards.
- `caos/server/caos/methodology/{bundle,cpdr,prompt}.py` — integrity-verified
  staged authority, full immutable brief, exact scope ledger, exhaustive
  citations, and host-owned coverage/confidence inputs.
- `caos/server/caos/store.py` — takeover recovery and fenced atomic
  artifact/node/research completion for memory and PostgreSQL.
- `caos/server/caos/workflows/{domain,provider}.py` — total active-time and
  manifest ceilings, crash recovery, strict artifact envelope, duplicate-key
  rejection, per-call remaining timeout, and sanitized terminal telemetry.
- `caos/tests/test_cp_dr_{planning,runtime}.py` — corrected planning-time
  expectation plus the deterministic remediation matrix.

### Corrected roots

1. Replacement claims recover stale running nodes. A run cannot succeed unless
   every planned node is succeeded and linked to an existing matching artifact.
   Artifact insert/reuse, node success/link, and research completion are one
   fenced atomic boundary in both stores. Reclaim behavior is explicit for
   unresolved in-flight spend, reconciled/no-artifact restart, valid existing
   fingerprint reuse, and completion-before-terminal-event recovery.
2. Returned evidence carries the host's canonical source-content SHA-256 as its
   origin family and an unclassified authority class. Ordinary material facts
   need two host-distinct origins or provable host primary authority. A single
   source characterisation is sufficient only when explicitly non-material.
   Provider lineage, QA,
   independence, and coverage cannot set the scorer inputs or result.
3. The complete approved brief is digest-checked immediately before prompt
   compilation and sent separately as lower-authority untrusted user data. The
   typed scope ledger is a one-to-one host comparison across every unique
   must-answer assignment and exclusion; missing, duplicate, changed, or
   explicitly unrespected rows fail.
4. Claims, counter-evidence, and conflicts contribute to one exhaustive cited
   set. Every pair must have been returned and occur exactly once in the source
   registry with exact host locator/digest/extractor/confidence metadata.
   Conflict identities, claims, distinct references, and host origins are
   validated.
5. Planning and every active research segment are durably charged; approval
   wait is excluded. SDK and tool operations receive a timeout no greater than
   remaining active seconds, and failed evidence, validation, rendering, and
   fenced completion are charged. Crossing the ceiling after atomic completion
   fails the node/run before any run-success transition.
6. The source metadata manifest is incrementally bounded to 2,000 blocks and
   256 KiB. Exact limits pass; overflow fails `AGENT_BUDGET_EXCEEDED` before
   gateway construction without truncation or persisted source text.
7. The CP-DR artifact digest now covers a strict host envelope containing the
   validated transport payload, host confidence, canonical filename,
   raw-Markdown SHA-256, methodology/plan/source/upstream identity, and schema
   version. Fingerprint reuse and snapshot acceptance independently validate
   this envelope; unchanged rerender is stable.
8. Every post-interaction failure path records a bounded stable terminal code,
   including after count/reservation failure and validation repair exhaustion.
   Unexpected provider/scorer/renderer/validator exceptions map to sanitized
   `AGENT_OUTPUT_INVALID`; `JobFencedError` remains silent and no exception,
   body, prompt, key, or evidence content is persisted.
9. The actual system authority is extracted from integrity-verified vendored
   hard rules and the required source/search, claim ledger, stop, output/QA,
   and issuer sections, plus only the narrow CAOS compatibility wrapper.
   Tampering fails verification. The installed Anthropic SDK 1.0.0 was exercised
   through local MockTransport for constructor and serialized-request shape.

### TDD, rewrite tournament, and confidence review

Each remediation group was introduced red and made green. Representative red
states reproduced stale running-node success, missing atomic completion,
forged snapshot acceptance, self-declared coverage/confidence, incomplete scope
rows, ghost conflict citations, unbounded manifests, unbound handoff fields,
duplicate JSON keys, missing terminal attempts, and raw `NODE_ERROR` fallback.

The required inline no-argument rewrite tournament covered the material changed
symbols in successive two-symbol passes. Readability challengers won for the
shared host-coverage decision and reusable strict artifact-envelope validator.
The incumbents held for the provider loop, runtime lease boundary, and atomic
store completion: speed/memory/readability candidates either removed durable
checkpoints, weakened fencing/attempt telemetry, or split the transaction. The
post-tournament focused suite passed 102/102.

Confidence review least-certain points and dispositions:

- Canonical origin identity: **confirmed bug and fixed** — promoted analyst
  notes used a metadata-object digest; they now hash exact UTF-8 body bytes.
  Upload ingestion already hashes exact content bytes.
- Duplicate approved scope items: **confirmed bug and fixed** — dict
  construction could collapse duplicate exclusions; duplicates now fail before
  comparison.
- Terminal telemetry before create: **confirmed bug and fixed** — a reserve or
  semaphore failure after successful count could bypass gateway `abort`; the
  stable terminal code is now guaranteed without reserving create tokens.
- Fingerprint crash reuse: **confirmed bug and fixed** — fingerprint alone did
  not prove a complete validated handoff; reuse now requires the full strict
  envelope and digest match.
- Manifest boundary arithmetic, active-time equality/approval exclusion,
  conflict origin checks, PostgreSQL rollback/idempotency, and snapshot identity:
  **verified fine** by exact-boundary fake-clock, mutation, and real-PostgreSQL
  tests.

### Final verification evidence

- Focused remediation, with PostgreSQL tests active:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  caos/server/.venv/bin/pytest -q caos/tests/test_cp_dr_runtime.py` →
  **`102 passed in 7.01s`**.
- Full real-PostgreSQL-backed backend:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  caos/server/.venv/bin/pytest -q caos/tests` →
  **`230 passed in 11.28s`**. The first full attempt correctly exposed four
  stale zero-planning-time assertions (`226 passed, 4 failed`); those tests
  were corrected to preserve the new hard active-time contract before the
  clean rerun.
- Vendored scorer:
  `caos/server/.venv/bin/python .../confidence_score.py --self-check` →
  **`confidence_score self-check: OK`**.
- Ruff:
  `caos/server/.venv/bin/python -m ruff check caos/server/caos caos/tests` →
  **`All checks passed!`**.
- Dependency integrity:
  `caos/server/.venv/bin/python -m pip check` →
  **`No broken requirements found.`**.
- Root security audit:
  `caos/server/.venv/bin/python run_sec_audit.py` → **`[]`**.
- Cached patch checks: `git diff --cached --check` → clean. The cached red-team
  diff contained only RT-070..076 and the unstaged red-team diff was empty.

Staged GitNexus `detect_changes()` reported HIGH with 12 indexed changed
symbols, nine affected symbols/processes, and ten files. Inspection showed
stale line-shift attribution to untouched `_merge_state`, event methods,
constructors, `accept_run`, and `stream_events`; the zero-context cached diff
mapped the actual changes to claim recovery/atomic store completion, DAG/CP-DR
runtime execution, and snapshot build. The genuinely affected accept, persist,
and build flows are covered by the seven real-PostgreSQL focused cases and the
230-test backend suite.

### Remaining doubts and external gates

- Provider behavior is verified only through the installed SDK and local mock
  transport; live-provider behavior remains intentionally untested until the
  approved processing/ZDR and evaluation gates are satisfied.
- The provider semaphore remains process-local. Multi-worker deployment needs
  a durable global concurrency reservation and a separate design/review.
- Unresolved in-flight spend remains intentionally charged and fails closed;
  it requires operator resolution rather than risking duplicate paid work.
- LITE, sector/theme, web, external retrieval, other providers, dynamic DAGs,
  and horizontal scale-out remain explicitly unauthorized.

## Second independent-rejection remediation addendum

The fresh review of `be242e1`/`fe742c7` returned **NOT APPROVED — CRITICAL**.
Commit `2bb8af6` closes every Critical and Important item from the second
corrective brief. No live provider, external document, web access, or new
methodology authority was used.

### Root fixes

1. **Authoritative PostgreSQL takeover.** `PostgresStore.claim_job()` now uses
   an opt-in fenced transaction that locks and adopts the current `caos_state`
   before stale running-node recovery, while preserving the replacement claim's
   new job token. Failure restores the locked authoritative state. The exact
   two-store regression constructs the replacement before the first worker
   persists running state, expires the database lease, and proves pending
   recovery, completion, and reload without relying on shared memory.
2. **One strict artifact boundary.** The shared CP-DR validator independently
   recomputes the approved-plan hash, exact current input fingerprint, host
   identity, every pinned source and cited block, canonical host provenance and
   coverage, vendored confidence, exact filename/Markdown/envelope, and the real
   vendored handoff result. Crash reuse, run-success eligibility, snapshot
   acceptance, and atomic completion all use that same loaded bundle-backed
   validator. Memory and PostgreSQL replace an invalid older same-fingerprint
   artifact transactionally with the already validated new one.
3. **Host-owned provenance/confidence.** Persisted evidence families are exact
   canonical source-content SHA-256 digests. Evidence lineage and claim
   lineage/confidence are host-derived before persistence and rendering.
   Material adequacy requires host primary authority or two distinct host
   origins; provider `source_characterisation` cannot upgrade one ordinary
   source. A single-source characterisation can describe only an explicitly
   non-material claim.
4. **Hard active wall time.** Confidence scoring, rendering, vendored
   validation, envelope construction, strict completion validation, and fenced
   atomic completion charge elapsed time in `finally` paths. Failure time is
   durable where the lease remains current. A completion that moves usage from
   179 to 181 seconds cannot transition the run to success; the CP-DR node and
   run finish with `AGENT_BUDGET_EXCEEDED`.
5. **Terminal interaction guarantee.** Once an SDK interaction begins, an
   `AgentError` from active-time charging or ordinary recording routes through
   a sanitized emergency terminal record. It updates the last bounded attempt
   or creates one, respects the 50-record cap, and stores no prompt, evidence,
   response/error body, or exception text. Count and create ceiling crossings
   both end with `AGENT_BUDGET_EXCEEDED` telemetry.
6. **Pre-encoding manifest bounds.** Filename, media type, block ID, locator,
   extractor version, and confidence receive concrete type, character,
   depth, per-container, and total-node limits before encoding. The existing
   2,000-block and 256-KiB totals remain incremental. Pathological fields and
   many short locator nodes fail before gateway construction or derived JSON
   allocation; exact aggregate boundaries still pass.
7. **Real installed-SDK brief assertion.** The local Anthropic 1.0.0
   `MockTransport` capture now asserts that the serialized count/create request
   contains sentinels for research question, decision context, time horizon,
   must-answer, and exclusions together with the strict evidence tool and
   transformed output schema.

### TDD evidence

The second pass began with deterministic red cases:

- the replacement `PostgresStore` retained a running node after takeover;
- one unclassified source plus forged `source_characterisation`/family/lineage/
  confidence passed host validation;
- count/create active-time crossings produced no terminal attempt;
- arbitrary Markdown and stale/corrupted artifact fields could satisfy the old
  self-consistency predicate;
- invalid-old/new-valid fingerprint collisions selected the old artifact;
- throwing post-provider host operations and slow completion skipped time;
- huge manifest fields reached `json.dumps`; and
- the real SDK request had no complete-brief sentinel assertion.

After the root fixes, the focused real-PostgreSQL matrix is **128 passed**. It
includes invalid Markdown, transport, confidence, filename, digest, fingerprint,
approved-plan state, pinned-source withdrawal, real vendored validation,
memory/PostgreSQL collision replacement, two-process takeover, all host-operation
failure clocks, 179-second completion, pre-encoding field/node bounds, and the
actual SDK request capture.

### Rewrite tournament

The mandated no-argument tournament ran inline in successive two-symbol passes
over `cpdr_artifact_is_valid`, `_execute_cpdr`, `AnthropicGateway.run`,
`PostgresStore._fenced_connection`, `validate_cpdr_payload`, both atomic
completion implementations, `_build_artifact`, and the manifest bound helpers.
Each pass compared incumbent, speed, memory, and readability candidates against
the live callers and lease/security invariants. **Incumbents held.** Proposed
splits either duplicated the one artifact authority, passed mutable ledger state
across more seams, weakened `finally` charging/terminal ordering, or changed the
single database transaction. The only small readability improvements retained
were named host-operation/envelope/bound helpers already covered by the focused
matrix. No signature or persistence side effect changed during the tournament.

### Confidence review

Least-confident points were investigated adversarially:

1. **Current approved-plan and fingerprint identity:** confirmed bug. The first
   strict validator trusted surrounding research/fingerprint fields without
   independently recomputing them. It now verifies the canonical plan hash,
   proposed/approved equality, brief/build/scope/source/upstream identities, and
   current input fingerprint. Plan-state and fingerprint mutations fail.
2. **Uncited pinned-source mutation:** confirmed bug. Evidence reconstruction
   originally visited only registry rows. The validator now checks every pinned
   source for case, withdrawal, canonical digest, block-list type, and unique
   block IDs before validating citations. Withdrawing an uncited pinned source
   invalidates reuse and snapshot acceptance.
3. **Evidence-read wall-time double charge:** confirmed bug. Ordinary attempt
   recording also checkpointed elapsed time before the gateway's explicit tool
   `finally` charge. Removing that duplicate checkpoint preserves hard charging
   while avoiding premature budget exhaustion; later host checkpoints still
   include recording persistence time.
4. **Nested locator allocation:** confirmed weakness. Per-container bounds alone
   allowed many individually short child collections. A shared 500-node budget
   now rejects the structure before encoding.
5. **Cross-process merge/rollback, collision rollback, terminal secrecy/cap,
   exact manifest byte arithmetic, and post-completion ceiling behavior:**
   verified fine through real PostgreSQL, mutation, fake-clock, and exact-boundary
   cases. Broad validator exception handling is deliberately fail-closed.

No known implementation correctness issue remains after this review.

### Final verification evidence

- Focused, real PostgreSQL:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  caos/server/.venv/bin/pytest -q caos/tests/test_cp_dr_runtime.py` →
  **`128 passed in 6.88s`**.
- Full backend, real PostgreSQL:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  caos/server/.venv/bin/pytest -q caos/tests` →
  **`256 passed in 14.53s`**.
- Vendored scorer:
  `caos/server/.venv/bin/python .../confidence_score.py --self-check` →
  **`confidence_score self-check: OK`**.
- Ruff:
  `caos/server/.venv/bin/python -m ruff check caos/server/caos caos/tests` →
  **`All checks passed!`**.
- Dependency integrity:
  `caos/server/.venv/bin/python -m pip check` →
  **`No broken requirements found.`** (the disabled user-cache warning is
  environmental and does not affect package integrity).
- Root security audit:
  `caos/server/.venv/bin/python run_sec_audit.py` → **`[]`**.
- Patch checks: unstaged/cached `git diff --check` were clean; the corrective
  red-team hunk was an append-only RT-077..083 section.

Staged GitNexus `detect_changes()` reported **HIGH** with nine indexed changed
symbols and seven flows. The stale index attributed shifted lines to untouched
`latest_version`, `_merge_state`, `WorkflowRuntime.__init__`, `close`,
`start_run`, and `logical_ids`. The cached patch shows the actual affected
surfaces are strict CP-DR artifact/snapshot validation, opt-in PostgreSQL
adoption and atomic collision handling, CP-DR execution/provenance/time/manifest
logic, provider terminal handling, and their tests. The genuine `_execute` and
PostgreSQL persistence paths are covered by the 128-test focused PostgreSQL
matrix and 256-test full suite.

### Remaining doubts and external gates

- Live-provider behavior remains intentionally untested until approved
  processing/ZDR and shadow-evaluation gates are satisfied.
- Runtime source authority is conservatively `unclassified`; absent a separate
  host-owned primary-authority classifier, material adequacy needs two distinct
  canonical content digests.
- The provider semaphore remains process-local. Horizontal worker deployment
  still needs a durable global concurrency reservation and a separate review.
- Whole-envelope PostgreSQL persistence remains the accepted current topology;
  scale-out beyond that topology is not authorized by Phase 4.
- Unresolved in-flight spend remains charged and fails closed for operator
  resolution rather than risking a duplicate paid request.
- LITE, sector/theme, web, external retrieval, other providers, dynamic DAGs,
  and horizontal scale-out remain unauthorized.

## Third independent-review remediation addendum

The third independent review of `2bb8af6`/`e08d598` found no Critical defects
but returned **NOT APPROVED — IMPORTANT**. Commit `131713e` closes all four
Important roots from the third corrective brief. It changes only:

- `caos/server/caos/artifacts/domain.py`
- `caos/server/caos/store.py`
- `caos/server/caos/workflows/domain.py`
- `caos/server/caos/workflows/provider.py`
- `caos/tests/test_cp_dr_runtime.py`

No live provider, external document, web request, or new methodology authority
was used.

### Root fixes

1. **Final success budget boundary (superseded by pass four).** This pass timed
   and durably charged strict CP-DR artifact validation and then timed the
   success-state write. The fourth review correctly rejected that ordering:
   timing after success could require a fallible post-success ledger write.
   Current behavior is described in the fourth-remediation addendum.
2. **Post-interaction terminal guarantee.** Post-call lease checking,
   active-time charging, and ordinary attempt recording now share one guarded
   boundary. A transient ordinary failure maps to sanitized
   `AGENT_OUTPUT_INVALID`; post-call budget failures retain their stable code;
   both make a best-effort terminal attempt after interaction. True
   `JobFencedError` remains unmodified and silent. No exception text, prompt,
   body, evidence, or key enters telemetry.
3. **Current methodology integrity.** The shared strict CP-DR artifact
   validator calls current `bundle.verify()` before using any cached scorer,
   renderer, or handoff validator. Forced integrity failure now rejects the
   same canonical artifact at fingerprint reuse, no-pending run success, and
   snapshot construction.
4. **Normalized PostgreSQL authority (superseded by pass four).** Claim setup no longer overwrites an
   existing normalized run row from a stale process mirror. After the fenced
   transaction locks and adopts authoritative `caos_state` and recovers stale
   nodes, it rewrites normalized status, bounded error, plan, and accepted
   snapshot identity from that authoritative run before the same transaction
   commits. This covered takeover only; the fourth review correctly required
   synchronization from the exact state at every shared persistence boundary.

### TDD and focused evidence

The initial targeted run reproduced six failures: three current-bundle
entrypoints accepted the canonical artifact, final validation succeeded after
the active ceiling, a transient ordinary record failure escaped as raw
`RuntimeError`, and a post-count budget loss left no terminal attempt. The
cross-process PostgreSQL extension also exposed the stale normalized row. The
root fixes made that matrix green. The former success-state-write regression is
historical evidence only; pass four replaces that design with pre-reservation
and one atomic terminal operation.

Final focused, real-PostgreSQL result:

`CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
caos/server/.venv/bin/python -m pytest -q caos/tests/test_cp_dr_runtime.py` →
**`135 passed in 12.22s`**.

### Rewrite tournament

The required no-argument tournament ran inline over the two material changed
symbols, `WorkflowRuntime._execute` and `PostgresStore.claim_job`, after exact
GitNexus context/impact review. Both incumbents held:

- `_execute`: speed and memory candidates reduced lookups but risked charging
  stale research or emitting success before the hard-ceiling checkpoint; the
  readability candidate moved attempt-local fenced closures across a wider
  interface. The incumbent preserves current-token persistence and explicit
  validation/write/event ordering.
- `PostgresStore.claim_job`: a combined SQL/CTE candidate shortened the method
  but obscured the existing authoritative-envelope persistence and rollback;
  a helper extraction separated normalized synchronization from the adopted
  transaction. The incumbent keeps adoption, recovery, normalized update, and
  envelope persistence visibly in the one fenced transaction.

Signatures and side effects stayed unchanged. The post-tournament invariant
probe passed **3/3**: both final-budget cases and the real two-store normalized
takeover. GitNexus reported `_execute` LOW with one test caller, but that
`test_expired_start_attempt_is_finalized` symbol is absent from the current
tree and is a stale-index false positive; `PostgresStore.claim_job` was LOW
with no indexed callers.

### Confidence review

Least-confident points and dispositions:

1. **Success-write time could become the next uncharged edge:** the third pass
   classified this as only a test gap, but the fourth review proved a production
   atomicity gap. Pass four reserves bounded time before success and removes all
   post-success ledger writes.
2. **Terminalization might hide a real stale lease:** verified fine. The
   existing in-flight loss regression plus the new ordinary/budget cases prove
   `JobFencedError` remains silent while lease-permitted failures receive stable
   bounded telemetry; the adversarial set passed **9/9**.
3. **Current verification might cover only one acceptance path:** verified
   fine. One parameterized canonical-artifact mutation exercises reuse,
   no-pending success, and snapshot acceptance, and all three fail closed.
4. **Normalized synchronization might use the pre-adoption mirror or escape
   its transaction:** verified fine. The update reads `self.runs` only after
   `adopt_current=True` enters, uses the yielded fenced connection, and the
   two-store PostgreSQL assertions pass before and after completion.
5. **Exact ceiling equality and secrecy:** equality and secrecy were verified,
   but the later atomicity finding remained. The fourth addendum records its
   root fix and final confidence disposition.

### Final verification evidence

- Full real-PostgreSQL backend:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  caos/server/.venv/bin/python -m pytest -q caos/tests` →
  **`263 passed in 22.57s`**.
- Vendored CP-DR scorer:
  `caos/server/.venv/bin/python
  caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/scripts/confidence_score.py
  --self-check` → **`confidence_score self-check: OK`**.
- Ruff:
  `caos/server/.venv/bin/python -m ruff check caos/server/caos caos/tests` →
  **`All checks passed!`**.
- Dependency integrity:
  `caos/server/.venv/bin/python -m pip check` →
  **`No broken requirements found.`**. The disabled user-cache warning is
  environmental and does not affect package integrity.
- Root security audit:
  `caos/server/.venv/bin/python run_sec_audit.py` → **`[]`**.
- Cached patch: `git diff --cached --check` was clean and contained only the
  five owned server/test paths. No frontend or progress path was staged.

Staged GitNexus `detect_changes()` reported **LOW**: four indexed changed
symbols, zero affected symbols/processes, and five files. Its line-shift mapping
named untouched `WorkflowRuntime.stream_events` and
`AnthropicGateway.__init__`; the inspected zero-context cached diff shows the
actual changes are `_execute`, `PostgresStore.claim_job`,
`AnthropicGateway.run`'s interaction boundary, the strict artifact validator,
and their focused tests.

### Remaining doubts and external gates

- Live-provider behavior remains intentionally untested until approved
  processing/ZDR and shadow-evaluation gates are satisfied.
- Full bundle integrity verification at every strict artifact boundary is
  deliberately fail-closed and adds bounded active time; production evaluation
  should measure its latency without caching away the current-integrity check.
- The provider semaphore remains process-local, and whole-envelope PostgreSQL
  persistence remains the accepted topology. Horizontal workers require a
  separate durable concurrency/storage design and review.

## Fourth independent-review remediation addendum

The fourth independent review of `131713e`/`9b7ea6f` returned **NOT APPROVED —
CRITICAL** because terminal success was not atomic, normalized PostgreSQL run
rows drifted after later writes, and post-interaction provider work still had
unterminated exception paths. Implementation commit `1f400d8` closes those
roots without broadening the disabled issuer-only pilot. No live provider,
external document, web request, or new methodology authority was used.

### Exact changed paths

- `.agent-reviews/redteam.md` — append-only RT-088..091.
- `caos/server/caos/store.py` — one atomic fenced terminal-success operation in
  both stores and exact normalized-run synchronization at shared persistence.
- `caos/server/caos/workflows/domain.py` — pre-success finalization reservation,
  stable failure mapping, and removal of post-success ledger/event writes.
- `caos/server/caos/workflows/provider.py` — one outer fail-closed boundary
  around every post-interaction operation.
- `caos/server/migrations/001_baseline.sql` — normalized run status accepts the
  real `planning` state that `MemoryStore.create_run()` durably persists before
  the workflow moves to queued/paused.
- `caos/tests/test_clean_slate.py` and `caos/tests/test_cp_dr_runtime.py` — fake
  transaction contract update and the complete deterministic remediation
  matrix.

### Root fixes

1. **Atomic terminal success.** Strict artifact validation and its actual active
   time charge complete while the run is non-successful. The host then durably
   reserves a fixed five-second finalization allowance. Only one fenced store
   operation may set `status=succeeded`; that same operation persists the
   reserved research ledger and `run.succeeded` event, while PostgreSQL also
   synchronizes the normalized run row in the same database transaction.
   Memory snapshots status/event before persistence and restores both on any
   failure. PostgreSQL rollback restores the locked authoritative envelope.
   No budget or lifecycle-event write follows success.
2. **Conservative finalization ceiling.** The original one-second draft reserve
   was rejected during review because the adversarial finalization takes two
   seconds. The final constant is five seconds. Its ponytail ceiling requires
   an increase if measured p99 exceeds four seconds; unused time is deliberately
   overcharged. A fake-clock two-second terminal operation proves actual time is
   inside the reserve, and 175 seconds plus the reserve fails at exact equality.
   A run at 179 seconds cannot enter terminal success.
3. **Exact normalized PostgreSQL state.** `_persist_connection()` upserts each
   run's status, error, plan, accepted snapshot, and immutable required fields
   from the exact merged state that is written to `caos_state`, before the same
   commit. Referenced cases are inserted first for FK integrity; an absent case
   fails closed. The real two-store probe compares normalized and authoritative
   state after takeover/recovery, completion, plan/error mutation, atomic
   finalization, and snapshot acceptance. Forced terminal persistence failure
   rolls both authorities back.
4. **Complete provider terminal boundary.** The full count/create/reconcile,
   generation/retry telemetry, evidence, repair, and local-validation loop is
   enclosed once. After a real interaction, ordinary failures map to sanitized
   `AGENT_OUTPUT_INVALID`, `AgentError` retains its stable code, and terminal
   recording is best-effort and one-shot. `JobFencedError` is re-raised silently
   and unchanged. Fine-grained provider retry, usage reconciliation, one repair,
   and request hashing remain unchanged.

### TDD evidence

The first targeted run was intentionally red at **14 failed, 3 passed, 1
skipped**. It reproduced success before atomic persistence, reservation and
terminal-event failure acceptance, missing normalized updates, and ordinary
post-interaction exceptions. The initial real-PostgreSQL subset added three
failures for normalized drift and missing atomic terminal methods. After the
root changes, the targeted matrix reached **17 passed, 1 skipped**.

The completed deterministic matrix covers:

- 179 seconds plus final work cannot succeed;
- fixed-reserve equality, reservation persistence failure, and a measured
  two-second terminal operation;
- atomic status/event rollback and `RUN_NOT_READY` acceptance in memory and
  PostgreSQL;
- exactly one successful terminal run mutation;
- real two-store normalized parity through acceptance; and
- ordinary and `AgentError` failures at reconcile, generation record,
  provider-retry record, evidence handling, and final validation, plus silent
  post-interaction fencing.

The first full backend attempt reported **269 passed, 13 failed**. One failure
was genuine: an older fake persistence test used intentionally partial case/run
dictionaries, exposing that the first sync draft eagerly dereferenced every
case. The root fix synchronizes only run-referenced cases and the fixture now
models the required normalized fields. The other twelve failures were local
PostgreSQL `Operation not permitted` sandbox denials. The isolated fake
transaction regression then passed, and the authorized real-database rerun was
clean at **282 passed**.

### Rewrite tournament

The required no-argument tournament ran inline over the two most material
symbols after caller and invariant review. GitNexus resolved `_execute` as LOW
with one stale test caller; it could not resolve the rewritten gateway `run`, so
live repository callers and the focused matrix supplied its impact set.

- **Winner: Incumbent holds — `WorkflowRuntime._execute`.** Speed and memory
  candidates reduced defensive reads but could reserve from stale research;
  the readability candidate split attempt-local fencing and terminal ordering
  across another interface. The incumbent keeps validation, durable reserve,
  atomic success, and sanitized failure visibly ordered under one attempt.
- **Winner: Incumbent holds — `AnthropicGateway.run`.** Speed/memory candidates
  did not remove an SDK or persistence interaction. A helper-method extraction
  widened the callback surface and made `provider_interacted`/one-shot terminal
  state cross another seam. The nested loop plus single outer boundary is the
  smallest verified structure that preserves retry, repair, reconciliation,
  fencing, and secrecy contracts.

The smaller new store methods were skipped under the skill's two-symbol cap;
they are single-purpose transaction wrappers covered directly in memory and
real-PostgreSQL rollback tests. No challenger provided a verified semantic or
complexity improvement, so no tournament rewrite was applied. The post-
tournament focused file passed **154/154** and the full backend passed
**282/282**.

### Confidence review

Least-confident points and dispositions:

1. **A failed atomic commit might leave an in-memory successful mirror.**
   Verified fine after adversarial failure: memory restores status/event
   snapshots; `_fenced_connection()` rolls back PostgreSQL and re-adopts the
   locked database state. Acceptance remains `RUN_NOT_READY` in both stores.
2. **The fixed allowance might undercharge realistic terminal persistence.**
   Confirmed weakness in the one-second draft and fixed at five seconds. The
   reviewed two-second clock probe is inside the allowance; equality at the
   three-minute ceiling fails before success. The p99>4s trigger is explicit.
3. **Shared normalized sync might use a pre-merge mirror or incomplete FK
   ordering.** Verified/fixed: synchronization receives the exact post-merge
   state from `_persist_connection()`, inserts only referenced cases before
   runs, and shares its transaction. The fake-state regression and multi-stage
   two-store PostgreSQL comparison both pass.
4. **`planning` could be a test-only status accidentally widening production.**
   Verified production behavior: `MemoryStore.create_run()` sets `planning` and
   immediately persists; `WorkflowService.create_run()` moves it to
   queued/paused only afterward. The migration restores schema/state parity.
5. **The provider boundary might double-record terminals or swallow fencing.**
   Verified fine: `terminal_recorded` makes conversion idempotent, and explicit
   `JobFencedError` branches bypass `abort`. Ten typed/ordinary cases and the
   separate fencing-silence probe pass without secret text.
6. **A successful run might receive a later run/ledger mutation.** Verified
   fine: the successful regression records one terminal run mutation; `finally`
   only releases the job reservation and does not rewrite run state or events.

Fixed during confidence review: eager normalization of unreferenced partial
fake cases and the too-small one-second finalization reserve. No known
implementation correctness issue remains. External rollout doubts remain below.

### Final verification evidence

- Focused, real PostgreSQL:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  PYTHONPATH=caos/server caos/server/.venv/bin/python -m pytest -q
  caos/tests/test_cp_dr_runtime.py` → **`154 passed in 378.85s (0:06:18)`**.
- Full backend, real PostgreSQL:
  `CAOS_TEST_DATABASE_URL=postgresql://caos_test:…@127.0.0.1:55460/caos_test
  PYTHONPATH=caos/server caos/server/.venv/bin/python -m pytest -q caos/tests`
  → **`282 passed in 237.96s (0:03:57)`**.
- Vendored scorer: `caos/server/.venv/bin/python
  caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/scripts/confidence_score.py
  --self-check` → **`confidence_score self-check: OK`**.
- Ruff: `caos/server/.venv/bin/python -m ruff check caos/server/caos caos/tests`
  → **`All checks passed!`**.
- Dependency integrity: `caos/server/.venv/bin/python -m pip check` →
  **`No broken requirements found.`**. The disabled user-cache warning is
  environmental and does not affect package integrity.
- Root security audit: `caos/server/.venv/bin/python run_sec_audit.py` →
  **`[]`**.
- Cached checks: `git diff --cached --check` was clean. The cached red-team diff
  contained only RT-088..091; its unstaged diff was empty. Frontend and the
  controller-owned progress file were not staged.

Staged GitNexus `detect_changes()` reported **CRITICAL** with eleven indexed
changed symbols, sixteen affected processes, and seven files. The controller
acknowledged that warning before commit. Exact zero-context inspection shows
the stale index assigned inserted store lines to untouched `_merge_state`,
`get_snapshot`, `latest_run_for_case`, `versioned`, and `append_version`, and
inserted runtime lines to untouched `start_run`/`stream_events`; it omitted the
rewritten provider method. The actual cached surfaces were atomic finalization,
shared exact-state persistence, provider terminalization, migration parity, and
their tests. The 154-test focused and 282-test full real-PostgreSQL suites cover
the genuinely affected workflow, persistence, acceptance, and provider paths.

### Remaining doubts and external gates

- Five seconds is a measured single-worker finalization allowance, not a
  universal database SLA. Production p99 above four seconds requires raising
  the constant and rerunning the hard-ceiling matrix before rollout.
- Live-provider behavior remains intentionally untested until approved
  processing/ZDR and shadow-evaluation gates are satisfied.
- The provider semaphore remains process-local and whole-envelope PostgreSQL
  persistence remains the accepted topology. Horizontal workers require a
  separate durable concurrency/storage design and review.
- Unresolved in-flight spend remains charged and fails closed for operator
  resolution rather than risking a duplicate paid request.
- LITE, sector/theme, web, external retrieval, other providers, dynamic DAGs,
  and horizontal scale-out remain unauthorized.
