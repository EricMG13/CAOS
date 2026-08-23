# Hybrid CP-DR Phase 4 implementation report

Date: 2026-08-23

Scope: bounded issuer-only CP-DR provider execution, host validation, and canonical vendored handoff

Base: `78abc14` — `fix(frontend): ship Inter and JetBrains Mono via next/font`

Implementation commit: `ae0400a` — `feat(server): execute bounded CP-DR research`

Remediation commit: `be242e1` — `fix(server): harden CP-DR execution boundaries`

## Status

Remediated after independent rejection. Commits `ae0400a..a8005f3` were
independently rejected because the original verification did not cover several
critical crash, provenance, scope, citation, timing, artifact, telemetry, and
authority roots. The original implementation narrative and 200-test evidence
below are retained as historical evidence only and are superseded by the
remediation addendum at the end of this report.

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
   need two host-distinct origins; one source is allowed only for attributed
   source characterisation or provable host authority. Provider lineage, QA,
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
   final persistence checkpoints are charged before artifact completion.
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
