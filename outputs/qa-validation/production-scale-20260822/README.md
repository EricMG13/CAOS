# CAOS production-scale local validation dataset

Generated 2026-08-22. This fixture is entirely synthetic. It contains no
production credentials, customer data, copied filings, or other sensitive
material.

## Reusable fixture

- PostgreSQL custom dump: `caos-production-scale.dump`
- SHA-256: `954bbd96bc43d45c36d6d46ca0ca09eda77771bc21ffd5064e6c631922eb43bd`
- Sanitized source vault: `vault/`
- Machine-readable final inventory: `inventory-final.json`
- Database revision: 2174
- Restore proof: a fresh database restored successfully with 234 cases, 153
  sources, and 832 audit events.
- Production-like runtime used PostgreSQL 17, a separate leased/fenced worker,
  ClamAV, trusted-edge identity headers, production configuration validation,
  and the static production frontend build.

Restore into an empty local database with `pg_restore -d <database>
caos-production-scale.dump`. Supply new local-only secrets through the normal
environment variables; no secret is embedded in this fixture. Source records
use the absolute vault prefix from this checkout. A restore under another root
must deliberately rewrite that synthetic prefix and repeat the vault
existence/hash check; this fixture does not claim cross-host portability.

The principal dense case is `case_d5e3151a64554296` (`Synthetic Dense
Issuer`):

- 130 immutable sources across TXT (64), Markdown (34), CSV (22), and JSON
  (10); active source-set version 130
- all six pathways have a repaired run that executed, succeeded, produced an
  artifact for every durable node (44/44), and was explicitly accepted: Full
  Credit, Earnings Update, Covenant & Refinancing, Relative Value, Distressed
  & Restructuring, and Deep Research
- 12 accepted snapshots: six repaired, populated authorities and six older
  empty-artifact snapshots deliberately retained as regression evidence for
  F-07; the visible and latest authorities are repaired
- 300 RV observations (250 eligible, 50 excluded)
- 60 notes, including 10 promoted notes; 60 assumptions
- 40 instrument recommendations in one governed version
- an Approver-ratified report with Markdown, PDF, and XLSX exports

Global fixture counts at the frozen dump boundary: 234 cases, 153 sources, 43
runs, 212 nodes, 160 artifacts, 35 snapshots, 43 job records, 43 event streams,
6 reports, and 832 audit events. The vault has 143 source references backed by
124 content-addressed files; all referenced files exist and all SHA-256 values
match. Repeated content is stored once.

## Acceptance inventory

Every visible element was inventoried for the analyst and PM/QA identities.
Every distinct control behavior was exercised; repeated row controls use the
same implementation and were covered as an equivalence class. The final dense
pass covered 16 route/role combinations with no alert, stuck loader, or page
overflow.

| Destination | Distinct controls and workflows exercised | Loading, empty, error, and governed states | Acceptance criterion | Finite risk edge |
| --- | --- | --- | --- | --- |
| Cases | Create case; select/switch case; file intake | Loading register; no-case and no-source boundaries; create/upload pending; accepted/not-accepted status | Case context changes atomically, source intake creates an immutable set, and stale authority cannot survive a case switch | More than 200 repeated Select buttons are rendered without pagination; introduce paging/virtualization before substantially exceeding 500 visible cases |
| Sources | Expand source; upload; evidence chip preview/open; clear selection; open full source | Loading/empty; malformed-JSON failure and reload recovery; missing evidence; active linked evidence | 130-source set loads without overflow, evidence remains case-bound, and recovery does not open a stale drawer | Each source exposes only its first 20 blocks in the UI and all 130 source summaries remain in the DOM; paginate before materially larger sets |
| Run Console | Six-purpose selector; screen/full depth; compile; accept | No-run; source-empty paused; running DAG; succeeded; failed authority; stale/cross-case run rejection | A worker can claim only after every node is durable, and acceptance pins the exact source set and artifacts | One worker and one API process were tested; multi-API-writer horizontal scale remains outside this local gate |
| Deep-Dive | Artifact evidence links; explicit visible-snapshot switch | No accepted snapshot; loading/error; current snapshot; newer accepted snapshot warning | The visible snapshot stays pinned until the user switches it, then matches the latest accepted authority | Concurrent switch-to-a-newer-than-rendered snapshot is protected by server authority but was not stressed with multiple simultaneous analysts |
| RV Screener | Ten row fields; native dates/numbers; add row; remove row; version universe; excluded-row disclosure | Loading/empty/error; eligible and excluded rows; pending version | Currency normalizes, incomplete/non-comparable rows are excluded, and system signal never writes the analyst recommendation | 300 rows are evaluated server-side and the current UI is not virtualized; reassess beyond roughly 1,000 observations |
| Command Center | Read-only issuer lens and change posture | Loading/error; no snapshot; no change; source/artifact change | PM/QA sees only accepted authority and an exact snapshot diff, never a system-authored recommendation | It is a summary surface; detailed evidence remains one link away in Deep-Dive/Sources rather than inline |
| Model Builder | Read-only authority gate | Loading/error; explicit official-model blocked state | The product refuses to fabricate CP-MODEL and explains the signed-authority dependency | This remains intentionally blocked until corrected signed Deploy V authority exists |
| Report Studio | Thesis, instrument, recommendation, evidence refs; freeze; Approver ratification; Markdown/PDF/XLSX exports | Loading/empty/error; dirty draft; pending approval; approved | Thesis and recommendations version together, freeze pins exact inputs/snapshot, only an Approver/Admin ratifies, and all exports match the approved record | Local exports validate contract and readability, not downstream portfolio-system ingestion or printer fidelity |

