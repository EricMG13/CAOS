# CAOS production-scale local validation dataset — 2026-08-24

## Outcome

**PASS.** This bundle is the sanitized database and source vault frozen after
the current production-image rerun. It contains only fabricated issuers,
documents, users under `.invalid`, workflows, and market observations. No
production endpoint, identity provider, credential, customer record, copied
filing, or external storage was used.

The machine-readable browser result is `inventory-final.json`. The older QA
workbook under `../01a019bd-f840-7833-92e0-eab62b3b4b80/` remains historical
evidence; the current acceptance inventory below supersedes its former manual
RV and blocked Model Builder rows.

## Reusable fixture

- PostgreSQL 17 custom dump: `caos-production-scale.dump`
- SHA-256:
  `1671f2f92693fef625d70d4841a8531342c401b75d045ad026285250622dc37a`
- Sanitized content-addressed source vault: `vault/`
- State revision: 2627
- Schema migrations: `001_baseline` through `005_runs_planning_status`
- State cardinality: 248 cases, 171 sources, 56 runs, 264 workflow nodes,
  212 artifacts, 47 snapshots, 56 jobs, 56 event streams, 10 reports, and 926
  audit events
- RV workbook state: 4 immutable loan-universe versions and 8 imported loan
  rows in addition to the 300-observation dense comparison universe
- Vault integrity: 161 file-backed source references resolve to 125 unique
  files; all SHA-256 values match. Ten derived-note sources are deliberately
  inline and have no vault path.
- Restore proof: an empty database restored to revision 2627 with all 248
  cases, 171 sources, 926 audit events, and migrations 001–005 present. The
  temporary restore database was removed.
- Secret scan: Gitleaks scanned the complete bundle and found zero leaks.

Restore into an empty local database with:

```sh
pg_restore -d <database> caos-production-scale.dump
```

Mount the included `vault/` directory at `/vault` and supply fresh local-only
runtime secrets. The dump contains `/vault/...` paths and no embedded secret.

The dense read/load case is `case_d5e3151a64554296` (`Synthetic Dense
Issuer`): 130 immutable sources; all six accepted pathways; 44/44 durable,
artifact-bound workflow nodes; 250 eligible and 50 explicitly excluded RV
observations; and an approved report. The final analyst-to-PM/QA journey is
`case_e25fcfe0b46e4819`.

## Production-like boundary

- Isolated Docker network and named local volumes only.
- Current app image in `ENVIRONMENT=production`, static Next.js production
  export served by FastAPI, and a separate worker process.
- PostgreSQL 17 and ClamAV 1.4; read-only app/worker root filesystems,
  `no-new-privileges`, and all Linux capabilities dropped.
- API bound only to `127.0.0.1`; trusted-edge headers used fabricated analyst,
  approver, admin, and reader identities.
- External canonical/deep-research agents disabled; no API key supplied.

## Acceptance method

Every distinct control behavior was exercised. Repeated case-selection and
source-disclosure controls use the same component and were treated as finite
equivalence classes: the dense render still inventoried every resulting DOM
control (up to 247 on one route) and asserted no alert, stuck loader, or page
overflow. Controlled loading and HTTP 503 responses were injected at each
route's primary data boundary, and an empty synthetic case exercised every
empty/governed-not-ready state.

### Global shell, routes, roles, and modals

