# Adopt the hybrid CP-DR runtime

**Date:** 2026-08-23

**Status:** Ready for implementation

**Approved design:** [Hybrid agent runtime design](../specs/2026-08-23-hybrid-agent-runtime-design.md)

## Outcome

Keep `WorkflowRuntime` as CAOS's sole DAG supervisor and add one bounded,
source-only CP-DR specialist inside the existing CP-DR node. The first release
is disabled by default, limited to full-depth issuer research, requires CP-0 and
exact plan-hash approval, and fails closed without a canonical validated
artifact.

The implementation stops at CP-DR. It does not add an agent framework, provider
abstraction, dynamic DAG, web search, MCP, managed agents, model memory, shell,
or code execution.

## Execution rules

- Execute phases in order. Each phase must leave the branch testable and may be
  handed to a fresh agent with this document as its task.
- Before editing any function, class, or method, run GitNexus upstream impact on
  that symbol. Warn before editing a `HIGH` or `CRITICAL` target.
- The known authorization change to `require_case()` is `CRITICAL`: 33 symbols,
  32 processes, and four modules are affected. It is isolated in Phase 1.
- Run `rewrite-tournament` after every phase containing non-trivial code, then
  run `confidence-review` and fix confirmed issues.
- Before every commit, run GitNexus `detect_changes(scope="staged")`, inspect the
  affected flows, and stage only the explicit phase files.
- Keep the feature flag off through Phases 0–6. Production activation is an
  operational decision in Phase 7, not a code default.
- Never send production documents to CI or a developer provider account.

## Phase map

| Phase | Deliverable | Depends on |
|---|---|---|
| 0 | Frozen authority and allowed APIs | Approved design |
| 1 | Correct case-write authorization | Phase 0 |
| 2 | Renewable leases and fenced lifecycle events | Phase 1 |
| 3 | Durable brief, plan pause, and exact-hash approval | Phase 2 |
| 4 | Bounded Anthropic tool loop and canonical CP-DR artifact | Phase 3 |
| 5 | Run Console brief, plan review, and unavailable states | Phase 4 |
| 6 | Disabled deployment foundation and operational metadata | Phase 5 |
| 7 | Full verification, shadow evaluation, opt-in pilot | Phase 6 |

## Phase 0: Freeze authority and allowed APIs

### Objective

Resolve the host decisions needed to implement the signed contract without
editing the integrity-pinned vendor bundle or inventing provider calls.

### Documentation to use

- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/SKILL.md:8-35,116-169`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/references/REF_CP-DR_STEPS.md:7-107`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/references/CP-DR_DeepResearch.schema.md:18-38`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/references/CP-DR__DeepResearch__payload.schema.txt`
- `caos/server/caos/methodology/vendor/deploy_v/CP_MODULE_PAYLOAD_BASE.schema.txt`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json:1177-1180,1551-1572,2098-2119`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/scripts/confidence_score.py:88-142`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/scripts/validate_handoff.py:650-671,834-872`

### Contract decisions

Record these as host compatibility rules and golden tests:

1. CP-0 is required and must be an accepted upstream artifact with matching
   source-set and run lineage.
2. Phase 1 accepts `DEEP_RESEARCH` with `depth="full"` only. The LITE route is
   unavailable until signed authority defines its reduced analytical contract.
3. Phase 1 accepts issuer scope only. `subject_name` comes from the case issuer;
   `scope_type` is fixed to `issuer`.
4. `source_mode` is fixed to `supplied_only`; `research_budget` is fixed to
   `standard`; plan approval is always required.
5. The brief uses the vendored vocabulary: `research_question`,
   `decision_context`, `as_of_date`, `time_horizon`, `must_answer`, and
   `exclusions`.
6. Hash the complete plan with existing compact sorted canonical JSON and store
   it as `sha256:` plus the 64-character digest.
7. Derive `scope_key` as `case_id.replace("_", "-")`. Reject rather than repair
   any result that does not reproduce the pinned value.
8. Set the CP-DR `reporting_period` to the brief's ISO `as_of_date` and pass that
   exact value to the vendored handoff validator.
9. Define strict host row models for workstreams, claim/evidence entries, and
   conflicts from `REF_CP-DR_STEPS.md:64-105`. The host models may narrow the
   underspecified child JSON schema but may not weaken it.
10. Treat provider JSON as typed runtime transport. Persist the validated typed
    payload and the canonical Markdown artifact; the Markdown remains the sole
    analytical handoff.
11. Use the vendored `confidence_score.compute(...)` and
    `validate_handoff.validate_text(...)`. CP-DR has no vendored completeness
    script, so implement a host semantic-completeness gate from the required
    rows, citations, headings, and identity fields.
12. Keep synthetic CP-PARSE identity inside the host plan. Do not pass its stage
    zero route identity into vendor helpers that require stages 1–99.

If governance supplies a new signed bundle resolving these contradictions,
replace the vendor bundle as a single verified update and revise the golden
tests. Do not patch individual integrity-pinned files.

### Allowed provider APIs

Use only the official Anthropic Python SDK and these documented surfaces:

- `Anthropic(api_key=..., max_retries=0, timeout=...)`
- `client.messages.create(...)`
- `client.messages.count_tokens(...)`
- top-level `system=...`; normal `messages=[...]`
- client tools with `strict: true`
- `tool_choice={"type": "auto", "disable_parallel_tool_use": true}`
- `output_config.format` with `anthropic.transform_schema(...)`
- response `_request_id`, `usage.input_tokens`, `usage.output_tokens`, and
  `stop_reason`
- documented exceptions including `APITimeoutError`, `APIConnectionError`,
  `RateLimitError`, `APIStatusError`, `AuthenticationError`, and
  `PermissionDeniedError`

References:

- [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
- [Messages create](https://platform.claude.com/docs/en/api/python/messages/create)
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Tool-result handling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)

### Verification

- Run `DeployVBundle.verify()` and the repository taxonomy consistency check.
- Add a planning checklist confirming all 12 decisions above have a golden test
  owner in a later phase.
- Confirm the provider organization has an approved processing arrangement and
  ZDR eligibility before any live test. This is an activation gate, not a unit
  test.

### Anti-pattern guards

- Do not use `output_format`, beta structured-output headers, a `system` message
  role, `RequestTimeoutError`, provider Files, remote MCP, managed agents, web
  tools, prompt caching with issuer data, or SDK automatic retries.
- Do not treat the absent `completeness_check.py` as an available validator.
- Do not proceed to provider-backed persistence while a golden CP-DR Markdown
  fixture fails the vendored handoff validator.

### Exit gate

The contract decisions and allowed APIs are testable and no unresolved authority
question can change a public request field, artifact identity, or rollout scope.

## Phase 1: Correct case-write authorization

### Objective

Fix the shared authorization root before adding another case-write endpoint.

### Files

- Modify `caos/server/caos/identity_cases/domain.py`.
- Modify `caos/tests/test_clean_slate.py`.
- Modify `run_sec_audit.py` only if the existing direct-call detection cannot
  recognize the unchanged authorization pattern.

### Implementation

1. Re-run GitNexus impact for `require_case()` and review all direct callers.
2. In `require_case(store, case_id, identity, write=True)`, require both:
   - global identity role in `ANALYST`, `APPROVER`, or `ADMIN`; and
   - stored case-member role in `ANALYST`, `APPROVER`, or `ADMIN`.
3. Preserve current read behavior and cross-case 404 behavior.
4. Add a role matrix proving that a globally privileged identity stored as a
   case `READER` cannot upload, start, upgrade, approve, accept, or mutate case
   analysis.
5. Prove existing case analysts, approvers, and admins retain their intended
   write access.

### Copy-ready references

- Current guard: `caos/server/caos/identity_cases/domain.py:43-49`
- Membership API: `caos/server/caos/store.py:97-103`
- Existing forged-identity tests: `caos/tests/test_clean_slate.py:137-157,675-686`
- Route security scanner: `run_sec_audit.py:76-137`

### Verification

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_clean_slate.py -q -k 'identity or member or reader or authorization'
caos/server/.venv/bin/python run_sec_audit.py
```

Then run the full server suite because this guard affects 32 flows.

### Anti-pattern guards

- Do not special-case only the future research-plan endpoint.
- Do not replace case membership with the request header's global role.
- Do not convert unauthorized cross-case reads from 404 to information-leaking
  403 responses.

### Exit gate

The full authorization matrix and route security audit pass before any CP-DR
endpoint is added.

## Phase 2: Add renewable leases and fenced lifecycle events

### Objective

