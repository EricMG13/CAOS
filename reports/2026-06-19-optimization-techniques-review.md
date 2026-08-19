# CAOS — Optimization Techniques Review

**Date:** 2026-06-19
**Scope:** Whole-system review (FastAPI engine + Next.js frontend + agent/LLM orchestration) against current (2025–26) optimization practice, web-search–grounded.
**Method:** Read the engine (`runner`, `planner`, `synth`, `budget`, `retrieval`, `council`, `debate`), the run executor, config, `main`, `deepresearch`, and the frontend build (`next.config.js`, chart/markdown components). Cross-checked against published guidance on prompt caching, parallel multi-agent/DAG execution, the Batches API, and Next.js bundle splitting.

---

## Implementation status (applied 2026-06-19)

Done in this pass — all 280 server tests green: **#1** intra-run layer parallelism (`runner.py` `_dependency_layers` + per-layer concurrent synthesis, session-touching modules serial, `synth_concurrency` semaphore), **#3** module-focused grounding query for CP-1's live path (`synth.py`), **#4** off-thread PDF/XLSX parsing (`routes/ingestion.py`). Deferred per the report's own guidance: **#2** (Deep Research backgrounding — do when timeouts appear) and **#5** (uvicorn workers — leave at 1 for the pilot).

## Bottom line

The codebase is **already well-optimized** — most of the obvious levers are pulled (see "Already done"). There is **one high-leverage gap left: the analytical module loop runs strictly serially** even though the planner already produces a dependency DAG and the team already uses `asyncio.gather` everywhere *else*. Fixing that is the single biggest wall-clock win. Everything else is incremental or YAGNI.

---

## Already done (don't redo)

These are in place and correct — credit where due:

| Optimization | Where | Notes |
|---|---|---|
| **Prompt caching** (ephemeral `cache_control` on system+tools) | `synth.py:267` | Covers the whole tools+system prefix; guaranteed hit on the one-shot repair and on same-module re-runs in the 5-min window. |
| **Advisor tool** (cheap executor + strong advisor mid-generation) | `synth.py:268`, `config.py:72` | Opt-in. Near-advisor quality at executor rates. |
| **Per-run token budget** (degrade/gate instead of overspend) | `budget.py` | `ContextVar`-threaded; caching-invariant accounting. |
| **BM25 index built once per run**, reused across all `retrieve()` | `retrieval.py:116`, `runner.py:98` | P4-2 — corpus tokenized once, not per call. |
| **N+1 elimination** in cross-issuer NL query | `retrieval.py:163` | PERF-1 — one query + one BM25 pass for per-issuer best chunk. |
| **Council / debate LLM fan-out parallelized** | `council.py:114,166`, `debate.py:350` | Seats, peer round, and bull/bear all `asyncio.gather`. |
| **Frontend chart + markdown code-split** | `G2Chart.tsx` (runtime `import()`), `research/page.tsx:22` (`next/dynamic`) | `@antv/g2` (the heavy lib) is out of first-load; `optimizePackageImports` on too. |
| **Postgres queue worker** (`FOR UPDATE SKIP LOCKED`, lease, reaper) | `run_executor.py:97` | Sound concurrency primitive; in-process fallback on SQLite. |
| **Deep research streamed** to avoid HTTP timeouts | `deepresearch.py:172` | Already self-flagged for backgrounding (below). |

---

## Recommendations (ranked)

| # | Change | Lever | Effort | Priority |
|---|---|---|---|---|
| 1 | Parallelize independent analytical modules per DAG layer | Wall-clock latency | M | **High** |
| 2 | Promote Deep Research to a background job | Reliability (timeouts) | S–M | Medium |
| 3 | Module-tailored retrieval queries | Grounding quality (+ tokens) | S | Low–Med |
| 4 | Offload sync PDF/XLSX parsing off the event loop | Throughput under load | S | Low |
| 5 | uvicorn worker count for the Postgres deploy | Scaling headroom | S | Low |

### 1. Parallelize the analytical module loop (the one real gap)

**Today:** `runner.py:245` runs modules one at a time — `for module_id in routed: await _attempt(module_id)`. With ~15 modules and the LLM-backed ones each costing seconds, a live run pays roughly the **sum** of all module latencies. The planner (`planner.py`) already computes a topological order *and* every module's `depends_on`, so the dependency layers are known for free.

**Why it's safe to do now:** the QA side already proves the pattern works here — `council`/`debate` fan out with `asyncio.gather`. Published practice agrees: with app-layer async + concurrent LLM calls, "total latency approach[es] the longest individual step rather than the sum of all steps" ([Zylos](https://zylos.ai/research/2026-04-26-parallel-concurrency-agent-execution/), [arXiv 2507.08944](https://arxiv.org/pdf/2507.08944)). Many downstream synthesizers (CP-2B/2C/2D/2E/2F, CP-3/3B/3C/3D, CP-4, CP-4C, CP-1A/1B, debate) are pure: they read `upstream` payloads + the in-memory BM25 index and **touch no DB during synthesis**.

