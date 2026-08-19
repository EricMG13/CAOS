# Security, Concurrency & Data-Integrity Audit — Execution Context for Fable 5

> **What this file is.** A self-contained context pack. You (Fable 5) are the **Principal Security Architect** of this application — you own the systemic-risk map and the remediation plan. Read this whole file, then own the mission below. Everything you need — the objective, the governing security law, the *measured* baseline (already run for you, §2d), the exact detector commands, the real auth/session/concurrency map, a proven output shape, and a self-check protocol — is here. You are not filling in a template; you are deciding what this application's risk posture must become before it holds enterprise financial data under concurrent multi-user load. Do **not** write application code — your deliverable is a Markdown triage specification that **Opus 4.8** executes.
>
> **Repo root:** `/home/user/Credit-Operating-System` (local: `/Users/ericguei/Claude/Projects/Credit Operating System`)
> **Source under audit:** `caos/frontend/src/` (Next.js 15 / React 19, ~224 files) **and** `caos/server/` (FastAPI, ~146 files). The raw prompt's "`/src`" resolves to **both** — the risk vectors span them.
> **Write your spec to:** `caos/docs/SECURITY_IMPLEMENTATION_SPEC.md`

---

## 0. The Mission

**Outcome you own:** a determination, defensible to a security review board, of whether CAOS can process enterprise-grade financial data under concurrent multi-user load **without silent failures, memory leaks, or data cross-contamination between user sessions** — plus the exact, sequenced remediation plan that closes every gap you find. Everything below serves that one outcome.

CAOS is an institutional leveraged-finance credit platform: analysts push real financial data (EDGAR filings, extracted fundamentals, model outputs) through an extraction-and-analysis pipeline, and money rides on a correct read. Your job is to map the systemic risk surface against three vectors and specify the fixes:

1. **Concurrency & State** — race conditions, unhandled async promise rejections, and global-state mutations that leak request-scoped data across callers or corrupt under concurrency.
2. **Data Integrity** — missing validation boundaries where malformed or hostile financial data crashes or silently poisons the extraction pipeline.
3. **Silent Failures** — swallowed exceptions and missing error-boundary fallbacks that turn a failure into a wrong-but-quiet result.

**Your authority is full, inside four fixed posts.** You decide severity, sequencing, and the exact patch each finding needs. You do **not** get to move these four, and every finding must survive them:

- **The single-team authorization model is BY DESIGN, not a bug (governing law §1 below, `SECURITY.md` S-4).** Every authenticated analyst can read and write every issuer, run, and document; there is intentionally no row-level or per-issuer authorization. **Do not flag missing ACLs, missing tenant scoping, or "analyst X can see analyst Y's issuer" as a vulnerability.** "Cross-contamination between user sessions" means something narrower and real: **process-global state that leaks one request's data into another's response, or races under concurrent requests** — regardless of authorization. Hold that distinction on every concurrency finding.
- **Documented-intentional swallows are not silent failures.** `SECURITY.md` §4 states document parsing (`ingest.py`, pypdf/openpyxl) is deliberately best-effort exception-swallowing so hostile/scanned files vault without crashing. Do not flag that. A swallow is a finding only where discarding the error produces a *silently wrong financial read* or hides data corruption.
- **Standard language/framework behavior is not a bug.** Do not flag the Python GIL, per-request FastAPI dependency scoping, React StrictMode double-invocation, awaited promises that have a handler, or effects that correctly return cleanup. Precision over volume.
- **Assess, don't fix.** The deliverable is the triage spec. Do not modify application source. The only file you write is the spec.

**Deliverable.** A single Markdown spec Opus 4.8 executes top-to-bottom, **grouped strictly by execution severity (Critical → High → Medium)**. Each item states the failure in one sentence, points at real files and named functional blocks (**never guessed line numbers**), gives Opus an explicit technical patch instruction, and names the STRIDE lens plus the data-integrity payoff it serves. §6 gives the item shape; §7 the self-check. Run the self-check as you go.

---

## 0.1 How to work — operating guide (written for how Fable 5 performs best)

Read this before you start.

