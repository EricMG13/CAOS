---
title: Maintain issuer sources and refresh live metrics
contentType: Conceptual
status: Approved
date: 2026-08-19
---

# Maintain issuer sources and refresh live metrics

CAOS will use a persistent issuer registry for routine search, document maintenance, and metric refresh. Cases will remain frozen workspaces for governed analysis, recommendations, approvals, and reports.

## Content plan

- **Audience**: product, frontend, backend, data, and quality engineers implementing the issuer-first workflow
- **Goal**: define an implementation-ready contract for issuer search, staged source updates, explicit refresh, immediate metric publication, and case isolation
- **Scope**: issuer registry, source ownership, refresh execution, live metric snapshots, case creation, authorization, failure handling, migration, and verification
- **Open questions**: none

## Decisions

The approved product decisions are:

- The issuer registry is the routine entry point
- Analysts upload documents without creating a case
- Uploads stage a new source-set version and do not run analysis
- Analysts trigger metric refresh explicitly
- A successful refresh publishes immediately without analyst acceptance
- A failed refresh preserves the current live metrics
- Cases pin the issuer state at creation and never follow later issuer refreshes
- The metric catalog is a derived read model, not an independent authority

## Product boundary

The issuer owns reusable coverage data. A case owns a specific analytical decision process.

Issuer-owned records include:

- Stable issuer identity and search aliases
- Uploaded source documents
- Immutable issuer source sets
- The pointer to the current issuer source set
- Issuer metric refreshes
- Versioned metric snapshots
- The pointer to the live metric snapshot

Case-owned records include:

- The issuer, source set, and metric snapshot pinned when the case starts
- Workflow runs and artifacts
- Case-local notes and assumptions
- Thesis and recommendation versions
- Snapshot acceptance and switching
- Report approval and publication

Later issuer uploads or refreshes never change an existing case. A case must start a new case-owned run to use newer issuer material.

## Navigation and issuer workflow

The primary navigation replaces **Cases** with **Issuers**. The destination count remains eight. Existing cases appear within each issuer record.

The issuer workflow is:

1. Open **Issuers**
2. Search by legal name, display name, ticker, or alias
3. Select an issuer or create one when no match exists
4. Upload documents to the issuer Source Library
5. Review the pending source-set version
6. Click **Refresh metrics**
7. Continue using the previous metrics while the refresh runs
8. See the new metrics immediately after successful publication
9. Click **Start case** only when governed analysis is required

The issuer page contains four regions:

- **Identity**: legal name, display name, ticker, sector, aliases, and last refresh time
- **Live metrics**: current values, basis, period, quality status, source-set version, and change from the previous snapshot
- **Source Library**: active documents, withdrawn documents, upload action, and pending-refresh status
- **Cases**: existing cases plus **Start case**

The global context control distinguishes issuer context from case context. Issuer maintenance never shows an implied active case. Deep-Dive, Run Console, Model Builder, and Report Studio continue to require an active case.

## Issuer search and creation

Search returns at most 50 deployment-visible issuers and orders exact ticker, exact name, prefix, then substring matches. The first result page must not require a case join.

Creation accepts legal name, display name, ticker, sector, and aliases. The service normalizes ticker casing and search text before persistence.

The service rejects an exact ticker conflict. Name and alias similarity returns candidate matches but does not auto-merge records. Concurrent creates use an idempotency key and a database uniqueness constraint for normalized non-null ticker values.

Phase 1 does not include issuer merge. Existing data migration creates one issuer for each existing case, even when names look similar. This preserves case isolation and avoids an unsafe automatic consolidation.

## Source ownership and source sets

Immutable source records belong to the authenticated deployment. Source sets determine whether a source participates in an issuer or case context.

A source set has an owner type, owner identifier, version, ordered source identifiers, creator, creation time, and digest. The database enforces a unique owner and version pair.

