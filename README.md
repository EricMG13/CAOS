# Credit Operating System

**An institutional leveraged-finance credit-analysis platform** — a structured
analytical methodology (the *Modular OS* prompt corpus) implemented as a
deployable analyst workspace (**CAOS — Credit Agent OS**). It turns a deal's
source documents into a defensible credit view, with every figure one click from
its source and a deterministic QA gate standing between draft and committee.

Built for the **buy-side credit analyst** (deep work in Deep-Dive, Model Builder,
Report Studio), with secondary lenses for the **PM/CIO** (portfolio posture) and
**Head of Research / QA** (coverage health, the QA gate).

> Demo/portfolio build. Figures are anchored to a seeded reference deal —
> *Atlas Forge Industrials (ATLF)* — and much of the deep-dive UI is high-fidelity
> illustrative data; see **Status** below for exactly what is engine-derived vs seeded.

---

## What's in here

| Path | What it is |
|------|------------|
| [`Modular OS/`](Modular%20OS/) | The credit methodology corpus — CP-0…CP-6E, CP-SR/MON/X, plus canonical schemas. Analytical **prose**, the single source of truth for module behaviour. |
| [`caos/`](caos/) | The app: Next.js 16 analyst UI (`frontend/`) + FastAPI engine/service (`server/`), deployed as a **self-hosted Docker stack** (`caos/deploy/`). See [caos/README.md](caos/README.md). |

> **Module inventory (source of truth: [`caos/server/engine/registry.py`](caos/server/engine/registry.py)).** The engine routing index wires **19 implemented analytical modules** in the default route plan (CP-0, CP-1/1A/1B/1C, CP-2/2B/2C/2D/2E/2F, CP-3/3B/3C/3D, CP-4/4C, CP-6A/6E) plus feature-flagged, default-off **CP-2G** and **CP-4D**, gated by the **CP-5 QA phase** (CP-5B lineage + the CP-5 severity gate, which run as a gate step rather than routed graph nodes). Two further corpus modules are registered **spec-only** (`implemented=False`, never executed) so the route plan reflects the mesh honestly: **CP-SR** (SectorReview) and **CP-MON** (CreditPulse) on L7. **CP-RENDER** and **CP-EXTRACT** are deliberately *not* registered (PD-06, 2026-07-22): Report Studio is CP-RENDER's equivalent service, and CP-EXTRACT is retired — see the registry docstring. The broader corpus names ~27 modules; older planning docs that cite "27" / "24" / "7" are describing aspirations or earlier slices — the registry above is what actually runs.
| [`caos/docs/`](caos/docs/) | Architecture, audit, security, and planning docs (index below). |

## Capabilities

- **Analytical engine** — runs the 19-module DAG (CP-0 → CP-1 family → CP-2
  family → CP-3 family → CP-4 family → CP-6 debate; see the registry) followed by
  **CP-5B evidence-lineage validation** and the deterministic **CP-5 QA gate**
  (CRITICAL→Blocked, MATERIAL→Restricted, else Passed). Each claim is traced to an
  ingested source chunk via BM25 retrieval. The CP-5 gate's calculation, cross-module
  and evidence-trace checks are always-on and deterministic; its unsupported-claim,
  legal, market-RV, schema and export lanes run only under the **opt-in LLM council**
  (requires an API key). Runs use a fixture synthesizer offline and live Claude when
  a key is set.
- **Analyst UI — 15 destinations in five workflow groups** (Intake / Analyze /
  Decide / Publish / Monitor), anchored by the six core concepts — Command
  Center, Pipeline, Deep-Dive, Model Builder, Report Studio, Monitor — plus
  Directory/Upload, Research, Query, Sector Review, RV Screener, Sponsors,
  Portfolio Lab, IC Book, and a global **Ask (⌘K)** launcher.
- **Cross-issuer natural-language query** (Command Center) — structured metric
  ranking, semantic evidence retrieval, and a hybrid of both, with a
  **run / derived / seed provenance** ladder and **click-to-source** citations.
