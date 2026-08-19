# Audit Log — front-end & system design

Read-only audit (no code changed). Each item is something I was *least confident
about* on first read; investigated to a definitive root cause with direct
evidence, then marked verified. Branch: `fix/vmo2-followups` (uncommitted WIP +
recent commits). Date: 2026-06-22.

Severity: 🟢 correct-as-designed · 🟡 real gap, bounded · 🔴 bug.

---

- [x] **1. `views.tsx` color swap `var(--tranche-sub)` → `var(--caos-consumer)` 🟢**
  Worry: a renamed CSS var that isn't defined → invalid color → element renders
  with inherited/transparent text (silent visual bug).
  Evidence: `--caos-consumer: #c4b5fd` is defined at
  [globals.css:18](caos/frontend/src/app/globals.css:18) and mirrored in
  [tailwind.config.js:15](caos/frontend/tailwind.config.js:15). The old
  `--tranche-sub` (#a855f7) still exists (globals.css:39) but is a *tranche
  seniority* hue; the new var is the *downstream-consumer* signal that pairs with
  `--caos-accent` (upstream lineage) in the Query-graph legend. The Inspector
  empty-state at [views.tsx:210](caos/frontend/src/components/pipeline/views.tsx:210)
  describes "downstream consumers," so this is a correct semantic fix, not a typo.
  **Root cause: intentional semantic-color correction; var is defined. Not a bug.**

- [x] **2. Deep-Dive `?issuer=` overlay — mislabeling risk 🟡(documented tradeoff)**
  Worry: opening a non-reference issuer keys the live overlay off an arbitrary id;
  bespoke tabs (debate/recovery/covenant) are ATLF fixtures — do they get rendered
  under the real issuer's name, passing ATLF analysis off as that issuer's?
  Evidence: [deepdive/page.tsx:67-86](caos/frontend/src/app/deepdive/page.tsx:67)
  derives `issuerId`, `isReference`, `code`, `dealLabel`; default tab is `CP-1`
  for non-reference vs `CP-6A` for reference (line 86). Panel content switch at
  [page.tsx:285-289](caos/frontend/src/app/deepdive/page.tsx:285) hardwires
  `CP-6A/CP-6E → DebateTab`, `CP-3B → RecoveryTab`, `CP-4 → CovenantsTab` — these
  take no issuer prop, so they always show ATLF fixtures. Mitigations present: a
  warning chip "live engine output · bespoke tabs show the ATLF reference
  template" ([page.tsx:160](caos/frontend/src/app/deepdive/page.tsx:160)), the
  per-module `● LIVE` badge only when `live.runId` exists (page.tsx:269), and the
  header shows the real `code`/`dealLabel`. Residual: a non-reference issuer with
  **no run** falls back to the seeded ATLF register inside `ModuleView` with no
  LIVE badge (absence-of-badge is the only signal). **Root cause: deliberate
  "reference-template" UX, explicitly flagged in-code; bespoke tabs are not
  issuer-parameterized by design. Low-severity transparency edge when no run
  exists. Not a logic bug.**

- [x] **3. `issuers/page.tsx` stretched-link row (WCAG nested-interactive fix) 🟢**
  Worry: replacing `role="button"` row with an absolute `<Link inset-0 z-0>` —
  does the Upload button still click, is the row keyboard-operable, does z-stacking
  actually work?
  Evidence: [issuers/page.tsx:209-242](caos/frontend/src/app/issuers/page.tsx:209).
  The `<Link className="absolute inset-0 z-0 focus-ring">` overlays the row as the
  single primary target; the Upload `<button>` is `relative z-[1]`, so a positioned
  z-1 sibling paints above the z-0 link and receives its own clicks (the former
  `e.stopPropagation()` is correctly dropped — they no longer nest). Two tab stops
  per row (link + button), neither nested → resolves the prior axe
  `nested-interactive` violation (old row was `role=button` *containing* a button).
  Cost: the z-0 link sits above static text spans, so row text isn't selectable —
  acceptable for a directory row. **Root cause: correct stretched-link pattern;
  stacking and the stopPropagation removal are right. Not a bug.**

- [x] **4. `issuers.py` slash-tolerant dual-registration `@router.get("")` 🟢**
  Worry: is the "`/api/{path:path}` catch-all shadows redirect_slashes" claim real,
  or is the extra route redundant?
  Evidence: routers are included at
  [main.py:163](caos/server/main.py:163) (issuers, prefix `/api/issuers`) *before*
  the catch-all at [main.py:178](caos/server/main.py:178)
  (`/api/{path:path}` over all methods → JSON 404). Starlette matches by
  registration order, not specificity. A request to `/api/issuers` (no slash, as
  `next dev`'s proxy rewrites it) would normally 307-redirect to `/api/issuers/`
  via `redirect_slashes` — but only when *no* route matches. The catch-all *does*
  match `/api/issuers` (`path="issuers"`), so the redirect never fires and the
  client gets a 404. Registering `@router.get("")`
  ([issuers.py:60](caos/server/routes/issuers.py:60)) → full path `/api/issuers`,
  matched before the catch-all → correct handler. **Root cause: catch-all 404 route
  intercepts the trailing-slash redirect; dual-registration is the right fix
  (QA BUG-001). Verified.**

- [x] **5. `GraphCanvas` keyboard handler `onActivate` swap 🟢**
  Worry: changing the inline `if (ev.key === "Enter")` to `onActivate(...)` on an
  SVG `<g role="button">` — does behavior regress?
  Evidence: [a11y.ts:7-14](caos/frontend/src/lib/a11y.ts:7) — `onActivate` fires on
  Enter **and Space**, calling `preventDefault()` (suppresses Space-page-scroll),
  matching native button semantics. The GraphCanvas node also gains
  `className="graph-node"` ([GraphCanvas.tsx:179](caos/frontend/src/components/query/GraphCanvas.tsx:179)),
  and the new `.graph-node:focus-visible` rule
  ([globals.css:110-114](caos/frontend/src/app/globals.css:110)) gives an outward
  outline because `.focus-ring`'s `-2px` inset outline doesn't render on a
  box-model-less SVG `<g>`. **Root cause: strict improvement — adds Space
  activation + visible SVG focus ring; consistent with other role=button rows.
  Not a bug.**

- [x] **6. `InProcessExecutor` stranded-run recovery on hard crash (SQLite) 🟡**
  Worry: a run left in `running` after an ungraceful process death — is there a
  startup sweep, or does it strand forever and the UI poll hang?
  Evidence: graceful shutdown is covered —
  [run_executor.py:39-46](caos/server/run_executor.py:39) catches
  `CancelledError`, marks failed, re-raises; `InProcessExecutor.stop()`
  (run_executor.py:105-113) cancels tasks and awaits the handlers. But on
  SIGKILL/crash that handler never runs, and `init_db()`
  ([database.py:291-294](caos/server/database.py:291)) only runs migrations — **no
  reset of orphaned `running` rows at startup**, and `InProcessExecutor` has no
  reaper (only `QueueWorker._reap_orphans`, run_executor.py:166, does lease-based
  recovery). Clients "poll GET /runs/{id} to completion"
  ([runs.py:4](caos/server/routes/runs.py:4)), so a stranded run polls forever.
  Bounded: `get_executor()` (run_executor.py:232) only returns `InProcessExecutor`
  on SQLite; production is Postgres → `QueueWorker` → lease reaper self-heals.
  SQLite is single-process dev/local only. **Root cause: no startup orphan-sweep
  for the SQLite/in-process path; real but dev-only gap — Postgres prod is
  covered by the lease reaper. Lowest-cost fix would be a one-shot
  `UPDATE runs SET status='failed' WHERE status='running'` in the in-process
  executor's `start()`.**

- [x] **7. `identity.py` edge-auth gate (fail-closed + constant-time compare) 🟢**
  Worry: forged `X-Forwarded-*` headers, or a 500 (instead of 401) from a non-ASCII
  edge secret.
  Evidence: [identity.py:56-92](caos/server/identity.py:56). `deployed` is true when
  `environment=="production"` or the legacy `DATABRICKS_APP_PORT` is set; in that
  state a header-less request raises 401 (fail-closed, line 82-85). When
  `edge_proxy_secret` is set, every deployed request must present a matching
  `x-edge-authorization`, compared with `hmac.compare_digest` on **bytes**
  (line 72) — the comment notes header values decode latin-1, so comparing bytes
  avoids `compare_digest` raising `TypeError` on a non-ASCII str (which would
  surface as 500, not 401). Startup warns if prod has no secret
  ([main.py:38-44](caos/server/main.py:38)). **Root cause: correct fail-closed
  design with the byte-compare edge case already handled. Not a bug.**

- [x] **8. `useLatestRun` / `useLivePipeline` live-overlay contract 🟢**
  Worry: a stale `issuerId` clobbering a newer load; an error stranding the page on
  a loading state; "running" nodes appearing for a terminal run.
  Evidence: [useLatestRun.ts:19-42](caos/frontend/src/lib/engine/useLatestRun.ts:19)
  — `cancelled` flag guards every `setValue`, and the effect keys on `issuerId`
  only, so a superseded load can't write. Any throw (no backend/network) →
  `setValue(empty)` (line 32) = static fallback, never a stuck loader.
  `buildLiveSnapshot` ([useLivePipeline.ts:52-105](caos/frontend/src/lib/pipeline/useLivePipeline.ts:52))
  is a pure transform; `liveOutcome` (line 30) maps committee_status → node state
  and never emits "running" (a terminal run has none), with idle reserved for
  nodes the run didn't produce. **Root cause: cancel-safe, side-effect-free,
  "prefer live / static fallback" honored. Not a bug.**

---

## Summary of root causes

Eight low-confidence items investigated; **no correctness bugs found**. Seven are
correct-as-designed (🟢); one is a real but bounded gap (🟡):

| # | Item | Verdict |
|---|------|---------|
| 1 | `--caos-consumer` color swap | 🟢 var defined (globals.css:18); intentional semantic fix |
| 2 | Deep-Dive `?issuer=` overlay | 🟢 documented reference-template UX; bespoke tabs flagged by banner + LIVE badge |
| 3 | Issuers stretched-link row | 🟢 correct WCAG nested-interactive fix; z-stacking sound |
| 4 | Issuers slash-tolerant route | 🟢 catch-all shadows redirect_slashes; dual-registration is the right fix |
| 5 | GraphCanvas `onActivate` | 🟢 strict a11y improvement (adds Space + SVG focus ring) |
| 6 | InProcessExecutor stranded runs | 🟡 no startup orphan-sweep on SQLite/in-process; **dev-only** (Postgres prod self-heals via lease reaper) |
| 7 | identity.py edge-auth gate | 🟢 fail-closed; byte-compare handles non-ASCII secret |
| 8 | useLatestRun/useLivePipeline | 🟢 cancel-safe, pure, static-fallback contract holds |

**Only actionable finding: #6.** On the SQLite/in-process executor a run orphaned
by an ungraceful crash stays `running` forever (no reaper, no startup sweep) and
the client polls it indefinitely. Production (Postgres → `QueueWorker`) is
unaffected — the lease reaper recovers it. One-line fix if desired: reset
`running → failed` in `InProcessExecutor.start()`.

---

# Pass 2 — security/data-path seams

Second sweep over the LLM-facing and filesystem-facing server seams (the ones
where untrusted text or a user-supplied URL/path reaches an effectful operation).

- [x] **9. EDGAR `fetch_exhibit` — server-side request forgery (SSRF) 🟢**
  Worry: the `POST /api/edgar/vault-exhibit` route hands a client-supplied
  `exhibit_url` to a server-side `urllib` GET — classic SSRF into the internal
  network.
  Evidence: [edgar.py:250-256](caos/server/edgar.py:250) — `fetch_exhibit` refuses
  any URL that doesn't `startswith("https://www.sec.gov/Archives/")`. The check is
  robust against the usual bypasses because it requires the `/` immediately after
  the host: `https://www.sec.gov@evil.com/...` fails (char after host is `@`, not
  `/`); `https://www.sec.gov.evil.com/Archives/` fails (`.` not `/`);
  `https://www.sec.gov/Archives/@evil.com` keeps the host as `www.sec.gov` (the
  `@` is in the path, not the authority). Body size is capped
  (`edgar_max_exhibit_mb`, line 255) and a User-Agent is mandatory (line 91, also
  the off-switch). Residual: `urllib` follows redirects, so a 3xx from sec.gov
  could chase an off-domain target — but that requires sec.gov itself to be
  hostile (not an attacker-controlled redirect). **Root cause: SSRF closed by a
  strict scheme+host prefix allowlist that pins the authority. Not a bug.**

- [x] **10. `nlquery` — SQL injection / prompt-injection-to-query 🟢**
  Worry: a natural-language question reaches the DB; could the model (or a crafted
  question) inject SQL or pivot the query onto an arbitrary column?
  Evidence: the model never authors SQL — it fills a closed `QuerySpec`
  ([nlquery.py:46](caos/server/nlquery.py:46)) that `validate_spec`
  ([nlquery.py:77-93](caos/server/nlquery.py:77)) checks against `CATALOG_BY_KEY`
  (rejects out-of-vocabulary `rank_by`/metric keys) and an op allowlist
  (`_FILTER_OPS`). In `execute`, `getattr(Issuer, f.field)`
  ([nlquery.py:314](caos/server/nlquery.py:314)) is reached only for
  `f.field in _FILTER_FIELDS` = `{industry, country}` (filtered at line 305), so
  the attribute name can't be attacker-chosen. Values go through SQLAlchemy
  (`col.ilike(f"%{value}%")` / `col == value`, line 315) — bound parameters, no
  string-built SQL. Prompt-injection blast radius is a wrong-but-in-vocabulary
  ranking, surfaced with provenance caveats. **Root cause: closed-schema +
  parameterized + catalog-validated; injection not reachable. Not a bug.**

- [x] **11. `rate_limit` fixed-window limiter 🟢**
  Worry: off-by-one in the budget check, unbounded `_windows` growth, or a thread
  race.
  Evidence: [rate_limit.py:31-43](caos/server/rate_limit.py:31). All reads/writes
  under `_lock`. Window roll: `now - start >= window_seconds` → reset to `(now, 1)`
  return True; else increment and return `count + 1 <= max_attempts` (correct
  inclusive budget). Map bounded by a sweep of expired entries once
  `len > _SWEEP_THRESHOLD` (line 35). Known fixed-window 2×-burst-at-boundary and
  the per-process caveat are both documented (module docstring lines 7-9).
  **Root cause: correct for the single-process deploy; multi-replica caveat is
  explicit. Not a bug.**

- [x] **12. `vault_export` filename construction — path traversal 🟢**
  Worry: an issuer name flows into a written file path
  (`runs_dir / f"{spoke_title(name,...)}.md"`); could `../` or an absolute path
  escape the vault?
  Evidence: every path component passes through `_title`
  ([vault_export.py:30-32](caos/server/vault_export.py:30)), which replaces each
  char in `_ILLEGAL = '\\/:*?"<>|#^[]'` (line 27) — including both slash kinds —
  with `-`, so no separator survives. `..` isn't stripped, but the basename is
  always suffixed `.md` and the spoke embeds `" - {rid}"`
  ([vault_export.py:91-98](caos/server/vault_export.py:91)), so a bare `..` segment
  is unreachable (worst case a file literally named `...md`). `vault_dir` itself is
  server config (`VAULT_EXPORT_DIR`), not user input. Defense-in-depth bonus:
  `_redact` (line 64) blanks raw-source-text keys before they hit a file that may
  sync off-machine. **Root cause: separator-stripping + mandatory `.md`/run-id
  suffix prevents traversal; the only user-controlled component is sanitized.
  Not a bug.**

- [x] **13. `scenario` driver-delta clamp — NaN/Infinity bypass 🟡(low)**
  Worry: model-supplied deltas reach the cash-flow projection after a `max/min`
  clamp; does the clamp actually bound *every* float the model can return?
  Evidence: `validate_scenario`
  ([scenario.py:51-59](caos/server/scenario.py:51)) clamps each field with
  `max(lo, min(hi, float(x or 0.0)))`. This bounds ordinary numbers, **but not
  NaN/±Infinity**: Python's `json.loads` accepts the non-standard `NaN` /
  `Infinity` literals by default, pydantic's `float` admits them, and `max`/`min`
  short-circuit on NaN comparisons (`min(0.05, nan) → nan`, `max(-0.15, nan) → nan`),
  so a NaN delta passes through unclamped. The no-op guard
  (`any(getattr(spec, f) …)`, line 55) treats NaN as truthy, so it isn't rejected
  either. A NaN/Inf delta then reaches the frontend Drivers and poisons the
  projection (renders `NaN`). Bounded: requires the model to emit non-standard JSON
  literals (a crafted/odd response, not normal output), and the impact is a broken
  projection display, not a security or data-integrity breach. The sibling
  `nlquery.validate_spec` is incidentally safe here because its `int(spec.limit)`
  raises on NaN and falls back to the demo mapper. **Root cause: `max/min` clamp
  doesn't sanitize non-finite floats that `json.loads`/pydantic admit. Lowest-cost
  fix: coerce with `0.0 if not math.isfinite(x) else x` before clamping (or set
  pydantic `allow_inf_nan=False` on the spec).**

---

## Pass-2 summary

Five LLM/filesystem-facing seams; **four correct-as-designed, one new bounded gap.**

| # | Item | Verdict |
|---|------|---------|
| 9 | EDGAR SSRF | 🟢 strict `https://www.sec.gov/Archives/` prefix allowlist pins the host |
| 10 | nlquery injection | 🟢 closed schema, catalog-validated, parameterized |
| 11 | rate_limit | 🟢 correct single-process; multi-replica caveat documented |
| 12 | vault_export traversal | 🟢 separator-strip + `.md`/run-id suffix; no escape |
| 13 | scenario NaN/Inf clamp | 🟡 non-finite deltas bypass `max/min` → poison projection (low: needs odd model output) |

**New actionable finding: #13** — `validate_scenario`'s `max/min` clamp lets
NaN/±Infinity through (json.loads admits them, NaN defeats comparison-based
clamping). One-line fix: drop non-finite to `0.0` before clamping, or
`allow_inf_nan=False` on `ScenarioSpec`. Running tally across both passes:
**13 items, 0 security bugs, 2 bounded robustness gaps (#6 dev-only stranded runs,
#13 NaN scenario deltas).**

---

# Pass 3 — engine core (the trust spine)

The pieces a wrong read rides on: the deterministic QA gate, the per-run token
budget under concurrent fan-out, and the BM25 evidence retriever. Verified the
pure logic *and* its wiring in `runner.py`.

- [x] **17. CP-5 gate `gate.py` — deterministic, fail-safe defaults 🟢**
  Worry: an LLM declaring its own output committee-ready, or an unknown
  status/confidence string silently upgrading a run.
  Evidence: the gate is pure functions, not model-decided
  ([gate.py:36-71](caos/server/engine/gate.py:36)). `qa_status_from` =
  CRITICAL→Blocked / MATERIAL→Restricted / else Passed (line 38-42);
  `committee_status_from` only returns `Committee Ready` after Blocked/Restricted/
  Not-Reviewed and `Insufficient Information` confidence are all excluded
  (line 45-55). Wiring confirmed in the runner: per-module at
  [runner.py:397-400](caos/server/engine/runner.py:397) and run-level at
  [runner.py:429-431](caos/server/engine/runner.py:429)
  (`roll_up_qa_status` over module statuses + `committee_status_from(.., worst_confidence(..))`).
  `worst_confidence` maps an unknown confidence to `0` = Insufficient = worst
  ([gate.py:71](caos/server/engine/gate.py:71)) → conservative/fail-safe. One
  asymmetry: `roll_up_qa_status` maps an unknown status to `-1` (better than
  Passed, [gate.py:63](caos/server/engine/gate.py:63)) — *fail-open* — but the
  inputs come from `qa_status_from`'s closed set {Blocked,Restricted,Passed}, so
  junk can't reach it. **Root cause: gate is deterministic and conservatively
  defaulted; LLM never self-certifies. Not a bug (the unknown-status fail-open is
  unreachable given the closed producer).**

- [x] **18. `budget.py` token budget — ContextVar threading under concurrent gather 🟢**
  Worry: modules fan out as concurrent tasks; does the per-run budget actually
  thread into each task, and can `used += …` lose updates under that concurrency?
  Evidence: the runner installs one `RunBudget` and `set_budget()`s it *once*
  ([runner.py:206-207](caos/server/engine/runner.py:206)) **before** the parallel
  `asyncio.gather(*(_attempt_synth(m) …))`
  ([runner.py:314](caos/server/engine/runner.py:314)). `gather` wraps each
  coroutine in a Task that copies the current context, so every module task reads
  the *same* `RunBudget` object via the ContextVar
  ([budget.py:40-50](caos/server/engine/budget.py:40)); `record()` mutates that
  shared object in place ([budget.py:36-37](caos/server/engine/budget.py:36)) with
  no `await` between read and write, so on the single-threaded event loop the
  `+=` can't interleave — no lost updates. `_input_tokens` sums input +
  cache_read + cache_creation so the cap is caching-invariant (budget.py:59-68).
  Advisory by design: `llm_allowed()` gates *new* calls; an in-flight call can
  overshoot — documented ("degrades to deterministic path"). **Root cause: shared
  object + set-before-fan-out + no await-in-record = correct accrual. Not a bug.**

- [x] **19. `retrieval.py` BM25 — scoring correctness + scaling ceiling 🟢→🟡(scale)**
  Worry: a hand-rolled Okapi BM25 (no library) ranking the evidence — subtle
  scoring bugs, div-by-zero, or a memory cliff at portfolio scale.
  Evidence: scoring is standard Okapi
  ([retrieval.py:82-94](caos/server/retrieval.py:82)) with the robust
  `log(1 + (n-df+0.5)/(df+0.5))` idf that stays strictly positive (no negative-idf
  pathology for common terms); empty-doc guard `len(toks) or 1` avoids div-by-zero
  (line 67); `score > 0` filter + best-first top-k (line 91-94). In-run path builds
  the index once and reuses it ([runner.py:218](caos/server/engine/runner.py:218)
  → `rank_with_index`), the documented P4-2 optimization. Bounded concern: the
  cross-issuer paths (`retrieve_corpus`, `retrieve_corpus_by_issuer`,
  [retrieval.py:139-184](caos/server/retrieval.py:139)) `SELECT` **every** chunk of
  the in-scope issuers into Python and re-tokenize per query — O(corpus) memory +
  CPU with no DB-side prefilter. Fine for Phase-1 (a handful of public issuers);
  it becomes a latency/memory cliff at scale. The module header already names the
  upgrade path (swap the corpus fetch for a pgvector index behind the same
  interface). **Root cause: BM25 math is correct and guarded; the only real
  exposure is a documented O(corpus)-per-query scaling ceiling, not a correctness
  bug.**

---

## Pass-3 summary

Three trust-spine seams; all correct, one carries a documented scaling ceiling.

| # | Item | Verdict |
|---|------|---------|
| 17 | CP-5 gate | 🟢 deterministic, fail-safe confidence default; LLM never self-certifies |
| 18 | run token budget | 🟢 shared object across gather, no `+=` race; advisory by design |
| 19 | BM25 retrieval | 🟢 correct Okapi; 🟡 O(corpus)-per-query at scale (pgvector upgrade path noted) |

Running tally across all three passes: **19 items, 0 security bugs, 2 bounded
robustness gaps (#6 SQLite stranded runs, #13 NaN scenario deltas), 1 documented
scaling ceiling (#19 BM25 loads full corpus per cross-issuer query).** Engine
trust spine (deterministic gate, bounded budget, grounded retrieval) verified
intact.
