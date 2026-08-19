# Adversarial Review run-2 — Whole codebase, all lenses

Two staggered multi-agent workflows (backend + frontend), critic→advocate→judge.
**20 findings, every one survived adversarial rebuttal** (1 frontend finding
overturned by the advocate, kept visible). No code changed by the review.
Detail: [findings-backend.md](findings-backend.md) · [findings-frontend.md](findings-frontend.md).

Run cost: 31 agents, ~2.2M subagent tokens, ~44 min wall. No token-cap trip
(staggered 2 lenses / 2 verifiers at a time — the run-1 lesson held).

## Status (post-fix, commit f90dfae)

**Engine batch FIXED + tested** (full server suite 563 passed / 3 skipped):
B2+B3 (edgar per-leg net-debt freshness), B4+B5 + the full `year()→sort_key`
sweep (earnings, peers, **and a third callsite** querygraph:548), B6 (identity
cookie-sig bytes compare), B9+B10 (import-time registry acyclicity / dangling-dep
self-check).

**Frontend batch FIXED + verified** (commit c60a484; tsc + eslint clean, frontend
vitest 204 passed): F2 (Credit Snapshot tied to canonical 3,270, new
`builders.test`), F1 (sub-subtotal own multiple), FA1 (lineage-row keyboard
operability via `onActivate`), FR1 (`useLatestRun` synchronous reset on issuer change).

**DEFER hardening FIXED** (commit 5a0167f; backend 563 passed, frontend tsc/lint
clean + vitest 204): B8 (debate CP-2F KeyError guard), B12 (edgar redirect-host
SSRF defense), FR2 (query-page request-sequence guard), B7 (run_executor docstring).
B9/B10 (planner cycle / dangling dep) were already closed by the registry
import-time self-check in f90dfae.

**Deliberately left (not churn-worth fixing):**
- **B1** `liquidity.py:124` — your live WIP, yours to fix (one line: drop the
  `Maturity wall` row from the `disclosed_liquidity` sum).
- **B11** `reported_cp1.py:45` (SPEC — no captured case; a regex tweak here risks
  churn without a demonstrated miss).
- **FA2** color-alone run-state `Dot` — real but best done as one pass on the shared
  `Dot` atom (add an aria/title state token), not a one-off.
- **FR3** `reports/page` restore-vs-edit race (SPEC — no timed repro).

## Top priorities across both surfaces (PROVEN unless noted)

| # | sev | tier | surface | file:line | defect |
|---|-----|------|---------|-----------|--------|
| B2 | **HIGH** | PROVEN | engine | `edgar_cp1.py:217` | Net debt sums 3 independently-dated XBRL legs; freshness gate checks only the LT-debt leg → **18x leverage labelled "FY2025"** vs true ~3x. |
| F2 | **HIGH** | PROVEN | frontend | `lib/reports/builders.ts:129` | Committee tear-sheet prints **seeded** tranche dollars (Total 2,575) contradicting canonical 3,270 under real facility names; equity overstated ~$695M. `applyAnchor` leaves the debt stack seeded even on a live run. |
| B3 | MED | PROVEN | engine | `edgar_cp1.py:218` | Cash leg has no freshness gate → stale cash **understates** leverage (risk-looks-safe). 0.2x vs ~2.0x in repro. |
| B1 | MED | PROVEN | engine ⚠️ | `liquidity.py:124` | **(your live WIP)** Maturity wall summed into `disclosed_liquidity` → inflates headline + interest runway (1300 vs 500; 156mo vs 60mo). |
| B4 | MED | PROVEN | engine | `earnings.py:41` | `sorted(set,key=year)` same-year tie → set-hash order → **spurious YoY decline**. |
| B5 | MED | PROVEN | engine | `peers.py:52` | `max(key=year)` picks stale closed-FY margin over live LTM → skews peer percentile. |
| F1 | MED | PROVEN | frontend | `lib/reports/builders.ts:168` | Sub-subtotal row's Multiple uses `xm(tdebt)`=6.67x (total leverage) not `xm(sub)`=0.52x. One-token fix. |
| FR1 | MED | ARGUED | frontend | `lib/engine/useLatestRun.ts:19` | No reset-to-loading on `issuerId` change → Deep-Dive bleeds prior issuer's live run under new chrome. Chat was fixed, main surface left. |
| FA1 | MED | PROVEN | frontend | `components/pipeline/views.tsx:335` | CP-5B lineage rows are click-only `<div>`s — keyboard-inoperable (WCAG 2.1.1); axe can't catch it. |
| B6 | LOW | PROVEN | engine | `identity.py:88` | `hmac.compare_digest` on `str` → TypeError 500 on a non-ASCII cookie-sig byte. |

**Deferred (lower / conditional):** planner cycle + dangling-dep guards (B9/B10),
debate CP-2F KeyError (B8), reported_cp1 leverage-vs-covenant pattern (B11), edgar
redirect SSRF (B12, no open redirect found), run_executor stale docstring (B7),
query-page out-of-order graph (FR2), color-alone run-state Dot (FA2), reports-page
restore race (FR3).

## Systemic theme — the run-1 `sort_key` fix is incomplete

Run-1 fixed `periods.latest()` + `metrics._headline_period`, but **other callsites
still call `year()` directly**: `earnings.py:41` (B4), `peers.py:52` (B5) — and
per the `periods.py` docstring, `liquidity`, `capstructure`, `macro` are also
`year()`-ordered consumers. **Action: grep every `year(`/`key=year` callsite and
route each through `periods.sort_key`.** One sweep closes B4/B5 and prevents the
next.

A second systemic gap: the module **registry has no acyclicity / dangling-dep
self-check** (B9/B10), unlike `querygraph.py:949-954` which does. A startup/CI
assertion would convert both latent gaps into loud failures.

## Consolidated coverage gaps (untested critical paths)

1. EDGAR per-leg net-debt freshness — no multi-year-leg fixture (B2/B3). **Highest.**
2. Same-year FY/LTM ordering in `earnings`/`peers` (B4/B5).
3. Liquidity source-type exclusion of the maturity wall (B1).
4. Report Studio cap-structure tranche dollars / leverage — `model.test.ts` asserts none (F1/F2).
5. Deep-Dive cross-issuer in-place nav reset (FR1); keyboard-operability of click-div rows (FA1).
6. Registry acyclicity / dangling-dep self-check (B9/B10).

## Proposed fix plan

**Safe to fix now (NOT your WIP):**
- **A. Engine domain (highest value):** B2+B3 edgar freshness gates (one pass on
  `edgar_cp1.py`, mirror the existing `bs_stale` pattern); B4+B5 + the full
  `year()→sort_key` sweep; B6 identity cookie (`compare_digest` on bytes / guard).
  Each with a regression test.
- **B. Frontend:** F2 anchor the cap-structure debt to canonical (or correct the
  seed) — HIGH, committee-facing; F1 `xm(tdebt)→xm(sub)` (trivial); FA1 keyboard
  rows via the existing `onActivate` helper; FR1 synchronous reset-to-loading.

**Yours to fix (live WIP — I won't touch):**
- **B1** `liquidity.py:124` — exclude the `Maturity wall` row from the
  `disclosed_liquidity` sum. You have the file open; the contract test
  `test_interest_runway_contract.py` won't break (it tests the helper in isolation).

**Defer:** the DEFER list above, plus the registry self-check (small, do with A).
