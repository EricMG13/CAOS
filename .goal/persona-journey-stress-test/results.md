# Persona Journey Stress Test — P3 Reproduction Gate

Nothing below entered this table unproven. Each candidate finding was re-run
from a clean stack/session before classification. WITHDRAWN entries are
**recorded, not deleted** — several plausible-looking defects did not survive
verification, and that is the point of the gate.

- **Date:** 2026-07-26 · **Branch:** `claude/multi-persona-stress-test-cgegcb` · **Base:** `341d14b`
- **Contract:** [contract.md](contract.md) (written before any journey ran)
- **Stacks:** p1 `:8010/:3010` · p2 `:8020/:3020` · p3 `:8030/:3030`, separate SQLite DB each, no `CAOS_DEMO_SEED`, no `*_facts.json` seeding.

## Gate table

| ID | Finding | Persona(s) | Reproduced? | Layer | Anchor | Verdict |
|---|---|---|---|---|---|---|
| F-01 | Directory offers per-row "Upload documents for *X*" on all 346 demo issuers; target wizard shows "0 registered" and never names the clicked issuer | p1, p3 | **Yes** — clean p3 stack, fresh DB, different issuer (`BCULC`) | frontend | `src/app/issuers/page.tsx` → `/upload` | **CONFIRMED** |
| F-02 | `document.title` identical on all 18 routes | p1, p2, p3 | **Yes** — 16/16 route loads across 3 personas | frontend | `src/app/layout.tsx:19`; `src/components/shared/RouteHeading.tsx:47` | **CONFIRMED** |
| F-03 | Transient UI placeholders persisted as durable analysis-context names | p1 | **Yes** — 2 polluted contexts in p1 DB | frontend→API | `src/app/deepdive/page.tsx:201-202` | **CONFIRMED** |
| F-04 | Frontend calls flag-gated `/freshness` endpoints unconditionally → 8×404 per issuer-profile load; all freshness reads "UNKNOWN" | p1, p2 | **Yes** — every profile load | frontend/contract | `src/lib/api.ts:468-472`; `config.py:80` | **CONFIRMED** |
| F-06 | Committed `qa2-backend` launch profile refuses to boot with its own env values | infra | **Yes** — booted verbatim on spare port | config/DX | `.claude/launch.json` (qa2-backend); guard `caos/server/config.py:392` | **CONFIRMED** |
| F-05 | `/monitor` first render ~14 s vs ~7–8 s for peer routes | p2, p3 | Observed both personas; **dev-server cold build not isolated** | frontend | `/monitor` | **PLAUSIBLE** (not confirmed as product defect) |

### Withdrawn (recorded, not deleted)

| ID | Candidate | Why it did not survive |
|---|---|---|
| W-01 | "346 sample issuers" is an unlabelled mock count | It **is** labelled — "Demo coverage" badge + tooltip *"No live coverage yet — these are sample issuers, not real coverage"* (`src/app/issuers/page.tsx:306,341-343`). Honest. |
| W-02 | Portfolio-creation referral is a dead end | `/portfolios` → "Open Settings" deep-links to `/settings?tab=portfolios` with a working create form and a clear disabled-state hint ("Enter a portfolio name first"). Correct workflow. |
| W-03 | Analysis contexts churn on every navigation | Contexts are **one per surface and reused** (5 surfaces → 5 contexts on both p1 and p3). Hypothesis wrong. |
| W-04 | Infinite "Verifying your CAOS session" spinner | Caused by **my own** cross-origin misconfiguration (page on `127.0.0.1:3010`, API pointed at `localhost:8010`). Not reproducible under correct config. Retained as a note — an unreachable API yields an unbounded spinner with no surfaced error — but not charged as a product defect on this evidence. |
| W-05 | UI declares a run complete while CP-0 is "not ready" | Backend correctly returns `qa_status=Restricted`, `committee_status=Restricted`, 4 MATERIAL + 2 MINOR findings; UI surfaces "0 crit · 4 mat" and per-metric FABRICATED badges. "Completed and ready to review" ≠ committee-ready. No defect. |

## Invariants verified as PASSING

These are recorded because a stress test that reports only failures misrepresents
the system.

| ID | Verdict | Evidence |
|---|---|---|
| **I6 provenance honesty** | **STRONG PASS** | Every KPI on the issuer profile is badged **FABRICATED / FAB** with *"Source unavailable · No persisted document chunk for this metric."* CP-1 `limitation_flags` state verbatim: *"Financials are synthetic Atlas Forge demo-fixture data … NOT sourced from this issuer's filings or any real disclosure. Treat as illustrative only; not committee-usable."* Ingestion reported **"scan verdict unavailable"** rather than claiming a clean AV scan with no ClamAV present. Empty states read "NO OBSERVED DATA" / "Live activity unavailable" / *"No seeded analysis has been substituted."* |
| **I5 gate honesty** | **PASS** | CP-5 emitted `Restricted` with 4 MATERIAL + 2 MINOR findings on a zero-evidence run; `model_id: "fixture"`, `prompt_version: "v2.0+fixture"`, `input_snapshot_state: "unapproved"`. The LLM never self-declared committee-ready. |
| **I2 citation integrity** | **PASS (detection)** | The gate itself caught dangling citations — QA-001/QA-002: *"could not be resolved to an ingested source chunk."* |
| **I4 NaN/∞** | **PASS** | Zero `NaN` / `Infinity` / `undefined` / `[object Object]` across 16 route renders on 3 personas. |
| **I9 a11y** | **PASS** | `node caos/frontend/scripts/a11y-axe.mjs` — **18 routes, 0 violations, 0 scan errors, 0 layout failures**, tags `wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa,best-practice`. Full output: [a11y.json](a11y.json). |

## Blocked — could not be tested here

Stated as blocks, never as passes.

| Item | Reason |
|---|---|
| **REAL DOCS: ≥4 live-EDGAR issuers; ≥2 filed docs fetched; ≥1 no-CIK issuer** | Network policy blocks all general outbound HTTPS (`sec.gov`, `data.sec.gov`, `efts.sec.gov`, `example.com` → proxy CONNECT 403). Only package registries reachable. **The prompt's central REAL DOCS clause is unsatisfiable in this container.** |
| I8 — ClamAV leg | No Docker daemon (`/var/run/docker.sock` absent). Size cap + magic-byte sniff paths remain untested end-to-end for the same reason the AV leg is. |
| I1 — true 401 fail-closed | Requires a non-`development` boot; dev identity fallback is active by design. |
| I3 — same-number-everywhere incl. XLSX export | No real financials to propagate; CP-1 served labelled synthetic fixture data, so cross-surface numeric identity was never exercised end-to-end. |
| I10 — concurrent runs / two personas on one issuer | Personas ran on isolated DBs; no shared issuer existed to contend over. Back/forward and refresh legs were exercised. |

## What was actually ingested

One genuine scanned filed document — `caos/tests/server/golden/scanned_atlf_earnings.pdf`
(1 page, **0 extractable text**, a true OCR-fallback case) — uploaded through the
real `/upload` wizard for a newly registered issuer, producing run
`456fbaa2-56fa-491e-93d5-d36282ecc69a`. No OCR toolchain is present
(`tesseract`/`pytesseract` absent), and the product reported this honestly:
**"1/1 vaulted · 0 chunks"**, **"0 chunks — no text"**, **"1 with no extractable text"**.

The document belongs to the repo's synthetic "Atlas Forge" issuer, so even this
upload is **not a real issuer document**.
