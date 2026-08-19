# Audit Backlog — Round 2

Areas of the CAOS frontend + system design investigated this round. Within each
section, items were ordered least-confident first. Each carries a verdict and a
root-cause finding with `file:line` evidence.

**Status: investigated 2026-06-23 (read-only; no code changed).** Verdicts:
🟢 correct-as-designed · 🟡 real gap, bounded · 🔴 bug.

**Net result:** 4 🔴 bugs — **S7** (CRLF log-injection in the exception
logger), **P4** (`list_runs` returns all rows unbounded), **L2** (truncated
deep-research report returned as complete), **D5** (failed `pg_dump` rotates
out good backups). ~10 🟡 bounded gaps. The rest are correct-as-designed.
Several of this backlog's own (unverified) premises turned out factually wrong
— corrected inline (notably C2, C4, C5, P2, P3, L4, L5, D1, D4, D7, D10).

**Excludes** the 24 items already resolved in
[`audit-backlog.round1-resolved.md`](audit-backlog.round1-resolved.md) and
[`audit-log.md`](audit-log.md).

Branch `fix/vmo2-followups` has uncommitted WIP edited in parallel.

### Remediation (2026-06-23) — the 4 🔴, fixed + adversarially verified

- **S7** — `sanitize_field()` strips C0/DEL + caps 256 at every identity boundary:
  `principal`/`client_source` ([access_log.py](caos/server/access_log.py)), both
  `CallerIdentity` constructions ([identity.py](caos/server/identity.py)), and
  the `Analyst` name/email persistence ([routes/auth.py](caos/server/routes/auth.py)
  — added in the same-class sweep the verifier flagged).
- **P4** — `limit`/`offset` clamps on `list_runs`
  ([routes/runs.py](caos/server/routes/runs.py)) **and** the sibling unbounded
  lists `list_issuers` + `list_issuer_documents`
  ([routes/issuers.py](caos/server/routes/issuers.py)). `filing_exhibits` left
  alone (bounded by one external filing; a cap would hide covenant docs).
- **L2** — `truncated` flag + emoji-free in-report banner; empty-at-cap no longer
  mislabeled as "model finished" ([deepresearch.py](caos/server/deepresearch.py)).
- **D5** — rotation gated on `pg_dump … && [ -s file ]`; partial dropped on
  failure ([backup.sh](caos/deploy/backup.sh)).

Plus **L2-class:** `llm.py:ask_issuer` now flags a `max_tokens`-capped chat reply
([llm.py](caos/server/llm.py)).

### Remediation round 2 (2026-06-23) — 🟡 batch

- **S2** empty `analyst_signup_code` → fail closed (503), not silent
  ([routes/auth.py](caos/server/routes/auth.py)).
- **S5** cookie `Secure` now rides `environment != "development"`, not the exact
  label `"production"` ([routes/auth.py](caos/server/routes/auth.py)).
- **C3** cyclic registry → `raise` instead of silent Blocked cascade
  ([engine/runner.py](caos/server/engine/runner.py)).
- **C6** worker loop escalates to error after 3 consecutive failed ticks — a
  stalled queue is now distinguishable from an empty one
  ([run_executor.py](caos/server/run_executor.py)).
- **D6** static `Cache-Control` — immutable for `/_next/static/*`, `no-cache` for
  HTML docs ([main.py](caos/server/main.py)).
- **D8** `ix_metric_facts_run_id` index + model flag (migration 0009).
- **P1/P2/L6** root: axios default `timeout: 20000`
  ([api.ts](caos/frontend/src/lib/api.ts)) — long calls still override
  (`deepResearch: 0`). Closes the hung-live-overlay / hung-settings-probe paths.

Tests: **339 pass / 2 skip**; frontend `tsc --noEmit` clean. Still deferred:
`Run.created_at` index for large-offset latency (low severity); L2 frontend
`truncated` chrome chip (cosmetic — banner is in the report); **S6** rate-limiter
(login key off spoofable XFF + per-process scaling); **D3** `/api/health` DB
check; **D9** image digest pinning + `markitdown[pdf]` pin; **CI** deploy-asset
lint (`shellcheck`/`compose config`); L6 residual (research page still treats an
unknown `llmConfigured` as configured — now fails fast instead of hanging).

### Remediation round 3 (2026-06-23)

- **S6** — hard ceiling (`_MAX_ENTRIES`) evicts oldest windows so distinct-key
  spraying can't grow the map unbounded ([rate_limit.py](caos/server/rate_limit.py)).
  Login key left on the proxy-set XFF first hop (socket-peer would collapse all
  users behind the shared proxy into one bucket); XFF-spoof + per-process scaling
  remain deployment-bounded (off-proxy / multi-replica only).
- **D3** — `/api/health` now probes the DB (`SELECT 1`) and returns 503 on
  failure: readiness, not just liveness ([routes/health.py](caos/server/routes/health.py)).