| Surface | Inventory and acceptance | Finite risk edge |
|---|---|---|
| Routes | `/`, the eight destinations below, auxiliary `/admin-studio/`, and a true unknown-route 404. Current route, case, run, question, source, and artifact query authority must survive client navigation. | Only registered static destinations are valid; an arbitrary missing path must render “Page not found,” never Cases. |
| Workflow/tool navigation | Desktop workflow rail, tool rail, active-route state, case selector, accepted-authority strip, source count, QA trigger, and narrow command-palette substitutes. | At 375 px, Cases and the selected Run must remain reachable without a full-document fallback. |
| Command palette dialog | Open by button and Cmd/Ctrl+K; search authorized cases, workflows, tool routes, source IDs, and artifact IDs; arrow/selection route correctly; Escape closes and returns focus. | Unauthorized case search returns “No authorized matches”; same-route evidence navigation must not reopen a dismissed drawer. |
| Source details dialog | Loading, resolved, unavailable, and no-stale-data states; Escape close; case reselection and case switch behavior. | A late response from the prior case must not overwrite the new case authority. |
| Evidence dialog | Hover/focus-linked chips, source/block detail, Open full source, direct source/artifact query hydration, close and focus behavior. | Cross-case or missing evidence IDs never open a drawer and never leak another case's source metadata. |
| QA details dialog | Available/unavailable snapshot summary, Escape close, focus return. | Absence of governed snapshot QA is explicit, not represented as zero or a fabricated pass. |
| Native confirmations | Accept analytical snapshot and unsaved Report Studio draft navigation; cancel remains retryable. | A delayed acceptance completing after a case switch must not refresh the newly selected case with stale authority. |
| Roles | `ANALYST`, `APPROVER`, `ADMIN`, `READER`; analyst and approver/PM were exercised through all eight routes. Reader read/write and analyst privilege-escalation boundaries were exercised through the API. | Assigned Reader read = 200 and run creation = 403; Analyst cannot appoint Approver; Admin membership mutation succeeds; only Approver/Admin ratifies a report. |
| Responsive/accessibility | 1440×1000, 1024×768, 720×900, 390×844, and touch 375×812; visible focus, keyboard dialogs/tabs/grids, scroll regions, and reduced motion. | No page-level horizontal overflow; reduced-motion live pulse is paused and finite; meaning is not color-only. |

### Destination inventory