- **Decide, don't survey.** You have the goal, the governing law, the measured baseline, and the map. When you have enough to rule on a finding, rule on it — assign the tier and write the patch instruction. Give a recommendation, not an exhaustive list of options. Re-deriving what this file establishes, or re-litigating a settled boundary (the single-team model), is wasted motion.
- **Start at the hardest surface.** The concurrency/global-state vector in `caos/server/engine/` and the extraction-pipeline data-integrity vector are where the real risk lives and where a wrong read costs money — scope them first; the frontend async/leak vector follows the pattern you set. The auth/session layer is already largely hardened (§2d) — confirm, don't re-litigate it.
- **Ground every claim in evidence.** Before asserting a file contains a race, a swallow, or an unguarded divide, point to the code — a path plus the named block. A finding you did not read in the source is a defect, not a finding. The §2d baseline was produced this way; hold your own additions to the same bar.
- **Prefer confirming a real failure state over pattern-matching.** For each candidate, state the concrete trigger: the inputs/state and the wrong output, crash, or cross-request leak. If you cannot name the trigger, it is not yet a finding.
- **Keep a working-memory file.** As you audit, record decisions and rejected candidates with their reason in a short `caos/docs/.security-spec-notes.md` — which findings you tiered where and why, which candidates you dropped as by-design or standard-behavior. It keeps the spec internally consistent across ~380 files and gives your checkpoints something to audit against.
- **Delegate verification to fresh-context sub-agents, and keep working while they run.** Your self-check (§7) is strongest when a separate agent that has not seen your reasoning audits it — fresh eyes catch hallucinated paths and by-design behavior rationalized as a bug. Fan these out asynchronously at each checkpoint; don't block on the slowest.
- **De-prescription is deliberate.** This file gives you the goal, the law, the baseline, and the map — not a step list. Fill the gaps with judgment; that is the job.

---

## 1. Governing security law (from `caos/docs/SECURITY.md` — authoritative, condensed)

This is the design law Opus must obey and the boundary of the threat model. Every finding is measured against it.

**Authentication (two layers).** Every request is authenticated at the edge by **oauth2-proxy** (Google Workspace OIDC) behind **Caddy** (TLS); the verified identity arrives as forwarded headers (`X-Forwarded-User/-Email/-Preferred-Username`). On top, each analyst holds a **code-gated in-app profile** (`routes/auth.py`), surfaced by `identity.py` at `/api/auth/me`. The profile rides a `caos_analyst` cookie signed HMAC-SHA256 with `SESSION_SECRET`; **production refuses to start** if the secret, the edge secret, or the signup code is unset/default, or if demo-seed is on (`main.py` boot guards).

**Fail-closed gate.** `identity.py` rejects (401) a request with no profile cookie and no identity headers whenever `ENVIRONMENT != development` (`config.is_deployed`) — a typo/unset value fails closed; the Docker stack bakes in `ENVIRONMENT=production`.

**Trusted-header assumption (S-3).** In production the app trusts `X-Forwarded-*`, safe **only because the auth proxy is the sole network path** — Caddy strips client-supplied headers and the app publishes no directly-reachable port. Never publish the app port. This is a documented assumption, not a finding.

**Single-team model (S-4) — BY DESIGN.** No row-level / per-issuer authorization; every analyst reads/writes everything. Explicit non-goal, not an oversight.

**Input handling.** Uploads (`ingest.py`): incremental `MAX_UPLOAD_MB` cap (250), magic-byte MIME sniff, path-traversal-safe UUID storage, `run_mode` allow-list, optional ClamAV that **fails closed** if configured-but-unreachable. Document parsing is **intentionally** best-effort exception-swallowing. `contentEditable` report editing sanitizes paste to plain text; React escapes rendered text.

**Response headers** (`main.py` middleware, every response): CSP `default-src 'self'` (+ `'unsafe-inline'` for script/style — a static export cannot carry a per-request nonce), `object-src 'none'`, `nosniff`, `Referrer-Policy`, HSTS.

