# Persona Journey Stress Test — P1 Journey Contract

Written **before** any journey ran, per the P1 discipline: the invariants are
fixed in advance so no observed failure can be rationalized as "expected".

- **Run date:** 2026-07-26
- **Branch:** `claude/multi-persona-stress-test-cgegcb`
- **Base commit:** `341d14b` (WIP: epitaxy pre-switch from codex/112)
- **Host:** Linux 6.18.5 cloud container, 4 cores / 15 GB, Python 3.11.15,
  Node 22.22.2, FastAPI 0.139.2 (pin intact, not downgraded).

## Environment reality — recorded up front

The prompt assumes the author's macOS workstation. This run executes in a
locked-down cloud container. The deltas below are **environmental**, not
findings, and are stated here so that Section "Testability" cannot be
retro-fitted after results are known.

| Capability | State | Consequence |
|---|---|---|
| Outbound HTTPS (general) | **BLOCKED** by network policy | `sec.gov`, `data.sec.gov`, `efts.sec.gov`, and even `example.com` fail at the proxy CONNECT tunnel (403). Only `pypi.org` / `registry.npmjs.org` and peers in the proxy `noProxy` list resolve. |
| Live EDGAR acquisition | **IMPOSSIBLE** | The "≥4 issuers via live EDGAR" and "≥2 filed docs you fetch" clauses of REAL DOCS cannot be satisfied here. |
| Docker daemon | **ABSENT** (`/var/run/docker.sock` missing) | No ClamAV container → I8's AV leg untestable. No Postgres → SQLite lane only, `InProcessExecutor` not `QueueWorker`. |
| LLM providers | **NO KEYS** (`llm: demo-fallback`) | Every LLM leg takes its deterministic/offline path. |
| `.claude/launch.json` | macOS paths (`/Users/ericguei/...`) | Rewritten for this host; per-persona DB isolation preserved. |

Real documents actually available offline: exactly **one** genuine filed
document — `caos/tests/server/golden/scanned_atlf_earnings.pdf` (scanned →
exercises the OCR fallback chain and its provenance stamps).

**Consequence for scope:** the run proceeds on everything not gated by live
data. The prompt's own closing instruction governs: *"Report faithfully: if a
journey stopped, say where and why."*

## Reframing: what a dead-upstream environment tests *better*

With EDGAR down, no LLM keys, and no AV daemon, every upstream this product
depends on is unavailable. That makes **I6 (provenance honesty)** the headline
invariant rather than a side check: a platform whose upstreams are all dead must
say so on every surface. Any real number, any confident posture, any
committee-ready verdict rendered under these conditions is a **FAULT** of the
most serious class — a silent wrong read with money behind it.

## Invariants

| ID | Invariant | Testable here? |
|---|---|---|
| I1 | auth fail-closed; no pre-auth data flash; deep-link survives login | **PARTIAL** — `ENVIRONMENT=development` activates the dev identity fallback by design. Deep-link/flash behavior testable; true 401 fail-closed needs a non-dev boot (run separately). |
| I2 | every claim→evidence→chunk id resolves; no dangling ids | **PARTIAL** — only over chunks derived from the one uploaded PDF. |
| I3 | same-number-everywhere (C9): Deep-Dive = Model = Report = XLSX, matching ORIGIN/METHOD/RUN/AS-OF stamps | **PARTIAL** — no XBRL financials to populate CP-1, so cross-surface identity is checked on whatever the app *does* render. |
| I4 | no NaN/∞ leak (`is_finite_number`); blank/NaN/silent-degrade where a number belongs = fault | **YES** — and materially more likely with empty CP-1 inputs. |
| I5 | CP-5 verdict from `gate.py` findings; LLM never self-declares committee-ready | **YES** — gate is deterministic. p3 actively attacks this. |
| I6 | no mock/seed number tagged `prov="run"`; upstream down → explicit unavailable, never silent substitution | **YES — headline.** All upstreams are down; honesty is maximally observable. |
| I7 | frozen report versions + IC snapshots immutable; withdraw supersedes, never silent-deletes | **YES** — local DB operations. |
| I8 | size cap + magic-byte sniff + ClamAV fire BEFORE parse; rejects are named 422s, no vault write | **PARTIAL** — size cap and magic-byte sniff testable; **ClamAV leg untestable** (no daemon). |
| I9 | keyboard-operable, visible focus, status never color-alone, reduced-motion honored | **YES** — via `node caos/frontend/scripts/a11y-axe.mjs`. |
| I10 | stress: concurrent runs, nav-away mid-run, refresh during ingest, double-submit finalize, back-button in a wizard, two personas on one issuer | **YES** — the highest-value class here, and independent of live data. |

**WORKFLOW LOGIC** (P4's highest-weighted class for the analyst persona) is
fully testable and does not depend on any blocked upstream. It is therefore the
primary yield of this run.

## Stacks

Per-persona isolation preserved (separate port + separate SQLite DB); no
`CAOS_DEMO_SEED`, no `*_facts.json` fixture seeding on primary journeys.

| Persona | Backend | Frontend | DB |
|---|---|---|---|
| p1 analyst | `:8010` | `:3010` | `data/caos_p1.db` |
| p2 pm | `:8020` | `:3020` | `data/caos_p2.db` |
| p3 qa | `:8030` | `:3030` | `data/caos_p3.db` |

## Recording rules

- Nothing enters `results.md` without passing the P3 reproduction gate
  (clean stack + fresh session) → CONFIRMED / FLAKY(rate) / WITHDRAWN.
- WITHDRAWN findings are recorded, never deleted.
- Every finding names its layer (frontend | API | engine | ingestion) and a
  `file:line` or endpoint.
- Environmental blocks are reported as blocks, never as passes.
