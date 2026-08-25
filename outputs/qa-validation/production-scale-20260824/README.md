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
  `45186eb565c305c1f96a79b8c881f11254b2e3f4efb1e265d2c830233d583bc1`
- Sanitized content-addressed source vault: `vault/`
- State revision: 2846
- Schema migrations: `001_baseline` through `005_runs_planning_status`
- State cardinality: 254 cases, 180 sources, 62 runs, 288 workflow nodes,
  236 artifacts, 53 snapshots, 62 jobs, 62 event streams, 13 reports, and 980
  audit events
- RV workbook state: 7 immutable loan-universe versions and 761 imported loan
  rows, including the 300-observation dense comparison universe
- Vault integrity: 170 file-backed source references resolve to 126 unique
  files; all SHA-256 values match. Ten derived-note sources are deliberately
  inline and have no vault path.
- Restore proof: an empty database restored to revision 2846 with all 254
  cases, 180 sources, 980 audit events, 761 RV rows, and migrations 001–005 present. The
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
`case_1f7bc51464d84d89`.

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
control (up to 253 on one route) and asserted no alert, stuck loader, or page
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
| Cases | `/cases/`; create name/issuer/sector; select/switch any case; upload supported source; open source register; inline purpose/depth compile; watch DAG; accept snapshot. | Loading and 503 case register; zero cases; no current run; upload/compile/accept pending; paused, failed, succeeded, accepted. | Case context changes atomically, uploads create an immutable source-set version, and an accepted run pins its exact artifacts/source authority. | 254 cases produced 251 analyst and 253 approver controls without overflow. Add pagination/virtualization before materially exceeding 500 visible cases. |
| Sources | `/sources/`; 130 disclosure controls on the dense case; first-20 extracted blocks per source; evidence preview/open; selection clear; direct source/artifact focus; safe file intake. | Loading, empty, 503, malformed response recovery, missing/cross-case evidence, active linked evidence. | Only the active case's immutable sources and artifacts render; errors replace stale authority; upload passes scanner and content-address hash checks. | The UI intentionally renders every source summary and only the first 20 blocks. Paginate source summaries before materially larger sets. |
| Run Console | `/run-console/`; six pathway options; Screen/Full depth; bounded Deep Research brief; compile; persisted DAG; research-plan review/hash approval; accept snapshot. | No run; planning/queued/running; source-empty pause; plan-approval pause; succeeded; failed; stale run/case race; disabled Deep Research deployment. | A run is invisible to the worker until every node is durable; approval binds the exact plan hash; acceptance requires a completed case-bound run and explicit confirmation. | One API writer and one leased/fenced worker were tested. Multiple API writers remain an external scale gate. Brief bounds are 400 characters per main field, 10 combined list items, 200 characters per list item. |
| Deep-Dive | `/deep-dive/`; accepted artifacts/evidence links; question context; explicit visible-snapshot switch; inline compile/accept and Run Console link. | Loading, empty, 503, current snapshot, newer accepted snapshot warning, switched authority. | The visible snapshot remains pinned until explicit switch and every conclusion stays linked to case-bound source evidence. | A case switch during a delayed acceptance/snapshot response must discard the stale completion. Concurrent multi-analyst switching is server-authoritative but not locally load-stressed. |
| RV Screener | `/rv-screener/`; fixed CP-3 XLSX upload; search; sector/rating/ranking/loan-type filters; maturity range; margin and 3Y DM ranges; sortable columns; paging; finding disclosure. | Loading, empty, 503, scanning/validation pending, accepted workbook, structured validation findings, eligible/excluded observations. | Import is source-bound and immutable; required headers and row types are validated; active version changes only after a valid import; filter/sort results match numeric/date semantics. | Production journey imported 251 instruments, proved the 250/1 page boundary, and filtered FinThrive back onto page 1; dense comparison covers 250 eligible/50 excluded. Reassess server paging beyond roughly 1,000 active rows. |
| Command Center | `/command-center/`; read-only issuer lens, accepted authority, source count/QA dialogs, “what changed” list, question context. | Loading, empty, 503, no change, source/artifact change, no accepted snapshot. | PM/QA sees accepted authority and exact snapshot deltas only; no system-authored recommendation appears. | It is deliberately a summary: evidence remains one interaction away in Deep-Dive/Sources rather than being duplicated. |
| Model Builder | `/model-builder/`; readiness gate; build/retry; refresh; immutable build history; worksheet tabs; arrow/Home/End keyboard navigation; cell formula/source lineage; export/retry/download XLSX; Reader read-only state. | Loading, 503, accepted-Full-Credit missing, canonical-input invalid, ready-to-build, queued, building, ready, calculation failed, export queued/exporting/ready/failed. | Only canonical QA-passed accepted Full Credit handoffs can build; polling never overlaps or continues after terminal state; worksheet/build identity digests match; output is read-only and one click from lineage. | Browser state matrix uses deterministic network fixtures; the real production-image model engine, LibreOffice recalculation, 338 formulas, 20 semantic checks, and XLSX round-trip are independently covered in `../cp-model-20260824/README.md`. No live market-data model is claimed. |
| Report Studio | `/report-studio/`; thesis, instrument, recommendation, evidence search/toggles and ID entry; optional explicit ready-model/export consent; freeze; approver ratification; Markdown/PDF/XLSX download and filed proof. | Loading, empty, 503, evidence sub-load failure, dirty local draft, missing accepted snapshot, evidence mismatch/withdrawal, pending approval, approved, model replacement race. | Thesis/recommendation version together; freeze pins exact snapshot/evidence/model inputs; consent never transfers to a replacement model; only Approver/Admin ratifies the exact preview/fingerprint; all exports match the approved record. | Browser exports were 681-byte MD, 742-byte PDF, and 5,017-byte XLSX. Local checks cover contract/readability, not downstream portfolio ingestion or physical-printer fidelity. |

