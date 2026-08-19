# CAOS — Roadmap Consolidation Review

**Date:** 2026-06-15 · **Author:** product/strategy pass before locking the roadmap.
**Method:** read the shipped code first, then all prior-session reports, then external
sources (in the order specified). Every claim about how something is built was checked
against the actual file; low-confidence claims are flagged inline.

**Companion to** [AUDIT.md](../caos/docs/AUDIT.md) · [FINANCE_SKILLS_REVIEW.md](../caos/docs/FINANCE_SKILLS_REVIEW.md)
· [TOOLING_REVIEW.md](../caos/docs/TOOLING_REVIEW.md) · [IA_REVIEW.md](../caos/docs/IA_REVIEW.md)
· [TIER1_ENGINE_PLAN.md](../caos/docs/TIER1_ENGINE_PLAN.md). This report **builds on**
those — it does not re-propose what they settled.

---

## 1. Baseline — what is actually shipped (grounded in code)

CAOS is a six-concept Next.js 15 analyst UI (Command · Pipeline · Deep-Dive · Model ·
Report · Monitor + a global ⌘K Ask) served by a FastAPI app as a single Databricks App.
~4.4k LOC Python (35 files) + ~14k LOC TS/TSX. SQLite by default (Alembic migrations),
Lakebase/Postgres for durability, BM25 over locally-vaulted documents, Anthropic Claude
for live synthesis with a deterministic offline fallback.

### 1.1 The real analytical engine (`caos/server/engine/`)

The shipped engine is a **lean, deterministic slice — not the agent mesh the planning
docs describe** (see §1.4). The runner executes exactly three analytical modules and the
QA stack:

| File | What it actually does |
|---|---|
| [runner.py](../caos/server/engine/runner.py) | `ANALYTICAL_SLICE = ["CP-0","CP-1","CP-2"]` with explicit deps. Per module: input-gate → retrieve → synthesize → validate → persist; then CP-5B lineage, **CP-5C council (opt-in)**, CP-5 gate, then projects `metric_facts`. Run-level roll-up. **Synchronous.** |
| [synth.py](../caos/server/engine/synth.py) | `FixtureSynthesizer` (canonical ATLF payloads, fully offline) vs `LiveSynthesizer` (reads the module's on-disk `Modular OS/CP-*/CP-*_ACTIVE_PROMPT.md`, grounds in BM25 chunks, calls Claude, parses JSON). Picks Live only when `ANTHROPIC_API_KEY` set. |
| [coststructure.py](../caos/server/engine/coststructure.py) | **CP-2** is fully deterministic: regex-extracts "energy as % of COGS" from retrieved chunks ([metrics.py](../caos/server/engine/metrics.py) `derive_energy_cost_pct`), emits a Calculated, source-cited claim. Works for any issuer with docs — no LLM. This is the template for future deterministic modules. |
| [lineage.py](../caos/server/engine/lineage.py) | **CP-5B** — validates claim→source lineage, flags orphan/weak-lineage claims as `Finding`s. |
| [council.py](../caos/server/engine/council.py) | **CP-5C** — opt-in ensemble of 4 adversarial reviewer "seats" (NumericalConsistency, CovenantConstruction, EvidenceSufficiency, DevilsAdvocate) fanned out concurrently, deterministic `_merge` dedup, optional blind peer-vote round (`_tally_votes`). **Produces findings only; never decides status.** No-op/zero-cost unless `council_enabled` + key. |
| [gate.py](../caos/server/engine/gate.py) | **CP-5** — pure functions: any CRITICAL→Blocked, any MATERIAL→Restricted, else Passed. `committee_status_from` adds confidence. **The LLM never declares its own work committee-ready** — the differentiator. |
| [metrics.py](../caos/server/engine/metrics.py) | The **8-metric catalog** (revenue, adj_ebitda, ebitda_margin, gross_margin, net_leverage, interest_coverage, fcf_conversion, energy_cost_pct) and `extract_facts` projecting CP-1 `normalized_financials` into cited `metric_facts`. gross_margin/fcf_conversion are **seed-only illustrative**. |

### 1.2 Retrieval, ingestion, query

- [retrieval.py](../caos/server/retrieval.py) — self-contained Okapi **BM25** (no extra dep), issuer-scoped (`retrieve`) and cross-issuer (`retrieve_corpus`). Comment notes Phase-2 vector-search swap behind the same interface.
- [ingest.py](../caos/server/ingest.py) — `pypdf` page-text concat + flat `openpyxl` dump. **markitdown** is wired but **flag-gated, out-of-process, off by default** (`markitdown_cmd=""`), needs a separate 3.10+ install. **No positional anchors** (page/char/bbox) captured → no true click-to-source highlight.
- [nlquery.py](../caos/server/nlquery.py) — cross-issuer NL→**constrained QuerySpec** (model fills a closed schema, never authors SQL), validated against the catalog; structured / semantic / hybrid routing; ranked, cited, provenance-tagged (run/derived/seed). The genuinely impressive surface.

### 1.3 Frontend (what's real vs mock)

- **Real, overlaid via `useLiveRun`:** the deep-dive CP-1 tab renders live adapted output ([lib/engine/adapt.ts](../caos/frontend/src/lib/engine/adapt.ts)), the NL query results, the citation viewer, and the Model Builder's scenario lens **re-bases on the live PF column** ([lib/model/scenarios.ts](../caos/frontend/src/lib/model/scenarios.ts) — best/base/worst + an adjustable 1-way **tornado**).
- **Still seeded mock:** most of deep-dive ([lib/deepdive/step-outputs.ts](../caos/frontend/src/lib/deepdive/step-outputs.ts) is 1,789 LOC), the Command posture/RV/sector boards, the Pipeline sim, and the Monitor concept (a frontend `useSimRun`, not a real service). The CP-3 RV scatter, CP-3B recovery waterfall, CP-4 covenant tables, and CP-6A debate the UI shows are **not executed by any backend module**.

### 1.4 The doc-vs-shipped gap (important context for §6)

[V2_REDEPLOY_PLAN.md](../caos/docs/V2_REDEPLOY_PLAN.md) and [CAOS_Master_Blueprint.md](../caos/docs/CAOS_Master_Blueprint.md)
describe a `backend/` with `agents/`, `governance/`, a 24-node registry-driven DAG,
CP-RENDER/EXTRACT/DB, an email plane, MinIO, LangGraph, MS Graph. **Verified 2026-06-15:
none of that exists in this repo** (no `backend/`, `server/agents/`, `server/governance/`).
Treat those two docs as **aspirational design, not as-built**. The pragmatic path is to
extend the lean `engine/` slice — *not* to resurrect the mesh. The 27-module `Modular OS/`
**prompt corpus is real and complete** (the methodology); the *execution* of it is 3 modules deep.

---

## 2. The HY analyst lens (what I judge candidates against)

Optimizing for the buy-side leveraged-finance analyst, the concrete jobs-to-be-done are:

1. **Spread the financials** — normalize statements, build Adj. EBITDA (with add-back scrutiny), leverage & coverage. *(CP-1)*
2. **Model the cash flow + downside** — FCF, deleveraging path, liquidity runway, when does a covenant break. *(Model Builder / CP-2B)*
3. **Covenant & document analysis** — headroom, baskets, RP/restricted-debt capacity, ECF sweep, EBITDA add-back definitions, leakage (J.Crew/Serta/Chewy-style). **The lev-fin specialty.** *(CP-4 / CP-4C)*
4. **Recovery / downside** — waterfall, LGD by instrument, structural subordination. *(CP-3B)*
5. **Relative value & security selection** — spread vs peers/rating/curve, new-issue concession, which part of the cap stack. *(CP-3)*
6. **Refinancing & maturity wall / LME risk** — can they refi, at what coupon, who gets primed. *(CP-3D)*
7. **Peer benchmarking** — vs sector cohort, outlier detection. *(CP-1C)*
8. **Monitoring "what changed"** — earnings deltas, rating actions, covenant trips, news. *(CP-MON / CP-1B)*
9. **Committee deliverable** — an IC memo where **every number is one click from its source** and survives scrutiny. *(CP-6A / Report Studio)*
10. **Screen the book** — surface deteriorating credits early across the portfolio. *(portfolio / early-warning)*

CAOS today does **1** well (live), **3 partially** (the tornado/scenario half of #2), and
**fakes 3,4,5,6,7,8** in the UI. The non-negotiable filter (inherited from FINANCE_SKILLS_REVIEW):
**anything adopted must feed CP-5B evidence lineage and clear the CP-5 gate.** A number with
no source trace is exactly what the platform exists to prevent.

---

## 3. Candidate inventory (rubric applied)

Effort: S ≤ ~3 days · M ~1–2 weeks · L ~3+ weeks. Verdict: **Strongly recommend / Consider / Park.**

| # | Candidate (JTBD) | Source / inspiration | Adaptation for HY | Effort & fit (files) | Differentiation | Key risk | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **SEC EDGAR XBRL ingestion → real CP-1** (#1 spread the financials) | SEC EDGAR MCP / [edgartools](https://www.edgartools.io/edgartools-mcp-for-sec-filings/) — **free, no API key, 13M+ filings, XBRL facts** | Map XBRL us-gaap facts → CP-1 `normalized_financials`; emit Calculated, source-cited claims like CP-2. HY caveat: many HY issuers are private; covers public-debt registrants. | **M.** New `engine/edgar.py` + connector; [routes/ingestion.py](../caos/server/routes/ingestion.py), [seed.py](../caos/server/seed.py), [metrics.py](../caos/server/engine/metrics.py). Same deterministic pattern as [coststructure.py](../caos/server/engine/coststructure.py). | Turns CP-1 from *fixture* into *sourced fact* — closes the A-1 mock gap with **free** data (fits no-paid-services). | Private issuers; XBRL tagging noise. | **Strongly recommend** — biggest single step from "mock" to "real," at zero data cost. |
| 2 | **Positional anchors + true click-to-source** (#9 defensible memo) | Master Blueprint §2 (F2/F6, never built) + productionize the landed markitdown spike | Capture `(page, char_start, char_end, bbox?)` at chunk time; thread to `evidence_items`; PDF viewer jumps+highlights. quote-fallback when no bbox. | **M.** [ingest.py](../caos/server/ingest.py), `evidence_items` (migration), [retrieval.py](../caos/server/retrieval.py), `PDFViewer`. markitdown already flag-gated. | The literal "show your work" promise — still unfulfilled. No competitor ties a committee number to a PDF coordinate by default. | bbox unreliable on scanned OMs (mitigate w/ quote re-location). | **Strongly recommend** — the brand pillar with no home yet. |
| 3 | **CP-4C deterministic covenant-capacity calculator** (#3 covenants) | Domain ([Simpson Thacher Covenant Handbook](https://www.stblaw.com/docs/default-source/publications/leveraged-finance-101---a-covenant-handbook.pdf)), CP-4/4C corpus, Octagon "debt covenant analysis" | Extract covenant defns + compute headroom / debt & RP baskets / ECF sweep with formula+numerator+denominator+period+source-trace, gated by CP-5. Follow CP-2's deterministic template. | **L.** New `engine/covenants.py` + catalog entries; covenant tab (mock today). | **The** marquee HY differentiator — covenant headroom is the daily lev-fin job; CreditSights/Covenant Review charge for it, none evidence-gate it. | Covenant text varies wildly; start with financial-covenant headroom, defer exotic baskets. | **Strongly recommend** — highest domain differentiation. |
| 4 | **Monte Carlo + P(covenant breach) on the cash-flow model** (#2 downside) | Anthropic **financial-modeling** skill (Apache-2.0, already "Adopt" in FINANCE_SKILLS_REVIEW); extends the **shipped** tornado | Sample drivers (rev growth, margin, rate, capex) → distributions of exit leverage, min cash, **P(breach)**, recovery. | **M.** Extends [lib/model/scenarios.ts](../caos/frontend/src/lib/model/scenarios.ts) (already has drivers + `project`); add a viz. | Probabilistic downside on an evidence-anchored model, not a static base/downside. | Spurious precision — present as ranges, not point PDs. | **Strongly recommend** — builds directly on a settled decision + shipped code. |
| 5 | **Altman-Z / structural distress early-warning score + portfolio screen** (#10 screen the book) | [Merton / Altman / KMV](https://analystprep.com/) (cross-domain credit theory) | Altman-Z computable from CP-1 facts alone (deterministic, S). Merton DD needs equity price+vol → public issuers only (M). Surface as a portfolio early-warning rank feeding Monitor. | **M.** New `engine/distress.py`; `metric_facts` + a Command/Monitor screen. | A transparent, cited deterioration score — not a black-box rating. | Z-score calibrated to manufacturers; document limits, don't over-trust. | **Strongly recommend** (Altman, S) / **Consider** (Merton). |
| 6 | **Real Excel + docx/pptx IC pack** (#9 deliverable) | First-party `anthropic-skills` **xlsx/docx/pptx** (available in this environment); FINANCE_SKILLS_REVIEW already said **"Adopt"** | Report Studio → live-formula workbook (NPV/IRR/3-statement/sensitivity) + Word IC memo + PPT, all gated on `committee_status`. | **M.** [engine/report.py](../caos/server/engine/report.py), Report Studio components. | Committee-grade, auditable, *filed-document* output vs a printed HTML tear-sheet. | Keep the light tear-sheet brand; don't ship generic templates. | **Strongly recommend** — settled "adopt," now buildable. |
| 7 | **Background run execution + per-run token budgeting + caching** (enabler) | TIER1_ENGINE_PLAN §8 risk 4 (flagged, not built) | Async runner + a `queued→running→complete` worker; cap tokens/run; cache upstream artifacts. | **M.** [runner.py](../caos/server/engine/runner.py), [routes/runs.py](../caos/server/routes/runs.py). | — (infra) | Scope creep into a full queue; keep it minimal. | **Strongly recommend** — dependency for opening the runner past 3 modules. |
| 8 | **CP-3B recovery waterfall + LGD engine** (#4 recovery) | CP-3B corpus + domain; recovery distribution can reuse the MC engine (#4) | Cap-structure → seniority waterfall → recovery by instrument, source-cited. | **M–L.** New `engine/recovery.py`; recovery tab (mock today). | Evidence-traced recovery vs a spreadsheet guess. | Needs clean cap-structure capture (depends on #1/#2). | **Consider** — high value, gated behind data foundation. |
| 9 | **Maturity-wall / CP-3D refinancing dashboard** (#6 refi risk) | Domain (Moody's/Fitch lev-fin coverage); CP-3D corpus | Portfolio maturity ladder + refi-cost-at-current-spread + LME/priming flags. | **M.** New engine module + a portfolio view. | Timely (high-rate refi wall); few tools make it portfolio-level + cited. | Needs maturity data from docs (depends on #1). | **Consider** — strong analyst pull, distinct surface. |
| 10 | **CP-1C peer benchmark / cross-sectional Z-score screen** (#7 peers) | Equity-quant cross-sectional ranking; K-Dense stats; builds on `metric_facts` + `nlquery` | Per-metric peer percentile / Z-score & outlier flags over the metric store. | **M.** [metrics.py](../caos/server/engine/metrics.py), [nlquery.py](../caos/server/nlquery.py) catalog, a Command view. | Turns the already-strong NL query into a screening engine. | Thin until more issuers/metrics exist (depends on #1). | **Consider.** |
| 11 | **CP-5C council eval harness + cost guardrails** (trust the gate) | claude-cookbooks **evaluator-optimizer** pattern; `senior-prompt-engineer` skill | Golden set of seeded-error payloads; measure council precision/recall; pin cost. | **M.** Tests + a harness around [council.py](../caos/server/engine/council.py). | Makes the opt-in council *trustworthy* enough to enable. | Eval-set maintenance. | **Consider** — do before defaulting the council on. |
| 12 | **Real CP-MON signal feed (news / rating actions)** (#8 monitoring) | IA_REVIEW promoted Monitor (shipped as a **sim**); vetted RSS only (TOOLING_REVIEW excluded scraping) | Replace `useSimRun` with a vetted RSS/rating-action poller writing real alerts. | **L.** New service + Monitor wiring. | Fills the promoted concept with real signal. | Source licensing/MNPI; revisit authz (S-4). | **Consider** — surface exists; needs a *vetted free* feed. |
| 13 | **Vector-search retrieval (embeddings)** (better grounding) | TIER1 §4 Phase 2 | Swap corpus fetch for embeddings behind the `retrieve` interface. | **M.** [retrieval.py](../caos/server/retrieval.py). | Marginal over BM25 at demo scale. | Infra/cost; BM25 is "good enough" now (PERF-1 is the real trigger). | **Park** until scale demands it. |
| 14 | **Live spread / OAS RV via rateslib/QuantLib** (#5 RV) | [rateslib](https://github.com/topics/fixed-income) / [QuantLib](https://www.quantlib.org/) / FinancePy | Real spread/curve analytics for CP-3. | **L.** New engine + RV surface. | Real RV vs mock scatter. | **Needs market pricing data = out of scope + paid.** | **Park** — gated on a pricing-data decision. |
| 15 | **Paid data MCP connectors** (Moody's, S&P, FactSet, Daloopa, PitchBook) | anthropics/financial-services connectors | Drop-in fundamentals/ratings. | M each. | More data. | **Violates no-paid-services + vendor lock-in.** | **Park** — optional adapters only, never core. |

---

## 4. Cross-domain techniques worth porting (and how)

These are specific, transferable methods — not whole tools — adapted to the HY lens and the
evidence-gated architecture:

- **Structural & reduced-form credit models (academic/banking → early-warning).** Altman-Z
  (deterministic, CP-1 inputs only), Merton **distance-to-default** (public issuers w/ equity
  vol), Ohlson O-score. Port as `engine/distress.py`, each emitting a **cited, deterministic**
  score that feeds a portfolio screen and CP-MON — *transparent*, not a black box. (Candidate 5.)
- **Monte Carlo / sensitivity (quant → downside).** The financial-modeling skill's MC +
  best/base/worst already partly landed as the tornado. Extend to driver distributions →
  **P(covenant breach)** and a recovery distribution. Reuse the same engine for CP-3B. (4, 8.)
- **Cross-sectional Z-score screening (equity systematic → peers).** Standardize each catalog
  metric across the cohort; rank percentiles; flag outliers. Cheap on the existing `metric_facts`
  + `nlquery`. (Candidate 10.)
- **Excess-cash-flow / basket math (lev-fin legal → covenants).** The ECF-sweep waterfall and
  RP/debt-basket capacity formulas are *deterministic arithmetic* over extracted definitions —
  ideal for the CP-2-style "compute + cite + gate" pattern. (Candidate 3.)
- **GARCH spread-vol bands (time-series, K-Dense → RV).** Only once a spread history exists
  (needs pricing) — **parked** with candidate 14.
- **Agent-workflow patterns (claude-cookbooks → engine).** The **evaluator-optimizer** and
  **orchestrator-workers** notebooks are the textbook form of what `council.py` (evaluator)
  and a future CP-X DAG (orchestrator) already gesture at — use them to harden, not rebuild. (11.)

---

## 5. Delta vs. prior reports

**Already settled — do not re-propose (status):**

- *financial-modeling skill (MC/sensitivity/LBO)* — FINANCE_SKILLS_REVIEW "Adopt (top)"; **tornado/scenarios landed.** Candidate 4 is the *next increment* (MC + breach prob), not a new idea.
- *Office xlsx/docx/pptx skills* — FINANCE_SKILLS_REVIEW "Adopt"; **not yet built.** Candidate 6 = finish the settled decision.
- *markitdown* — TOOLING_REVIEW "Adopt"; **spike landed, flag-gated.** Candidate 2 = productionize + add the anchors it was always meant to enable.
- *CopilotKit patterns* — "Adopt selectively"; **Ask ATLF shipped.** Nothing to add.
- *Monitor concept + global Ask + upload-in-Pipeline* — IA_REVIEW; **Monitor & Ask shipped** (Monitor as a sim). Candidate 12 fills it with real signal.
- *Vector search / more modules / async+budgeting* — TIER1_ENGINE_PLAN flagged. Candidate 7 (async+budgeting) and 13 (vectors) are those items, prioritized.
- *Compliance/academic-NC/equity/backtesting skills* — already excluded/reference-only. Unchanged.

**Genuinely new in this report:**

1. **SEC EDGAR free XBRL ingestion → real CP-1** (no prior report mentions it; the cleanest mock-killer at zero data cost).
2. **CP-4C deterministic covenant-capacity calculator** as the marquee HY differentiator (prior reports treat covenants only as a UI tab).
3. **Altman-Z / Merton structural early-warning** as a portfolio screen (cross-domain port, not previously proposed).
4. **The doc-vs-shipped reconciliation** (§1.4) — prior plans assume an agent mesh that isn't in the repo; this reframes the roadmap around the lean engine.
5. **Recovery (CP-3B) and maturity-wall (CP-3D)** as deterministic engines reusing the MC core and the EDGAR data foundation.

---

## 6. Ranked shortlist (sequenced, with dependencies)

The spine is **data foundation → engine scaling → the HY-specific analytical modules →
deliverables/portfolio.** Each item names the files it touches.

| Seq | Build | Depends on | Touches |
|---|---|---|---|
| **1** | **SEC EDGAR XBRL ingestion → real CP-1** | — | new `engine/edgar.py`, [routes/ingestion.py](../caos/server/routes/ingestion.py), [seed.py](../caos/server/seed.py), [metrics.py](../caos/server/engine/metrics.py) |
| **2** | **Background run exec + token budgeting + caching** | — | [runner.py](../caos/server/engine/runner.py), [routes/runs.py](../caos/server/routes/runs.py) |
| **3** | **Positional anchors + click-to-source** (productionize markitdown) | — | [ingest.py](../caos/server/ingest.py), `evidence_items` migration, [retrieval.py](../caos/server/retrieval.py), `PDFViewer` |
| **4** | **CP-4C deterministic covenant-capacity calculator** | 1, 3 | new `engine/covenants.py`, [metrics.py](../caos/server/engine/metrics.py), covenant tab |
| **5** | **Monte Carlo + P(covenant breach)** on the model | 4 (breach line) | [lib/model/scenarios.ts](../caos/frontend/src/lib/model/scenarios.ts) + viz |
| **6** | **Altman-Z early-warning score + portfolio screen** | 1 | new `engine/distress.py`, [metrics.py](../caos/server/engine/metrics.py), Command/Monitor view |
| **7** | **Real Excel/docx/pptx IC pack** | 2 | [engine/report.py](../caos/server/engine/report.py), Report Studio |
| **8** | **CP-3B recovery waterfall + LGD** | 1, 5 (MC reuse) | new `engine/recovery.py`, recovery tab |
| **9** | **Maturity-wall / CP-3D refi dashboard** | 1 | new `engine/refinancing.py`, portfolio view |
| **10** | **CP-1C peer Z-score screen** | 1, 6 | [metrics.py](../caos/server/engine/metrics.py), [nlquery.py](../caos/server/nlquery.py), Command view |
| 11 | *(Consider)* CP-5C council eval harness | — | tests around [council.py](../caos/server/engine/council.py) |
| 12 | *(Consider)* Real CP-MON vetted-RSS signal feed | 2 | new service, Monitor |

**Critical path:** 1 and 2 unblock almost everything (real data + the ability to run more
than three modules). 3 is independent and high-symbolic-value. 4 is the differentiator and
should start as soon as 1+3 land. 5–10 are then mostly "write a deterministic engine in the
CP-2 mold + un-mock the matching UI tab."

---

## 7. What I would explicitly NOT pursue

- **Live market-data / pricing engines (real OAS/spread RV, GARCH spread-vol).** Out of scope per the brief and gated on a data-licensing decision; the inputs are paid. *Park candidates 14 and the spread-vol port.*
- **Paid data MCP connectors** (Moody's, S&P, FactSet, Daloopa, PitchBook, Morningstar). They violate the **no-paid-services / no-vendor-lock-in** rule. Keep them as *optional, operator-configured adapters* behind the free path — never a core dependency. *Park candidate 15.*
- **Resurrecting the `backend/` agent-mesh** (LangGraph DAG, governance registry, CP-RENDER/EXTRACT/DB, MinIO) from V2_REDEPLOY_PLAN/Blueprint. It isn't in the repo; rebuilding it is a multi-month rewrite that competes with shipping real analyst value. Extend the lean `engine/` instead; add a thin CP-X router only when module count justifies it.
- **Social-media / web scraping for signals** (Agent-Reach class). Already excluded by TOOLING_REVIEW — MNPI/ToS/compliance risk in a regulated credit process.
- **MDX / arbitrary-component narrative rendering.** The Blueprint already rejected it (LLM-authored component injection); stay on `react-markdown` with an allow-list.
- **Algorithmic/backtesting/systematic-trading skills.** Off-domain for fundamental IC-memo credit work (FINANCE_SKILLS_REVIEW already excluded).
- **A second conversational/answer renderer.** IA_REVIEW settled Ask as one global launcher; don't fork it.

---

## 8. Production phasing (added 2026-06-15 — owner input)

The owner set the deployment path, which resolves the open market-data question and adds
two hard constraints. **Phase 1:** launch on a private Databricks workspace, validate the
app is functional **against public-issuer data**, and surface faults. **Phase 2:** migrate
the repo from personal → enterprise platform (which runs **security checks + code review** as
a gate); once passed, **market data arrives via Bloomberg** — either Bloomberg-powered Excel
sheets or the Bloomberg API.

### 8.1 What this changes
- **Market data is no longer out of scope — it's Phase 2.** Candidate 14 (spread/OAS RV), GARCH spread-vol, and Merton distance-to-default (needs equity price+vol) are **un-parked, but Phase-2-only**. CP-3 RV stops being mock once Bloomberg lands.
- **The "no-paid-services" rule is now phased, not absolute:** free/OSS for Phase 1 (SEC EDGAR); **Bloomberg is the sanctioned enterprise data source for Phase 2.** OSS still wins for everything Bloomberg doesn't uniquely provide.
- **Security hardening becomes a Phase-2 *entry criterion*, not a backlog item.**

### 8.2 Phase 1 — functional validation on public-issuer data (free/OSS, fault-finding)

| Build this in Phase 1 | Why it belongs here |
|---|---|
| **1 · SEC EDGAR XBRL → deterministic CP-1** | **Near-prerequisite, not optional** (see gotcha below). Free, public, real numbers. |
| **3 · Positional anchors + markitdown productionize** | Real 10-Ks/credit agreements are table-dense and 200–400pp; pypdf mangles them. This is where faults will actually appear. |
| **4 · CP-4C covenant calculator** | Public HY issuers file credit agreements/indentures as **EDGAR exhibits** — covenant text is available free in Phase 1. |
| **5 · Monte Carlo / P(breach)**, **6 · Altman-Z**, **7 · Excel/docx/pptx IC pack** | All compute from CP-1 fundamentals + the cash-flow model — **no market data**, so fully Phase-1. |
| **Observability / fault instrumentation** | Phase 1's stated goal *is* fault-finding: structured per-run logging, surfaced failure reasons, a run-inspection view. [runner.py](../caos/server/engine/runner.py) currently just sets `status="failed"`. |

> **Phase-1 gotcha to flag loudly.** [synth.py](../caos/server/engine/synth.py) uses the **ATLF
> fixture for CP-1 whenever `ANTHROPIC_API_KEY` is unset** — so running *public* issuers with no
> key will render **ATLF's numbers for every issuer**, which looks like a bug but isn't. Two
> clean fixes, both Phase-1: wire the key as a Databricks secret, **and/or** ship candidate 1
> (EDGAR deterministic CP-1) so real fundamentals flow without any LLM. The EDGAR path is the
> safer validation anchor — deterministic, cited, reproducible, no token cost. Expect **CP-2 to
> return "Insufficient Information" on most real docs** (the "N% of COGS" energy pattern is rare)
> — that's honest behavior, not a fault.

Background async execution + token budgeting (candidate 2) can stay **partial** in Phase 1
(keep the synchronous runner; add token caps + observability) and harden in Phase 2.

### 8.3 Phase 2 — enterprise, post-security-review, Bloomberg-enabled

**Entry criteria (pre-flight before the enterprise gate):** resolve the AUDIT items an
enterprise scanner *will* flag — **D-1** npm advisories (have an upgrade/justification plan;
never `audit fix --force`), **S-4** per-issuer authz (becomes material the moment Bloomberg /
MNPI-bearing data is multi-user), **B-2** untrusted-document parsing surface, the **markitdown
subprocess** surface, and **secrets handling** (the Anthropic key today; Bloomberg creds next).
Pre-flight with the `security-review` / `/security-review` and `code-review` skills so the
enterprise review finds little. Then the market-data-dependent work lands: **CP-3 RV/spread/OAS**,
**spread-vol**, **Merton DD**, the market-relative half of **CP-1C** peers and **CP-3D** refi-cost,
and a real **CP-MON** feed.

### 8.4 Bloomberg integration — recommend the Excel-upload path

The two Bloomberg options are not equivalent in cost or compliance:

- **Bloomberg-powered Excel sheets → upload (recommended).** The analyst pulls a pricing/curve
  sheet via the Terminal's Excel add-in (BDP/BDH/BDS), then uploads it — **CAOS already has
  [`POST /api/upload/pricing-sheet`](../caos/server/routes/ingestion.py)**, so this is *near-free*
  architecturally. Entitlement stays at the Terminal/per-user level (compliant), and no
  server-side Bloomberg session is required.
- **Direct Bloomberg API.** Desktop **DAPI/BLPAPI** needs a live Terminal session on the host
  (won't work for an unattended Databricks app); server-side **B-PIPE / Data License** is a
  separate enterprise contract with **per-security fees and redistribution limits** — and
  **storing Bloomberg data in CAOS's DB and serving it to all analysts can breach the data
  license** unless every consumer is entitled. This intersects directly with the S-4 authz item.

**Recommendation:** start Phase 2 on the **Excel-upload path** (compliant, reuses existing
ingestion, no new infra); only pursue B-PIPE/Data License if unattended/real-time pricing is a
hard requirement — and get the redistribution/entitlement question to compliance *first*.

---

## Appendix — sources reviewed (in the specified order)

1. **[alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)** (MIT, 337 skills) — broad; finance dir = Financial Analyst (DCF), Business Investment Advisor. **No credit/fixed-income specialization** — patterns only.
2. **[anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks)** (MIT) — no finance section, but the **[agent patterns](https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents)** (prompt-chaining, routing, parallelization, **orchestrator-workers**, **evaluator-optimizer**) map onto CP-5C/CP-X. Used in §4/candidate 11.
3. **[anthropics/financial-services](https://github.com/anthropics/financial-services)** (Apache-2.0) — **richest.** IC-memo, LBO, returns, dd-checklist, portfolio-monitoring, catalyst-calendar, thesis-tracker, comps, audit-xls (model audit), morning-note, sector-overview; MCP connectors (Moody's, S&P, FactSet, PitchBook, Daloopa…). Verdict: harvest *patterns* (IC-memo, returns, model-audit), treat connectors as paid/optional.
4. **mcpmarket.com/tools/skills** — **INACCESSIBLE** (HTTP 429 on two attempts). Not inferred. Covered the intent via the web search below.
5. **Broad web search** (queried: OSS fixed-income/credit libs; SEC-EDGAR MCP; HY analyst workflow; Merton/Altman; covenant-extraction; awesome-claude-skills/finance). Findings: **[SEC EDGAR MCP / edgartools](https://www.edgartools.io/edgartools-mcp-for-sec-filings/)** (free, XBRL — candidate 1); **[rateslib](https://github.com/domokane/FinancePy)/QuantLib/FinancePy/ORE** (OSS analytics — parked on pricing data); **Merton/Altman** structural models (candidate 5); **[Simpson Thacher covenant handbook](https://www.stblaw.com/docs/default-source/publications/leveraged-finance-101---a-covenant-handbook.pdf)** + EBITDA-addback/basket domain (candidate 3); **[OctagonAI/skills](https://github.com/OctagonAI/skills)** (MIT but *paid* Octagon API — debt-covenant analysis + Altman-Z patterns); K-Dense scientific skills (time-series). In-environment skills also available: `anthropic-skills` xlsx/docx/pptx/pdf (candidate 6), `daloopa:*`, `sp-global:*`, `lseg:*` (paid-data partner plugins — optional only).