| Destination | Routes, controls, and workflows | States exercised | Acceptance criterion | Finite risk-based edge |
|---|---|---|---|---|
| Cases | `/cases/`; create name/issuer/sector; select/switch any case; upload supported source; open source register; inline purpose/depth compile; watch DAG; accept snapshot. | Loading and 503 case register; zero cases; no current run; upload/compile/accept pending; paused, failed, succeeded, accepted. | Case context changes atomically, uploads create an immutable source-set version, and an accepted run pins its exact artifacts/source authority. | 248 cases produced 245 analyst and 247 approver controls without overflow. Add pagination/virtualization before materially exceeding 500 visible cases. |
| Sources | `/sources/`; 130 disclosure controls on the dense case; first-20 extracted blocks per source; evidence preview/open; selection clear; direct source/artifact focus; safe file intake. | Loading, empty, 503, malformed response recovery, missing/cross-case evidence, active linked evidence. | Only the active case's immutable sources and artifacts render; errors replace stale authority; upload passes scanner and content-address hash checks. | The UI intentionally renders every source summary and only the first 20 blocks. Paginate source summaries before materially larger sets. |
| Run Console | `/run-console/`; six pathway options; Screen/Full depth; bounded Deep Research brief; compile; persisted DAG; research-plan review/hash approval; accept snapshot. | No run; planning/queued/running; source-empty pause; plan-approval pause; succeeded; failed; stale run/case race; disabled Deep Research deployment. | A run is invisible to the worker until every node is durable; approval binds the exact plan hash; acceptance requires a completed case-bound run and explicit confirmation. | One API writer and one leased/fenced worker were tested. Multiple API writers remain an external scale gate. Brief bounds are 400 characters per main field, 10 combined list items, 200 characters per list item. |
| Deep-Dive | `/deep-dive/`; accepted artifacts/evidence links; question context; explicit visible-snapshot switch; inline compile/accept and Run Console link. | Loading, empty, 503, current snapshot, newer accepted snapshot warning, switched authority. | The visible snapshot remains pinned until explicit switch and every conclusion stays linked to case-bound source evidence. | A case switch during a delayed acceptance/snapshot response must discard the stale completion. Concurrent multi-analyst switching is server-authoritative but not locally load-stressed. |
| RV Screener | `/rv-screener/`; fixed CP-3 XLSX upload; search; sector/rating/ranking/loan-type filters; maturity range; margin and 3Y DM ranges; sortable columns; paging; finding disclosure. | Loading, empty, 503, scanning/validation pending, accepted workbook, structured validation findings, eligible/excluded observations. | Import is source-bound and immutable; required headers and row types are validated; active version changes only after a valid import; filter/sort results match numeric/date semantics. | Production journey imported 2 instruments and filtered FinThrive; dense comparison covers 250 eligible/50 excluded. Reassess server paging beyond roughly 1,000 active rows. |
| Command Center | `/command-center/`; read-only issuer lens, accepted authority, source count/QA dialogs, “what changed” list, question context. | Loading, empty, 503, no change, source/artifact change, no accepted snapshot. | PM/QA sees accepted authority and exact snapshot deltas only; no system-authored recommendation appears. | It is deliberately a summary: evidence remains one interaction away in Deep-Dive/Sources rather than being duplicated. |
| Model Builder | `/model-builder/`; readiness gate; build/retry; refresh; immutable build history; worksheet tabs; arrow/Home/End keyboard navigation; cell formula/source lineage; export/retry/download XLSX; Reader read-only state. | Loading, 503, accepted-Full-Credit missing, canonical-input invalid, ready-to-build, queued, building, ready, calculation failed, export queued/exporting/ready/failed. | Only canonical QA-passed accepted Full Credit handoffs can build; polling never overlaps or continues after terminal state; worksheet/build identity digests match; output is read-only and one click from lineage. | Browser state matrix uses deterministic network fixtures; the real production-image model engine, LibreOffice recalculation, 338 formulas, 20 semantic checks, and XLSX round-trip are independently covered in `../cp-model-20260824/README.md`. No live market-data model is claimed. |
| Report Studio | `/report-studio/`; thesis, instrument, recommendation, evidence search/toggles and ID entry; optional explicit ready-model/export consent; freeze; approver ratification; Markdown/PDF/XLSX download and filed proof. | Loading, empty, 503, evidence sub-load failure, dirty local draft, missing accepted snapshot, evidence mismatch/withdrawal, pending approval, approved, model replacement race. | Thesis/recommendation version together; freeze pins exact snapshot/evidence/model inputs; consent never transfers to a replacement model; only Approver/Admin ratifies the exact preview/fingerprint; all exports match the approved record. | Browser exports were 681-byte MD, 742-byte PDF, and 5,017-byte XLSX. Local checks cover contract/readability, not downstream portfolio ingestion or physical-printer fidelity. |

## Reproducible failures grouped by root cause

Prior F-01 through F-11 and their regressions are retained in the 2026-08-22
fixture README and 2026-08-23 rerun. This rerun reproduced and closed two new
root causes:

| ID | Reproduction | Root cause | Smallest coherent fix | Regression evidence |
|---|---|---|---|---|
| F-12 | Restore a database whose `schema_migrations` already contains `001_baseline` and whose `runs_status_check` predates `planning`; start a run. Persistence reaches normalized `runs` and returns HTTP 500. | The baseline SQL had gained `planning`, but an applied baseline never reruns. Existing databases therefore retained the legacy status constraint. | Add forward-only migration `005_runs_planning_status.sql`; inspect the live constraint, replace it only when `planning` is absent, then record 005. | PostgreSQL regression installs the legacy constraint, runs the real migration runner, and asserts only 005 applied and the resulting definition includes `planning`; full suite 354/354. |
| F-13 | Intercept `GET /api/cases/:id/reports` with 503 and open Report Studio as analyst or approver. The editor/paper remained visible instead of the route-level error state. | `ReportView` used one `error` value for both initial-load and mutation failures, while its render boundary depended only on `loading`; a completed failed load therefore selected the normal form branch. | Keep action errors in `error`, add route-load `loadError`, and use it in both editor and paper load boundaries. | Exact controlled error probes now pass for Report Studio under both roles; all 16 error, 16 loading, and 16 empty/governed-state probes pass. |

