# CAOS Codebase Deepening Design

**Date:** 2026-08-24
**Status:** Approved
**Scope:** Storage locality, HTTP response contracts, worker scheduling, agent-provider injection, and browser authority state

## Objective

Fix the five design findings from the codebase review without changing CAOS's
user-visible routes, HTTP paths, JSON response shapes, domain error codes, or
product behavior. The result should concentrate transaction logic and runtime
coordination behind deep modules whose interfaces are also their test surfaces.

This is a pre-production cutover. PostgreSQL may start from a fresh database;
there is no migration path from the legacy `caos_state` JSON envelope.

## Constraints

- Preserve all existing HTTP paths and JSON response shapes.
- Preserve current authorization, error codes, status codes, job fencing,
  immutable-source semantics, evidence lineage, and report governance.
- PostgreSQL normalized tables are authoritative in production.
- The memory implementation remains available for local boot and fast tests.
- Do not add a queue system, state-management library, schema generator, ORM,
  or new runtime dependency.
- Do not mechanically split large files unless doing so creates a useful seam.
- Preserve the existing dirty worktree and stage explicit agent-owned paths only.

## Rejected Approaches

### Whole-application rewrite

Replacing storage, routes, frontend state, and runtime execution simultaneously
would discard substantial behavioral coverage and make regressions difficult to
localize. It provides no user-facing benefit.

### Compatibility wrappers over the existing store

Adding protocols and response models while callers still mutate public buckets
would make the interface look cleaner without improving locality or atomicity.
The single-row JSON persistence bottleneck would remain.

### One mega-store protocol

Mirroring the existing store's methods and public buckets into one protocol
would formalize a shallow interface. The seams instead follow consistency
boundaries with independent memory and PostgreSQL adapters.

## Architecture

### SourceCatalog

`SourceCatalog` owns source ingestion, immutable source-set creation, source
withdrawal, note promotion into evidence, current and historical source-set
reads, and pinned evidence reads.

Its external interface is deliberately small:

- ingest one validated source and return its public record plus source set;
- withdraw one source and return the resulting public state;
- list/read current or historical source authority;
- read exact pinned evidence blocks.

The implementation hides ID generation, duplicate detection, source-set
versioning, audit writes, withdrawal cascades, assumption staleness, active loan
universe deactivation, transaction rollback, and storage-specific locking.

Vault writes remain content-addressed and precede the metadata transaction. A
failed transaction may leave an unreferenced blob; it is harmless and garbage
collection is not part of this change.

### RunLedger

`RunLedger` owns runs, nodes, jobs, leases, events, execution artifacts,
research-plan approval, and snapshot acceptance.

Its external interface supports:

- atomic run and node creation;
- run, node, artifact, and source-set reads required by execution;
- pending-job discovery and fenced claim/renew/complete/fail operations;
- atomic artifact/node/event completion and run finalization;
- research-plan approval and snapshot acceptance;
- event streaming reads.

Callers never mutate run, node, case, snapshot, job, artifact, audit, or event
buckets. Fenced writes verify the active attempt inside the same transaction as
their state transition.

### PublicationLedger

`PublicationLedger` owns thesis and recommendation versions, notes, assumptions,
reports, approvals, methodology drafts, and their audit events.

The interface exposes domain transitions rather than generic bucket operations:

- read or append a version with optimistic version checking;
- create and promote notes through `SourceCatalog`;
- create/read assumptions;
- save report inputs, freeze, approve, and read a report;
- create, validate, and confirm methodology drafts;
- read authorized audit history.

Source withdrawal owns its cross-table cascade. `PublicationLedger` reads the
resulting assumption state but does not perform a second transaction.

### ModelLedger

The existing model-build and model-job behavior becomes the `ModelLedger`
interface. Queue, retry, claim, renew, complete, fail, export, and list/read
operations use normalized PostgreSQL tables directly and preserve current
fencing and digest validation.

### Adapter composition

The application composition root creates one adapter set:

- memory adapters backed by private dictionaries and a process-local lock; or
- PostgreSQL adapters backed by normalized tables and database transactions.

The domain modules receive only the interfaces they use. The legacy
`caos_state`, `_merge_state`, full-state snapshot/restore, request-time full
refresh, and caller-managed rollback are removed from live execution. An old
`caos_state` table may remain inert on an existing database, but CAOS neither
reads nor migrates it.

## HTTP Interface

Requests continue to use the existing strict Pydantic models. Add Pydantic
response models for the shared response families:

- identity and case records;
- source and source-set records;
- runs, nodes, research plans, and snapshots;
- model readiness, builds, and worksheets;
- report, publication, RV, and administrative responses.

Every JSON route declares a response model. Models preserve current key names,
nullability, nesting, and omission behavior. Contract tests compare serialized
responses before and after the change and validate the generated OpenAPI schema.

Frontend transport types move from `Workspace.tsx` to `src/lib/api.ts`. This
centralizes the caller-facing interface without adding code generation. Native
FastAPI OpenAPI remains the authority for later generation if manual drift
becomes measurable.

## Worker Interface

The production worker no longer scans storage buckets or calls private runtime
methods. Ledgers expose pending-job discovery. `WorkflowRuntime` gains a public
schedule entry point matching the existing model schedule methods. The worker
tracks returned futures only; runtimes retain claim and fencing responsibility.