## Reproducible failures grouped by root cause

Prior F-01 through F-11 and their regressions are retained in the 2026-08-22
fixture README and 2026-08-23 rerun. This rerun reproduced and closed five new
root causes:

| ID | Reproduction | Root cause | Smallest coherent fix | Regression evidence |
|---|---|---|---|---|
| F-12 | Restore a database whose `schema_migrations` already contains `001_baseline` and whose `runs_status_check` predates `planning`; start a run. Persistence reaches normalized `runs` and returns HTTP 500. | The baseline SQL had gained `planning`, but an applied baseline never reruns. Existing databases therefore retained the legacy status constraint. | Add forward-only migration `005_runs_planning_status.sql`; inspect the live constraint, replace it only when `planning` is absent, then record 005. | PostgreSQL regression installs the legacy constraint, runs the real migration runner, and asserts only 005 applied and the resulting definition includes `planning`; full suite 357/357. |
| F-13 | Intercept `GET /api/cases/:id/reports` with 503 and open Report Studio as analyst or approver. The editor/paper remained visible instead of the route-level error state. | `ReportView` used one `error` value for both initial-load and mutation failures, while its render boundary depended only on `loading`; a completed failed load therefore selected the normal form branch. | Keep action errors in `error`, add route-load `loadError`, and use it in both editor and paper load boundaries. | Exact controlled error probes now pass for Report Studio under both roles; all 16 error, 16 loading, and 16 empty/governed-state probes pass. |
| F-14 | Upload a source beyond an extraction cap, or an XLSX whose declared dimension hides a real row/column. The prior extractor accepted a truncated evidence set. | Worksheet/row/column/text limits stopped iteration or sliced content instead of rejecting, and read-only worksheet iteration trusted untrusted dimension metadata. | Reject every exceeded limit, reset worksheet dimensions before streaming actual cells, and retain stable 64-column block padding for valid workbooks. | Endpoint and direct regressions cover persistence rollback, sheets, rows, columns, aggregate text, long lines, exact limits, and lying row/column dimensions; focused suite 16/16. |
| F-15 | Put an identically named constraint on another table—or a wrong same-named FK on the target table—then run migration 004. | The migration originally looked up only `conname`, so unrelated or malformed constraints could satisfy the guard. | Match target/reference relations, exact source/destination key columns, FK type, and `ON DELETE RESTRICT`; unexpected same-target definitions fail loudly. | Real PostgreSQL regressions prove the decoy is ignored, the exact FK is installed, and a wrong target FK aborts; focused suite 4/4. |
| F-16 | Claim RV pagination coverage with the original two-row CP-3 browser fixture. | The browser journey exercised import/filter/sort but never crossed the 250-row page boundary. | Expand the deterministic workbook to 251 valid loans and assert both pages, terminal navigation, and filter reset. | Final production-image journey rendered 250 rows on page 1, one on page 2, then returned FinThrive to page 1; all inventory gates passed. |