**The one caveat that shaped the design:** a SQLAlchemy `AsyncSession` is **not** safe for concurrent use, and "true parallelism requires … independent state per agent" ([arXiv 2601.10560](https://arxiv.org/html/2601.10560)). So don't gather DB work — gather only the *synthesis*:

> Per DAG layer (modules whose deps are all satisfied): `await asyncio.gather(*synthesize(m) for m in layer)` under a small `asyncio.Semaphore` (cap concurrency to respect Anthropic rate limits), then **persist each result sequentially** on the single session in deterministic order (validate → resolve evidence → `_persist_output`). CP-0, CP-1, CP-1C touch the session during synthesis and sit on the critical path anyway, so they naturally serialize ahead of the fan-out.

**Prompt-cache interaction (checked, it's fine):** the usual "parallel requests miss the cache" warning ([Claude docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)) applies to calls *sharing a prefix*. Here each module has a **distinct** Active Prompt → distinct system block → no shared cross-module cache to lose. The cache that matters (the within-module one-shot repair) stays sequential and still hits.

**Ceiling / upgrade path:** `# ponytail: layer-parallel within one run; if rate limits or many concurrent runs bite, add a global LLM concurrency cap across runs, not just per-run.` Bound it with the semaphore and keep `caos_run_concurrency` in mind (2 concurrent runs × layer fan-out = peak in-flight calls).

**Test left behind:** one `test_*` asserting a run with two independent modules persists both with identical outputs and gate status to the serial baseline (determinism preserved), plus that a synthesis exception in one module still gates only that module.

### 2. Promote Deep Research to a background job

`deepresearch.py:13` already carries the `ponytail:` note: it holds the HTTP connection for a multi-minute, multi-continuation web-search run. Fine for the pilot, but a proxy/edge timeout (Caddy/oauth2-proxy in `deploy/`) will sever long reports. Reuse the existing `run_executor` pattern — enqueue, return an id, poll — rather than inventing a new mechanism. Do this **when** you see truncated/aborted reports or move past the single-user pilot, not before.

### 3. Module-tailored retrieval queries

`synth.py:306` grounds *every* module with one generic query: `"{issuer} {module} financials covenants leverage liquidity"`. A covenant module and a liquidity module retrieve the same chunks. A one-line per-module query string (or reuse the module's `owned_object`/keywords) improves grounding precision and trims wasted grounding tokens. Quality lever more than speed; low effort, low risk.

### 4. Offload synchronous parsing off the event loop

The single uvicorn worker shares one event loop. `pypdf`/`openpyxl` parsing in the ingest path is CPU/IO-bound and synchronous, so a large upload blocks every other request while it parses. The codebase already knows the fix — EDGAR fetch is wrapped in `asyncio.to_thread` (`runner.py:408`). Apply the same to the ingest parse. Negligible benefit at single-user pilot scale; worth it before any concurrent usage.

### 5. uvicorn workers for the Postgres deploy

`run.py` launches one worker. The `QueueWorker` uses `SKIP LOCKED`, so multiple workers/replicas coordinate safely — raising worker count is a clean horizontal lever **if** API latency under concurrent users becomes the bottleneck. Leave at 1 for the pilot.

---

## Evaluated and *not* recommended (YAGNI / cost)

- **Message Batches API (50% off).** **Correction (verified against Anthropic's own docs 2026-06-19):** an earlier draft of this report said batches "have no tool-use support" — that is **wrong**. The [batch-processing docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing) state batches support nearly all Messages features including **tool use and all server tools**, and prompt caching (best-effort, stacks with the 50% discount); the only unsupported params are `stream`, `speed`, `store`, `cache_hint`, `max_tokens:0`, and a couple of betas. So the real disqualifier for the **interactive** path is *latency*, not tools: batches are async (most <1h, but results only when the whole batch finishes or at the 24h expiry), and an interactive run can't wait. Deep Research is also out (it needs `stream`). And a single run only has ~2 LLM modules — no burst volume to batch. **Where it does fit, and now more clearly:** a future **offline eval/regression harness** that re-runs the engine across many issuers — the forced-tool synth calls batch fine, at 50% off with caching stacked.
- **Embeddings / pgvector retrieval.** BM25 is the correct, dependency-free choice for current corpus sizes, and aligns with the no-paid-services constraint. The code already names pgvector as the swap-in behind the same interface. Add hybrid retrieval **only if** retrieval quality measurably degrades on real deals — not speculatively.
- **Cross-module prompt-cache hoisting.** Distinct per-module Active Prompts mean almost no shared prefix to cache across modules; restructuring for it isn't worth the complexity. Current within-module caching already captures the easy win.
- **Frontend bundle work.** Already handled — G2 and remark-gfm are code-split out of first load. No action.

---

## Sources

- [Prompt caching — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Prompt caching announcement — Anthropic](https://www.anthropic.com/news/prompt-caching)
- [Optimizing Sequential Multi-Step Tasks with Parallel LLM Agents — arXiv 2507.08944](https://arxiv.org/pdf/2507.08944)
- [Learning Latency-Aware Orchestration for Parallel Multi-Agent Systems — arXiv 2601.10560](https://arxiv.org/html/2601.10560)
- [Parallel Concurrency in Production AI Agents: DAG Scheduling — Zylos](https://zylos.ai/research/2026-04-26-parallel-concurrency-agent-execution/)
- [When and How to Use the Anthropic Batch API — dev.to](https://dev.to/mukundakatta/when-and-how-to-use-the-anthropic-batch-api-in-your-agent-5fgn)
- [Anthropic API Pricing in 2026 — Finout](https://www.finout.io/blog/anthropic-api-pricing)
- [Dynamic imports and code splitting with Next.js — LogRocket](https://blog.logrocket.com/dynamic-imports-code-splitting-next-js/)