Multiple workers may discover the same pending identity. This remains safe
because the database claim is authoritative and exactly one attempt token wins.

## Agent Provider Seam

The agent loop owns evidence-tool policy, budgets, retries, repair, validation,
fencing, telemetry, and `AGENT_*` error normalization.

A minimal provider port owns only:

- token counting for one normalized request;
- message creation for one normalized request.

The Anthropic adapter satisfies the port in production. Tests use an in-memory
fake adapter passed through the composition root. `WorkflowRuntime` accepts the
provider dependency and never constructs or monkeypatches a module-global
provider. Existing provider error codes and retry ceilings remain unchanged.

## Browser Authority State

Case/run selection is an explicit pure reducer. Its state contains selected
case and run identities, hydration status, authority state, generation counters,
and pending transition metadata. Its events cover:

- hydration and route authority;
- case selection;
- run selection and creation;
- request start/success/failure;
- case/run invalidation;
- accepted-snapshot refresh.

React effects perform URL, session-storage, HTTP, SSE, and timer I/O. Every
asynchronous result carries the generation, case ID, and run ID under which it
started. The reducer ignores results that no longer match all three. Existing
Report Studio draft-confirmation behavior remains outside the reducer as a user
decision before dispatching a case transition.

No state-management dependency is added. The reducer is tested with Node's
built-in test runner; browser smoke tests remain the external test surface for
real navigation and storage behavior.

## Data Flows

### Source upload

1. The HTTP handler authenticates and authorizes the case.
2. `SourceCatalog` validates the file, malware result, archive bounds, parsed
   evidence, and content digest.
3. The vault writes the content-addressed blob.
4. One adapter transaction inserts the source, creates the immutable source set,
   and appends the audit event.
5. The response model validates the unchanged public shape.

### Workflow execution

1. `WorkflowRuntime` compiles a plan.
2. `RunLedger` creates the run and all nodes atomically.
3. The worker discovers a pending identity and calls public scheduling.
4. Runtime claims a fenced attempt, executes, and commits artifact, node, event,
   and final state through ledger transitions.
5. Snapshot acceptance verifies pinned source and artifact identities and commits
   the snapshot, case pointer, run pointer, and audit event together.

### Publication

1. Report inputs append optimistic versions in one transaction.
2. Freeze verifies exact versions, snapshot, optional model identity, and export
   consent before committing the report and audit event.
3. Approval revalidates the frozen identity and commits approval plus audit.

### Browser authority

1. Route or user action dispatches an authority transition.
2. Effects start reads with the resulting generation and identities.
3. Responses dispatch guarded results.
4. Only matching results can change visible authority.

## Error Handling

- Preserve existing domain error strings and HTTP mappings.
- Map unique and optimistic-version conflicts to their existing stable errors.
- Database exceptions roll back the complete transition; callers do not restore
  dictionaries manually.
- Lost or expired leases are silent stale-worker exits and never write state.
- Response validation failures fail closed and are exercised in contract tests.
- Provider transport failures continue through `AGENT_PROVIDER_*`; malformed
  output continues through `AGENT_OUTPUT_INVALID`.
- Stale browser results are ignored, not rendered as user-visible errors.

## Testing

### Adapter contracts

Each ledger has one behavioral contract suite. It always runs against memory
adapters and runs against a fresh migrated PostgreSQL database when
`CAOS_TEST_DATABASE_URL` is available. Contract cases cover successful
transitions, rollback, optimistic conflicts, concurrent claims, fencing, and
cross-record invariants.

### HTTP contracts

Existing FastAPI tests remain. Add response-model and OpenAPI assertions for the
shared response families and exact compatibility assertions for representative
payloads.

### Provider

Replace module-global provider monkeypatches with injected fake-adapter cases.
Retain budget, retry, repair, timeout, evidence, malformed response, and fencing
coverage through the agent-loop interface.

### Frontend

Add reducer tests for route hydration, case changes, cross-case run rejection,
late responses, accepted snapshots, and invalidation. Retain the production
browser journey for URL writes, draft prompts, SSE/polling, accessibility, and
cross-case races.

### Final gates

- fresh PostgreSQL migration and adapter contract suite;
- complete server suite in the project virtual environment;
- frontend unit, lint, TypeScript, and production build checks;
- combined-app production inventory and accessibility checks when available;
- rewrite tournament on changed non-trivial functions;
- confidence review and confirmed-issue patches;
- GitNexus `detect_changes` against `origin/main` before commit.

## Implementation Order

1. Response models and centralized frontend transport types.
2. Provider port and injected fake adapters.
3. Public worker scheduling and pending-job reads.
4. Pure browser authority reducer.
5. Ledger interfaces and memory adapters.
6. Normalized PostgreSQL adapters and removal of the state envelope.
7. Replace implementation-coupled tests with ledger interface tests.
8. Run all verification and adversarial review gates.

Every slice must leave the repository green. The storage cutover lands only
after all callers use ledger interfaces, so no intermediate state mixes direct
bucket mutation with normalized database authority.

## Non-goals

- Legacy `caos_state` data migration or dual-read operation.
- Changed HTTP paths, JSON shapes, or product behavior.
- New queue, event bus, ORM, state library, or generated client dependency.
- Horizontal-scale redesign beyond the existing database claim and fencing
  model.
- UI redesign or mechanical file splitting.
- Vault garbage collection.