- **D9** — **deferred (attempted, reverted).** Tried `pip install -c
  requirements.txt 'markitdown[pdf]'` but pip constraint files reject `[extras]`
  (requirements.txt carries one) → image build failed, reverted. Proper integrity
  fix = a pip-compiled lockfile (single resolution + hashes); plus markitdown
  version + image `@sha256` digest pins. All follow-up (can't resolve offline).
- **CI** — new `deploy-assets` job: `shellcheck caos/deploy/*.sh caos/scripts/*.sh`
  + `docker compose config -q` ([ci.yml](.github/workflows/ci.yml)) — closes the
  blind spot that let D5 through. (One intentional `SC2012` disable on the
  mtime-sort rotation lines.)

Tests: **341 pass / 2 skip**; ruff 0.15.18, `tsc`, shellcheck all clean. Compose
validation runs in CI (no local docker). Remaining: `Run.created_at` index; L2
frontend `truncated` chip; D9 version/digest pins; S6 (b)/(c) deployment-bounded;
L6 demo-warning gate.

Categories: `[security]` `[auth]` `[secrets]` `[dos]` `[concurrency]`
`[logic]` `[error]` `[perf]` `[edge]` `[migration]` `[db]` `[deploy]`
`[config]` `[data-loss]`.

---

## Security / auth / secrets

- [x] **Session-secret HMAC over an empty key.** `read_session_token`
  ([identity.py:130](caos/server/identity.py)) — confirm what happens when
  `session_secret` is empty/unset: does an HMAC keyed on `b""` accept a
  forge-able cookie, and does prod fail closed? `config.py:47-49` is said to
  raise on the dev default in prod, but verify the empty-string and non-prod
  paths. [auth]

  **🟢 correct-as-designed (one retired-path nuance).** `read_session_token`
  ([identity.py:69-81](caos/server/identity.py)) does a genuine constant-time
  `hmac.compare_digest(sig, _sig(raw, secret))`, not a presence check — so an
  empty key *would* verify an empty-key-signed forgery, but prod can't reach
  that state: [main.py:46-53](caos/server/main.py) raises `RuntimeError` if
  `environment=="production"` and `session_secret in ("", "dev-insecure-session-secret")`.
  Fail-closed on both empty and default. **Residual:** the legacy
  `DATABRICKS_APP_PORT`-only "deployed" path treats requests as deployed
  ([identity.py:104](caos/server/identity.py)) but the SESSION_SECRET guard keys
  only on `environment=="production"`, so a non-prod Databricks deploy would
  trust the public dev-default secret. Dead code — Databricks was dropped — but
  it shares the brittle exact-string `=="production"` root with S3/S5.

- [x] **Login code fails *open* on empty value.** `routes/auth.py:97` uses
  `hmac.compare_digest` against `analyst_signup_code`, but if that setting is
  empty there may be no fail-closed guard — every code would pass. Default
  `131113` is also hardcoded in source ([config.py:57](caos/server/config.py)).
  [auth]

  **🟡 real gap, bounded (operator footgun).** Confirmed there is no
  empty-`analyst_signup_code` guard at [auth.py:97](caos/server/routes/auth.py),
  and `hmac.compare_digest("", "") → True`, so `ANALYST_SIGNUP_CODE=""` would let
  an empty submitted code through. **Two mitigations stop it being a default
  exploit:** the Pydantic body enforces `code: str = Field(min_length=1, …)`
  ([auth.py:47](caos/server/routes/auth.py)) so a client *cannot* submit `""`
  (422 before the compare), and the default is non-empty `131113`. So it only
  bites if an operator explicitly exports an empty code — and unlike
  `SESSION_SECRET` there's no startup guard against that. Secondary note: the
  code is low-entropy (6 digits, in source), partly offset by 10/min per-IP
  login throttling. **Fix:** `if not settings.analyst_signup_code: raise
  HTTPException(503, "Login disabled")` (or extend the `main.py` prod startup
  guard to reject an empty code).

- [x] **Asymmetric fail behavior on the two secrets.** Missing `SESSION_SECRET`
  is said to *stop* the app in prod; missing `EDGE_PROXY_SECRET` only *warns*
  ([main.py:38](caos/server/main.py)) and boots. Confirm this asymmetry is
  intended. [config]

  **🟢 correct-as-designed.** Both behaviors verified exactly:
  missing/default `SESSION_SECRET` → `RuntimeError`
  ([main.py:46-53](caos/server/main.py)); missing `EDGE_PROXY_SECRET` →
  `logger.warning` + boot ([main.py:39-45](caos/server/main.py)). The asymmetry
  is sound: `SESSION_SECRET` is the *sole* integrity control on the analyst
  cookie (no safe fallback → must fail closed), whereas `EDGE_PROXY_SECRET` is
  *defense-in-depth* over network isolation (app publishes no port; only the
  proxy reaches it), so warn-and-boot is the right posture for an optional
  hardening layer. The code comments at [config.py:41-50](caos/server/config.py)
  and identity.py articulate this. Caveat: both gates key on the brittle exact
  string `=="production"` (shared with S1/S5).

- [x] **Vault/exhibit filename sanitization vs path traversal.** `_title()`
  ([vault_export.py:31](caos/server/vault_export.py)) strips illegal chars;
  vault writes ([vault_export.py:210](caos/server/vault_export.py)) +
  `routes/edgar.py:181` (`file_name` from a URL basename) build paths from
  issuer/run/exhibit names. [edge]

  **🟢 correct-as-designed (airtight).** Two independent sanitizers each
  neutralize separators. `_title()` replaces every char in
  `_ILLEGAL = '\\/:*?"<>|#^[]'` — **both `/` and `\`** — with `-`
  ([vault_export.py:27-32](caos/server/vault_export.py)); confirmed
  `"../../etc/passwd" → "..-..-etc-passwd"`. The upload/exhibit store runs
  `re.sub(r"[^A-Za-z0-9._-]", "_", Path(file_name).name)`
  ([ingest.py:76-77](caos/server/ingest.py)) — `Path().name` collapses any
  directory part, whitelist kills residual backslashes; `"../../etc/passwd" →
  "passwd"`. The EDGAR basename is re-sanitized by `store()`
  ([routes/edgar.py:181-183](caos/server/routes/edgar.py)). A bare `".."`
  survives `_title` but is always a single component under a fixed parent and
  cannot climb without an embedded separator (and would hit a directory and fail
  the write). No fix warranted.

- [x] **Cookie `Secure` only in production.** `routes/auth.py:72` sets the
  flag only when `environment == "production"`. [auth]

  **🟡 real gap, bounded.** Confirmed at
  [auth.py:69-73](caos/server/routes/auth.py): `httponly=True` and
  `samesite="lax"` are always set (correct), but
  `secure=settings.environment == "production"` — so any env-label mistype
  (unset, `prod`, `Production`) drops the `Secure` attribute and the auth cookie
  rides plaintext HTTP. Masked in the intended deploy by Caddy TLS + HSTS
  ([main.py:112](caos/server/main.py)), but the cookie's own flag is the
  last-line control and it silently degrades on a one-character env mismatch —
  the same brittle `=="production"` that also governs SESSION_SECRET enforcement
  and docs closure, so a single mistype downgrades several controls at once.
  **Fix:** derive `Secure` from `request.url.scheme == "https"` (or
  `environment != "development"`) instead of the exact literal.

- [x] **Rate-limiter is per-process, unbounded, and IP-keyable to a constant.**
  `rate_limit.py` — keys sweep only past 1024 entries; in-memory store isn't
  shared (scaling bypass); login keyed by client IP that falls back to `"?"`
  ([routes/auth.py:91](caos/server/routes/auth.py)). [dos]

  **🟡 real gap, bounded (all three confirmed, by-design for the topology).**
  (a) `_windows` grows until >1024 entries and the sweep evicts only *expired*
  windows ([rate_limit.py:20-37](caos/server/rate_limit.py)), so 1024+ live
  distinct keys stay resident — memory-pressure only (tiny entries). (b)
  Per-process map, documented to multiply limits by replica count. (c) The
  bigger issue isn't the `"?"` fallback (that *shares* one bucket — benign) but
  that the login key derives from the **client-supplied first `X-Forwarded-For`
  hop** ([access_log.py:37-39](caos/server/access_log.py)); off-proxy, each
  forged XFF is a fresh key, fragmenting the 10/min budget. All bounded because
  oauth2-proxy is the sole ingress and overwrites XFF in the supported topology.
  **Fix:** key the login throttle on `request.client.host` (socket peer) rather
  than the spoofable XFF.

- [x] **Log injection / PII via forwarded + uploaded fields.**
  `access_log.py:38` splits `X-Forwarded-For` on comma; `uploaded_by =
  caller.email` is stored raw ([routes/ingestion.py:81](caos/server/routes/ingestion.py)).
  [edge]

  **🔴 bug (premise partly corrected).** The *access log* itself is safe — it
  goes through `json.dumps`, which escapes CRLF
  ([access_log.py:54-62](caos/server/access_log.py)), and it logs only the first
  XFF hop, not the whole header (so S7(a) is *not* a bug). **The real sink:** the
  unhandled-exception logger interpolates the raw principal into a plain-text
  record — `logger.exception("unhandled exception: %s %s (caller=%s)", …,
  principal(headers))` ([main.py:160-165](caos/server/main.py)) — and
  `principal()` ([access_log.py:26-30](caos/server/access_log.py)) returns
  `X-Forwarded-Email`/`-User` with no sanitization, so a `\r\n`-bearing header
  forges log lines there. Separately `uploaded_by=caller.email` is persisted raw
  ([routes/ingestion.py:81](caos/server/routes/ingestion.py),
  [routes/edgar.py:193](caos/server/routes/edgar.py)). Bounded: oauth2-proxy
  sets `X-Forwarded-Email` from the SSO session (not client-settable), so it
  needs proxy misconfig or un-proxied access. **Fix:** strip control chars at the
  identity boundary, e.g. `re.sub(r"[\x00-\x1f\x7f]", "", v)[:256]` in
  `principal()`/`client_source()` and when assigning `uploaded_by`.

- [x] **Stack traces to logs.** `logger.exception()`
  ([main.py:160](caos/server/main.py)) — confirm this isn't reachable into a
  client response. [edge]

  **🟢 correct-as-designed.** The handler `log_unhandled`
  ([main.py:158-166](caos/server/main.py)) writes the trace to the server log
  only and returns a fixed `JSONResponse({"detail": "Internal Server Error"},
  status_code=500)` — the exception/traceback/internals never enter the response
  body. App is built without `debug=True`; docs/openapi are `None` in prod
  ([main.py:84-86](caos/server/main.py)). Textbook log-internally /
  return-opaque pattern. (The principal *value* logged here is the S7 CRLF sink,
  but the trace itself doesn't leak to clients.) No fix.

## Performance

- [x] **`useLiveRun` `Promise.all` has no short-circuit / timeout.**
  [useLiveRun.ts:32](caos/frontend/src/lib/engine/useLiveRun.ts) — one slow
  `getModule` blocks all live modules; no per-call timeout. [perf]

  **🟡 real gap, bounded.** Each `getModule` has a per-module `try/catch`
  ([useLiveRun.ts:32-40](caos/frontend/src/lib/engine/useLiveRun.ts)) so a
  *rejection* is isolated, but `Promise.all` still waits for the slowest, and the
  shared axios client has **no default timeout**
  ([api.ts:6-8](caos/frontend/src/lib/api.ts)) — so one hung (never-rejecting)
  module stalls the whole `await`, leaving `loading:true` and no live render.
  Results commit once (no streaming) at
  [useLatestRun.ts:29-30](caos/frontend/src/lib/engine/useLatestRun.ts). Bounded:
  it's the live *overlay*; the seeded static demo shows underneath, so it
  degrades rather than white-screens. **Root fix (shared with P2/L6):** give the
  engine reads a bounded `timeout` so a stall rejects and the existing per-module
  catch skips it.

- [x] **`useLivePipeline` `getModule` can hang.**
  [useLivePipeline.ts:108](caos/frontend/src/lib/pipeline/useLivePipeline.ts)
  — no timeout on the poll call. [perf]

  **🟢 correct-as-designed (premise wrong: there is no poll).**
  `useLivePipeline` fires once per `issuerId` via `useLatestRun` — no polling
  loop ([useLivePipeline.ts:108-114](caos/frontend/src/lib/pipeline/useLivePipeline.ts));
  the CP-X fetch is guarded `getModule(...).catch(() => null)`. The page renders
  the offline sim while `live` is `null` (`useLive = liveMode && live != null`,
  [pipeline/page.tsx:52](caos/frontend/src/app/pipeline/page.tsx)) — no stuck
  spinner. Only residual is the shared no-timeout hang (P1's root), whose effect
  here is merely "stays on the offline demo." No correctness fix needed.

- [x] **EDGAR rate lock is synchronous.** `_rate_lock` / `_http_get`
  ([edgar.py:101](caos/server/edgar.py)) — a blocking lock + wall-clock
  `sleep()` can stall the event loop. [perf]

  **🟢 correct-as-designed (premise wrong on the dangerous half).** It *is* a
  `threading.Lock` + synchronous `time.sleep` ([edgar.py:48,100-104](caos/server/edgar.py))
  — but it never runs on the event loop. Every async caller dispatches the sync
  EDGAR functions to a worker thread: `await asyncio.to_thread(edgar_cp1.fetch_cp1, …)`
  ([runner.py:502](caos/server/engine/runner.py)) and `await
  run_in_threadpool(edgar.…)` for all four routes
  ([routes/edgar.py:114,132,148,177](caos/server/routes/edgar.py)). So the
  `threading.Lock`+`sleep` is the *correct* primitive — a cross-thread throttle
  that serializes SEC requests ≥150 ms apart in worker threads, never touching
  the loop. No fix.

- [x] **No pagination on list/query results.** `list_runs`
  ([routes/runs.py:213](caos/server/routes/runs.py)) returns all runs;
  `nlquery.execute` ([nlquery.py](caos/server/nlquery.py)) can return all
  matching `metric_facts`. [dos]

  **🔴 bug (`list_runs`) / 🟢 (`nlquery`).** `GET /api/runs` issues
  `select(Run).order_by(Run.created_at.desc())` with **no `.limit()`/offset** and
  returns every row ([routes/runs.py:203-214](caos/server/routes/runs.py)); run
  rows accumulate one-per-analysis forever → genuine unbounded
  memory/latency/exfil-volume growth, unlike the sibling EDGAR/query endpoints
  which clamp via `Query(..., le=...)`. `nlquery.execute` is **safe**: spec
  `limit` is hard-clamped to `_MAX_LIMIT=50`
  ([nlquery.py:37,92](caos/server/nlquery.py)), results truncated
  ([nlquery.py:362-363](caos/server/nlquery.py)), and the SQL is pre-filtered to
  `headline.is_(True)` × a handful of catalog metrics — bounded by curated data,
  not attacker input. **Fix:** add `limit: int = Query(100, ge=1, le=500)` →
  `stmt.limit(limit)` on `list_runs`.

- [x] **Index-keyed source list + duplicate print portals.**
  `ReportPane` index keys ([ReportPane.tsx:123](caos/frontend/src/components/research/ReportPane.tsx));
  `PrintPortal` appends to `document.body` with no unique id
  ([reports/page.tsx:38](caos/frontend/src/app/reports/page.tsx)). [perf]

  **🟢 correct-as-designed (both).** (a) The `sources` array is render-once,
  append-only output of a completed run, never reordered/spliced, and the items
  are stateless leaf `<li><a>` — index keys carry no identity-loss or perf
  penalty here ([ReportPane.tsx:123-124](caos/frontend/src/components/research/ReportPane.tsx)).
  (b) `PrintPortal` creates its div in a `useEffect` with empty deps and returns
  `() => d.remove()` ([reports/page.tsx:36-42](caos/frontend/src/app/reports/page.tsx)),
  rendered once at :254 — re-renders update portal *contents* via `createPortal`,
  not the node, so no duplicate/leaked `.print-root` divs. No fix.

## Concurrency / run lifecycle

- [x] **`_CREATE_RUN_LOCK` lazy-init race.**
  [routes/runs.py:36](caos/server/routes/runs.py) — two requests could each
  construct a `Lock` and one overwrites the other. [concurrency]

  **🟡 real gap, bounded (unreachable as written).** The check-then-set
  `if _CREATE_RUN_LOCK is None: _CREATE_RUN_LOCK = asyncio.Lock()`
  ([routes/runs.py:40-44](caos/server/routes/runs.py)) is non-atomic in
  principle, but there is **no `await` between the read and the write**, so under
  single-loop CPython asyncio no other coroutine can interleave — the race is
  unreachable today. It would become real only if a future edit inserted an
  `await` there, or the function were called from multiple threads. **Fix
  (defensive):** initialize the lock eagerly in the lifespan/startup hook to
  remove the check-then-set entirely.

- [x] **`asyncio.gather(return_exceptions=True)` result/ input order.**
  [engine/runner.py:315](caos/server/engine/runner.py) — confirm results map to
  the right module. [logic]

  **🟢 correct-as-designed (premise wrong on two counts).** `asyncio.gather`
  preserves awaitable order, and the code zips that result list against the
  *same* source list: `gather(*(_attempt_synth(m) for m in parallel))` then
  `zip(parallel, gathered)` ([runner.py:314-315](caos/server/engine/runner.py))
  — `module_id` always lines up with its own result, no mispairing. The call
  does **not** use `return_exceptions=True` and doesn't need to: `_attempt_synth`
  catches `SynthesisError` and *returns* it as a value
  ([runner.py:255-256](caos/server/engine/runner.py)), so expected failures
  arrive as ordered elements; an unexpected exception intentionally propagates
  and fails the whole run ([runner.py:436](caos/server/engine/runner.py)). No fix.

- [x] **Dependency-cycle fallback runs anyway.**
  [engine/runner.py:102](caos/server/engine/runner.py) — remaining modules run
  in arbitrary order instead of failing the run. [logic]

  **🟡 real gap, bounded.** Confirmed: `_dependency_layers`
  ([runner.py:97-108](caos/server/engine/runner.py)) does `if not layer: layer =
  list(remaining)` on a layering stall, accepting all remaining modules as one
  layer in input order rather than raising. Consequences are bounded — input
  order is the planner's topo order (not truly arbitrary), and the per-module
  input gate ([runner.py:238-242](caos/server/engine/runner.py)) still blocks any
  module whose upstream hasn't produced — so a real cycle degrades to a run full
  of "Blocked" modules, not wrong-but-green output. The gap: a genuinely cyclic
  registry fails *silently* instead of surfacing "registry is not a DAG."
  **Fix:** `raise RuntimeError(f"CP-X cycle among {remaining}")` in the fallback.

- [x] **MetricFact delete-then-reinsert without dup guard.**
  [engine/runner.py:408](caos/server/engine/runner.py) — empty extract could
  wipe the issuer's facts; atomicity across partial failure? [error]

  **🟢 correct-as-designed (premise wrong three ways).** (1) **Order:** facts are
  *added first* ([runner.py:408-413](caos/server/engine/runner.py)) and the
  supersede DELETE runs *after* (:419-425). (2) **Scope:** the DELETE excludes
  the current run and seeds — `provenance=="run" AND run_id != run.id`
  ([runner.py:421-424](caos/server/engine/runner.py)) — so it can't delete the
  just-inserted rows. (3) **No-wipe-on-empty:** extractors are None-guarded;
  empty/garbage financials yield zero new facts (transient gap until next good
  run), not corruption. Atomic: adds+delete share one session committed together
  ([run_executor.py:37](caos/server/run_executor.py)); partial failure rolls back.
  `uq_fact` is the dup guard. No fix.

- [x] **`expire_on_commit=False` cross-session staleness.**
  [database.py:59](caos/server/database.py) — worker vs request could serve
  stale state. [concurrency]

  **🟢 correct-as-designed.** Request and worker use **separate sessions with
  separate identity maps** (worker: `AsyncSessionLocal()`
  [run_executor.py:30](caos/server/run_executor.py); request: `get_db`
  [database.py:314-322](caos/server/database.py)) — there is no shared live `Run`
  object to go stale. The poll path `GET /runs/{id}` does `db.get(Run, run_id)`
  in a fresh session ([routes/runs.py:223](caos/server/routes/runs.py)) → real
  SELECT of whatever the worker last committed. `expire_on_commit=False` is in
  fact *required* here (documented at
  [database.py:36-40](caos/server/database.py)) — expiring triggers lazy reloads
  that break under the test harness's cross-loop pooling. No fix.

- [x] **Run-failure write paths can themselves fail silently.**
  `_mark_run_failed` swallows nested exceptions
  ([run_executor.py:78](caos/server/run_executor.py)); the worker loop never
  re-raises/alerts ([run_executor.py:239](caos/server/run_executor.py)). [error]

  **🟡 real gap, bounded.** Both swallows are real. (a) `_mark_run_failed`
  ([run_executor.py:75-86](caos/server/run_executor.py)) wraps
  rollback+mark+commit in `try/except: logger.exception` — a persistently
  unreachable DB leaves the run `running`. Bounded by recovery: Postgres
  `_reap_orphans` ([run_executor.py:179-208](caos/server/run_executor.py)) flips
  lease-expired runs to failed/re-claims them; SQLite `InProcessExecutor.start()`
  fails non-terminal runs on next boot — so it self-heals within a lease window /
  on restart, doesn't hang forever. (b) The worse half: `_run_loop` catches
  `except Exception: logger.exception("worker loop tick failed")`
  ([run_executor.py:237-238](caos/server/run_executor.py)) and continues with no
  alert — a persistent per-tick DB error means the worker is **alive but silently
  idle**, queued runs never execute, only log noise as signal. **Fix:** emit a
  metric/alert on N consecutive failed ticks (and failed mark-failed commits).

## Logic / correctness

- [x] **Model-JSON specs admit NaN/Inf before clamping.** `nlquery.py:212`
  and `scenario.py:143` build a Pydantic spec from `json.loads` of model
  output; clamping happens after. [logic]

  **🟢 (`scenario.py`) / 🟡 (`nlquery.py`).** Premise confirmed: Python's
  `json.loads` accepts `NaN`/`Infinity` by default (no `parse_constant`
  anywhere), and Pydantic floats pass them through. **`scenario.py` is
  correctly defended** — `validate_scenario` clamps with an explicit
  `if not math.isfinite(v): v = 0.0` *before* `max/min`
  ([scenario.py:56-58](caos/server/scenario.py)) — necessary because `max/min`
  silently mis-clamp NaN. **`nlquery.py` 🟡:** `Filter.value` is typed `object`
  and not finite-checked ([nlquery.py:42](caos/server/nlquery.py)), so a
  `value: Infinity` survives validation — but at execution `_passes` does
  `float(target)` then a comparison, where `x > inf` is just `False` (no crash,
  no division); blast radius is "an over-restrictive filter quietly returns
  fewer rows." Ranked numbers come from the DB, not the spec, so ranking can't be
  poisoned. **Also:** neither path logs the raw hallucinated JSON on
  validation failure ([nlquery.py:223](caos/server/nlquery.py),
  [scenario.py:154](caos/server/scenario.py)) — diagnostic gap. **Fix:** mirror
  the `math.isfinite` guard on `Filter.value`; log truncated raw JSON on
  `QueryError`/`ScenarioError`.

- [x] **Deep-research partial report not flagged.**
  [deepresearch.py:192](caos/server/deepresearch.py) — a report cut off at the
  continuation cap is returned as if complete. [error]

  **🔴 bug (bounded severity).** Confirmed: `for _ in range(_MAX_CONTINUATIONS)`
  (cap 4, [deepresearch.py:36,192](caos/server/deepresearch.py)); if the model
  is still `pause_turn` on the last iteration the loop exhausts and falls through
  to `report = "".join(text_parts)` returned as a normal
  `ResearchResult(report=…, demo=False)` ([deepresearch.py:220-230](caos/server/deepresearch.py))
  with **no completeness flag**. The only guard fires on *zero* prose — a
  present-but-truncated report (several sections then cut) passes as complete.
  Same for a single turn hitting `max_tokens` (16000). `ResearchResult`
  ([deepresearch.py:118-121](caos/server/deepresearch.py)) has no
  `truncated`/`stop_reason` field to carry the signal. A committee-facing report
  can be silently missing sections. **Fix:** track `break` (terminal) vs
  range-exhaustion / `max_tokens`, add a `truncated` field, and append a
  "⚠ truncated at the research cap" banner.

- [x] **Issuer search: no AbortController → stale clobber.**
  [issuers/page.tsx:70](caos/frontend/src/app/issuers/page.tsx) — slow earlier
  response could overwrite a newer one. [logic]

  **🟢 correct-as-designed.** No AbortController, but the standard `stale`-flag
  pattern prevents any clobber: each `query` change re-runs the effect whose
  cleanup flips the prior run's captured `stale = true`
  ([issuers/page.tsx:81](caos/frontend/src/app/issuers/page.tsx)), and every
  `setIssuers`/`setDegraded` is guarded by `if (stale) return`
  ([issuers/page.tsx:70-79](caos/frontend/src/app/issuers/page.tsx)) — a
  late-arriving older response no-ops. AbortController would only save bandwidth.
  No fix.

- [x] **`sim.ts` interval runs stale closures.**
  [sim.ts:159](caos/frontend/src/lib/pipeline/sim.ts) — `speed`/`complete`
  change without re-scheduling. [logic]

  **🟢 correct-as-designed (premise wrong).** The interval effect's dep array
  **is** `[playing, speed, sim.done, plan, complete, tickMs]`
  ([sim.ts:157-161](caos/frontend/src/lib/pipeline/sim.ts)) — `speed`/`complete`
  changes tear down (`clearInterval`) and reschedule. The body uses the
  functional updater `setSim((s) => stepSim(s, plan, complete))` so it always
  reads latest state, and `plan`/`complete` are current because the effect
  re-ran. No stale closure. No fix.

- [x] **`localStorage` reads without shape/`NaN` guards.**
  `reports/page.tsx:61` (`parseFloat`→`NaN`), `reports/page.tsx:89` (three
  `JSON.parse` unverified), `IssuerChat.tsx:80` (parse in initializer). [logic]

  **🟢 correct-as-designed (all three; premises wrong).** (a) `parseFloat("")
  → NaN`, but the range check `s >= 0.5 && s <= 1.5 ? s : 1`
  ([reports/page.tsx:62-65](caos/frontend/src/app/reports/page.tsx)) rejects NaN
  (both comparisons false) → default `1`. (b) All three parses **are**
  type-checked before assignment — `if (o && typeof o === "object") setOmit(o)`
  ([reports/page.tsx:89-92](caos/frontend/src/app/reports/page.tsx)) — inside a
  `try/catch`. (c) The `JSON.parse` **is** inside the `try` in the initializer
  with `|| []` fallback ([IssuerChat.tsx:79-81](caos/frontend/src/components/deepdive/IssuerChat.tsx));
  missing/malformed → `[]`. Only a hand-corrupted valid-JSON non-array would slip
  through (app only ever writes arrays). No fix (defensive nicety:
  `Array.isArray(x) ? x : []`).

- [x] **Settings/research config errors swallowed.**
  `research/page.tsx:66` and `settings/page.tsx:66` — `getSettings()` failures
  caught silently. [logic]

  **🟡 (research) / 🟢 (settings).** **Research** `getSettings().then(s =>
  setLlmConfigured(s.llm_configured)).catch(() => {})`
  ([research/page.tsx:65-67](caos/frontend/src/app/research/page.tsx)) — on
  failure *or* a hung untimed request, `llmConfigured` stays `null`, which is
  treated as "configured": the demo banner only shows on `=== false`
  ([research/page.tsx:164](caos/frontend/src/app/research/page.tsx)) and the
  button reads "Run deep research." So a no-key/demo backend whose probe fails
  gets *no* demo warning before a run — exactly the case the code meant to guard.
  Bounded (the run still returns a canned report). **Settings** sets an explicit
  `cfgErr` flag rendered as an error ([settings/page.tsx:124-126](caos/frontend/src/app/settings/page.tsx))
  — correct. **Fix:** bounded `timeout` on `getSettings` + treat a failed probe
  conservatively.

## Edge cases — finance math

- [x] **Division-by-zero across engine math.** `adjusted.py:150/152`,
  `covenants.py:209`, `capstructure.py:99`, `liquidity.py:52`, `peers.py:38`,
  `earnings.py:34`, `distress.py:36`. [edge]

  **🟢 correct-as-designed (all eight guarded).** The shared upstream guard is
  `cp1_leverage()` ([schemas.py:116-129](caos/server/engine/schemas.py)):
  `lev = float(lev) if isinstance(lev,(int,float)) and lev else None` — the `and
  lev` truthiness gate coerces `0`/`0.0` → `None`, making every `/lev` and
  `/ebitda` denominator provably non-zero. The rest guard locally: `adjusted`
  early-returns on `None` and `pct ∈ (0,1)` so `ebitda_excl ≠ 0`; `covenants`
  computes `pf_lev` only when `ebitda is not None`; `capstructure`
  `pct_of_structure` gated `if total and …`; `liquidity` returns `(None,None)
  if not cash_interest`; `peers` `_percentile` skipped on empty `peer_vals`
  ([peers.py:121](caos/server/engine/peers.py)); `earnings` `if not prev: return
  None`; `distress` returns `None if total_assets<=0 or total_liabilities<=0`.
  No fix. (Note: closes the *zero* case; the NaN/Inf case is F3.)

- [x] **`0.0`-as-falsy masks valid zero-debt cases.**
  [covenants.py:199](caos/server/engine/covenants.py) — a legitimate `0.0`
  (zero net debt) treated as missing. [logic]

  **🟡 real gap, bounded.** Confirmed: `cp1_leverage`
  ([schemas.py:127-128](caos/server/engine/schemas.py)) and
  `covenants.py:199` (`(nd/lev) if (lev and nd) else None`) use truthiness, not
  `is not None`. A genuine zero-net-debt issuer (`net_debt_ltm == 0`, a real
  credit state) has `nd` coerced to `None`, so headroom math degrades to "CP-1
  did not provide net leverage" — a valid datum read as missing. Bounded:
  zero-net-debt is uncommon in leveraged finance and the failure is conservative
  (degrade-to-insufficient, never a wrong number). Same falsy pattern at
  `liquidity.py:50`, `peers.py:49` (all bounded); `distress.py` correctly uses
  `<= 0`. **Fix:** distinguish absent from zero at the `cp1_leverage` boundary
  and add an explicit non-zero check at each division site.

- [x] **NaN/Inf propagate through `round()`.** `downside.py:36`
  (`lev/(1-s)`); `ScenarioPanel.tsx:114` (Infinity rendered). [edge]

  **🟡 real gap, bounded.** The denominator `(1-s)` is safe — `s ∈ {0.10,0.20,
  0.30}` hardcoded, never 1.0 ([downside.py:18](caos/server/engine/downside.py)).
  The exposure is the *inputs*: `lev`/`cov` are read with only an `isinstance`
  check, no `math.isfinite` ([downside.py:29-31](caos/server/engine/downside.py)),
  and `round(nan)→nan`, `round(inf)→inf` (don't raise with `ndigits`). They're
  guarded to finite on the deterministic CP-1 paths (`edgar_cp1`,
  `reported_cp1`), but the **live LLM CP-1** path takes `runtime_output` verbatim
  — `validate_payload` checks structure only, no numeric domain
  ([schemas.py:85-113](caos/server/engine/schemas.py)). If a non-finite slipped
  through it would persist (stdlib `json.dumps` permits NaN) then surface as a
  **late Starlette `allow_nan=False` 500** on serialize — a hard error, not a
  silent bad credit figure, but with no diagnostic of which value poisoned it.
  Low probability (the model API normally rejects bare `NaN` tokens). **Fix:**
  coerce non-finite numerics to `None` at `cp1_leverage`/`_payload_from_data`
  (`v if isinstance(v,(int,float)) and math.isfinite(v) else None`) — closes F2
  and F3 together at one boundary.

## Edge cases — frontend / hydration

- [x] **`window.innerWidth` + resize listener on mount.**
  `deepdive/page.tsx:98-136` — SSR hydration-mismatch risk; listener cleanup?
  [edge]

  **🟢 correct-as-designed.** No SSR mismatch: the `window.innerWidth` read sits
  inside a `useEffect` ([deepdive/page.tsx:126-139](caos/frontend/src/app/deepdive/page.tsx))
  which never runs during the static-export build-time prerender, so it can't
  desync prerendered HTML from first client render (the earlier :99-101 read is
  also effect-guarded + `typeof window` checked). The resize listener **is**
  removed on unmount — add/remove target the same stable `onResize` in an empty-
  deps effect ([deepdive/page.tsx:137-138](caos/frontend/src/app/deepdive/page.tsx)).
  No leak, no fix.

- [x] **localStorage-restored view state vs SSR markup.** `pipeline/page.tsx`
  restores `view` without a hydration guard. [edge]

  **🟢 correct-as-designed (cosmetic flash at most).** `view` initializes to the
  constant `"graph"` ([pipeline/page.tsx:36](caos/frontend/src/app/pipeline/page.tsx)),
  so prerendered HTML and first client render agree — no hydration mismatch. The
  localStorage restore runs post-hydration in a `useEffect` then `setView`
  ([pipeline/page.tsx:64-68](caos/frontend/src/app/pipeline/page.tsx)); the only
  artifact is a possible one-frame `graph→lanes` flash for returning users. The
  `viewHydrated` guard correctly prevents clobbering stored state with the
  default. No fix (gating render on `viewHydrated` trades flash for delayed
  paint — not worth it).

## System design / deploy / data integrity

- [x] **Migration ↔ ORM nullability drift.** `0005_run_tokens_used.py:22`
  vs model `nullable=False`; `0001_baseline.py:36` `Documents.issuer_id`. [migration]

  **🟢 correct-as-designed (premise wrong both ways).** Schema is created
  **only by Alembic** (`init_db` → `upgrade head`; no `create_all` anywhere), so
  migration DDL is ground truth and ORM `nullable=` is advisory. `0005` adds
  `tokens_used` with `server_default="0"` and the ORM is
  `mapped_column(Integer, default=0)` — **not** `nullable=False`
  ([0005:22](caos/server/migrations/versions/0005_run_tokens_used.py),
  [database.py:156](caos/server/database.py)) — they agree. `0001` explicitly
  sets `issuer_id ... nullable=False`
  ([0001:36](caos/server/migrations/versions/0001_baseline.py)) matching the ORM
  ([database.py:108](caos/server/database.py)). No drift of consequence; no fix.

- [x] **Partial-migration recovery path.** `_run_migrations`
  ([database.py:294](caos/server/database.py)) baseline-stamps; crash mid-init
  recovery? [migration]

  **🟢 correct-as-designed (Postgres).** Alembic runs each migration in a
  transaction ([env.py:48-53](caos/server/migrations/env.py)) and Postgres DDL
  is transactional — a mid-`upgrade` crash rolls back, leaving `alembic_version`
  at the last committed revision; restart resumes via idempotent `upgrade head`.
  The baseline-stamp branch fires only when `alembic_version` is absent *and*
  tables exist ([database.py:303-304](caos/server/database.py)), so it never
  double-stamps. Caveat: SQLite (dev-only) auto-commits some DDL so a mid-crash
  *can* strand a half-applied revision — but deploy is Postgres. No prod fix.

- [x] **Healthcheck doesn't gate on migration completion.**
  app depends on `db: service_healthy`, but `/api/health` may not verify DB /
  migrations. [deploy]

  **🟡 real gap, bounded.** `/api/health` is liveness-only — returns
  `{"status":"ok"}` with no DB touch
  ([routes/health.py:17-23](caos/server/routes/health.py)). **But migrations *do*
  gate traffic today**: `init_db()` runs inside the FastAPI lifespan *before*
  `yield` ([main.py:54](caos/server/main.py)), and uvicorn doesn't accept
  connections until lifespan startup returns. The gap is that health reports "ok"
  even if the DB later drops, or if a future change moved init after first-accept.
  **Fix:** add a cached `SELECT 1` to `/api/health` so the probe reflects real
  readiness, not just process liveness.

- [x] **`DATABASE_URL` relative path → silent new empty DB.**
  [config.py:30](caos/server/config.py) — changed CWD creates a fresh DB. [data-loss]

  **🟢 correct-as-designed (premise wrong).** The default SQLite URL is anchored
  to an **absolute** path from the source-file location, not CWD: `SERVER_DIR =
  Path(__file__).resolve().parent` then
  `sqlite+aiosqlite:///{SERVER_DIR/'data'/'caos.db'}`
  ([config.py:20,30](caos/server/config.py)) — a changed CWD can't repoint it.
  Prod sets an explicit absolute Postgres `DATABASE_URL` in compose. No current
  path triggers the risk; no fix (a hand-set *relative* URL would reintroduce it
  — could guard by rejecting relative SQLite paths).

- [x] **Backups can silently rot.** named volume (lost on teardown) + script
  continues on `pg_dump` failure (`|| echo …`). [data-loss]

  **🔴 bug.** Confirmed in `caos/deploy/backup.sh`: (1) `pg_dump -Fc -f
  /backups/caos-db-$ts.dump` opens the output file before streaming, so a failed
  dump leaves a 0-byte/truncated file matching the rotation glob; (2)
  failure is swallowed (`if pg_dump … else echo "…FAILED" >&2`, no `exit`,
  no removal — [backup.sh:23-28](caos/deploy/backup.sh)); (3) rotation runs
  **unconditionally** afterward, keeping newest `$KEEP` by mtime regardless of
  validity ([backup.sh:35-36](caos/deploy/backup.sh)). So failed nights write
  `$KEEP` junk dumps that evict every good one, signalled only to stderr. Target
  is a **named volume** (host-only, [docker-compose.yml:144](caos/deploy/docker-compose.yml)).
  **Fix:** on failure `rm -f` the partial and skip rotation that cycle (rotate
  only after `[ -s file ]`); surface failures off-box.

- [x] **Static-bundle staleness / divergence.** `out/` vs `server/static/`;
  `StaticFiles(html=True)` ([main.py:196](caos/server/main.py)) no
  `Cache-Control`. [deploy]

  **🟡 real gap, bounded (divergence impossible; caching real).**
  `caos/server/static/` is **gitignored and uncommitted**, and the Dockerfile
  rebuilds the export fresh and copies it
  ([Dockerfile:13,38](caos/deploy/Dockerfile)) — there's no committed bundle to
  go stale, so (D6/D10) divergence can't happen. **The real gap is caching:**
  the mount sets no `Cache-Control` and the security middleware adds none
  ([main.py:108-121,196-198](caos/server/main.py)), so a browser/proxy may serve
  a stale `index.html` pointing at a hashed chunk that no longer exists after
  redeploy → white screen until hard refresh. **Fix:** `Cache-Control: public,
  max-age=31536000, immutable` for `/_next/static/*`, `no-cache` for HTML.

- [x] **SQLite pragma gating is string-fragile.**
  [database.py:49](caos/server/database.py) — pragmas only fire on
  `startswith("sqlite")`. [config]

  **🟢 correct-as-designed.** Canonical URLs are lowercase and start with
  `sqlite` (`sqlite+aiosqlite:///…`, [config.py:30](caos/server/config.py)) /
  `postgresql+asyncpg://…`; `startswith("sqlite")` matches the dialect+driver
  form and correctly skips Postgres. SQLAlchemy requires lowercase dialect
  tokens, so an uppercase `SQLITE://` isn't a reachable form. Same correct prefix
  guards the pragma, the parent-dir `mkdir`, and the WAL listener. No fix.

- [x] **`metric_facts` lacks a `run_id`-only index.**
  `0003_metric_facts.py:40` — `run_id` only inside a composite unique. [db]

  **🟡 real gap, bounded (latent).** Confirmed: only
  `ix_metric_facts_issuer_id` + `uq_fact(issuer_id, run_id, metric_key, period)`
  ([0003:40-42](caos/server/migrations/versions/0003_metric_facts.py)); the
  composite leads with `issuer_id` so a `run_id`-alone filter can't use it. But
  the hot retention delete leads with `issuer_id` (covered), and the querygraph
  joins are driven from `Run` (PK side) with `headline` filters — so **no query
  filters by `run_id` alone on a large table today**. Latent scalability gap, not
  a current hot-path miss. **Fix (low priority):** `CREATE INDEX
  ix_metric_facts_run_id ON metric_facts(run_id)` if run-scoped reads grow.

- [x] **Image / dependency pinning gaps.** oauth2-proxy pinned by tag not
  digest; `markitdown[pdf]` unpinned. [deploy]

  **🟡 real gap, bounded.** (a) All service/base images use mutable tags
  (`oauth2-proxy:v7.15.2`, `postgres:16-alpine`, `caddy:2-alpine`,
  `node:20-slim`, `python:3.11-slim`) — a rebuild can pull a re-tagged image;
  not reproducible, though CI rebuilds+scans. (b) `markitdown[pdf]` is installed
  unpinned *after* `requirements.txt` with no constraints file
  ([Dockerfile:27,34](caos/deploy/Dockerfile)). It can't pull a vulnerable
  starlette (markitdown doesn't depend on fastapi/starlette; the `fastapi==0.138.*`
  pin floors the transitive starlette), but it **can** silently upgrade a
  *shared* transitive (`requests`/`anyio`/etc.) past the resolved set, and
  CI pip-audit only scans `requirements.txt`. **Fix:** pin
  `markitdown[pdf]==x.y.z -c requirements.txt`; pin images by `@sha256:` digest.

- [x] **CI doesn't commit `out/` but a stale `server/static/` could ship.**
  `.github/workflows/ci.yml`. [ci]

  **🟢 correct-as-designed.** `caos/server/static/` is gitignored/uncommitted,
  and CI rebuilds the frontend from source in both the image job
  ([ci.yml:127-134](.github/workflows/ci.yml) → Dockerfile `npm run build`) and
  E2E (`build_frontend.sh`) — no staged bundle to diverge. Full gate enforced:
  frontend lint+typecheck+test+build, server pytest on SQLite **and** Postgres,
  Docker build, fallow dead-code gate, corpus taxonomy check, and a security job
  (pip-audit + bandit + npm audit + gitleaks). A broken build fails the
  `frontend`/`e2e`/`image` jobs → blocks merge. **Residual (orthogonal):** CI
  never lints the deploy assets (no `shellcheck backup.sh`, no `docker compose
  config`), so the D5 backup bug and D9 digest gaps wouldn't be caught — worth a
  small CI addition.