Make a paid provider call safe under the existing job ownership model before
adding the call itself.

### Files

- Modify `caos/server/caos/store.py`.
- Modify `caos/server/caos/workflows/domain.py`.
- Modify `caos/tests/test_clean_slate.py`.
- Add PostgreSQL-backed coverage in `caos/tests/test_cp_dr_runtime.py` if the
  existing fake-connection fixtures cannot prove database-clock behavior.

### Implementation

1. Run impact for `MemoryStore`, `PostgresStore`, `WorkflowRuntime._execute`,
   and every existing method whose signature changes.
2. Keep the existing 60-second lease and add a fixed 20-second heartbeat. Do not
   add an environment setting before measured need.
3. Add matching concrete store methods:

   ```python
   renew_job(run_id: str, attempt_token: str) -> bool
   emit_fenced(run_id: str, attempt_token: str, event: str, data: dict[str, Any]) -> None
   audit_event_fenced(run_id: str, attempt_token: str, action: str, actor: str, **details: Any) -> None
   ```

4. The memory implementation reuses `_assert_job_locked()` and must not renew an
   expired token.
5. The PostgreSQL implementation uses a conditional `UPDATE ... WHERE
   attempt_token = %s AND lease_until > now() RETURNING id`; it must never revive
   an expired lease.
6. Start one heartbeat thread after a job claim. Stop and join it in `_execute()`
   `finally`, including exceptions and planning pauses.
7. Set a shared lost-lease event when renewal fails. Check it before every future
   provider turn and evidence-tool call; retain `put_artifact_fenced()` as the
   final write gate.
8. Replace only worker-originated lifecycle events with `emit_fenced()`:
   `run.running`, `node.running`, `node.succeeded`, `node.failed`,
   `run.succeeded`, and `run.failed`.
9. Keep user-originated `run.created`, source-empty pause, plan approval, and
   snapshot acceptance on ordinary authorized event paths.

### Copy-ready references

- Memory fencing: `caos/server/caos/store.py:183-231,265-273`
- PostgreSQL fenced transaction: `caos/server/caos/store.py:443-484`
- Current worker events: `caos/server/caos/workflows/domain.py:61-110`
- Existing lease tests: `caos/tests/test_clean_slate.py:985-1036,1118-1207`

### Verification

- Memory and PostgreSQL tests cover renewal, expired-token refusal, takeover,
  stale event rejection, stale audit rejection, heartbeat shutdown, and final
  artifact fencing.
- Include one real PostgreSQL integration check for database time and row-lock
  semantics; mocks alone are insufficient.

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_clean_slate.py caos/tests/test_cp_dr_runtime.py -q -k 'lease or fenced or heartbeat or stale'
```

### Anti-pattern guards

- Do not renew by run ID alone.
- Do not let an expired worker emit a terminal event after its state write was
  fenced out.
- Do not create a second scheduler, queue, or lease table.

### Exit gate

A forced token takeover during a simulated long call produces no stale state,
event, audit entry, or artifact.

## Phase 3: Persist the brief, planning pause, and exact approval

### Objective

Represent CP-DR planning and approval durably on the existing run so pause and
resume work in memory and PostgreSQL without a new table.

### Files

- Modify `caos/server/caos/contracts.py`.
- Modify `caos/server/caos/config.py`.
- Modify `caos/server/caos/methodology/bundle.py`.
- Modify `caos/server/caos/workflows/domain.py`.
- Modify `caos/server/caos/http.py`.
- Modify `caos/server/caos/store.py` only if an atomic helper is needed.
- Add `caos/tests/test_cp_dr_runtime.py`.
- Modify `caos/tests/test_run_launcher.py` for settings parsing.

No database migration is expected. `runs` already live in the durable
`caos_state.state` envelope, and `MemoryStore.get_run()` preserves extra run
keys.

### Public contracts

Add strict request models using `StrictModel`:

```python
class ResearchBrief(StrictModel):
    research_question: str = Field(min_length=1, max_length=400)
    decision_context: str = Field(min_length=1, max_length=400)
    as_of_date: date
    time_horizon: str = Field(min_length=1, max_length=200)
    must_answer: list[str] = Field(default_factory=list, max_length=10)
    exclusions: list[str] = Field(default_factory=list, max_length=10)