**Explicit non-goals today (§8):** multi-tenant isolation, per-issuer authorization, rate-limiting beyond the upload cap and the per-IP access-code throttle. A finding that reduces to one of these is out of scope — note it as a documented boundary, do not tier it.

---

## 2. The rubric and the measured baseline

### 2a. Lenses (how to classify and score each finding)
Use **STRIDE** to name the failure class and **DREAD** to defend the tier:
- **S**poofing→authn · **T**ampering→integrity · **R**epudiation→audit trail · **I**nfo-disclosure→access/leak · **D**oS→availability/exhaustion · **E**levation→privilege.
- DREAD (Damage, Reproducibility, Exploitability, Affected users, Discoverability, each 1–10): a finding averaging ≥7 is Critical/High and needs a named patch owner. OWASP Top 10 / ASVS via the `owasp-security` skill is the code-level companion for injection/validation items.

For this audit the dominant lenses are **Tampering** (data integrity — a silently wrong financial read) and **DoS/Info-disclosure** (concurrency — a leak or a resource exhaustion under load), not Spoofing/Elevation (the authn layer is hardened — §2d).

### 2b. Detectors (run these directly; cite their output)
- `python3 run_sec_audit.py` — **⚠ KNOWN-BROKEN, see §2d finding SEC-TOOL-1. Do not treat its empty output as a pass.**
- `pip-audit -r caos/server/requirements.txt` — Python dependency CVEs (OSV).
- `bandit -r caos/server caos/scripts --severity-level high --confidence-level medium` — Python SAST (the CI gate; note the one High is a documented false positive, §2d).
- `pytest` under `caos/server/` — server suite (currently red on `main`; see §2d).
- Frontend: `npm run -w caos/frontend lint && npx -w caos/frontend tsc --noEmit` for the TS/async surface. These are your objective, reproducible signals — cite file + rule.

### 2c. Governing baseline docs
`caos/docs/qa/REVIEW_MATRIX_SECURITY.md` is the **prior** measured baseline — but it covered **route endpoints only** (16 `routes/*.py` files). `engine/`, the extraction pipeline, and the **entire frontend** were never scored. Those are your un-scored surfaces: audit them fresh, they are where the deficit concentrates.

### 2d. MEASURED BASELINE (already run for you — 2026-07-08)

Detectors and four fresh-context inventory sweeps were run across `caos/server/` and `caos/frontend/src/` before this brief was written. **Use these as your starting findings; verify each against the current tree before you tier it, and re-run the detector on any surface you touch.** Headline: **the authentication/session layer is hardened and the route-authz layer is clean; the real risk lives in server concurrency edge-cases, the un-scored extraction-pipeline data-integrity boundary, the frontend async/leak surface, and — most urgently — a security *gate* that is silently dead.**

**Prior route-matrix findings, re-verified against the live tree:**

| Prior finding | Status now | Evidence |
|---|---|---|
| HIGH `auth.py:~176` `create_profile` edge-SSO bypass | **FIXED** — do not re-tier | Now closed by an inline forwarded-header presence gate in `create_profile`, the `edge_origin_guard` middleware (`main.py`), and the boot guards requiring `EDGE_PROXY_SECRET`. SSO branch keys `Analyst` strictly by verified email; name collision → 409, so no impersonation. |
| MED `query.py:~361` `list_accepted_links` blanket table scan | **PRESENT, but informational** | Unfiltered `select(QueryAcceptedLink).limit(1000)`, no caller/scope filter. Under the single-team model accepted links are shared desk work product, so this is by-design sharing, not a confidentiality gap. Tier at most Medium/informational; the real defect is the absence of a scope filter *should multi-tenancy ever land* — note it, don't inflate it. |

**Newly measured findings (starting anchors — verify, then tier):**