## Final proof

| Gate | Result |
|---|---|
| Production inventory | 16/16 loaded role/destination combinations; zero alerts, stuck loaders, overflow, or failures |
| Controlled states | 16 loading + 16 error + 16 empty/governed-not-ready = 48/48 passed |
| Workflow journey | Case/source intake; Earnings and RV runs; acceptance/snapshot switch; CP-3 workbook import/filter/sort; report freeze, PM/QA approval, and MD/PDF/XLSX exports passed |
| Authorization | Four roles resolved; Reader write and Analyst escalation rejected; Admin membership and Approver ratification passed |
| Extended browser smoke | Passed; DCL 19.2 ms, FCP 76 ms; dialogs, races, keyboard, 375/390/720 px, Model Builder state matrix, and reduced motion passed |
| Accessibility | 9 routes × 3 viewports plus pending-plan and ready-model fixtures = 29 combinations; zero axe violations |
| Load/recovery | 120/120 requests passed across 1/4/12/24 readers; p95 36.5/123.9/626.0/901.8 ms; post-load recovery 30.5 ms |
| Server | 354/354 tests passed against a fresh isolated PostgreSQL database |
| Frontend | ESLint, 8 unit tests, `tsc --noEmit`, and Next.js production build passed |
| Image authority | 307 vendored methodology files checked; zero mismatches |
| Dump/vault | Fresh restore matched revision/cardinality; 161/161 file-backed hashes passed; Gitleaks zero findings |

## Confidence review — final dataset and fixes

Least confident about (ranked):

1. The legacy constraint repair might differ under combined `ALTER TABLE`.
   Investigation found no DDL event triggers, and PostgreSQL 17 validated the
   replacement transactionally. Verdict: fixed and verified by the focused
   2/2 migration test plus the fresh-database 354/354 suite.
2. Separating Report Studio load errors might hide freeze/approval recovery.
   The load boundary now uses only `loadError`; action failures remain in the
   rendered form's `error`. Verdict: fixed and verified by both-role 503 probes
   plus missing-snapshot/evidence/action browser paths.
3. The restored JSON envelope and normalized tables might have drifted.
   All 56 runs match normalized status, all 4 loan universes and 8 rows match,
   and run/source foreign-key orphan counts are zero. The smaller normalized
   case/source populations are by design because those tables mirror only run
   and loan-universe query authority.
4. Model Builder browser fixtures might overstate real engine coverage.
   Browser fixtures cover UI concurrency and terminal states only; the real
   worker image independently recalculated 338 formulas, passed 20 semantic
   checks, and the real backend paths are in the 354-test PostgreSQL suite.
5. The bundle might have been frozen before the definitive pass.
   Final images were rebuilt, the full inventory reran, then the dump/result
   manifest was frozen and restored. The later tournament-only consolidation
   of two equivalent DDL subcommands passed PostgreSQL proof and changes no
   application execution path.

Fixed: legacy-database run creation and Report Studio initial-load failure
rendering. Verified fine: normalized mirrors, report action recovery, model
engine/UI evidence boundary, dump restore, vault hashes, and secret scan.
By design: repeated row controls are equivalence classes and Model Builder UI
failure states use deterministic browser fixtures. Still open: only the named
external gates below.

## Explicit external gates

This clean local pass does not claim a real OIDC redirect/MFA/step-up exchange,
external deep-research/provider behavior, production market/source licensing, or
horizontal multi-API-writer traffic. Those require separate non-local authority
and are intentionally excluded from this sanitized dataset.
