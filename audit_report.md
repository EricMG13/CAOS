# CAOS — 2026 Multi-Agent Deployment Audit

**Scope:** Secrets management · Docker (non-root / multi-stage / `.dockerignore`) ·
agent-loop turn caps · Pydantic tool validation · async web endpoints ·
multi-agent architecture & state · tool fencing · network isolation ·
observability · graceful degradation.

**Date:** 2026-06-24 · **Branch:** `fix/vmo2-followups` · **Auditor:** Claude Code (automated)

---

## 0. Architectural context (read this first)

CAOS is **not** an open agent mesh and has no autonomous tool-using agents. It is
a single FastAPI process driving a **deterministic governed DAG** (the CP-X
`PlannerRouter`, [`engine/planner.py`](caos/server/engine/planner.py)). Modules
are topologically ordered (Kahn's algorithm,
[planner.py:213](caos/server/engine/planner.py:213)); the router *routes and
governs, it does not analyse*. LLMs appear only as **bounded, optional, tool-less
narrators** inside individual modules (synth, council, debate, chat, deep
research), and every consequential verdict is computed by deterministic code, not
a model (e.g. the debate chair tally,
[debate.py:216](caos/server/engine/debate.py:216)).

This design **already satisfies** most of the checklist's hardest items
(supervisor vs. mesh, no "you do it" loops, least-privilege tooling, memory
isolation). The faults below are real but sit at the edges; **no CRITICAL faults
were found.** A conformance summary of what passed is in §6.

---

## 1. CRITICAL

*None identified.*

The properties that would make this section non-empty — an LLM lane with
write/filesystem/DB tools, root containers, a published app port, forgeable
identity, or an unbounded agent loop — are all absent. See §6.

---

## 2. HIGH