- **SEC-TOOL-1 (elevate this):** `run_sec_audit.py` is **silently non-functional**. It gates on `isinstance(node, ast.FunctionDef)`, but every CAOS route handler is `async def`, which `ast` represents as `ast.AsyncFunctionDef` — a distinct type `FunctionDef` never matches. The detector inspects **zero** handlers and always returns `[]`, giving false-green assurance that routes are auth-covered. (Compounding: line ~28 checks `Depends` as an annotation when it is the parameter default; line ~32's `'auth' not in route` substring-excludes any path containing "auth".) A dead security gate that reports success is itself a finding. *(Manual cross-check confirmed the underlying coverage is actually fine — every route has `get_identity` except the intentional pre-auth/health endpoints — so the fix is the detector, not the routes.)*

**Server concurrency & global state** — *most module-global state is correctly keyed/guarded (`rate_limit._windows` under a `threading.Lock`), or request-scoped via ContextVars (`engine/presets.py` model mode); genuinely user-scoped caches (Desk Brief, query answers) are DB-backed keyed by `analyst_id`. There is no naive cross-request content leak in the server.* The real items:
- **CONC-1 (High/Med):** `main.py` lifespan → `asyncio.create_task(run_warmup())` retains no reference to the task, so Python may garbage-collect it mid-flight and cancel the embeddings warmup. Exceptions are caught inside, so this is reliability, not a crash. Patch: hold the task in `app.state` (or a module-level set with an `add_done_callback` discard), matching the executor pattern already used elsewhere.
- **CONC-2 (Med):** `engine/locks.py::release_advisory_lock` swallows the unlock exception (`except Exception: pass`); a failed release leaves a **session-level** Postgres advisory lock held on a pooled connection (the pool's reset-on-return `ROLLBACK` does not drop session-level advisory locks), transiently stranding the single-flight lane until the connection is recycled. Patch: on release failure, invalidate/close the connection so auto-release fires, and log rather than swallow.
- **CONC-3 (Low, documented):** `engine/queryinsights.py` `_regen_inflight`/`_regen_tasks` single-flight is **single-worker-scoped** — under a multi-worker deploy the Desk-Brief regen dedup does not coordinate (duplicate regenerations), whereas the autonomy path already routes through the `advisory_lock` primitive. Patch (only if multi-worker is a target): route regen single-flight through `advisory_lock`.

**Server data integrity & silent failures** — **⚠ THIS VECTOR IS ESSENTIALLY CLEAN. Do not manufacture findings here.** A full read of the extraction pipeline and every CP arithmetic module found **0 confirmed swallowed-exception wrong-reads, 0 missing validation boundaries, and 0 unguarded CP-1 divides/multiplies.** The `is_finite_number` convention (`engine/periods.py:70`) is rigorously enforced across `adjusted`, `capstructure`, `liquidity`, `distress`, `downside`, `macro`, `metrics`, `peers`, `metricengine`, `covenants`, `portfolio`, `anomaly`; extraction boundaries validate (`edgar_cp1._annual_series` gates raw XBRL values that a JSON decoder can emit as `NaN`/`Infinity`; `portfolio_ingest._num` rejects `NaN`/`inf`; `reported_cp1` range-bounds extracted leverage; `ingest.py` size-caps + magic-byte-sniffs; `edgar.py` SSRF-validates host/scheme). The only items:
- **DATA-1 (Low — the one real item):** `engine/queryinsights.py::_delta_entries` reads `MetricFact.value` directly for a subtract-and-format without the `is_finite_number` re-guard its sibling `engine/metricengine.py::_delta_entries` applies (and labels as the CLAUDE.md convention). Values are finite at write time (`metrics.add`), so a smuggled `NaN` would render the literal text "nan" in the Desk Brief — a defensive-consistency gap, not a confirmed wrong read, and a subtraction not a divide. Patch: mirror the sibling's finite re-guard.
- **DATA-2 (Informational, latent):** `edgar.py::search` — a single non-numeric CIK in an EFTS result raises `EdgarError` and aborts the whole batch (caught → 502). EDGAR always returns numeric CIKs, so this is latent, not live. Patch: skip the malformed hit instead of failing the batch.

**Frontend async, leaks, silent failures, error boundaries** — *the frontend is unusually disciplined: most effects return correct cleanup and most `api.ts` callers have real handlers (the `lib/engine/*` "prefer live, static fallback" catches are by-design degrades, not swallows). There are **no** module-level data caches in `lib/`.* The real items:
- **FE-1 (Critical/High — this is the prompt's core "cross-session contamination", and it is real):** roughly six `localStorage`/`sessionStorage` families holding analyst/issuer-scoped work product are **never cleared on `caos:auth-lost` or sign-out** — `AuthProvider.tsx::onLost` and `AnalystBadge.tsx::signOut` only `refresh()`/`logout()`. On a shared browser the **next analyst sees the previous analyst's** issuer Q&A transcripts (`caos-chat-<runId>`, `components/deepdive/IssuerChat.tsx`), assembled report + query history (`REPORT_STORAGE_KEY` / `caos:query-history`, `app/query/page.tsx`), committee-report edits (`caos-e-edits`/`-omit`/`-active`/`-zoom`, `app/reports/page.tsx`), per-issuer model overrides (`caos-d-overrides:<issuerId>`, `app/model/page.tsx`), and saved assumptions (`lib/reports/assumptions.ts`). Patch: register a central handler that, on `caos:auth-lost` and explicit logout, purges the `caos-*` / `caos:*` key families from both storages.
- **FE-2 (High/Med):** `components/charts/G2Chart.tsx` — the dynamic `import("@antv/g2").then(...)` has **no `.catch`**; a chunk-load failure (stale deploy / network blip) throws an unhandled promise rejection and the chart silently never initializes. Patch: add a `.catch` that sets a chart error/empty state.
- **FE-3 (Med):** four `.catch(() => {})` swallows hide load failures with no user-visible error — `components/upload/UploadWizard.tsx` `getIssuers` (issuer picker silently empty), `app/query/page.tsx` `queryCapabilities` (×2, capability rail silently stale), `app/research/page.tsx` `getSettings` (`llm_configured` silently false → research reads as unavailable). Patch: surface a plain-language error/retry state instead of swallowing.
- **FE-4 (Med):** `app/query/page.tsx` `loadBrief` schedules a chained `setTimeout(..., 8000)` poll with no stored id, and the mount effect returns no cleanup — it refetches `queryInsights` and calls `setBrief`/`setBriefLoading` **after unmount** (bounded to ~4 hops via `briefPolls.current`, but still a leak). Patch: store the timer id and clear it in the effect cleanup; gate `setState` behind a mounted ref.
- **FE-5 (Low):** `components/shared/Notifications.tsx` toast auto-dismiss `setTimeout` is never captured/cleared (root-mounted, so effectively never unmounts). Patch: clear the timer in cleanup.
- **FE-6 (Med — silent-failure vector):** **all 14 route segments lack their own `error.tsx`** — only root `app/error.tsx` and `global-error.tsx` exist, so a render error in any one surface bubbles to the whole-app fallback rather than an in-place per-surface boundary. Patch: add a per-segment `error.tsx` (reusing the root's shape) for `command`, `deepdive`, `model`, `pipeline`, `reports`, `research`, `sector`, `sector-rv`, `query`, `issuers` (+ `issuers/profile`), `monitor`, `settings`, `upload`.

- **SAST noise:** `bandit` reports 1 High at `engine/locks.py:46` (`hashlib.sha1`, B324/CWE-327) — a **false positive**: SHA-1 is used as a non-cryptographic content hash to derive a stable int64 advisory-lock key (documented in the `locks.py` docstring). It fails the CI gate but is not a vulnerability. The clean fix is `usedforsecurity=False`; tier it Medium as *CI-hygiene*, not a security defect.

**STRATEGIC IMPLICATION (weight your spec accordingly — and note the codebase is markedly healthier than the raw prompt's hypothesis assumed):**
1. **Do not spend the spec on authn/authz** — it is hardened and the one open matrix item is by-design. A finding there is the exception, and must clear a high bar.
2. **Do not manufacture data-integrity findings.** The `is_finite_number` guard convention is rigorously enforced and the extraction boundaries validate (§ Server data integrity, above). The measured result is ~zero real defects in that vector. If you believe you have found an unguarded divide or a missing boundary, you are most likely looking at a guard you didn't read — re-read before you tier it. This is the single place the anti-hallucination discipline matters most.
3. **The genuine cross-session contamination is on the client, not the server.** FE-1 — analyst work product persisted in `localStorage`/`sessionStorage` and never cleared on logout — is the real instance of the prompt's core concern (a shared-browser leak), because the *server's* shared-data model is by-design single-team. This is likely your top item.
4. **Concentrate Critical/High on:** (a) FE-1, the client-storage cross-session leak; (b) SEC-TOOL-1, the dead security detector — a false-green gate is a systemic risk multiplier; (c) FE-2, the one genuine unhandled promise rejection; (d) CONC-1/CONC-2, the untracked warmup task and the stranded advisory-lock release. Everything else is Medium/Low.

---

## 3. Real architecture map (verified paths — use these, do not invent)

### Auth / session lifecycle (from `identity.py`, `main.py`, `routes/auth.py`, `config.py`, `engine/presets.py`)
Request → **`edge_origin_guard` middleware** (`main.py`, constant-time compares `X-Edge-Authorization` when deployed; 401 on mismatch; single chokepoint) → **`get_identity` dependency** (`identity.py`): re-checks edge secret, then resolves the `caos_analyst` HMAC cookie (`<b64>.<hmac-sha256>`, mandatory `exp`, `token_version` revocation check via one `db.get(Analyst, id)`, cross-user guard against `X-Forwarded-Email`), else falls back to sanitized `X-Forwarded-*` (`source="proxy"`), else **fail-closed 401** when deployed. Per-request state is a frozen `CallerIdentity` + per-request `AsyncSession`. **Model mode is carried in ContextVars (`engine/presets.py`), not module globals — request-scoped, no cross-request bleed.** No session/identity state lives in a module global.

### Concurrency / global-state surface (`caos/server/`)
Advisory locks `engine/locks.py` (Postgres `pg_try_advisory_lock`; SQLite fallback `_sqlite_held` module set — test dialect only); in-process rate limiter `rate_limit.py` (`_windows` keyed by caller/IP, `threading.Lock`); single-flight regen `engine/queryinsights.py` (`_regen_inflight`/`_regen_tasks`, single-worker-scoped); executors (`run_executor.py`, `research_executor.py`, `research_report_executor.py`, `engine/pipeline_executor.py` — all retain tasks + `add_done_callback`); lifespan warmup `main.py`. Genuinely user-scoped caches (Desk Brief, query answers) are **DB-backed, keyed by `analyst_id`** — not module globals.

### Extraction pipeline (data-integrity surface)
`edgar.py` / `routes/edgar.py` / `engine/edgar_cp1.py` (SEC ingest, `_TICKER_CACHE`) → `ingest.py` / `portfolio_ingest.py` (upload parse, intentionally swallowing) → `engine/factpack.py`, `metricengine.py`, `packer.py` (assembly) → `engine/periods.py::is_finite_number` (line 70 — the CP-1 numeric guard) and the CP-2*/CP-3* modules (`adjusted.py`, `capstructure.py`, `liquidity.py`, `distress.py`, `downside.py`) that must gate every divide/multiply through it.

### Frontend data seam (`caos/frontend/src/`)
Single API client `lib/api.ts` (~65 typed calls, attaches `X-Model-Mode`/`X-Query-Model`, fires `caos:auth-lost` on 401); live-engine hooks `lib/engine/*` (`useLiveRun`, `useLatestRun`, `useModelEngine`, `usePortfolio`) and `lib/pipeline/useLivePipeline` — all "prefer live, static fallback". Error surfaces: root `app/error.tsx`, `global-error.tsx`, `not-found.tsx` exist; per-surface `error.tsx` coverage is the open question (§ BASELINE-C).

---

## 4. Data-source / finding classification (know before you tier)

**Genuine findings** (tier these): process-global state leaking request-scoped *content* or racing; unguarded arithmetic on external/LLM-extracted financial figures; a swallow that yields a silently wrong number; an unhandled promise rejection that strands the UI in a false state; an undismissed observer/timer/listener leaking memory across navigations; a dead/false-green security gate.

**NOT findings** (note as boundary, do not tier): missing per-issuer/tenant authz (S-4 by design); intentional document-parse swallowing (§4 law); trusting `X-Forwarded-*` behind the sole-path proxy (S-3); the bandit SHA-1 false positive (non-crypto use); standard GIL/StrictMode/framework behavior; rate-limiting beyond the documented controls.

---

## 5. Output specification — how to write `SECURITY_IMPLEMENTATION_SPEC.md`

Produce ONE Markdown file, **grouped strictly by execution severity** so Opus works top-to-bottom. Use these groups, in order:

```
# CAOS Security & Data-Integrity Implementation Spec (for Opus 4.8)

## CRITICAL — silent-wrong-read / cross-request leak / dead security gate   (do first)
## HIGH — races & unhandled rejections that degrade correctness under concurrency; swallows on data paths
## MEDIUM — missing error boundaries, non-critical leaks, CI-hygiene, defensive gaps at real boundaries
```

Order items within a tier by blast radius. **Every item follows this shape — adapt it to the finding; it is a completeness floor, not a cage:**

```markdown
### [TIER] <Subsystem> — <Short title>
- **Failure state (1 sentence):** <concrete trigger → wrong output / crash / cross-request leak; no hedging>.
- **Location:** `caos/server/<...>.py` → <named function/class/block> (or `caos/frontend/src/<...>` → <component/hook>); NOT a guessed line number.
- **Lens:** STRIDE <S|T|R|I|D|E> + OWASP/ASVS ref if applicable; one line of why it clears the by-design boundaries in §1/§4.
- **Opus instruction (technical):** <exact imperative patch — the guard to add (e.g. gate through `engine.periods.is_finite_number` and return None on non-finite), the cleanup to return from the effect, the `.catch`/error-state to wire, the ContextVar/scoping change, the retained task-reference, the error-boundary component to add — and where>.
- **Integrity payoff (1 line):** <how this prevents a silent wrong read, a leak, or a crash under enterprise load>.
```

**Rules for the spec:**
- **Reuse before invent.** Extend existing guards/primitives (`is_finite_number`, the executor task-tracking pattern, ContextVars, the existing `error.tsx` shape); do not introduce a new dependency or pattern a few lines cover.
- **State logic is mandatory for silent-failure fixes.** Where you replace a swallow, specify what the caller does on the error (degrade to `None`, surface a typed error, log-and-reject) — never "just re-raise" without saying what catches it.
- **No line numbers.** Name the function, block, or component.
- **Tie every item to a lens and a payoff.** No lens or no payoff → cut it.
- **Respect the by-design boundaries (§1/§4).** If a finding reduces to a documented non-goal, note it as a boundary in an appendix, do not tier it.
- **Every item must be executable by Opus without re-deriving your analysis.**

---

## 6. Self-check protocol (verify as you go)

Establish a method for checking your own work **at an interval of every 5 files** as you audit. Treat that as the default cadence; resequence to fit the risk. At each interval, **dispatch a fresh-context verifier sub-agent** (general-purpose or Explore) — do not self-approve — with this charge:

> "Review the last 5 files' worth of candidate findings in `caos/docs/SECURITY_IMPLEMENTATION_SPEC.md` (`<file list>`). For each item verify: (1) **the file path and named block actually exist** in the tree — flag any hallucinated path or function; (2) the **failure state is reproducible from the code** — read the block and confirm the concrete trigger; reject anything you cannot reproduce; (3) it does **not** reduce to a documented by-design boundary — missing per-issuer/tenant authz (SECURITY.md S-4), intentional document-parse swallowing (§4), trusting `X-Forwarded-*` behind the sole-path proxy (S-3), or the bandit SHA-1 non-crypto false positive; (4) it is **not** standard language/framework behavior — GIL, per-request FastAPI deps, React StrictMode double-invoke, awaited promises with a handler, effects with correct cleanup; (5) the **STRIDE lens and tier are justified** (DREAD sanity-check). Return a table: item → PASS / REVISE (with the specific defect). Be adversarial; assume a finding is hallucinated or by-design until the code proves otherwise."

Dispatch verifiers asynchronously and keep auditing while they run; **reconcile every REVISE before you declare the spec done.** Record each check's verdict inline (`> Checkpoint N: X pass, Y revised — <what changed>`) so the audit trail is visible. Log how many candidates were proposed vs confirmed per interval — a high false-positive rate is a signal to tighten, not to pad.

**Anti-hallucination guardrails (apply continuously):**
- Before citing any file/function/block, confirm it exists (read it). A path you did not verify is a defect.
- Before tiering a finding, name the concrete failure trigger in one sentence. No trigger → cut it.
- Do not report a detector result you did not actually produce; if you reasoned from reading code without running the tool, say so.
- When in doubt between "bug" and "by-design," consult §1/§4 and default to *not a finding* unless the code proves a real failure state.

---

## 7. Definition of done

- `caos/docs/SECURITY_IMPLEMENTATION_SPEC.md` exists, severity-grouped Critical → High → Medium; every item carries the §5 fields that apply (failure · location · lens · instruction · payoff), adapted to the finding — gate on the *information* being present, not literal template conformance.
- Every path and named block is verified against the tree; every checkpoint verdict is recorded inline.
- No item reduces to a documented by-design boundary (§1/§4) or to standard language/framework behavior; any such candidate is noted as a boundary in an appendix, not tiered.
- Every Critical/High item names its STRIDE lens and a concrete failure trigger, and its patch instruction is executable by Opus **top-to-bottom without further clarification** — named blocks, not line numbers.
- The prior route-matrix findings are reconciled (the HIGH is confirmed FIXED and not re-tiered; the MED is tiered at most informational), and SEC-TOOL-1 (the dead detector) is addressed.

**Recommended effort:** run at `xhigh` — this is a wide, capability-sensitive analysis over ~380 files where a missed cross-request leak or a silently-wrong-read boundary is the expensive failure.

---

## 8. Prompt to hand to Fable 5 (copy-paste)

> I'm hardening CAOS — an institutional leveraged-finance credit platform where analysts push real financial data through an extraction-and-analysis pipeline and money rides on a correct read — for enterprise multi-user deployment. Read `.agent-reviews/src-security-audit-brief.md` in full first: it is your context pack — the governing security law, a measured baseline of findings already run for you (§2d), the verified auth/session/concurrency/pipeline map (§3), the exact detectors (§2b), and the by-design boundaries you must not flag (§1, §4). Own the mission in it.
>
> Act as the Principal Security Architect and audit the CAOS application source across both trees — `caos/frontend/src/` (Next.js 15 / React 19) and `caos/server/` (FastAPI) — against three vectors: (1) Concurrency & State — races, unhandled async promise rejections, and process-global state that leaks request-scoped data across callers; (2) Data Integrity — missing validation boundaries where malformed financial data crashes or silently poisons the extraction pipeline; (3) Silent Failures — swallowed exceptions and missing error-boundary fallbacks. Do not write or apply any fix; produce one Markdown triage specification at `caos/docs/SECURITY_IMPLEMENTATION_SPEC.md`, grouped strictly Critical → High → Medium so Opus 4.8 executes it top-to-bottom. Each item: the exact file path and named functional block (never a guessed line number), a one-sentence concrete failure state, its STRIDE lens, and an explicit technical patch instruction for Opus.
>
> Start from the measured baseline in §2d — verify each embedded finding against the current tree, then extend. Two hard constraints from the pack: the single-team authorization model and the intentional document-parse swallowing are BY DESIGN — do not flag them; and the data-integrity vector measured essentially clean (the `is_finite_number` convention is rigorously enforced), so do not manufacture findings there — if you think you found an unguarded divide, you are most likely looking at a guard you didn't read.
>
> Establish a method for checking your own work at an interval of every 5 files as you audit. Run this every 5-file interval, dispatching fresh-context verifier subagents with the charge in §6 — reject any finding that is hallucinated, unreproducible from the code, reduces to a documented by-design boundary, or flags standard language/framework behavior as a bug. Only confirmed findings enter the spec. You are operating autonomously — work through the read-and-write task without pausing, and end only when the triage spec is complete.

Run at effort `xhigh`.