Each issuer stores `current_source_set_id`. Upload and withdrawal transactions create the next immutable set and update this pointer together. The live metric snapshot retains its own source-set identifier, so the interface can detect pending source changes without inference.

Issuer uploads reuse the current controls for:

- Allowed file types and upload size
- Malware scanning
- Archive expansion and path validation
- Content hashing and deduplication
- Content-addressed vault storage
- Safe block extraction

An upload creates a new issuer source-set version. It sets the issuer state to **Pending refresh** but does not change the live metric snapshot.

Withdrawing a source creates another issuer source-set version. Sources remain immutable and recoverable through history. Phase 1 does not permanently delete source content.

Case creation copies the pinned issuer source identifiers into a new case-owned source set. It reuses the immutable source blobs without letting later issuer membership changes affect the case. Case-local analyst notes can enter later case-owned source sets but never enter the issuer library implicitly.

## Metric refresh execution

`POST /api/issuers/{issuer_id}/metric-refreshes` starts one refresh for the issuer's current source set. The request captures the source-set identifier, version, digest, methodology build, metric-catalog version, actor, and idempotency key.

The refresh uses the existing Screen-depth Full Credit route from the vendored Deploy V authority. It runs the route and quality gate against the pinned source set, then projects the approved headline metric catalog from typed artifacts.

Each refresh records exactly one of these states:

- `queued`
- `running`
- `succeeded`
- `failed`

Only one queued or running refresh may exist for an issuer. A repeated request with the same idempotency key returns the existing refresh. A second distinct request returns a conflict until the active refresh finishes.

Documents uploaded during a refresh create a newer pending source set. The running refresh remains pinned to its original set. If it succeeds, its metrics publish with their exact source-set version while the interface keeps the newer set marked **Pending refresh**.

## Metric snapshot contract

A successful refresh creates one immutable metric snapshot. The snapshot records:

- Issuer identifier
- Refresh and source-set identifiers
- Source-set version and digest
- Methodology build identifier
- Metric-catalog version
- Quality status
- Creation time and actor
- Prior live snapshot identifier

Each metric row records:

- Metric key and definition version
- Value or explicit unavailable status
- Unit, period, basis, and polarity
- Quality status and confidence
- Artifact and evidence references
- Formula or extraction rule identifier

The publisher never copies a missing value from an older snapshot. A missing metric remains unavailable in the new snapshot.

The live pointer changes only when the Full Credit Screen and its quality gate succeed. The database inserts the complete snapshot and updates the issuer's live pointer in one transaction. Any failure rolls back the transaction and preserves the previous pointer.

Immediate publication means no analyst acceptance step. It does not bypass methodology validation, quality gates, finite-number checks, or evidence requirements.

## Case creation and isolation

**Start case** creates a case with these immutable starting references:

- `issuer_id`
- `issuer_source_set_id`
- `issuer_metric_snapshot_id`, when available

The case also creates its first case-owned source set from the pinned issuer source identifiers. Existing case workflows continue to use case-owned source sets and accepted snapshots.

A case may start before an issuer has live metrics. In that state, the metric snapshot reference is null and the case displays **No issuer metric snapshot pinned**. It never substitutes future live metrics silently.

## Authorization and audit

CAOS is self-hosted as one authenticated deployment. Issuer visibility is deployment-wide rather than public or cross-deployment.

Authorization rules are:

- `READER` can search issuers and read issuer metrics and source metadata
- `ANALYST`, `APPROVER`, and `ADMIN` can create issuers, upload or withdraw sources, and start refreshes
- Existing case membership controls every case read and write
- Starting a case adds the creator as its analyst member

Every issuer route requires trusted identity. Direct source access must first prove that the source belongs to an issuer source set visible to the caller or a case source set authorized by case membership. Raw vault paths never enter API responses.

Audit events cover issuer creation, source upload, source withdrawal, refresh start, refresh success or failure, live pointer publication, and case creation from an issuer snapshot.

## API contract