Global shell coverage included all workflow and tool navigation, the case
selector, source-authority drawer, QA details dialog, command palette commands,
keyboard escape/focus return, a true unknown-route 404, 720 px reflow, and
`prefers-reduced-motion`.

## Role and security checks

| Check | Result |
| --- | --- |
| Request without trusted-edge proof | 401 |
| Analyst trusted-edge identity | ANALYST |
| PM/QA trusted-edge identity | APPROVER |
| Admin trusted-edge identity | ADMIN |
| Reader trusted-edge identity | READER |
| Reader reads an assigned case / starts a run | 200 / 403, expected |
| Analyst self-appoints an Approver | 403, expected |
| Admin adds case Approver membership | 201 |
| PM/QA ratifies exact pending report preview | Passed |
| Cross-case forged identity/read | Rejected |
| Admin methodology mutation without step-up | Rejected by the existing contract tests |

## Failures, root causes, and regressions

| ID | Observed failure | Root cause | Smallest durable fix | Regression evidence |
| --- | --- | --- | --- | --- |
| F-01 | PM production smoke completed a run with no CP-0 artifact while nodes remained pending | The run became `queued` before its node IDs and node records were durable, so the separate worker claimed an empty DAG | Create runs as `planning`; publish `queued` only after every node is persisted | Queue-boundary unit regression; analyst and PM production smoke both pass |
| F-02 | Governance state could persist without its audit event, or vice versa | Several methodology and analyst-content paths persisted between related mutations | Mutate state and audit under one lock, persist once, and roll back exact prior values | Atomicity/failure regressions for methodology, thesis, recommendations, report inputs, notes, promotion, and assumptions |
| F-03 | A promoted note could be treated as active after its derived source was missing/withdrawn; a local variable shadowed the new source | Idempotency checked only the note flag and the comprehension reused the source name | Require an active derived source before returning idempotently and keep source identities distinct | Missing-source and withdrawn-source re-promotion regression |
| F-04 | A production-only failed PostgreSQL commit could leave in-memory state rebound to an uncommitted merge | The store adopted merged state and revision before `commit()` | Return the pending merge from the SQL step and adopt it only after commit; restore database-authoritative state on ordinary or fenced failure | Revision-merge plus ordinary/fenced commit-failure regression |
| F-05 | Dense reads deep-copied the complete state envelope on every request | `refresh()` restored and snapshotted even when the database revision had not changed | Skip restore/snapshot when the revision is unchanged | Unit regression plus repeated staged load |
| F-06 | Approved report status failed paper contrast at 2.09:1 | Dark-workspace success green was reused on the light report surface | Add paper-specific success/warning/critical semantic colors | 54 final route/viewport/role axe combinations, zero violations |
| F-07 | The first dense fixture claimed six accepted pathways, but all six pre-fix runs had pending nodes and empty accepted snapshots | The fixture had been created before the F-01 queue-publication repair, and the earlier acceptance check asserted pathway/status presence without asserting durable node artifacts | Re-execute and accept all six pathways under the fixed worker, switch visible authority to the repaired snapshot, and require every accepted pathway run to have succeeded nodes with artifact IDs | Two clean full-inventory passes; repaired runs contain 44/44 node artifacts while the older snapshots remain labeled regression evidence |

Validation-harness false starts were also retained in the log: source upload
was successful while a probe waited for copy that the page does not render;
the oracle was corrected to the case/source authority. A snapshot-switch setup
accepted the wrong overlapping run; the rerun created, awaited, accepted, and
asserted a separate run before touching the switch. Neither was classified as
a product defect. A loading probe initially closed its page before delayed
interceptors had resumed, producing a `Route is already handled` teardown race;
the harness now releases the barrier and waits for network idle before unroute.
The analyst's 403 on adding an Approver was an expected RBAC boundary, and setup
was completed through an admin identity.

## Final proof

- Server: 73 passed; one upstream Starlette/httpx deprecation warning
- Frontend: ESLint passed; Next.js production build and TypeScript passed;
  deployed static files exactly match that build
- Analyst production smoke: passed; DCL 16.2 ms, FCP 76 ms
- PM/QA production smoke: passed; DCL 21.6 ms, FCP 80 ms
- Accessibility: 9 routes x 3 viewports x 2 roles = 54 combinations, zero axe
  violations
- Route/role inventory: 8 destinations x 2 roles = 16 combinations, zero
  alerts, stuck loaders, or horizontal overflow
- Controlled state inventory: 16 loading, 16 error, and 14 empty-state probes;
  zero failures (Model Builder's governed blocked state replaces an empty state)
- Load gate: 120/120 successful requests across staged 1/4/12/24-reader runs.
  Warm p50/p95 was 38.2/45.6 ms at one reader, 147.6/149.8 ms at four,
  448.5/704.7 ms at twelve, and 1,079.9/1,172.8 ms at twenty-four; post-load
  recovery was 42.6 ms
- Export proof: Markdown 624 bytes, PDF 742 bytes, XLSX 5,042 bytes
- Dump restore: revision and every state cardinality matched; the temporary
  verification database was removed
- Secret scan: complete fixture scanned, zero leaks

## Explicit external gates

The local product pass is clean within the stated scale and topology. Three
external gates remain and are not represented as locally verified:

1. a real identity-provider redirect, MFA, and oauth2-proxy step-up exchange;
2. signed corrected Deploy V authority required to enable official Model
   Builder output;
3. multiple concurrent API writer processes and production traffic/latency
   beyond the tested 24-reader burst.

Keep the current single-API-process topology until the state envelope is
normalized or multi-writer CAS is added and stress-tested.