class ApproveResearchPlanRequest(StrictModel):
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
```

Cap every `must_answer` and `exclusions` item at 200 characters. Extend
`StartRunRequest` with `research_brief: ResearchBrief | None` and validate:

- `DEEP_RESEARCH` requires `depth="full"` and a brief;
- other pathways reject a research brief;
- `must_answer` and `exclusions` contain no more than 10 entries combined;
- caller input cannot set subject, scope, source mode, budget, model, tools, or
  approval state.

### Durable run shape

For CP-DR runs, store one `research` object on the existing run:

```text
brief
phase: planning | awaiting_approval | approved | researching | complete | failed
proposed_plan
proposed_plan_hash
approved_plan_hash
approved_by
approved_at
model
budget_limits
budget_used
inflight_request_digest
attempts
```

The plan contains 3–5 bounded workstreams with ID, question, perspective,
hypothesis, evidence needs, source classes, disconfirming test, completion test,
and effort cap. It also records synthesis and adversarial coverage. Canonicalize
the full object before hashing.

### Planning pause and approval

1. Add a typed internal planning outcome that `_execute()` handles before the
   generic node-exception path.
2. After planning, fenced-update CP-DR from `running` to `pending`, store the
   plan/hash/remaining budgets, and pause the run with error code
   `PLAN_APPROVAL_REQUIRED`.
3. Emit `research.plan_ready` and `run.paused` only after the state is durable.
4. Add:

   ```python
   WorkflowRuntime.approve_research_plan(run_id: str, actor: str, plan_hash: str) -> dict[str, Any]
   ```

5. Compare the supplied hash to the currently pending hash inside one locked
   persistence operation. Reject wrong, stale, already consumed, wrong-phase,
   and changed-source-set approvals.
6. Persist approval identity/time/hash, clear only the approval pause error,
   set the same run to `queued`, audit the action, and emit
   `research.plan_approved`.
7. In development, resubmit `_execute()` like `start_run()`; in production, let
   the existing worker polling pick up the queued run.
8. Add the exact endpoint:

   ```text
   POST /api/runs/{run_id}/research-plan/approve
   {"plan_hash":"sha256:..."}
   ```

   Use `identity()`, `get_run_or_404()`, and the corrected
   `require_case(..., write=True)` before the runtime call.

### Copy-ready references

- Strict models and canonical digest: `caos/server/caos/contracts.py:82-120,220-225`
- Durable run extension: `caos/server/caos/store.py:115-181,498-505`
- Existing pause: `caos/server/caos/workflows/domain.py:36-59`
- Resume scheduler: `caos/server/worker.py:18-28`
- Case-scoped routes: `caos/server/caos/http.py:231-273`
- Exact-hash rollback pattern: `caos/server/caos/http.py:422-452`

### Verification

- Test strict brief bounds and forbidden authority fields.
- Test plan hash determinism and the required `sha256:` prefix.
- Test wrong/stale/double/cross-case/read-only approval.
- Test plan pause and same-run resume in memory and PostgreSQL.
- Test approval persistence rollback and no event on failed persistence.
- Test that a changed source set requires a new run.

```bash
caos/server/.venv/bin/python -m pytest caos/tests/test_cp_dr_runtime.py caos/tests/test_clean_slate.py -q -k 'research or plan or approval'
caos/server/.venv/bin/python run_sec_audit.py
```

### Anti-pattern guards

- Do not create a second plan-status endpoint or research-plan table.
- Do not infer approval from starting a run.
- Do not mutate a brief or workstream in place after hashing.
- Do not reset budget counters when the run resumes.

### Exit gate

A deterministic fake planner can pause, expose one ordinary run record, accept
the exact plan hash, and resume the same pinned run with unchanged source and
upstream identities.

## Phase 4: Implement bounded CP-DR execution

### Objective

Add the only adaptive execution path: a direct Anthropic Messages/client-tool
loop for CP-DR, followed by strict host and vendored validation.

### Files

- Add `caos/server/caos/methodology/cpdr.py` for strict CP-DR transport models,
  semantic completeness, and canonical Markdown rendering.
- Modify `caos/server/caos/methodology/bundle.py` to load and call the vendored
  confidence scorer and handoff validator without editing them.
- Modify `caos/server/caos/methodology/prompt.py` for staged CP-DR authority and
  separate system/user content.
- Modify `caos/server/caos/workflows/provider.py` for the Messages/tool loop and
  error classification.
- Modify `caos/server/caos/workflows/domain.py` for the static CP-DR dispatch,
  provider semaphore, evidence reads, and artifact persistence.
- Modify `caos/server/caos/config.py` for provider key/model and feature/pilot
  settings.
- Modify `caos/server/requirements.txt` and review transitive changes.
- Extend `caos/tests/test_cp_dr_runtime.py`.

### Provider dependency and construction

1. Pin `anthropic>=1,<2`; test the lock-free clean install at the current stable
   SDK before landing.
2. Construct the concrete client with `max_retries=0` and the active-worker
   timeout. Do not add a provider interface or factory.
3. Keep one CP-DR-specific `threading.BoundedSemaphore(2)` per worker.
4. Keep `claude-sonnet-4-6` as the pinned initial model and persist it on the run
   before the first call.

### Prompt and tool loop

1. Stage authority instead of loading the full skill bundle on every turn:
   - planning: binding skill plus brief/planning sections;
   - research: source policy, claim ledger, stop rules, and issuer profile;
   - synthesis: output/QA contract plus accumulated structured ledger.
2. Give the planning call only the bounded brief and source metadata manifest;
   do not expose substantive evidence blocks or the evidence tool before plan
   approval.
3. Pass immutable methodology in `system=`. Put the brief, approved plan,
   upstream digests, and source manifest in normal user content. Mark filenames,
   evidence, and tool results as lower-authority untrusted data.
4. Expose one strict client tool during approved research:

   ```json
   {
     "name": "read_evidence",
     "strict": true,
     "input_schema": {
       "type": "object",
       "properties": {
         "source_id": {"type": "string"},
         "block_ids": {"type": "array", "items": {"type": "string"}}
       },
       "required": ["source_id", "block_ids"],
       "additionalProperties": false
     }
   }
   ```

5. For each read, verify case ownership, pinned source-set membership, source not
   withdrawn, block existence, and all remaining limits. Return source digest,
   block ID, locator, extractor version, confidence, and text; never return
   `vault_path`.
6. Append the complete assistant tool-use content, then an immediate user
   message with `tool_result` blocks first. Disable parallel tool use.
7. Continue only on `tool_use`; accept final structured output only on
   `end_turn`. Classify refusal, `max_tokens`, context termination, malformed
   content, and unexpected stop reasons as explicit failures.
8. Use `output_config.format` and `anthropic.transform_schema()` for the final
   strict CP-DR response. Revalidate all constraints locally because schema
   transformation may omit unsupported keywords.
9. If final validation fails, allow one repair message containing only bounded
   validation errors and the existing conversation. The repair cannot call the
   evidence tool or add evidence.

### Cumulative budgets

Persist and enforce one run-wide ledger across planning, pause, resume, research,
retry, and repair:

- 8 model turns;
- 12 evidence reads;
- 1 MiB returned evidence;
- 100,000 input tokens;
- 8,000 output tokens;
- 3 minutes active worker time;
- one provider retry;
- one validation repair with no new evidence;
- two concurrent provider calls per worker.

The analyst approval wait consumes no active worker time.

Call `messages.count_tokens()` before a generation. Reserve its count against
the input budget and the requested `max_tokens` against the output budget before
sending. On success, reconcile both to actual usage. On timeout or unknown
usage, keep the reservations charged; retry only if the remaining run budget can
fund the same request. Persist an in-flight request digest before sending. A
reclaimed run with an unresolved in-flight request fails closed instead of
silently repeating unknown spend.

### Validation and artifact sequence

Implement this order exactly:

1. verify vendor integrity and accepted CP-0 lineage;
2. verify exact approved-plan hash, source set, model, and remaining budget;
3. run the bounded Messages/tool loop;
4. parse strict Pydantic outer and nested models with unknown fields forbidden;
5. reject non-finite numbers, oversize values, wrong identities, and citations
   to blocks not returned in this run;
6. require entity, period, unit/currency, and perimeter on material numbers;
7. run the host semantic-completeness and coverage gates;
8. call vendored `confidence_score.compute(...)` rather than copying its
   formula;
9. render `[ScopeKey]_CP-DR_[YYYYMMDD].md` with the required YAML and six H2s;
10. call vendored `validate_handoff.validate_text(...)` with filename,
    `expected_module="CP-DR"`, expected run ID, and expected reporting period;
11. persist through `put_artifact_fenced()` only after every check passes.

### Failure mapping

Map failures to the design's stable codes:

- `AGENT_PROVIDER_UNAVAILABLE`
- `AGENT_PROVIDER_REJECTED`
- `AGENT_PROVIDER_TIMEOUT`
- `AGENT_BUDGET_EXCEEDED`
- `AGENT_OUTPUT_INVALID`
- `AGENT_AUTHORITY_MISMATCH`

Never fall back to the generic deterministic CP-DR summary.

### Verification

Add deterministic fake-client tests for:

- planning, approval, tool use, structured output, canonical artifact, and
  snapshot acceptance;
- exact SDK request shape, system placement, schema transformation, and tool
  result ordering;
- every provider exception class and retry/no-retry decision;
- refusal, context, stop-reason, JSON, schema, citation, numerical-context,
  completeness, confidence, filename, heading, period, and identity failures;
- cross-case, withdrawn-source, absent-block, byte, call, token, turn, time, and
  concurrency denials;
- timeout unknown-usage reservation and reclaimed in-flight fail-closed behavior;
- no transcript, prompt, evidence text, provider error body, or key in persisted
  audits/events.

```bash
PYTHONPATH=caos/server caos/server/.venv/bin/python -m pytest caos/tests/test_cp_dr_runtime.py -q
caos/server/.venv/bin/python caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/scripts/confidence_score.py --self-check
```

### Anti-pattern guards

- Do not catch all SDK errors as provider unavailability.
- Do not trust tool arguments, transformed schemas, model citations, or model
  identity fields.
- Do not persist hidden reasoning or provider transcripts.
- Do not add web, Files, MCP, managed-agent, shell, code, memory, or server-side
  provider tools.

### Exit gate

The deterministic end-to-end CP-DR test produces one canonical, cited, fenced,
validator-passing artifact and every forced failure produces its exact explicit
code with no fallback artifact.

## Phase 5: Add the Run Console workflow

### Objective

Let an analyst submit the bounded brief, review the full proposed plan, approve
its exact hash, and understand disabled or failed states without leaving the
existing Run Console.

### Files

- Modify `caos/frontend/src/components/Workspace.tsx`.
- Modify `caos/frontend/src/lib/workbench.ts` only for shared case/run types.
- Modify `caos/frontend/app/globals.css` only if existing panel, table, callout,
  focus, and unavailable styles cannot express the state.
- Modify `caos/frontend/scripts/workbench-smoke.mjs`.
- Modify `caos/frontend/scripts/a11y-axe.mjs`.
- Modify `caos/server/caos/http.py` to expose actor-specific CP-DR availability
  in existing case detail; do not add a capability endpoint.

### Public response and availability

Extend the existing case response with:

```text
deep_research_available: boolean
deep_research_unavailable_reason: string | null
```

Availability is true only when the feature is enabled and either the actor or
case is on the pilot allowlist. An empty allowlist denies all. The API still
rechecks eligibility when starting a run; UI state is informative, not an
authorization boundary.

Extend the existing run response with the persisted `research` object. Do not
create a second read model or endpoint.

### UI implementation

1. Keep state and requests in `Workspace.tsx`; the application has no hook/data
   layer to extend.
2. Add controlled pathway state. When Deep Research is selected:
   - force full depth and disable screen;
   - show labeled fields for question, context, native date, horizon,
     must-answer lines, and exclusion lines;
   - split the two line-based fields into bounded arrays before submission.
3. If unavailable, disable the pathway option and show the server reason with
   `aria-describedby`.
4. Branch paused-state copy on `run.error.code`; preserve `SOURCE_SET_EMPTY` and
   add a distinct `PLAN_APPROVAL_REQUIRED` view.
5. Render every proposed workstream field and the complete plan hash in a
   semantic table or list. Do not truncate the hash being approved.
6. Add one `Approve research plan` action posting the currently displayed hash.
   Reuse the existing pending-action pattern and refresh the ordinary run record
   after success.
7. Add `research.plan_ready` and `research.plan_approved` to the existing SSE
   refresh list. Retain polling as the recovery path.
8. Use `role="status"`/`aria-live="polite"` for normal pending approval and
   `role="alert"` for request failures. Preserve visible text alongside color.

### Copy-ready references

- Request helper and run type: `caos/frontend/src/components/Workspace.tsx:10,36-43`
- Case/run boundary guards: `caos/frontend/src/components/Workspace.tsx:140-190`
- SSE refresh: `caos/frontend/src/components/Workspace.tsx:290-299`
- Start/accept pending actions: `caos/frontend/src/components/Workspace.tsx:324-356`
- Run Console: `caos/frontend/src/components/Workspace.tsx:465-467`
- Unavailable state: `caos/frontend/src/components/Workspace.tsx:543-548`
- Existing unavailable style: `caos/frontend/app/globals.css:98-102`

### Verification

- Extend the workbench journey with an exact mocked pending-plan response and
  approval request. Intercept both exact and query-string request forms and
  assert the fixture was actually hit.
- Add axe coverage for the pending-plan fixture, not only the generic Run
  Console route.
- Verify keyboard operation, visible focus, reduced motion, 375px reflow, no
  page-level overflow, and readable long hashes/workstream content.

```bash
npm --prefix caos/frontend run lint -- --max-warnings=0
npm --prefix caos/frontend run build
npm --prefix caos/frontend run test:workbench
npm --prefix caos/frontend run a11y
```

### Anti-pattern guards

- Do not infer every pause means missing sources.
- Do not hide plan approval behind color, hover, or a mouse-only control.
- Do not expose the provider key, provider exception body, prompt, or source
  excerpts in the browser.
- Do not add a new UI library or state manager.

### Exit gate

An analyst can complete brief → plan review → exact approval → running → artifact
review → snapshot acceptance, and a disabled deployment remains explicit and
accessible.

## Phase 6: Wire the disabled deployment and operational metadata

### Objective

Ship a production-safe foundation that remains off until external data and pilot
gates are satisfied.

### Files

- Modify `caos/deploy/docker-compose.yml`.
- Modify `caos/.env.example`.
- Modify `caos/README.md`.
- Modify `.github/workflows/ci.yml` and `.github/workflows/nightly.yml` only as
  needed to keep provider credentials blank and exercise deterministic fakes.
- Modify `caos/tests/test_clean_slate.py` for environment/Compose coverage.

### Settings and secret placement

Use these exact environment names:

```text
CPDR_AGENT_ENABLED=false
CPDR_PILOT_CASE_IDS=
CPDR_PILOT_SUBJECTS=
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=
```

- Parse the boolean strictly; reject unknown text.
- Parse allowlists as trimmed comma-separated exact values; empty lists deny all.
- Give the app and worker the flag, allowlists, and model.
- Give `ANTHROPIC_API_KEY` to the worker only. Do not add it to the app, browser,
  build arguments, Caddy, oauth2-proxy, health response, logs, or artifacts.
- Keep Compose `read_only`, `cap_drop: ["ALL"]`, and
  `no-new-privileges:true` unchanged.
- Disabled deployments and CI must boot with an empty key.

### Operational metadata

Persist one bounded attempt record after each provider interaction in the
run-attached research state, under the current lease:

- run/node/attempt/model/approved-plan IDs;
- authority, prompt, source-set, upstream, request, and output digests;
- provider request ID;
- tool name and referenced source/block IDs;
- input/output tokens, latency, retry count, stop reason, and terminal code.

Keep durable events coarse. Do not emit token deltas. Do not store prompts,
conversations, raw source/tool text, hidden reasoning, provider exception bodies,
or secrets.

### Verification

```bash
docker compose -f caos/deploy/docker-compose.yml config -q --no-interpolate
docker compose --env-file caos/.env.example -f caos/deploy/docker-compose.yml config -q
caos/server/.venv/bin/python -m pytest caos/tests/test_clean_slate.py -q -k 'env or compose or provider or cpdr'
```

Build the image and prove:

- app environment has no provider key;
- worker environment receives the key only when supplied by the operator;
- health works while the feature is disabled;
- a missing worker key produces `AGENT_PROVIDER_UNAVAILABLE` only for an
  eligible CP-DR run;
- logs and persisted state pass a secret/source-text scan.

### Anti-pattern guards

- Do not make the provider key Compose-required; that would break the disabled
  foundation.
- Do not call the provider from `/api/health`.
- Do not add a metrics platform for Phase 1; use the existing durable run/audit
  state.

### Exit gate

The production image and Compose stack pass with CP-DR disabled, the provider
key is worker-only, and an operator can enable only a named user or case without
rebuilding the image.

## Phase 7: Verify, evaluate, and pilot

### Objective

Prove correctness and research value before any user-visible production
activation.

### Full automated gate

Use the project virtual environment and current CI commands:

```bash
caos/server/.venv/bin/python -m ruff check --config ruff.toml caos/server caos/tests --exclude caos/server/caos/methodology/vendor
caos/server/.venv/bin/python -m pytest caos/tests -q -W always
caos/server/.venv/bin/python run_sec_audit.py
npm --prefix caos/frontend run lint -- --max-warnings=0
npm --prefix caos/frontend run build
npm --prefix caos/frontend run test:workbench
npm --prefix caos/frontend run a11y
docker compose -f caos/deploy/docker-compose.yml config -q --no-interpolate
docker compose --env-file caos/.env.example -f caos/deploy/docker-compose.yml config -q
caos/server/.venv/bin/python caos/deploy/verify_image_resources.py
caos/server/.venv/bin/python "Modular OS/tools/check_module_consistency.py"
```

Also run clean Python 3.11 and 3.14 installs, `pip check`, the existing CI
`pip-audit` gate, the image vulnerability scan, and one live PostgreSQL lease/
pause/resume test.

Run `rewrite-tournament`, `confidence-review`, and GitNexus staged
`detect_changes()` after the complete implementation, even if each phase already
ran them.

### Live-provider smoke test

After ZDR and commercial processing approval:

1. Enable one sanitized internal case and one named analyst.
2. Use no production documents.
3. Verify request ID, model, tokens, latency, tools, digests, stop reason, and
   terminal state.
4. Verify no prompt, transcript, source text, key, or provider exception body is
   retained outside the final validated artifact.
5. Force a wrong tool argument, timeout, invalid citation, lost lease, and
   malformed output; confirm explicit failure and no fallback artifact.

### Twenty-case shadow evaluation

Use 20 sanitized, representative source sets. Keep reviewer identities and case
mapping outside the repository.

For every case:

1. preserve the current deterministic output as the baseline;
2. run the candidate against the same pinned source-set version and brief;
3. strip model/baseline labels before review;
4. have a buy-side credit analyst score evidence grounding, decision usefulness,
   conflict handling, and completeness on the agreed five-point rubric;
5. retain only allowed operational metadata and the scored artifact references.

Activation requires all of the following:

- every material claim has a valid returned-block citation;
- zero unsupported material claims;
- zero cross-case reads or unapproved tools;
- at least 19 of 20 runs complete within all budgets;
- p95 active worker time no greater than three minutes;
- complete attempt telemetry for every provider interaction;
- at least 16 of 20 candidates score 4/5 or better and win their blinded
  pairwise comparison with the deterministic baseline.

Any critical grounding, privacy, case-isolation, authorization, methodology, or
lease-fencing failure blocks activation regardless of aggregate scores.

### Opt-in pilot and rollback

- Enable only the named subjects/cases that passed governance review.
- Keep plan approval and snapshot acceptance mandatory.
- Review cost, latency, unsupported-claim scans, and analyst scores after every
  pilot batch.
- Roll back by setting `CPDR_AGENT_ENABLED=false`. The UI must show Deep Research
  as unavailable; the runtime must never restore the generic CP-DR summary.
- Do not enable CP-1C, CP-5, CP-6, another provider, LITE research, sector scope,
  or web access under this plan. Each requires a new design and red-team gate.

### Exit gate

The shadow gates pass, governance approves activation, the opt-in pilot remains
bounded, and rollback has been exercised successfully.

## Definition of done

- `WorkflowRuntime` remains the sole supervisor.
- Only CP-DR can call the provider, through one static dispatch.
- CP-0, full issuer scope, supplied sources, standard budget, and exact plan
  approval are enforced by the host.
- Provider calls are renewable, fenced, budgeted, classified, and auditable.
- Evidence reads cannot cross case or pinned source-set boundaries.
- Only canonical validator-passing CP-DR artifacts can reach snapshot acceptance.
- The provider secret exists only in the worker.
- Disabled and rollback states are explicit; no placeholder success is emitted.
- The automated, live smoke, shadow, accessibility, security, and rollback gates
  all pass before broader adoption.