## Final proof

| Gate | Result |
|---|---|
| Production inventory | 16/16 loaded role/destination combinations; zero alerts, stuck loaders, overflow, or failures |
| Controlled states | 16 loading + 16 error + 16 empty/governed-not-ready = 48/48 passed |
| Workflow journey | Case/source intake; Earnings and RV runs; acceptance/snapshot switch; 251-row CP-3 workbook import/filter/sort/paging; report freeze, PM/QA approval, and MD/PDF/XLSX exports passed |
| Authorization | Four roles resolved; Reader write and Analyst escalation rejected; Admin membership and Approver ratification passed |
| Extended browser smoke | Passed; DCL 19.2 ms, FCP 76 ms; dialogs, races, keyboard, 375/390/720 px, Model Builder state matrix, and reduced motion passed |
| Accessibility | 9 routes × 3 viewports plus pending-plan and ready-model fixtures = 29 combinations; zero axe violations |
| Load/recovery | 120/120 requests passed across 1/4/12/24 readers; p95 58.1/241.7/834.7/1,362.2 ms; post-load recovery 46.0 ms |
| Server | 357/357 tests passed against a fresh isolated PostgreSQL database |
| Frontend | ESLint, 8 unit tests, `tsc --noEmit`, and Next.js production build passed |
| Image authority | 307 vendored methodology files checked; zero mismatches |
| Dump/vault | Fresh restore matched revision/cardinality; 170/170 file-backed hashes passed; Gitleaks zero findings |

## Confidence review — final dataset and fixes

Least confident about (ranked):

1. Read-only XLSX dimensions might still hide evidence beyond the declared
   range. A malformed workbook reproduced the truncation; resetting dimensions
   exposed the real row/column stream, and regressions now cover both directions.
   Verdict: confirmed, fixed, and verified by the 16/16 focused suite.
2. Migration 004 might accept a same-named but semantically different FK.
   Exact relation checks alone were insufficient on an empty database; the
   predicate now binds both key columns and delete action. Verdict: confirmed,
   fixed, and verified by 4/4 real-PostgreSQL migration tests.
3. The paging claim might still rely on mocked or sub-threshold data. The final
   production-image journey uploaded a real 251-row XLSX through source intake
   and the RV importer, then asserted the 250/1 split and filter reset. Verdict:
   verified fine without request mocking.
4. The bundle might not match the definitive run. Final images were rebuilt,
   the full inventory reran, and only then were the result JSON, revision-2846
   dump, and 126-file vault frozen. A clean restore and all 170 hashes passed;
   Gitleaks found zero secrets. Verdict: verified fine.
5. Model Builder browser fixtures might overstate real engine coverage.
   Browser fixtures cover UI concurrency and terminal states only; the real
   worker image independently recalculated 338 formulas, passed 20 semantic
   checks, and the real backend paths are in the 357-test PostgreSQL suite.

Fixed: silent extraction truncation, malformed worksheet dimensions, ambiguous
FK detection, and missing production pagination coverage. Verified fine:
report action recovery, model engine/UI evidence boundary, dump restore, vault
hashes, and secret scan.
By design: repeated row controls are equivalence classes and Model Builder UI
failure states use deterministic browser fixtures. Still open: only the named
external gates below.

## Explicit external gates

This clean local pass does not claim a real OIDC redirect/MFA/step-up exchange,
external deep-research/provider behavior, production market/source licensing, or
horizontal multi-API-writer traffic. Those require separate non-local authority
and are intentionally excluded from this sanitized dataset.
