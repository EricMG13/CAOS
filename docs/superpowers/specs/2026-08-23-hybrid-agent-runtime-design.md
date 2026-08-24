# Hybrid agent runtime design

**Date:** 2026-08-23

**Status:** Approved design; MVP implemented; activation controls stored

**Initial scope:** CP-DR Deep Research only

## Decision

CAOS will adopt a hybrid execution model by keeping the existing deterministic
Deploy V workflow runtime as the sole supervisor and allowing one explicitly
approved module, CP-DR, to use a bounded specialist agent inside its existing
workflow node.

The agent does not become a second orchestrator. It cannot add nodes, change
dependencies, widen the selected pathway, mutate methodology authority, access
another case, or write directly to application storage. The existing DAG,
source-set pinning, deterministic calculators, validation, fenced persistence,
snapshot acceptance, and report approval remain authoritative.

The MVP succeeds when the bounded CP-DR path is implemented, locally verified,
disabled by default, and deny-all without explicit allowlists. Materially better
source-cited research, governance approval, and production activation remain
post-MVP gates; MVP completion does not claim them.

## Current state

The reusable foundations already exist:

- `WorkflowRuntime._execute()` schedules dependency-safe waves and owns run and
  node state transitions.
- `_build_artifact_with_slot()` is the narrow insertion point for selecting
  deterministic or agent-backed execution.
- `DeployVBundle.compile()` pins the route, dependency graph, source-set
  identity, focus questions, and plan digest.
- `validate_invocation_plan()` and `compile_prompt()` already prevent adaptive
  inputs from supplying system authority, tools, schemas, dependencies, or
  module identity.
- Source ingestion already produces bounded, locator-bearing evidence blocks
  marked as untrusted data.
- Job claims, attempt tokens, artifact fingerprints, explicit run acceptance,
  and authenticated event streaming already provide most lifecycle controls.

The agent path is not currently functional. `AnthropicGateway` is unused; the
Anthropic SDK is not installed; no provider secret reaches the worker; prompt
compilation is test-only; payload validation is shallow; evidence text is not
available to the provider; and a fixed 60-second job lease has no renewal.

## Considered approaches

### Selected: agent inside selected DAG nodes

Dispatch only CP-DR to a bounded agent path. This is the smallest design that
adds adaptive research while preserving CAOS's authority and audit model.

### Rejected: planning-agent supervisor

A planning agent that selects or reorders modules conflicts with the signed
Deploy V route and with the rule that the orchestration specification is
design-time only, not a payload, agent, or node.

### Deferred: independent agent mesh

Peer agents and a synthesizer may later fit CP-6's Bull/Bear/Chair debate, but
they add cost, state, failure modes, and audit ambiguity without helping the
first source-bound research pilot.

## Architecture boundary

`WorkflowRuntime` remains the only supervisor. A static allowlist selects the
agent path:

- CP-DR: bounded specialist execution.
- Every other module: existing deterministic execution.
- CP-PARSE, CP-0, CP-MODEL, CP-MEMO, CP-OS, digests, calculators, schema checks,
  and publication gates: always deterministic.

Phase 1 adds no generic agent framework and no provider interface with one
implementation. It extends the existing Anthropic gateway directly. Any later
provider or module requires a separate design decision backed by pilot data.

## CP-DR plan approval

CP-DR requires an approved research plan before substantive research. CAOS will
enforce that requirement rather than treating a click on “Run” as approval of
workstreams the analyst has not seen.

For a Deep Research request, the client supplies a bounded research brief:

- one research question, up to 400 characters;
- decision context, up to 400 characters;
- an ISO 8601 as-of date;
- a horizon, up to 200 characters;
- up to 10 inclusion and exclusion boundaries, each up to 200 characters.

The subject comes from the case. Phase 1 fixes `source_mode` to `supplied_only`
and `budget` to `standard`; it does not expose web or hybrid source modes.

Execution runs CP-PARSE and CP-0 under the existing route, then CP-DR produces a
3–5-workstream plan containing perspectives, disconfirming tests, completion
tests, and scope boundaries. The run enters the existing `paused` state with
reason `PLAN_APPROVAL_REQUIRED`; the CP-DR node returns to `pending`. The Run
Console shows the plan and its hash.

An analyst with case-write authority approves that exact hash through
`POST /api/runs/{run_id}/research-plan/approve` with `{ "plan_hash": "..." }`.
The endpoint verifies run, case, user, and pending-plan identity before approval
queues the same pinned run. A changed brief or workstream requires a new run;
there is no in-place scope mutation. This keeps the approved-plan hash,
source-set identity, upstream digests, and artifact fingerprint reproducible.

The CP-DR source contains contradictory language about whether CP-0 is optional.
The pilot follows the stricter runtime/catalog/envelope rule: CP-0 remains a
required accepted upstream artifact until signed authority resolves the
conflict.

## Components

### Static dispatcher

The existing node builder checks the module ID. Only CP-DR may enter the agent
path. Selection is not model-controlled and is not caller-configurable.

### Evidence reader

One application-executed, read-only tool exposes existing extracted blocks. A
request identifies a source and block IDs; the host verifies:

- the source belongs to the run's case;
- the source belongs to the run's pinned source set and is not withdrawn;
- every block ID exists;
- per-call and cumulative byte, block, and tool-call limits remain available.

The result contains source ID, source digest, block ID, locator, extractor
version, confidence, and text. It exposes neither vault paths nor arbitrary
filesystem, database, network, or application APIs.

### Anthropic gateway

The worker uses the official Python SDK and the Messages API. Client-side tool
use follows Anthropic's contract: the model requests a typed tool call, CAOS
executes it, and CAOS returns the result. Final output uses structured JSON with
`output_config.format` and the CP-DR schema. SDK automatic retries are disabled;
CAOS owns one bounded retry so usage and attempt semantics remain visible.

Phase 1 retains the configured `claude-sonnet-4-6` model and pins it per run. A
model change requires the same evaluation gate as initial activation.

### Validation gate

Provider output is untrusted until all checks pass:

1. parse the structured response into the exact CP-DR payload model;
2. reject unknown fields, oversized values, non-finite numbers, or wrong module,
   run, profile, selection, source-set, plan, or upstream identity;
3. verify every citation resolves to a block actually returned during the
   attempt;
4. require entity, period, unit, and perimeter on material numeric claims;
5. render canonical Markdown with the required YAML envelope and six ordered
   H2 sections;
6. run the vendored CP-DR confidence scorer and handoff validator plus the host
   semantic-completeness gate;
7. persist only through the existing fenced, idempotent artifact path.

The current host payload/render contract and the vendored canonical contract do
not match. Reconciling them for CP-DR is an activation blocker, not a follow-up.

### Audit and telemetry

Each attempt records only operational metadata:

- run, node, attempt, model, and approved-plan identifiers;
- prompt, authority, source-set, upstream, and output digests;
- provider request ID;
- tool names and referenced source/block IDs;
- token usage, latency, retry count, stop reason, and terminal error code.

It does not persist hidden reasoning, provider conversation transcripts, or
duplicate raw source text. Existing durable events remain coarse lifecycle
events; token streaming does not enter the event/state envelope.

## Data flow

1. The analyst submits a source-bound Deep Research brief.
2. CAOS compiles and persists the normal Deploy V run and nodes against an
   immutable source set.
3. CP-PARSE and CP-0 complete deterministically.
4. CP-DR compiles the authority-first planning prompt and proposes bounded
   workstreams without reading substantive source blocks.
5. CAOS pauses the run and presents the plan hash for analyst approval.
6. Approval requeues the same run.
7. The specialist receives the immutable contract, approved plan, source
   manifest, and upstream digests.
8. The specialist requests evidence through the bounded reader.
9. The provider returns schema-constrained output.
10. CAOS validates schema, citations, lineage, canonical Markdown, and vendored
    QA rules.
11. A current lease holder persists the artifact through the existing fenced,
    idempotent write.
12. The analyst reviews the completed run and explicitly accepts the snapshot.

## Security and data governance

Production activation requires an approved commercial data-processing
arrangement and zero-data-retention configuration for the provider organization.
The provider key is injected only into the worker container; the API container,
browser, logs, artifacts, and event stream never receive it.

Phase 1 uses only the Messages API and application-executed evidence tools. It
does not use provider Files, remote MCP, managed agents, server-side web search,
shell, code execution, or model memory. This choice keeps source access inside
CAOS's case authorization and avoids provider features that may sit outside the
approved retention arrangement.

Source text and tool results remain lower-authority data. They cannot change
tools, schemas, dependencies, budgets, module identity, or system instructions.
Tool arguments are host-validated and outputs are rendered as data, never
executed. Logs and user-visible errors contain no provider secrets or source
text.

## Initial budgets

One CP-DR run shares these cumulative budgets across planning, approval resume,
research, provider retry, and output repair. The approval wait itself does not
consume active worker time.

| Budget | Ceiling |
|---|---:|
| Model turns | 8 |
| Evidence-tool calls | 12 |
| Evidence returned | 1 MiB cumulative |
| Model input | 100,000 tokens cumulative |
| Model output | 8,000 tokens cumulative |
| Active worker time | 3 minutes cumulative |
| Provider retry | 1 failed request, with identical request bytes |
| Output repair | 1, validation errors only and no new evidence |
| Concurrent provider calls | 2 per worker |

The runtime stores remaining budgets with the run so pausing, resuming, retrying,
or repairing cannot reset them. These are downward-only activation ceilings.
Raising any ceiling requires a new evaluation and red-team entry. The initial
deployment has one worker; multi-worker global provider reservations are
deferred until the topology changes.

## Lease, retry, and failure semantics

The worker renews the run lease on a fixed heartbeat while a provider call is in
flight. Renewal and lifecycle events are fenced. If renewal fails, CAOS stops
issuing tools, discards the provider result, emits no stale terminal event, and
allows the current lease holder to decide the run.

Failures are explicit:

| Condition | Result |
|---|---|
| Provider disabled or credential missing | `AGENT_PROVIDER_UNAVAILABLE` |
| Provider authentication or policy rejection | `AGENT_PROVIDER_REJECTED` |
| Rate, network, or timeout failure after one retry | `AGENT_PROVIDER_TIMEOUT` |
| Turn, token, evidence, tool, or wall-time ceiling | `AGENT_BUDGET_EXCEEDED` |
| Invalid schema or citations after one repair | `AGENT_OUTPUT_INVALID` |
| Lost lease | result discarded; no stale write or terminal event |
| CP-DR authority/schema mismatch | `AGENT_AUTHORITY_MISMATCH` |

The run fails closed after a terminal agent error. It never falls back to the
current generic deterministic CP-DR summary. Disabling the feature makes Deep
Research visibly unavailable; it does not manufacture a successful research
artifact. A user starts a new run after correction; Phase 1 adds no general
cancellation or arbitrary retry interface.

## Verification strategy

### Automated tests

- deterministic fake-provider planning, approval, tool, structured-output, and
  acceptance flow;
- invocation allowlist and prompt-injection corpus;
- case, source-set, withdrawn-source, and block authorization;
- tool, byte, turn, token, output, concurrency, and time budgets;
- malformed JSON, unknown fields, non-finite values, oversized values, false
  citations, missing numerical context, and canonical-handoff failures;
- retry classification, identical-request reuse, provider outage, and repair
  exhaustion;
- lease heartbeat, lost-lease discard, fenced events, stale-worker rejection,
  and artifact idempotency;
- in-memory and PostgreSQL source → plan → approval → research → artifact →
  snapshot acceptance;
- existing run, source pinning, report approval, authorization, security, and
  accessibility suites.

### Stored post-MVP live-provider smoke test

The live-provider smoke test is removed from MVP creation but retained as a
mandatory pre-activation control. It is opt-in and never runs with production
documents in CI. Normal CI uses the deterministic fake provider and a blank
provider key.

### Stored post-MVP shadow evaluation

This evaluation is removed from MVP creation but retained as a mandatory
pre-activation control. Before user-visible activation, run 20 sanitized
source-set cases against the current deterministic result and the candidate
agent result. Activation requires:

- every material claim has a valid evidence-block citation;
- zero unsupported material claims;
- zero cross-case reads or unapproved tool calls;
- at least 19 of 20 runs complete within all budgets;
- p95 wall time no greater than 3 minutes;
- model, request, token, latency, tool, and digest telemetry for every attempt;
- at least 16 of 20 candidate outputs receive a blinded analyst score of 4/5 or
  better and win their blinded pairwise comparison with the deterministic
  baseline.

### Stored post-MVP opt-in pilot

This pilot is removed from MVP creation but retained as a mandatory activation
control. Enable CP-DR only for named internal users or cases. Human plan
approval and snapshot acceptance remain mandatory. Any critical grounding,
privacy, case isolation, or methodology-authority failure disables the pilot.
Rollback turns off CP-DR execution visibly; it does not restore the generic
summary.

## Non-goals

Phase 1 does not add:

- an agent framework, provider-neutral interface, orchestration agent, peer
  chat, long-term agent memory, or dynamic DAG;
- external web search, remote MCP, Files API, code execution, or shell tools;
- CP-MODEL activation or any change to its signed-authority block;
- automatic snapshot acceptance, recommendation authority, or report approval;
- agent execution for CP-1C, CP-5, CP-6, or any legacy alias;
- horizontal multi-worker provider reservations, cancellation, or general job
  retry controls.

## Follow-on order

No additional module is agent-enabled automatically. If the CP-DR pilot passes,
the preferred evaluation order is:

1. CP-1C for bounded public-source peer research with deterministic statistics;
2. CP-5 as an isolated reviewer plus deterministic validators;
3. CP-6 as independently isolated Bull, Bear, and Chair roles;
4. reasoning wrappers around CP-1D, CP-2, CP-2A, CP-3, CP-4, and CP-4C while
   retaining their script-owned calculations.

Each expansion receives its own design, provider-data review, evaluation corpus,
and red-team gate.

## Allowed provider APIs

- [Python SDK `Anthropic` client and `messages.create`](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
- [Structured JSON through `output_config.format`](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Client tool-use contract](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [API and zero-data-retention policy](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)

Implementation must not use deprecated `output_format` request parameters,
beta structured-output headers, invented SDK methods, provider-hosted files,
remote MCP connectors, or managed-agent sessions.

## Local authority references

- `caos/server/caos/workflows/domain.py`
- `caos/server/caos/workflows/provider.py`
- `caos/server/caos/methodology/prompt.py`
- `caos/server/caos/methodology/bundle.py`
- `caos/server/caos/sources/domain.py`
- `caos/server/caos/store.py`
- `caos/server/worker.py`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-dr-deep-research/SKILL.md`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-os-credit-os/scripts/credit_os_v/envelope.py`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-os-credit-os/scripts/credit_os_v/routing.py`
- `caos/server/caos/methodology/vendor/deploy_v/skills/cp-os-credit-os/references/CREDIT_OS_RUNTIME_LIMITS_v1.json`