### [x] H-1 — Per-run token budget resets on retry and the whole run re-bills on re-claim
**RESOLVED:** `execute_run` now seeds `RunBudget` from the run's persisted
`tokens_used` (so the budget is cumulative across attempts, not per-attempt) and
`_mark_run_failed` recovers the attempt's spend from the budget contextvar after
its rollback (so a failed/cancelled attempt's tokens are no longer lost) — capping
true per-run spend at `run_token_budget` instead of up to ~3× it.

**Verification:** 2 regression tests added
([`test_budget.py`](caos/tests/server/test_budget.py)) — rehydrate-on-reclaim +
persist-on-failure. Server suite `343 passed, 2 skipped`; budget/executor subset
`PYTEST_EXIT=0`. `docker compose build app` → `BUILD_EXIT=0` (image
`caos-app:latest`, 785 MB), verified on colima/Docker 29.5.2.

**Files:** [`engine/budget.py`](caos/server/engine/budget.py) ·
[`run_executor.py:192`](caos/server/run_executor.py:192) ·
[`config.py:106`](caos/server/config.py:106)

`run_token_budget` (default 120 000) is the stated runaway-billing guard
([config.py:142](caos/server/config.py:142)). But `RunBudget` is an in-memory
`ContextVar` ([budget.py:40](caos/server/engine/budget.py:40)) created fresh for
each `execute_run`; it is **never persisted**. The `QueueWorker` re-claims a
lease-expired run up to `caos_run_max_attempts = 3` times
([run_executor.py:201-208](caos/server/run_executor.py:201)) and re-runs
`execute_run` **from the top** — there is no per-module checkpoint, so every
already-completed LLM module re-executes and re-bills. A run that flaps late
(times out / worker dies after the expensive modules) can therefore spend up to
**~3× the configured budget** (≈360k tokens), and the budget's per-attempt reset
means the cap it advertises is not the cap that holds across a run's lifetime.

**Fix:** persist `used` onto the `Run` row and rehydrate `RunBudget` from it on
re-claim, so the budget is cumulative across attempts; optionally checkpoint
completed module payloads so a re-claim resumes rather than restarts. Lower
`caos_run_max_attempts` only masks it.

---

## 3. MEDIUM

### [x] M-1 — No LLM-specific tracing (model / tokens / latency / tool-choice per lane)
**RESOLVED:** every live inference now routes through `engine/llm_client.create`
(or `budget.trace_llm` for the streaming/beta lanes), which emits one structured
`caos.llm` JSON line per call — `run_id`, `lane`, `model`, `fallback`, in/out
tokens, latency, `stop_reason` — correlating a run's whole LLM fan-out with zero
new infra.

**Files:** [`main.py:30`](caos/server/main.py:30) ·
[`engine/synth.py`](caos/server/engine/synth.py) ·
[`engine/debate.py`](caos/server/engine/debate.py)

Observability is stdlib `logging` only: a structured JSON **HTTP** access log
([main.py:139](caos/server/main.py:139)), per-call `output_tokens` logs in synth,
and unhandled-exception logging ([main.py:167](caos/server/main.py:167)). There
is **no per-inference trace** correlating model, prompt, token usage, latency, and
which lane (synth vs. council seat vs. debate advocate) fired, keyed by `run_id`.
For a run that fans out across many LLM calls, you cannot reconstruct the
reasoning/spend path of a single run from the logs. (Note: the checklist's
"`print()` will fail you" concern is partly met — this code uses `logging`, not
`print` — but HTTP logs ≠ agent traces.)

**Fix:** self-hostable OSS tracing satisfies the no-paid-services constraint —
Langfuse or Arize Phoenix (both self-hostable) or OpenTelemetry spans around each
`messages.create`, tagged with `run_id` + lane. Even a structured
`caos.llm` JSON line per call (run_id, module, model, in/out tokens, ms,
stop_reason) would close most of the gap with zero new infra.

### [x] M-2 — No automated heavy→cheap model fallback on rate-limit / overload
**RESOLVED:** `engine/llm_client.create` now catches a 429/529 that survives the
SDK's own retries and retries the call ONCE on `synth_executor_model` before
surfacing the error; the deep-research streaming lane downgrades the same way for
the rest of its run. A heavy-model quota spike degrades to a cheaper model instead
of 502-ing the lane.

**Files:** [`llm.py:69`](caos/server/llm.py:69) ·
[`deepresearch.py:197`](caos/server/deepresearch.py:197) ·
[`config.py:92`](caos/server/config.py:92)

On a 429/529 the Anthropic SDK retries in place (default `max_retries`), then the
call fails: chat and deep research return **502**
([chat.py:62](caos/server/routes/chat.py:62),
[research.py:43](caos/server/routes/research.py:43)). There is no automatic
downgrade from `anthropic_model` (`claude-opus-4-8`) to a faster/cheaper model.
The `ai_mode: "lite"` preset ([deepresearch.py:54](caos/server/deepresearch.py:54))
and `synth_executor_model` exist but are **manual** per-analyst settings, not a
rate-limit fallback. *Partial mitigant:* the engine modules degrade to their
**deterministic fixture** path when a live call fails, so a run completes (gated)
rather than erroring — graceful degradation exists, just not a model fallback.

**Fix:** wrap the live `messages.create` calls so a `RateLimitError` /
overloaded after SDK retries falls back to `synth_executor_model`
(`claude-sonnet-4-6`) before surfacing 502 / before degrading to fixture.

### [x] M-3 — Deep Research was synchronous and connection-bound (not durable)
**RESOLVED:** Deep Research now runs as a durable background job. POST
`/api/research` persists a `ResearchJob` (migration 0010) and spawns a task in the
new `research_executor.py` (in-process + sweep-on-boot, mirroring
`InProcessExecutor`), returning the job id immediately; the client polls
GET `/api/research/{id}` (scoped to `analyst_id` — a 404, not 403, for another
analyst's job, so per-user isolation holds too). A dropped client/proxy connection
no longer aborts the run or loses its token spend; a process restart sweeps
stranded `running` jobs to failed (a stream can't be resumed) and the analyst
re-submits. Frontend `deepResearch` reimplemented as create+poll, preserving the
`Promise<ResearchResult>` contract so the page is unchanged. (Issuer chat stays a
single short bounded call — low blast radius, left synchronous.)

**Hardened post-review:** a 5-lens adversarial review caught that the first cut of
the client poll loop aborted the whole run on a *single* transient GET failure
(proxy blip / 20s timeout) — defeating the durability goal, since the job survived
server-side but the client threw it away. Fixed: the loop now tolerates
consecutive transport errors and keeps polling, bounds itself with a 15-min
wall-clock cap, and polls immediately (no 2s floor on the demo). Also added a
concurrency semaphore (`caos_research_concurrency`, default 2) so fire-and-forget
jobs can't accumulate unbounded multi-minute runs — restoring the backpressure the
old synchronous call had.

**Verification:** server suite **357 passed / 2 skipped** (py3.9 + py3.11) incl.
new tests for background completion, mark-failed, sweep, per-analyst isolation,
the `running`→poll-again branch, and the concurrency cap; frontend `tsc` clean +
`next build` green in the image; E2E stub exercises running→complete polling.

**Files:** [`research_executor.py`](caos/server/research_executor.py) ·
[`routes/research.py`](caos/server/routes/research.py) ·
[`database.py` ResearchJob](caos/server/database.py) ·
[`migrations/0010`](caos/server/migrations/versions/0010_research_jobs.py) ·
[`api.ts deepResearch`](caos/frontend/src/lib/api.ts:205)

Unlike module runs (durable via the Postgres queue + lease/reap), the
multi-minute Deep Research call holds the HTTP connection for its full duration —
the code's own `ponytail:` note flags this
([deepresearch.py:13](caos/server/deepresearch.py:13)). If the client connection
or an upstream proxy drops mid-run, the work and its token spend are lost with no
resume. Same shape for issuer chat (single bounded call, lower blast radius).

**Fix:** promote Deep Research to the existing `run_executor` background-job +
polling pattern (the durable path already in the codebase), so a dropped
connection doesn't discard an in-flight research run.

### [x] M-4 — Shared analyst access code defaults to a public value with no production guard
**RESOLVED:** `lifespan` now logs a loud production warning when
`analyst_signup_code` is unset or the in-source default `131113` — a warning, not
fail-closed, because the SSO edge fronts it and the live pilot legitimately runs
that code, so fail-closed would break a running deploy for a defense-in-depth gap.

**Files:** [`config.py:57`](caos/server/config.py:57) ·
[`routes/auth.py:107`](caos/server/routes/auth.py:107) ·
[`main.py:46`](caos/server/main.py:46)

`session_secret` and `edge_proxy_secret` fail closed / warn loudly in production
([main.py:46-53](caos/server/main.py:46)). `analyst_signup_code` does **not**: it
defaults to the in-source literal `"131113"`
([config.py:57](caos/server/config.py:57)) and the login compares against it with
no startup check that it was overridden in prod. *Mitigant:* the code only gates
**profile self-registration**, sits behind the oauth2-proxy SSO network gate, and
new profiles are bound to the verified `X-Forwarded-Email`
([auth.py:117](caos/server/routes/auth.py:117)) — so this is a defense-in-depth
weakness, not a primary authn bypass.

**Fix:** add `analyst_signup_code` to the production fail-closed/warn block in
`lifespan` alongside `session_secret`, so booting prod on the default code is
refused or loudly warned.

---

## 4. LOW

### [x] L-1 — `.dockerignore` does not defensively exclude `.git/`
**RESOLVED:** added `**/.git` + `.git` to [`caos/.dockerignore`](caos/.dockerignore)
(belt-and-suspenders; the repo `.git/` was already outside the `caos/` build context).

**File:** [`caos/.dockerignore`](caos/.dockerignore)

`.env`, `.env.*`, `**/.venv`, `**/__pycache__`, `**/*.pyc`, `server/static`,
`server/data` are all excluded — good. `.git/` is **not** listed. *Mitigant:* the
build context is `caos/` ([docker-compose.yml:36](caos/deploy/docker-compose.yml:36))
and the repo `.git/` lives at the repo root, **outside** the context, so nothing
is baked today. Add it anyway as belt-and-suspenders in case the context ever
widens. (No ChromaDB/FAISS stores exist — retrieval is in-Postgres BM25,
[retrieval.py](caos/server/retrieval.py) — so that part of the checklist is N/A.)

### [x] L-2 — `extract_json` returns a raw `json.loads` dict, not a Pydantic model
**RESOLVED:** `extract_json` gained an **opt-in** `schema=<PydanticModel>` param —
when passed, the reply is validated at the boundary and the validated model is
returned (a shape/type mismatch degrades to None, same as a no-JSON reply); without
it the raw-dict contract is unchanged. The add-back extractor (`engine/adjusted.py`)
adopts it via `_AddbackExtract`, so the type-checks (`isinstance`/coercion) move to
the schema while the domain range (`0 < pct < 1`) stays in the caller — it's a real
adopter, not a speculative param. (An earlier unreachable `isinstance(parsed, dict)`
guard was reverted; the covenant extractor keeps its working manual validation —
migrate later if desired.)

**Files:** [`engine/llm_safety.py:57`](caos/server/engine/llm_safety.py:57) ·
[`engine/adjusted.py` `_AddbackExtract`](caos/server/engine/adjusted.py:94)

The shared document→LLM extractor parses the first `{...}` from the reply and
returns the raw dict; callers do their own domain validation + `safe_chunk_id`
gating. It works and is injection-hardened, but the validation isn't a declared
Pydantic schema at that boundary the way the synth path is (forced-tool +
`validate_payload`, [synth.py:22-25](caos/server/engine/synth.py:22)). Low risk
because outputs are clamped downstream and the CP-5 gate is deterministic.

**Fix (optional):** validate the parsed dict against a small Pydantic model per
extractor for parity with the synth path.

---

## 5. Per-requirement verdict matrix

| # | Requirement | Verdict | Evidence |
|---|-------------|---------|----------|
| A1 | Centralized supervisor (no open mesh / "you do it" loops) | ✅ PASS | Deterministic CP-X `PlannerRouter` DAG, Kahn order; verdicts are code, not LLM ([planner.py](caos/server/engine/planner.py), [debate.py:216](caos/server/engine/debate.py:216)) |
| A2 | Durable execution (survive API/container drop) | ✅ PASS | Runs durable via Postgres queue+lease+reap ([run_executor.py:134](caos/server/run_executor.py:134)); deep research now a durable background job + poll (**M-3 fixed**); budget persisted across retries (**H-1 fixed**). Issuer chat stays a short synchronous call (low blast radius) |
| A3 | Hard turn caps & token budgets on every loop | ✅ PASS | Caps everywhere — `_MAX_CONTINUATIONS=4` + `max_uses` (deep research), one-shot repair (synth), single-call lanes, `run_token_budget` now cumulative across attempts (**H-1 fixed**) |
| A4 | Per-user / per-session memory isolation | ✅ PASS | Per-run DB session + `run_id` scope; `RunBudget` is per-task `ContextVar`; chat stateless (client-supplied history); retrieval scoped per issuer ([run_executor.py:30](caos/server/run_executor.py:30)) |
| B1 | Multi-stage Docker build | ✅ PASS | node build → python runtime ([Dockerfile:8,16](caos/deploy/Dockerfile:16)) |
| B2 | Non-root execution | ✅ PASS | `USER caos` uid 10001 + `cap_drop: ALL` + `read_only` ([Dockerfile:44](caos/deploy/Dockerfile:44), [docker-compose.yml:46](caos/deploy/docker-compose.yml:46)) |
| B3 | Strict `.dockerignore` (`.env`, `.git`, vectors, `__pycache__`) | ✅ PASS | `.env*`/`.venv`/`__pycache__`/local data excluded; `.git` now listed too (**L-1 fixed**) |
| C1 | Least-privilege tool fencing | ✅ PASS | No LLM lane has DB-write / filesystem / shell tools. Only read-only `web_search` server tool (deep research); synth's only tool is an **output** emitter |
| C2 | Pydantic guardrails on inputs **and** outputs | ✅ PASS | Inputs: `ChatRequest`/`ResearchBrief` constrained ([chat.py:27](caos/server/routes/chat.py:27)). Outputs: forced-tool + `validate_payload` + one-shot repair (synth); `extract_json` opt-in `schema=` boundary validation (**L-2 fixed**) |
| C3 | Network isolation (no agent port public) | ✅ PASS | App has **no** `ports:`; reachable only via oauth2-proxy on `internal` net ([docker-compose.yml:72](caos/deploy/docker-compose.yml:72)) |
| D1 | Agentic tracing (not `print()`) | ✅ PASS | Structured `caos.llm` JSON line per inference (run_id/lane/model/tokens/ms/stop) via the `llm_client` seam (**M-1 fixed**) |
| D2 | Automated fallback model on rate limit | ✅ PASS | `llm_client.create` retries on `synth_executor_model` on 429/529; deep-research stream downgrades too (**M-2 fixed**) |
| — | Secrets management | ✅ PASS | All secrets env-driven via `pydantic-settings`; `.env` git/docker-ignored; gitleaks in CI ([ci.yml](.github/workflows/ci.yml)); `session_secret`/`edge_proxy_secret` fail-closed in prod. Exception: signup-code default (**M-4**) |
| — | Async web endpoints | ✅ PASS | All 33 route handlers `async def`; non-async `def`s are helpers/validators only |

---

## 6. Conformant / Strengths (no action needed)

- **Supervisor, not mesh.** CP-X is a pure, unit-testable routing/governance DAG;
  the runaway-collaboration failure mode the checklist warns about is structurally
  impossible here.
- **Tool-less LLMs.** The single most important property: no model lane holds a
  write, filesystem, shell, or DB tool. An indirect prompt injection's blast
  radius is "a wrong-but-in-range figure", deterministically gated by CP-5
  ([llm_safety.py:1-18](caos/server/engine/llm_safety.py:1)).
- **Injection hardening.** Untrusted document/web content is delimited and
  rule-fenced (`wrap_untrusted`, `UNTRUSTED_RULE`); model-returned evidence ids
  are validated against actually-retrieved chunks (`safe_chunk_id`).
- **Container hardening exceeds the checklist:** `cap_drop: ALL`, `read_only`
  rootfs, `no-new-privileges`, `tmpfs` for scratch, `mem_limit`, healthchecks,
  per-service hardening.
- **Identity fails closed** in deployed contexts (401 on missing forwarded
  identity), with an optional enforced edge-secret check on top of network
  isolation.
- **Graceful degradation** is pervasive: every live LLM lane has a deterministic
  fixture fallback, so the engine runs fully offline and a failed call degrades
  rather than errors.

---

## 7. Remediation priority

1. ~~**H-1** — persist token budget across re-claims (caps true per-run spend).~~
   **DONE** — budget rehydrated from `tokens_used` + recovered in `_mark_run_failed`.
   (Module-level checkpointing remains optional/deferred — the billing cap holds
   without it.)
2. ~~**M-1** — structured `caos.llm` per-call logging keyed by `run_id`.~~ **DONE**.
3. ~~**M-2** — automatic heavy→cheap model fallback on rate-limit.~~ **DONE**.
4. ~~**M-3** — move Deep Research onto the durable background-job path.~~ **DONE**
   (persisted `ResearchJob` + `research_executor` + poll endpoint + create-poll frontend).
5. ~~**M-4** — guard the default `analyst_signup_code` in production.~~ **DONE**
   (loud prod warning).
6. ~~**L-1** — defensive `.git` ignore.~~ **DONE**. ~~**L-2** — Pydantic-validate
   `extract_json`.~~ **DONE** (opt-in `schema=`, adopted by the add-back extractor).

**Verification (MEDIUM/LOW round):** new seam centralizes every plain
`messages.create` in `engine/llm_client.py` (M-1 trace + M-2 fallback);
`test_llm_client.py` (4) + synth single-count guards (3) added. Full server suite
**350 passed, 2 skipped** (py3.9 + py3.11); `docker compose build app` →
`BUILD2_EXIT=0`. A 4-lens adversarial review (correctness / security / runtime /
tests) surfaced 3 confirmed gaps — all *missing tests on correct code*, now closed;
the L-2 guard was reverted as unreachable. Untrusted-data wrapping verified intact
at every routed lane; the `test_no_unreviewed_llm_call_sites` guard now also tracks
`llm_client.create` callers so no model-reaching lane escapes review.