- **Model Builder** — a sourced cash-flow grid grounded in the live CP-1 run,
  a forward Scenario & Sensitivity lens (tornado), and a **Scenario Builder**
  (presets + natural language) that re-centers base/downside forecasts.
- **Report Studio** — a print-ready institutional tear-sheet, gated on
  committee-ready status.

## Architecture

One process serves everything: FastAPI exposes the JSON API under `/api` and
serves the **statically-exported** Next.js frontend at `/` (no Node in
production). The supported deployment is the **self-hosted Docker stack**
(`caos/deploy/`): **Caddy (TLS) → oauth2-proxy (Google Workspace OIDC) → app →
Postgres**. The app trusts the forwarded identity headers set by oauth2-proxy
(`X-Forwarded-User` / `-Email`), layered with an in-app analyst-profile login, and
the gate **fails closed in production** (Caddy strips client-supplied
`X-Forwarded-*`). Storage is SQLite + a local vault by default; set `DATABASE_URL`
to the bundled Postgres and `CAOS_STORAGE_DIR` to a durable volume mount for
persistence. Schema is managed by **Alembic** (migrations run on boot); LLM
features run on a tiered multi-provider mesh — Anthropic Claude
(`claude-opus-4-8`) on the top tier, DeepSeek via OpenRouter on the
cheap/fast/strong tiers, Gemini for embeddings — and degrade to deterministic
demo behaviour without keys. See [caos/docs/LAUNCH_PHASE1.md](caos/docs/LAUNCH_PHASE1.md)
for the launch runbook and [caos/docs/SECURITY.md](caos/docs/SECURITY.md) for the
trust model.

```
Credit Operating System/
  Modular OS/        methodology corpus (CP-0…CP-6E, schemas)
  caos/
    frontend/        Next.js 16 (output: "export")
    server/          FastAPI app + analytical engine (serves /api and the built UI)
    deploy/          self-hosted Docker stack (Dockerfile, docker-compose, Caddy, oauth2-proxy)
    scripts/         build_frontend.sh (stages the UI into server/static)
    tests/           pytest (server) + Playwright (e2e)
    docs/            architecture / audit / security / plans
```

## Quickstart (local, single process — what production runs)

```bash
cd caos
python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt
./scripts/build_frontend.sh                 # builds the UI into server/static
cd server && ../.venv/bin/python run.py     # http://localhost:8000
```

UI hot-reload, the self-hosted Docker deploy, and full test commands are in
**[caos/README.md](caos/README.md)**.

## Status

Healthy and deploy-ready (no P0/P1 — see [AUDIT.md](caos/docs/AUDIT.md)).

| Check | State |
|-------|-------|
| Server tests | 2,925 pytest ✓ (39 skipped · 2026-07-23) |
| Frontend | eslint ✓ · `tsc --noEmit` (strict) ✓ · 1,824 vitest ✓ (2026-07-23) · `next build` ✓ |
| CI | [ci.yml](.github/workflows/ci.yml) runs all of the above |

**Engine-derived vs seeded (honest line):** the engine genuinely produces
CP-0/CP-1/CP-2 outputs, the QA gate, evidence lineage, and the metric store that
backs NL query. Much of the broader deep-dive/report UI is still high-fidelity
**seeded** demo data — tracked as finding A-1 in the audit. Values carry a
`run` / `derived` / `seed` provenance badge so the distinction is visible in-product.

## Docs

- [caos/README.md](caos/README.md) — deploy & local dev
- [caos/docs/AUDIT.md](caos/docs/AUDIT.md) — codebase audit & findings
- [caos/docs/SECURITY.md](caos/docs/SECURITY.md) — trust model & authz posture
- [caos/docs/TIER1_ENGINE_PLAN.md](caos/docs/TIER1_ENGINE_PLAN.md) — engine design
- [caos/docs/IA_REVIEW.md](caos/docs/IA_REVIEW.md) — information-architecture review
- [.impeccable.md](.impeccable.md) / [CLAUDE.md](CLAUDE.md) — design system & contributor guidance