Phase 1 adds these issuer routes:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/issuers?query=` | Search deployment-visible issuers |
| `POST` | `/api/issuers` | Create an issuer |
| `GET` | `/api/issuers/{issuer_id}` | Read issuer identity and live status |
| `GET` | `/api/issuers/{issuer_id}/sources` | List issuer source history |
| `POST` | `/api/issuers/{issuer_id}/sources` | Upload and stage a source |
| `POST` | `/api/issuers/{issuer_id}/sources/{source_id}/withdraw` | Withdraw a source and create a source-set version |
| `GET` | `/api/issuers/{issuer_id}/metrics` | Read the live metric snapshot and prior-snapshot changes |
| `POST` | `/api/issuers/{issuer_id}/metric-refreshes` | Start an explicit refresh |
| `GET` | `/api/metric-refreshes/{refresh_id}` | Read refresh state and failure details |
| `POST` | `/api/issuers/{issuer_id}/cases` | Start a pinned case |

Existing case endpoints remain authoritative for case-owned analysis. During migration, `POST /api/cases` becomes a compatibility alias that requires `issuer_id` and delegates to the nested issuer route. It no longer creates issuer identity from free-text case fields. No new issuer workflow should call a case upload endpoint.

## Failure behavior

Failure states preserve the last valid view:

- Upload rejection creates no source or source set
- Refresh validation failure creates no live metric snapshot
- Worker failure leaves the previous live pointer unchanged
- Publication transaction failure leaves no partial metric snapshot
- Duplicate create returns the existing conflict candidate without merging
- Unauthorized issuer or source identifiers return a masked not-found response where required to prevent enumeration

The interface shows a concise failure reason and a retry action. It never clears live metrics while a refresh is queued, running, or failed.

## Migration and compatibility

The migration proceeds without merging existing records:

1. Create one issuer for each existing case
2. Associate each case with its new issuer
3. Preserve each case's current source set and accepted snapshots
4. Seed the issuer Source Library from that case's current governed documents
5. Leave the issuer metric pointer empty until the first explicit refresh
6. Redirect the current **Cases** landing route to **Issuers** while retaining compatibility links for existing case URLs

The migration must be restart-safe. It records the source case on each backfilled issuer so a retry cannot create another issuer.

## Verification plan

Server verification covers:

- Exact, prefix, substring, alias, and ticker search
- Duplicate and concurrent issuer creation
- Role-gated issuer mutations and masked direct-object access
- Upload validation, malware rejection, deduplication, and withdrawal
- Source-set versioning and digest stability
- One active refresh per issuer and idempotent retry
- Upload during refresh
- Successful atomic publication
- Failed refresh and failed publication preserving the prior pointer
- Missing metrics remaining unavailable without stale-value carry-forward
- Case creation with and without a live metric snapshot
- Case source and metric isolation after later issuer refreshes
- Restart-safe existing-case backfill

Frontend verification covers:

- Keyboard-operable issuer search, creation, upload, refresh, and case start
- Visible loading, running, pending, failed, and live states
- Source-set version and last-refresh disclosure
- Metric changes and unavailable values without color-only meaning
- Search and issuer detail accessibility through the local axe-core runner
- Existing case workflow regressions

## Release gates

The issuer-first workflow cannot ship until these conditions pass:

- Atomic publication is proven against PostgreSQL
- No issuer or source direct-object authorization defect remains
- Existing case snapshots remain unchanged after issuer refreshes
- The live metric view contains no seeded or manually edited values
- Every metric has a versioned definition and evidence path
- Failed refreshes preserve the previous live snapshot
- The rendered issuer workflow passes keyboard and WCAG 2.1 AA checks

## Out of scope

Phase 1 excludes:

- Automatic refresh after upload
- Analyst acceptance before metric publication
- Hidden rolling cases
- Manual metric editing
- Issuer merge
- Cross-issuer natural-language query
- Portfolio-wide dictionary screens beyond the live issuer metric read model
- Permanent source deletion
- Automatic propagation from issuer refreshes into existing cases
