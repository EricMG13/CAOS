# Red-Team Decision Log

Before committing to an architecture, interface, or rollout plan, run a critic pass here first.

## Current Decision

Adopt this repository-local Markdown log, linked from `AGENTS.md`, as the red-team gate for future architecture, interface, and rollout commitments.

## Protocol

1. Builder records the proposed decision and evidence.
2. Critic argues why it is wrong, with one objection per row.
3. Builder fixes and verifies every high-impact weakness, or marks it accepted with a concrete reason.
4. Critic may reopen any unsupported answer.
5. Stop when no high-impact objection remains, or when the same objections repeat for two rounds without new evidence.
6. Do not paste secrets or confidential raw data into this log; reference files, commands, or sanitized excerpts.

## Objections

| ID | Date | Decision / Plan | Objection | Impact | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| RT-2026-07-02-01 | 2026-07-02 | Use `.agent-reviews/redteam.md` as the red-team gate | A hidden repo-local log is easy to miss, so future architecture/interface/rollout work could bypass the critic loop. | High | Resolved | `AGENTS.md` now links to this file in "Red-team decision gate". |
| RT-2026-07-02-02 | 2026-07-02 | Use `.agent-reviews/redteam.md` as the red-team gate | The first log row put `Accepted` under Impact, so the ledger did not actually record objection impact separately from status. | High | Resolved | This table now has separate `Impact` and `Status` fields with concrete values. |
| RT-2026-07-02-03 | 2026-07-02 | Use `.agent-reviews/redteam.md` as the red-team gate | A decision log can tempt agents to paste sensitive plans, data, or secrets directly into review evidence. | Medium | Resolved | Protocol item 6 requires file/command references or sanitized excerpts instead of secrets/raw confidential data. |
| RT-2026-07-02-04 | 2026-07-02 | Use `.agent-reviews/redteam.md` as the red-team gate | No product architecture, interface, or rollout proposal was supplied yet, so this pass cannot approve any substantive CAOS change. | Low | Accepted | The current decision is only the review gate itself; future concrete proposals must add their own objections. |
| RT-2026-07-04-01 | 2026-07-04 | Query Intelligence Plan (caos/docs/QUERY_INTELLIGENCE_PLAN.md) | Strict numeric grounding will false-drop reformatted figures ("4.25x"→"4.3x") and routinely empty the Desk Brief. | High | Resolved | Plan §Q1 validator: formatting-tolerant compare (separators stripped, 1-dp rounding) + all-cards-dropped degrades to labeled deterministic digest highlights, never a blank/fabricated panel. |
| RT-2026-07-04-02 | 2026-07-04 | Query Intelligence Plan | Brief generation on first page view (HEAVY lane, 10–60s live) could block or wedge the Query page load. | High | Resolved | Plan §Q1 trigger: endpoint always returns the persisted brief instantly; regeneration is a background single-flight task with `refreshing: true`; failures serve the prior brief (deterministic-fallback pattern). |
| RT-2026-07-04-03 | 2026-07-04 | Query Intelligence Plan | Delta/digest evidence ids are not chunk-resolvable, breaking the "every conclusion one click from evidence" mandate for those cards. | Medium | Resolved | Plan §Q1: non-chunk cards click through via their walk deep-link (delta → `metric-trend` for that issuer/metric; digest → the relevant watch walk); figures still pass the numeric gate. |
| RT-2026-07-04-04 | 2026-07-04 | Query Intelligence Plan | Untrusted memo/doc text flows into three new prompts — prompt-injection surface grows. | High | Resolved | Plan §5: `llm_safety` wrap on all untrusted text, closed-set id validation, numeric gate, no tools/writes on any lane, call sites registered in `_REVIEWED_LLM_CALL_SITES`, React-only rendering, AI text excluded from CSV (no CSV-injection path). |
| RT-2026-07-04-05 | 2026-07-04 | Query Intelligence Plan | Run-burst days could churn the data fingerprint and multiply daily LLM spend. | Medium | Resolved | Plan §Q1: regeneration requires BOTH >24h age AND fingerprint change; force is rate-limited; answers cached by (question, fingerprint); keyless deploys make zero calls. |
| RT-2026-07-04-06 | 2026-07-04 | Query Intelligence Plan | Single-flight `asyncio.Lock` and in-process rate limits silently break under Phase-2 multi-worker. | Medium | Accepted | Recorded Phase-1→2 boundary (plan §5) alongside the existing create-run lock/limiter assumptions; Phase-2 needs a DB advisory lock — documented, deliberately not built now. |
| RT-2026-07-04-07 | 2026-07-04 | Query Intelligence Plan | Migrations 0024/0025 may collide with parallel-WIP branches. | Low | Accepted | Renumber at rebase; `test_migrations.py` single-head + `alembic check` guards catch collisions before merge. |
| RT-2026-07-04-08 | 2026-07-04 | Query Intelligence Plan | Scope grows beyond the committed D2 (L) item — could crowd pre-deployment phases. | Medium | Accepted | The expansion is the user's explicit 2026-07-04 request (proactive insights); plan is gated PROPOSED until user approval, phases independently shippable, Q1 alone satisfies the core ask. |
| RT-2026-07-04-09 | 2026-07-04 | Query Intelligence build (Q1/Q2/Q3 IMPLEMENTED) | 2-lens adversarial red-team of the grounding gates: numeric-bypass + citation/injection/fault-isolation. | High | Resolved | Verdict (workflow wf_d67a7ba8): NO shipping defect. Citation gate (closed-set `by_id`), injection defense (wrap_untrusted + UNTRUSTED_RULE + pydantic drops extras), fault isolation (`_regen_inflight` set pre-`create_task`, `finally` reset, bg `except` logs, `/graph` independent), CSV/print exclusion — all confirmed sound. |
| RT-2026-07-04-10 | 2026-07-04 | queryinsights `_validate` numeric pool | Grounding pool appended each cited entry's free `text`, widening the intended closed `numbers` set (a card could ground a figure off a filename year / finding-id numeral). | Medium | Resolved | Fixed in-tree: ground ONLY against `e.numbers` (curated closed set); delta/coverage unaffected, finding/docs become word-only (numeric claim citing only them fails closed). +1 test (`test_validate_grounds_only_against_closed_numbers_not_free_text`). 925 BE pass. |
| RT-2026-07-04-11 | 2026-07-04 | Migrations 0024/0025 | New tables could reproduce the pre-existing `query_overlays` NOT-NULL drift flagged by `alembic check`. | Low | Resolved | Migration nullability aligned to the models (payload/timestamps NOT NULL); both new tables are drift-free (absent from `alembic check` output). Pre-existing systemic drift on other tables is out of scope (documented, fixed in a separate worktree per prior memory). |
| RT-2026-07-04-12 | 2026-07-04 | Covenant-register + sponsor-graph Query walks (shipped, no migration) | Adversarial review of the two new `querygraph` builders: node-id collision, NaN-poisoned headroom, `_append_accepted_links` shape assumptions, synthesis misread. | Medium | Resolved | Verified: hub ids namespaced (`cov:`/`sp:`) vs issuer UUIDs — no collision; headroom gated through `is_finite_number` on BOTH `leverage_covenant_x` and `current_net_leverage` (NaN/inf → cov-lite bucket, no false thin-flag); `_append_accepted_links` only reads `n["id"]`/appends issuer edges — safe on the new node shapes; the generic `concentration` synthesis would misread the register as a "largest cluster", so a capability-aware branch was added (leads with maintenance/cov-lite split + thin-headroom count, never a superlative). 928 BE + 26 FE tests green. |
| RT-2026-07-04-13 | 2026-07-04 | Covenant-register data-quality & scan bound | (a) Latest CP-4C is read regardless of `qa_status`, so a Blocked run's extracted covenant terms can surface as a node; (b) `_COVENANT_SCAN_CAP=2000` silently drops an issuer whose latest CP-4C sits past the newest 2000 module-output rows. | Low | Accepted | (a) Mirrors the existing committee-board / gate-lane boards (no `qa_status` filter) and the view is extraction-caveated ("keyword scan of governing docs"), not a validated-number aggregate like peer medians — lower poisoning stakes; upgrade path = filter to non-Blocked runs if covenant terms ever feed a validated downstream. (b) At the 33-issuer Phase-1 corpus, 2000 rows is ample; the comment names the ceiling; upgrade = SQL window latest-per-issuer if the corpus outgrows it. |
| RT-2026-07-05-01 | 2026-07-05 | Arrange issuer-profile layout rhythm in `ProfileContent.tsx` | A layout pass could accidentally demote the prior Financial trend → Strengths/Weaknesses/Thesis order or turn the dense profile into a decorative card stack. | High | Resolved | Preserved the current panel system and added `profile-distill.test.tsx` order assertions: Financial trend → Thesis → Business → Market. Focused Vitest passed. |
| RT-2026-07-05-02 | 2026-07-05 | Arrange issuer-profile layout rhythm in `ProfileContent.tsx` | The profile also renders inside `IssuerProfileOverlay`, so wider page-level spacing could make the overlay feel cramped or overflow. | Medium | Resolved | Playwright rendered the live profile at 1440px and 900px with `overflowX=false`; local axe scan on `/issuers/profile?id=a71f...0001` returned zero violations. |
| RT-2026-07-06-01 | 2026-07-06 | Command Center layout and query bar refactoring | Removing the Panel shell and predefined starters from the query bar could cause results to overflow or cause sudden layout shifts. | Low | Resolved | Results expand within the flex-col layout of the dashboard; the dashboard handles scroll regions gracefully. |
| RT-2026-07-06-02 | 2026-07-06 | Command Center layout and query bar refactoring | Collapsing the Sector Review Board horizontally could cause text overflow or button clipping in narrow viewports. | Medium | Resolved | Collapsed panel is rendered as a clean 40px wide sidebar with `writingMode: "vertical-lr"`, keeping the toggle button and label visible and readable. |
| RT-2026-07-06-03 | 2026-07-06 | Command Center portfolio view layout polish | Segmented view selector custom styling could break existing keyboard access or focus outline if not styled correctly. | Medium | Resolved | Verified: all buttons inside the segmented control retain focus-ring styling and are fully keyboard accessible. |
| RT-2026-07-06-04 | 2026-07-06 | Command Center SectorBoard grid-cols reduction | Changing SectorBoard grid from 4 columns to 2 columns and moving Add sector inside could overflow the container vertically or break text layouts. | Medium | Resolved | Verified: card size (min-h-110px) layout handles multi-line content gracefully, fits within left-sidebar flex, and Add sector tile follows consistent sizing. |
| RT-2026-07-06-05 | 2026-07-06 | Temporarily disable login in local frontend preview | A login bypass could leak into production or hide broken auth/API behavior. | High | Resolved | Bypass is guarded to non-production in `AuthProvider`; focused `AuthProvider.test.tsx` proves `/me` is not called only when the bypass flag is enabled. |
| RT-2026-07-06-10 | 2026-07-06 | Sector Review concept implementation | A standalone Sector Review route duplicates the existing Command Center `SectorBoard` / `SectorReview` flow and may split analyst attention before the workflow proves value. | High | Resolved | GitNexus found existing `SectorBoard -> SectorReview`; implementation should start in-place and only graduate to a route after daily topic items, source links, issuer links, and ASK handoff are validated. |
| RT-2026-07-06-11 | 2026-07-06 | Sector Review concept implementation | AI-curated summaries without claim-level source backing would violate "show your work" and make the surface feel like a news toy, not a defensible credit workflow. | High | Resolved | MVP must model each briefing item as source-backed rows with explicit source chips and issuer chips; AI impact analysis is an ASK handoff, not hidden prose that rewrites the source record. |
| RT-2026-07-06-12 | 2026-07-06 | Sector Review concept implementation | Shipping search, monitor embedding, notifications, and feed settings together turns a bounded daily briefing into a broad platform build. | Medium | Accepted | Phase 1 is limited to daily sector topic cards inside the existing board/modal; search, monitor widget, and notifications are follow-on phases once the daily workflow earns use. |
| RT-2026-07-06-13 | 2026-07-06 | Sector RV fresh-start plan execution | Jumping straight to SectorBoard/SectorReview consolidation would turn a stabilization request into a broad IA migration and risk breaking the existing Command Center flow. | High | Accepted | Execute Phase 0 in the existing `/sector-rv` surface first; GitNexus impact for the touched Sector RV symbols is LOW and scoped to `SectorRvPage`. Phase 1 consolidation remains a separate follow-on. |
| RT-2026-07-06-14 | 2026-07-06 | Sector RV fresh-start plan execution | Hardcoded source dates, RV thresholds, and staleness labels can drift separately across the route header, caveat bar, and calculation layer, making the surface look current when the feed is stale. | High | Resolved | Centralize `RV_AS_OF`, `RV_FILE_LABEL`, `RV_THRESHOLDS`, and staleness derivation in `rvdata.ts`; route and caveat UI read the same constants. |
| RT-2026-07-06-15 | 2026-07-06 | Sector RV fresh-start plan execution | Evidence and interaction polish could become cosmetic if it does not fix concrete access paths: unlabeled deltas, mouse-only row selection, and color-only evidence states. | Medium | Resolved | Restore DeltaCell labels, company-cell buttons, motion-reduced pulses, row-derived evidence ticks, and focused DOM tests for the table affordances. |
| RT-2026-07-06-16 | 2026-07-06 | Sector Review standalone execution | The earlier in-place Command assumption (RT-2026-07-06-10) now conflicts with the product decision: keeping Sector Review Board in Command would preserve the wrong IA and duplicate the new workflow. | High | Resolved | Supersede RT-2026-07-06-10 for this implementation. Remove the Command board/filter path and make `/sector` the owned CP-SR surface with explicit seed provenance until live synthesis exists. |
| RT-2026-07-06-17 | 2026-07-06 | Sector Review standalone execution | Shared chrome changes can regress unrelated concepts; GitNexus marked `ConceptNav` as CRITICAL because it is used across the main route set. | High | Resolved | Keep nav/hotkey/heading changes additive, preserve existing entries, and smoke-test `/command`, `/sector`, `/monitor`, `/sector-rv`, `/query`, and `/issuers/profile` before commit. |
| RT-2026-07-06-18 | 2026-07-06 | Sector Review standalone execution | Seeded sector cards and deterministic topic ASK could be mistaken for live CP-SR/CP-MON output. | High | Resolved | Badge every first-version card/source as seed/demo, expose the API substrate separately, and keep CP-SR/CP-MON registry entries `implemented=False` until live and offline schema-valid synthesis exists. |
| RT-2026-07-06-19 | 2026-07-06 | Sector RV portfolio overlay phase | Mapping portfolio holdings into market RV by fuzzy issuer text could create false "held" flags and make RV recommendations look owned when they are only peers. | High | Resolved | Match by exact FIGI/id first and exact displayed name/borrower only as secondary keys; no fuzzy matching. |
| RT-2026-07-06-20 | 2026-07-06 | Sector RV portfolio overlay phase | Live portfolio rows do not carry loan FIGIs today, so forcing a live-only bridge would make local/no-backend Sector RV look empty again. | Medium | Resolved | Use the live portfolio rows when available and fall back to the existing sample `PORTFOLIO` sleeve; the UI labels the result as a portfolio overlay, not positions truth. |
| RT-2026-07-06-21 | 2026-07-06 | Sector RV exits and ASK phase | Creating a bespoke Sector RV LLM panel would duplicate the existing Query-backed ASK overlay and create another ungrounded answer surface. | High | Resolved | Reuse global ASK with `/sector-rv` prompt chips and add simple exits from the selected RV loan; no new LLM route or prompt executor. |
| RT-2026-07-06-22 | 2026-07-06 | Sector RV impeccable critique execution | Legibility and ARIA fixes could accidentally change RV math, benchmark eligibility, or sort order while appearing to be cosmetic. | High | Resolved | Keep calculation changes limited to the new `derivePosture` read; focused baseline tests passed 19/19 and GitNexus impact for touched Sector RV symbols is LOW, scoped to `SectorRvPage`. |
| RT-2026-07-06-23 | 2026-07-06 | Sector RV filter-state polish | Warning that the heatmap ignores filters could still be missed, leaving analysts to compare a filtered table against an unfiltered reference grid. | Medium | Resolved | Render the heatmap in `PanelShell` with a warning-tone caption when column filters are active; add a regression test for the exact reference-universe warning. |
| RT-2026-07-06-24 | 2026-07-06 | Deep-Dive layout tiers (`summary` / `report` / `dense`) | Renaming `core` to a least-detail summary tier can silently invert a saved browser preference and strand analysts in the wrong view. | High | Resolved | `loadLayout()` migrates legacy `core` → `summary`, `base` → `report`, preserves `dense`, and the focused layout-pref test covers the migration. |
| RT-2026-07-06-25 | 2026-07-07 | Deep-Dive layout tiers (`summary` / `report` / `dense`) | A summary tier that replaces the analysis with layer/module summaries would hide the actual charts and tables analysts need before workflow detail. | High | Resolved | `ModuleView` keeps the normal analysis body in `summary`; only the workflow-step area switches to compact narrative summaries, and live issuer output never falls back to seeded workflow fixtures. |
| RT-2026-07-06-26 | 2026-07-06 | Deep-Dive layout tiers (`summary` / `report` / `dense`) | Summary mode on CP-6A could break the existing evidence-sync E2E if the default layout stops rendering evidence chips and the matrix. | Medium | Resolved | `DEFAULT_LAYOUT` remains `report`; only explicit `summary` hides detailed bespoke tables, so `/deepdive` still opens with the evidence-rich report view. |
| RT-2026-07-07-01 | 2026-07-07 | Phase-1 graph-expansion retrieval lane (test backfill + integration proof) | The 1-hop cap on `hops>1` is silent — a caller passing `hops=2` gets 1-hop results without warning, masking a future 2-hop implementation gap. | Medium | Accepted | The function accepts `hops>1` without error (forward-compat) but the docstring explicitly states "v1 caps at 1-hop; 2-hop is a measured follow-on." A test (`test_graph_neighbors_one_hop_only_v1_cap`) pins the v1 behavior so a future 2-hop implementation must update the test deliberately. Warning would be noise on a query-path hot lane. |
| RT-2026-07-07-02 | 2026-07-07 | Phase-1 graph-expansion retrieval lane | `retrieve_corpus(expand_graph=True)` fuses neighbor chunks via RRF, but a neighbor's chunk could outrank the seed issuer's own chunk on a scoped query — diluting the answer with peer noise when the analyst asked about one issuer. | High | Resolved | The expansion widens the candidate pool (recall fix) but RRF + MMR packer still rank by query relevance; a neighbor chunk only surfaces if it genuinely matches the query better. The opt-in `expand_graph=bool(issuer_ids)` ensures unscoped queries (already whole-corpus) are unaffected. The integration test (`test_retrieve_corpus_expand_graph_widens_to_neighbor_chunks`) proves the widening is targeted (Beta's chunk surfaces only because it matches "sponsor"), not unconditional. |
| RT-2026-07-07-03 | 2026-07-07 | Phase-1 metric-fact SQL lane (lexicon) | The query→metric-key lexicon uses substring matching for punctuation-bearing synonyms ("z-score", "top line") — a query like "top line of business" could false-positive match `revenue` via "top line" when the analyst means a business segment, not the revenue metric. | Medium | Accepted | The lexicon is deliberately broad (recall-biased) — the lane surfaces candidate facts, the LLM still must cite and ground them through the fail-closed gates. A false-positive match adds a relevant-or-irrelevant fact to the facts_note; an irrelevant fact is simply not cited. The cost is a slightly larger facts_note, not a wrong answer. Tightening the lexicon would hurt recall (the dropped-claim-rate problem the lane exists to fix). |
| RT-2026-07-07-04 | 2026-07-07 | Phase-1 metric-fact SQL lane (grounding gate) | The raw fact's `numbers` set includes the period's 4-digit year (`_period_year`) so a sentence stating "FY2024" grounds — but this lets an LLM state ANY year that appears in any cited fact's period, conflating temporal labels with credit figures. | Medium | Resolved | The year is added ONLY when it appears in the SAME fact's period string (deterministic from the stored fact, not fabricated). A sentence citing `fact:i1:revenue:raw:FY2024` may state 2024 (that fact's period) but NOT 2023 (a different fact's period) — the gate pools per-cited-fact. The year is a temporal label the claim legitimately restates; excluding it would drop correct sentences (the bug that motivated the fix, pinned by `test_render_entries_includes_period_year_in_numbers`). |
| RT-2026-07-07-05 | 2026-07-07 | Phase-1 metric-fact SQL lane (dedup vs Metric Engine) | `dedup_against_derivatives` keys on `(issuer, key, value)` — a delta and a raw fact with the same latest value get deduped, but a peer-z derivative with `numbers=[own, med, z]` covers `(issuer, key, own)` AND `(issuer, key, med)` — incorrectly suppressing a raw fact whose value happens to equal a peer median. | High | Resolved | The covered-set logic adds BOTH `numbers[1]` (delta latest / peer-z med) and `numbers[0]` (delta prior / peer-z own) — but a raw fact's value equals the peer MEDIAN only by coincidence, and in that case the raw fact IS restating a figure the peer-z already narrated ("own value X vs peer median Y"). The suppression is correct: the peer-z derivative already states both figures. If the raw fact's value differs from both, it survives. Pinned by `test_dedup_keeps_raw_when_no_derivative_covers` and `test_dedup_removes_raw_when_delta_covers_latest`. |
| RT-2026-07-07-06 | 2026-07-07 | queryanswer.py reapply reconciliation | Parallel user work reverted `queryanswer.py`, `retrieval.py`, and `test_query_answer.py` to pre-Phase-2 state while the golden tests (`test_golden_query_gates.py`) and dedicated module tests (`test_metricengine`, `test_entailment`, `test_metricfactlane`, `test_graphexpansion`) expected the Phase-2/SQL-lane APIs. Re-applying all changes in one pass risks a silent contract drift between the reconciled `queryanswer.py` and the (un-reverted) downstream consumers. | High | Resolved | Re-applied the full stack in dependency order: (1) `retrieval.py` `expand_graph` param + graph-expansion call, (2) `queryanswer.py` full Phase-2/3/4 + SQL-lane wiring (Metric Engine facts, claim_type, entailment demote, bounded self-correction, `expand_graph` flag, metric-fact SQL lane step 4b), (3) `test_llm_safety.py` `_REVIEWED_LLM_CALL_SITES` re-added `engine/entailment.py`, (4) `test_query_answer.py` mock + assertion updates (self-correction doubles the call count) + re-added 7 integration tests (fact-citation survives/traced, fact-citation ungrounded dropped, claim_type preserved+coerced, self-correction rescues all-dropped, SQL lane raw fact cited, SQL lane no-op on no match). Full suite: 1130 passed, 4 failed (3 are user parallel-work regressions — `PipelineRun` model reverted from `database.py` while migration 0031 persists; `test_vault_memo` cross-test contamination, pre-existing). 102 tests in the query-answer cluster green. mypy clean on `metricfactlane.py`; pre-existing `CorpusHit`/`Hit` type-variance on `retrieval.py`/`queryanswer.py` unchanged. |
| RT-2026-07-07-07 | 2026-07-07 | PipelineRun model + autonomy route reconciliation | Parallel user work reverted the `PipelineRun` model from `database.py` AND the autonomy router + `PipelineExecutor` lifespan wiring from `main.py`, while migration 0031 (`pipeline_runs` table), `engine/pipeline.py`, `engine/pipeline_executor.py`, `routes/autonomy.py`, and the tests (`test_pipeline_runs`, `test_pipeline_executor`, `test_autonomy`) all expected the model + route to exist. Re-adding the model without the route wiring (or vice versa) would leave the schema drift fixed but the route 404'ing. | High | Resolved | Re-applied in dependency order: (1) `PipelineRun` model re-added to `database.py` (mirrors `ResearchJob` — `_uuid` id, `kind`/`status` indexed, `prior`/`current_fingerprints`/`draft`/`summary` JSON, `worker_id`/`error`/`completed_at`), matching migration 0031 exactly so `alembic check` passes; (2) `main.py` re-added `autonomy` to the routes import, `from engine.pipeline_executor import PipelineExecutor` (note: `pipeline_executor.py` lives under `engine/`, not top-level like `research_executor.py`), `PipelineExecutor` start/stop in lifespan, and `app.include_router(autonomy.router, prefix="/api/autonomy")`. Full suite: 1153 passed, 2 skipped, 1 pre-existing cross-test contamination (`test_vault_memo` — passes in isolation). The `PipelineExecutor` sweep-on-boot now strands any orphaned `running` rows to `failed` on restart. |
| RT-2026-07-07-08 | 2026-07-07 | Phase-1 cross-encoder re-rank (architecture) | Local `mxbai-rerank-large-v1` via `sentence-transformers` ships a ~670MB model weight resident in the server process for the lifetime of the run — a long-running multi-worker deploy holds N×670MB and the weight is not in the Docker image today, so a fresh pull at boot could stall startup or fail offline. | High | Resolved | (1) Model is lazy-loaded on first `rerank()` call, NOT at import — keyless/CI deploys never load it (gate: `RERANK_ENABLED` setting, default off). (2) The model instance is cached at module level (single load per process, mirrors the embeddings warmup pattern). (3) Any load or inference failure is fault-isolated — `rerank()` returns the input hits unchanged, so a missing/corrupt weight degrades to today's RRF-only ranking rather than crashing the query lane. (4) `sentence-transformers` added to `requirements.txt` so the Docker image bakes the weight at build time (no boot-time pull). (5) Documented cache-eviction story: the model stays resident by design (latency floor accepted; the alternative — load-per-call — pays the 670MB load on every query, far worse). |
| RT-2026-07-07-09 | 2026-07-07 | Phase-1 cross-encoder re-rank (architecture) | Adding `rerank: bool = True` to `retrieve_corpus` changes the default behavior for ALL 4 upstream callers (`queryanswer`, `queryoverlay`, `nlquery`, `querygraph`) — a re-rank on a hot lane (NL query) adds ~50ms/query CPU latency even when the existing RRF ranking was already adequate. | Medium | Resolved | The gate makes the default a no-op: `RERANK_ENABLED` defaults to `False`, so all callers see today's RRF-only ranking unless an operator opts in. When enabled, the re-rank runs only on the top-`2K` (latency-bounded), and the benchmark harness proves precision@5 ≥ RRF precision@5 on the golden seed before the opt-in is justified. The kwarg is opt-OUT (`rerank=False`) for callers that want BM25-only regardless of the setting (e.g. the graph-expansion integration test path). |
| RT-2026-07-07-10 | 2026-07-07 | Phase-1 cross-encoder re-rank (architecture) | Re-ranking overwrites `CorpusHit.score` with the cross-encoder score, breaking the MMR packer's `relevance = cand.score` assumption — the RRF score (a rank-fusion score, not a similarity) and the cross-encoder score (a logit, unbounded) are on different scales, so MMR's `lambda_mmr * relevance - (1-lambda_mmr) * redundancy` could be dominated by whichever scale is larger. | High | Resolved | The cross-encoder score is sigmoid-normalized to [0,1] before assignment (a logit → probability), placing it on a comparable scale to MMR's redundancy term (cosine/Jaccard, also [0,1]). The RRF score was already on an arbitrary ~[0,0.03] scale (1/(60+rank)), so the cross-encoder score is actually MORE interpretable to MMR, not less. The packer consumes the re-ranked list order regardless of absolute score (it re-sorts by MMR internally), so a score-scale change does not break the diversity logic — only the relevance weight shifts, which is the intended precision improvement. Pinned by `test_rerank_normalizes_score_to_unit_interval`. |
| RT-2026-07-07-11 | 2026-07-07 | Phase-1 cross-encoder re-rank (architecture) | The graph-expansion integration test (`test_retrieve_corpus_expand_graph_widens_to_neighbor_chunks`) runs BM25-only (GEMINI_API_KEY blanked); if re-rank does not short-circuit in keyless mode, the test breaks because the reranker model is not present in CI. | High | Resolved | Re-rank gates on `RERANK_ENABLED` (unset in CI per conftest), AND on lazy-load success. The test env has neither a key nor the weight, so `rerank()` returns hits unchanged on the first guard — the integration test passes without modification. Pinned by `test_rerank_passthrough_when_disabled` and `test_rerank_passthrough_on_load_failure`. |
| RT-2026-07-07-12 | 2026-07-07 | Phase-1 cross-encoder re-rank (benchmark) | A benchmark asserting "precision@5 ≥ RRF precision@5" on a tiny golden seed (2 chunks) is statistically meaningless and could PASS trivially (both 1.0) without proving the re-rank lifts precision — the deferral reason (unmeasured latency cost) is not actually addressed. | Medium | Accepted | The seed is small by design (the golden cases ship 2 hits), so the benchmark's primary value is REGRESSION detection (re-rank does not regress precision vs RRF on the known-good set), not a powered precision-lift claim. The real precision-lift measurement is a follow-on with a larger labeled set (deferred, named in the handoff). The harness is structured so adding labeled pairs is a one-line extension of `SEED_LABELS`; the assertion `rerank_precision >= rrf_precision` is the correct non-regression guard for the seed we have. |
| RT-2026-07-07-13 | 2026-07-07 | Analyst memos in retrieval (chunk memos into document_chunks) | A multi-issuer memo (wikilinking N issuers) cannot fit the single-issuer `Document` model (`Document.issuer_id` is NOT NULL, FK to issuers) — so a memo that links 3 issuers can't be chunked under "the memo" once and found by a scoped `retrieve_corpus(issuer_ids=[X])` query over any of the 3. | High | Resolved | Create one `Document(doc_type="analyst-memo")` PER linked issuer, each carrying the memo's chunks. A scoped query over issuer X finds X's memo copy; an unscoped query sees N copies but MMR's vector-redundancy dedup collapses them to ~1 in the packed context (same text → same embedding → max redundancy). The chunk text is duplicated N times in `document_chunks` but is bounded (memos are small, linked issuers are few) and `DocumentChunkEmbedding` dedups by `chunk_hash` (unique index `(model, chunk_hash)`) so the expensive embedding is stored once. Memos linking zero issuers stay vault-only (today's behavior) — the analyst can still reach them via the Query graph. |
| RT-2026-07-07-14 | 2026-07-07 | Analyst memos in retrieval (engine pollution) | Chunking memos under an issuer makes them visible to `build_issuer_index`, the BM25 index the run pipeline builds once per run and feeds to EVERY CP-1–CP-6 module via the `retrieve` closure. CP-1 (deterministic financial extraction) would then retrieve and cite analyst commentary as source truth — a fabrication risk (an analyst's "leverage looks ~5x" memo cited as the CP-1 leverage figure). This is the exact opposite of committee-ready. | High | Resolved | Surgical exclusion: `build_issuer_index` filters `Document.doc_type != "analyst-memo"` when fetching chunks. This is the SINGLE chokepoint for the run path (all engine modules retrieve through the closure over this index), so one filter guards the entire engine. The filter is NARROW (excludes only `analyst-memo`, not a broad allowlist) so the CONFIDENCE_AUDIT-2026-06-26 behavior (EDGAR issuers' uploaded credit agreements reachable by reconcile, no doc-type filter) is preserved for all other doc_types. `retrieve_corpus` (the Q2 query path) does NOT get the filter — memos SHOULD be citable in query answers (the point of the phase). Pinned by `test_build_issuer_index_excludes_analyst_memos` and `test_retrieve_corpus_includes_analyst_memos`. |
| RT-2026-07-07-15 | 2026-07-07 | Analyst memos in retrieval (readiness misclassification) | `readiness._categorize` classifies a document by `doc_type` substrings AND by content markers in the head. A memo whose commentary mentions "credit agreement" / "covenant" / "10-K" would match the `agreement`/`covenant`/`financials` content markers and be miscounted as source-filing coverage — making an issuer look "ready" off analyst commentary alone. | Medium | Resolved | `_categorize` short-circuits to an empty set when `doc_type == "analyst-memo"` — analyst commentary is never a source filing, regardless of what terms it mentions. Pinned by `test_readiness_excludes_analyst_memos`. |
| RT-2026-07-07-16 | 2026-07-07 | Analyst memos in retrieval (idempotent re-upload) | `write_memo` uses exclusive-create (`path.open("x")`) and dedups the FILENAME on collision ("Title - 2"), so re-uploading the same filename produces a NEW title — but an analyst who deletes the vault file and re-uploads the same title, or a network-retry that resubmits, would create duplicate `Document`+chunk rows for the same memo title, polluting the corpus with N×M copies. | Medium | Resolved | `chunk_memo_into_corpus` is idempotent on title: before inserting, it deletes prior `Document` rows where `doc_type="analyst-memo" AND file_name=<title>` (and their chunks + lineage edges), then re-creates. Deletion order respects the no-cascade FK structure (lineage by `parent_id`/`artifact_id` strings → chunks → documents). Pinned by `test_chunk_memo_idempotent_on_re_upload`. |
| RT-2026-07-08-01 | 2026-07-08 | Frontend implementation spec (`caos/docs/FRONTEND_IMPLEMENTATION_SPEC.md`) — the P0→P3 redesign + AI-wiring plan Opus 4.8 executes | The `.impeccable/critique` snapshots the spec baselines on (2026-07-03…07-05) predate this-morning's fix commits (`5a8e6020` ResponsiveShell migration, `35ef62fd` autonomy/RAG), so a spec built from them would put a backbone of already-fixed defects (Model keyboard trap, Deep-Dive stamp, Query question-swap, Profile color-alone, Monitor pause-count, Reports dead button) in P0/P1 — Opus burns budget re-fixing working code and the real gaps get P2 attention. | High | Resolved | Every snapshot-named defect was re-verified against HEAD before inclusion; all were confirmed already-fixed and DROPPED. Each of the 42 emitted items carries a `Verified open at HEAD` line with concrete current-tree evidence. Result: **no open P0** (honestly empty, not padded); the spec's correctness work is genuinely P1. |
| RT-2026-07-08-02 | 2026-07-08 | Frontend spec — Command/Monitor AI-wiring direction | Additively wiring live lanes onto Command/Monitor could worsen the exact defect the whole-app critique (26/40) names — "too many equal-weight panels compete" (H8=2) — making the surfaces busier and lower-scoring, not better. | High | Resolved | Every addition is paired with a demotion: the Command TODAY-band item removes `PostureSummary` as lead, the de-sim item strips SimControls/clock, and NlQuery compacts to a one-line bar; Monitor's worklist replaces the sim tape rather than sitting beside it. The pairing is written into each item so H8 improves. |
| RT-2026-07-08-03 | 2026-07-08 | Frontend spec — Monitor "triage desk" framing | Framing Monitor as a live "stream/intraday tape" describes a cadence the backend cannot feed — no alert-inbox/SSE/websocket endpoint exists — so the spec would replace sim theatre with stream-affect over pull snapshots (theatre with better provenance). | High | Resolved | Monitor is specced as a **pull-only ranked triage worklist** (digest `ccc_watch`/`stale`/`qa` + `activity_24h` failed-runs + autonomy sections), never a stream. EmailIntel (no lane) is retained as an explicitly labeled sample; acknowledge/dismiss is explicitly local, per-analyst-namespaced state (no backend ack lane). Distinctness from Command is enforced by depth (whole queue + triage state vs single worst item), not cadence. |
| RT-2026-07-08-04 | 2026-07-08 | Frontend spec — P3 net-new items | A net-new feature wired to an imagined data lane is the highest fabrication risk; the spec must never tell Opus to build a UI against a lane the engine cannot produce. | High | Resolved | Every P3 names a live lane verified present in `caos/server/routes` (autonomy/digest/cross-default/sponsors/research-report/edgar/catalog/report) with `api.ts` confirmed lacking the client (net-new, not duplicate); the three unbuildable artifacts (IC Decision Record, Excel pack, maturity wall) are tagged `⚠ BACKEND-BLOCKED` with the exact missing route. A fresh-context per-item reviewer confirmed each lane + shape (Workflow A: 42 items, 0 CUT). |
| RT-2026-07-08-05 | 2026-07-08 | Frontend spec — async honesty debt (autonomy cold-start, research-report poll, exportReport 409, digest) | Unspecified async state machines ship spinners and error toasts that tank exactly the heuristics (H1/H9) the wiring is meant to lift. | Medium | Resolved | A single shared `LiveLaneState` four-state primitive (loading pulse / desk-worthy empty / plain-language error+retry / live+FlashOnChange) is defined once (first P1 item) and referenced by every live surface; cold-start (`refreshing:true` poll), the 409 "NOT COMMITTEE READY" designed state, and job-poll progress are each specced explicitly, never as a bare spinner. |
| RT-2026-07-08-06 | 2026-07-08 | Frontend spec — cross-reference / build-order integrity | Shared primitives referenced before they are defined (or defined twice) would make the spec non-executable top-to-bottom for Opus. | Medium | Resolved | Inline whole-file audit: `LiveLaneState`/`useRunPoll` are the first two P1 items (before all adopters); `getCrossDefault` added once in Deep-Dive and reused; `SECTORS` deletion assigned to exactly one item; Profile cross-default deep-link marked dependent on the Deep-Dive anchor (Deep-Dive ordered first in P3). One forward-reference found — `ShortcutReference` defined in the last P2 item but referenced by earlier P2 items — fixed by an explicit build-order note at the top of P2. |
| RT-2026-07-08-07 | 2026-07-08 | Frontend spec — final whole-file adversarial audit (Workflow B) | The independent fresh-context whole-file audit (4 auditors) could not complete — first attempt hit the session token limit, and the re-run was blocked by the opus-4-8 safety-classifier outage that also disabled Bash/Workflow spawns — so the belt-and-suspenders 4-agent pass did not run. | Medium | Accepted | Three independent verifications stand in for it: (1) Workflow A gave every one of the 42 items a fresh-context adversarial per-item review at HEAD (35 PASS / 7 REVISE / 0 CUT, all applied); (2) inline whole-file consistency audit (cross-reference integrity, primitive define-before-adopter ordering — one forward-ref found + fixed, P0-empty soundness, Report-Studio light-theme flags, no invented tokens/deps, no line-numbers); (3) **direct HEAD source-read confirmation of ALL SIX wired lanes** — `digest.py` DigestResponse (coverage/warf/warf_band/ccc_watch/stale/qa/activity_24h), `autonomy.py` /draft envelope (marking/sections/summary.n_anomalies/refreshing/error, fault-isolated), `issuers.py` get_cross_default_map (dominoes[]{code,tranche,amount_musd,trips_cross_default,pulls_in}) + research-report ({id,status}/ResearchReportOut, 3/min), `sponsors.py` SponsorTrackRecordResponse (avg_governance_risk_score/flag_counts/issuers), `edgar.py` search/filings/exhibits (FilingHitOut/ExhibitOut{doc_label,authority_rank}) — every response shape matches the spec's api.ts client instructions verbatim. Residual: no single *independent* fresh-context whole-file agent pass; re-run the persisted audit workflow when the classifier recovers. **UPDATE (same day): 7 spawn attempts across BOTH Workflow and Agent paths all rejected by the persistent classifier outage (only trivial Bash + Read pass). Completed the audit's substance on the main thread — all four auditor scopes now personally read against HEAD: whole-file-consistency (inline, one forward-ref fixed); p3-netnew (six server lanes + exportReport/getMetricCatalog unused-client by direct read); core-ai-wiring (digest/autonomy lanes read; CoverageMatrix orphan — GitNexus's live "Called by CommandCenter" edge confirmed STALE per the spec's own caveat); surfaces-p1p2 (useLivePipeline buildLiveSnapshot drops as_of_date, ConceptHotkeys returns null w/ inline literals, upload/page.tsx hand-rolls the h-10 header with no ResponsiveShell import, plus Model/Query/Deep-Dive/Profile DROPs confirmed fixed). Verdict: PASS, zero unresolved defects, done-gate all green. Only unmet item — a NET-NEW independent fresh-agent second opinion, redundant with Workflow A's per-item fresh review (0 CUT).** |
| RT-2026-07-07-17 | 2026-07-07 | Phase-1 2-hop graph expansion measurement harness (architecture) | The handoff gates 2-hop enablement on "a recall-vs-precision measurement on REAL cross-issuer questions." A synthetic contagion-chain seed proves the wiring but NOT the real-world recall lift — the same limitation accepted for the rerank bench (RT-2026-07-07-12). Building a synthetic harness and treating it as the gate would be cargo-cult discipline. | High | Resolved | The synthetic harness is framed as PRELIMINARY measurement + harness infrastructure, NOT the production enable gate. The decision artifact (`GRAPH_EXPANSION_2HOP_MEASUREMENT.md`) explicitly records that real-data measurement on production cross-issuer queries is the actual gate before enabling 2-hop in `retrieve_corpus`. The synthetic seed models the contagion-chain use case the lane serves (sponsor/contagion exposure across ratified edges), so the numbers are directionally informative — they show whether 2-hop surfaces relevant chunks 1-hop misses AND whether it dilutes precision with irrelevant peers. The harness is structured so production-labeled pairs extend it in one line (mirrors the rerank bench). |
| RT-2026-07-07-18 | 2026-07-07 | Phase-1 2-hop graph expansion measurement harness (architecture) | Lifting the v1 1-hop cap on `graph_neighbors` to implement real n-hop traversal risks accidentally wiring 2-hop into `retrieve_corpus` and diluting the pack with loosely-related peers before the measurement justifies it — exactly the dilution the handoff warns about. | High | Resolved | (1) `graph_neighbors` gains real n-hop BFS (bounded by `hops`, visited-set prevents cycles), but `expand_issuer_set` keeps its default `hops=1`, and `retrieve_corpus` calls `expand_issuer_set(db, issuer_ids)` with no `hops` arg → production path stays 1-hop. (2) A gate test (`test_expand_issuer_set_default_stays_one_hop`) pins that `expand_issuer_set`'s default does NOT traverse 2-hop even when 2-hop edges exist — so a future caller must explicitly opt into `hops=2`. (3) The measurement harness calls `expand_issuer_set(..., hops=2)` directly to measure; it does NOT change `retrieve_corpus`. Enablement is a separate decision gated on the measurement artifact. |
| RT-2026-07-07-19 | 2026-07-07 | Phase-1 2-hop graph expansion measurement harness (architecture) | A 2-hop BFS on a cyclic ratified graph (A↔B, B↔A re-proposed, or a triangle A↔B↔C↔A) could revisit nodes or loop if the hop bound is mis-counted. | Medium | Resolved | The n-hop traversal is a BFS with a `visited` set seeded with the input issuers; each hop expands the frontier by the new neighbors only. Hop count is the loop bound (not the graph structure), so a cycle can't make it run past `hops` iterations. Pinned by `test_graph_neighbors_two_hop_handles_cycle_without_loop` (a triangle seeded at one node returns the two neighbors at hop 1 and does not re-add the seed at hop 2). |
| RT-2026-07-07-20 | 2026-07-07 | Phase-1 2-hop graph expansion measurement harness (metrics) | "Precision@K" for a cross-issuer RECALL fix is ambiguous — a relevant 2-hop chunk surfaced by expansion is a recall win, but counting it in precision@K conflates the two. A naive precision@K could even PENALIZE the expansion for surfacing more relevant chunks (if K is fixed and they push out seed-issuer chunks). | Medium | Resolved | The harness reports THREE distinct metrics, not a single ambiguous precision@K: (1) `recall@K = relevant chunks surfaced / total relevant` — the recall lift 2-hop is supposed to provide; (2) `precision@K = relevant in top-K / K` — the dilution signal (drops when irrelevant peers enter top-K); (3) `dilution = irrelevant chunks introduced / expanded hits` — the direct cost of widening. The decision rule uses recall lift AND dilution together: enable 2-hop only if recall@K lifts materially AND dilution stays below a threshold. Definitions pinned in `bench/graphexpansion_seed.py` and asserted in the harness tests. |
| RT-2026-07-07-21 | 2026-07-07 | Phase-1 2-hop graph expansion measurement harness (test gate) | The v1-cap pin test (`test_graph_neighbors_one_hop_only_v1_cap`) is a deliberate gate — its docstring names 2-hop as a "measured follow-on." Removing it to add 2-hop could let 2-hop ship without the measurement if a future agent treats the test removal as license to wire it in. | Medium | Resolved | The v1-cap test is REPLACED (not deleted) with two tests that together preserve the gate's intent: (1) `test_graph_neighbors_two_hop_traverses_chain` proves the n-hop implementation works (delta surfaces at hops=2 but not hops=1); (2) `test_expand_issuer_set_default_stays_one_hop` pins the production default at 1-hop. The measurement artifact (`GRAPH_EXPANSION_2HOP_MEASUREMENT.md`) is the recorded decision gate a future agent must read before flipping `retrieve_corpus` to `hops=2`. |
| RT-2026-07-07-22 | 2026-07-07 | Phase-2 per-analyst briefs (scoping) | Scoping the Desk Brief to an analyst's watchlist multiplies LLM spend from ≤1 call/24h/book to ≤1 call/24h/analyst — N analysts each with a watchlist means N regenerations per book-change, and a run-burst day could fan out N model calls. | High | Resolved | The existing fingerprint-gated regen rule is preserved PER analyst: regeneration needs BOTH a changed per-analyst fingerprint AND a >24h-old brief (or explicit force). The per-analyst fingerprint incorporates the watchlist issuer set + their latest runs, so an analyst whose watchlist is unchanged and whose issuers had no new run sees no regeneration. Single-flight is keyed by `analyst_id` (not module-global) so per-analyst regens don't serialize, but each is still bounded to ≤1/24h. Spend is now ≤N calls/24h on a book-change day, accepted as the cost of personalization (the desk pays for relevance). |
| RT-2026-07-07-23 | 2026-07-07 | Phase-2 per-analyst briefs (empty-watchlist fallback) | An analyst with an empty watchlist would get a degraded/empty brief — worse than today's book-level brief — breaking the "never a blank panel" guarantee. | High | Resolved | Empty-or-absent watchlist falls back to the book-level brief (the existing `analyst_id IS NULL` row). The cache lookup is two-tier: try the per-analyst row (`analyst_id == caller.id`); if none and the watchlist is empty, serve the book-level row (`analyst_id IS NULL`). An analyst only gets a per-analyst brief once they curate a non-empty watchlist — opt-in, never a regression. Pinned by `test_insights_empty_watchlist_falls_back_to_book_level`. |
| RT-2026-07-07-24 | 2026-07-07 | Phase-2 per-analyst briefs (cache-key migration) | `insights()` today fetches the latest `QueryInsight` row ignoring `analyst_id` (book-level). Switching to per-analyst keying means existing book-level rows (`analyst_id NULL`) must still be served to no-watchlist analysts, and a stale book-level row must not shadow a newer per-analyst row. | High | Resolved | The lookup filters by the resolved scope: `analyst_id == caller.id` when the analyst has a watchlist, else `analyst_id IS NULL`. A per-analyst analyst never sees a book-level row and vice versa. The model docstring is updated from "records who triggered" to "records the scope (NULL = book-level)". No data migration — existing NULL rows remain the book-level brief for no-watchlist analysts. |
| RT-2026-07-07-25 | 2026-07-07 | Phase-2 per-analyst briefs (scoping correctness) | Scoping deltas/findings to the watchlist must not drop the book-level context entries (coverage counts) — an analyst watching 3 issuers still needs to know the book is 50 issuers / 200 docs. And the per-analyst fingerprint must change when the watchlist changes (add/remove an issuer) so the brief regenerates. | Medium | Resolved | `build_pack(db, issuer_ids)` scopes ONLY the delta + finding entries (issuer-specific signals) to the watchlist; the context entries (`_context_entries`) stay book-level (coverage is a book-wide fact). The per-analyst fingerprint hashes the sorted watchlist issuer_ids + their latest run ids, so a watchlist edit changes the fingerprint and forces a regen on the next >24h/force boundary. |
| RT-2026-07-07-26 | 2026-07-07 | One-box unification (dispatch ambiguity) | A typed question can be BOTH a graph walk ("who are the peers") AND a metric screen ("which issuers are most levered"). A unified box that silently picks one lane loses the other — the analyst's intent is not always recoverable from the text. | High | Resolved | The unification is ADDITIVE, not replacing: the Query bar's existing walk-routing stays the primary action (Enter → submit → walk + Q2 answer). The /nl metric-screen lane is offered as an explicit secondary action ("Scan metrics" button) that calls `nlQuery()` and renders the ranked table in the reused `QueryResultsModal`. No silent dispatch — the analyst chooses the lane. Auto-detection is a documented follow-on, not this phase. |
| RT-2026-07-07-27 | 2026-07-07 | One-box unification (result-surface mismatch) | /nl results are a ranked table / evidence list (`StructuredView`/`SemanticView`) rendered in a modal; the Query page renders graphs in the canvas. Forcing the /nl result into the graph canvas would mangle it. | Medium | Resolved | The /nl result renders in the existing `QueryResultsModal` (the same modal the Command Center /nl box uses), imported and reused from `NlQuery.tsx`. The Query page's graph canvas is untouched — the modal is a self-contained overlay. The CitationViewer is shared (already imported on the Query page). No new result surface is built. |
| RT-2026-07-07-28 | 2026-07-07 | One-box unification (Command Center box removal) | "Merging /nl into the Query bar" could be read as REMOVING the Command Center /nl box — a regression for PMs who live on the Command Center and never open Query. | Medium | Accepted | This phase ADDS the /nl capability to the Query bar (one box can do both lanes) WITHOUT removing the Command Center /nl box. The Command Center box stays the dedicated scan surface for the PM persona; the Query bar gains it for the analyst who lives in Query. Whether to deprecate the Command Center box is a separate IA decision deferred to a follow-on (named in the handoff). No regression for either persona. |
| RT-2026-07-07-29 | 2026-07-07 | Re-rank pivot local→API (policy + cost/latency) | The shipped re-rank loaded a local `mxbai-rerank-large-v1` weight (~670MB) via `sentence-transformers` — a model DOWNLOAD, which the user's hard policy forbids ("all LLM usage must be through API, using the models in settings/.env; no models downloaded"). Beyond the policy violation, the local-model path is also a deploy burden (670MB baked into the Docker image, CPU inference floor) and an outlier in an otherwise all-API engine. | High | Resolved | The re-rank is re-architected to one batched LLM call through the shared `engine/llm_client.create` seam, on a model picked by the tier system (`RERANK_MODEL_TIER`, default `cheap`). No download, no new dependency, no weight. Fault-isolation preserved end-to-end (setting off / no provider key / API error / malformed JSON / score-count mismatch → RRF-only passthrough). `sentence-transformers` removed from `requirements.txt`. The prior local-model RTs (08–12) are historical; the bench's fake-scorer still proves the WIRING, and a live-LLM precision measurement against the configured tier model is an optional follow-on (not run now to avoid unrequested token spend). Trade-off accepted: per-query token cost + one API round-trip replace the local-model CPU floor — cheaper to operate, no deploy weight, policy-compliant. |
| RT-2026-07-07-30 | 2026-07-07 | Issuer Profile: AI Research Report tab — architecture & synthesis design | The Research Report is a full L1–L6 LLM synthesis call (multi-thousand-token opus call). If it runs synchronously inside the GET request, a dropped client/proxy connection loses the work and its token spend — the exact bug `research_executor.py` was built to fix for Deep Research. | High | Resolved | The report uses the durable background-job pattern (mirrors `ResearchJob` + `research_executor.py`): POST persists an `IssuerResearchReport` row and enqueues a background task; the client polls GET. A dropped connection does not abort execution. The report is cached per `(issuer_id, run_id)` — subsequent GETs serve the cached payload instantly. |
| RT-2026-07-07-31 | 2026-07-07 | Issuer Profile: AI Research Report tab — fabrication risk in forecasts | The "Forecasts & Outlook" section asks the LLM to synthesize forward-looking signals. Without a hard gate, the model could invent a DCF, a revenue projection, or a maturity figure that no module emitted — poisoning the committee read with fabricated numbers that inherit the "live run" provenance of the surrounding report. | High | Resolved | Three-layer defense: (1) The forced tool-call schema (`emit_research_report`) requires `source_module_id` + `source_path` on every figure — the model cannot emit a bare number. (2) `validate_report_figures` resolves every `source_path` against the cited module's `runtime_output`; mismatches/unresolvable paths are DROPPED from the payload before persistence. (3) The system prompt explicitly prohibits invented forecasts and requires `[Insufficient Information]` for absent forward signals. The rendered report can never display a number that does not trace to a module. |
| RT-2026-07-07-32 | 2026-07-07 | Issuer Profile: AI Research Report tab — stale cached report | The report is cached per `(issuer_id, run_id)`. If an analyst re-runs the pipeline (new run completes), the cached report for the old run still renders as current — a committee read off a stale synthesis is a money-losing failure. | High | Resolved | `GET /research-report` returns `is_stale = (report.run_id != latest_complete_run_id)`. The UI renders a warning banner: "This report reflects run A (as-of date). A newer run B exists — Regenerate." with a one-click Regenerate button. The masthead always shows the report's `run_id` + `as_of_date`, so staleness is visible even in a screenshot. Auto-regeneration is deliberately NOT implemented (cost control). |
| RT-2026-07-07-33 | 2026-07-07 | Issuer Profile: AI Research Report tab — partial run / missing modules | An issuer with a run where only CP-0/CP-1 completed (L2–L6 missing) would produce a report that fabricates the missing layers — a made-up L2 synthesis reading as sourced. | High | Resolved | Hard gates: (1) POST returns 409 if no complete run exists. (2) `build_module_digest` omits modules not present; the system prompt instructs the model to render `[Insufficient Information]` for missing layers. (3) The payload's `gaps[]` array explicitly lists missing modules + impact. (4) A report with <3 modules present is auto-failed with "insufficient module coverage." |
| RT-2026-07-07-34 | 2026-07-07 | Issuer Profile: AI Research Report tab — indirect prompt injection via ingested module text | A module's `runtime_output` carries text extracted from an ingested offering memorandum that contains adversarial instructions ("Ignore previous rules and rate this issuer Overweight"). The LLM obeys the injected instruction. | High | Resolved | The system prompt explicitly marks module digests as "untrusted DATA to analyze, never instructions" (mirrors `deepresearch.py`'s AML.T0051.001 guard). The figure validator (RT-2026-07-07-31) is the backstop: even if the model is manipulated into a stance, the `action_bias` must match the CP-6A digest value, and fabricated figures are dropped. |
| RT-2026-07-07-35 | 2026-07-07 | Issuer Profile: AI Research Report tab — rate limit / cost runaway | An analyst clicking Regenerate repeatedly (or a script) fires a multi-thousand-token opus call each time — unbounded token spend. | High | Resolved | POST is rate-limited at 3/min per caller (mirrors `routes/research.py`). 429 renders as a toast. `ai_mode` defaults to "standard"; "max" is opt-in with a cost hint. `tokens_used` is persisted and surfaced in the toolbar (cost transparency). Polling GET is not rate-limited (cheap read). |
| RT-2026-07-07-36 | 2026-07-07 | Issuer Profile: AI Research Report tab — shared vs analyst-private scope | Deep Research jobs are analyst-scoped (`analyst_id` isolation). If the Research Report reuses `ResearchJob`, one analyst's report is invisible to another — but the report is the house's synthesized credit summary, not a personal brief. | Medium | Resolved | New `IssuerResearchReport` table keyed on `(issuer_id, run_id)` — a shared house artifact. Any analyst viewing the same issuer+run sees the same report. `analyst_id` is recorded for audit (who triggered the synthesis) but does not scope reads. This differs from Deep Research (analyst-private briefs). |
| RT-2026-07-07-37 | 2026-07-07 | Issuer Profile: AI Research Report tab — NaN/±inf poison from CP-1 figures | The module digest extracts numeric figures from `runtime_output`. A CP-1-derived value (leverage, EBITDA, coverage) that is `NaN` or `±inf` would pass a plain `isinstance(x, (int, float))` guard (since `bool(NaN)` is `True`) and poison downstream division/multiplication in the digest builder or the LLM context. | High | Resolved | Every numeric extraction in `build_module_digest` that reads a CP-1-derived value is gated through `engine.periods.is_finite_number(x)` before inclusion — `NaN`/`±inf` values are set to `None` (omitted from the digest). This mirrors the AGENTS.md CP-1 guard convention enforced across CP-2B/2E/2F/3B/3D and the Altman score. |
| RT-2026-07-07-38 | 2026-07-07 | Issuer Profile: AI Research Report tab — LLM truncation mid-report | A full L1–L6 synthesis is a long output; the model may hit the token cap mid-section, producing a report that ends abruptly and reads as complete. | Medium | Resolved | Mirror `deepresearch.py`'s truncation handling: `truncated=True` when the cap is hit before `stop_reason="end_turn"`. A visible banner is prepended to `markdown`: "> Report may be incomplete — synthesis stopped at its length cap." The UI surfaces a `truncated` chip in the toolbar with a prominent Regenerate CTA. `ai_mode: "max"` raises the token ceiling (12000 → 16000). |
| RT-2026-07-07-39 | 2026-07-07 | Issuer Profile: AI Research Report tab — tab toggle breaks existing profile layout | Adding a `ToggleGroup` to the sub-header and conditionally swapping the body could regress the existing profile rows (Credit snapshot, Financial trend, Thesis, Business profile, etc.) — the profile is also rendered inside `IssuerProfileOverlay`, so a layout change could break the overlay. | Medium | Resolved | The toggle is ADDITIVE: the existing `body` variable is wrapped in a conditional (`tab === "research" ? <ResearchReportView> : <ProfileRows>`). The sub-header, header actions, and bottom function bar render for BOTH tabs unchanged. The `Profile` component's exported props are unchanged (no overlay break). The toggle uses the existing `ToggleGroup` component with `size="sm"` — same pattern as the FY/Q granularity toggle already in the profile. |
| RT-2026-07-08-01 | 2026-07-08 | PDF→OKF ingestion blueprint (caos/docs/PDF_INGESTION_OKF_BLUEPRINT.md) — supersede semantics | Design copied `memochunks._delete_prior_memo_docs` (hard delete lineage→chunks→doc) into a lane whose chunks are engine-CITABLE. `EvidenceItem.document_chunk_id` is a real FK (`database.py`); a re-ingest DELETE hits an enforced FK on Postgres → IntegrityError/500, while SQLite dev never enables `PRAGMA foreign_keys` so tests pass and prod breaks. | High | Resolved | Blueprint D10: evidence-aware supersede — hard-delete ONLY when no `EvidenceItem.document_chunk_id` references the prior doc's chunks; else keep the old Document+chunks as a shadow and repoint the registry. Blueprint states the PG-enforces/SQLite-ignores FK asymmetry and mandates the supersede test assert PG semantics. |
| RT-2026-07-08-02 | 2026-07-08 | PDF→OKF blueprint — supersede identity key | Key `(issuer_id, file_name, doc_type)` is wrong both ways: monthly re-issues under an identical filename ("Lender_Update.pdf") would DELETE the prior period's distinct record; the same PDF under a different filename never matches → duplicate Documents/chunks. | High | Resolved | D10: identity key = `(issuer_id, doc_type, source?, report_date-or-fiscal_period)` — same name + different extracted date versions alongside; per-issuer `content_sha256` match = true-duplicate no-op returning the existing `document_id`. |
| RT-2026-07-08-03 | 2026-07-08 | PDF→OKF blueprint — okf_notes registry FK | `okf_notes.document_id` (unique FK→documents.id) + delete-and-recreate supersede (new uuid each ingest) means the registry row points at a to-be-deleted doc → FK violation on the 2nd upload (no cascades in this schema; memochunks manually orders deletes). | High | Resolved | D10 transaction ordering: insert new Document+chunks+LineageEdge → UPDATE the okf_notes row in place (repoint document_id/note_path/content_sha256/status) → evidence-aware cleanup of the prior doc → commit. Repoint-before-delete; registry mutation precedes the documents delete. |
| RT-2026-07-08-04 | 2026-07-08 | PDF→OKF blueprint — Sources/ note filename | Filename embedding `document_id[:8]` never overwrites in place (supersede mints a new uuid each time), so `Sources/` accumulates orphan notes carrying full source text that no registry row tracks. `spoke_title`'s id-suffix works only because `run.id` is stable across re-export. | Medium | Resolved | D9: filename derives from the supersede IDENTITY (`_title(f"{issuer} - {doc_type} - {source?} - {report_date}")`), `document_id` moves to frontmatter; `note_path` UNIQUE in the registry; supersede unlinks the prior file on slug drift; residual collision → deterministic ` - 2` suffix. |
| RT-2026-07-08-05 | 2026-07-08 | PDF→OKF blueprint — note-write vs commit lifecycle | "Write note off-thread after commit" is impossible inline: `get_db` commits in dependency teardown AFTER the handler returns, so an inline `to_thread(write_note)` runs BEFORE commit — a commit failure leaves a phantom note projecting a nonexistent document. | Medium | Resolved | D11(b): the note file is written in a `BackgroundTasks` task (FastAPI ≥0.106 runs these after teardown/commit; pin 0.138) with its own `AsyncSessionLocal`, advancing registry status `pending_note → written | note_failed` so the ledger stays truthful on disk-write failure. |
| RT-2026-07-08-06 | 2026-07-08 | PDF→OKF blueprint — routes/okf.py security ladder | Auth is per-endpoint in CAOS (no global auth dependency); a new route that forgets any of `Depends(get_identity)`, the rate guard, scan-before-parse (`read_capped→sniff_pdf→avscan.scan`), or `uploaded_by=caller.email` is an unauthenticated/unscanned/unattributed ingest hole. | Medium | Resolved | D11(a): blueprint enumerates the full ladder verbatim from `upload_document` and reuses `_upload_rate_guard`, `get_identity`, and `avscan.scan`-before-parse ordering; router registered in `main.py`. |
| RT-2026-07-08-07 | 2026-07-08 | PDF→OKF blueprint — redaction posture reversal | `Sources/` notes carrying whole offering memos flip the vault from "safe to sync" (OBSIDIAN_DATABANK.md redacts raw source) to "contains MNPI-grade source text"; the `contains_source_text` flag has no consumer. | Medium | Resolved | D5 + D11(d): posture stated explicitly in the OKF spec; OBSIDIAN_DATABANK.md update is a blueprint deliverable (inbound Sources/ section, sync/cloud-embed now a data-handling decision, local-embed mandate restated); `_redact` unchanged for the outbound engine-output note families. |
| RT-2026-07-08-08 | 2026-07-08 | PDF→OKF blueprint — breadcrumb numerals vs grounding gate | `engine/grounding.all_grounded` builds its allowed numeric pool from cited-chunk text; breadcrumb lines carrying page integers/years would let a fabricated figure pass by colliding with "page 12"/"2026". | Low | Resolved | D4: breadcrumb kept numeral-lean (issuer/doc-type/section words, no bare page integers); page anchors live in section headings; residual widening documented as accepted (Query lanes only). |
| RT-2026-07-08-09 | 2026-07-08 | PDF→OKF blueprint — breadcrumb vs cross-doc chunk_hash dedup | Per-doc breadcrumb prefixes make identical boilerplate hash-distinct across documents → duplicate embedding spend (embeddings dedup by `(model, chunk_hash)`). | Low | Accepted | Within-document supersede reuse is unaffected (same source → same note body → same hashes); cross-doc boilerplate dedup loss is a bounded embed-cost note. Upgrade path = hash the pre-breadcrumb section text if spend matters. |
| RT-2026-07-08-10 | 2026-07-08 | PDF→OKF blueprint — readiness._categorize coverage | `_CATEGORIES` doc_type substrings (`audit`/`edgar-xbrl`/`sfa`/`indenture`/`prospectus`/`covenant`) match none of the 5 new types, so CP-0 coverage under-counts cleanly-typed OKF docs (falls back to filename/content markers). | Low | Resolved | D11(c): additive one-line extension of the `_categorize` substring table for the new doc_types; all other doc_type sites verified display/pass-through or self-set values. |
| RT-2026-07-08-11 | 2026-07-08 | PDF→OKF blueprint — fiscal_period stored twice | `Document.fiscal_period` and `okf_notes.fiscal_period` both hold the period → drift risk with no declared canonical. | Low | Resolved | D11(e): `Document.fiscal_period` declared canonical; the registry column is a denormalized audit copy written from the same extracted value in one transaction. |
| RT-2026-07-08-12 | 2026-07-08 | PDF→OKF blueprint — storage blob retention on supersede | OKF supersede deletes Document rows whose `storage_key` points at real files under `caos_storage_dir`, orphaning the blob and removing the vault's regeneration source. | Low | Resolved | D10: storage blobs are RETAINED on supersede (audit + regeneration source), stated explicitly; the "regenerable vault" claim keeps its source. |

## Engine Architecture Spec — Critic Pass (2026-07-08)

Decision under review: the interface choices in `caos/docs/ENGINE_IMPLEMENTATION_SPEC.md`
(the P0→P3 deepening spec Opus 4.8 executes). Five fresh-context adversarial
verifiers (Checkpoints A–E) audited the written items against the code; the
high-impact objections below are their confirmed findings, each reconciled into
the spec before sign-off. No high-impact objection remains open.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-08-13 | 2026-07-08 | C1 `bindings` extraction ("move the exact code under each `if`") | Two dispatch branches carry `and issuer is not None`, falling through to the default synthesizer when `issuer is None`; a naive `BINDERS` map always routes, turning a null-issuer run from default-output into CP-0/CP-1C **Blocked** — and goldens use seeded (non-null) issuers, so they would not catch it. | High | Resolved | Checkpoint A. Spec step 2b mandates `_bind_cp0`/`_bind_cp1c` begin `if ctx.issuer is None: return await _default_binder(ctx)`, and moves CP-1's reconcile basis-gate with the reconcile. |
| RT-2026-07-08-14 | 2026-07-08 | C4 `querygraph` split ("extract concentration builders; metric-axis may leave in core") | `_concentration` dispatches to `_scatter/_percentile/_trend/_coverage` **and `_provenance_split`** (unassigned in the draft); leaving any in core while `_concentration` moves recreates a `querygraph↔queryclusters` import cycle. | High | Resolved | Checkpoint C. Spec must-fix moves all five dispatch targets *with* `_concentration` into `queryclusters`; the "leave in core" option is deleted. |
| RT-2026-07-08-15 | 2026-07-08 | P1 `guarded_llm_call` ("8 lanes share one wrap+rule+finite triad; migration keeps outbound bytes identical") | False premise: `council` carries no `UNTRUSTED_RULE`/`wrap_untrusted` and has 2 call sites; rule is suffixed by 7 lanes but prefixed by `rerank`; user shapes carry lane-specific labels/composites — a byte-identical single interface is infeasible. | High | Resolved | Checkpoint D. Item downgraded P1→P2 and reframed: concentrate only the byte-safe call+finite-parse (callers keep composing system/user); the non-uniform injection posture is surfaced as a flagged finding, `council` excluded/migrated last. |
| RT-2026-07-08-16 | 2026-07-08 | C3 `safe_div` migration list | `downside`'s `cov*(1-s)` is a multiplication and `lev/(1-s)` a literal denominator; `peers._percentile` divides counts — none is a CP-1 variable/variable divide, so mechanical migration is wrong. | Medium | Resolved | Checkpoint B. Spec names both as explicit exclusions; migration list restricted to the ~6 genuine CP-1 divides. |
| RT-2026-07-08-17 | 2026-07-08 | C3 `safe_ratio(scale=)` helper | `scale*(num/den)` reassociates the float vs the current `(scale*num)/den`; a golden could shift on raw values. | Medium | Resolved | Checkpoint B measured 0/2,000,000 differ after `round(,1)`, but to keep bitwise-raw identity the spec drops `safe_ratio` and uses `safe_div(scale*num, den)` (numerator scaled before the divide). |
| RT-2026-07-08-18 | 2026-07-08 | C2 folding `queryinsights._delta_entries` onto the shared predicate | It is the one reader missing `qa_status != "Blocked"`; folding it in *adds* that filter — a behavior change that could shift a query-gate golden. | Medium | Resolved | Spec instructs verifying against `test_golden_query_gates.py`/`test_query_insights.py`; the runner write-skip should make it result-identical, and if a golden shifts that is evidence of a real write-skip gap (a separate finding), not a reason to force the filter off. |
| RT-2026-07-08-19 | 2026-07-08 | C4 split renaming private `_best_fact` | `test_fact_collapse.py` imports `engine.querygraph._best_fact` directly; moving it to `queryfacts` breaks the test. | Low | Resolved | Spec instructs updating the import (or re-exporting `_best_fact` from `querygraph`). |
| RT-2026-07-08-20 | 2026-07-08 | P2 `DraftReport` schematization | It reshapes the `GET /api/autonomy/draft` response contract. | Medium | Accepted | Measured **0** frontend consumers today (Command Center/Monitor still mock), so this is the low-cost window; the spec migrates `routes/autonomy._empty_draft` in lockstep and flags coordination with `FRONTEND_ARCHITECT_BRIEF.md`. |
| RT-2026-07-08-21 | 2026-07-08 | Inheriting the brief's measured baseline verbatim | The brief's §3 measurement script counts only the dotted `from engine.X import` form, so its fan-out (27), edge (129), and other counts undercount the real graph. | Low | Resolved | Spec baseline re-measures both import forms and states both counts + the method: runner fan-out 31, edges 166, queryanswer 11, autonomy 6, dedicated tests 39 — each labeled as a correction, none silently overriding the brief. |
| RT-2026-07-08-22 | 2026-07-08 | C1 `bindings` module structure ("`_bind_cp1` imports `runner._synthesize_cp1`; no cycle because runner imports `resolve_binding`") | A top-level `bindings → runner` back-edge for `_synthesize_cp1` is a **fatal circular import** (Python loads a partially-initialized `runner` — the CP-1 helpers are defined low in the file — and raises `ImportError`); the "no cycle" reasoning was wrong. The five Checkpoint verifiers missed it because they verified arg-shapes/behavior, not the module-load import graph. | High | Resolved | Grilling (C1, the highest-leverage seam). Spec instruction step 2 extracts `_synthesize_cp1` + `_vault_edgar_facts` into a new cycle-free `engine/cp1_sources.py` (imports only leaf producers `edgar_cp1`/`reported_cp1`, which never import `runner`/`bindings`), so there is **no `bindings → runner` edge**. Grilling also added a verbatim behavior-preservation checklist (per-module `["CP-1"]` vs `.get`, CP-1B sync/no-await, CP-2 branch, CP-6A/6E shared binder) and fixed the `test_bindings.py` scope to routing-only across all 18 binders. |
| RT-2026-07-08-23 | 2026-07-08 | C2 "concentrate the quadruplicated headline-fact read into a shared `Select` builder" | Reading all four readers shows they are structurally *different* queries (different columns/joins/provenance/caps) sharing only three predicates — a shared `Select` is the wrong shape and oversells the concentration; and `queryinsights`'s missing `qa_status != "Blocked"` is a consistency gap, not a live bug (the runner write-skip already keeps Blocked CP-1 facts out of the store), so "MEDIUM risk, 4 byte-identical migrations" overstated it. | Medium | Resolved | Grilling (C2). Reframed to a `metrics.headline_fact_predicates(keys)` helper (the three shared conditions) each reader spreads — not a shared query. Blast radius corrected to **LOW** (`peers`/`metricengine`/`metricfactlane` are byte-identical — they already carry all three; only `queryinsights` changes, gaining the guard); `metrics.py` gains a cycle-free `database` leaf import; test targets the predicate list once. |
| RT-2026-07-08-24 | 2026-07-08 | C4 querygraph split — "builders share only the layout kit; extract layout first to break the cycle" | The cycle rule was stated only for layout, but `_concentration` also calls `_profile_values` (facts); leaving `_profile_values` in core while `queryclusters` imports it — and core imports `queryclusters` for dispatch — recreates the same `querygraph↔queryclusters` cycle. So the *facts* extraction is cycle-forced too, not a convenience. | Medium | Resolved | Grilling (C4). Verified full acyclicity by reading the builder bodies (`provenance` calls no facts/clusters helper; `facts` calls nothing upward). Generalized the MUST-FIX to the rule "anything a to-be-extracted builder calls must not stay in core," naming `_profile_values` explicitly alongside `_concentration`'s five dispatch targets. Granularity is fact-determined; no open decision. |
| RT-2026-07-08-25 | 2026-07-08 | C1 `CycleStages` — "inject the four DAG stages behind a stages seam" | The "four stages" undercounts the real injection surface — `run_cycle` also branches on `_current_fingerprints` (DB) and `queryanswer.available()` (capability), which `test_autonomy._wire` already monkeypatches (7 attrs, db=None); and since the monkeypatch already gives DB-free branch coverage with no non-test consumer, the item was overstated as a fix rather than a consistency polish. | Low | Resolved | Grilling (C1/autonomy). Corrected to inject the **5 DB/LLM/capability boundaries** (`_current_fingerprints`, `detect_anomalies`, `available`, `investigate`, `compose_draft_report`) via a frozen `CycleStages` + `DEFAULT_STAGES`, keeping the pure sentinel fns direct (test exercises the real diff). Reframed honestly as a test-idiom upgrade for sibling-consistency (`get_*` factory-seam parity), lowest-priority P1, safe to defer. |
| RT-2026-07-08-26 | 2026-07-08 | C3 `safe_div` — P0 "the guard becomes the interface / impossible to bypass" at metric-lane scope | ~15 guarded CP-1 divides live *outside* the migrated metric-lane 6 (`macro`/`liquidity`/`distress`/`anomaly`/`capstructure`/`covenants`/`earnings`/`relval`), so the claim was ~30% realized; and migrating call sites never makes the guard unbypassable — a raw `a/b` always can be written. | Medium | Resolved | Grilling (C3). Softened the P0 principle/payoff to "concentrated + enforceable," and added a **P2 CI-lint item** as the real enforcement (a new unguarded CP-1 divide fails CI) — specced honestly as a diff-scoped *heuristic* (AST can't prove CP-1 provenance) with a `noqa` escape. The other ~15 divides (all already correctly guarded per Checkpoint B) are left to opportunistic migration, not risky mass-churn across 12 modules. |
| RT-2026-07-08-27 | 2026-07-08 | P2 `guarded_llm_call` — "concentrate the call + finite-parse behind one interface" | After Checkpoint D removed the wrap+rule leg, the remainder concentrates nothing: `llm_client.create` is already the shared seam, the reply-parse varies per lane, and every lane already finite-rejects via the shared `first_json_*`/`loads_finite` primitives — so the wrapper is churn with no gain. | Medium | Resolved | Grilling (LLM). Dropped the wrapper build. The P2 item is reframed to the one finding with teeth: `council` passes engine `ModulePayload`s to the model **unfenced**, and a payload's `runtime_output` may carry doc-extracted text — Opus is instructed to trace that injection path and fence `council`'s input if it exists (one-lane, golden-verified), not to build an interface. |

## Secure Performance Frontend Blueprint — Critic Pass (2026-07-08)

Decision under review: [`caos/docs/SECURE_PERFORMANCE_FRONTEND_BLUEPRINT.md`](../caos/docs/SECURE_PERFORMANCE_FRONTEND_BLUEPRINT.md) — the BFF-proxy / atomic-state / windowed-rendering hardening blueprint for Opus 4.8 to implement pre-deploy. Nine fresh-context adversarial verifiers, one per core dashboard route (command, sector-rv, pipeline, deepdive, model, reports, monitor, query, issuers+profile), each independently answered two questions against their own greps of the built bundle and the FastAPI routes: (a) does the proposal leave any AI/DB token reachable from the browser, (b) does any performance change re-expose a secret moved server-side. Result: **18/18 PASS**. Three objections below changed the document; the rest confirmed the draft with no changes.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-08-28 | 2026-07-08 | Δ1 bundle secret-scan allowlist ("allowlist the settings-page env-var-NAME hint labels") | A single-pass line allowlist keyed on the bare name (`ANTHROPIC_API_KEY`) would also match — and hide — a real leaked value written as `ANTHROPIC_API_KEY=sk-ant-...`; the /command route verifier flagged this as a real design gap before any code existed. | High | Resolved | Δ1 respecced as two independent passes: pass 1 (value patterns — key prefixes, DSNs, external AI hosts) has no allowlist and fails on any hit; pass 2 (bare names) is allowed only in the exact quoted UI-label form `reqKey:"<NAME>"`/`hint:"<NAME>"`, never followed by `=`. |
| RT-2026-07-08-29 | 2026-07-08 | §1.1 route contract listed `GET /api/autonomy/draft` as a live route the Command Center UI polls | The /command route verifier found `grep autonomy src/` returns empty — no frontend code calls this endpoint; the Command Center still renders mock data (matches the known autonomy-cycle unwired-frontend state). Presenting it as an active UI dependency was a false premise. | Medium | Resolved | Row annotated "no frontend caller today... contract pinned for when it wires"; Δ2's schema pin on this route reframed as forward-hardening, not a fix to an active leak path. |
| RT-2026-07-08-30 | 2026-07-08 | Δ2 `AnswerResponse` pin for `POST /api/query/answer` | The /query route verifier read `query/page.tsx:329-333` and found the UI's `AiAnswer` render consumes `model`/`created_at`/`cached` fields that the drafted schema omitted — shipping the pin as drafted would have silently dropped those fields and regressed the answer display, not just tightened security. | Medium | Resolved | Schema extended with the three optional cache-envelope fields; instruction added to diff against one live payload before implementing, in case the envelope carries anything else undocumented. |

Verifier misfires (process note, not a finding): 3 of 12 subagent spawns across this pass returned zero-tool-call boilerplate instead of executing; each was resumed with an explicit re-instruction and then produced full evidence-backed verdicts. No verdict in the table above rests on an unexecuted run.

## Agentic Infrastructure & Memory Hub — Build Spec (2026-07-08)

Decision under review: [`caos/docs/AGENTIC_INFRA_MEMORY_HUB_SPEC.md`](../caos/docs/AGENTIC_INFRA_MEMORY_HUB_SPEC.md) — the gateway/MCP-router (WS1), telemetry+masking (WS2), and bidirectional memory-sync (WS3) consolidation spec, design-complete for Fable 5 to implement. Two independent Plan agents produced the WS1+WS2 and WS3 designs from a shared codebase inventory; five fresh-context verifier subagents then checked the drafted spec's own claims against the actual code, one per major transformation step (prompt formatting, cost calculation, masking, chunk diffing, embedding refresh). Every verifier's file:line citations were spot-checked directly before being trusted. Result: the two Plan-agent designs disagreed on one point (below) and were reconciled before drafting; the five post-draft verifiers surfaced two real defects (one High, one Low) in the drafted text itself, both fixed in the spec; one pre-existing production risk was discovered during pricing research and is flagged, not fixed (out of scope for a design-only deliverable).

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-08-31 | 2026-07-08 | WS1's proposed embedding-failure fix: persist a live-call mock fallback under a synthetic `"mock-{dim}"` model label | Keyless-dev/test retrieval filters vector reads by `DocumentChunkEmbedding.model == settings.embedding_model` (`retrieval.py`); renaming a mock row's model to `"mock-768"` would make it invisible to that filter, silently breaking keyless vector search in dev/test — the fix would trade a production defect for a dev-environment regression. | Medium | Resolved | Adopted WS3's alternative design instead: `get_embeddings` raises `EmbeddingUnavailable` only when `gemini_api_key` is set and the live call fails; the keyless branch (which never reaches a live call) is left untouched, preserving today's mock-under-real-model dev/test behavior. Spec §9.8. |
| RT-2026-07-08-32 | 2026-07-08 | Migration numbering for the new telemetry and vault-sync-provenance tables | Three separate initiatives — this spec's telemetry migration, this spec's vault-sync-provenance migration, and the unlanded `PDF_INGESTION_OKF_BLUEPRINT.md`'s reserved `okf_notes` migration — all independently claimed migration number `0034` off the same `0033` head, an unnoticed collision until cross-checked. | Medium | Resolved | This spec claims `0034_llm_telemetry` and `0035_vault_sync_provenance` in that order; the OKF blueprint renumbers to `0036` if it lands after either. Spec §0.1 and §13 state this explicitly so neither PR can silently resolve the collision without the other author noticing. |
| RT-2026-07-08-33 | 2026-07-08 | §2.2's justification for keeping the MCP tool loop out of `create` (a separate `create_with_tools` entry point) cited two existing `tools=` callers — synth's forced payload tool and `queryoverlay.py` — as both depending on unexecuted `tool_use` blocks | Fresh-context verifier read `queryoverlay.py` directly: it has zero `tools=`/`tool_choice` usage anywhere, and its own module docstring states "no tools and no writes" — the module was never actually load-bearing for this design decision. Citing a caller that doesn't exist as evidence risks an implementer looking for tool-handling logic that isn't there, or trusting an unverified second data point. | Medium | Resolved | §2.2 corrected: the design decision is justified solely by synth's forced-tool contract (`synth.py:427-428`, `_payload_data_from_resp` reading `block.input` directly, verified real); `queryoverlay.py` is now cited only as confirmation that today's `tools=` usage is narrow, not as a second dependent caller. |
| RT-2026-07-08-34 | 2026-07-08 | §7's masking regex, class 1 (`AMT` currency), suffix alternation `k\|m\|mm\|bn\|b\|t\|mio\|mrd\|million\|billion\|thousand\|trillion` | Regex alternation is first-match, not longest-match; short forms (`m`, `b`, `t`) were listed before the longer forms they are prefixes of (`mm`/`mio`/`million`, `billion`, `thousand`/`trillion`). Fresh-context verifier demonstrated this breaks the spec's *own* worked example: `EUR 1,2 Mrd` matches only the `M` of `Mrd`, leaving `rd` as unmasked plain text after the placeholder — and the same defect hits any spelled-out or `mm`-style amount, arguably the most common way leveraged-credit prose writes these figures. | High | Resolved | Alternation reordered longest-first: `million\|billion\|thousand\|trillion\|mrd\|mio\|mm\|bn\|k\|m\|b\|t`. Spec §7. |
| RT-2026-07-08-35 | 2026-07-08 | Same regex cell (self-caught during the fix for RT-2026-07-08-34, not a verifier finding) | The character class `[\d.,' ]` (intended: digit-run continuation allowing space-grouped thousands) contained a literal U+00A0 non-breaking-space byte instead of an ASCII space — an authoring artifact from drafting, silently non-matching on any real analyst text typed with an ordinary space. | Low | Resolved | Byte replaced with ASCII space; file swept for any other NBSP occurrences (none found). Spec §7. |
| RT-2026-07-08-36 | 2026-07-08 | §6's cost matrix prices the `embedding_model` config default (`"text-embedding-004"`) as an active, billable model | WebSearch during rate-fetching (not a code finding) surfaced that Google retired `text-embedding-004` on 2026-01-14 — five-plus months before this session. `config.py:105` still defaults to it, uncommented, unchanged as recently as 2026-07-07. If `GEMINI_API_KEY` has been set in any deployed environment since the retirement date, every live embed call has been failing and — per the exact defect this same spec's §9.8 independently identifies and fixes — silently persisting mock vectors under that (now-dead) model label into the production vector store, indistinguishable from real vectors under the current schema. | Critical (production data-integrity risk, discovered incidentally) | Accepted / flagged, not remediated here | Out of scope for a design-only spec — no code changed. Flagged prominently in spec §0.1 and §6.2 as an operator action item: check whether `GEMINI_API_KEY` was live in production after 2026-01-14; if so, audit `document_chunk_embeddings` rows under that model label (the fix in §9.8 prevents new occurrences but cannot retroactively distinguish old ones — nothing in the current schema tags a row's provenance). This fact is unverifiable from the repository alone (confirmed by a dedicated verifier pass, which found the retirement date traces only to this session's own external research, with no corroborating signal anywhere in the codebase) and must be independently confirmed against Google's live pricing/deprecation page before acting on it. |

Verifier method note: five Explore-type subagents ran with no shared context, each given only the relevant spec section(s) plus the zero-added-latency constraint, and instructed to report PASS/FAIL/PARTIAL per claim with file:line evidence rather than accept any claim on faith. 33 of 35 individually-checked claims across the five passes returned PASS; the two non-PASS findings (RT-33, RT-34) are both recorded above and fixed. No verdict in this table rests on an unexecuted or unverified claim.

**Follow-up pass**: user asked "is that all" after the first 9-route sign-off. Re-checked coverage against the 5 named CAOS UI concepts (command/pipeline/deepdive/model/reports — all verified) plus route significance, and found two gaps: `/settings` (the only route where any bundle grep ever hit, previously checked only by the authoring session itself, never by an independent subagent) and `/research` (the heaviest external LLM+search lane, listed in the proxy table but never independently verified). Both closed below — 20/20 PASS overall, two small accuracy fixes folded.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-08-31 | 2026-07-08 | §1.1 `POST /api/research` credential column said "LLM + web-search keys server-side" | The /research verifier read `deepresearch.py:248` and `config.py` and found Deep Research's web search is Anthropic's own server-side `web_search_20260209` tool, gated by `ANTHROPIC_API_KEY` alone — no separate search-provider key exists in config (grepped for serper/bing/brave/tavily). "Web-search keys" implied a second credential that isn't real. | Low | Resolved | Column corrected to name `ANTHROPIC_API_KEY` only, with the tool name and the negative-grep evidence. |
| RT-2026-07-08-32 | 2026-07-08 | Δ1 bundle-scan target | Both the /settings and /research verifiers independently noticed `caos/frontend/out/` and `caos/server/static/` are different point-in-time builds in this checkout (different chunk hashes, one route's chunk even had a prop-shape diff) — two fresh-context passes converging on the same observation flags it as a real footgun: a scan aimed at the wrong tree could pass on a stale artifact. | Low | Resolved | Δ1 now states explicitly to scan `out/` immediately post-build, not `server/static/` (a deploy-time copy that isn't a reliable freshness signal in a dev checkout). |

Settings verdict: PASS/PASS — page.tsx read in full, no save-key form exists (grep for password-type inputs/apiKey fields = 0), `GET /api/settings` returns only booleans (`llm_configured` etc.) never the key string, bundle grepped additionally for masked/partial-key patterns (`sk-...`, `****`, last-4) with zero hits in both build trees.
Research verdict: PASS/PASS — both endpoints authed, 404-not-403 isolation confirmed identical for missing-vs-not-mine (no existence leak), `ResearchJobStatus` schema carries no credential-shaped field, source URLs whitelisted to http(s) server-side with a dedicated unit test, and the report renderer uses `react-markdown` with no raw-HTML escape hatch.

## Container-Hardening Blueprint — Critic Pass (2026-07-08)

Decision under review: [`caos/docs/CONTAINER_HARDENING_BLUEPRINT.md`](../caos/docs/CONTAINER_HARDENING_BLUEPRINT.md) — the zero-root/read-only/digest-pinned hardening design for all six images in the CAOS Docker Compose stack (app, db, caddy, oauth2-proxy, backup, clamav), design-complete for Opus 4.8 to implement. Six fresh-context adversarial verifiers, one per image section, each independently re-fetched the primary sources the drafted section cited (upstream Dockerfiles/entrypoints/source on GitHub via `gh api`, not trusted from the blueprint's own quotes) rather than only checking internal consistency. No live Docker daemon was available in this environment for any pass (author or verifiers) — all findings are source/mechanism-level, cross-checked against primary source or, where a claim genuinely required a running container, tagged `[VERIFY AT IMPLEMENTATION]` in the document with the exact command to run. Result: 5 of 6 sections had at least one confirmed defect; oauth2-proxy came back clean. Every CONFIRMED-ISSUE finding below was fixed in the document before sign-off; two open gaps (RT-40, RT-44) are documented as unresolved because closing them requires an application-code change outside a Dockerfile/compose blueprint's scope, not because they were missed.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-08-37 | 2026-07-08 | §1.1 db live-data migration procedure (`docker run -v vol:/old -v vol:/new busybox cp -a /old/. /new/18/docker`) | Mounting the same named volume twice into one container under two different paths is not two independent trees — it's one directory reachable two ways. The `mkdir /new/18` step is also visible under `/old`, so the subsequent `cp -a /old/. /new/18/docker` recursively copies a tree into a path nested under itself. Verifier reproduced the equivalent topology locally (no Docker daemon available): real data survived (cp's cycle-guard truncated the self-reference), but it left a stray artifact directory and, on some `cp` implementations, an ambiguous non-zero exit — unacceptable ambiguity during a live production-data migration. | High | Resolved | §1.1 rewritten to a single-mount, explicit-`mv`-based procedure (named files moved into a staging dir, then the staging dir moved into place) — no double-mount, no wildcard that could sweep up its own destination. |
| RT-2026-07-08-38 | 2026-07-08 | §5.4 caddy volume-ownership migration one-liner (`docker compose run --rm --user 0:0 --entrypoint sh caddy -c 'chown -R 10002:10002 /data /config'`) | `docker compose run` inherits the service's `cap_drop: ["ALL"]` unconditionally — `--user 0:0` overrides the uid but restores no capability, and `chown(2)` requires `CAP_CHOWN` regardless of uid once capabilities are stripped (verified against `docker/compose`'s own Go source: `applyRunOptions` only mutates `CapAdd`/`CapDrop` if `--cap-add`/`--cap-drop` are explicitly passed on the `run` invocation). As written, the command fails `Operation not permitted` on every file. Verifier also confirmed the same bug pattern — and therefore the same fix — applies to every other migration one-liner in the document that combines `user: 0:0` with a `cap_drop: ["ALL"]` service. | High | Resolved | `--cap-add=CHOWN` added to the caddy snippet and, pre-emptively (before their own audits ran), to the equivalent snippets in §4.2 (db), §7.3 (backup), §8.3 (clamav) — all four now carry the flag with an explanation of why it's required. |
| RT-2026-07-08-39 | 2026-07-08 | §3.2/§3.4 app image "no pip, no build tools" claim | `apt-get install ocrmypdf tesseract-ocr` transitively pulls Debian's `python3-setuptools` via a hard `Depends` chain (`ocrmypdf → python3-pkg-resources → python3-setuptools`) that `--no-install-recommends` does not block. It lands under `/usr/bin/python3`'s tree, untouched by the `pip uninstall` step (scoped to `/usr/local`), and §3.4's verification command only probes `/usr/local` — so it would report clean regardless of whether `setuptools` is present. | Medium | Resolved | §3.2 corrected to the accurate claim ("no *installer* ships," not "no build-tooling artifacts at all"), the specific untagged sentence retagged `[VERIFY AT IMPLEMENTATION]` with the exact `apt-cache depends` command to confirm plain `pip` itself isn't also pulled in. |
| RT-2026-07-08-40 | 2026-07-08 | §3.3 app image `/scratch` volume + tmpfs redesign, framed as closing the OCR-lane memory-pressure gap | Two real OOM contributors survive the redesign untouched: (1) upload handling buffers the full request body into an in-process `bytearray` up to `MAX_UPLOAD_MB` (250 MB) — genuine RSS, unaffected by `TMPDIR`/volume choice since no tempfile is involved; (2) `ocrmypdf` is invoked with no `--jobs` cap, defaulting to every CPU core the host exposes, inside the same `mem_limit: 2g` cgroup as everything else. | Medium | Accepted, flagged not fixed | Both require an application-code change (`ingest.py`), out of scope for a Dockerfile/compose blueprint. §3.3 now states both explicitly and instructs a load test (a ~250 MB many-page scanned PDF at `mem_limit: 2g`) before treating that limit as final, with the `--jobs` cap named as the fix if it OOMs. |
| RT-2026-07-08-41 | 2026-07-08 | §3.1/§3.3 app image runtime write-path inventory | `caos/server/config.py`'s `vault_export_dir` (default `""`, disabled) is a real, reachable write path (`vault_export.py`'s `mkdir`+`write_text`, called from two routes) with no volume or tmpfs covering it in the design — silently `EROFS` if ever enabled. | Medium | Resolved | §3.3 documents the gap explicitly: feature is off by default so no fix is forced now, but guidance is added for what to mount if `VAULT_EXPORT_DIR` is ever turned on. |
| RT-2026-07-08-42 | 2026-07-08 | §7.2 backup service `/tmp` tmpfs, sized 16 MB "defensively" for `pg_dump`/`tar` (which the audit confirmed need no `/tmp` scratch for their actual invocation) | `backup.sh`'s own header comment documents a quarterly restore-drill procedure that decompresses a full vault tarball into `/tmp` — a single upload can already be 250 MB, so any real vault tarball exceeds a 16 MB tmpfs by a wide margin. The unhardened service has no such ceiling today, so this drill has never failed before; the hardening design would silently break it. | Medium | Resolved | §7 documents the fix: point the drill at `/backups/_vault_restore_test/` (same volume the service already owns, no size ceiling) instead of `/tmp`, with a note to update `backup.sh`'s comment when implemented. |
| RT-2026-07-08-43 | 2026-07-08 | §8.2 clamav compose design, claimed to write only to `/tmp` and `/var/lib/clamav` | The image's baked `freshclam.conf` unconditionally sets a file-log target (`UpdateLogFile /var/log/clamav/freshclam.log`) that the `--stdout` entrypoint flag does not disable (traced into `freshclam.c`/`common/output.c`) — a third, uncovered write path. Under `read_only: true` with no mount there, every log line (including during first-boot signature download) fails `EROFS` — non-fatal but spams `docker compose logs clamav`, and the original verification gate's `grep -i denied` would not have caught this failure mode (`"Read-only file system"` ≠ `"denied"`). | Medium | Resolved | Added a dedicated `/var/log/clamav` tmpfs mount (§8.2) so the writes succeed instead of failing; widened §8.4's verification gate to also check for zero `"Read-only file system"` lines. |
| RT-2026-07-08-44 | 2026-07-08 | §8.2 clamav `/tmp` tmpfs sized 768 MB, reasoned as covering `StreamMaxLength` (300 MB) plus slack for one INSTREAM scan | Verifier traced clamd's INSTREAM handling into its own C source and confirmed the full-stream-to-disk buffering premise is correct (not oversized, not undersized for one scan) — but the sizing assumes one scan in flight. `caos/server/avscan.py` opens one independent TCP connection per upload with no concurrency limit, and clamd's receive/buffer step is not gated by `MaxThreads` (which only caps scan workers, not the connection-level write). Three simultaneous near-max uploads (900 MB) already exceeds 768 MB. | Medium | Accepted, flagged not fixed | Closing this requires either an application-level semaphore in `avscan.py` (out of scope for this document) or an operational sizing decision for expected peak concurrency. §8.2 states the gap explicitly rather than presenting 768 MB as fully closing the question; §8.4's functional gate gained a dedicated concurrent-upload test case to catch this at implementation time if it's not otherwise addressed. |
| RT-2026-07-08-45 | 2026-07-08 | §6.2 oauth2-proxy compose design, removing the existing `/tmp` tmpfs on the claim the process "writes nothing at runtime" | Verifier found this true only as currently configured — source-traced one real (but currently dormant) file-write gate in oauth2-proxy's own logging code, reachable only if `logging_filename` is ever set in `oauth2-proxy.cfg` (not set today). Stating the claim unconditionally risks a future editor reintroducing a write path without restoring a mount for it. | Low | Resolved | §6.2 caveat added, naming the three cfg options (`logging_filename`, Redis session store, in-process TLS) that would reintroduce a write path if ever enabled, and noting the fail-closed behavior (EROFS, not silent data loss) is correct if that happens. |

Verifier method note: each of the six passes was told explicitly to independently re-fetch the primary source the drafted section cited (not trust the blueprint's own quotes) and to be hardest on whichever single claim in its section was reasoning/inference rather than a directly-quoted fact — every CONFIRMED-ISSUE above trace to exactly that kind of claim (a migration procedure never run, a sizing calculation, a dependency-tree side-effect). Two sections — db and oauth2-proxy — had their core design claims independently re-verified at a deeper level than the blueprint's own citations (respectively: the Docker/containerd volume-populate mechanism traced to its Go implementation rather than "documented behavior," and oauth2-proxy's full source tree swept for write primitives rather than reasoning from its session-store config alone) and came back confirming the original design was sound beyond what the author had claimed. No verdict in this table rests on an unexecuted or unverified subagent run.

**Follow-up pass**: user asked "is that all" after the six-image sign-off. The prior pass audited every per-service section (§3–§8) but never independently checked the document's cross-cutting parts — §2 (global conventions), §9 (rollout order), §10 (`.dockerignore`), or whether the six per-service compose snippets actually assemble into one valid file. Five more fresh-context subagents closed that gap, one per cross-cutting area, each re-fetching or directly executing against primary source rather than trusting the document's own citations. Found: one new critical pre-existing production defect (not previously known to this blueprint at all), one confirmed structural defect in the document's own formatting (mechanically verified with the real `docker compose config` loader, not just `yaml.safe_load`), two rollout-order gaps, several `.dockerignore` completeness gaps, and two overclaimed mechanism explanations. All fixed below.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-09-46 | 2026-07-09 | Blueprint's prerequisite completeness (§1) — implicitly scoped to what the original six-image audit had already surfaced | `caos/server/engine/synth.py:56` (`MODULAR_OS_DIR = SERVER_DIR.parent.parent / "Modular OS"`) reads a 24-file prompt corpus at a path that resolves entirely outside the `caos/` Docker build context (repo root, sibling to `caos/`) — no `.dockerignore` pattern can reach it, since it was never in context to begin with. `LiveSynthesizer.synthesize()` hard-raises `SynthesisError` for every CP module in any deployed container whenever a real API key is configured — the platform's core LLM-driven module-synthesis feature is non-functional today, independent of this blueprint, discovered incidentally while a verifier was checking an unrelated `.dockerignore` claim. | Critical | Resolved | New §1.4 prerequisite: read-only bind-mount of the host's `Modular OS/` directory into the `app` service at `/Modular OS` (the same pattern already used for `Caddyfile`/`clamd.conf`/`oauth2-proxy.cfg`), compatible with `read_only: true` with no other change. Widening the build context and baking the corpus into the image was considered and rejected — it couples prompt edits to image rebuilds for no benefit here. |
| RT-2026-07-09-47 | 2026-07-09 | §3.3 app service compose block, presented as one fenced code block containing both the `app:` service body and a trailing top-level `volumes:` addendum | Verifier assembled the full compose file two ways — correctly merged, and literally spliced in place as printed — and mechanically validated both with the real `docker compose config` loader, not just `yaml.safe_load`. The literal splice: `yaml.safe_load` **passes silently** while actually collapsing `services:` down to 2 of 6 (later services swallowed as nested keys under the first `volumes:` mapping) and losing `app-scratch` entirely (last-key-wins); `docker compose config` correctly **rejects** the same file with `mapping key "volumes" already defined`. A real implementation-time corruption risk, not a nitpick — confirmed against the actual authoritative tool, not just a YAML parser. | High | Resolved | §3.3 reformatted into two explicitly separate fragments (the self-contained `app:` body, then a clearly-labeled instruction to merge one line into the file's existing top-level `volumes:` block) with an explicit warning not to paste them contiguously, and a note that `docker compose config` — not `yaml.safe_load` alone — is the check that actually catches a mistake here. |
| RT-2026-07-09-48 | 2026-07-09 | §9 step 6 (caddy rollout step) | Bundles three changes — Caddyfile global `http_port`/`https_port` block, compose `user:`, compose `cap_drop: ["ALL"]` + host port remap — with no statement that they must land atomically. Verifier traced both partial-application failure modes: compose half first → non-root Caddy with no `NET_BIND_SERVICE` tries to bind ports 80/443 → `EACCES` crash-loop of the stack's sole ingress; Caddyfile half first → Caddy listens internally on 8080/8443 while the host still forwards the old ports → silent full-site outage, uncaught by any healthcheck (caddy has none). | High | Resolved | §9 step 6 now states the atomicity requirement explicitly and names both failure modes. |
| RT-2026-07-09-49 | 2026-07-09 | §9 step 9 (clamav rollout step) | Doesn't mention §8.3's volume-ownership migration, unlike step 6 (caddy) and step 8 (backup), which both explicitly append "+ one-shot volume chown." The current, unhardened `clamav` service sets no `user:` override, so `/var/lib/clamav`'s ownership after any prior root run under the `av` profile isn't guaranteed already-uid-100. | Medium | Resolved | §9 step 9 now names the migration explicitly, matching the parallel structure already used for caddy and backup. |
| RT-2026-07-09-50 | 2026-07-09 | §10 `.dockerignore` completeness, both the replacement pattern list and the `[VERIFY AT IMPLEMENTATION]` footnote | Four confirmed gaps: (1) the bare, root-anchored `scripts/` pattern misses `server/scripts/` and `frontend/scripts/` — `server/scripts/smoke_gemini.py` confirmed actually shipping into the built runtime image; (2) `caos/frontend/coverage/` (1.2 MB) matched no pattern; (3) `**/.venv` was fully redundant with `**/.venv*` already present; (4) the footnote cited a nonexistent file (`frontend/.env.example`) instead of the real one affected (`caos/.env.example`). A fifth, separate gap: §7.1's new `Dockerfile.backup` introduces a second, entirely unfiltered build context (`caos/deploy/`) this blueprint never addressed. | Medium | Resolved | `scripts/` widened to `**/scripts`; `**/coverage` added; redundant `**/.venv` line removed; footnote corrected; new `caos/deploy/.dockerignore` added covering the second build context. |
| RT-2026-07-09-51 | 2026-07-09 | §2.1 digest-resolution workflow's stated mechanism ("requesting index media types first is what makes this return the multi-arch digest") | Verifier executed the exact curl commands against multiple images — including a fresh, never-before-queried tag — with a single-platform-only `Accept` header and with no `Accept` override at all; all variants returned the identical OCI index digest and content-type. Docker Hub appears to serve the index unconditionally for these tags regardless of header content; the stated causal mechanism doesn't hold as tested. | Low | Resolved | §2.1 corrected: the resolved digest values are unaffected (still correct either way — 7/7 independently re-verified exact matches across two separate verifier passes), but the causal claim is now flagged as untested-on-other-registries rather than asserted as fact. |
| RT-2026-07-09-52 | 2026-07-09 | §2.3's capability-dropping guarantee ("`cap_drop: ["ALL"]` + non-root user ⇒ CapEff all-zero by construction, because there's nothing to drop from a non-root process") | Imprecise as stated — a non-root process exec'ing a binary with file capabilities set via `setcap`, *without* `cap_drop: ["ALL"]` in effect, absolutely can gain non-zero capabilities (exactly the mechanism caddy's own baked-in `setcap cap_net_bind_service` bit would otherwise exploit, per the document's own §5.1). Also stated as an unconditional guarantee with no acknowledgment that it assumes a non-buggy container runtime — verifier researched and cited a real, patched vulnerability in exactly this mechanism (runc CVE-2022-29162, fixed 1.1.2) where a buggy runtime could populate a container's inheritable capability set, which combined with a binary's file-inheritable bits can smuggle capabilities in independent of the bounding-set restriction `cap_drop: ["ALL"]` actually relies on. | Medium | Resolved | §2.3 corrected to name the real mechanism (bounding-set intersection in the kernel's exec-time capability formula, per `capabilities(7)`), note `no-new-privileges`'s complementary role for the adjacent setuid vector, and flag the runtime-version dependency. Practical conclusion (CapEff reads all-zero on any current Docker Engine/runc) is unchanged — this was a precision fix to the stated justification, not a change to any recommended directive. |

Verifier method note (follow-up pass): all five passes ran independently in parallel with no shared context; three (RT-47, RT-50, RT-51) executed real commands against live systems (assembling and validating an actual compose file with the real `docker compose config` loader; running curl against seven live registries plus adversarial control requests; researching a real CVE via primary source) rather than reasoning from the document's text alone. RT-46, the highest-impact finding of either audit pass, was found by a subagent whose assigned task was a narrower `.dockerignore` check — it surfaced while tracing "what else reads a `.md` file at runtime," one level past what was strictly asked, which is the kind of finding a narrowly-scoped check can miss entirely if a verifier doesn't follow a thread past its literal instructions. No verdict in this table rests on an unexecuted or unverified subagent run.

**Second follow-up pass**: user asked "anything else" after the cross-cutting pass above. The fixes just applied in that pass (§1.4's new prerequisite, §3.3's restructured compose block, and several smaller corrections) had been written by the same session that found the problems they fix — nobody had adversarially checked whether the fixes themselves were correct and complete. Three more fresh-context subagents verified the fixes directly: one re-derived the Modular OS bind-mount's path arithmetic and write-safety from scratch, one re-assembled the full compose file a second time (now including the new bind-mount line) and validated it with a working `docker compose config` in that agent's environment, and one swept the document itself for internal contradictions introduced by the edits. Two of the three found something.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-09-53 | 2026-07-09 | §1.4's Modular OS bind-mount fix, presented as sufficient to resolve the `LiveSynthesizer` failure | Unlike the named volumes elsewhere in this blueprint, a bind mount performs no ownership remap — Docker never chowns a bind-mounted host directory, and this stack sets no `userns_mode`. Access to the corpus depends entirely on the host directory's raw permission bits granting the container's uid 10001 (no matching owner/group) at least "other" read+execute. Verifier confirmed this works today only because of this checkout's default umask (`755`/`644`, world-readable) — a host with a hardened default umask (`027`/`077`, common on CIS-hardened servers) would checkout the corpus without world-read bits, and uid 10001 would hit `EACCES` on every prompt file: the identical `SynthesisError` failure this section exists to fix, just relocated from "path missing" to "permission denied," and equally silent until the first real synthesis call. Compounding this: §3.4's verification block for the `app` service never actually reads a file under `/Modular OS` — the stated "functional gate" only exercises the OCR upload lane, giving zero signal on whether §1.4's fix actually works. | High | Resolved | §1.4 gained an explicit permission-dependency caveat with a pre-deploy check (`find ... ! -perm ...`) and fix command (`chmod -R o+rX`). §3.4 gained a dedicated read-test (`test -r .../CP-1_ACTIVE_PROMPT.md`) plus an instruction to trigger one live synthesis call as the real end-to-end proof. §9 step 4 (app rebuild) now explicitly names §1.4 and its verification as part of that step, rather than leaving it implicit. |
| RT-2026-07-09-54 | 2026-07-09 | §13's closing sentence ("Every CONFIRMED-ISSUE finding above was fixed... none were left as known-broken") vs. §13.1's own text three paragraphs later ("nothing found was left open except the two items already flagged in §13's table") — and separately, §12's coverage-summary row for `backup` ("no unresolved unknowns") vs. §13's own row for the same service noting an unfixed `PGPASSWORD` bug in `backup.sh`'s restore-drill comment | A reader skimming §13's closing line in isolation would reasonably conclude every finding was fixed outright; §13.1, describing the same table, explicitly names two rows using "flagged as unresolved"/"documented as an open gap" language. Both statements are true under a narrow reading ("no documentation claim was left factually wrong" vs. "no underlying risk was left open"), but sitting three paragraphs apart without reconciling the two readings is a real internal-consistency defect a careful reader would catch. The `backup` row makes the same class of error more narrowly — an absolute claim directly contradicted two sections earlier in the same document. | Medium | Resolved | §13's closing line reworded to state the actual, narrower claim (fixed-or-explicitly-flagged, nothing silently dropped) rather than implying universal resolution. §12's `backup` row and its "items gating full confidence" paragraph both corrected to name the two explicitly-accepted-open items (app OCR memory footprint, clamav concurrent-scan sizing) instead of omitting them. |
| RT-2026-07-09-55 | 2026-07-09 | §9 step 6 and §13.1's table both cite "(§11.4)" as the source for "caddy has no healthcheck" | §11 item 4 is titled "oauth2-proxy healthcheck gap" and is about that service's distroless-image inability to have a `HEALTHCHECK`; it mentions caddy only in passing (its `depends_on` can't use `condition: service_healthy`). The underlying fact cited is independently true (§5.2's compose block genuinely has no `healthcheck:`), so this wasn't a factual error, but the citation pointed at a section whose stated topic is adjacent-but-different from the specific claim being sourced to it. | Low | Resolved | Both citations changed to reference `caddy`'s own compose block (§5.2) directly rather than the oauth2-proxy-titled appendix item. |
| RT-2026-07-09-56 | 2026-07-09 | §3.3's two-fragment restructuring (the RT-47 fix from the prior pass) | The restructuring successfully eliminates the silent-corruption risk it was designed to fix (independently re-confirmed: `docker compose config` accepts the correctly-assembled file cleanly, with the new Modular OS bind-mount line coexisting correctly alongside the other two `volumes:` entries in the `app` service). But verifier tested the adjacent failure mode of selecting/pasting across both fences *and* the prose paragraph between them, and found it produces a loud, immediate YAML parse error — safer than the original bug, but the document's own house style (which uses bold text and a `[CONFIRMED BY AUDIT]` tag to warn about the original risk) had no equivalent one-line warning against this milder but still-avoidable copy-paste hazard. | Low | Resolved | Added a one-line instruction to copy each fenced block separately rather than selecting across the gap between them. |

Verifier method note (second follow-up pass): all three passes ran independently with real command execution, not just reasoning from the document's text — one traced `synth.py`'s actual path arithmetic and full read/write behavior in Python rather than trusting the blueprint's citation; one located a working `pyyaml` install and, separately, a working `docker compose config` in its own environment (this session's own environment has neither reliably available) and used both to re-validate the assembled compose file, including reproducing the exact negative-control failure the prior pass's RT-47 finding described, confirming that citation was accurate and the fix for it works; one did a pure grep-and-cross-reference sweep of the document and redteam.md for internal contradictions, catching a genuine tension between two sections' completeness claims that neither prior pass had been scoped to notice since each prior pass was checking technical correctness, not the document's own rhetorical consistency. No verdict in this table rests on an unexecuted or unverified subagent run. This is the third independent round of adversarial verification on this blueprint (six-image audit → cross-cutting gap check → fix verification); each round found real, distinct defects, and this round's findings were narrower in scope and lower average severity than the prior two — consistent with genuine convergence rather than an artifact of continuing to look.

**2026-07-11 pass**: audit finding #5 (rolling multi-replica boot sweep killing a live sibling's job) — `research_report_executor.py` and `engine/pipeline_executor.py` gained the same lease-expiry-gated reap `run_executor.py`'s `QueueWorker._reap_orphans` already uses. (The originally-planned third executor, `research_executor.py`, was rescoped out on the 07-11 rebase: main's migration `0036_research_job_lease` had independently landed the full four-column claim/lease treatment for `research_jobs`, so this change covers only the two executors main left with unconditional boot sweeps.)

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-11-01 | 2026-07-11 | Give `PipelineRun` a `queued` state so `pipeline_executor.claim_next_job`'s Postgres `SKIP LOCKED` path can claim it, per the audit's open question | `claim_next_job` solves claiming *unclaimed* work from a shared pool — a race that doesn't exist here. `enqueue()` in both executors spawns the task same-process, synchronously, right after the route commits the row; no second worker ever contends for the same row. Changing the lifecycle to fit an unused claim path would touch `routes/autonomy.py` and `engine/pipeline.py` for no correctness gain. | Medium | Resolved | Left `claim_next_job` exactly as its own docstring says — additive and inert infrastructure for a future sync→enqueue+poll route rewiring. Fixed the actual bug (unconditional sweep) directly in each executor's `start()`, orthogonal to queued-vs-running. |
| RT-2026-07-11-02 | 2026-07-11 | Give `IssuerResearchReport` the same four lease columns as `Run` (`claimed_at`, `lease_expires_at`, `attempts`, `worker_id`), per the audit's suggested starting shape | Nothing polls for a lease-expired row and retries it in these two systems (unlike `QueueWorker`) — a lease-expired row goes straight to `failed`, once, exactly like today's unconditional sweep already does. `attempts` would never move past 0→1; `claimed_at` would always equal `created_at` (row is born running, spawned immediately) — both would be dead columns carried forever. | Low | Resolved | Added only `lease_expires_at` (gates the reap) + `worker_id` (audit trail) via migration `0038_background_job_leases`. `PipelineRun` already had `worker_id`; only `lease_expires_at` was new there. (`research_jobs` got all four columns from main's `0036` instead — its re-claiming QueueWorker model genuinely uses them.) |
| RT-2026-07-11-03 | 2026-07-11 | Treat `lease_expires_at IS NULL` as reapable in the gated sweep | A row could be `status='running'` with a NULL lease in the microseconds window between the route's commit and the spawned task's own lease-set commit — if a sibling replica boots in that exact window, is reaping it safe? | Low | Accepted | Yes: (a) boot sweep only ever runs in `start()`, before any request is served on that replica, so it can never race its own in-flight work; (b) the only way another *live* replica's row has a NULL lease is that same sub-millisecond window, and if the reaping replica commits `failed` there, the owning replica's own later `session.commit()` (which holds the stale ORM object, unaware of the intervening write) will still write its real terminal status last — SQLAlchemy has no compare-and-swap here, so last-write-wins and the true outcome survives. Worst case is a redundant failed→complete flip visible for one poll tick, never a lost result. This mirrors the codebase's existing tolerance for narrow best-effort commit windows (e.g. `run_executor.py`'s CancelledError-after-commit guard). NULL-as-reapable is also required to sweep legacy pre-migration rows. |

## Resolved Objections

## Outstanding Audit Remediation — Critic Pass (2026-07-11)

Decision under review: close every item that `caos/docs/AUDIT.md` still presents as outstanding.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-11-57 | 2026-07-11 | Treat all four audit rows as immediate defects | `S-4` requires an entitlement policy and `A-1` spans multiple engine/data contracts, including Phase-2 market data. A quick implementation would invent access rules and relabel seeded output as live. | High | Resolved | Preserve both as explicit roadmap constraints. Close only defects independently verified in current code; do not claim Phase-2 architecture is implemented. |
| RT-2026-07-11-58 | 2026-07-11 | Mark `PERF-2` resolved because dynamic imports exist | Source-level code splitting does not prove the shipped first-load payload improved; stale build artifacts can also mislead. | Medium | Resolved | Require a fresh production build and record its route-size evidence before changing the finding status. |
| RT-2026-07-11-59 | 2026-07-11 | Remove `F-2` suppressions mechanically | Replacing `any` with broad assertions could preserve lint cleanliness while weakening useful type checks in the shared Model Builder/Reports engine. | Medium | Resolved | Use narrow structural input types for the three finalizers, retain strict compilation, and run model/scenario plus full frontend tests. Fixture-wide disables may be removed only after linting those files with inline config disabled. |

- RT-2026-07-02-01: Discoverability gap fixed by linking this log from `AGENTS.md`.
- RT-2026-07-02-02: Malformed impact/status evidence fixed by replacing the initial row with explicit `Impact` and `Status` columns.
- RT-2026-07-02-03: Evidence-handling risk fixed by adding a no-secrets protocol rule.

## Accepted Objections

- RT-2026-07-02-04: No substantive CAOS proposal exists in this turn. Accepted because the decision under review is only the gate.

## Critic Reopen Check

Round 2 did not reopen RT-2026-07-02-01 or RT-2026-07-02-02 because the current files contain direct evidence for both fixes. No high-impact objection remains open.

## Stalemate

None.

## Residual Design Rebuild Continuation — Critic Pass (2026-07-12)

Decision under review: resume the residual-gap plan in the attached reconnaissance after the completed G1-G8 work, beginning with the partially written Coverage Control Plane and then the Scenario Network, IC Decision Room, and Thesis Memory.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-12-01 | 2026-07-12 | Complete the in-progress ingestion-gap endpoint as the first G14 slice | The partial implementation caps the cross-tenant OCR document-id query before applying issuer visibility, so another team's rows can consume the cap and hide a caller's own OCR gaps. The frontend API contract is also absent, leaving the current tree uncompilable. | High | Resolved | Replace the global id scan with a tenancy-scoped correlated existence query, add the typed API client, and keep endpoint/component tests in the same slice. |
| RT-2026-07-12-02 | 2026-07-12 | Propagate every scenario node, including portfolio loss | G9 can accidentally smuggle in the vetoed G12 positions/OMS architecture or fabricate a position-weighted loss when no linked portfolio data exists. | High | Resolved | Scenario propagation reuses only existing run and portfolio-fit fields. Any unavailable portfolio input returns `NO_DATA` or downstream `DEGRADED`; it does not create positions, OMS state, or synthetic exposure. G12 remains deferred unless the user explicitly overrides the product boundary. |
| RT-2026-07-12-03 | 2026-07-12 | Add IC decisions and versioned thesis memory in one rollout | A mutable live report or thesis read could drift after approval and falsely imply that the committee approved later evidence. | High | Resolved | Decisions store an immutable snapshot and document hash, votes append rather than rewrite the snapshot, and material-change reopen creates an audit event plus a new thesis version. No endpoint updates a prior snapshot in place. |
| RT-2026-07-12-04 | 2026-07-12 | Finish the full Control Plane described in G14 | Entitlement visibility and full audit-history UI have no defined source contract and overlap the explicitly deferred G15 scope. | Medium | Accepted | This continuation ships live ingestion gaps, origin rollup, and analyst ownership only. Entitlements and expanded audit history remain deferred and are rendered nowhere until a real policy/source exists. |

## Critic Reopen Check (2026-07-12)

The continuation is allowed only while each implementation preserves the resolutions above. Any scenario code that invents portfolio exposure, any decision update path that mutates a snapshot, or any entitlement schema is a stop-and-escalate condition.

## Design Rebuild Phases 1+2 — Critic Pass (2026-07-11)

Decision under review: the approved Phases 1+2 implementation plan for the persona-led design rebuild (workflow-grouped nav, role views, provenance grammar, decision header, shell consolidation, ⌘K palette; then per-surface restructuring per `.agent-reviews/design-rebuild-handoff.md`). Branch `feat/design-rebuild-p1` off `origin/main@9326fc92`.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-11-60 | 2026-07-11 | WP1 workflow-grouped ConceptNav with group micro-labels | 5 group labels (~40–60px each at 7.5px uppercase) added to 12 compact chips ≈ +250px in the 40px strip; dense headers (Model: badge + title + provenance + save-state + two actions) already crowd 1280px. Full labels overflow. | High | Resolved | Compact mode labels only the ACTIVE group (extends the existing active-chip-label pattern); inactive groups render separator + tooltip. Explicit verification gate: preview measurement at exactly 1280px on Model and Query before the WP commits. MEASURED 2026-07-11 (qa-frontend :3010, /model): compact nav = 520px, fully visible at ≤1279 (MoreDrawer collapse gives identity 820px) and ≥~1330. Model's identity container was ALREADY clipped pre-change at every width below ~1900px (scrollWidth 1138 vs 643 client at 1440 — title/provenance silently hidden by `overflow-hidden` before this work); the group labels add ~60px to that pre-existing deficit, which at exactly 1280–1330 pushes the nav tail (Settings/badge) into the clip. Structural fix assigned to WP2: Model identity gets `min-w-0 truncate` on the title so text shrinks instead of hard-clipping trailing chrome. |
| RT-2026-07-11-61 | 2026-07-11 | WP3 persisting `role_view` server-side vs localStorage-only | A presentation preference does not obviously justify a server schema field; localStorage is one line. | Medium | Resolved | Server field kept for two verified reasons: (1) handoff locks "persist in the existing analyst settings JSON" for multi-device consistency; (2) `PUT /api/settings/analyst` replaces the whole blob and GET filters to known model keys — an undeclared key is silently destroyed by the next writer, so a client-only key inside that JSON is structurally impossible without the model change anyway. localStorage stays as instant-paint cache and as the fallback for the local-dev bypass identity whose PUT 404s. |
| RT-2026-07-11-62 | 2026-07-11 | WP6 palette taking over ⌘K from Ask | Analysts have ⌘K→Ask muscle memory; a nav palette answering that chord breaks a trained reflex on a daily-use tool. | Medium | Resolved | Free text in the palette always surfaces an `Ask CAOS: "<text>"` row ranked first whenever input doesn't strongly match a page/issuer, so ⌘K→type→Enter still lands in Ask for question-shaped input; Alt+K keeps today's direct-Ask behavior unchanged; AskLauncher button untouched. Accepted residual: two keystroke paths diverge for one release; revisit after adoption. |
| RT-2026-07-11-63 | 2026-07-11 | WP1 Alt+←/→ cycle order change (`CONCEPT_CYCLE` = visual order; `/issuers` + `/upload` join the cycle) | Deliberate behavior change to a shipped, test-covered hotkey; users cycling by spatial memory get re-ordered stops. | Low | Resolved | Accepted: cycle order equal to visual nav order is strictly more predictable than today's divergent hidden order (current `CONCEPTS` array omits two routes and disagrees with `SECTIONS`). Single source of truth removes the drift class permanently. Tests updated in the same commit; noted in commit message. |
| RT-2026-07-11-64 | 2026-07-11 | WP2 single-breakpoint consolidation (`useBreakpoint` matchMedia 1280/1024/768 replacing SubHeader's matchMedia + ResponsiveShell's `innerWidth` listener) | `innerWidth` includes scrollbar width; `matchMedia` viewport may not — on platforms with classic scrollbars the 1024 threshold can flip within a ~15px band, changing which contract (`contextualControls` vs `essentialControls`) renders vs today. | Medium | Resolved | Accepted: the band is hairline, macOS (primary target) uses overlay scrollbars where the two agree, and one consistent source beats two disagreeing ones (today a 1024–1280 window already renders the full contextual set inside a collapsed drawer — an incoherence this fix removes). Verification gate: preview at exactly 1280/1024/768 on all migrated pages. |
| RT-2026-07-11-65 | 2026-07-11 | WP4 legacy→grammar mapping (SEEDED, REFERENCE, sample, illustrative → Origin axis) | Inconsistent mapping would relabel seeded output — violating the non-negotiable "never relabel seeded/reference/fallback as live" and potentially inflating DEMO fixtures to REFERENCE credibility. | High | Resolved | Mapping rule fixed and recorded: current copy saying demo/sample/illustrative → `DEMO`; curated reference fixtures/templates (Deep-Dive/Pipeline reference issuer, Reports reference templates) → `REFERENCE`; `LIVE` requires a live run id/engine flag, never inferred. Omitted axes render nothing (no fake `CURRENT`). Mapper unit tests assert no legacy label maps to LIVE. |
| RT-2026-07-11-66 | 2026-07-11 | Phase-2 WP-0 new `alert_states` table for ack/assign | New table for two fields smells like scope creep; `qa_flags` already exists as a write-path. | Low | Resolved | Reuse rejected deliberately: `qa_flags` lacks state/assignee semantics and shares the CP-5 QA queue — mixing alert acks in would pollute a governance surface with triage noise. Table is 7 columns cloning the proven `qa.py` pattern; cycle-scoped `alert_key` makes re-fired anomalies correctly reset to open. Smallest honest persistence. |
| RT-2026-07-11-67 | 2026-07-11 | Building on `origin/main` while the user's local `main` and two pre-deployment docs remain behind/diverged | Later merge of this branch could tangle with the user's unreconciled doc WIP. | Low | Accepted, flagged not fixed | User explicitly chose this split (build on refreshed code; docs stay theirs to reconcile). Doc files are never staged by this work; branch tracks `origin/main`; the docs conflict resolves whenever the user reconciles, independent of this branch. |

## Decision Workbench Consolidation — Critic Pass (2026-07-12)

Decision under review: apply both user-supplied wireframe batches and the 2026-07-12 Impeccable critique across the current frontend while preserving the shipped analytical substrate.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-12-68 | 2026-07-12 | Add a persistent desktop workflow rail at the root layout | Every route already embeds `ConceptNav`; rendering both creates duplicate landmarks, duplicate role controls, and a narrower modeling canvas. | High | Resolved | The root rail owns full desktop navigation. Embedded `ConceptNav` becomes the compact/tablet fallback and is suppressed when the persistent rail is active. Role view appears once per viewport contract. The model body keeps horizontal overflow and its existing editor implementation. |
| RT-2026-07-12-69 | 2026-07-12 | Make the wireframes the new visual language | The wireframes are mid-fi and rely on very small mono text, clipped right rails, and empty black space. Literal reproduction would worsen accessibility and repeat the critique's hierarchy defects. | High | Resolved | Treat them as spatial and workflow contracts only. Production styling follows `DESIGN.md`: readable sans for prose, mono for numerics/metadata, 10px desktop operational floor, AA contrast, deliberate panel rhythm, and responsive evidence drawers. |
| RT-2026-07-12-70 | 2026-07-12 | Expose `LIVE` prominently throughout the new authority system | Transport freshness can be mistaken for analytical approval, especially beside generated Watchtower output. | High | Resolved | Conclusion authority is always composite: origin, method, approval, freshness. Standalone `LIVE` is limited to feed/source origin and never implies ratification. |
| RT-2026-07-12-71 | 2026-07-12 | Apply role-specific layouts across all pages | Separate role implementations would drift, duplicate business logic, and risk turning presentation preference into access control. | High | Resolved | Role views are composition-only selectors over the same read model. Shared components reorder or disclose existing fields; no role-specific endpoint, calculation, or authorization branch is added. |
| RT-2026-07-12-72 | 2026-07-12 | Finish every proposed net-new feature while redesigning the shell | Combining Portfolio Decision Lab, entitlement control plane, sponsor network, and shell migration expands the blast radius beyond verifiable UI work and could invent missing source contracts. | High | Resolved | This pass connects already-shipped decision, thesis, scenario, Watchtower, and governance components. It does not invent entitlements, OMS/positions, or new compute. Incomplete source contracts remain explicit unavailable states. |
| RT-2026-07-12-73 | 2026-07-12 | Apply global panel styling to achieve the reference look | `Panel` is a high-risk shared primitive affecting Deep-Dive, Command, and Model. API or overflow changes could break analytical flows. | High | Resolved | Preserve the `Panel` API and scroll measurement. Prefer shell tokens and CSS-level hierarchy; any Panel markup change must retain focusable-overflow behavior and pass primitives, Deep-Dive, Command, and Model tests. |

### Critic reopen conditions

Stop and revise if the implementation duplicates navigation/role controls at desktop, hides modeling functionality, labels generated output as ratified/live, introduces a role-specific compute path, or requires an entitlement/OMS contract that does not exist.

## Workbench + Atlas Enterprise Remediation — Critic Pass (2026-07-13)

Decision under review: migrate the complete frontend to a shared enterprise page anatomy and explicit decision/recovery state grammar while preserving the institutional terminal and shipped analytical substrate.

| ID | Date | Decision under review | Objection | Impact | Status | Resolution |
|----|------|----------------------|-----------|--------|--------|------------|
| RT-2026-07-13-74 | 2026-07-13 | Replace nullable decision values with explicit states | A mechanical wrapper could relabel every existing `undefined` as a successful empty observation, preserving the exact dangerous ambiguity this migration exists to remove. | High | Resolved | `observed-empty` is an explicit state that requires `asOf` and authority. Missing legacy props adapt to `unavailable`, never to “No material change.” Routes may claim no material change only after a successful source response. |
| RT-2026-07-13-75 | 2026-07-13 | Put every route inside one enterprise page component | Full-screen tools (Model, Query graph, Report Studio) have materially different overflow and finalization needs. A rigid wrapper would create nested scroll containers and regress the editors. | High | Resolved | The shared contract standardizes chrome and state semantics but keeps surface kinds (`worklist`, `object`, `analytical`, `editor`, `wizard`). Editors retain their current workspace body and overflow ownership; finalization and evidence regions are opt-in slots. |
| RT-2026-07-13-76 | 2026-07-13 | Standardize all tables and worklists | Replacing the bespoke Model sheet or virtualized Command grid with a generic table would remove spreadsheet behavior and degrade large-dataset performance. | High | Resolved | The workbench contract applies to list/worklist surfaces only. Model remains a spreadsheet instrument. Command keeps virtualization and receives shared toolbar/count/action anatomy without changing its data engine. |
| RT-2026-07-13-77 | 2026-07-13 | Collapse secondary controls into utility drawers | Hiding replay, scenario, or layout controls can slow expert users and break trained keyboard paths. | Medium | Resolved | Only low-frequency controls move; keyboard accelerators and direct primary actions remain. Drawers use labeled sections, disclose current state in the trigger, close on Escape, and restore focus. |
| RT-2026-07-13-78 | 2026-07-13 | Continue showing `AN / PM / QA` in the global rail | The abbreviations can be interpreted as authorization or governance authority, particularly when QA view exposes gates. | High | Resolved | The visible control is renamed `View: Analyst / PM / QA`, and supporting copy states “presentation only — permissions unchanged.” Approval controls continue to derive solely from existing authorization and data contracts. |
| RT-2026-07-13-79 | 2026-07-13 | Add one evidence inspector to every surface | Always-visible evidence would steal width from tables and editors and duplicate route-native evidence panes. | Medium | Resolved | Evidence is a shared semantic component, not an always-mounted third pane. Routes with native evidence reuse it; worklists open the inspector contextually; narrow layouts use a drawer. No page renders two evidence inspectors. |
| RT-2026-07-13-80 | 2026-07-13 | Migrate every route in one pass | A big-bang shell/state change makes regressions difficult to isolate and could leave half-migrated routes with incompatible state contracts. | High | Resolved | Land compatibility-first shared primitives, then migrate analyst, PM, and QA/publishing route groups. Legacy props remain supported as `unavailable` adapters until every route is explicit; removal occurs only after route tests and screenshot gates pass. |

### Critic reopen conditions (2026-07-13)

Stop and revise if any failure renders as “No material change,” any editor gains an extra scroll owner, any presentation view changes permissions, any list migration removes virtualization/spreadsheet behavior, or any surface displays duplicate evidence regions.

## Workbench + Atlas — Final Adversarial Reopen Check (2026-07-13)

| ID | Perspective | Objection | Impact | Status | Resolution |
|----|-------------|-----------|--------|--------|------------|
| RT-2026-07-13-81 | Saboteur | Static browser verification proves recovery/layout behavior but not a live backend handoff preserving every cross-route filter and selection. | Low | Accepted | Component and integration tests cover the state contracts; record a backend-connected Playwright journey as release hardening, not as a prerequisite for this API-neutral UI migration. |
| RT-2026-07-13-82 | New Hire | Route-local mappings into the shared decision-state contract may drift in timestamp and authority handling. | Low | Accepted | Keep mappings explicit while domain semantics differ; extract only when identical mappings recur. Central types and rendered contracts already prevent nullable ambiguity. |
| RT-2026-07-13-83 | Security Auditor | The opt-in Playwright identity stub could be mistaken for an authorization test. | Low | Resolved | The stub lives only in local scripts, intercepts one browser context, requires `BYPASS_AUTH=1`, and is documented as post-auth surface verification rather than policy validation. |

Final verdict: **CLEAN** — no critical or warning findings. Full report: `.agent-reviews/adversarial-workbench-atlas-2026-07-13.md`.

## Query + Sector Review + RV Full-Stack Redesign — Critic Pass (2026-07-13)

Decision under review: retain three focused analytical routes while introducing shared analyst-owned context, versioned CP-SR/RV/Query runs, explicit ratification, and normalized source adapters.

| ID | Perspective | Objection | Impact | Status | Resolution |
|----|-------------|-----------|--------|--------|------------|
| RT-2026-07-13-84 | Saboteur | A migration that continues ranking market outliers as actionable while recovery, downside, instrument identity, or portfolio impact is missing would preserve the highest-risk false-positive behavior under new chrome. | High | Resolved | The RV contract separates `actionable`, `screen_only`, and `unavailable`. Only current market evidence, cohort n≥2, exact instrument identity, downside/recovery, and portfolio impact can produce `actionable`; every missing gate is returned explicitly. |
| RT-2026-07-13-85 | New Hire | Three new route implementations could repeat the current monoliths and create another incompatible context model per concept. | High | Resolved | Shared domain contracts live outside route components; routes compose context, runs, findings, and authority through typed clients/hooks. Existing route paths remain stable and compatibility adapters stay until parity tests pass. |
| RT-2026-07-13-86 | Security Auditor | Persisting shared contexts and findings creates an IDOR surface and could expose one analyst's sensitive investigation to another. | High | Resolved | Every context, finding, ratification, and run is analyst-scoped at query time; foreign IDs return 404. Question text is stored server-side, never in the URL, and client storage becomes a non-authoritative cache only. |
| RT-2026-07-13-87 | Saboteur | Treating today's reference JSON and seed sector signals as normalized inputs could quietly upgrade them to live evidence. | High | Resolved | Imports preserve `DEMO`/`REFERENCE` origin. Reference snapshots may render and support screen-only exploration but cannot be published, ratified as live, or satisfy an actionable RV gate. |
| RT-2026-07-13-88 | New Hire | Sector Review, RV, and Query currently use different sector labels and can hand off incompatible universes. | High | Resolved | One canonical taxonomy plus alias map is applied at ingestion. Cross-route handoffs pass an analyst-owned `AnalysisContext` containing canonical sector, instrument, snapshot, and run identifiers; mismatches render `partial`, never silently recompute. |
| RT-2026-07-13-89 | Saboteur | A failed refresh could replace the last ratified review with an empty/error draft or make downstream consumers read an in-progress version. | High | Resolved | Published review versions are immutable. Refresh creates a separate draft job; downstream consumers read only the latest ratified published version. Failed/cancelled jobs preserve the prior published artifact. |

### Critic reopen conditions (2026-07-13)

Stop and revise if reference/demo data becomes actionable, any foreign analyst ID is distinguishable from a missing ID, a draft run replaces a published artifact, any route silently drops the shared context, or a missing RV evidence gate still renders “Cheap,” “Add,” or an actionable recommendation.

## Query + Sector Review + RV — Final Adversarial Review (2026-07-13)

Scope: the implemented analysis contracts, migrations, owned context/findings APIs, versioned Query/Sector/RV routes, three replacement workbenches, and the live Sector → RV → Query → Findings → Report Studio journey.

| ID | Perspective | Finding | Severity | Status | Resolution / disposition |
|----|-------------|---------|----------|--------|--------------------------|
| RT-2026-07-13-90 | Saboteur | The floating Ask launcher intercepted Sector Review's sticky `Request refresh` action, making the primary workflow unclickable despite correct visual placement. | Warning | Resolved | The launcher now clears sector finalization bars. The real Playwright click path passes at desktop, tablet, phone and 200% zoom. |
| RT-2026-07-13-91 | Saboteur | First-load taxonomy inserts raced under simultaneous context creation and could fail with a uniqueness error. | Warning | Resolved | Canonical taxonomy seeding moved into migration `0047`; runtime workers treat it as immutable reference data and fail explicitly when migrations are missing. |
| RT-2026-07-13-92 | New Hire | Query's generic row adapter rendered nested metric results as `Result 1` and hid the rank's financial meaning. | Warning | Resolved | The adapter now recognizes the legacy nested issuer envelope and displays issuer, ticker, industry, metric label, value and unit. |
| RT-2026-07-13-93 | Security Auditor | Findings accepted a client-authored `AuthorityEnvelope`, allowing an authenticated analyst to forge `LIVE`/`RATIFIED` metadata disconnected from the cited run. | Critical after Saboteur corroboration | Resolved | Findings now require an owned source run, resolve authority server-side, start draft, and reject ratification unless the source is current, live and source-backed. Foreign or mismatched runs return 404. |
| RT-2026-07-13-94 | New Hire | `routes/sector.py` now contains both legacy compatibility routes and CP-SR V2 and remains an 1,100-line change hotspot. | Warning | Accepted | Compatibility cannot be retired until downstream parity is proven. The V2 frontend is isolated in a 204-line dossier and shared contracts are separate; split the backend module when legacy endpoints are removed. |
| RT-2026-07-13-95 | Saboteur | Sector display-version allocation is serialized only by normal request flow; concurrent multi-worker refreshes can allocate the same display version because version is still embedded in the payload rather than protected by a unique database column. | Warning | Accepted | Run IDs remain unique and published artifacts are not overwritten, so decision integrity is preserved. Add a dedicated context/version column and uniqueness constraint before enabling high-concurrency scheduled refreshes. |
| RT-2026-07-13-96 | Security Auditor | Context `filters`/`selected` and finding `evidence` remain opaque JSON objects; field-level schema validation is deliberately deferred to adapter-specific contracts. | Note | Accepted | Auth ownership, request-size middleware and write-rate limits bound the current exposure. Promote adapter payloads to discriminated schemas as external vendors are added. |

Final verdict: **CONCERNS** — no open critical finding. Two contained warnings remain: legacy Sector module concentration and multi-worker display-version allocation. Neither can publish reference data, cross analyst boundaries, or overwrite a prior published review.

## Remaining Surfaces Full Redesign — Critic Pass (2026-07-13)

Decision under review: redesign every concept and contextual surface except the already-migrated Query, Sector Review, and RV Screener, while extending the Workbench + Evidence Atlas contracts across the full application.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-97 | Saboteur | A visual migration could preserve the existing live/reference/demo mixtures and merely make lower-authority content look more credible. | High | Resolved in plan | Actionability, publication, ratification, and ranking gates explicitly reject `DEMO`, `REFERENCE`, and seeded artifacts. Reference work moves into a separate reference workspace rather than the live worklist. |
| RT-2026-07-13-98 | New Hire | Extending `AnalysisContext` to every route could produce one unmaintainable mega-object whose optional fields mean different things on each surface. | High | Resolved in plan | Keep a small owned context identity plus typed, surface-specific references (issuer run, model checkpoint, report version, alert, sponsor event). Adapters declare required references and render `partial` on mismatch; they do not silently recompute. |
| RT-2026-07-13-99 | Security Auditor | Report edits, model inputs, and settings can survive an SSO/profile principal change because browser state is cleared on explicit logout but not necessarily when `/me` resolves to a different analyst. | High | Resolved in plan | Decision-bearing state becomes analyst-owned server state. Browser caches are keyed to the active principal and cleared before rendering when the principal id changes. |
| RT-2026-07-13-100 | Saboteur | A state-dependent primary action can move or change unexpectedly and cause an analyst to commit the wrong operation under time pressure. | Medium | Resolved in plan | The primary action keeps one stable finalization-bar location. Only its label, disabled state, and recovery semantics change; destructive transitions require a reviewable summary and preserve the prior immutable version. |
| RT-2026-07-13-101 | New Hire | Rebuilding all remaining routes risks replacing current monoliths with one shared shell monolith and tightly coupling Model, Report Studio, and worklists. | High | Resolved in plan | Shared contracts standardize authority, context, jobs, worklists, evidence, and finalization only. Model retains spreadsheet ownership, Report Studio retains paper/editor ownership, and route adapters remain separate from domain components. |
| RT-2026-07-13-102 | Security Auditor | Sponsor events, alerts, research briefs, and report claims can expose MNPI or analyst intent if findings/context ids are accepted without owner checks. | High | Resolved in plan | Every context, finding, source manifest, model checkpoint, report draft, sponsor event review, and alert assignment is analyst/tenant-scoped at query time; foreign ids resolve as not found. |
| RT-2026-07-13-103 | Saboteur | Blocking Report Studio export on every imperfect source could strand an IC deadline and encourage screenshots or manual copying outside the audit trail. | Medium | Resolved in plan | The finalization bar names the exact blockers and recovery routes while keeping the prior approved PDF available. Any future waiver requires an explicit permission and immutable exception record; the UI will not invent a client-only bypass. |
| RT-2026-07-13-104 | New Hire | Thirteen surfaces plus shared contracts is too broad for a big-bang release and makes parity impossible to prove. | High | Resolved in plan | Delivery is compatibility-first and staged: foundation; intake/identity; analyst instruments; operations/PM; publishing/policy; ASK; retirement. Legacy paths are removed only after route-level parity and end-to-end context tests pass. |

### Critic reopen conditions (2026-07-13)

Stop and revise if any reference/demo artifact enters a live decision gate, if the shared context becomes an untyped property bag, if principal changes do not clear/re-key caches, if a route gains a second page-level primary action, if Model or Report Studio lose their specialized interaction models, or if ASK bypasses the versioned Query run and findings contracts.

## Remaining Surfaces — Final Adversarial Reopen Check (2026-07-13)

| ID | Perspective | Finding | Severity | Status | Resolution / disposition |
|----|-------------|---------|----------|--------|--------------------------|
| RT-2026-07-13-105 | Saboteur | Model and Deep-Dive technically reflowed at 390px but still exposed workstation authoring controls, contradicting the phone-triage-only contract and encouraging unsafe partial edits. | Warning | Resolved | Both routes now render read-only authority/posture summaries with context-preserving Query/Pipeline/desk handoffs below 640px. The complete instruments remain unchanged from tablet upward. |
| RT-2026-07-13-106 | Saboteur | The new Model primary action initially required an analysis context before saving, so a context outage could block the pre-existing mutable draft save and strand edits. | Critical after compatibility review | Resolved | Save checkpoint now persists the working SavedModel first, preserving legacy error/conflict behavior, then creates an immutable checkpoint when context is ready. Focused conflict tests and the full 673-test frontend suite pass. |
| RT-2026-07-13-107 | New Hire | Report Studio exposed paper, source, editing, zoom, QA, export and submission controls alongside the page action, obscuring the one-primary-action hierarchy. | Warning | Resolved | The header now shows compact editorial state plus the single publish action. Every prior control remains in a labeled utility drawer and existing keyboard zoom shortcuts remain active. |
| RT-2026-07-13-108 | Security Auditor | New private source, model and report artifacts could survive analyst erasure even though their owning context is deleted. | Critical | Resolved | erase_analyst_data deletes report versions/drafts, model checkpoints and source manifests dependency-first, then contexts and principal data. The full 1,457-test server suite passes, including the updated GDPR contract. |
| RT-2026-07-13-109 | Saboteur | Pipeline module exits could silently drop the selected run/context and reopen a different analytical artifact. | Warning | Resolved | CP-0, Deep-Dive and Report Studio exits now carry issuer, run and owned context. The 75-case responsive gate and browser captures verify route stability. |

Final verdict: **CLEAN** — no open critical or warning finding. Reopen if any compatibility adapter is removed before its row in the parity matrix is re-verified against production data.

## Pre-Deployment Plan Reconciliation — Critic Pass (2026-07-13)

Decision under review: replace the stale deployment grounding with a code-backed inventory of every currently discoverable unwired user-facing control, production-data seam, and phase-gate status.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-110 | Saboteur | Calling every disabled control “unwired” would bury real dead ends beneath valid prerequisite gates such as empty Query input, missing selection, in-flight writes, and committee-readiness checks. | High | Resolved in plan | The register separates dead/no-op, intentionally state-gated, local/reference-only, and backend-unwired controls. Only the latter two become remediation rows; valid gates remain documented as wired. |
| RT-2026-07-13-111 | New Hire | A feature can have a migration, API, and rendered button yet still be unusable in production because its only source is reference data or a required dependency is always missing. | High | Resolved in plan | Status is judged end-to-end. RV remains screen-only while its snapshot is reference and risk-budget/recovery/downside inputs are absent; Sector Review and Report Studio remain incomplete while CP-SR/CP-RENDER are spec-only. |
| RT-2026-07-13-112 | Saboteur | Marking open-PR work complete would make `main` look safer than it is and could erase the only visible deployment blockers. | High | Resolved in plan | The document records three separate ledgers: `origin/main`, the committed two-commit branch delta, and uncommitted working-tree implementation. Open PRs are never counted as merged capability. |
| RT-2026-07-13-113 | Security Auditor | Treating presentation views (`Analyst`/`PM`/`QA`) as roles would imply authorization that the server does not enforce. | High | Resolved in plan | Roles-lite remains open. The current selector is recorded as composition-only, and admin/read-only enforcement stays an explicit E2 gate. |
| RT-2026-07-13-114 | New Hire | A “latest status” rewrite based only on source greps could declare the application deployable while the current remote CI is red. | High | Resolved in plan | The top-level gate records the exact failing main-branch Playwright assertions alongside the locally green suite. Local verification does not override the required green `main` run. |
| RT-2026-07-13-115 | Saboteur | A control can have a non-empty handler yet still misrepresent its effect; Upload’s mode selector persists metadata while the queued engine run always takes the full route. | High | Resolved in plan | UW-23/C12 require the selected mode to become an immutable validated server plan, or require all routing claims to be removed. The scan therefore checks semantic effect as well as literal no-op handlers. |

### Critic reopen conditions (2026-07-13)

Reopen if a reference/demo artifact is described as live, if an open PR is counted as merged, if a prerequisite-gated control is mislabeled dead, if a control label overstates its server-side effect, if the two failing `main` E2E assertions disappear from the release gate without a green rerun, or if any phase checkbox is closed from documentation evidence alone rather than current code plus its stated verification.

## CAOS Applicable Updates — Phase 1C freshness critic pass (2026-07-14)

Decision under review: introduce one source-aware freshness policy and reporting-profile contract before replacing the existing surface-specific staleness heuristics.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-14-166 | Credit analyst | Missing fiscal-period, publication, or market as-of metadata could be treated as recent merely because the file was uploaded recently. | High | Resolved in contract | `unknown` is the mandatory result when source-effective metadata is missing or invalid. Upload time is observation metadata only and never substitutes for a reporting period or market as-of. |
| RT-2026-07-14-167 | Saboteur | Fixed day arithmetic can misclassify month-end, leap-year, quarterly, semiannual, annual, or private-company reporting cycles. | High | Resolved in contract | Calendar-period advancement is cadence-aware, evaluated in UTC, and covered at month-end, leap-year, exact-boundary, and timezone edges. Private/event-driven and unknown cadence do not receive an invented due date. |
| RT-2026-07-14-168 | Data-governance reviewer | A restated document or replaced source version could leave a derived run, checkpoint, or report labelled current even though its inputs changed. | High | Resolved in contract | Derived freshness compares the bound source identity/version set with the lineage parents used at creation. A proven mismatch is stale; missing lineage is unknown, never current. |
| RT-2026-07-14-169 | Security auditor | A consolidated freshness endpoint could reveal the existence or timestamps of foreign issuers, contexts, reports, or source artifacts. | High | Resolved in contract | Freshness reads reuse issuer/team/analyst authorization, resolve foreign identifiers as 404, and never traverse lineage outside the caller's owned context. |
| RT-2026-07-14-170 | New hire | One universal age threshold would conflate prices, reported accounts, ratings, legal documents, runs, and derived artifacts. | High | Resolved in contract | The evaluator uses explicit source kinds and independent clocks. Event-driven sources remain current only when their version is known and unchanged; they do not inherit a quarterly clock. |
| RT-2026-07-14-171 | Release engineer | Replacing every existing stale label at once could change production decisions without a rollback path. | High | Resolved in rollout | Schema and metadata writes are additive. New reads and route adapters are gated by `CAOS_LINEAGE_V2_ENABLED`; flag-off preserves the current staleness behavior while stored source metadata remains available for a later retry. |

### Critic reopen conditions (Phase 1C)

Reopen if upload time is proposed as a market/reporting as-of fallback, if a new source kind is introduced without an explicit clock, if a derived artifact lacks a stable source fingerprint or lineage comparison, if freshness reads cross an existing authorization boundary, or if the policy/version vocabulary changes without a migration and compatibility test.

## All-Surface Impeccable Lifecycle Deployment — Critic Reopen (2026-07-13)

Decision under review: apply the approved critique, system-convergence, surface-refinement, production-readiness, and release passes to every analyst route and global overlay while retaining Query, Sector Review, and RV Screener as visual goldens.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-116 | Saboteur | A global style sweep can make every route look alike while erasing the materially different work modes of worklists, analytical dossiers, spreadsheets, and paper output. | High | Resolved in plan | Shared changes are limited to chrome, state grammar, identity, focus, and action hierarchy. `EnterprisePage` surface kinds retain overflow ownership; Model keeps its spreadsheet and Report Studio keeps its paper output. |
| RT-2026-07-13-117 | New Hire | Introducing a shared `SurfaceState` can become another generic abstraction that hides route-specific recovery requirements. | High | Resolved in plan | The component owns presentation only. Callers supply exact state kind, message, authority, and recovery actions; no component infers success, live origin, or actionability from missing data. |
| RT-2026-07-13-118 | Saboteur | Compacting Deep-Dive chrome can accidentally hide the full analysis body or remove expert controls under the guise of simplification. | High | Resolved in plan | Summary continues to preserve KPIs, tables, charts, and analysis. Only unavailable controls and low-frequency chrome compact; specialist controls remain directly reachable and keyboard paths are regression-tested. |
| RT-2026-07-13-119 | Performance Auditor | Chasing raw DOM counts could virtualize Report Studio's print tree or Model's editable grid in ways that break printing, formulas, paste, focus, or assistive technology. | High | Resolved in plan | Optimizations require measured interaction or commit cost. Print completeness, spreadsheet semantics, keyboard focus, paste, and screen-reader behavior are hard gates; no optimization lands on node-count reduction alone. |
| RT-2026-07-13-120 | Accessibility Auditor | Converging overlays can create nested focus traps or floating controls that intercept finalization actions, repeating the previously found ASK/Sector collision. | High | Resolved in plan | Global overlays retain one active modal owner, restore focus, close on Escape, use the semantic z-index scale, and are tested against sticky finalization bars at desktop, phone, and 200% zoom. |

### Critic reopen conditions (2026-07-13)

Stop and revise if a shared visual change alters a route's work model, if missing data is rendered as observed-empty, if Deep-Dive Summary loses analysis content, if print/model behavior regresses for a DOM-count win, or if any overlay traps focus or occludes a page-level action.

## Persona, Intelligence, Portfolio Lab, and IC Book — Critic Gate (2026-07-13)

Decision under review: complete the approved persona-composition and one-table architecture, add Portfolio Lab and IC Book as the only new top-level concepts, and introduce a shared cited-insight layer without weakening deterministic credit controls.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-121 | Saboteur | Re-implementing the workbench plan wholesale would duplicate the already-landed Workbench and Evidence Atlas contracts and could regress the 673 frontend and 1,457 server test baselines. | High | Resolved in implementation strategy | Reconcile current code against the approved contracts first. Extend existing primitives and migrate only missing surfaces; do not create parallel shells, role providers, evidence panes, or analysis-context models. |
| RT-2026-07-13-122 | Security Auditor | Presentation lenses could leak into portfolio, committee, or insight authorization and make PM/QA labels appear to confer mutation authority. | High | Resolved in contract | `RoleViewProvider` remains presentation-only. All portfolio, agenda, vote, ratification, and rejection mutations resolve the authenticated server principal and server role; foreign resources return not found. |
| RT-2026-07-13-123 | Saboteur | A literal one-table rule could hide exact data behind charts or force Model and Report Studio into inappropriate generic list layouts. | High | Resolved in contract | Enforce one visible table scroll owner only on list/worklist compositions. Model retains spreadsheet semantics, Report Studio retains document semantics, and every chart exposes an accessible tabular fallback without mounting a second visible table. |
| RT-2026-07-13-124 | Performance Auditor | Portfolio analytics could ship every position and chart series in one payload, creating slow filters, high memory use, and misleading stale aggregates on large books. | High | Resolved in API design | Positions are separately paginated/sorted/filtered; analytics return bounded aggregate series with `as_of`, authority, and missing dependencies. The UI virtualizes long position lists and fingerprints filters independently from aggregate refreshes. |
| RT-2026-07-13-125 | Security Auditor | AI-generated committee or portfolio prose could forge citations, repeat prompt-injected source text, or directly change decision-bearing state. | High | Resolved in insight boundary | Insights use an owned, closed source set, server-derived authority, claim-level evidence ids, numeric validation, untrusted-content wrapping, bounded output, and deterministic fallback. AI has no write tools; proposed changes require preview, explicit confirmation, and a deterministic domain endpoint. |
| RT-2026-07-13-126 | Saboteur | A failed automatic refresh could replace a ratified brief with an empty or partial result immediately before an IC meeting. | High | Resolved in persistence model | Insight versions are immutable and fingerprinted. Background refresh creates a new queued/running artifact; readers retain the last ratified or ready artifact until the replacement is ready. Error/partial artifacts never overwrite prior ratified content. |
| RT-2026-07-13-127 | New Hire | Adding Portfolio Lab, IC Book, QA Control, Covenant Lab, Calendar, and Market views together would recreate navigation overload. | Medium | Resolved in information architecture | Only `/portfolios` and `/decisions` become top-level concepts. QA, covenant, catalyst, and market capabilities remain modes or inspectors within existing routes until production data and workflow volume justify promotion. |
| RT-2026-07-13-128 | Accessibility Auditor | Responsive inspectors and visualization fallbacks could create duplicate focus targets, nested scroll owners, or charts whose meaning is carried only by color. | High | Resolved in component acceptance gates | One inspector is active per route, drawers restore focus and close on Escape, one table owns scrolling, reduced motion is honored, status uses text/glyphs, and every visualization provides an accessible summary plus an on-demand equivalent data view. |

### Critic reopen conditions (2026-07-13)

Stop and revise if a persona changes data access, a list route renders two visible table scroll owners, a failed insight replaces a ratified artifact, AI writes domain state, portfolio analytics lose their as-of/authority envelope, a third new top-level concept is added, or responsive drawers duplicate evidence/focus ownership.

## Portfolio Lab Backend Contracts — Critic Pass (2026-07-13)

Decision under review: add exact-team portfolio tenancy, paginated positions,
deterministic analytics/stress snapshots, and server-role mutation gates without
changing the tenancy-disabled shared-desk contract.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-129 | Security Auditor | Adding a team column only to the primary portfolio routes would leave indirect references, run auto-binding, RV screening, and CP-3C able to cross tenant boundaries. | High | Resolved in implementation strategy | One exact-team by-id helper and one query scoper gate every direct and indirect portfolio seam. Foreign identifiers resolve as 404; tenancy-off behavior remains a no-op. |
| RT-2026-07-13-130 | Saboteur | Persisting only stress outputs would make a result impossible to reproduce after holdings change, while recalculating reads would mutate committee evidence. | High | Resolved in persistence contract | Each stress run stores immutable canonical inputs, outputs, authority, and a fingerprint over the exact sorted holdings snapshot plus inputs. Reads never recompute or update it. |
| RT-2026-07-13-131 | New Hire | A cursor encoded from a mutable sort field can skip or duplicate positions when values tie. | High | Resolved in API contract | The cursor is an opaque bounded offset into a deterministic allow-listed ordering with an id tie-breaker; tests pin no duplicates across pages. |
| RT-2026-07-13-132 | Security Auditor | UI role-view controls could be mistaken for authorization and allow a server-side read-only principal to mutate holdings, stresses, votes, or decisions. | High | Resolved in authorization contract | A reusable identity-role helper rejects server principals in read-only roles before every portfolio and decision mutation. Presentation role view is never consulted. |
| RT-2026-07-13-133 | Saboteur | NaN, infinity, or a zero NAV can leak invalid JSON or silently corrupt concentration and stress percentages. | High | Resolved in computation contract | Every holdings multiply/divide uses `is_finite_number`; invalid inputs become explicit missing dependencies, finite par can backstop an invalid price, and zero denominators produce `None`. |

### Critic reopen conditions (2026-07-13)

Stop and revise if any portfolio id is dereferenced without the shared gate, if
tenancy-disabled cross-analyst reads/writes regress, if a stored stress snapshot is
recomputed on read, if a read-only server principal can mutate portfolio/decision
state, or if any response can contain NaN or infinity.

## IC Book Agenda and Finalization — Critic Pass (2026-07-13)

Decision under review: add mutable committee preparation around the existing
immutable decision and vote record, then finalize the preparation into a frozen
committee artifact in one transaction.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-134 | Security Auditor | An agenda id accepted without issuer, portfolio, and owner checks could expose a different team's thesis or permit cross-tenant finalization. | High | Resolved in contract | Agenda reads and writes derive scope from the authenticated principal and linked resources. Foreign identifiers return 404; presentation lens is never consulted. |
| RT-2026-07-13-135 | Saboteur | A two-step finalize path could create a decision while leaving the agenda editable, or mark the agenda decided without creating the immutable snapshot. | High | Resolved in transaction boundary | Readiness validation, snapshot freezing, decision creation, and agenda linkage execute inside one database transaction. Any failed validation or write leaves both artifacts unchanged. |
| RT-2026-07-13-136 | New Hire | Copying agenda fields into a decision without the exact run, report, evidence, and portfolio references would make committee history look complete while severing lineage. | High | Resolved in snapshot contract | Finalization records the canonical agenda fields and freezes each supplied artifact reference plus its authority/fingerprint. Missing required dependencies fail explicitly before creation. |
| RT-2026-07-13-137 | Saboteur | Adding filters or pagination by rewriting the existing issuer-only list could break Monitor and Decision Room clients. | High | Resolved in compatibility contract | Existing `issuer_id` calls and list response remain valid. New filters, stable sorting, pagination metadata, and by-id lookup are additive and receive compatibility tests. |
| RT-2026-07-13-138 | Accessibility Auditor | Agenda and decision history displayed together can violate the one-table rule and duplicate inspector focus on narrow screens. | High | Resolved in composition contract | Agenda and history are mutually exclusive datasets in one dominant table region. A single decision inspector becomes a drawer at narrow breakpoints, restores focus, and exposes votes, dissent, evidence, expiry, and reopen history as structured lists. |

### Critic reopen conditions (2026-07-13)

Stop and revise if finalization can partially commit, if a finalized agenda can be
edited, if a foreign agenda or linked artifact is distinguishable from missing, if
existing decision clients change shape, or if agenda and history tables are visible
at the same time.

## Phase 1B Transactional Lineage and Reconciliation — Critic Pass (2026-07-13)

Decision under review: bind producer refs and derivation edges inside existing
transactions, then add a bounded operator reconciler over authoritative history.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-161 | Saboteur | A producer that serializes a stale context JSON object can erase refs written by a sibling producer that completed first. | High | Resolved in implementation | All v2 producers lock and reload the owned context, merge refs by `(kind,id,version)`, retain unrelated keys and legacy scalars, and flush within the caller transaction. Typed ordering is canonical. |
| RT-2026-07-13-162 | Security Auditor | Accepting a context id on ingestion or run creation can become an ownership or cross-team existence oracle. | High | Resolved in implementation | V2-enabled requests validate owner and issuer membership through non-enumerable 404 responses before domain persistence. Flag-off and omitted-context requests retain the v1 path. |
| RT-2026-07-13-163 | Saboteur | Backfilling run inputs from the context's present contents would fabricate provenance for documents attached after the run began. | High | Resolved in implementation | Run input edges are captured only at run creation. The reconciler upgrades the run ref but records unresolved history rather than synthesizing run-input edges. |
| RT-2026-07-13-164 | Security Auditor | A reconciliation script could silently rewrite legacy history, cross tenant boundaries, or partially mutate an unbounded dataset. | High | Resolved in implementation | The service pages over every context, resolves persisted owners separately, uses bounded tenancy-off fallbacks, fails closed on tenancy-on owner gaps, adds only proven v2 refs/edges, never deletes, and commits once per context only in apply mode. Dry-run and verify roll back. |
| RT-2026-07-13-165 | Saboteur | A uniqueness loser could leave insight edges even though its insight row rolled back. | High | Resolved in implementation | Insight edges are written only after the nested flush succeeds. A uniqueness loser resolves the winner without writing; any later edge failure rolls the outer request transaction back with the new insight. |

### Critic reopen conditions (2026-07-13)

Stop and revise if a helper commits, if producer lineage can survive without its
domain row, if reconciliation invents run inputs, if verify mutates state, or if a
foreign context/artifact produces a distinguishable response.

## Report Studio Live Rendering and Binary Export — Critic Pass (2026-07-13)

Decision under review: bind Report Studio to live module output and immutable report
versions, then export committee-ready versions as real PDF and XLSX files.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-139 | Saboteur | Reusing the Atlas Forge report template for another issuer can present fixture narrative and covenant claims as live analysis. | High | Resolved in contract | Non-reference issuers render only their own adapted module outputs and authority. The reference template remains visibly marked and is never publishable as a live version. |
| RT-2026-07-13-140 | Security Auditor | A binary export endpoint could become an IDOR or let mutable client payloads bypass the immutable publication gate. | High | Resolved in contract | Export reloads an analyst-owned, published, live-origin `ReportVersion` and renders only its frozen canonical document. Unsupported formats and unpublishable versions fail closed. |
| RT-2026-07-13-141 | New Hire | An XLSX that is merely JSON renamed with an `.xlsx` suffix would pass a superficial download check but fail in Excel and destroy number semantics. | High | Resolved in verification gate | The server emits OpenXML with typed cells, styled headers, frozen panes and source metadata; tests reopen it with an independent parser and assert workbook structure and representative values. |
| RT-2026-07-13-142 | Accessibility Auditor | Replacing browser print with a hidden download-only action can remove the inspected document preview and keyboard-accessible print path. | Medium | Resolved in interaction design | The paper preview and print path remain. Published-version PDF/XLSX downloads are additive, labelled controls with explicit version state and do not introduce a surrounding data table. |

### Critic reopen conditions (2026-07-13)

Stop and revise if a non-reference issuer sees fixture narrative, if export reads a
mutable draft or foreign version, if a downloaded workbook cannot be reopened as
OpenXML, if export drops the authority/version identifiers, or if print preview is
removed.

## Persona, Intelligence, Portfolio Lab, and IC Book — Implementation Closure (2026-07-13)

The implementation did not reopen any high-impact objection in RT-121 through
RT-142. The shared shell remains adapter-based; presentation lenses are absent
from authorization; Portfolio Lab and IC Book are the only added top-level
concepts; insight writes remain advisory and deterministic-domain mediated; and
portfolio/committee resources are principal-scoped.

Closure evidence:

- Frontend: 734 Vitest assertions, lint, production build, 27 current-stack
  Playwright cases, three production-shell login cases, four dedicated workbench
  verifiers, and the 85-case route/responsive/200%-zoom layout gate pass.
- Accessibility: the local axe runner reports zero violation nodes across all 17
  migrated product routes, including the issuer profile fixture.
- Server: 1,489 sandbox-safe tests plus all eight AV socket tests pass; seven
  environment-dependent cases remain explicitly skipped. Migrations upgrade to
  0051, downgrade to 0048, and re-upgrade to 0051 cleanly.
- Export and integrity: XLSX is independently reopened as OpenXML; PDF snapshot,
  immutable agenda finalization, stress fingerprinting, finite-number guards,
  tenant isolation, insight grounding, ratification, and lease behavior are
  covered by the passing contract suites.

Residual tooling note: the GitNexus index reports current at commit `37a1f01`,
but symbol impact and final `detect-changes` cannot open its pending LadybugDB WAL
because `lbug.shadow` is absent. No WAL data was deleted; exhaustive source/diff
review and the full verification matrix are the fallback required by AGENTS.md.

## CAOS Applicable Updates — Phase 0 critic pass (2026-07-13)

Decision: adopt the bounded execution contract in
`docs/superpowers/plans/2026-07-13-caos-applicable-updates.md`; Phase 0 freezes
source contracts and default-off gates without changing runtime behavior.

| ID | Date | Decision / Plan | Objection | Impact | Status | Evidence / resolved commitment |
| --- | --- | --- | --- | --- | --- | --- |
| RT-2026-07-13-143 | 2026-07-13 | Applicable Updates rollout | A coupled rollout makes one defect block or contaminate unrelated capabilities. | High | Resolved | The contract defines bounded, independently deployable phases with per-phase acceptance and rollback gates. |
| RT-2026-07-13-144 | 2026-07-13 | Lineage v2 | Lineage written after the business transaction can diverge; broad reads can leak cross-scope evidence. | High | Resolved in contract | Lineage is transactional with its source write and every read/write preserves existing authorization and tenancy scope. |
| RT-2026-07-13-145 | 2026-07-13 | Market/model XLSX import | A hostile workbook can evaluate formulas, follow links, spoof cached values, or mutate state during preview. | High | Resolved in contract | `.xlsx` only, quarantine and bounded parsing, no formula evaluation, cached-value/as-of validation, preview has no writes, and ambiguity fails closed. |
| RT-2026-07-13-146 | 2026-07-13 | Model engine v2 | Parallel production calculators can silently produce inconsistent committee numbers. | High | Resolved in contract | Exactly one production calculator is canonical; rollout changes routing under a default-off flag and parity goldens. |
| RT-2026-07-13-147 | 2026-07-13 | Analyst model overrides | Untyped edits without actor/reason provenance can bypass model discipline and leave dependent outputs stale. | High | Resolved in contract | Overrides are typed, authorized, immutable-audited, and atomically trigger dependency-aware downstream recomputation. |
| RT-2026-07-13-148 | 2026-07-13 | CP-2G/CP-4D integration | Runtime adapters can drift from supplied prompts/schemas and become impossible to disable safely. | High | Resolved | Supplied bytes are vendored with SHA-256 manifests; compatibility goldens and independent default-off flags gate each module. |
| RT-2026-07-13-149 | 2026-07-13 | Persistence evolution | Destructive migrations or one-shot backfills make rollback unsafe and can strand partial data. | High | Resolved in contract | Migrations are additive; backfills are resumable/idempotent; rollback disables routing and uses forward correction without deleting analyst evidence. |
| RT-2026-07-13-150 | 2026-07-13 | Notifications | In-memory or globally addressed alerts disappear on restart or disclose another analyst's activity. | High | Resolved in contract | Notifications are durable, authorization checked, and analyst scoped; delivery can be disabled without deleting the ledger. |
| RT-2026-07-13-151 | 2026-07-13 | All new UI | Accessibility deferred to the end can make dense evidence/import interactions unusable by keyboard or color-dependent. | High | Resolved in contract | WCAG 2.1 AA, keyboard operation, visible focus, semantic status labels, reduced motion, and axe evidence are gates in every UI-bearing phase. |

### Critic reopen conditions (Applicable Updates)

Reopen before proceeding if any phase cannot deploy/roll back independently; a
lineage event can diverge from its authorized source transaction; XLSX processing
evaluates formulas or accepts ambiguous/stale caches; more than one calculator is
production-authoritative; an override lacks type/audit/recomputation; a prompt or
schema changes without compatibility proof and a flag; a migration is destructive
or a backfill non-resumable; notifications are ephemeral or cross analyst scope;
or any interaction fails the accessibility gates.

## Pre-Deployment Program Coverage Review — Critic Pass (2026-07-13)

Decision under review: retain the eight-phase pre-deployment program, but close
coverage holes before treating its final gate as an enterprise-transfer claim.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-13-152 | Release engineer | H1 can build from a mutable checkout and auto-migrate on boot without first naming the exact release commit, image digest, schema head, or pre-migration restore point. A rollback may therefore rebuild different bytes or discover too late that the old image cannot read the new schema. | High | Resolved in plan | Add an immutable release-candidate manifest, clean-tree/main-tip gate, final-image scan, production-schema preflight, immediate off-host backup, migration rehearsal, rollback threshold, and evidence bundle before H1. |
| RT-2026-07-13-153 | Incident commander | G2 asks CAOS's own Monitor/AlertSink to report CAOS failure. A dead app, host, ingress, DB, or full disk cannot reliably alert through itself. | High | Resolved in plan | Require an independent external availability path plus host/container/disk/certificate/backup monitoring, a tested notification route, severity model, owner, and SLO/error-budget decision. Product Monitor remains a separate credit-workflow control. |
| RT-2026-07-13-154 | Disaster-recovery operator | G6 is marked done when an optional `BACKUP_SYNC_CMD` hook merely exists; an unset or failing hook still means total loss on host failure. Restore evidence also does not prove backup age, encryption, or alerting. | High | Resolved in plan | Split mechanism-present from deployment-configured: final gate requires encrypted off-host destination, observed successful sync, freshness check, failure alert, and restore from the off-host copy at realistic pilot volume. |
| RT-2026-07-13-155 | Product owner | Four spec-only modules are listed as blockers in the reconciliation, but no blocking phase item owns the decision to implement them or map their promises to equivalent live services. CP-SR is also placed in the non-blocking expansion backlog while Sector Review is treated as a production surface. | High | Resolved in plan | Add a blocking promise-resolution item mapping CP-SR/CP-MON/CP-RENDER/CP-EXTRACT to implemented modules or explicit equivalent services, with user-visible scope and tests; Sector Review cannot pass on reference synthesis alone. |
| RT-2026-07-13-156 | Data-governance reviewer | The plan covers GDPR erasure but not record-class retention, backup deletion propagation, legal hold, data classification, vendor data handling/residency, or the fate of uploaded documents and immutable committee records. | High | Resolved in plan | Add a data-governance gate and handover artifacts covering retention/deletion by record class, backup expiry, legal hold, vendor/DPA decisions, and accepted exceptions. |
| RT-2026-07-13-157 | QA lead | One concept-link happy path plus per-surface tests does not constitute persona UAT across analyst, PM/CIO, and Research/QA workflows, degraded states, exports, narrow layouts, and supported browsers. | High | Resolved in plan | Add a signed persona-critical UAT matrix on the immutable release candidate, with seeded/reference content prohibited from masquerading as live evidence. |
| RT-2026-07-13-158 | Host administrator | Application/container hardening is detailed, but the release gate does not own host firewall/SSH, Docker daemon access, OS patch level, time sync, volume permissions, disk encryption/capacity, log rotation, or certificate expiry. | High | Resolved in plan | Add a host-readiness checklist and evidence artifact; only 80/443 are public, administrative access is controlled, and capacity/rotation/expiry thresholds are monitored. |
| RT-2026-07-13-159 | Saboteur | F1 says to reset the production registry while retaining golden/corpus issuers. That can put test fixtures in the live analyst workspace and conflicts with demo-seed-off launch behavior. | High | Resolved in plan | Scope F to an isolated beta environment and keep goldens/corpus offline; production starts empty unless a separately approved migration imports real pilot data. |
| RT-2026-07-13-160 | Program auditor | The final `grep -c "^- [ ]"` test can never prove readiness because the same document intentionally keeps non-blocking C7-C9 and expansion X-items open, while H4's activation bullets are not checkbox rows. | High | Resolved in plan | Replace the raw checkbox count with a blocker-only closure ledger covering blocking A-H and the new coverage-gap register; preserve non-blocking backlog items without confusing the release verdict. |

### Critic reopen conditions (Pre-Deployment Program)

Reopen if a release can be built from an unclean or unpinned checkout; a schema
change reaches the pilot without a rehearsed data-safe recovery path; off-host
backup or external alerting remains optional at sign-off; any spec-only module's
user promise has no blocking owner; beta fixtures can enter production; the
handover omits retention/vendor/host operations; persona UAT is unsigned; or
readiness is inferred from an undifferentiated checkbox count.

## Phase 2 Secure Market Workbook — Critic Pass (2026-07-14)

Decision under review: add a stateless preview/revalidated commit boundary for
analyst-supplied Bloomberg-style `.xlsx` files and create immutable, owned market
snapshots without weakening the Phase 1 lineage or tenancy contracts.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-14-172 | Security auditor | A preview that vaults the upload or creates a database token is already a state mutation; a commit that trusts preview rows or client-returned warnings can bypass later validation. | High | Resolved in contract | Preview is read-only. Commit receives the workbook again, verifies the preview SHA-256, rescans and reparses it under the same bounded policy, and derives rows and issues server-side before any write. |
| RT-2026-07-14-173 | Saboteur | The existing globally unique market payload hash can cause a second analyst uploading identical bytes to receive the first analyst's snapshot, leaking its existence and authority. | High | Resolved in contract | Imported snapshots are analyst-owned and every import/read/screen lookup is owner-scoped with foreign IDs returning 404. The stored idempotency fingerprint is authority-scoped while the unsalted workbook SHA-256 remains audit metadata; retries converge only inside the owning analyst scope. |
| RT-2026-07-14-174 | Data-governance reviewer | A broad market workbook cannot safely be assigned to an arbitrary issuer-owned `Document`: a user authorized for that issuer could then retrieve prices for issuers or teams elsewhere in the file. | High | Resolved in contract | The raw workbook is represented once by an analyst-owned market source record and manifest with no invented issuer anchor. Exact FIGI or explicit authorized mappings may link individual normalized rows to issuers; the binary remains analyst-scoped. |
| RT-2026-07-14-175 | Database reviewer | Writing the vault file before the database transaction can leave an orphan when commit fails, while writing it after commit can leave a snapshot whose evidence bytes never landed. | High | Resolved in implementation contract | Commit performs a deterministic atomic vault write, creates source, manifest, snapshot, instruments, issue ledger, and lineage in one explicit database transaction, and removes only a newly-created vault object if that transaction fails. Idempotent retries reuse an already-valid owned object. |
| RT-2026-07-14-176 | Hostile-input tester | A ZIP with traversal names, duplicate members, extreme compression, macros, external relationships, too many sheets/cells, or oversized strings can bypass a simple `PK`/`xl/` sniff and exhaust or influence the parser. | High | Resolved in contract | A pre-open OOXML gate rejects encrypted, duplicate, traversing, macro/external-link and over-budget packages; workbook sheet/row/column/cell/string/formula budgets are enforced before normalization. ClamAV remains scan-before-parse and fails closed whenever configured. |
| RT-2026-07-14-177 | Credit analyst | Automatic borrower-name matching, implicit Bid/Ask selection, or upload-time dating can silently bind the wrong issuer or market observation. | High | Resolved in contract | Issuer linkage is exact FIGI or explicit authorized issuer ID only. Sheet, noncanonical headers, Bid/Ask-to-price choice, currency and as-of constants require explicit mapping; upload time never supplies market as-of and inconsistent/future row dates block commit. |
| RT-2026-07-14-178 | Spreadsheet specialist | Loading a formula workbook with `data_only=True` alone hides formulas; loading it with formulas alone cannot prove cached values. External references can also appear in relationships or formula text. | High | Resolved in contract | The parser opens independent formula and cached-value views, inspects package relationships and formula text, never calculates, and records every formula-bearing mapped cell. Any required formula without an acceptable finite cached value blocks commit. |

### Critic reopen conditions (Phase 2)

Reopen if preview writes state; commit accepts client-normalized rows; a duplicate
can cross analyst scope; the raw workbook is assigned an invented issuer; any
formula is evaluated; external relationships, macros, or workbook budgets are
relaxed; upload time becomes market as-of; issuer matching uses borrower text; or
the raw source, manifest, snapshot, instruments, issue ledger, and lineage can
diverge across a failed commit.

## Phase 3 Canonical Model Engine v2 — Critic Pass (2026-07-14)

Decision under review: introduce a default-off, pure server-side ModelEngineV2
and additive ModelDraftV2 contract, then make that server result the only live
issuer calculation authority while retaining the TypeScript Atlas Forge model
solely as a clearly labelled reference fixture.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-14-179 | Credit model reviewer | Running the current TypeScript calculator beside the new server engine for live issuers creates two plausible but divergent committee answers. | High | Resolved and verified | Atlas Forge is the only issuer permitted to load the TypeScript reference calculator, independent of flag state. Flag-on live issuers consume only server V2; flag-off live issuers fail closed instead of inheriting fixture values. No live shadow comparison is introduced. |
| RT-2026-07-14-180 | Database reviewer | Timestamp check-then-update permits concurrent saves that both pass and silently lose one analyst edit. | High | Resolved in contract | ModelDraftV2 has an integer revision. Every mutation uses one `UPDATE ... WHERE id/owner/revision = expected` statement and requires exactly one affected row; conflicts return 409 with the authorized current revision. First creation relies on the unique owner/issuer key and never falls back to last-write-wins. |
| RT-2026-07-14-181 | Model-risk reviewer | “Edit any cell” can replace a derived value without showing the displaced formula, propagate stale dependents, or erase unrelated overrides during scenario reset. | High | Resolved and verified | Overrides are typed graph-node replacements. Calculation always starts from canonical inputs, applies active replacements, recomputes dependents, retains original formula/value and an immutable audit record, and emits invariant warnings. Derived overrides require reason, actor, before/after, scope, source, and a timezone-aware future expiry. Scenario reset changes scenario inputs only. |
| RT-2026-07-14-182 | Credit analyst | Missing live debt terms could silently inherit Atlas Forge balances, margins, or rates and make a fabricated forecast look complete. | High | Resolved in contract | Live calculations accept only sourced/imported inputs. Missing required inputs produce an explicit `insufficient_inputs` result with null dependent outputs and named gaps; reference constants are unreachable from the server engine. |
| RT-2026-07-14-183 | Spreadsheet security reviewer | A model workbook can carry macros, links, volatile formulas, stale caches, ambiguous row labels, or formulas crafted to become executable after export. | High | Resolved in contract | Reuse the bounded OOXML/AV gate, accept `.xlsx` only, never evaluate formulas, treat formula text as informational, fail closed on active content/external links/ambiguity, neutralize exported text cells against formula injection, and revalidate the original bytes during commit. |
| RT-2026-07-14-184 | Contract reviewer | The Phase 0 model-workbook note names `Historical`, `Forecast`, `Debt`, and `Outputs`, while the approved Phase 3 public contract names `Model`, `Debt Schedule`, `Overrides`, and `Sources/Audit`. Implementing both would create incompatible v1 formats. | High | Resolved before implementation | The approved Phase 3 logical contract is authoritative. The physical workbook uses the five literal valid names plus `Sources - Audit`; its logical sheet ID and product label remain `Sources/Audit`. Stable row IDs and period keys remain canonical. |
| RT-2026-07-14-185 | Authorization reviewer | Draft, calculation, import-preview, checkpoint, or export lookups by raw ID can disclose another analyst's issuer/model existence. | High | Resolved in contract | Every lookup is analyst- and issuer-authorized, uses `require_issuer`, scopes by owner in SQL, and returns 404 for foreign objects. Preview is stateless; commit repeats authorization and validation inside the transaction. |
| RT-2026-07-14-186 | Lineage reviewer | Checkpoints and reports can bind the draft payload while exports bind a later recalculation, so identical labels conceal different numbers. | High | Resolved in contract | Every calculation carries engine version, canonical input fingerprint, calculation hash, and revision. Checkpoint, report, and workbook exports bind the same immutable calculation envelope; restores create a new draft revision and calculation rather than mutating history. |
| RT-2026-07-14-187 | Release engineer | A flag rollback after a destructive schema rewrite could strand existing models or require dual-writing two incompatible payloads. | High | Resolved in contract | Migration is additive. Existing `SavedModel` remains the flag-off compatibility path; V2 uses new nullable/additive tables and columns. Disabling the flag stops V2 routing without deleting drafts, calculations, overrides, or audit evidence. |
| RT-2026-07-14-188 | UX/accessibility reviewer | A browser-only unload prompt misses internal Next.js navigation, while aggressive interception can trap keyboard users or silently autosave. | Medium | Resolved in contract | A persisted analyst preference controls both `beforeunload` and internal-link interception. The dialog is keyboard/focus safe, clearly offers stay or discard-and-leave, and never autosaves. Clean drafts never prompt. |
| RT-2026-07-14-189 | OOXML verifier | The approved literal worksheet title `Sources/Audit` is impossible: Excel forbids `/` in worksheet names, so an exporter using it cannot save a valid `.xlsx`. | High | Resolved before implementation | Use physical title `Sources - Audit` and logical ID/label `sources_audit` / `Sources/Audit`. Preview and round-trip tests require this exact mapping and reject alternate or duplicate audit sheets. |
| RT-2026-07-14-190 | Release/model-risk reviewer | A flag-off live issuer could fall through to the synthetic fixture calculator and display plausible Atlas Forge values under a real issuer. | High | Resolved and verified | Route authority is fail-closed for every live issuer unless V2 is explicitly enabled and returned with the V2 authority marker. Resolver and rendered-route tests prove the reference calculator is reachable only for the explicit Atlas Forge ID. |
| RT-2026-07-14-191 | Scale-control reviewer | Defaulting an omitted model or close-format workbook currency/unit to USD/millions can create a 1,000x wrong read. | High | Resolved and verified | `ModelDraftPayload` and `LegacyWorkbookMapping` require explicit supported monetary identity. CP-1, API, mapping, workbook and UI paths reject missing, empty, null, conflicting or unsupported values; close-format templates begin blank and require analyst entry. |
| RT-2026-07-14-192 | Credit model reviewer | Negative effective cash interest increases free cash flow under the positive-expense formula and can overstate coverage/cash generation. | High | Resolved and verified | Explicit, derived-override and debt-schedule negative cash interest becomes unavailable with a named gap; coverage and free cash flow degrade to null. Zero remains separately identified as undefined coverage. |
| RT-2026-07-14-193 | Debt-model reviewer | An untied actual roll-forward or discontinuous actual opening can still look ready; overlapping YTD/LTM windows can also create false discontinuity alarms. | High | Resolved and verified | Material actual residuals make the result partial. Later sourced openings are compared only across contiguous month-end-aware intervals; sourced values remain visible, while genuine discontinuities add a warning and named gap. Same-end and overlapping comparison shapes remain independent. |
| RT-2026-07-14-194 | Governance reviewer | An override can expire after checkpoint/preview while a report or pending mutation still publishes the stale reviewed result. | High | Resolved and verified | Every effective expiring override blocks new report preview/publication at or after expiry. The workbench invalidates pending/scenario previews locally before refresh, including refresh failure, and disables commit/checkpoint/export until recalculation is explicitly saved. Existing published versions remain immutable. |
| RT-2026-07-14-195 | Availability reviewer | A valid maximum-size graph can render hundreds of thousands of table cells/options and freeze Model Builder. | Medium | Resolved and verified | Calculation nodes render in 100-row pages with period/text filters; the sensitivity picker renders at most 200 searchable options. A 350-node DOM regression proves off-page nodes remain reachable without mounting the full graph. |
| RT-2026-07-14-196 | Source-contract reviewer | CP-1 synthesis and binder assumptions can lose fiscal calendar, currency or scale and silently convert non-calendar/GBP disclosures into calendar/USD millions. | High | Resolved and verified | Synthesized, EDGAR and reported CP-1 emit explicit currency/unit; missing or ambiguous identity fails closed. Fiscal-profile-aware FY/Q/YTD parsing handles Qn-before-FY and end-of-month arithmetic. GBP identity survives model, workbook, checkpoint and frozen report surfaces. |
| RT-2026-07-14-197 | Audit reviewer | The workbench hides actor/time/before/after details even though the append-only audit records contain them. | Medium | Resolved and verified | Model history now exposes actor/time, before/after, displaced formula/value, reason, scope, source, expiry, action and revision. Checkpoints freeze draft ID/revision and reports freeze checkpoint identity, so the applicable append-only events remain addressable without duplicating the event store. |

### Critic reopen conditions (Phase 3)

Reopen if any live issuer number can come from the TypeScript fixture calculator;
revision writes are not a single database CAS; a derived override lacks immutable
audit data or downstream recomputation; missing inputs receive reference defaults;
workbook formulas execute or ambiguous mappings auto-bind; foreign object access
does not return 404; checkpoint/report/export fingerprints can diverge; rollback
requires deleting V2 evidence; currency/unit can be inferred or defaulted; an
expired override can feed a new preview/publication; or unsaved navigation silently
saves or traps focus.

## Phase 4 CP-4D and CP-2G — Critic Pass (2026-07-15)

Decision under review: add CP-4D and CP-2G as independently flagged analytical
modules using the supplied prompt methodology, while retaining CAOS persistence,
authorization, confidence, evidence, and report governance as authoritative.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-198 | Release engineer | Registering either module in the static plan without connecting its existing flag would change every run while the flag is off and defeat independent rollback. | High | Resolved in contract | Module specs carry an explicit feature flag. Planning receives the enabled-flag set and omits disabled modules from execution while keeping their contracts addressable in the registry. Flag-off route plans remain byte-for-byte equivalent to the pre-Phase-4 plan. |
| RT-2026-07-15-199 | Prompt-governance reviewer | The current live synthesizer loads only the Active Prompt; CP-4D and CP-2G require their complete REF, schema, system, and common-preamble context. A partial load can silently change analytical rules. | High | Resolved in contract | Add a deterministic manifest-verifying bundle loader. It loads the common preamble, Active Prompt, ordered REF files, schema reference, and system reference; hashes relative paths plus exact bytes; rejects missing, extra, or mismatched module files; and never falls back to Active Prompt-only loading for these modules. |
| RT-2026-07-15-200 | Platform architect | The supplied packs contain M365/OneDrive/DOCX export instructions and reference shared files that are absent from the supplied corpus. Executing or inventing those rules would create a second governance/export authority. | High | Resolved before implementation | Keep the supplied directories byte-locked and fingerprinted, then append a CAOS runtime overlay that prohibits filesystem, M365, OneDrive, and document-export actions and requires structured tool output only. CAOS confidence, evidence, persistence, and reporting contracts remain canonical; no numeric-confidence or missing export policy is invented. |
| RT-2026-07-15-201 | Source-gate reviewer | Thin disclosure can be mistaken for evidence of no structural or ESG risk, creating a false clean conclusion. | High | Resolved in contract | CP-4D blocks without affirmative entity-perimeter and guarantee evidence and limits when security/intercreditor evidence is incomplete. CP-2G zero-source input is Blocked; partial or unknown disclosure is Completed with Limitations. CP-2G Not Applicable requires affirmative sourced inventory, all assessed factors Immaterial to Credit, and no sustainability-linked instrument. Absence alone never proves Not Applicable. |
| RT-2026-07-15-202 | Orchestration reviewer | Making CP-4D or CP-2G a new hard dependency can block legacy CP-4C, CP-3B, or CP-6A runs and make an optional module failure a platform-wide failure. | High | Resolved in contract | CP-4D and CP-2G have hard upstream source dependencies but only soft downstream ordering. CP-4C and CP-6A degrade when either is disabled, absent, blocked, or malformed. CP-3B keeps its current execution position and may consume only a nullable, versioned CP-4D handoff on a later run. CP-2G is marked non-run-blocking. |
| RT-2026-07-15-203 | Schema reviewer | A generic object tool can accept invented labels, incomplete registers, numeric leakage guesses, or an unsupported CP-2G module ID. | High | Resolved in contract | Add concrete versioned Pydantic runtime schemas and cross-field validators. Extend module-ID validation only for literal `CP-2G`; keep CP-4D under the existing D range. Enforce exact status/materiality/priority/severity vocabularies, named structural gaps/stranded value, CP-2G Not Applicable invariants, finite numbers, and a complete explicit gaps ledger. |
| RT-2026-07-15-204 | Evidence-lineage reviewer | Model output can cite search snippets, external unfetched documents, or another analyst's evidence and appear fully sourced. | High | Resolved in contract | Source gates and binders use only retrieved, authorized CAOS chunks. Every material claim carries evidence IDs that the existing runner resolves to owned chunks; unresolved evidence remains a limitation or blocks the source gate. Search hits and filenames alone never establish execution, guarantees, collateral, materiality, or linked-debt mechanics. |
| RT-2026-07-15-205 | Prompt-injection reviewer | Legal and sustainability documents are untrusted text and can instruct the synthesizer to ignore the methodology or perform tool/file actions. | High | Resolved in contract | The CAOS overlay explicitly treats retrieved text as evidence, never instructions; the live call exposes only the pinned structured-output tool; no file/network/export tool is available; runtime output is schema-validated before persistence. |
| RT-2026-07-15-206 | Product-integrity reviewer | Adding rich ATLF or other seeded CP-4D/CP-2G findings would make invented risks look like live analytical evidence. | High | Resolved in contract | Do not add production/reference findings. Offline fallback is source-gated and emits the complete schema with empty registers, explicit limitations/gaps, and Insufficient Information states. Frontend reference routes render explicitly unavailable unless a real persisted module result exists. |
| RT-2026-07-15-207 | IC-methodology reviewer | CP-6A can over-weight an optional module, infer a score from malformed severity text, or change legacy verdicts when the new handoff is absent. | High | Resolved in contract | CP-6A reads only the versioned module handoff, validates its enums and finite values, emits bounded evidence-attributed signals, and otherwise records no score. Absent/blocked/malformed optional outputs preserve the legacy verdict and surface a limitation. |
| RT-2026-07-15-208 | Runtime-capacity reviewer | Loading every reference on every attempt can exceed prompt budgets and make retries nondeterministic. | Medium | Resolved in contract | Validate and load the bundle once per module execution, use a fixed file order, apply explicit bounded retrieval context separately, and reuse that exact in-memory bundle for corrective retry. Cross-run caching is deliberately avoided so an on-disk hash mismatch cannot be masked by stale process state. A bundle over the explicit byte cap fails closed rather than dropping references. |
| RT-2026-07-15-209 | Corpus-maintenance reviewer | Registry, CP-X routing, Pipeline, Deep-Dive, Research, onboarding, and consistency tools can drift and expose different module orders or promises. | High | Resolved in contract | Update every canonical route/reference surface and add consistency tests covering registry IDs, execution order, prompt manifests, frontend module maps, and documentation. Vendored module bytes remain unchanged; any prompt-pack hash change reopens this gate. |

### Critic reopen conditions (Phase 4)

Reopen if a disabled module changes the flag-off plan; any module runs from only
its Active Prompt; bundle verification is bypassed; M365/file export instructions
become executable; a thin or absent source pack becomes a clean/Not-Applicable
finding; optional modules hard-block CP-4C, CP-3B, CP-6A, or the overall run; a
runtime schema accepts noncanonical enums or unsupported numeric confidence;
unresolved or foreign evidence satisfies a source gate; synthetic findings appear
in production/reference UI; CP-6A changes its legacy verdict when the new handoff
is absent; or the corpus, server registry, and frontend route maps disagree.

## Phase 5 Workflow and Navigation Contracts — Critic Pass (2026-07-15)

Decision under review: consolidate global issuer lookup into the command palette,
bind Command to authorized persisted holdings, make exact queued runs observable,
and add durable analyst-scoped completion events without changing Watchtower or
model-calculation authority.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-210 | Interaction reviewer | A shared issuer link inside an activating row can both open the profile and activate the detail strip, while wrapping the whole row in a link creates invalid nested controls. | High | Resolved in contract | Ticker/name remain exact-ID `IssuerLink` anchors that stop propagation. The row remainder is a separate keyboard-operable grid row using its stable position or issuer ID; Enter/Space mirror pointer activation. |
| RT-2026-07-15-211 | Portfolio-risk reviewer | Joining holdings to an unbound or merely name-matched run can display another sleeve's posture as if it belongs to the selected book. | High | Resolved in contract | Command uses authorized persisted holdings and only the newest complete run whose exact `issuer_id` and `portfolio_id` match the selected portfolio. Missing links or bound runs are `UNKNOWN`; borrower-name fuzzy matching is prohibited. |
| RT-2026-07-15-212 | Authorization reviewer | A notification or portfolio cursor can disclose another analyst's run, import, issuer, or book, even if the target object itself is otherwise protected. | High | Resolved in contract | Portfolio reads retain `require_portfolio_access`. Notification writes copy the terminal object's owning analyst; reads and seen mutations scope in SQL to the authenticated analyst and foreign IDs return 404. Cursor payloads reveal no foreign object and are bounded. |
| RT-2026-07-15-213 | Transaction reviewer | Emitting a completion toast after committing the run can lose the event on process death; emitting before the terminal state can publish success that later rolls back. | High | Resolved in contract | The idempotent `NotificationEvent` row is added in the same database transaction as the terminal run/failure mutation. Its unique key is derived from event kind and immutable object ID; retries converge on one event. |
| RT-2026-07-15-214 | Frontend reliability reviewer | Replaying notification history on first mount floods the analyst with old completion toasts, while polling every hidden tab wastes reads and can duplicate events across refreshes. | Medium | Resolved in contract | The first visible read establishes a cursor without toasting history. Subsequent visibility-aware cursor reads deduplicate by event ID, render linked toasts once, and expose a separate seen mutation. Watchtower alerts remain a different domain feed. |
| RT-2026-07-15-215 | Pipeline reviewer | Navigating to an issuer's latest run after upload can show a different run than the one just queued, and a one-shot exact-run read strands the graph in “in progress.” | High | Resolved in contract | Upload navigation carries exact issuer, context, run ID, and `view=graph`. Exact-run loading polls queued/running status until complete or failed without falling back to latest-run or reference output. |
| RT-2026-07-15-216 | Accessibility reviewer | Making an entire shared panel header a button can nest toolbar controls, break heading semantics, or turn sortable column headers into accidental disclosure toggles. | High | Resolved in contract | Only `collapsible` section shells gain a title-region button with `aria-expanded`/`aria-controls`; right-side controls stay siblings. Non-collapsible panels and sortable/filterable table headers remain unchanged. |
| RT-2026-07-15-217 | Model-risk reviewer | Combining formula scenario editing and cross-module propagation in one stateful panel makes it unclear which values are saved and allows reset in one mode to erase the other. | High | Resolved in contract | The panel exposes two named modes—Model scenario and Cross-module propagation—with separate component state and purpose copy. Model reset cannot mutate propagation inputs/results, and propagation never writes the model draft. |
| RT-2026-07-15-218 | Release engineer | Replacing sample Command content with an incomplete live read could silently fall back to plausible fixtures on network failure or require destructive rollback. | High | Resolved in contract | Command renders distinct loading, unavailable, no-portfolio, and empty-holdings states; it never falls back to sample positions. Server additions and notification migration are additive, and disabling/removing the new reads leaves existing domain data intact. |
| RT-2026-07-15-219 | Navigation reviewer | Remapping Alt+S by simulating Cmd+K or bypassing the navigation/modal coordinator can produce two open overlays or skip unsaved-edit protection. | Medium | Resolved in contract | Alt+S dispatches one explicit palette-open event owned by `CommandPalette`; the palette retains the modal coordinator and its existing guarded page navigation. Editable targets remain excluded. |

### Critic reopen conditions (Phase 5)

Reopen if a ticker/name click also activates its row; portfolio posture accepts an
unbound run or fuzzy borrower match; foreign portfolio/notification objects are
distinguishable from 404; a terminal state and its completion event can commit
separately; initial history produces toasts; exact-run polling can switch run IDs
or fall back to reference data; a disclosure button nests another control; either
scenario mode mutates the other's state; sample holdings return as a live fallback;
or Alt+S opens a surface other than the guarded command palette.

## PR #193 Quality-Gate Compatibility — Critic Pass (2026-07-15)

Decision under review: preserve the C901 and Fallow duplication gates for new or
worsening debt while allowing this branch's pre-gate findings through checked,
bounded baselines.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-220 | Code-quality reviewer | A broad ignore or disabled C901 check would let unrelated complexity regressions merge unnoticed. | High | Resolved in contract | The gate remains enabled at threshold 10. Only exact path-and-symbol baseline entries are accepted; every new finding and every increase above the recorded complexity fails. |
| RT-2026-07-15-221 | Maintenance reviewer | A permanent baseline can accumulate obsolete exceptions after functions are simplified, renamed, or removed. | Medium | Resolved in contract | When a baseline-owned file changes, entries that no longer map to an active C901 finding fail as stale and must be removed in the same change. |
| RT-2026-07-15-222 | CI portability reviewer | Newline-delimited filenames are split by `xargs`, so the tracked `Modular OS/...` checker is interpreted as two nonexistent paths. | High | Resolved in contract | A Python subprocess receives an explicit argument list from NUL-delimited Git output; spaces and other shell-significant filename characters are never reparsed. |
| RT-2026-07-15-223 | Governance reviewer | A baseline generated from arbitrary Ruff output can hide malformed findings or silently drift from the configured threshold. | High | Resolved in contract | The checker validates the baseline schema, rejects duplicates and nonpositive limits, parses only C901 JSON, requires the configured threshold, and fails closed on malformed Ruff output or subprocess errors. |
| RT-2026-07-15-224 | Duplication reviewer | Raising token/line thresholds or excluding broad directories would hide new copy-paste regressions as well as the inherited clone set. | High | Resolved in contract | Keep Fallow's existing detection mode and thresholds. Its native baseline records only the 38 exact clone groups on this branch; `--ci` continues to fail on any unrecorded clone. |
| RT-2026-07-15-225 | Baseline-integrity reviewer | A hand-authored clone allowlist could drift from Fallow's matcher and silently accept groups the tool did not actually observe. | High | Resolved and verified | The baseline is generated and consumed by the same pinned Fallow 3.5.1 native format. A local CI-equivalent run returns zero results with the baseline and 38 groups without it. |

### Critic reopen conditions (PR #193 complexity gate)

Reopen if C901 is disabled globally; an exception is not keyed to an exact path and
symbol; complexity can rise above its recorded maximum; stale entries survive a
change to their owning file; Ruff errors are treated as success; file paths pass
through whitespace-delimited shell expansion; Fallow thresholds or scope are
relaxed; or an unrecorded clone does not fail the duplication step.

## Phase 6 Legibility and Responsive Density — Critic Pass (2026-07-15)

Decision under review: improve legibility and responsive behavior on analytical
surfaces without weakening information density, changing analytical values, or
breaking the Report appendix's single-landscape-page contract.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-226 | Design-system reviewer | Globally brightening muted text or inflating the type scale would flatten hierarchy, reduce terminal density, and make secondary metadata compete with decisions. | High | Resolved in contract | Remediation is semantic-role based: decision-bearing values, interactive labels, table headings, and chart annotations receive stronger ink/weight; secondary provenance and timestamps retain the existing AA-compliant muted token. |
| RT-2026-07-15-227 | Accessibility reviewer | A chart that exposes exact values only on hover remains unusable by keyboard, touch, zoom, print, and assistive technology. | High | Resolved in contract | Each changed analytical chart carries a title, concise accessible summary, source identifiers, legible direct/tooltip values, and a keyboard-operable equivalent data table using the shared `SemanticVisualization` contract. |
| RT-2026-07-15-228 | Credit analyst | Reflowing workflow steps into masonry or columns can scramble analytical order and separate a conclusion from its evidence/open-output action. | High | Resolved in contract | Summary is one source-ordered compact sequence. Report uses a responsive consolidated grid; Dense uses auto-fit cards and wrapping, with horizontal scrolling reserved for genuine tabular evidence. Stable step IDs and output actions remain intact. |
| RT-2026-07-15-229 | Pipeline operator | Making the DAG fit by shrinking node labels or hiding the inspector can make the exact run harder to diagnose at narrow widths. | High | Resolved in contract | Layout adapts before typography: the inspector stacks/collapses at explicit breakpoints, node labels keep their effective size, and the graph retains controlled two-axis navigation, focus, and an exact-run status context. |
| RT-2026-07-15-230 | Model-risk reviewer | Styling only positive values as key totals makes adverse or negative cases visually disappear and can imply different calculation semantics. | High | Resolved in contract | Key-account emphasis is row-role based and sign-independent. Period separators use stable period-group metadata; neither styling change alters values, formulas, overrides, or engine fingerprints. |
| RT-2026-07-15-231 | Report-production reviewer | Broad whitespace or oversized appendix text can push the full model grid onto another page, while label-derived separators can drift when display copy changes. | High | Resolved in contract | The Report DSL carries explicit column-group starts. Narrow gutters/rules and stronger paper ink preserve the full-grid single-landscape-page geometry; print tests guard pagination and all groups from Q through Downside. |
| RT-2026-07-15-232 | Interaction reviewer | Promoting every action creates toolbar noise, while leaving frequent decision actions as faint text or disclosure-only controls keeps them undiscoverable. | Medium | Resolved in contract | Only frequent decision-bearing actions receive primary/secondary action treatment and visible focus. Low-frequency utilities remain under disclosure, preserving Phase 5 interaction contracts. |
| RT-2026-07-15-233 | Regression reviewer | CSS-only visual changes can pass unit tests while clipping at 200% zoom, overflowing at target widths, ignoring reduced motion, or altering print output. | High | Resolved in contract | Acceptance includes axe, keyboard/focus, reduced-motion, 200% zoom, 390/700/900/1100/1440px responsive checks, and Report print inspection in addition to type, unit, lint, and build gates. |

### Critic reopen conditions (Phase 6)

Reopen if secondary metadata and decision text are changed through one global
token; an analytical chart lacks an equivalent table or explicit sources; visual
layout changes reorder workflow steps or hide evidence; the Pipeline DAG fits by
shrinking labels; key-total emphasis depends on sign; appendix grouping is parsed
from display labels or breaks the single-page full grid; low-frequency actions
crowd the primary toolbar; or any changed route fails zoom, focus, motion,
responsive, accessibility, or print gates.

## Phase 7 Integrated Verification and Controlled Release — Critic Pass (2026-07-15)

Decision under review: prove the cross-phase artifact chain, rehearse reversible
flag transitions, and publish a release decision without treating local or CI
evidence as authorization to change production configuration.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-234 | Model-risk reviewer | Independent green tests can still bind a report, workbook, or checkpoint to a different run or model calculation than the source and market artifacts shown upstream. | High | Resolved in contract | Add one release journey that carries exact issuer, context, manifest, document, market snapshot, run, CP-4D/CP-2G output, draft, calculation, checkpoint and report identities through the chain and asserts representative model figures in the exported workbook. |
| RT-2026-07-15-235 | Authorization reviewer | A positive journey does not prove that foreign artifact, lineage, import, model, notification, report and module-output identifiers remain non-enumerable. | High | Resolved in contract | Maintain an explicit endpoint matrix mapped to negative tests. Every protected Phase 1-5 object has an owned read/mutation plus foreign-object 404 coverage; missing coverage blocks release. |
| RT-2026-07-15-236 | Database reliability reviewer | A downgrade rehearsal against retained analyst evidence could destroy or rewrite immutable artifacts merely to prove rollback. | Critical | Resolved in contract | Exercise empty-schema downgrade/re-upgrade only in disposable databases. Evidence-bearing migrations must refuse destructive downgrade; operational rollback disables flags and retains rows/binaries. Forward corrective migrations are the only production schema recovery path. |
| RT-2026-07-15-237 | Release engineer | Enabling all flags together prevents attribution, can violate dependencies, and makes a failed cohort impossible to unwind safely. | High | Resolved in contract | The runbook orders lineage dual-write, freshness reads, market import, Model Engine v2, CP-4D and CP-2G. Each stage has a bounded cohort, observation criteria, stop condition and flag-only rollback before the next stage. |
| RT-2026-07-15-238 | Governance reviewer | A successful local rehearsal or green pull request can be misreported as a completed production observation window or authorization to deploy. | High | Resolved in contract | Phase 7 may establish release readiness and a go/no-go record only. Production flag changes, cohort selection and elapsed observation-window acceptance require an authorized operator and external evidence; compatibility paths remain in place meanwhile. |
| RT-2026-07-15-239 | Workbook security reviewer | Synthetic workbooks can miss Bloomberg cached-formula behavior, while committing proprietary workbook bytes to the repository creates a data-governance incident. | High | Resolved in contract | Keep hostile and formula fixtures synthetic/sanitized. Reference the recorded sanitized real-workbook preview hash and require an authorized environment to repeat preview before default-on; never commit proprietary workbook bytes. |
| RT-2026-07-15-240 | Test-environment reviewer | Sandbox-denied antivirus sockets, browser launch restrictions, or unavailable Postgres can be mistaken for product failures or silently waived. | High | Resolved in contract | Separate deterministic local gates from environment-dependent gates. Record the exact blocked command and require unrestricted CI/release evidence for ClamAV, Chromium and Postgres; no blocked gate is relabelled as passed. |
| RT-2026-07-15-241 | Compatibility reviewer | Removing legacy reads or migration compatibility as part of “release completion” eliminates the safe rollback path before the observation window exists. | Critical | Resolved in contract | Phase 7 does not remove compatibility paths. Cleanup is a later, separately reviewed change after a green observation window and successful rollback rehearsal with retained evidence. |

### Critic reopen conditions (Phase 7)

Reopen if the integrated gate substitutes latest or fixture identities for an
exact bound artifact; any protected object lacks foreign-object denial; a rollback
deletes evidence; flags can be enabled out of dependency order; a local/CI pass is
presented as production authorization; proprietary workbook bytes enter the repo;
an environment-blocked check is called green; a new artifact/source kind appears;
prompt-pack hashes change; direct Bloomberg transport, macros, external links or
cross-team sharing enter scope; or compatibility paths are removed before the
observation window and rollback rehearsal are complete.

## Repository Triage Remediation — Critic Pass (2026-07-15)

Decision under review: close the reproduced issuer authorization, dead-code CI,
ingestion rollback, and concurrent issuer-identity findings without weakening
transactional evidence integrity or multi-team isolation.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-242 | Authorization reviewer | Fixing only the UI or rate limiter would still let a forged/read-only server principal create shared coverage. | High | Resolved and verified | `create_issuer` calls the existing server `require_write_role` before rate limiting or mutation. A dependency-overridden `read_only` principal receives 403 and no row is created. The wider E2 route matrix remains separately tracked. |
| RT-2026-07-15-243 | Storage reliability reviewer | Deleting the uploaded object on every commit exception can create a durable `Document` row pointing at missing bytes when the database reports an ambiguous post-commit connection failure. | High | Resolved and verified | Rollback callbacks run only for route/pre-commit failure and are discarded after success. Commit-time exceptions retain the unique object deliberately. Tests prove a forced flush leaves no file and a successful upload retains its file and ledger row. |
| RT-2026-07-15-244 | Tenancy reviewer | A global case-insensitive issuer constraint would leak one team's namespace into another; a nullable-team composite constraint would still allow duplicate shared issuers. | High | Resolved and verified | The invariant uses explicit `uniqueness_scope` (`team_id` or the shared empty scope) plus a Unicode-casefolded key. Migration tests allow the same normalized name in different non-null teams and refuse duplicates inside one team/shared scope. |
| RT-2026-07-15-245 | Migration operator | Automatically deleting or merging pre-existing duplicate issuers can misbind runs, documents, metrics, and reports during upgrade. | Critical | Resolved in contract | Migration 0059 performs a read-only preflight and fails with the conflicting normalized name/scope before DDL when repair is required. It never chooses a winner or rewrites dependent evidence. Empty/clean upgrade, schema check, downgrade/re-upgrade, and duplicate refusal are tested. |
| RT-2026-07-15-246 | Data-integrity reviewer | Denormalized identity keys can drift from display name/team and make the unique constraint meaningless, especially through bulk/direct writes or inconsistent Unicode lowering. | High | Resolved with reopen condition | All current issuer writers are ORM construction paths; exhaustive search found no bulk/direct issuer insert outside migrations. ORM insert/update events trim and Python-casefold names and derive scope; migration backfill uses the same Python operation. Reopen this gate before adding any bulk/direct issuer writer. |
| RT-2026-07-15-247 | Cancellation reviewer | A client disconnect raises `asyncio.CancelledError`, which bypasses an `except Exception` transaction guard and can strand a pre-commit vault object without its document row. | High | Resolved and verified | `get_db` now rolls back and runs pre-commit cleanup on every nonlocal `BaseException`, then re-raises it unchanged. A direct async-generator cancellation test proves rollback and cleanup both occur; the existing commit-time ambiguity rule remains unchanged. |
| RT-2026-07-15-248 | Tenancy reviewer | A visibility-scoped duplicate preflight sees shared issuers as well as the caller's team, so it can reject a name that the exact database uniqueness scope permits. | High | Resolved and verified | Issuer creation now computes the target team first and queries the same `(uniqueness_scope, normalized_name)` identity enforced by the database. Regression coverage proves the same name may exist once in shared, team A, and team B scopes while a second team-B copy is still rejected. |
| RT-2026-07-15-249 | Accessibility reviewer | The base axe matrix records a route readiness failure as `scan_error` but exits 0, so incomplete coverage can be reported as a clean accessibility pass. | High | Resolved and verified | The runner now counts scan errors separately, preserves them in the JSON summary, and exits nonzero for either a scan error or any violation. A missing-route probe fails while the complete static-export matrix exits 0 with all routes scanned. |

### Critic reopen conditions (repository triage remediation)

Reopen if another legacy issuer mutation lacks `require_write_role`; rollback
cleanup runs after commit has started; a new external object is registered without
unique ownership and compensating cleanup; issuer identity is written through
bulk/direct SQL without deriving its normalized key and scope; cross-team names
share a uniqueness scope; migration 0059 auto-merges existing issuer evidence; or
the configured Vulture command again reports a source finding; or cancellation
before route completion bypasses rollback cleanup; or an API duplicate preflight
uses visibility scope instead of the exact target uniqueness scope; or the axe
matrix exits successfully after any route failed readiness or reported a violation.

## Turbopack Build and Diagnostics — Critic Pass (2026-07-15)

Decision under review: use Turbopack for the default frontend production build,
keep the persistent development cache disabled, preserve an explicit webpack
fallback, and expose the API rewrite only during `next dev`.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-260 | Build reliability reviewer | Turbopack's PostCSS worker creates an internal process that binds a loopback port; restricted sandboxes reject this with `Failed to write app endpoint /page`, so replacing webpack without a fallback can block local verification. | High | Resolved and verified | Keep `build:webpack` as a documented fallback. The unrestricted default Turbopack export passed; the sandbox `EPERM` is classified as an environment limitation rather than a source regression. |
| RT-2026-07-15-261 | Deployment reviewer | A successful compile is insufficient if Turbopack's static export omits a route or produces assets that the FastAPI staging script cannot serve. | High | Resolved and verified | The complete 19-route app inventory passed and `build_frontend.sh` staged all 214 generated files into `caos/server/static`. |
| RT-2026-07-15-262 | Developer-experience reviewer | Making the rewrite conditional could silently remove `/api/*` proxying from development and leave the app waiting on authentication or data calls. | High | Resolved and verified | The rewrite is gated on Next's documented development phase; `next dev` compiled `/command`, and the generated routes manifest contains the `/api/:path*` proxy. Production static export intentionally has no custom-route support. |
| RT-2026-07-15-263 | Stability reviewer | Re-enabling Turbopack's persistent development cache to improve warm starts would recreate the prior 41–58 GB cache growth and system-wide write-pressure failures. | Critical | Resolved and verified | `experimental.turbopackFileSystemCacheForDev: false` remains unchanged and was reported disabled by both dev and build. Production filesystem caching also stays off; optimization comes from the bundler switch, not persistent cache state. |
| RT-2026-07-15-264 | Performance reviewer | A single warm benchmark can overstate the improvement because webpack and Turbopack cache different work and tracing adds overhead. | Medium | Accepted with bounded claim | Report the observed local timings as diagnostic evidence only, not a universal speed guarantee. Correctness gates and the retained fallback decide the rollout; future CI timings remain the authoritative environment-specific measure. |

### Critic reopen conditions (Turbopack build and diagnostics)

Reopen if the webpack fallback is removed; the development filesystem cache is
enabled without a bounded-size proof; the unrestricted Turbopack build fails; the
static route inventory or staged artifact differs; `/api/*` is absent from the dev
routes manifest; or a sandbox-only port denial is reported as an application bug.

## Adversarial Review Remediation — Critic Pass (2026-07-15)

Decision under review: close the remaining tenant-isolation, server-role,
workbook-resource, reranker-integrity, and test-isolation findings without
weakening read-only analytical workflows or established import error contracts.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-265 | Tenancy reviewer | Scoping accepted links by only one issuer still leaks the existence or relationship of a foreign issuer through the other endpoint. | Critical | Resolved and verified | Creation requires both issuers to be visible. Listing and deletion require both stored endpoints to remain visible and return a non-enumerable 404 for foreign links; integration tests cover reports, links, and watchlists across teams. |
| RT-2026-07-15-266 | Authorization reviewer | Applying a write dependency to every POST would incorrectly block read-style natural-language queries, translations, and previews for viewers. | High | Resolved and verified | Persistent/enqueueing handlers use the server write identity or an ownership-first write guard. Viewer mutation probes return 403 while chat and scenario POST reads remain available. |
| RT-2026-07-15-267 | Workbook security reviewer | A shared ZIP validator can silently change Market Workbook error codes or still permit worksheet dimensions that cause unbounded iteration after decompression. | Critical | Resolved and verified | One pre-parse gate now enforces path/member/expanded-size/ratio/active-content/dimension/cell limits across generic ingest, portfolio, ratings, Market, and Model paths. Resource-bomb and nominal cross-parser tests pass. |
| RT-2026-07-15-268 | Retrieval integrity reviewer | Valid JSON strings such as `"NaN"`, `"Infinity"`, or overflow exponents bypass a JSON-only check and can poison sorting and confidence metadata. | High | Resolved and verified | Both the LLM parser and orchestration boundary require finite numeric scores; invalid or mismatched batches fall back atomically. String-encoded and injected non-finite regressions pass, and the retrieval import graph is cycle-free. |
| RT-2026-07-15-269 | Test reliability reviewer | Changing environment variables after cached settings and route modules are imported creates a second, ineffective storage/database configuration inside the same process. | High | Resolved and verified | Server tests now use conftest's pre-import process configuration, and ingest resolves cached settings per operation. The server suite passed with antivirus socket tests rerun outside the sandbox. |

### Critic reopen conditions (adversarial review remediation)

Reopen if a relationship can be listed or deleted while either issuer is foreign;
a viewer can reach any persistent domain mutation; a read-only analytical POST is
blocked merely because it uses POST; any XLSX parser opens a package before shared
resource validation or iterates attacker-declared dimensions without a cap; a
non-finite reranker score reaches sorting or metadata; or a test fixture mutates
cached process settings after application modules have imported them.

## Pre-Deployment Plan 2026-07-15 Reconciliation — Critic Pass (2026-07-15)

Decision under review: execute A8 (plan re-grounding) from branch
`codex/112@76daeecf`, close C7/C9/A8 and UW-04/08/09/UF-05/12/14, add C14
(flag-wave disposition), and re-anchor C5/C11/C3-seam onto the merged
0055/0056/0058 stores.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-270 | Evidence reviewer | Closing UW rows from subagent verdicts risks over-crediting — agents historically inflate or misread fix status. | High | Resolved and verified | Every FIXED verdict was re-verified first-hand before any flip: zero `Sample|useSharedDayRun` hits in command/page.tsx, ExcelJS import + stamped sheets in export.ts, reports.py composition + `publishCommitteeVersion`, `database.py:249` role column. STILL-TRUE rows were left open. |
| RT-2026-07-15-271 | Release auditor | Marking A8 done from a feature branch (not a bare `origin/main` checkout) could smuggle unreviewed drift into "current" claims. | High | Accepted with bounded claim | The 3 branch-only commits are individually inventoried in the reconciliation block and the A8 note names the scope; the block also mandates re-running A8 at the next major landing (C8/E3 merges or any flag enablement). |
| RT-2026-07-15-272 | Program-scope reviewer | Adding C14 could duplicate APPLICABLE_UPDATES_PHASE7_RELEASE.md's authority and create two competing rollout ledgers. | Medium | Resolved in design | C14 explicitly leaves mechanism (stages, entry evidence, abort, rollback) to the release record and owns only the program decision: signed flag disposition, sign-off wiring into H5/H3, and the H0 manifest recording the frozen flag state. |
| RT-2026-07-15-273 | Duplication reviewer | Re-anchoring C5/C11/C3-seam onto the wave's stores could still be ignored at pickup, producing parallel `market_quotes`/scenario/alert stores. | High | Resolved in contract | Each item now carries an explicit do-not-duplicate instruction naming the merged table/route to build on (`market_snapshots`+market_import.py; `model_override_events` replay; `notification_events` idempotent feed). The L-item pickup plans must reconcile naming against these stores before writing schema. |

### Critic reopen conditions (plan reconciliation)

Reopen if a UW/UF row is closed without first-hand anchor verification; a
"current" plan claim cites this reconciliation after the C8/E3 merges or any
flag-stage change without a fresh A8 pass; a C5/C11/C3-seam implementation
plan introduces a second store overlapping 0055/0056/0058; or a flag ships to
the transfer candidate in a state that differs from C14's signed disposition.

## CP-1 Money-Path Remediation — Critic Pass (2026-07-15)

Decision under review: close the eight CP-1 source, model-admission, QA-read,
and provenance findings without suppressing usable Restricted analysis or
mixing evidence from unrelated disclosures.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-274 | Model-governance reviewer | Rejecting every Restricted CP-1 would disable legitimate analyst use merely because a run carries a material caveat. | High | Resolved and verified | Legacy and v2 model admission reject `Blocked` and explicit demo-fixture CP-1 outputs while preserving Restricted reference sources. Regression coverage passes in both model lanes. |
| RT-2026-07-15-275 | XBRL reviewer | Replacing concept precedence with naive merging could splice semantically different GAAP tags into one historical series; using history length before semantic precedence can also narrow a current impairment concept. | High | Resolved and verified | Selection uses latest fiscal year, then declared semantic precedence, then coverage; D&A compares direct and component lanes by freshness. Freshness regressions and the existing golden corpus pass. |
| RT-2026-07-15-276 | Disclosure-accounting reviewer | Requiring every reported metric to come from one text chunk would drop valid table rows split from the dated narrative in the same report. | High | Resolved and verified | The extractor accepts same-period or undated supporting chunks, rejects explicitly different dates and currencies, filters covenant caps, and records omissions as limitations. Reported-disclosure regressions pass. |
| RT-2026-07-15-277 | Read-model reviewer | Simply hiding retained facts after a Blocked rerun would discard the intentional last-QA-passed snapshot and leave the profile empty. | High | Resolved and verified | Profile facts expose their source run and as-of, retained values are labelled Last QA-passed, and Blocked run/module signals are excluded. Backend and rendered profile regressions pass. |
| RT-2026-07-15-278 | Scenario reviewer | A run-level pass alone is insufficient because individual modules can still be Blocked after CP-5. | High | Resolved and verified | Propagation requires a completed non-Blocked run, excludes Blocked modules, and returns visible accepted/excluded source status. Route, engine, and rendered panel regressions pass. |
| RT-2026-07-15-279 | Readiness reviewer | Calling a ticker-only issuer EDGAR-ready overpromises a source that execution cannot use when the SEC user agent is disabled. | Medium | Resolved and verified | CP-0 now requires both ticker and configured SEC user agent before declaring EDGAR available; configured and disabled readiness regressions pass. |

### Critic reopen conditions (CP-1 money-path remediation)

Reopen if demo-fixture figures can be labelled LIVE; a Blocked CP-1 can seed a
model or scenario; XBRL selection prefers a stale tag over a fresher equivalent;
reported CP-1 combines explicitly different reporting dates or currencies;
covenant caps appear as actual leverage; profile facts lack source-run age; or
CP-0 promises EDGAR grounding while the execution predicate is false.

## 2026-07-15 — Frontend design-fault remediation (85-fault critique sweep)

Decision under review: resolve all 85 faults from the 2026-07-15 adversarial
critique via 6 systemic workstreams (S1 date util, S2 lexicon, S3 nav/breakpoint,
S4 SubHeader overflow, S5 seam labeling, S6 interaction semantics) + 6 surface
phases, ~23 commits on codex/111. Plan: ~/.claude/plans/construct-plan-to-resolve-elegant-brook.md.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-280 | Desk-user reviewer | Moving the rail cutoff 1180→1280 removes the sidebar for users currently at 1180–1279 — a visible regression band. | High | Resolved in design | That band is broken today (rail + collapsed contextual controls simultaneously). Compact nav + full-label Concepts drawer replace it coherently; contract test pins CSS↔JS to one constant so the band cannot silently reopen. |
| RT-2026-07-15-281 | Layout reviewer | Measured SubHeader collapse (ResizeObserver) risks collapse↔expand oscillation: collapsing frees width, which triggers re-expansion. | High | Resolved in design | Hysteresis: record the width that was needed at collapse; re-expand only when clientWidth exceeds it. Pure `nextCollapseState` function unit-tested against the oscillation table; jsdom guard for missing ResizeObserver. |
| RT-2026-07-15-282 | QA reviewer | Changing every as-of string to UTC format could break tests or downstream scripts grepping old formats. | Medium | Resolved in design; verification pending | Grep confirmed no test or validate-*.mjs asserts the old formats. Producers-format-only keeps DecisionHeader/SemanticVisualization dumb; per-file revert possible. |
| RT-2026-07-15-283 | Governance reviewer | Relabeling Monitor seeded stats "Replay" without touching data could still mislead if a future live path reuses the label. | Medium | Accepted risk | Labels attach at the seeded callsites only; live-path stats keep unprefixed labels. Critical stat switches to live computation whenever live rows exist. Reopen if a live counter ever renders under a Replay label. |
| RT-2026-07-15-284 | Regression reviewer | IC Book full CSS migration (~12 controls to caos-action-*) can regress form usability in one shot on a governance surface. | Medium | Resolved in design | Phased last (P6) after shared patterns proven on other surfaces; axe + manual create/edit walk in verification; bespoke table/inspector CSS deliberately retained. |
| RT-2026-07-15-285 | Repo reviewer | 23 commits on a tree carrying heavy parallel server WIP risks staging user files. | High | Resolved in design | Frontend-only scope; explicit-path staging per commit; git status/diff re-checked by the main thread before each commit; redteam.md appended but never staged. |
| RT-2026-07-15-286 | Product reviewer | Query headline synthesis (frontend-composed sentence) could overclaim vs what the lane computed — the exact fault class being fixed. | High | Resolved in design | Metric-lane sentence is deterministic from rank fields actually rendered; Δ-keyword caveat chip marks level-vs-change mismatch; question renders as eyebrow, never as answer. Reopen if a synthesized sentence names a metric not present in the result table. |

### Critic reopen conditions (design remediation)

Reopen if: nav is unreachable at any viewport width; a page primary action can
render offscreen at ≥1024px; a seeded number cohabits unlabeled with a live zero;
any as-of stamp renders raw ISO-with-microseconds; or the critique re-run scores
any P0/P1 in the resolved fault classes.

## 2026-07-15 — GitNexus grouped adversarial rewrite tournament

Decision under review: collapse the active `codex/112` GitNexus graph into a
bounded set of connected macro-groups, select a concrete high-risk symbol or
region in each group, and run scratch-only rewrite tournaments without changing
production code unless a separately verified implementation is later requested.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-287 | Graph reviewer | The flat GitNexus registry still reports stale `main` and an older `codex/112` row, so unpinned clusters could classify the wrong code. | High | Resolved in method | CLI status at `codex/112@7b16397` is the freshness authority; graph queries are pinned to `branch: codex/112`, and every tournament target is read from the checked-out source before agents see it. |
| RT-2026-07-15-288 | Coverage reviewer | Collapsing 504 communities into macro-groups can hide low-cohesion or generically named clusters and falsely imply whole-group proof from one symbol. | High | Resolved in scope | Grouping uses aggregated labels, cross-community edge counts, file membership, process membership, caller count, and function length. Reports must distinguish group-wide findings from the representative rewrite target and may not claim exhaustive line coverage. |
| RT-2026-07-15-289 | Financial-model reviewer | The generic tournament checklist assumes an in-house yield/day-count engine, but CAOS currently ingests YTM/DM rather than calculating them; inventing a spot-check would test semantics the product does not own. | High | Resolved in invariant map | Record YTM/DM as finite passthrough fields and explicitly note the absence of a native day-count/yield calculator. Verify implemented money paths instead: finite-number guards, leverage/coverage denominators, covenant headroom, PIK/debt roll-forward, free-cash-flow identity, and absolute-priority recovery waterfall. |
| RT-2026-07-15-290 | Change-safety reviewer | Large challenger rewrites can look cleaner while silently changing signatures, ordering, database effects, lineage, or UI state relied on by callers. | High | Resolved in gate | `context` plus upstream/downstream `impact` is mandatory before each candidate; signature, return type, ordering, and side effects are disqualification constraints. Only scratch copies are patched, real focused tests plus caller checks decide the winner, and Incumbent wins on any unverified ambiguity. |
| RT-2026-07-15-291 | Parallel-WIP reviewer | A repository-wide exercise can absorb or overwrite unrelated work that appears during the run. | High | Resolved in isolation | Record the baseline and preserve the user-owned `caos/frontend/src/app/reports/reports-freshness-transition.test.tsx` modification. Use explicit paths only; production files remain read-only and scratch candidates live outside the repository. |

### Critic reopen conditions (grouped tournament)

Reopen if a graph query is not branch-pinned; a target is sent to an agent before
the orchestrator reads its real source; a candidate changes a contract observed
in the impact set; verification relies on a fabricated yield/day-count case; a
group verdict is presented as exhaustive when only one symbol was tournamented;
or any parallel user file is modified, staged, or copied into a candidate patch.

## 2026-07-15 — Fallow whole-frontend remediation critic pass

Decision under review: remediate every verified actionable finding from the
Fallow 3.5.1 whole-frontend review on `codex/112@8fbbe3a4` while preserving
runtime behavior, current user work, and intentional product/architecture
constraints.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-292 | Regression reviewer | Treating 200 complexity threshold findings as permission for a whole-app rewrite would create a larger correctness risk than the debt being removed. | High | Resolved in scope | Remediate the verified dead-code/API-hygiene set, the strongest traced exact clones, and the highest-risk complexity/coverage overlaps behind focused tests. Re-run Fallow and report the residual metric honestly; do not suppress complexity or claim every threshold breach is a defect. |
| RT-2026-07-15-293 | Product reviewer | Four statically unreachable Query components may represent a dormant product path rather than accidental files. | High | Resolved by evidence | Delete only after fresh trace-file/export checks confirm no entry point, imports, or re-export chain. Preserve Git recovery and verify typecheck/tests after deletion. If a live caller appears during the pass, retain and wire the component instead. |
| RT-2026-07-15-294 | Semantics reviewer | Fallow's duplicate `Scope` export groups two intentionally different domains; auto-suppressing both hides ambiguity while consolidating them would corrupt types. | Medium | Resolved in naming | Rename the exported types to `PersistenceScope` and `AnalysisScope`, update their direct consumers, and keep both unions distinct. Do not add ignore rules. |
| RT-2026-07-15-295 | React reviewer | Extracting repeated D3 zoom or filter state code can change effect dependencies, stale closures, or setter semantics. | High | Resolved in contract | Preserve dependency arrays and updater behavior exactly, add focused helper/hook tests where behavior is not already rendered, and retain component-level tests as the acceptance gate. |
| RT-2026-07-15-296 | Coverage reviewer | Static dependency-path gaps are not equivalent to missing behavioral coverage; route wrappers and executable validation scripts can be legitimate roots. | Medium | Resolved in prioritization | Add coverage where the gap intersects critical business logic or a critical complexity finding. Do not add tautological import-only tests or suppress valid script roots. |
| RT-2026-07-15-297 | Architecture reviewer | Adding Fallow boundaries without an agreed CAOS layer policy would invent architecture and could convert a clean graph into arbitrary policy noise. | High | Accepted constraint | Leave boundary enforcement unconfigured in this remediation. Record it as a governance decision requiring an explicit layer contract, not as a code defect that can be safely auto-fixed. |

### Critic reopen conditions (Fallow remediation)

Reopen if a deleted file gains a live caller; a shared extraction changes a hook
dependency or state-update contract; an analyzer suppression is used instead of
fixing verified code; a test is added only to game static reachability; the
existing uncommitted red-team tournament entry is overwritten; or final claims
equate the remaining complexity count with known-broken behavior.

## 2026-07-15 — CAOS optimisation and Copilot skills deployment

Decision under review: optimise the full Modular OS/CAOS system and make its
methodology available through Microsoft 365 Copilot without weakening analytical
quality, source lineage, deterministic calculation, or committee governance.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-15-298 | Credit-governance reviewer | Replacing CAOS with 26 independent skills would turn hard dependencies, source gates, durable state, and CP-5 clearance into probabilistic prose handoffs. | Critical | Resolved in architecture | Retain CP-X, calculations, persistence, lineage, and CP-5 in the CAOS backend; Copilot skills are workflow clients over coarse governed tools. |
| RT-2026-07-15-299 | Platform reviewer | The 26-module portfolio exceeds the conservative 20-skill Cowork limit, and current Microsoft pages conflict by also citing 50. | High | Resolved conservatively | Design the primary portfolio as 6–8 workflow skills and require target-tenant confirmation before any larger package; one-per-module requires two admin-managed packages or a selective set. |
| RT-2026-07-15-300 | Analytical-quality reviewer | Compressing prompts to an 8,000-character declarative-agent ceiling can remove legal, numerical, or uncertainty controls while appearing faster. | Critical | Resolved by gate | Generate compact instructions from the canonical bundle with headroom; ship only after a versioned evaluation corpus proves non-inferiority on numerical/legal errors, citation fidelity, gate severity, and expert preference. |
| RT-2026-07-15-301 | Corpus reviewer | Manual Copilot packages would create a third definition of each module while 19 implemented runtime modules already consume only their active prompt rather than the full folder. | High | Resolved in roadmap | Generalise manifest-verified bundle loading and generate runtime/Copilot artifacts from one canonical source with file-list and hash stamps. |
| RT-2026-07-15-302 | Product-truth reviewer | Copilot could make seeded UI surfaces or spec-only CP-SR/CP-MON capabilities look production-live. | High | Resolved in rollout gate | Skills must return backend provenance and assessed/unassessed status; do not expose sector-monitor as live until its runtime and persistence exist. |
| RT-2026-07-15-303 | M365 governance reviewer | The Gemini proposal understates admin, billing, model, Purview, connector, and sensitive-action controls. | High | Resolved in prerequisites | Treat Cowork as tenant-governed preview capability; require admin and data-governance review before pilot and preserve approval gates for sensitive external actions. |

### Critic reopen conditions (Copilot deployment)

Reopen if Copilot becomes the source of truth for calculations or run state; a
skill infers committee clearance from prose; compact instructions are edited
independently of the canonical corpus; tenant limits are assumed rather than
verified; a spec-only or seeded capability is labelled live; or an optimisation
ships without analytical non-regression evidence.

## 2026-07-16 — Pre-production security and correctness remediation

Decision under review: close the 2026-07-15 adversarial pre-production findings
across CP-1 grounding, immutable run inputs, analyst isolation, report export,
provider egress, embeddings, upload safety, durable execution, and browser state
without weakening evidence lineage or making legacy work silently disappear.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-304 | Credit-governance reviewer | Promoting every grounding miss to Blocked would make legitimate FX-normalized analysis unusable, while leaving it advisory still permits fabricated figures to reach Committee Ready. | Critical | Resolved and verified | Preserve the analytical payload as Restricted, but require source-backed primitives and server-derived headline ratios before Committee Ready. Unknown basis or currency remains reviewable but non-exportable. |
| RT-2026-07-16-305 | Lineage reviewer | Freezing only a manifest ID still permits the runner to read unrelated issuer documents, while switching immediately to exact inputs could strand legacy runs that have no snapshot rows. | Critical | Resolved and verified | New runs transactionally snapshot exact document IDs and hashes and retrieve only that corpus. Legacy rows degrade explicitly to Restricted legacy-corpus mode rather than fabricating exact lineage. |
| RT-2026-07-16-306 | Authorization reviewer | Flipping the existing team flag does not provide analyst isolation because NULL-team issuers remain global and shared run/document behavior is intentional today. | Critical | Resolved and verified | Add an explicit private-owner boundary for analyst-created work, retain only deliberately published institutional artifacts as shared, and cover list/by-ID/mutation/export probes with analyst-A-versus-B tests. |
| RT-2026-07-16-307 | Availability reviewer | Fail-closed malware and provider controls can make all uploads or analysis unavailable when optional infrastructure is absent. | High | Resolved and verified | Production fails closed; development/test may use explicit non-production bypass states that are truthfully labelled unscanned or local-only and can never be published. |
| RT-2026-07-16-308 | Concurrency reviewer | Adding retries without fencing increases duplicate spend and allows stale attempts to overwrite successful terminal state. | Critical | Resolved and verified | Claims receive monotonic fencing tokens; all attempt-owned writes and terminal transitions compare the active fence. Stale attempts become no-ops and emit diagnostics. |
| RT-2026-07-16-309 | Migration reviewer | Introducing snapshot, ownership, idempotency, and revision columns in one pass can break existing databases or create nullable states interpreted as safe. | High | Resolved and verified | Additive migrations use explicit legacy/unknown states, backfill conservatively, and gate new authority on populated verified fields. No nullable legacy value is treated as approved. |
| RT-2026-07-16-310 | Frontend reviewer | Clearing all local draft state on navigation prevents leakage but can destroy unsaved analyst work. | High | Resolved and verified | Persist sensitive drafts server-side by analyst/context/issuer/run, keep only harmless display preferences locally, abort stale requests, and surface conflicts instead of silently overwriting either scope. |

### Critic reopen conditions (pre-production remediation)

Reopen if an ungrounded CP-1 can become Committee Ready; a run reads a document
outside its frozen input set; a foreign analyst can enumerate or mutate private
work; an unscanned upload is labelled clean; a stale worker can write terminal
state; a degraded provider path remains publishable; or Report Studio can render,
print, or autosave content under a different context, issuer, or run identity.

## 2026-07-16 — Command to Query CI handoff repair

Decision under review: keep Command as one dominant worklist while exposing one
reliable, semantic deep-link to the persisted cross-coverage Query workbench.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-311 | Workflow reviewer | Keeping the link only inside the optional inspector makes the handoff persona- and layout-dependent; the link can be absent even though Query is available. | High | Resolved in interface | Render one unconditional secondary link in the main workbench toolbar, preserving the active context when it exists and falling back to `/query` while context creation is pending. |
| RT-2026-07-16-312 | Product reviewer | Restoring the removed Command query composer would create two competing query surfaces and violate the one-dominant-worklist contract. | High | Resolved in scope | Restore navigation only. Command retains its single ranked worklist and Query remains the sole cross-coverage execution surface. |
| RT-2026-07-16-313 | Accessibility reviewer | Replacing the missing anchor with an imperative button would weaken link semantics and the existing role-based Playwright contract. | Medium | Resolved in interface | Keep a real Next.js link with visible text `Open cross-issuer Query` and the existing focus-ring treatment; remove the inspector duplicate. |

### Critic reopen conditions (Command to Query handoff)

Reopen if the link is conditional on a loaded analysis context, hidden behind a
persona-only panel, duplicated on the page, implemented as a non-link control,
or loses the active context when one is available.

## 2026-07-16 — Intentional auth failure handling

Decision under review: keep global mid-session 401 teardown while allowing the
login, registration, profile-creation, and recovery forms to render their own
expected credential errors.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-314 | Authentication reviewer | Dispatching `auth-lost` for a wrong invite code, password, or recovery phrase remounts the form and erases the server error before the analyst can read it. | High | Resolved in interceptor | Exclude only exact unauthenticated POST entry endpoints from the global 401 event; their local form handlers retain and announce the backend detail. |
| RT-2026-07-16-315 | Session-safety reviewer | Excluding all `/api/auth/*` requests would hide a genuinely revoked session during authenticated profile deletion or future auth mutations. | High | Resolved in scope | Match method plus exact path. `GET /me` remains provider-owned, the four credential-entry POSTs remain form-owned, and every other API 401 still tears down the stale workspace. |

### Critic reopen conditions (intentional auth failures)

Reopen if a credential-entry 401 clears or remounts the form, a non-entry API
401 fails to dispatch `auth-lost`, or the exclusion broadens to an auth-prefix
match that suppresses authenticated session-loss signals.

## 2026-07-16 — Agentic Infrastructure and Memory Hub design

Decision under review: consolidate existing CAOS model calls, MCP tools, semantic
telemetry, pgvector embeddings, and the human-edited vault behind the in-process
gateway specified in `caos/docs/AGENTIC_INFRA_MEMORY_HUB_SPEC.md`, without adding
awaited or blocking instrumentation to a primary request.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-316 | Latency reviewer | Capturing semantic telemetry can quietly replace the current awaited DB tail with masking, serialization, logging, or OTel work on the caller coroutine; making delivery lossless would also block when the queue is full. | Critical | Resolved in specification | H1/H2 and Z1–Z4 permit only the existing budget arithmetic, owned outer-container snapshot, event construction, and `put_nowait`; all semantic work begins after dequeue. Queue overflow increments memory only, explicitly accepting telemetry loss to preserve the request contract. |
| RT-2026-07-16-317 | Router reviewer | Current OpenRouter normalization drops tool-call ids and flattens non-text history, so a nominal MCP router could execute one call but could not perform the second provider turn; deployed EDGAR calls would also fail the edge proof. | Critical | Resolved in specification | Define canonical `ToolCall`/`ToolRunResult`, exact Anthropic/OpenRouter round-trip mappings, five executed tool rounds plus terminal status, two-round golden tests, qualified allowlists, and `EDGE_PROXY_SECRET` → `X-Edge-Authorization`. Gemini dynamic tools fail before network. |
| RT-2026-07-16-318 | Telemetry reviewer | Provider-routed OpenRouter prices are not recoverable from a model-tier label, and arbitrary SDK response objects can either defeat JSON encoding or invoke unsafe `str`/`repr` paths before masking. | High | Resolved in specification | Provider `usage.cost` is authoritative; a routed OpenRouter request without it is NULL rather than matrix-priced. A bounded, cycle-safe background normalizer handles Pydantic/dataclass/known DTO shapes, poisons unsupported events without stringification, then masks before any log, DB, or OTel operation. |
| RT-2026-07-16-319 | Tenancy reviewer | A manually created or edited memo could become a NULL-owned institutional Document, and the current unscoped `AnalystLink` query could expose one analyst's note to another. | Critical | Resolved in specification | Upload tasks carry the caller id; recovery resolves `uploaded_by` to exactly one analyst; unresolved or mixed ownership quarantines without mutation. Add owner-tagged AnalystLinks, hide legacy NULL links, pass caller id through both Query graph paths, and copy original ownership to OKF projections. |
| RT-2026-07-16-320 | Durability reviewer | A bounded watcher queue, five finite retries, rename ordering, a crash after a memo response, or an unmounted empty vault can leave the projection stale or erase it incorrectly. | High | Resolved in specification | Queue overflow triggers direct full reconcile, present paths precede missing paths, rename takes ordered old/new locks, targeted upload sync is only acceleration, and the elected leader runs startup plus 300-second reconciliation. A hidden marker distinguishes a healthy deliberate final deletion from an absent mount, so jobs remain reconstructable without a job table. |
| RT-2026-07-16-321 | Lineage reviewer | A citation can be inserted after the watcher checks references but before it deletes a chunk; JSON lineage alone does not cover direct `EvidenceItem` and `MetricFact` foreign-key writers. | Critical | Resolved in specification | One sorted per-chunk transaction-lock helper is mandatory for JSON/lineage, EvidenceItem, MetricFact, and watcher deletion. Deletion rechecks every citation family after locking and shadows any cited chunk; registry and three-family Postgres race tests enforce adoption. |
| RT-2026-07-16-322 | Vector reviewer | Gemini Embedding 2 aggregates multi-input requests, legacy NULL chunk hashes can make cutover coverage falsely pass, and a global “all live chunks atomic” claim contradicts current ordinary uploads. | Critical | Resolved in specification | Require one request per text with four-way background concurrency and all-or-zero validation; backfill every NULL hash and make it non-null before EXCEPT readiness; scope atomic generation to watched projections while explicitly retaining ordinary upload's temporary BM25-only state. |
| RT-2026-07-16-323 | Migration reviewer | A fixed revision number can collide with parallel work, and applying only a “portion” of one Alembic revision is impossible. | High | Resolved in specification | A live `alembic heads` check returned `0062`; the complete additive hub migration is `0063` over `0062`, applied once before Phase B. The implementer must re-run heads and adjust only revision metadata if the workspace advances again. |

### Critic reopen conditions (Agentic Infrastructure and Memory Hub)

Reopen if any payload normalization, masking, cost, logger, DB, or OTel operation
runs before telemetry dequeue; a provider tool id is synthesized or lost; an
OpenRouter request without provider cost is tier-priced; a NULL/unresolved memo
owner becomes query-visible; reconciliation requires a new filesystem event after
recovery; a citation writer bypasses the shared chunk lock; an Embedding 2 request
contains more than one text; readiness ignores NULL hashes; ordinary uploads are
claimed atomic; a zero-file reconcile deletes without the valid vault marker; or the
migration is created without a fresh `alembic heads` check.

## 2026-07-16 — Phase-1 live-surface closure

Decision under review: replace the remaining coarse or seeded Phase-1 UI
surfaces with bounded, access-controlled runtime data while keeping Phase-2
Sector Review and Monitor modules explicitly out of scope.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-324 | Authorization reviewer | A cross-coverage QA feed can expose another analyst's finding text even when issuer rows are visible institutionally. | Critical | Resolved in interface | The bulk findings endpoint applies both issuer tenancy scope and the existing cross-analyst run-sharing rule before joining findings. It is bounded and returns findings only from the latest accessible completed run per issuer. |
| RT-2026-07-16-325 | Performance reviewer | Fetching QA detail run-by-run turns the Command Center into an N+1 fan-out and can make governance state lag the portfolio. | High | Resolved in interface | Use one windowed database query and one frontend request for the latest accessible findings; retain the coarse issuer gate only as an explicit fallback when an accessible run has no detailed findings. |
| RT-2026-07-16-326 | Product-truth reviewer | Calling seeded step names or charts “live detail” would manufacture runtime structure that the engine did not emit. | Critical | Resolved in interface | Live Deep-Dive renders only adapted runtime sections in a provenance-labelled register. Seeded charts and workflow steps remain demo-only and are never substituted into a live run. |
| RT-2026-07-16-327 | Credit-methodology reviewer | A deterministic top-five algorithm can masquerade as a market-materiality ranking without a defensible score. | Critical | Resolved in methodology | CP-5B selects persisted claims by disclosed decision-proximity and module-diversity rules, carries source evidence and QA status, and labels the result “decision-relevant,” not a ranked materiality score. |
| RT-2026-07-16-328 | Failure-state reviewer | Falling back to a seeded lineage register when a live CP-5B output is absent makes an incomplete run appear assessed. | High | Resolved in interface | Live Pipeline fails explicitly to an unavailable state. Seed lineage is shown only in demo mode; live evidence chips come solely from persisted CP-5B evidence identifiers. |

### Critic reopen conditions (Phase-1 live-surface closure)

Reopen if a QA description crosses an unauthorized analyst boundary; Command
issues one QA request per issuer or run; a live Deep-Dive panel renders seeded
steps or charts; CP-5B describes deterministic ordering as measured market
materiality; or a live missing output silently falls back to demo lineage.

## 2026-07-16 — Canonical continuous-quality register

Decision under review: publish one workbook as the quality source of truth by
combining the curated feature catalogue with code-discovered screens, FastAPI
handlers, runtime settings, business journeys, generated scenarios, current
execution evidence, and iteration defects.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-329 | QA-evidence reviewer | Copying a suite-level green result onto every generated scenario would falsely claim that thousands of boundary, permission, performance, and responsive cases were individually executed. | Critical | Resolved in schema | Use `Pass` only for directly observed evidence. Aggregate regression coverage is labelled `Suite evidence`; every generated but unexecuted scenario remains `Designed`, and skips remain visible gaps. |
| RT-2026-07-16-330 | Discovery reviewer | One generated row per route or setting proves inventory coverage, not that every branch has been behaviorally understood. | High | Resolved in status model | Preserve detailed curated rows, add exact source/handler/config provenance, and mark generated inventory rows `Documented — direct execution pending`; discovery completeness and execution completeness are reported separately. |
| RT-2026-07-16-331 | Product-truth reviewer | A stale CSV seed or old workbook date could masquerade as current implementation truth after routes, endpoints, and UI workflows change. | Critical | Resolved in builder | Re-scan physical `page.tsx` routes, `main.py` router prefixes, route decorators, and `Settings` fields on every build; publish the workbook dated to the current validation run and retain the seed source only as traceable input. |
| RT-2026-07-16-332 | Release reviewer | A confidence score can conceal open skipped journeys or a fixed high-severity release blocker. | High | Resolved in summary | Confidence is conservative and accompanied by formulas for open critical/high/other defects, direct-pass counts, designed cases, skips, and explicit remaining-risk notes. Completion is prohibited while gaps remain. |

### Critic reopen conditions (continuous-quality register)

Reopen if generated cases are marked executed without direct evidence; a new
screen, API handler, or `Settings` field is absent from the workbook; skipped
tests disappear from the defect/risk view; the workbook reports completion with
open gaps; or a derived coverage count is manually hard-coded instead of linked
to its source sheet.

## 2026-07-16 — Isolated production-like full-inventory QA lane

Decision under review: exercise the complete user-facing inventory against an
isolated local PostgreSQL database containing a deterministic 300-issuer
fictional credit book, with production boot/auth guards enabled, no external
model keys, and no production or developer database access.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-333 | Data-governance reviewer | A “production-scale” seed can accidentally import real issuer names, source documents, credentials, or a developer database, and a cleanup step could destroy unrelated local data. | Critical | Resolved in lane design | Generate only deterministic invented issuers/documents/metrics into a uniquely named disposable PostgreSQL container and workspace vault. Clear every external provider key. Record database identity and fixture counts before testing; never point the lane at an existing database and do not remove user-owned state. |
| RT-2026-07-16-334 | Scale reviewer | Calling the existing 30-issuer fixture “production scale” is an unbounded claim, while creating full run history for every issuer would add cost and time without matching the repository’s own stress contract. | High | Resolved in acceptance contract | Pin the finite target to the stress plan’s 300 issuers, at least two documents and eight headline facts per issuer, plus a bounded representative set of offline terminal runs. Publish exact counts and latency observations; describe the result as the 300-issuer pilot/stress envelope, not universal production capacity. |
| RT-2026-07-16-335 | Deployment reviewer | Running FastAPI directly with production environment variables proves application guards but bypasses Caddy, oauth2-proxy, TLS, and the real ClamAV signature service; labelling it a production deployment pass would be false. | Critical | Resolved in evidence labels | Call this a production-like application lane. Require PostgreSQL, production boot guards, demo seed off, private local secrets, and valid edge identity headers on every request. Keep proxy/TLS/real-ClamAV verification separate; use the existing fake clamd protocol only for deterministic upload behavior and never claim a full deployment-stack pass from this lane. |
| RT-2026-07-16-336 | Inventory reviewer | Base-route DOM scans omit conditional buttons, modal contents, error states, and presentation-role variants; static source scans alone include dead or unreachable controls. | High | Resolved in inventory method | Reconcile three sources: current TSX control discovery with file/line provenance, curated feature/state contracts, and authenticated browser evidence across Analyst/PM/QA views. Mark source-only controls as documented rather than executed until a journey opens them; do not infer a clean interaction pass from route-load evidence. |
| RT-2026-07-16-337 | Authorization reviewer | The Analyst/PM/QA switch is presentation-only and must not be confused with server authorization roles; testing only the default analyst can miss read-only write bypasses. | Critical | Resolved in role model | Inventory presentation views separately from authenticated capabilities. Exercise analyst write behavior and viewer/read-only mutation denial through the server boundary; record that PM/QA alter information priority, not authorization. |
| RT-2026-07-16-338 | Test-isolation reviewer | Broad Playwright globs can miss a queryless or query-string request and silently fall through to the seeded server, corrupting deterministic evidence or consuming real provider quota. | High | Resolved in harness contract | Match fixture routes by URL pathname and method, assert fixture identity/source before accepting results, clear all external provider keys, and treat any unexpected network/provider request as a defect. Production-like runs that intentionally use the local server are separately labelled and bound to the unique QA database. |

### Critic reopen conditions (production-like QA lane)

Reopen if any real/sensitive input enters the seed; the database or vault is not
uniquely isolated; “production scale” lacks exact counts; a direct-app run is
presented as proxy/TLS/real-AV proof; a source-only control is marked executed;
presentation views are treated as authorization roles; or a browser fixture can
fall through without an explicit local-server or fixture-identity assertion.

---

## 2026-07-16 — Critique-score plan (29 → ≥35), red-team pass

Plan: `~/.claude/plans/construct-plan-to-resolve-elegant-brook.md` (W0-W6). Critic objections and dispositions:

1. **Consistency 2→4 is a two-point claim.** An adversarial director need find only one un-swept casing/control drift to hold it at 3. *Mitigation:* the W1 long tail (segmented controls ×3 grammars, ic-book buttons, row-action grammar documented as a two-tier system, alias-class collapse) plus the score-path buffer math tolerates Consistency landing at 3 (34 + any one buffer = 35). Accepted residual.
2. **ActionReason retrofit can break name-based test queries.** *Mitigation (hard rule):* the reason text never enters the button's accessible name; `settings_flow.spec.ts` asserts `title="No unsaved changes"` verbatim — kept byte-identical. `research-recovery.test.tsx:59` `.disabled` assertion is updated in the same commit as the conversion.
3. **Cold-board RankedChanges is a moving target** — the first draft GET enqueues a cycle that may populate mid-critique, hiding the OPEN TOP CHANGE gate and UNRATIFIED suppression. *Disposition:* accepted; the gate is correct in both states and H5/H8 don't rely on it alone.
4. **Parallel-WIP collision risk is the top execution hazard**, not design: `command/page.tsx` and 3 pipeline files are user-dirty right now; the branch moved twice during planning. *Mitigation:* re-fetch + `git status` before every commit; stage only fully-mine files; mixed files ride the working tree until clean (established session pattern).
5. **ReportDoc div→h2/h3 conversion** could change CSS specificity or print layout if any selector is element-qualified. *Gate:* grep `rd-h`/`rd-subhead` selectors before editing; class-based only → safe.
6. **usePortfolio empty-vs-unavailable seam** must not re-grammar the error branch: `monitor-governance.test.tsx:38-52` and `command_flow.spec.ts:347-366` assert "unavailable" wording on all-rejected backends. The seam splits *reachable-but-zero* out; fetch-fail wording is unchanged.
7. **Help overlay lists only working bindings** (verified: ⌘M exists but is route-scoped to Deep-Dive/Model; no bare-C binding). A documented-but-dead key would cost the point it buys.

## 2026-07-16 — Actual-code audit remediation

Decision under review: close every evidence-backed weakness from the 2026-07-16
actual-code/configuration audit without weakening production fail-closed controls,
breaking analyst workflows, or overwriting the parallel dirty working tree.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-16-339 | Deployment reviewer | Making malware scanning “optional” to restore boot would remove the production upload gate instead of fixing the contradictory Compose defaults. | Critical | Resolved in design | Keep the production guard and make ClamAV a mandatory healthy dependency with `CLAMAV_HOST=clamav`; development remains explicitly scanner-optional. |
| RT-2026-07-16-340 | Authorization reviewer | Merely adding a write-role dependency to the existing GET still leaves a state-changing, prefetchable endpoint and an unbounded `force` spend bypass. | Critical | Resolved in interface | Make GET read-only, move enqueue to POST with write-role plus a non-simple action header, remove public force bypass, and preserve the stale/single-flight spend bound. |
| RT-2026-07-16-341 | Concurrency reviewer | A boot-only lease sweep or an unfenced retry can either strand work forever or let a stale worker overwrite a reclaimed attempt. | Critical | Resolved in architecture | Keep the existing schema, enqueue `queued`, continuously claim queued/expired rows, heartbeat live claims, exclude local inflight ids, and verify worker ownership again before terminal commit. |
| RT-2026-07-16-342 | Performance reviewer | Moving parsers to a generic process pool does not guarantee a timed-out running task stops, while scaling workers multiplies the whole-file buffer and DB pool. | Critical | Resolved in architecture | Run each bounded parser in its own spawn process and terminate it on timeout; cap supported web workers at two, reduce upload fan-out to one per process, and raise the documented container memory envelope to 4 GiB. Preserve `read_capped`'s bytes contract because GitNexus reports a critical shared blast radius. |
| RT-2026-07-16-343 | External-compliance reviewer | A per-process EDGAR sleep still violates the SEC aggregate ceiling when web workers or replicas increase. | High | Resolved in configuration | Scale the per-process interval by the configured total process partitions, never below local `WEB_CONCURRENCY`, and fail deployment documentation closed on replica-count configuration. |
| RT-2026-07-16-344 | Supply-chain reviewer | Auditing loose requirements can remain green while the hashed production lock ships vulnerable transitive packages. | High | Resolved in gate | Upgrade the exact lock, audit that lock with `--require-hashes` in CI, and keep the existing loose-spec/lock-sync contract as a separate check. Force the patched UUID transitive version through the npm lock and re-audit it. |
| RT-2026-07-16-345 | Recovery reviewer | Requiring an arbitrary sync hook can still silently fail, and local restore scripts that are never scheduled do not prove recoverability. | High | Resolved in operations | Require a non-empty off-host sync command for the shipped production stack, persist failure sentinels surfaced by container health, and run the scratch restore drill on a bounded automatic cadence after successful backups. |
| RT-2026-07-16-346 | Test-platform reviewer | Enabling three Playwright projects without isolating shared state can turn browser coverage into nondeterministic SQLite writer contention. | High | Resolved in test architecture | Retain one Playwright worker and shared authenticated setup, run Chromium/Firefox/WebKit as explicit serial projects, and install all three engines in CI. |

### Critic reopen conditions (audit remediation)

Reopen if production can boot without a live scanner; any GET starts or mutates an
autonomy cycle; a viewer can enqueue one; an expired pipeline claim is not
revisited after startup; a stale claimant can commit; a parser process survives
its timeout; supported worker counts can exceed the documented memory/connection
envelope; aggregate EDGAR throughput can exceed the configured partition budget;
CI audits a dependency graph other than the production lock; off-host sync or a
scheduled restore failure remains health-invisible; or CI runs only Chromium.

## 2026-07-17 — Remote backup round-trip closure

Decision under review: replace the backup container's arbitrary off-host shell
hook with one supported, credential-isolated transport and prove recovery from
the downloaded remote copy rather than from the same host volume.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-347 | Recovery reviewer | `BACKUP_SYNC_CMD` is required but the shipped image has no documented rsync, rclone, scp, or cloud client, so the fail-closed configuration can still be operationally unusable. | Critical | Resolved in design | Keep artifact creation credential-free and add a separate rclone/Postgres-client sync service with `/backups` read-only, a structured `BACKUP_REMOTE`, and provider-neutral configuration mounted as a Docker secret. |
| RT-2026-07-17-348 | Disaster-recovery reviewer | Restoring the local `/backups` copy proves only pg_dump/tar integrity; it does not prove upload, remote durability, credentials, or the download path. | Critical | Resolved in design | After every configured cadence, download the remote artifact set into a fresh scratch directory and run the existing DB/vault restore assertions exclusively against that downloaded copy. Any upload, download, or restore failure keeps the service unhealthy. |
| RT-2026-07-17-349 | Security reviewer | An operator-supplied `sh -c` hook is command-injection by design and can read both database and remote credentials. | High | Resolved in interface | Remove shell-command execution. The script accepts only an rclone remote path, invokes rclone with argument boundaries, and reads credentials from a read-only Compose secret. |
| RT-2026-07-17-350 | Privilege reviewer | Overriding the official Postgres entrypoint leaves the backup loop running as root with a writable root filesystem. | High | Resolved in container design | Build minimal client-only images, run backup and sync as fixed non-root UIDs with all capabilities dropped, mount only their recovery volumes writable, and make each root filesystem read-only with bounded `/tmp`. A dedicated recovery GID grants the sync UID read/traverse access to the producer-owned `0750` volume while `/backups` remains mounted read-only. Existing backup volumes require the documented one-time ownership migration before cutover. |

### Critic reopen conditions (remote backup closure)

Reopen if a production backup can start without a remote target and readable
secret; sync executes operator shell text; the scheduled drill reads the local
backup volume instead of a newly downloaded copy; a failed remote round trip can
leave the health sentinel green; the sync UID cannot read the producer-owned
artifacts; or either long-running process remains root.

## 2026-07-17 — Scenario growth-polarity repair

Decision under review: correct the offline Scenario Builder after a realistic
growth-slowdown case was translated as revenue upside.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-351 | Credit-methodology reviewer | Simply adding `slows` to the downside list while retaining bare `growth` as upside leaves contradictory matches and lets “growth capex” manufacture revenue acceleration. | High | Resolved in classifier | Remove bare growth/expansion polarity. Require explicit recovery, improvement, rebound, or acceleration phrasing for upside and explicit slowdown, contraction, decline, or worsening churn phrasing for downside. |
| RT-2026-07-17-352 | Regression reviewer | Broad slowdown matching can flip genuine demand-recovery cases or alter unrelated rates/capex drivers. | High | Resolved in coverage | Pin the exact slowdown failure, retain the existing recovery and pricing-power regressions, assert unrelated driver deltas remain zero, and add the phrase to the bounded realistic benchmark corpus. |

### Critic reopen conditions (scenario growth polarity)

Reopen if bare `growth` or `expansion` changes revenue without directional context;
slowdown/churn deterioration maps positive; a recovery case maps negative; or the
repair moves rate/capex drivers for a growth-only phrase.

## 2026-07-17 — Scenario input-cost direction repair

Decision under review: correct the offline Scenario Builder after easing inflation
was translated as margin pressure and higher rates.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-353 | Credit-methodology reviewer | Matching the bare token `inflation` before its qualifier inverts disinflation and cost normalization into a downside, a directionally wrong credit read. | High | Resolved in classifier | Give explicit deflation, disinflation, inflation-easing, and input-cost-normalization phrases precedence; apply the generic cost-inflation shock only when no relief phrase matched. |
| RT-2026-07-17-354 | Scope reviewer | Treating every `ease` or `normalize` token as cost relief could misclassify monetary easing or unrelated operational normalization. | High | Resolved in vocabulary | Match only cost/inflation-qualified phrases, assert growth/rates/capex remain unchanged, and retain the oil/energy stress regression alongside the new failure case and benchmark entry. |

### Critic reopen conditions (scenario input-cost direction)

Reopen if inflation easing or normalized input costs map to margin pressure; an oil,
fuel, commodity, or unqualified inflation shock maps to relief; or cost-only language
moves growth, capex, or rates without an explicit rate phrase.

## 2026-07-17 — Surface redesign table and row-interaction contract

Decision under review: adopt one typed `DataTable` for ordinary application
tables while retaining purpose-built paper, chart-fallback, spreadsheet, and
virtualized-grid renderers; use one roving row tab stop with explicit activation.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-355 | Interaction reviewer | Reusing the tab-selection callback for rows made Arrow Up/Down call `onRowActivate`; on a worklist where activation opens a route or mutates selection, merely inspecting the next row would execute the action. | High | Resolved in primitive | Keep roving focus as local `activeIndex` state. Arrow/Home/End move focus only; Enter, Space, or a deliberate row click activate. Tests pin the separation. |
| RT-2026-07-17-356 | Accessibility reviewer | A button or link nested in an activatable row could bubble click/Enter to the row and execute two actions, while the selected row had no programmatic selection state. | High | Resolved in primitive | Ignore row activation from interactive descendants (native controls, links, summary, contenteditable, positive tab stops, and button/link roles) and expose controlled selection through `aria-selected`. A regression test exercises a nested action. |
| RT-2026-07-17-357 | Output reviewer | Forcing Report Studio, research Markdown, chart fallbacks, the model spreadsheet, or virtualized grids through the ordinary table primitive would erase print rules, responsive fallbacks, or domain-specific keyboard behavior. | High | Resolved in scope | `DataTable` owns only non-virtualized application tables. Specialized renderers remain in place and are audited against the same text/numeric/header alignment contract without sharing markup. |
| RT-2026-07-17-358 | API reviewer | `sortable: true` without an `onSort` callback rendered a focusable header button that announced sortability but did nothing. | Medium | Resolved in primitive | A sortable header becomes interactive and receives `aria-sort` only when both the column flag and table callback are present; otherwise it renders as plain header text. |
| RT-2026-07-17-359 | CSS reviewer | The global legacy app-table rule centers every header and cell with higher effective precedence, so a typed `text`/`numeric` column can still render centered even though the primitive emits the right utility classes. | High | Resolved in stylesheet boundary | Mark primitive output with `caos-data-table` and exempt only that class from the legacy centering selector. The screenshot-backed Pipeline proof and a primitive class test pin the boundary without changing raw specialized tables. |
| RT-2026-07-17-360 | Screen-reader reviewer | Mechanical migration changed identifying `<th scope="row">` cells in IC Book and Portfolio Lab into ordinary `<td>` cells, weakening row navigation even though the visual output stayed identical. | High | Resolved in primitive and call sites | Add a typed `rowHeader` column flag that renders native row headers; apply it to run, borrower, constraint, meeting/date, issuer, observation, and adapter identifier columns. The primitive test pins `scope="row"`. |
| RT-2026-07-17-361 | Power-user reviewer | A roving row plus naturally tabbable links and buttons still leaves O(rows) stops, while blindly suppressing them makes profile/evidence actions keyboard-inaccessible. | High | Resolved in interaction contract | Activatable tables expose only the roving row by default. The caption and `aria-keyshortcuts` announce F2; F2 exposes and focuses actions for that row only, Escape restores the row, blur closes action mode, and disabled or explicitly negative-tabindex controls are never promoted. Tests pin entry, exit, discoverability, and exclusion. |
| RT-2026-07-17-362 | Virtualization reviewer | Building roving focus from only rendered IDs makes Arrow Down clamp at the virtual-window edge; analysts cannot keyboard-reach the rest of a large book. | High | Resolved in grid adapters | Roving state uses the full filtered ID order. When the next ID is offscreen, store a pending focus target, scroll to its estimated offset, and focus after virtualization mounts the row. Boundary tests cover the handoff. |
| RT-2026-07-17-363 | Maintainability reviewer | Four local copies of the F2/tab-stop algorithm would drift on disabled controls, explicit negative tabindex, or newly interactive descendants. | High | Resolved in utility | Consolidate selector, original-tabindex preservation, availability sync, and first-action focus in `lib/rowActionMode.ts`; DataTable and all four grids consume it, with focused suites covering both table and grid paths. |
| RT-2026-07-17-364 | Failure-state reviewer | Entering action mode on a row with no available actions can remove the row from the Tab order while focus stays nowhere. | High | Resolved in utility contract | `focusFirstRowAction` returns whether an available action was focused; callers set action mode only on success. Disabled, aria-disabled, and author-negative controls never qualify. |

### Critic reopen conditions (surface table contract)

Reopen if arrow-key row movement navigates, mutates, or opens detail; a nested
control also activates its parent row; controlled selection lacks an announced
state; a header advertises sorting without an effect; or specialized paper,
chart, spreadsheet, or virtualized-grid output is mechanically migrated to the
ordinary `DataTable`; or the legacy global table selector overrides typed column
alignment inside `DataTable`; or an identifier column loses native row-header
semantics during migration; or nested row actions either multiply the default Tab
sequence or become unreachable without an announced keyboard path; virtualization
traps focus at a rendered-window boundary; or an actionless row can enter action
mode and lose its focus stop.

## 2026-07-17 — Surface redesign live-path parity contract

Decision under review: bring Deep-Dive, Monitor, Pipeline, Query, Reports,
Profile, Portfolio, Sector, and Model live paths to parity through conservative
adapters and a shared source-reference presentation without inventing evidence
or laundering partial/Restricted states into committee-ready output.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-365 | Provenance reviewer | A reusable source chip can make a human label or missing identifier look like clickable persisted evidence, creating a false audit trail. | Critical | Resolved in component contract | `SourceRef` accepts an explicit ready source with an identifier and handler/href, or an explicit unavailable state with a reason. It never synthesizes an identifier, never renders an inert element as a link, and always exposes absence in text. |
| RT-2026-07-17-366 | Data-semantics reviewer | Inferring alignment from numeric-looking strings will right-align CUSIPs, dates, module IDs, versions, and rating labels as if they were measures. | High | Resolved in adapter rule | Prefer adapter schema metadata; infer numeric alignment only for finite numeric values in measure columns. Identifier/date/rating keys remain text even when every rendered value contains digits. Tests pin representative false-positive keys. |
| RT-2026-07-17-367 | Disclosure reviewer | Truncating live adapter arrays to a fixed slice silently discards adverse rows and can make a stressed credit look cleaner. | Critical | Resolved in disclosure contract | Initial density may be bounded, but every truncation renders an exact `+N more` control that expands the full persisted list in place and is keyboard-operable. Counts derive from the same array rendered, never a parallel summary. |
| RT-2026-07-17-368 | QA-governance reviewer | Layer or pane aggregation can average away a single Blocked/Restricted module and display a green parent state. | Critical | Resolved in severity contract | Aggregate with the Phase-1 worst-severity ordering. Blocked dominates Restricted, Restricted dominates Passed, and absent/not-reviewed never upgrades to green. Pane and layer labels retain the source status vocabulary. |
| RT-2026-07-17-369 | Monitoring reviewer | Attaching a plausible source label to an alert without a persisted source identifier gives the appearance that the alert is one click from evidence when it is not. | Critical | Resolved in live-row contract | Monitor evidence actions are built only from persisted evidence/source identifiers. Missing provenance renders `Source unavailable` with the reason; demo evidence remains visibly demo and cannot be mixed into a live row. |
| RT-2026-07-17-370 | Pipeline reviewer | Reconstructing mid-flight output from persisted rows can look terminal, while a re-run affordance on an active run can duplicate work or spend. | High | Resolved in state contract | Partial simulation is explicitly labelled running/partial and shows produced, pending, and Blocked rows separately. Re-run is offered only for a terminal Blocked/failed module with its persisted reason; active modules never expose re-run. |
| RT-2026-07-17-371 | Query reviewer | Routing a graph lane through the canvas while retaining stale result counts or uncited generated prose makes the visualization more polished but less truthful. | High | Resolved in renderer contract | Graph counts come from the rendered node/edge payload. Grounded prose renders its attached citations at the claim/result boundary; if none exist, it states that the result is uncited and remains draft. |
| RT-2026-07-17-372 | Model-governance reviewer | A per-node origin badge can call a node live merely because Model V2 is selected, even when the node is reference/fallback or V2 is unavailable for the real stack. | High | Resolved in origin contract | Origin is derived from the node's actual payload and availability gate, with explicit live/reference/derived/unavailable states. Selecting V2 does not upgrade provenance, and unavailable live stacks retain a usable, explained fallback path. |

### Critic reopen conditions (live-path parity)

Reopen if any source control lacks a persisted identifier or an explicit absence
reason; a digit-bearing identifier/date is inferred as a numeric measure; a
truncated adverse row cannot be revealed; a parent QA status is greener than its
worst child; live Monitor falls back to demo evidence; a running module exposes
re-run or appears complete; Query counts differ from the rendered payload or
grounded prose hides missing citations; or Model V2 selection alone changes an
origin to live.

## 2026-07-17 — Surface redesign per-surface close contract

Decision under review: close the remaining workflow, recovery, confirmation, and
copy defects surface by surface without turning an invalid context into a plausible
different record, hiding partial failure, or adding confirmation theater.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-373 | Context-integrity reviewer | Falling back from an unknown portfolio, issuer, or decision identifier to the first available record makes a stale deep link silently show the wrong credit. | Critical | Resolved in state contract | Unknown identifiers render an explicit not-found state and retain a visible route to a deliberate picker. Name resolution never substitutes another entity; unresolved persisted IDs remain labelled as unavailable IDs. |
| RT-2026-07-17-374 | Transaction reviewer | A generic confirm dialog can look safer while still concealing the exact vote, holdings replacement, batch scope, or ratification set being committed. | High | Resolved in confirmation contract | Use the shared arm/confirm interaction and state the exact action and affected scope inline. Reset the armed state when scope changes; active work is never launched by an arrow/focus gesture. |
| RT-2026-07-17-375 | Failure-recovery reviewer | Reporting only `N/M succeeded` discards the information needed to retry safely and encourages rerunning successful, cost-bearing work. | High | Resolved in outcome contract | Persist and disclose per-item failures with stable identifiers and reasons. Retry actions target only failed items where the endpoint supports it; otherwise the UI explicitly says a scoped retry is unavailable. |
| RT-2026-07-17-376 | Upload-governance reviewer | Retaining the result step can accidentally re-submit on refresh or claim that an ignored run-mode and absent scanner verdict were applied. | Critical | Resolved in upload contract | The settled outcome is display-only until an explicit new action. Run mode is labelled metadata unless carried by the request, EDGAR follows the same outcome transition, and scan posture is rendered only from persisted response data or explicitly unavailable. |
| RT-2026-07-17-377 | Settings reviewer | Unifying save affordances without one canonical persisted value and a normalized round trip leaves the visible setting different from the value actually used. | High | Resolved in persistence contract | Normalize at read/write boundaries, derive dirty state only from controls saved by the shared transaction, and keep immediate controls outside that snapshot. Unknown key posture remains checking/unavailable, never green-ready. |
| RT-2026-07-17-378 | Recovery-security reviewer | Confirming recovery words by storing or echoing plaintext beyond the signup interaction increases credential exposure and can leak secrets through logs or browser persistence. | Critical | Resolved in recovery contract | Compare the confirmation in component memory only, mask by default with an explicit reveal, never log or persist plaintext locally, and clear both entries after completion or mode change. |
| RT-2026-07-17-379 | Async-selection reviewer | Fetching the whole sponsor or worklist register on each selection can blank the page and let a slower prior request overwrite the current selection. | High | Resolved in selection contract | Fetch stable registers independently of selection, patch only the selected context, and reject stale detail responses by request identity where a detail fetch remains necessary. Selection stays visible while dependent detail loads. |
| RT-2026-07-17-380 | Time-semantics reviewer | Replacing raw UTC with local-only time makes committee records ambiguous across offices and daylight-saving boundaries. | High | Resolved in display contract | Decision times show a localized primary timestamp plus an explicit UTC value. Formatting is deterministic in tests; persisted values remain ISO/UTC. |
| RT-2026-07-17-381 | Retry reviewer | A post-completion retry that repeats the research run can duplicate spend when only context linking failed. | High | Resolved in recovery contract | Retry only the failed linking step with the existing completed result/run identifiers. If the API lacks that operation, retain the banner and state the limitation rather than rerunning research. |
| RT-2026-07-17-382 | Navigation reviewer | Role-aware landing can override an explicit deep link or stale role preference and strand a user away from the requested surface. | High | Resolved in routing contract | Apply role defaults only at the unaffiliated root entry. Explicit routes and query context always win, and every landing destination remains reachable in the global navigation. |

### Critic reopen conditions (per-surface closes)

Reopen if an invalid identifier renders a different real record; a confirmation
omits the exact mutation scope or survives a scope change; partial failure loses
item-level reasons; refresh or result retention re-submits work; ignored run mode
or absent scanner posture is presented as applied; settings display a value other
than the canonical persisted value; recovery words reach logs or persistent local
storage; stale selection requests can win; decision time loses UTC; retry repeats
completed spend; or root role routing overrides an explicit destination.

## 2026-07-17 — Analyst authority, governed exceptions, and verified research figures

Decision under review: add an append-only analyst view beside the deterministic
system view; permit a separately approved, time-bounded IC evidence exception
without changing CP-5; add cited advisory insights and deterministic CAOS-only
figures to Deep Research.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-383 | QA-governance reviewer | A so-called exception could silently upgrade a Restricted or Blocked run, bypassing the CP-5 committee gate for every downstream consumer. | Critical | Resolved in contract | Keep `committee_export_allowed()` and all engine statuses unchanged. Exception finalization is only available for a current Restricted or Insufficient Information run with no CRITICAL finding; it freezes a labelled exception artifact and never marks the source run Committee Ready. |
| RT-2026-07-17-384 | Authorization reviewer | The existing QA view is presentational, so checking it client-side would give an analyst approval power merely by switching a preference. | Critical | Resolved in route design | Review authority is server-side only, restricted to `qa` or `admin`; the reviewer cannot be the requester or agenda owner. `role_view` is never consulted. |
| RT-2026-07-17-385 | Decision-semantics reviewer | Reusing the IC action (`approve` / `decline` / `revisit`) as an analyst investment view conflates two distinct decisions and produces irreconcilable history. | High | Resolved in data model | Store an immutable analyst stance independently (`OVERWEIGHT` / `NEUTRAL` / `UNDERWEIGHT`) and explicitly freeze both the analyst view and IC action in the decision snapshot. |
| RT-2026-07-17-386 | AI-safety reviewer | Advisory prose could be mistaken for evidence or mutate an analyst view, an exception, or final IC state. | Critical | Resolved in authority contract | Advisory insights are explicit, cited, draft-only artifacts. Closed-set evidence validation, finite-number checks, and a deterministic fallback apply; AI has no route that mutates opinion, readiness, exception, or decision state. |
| RT-2026-07-17-387 | Research-evidence reviewer | Letting a web-research model emit chart rows makes visually persuasive but unverified numbers appear committee-grade. | Critical | Resolved in figure contract | Deep Research figures are built only from finite CAOS facts bound to an explicit issuer context. Web-only and demo research remain prose/tables; figures carry source IDs and accessible table equivalents. |
| RT-2026-07-17-388 | Migration reviewer | Requiring a new analyst opinion field could silently rewrite historical decisions or strand an existing immutable record. | High | Resolved in rollout | The migration is additive. Finalized decisions are never changed; unfinalized agenda items surface a clear missing-view readiness item until an analyst deliberately links a version. |

### Critic reopen conditions (analyst authority)

Reopen if an exception changes a run's CP-5 or export status; a client role
preference grants reviewer power; an IC action is displayed as an analyst stance;
AI output can write authority-bearing records; a research chart uses uncited web
numbers or non-finite data; or migration modifies an already finalized decision.

## 2026-07-17 — Surface polish and token-enforcement critic pass

Decision under review: complete a narrow token, typography, and motion consistency
pass without mechanically normalizing specialized spreadsheet, chart, or paper
output.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-17-389 | Design-systems reviewer | Replacing every literal color would erase intentionally semantic chart ramps and the Report Studio paper palette, producing less legible analytical output. | High | Resolved in scope | Change only application-chrome literals that have an exact CAOS token equivalent. Preserve chart, tranche, and paper-document palettes as documented semantic exceptions. |
| RT-2026-07-17-390 | Motion reviewer | A global duration replacement can remove meaningful live-state feedback or leave motion enabled for reduced-motion users. | High | Resolved in scope | Replace only the posture-bar's decorative 300ms width transition with the established 160ms ease-out timing plus an explicit reduced-motion opt-out; do not alter running-state animation contracts. |
| RT-2026-07-17-391 | Accessibility reviewer | Raising every 9px datum to the metadata floor can corrupt dense spreadsheet geometry or SVG label placement, while leaving chrome labels below the floor harms readability. | High | Resolved in scope | Adopt `text-caos-3xs` only for HTML metadata/chrome labels. Preserve spreadsheet coordinates and SVG/chart labels where their layout is data-visualization-specific. |
| RT-2026-07-17-392 | Maintainability reviewer | Treating raw buttons and specialized tables as automatic violations would trigger risky wholesale migrations and obscure genuine exceptions. | High | Accepted | Keep the inventory advisory. The typed `DataTable` applies only to ordinary operational data grids; paper, chart, spreadsheet, and virtualized outputs remain explicit exceptions. Add no blanket lint gate until each remaining surface has a safe component contract. |

### Critic reopen conditions (surface polish)

Reopen if a paper, chart, or tranche semantic color is converted to a generic UI
token; a transition loses reduced-motion behavior or changes live-state meaning;
spreadsheet or SVG geometry changes from a typography sweep; or an automated
enforcement rule forces specialized output into the ordinary table/button contract.

## 2026-07-18 — All-surface quieting, typesetting, layout, hardening, and copy pass

Decision under review: refine every routed frontend surface through shared type,
spacing, state, responsive, recovery, and copy contracts without relaxing CAOS's
dense institutional register or hiding specialist capability.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-393 | Credit-workflow reviewer | A generic "quieter" treatment could mute stale, Blocked, or unratified conclusions until a wrong read looks calm. | Critical | Resolved in design | Reduce only the area and chroma of semantic washes. Preserve the glyph, explicit status word, authority chips, and accessible contrast; never neutralize the status itself. |
| RT-2026-07-18-394 | Typography reviewer | Removing monospace wholesale would destroy numeric scanability and decimal alignment in dense tables. | High | Resolved in component boundary | Split prose from numerics only in shared decision and table primitives. Numeric columns, timestamps, ids, labels, and authority metadata retain mono tabular styling; narrative cells and conclusions use the sans reading face. |
| RT-2026-07-18-395 | Responsive-workflow reviewer | Hiding Model or Deep-Dive editors at tablet widths can strand an analyst who expected to edit from a smaller workstation. | High | Resolved in topology and copy | Use the existing compact read-only review below the desktop editor threshold, label the limitation and retained workstation capabilities explicitly, and keep navigation/handoff actions visible. Full editing remains available at desktop widths. |
| RT-2026-07-18-396 | Report-output reviewer | Stacking Report Studio rails too early could turn a committee review into a long page and obscure composition controls. | High | Resolved in topology | Stack only below the width at which the paper preview plus both fixed rails becomes unusable. Keep the preview first, deliverables second, composition/export controls third, with all functions retained and independently scrollable. |
| RT-2026-07-18-397 | Density reviewer | Raising every small label or optical offset mechanically would break spreadsheet, chart, appendix, and virtualized-row geometry. | High | Resolved in scope | Enforce the mobile 12px floor on product chrome and shared state copy. Preserve documented paper appendix, SVG/chart, spreadsheet, and row-fit literals as explicit specialist exceptions. |
| RT-2026-07-18-398 | Layout reviewer | Normalizing every 5–7px row padding to the 4pt scale could reduce usable row count or create oversized worklists. | Medium | Accepted exception | Normalize shared shell/group spacing and ordinary page chrome. Retain specialist row-density and optical-fit literals where exact geometry is part of the renderer; track them as local exceptions, not reusable tokens. |
| RT-2026-07-18-399 | Failure-recovery reviewer | Replacing terse retry labels with generic friendly prose can obscure the failed operation or imply work was lost. | High | Resolved in copy contract | Name the failed check/view/source in the action, state what remains preserved, avoid developer-only remediation in user-facing copy, and keep reference ids available for escalation. |
| RT-2026-07-18-400 | Regression reviewer | Shared type and spacing edits touch every route and can create horizontal overflow that unit tests will miss. | High | Resolved in verification gate | Run the complete build/test suite, the repository's multi-viewport layout matrix, and the mandated axe route matrix with browser-only fixtures; review representative desktop, phone, and 200% zoom captures before handoff. |

### Critic reopen conditions (all-surface refinement)

Reopen if any adverse state loses a glyph or explicit label; prose remains forced
into mono or numeric columns lose tabular alignment; a compact editor implies that
editing is available when it is not; Report Studio drops or reorders a capability;
the mobile chrome floor is still below 12px; specialist optical geometry is
normalized without renderer-specific proof; recovery copy does not name the failed
operation; or the route, layout, and accessibility matrices are not clean.

## 2026-07-18 — Final pre-deployment consolidation critic pass

Decision under review: consolidate the application, control-wiring, audit-loop,
throughput, and data-protection evidence into a final pre-deployment gate without
turning historical passes or configuration intent into a release claim.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-401 | Release-integrity reviewer | Results from a dirty working tree cannot identify the bytes being approved, even when every local command is green. | Critical | Resolved in gate design | The consolidated plan is a **NO-GO** until H0 produces a clean immutable candidate, image digest, schema/config fingerprint, and evidence bundle tied to those exact bytes. Current results are diagnostic evidence only. |
| RT-2026-07-18-402 | Product-coverage reviewer | Treating `FEATURE_TRACKER.csv` as the whole application hides newer Portfolio Lab, Decisions/IC Book, Sponsors, Sector RV, and shared-context flows that have no dedicated rows. | Critical | Resolved in inventory design | A route/platform surface matrix becomes the companion inventory; L23 requires route, nav, API, tracker, and E2E parity before release. The 355 historical Pass rows no longer stand alone as whole-app proof. |
| RT-2026-07-18-403 | Interaction reviewer | A source scan showing handlers on buttons proves only syntax, not that the action reaches the intended mutation, survives reload, or handles failure. | Critical | Confirmed blocker | Static wiring is retained as a completeness screen only. The current three-browser E2E failures block sign-off until each contract is fixed or the test is deliberately re-specified and rerun green. |
| RT-2026-07-18-404 | Performance reviewer | A fast 15-user SQLite laptop run could be presented as proof of production capacity despite using one worker, 30 seeded issuers, fixture LLMs, and no live external dependencies. | High | Resolved in evidence wording | The run is labelled current-tree smoke only. Production-like evidence remains the dated Postgres/two-worker 15-user run; L25 requires a repeat on the immutable target candidate with target data, identity, storage, and queue settings. |
| RT-2026-07-18-405 | Data-governance reviewer | “Everything is in the vault” is a dangerous false premise: structured work product is in Postgres and unsaved state can remain in browser storage. | Critical | Resolved in storage model | The security and closure documents now publish a record-by-record store matrix. Vault and Postgres must be backed up together; browser-only state is explicitly non-durable; any authoritative work product must cross a server persistence boundary. |
| RT-2026-07-18-406 | Recovery reviewer | Local restore scripts and an optional rclone service do not prove an encrypted, fresh, off-host recovery point exists or that operators will be alerted when it stops. | Critical | Confirmed blocker | G8/G9 and L22/L26 require target-host evidence: encrypted destination, least-privilege access, age/failure alert, and a remote-only restore after local-copy loss. Configuration review earns no closure credit. |
| RT-2026-07-18-407 | Maintainability reviewer | Reachability scans can call framework entrypoints dead and can miss dynamic imports; deleting all reported modules would be unsafe. | High | Resolved in disposition rule | The report labels 16 TypeScript paths as candidates, not confirmed deletion targets. L24 requires owner classification plus compiler/test/build proof before removal. Backend Vulture is clean; whole-tree Fallow remains a candidate-host gate because it could not be freshly installed in the restricted environment. |
| RT-2026-07-18-408 | Reliability reviewer | Six route error boundaries across eighteen pages leave most concepts dependent on the root fallback, so one failed segment can discard more analyst context than intended. | High | Confirmed blocker | L27 requires deliberate per-route recovery coverage or a documented shared-boundary equivalence, with failed-operation copy and preserved context verified in E2E. |
| RT-2026-07-18-409 | Integration reviewer | Route enumeration can still miss workers, queues, storage, provider egress, backups, and spec-only/equivalent-service seams. | Critical | Resolved in map design | The application map includes 18 page endpoints, 137 API routes, executors/background jobs, Postgres, vault, edge/auth, provider egress, market/email seams, and backup/restore. C3/C5/C13 remain explicit integration gates. |
| RT-2026-07-18-410 | Security reviewer | No secret finding and no indexed taint result are not proof of secure data flow, especially when the GitNexus PDG layer is unavailable. | High | Resolved in evidence wording | Secret scanning is reported with false-positive adjudication, and the absent taint layer is a limitation. L18/L26 require target configuration, authorization/isolation tests, egress policy, and recovery evidence; no “secure by scan” claim is permitted. |
| RT-2026-07-18-411 | Audit-governance reviewer | Adding more checklists without an owner, trigger, artifact, and consuming gate creates another unexecuted audit framework. | High | Resolved in loop contract | L23–L27 each name mechanism, trigger, artifact, and release gate. They are MANUAL/WORK-ITEM until evidence exists and cannot be cited as green merely because the rows exist. |

### Critic reopen conditions (pre-deployment consolidation)

Reopen if a dirty tree is called a release candidate; the 355-row tracker is
called whole-app coverage without surface parity; static button handlers are called
E2E proof; SQLite load is called production capacity; vault is described as the
only authoritative store; backup configuration is credited without remote recovery;
dead-code candidates are deleted without framework-aware confirmation; route failure
recovery remains implicit; non-page platform services disappear from the map; an
absent taint finding is called a security pass; or L23–L27 are cited without dated
artifacts.

## 2026-07-18 — Analysis-context layout stability critic pass

Decision under review: reserve stable shell geometry while the shared analysis
context resolves, and publish a presentation-only failure event from the existing
context hook so the reserved state cannot remain misleadingly busy.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-412 | Density reviewer | Reserving space for a context that never appears wastes scarce vertical room on every analytical surface. | High | Resolved in lifecycle | Enterprise surfaces already create or load an analysis context on mount. Reserve exactly the compact summary geometry they will receive; do not add space outside `EnterprisePage` or to non-enterprise routes. |
| RT-2026-07-18-413 | Reliability reviewer | If context creation fails before it dispatches a success event, a permanent loading label would misstate the system indefinitely. | High | Resolved in event contract | Emit a presentation-only `caos:analysis-context-error` event from the existing hook catch path. The strip replaces its loading copy in place with the current explicit unavailable state; authority and mutation state remain owned by the hook. |
| RT-2026-07-18-414 | Accessibility reviewer | Forcing the summary to a fixed row could clip the active context name or hide evidence counts from keyboard and screen-reader users. | High | Resolved in layout | Keep the full text in the accessible DOM, truncate only visually, retain the expandable disclosure and focus ring, and expose the full summary as a title. |
| RT-2026-07-18-415 | Security reviewer | Reusing the context object from a browser event would bypass the strip's independent ownership re-check. | Critical | Resolved in data flow | Keep the existing `getContext` and `listFindings` reload after every success event. The new error event carries no context data and grants no authority. |

### Critic reopen conditions (analysis-context stability)

Reopen if a non-enterprise route gains reserved chrome; a context failure leaves a
permanent busy state; summary content becomes unavailable to keyboard or assistive
technology; the event detail is trusted as owned context; or the cold-load route
matrix still records context-strip CLS.

## 2026-07-18 — Whole-frontend Fallow remediation critic pass

Decision under review: drive Fallow dead-code, security-candidate, duplication,
and health findings to zero through traced removals, behaviour-preserving
extraction, and narrowly justified suppressions for intentional static patterns.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-416 | Change-integrity reviewer | A bulk auto-fix can overwrite the large dirty worktree or delete dynamically imported code that the static graph cannot see. | Critical | Resolved in workflow | Preview every Fallow fix, trace every candidate, inspect exact repository references, and edit with explicit patches only. Treat pre-existing changes as user-owned and avoid overlapping files unless the edit is isolated and verified. |
| RT-2026-07-18-417 | React reviewer | Splitting high-complexity components mechanically can change hook order, closure freshness, focus restoration, or async race handling while improving a score. | Critical | Resolved in extraction contract | Preserve hook order and state ownership. Extract pure calculations and leaf render components first, pass explicit values/callbacks, and rerun the owning tests plus the full suite after each file. Do not move hooks across component boundaries merely to lower a metric. |
| RT-2026-07-18-418 | Domain-model reviewer | Similar-looking credit UI and report fragments can encode different authority or evidence semantics; consolidating every clone can create a misleading generic abstraction. | High | Resolved in duplication rule | Extract only clones with identical behavioural and authority contracts. For deliberate fixture, document, or domain-specific parallels, retain the code and apply the narrowest Fallow suppression with an inline justification, then run stale-suppression detection. |
| RT-2026-07-18-419 | Coverage reviewer | Optimizing CRAP scores against Fallow's estimated coverage can produce churn unrelated to actual risk, especially in test and browser-runner callbacks. | High | Resolved in evidence model | Generate the real Vitest V8 coverage artifact and use it consistently for health decisions. Separate genuine decision complexity from uncovered developer-runner code; add tests where executable behaviour warrants them and document non-unit-testable runner callbacks precisely. |
| RT-2026-07-18-420 | API-hygiene reviewer | A supposedly unused DTO may still be consumed through a dynamic import or external package boundary, and a cascading deletion can remove an implicit contract. | Critical | Resolved in deletion gate | Require Fallow trace, exact symbol search, GitNexus impact, private-package confirmation, TypeScript, and the full test suite before retaining a deletion. Dynamic imports receive explicit narrow suppressions rather than deletion. |
| RT-2026-07-18-421 | Quality-gate reviewer | Raising thresholds or disabling rule families would make the report clean without improving the code and defeat the user's requested loop. | High | Resolved in gate policy | Do not disable rule families or globally raise thresholds. A finding closes only through a verified code/test improvement or a local evidence-backed suppression for an intentional construct. Final verification uses dead-code, security, duplication, health with real coverage, stale-suppression, TypeScript, lint, and tests. |

### Critic reopen conditions (Fallow remediation)

Reopen if an untraced export/file is deleted; an existing dirty hunk is replaced;
hook order or state ownership changes without focused proof; a shared abstraction
mixes distinct authority semantics; estimated coverage is presented as real;
suppression lacks a local justification; a rule family or global threshold is
relaxed to manufacture a clean report; or final Fallow, TypeScript, lint, and test
evidence is not green on the resulting tree.

## 2026-07-18 — Whole-frontend accessibility remediation critic pass

Decision under review: remediate every confirmed WCAG 2.2 A/AA, axe
best-practice, keyboard, coarse-pointer, and narrow-layout accessibility fault,
then keep the rendered route matrix as the repository gate.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-422 | Assistive-technology reviewer | A green WCAG-tag-only axe run can conceal invalid landmark/heading/table structure, especially composite-widget ownership. | High | Resolved in gate | Add rendered best-practice coverage to the axe matrix, retain fail-closed route readiness, and inspect ARIA grids with the repository observation-log rules. |
| RT-2026-07-18-423 | Keyboard reviewer | Replacing landmarks or compact layouts can leave visual parity while breaking focus order, roving focus, Escape handling, or focus restoration. | Critical | Resolved in verification | Prefer native semantics, preserve DOM order, add focused interaction assertions, and run keyboard/focus checks across route and modal states. |
| RT-2026-07-18-424 | Responsive reviewer | Structural overflow checks can pass while headers overlap controls or narrow breakpoints remove the analyst's editing workflow. | Critical | Resolved in scope | Verify representative screenshots, hit-test the Ask launcher, measure real coarse-pointer targets, and compare desktop/narrow capability inventories for Deep-Dive and Model Builder. |
| RT-2026-07-18-425 | Design-system reviewer | Global changes to `Panel`, `SurfaceState`, or action sizing can damage dense desktop hierarchy across dozens of callers. | Critical | Resolved in change contract | Preserve public APIs, prefer contextual heading overrides, constrain touch sizing to coarse pointers, and run the complete route/viewport matrix. GitNexus marks `Panel` and `SurfaceState` CRITICAL, so focused and full verification are mandatory. |
| RT-2026-07-18-426 | Change-integrity reviewer | The dirty IC Book and QA worktree can be overwritten or falsely attributed to this audit. | Critical | Resolved in workflow | Use explicit patches only, avoid unrelated dirty hunks, record baseline TypeScript/lint faults separately, and inspect the final diff by path before handoff. |
| RT-2026-07-18-427 | Compliance reviewer | Claiming “no faults” from automation alone overstates conformance because screen-reader behavior and physical-device ergonomics retain manual limits. | High | Accepted with disclosure | Report “no detectable automated faults” only after repeated clean gates and disclose residual VoiceOver/NVDA, browser/OS, and physical-device manual-test limits. |

### Critic reopen conditions (accessibility remediation)

Reopen if best-practice rules are excluded; any route/state is skipped; a
composite widget has invalid ownership or incomplete keyboard behavior; a narrow
surface loses a desktop capability without an accessible alternative; the
launcher obscures a focusable control; shared-component blast radius is not
verified; unrelated dirty work is replaced; or the final report equates an
automated zero with complete legal conformance.

## 2026-07-18 — Query draft continuity across identity revalidation

Decision under review: retain an in-progress Query question across the existing
security remount on tab refocus without weakening principal isolation.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-422 | Security reviewer | Persisting an analyst question in browser storage can expose sensitive research to the next user on a shared workstation. | Critical | Resolved in storage boundary | Use tab-scoped `sessionStorage` under the existing `caos.*` namespace. The established principal binder clears that namespace on logout, 401, or identity change; the identity revalidation/remount itself remains unchanged. |
| RT-2026-07-18-423 | Context-integrity reviewer | A global draft can restore one issuer or portfolio question into a different analysis context. | High | Resolved in keying | Key the draft by the owned analysis-context id and gate composer readiness until that exact context's draft has hydrated. A context change restores only its own entry or an empty value. |
| RT-2026-07-18-424 | Reliability reviewer | Private mode, quota exhaustion, or disabled storage could make Query unusable if persistence is mandatory. | High | Resolved in degradation | Wrap reads and writes; storage failure preserves the current in-memory composer and execution path, losing only remount continuity. |
| RT-2026-07-18-425 | Authority reviewer | A browser draft could be mistaken for an authoritative or durable investigation. | High | Resolved in semantics | Cache only unsubmitted composer text. Runs, findings, evidence, and authority remain server-owned; no draft is shown as completed, cited, or recoverable beyond the current tab. |

### Critic reopen conditions (Query draft continuity)

Reopen if auth revalidation no longer tears down stale-principal state; a draft
survives logout or principal change; a draft crosses analysis-context ids; storage
failure blocks Query; or cached text is presented as a completed investigation.

## 2026-07-18 — All-surface spatial rhythm critic pass

Decision under review: arrange every CAOS route through shared spacing and
composition contracts while preserving the intentionally dense institutional
terminal, route capability, and specialist workbench behavior.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-428 | Analyst-density reviewer | A global spacing increase can make data-heavy worklists feel like consumer SaaS and reduce the rows, evidence, or model cells visible without scrolling. | Critical | Resolved in scale | Keep the 4px base and the existing compact control geometry. Use 8px for related content, 12px for pane rhythm, and 16–24px only for true section separation; do not inflate table rows or report-paper internals. |
| RT-2026-07-18-429 | Capability reviewer | Rearranging support rails can hide context or evidence at common laptop widths, breaking the one-interaction evidence principle. | Critical | Resolved in composition | Preserve every supplied slot and its existing drawer controls. Change presentation only; retain DOM order, focus behavior, drawer access, and the primary artifact as the dominant region. |
| RT-2026-07-18-430 | Shared-component reviewer | `PersonaWorkbench`, `SubHeader`, and `Panel` are CRITICAL hubs; an apparently small global rule can clip or overlap controls across most routes. | Critical | Resolved in implementation boundary | Do not change shared component behavior or public APIs. Constrain the work to existing CSS hooks and verify all 17 routed surfaces at 1440×1000 and 1024×900, including horizontal-overflow and browser-error checks. |
| RT-2026-07-18-431 | Report-integrity reviewer | Workspace rhythm rules can accidentally alter Report Studio and Research paper geometry, compromising print fidelity. | Critical | Resolved in selector boundary | Exclude `rd-*`, `research-doc`, and print rules from workspace spacing changes; treat the paper as a deliverable nested within the arranged dark shell. |
| RT-2026-07-18-432 | Responsive reviewer | A clean desktop composition can still become a monotonous stack or fixed-height overlap at compact widths. | High | Resolved in verification | Keep drawer mode and route-specific compact adaptations intact, add only breakpoint-scoped spacing compression, and inspect both full compact contact sheets and representative individual routes. |
| RT-2026-07-18-433 | Change-integrity reviewer | The repository has substantial unrelated WIP, including this review log, so a broad design pass can overwrite or misattribute user changes. | Critical | Resolved in workflow | Apply an append-only review entry and isolated CSS patch, avoid every pre-existing dirty source file, inspect exact diffs, and do not stage or commit. |

### Critic reopen conditions (all-surface spatial rhythm)

Reopen if table/report density changes; any context or evidence capability becomes
unreachable; a shared component API or behavior changes; paper output geometry
moves; any route develops overlap, horizontal overflow, or browser errors at the
verified viewports; or unrelated dirty work is replaced or attributed to this pass.

## 2026-07-18 — Settings save in-flight critic pass

Decision under review: make the global Settings save immediately inert while its
profile PATCH is in flight, then restore either a confirmed pristine state or the
existing dirty retry state.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-434 | Data-integrity reviewer | Disabling the action before persistence finishes could falsely imply that unsaved preferences are durable. | High | Resolved in state contract | Label the guarded state `Saving…`; update the baseline only after `saveAnalyst` returns true. A failed write keeps the old baseline, exposes the existing error/retry state, and re-enables the dirty action. |
| RT-2026-07-18-435 | Concurrency reviewer | A slow PATCH currently permits repeated clicks that enqueue duplicate revision-checked writes. | High | Resolved in guard | Set the in-flight flag synchronously before the first await, return early on subsequent invocations, and clear it in `finally`. |
| RT-2026-07-18-436 | Test-reliability reviewer | Asserting `aria-disabled` immediately can pass on the transient busy state without proving the save completed. | High | Resolved in browser contract | Make the E2E wait for the successful analyst-settings response and then assert the durable `No unsaved changes` title as well as the inert state. |

### Critic reopen conditions (Settings save in-flight)

Reopen if a failed save clears the dirty baseline; repeated clicks can enqueue more
than one profile write; the button presents `No unsaved changes` while the PATCH is
still pending; or browser coverage observes only the transient busy state without
confirming the server response.

## 2026-07-18 — Global Ask dock and Model target-size critic pass

Decision under review: reserve a compact, stable desktop dock for the global Ask
launcher and raise the two crowded Model Builder control families to the 24px
WCAG 2.5.8 target floor without changing analytical behavior.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-437 | Analyst-density reviewer | Reserving launcher space across the workspace can remove a useful model row from every route, including surfaces where Ask is unavailable. | High | Resolved in scope | Activate the 52px dock only while an authenticated, Ask-enabled route renders the stable Ask dock marker. Query and signed-out surfaces retain their full height. |
| RT-2026-07-18-438 | Interaction reviewer | Keying the dock to the visible trigger makes the page jump back to full height when Ask opens because the trigger disappears. | High | Resolved in lifecycle | Render a `display: contents` dock owner for the full authenticated Ask lifecycle, including open issuer chat, Deep-Dive ownership, and the global modal. The reserved geometry therefore does not change on open/close. |
| RT-2026-07-18-439 | Model-density reviewer | Enlarging all model rows would materially reduce worksheet information density. | High | Resolved in target boundary | Change only the crowded 20px assumption inputs and 15px collapsible row buttons identified by the rendered target-spacing gate; preserve column widths and all non-interactive worksheet row geometry. |

### Critic reopen conditions (Ask dock and Model targets)

Reopen if the launcher overlaps a painted focusable target; opening Ask changes
route height; Query or signed-out surfaces reserve an empty dock; Model Builder
loses column alignment or control reachability; or the full rendered route matrix
reports any target-size, clipping, overflow, or overlay failure.

## 2026-07-18 — Whole-suite database isolation critic pass

Decision under review: establish the existing throwaway CAOS database, vault,
key, and static-export test environment in the suite-root conftest before any
cohort, performance, server, or stress module can import cached server settings.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-440 | Production-safety reviewer | `get_settings` is a CRITICAL hub; changing it to accommodate pytest could alter 238 direct dependents and 58 execution flows. | Critical | Resolved in boundary | Do not edit production configuration or database symbols. Move only the existing pytest environment bootstrap one conftest level upward, before collection imports. |
| RT-2026-07-18-441 | Integration-test reviewer | Unconditionally replacing `DATABASE_URL` would silently turn the Postgres worker lane into SQLite and make its locking assertions vacuous. | Critical | Resolved in override contract | Preserve the existing `setdefault` contract: an explicitly supplied Postgres URL remains authoritative, while an unset local run gets a throwaway SQLite database. |
| RT-2026-07-18-442 | Credential-safety reviewer | Broadening the key blanking to all test packages could either spend real tokens unexpectedly or prevent a deliberately live test lane. | Critical | Resolved in existing opt-in | Retain the existing force-blank behavior and its `CAOS_TEST_LIVE=1` opt-in exactly; the only change is that it now takes effect before the earliest test import. |
| RT-2026-07-18-443 | Fixture-isolation reviewer | Leaving both bootstrap blocks active could allocate split temp roots so cleanup snapshots one database while server code binds another. | High | Resolved in single ownership | Make `caos/tests/conftest.py` the sole environment owner. Keep rate-limit, issuer-baseline, seeded-DB, and helper fixtures nested under `tests/server`, consuming the already-established environment. |

### Critic reopen conditions (whole-suite database isolation)

Reopen if any production module changes; an explicit Postgres test URL is
overridden; `CAOS_TEST_LIVE=1` no longer preserves supplied provider keys; nested
fixtures resolve a different database path than the imported engine; or a
whole-tree collection can bind `server/data/caos.db` before test isolation.

## 2026-07-18 — Fallow suppression-governance critic pass

Decision under review: give every active Fallow suppression a machine-readable
reason and enable the repository rule that rejects future unreasoned markers.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-444 | Code-health reviewer | Adding prose can cosmetically legitimize unresolved complexity instead of reducing it. | High | Resolved in evidence contract | Keep every suppression line-scoped, preserve Fallow's normal thresholds, require zero unsuppressed findings, and require every marker to remain non-stale. Reasons must name the concrete orchestration, render, dynamic-entry, or trust boundary. |
| RT-2026-07-18-445 | Security reviewer | A generic reason on `security-sink` could conceal a genuine path, TLS, or command-injection candidate. | Critical | Resolved in per-site trust boundary | Tie each runner suppression to its checked-in `import.meta.url`, separator-free `readdir` name, loopback-only TLS target, or fixed executable/argument constants; rerun the full security candidate scan at repository root. |
| RT-2026-07-18-446 | Tooling reviewer | Enabling `require-suppression-reason` can break CI or misparse JSX comments even when the source is legitimate. | High | Resolved in parser verification | Use the tool's verified `-- reason` syntax, inventory all TS/TSX/MJS markers afterward, and require `without_reason=0`, `stale=0`, and zero dead-code/governance findings. |
| RT-2026-07-18-447 | Coverage reviewer | Suppressing Playwright CRAP estimates could hide actual untested production branches. | High | Resolved in scope | Suppress only the six E2E harness functions whose execution is outside the Vitest Istanbul map; production functions continue to consume exact coverage and remain at zero findings. |

### Critic reopen conditions (Fallow suppression governance)

Reopen if a reason is generic or false; a security marker lacks a fixed trust
boundary; any marker becomes stale or unreasoned; Playwright suppression expands
into production source; or the root dead-code, complexity, or security scan is
non-zero after enforcement.

## 2026-07-18 — Local CI scanner isolation critic pass

Decision under review: make the repository's Vulture and Bandit CI commands
reproducible in a working tree that contains the designated `.venv311` runtime
and the legacy `.venv`, without narrowing either scanner's application-source
coverage.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-18-448 | Security reviewer | A broad virtual-environment exclusion could hide first-party Python placed under a source directory named `venv`. | High | Resolved in exact scope | Exclude only `caos/server/.venv` and `caos/server/.venv311`; keep all other `caos/server` and `caos/scripts` paths in Bandit's recursive scan. |
| RT-2026-07-18-449 | Dead-code reviewer | Vulture glob semantics could accidentally omit a sibling source path or fail to match site-packages consistently across platforms. | High | Resolved in verified patterns | Use absolute-path-matched suffix patterns `*/.venv/*,*/.venv311/*`, then rerun the exact repository-root command and require zero findings. |
| RT-2026-07-18-450 | CI-parity reviewer | Fixing only local documentation would leave the checked workflow command unreproducible and allow it to drift again. | Moderate | Resolved in canonical command | Put the exclusions directly in `.github/workflows/ci.yml`; clean CI runners retain identical first-party coverage while local agents can execute the same gate. |

### Critic reopen conditions (local CI scanner isolation)

Reopen if either exclusion expands beyond the two designated environment roots;
first-party code moves under an excluded root; a clean checkout and a local
`.venv311` checkout produce different first-party findings; or either scanner no
longer covers all of `caos/server` and `caos/scripts`.

## 2026-07-19 — Audit remediation critic pass

Decision under review: close every actionable audit finding across deployment,
security, worker correctness, resource governance, frontend delivery, and test
reliability without weakening existing controls or overwriting parallel work.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-451 | Production-safety reviewer | Enabling document egress merely because a provider key exists could send restricted credit documents off-host without an explicit operator decision. | Critical | Resolved in configuration contract | Pass the egress flag and provider/model settings through Compose, but retain the fail-closed `false` default and document that live synthesis requires an explicit `CAOS_DOCUMENT_EGRESS_ENABLED=true`. Test both disabled and enabled paths. |
| RT-2026-07-19-452 | Authentication reviewer | A CSRF control that trusts only `SameSite=Lax` is incomplete, while a token-only retrofit can break static-export clients, login bootstrap, or non-browser API consumers. | Critical | Resolved in layered boundary | Enforce same-origin `Origin`/`Referer` and Fetch Metadata on unsafe cookie-authenticated browser requests, provide a server-issued token for same-origin clients, and exempt only unauthenticated/bootstrap or explicitly non-cookie calls where the threat does not apply. Cover accepted and rejected paths with route-level tests. |
| RT-2026-07-19-453 | Authorization reviewer | Replacing the role denylist with an allowlist can lock out legitimate custom or historical roles, but retaining unknown-role write access fails closedness. | Critical | Resolved in migration boundary | Inventory persisted role values and declared role literals first; allow only documented writer roles, normalize legacy aliases deliberately, and reject unknown roles for writes while preserving read access. Add validation at both API and persistence boundaries where compatible with existing data. |
| RT-2026-07-19-454 | Distributed-systems reviewer | Moving rate limits into Postgres can add a database dependency to login, create a hot row, or fail open during database errors. | High | Resolved in bounded design | Use short-lived, source-keyed database buckets only when a shared database is configured, keep atomic increments and expiry cleanup bounded, and fail closed for protected login attempts. Retain an isolated test/local fallback only where a single process is explicit. Verify two limiter instances share a budget. |
| RT-2026-07-19-455 | Job-integrity reviewer | Adding worker IDs to claims is insufficient if progress, success, cancellation, or failure writes can still land after lease loss. | Critical | Resolved in complete fencing | Carry `(job_id, attempt, worker_id)` through the entire research execution path and predicate every mutable job write on all three values plus active status. Treat zero-row updates as lease loss, not success, and test stale-worker races. |
| RT-2026-07-19-456 | Cost-governance reviewer | Reserving maximum tokens per call can prevent overspend but strand budget on failures or sharply reduce useful concurrency. | High | Resolved in accounting contract | Atomically reserve the configured worst-case input/output allowance before dispatch, reconcile against actual usage in `finally`, and make reservation state observable. Never admit a call whose reservation exceeds the remaining issuer budget. Test simultaneous admissions at the boundary. |
| RT-2026-07-19-457 | Performance reviewer | Splitting the 351 KB command dataset can simply trade initial bundle weight for interaction stalls, duplicate chunks, or broken static export. | High | Resolved in interaction contract | Keep the small command index eager, load large route-specific payloads only when the launcher needs them, prefetch on launcher intent, and compare per-route raw/gzip output before and after. Preserve keyboard behavior and offline/static-export operation. |
| RT-2026-07-19-458 | Ingestion reviewer | Lowering the upload cap hides the memory problem and can break legitimate model documents; streaming alone does not help if downstream parsers duplicate the full payload. | Critical | Resolved in end-to-end memory boundary | Trace the complete upload-to-parser path, eliminate redundant byte copies or move parsing to file-backed inputs, and enforce a proxy/app cap with a calculated worst case below the container limit. If a parser cannot stream, constrain its concurrency explicitly and test the cap. |
| RT-2026-07-19-459 | Supply-chain reviewer | Digest-pinning an image without preserving its human-readable version or update automation can freeze security patches invisibly. | High | Resolved in maintenance contract | Pin tag-plus-digest from current official registry metadata, keep the version tag visible, update Dependabot coverage, and validate Compose resolution. Do not substitute a different major version during pinning. |
| RT-2026-07-19-460 | Change-integrity reviewer | “Fix all” across a dirty repository can absorb unrelated work or turn historical baseline debt into an unreviewable rewrite. | Critical | Resolved in workflow | Preserve the pre-existing modified tracker file, patch only audited findings, inspect path-specific diffs before each edit, and do not stage or commit. Report external/provider/runtime verification gaps as blocked rather than fabricating closure. |

### Critic reopen conditions (audit remediation)

Reopen if document egress becomes implicit; an unsafe cookie-authenticated request
can mutate state cross-origin; an unknown role can write; two production workers
receive separate login budgets; a stale research worker can update a reclaimed
job; admitted LLM work can exceed the hard issuer budget; route bundles do not
materially shrink or launcher interaction regresses; upload peak memory remains
unbounded relative to the container; an image tag is still mutable; or the
pre-existing quality-tracker modification is changed or attributed to this pass.

## 2026-07-19 — QA-flag tenancy critic pass

Decision under review: close the QA-flag cross-team read/write seam while
preserving the deliberately non-gating, durable audit-record contract.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-461 | Authorization reviewer | A caller can forge another team's `issuer_id` when creating a flag or enumerate that team's analyst notes through an unscoped list. | Critical | Resolved in interface | Validate supplied issuer IDs with the existing non-enumerable issuer guard before insert. Under tenancy, scope every flag-list query to visible issuer IDs and require explicit issuer filters to resolve through the same guard. |
| RT-2026-07-19-462 | Audit-integrity reviewer | Adding foreign keys or requiring a live run would destroy the existing guarantee that a flag survives deletion of its subject and never participates in the CP-5 export gate. | High | Resolved in bounded design | Keep `issuer_id`/`run_id` as nullable plain audit references and leave `qa_findings` untouched. Validate only a supplied live issuer at request time; preserve unbound historical flags in shared-desk mode. |
| RT-2026-07-19-463 | Frontend-context reviewer | Hiding ATLF inside a reusable QA control makes a future live caller silently count and write flags against the reference issuer. | High | Resolved in explicit contract | Make `issuerId` a required control prop. The two seeded reference callers pass the ATLF ID explicitly; no live page signature or evidence-resolution path changes. |

### Critic reopen conditions (QA-flag tenancy)

Reopen if a foreign issuer ID can be created or listed without a non-enumerable
404; an unfiltered tenancy-on list includes null/foreign issuer flags; the shared
control regains an implicit issuer default; or analyst flags begin gating runs or
committee exports.

## 2026-07-19 — Production-like E2E TLS critic pass

Decision under review: make the production-like browser lane prove the same
Secure-cookie boundary used by a deployed TLS edge.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-464 | Security-evidence reviewer | Accepting a plain-HTTP target under `ENVIRONMENT=production` splits Secure-cookie API contexts from browser fetches, so analyst-owned setup data and UI reads can resolve as different principals. A red or green result is therefore not valid production evidence. | Critical | Resolved in runner contract | Require a loopback HTTPS target before CSP preflight or Playwright starts. Keep self-signed local certificates supported through the existing `E2E_IGNORE_HTTPS_ERRORS=1` path. |
| RT-2026-07-19-465 | Test-operator reviewer | Silently relaxing the production cookie or turning off `Secure` for loopback would make the lane easier to run but stop testing the deployed session boundary. | High | Resolved by fail-fast behavior | Leave application cookie policy untouched. The runner rejects HTTP with an actionable TLS message; local orchestration must terminate TLS or use the real edge. |
| RT-2026-07-19-466 | CSRF reviewer | Once TLS makes the profile cookie active, direct Playwright API mutations can fail 403 or tempt an application-side test exemption because they omit the browser's double-submit header. | Critical | Resolved in fixture boundary | An authenticated E2E API fixture reads the project's fresh storage state, reuses its session and CSRF cookies, and sends the matching `X-CSRF-Token` plus same-origin `Origin`. The server guard receives no exemption or test flag. |

### Critic reopen conditions (production-like E2E TLS)

Reopen if the production-like runner accepts HTTP; production cookies are made
non-Secure for test convenience; or a cited production-like result bypasses the
TLS edge/session boundary. Also reopen if an authenticated E2E mutation bypasses
the signed double-submit contract or uses a hard-coded CSRF token.

## 2026-07-19 — Context-free Settings strip critic pass

Decision under review: settle the shared analysis-context strip on the Settings
utility route without changing the shared `EnterprisePage` interface or creating
a meaningless persisted analysis context.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-464 | Shared-shell reviewer | `EnterprisePage` is a CRITICAL hub with 21 direct consumers; adding a route-specific prop can regress 19 modules to fix one utility page. | Critical | Resolved in scope | Leave `EnterprisePage` unchanged. Confine the behavior to the LOW-risk `AnalysisContextStrip`, whose single direct caller remains untouched. |
| RT-2026-07-19-465 | Workflow-continuity reviewer | Treating every missing context as inactive could erase the reserved loading geometry and hide slow or failed context creation on analytical routes. | High | Resolved in exact route contract | Recognize only `/settings` without an explicit `context` query as context-free. Every analytical route retains the existing resolving, loaded, and unavailable states. |
| RT-2026-07-19-466 | Accessibility reviewer | Removing the busy strip can create layout shift or leave assistive technology with an unexplained gap in the shared shell. | Moderate | Resolved in settled status | Preserve the strip's existing geometry and render a neutral, non-busy `Workspace configuration · no analysis context` status on Settings. |

### Critic reopen conditions (context-free Settings strip)

Reopen if an analytical route can suppress its context state; a Settings URL
carrying an explicit context fails to load it; the shared shell geometry changes;
or `EnterprisePage` gains route-specific interface surface for this exception.

## 2026-07-19 — Whole-frontend Web Interface Guidelines critic pass

Decision under review: remediate deterministic Web Interface Guidelines faults
across every CAOS frontend route and shared component, then repeat static,
build, accessibility, and rendered-layout gates until no fault remains.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-467 | Analyst-density reviewer | Applying consumer-web defaults mechanically can enlarge controls, weaken terminal density, or turn specialist workbenches into generic forms. | Critical | Resolved in scope | Preserve all existing geometry and hierarchy. Limit this pass to semantic metadata, focus/touch/browser behavior, copy typography, and verified accessibility faults; rendered target-size checks remain the authority for layout. |
| RT-2026-07-19-468 | Report-integrity reviewer | Removing the report editor's paste cancellation can reintroduce rich markup or oversized clipboard payloads into committee-ready output. | Critical | Resolved in input contract | Permit the browser paste event, then normalize the editable leaf to capped plain text during `input`; retain the 2,000-character boundary and add a focused regression test proving paste is not cancelled and markup is removed. |
| RT-2026-07-19-469 | Shared-flow reviewer | Native `name`/`autocomplete` and placeholder changes touch HIGH-risk auth, profile, QA, and filter components even though the intended behavior is cosmetic. | High | Resolved in isolation | Add only stable field identifiers, correct browser autocomplete tokens, accessible names, and typographic ellipses. Do not alter state, submit handlers, URL state, focus order, API payloads, or component props; run focused tests for every HIGH-risk surface. |
| RT-2026-07-19-470 | Accessibility reviewer | Static regex findings can be false positives for implicit labels, compound focus rings, ARIA grids, and modal backdrops, creating churn while real rendered defects remain hidden. | High | Resolved in evidence hierarchy | Fix only deterministic source violations, use the repository's actual axe runner with best-practice tags, and require clean desktop and phone route matrices. Keep implicit native labels and intentional grid patterns when axe and keyboard contracts validate them. |
| RT-2026-07-19-471 | Change-integrity reviewer | The worktree already contains unrelated frontend and audit WIP, so a whole-codebase loop can overwrite or absorb another task's changes. | Critical | Resolved in workflow | Preserve every pre-existing dirty hunk, use additive or line-local patches, inspect path-specific diffs, and do not stage or commit. Treat the untracked browser-health harness as user-owned unless an isolated change is required and verified. |

### Critic reopen conditions (whole-frontend guidelines)

Reopen if row/control geometry changes; report paste can retain markup or exceed
its cap; auth/filter/API behavior changes; static findings are accepted without
rendered evidence; any route develops an axe, clipping, target-size, overflow,
console, or build fault; or pre-existing WIP is replaced or attributed to this
pass.

## 2026-07-19 — Closed Ask result-renderer split critic pass

Decision under review: remove graph-rendering code from every route's initial
authenticated shell while keeping the global Ask launcher and query controls
immediately available.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-472 | Interaction reviewer | Deferring the whole Ask surface would improve page LCP by moving the delay onto the analyst's first Alt+K or launcher interaction. | High | Resolved in boundary | Keep `AskProvider`, `AskLauncher`, issuer chat, modal controls, and capability routing eager. Defer only the four result renderers, which cannot be needed before a query returns. |
| RT-2026-07-19-473 | Performance reviewer | Four lazy imports can add duplicate chunks or delay the first result on a constrained connection. | High | Resolved in intent prefetch | Reuse one loader per renderer and start all four imports when Ask opens or receives pointer/focus intent. Compare production route JavaScript and constrained-mobile LCP before and after. |
| RT-2026-07-19-474 | Accessibility reviewer | A slow renderer import could leave the result region blank or produce an unannounced layout jump. | High | Resolved in fallback contract | Give every deferred renderer the same visible `role=status`, `aria-live=polite` result-loading surface with reserved minimum height; repeat axe and rendered-layout checks. |
| RT-2026-07-19-475 | Static-export reviewer | A client-only split can compile in development but omit chunks or fail under the exported production artifact. | High | Resolved in verification gate | Require a clean static production build, exercise the Ask graph/RV/scatter/lineage paths in focused tests, and rerun the production performance harness against `out/`. |

### Critic reopen conditions (closed Ask result-renderer split)

Reopen if opening Ask itself waits on a visualization chunk; a result renderer
is unavailable offline after the initial application load; any Ask keyboard,
focus, citation, or pinning contract regresses; the exported artifact omits a
renderer chunk; or initial-route JavaScript and constrained-mobile LCP do not
materially improve.

## 2026-07-19 — Mobile async-geometry stabilization critic pass

Decision under review: reserve the final geometry of four asynchronous mobile
surfaces that exceed the 0.1 CLS threshold, without changing their data,
interaction, or responsive contracts.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-476 | Shared-shell reviewer | `WorkbenchToolbar` is CRITICAL (14 impacted symbols across seven modules); changing its markup or interface to fix two title rows can regress unrelated worklists. | Critical | Resolved in route scope | Leave the component untouched. Reserve the observed two-line title geometry only beneath `.issuers-workbench` and `.sponsors-workbench` at phone widths. |
| RT-2026-07-19-477 | Decision-contract reviewer | `DecisionHeader` is CRITICAL (26 impacted symbols across nine modules); globally expanding repeated loading cells would add noise and reduce density. | Critical | Resolved in route scope | Leave its logic and accessibility tree untouched. Reserve the measured four-cell height only for Monitor's single-child loading grid; ready/offline/error states keep natural geometry. |
| RT-2026-07-19-478 | Analytical-density reviewer | Giving every finalization bar the Sector phone height would waste scarce viewport space on routes whose actions fit one line. | High | Resolved in route scope | Use the existing `.sector-workbench` ownership marker to reserve 78px only for Sector Review's wrapping three-action finalization bar. |
| RT-2026-07-19-479 | Lazy-loading reviewer | A generic Deep-Dive spinner is 134px shorter than the scenario panel and shifts the complete evidence workspace when its chunk arrives. | High | Resolved in component-specific fallback | Keep all other tab fallbacks unchanged. Give only the low-risk Scenario Network loader the measured 153px phone / 127px desktop content height. |
| RT-2026-07-19-480 | Verification reviewer | Hard-coded reserves can merely move the shift, clip translated copy, or conceal a changed natural height. | High | Resolved in measurement gate | Values come from final rendered bounding boxes. Repeat focused CLS traces first, then the full phone/desktop matrix, axe, clipping, overflow, and target checks; reopen on any mismatch. |

### Critic reopen conditions (mobile async geometry)

Reopen if a shared component interface or state contract changes; any reserve
clips content; Monitor's loading and settled decision regions differ in height;
the issuer/sponsor title row or Sector actions outgrow the reserve; Deep-Dive's
lazy replacement changes height; or any final route remains above 0.1 CLS.

## 2026-07-19 — Source-link protocol boundary critic pass

Decision under review: harden the shared `SourceRef` link sink against persisted
active-content URLs without changing evidence actions or valid source routes.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-476 | Evidence-integrity reviewer | Rewriting a rejected URL to a generic destination would make an unavailable source look verified and clickable. | High | Resolved in fail-closed state | Preserve valid relative and absolute HTTP(S) destinations exactly. Render the existing explicit `Source unavailable` state for every rejected destination; never substitute or normalize it into a different source. |
| RT-2026-07-19-477 | Browser-security reviewer | A scheme prefix check can miss whitespace, mixed-case, protocol-relative, credential-bearing, or escaped active-content URLs. | Critical | Resolved in parsed allowlist | Reject control/whitespace characters and protocol-relative URLs, parse against a fixed local base, allow only relative application routes or absolute `http:`/`https:` URLs, and reject credentials. Cover each bypass class in the component test. |
| RT-2026-07-19-478 | Shared-component reviewer | `SourceRef` is HIGH risk: seven direct consumers span Sector, Portfolio, Profile, and Monitor, and a broad contract change could disable local evidence actions. | High | Resolved in narrow branch | Leave `onOpen` actions and the public prop union unchanged. Apply validation only inside the `href` branch and rerun the direct component plus sector caller tests. |

### Critic reopen conditions (source-link protocol boundary)

Reopen if an active-content or protocol-relative URL renders as a link; valid
relative or HTTP(S) evidence links change destination; an `onOpen` source loses
its action; or the sector source-register caller no longer renders honest source
availability.

## 2026-07-19 — EDGAR redirect SSRF critic pass

Decision under review: enforce the SEC network allowlist before the initial EDGAR
request and before each redirect rather than checking only the final response URL.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-479 | SSRF reviewer | A final-response host check detects an off-SEC redirect only after `urllib` has already made the external/internal request. | Critical | Resolved at dispatch boundary | Validate the initial URL before constructing the request and install a redirect handler that validates each resolved target before `urllib` follows it. Retain the final response check as defense in depth. |
| RT-2026-07-19-480 | EDGAR-availability reviewer | Disabling redirects entirely can break legitimate SEC canonicalization and subdomain routing. | High | Resolved in exact allowlist | Permit redirects only to HTTPS `sec.gov` or its subdomains on the default HTTPS port; reject credentials, non-HTTPS schemes, malformed ports, and all other hosts. |
| RT-2026-07-19-481 | Change-integrity reviewer | `_http_get` is HIGH risk with four direct callers and 17 affected symbols; replacing the HTTP stack could regress throttling, fair-access identity, caps, or error translation. | High | Resolved in narrow transport seam | Keep `urllib`, request headers, throttle, timeout, bounded reads, and exception mapping unchanged. Add only the validating redirect handler and focused pre-dispatch tests, then run the complete EDGAR suite. |

### Critic reopen conditions (EDGAR redirect SSRF)

Reopen if any non-HTTPS, credential-bearing, non-SEC, or non-default-port URL can
reach the transport; an off-allowlist redirect is followed before rejection; a
legitimate SEC subdomain redirect is blocked; or EDGAR caps/fair-access behavior
regresses.

## 2026-07-19 — Registration credential-boundary critic pass

Decision under review: raise the self-registration passcode floor to the OWASP
ASVS-aligned 12 characters and bound each recovery credential before hashing.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-482 | Authentication reviewer | Applying the new minimum to login would strand existing accounts whose stored credential predates the policy. | Critical | Resolved at creation boundary | Enforce 12 characters only in `RegisterRequest`; retain the bounded 1–128 login input contract so existing hashes can authenticate and users are not locked out. |
| RT-2026-07-19-483 | Availability reviewer | Capping only the recovery-word list length still lets three near-request-sized strings reach repeated PBKDF2 work. | High | Resolved in element schema | Bound each recovery word to 1–80 characters and each optional hint to 160 characters in both registration and recovery request schemas, matching the existing browser controls. |
| RT-2026-07-19-484 | Shared-flow reviewer | The login form is CRITICAL because every protected route depends on it; backend-only enforcement would leave misleading UI readiness and copy. | Critical | Resolved in contract parity | Change only sign-up readiness, explanatory copy, and the short-passcode message to 12; keep sign-in and recovery behavior unchanged. Run the focused UI and complete auth suites. |
| RT-2026-07-19-485 | Password-policy reviewer | Composition rules or forced character classes can reduce usability and conflict with password-manager-generated credentials. | High | Resolved in length-only policy | Keep the 128-character maximum, permit spaces and Unicode, and add no character-class rules. Continue using the existing salted PBKDF2 verifier and constant-work failure path. |

### Critic reopen conditions (registration credential boundary)

Reopen if login rejects a valid legacy credential solely for being under 12
characters; registration accepts fewer than 12; any recovery word or hint is
unbounded at the API; or browser readiness/copy diverges from server validation.

## 2026-07-19 — Pre-parse request-body boundary critic pass

Decision under review: enforce content-type-aware request limits in ASGI before
FastAPI parses a body, while retaining the configured large-document upload lane.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-486 | Availability reviewer | Route validators and rate limits run only after FastAPI has buffered and decoded JSON, so an authenticated caller can repeatedly allocate near the 250 MiB upload ceiling before a 413 or 429. | Critical | Resolved before parsing | Install an ASGI receive boundary that rejects declared and chunked JSON bodies over 8 MiB before route parsing; keep existing route-specific persisted-payload limits as the narrower second gate. |
| RT-2026-07-19-487 | Document-ingestion reviewer | Applying the JSON ceiling globally would break legitimate PDF/XLSX multipart uploads up to the operator-configured `MAX_UPLOAD_MB`. | Critical | Resolved by media type | Use 8 MiB only for `application/json` and structured `+json`; all other request bodies retain the configured upload ceiling and existing upload semaphore, incremental read, malware scan, and parser limits. |
| RT-2026-07-19-488 | Protocol reviewer | A `Content-Length` check alone is bypassed by HTTP/1.1 chunked transfer or an HTTP/2 body without that header. | High | Resolved in receive stream | Reject an oversized declared length immediately, then wrap ASGI `receive` and count actual `http.request` bytes so undeclared/chunked bodies fail at the same boundary. |
| RT-2026-07-19-489 | Shared-boundary reviewer | The FastAPI application is a cross-cutting surface; a middleware error can strip security headers, suppress access telemetry, or interfere with WebSockets/lifespan. | Critical | Resolved in ordering and scope | Register the limiter as the innermost user middleware, leave non-HTTP scopes untouched, and retain the existing edge/auth, CSRF, access-log, and security-header wrappers. Verify declared, chunked, JSON, non-JSON, exact-limit, and non-HTTP cases independently. |

### Critic reopen conditions (pre-parse request-body boundary)

Reopen if JSON over 8 MiB reaches a handler or parser; chunked transfer bypasses
the limit; a valid configured-size multipart upload is rejected; an oversized
response lacks the normal API security headers/access record; or a non-HTTP ASGI
scope changes behavior.

## 2026-07-19 — Persisted analyst-state size critic pass

Decision under review: cap the remaining analyst-authored arbitrary JSON maps at
their domain write boundaries, after merge semantics but before database flush.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-490 | Storage-availability reviewer | The 8 MiB transport cap prevents a single extreme allocation but still permits repeated multi-megabyte context, finding, and RV rows that are replayed on reads and can grow Postgres without a domain quota. | Critical | Resolved at persistence seam | Bound combined context navigation state to 100 KiB, finding evidence to 250 KiB, and RV filter state to 32 KiB before the first flush; retain the shared 45/min and RV write rate gates. |
| RT-2026-07-19-491 | State-merge reviewer | Validating only an incoming context patch lets a caller accumulate an oversized record through many individually small merges. | High | Resolved after merge | Calculate the cap against the final `surface_state` + legacy `filters` + `selected` values after existing patch merge semantics and before assigning/flushing them. |
| RT-2026-07-19-492 | Evidence reviewer | A cap that is too small could reject legitimate citation bundles and destroy committee traceability. | High | Resolved with proportional headroom | Give finding evidence 250 KiB—well above identifiers/citations but far below a document—and reject with 413 without truncation, so evidence is never silently altered. |
| RT-2026-07-19-493 | Data-integrity reviewer | Python JSON serialization can persist `NaN`/infinity even though they are not interoperable JSON and can poison downstream numerical reads. | High | Resolved in strict serializer | Measure canonical UTF-8 JSON with `allow_nan=False`; return 422 for non-JSON/non-finite values and 413 only for a valid value beyond its domain ceiling. |

### Critic reopen conditions (persisted analyst-state size)

Reopen if incremental patches can exceed a record cap; legitimate citation or
navigation state approaches a ceiling in observed use; any value is truncated;
non-finite numbers persist; or a rejected write partially mutates a row.

## 2026-07-19 — Route-schema resource-bound critic pass

Decision under review: close the remaining mutation-schema gaps with maxima
aligned to database columns/vocabularies and bound legacy decision capture.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-494 | Decision-integrity reviewer | Legacy direct decision capture accepts an arbitrary client snapshot and has no per-caller write budget, allowing repeated large immutable rows even after the transport ceiling. | Critical | Resolved at decision boundary | Require write capability first, apply a 20/min caller budget, and reject client snapshot JSON over 250 KiB or containing non-finite values before loading the run or assembling the authoritative snapshot. |
| RT-2026-07-19-495 | Compatibility reviewer | Bounding fields more tightly than their persisted columns or closed vocabularies could reject valid existing clients. | High | Resolved by existing contracts | Match issuer/run/decision identifiers to their 36-character columns, EDGAR document fields to 64/512/16-character columns, URLs to 2,048, and already-anchored lane/mode vocabularies to their longest legal value. Do not alter accepted in-range values. |
| RT-2026-07-19-496 | Parser-cost reviewer | An anchored regex without `max_length` can still scan an 8 MiB string before rejecting it. | High | Resolved before regex work | Add explicit maxima to research-report mode and query lane fields so Pydantic rejects pathological strings at the schema boundary before downstream work. |
| RT-2026-07-19-497 | Sector-workflow reviewer | A broad schema rewrite could alter date parsing, canonical sector resolution, or signal lookup behavior. | High | Resolved as length-only validation | Add only length constraints to sector/timeframe/as-of/signal identifiers; preserve `_parse_dt`, canonical taxonomy, response shapes, and all valid defaults. |
| RT-2026-07-19-498 | Evidence-preservation reviewer | Silently truncating decision conditions or EDGAR metadata would make committee/audit records misleading. | Critical | Resolved fail closed | Reject over-limit values with normal validation or 413; never trim except where the existing handler already intentionally strips whitespace after validation. |

### Critic reopen conditions (route-schema resource bounds)

Reopen if a legal in-range request regresses; a decision snapshot over 250 KiB
or non-finite JSON persists; more than 20 direct decisions per caller/minute are
accepted; EDGAR metadata exceeds its database column; or any input is truncated.

## 2026-07-19 — Request-target size critic pass

Decision under review: reject an excessive raw URI path plus query string at the
same innermost ASGI boundary as body limits, before routing or query parsing.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-499 | Availability reviewer | Caddy/HTTP-server header allowances are much larger than any CAOS route needs, so a caller can force repeated parsing/routing of very large query strings before route-specific rate limits execute. | High | Resolved before routing | Reject `raw_path` + `query_string` over 16 KiB with 414 in the ASGI middleware before calling FastAPI. |
| RT-2026-07-19-500 | Compatibility reviewer | A global URI ceiling could break dense filter links or signed pagination cursors. | High | Resolved with headroom | The largest current cursor/filter requests are orders of magnitude below 16 KiB; count raw bytes, permit the exact boundary, and add focused path/query tests. |
| RT-2026-07-19-501 | Middleware reviewer | Expanding a body limiter into a target limiter may accidentally consume the request stream or affect non-HTTP scopes. | Critical | Resolved as independent early branch | Inspect only HTTP scope bytes, do not call `receive` on a 414, and preserve the existing non-HTTP passthrough plus outer telemetry/security-header ordering. |

### Critic reopen conditions (request-target size)

Reopen if an over-limit target reaches a route; an exact-limit target is rejected;
the 414 body is consumed first; security headers/access logging disappear; or a
real CAOS workflow approaches the 16 KiB ceiling.

## 2026-07-19 — Collection-item bound critic pass

Decision under review: complement existing list-count ceilings with per-string
maxima on analyst-authored collections that are persisted or used in DB lookups.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-502 | Storage reviewer | A list capped at 50/500/1,000 elements can still approach the full transport ceiling when each string is unbounded, producing oversized JSON rows and expensive `IN` predicates. | High | Resolved per item | Bound context subject identifiers to 36, sub-segments/sectors to 128, committee/opinion prose items to 2,000, and persisted link/watchlist identifiers to 36 characters. |
| RT-2026-07-19-503 | Compatibility reviewer | Adding minimum lengths or stricter vocabularies would change existing cleanup semantics for blank list items. | High | Resolved as maxima only | Add only `max_length` to item types; retain existing blank filtering, deduplication, canonicalization, and downstream ownership checks. |
| RT-2026-07-19-504 | Shared-model reviewer | Context and Query models are MEDIUM blast radius (19 and 30 impacted symbols respectively), so a nested type change could alter valid payload serialization. | High | Resolved with focused schema tests | Keep container types and response models unchanged, constrain only inbound item validation, and run the full Analysis/Query/committee/opinion/sector route suites. |

### Critic reopen conditions (collection-item bounds)

Reopen if a valid existing identifier/prose item is rejected; output serialization
changes; blank-item cleanup changes; oversized list members reach a handler; or
context/query/committee/opinion workflows regress.

## 2026-07-19 — Expensive and append-only action rate critic pass

Decision under review: add worker-shared per-caller budgets to the remaining
append-only governance writes and CPU-heavy report rendering endpoints.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-505 | Resource-abuse reviewer | Authenticated analysts can append committee agendas, opinion versions, or thesis versions without a request budget, growing storage and forcing lock/validation work. | High | Resolved before DB work | Apply 60 writes/min to committee authoring and 30/min independently to opinions and direct thesis creation, keyed by verified caller ID in the worker-shared limiter. |
| RT-2026-07-19-506 | CPU reviewer | Report-version XLSX/PDF rendering and run committee-report assembly can be repeated without a budget even though export generation is materially more expensive than a read. | High | Resolved before lookup/render | Apply 10 exports/min to immutable report versions and the existing 12/min run budget to committee-report assembly before DB/export work. |
| RT-2026-07-19-507 | Workflow reviewer | Rate-limiting the shared `create_thesis_version` helper would double-charge decision/finalization flows or make an atomic committee action fail after its parent gate. | Critical | Resolved at public route only | Gate only the public `create_thesis` handler; internally appended thesis versions remain governed by their decision/committee parent action. |
| RT-2026-07-19-508 | Authorization reviewer | Consuming a budget before role validation could let an unauthorized request receive 429 instead of the required 403. | High | Resolved after capability check | Committee’s guard checks `_require_committee_write` first, then consumes the rate budget. Other handlers already use `get_write_identity`; export routes require authenticated identity. |
| RT-2026-07-19-509 | Availability reviewer | A budget too low could block normal multi-item IC preparation or retries after a validation error. | High | Resolved with lane separation/headroom | Use separate caller buckets per domain and intentionally generous interactive ceilings; validation failures consume capacity to prevent malicious invalid-request work from bypassing the budget. |

### Critic reopen conditions (expensive and append-only action rates)

Reopen if unauthorized callers see 429 before 403; one lane exhausts another;
internal decision/finalization thesis creation is double-charged; normal IC/export
work approaches a ceiling; or invalid requests can bypass budget consumption.

## 2026-07-19 — Cookie/CSRF cryptographic-input bound critic pass

Decision under review: reject oversized attacker-controlled session and CSRF
values before HMAC/base64 work without changing minted token formats.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-510 | Authentication reviewer | `read_session_token` is CRITICAL (168 impacted symbols, 61 flows); an overly tight or malformed check could log every analyst out. | Critical | Resolved with format headroom | Accept the existing token format unchanged and reject only non-string/over-4-KiB inputs, many times larger than a minted profile token. Run the complete auth, CSRF, role, tenancy, and protected-route suites. |
| RT-2026-07-19-511 | Availability reviewer | A caller-controlled megabyte-scale cookie/header reaches HMAC and base64 parsing before rejection, creating linear CPU/allocation work per authenticated request. | High | Resolved before crypto | Check session token length before split/HMAC/decode and CSRF signed/cookie/header lengths before `compare_digest`. |
| RT-2026-07-19-512 | CSRF reviewer | Returning a distinct error for an oversized token could create a browser oracle or diverge from ordinary tamper handling. | High | Resolved as invalid credential | Return the existing generic invalid-session fallthrough and `Invalid CSRF token` response; expose neither the configured ceiling nor which value was oversized. |
| RT-2026-07-19-513 | Unicode reviewer | Character limits can understate encoded byte work for non-ASCII attacker input. | High | Resolved with byte ceilings | Measure UTF-8 bytes using the same error-tolerant encoding mode used by HMAC comparison, rejecting encoded values above the ceiling. |

### Critic reopen conditions (cookie/CSRF cryptographic inputs)

Reopen if a server-minted session/CSRF pair is rejected; over-limit values reach
HMAC/base64; errors reveal which credential differed; Unicode bypasses the byte
ceiling; or any protected-route authentication/role/tenancy test regresses.

## 2026-07-19 — QA flag subject-coherence critic pass

Decision under review: close the remaining relationship-level bypass between an
analyst QA flag's optional issuer and run subjects while preserving historical
audit rows after their subject is deleted.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-490 | Tenancy reviewer | Validating only `issuer_id` still lets a caller attach a flag to an existing foreign `run_id` by omitting the issuer. | Critical | Resolved at current-subject boundary | When the run exists, require normal run access before insertion and derive the persisted issuer from that run. Cross-team and cross-analyst foreign runs remain non-enumerable 404s. |
| RT-2026-07-19-491 | Evidence-integrity reviewer | Independently supplied issuer and run identifiers can produce a contradictory audit record even when both objects are individually accessible. | High | Resolved by coherence check | Reject an existing run paired with a different issuer as 422; otherwise persist the run's canonical issuer. |
| RT-2026-07-19-492 | Audit-retention reviewer | Requiring every referenced run to exist would break the table's deliberate no-FK contract and prevent an analyst from recording a flag against a deleted historical subject. | High | Resolved by existence-aware validation | Preserve unknown/deleted run identifiers as historical audit references. Apply access and coherence checks whenever the referenced run still exists. |

### Critic reopen conditions (QA flag subject coherence)

Reopen if a caller can flag an existing inaccessible run; an existing run can be
stored with the wrong issuer; deriving a current run's issuer loses visibility;
or a deleted historical run can no longer be referenced in an audit flag.

## 2026-07-19 — MoreDrawer fallback-focus critic pass

Decision under review: make the shared non-modal utility drawer's documented
focus fallback real without changing its trigger, portal, or scroll behavior.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-493 | Accessibility reviewer | The empty/read-only drawer calls `.focus()` on a plain `div`, so focus remains behind the open dialog and keyboard context is lost. | High | Resolved at focus target | Give the dialog `tabIndex=-1`; it becomes programmatically focusable without entering the normal Tab order. Assert the settled active element in the existing read-only contract. |
| RT-2026-07-19-494 | Shared-shell reviewer | `MoreDrawer` has CRITICAL blast radius across three execution flows and eight modules; changing close, portal, or trigger semantics could regress unrelated workbenches. | Critical | Resolved by one-attribute patch | Leave effects, public props, geometry, focus trap, and dismissal logic untouched. Add only the native focus target and rerun direct component, SubHeader, ConceptNav, shell, Issuers, Profile, and Upload coverage. |

### Critic reopen conditions (MoreDrawer fallback focus)

Reopen if a drawer without child controls leaves focus outside its dialog; the
dialog becomes an ordinary Tab stop; or any trigger, portal, geometry, scroll,
outside-pointer, Escape, or focus-cycle contract changes.

## 2026-07-19 — Sponsors mobile register-geometry critic pass

Decision under review: give the asynchronously populated Sponsors register a
fixed phone-height viewport so its record pane does not move when loading settles.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-490 | Credit-workflow reviewer | A fixed register height could hide covered sponsors and make a partial list look complete. | High | Resolved in scroll contract | Fix only the outer phone-height at the measured 215px settled-state geometry. `PanelBody` retains overflow detection, keyboard focus, its panel-title accessible label, and scrolling for every additional row. |
| RT-2026-07-19-491 | Responsive-layout reviewer | Applying the constraint at desktop widths would shrink the primary selector and waste the independent-height split-pane layout. | High | Resolved in route scope | Target a new `.sponsor-register-panel` ownership class only inside the existing max-767px breakpoint; desktop keeps its current `md:w-80` natural/flex height. |
| RT-2026-07-19-492 | Verification reviewer | The measured offline state may be taller than a populated list but shorter than future copy or browser font geometry. | High | Resolved in rendered gates | Re-run constrained production CLS, axe, focusability, clipping, and horizontal-overflow checks. Reopen if the body is not keyboard-scrollable when clipped or the phone panel itself exceeds the reserve. |

### Critic reopen conditions (Sponsors mobile register geometry)

Reopen if any sponsor row is unreachable by keyboard; the panel loses its
accessible scroll-region label; desktop register sizing changes; translated or
updated state copy clips outside the scroll body; or Sponsors remains above 0.1 CLS.

## 2026-07-19 — Command/Monitor initial-graph critic pass

Decision under review: separate the Monitor replay stream from the legacy
portfolio view module and defer selection-only governance/detail surfaces so
unrelated authored datasets do not block first paint.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-493 | Governance-contract reviewer | `GovernancePanel` is HIGH risk: four direct consumers and eight affected symbols span Command, Monitor, and Model. A lazy boundary could alter QA defaults or lose the selected dataset. | High | Resolved without contract change | Keep the component, props, call sites, and dataset resolution unchanged. Defer only its module evaluation on Command/Monitor and render an accessible, geometry-reserved loading status while the selected Governance dataset resolves. |
| RT-2026-07-19-494 | Evidence-workflow reviewer | Moving the alert/email stream could break the one-click source-email link, modal focus cycle, replay order, or severity filtering. | High | Resolved by verbatim extraction | Move `EmailWindow`, `EmailIntel`, and `AlertFeed` together with their existing data and accessibility dependencies; retain a compatibility re-export and run their interaction suite plus rendered axe. |
| RT-2026-07-19-495 | Data-integrity reviewer | Splitting the portfolio and monitor fixtures can create two editable sources whose counts, source indexes, or QA rows drift. | High | Resolved in single ownership | Move, rather than copy, the complete monitor/governance tail into one module and re-export its public contract from the legacy path. Direct runtime imports use the narrow owner; compatibility callers see the same values. |
| RT-2026-07-19-496 | First-interaction reviewer | Deferring the issuer detail strip can make a selected row appear inert on a slow link. | High | Resolved in selected-only fallback | The strip is never present before a live row is selected. Keep selection immediate and expose a visible `role=status` strip-height fallback until the unchanged detail component arrives. |
| RT-2026-07-19-497 | Performance reviewer | A module split can look cleaner in analysis but fail to reduce transferred JavaScript or LCP. | High | Resolved in measured gate | Compare cold constrained-mobile resource graphs and three-run route p75 values before/after. Revert or reopen if Command/Monitor bytes and LCP do not materially improve. |

### Critic reopen conditions (Command/Monitor initial graph)

Reopen if any Governance dataset, replay row, source email, issuer detail,
keyboard/focus contract, or compatibility import changes; if a deferred fallback
collapses geometry; or if the measured initial graph and LCP do not improve.

## 2026-07-19 — Pipeline evidence-modal startup critic pass

Decision under review: remove report construction and evidence-modal code from
Pipeline's initial route graph while preserving its one-click evidence workflow.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-498 | Evidence-integrity reviewer | Deferring the modal could change which report/evidence rows resolve for a selected `E-xx` identifier. | High | Resolved in isolated wrapper | Keep `EvidenceModal`, `buildReports()`, live mode, and selected identifier unchanged; move them together behind a selection-only module boundary and retain the same props. |
| RT-2026-07-19-499 | Accessibility reviewer | On a slow connection, activating evidence could leave no focusable dialog or announced feedback while the chunk loads. | High | Resolved with modal-state feedback | Render an immediate visible `role=status` overlay describing the pending evidence record until the unchanged dialog mounts; verify the loaded modal's focus and Escape contracts. |
| RT-2026-07-19-500 | Performance reviewer | A source split without an actual dynamic boundary would leave report builders on the startup graph and provide no LCP benefit. | High | Resolved in measured gate | Use a route-level dynamic import, confirm the builder/modal chunks are absent before activation, and compare three constrained-mobile Pipeline runs before and after. |
| RT-2026-07-19-501 | Shared-evidence reviewer | `EvChip` is CRITICAL risk: 11 direct consumers and 34 affected symbols span five modules, so a behavior rewrite could break cross-pane source synchronization far beyond Pipeline. | Critical | Resolved as exact move | Move the existing implementation byte-for-byte to a narrow module, compatibility re-export it from `EvidenceModal`, and repoint runtime consumers without changing props, markup, event order, or styling. Run the direct sync contract and affected surface suites. |

### Critic reopen conditions (Pipeline evidence modal)

Reopen if evidence identifiers resolve differently; live/reference badges drift;
activation has no announced loading state; dialog focus/Escape regresses; or the
report builder remains on Pipeline's pre-activation resource graph.

## 2026-07-19 — Report Studio below-fold/dialog startup critic pass

Decision under review: contain offscreen document sections and remove two
closed-by-default dialogs from Report Studio's constrained-mobile startup path.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-502 | Committee-output reviewer | Layout containment could alter the print/PDF document, hide report sections, or change the filed paper geometry. | Critical | Resolved in screen-only scope | Apply `content-visibility` only under `@media screen`; retain every DOM section, all print rules, and the measured 1,928px rendered paper height. Re-run paper geometry, print tests, and scroll-to-tail inspection. |
| RT-2026-07-19-503 | Layout-stability reviewer | A guessed intrinsic block size could shift the paper as lower sections become visible. | High | Resolved with browser-retained sizing and measured gate | Use `contain-intrinsic-size: auto 180px`, which lets Chromium retain each section's real size after layout; require unchanged cold-load CLS and verify progressive scroll geometry before/after. |
| RT-2026-07-19-504 | Evidence/decision reviewer | Deferring `EvidenceModal` or `DecisionRoomDrawer` could break exact evidence resolution, live-run decision eligibility, focus, or Escape handling. | Critical | Resolved at module boundary only | Keep both implementations, state gates, and props unchanged. Add immediate announced overlays while their modules load, then run Report Studio evidence and decision interaction contracts plus rendered axe. |
| RT-2026-07-19-505 | Performance reviewer | Containment alone measured only 160–168ms better and remained borderline; lazy imports can still be prefetched or accidentally retained through another import. | High | Resolved in production resource gate | Combine both safe mechanisms, inspect the production chunk graph before activation, and accept only if three cold constrained-mobile runs place p75 LCP below 2.5s without CLS or interaction regressions. |
| RT-2026-07-19-506 | Preference-hydration reviewer | Hiding the whole paper until a passive effect reads zoom delays LCP; simply showing the default first could flash or shift for analysts with a remembered zoom. | High | Rejected after production measurement | A normal production build showed no LCP improvement (2.648s p75); the earlier injected-response A/B had bypassed part of the throttled document path. Reinstate the visibility gate so remembered zoom never flashes at the wrong geometry. |
| RT-2026-07-19-507 | Document-completeness reviewer | Creating only the visible report lead first could transiently omit evidence, sources, or financial tables and accidentally leak into print/export. | Critical | Resolved in preview-only staging | Stage only the interactive screen preview's first four top-level sections for one painted frame, mark it `aria-busy`, then render the exact full report object. `ComposePanel`, publish payloads, downloads, and the independent `PrintPortal` always receive the complete report. Verify the tail and source register after staged settlement. |
| RT-2026-07-19-508 | Deliverable-routing reviewer | Avoiding construction of all six reference deliverables on the first frame could show the wrong report for a deep link or make later rail items differ from the canonical builders. | Critical | Resolved with canonical single-report dispatch | Add a single-report dispatcher that invokes the same private builder functions and model inputs as `buildReports`; assert every dispatched report deep-equals its canonical list counterpart. Seed the first frame from the requested report ID, then replace it with the full canonical list before the preview settles. |

### Critic reopen conditions (Report Studio startup)

Reopen if any paper section is missing or unreachable; screen and print output
diverge semantically; paper height or CLS regresses; evidence/decision focus or
eligibility changes; or measured p75 LCP remains above 2.5 seconds.

## 2026-07-19 — Report reference/live authority critic pass

Decision under review: require an accepted CP-1 model anchor—not merely a run
identifier—before labelling reference-report figures as live-run backed.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-509 | Provenance reviewer | A completed run with missing, blocked, synthetic, or malformed CP-1 leaves `eng.anchor=null`/`eng.live=false`; using only `eng.runId` falsely says fixture figures reflect that run. | Critical | Resolved at authority predicate | Gate the mixed-reference disclosure and `liveRunBacked` authority on `eng.live`, which is already the canonical accepted-anchor predicate. |
| RT-2026-07-19-510 | Freshness reviewer | Binding a rejected run's freshness to static fallback figures makes a current run badge appear to validate numbers that did not come from that run. | Critical | Resolved by reference target guard | For the reference path, pass a run freshness target only when `eng.live`; keep non-reference and immutable-version target resolution unchanged. |
| RT-2026-07-19-511 | Publication reviewer | Tightening the draft reference predicate could accidentally strip authority from immutable published versions or live non-reference reports. | High | Resolved by narrow branch | Preserve selected-version authority precedence and the entire non-reference route; change only the unfrozen reference fallback predicate. Run the caveat, frozen-preview, publication, and rendered authority suites. |

### Critic reopen conditions (report authority)

Reopen if a rejected CP-1 anchor is labelled live-backed or current; an accepted
anchor loses its mixed-reference disclosure; or published/non-reference report
authority, freshness, or publication eligibility changes.

## 2026-07-19 — Production credential-strength boot-gate critic pass

Decision under review: make deployed startup reject structurally weak session,
edge-proof, and analyst-signup secrets in addition to the known public defaults.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-514 | Authentication reviewer | A one-character `SESSION_SECRET` passes the current deny-list and makes every analyst cookie cheaply forgeable. | Critical | Resolve at startup | Require at least 32 UTF-8 bytes for session signing material before the server accepts traffic. |
| RT-2026-07-19-515 | Edge-trust reviewer | A short `EDGE_PROXY_SECRET` preserves the appearance of a trusted proxy proof while remaining guessable by any process able to reach the internal app network. | Critical | Resolve at startup | Apply the same 32-byte minimum to the edge credential and keep constant-time request comparison unchanged. |
| RT-2026-07-19-516 | Registration reviewer | The signup gate is an online credential, but requiring 32 bytes would break valid high-entropy invite formats and existing operator workflows. | High | Resolve with proportionate floor | Require at least 16 UTF-8 bytes for the signup code, retain the existing public-placeholder deny-list, and keep the shared source/global attempt budgets. |
| RT-2026-07-19-517 | Unicode/config reviewer | Character counts can overstate entropy and silently accept fewer bytes than the stated policy; logging the value during failure would expose it. | High | Resolve on encoded length | Validate UTF-8 byte length, emit only the variable name and minimum, and never log or echo the configured value. |

### Critic reopen conditions (production credential strength)

Reopen if any deployed boot accepts a sub-minimum credential; development
defaults stop working locally; a valid 32-byte session/edge value or 16-byte
signup value is rejected; or a failure message reveals credential contents.

## 2026-07-19 — CSV leading-line-feed neutralization critic pass

Decision under review: treat a leading LF as spreadsheet-active input at the
shared CSV cell boundary, matching the existing tab/CR/formula-prefix policy.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-518 | Spreadsheet-security reviewer | A text cell beginning with LF followed by `=`, `+`, `-`, or `@` can cross a row/cell interpretation boundary without receiving the existing apostrophe neutralizer. | High | Resolve in shared encoder | Add LF to the anchored dangerous-prefix class so every CSV producer receives the same protection. |
| RT-2026-07-19-519 | Data-fidelity reviewer | Prefixing every whitespace-leading value would mutate ordinary analyst-authored labels and create visible artifacts in non-spreadsheet consumers. | High | Resolve narrowly | Change only the omitted LF case; preserve ordinary spaces and all numeric handling. |
| RT-2026-07-19-520 | Regression reviewer | `csvCell` feeds issuer and Query exports; a quoting-order change could emit invalid multiline CSV. | High | Resolve with exact output tests | Keep neutralization before RFC-style quoting, then assert LF-plus-formula output and existing quotes/newlines behavior. |

### Critic reopen conditions (CSV LF neutralization)

Reopen if a leading LF is not apostrophe-neutralized; embedded LF quoting becomes
invalid; numeric negatives are converted to text; or issuer/Query export tests fail.

## 2026-07-19 — Route-layer type-gate expansion critic pass

Decision under review: expand the existing Python 3.11 mypy gate from the
analytical engine alone to the engine and FastAPI route layer after bringing all
104 modules to a clean baseline.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-521 | API-correctness reviewer | Leaving routes outside the gate permits nullable database rows and unconstrained persisted strings to drift back into response models, recreating the 121 faults found in this review. | High | Resolved in gate scope | Add `routes` to the existing configured file set and retain the same Python 3.11/mypy 2.1.0 CI leg that verified the clean baseline. |
| RT-2026-07-19-522 | Signal-quality reviewer | SQLAlchemy typing gaps can create noisy false positives that encourage blanket ignores and reduce trust in the gate. | High | Resolved without blanket suppression | Fix every current route diagnostic through explicit row names, validated Literal casts, and nullable guards; add no route-wide ignore and preserve the existing targeted dynamic-engine exclusions only. |
| RT-2026-07-19-523 | Delivery reviewer | Doubling the checked surface could materially slow CI or produce version-dependent local/CI results. | Medium | Resolved by pinned measurement | Keep the existing pinned mypy 2.1.0 CI install and Python 3.11 config; the full 104-module local run completes in about one second. |
| RT-2026-07-19-524 | Behavior reviewer | Type-driven rewrites in freshness and artifact ownership code could silently change authorization or lineage semantics. | Critical | Resolved in verification scope | Restrict changes to type narrowing plus a fail-closed unsupported-kind guard; run the dependent analysis, lineage, query, RV, report, digest, and run suites, then repeat the full backend suite. |

### Critic reopen conditions (route-layer type gate)

Reopen if route-wide ignores are introduced; CI uses a different mypy/Python
pair than the verified baseline; the gate exceeds the normal backend-job budget;
or authorization, freshness, lineage, query, RV, report, or digest tests regress.

## 2026-07-19 — First-fault stress protocol critic pass

Decision under review: execute a staged local stress ramp against the current
CAOS working tree and stop only after the first unexpected application fault is
reproduced and documented.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-525 | Data-safety reviewer | A destructive seed or load run against the user's live `:8000` process or its database could corrupt active work. | Critical | Resolved by isolation | Bind a new server to `127.0.0.1:8011`, use a fresh database and storage directory under `/tmp`, blank all provider keys, and leave the existing `:8000` and `:8010` listeners untouched. |
| RT-2026-07-19-526 | Failure-oracle reviewer | Treating designed `429`, `409`, or queue rejection as a fault would misclassify honest backpressure as an outage. | High | Resolved in oracle | Accept only endpoint-specific documented control responses. Stop on unexpected status, timeout, crash, integrity mismatch, or a fixed-budget breach; record controlled rejection rates separately. |
| RT-2026-07-19-527 | Reproducibility reviewer | One transient localhost timeout can come from test-driver saturation or an unrelated workstation process. | High | Resolved by confirmation | Capture client and server evidence, then rerun the smallest failing stage once against the same isolated target. List a fault only when its signature repeats or the server emits a deterministic exception. |
| RT-2026-07-19-528 | Change-attribution reviewer | The worktree contains extensive pre-existing edits, so a failure cannot automatically be attributed to the base branch or released application. | High | Accepted with explicit scope | Label findings as current-dirty-tree evidence, preserve the tested commit and `git status`, and require later clean-candidate confirmation before release attribution. Do not modify product code during this fault-finding goal. |
| RT-2026-07-19-529 | Cost/privacy reviewer | Stressing live LLM, EDGAR, or other external lanes can spend money, leak test content, or trigger provider abuse controls. | Critical | Resolved offline | Blank Anthropic, OpenRouter, Gemini, and Google credentials. The first-fault ramp targets local health/read/report/query-fixture behavior only; provider fault injection remains local-mock-only. |

### Critic reopen conditions (first-fault stress protocol)

Reopen if any request reaches `:8000` or `:8010`; the scratch database or
storage path is not demonstrably isolated; a provider credential is present;
expected backpressure is reported as a defect; the claimed fault cannot be
reproduced; or product code is changed before the observed fault is recorded.

## 2026-07-19 — Model Builder calculation-correction critic pass

Decision under review: correct the seven verified Model Builder calculation
defects across the live v2 engine, cross-module scenario rail, and ATLF-only
reference calculator without broadening the two explicitly disclosed scenario
model limitations.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-530 | Credit-methodology reviewer | Annualising one quarter of EBITDA would replace a known basis error with a seasonality-sensitive proxy that could still be read as covenant/LTM leverage. | Critical | Resolved fail-closed | Calculate leverage only for a 12-month EBITDA basis; for every other period retain debt and EBITDA but return no leverage and name the missing 12-month basis. Interest coverage remains period-consistent because both EBITDA and interest are period flows. |
| RT-2026-07-19-531 | Cash-flow reviewer | Rejecting negative tax or capex could hide legitimate refunds or asset-sale proceeds. | High | Resolved by explicit sign contract | Preserve taxes and capex as non-negative outflow fields, including analyst overrides. Route refunds, proceeds, and other signed sources through `other_cash_flow`, matching the published workbook contract; negative outflow inputs fail closed rather than increasing FCF. |
| RT-2026-07-19-532 | Debt-schedule reviewer | Splitting balance and interest completeness could accidentally aggregate a partial instrument set and understate debt. | Critical | Resolved with independent all-instrument gates | Keep the existing every-instrument period-row requirement for both gates; aggregate total debt only when every instrument has a usable reporting-currency balance, and aggregate cash interest only when every instrument has usable interest. One incomplete rate row can no longer erase a complete balance set. |
| RT-2026-07-19-533 | Async-state reviewer | Merely clearing scenario results in an effect leaves a stale render frame and lets an older request overwrite a newer shock. | High | Resolved by request identity | Key result, pending, and error state to issuer + run + EBITDA shock + rate shock. Render only an exact-key response and echo its run/shock basis; old in-flight results may settle but cannot become visible or block a new-key request. |
| RT-2026-07-19-534 | Forecast-methodology reviewer | Rebuilding interest from hard-coded spreads could still fail to reproduce the embedded agent baseline and would ignore fees/hedges already captured by the seeded cash-interest line. | High | Resolved by baseline-plus-delta | Make the embedded annual cash-interest and SOFR curve authoritative. Apply one explicit SOFR delta to the floating debt base, then apply the analyst cash-interest multiplier. Remove the unused EURIBOR/SONIA controls and exports from the USD/SOFR ATLF reference model. |
| RT-2026-07-19-535 | Persistence reviewer | Changing the SOFR assumption from an absolute rate to a delta can corrupt previously saved reference sessions. | High | Resolved with backward-compatible parser | Introduce a versioned `sofrDelta` field and migrate legacy absolute `sofrRate` values into per-year deltas against each case's embedded curve; unknown EURIBOR/SONIA values are dropped. New defaults remain true no-ops. |
| RT-2026-07-19-536 | Distress-output reviewer | A generic positive-denominator guard could blank valid negative FCF/debt ratios or net-cash positions along with meaningless leverage. | High | Resolved per-ratio | Require positive adjusted EBITDA only for leverage/coverage and positive interest only for coverage; retain signed numerators and require only a positive debt denominator for FCF/debt. Add direct negative-EBITDA regression coverage. |

### Critic reopen conditions (Model Builder calculations)

Reopen if any subannual period emits leverage; a negative tax/capex input or
override increases FCF; incomplete interest erases complete debt balances; a
scenario result survives an issuer/run/shock change; default ATLF interest no
longer ties to its seeded annual line and curve; a removed currency control is
still exported; or non-positive EBITDA renders a leverage/coverage multiple.

## 2026-07-19 — All-surface frontend design-audit critic pass

Decision under review: classify the current 18-route CAOS frontend as a shared
experience-architecture redesign while preserving its institutional visual
system, evidence/provenance model, Report Studio paper identity, and explicit
state grammar.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-537 | Scope-control reviewer | A product-wide redesign recommendation can become an aesthetic rewrite that destroys the strongest existing assets and exceeds the evidence. | Critical | Resolved by preserve/discard boundary | Preserve the dark terminal tokens, light report paper, evidence/provenance primitives, keyboard/focus contracts, and explicit live/demo/reference states. Limit structural redesign to persona composition, navigation hierarchy, high-stakes action semantics, and narrow task contracts. |
| RT-2026-07-19-538 | Visual-evidence reviewer | Dated 13 July captures could cause already-fixed overflows to be reported as current defects. | High | Resolved by current render matrix | Treat old captures only as regression history. Base current visual findings on the fresh 1440×900 and 390×844 route matrices, current source, and rendered axe output. |
| RT-2026-07-19-539 | Buy-side workflow reviewer | Preserving every desktop control at 390 px can be mistaken for responsive completeness even when the credit task becomes unreadable or requires blind lateral panning. | Critical | Resolved by task-capability standard | Judge narrow modes by whether the role can complete the intended task, not by DOM presence. Give Report, Pipeline, Model, directory tables, and tab bands explicit read/triage or authoring contracts with visible handoff. |
| RT-2026-07-19-540 | Persona reviewer | A role-view redesign could accidentally change permissions or hide shared facts, creating governance risk. | Critical | Resolved by composition-only boundary | Recompose priority, density, summaries, columns, and default panes while keeping the underlying authorized dataset and actions invariant; verify each persona against the same data authority. |
| RT-2026-07-19-541 | Delivery reviewer | Scoring the worst instance across 18 routes can overstate product failure and encourage a full rebuild rather than targeted shared-shell changes. | High | Accepted with explicit interpretation | The mechanical Rams total determines REDESIGN, but the handoff must redesign the shared information architecture and role/task contracts, not rebuild every route or replace the visual language. Route-specific faults remain a sequenced remediation register. |

### Critic reopen conditions (all-surface frontend design audit)

Reopen if the proposed work changes brand tokens or Report Studio paper without a
new evidence basis; changes role permissions or data authority; cites old
captures as current truth; claims narrow support from element presence alone; or
turns the mechanical REDESIGN verdict into an unbounded rewrite of all route
implementations.
# Desktop/tablet remediation implementation gate — 2026-07-19

Scope: implement the approved 71-finding CAOS frontend remediation while
excluding phone-specific task redesign. The design contract remains the dark
institutional workspace, light Report paper, evidence authority, immutable
finalization, and presentation-only role views.

## Critic objections and binding mitigations

1. **A big-bang persona or EnterprisePage API rewrite could break every route.**
   GitNexus reports CRITICAL upstream impact for `PersonaWorkbench` (19 direct
   consumers), `ConceptNav` (7 direct plus broad transitive reach), `Panel` (53
   direct), and `EnterprisePage` (21 direct). Mitigation: land additive fields
   and hooks first, keep current props compatible during migration, add 18-route
   contract tests, and remove compatibility only after all callers pass.
2. **Role-specific presentation could accidentally become authorization.**
   Mitigation: role projections may change order, emphasis, columns, density,
   and defaults only. Datasets, actions, backend calls, approval authority, and
   permissions must remain invariant and are asserted in tests.
3. **Reference mode could become another silent fixture fallback.**
   Mitigation: live is the only default; `?mode=reference` is explicit and
   screenshot-visible; missing live data remains an honest empty/unavailable
   state; fixture bundles never mount in a live result region.
4. **A generic success state could flatten processed, saved, published, and
   ratified into one misleading green badge.** Mitigation: preserve
   `SurfaceState` as non-happy-path and model completion with orthogonal
   execution, persistence, approval, and freshness axes.
5. **Typography remediation could destroy Report pagination or terminal
   density.** Mitigation: separate screen proofing and print floors, paginate
   rather than shrink, retain 12px dense workspace body and mono/tabular number
   grammar, and verify both screen and print output.
6. **Navigation simplification could hide specialist destinations.**
   Mitigation: `NAV_GROUPS` remains canonical and complete for All Workflows,
   headings, palette, and concept cycling; role projections alter prominence,
   never availability.
7. **Shared fixes could unintentionally expand phone scope.** Mitigation:
   acceptance is >=768px plus keyboard and real 200% zoom. A 390px smoke only
   checks mounting, landmarks, crashes, and regression of the existing axe
   baseline; no phone-specific authoring or review representation is added.
8. **The dirty worktree could absorb or overwrite parallel changes.**
   Mitigation: remain on the existing `codex/112` branch so current work is
   present, inspect overlapping hunks, use `apply_patch`, run explicit diffs,
   never stage unrelated paths, and do not clean/reset/stash user work.

Decision: proceed only with the mitigations above as release gates. Any shared
contract that cannot stay additive or any persona change that alters authority
returns to this critic gate before implementation continues.

## 2026-07-19 — Postgres pool-contention remediation critic pass

Decision under review: replace SQLAlchemy's implicit Postgres pool defaults with
explicit, environment-configurable sizing coupled to executor concurrency, and
correct the stress harness's designed-backpressure accounting.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-542 | Database-capacity reviewer | Increasing a per-process pool can multiply across workers, exceed Postgres `max_connections`, and merely move the queue from SQLAlchemy into the database. | Critical | Resolve with bounded auto-size | Keep the supported `WEB_CONCURRENCY` ceiling at two; cap the default auto envelope at 25 connections per worker (20 persistent + five overflow), leaving half of bundled Postgres's default 100 connections for migrations, probes, backups, and operator access. Explicit overrides remain operator-owned and documented. |
| RT-2026-07-19-543 | Regression reviewer | Passing QueuePool-only arguments to SQLite or test `NullPool` can break local development and the multi-loop test suite. | High | Resolve by dialect/test branch | Apply pool sizing only to Postgres outside `CAOS_TEST`; preserve SQLite engine construction and test `NullPool` unchanged, with direct unit coverage of every branch. |
| RT-2026-07-19-544 | Latency reviewer | A larger pool may hide slow transactions without fixing connection hold time, while adding CPU and database contention. | High | Resolve by same-oracle verification | Retain the existing transaction lifecycle, instrument checkout/SQL/event-loop waits, and repeat the 300-user issuer probe. Accept the change only if the fixed 500 ms gate passes without errors and SQL/health do not regress. |
| RT-2026-07-19-545 | Configuration reviewer | Invalid negative sizes or a non-positive timeout can crash deep inside SQLAlchemy with an opaque boot failure. | High | Resolve fail-fast | Validate the resolved Postgres pool parameters before engine creation and raise a configuration-specific `ValueError`; exercise auto, explicit, SQLite, test, and invalid cases. |
| RT-2026-07-19-546 | QA-signal reviewer | The tracked Locust client currently counts the report route's documented per-principal 429 as an application failure, contaminating the verification oracle. | High | Resolve in harness only | Accept 200/409/429 for report generation, preserve NL 429 handling, and keep all other statuses as failures. Do not weaken the product route or global failure oracle. |

### Critic reopen conditions (Postgres pool remediation)

Reopen if the default two-worker envelope can exceed 50 application
connections; SQLite or `CAOS_TEST` receives QueuePool arguments; 300-user p95
still exceeds 500 ms; any unexpected HTTP/5xx error appears; SQL p95 or recovery
materially regresses; or the stress harness treats an undocumented response as
success.

## 2026-07-19 — HTTP policy middleware consolidation critic addendum

Decision under review: replace four function-style FastAPI middleware layers
with one raw ASGI policy layer after the pool-only remediation failed the
300-user latency gate and an isolated upper-bound test cleared it when those
layers were removed.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-553 | Security-boundary reviewer | Consolidation can silently change the established access-log → CSRF → edge-proof → security-header order, allowing an untrusted browser mutation to reach a route or causing a rejected request to disappear from telemetry. | Critical | Resolve by explicit control flow | Keep access telemetry outermost, evaluate CSRF before the edge proof as the current runtime stack does, apply the edge exemption only to `/api/health`, and inject response policy headers around every downstream or short-circuit response. Pin both 401 and 403 paths in integration tests. |
| RT-2026-07-19-554 | HTTP-semantics reviewer | Rebuilding response headers can collapse duplicate fields such as `Set-Cookie`, overwrite a route's stricter cache policy, or omit policy headers from 413/414 responses emitted by the inner request-limit layer. | Critical | Resolve at `http.response.start` | Mutate the ASGI response-start message in place through `MutableHeaders`, use set-if-absent semantics, and leave all unrelated raw header entries untouched. Keep the request-limit middleware inside the policy layer and retain its 413/414 regression tests. |
| RT-2026-07-19-555 | Streaming reviewer | A middleware optimized for timing may buffer response bodies or emit the access event before a streaming response actually completes. | High | Resolve without body interception | Forward every ASGI message immediately, capture status and declared content length only from response start, and emit the access event after the downstream application returns. Do not inspect, join, or retain body chunks. |
| RT-2026-07-19-556 | Telemetry reviewer | Short-circuit responses or duplicated send callbacks can produce no event or multiple events, corrupting threat-detection volume and duration signals. | High | Resolve with request-scoped state | Capture a single status/volume pair per API scope and emit exactly once after completion; add tests asserting one 401 event, one 403 event, and preservation of 413/414 events. Static paths remain intentionally silent. |
| RT-2026-07-19-557 | Performance reviewer | Removing `BaseHTTPMiddleware` in a diagnostic wrapper proves an upper bound but not that the combined production policy layer, synchronous access logging, and pool sizing clear the real gate. | Critical | Resolve by repeated release oracle | Run the uninstrumented product with all policies and access logging enabled at 300 users for three repetitions. Accept only if every issuer probe p95 is below 500 ms, no unexpected failures occur, and the tracked mix remains valid. |

### Critic reopen conditions (HTTP policy middleware consolidation)

Reopen if policy order changes; any 401/403/413/414 response lacks the standard
security/cache headers or a single access event; duplicate response headers are
collapsed; a response body is buffered; static traffic enters the access feed;
or any of three 300-user verification repetitions misses the 500 ms issuer p95
gate.

## 2026-07-19 — Task 2A shared hierarchy/accessibility critic pass

Decision under review: centralize route titles in the canonical navigation
registry, move Ask into breakpoint-owned shell utilities, make Panel scroll
focusability measurement-driven, and raise shared/report type floors.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-547 | Navigation architecture | A second route-title map can drift from `NAV_GROUPS`, recreating the exact wrong-heading defect while appearing centralized. | High | Resolved in design | Derive workflow titles from `NAV_GROUPS`; keep only explicit utility and more-specific dynamic-route metadata beside that registry, with longest-match resolution and unknown fallback tests. |
| RT-2026-07-19-548 | Keyboard accessibility | Unconditionally focusable Panel bodies add dozens of inert tab stops, while resize-only measurement goes stale after late report content or font/layout changes. | Critical | Resolved in design | Focus only real overflow; observe the owner and content with `ResizeObserver` plus subtree `MutationObserver`; remeasure collapse transitions; retain the named visible focus treatment and avoid focusing or blurring during reclassification. |
| RT-2026-07-19-549 | Shell interaction | Moving Ask can break Alt+K, Query-route focus routing, issuer grounding, or modal focus restore if trigger and overlay ownership are split inconsistently. | Critical | Resolved in design | Keep `AskProvider` as the sole state/route coordinator and `AskLauncher` as the sole overlay owner; add a shared utility trigger in the wide rail and compact header, preserving the existing `toggle`, route exclusions, modal components, and scope resolver. |
| RT-2026-07-19-550 | Report production | Raising preview text by selector alone can overflow the fixed appendix or make print unusable, prompting a later regression back to microtype. | High | Resolved in design | Enforce separate screen and print floors; let screen paper widen/flow inside its named scroll owner and let print paginate/flow rather than scale below 9.5pt body and 8pt table/appendix floors. Pin both media contracts in executable CSS tests. |
| RT-2026-07-19-551 | Design governance | A color-literal gate can become meaningless if whole directories are allowlisted, or brittle if comments/test fixtures and non-color identifiers such as run numbers are treated as colors. | High | Resolved in design | Scan production style-bearing files, permit root token declarations and an explicit file-level chart-rendering allowlist only, ignore tests/comments, and replace shared/report CSS literals with semantic variables before enabling the gate. |
| RT-2026-07-19-552 | Parallel-work reviewer | Shared shell files overlap Task 1 dirty work; wholesale rewrites could erase reviewed persona navigation and skip-target repairs. | Critical | Resolved by execution constraint | Use narrow `apply_patch` hunks, retain role projections/drawers/skip ids unchanged, run the Task 1 62-test suite with Task 2A tests, and review explicit-path diffs only. |

Decision: proceed with additive registry metadata, a shared Ask utility trigger,
observer-driven Panel measurement, and media-specific type floors. Reopen if a
route title is sourced outside the canonical registry seam, Ask creates two
visible triggers at a supported width, or a fitting Panel enters the tab order.

### Task 2A independent-review repair addendum

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-562 | Policy-gate reviewer | A documentary chart list or stylesheet-only regex can advertise production-wide governance while missing literals in TS/TSX and the very Report components under remediation. | Critical | Resolved | Add a recursive production-source scanner over `src/app`, `src/components`, and `src/lib`; exclude tests, consume an imported exact allowlist, permit only the `:root` token block plus the centralized CSS-independent token module, and prove allowed/rejected fixtures including four-digit hex. |
| RT-2026-07-19-563 | Recovery semantics reviewer | Demoting local recovery titles leaves the sole global `h1` describing the requested route rather than the screen actually rendered. Adding local `h1`s would instead duplicate the outline. | Critical | Resolved | Keep one global `h1`; derive auth/loading/error titles directly from auth state and add a shared client override for mode-specific login and route-error titles. Unknown paths resolve to `Page not found`; root global error retains its standalone accurate `h1`. Rendered tests count exactly one and assert its accessible name. |
| RT-2026-07-19-564 | Zoom-verification reviewer | A 768px emulated viewport does not exercise Chrome zoom state, host-specific zoom overrides, native rounding, or browser-zoom layout behavior. | High | Resolved | Use a dedicated headed Chrome profile, select 200% in Chrome's own Appearance UI, remove the localhost 100% host override through Chrome's native Zoom levels UI, and require zoom setting 2, DPR 4, outer/inner 1728/864, and `visualViewport.scale === 1` before route checks. |
| RT-2026-07-19-565 | Compact-header reviewer | Preserving a long Report caveat as ordinary identity detail can clip the provenance chip or push utilities/primary action out at native 200% zoom. | High | Resolved | Move the must-survive provenance into `ShellIdentity.badges`, hide only secondary explanatory prose below the wide rail breakpoint, and assert settled DOMRects for Report utilities and the primary action remain inside the 864px layout viewport. |
| RT-2026-07-19-566 | Dynamic-content reviewer | Even when every shell/recovery surface owns exactly one `h1`, authored or model-generated Research Markdown can inject another `h1` at runtime and invalidate the route outline. | Critical | Resolved | Override ReactMarkdown's authored `h1` renderer at the `ReportBody` boundary so its content remains visible as a paper-styled `h2`; retain the GFM table renderers and prove both the no-`h1` heading contract and numeric alignment in the rendered component test. |

Decision: the repaired contracts are release-gated by the production color scan,
rendered exact-one-heading cases, the standard axe viewport matrix, and the
separate native Chrome 200% audit. Reopen if a new production literal bypasses
the exact allowlist, an override or dynamic Markdown creates a second `h1`, or
Chrome reports zoom 2 without the corresponding DPR/layout-viewport change.

## 2026-07-19 — Task 2B typed page-action critic pass

Decision under review: replace arbitrary `EnterprisePage.primaryAction` nodes
with one discriminated link-or-callback contract, migrate every route, and
correct the Model, Sector, Report, Sponsors, and IC Book action hierarchy.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-567 | Shared-contract reviewer | An arbitrary-node compatibility path would preserve multi-action primaries and let future routes bypass the one-effect guarantee. | Critical | Resolved in design | Export one `PageAction` union from `EnterprisePage`, accept no React-node escape hatch, migrate every direct caller in the same task, and render the action only at the shared boundary. |
| RT-2026-07-19-568 | Keyboard reviewer | Turning unavailable hrefs into ordinary links with only `aria-disabled` would still navigate, while native-disabled callbacks would disappear from the tab order. | Critical | Resolved in design | Render live hrefs as links; render unavailable href or callback actions through the guarded `Button`/`ActionReason` path with a stable label, visible-on-attempt and screen-reader reason, no native `disabled`, and no callback/navigation effect. |
| RT-2026-07-19-569 | Model-authority reviewer | Simplifying Model header actions could change checkpoint authority, calculation state, or erase parallel Model v2/report work. | Critical | Resolved by execution constraint | Change only action descriptors and utility placement. Legacy Save checkpoint keeps its existing handler/guards and Export keeps its existing handler in Model utilities; Model v2 keeps the state-dependent immediate handler while collapsing each state to one primary. No engine, checkpoint, revision, or calculation code changes. |
| RT-2026-07-19-570 | Hierarchy reviewer | Promoting Sector refresh or IC Book add without removing the old entry point would merely relocate duplication and still create competing primaries. | High | Resolved in design | Sector's refresh branch leaves the finalization bar actionless while the header owns Request refresh; IC Book's empty state names the single header action instead of rendering a second Add control. |
| RT-2026-07-19-571 | Skip-target reviewer | Omitting Sponsors' unavailable primary can leave the global page-actions skip link pointing to a dead target. | High | Resolved by existing shell contract | Preserve `SubHeader`'s honest focusable no-action target when `primaryAction` is absent; assert live, unavailable, and no-action skip states after migration. |
| RT-2026-07-19-572 | Regression reviewer | A CRITICAL 20-caller migration can silently change labels or immediate effects on otherwise unrelated routes. | Critical | Resolved by verification plan | Inventory every `EnterprisePage` call, pin route label/effect pairs in focused tests, compile the exclusive union, scan rendered primaries for at most one interactive descendant and no native disabled state, then run Task 1/2A regressions plus desktop/tablet axe. |

Decision: proceed with a single typed shared renderer and full call-site
migration. Reopen if any route needs arbitrary action markup, any unavailable
action navigates/fires, Model handlers differ from their current authority, or
the page-action region contains more than one interactive descendant.

### Task 2B independent-review repair addendum

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-579 | Shared-renderer reviewer | A live callback can supply `PageAction.title`, but the callback renderer drops it; an unavailable action must still expose the blocking reason instead of that live-state title. | High | Resolved | Thread the optional title through `EnterprisePage`, `Button`, and `ActionReason`; use `unavailableReason || actionTitle` so the blocking reason has explicit precedence, and pin both live and inert cases in the shared contract test. |
| RT-2026-07-19-580 | Accessible-name reviewer | Busy-state prose in `label` changes an action's accessible name during activation, making assistive-technology and voice-control targeting unstable across Model, Sector, Query, Research, RV, Report, and Deep-Dive. | High | Resolved | Keep labels operation-based and invariant across ready/busy/unavailable transitions; carry progress through `unavailableReason` or existing status surfaces, statically audit the known descriptors, and exercise representative transitions in rendered tests. |

Decision: the repaired contract is release-gated by title-precedence coverage,
stable ready-to-busy accessible names, focusable inert behavior, TypeScript,
focused lint, and scoped change detection. Reopen if progress text re-enters a
`PageAction.label` or a blocking reason loses title precedence.

## 2026-07-19 — Issuer direct-evidence and distress-rating critic pass

Decision under review: reconcile the 23 remaining Issuer tracker gaps to
assertion-level evidence and add a non-color distress cue to the register's
Rating cell.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-558 | Accessibility reviewer | Adding only an accessible label would still leave a sighted colorblind analyst dependent on the existing critical-red rating text. | High | Resolve with visible and AT cues | Pair a compact critical glyph with explicit screen-reader text inside the existing Rating gridcell; retain the agency rating as visible text and keep the row's interaction model unchanged. |
| RT-2026-07-19-559 | Dense-table reviewer | A verbose badge or added column would reduce scan density, disturb the eight-column grid, or crowd narrow horizontal layouts. | High | Resolve in-cell | Keep the existing column count and width; add only the shared 9px glyph with a one-gap inline layout, and validate the existing semantic grid rather than introducing a new control. |
| RT-2026-07-19-560 | Evidence-governance reviewer | Mapping an entire Issuer file as direct evidence could overclaim features whose exact behavior is not asserted. | High | Resolve assertion-by-assertion | Map only named test nodes with matching assertions and explicit scenario classifications; keep unproved scenarios Designed even after every Issuer feature has at least one direct node. |
| RT-2026-07-19-561 | Contract-drift reviewer | Reusing the legacy feature prose would preserve retired claims such as two profile ratings, G2-only trend charts, or a hardcoded US HY sleeve. | High | Resolve from current source | Override only the drifted rows with the current component behavior before rebuilding; preserve implementation-as-spec and record the correction as a tracker defect. |

Decision: proceed with the in-cell glyph/text cue, exact-node mappings, and
implementation-derived contract corrections. Reopen if the Rating column count
changes, row focus/action semantics regress, or any mapping lacks a matching
assertion in the cited test node.

## 2026-07-19 — Command scenario-closure and position-authority critic pass

Decision under review: close the 44 Command Center feature suites with exact
scenario evidence, restore the selected-position facts promised by the current
contract, and fail closed when a profile or Deep-Dive handoff lacks its required
identity authority.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-573 | Identity reviewer | Rendering a missing ticker as a clickable em dash makes an unnamed-looking control open a profile and conflicts with the distinct company-link action. | High | Resolve by conditional ownership | Render the ticker as an `IssuerLink` only when both issuer id and ticker exist; retain the borrower-name profile link when issuer identity exists, and keep row selection isolated from either nested action. |
| RT-2026-07-19-574 | Analytical-authority reviewer | A Deep-Dive link with an issuer but no bound run can silently open a newer or unrelated run, breaking the strip's promise to preserve portfolio-snapshot authority. | Critical | Resolve fail closed | Expose Open Deep-Dive only when both issuer id and run id exist; otherwise show an explicit authority-unavailable message. Encode both identifiers and pin the missing-run branch in a rendered test. |
| RT-2026-07-19-575 | Dense-layout reviewer | Adding maturity, ratings, and governance state to the strip can crowd the bottom action region or make the Close target collide with global utilities. | High | Resolve within the existing wrapping contract | Reuse the compact two-line stat treatment inside the existing flex-wrap strip, combine QA and committee state into one concise value, retain the existing Close control/Ask offset, and verify the route at desktop and narrow viewports. |
| RT-2026-07-19-576 | Evidence-governance reviewer | Bulk-mapping all seven scenario classes from a route-level pass would turn adjacency into false direct evidence and hide feature-specific gaps. | Critical | Resolve assertion-by-assertion | Attribute only exact named nodes whose assertions exercise the feature/scenario boundary; use shared authentication and rendered route geometry only for their genuine cross-cutting permission and mobile contracts, and keep a fail-closed 44-by-7 status gate. |
| RT-2026-07-19-577 | Contract-drift reviewer | The tracker still says Open top change changes tabs and focuses a panel, while the product and E2E contract now navigate directly to the encoded top issuer. | High | Resolve from current implementation | Correct the canonical story, expected behavior, edge cases, and trigger to the implemented Deep-Dive action; test unavailable draft/empty/missing-issuer reasons and do not mutate product behavior to satisfy stale prose. |
| RT-2026-07-19-578 | Concurrency reviewer | Focus refresh, portfolio switching, alert acknowledgement, insight generation, and context autosave can pass happy-path tests while stale completions overwrite newer state. | High | Resolve with existing and targeted race assertions | Map performance only to bounded virtualization, cleanup/race, duplicate-action, serialized-patch, or refresh assertions; do not treat a fast unit duration as a performance oracle, and retain the staged-load/recovery protocol for HTTP performance work. |

Decision: proceed with the identity/authority fixes, implementation-derived
contract correction, and exact-node evidence closure. Reopen if any missing
identity renders an actionable dash, Deep-Dive can omit the run binding, the
strip clips or loses Close at 390px, or the 44-by-7 gate is satisfied by a node
that does not assert the named scenario.

## 2026-07-19 — Task 2C completion/evidence contract critic pass

Decision under review: add orthogonal completion presentation and one reusable
evidence-selection list, then adopt them at Upload, Model, Report, Pipeline,
Deep-Dive, and Report Lineage seams without changing authority or source effects.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-581 | Authority reviewer | A shared “success” component could infer saved, published, ratified, or current from execution completion and recreate F-014 behind a cleaner visual. | Critical | Resolved in design | Keep `SurfaceState` non-happy-path. Require callers to pass four independently typed axes; render only the supplied value or explicit N/A, and add a complete/unsaved/unratified/unknown regression. |
| RT-2026-07-19-582 | Upload truth reviewer | A zero-success intake can still read CP-0 ready if the new axes are appended beneath the old unconditional headline. | Critical | Resolved in design | Make the completed-result panel title neutral, map zero successful vault writes to execution failed plus persistence unsaved, and pin a rendered zero-success assertion. Task 3 retains ownership of the fuller intake truth-copy rewrite. |
| RT-2026-07-19-583 | Evidence-authority reviewer | Deduplicating every citation would merge contextual paper claims, provenance inspection, or immutable-version selection with a register browser that has a different effect. | Critical | Resolved by scope boundary | Migrate only Deep-Dive output-register evidence inventories and Report Lineage. Preserve `ReportDoc` paper citations, analytical inline `EvChip`s, provenance controls, and published-version selection unchanged. |
| RT-2026-07-19-584 | Keyboard reviewer | A visually selected row without a real roving-focus contract can add tab stops or lose the selected source after Arrow/Home/End navigation. | Critical | Resolved in design | Use one listbox row tab stop, selection-following-focus, stable id-keyed refs, Arrow Up/Down and Home/End handling, `aria-selected` plus position/set-size, and one labelled external Open source action. |
| RT-2026-07-19-585 | Focus reviewer | Moving the modal opener outside each row can cause dialog close to restore focus to a stale row or nowhere. | High | Resolved in design | Open from the shared action itself so the existing modal focus hook captures that element; do not remount the action on selection, and test close/restoration through the affected Report/Deep-Dive integration path. |
| RT-2026-07-19-586 | Parallel-work reviewer | Model, Report, Pipeline, Deep-Dive and their tests already contain reviewed remediation or user WIP; broad rewrites could erase Task 1/2A/2B behavior. | Critical | Resolved by execution constraint | Use additive imports and tight `apply_patch` hunks, keep source IDs and handlers byte-for-byte, add new contract tests where practical, and review explicit-path diffs before verification. |

Decision: proceed with caller-owned independent axes and a listbox-plus-shared-
opener evidence contract. Reopen if any axis is derived inside the shared
component, an inline paper citation is removed, a selected row becomes an
additional modal opener, or zero successful uploads can render execution
complete/CP-0 ready.

## 2026-07-19 — Task 3A live/reference boundary critic pass

Decision under review: introduce URL-addressable live/reference mode at the
shared shell and make Profile, Research, and Deep-Dive refuse silent fixture
substitution.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-593 | Data-authority reviewer | Treating the reference issuer id as equivalent to Reference mode would let a live URL silently cross the truth boundary and keep today’s fallback under a new label. | Critical | Resolved in design | Only exact `?mode=reference` authorizes reference fixtures; live mode defaults fail closed even when issuer is absent or happens to equal the fixture id. Tests cover both distinctions. |
| RT-2026-07-19-594 | URL-state reviewer | Appending `mode=reference` ad hoc can drop issuer/run/context/module parameters, duplicate mode keys, or leak Reference into an explicit live transition. | Critical | Resolved in design | Centralize parse/set helpers around `URL`/`URLSearchParams`, retain all unrelated params and hash, replace duplicate mode keys, and remove the param for live. Pin round-trip cases. |
| RT-2026-07-19-595 | Bundle/performance reviewer | Hiding seeded JSX is insufficient if fixture modules still load and execute on every live visit, preserving startup cost and accidental data reachability. | High | Resolved by implementation gate | Put heavy Reference-only views/fixtures behind mode-gated dynamic imports or the narrowest existing lazy seam; add a cold-live regression where practical and record any unavoidable shared lightweight metadata separately. |
| RT-2026-07-19-596 | Header/zoom reviewer | A persistent marker can disappear when SubHeader collapses or displace the single page action at tablet/200% zoom. | High | Resolved in design | Give the marker a dedicated must-survive semantic slot in shared header chrome and include it in collapsed utilities; preserve the Task 2A responsive action region and add rendered/native-zoom geometry evidence. |
| RT-2026-07-19-597 | Analytical-state reviewer | Deep-Dive can still combine an unavailable live DecisionHeader with seeded debate/scenario panels if only the module body is gated. | Critical | Resolved in design | Derive decision context, default module, bespoke eligibility, and evidence/report loading from DataMode; a live missing-issuer/no-run state renders no fixture-backed decision region. |
| RT-2026-07-19-598 | Parallel-work reviewer | Profile, Research, Deep-Dive, ConceptNav, and SubHeader carry prior remediation and user WIP; broad rewrites could erase reviewed contracts. | Critical | Resolved by execution constraint | Use additive helpers and narrow patches, keep route/persona/action/evidence contracts intact, run their focused regression suites, and inspect explicit-path diffs before acceptance. |

Decision: proceed with an exact URL-owned boundary and fail-closed live states.
Reopen if any issuer id or missing API response activates fixtures without the
query mode, the marker disappears in collapsed chrome, or a live cold state
imports/renders a reference-only decision artifact.

Implementation verification: RT-593/594 are pinned by exact parser and URL
round-trip tests, including duplicate-mode replacement and preservation of
issuer/run/module/context/hash. RT-595 is resolved by a mode-gated dynamic
import for the Research fixture and by keeping Deep-Dive bespoke eligibility
strictly Reference-only. RT-596 is resolved by an always-rendered, non-hidden
header status marker plus 768px shell/axe coverage. RT-597 is resolved by the
standalone live missing-issuer setup state, which mounts no fixture decision,
scenario, evidence, or debate region. RT-598 is resolved by focused Task 3A and
prior Task 1 shell regressions, explicit-path diff review, and an isolated-index
GitNexus audit. No objection remains open within the Task 3A slice.

### Task 3A independent-review repair addendum

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-605 | URL-store reviewer | Query-only Next `Link` transitions can leave persistent marker and WorkflowRail consumers stale even while the route-local tree follows the new query. | High | Resolved | Install one idempotent History API notifier for native/Next `pushState` and `replaceState`, retain popstate/hash/custom-event support, and prove real Next-link plus direct-URL live → Reference → live transitions with the persistent rail mounted. |
| RT-2026-07-19-606 | Research-concurrency reviewer | A live poll can resolve after entering Reference, overwrite the fixture, and mutate context/findings; a fresh live `demo: true` terminal can also cross the truth boundary. | Critical | Resolved | Own each watch by live mode, job, controller, and epoch; abort the local poll on Reference entry without deleting the durable job pointer; reject stale or demo terminals before render, context patch, finding creation, or notification; cover both deferred races. |
| RT-2026-07-19-607 | Deep-Dive-authority reviewer | Reference can mix a resolved live run's authority/actions or a missing live scenario warning into the seeded decision region. | Critical | Resolved | Reference now supplies fixed fixture-owned decision context and excludes live run output, council, evidence map, scenario, standing-view run authority, and Vault export. Null/populated live-run reference regressions prove isolation; the live issuer path retains scenario and export. |

Decision: the repaired Task 3A boundary is release-gated by the real-browser
round trip, deferred poll/demo quarantine tests, null/populated Reference
Deep-Dive tests, focused and Task 1 shell suites, TypeScript/lint/diff checks,
and the affected 12-case axe matrix. Reopen if any History transition escapes
the store, a stale Research watch can mutate after mode change, or Reference
mounts a live-run action or unavailable-state panel.

## 2026-07-19 — Task 3C reference-isolation and desk-language critic pass

Decision under review: complete the Pipeline/Monitor live-reference boundary
and translate Query, Pipeline, RV, Sector, and Settings implementation language
without changing analytical payloads, mutations, permissions, or URL effects.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-613 | Pipeline-authority reviewer | Treating “no selected persisted run” as permission to mount the route simulator would silently recreate the seeded/live substitution fixed in Task 3A. | Critical | Resolved in design | Consume the exact shared DataMode contract. Live mode renders persisted-run loading/error/no-run/run states only; Reference alone may evaluate simulation fixtures. Preserve issuer/run selection, status precedence, evidence ids, and completion axes. |
| RT-2026-07-19-614 | Pre-execution-semantics reviewer | A fully populated Reference dependency graph can still imply completed work if planned nodes inherit green/passed glyphs, progress bars, or completion verbs before the simulation starts. | Critical | Resolved in design | Derive the plan count from the selected plan, state `N planned · 0 executed` before the first simulated event, and give untouched nodes neutral planned styling/labels. Simulated execution may change only the existing run-local state. |
| RT-2026-07-19-615 | Monitor-data reviewer | Hiding replay behind a disclosure is insufficient when the disclosure, replay counters, static Email Intelligence rows, or replay-state chart still auto-mount beside an empty/offline live worklist. | Critical | Resolved in design | Live Monitor owns only routed live alerts and live governance/control-plane reads. Reference owns replay and static Email Intelligence. Live empty/offline renders one concise state with no zero chart/toggle/replay controls. |
| RT-2026-07-19-616 | Persona reviewer | Gating Reference content could accidentally demote the QA governance-first composition or remove live alert effects shared with Analyst/PM. | High | Resolved by composition boundary | Keep `usePersonaComposition("monitor")`, slot ordering, selected-alert synchronization, acknowledgment, governance reads, and control-plane effects unchanged. Mode constrains datasets; persona still controls leading live region. |
| RT-2026-07-19-617 | URL-compatibility reviewer | Renaming visible Pipeline/RV views can break saved `view=` URLs or mutate internal lane/capability payload values if display and transport identities are conflated. | Critical | Resolved by projection | Preserve existing canonical payload keys and legacy URL values; add display-label projections and explicit aliases only. Tests pin old and new query forms to the same state/effect. |
| RT-2026-07-19-618 | Settings-truth reviewer | Inferring `Connected` from the presence of demo/static data or a configured provider key would overstate operational email intake. Moving every diagnostic into a disclosure could also hide task-relevant failures. | Critical | Resolved fail closed | Derive exactly four observable feed labels from connection read state plus explicit Reference mode: Connected, Not connected, Reference feed, Status unavailable. Keep task outcomes in primary copy; raw env/provider/code constants remain keyboard-reachable in a collapsed native disclosure. |
| RT-2026-07-19-619 | Parallel-WIP reviewer | All seven affected surfaces already contain reviewed remediation and active unrelated changes; broad component rewrites could erase persona, typed-action, authority, or recovery work. | Critical | Resolved by execution constraint | Use TDD and narrow `apply_patch` hunks; inspect current diffs before each overlap; do per-symbol upstream impacts; preserve handlers and payload values byte-for-byte; verify focused prior regressions and scope change detection without staging. |

Decision: proceed with mode-gated data ownership and display-only terminology
projections. Reopen if live mode evaluates seeded Pipeline/Monitor fixtures,
planned work looks completed, old URLs change effect, QA loses governance-first
composition, or Settings claims connection without an observable live source.

### Independent-review repair addendum

The independent review reproduced four reopen conditions hidden by diagnostic
attributes and shared render-time hooks. Each was treated as an architecture
objection, not a copy-only defect.

| ID | Objection | Impact | Resolution |
|----|-----------|--------|------------|
| RT-2026-07-19-625 | Branching inside a shared Pipeline view model still initializes seeded simulation in Live and calls live status/freshness/run hooks in Reference. | Critical | Branch before runtime hooks. Live imports a seed-free topology; Reference dynamically owns fixtures/simulation. Direct call counters prove zero cross-mode runtime reads, including `run=` in Reference. |
| RT-2026-07-19-626 | `N planned · 0 executed` can coexist with a zero progress bar and completion-style axes, still implying execution has begun. | High | Before the first reference event, omit progress bars/count ratios and mark execution, persistence, approval, and freshness N/A. |
| RT-2026-07-19-627 | Monitor tab filtering does not isolate data when a shared controller has already called autonomy, portfolio, governance, and insight hooks or rendered live decision context. | Critical | Use separate Live and Reference controllers before hooks. Reference returns an explicit adapter with decision context N/A and makes zero live authority calls. |
| RT-2026-07-19-628 | Keeping legacy model/provider terms in ordinary Settings panels violates task-language truth even when raw ids also exist in diagnostics. | High | Rename ordinary panels and choices around analysis/answer outcomes; retain implementation ids only in collapsed Deployment diagnostics. |

Addendum decision: proceed with the pre-hook controller boundaries above. All
four objections were observed RED, repaired, and verified GREEN in the focused
Task 3C suite and affected browser matrix.

## 2026-07-19 — Task 3B action/outcome truth critic pass

Decision under review: derive Upload completion from durable outcomes, correct
immediate-effect action labels, and add producer-owned notification action
labels through the database/API/toast boundary.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-599 | Readiness-authority reviewer | Vaulting and chunk creation are intake facts, not an affirmative CP-0 readiness verdict; deriving `CP-0 ready` locally would create another false green state. | Critical | Resolved in design | The Upload result may state processing, failure, partial vaulting, or not-ready. It may say CP-0 ready only if the response provides affirmative readiness prerequisites; otherwise it fails closed regardless of chunks/run queue state. |
| RT-2026-07-19-600 | Migration reviewer | Making `action_label` required would break historical rows, fallback producers, fixtures, and rolling deployments where old writers omit it. | Critical | Resolved in design | Add a nullable column and optional response/DTO field; rich current producers supply it, legacy/null events fall back to `Open related item`, and no client inference from href is allowed. |
| RT-2026-07-19-601 | Interaction reviewer | Renaming Command/Portfolio/Report actions without pinning effects can send empty users to no-op callbacks, persist a preview prematurely, or turn a drawer opener into an apparent mutation. | Critical | Resolved by contract tests | Test exact label→href/callback effects by state. Command uses real intake/worklist destinations; Portfolio preview remains non-mutating; one Report opener opens the room and only the drawer’s `Record IC decision` calls createDecision. |
| RT-2026-07-19-602 | Compliance-language reviewer | Replacing the MNPI claim with a softer badge alone still omits the crucial fact that the system does not detect classification or enforce a need-to-know wall. | High | Resolved in design | Add a keyboard-focusable limitations disclosure explicitly separating analyst declaration, detection, workspace access, governance, and entitlement enforcement; make no legal guarantee. |
| RT-2026-07-19-603 | Additive-schema reviewer | A downgrade that drops the new column while notification evidence exists could destroy producer-supplied labels or conflict with repository evidence-retention policy. | High | Resolved in design | Follow the additive migration convention: refuse destructive downgrade when populated labels exist, or otherwise drop only when safe; include chain and compatibility tests. |
| RT-2026-07-19-604 | Parallel-work reviewer | Upload, Command, Report, Portfolio, database and migration files all contain active remediation/user WIP; broad cleanup could erase unrelated authority and engine changes. | Critical | Resolved by execution constraint | Use narrow patches, preserve handlers/payloads, add a new migration rather than altering history, inspect explicit-path diffs, and run focused prior-task regressions before acceptance. |

Decision: proceed with fail-closed readiness, effect-pinned language, and a
nullable producer-owned notification label. Reopen if Upload infers CP-0 ready,
a label changes an underlying effect, historical notifications fail to render,
or the MNPI disclosure implies automated detection/entitlement enforcement.

## 2026-07-19 — Sector Review scenario-closure critic pass

Decision under review: close all seven scenarios for the nine current Sector
Review features while repairing context authority, failure visibility, and
publication-state defects found during assertion-level reconciliation.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-587 | Context-authority reviewer | A late history response from the previous analysis context can replace the active dossier, while changing only a URL section currently refetches the whole history and increases the race surface. | Critical | Resolve with generation ownership | Key history loading only to context/review authority, cancel superseded effects, keep section URL synchronization separate from fetching, and prove the newer context wins when promises settle out of order. |
| RT-2026-07-19-588 | Failure-state reviewer | Taxonomy/feed reads are silently converted to empty arrays and a rejected sector patch clears the visible dossier before persistence succeeds, making infrastructure failure look like authoritative absence. | Critical | Resolve fail closed | Surface bounded reference-data errors, preserve the current review until the context patch succeeds, disable re-entrant sector/feed mutations, and prove recovery re-enables the action. |
| RT-2026-07-19-589 | Data-boundary reviewer | `list_sector_reviews` applies the 100-row limit before filtering the requested context, so a valid older context can appear to have no history once other contexts accumulate enough versions. | Critical | Resolve in the query | Validate context ownership, filter the JSON `context_id` in SQL before ordering/limit, retain a defensive payload check, and exercise a target row beyond 100 newer distractors. |
| RT-2026-07-19-590 | Publication-authority reviewer | A published review is mapped to UNRATIFIED and falls back to a disabled Ratify updates control, contradicting the durable published state. | High | Resolve state semantics | Treat published authority as ratified for decision presentation and render no further ratification/publish action after publication; pin the post-publish state in the dossier test. |
| RT-2026-07-19-591 | Evidence-governance reviewer | Promoting all 40 designed scenarios from the existing happy-path cohort would overclaim invalid, permission, performance, responsive, and race behavior that those nodes do not assert. | Critical | Resolve assertion-by-assertion | Map only exact named nodes; add route-auth, malformed URL/source, duplicate-action/recovery, bounded server, cross-browser workflow, and exact-built axe evidence; retain a fail-closed 9-by-7 gate. |
| RT-2026-07-19-592 | Browser-fixture reviewer | A broad Playwright glob can miss queryless Axios traffic and silently exercise a developer database, while an overflow-only assertion can miss loss of narrow capabilities. | High | Resolve with exact predicates and capability inventory | Intercept pathname/method explicitly, record fixture hits, exercise all six tabs plus sector/feed/history/finalization controls at 390px, assert no document overflow, and visually inspect the narrow result after axe. |

Decision: proceed with context-owned async state, persist-before-clear sector
switching, SQL pre-limit context filtering, honest publication semantics, and
exact-node scenario mapping. Reopen if a stale response can change the active
context, a failed mutation erases prior evidence, the 63-row gate relies on
suite adjacency, or the narrow route loses a desktop capability without an
explicit alternative.

## 2026-07-19 — Monitor scenario-matrix closure

- Objection: mapping generic route evidence could overstate coverage for seven distinct Monitor contracts. Resolution: retain assertion-level mappings only; add direct invalid-URL and non-finite replay-KPI regressions; use the shared authentication gate, exact responsive route scan, and exact route performance audit only for the cross-cutting scenarios they actually prove.
- Objection: clamping all large ticks could mask a completed replay. Resolution: preserve the authored upper cap (`ALERTS.length`) and only normalize non-finite or negative ticks to the opening baseline; valid ticks and the inactive/completed branch remain unchanged.
- Objection: a zero-error performance sample alone would miss backpressure and recovery behavior. Resolution: the route audit is limited to UI responsiveness; any request-load exercise must separately report staged concurrency, expected backpressure, recovery, first-fault reproduction, and a post-load normal-user probe.

## 2026-07-19 — Pipeline scenario-matrix closure

Decision under review: close the 45-feature Pipeline matrix with assertion-level
frontend, API, browser, accessibility, and route-performance evidence while
repairing the defects found during reconciliation.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-608 | Evidence-governance reviewer | A route-wide browser or accessibility pass could be relabeled as endpoint validation or per-feature request-load proof. | Critical | Resolved by evidence boundaries | Use route/browser nodes only for composed UI, responsive, authentication, and cold-load scenarios. Map runs, modules, QA, issuer, and document API scenarios to exact server assertions; retain the staged-load protocol as a separate requirement and claim no Pipeline request-load result here. |
| RT-2026-07-19-609 | Simulation-contract reviewer | Normalizing `simClock` has a CRITICAL transitive graph and could alter every authored integer tick consumed by the shared simulation. | Critical | Resolved after direct-caller review | The four direct consumers supply authored non-negative integer ticks. The guard preserves every such tick and changes only fractional, negative, or non-finite input; the complete scheduler/simulation cohort and browser journeys pass. |
| RT-2026-07-19-610 | Narrow-workbench reviewer | Composing narrow essential controls with the full utility set duplicates progress, clearance, and Dependency map/Stage lanes controls in one phone dialog, creating ambiguous keyboard and screen-reader targets. | High | Resolved | CSS ownership now hides the desktop copies below `lg` while retaining run mode, simulation, clock, and dim controls. The 390px journey asserts exactly one Stage lanes control and passes in Chromium, Firefox, and WebKit; axe reports no duplicate-surface geometry or accessibility failures. |
| RT-2026-07-19-611 | Hostile-state reviewer | Unit coverage for individual widgets does not prove the assembled route survives an unsupported view, invalid stored preference, and adversarial context identifier. | High | Resolved | A composed-route regression falls back to Dependency map, remains explicitly non-running, preserves graph/inspector/evidence behavior, and proves the special context identifier is encoded in the Deep-Dive handoff. |
| RT-2026-07-19-612 | Static-artifact reviewer | Rebuilding while the validation server stays alive leaves stale CSP hashes and can make hydration failure look like a product defect. | High | Resolved by validation protocol | Restart the isolated FastAPI static server after every production artifact rebuild, then run browser, axe, and performance probes against the exact served artifact. |
| RT-2026-07-19-613 | Data-provenance reviewer | A fixture-backed Pipeline that appears by default can make reference execution state look like a live operational run, especially when its planned progress is non-zero. | High | Resolved | Live mode now stays honestly empty, reference data requires `mode=reference`, route handoffs preserve that mode, and the planned reference plan begins with zero executed modules. Focused, cross-browser, and responsive accessibility matrices pass. |
| RT-2026-07-19-614 | Publication-integrity reviewer | An immutable Report Studio deep link can race the active mutable draft, leaving publish briefly available for the wrong document state. | Critical | Resolved | Publishing is blocked while the requested immutable version is pending selection and remains unavailable after the immutable version is active. The complete affected Report Studio and responsive-recovery cohort passes 24/24. |
| RT-2026-07-19-615 | Accessibility-runner reviewer | A readiness contract limited to Enterprise/persona containers can hide standalone error, loading, or empty states from axe and turn real defects into scan errors. | High | Resolved | The runner now accepts `data-surface-state`, immediately exposed the Pipeline empty-state heading-order defect, and the standalone states use route-level h2 headings. The final six-state matrix is clean. |

Decision: proceed with the smallest storage, simulation-input, and narrow-control
repairs. Reopen if a valid authored tick changes, phone controls duplicate again,
an unsupported route value bypasses safe defaults, or workbook mappings conflate
route cold-load evidence with request-load or endpoint validation.

## 2026-07-19 — Monitor transport and global Ask bundle critic pass

Decision under review: correct the route-performance lab so it matches the
deployed Caddy gzip transport, then remove the closed global Ask surface from
the initial shared bundle without changing Ask state, hotkeys, route scope, or
analyst-visible behavior.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-620 | Measurement-validity reviewer | The prior Monitor result used an uncompressed development server even though the only supported public edge has `encode gzip`; treating 1,029KB and 6.18s LCP as deployed behavior creates a false product defect. | Critical | Resolved by transport-aligned protocol | Retain the raw result as diagnostic history, add a localhost gzip server that mirrors the checked-in edge setting, and require repeated cold-cache samples. Five current samples must stay explicit; no field-telemetry claim is made. |
| RT-2026-07-19-621 | Bundle reviewer | Compression can hide parse/evaluation cost, so closing the defect on encoded bytes alone could leave a large blocking shared shell. | High | Resolve with dual evidence | Continue reporting raw and encoded payloads, LCP, ready time, and TBT. Split only the closed heavy Ask surface behind the existing open state, rebuild the exact export, and accept the change only if the initial waterfall shrinks without moving work into an eagerly requested chunk. |
| RT-2026-07-19-622 | Ask-state reviewer | Moving a HIGH-risk shared context can create two providers, drop command-palette prefills, break Deep-Dive's inline chat, or change Escape/navigation/modal coordination. | Critical | Resolve through one context identity | Extract one provider/context module, re-export it from the legacy module for compatibility, update every production consumer to the same identity, and run provider, palette, Deep-Dive, hotkey, modal, prefill, pin-race, and browser regressions. |
| RT-2026-07-19-623 | Lazy-loading reviewer | A nominal dynamic import can still preload on route hydration, remove the phone trigger while loading, or make the first Ask interaction inaccessible. | High | Resolve by boundary and measurement | Keep the lightweight authenticated trigger and utility controls in the initial shell; render the dynamic Ask surface only after `open` becomes true; preserve focusable labels and loading status; verify the heavy chunk is absent from the closed Monitor waterfall and loads on an exercised Ask journey. |
| RT-2026-07-19-624 | Scope reviewer | A local gzip harness omits oauth2-proxy, WAN variability, cache/CDN policy, and production telemetry; passing it cannot prove population-level Core Web Vitals. | High | Accepted residual limitation | Label the result a constrained route lab, use p75 across five runs for the remediation gate, retain lack of field RUM as a low operational risk, and do not relabel this as request-load, backend-latency, or real-user evidence. |

Decision: proceed with the compatibility-preserving context/lazy-surface split
and transport-aligned measurement. Reopen if any Ask consumer resolves a
different context, the heavy Ask chunk is fetched while closed, the phone
trigger disappears, or the five-sample constrained-mobile p75 regresses.

## 2026-07-19 — Task 4A cold-state and control-consolidation critic pass

Decision under review: consolidate completion-evidence routes so each cold
surface presents one bounded setup path, while moving secondary actions behind
native disclosure controls and preserving every existing authority and mutation
contract.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-629 | Workflow reviewer | Removing duplicate empty frames can also remove the only recovery action or the only way to enter a workflow. | Critical | Resolve by action inventory | Preserve one reachable setup or retry action in the page header or consolidated state, then assert the action effect rather than only its label. |
| RT-2026-07-19-630 | Mutation-contract reviewer | Moving RV and Sector controls under `More` can silently change URL state, mutation keys, or keyboard reachability. | Critical | Resolve with native disclosure and effect tests | Use native `details`/`summary`, retain the existing handlers and tab identifiers verbatim, and exercise the hidden actions through the disclosure in interaction tests. |
| RT-2026-07-19-631 | Evidence-governance reviewer | Hiding inspectors in cold state could imply that evidence or governance has been discarded once real data arrives. | High | Resolve by data-gated composition | Suppress only zero-data shells; restore the existing inspector, visualization, and evidence components unchanged whenever the authoritative dataset exists. |
| RT-2026-07-19-632 | Responsive-layout reviewer | A desktop-only toolbar fix can still overlap at 200% zoom or when the persona grid narrows its container. | High | Resolve with container-aware wrapping | Keep filter sizing on flexible grid tracks, avoid fixed sibling widths, and verify Portfolio and Sector at real 200% zoom as well as 1440/1280/1024/768 CSS viewports. |
| RT-2026-07-19-633 | Parallel-WIP reviewer | These files contain accepted work from earlier remediation tasks; broad rewrites could erase exact action effects or cancellation semantics. | Critical | Resolve by surgical patches | Edit only the mapped render branches and styles, preserve existing handlers and authority disclosures, and run the affected regression cohorts plus a scoped diff review. |
| RT-2026-07-19-634 | Identity reviewer | Removing blank logo placeholders must not replace them with invented branding or derived images. | High | Resolve with text identity | Render the existing issuer name/ticker only unless a real asset is present; tests prohibit empty identity squares without asserting a fabricated logo. |

Decision: proceed with the narrow render and style changes above. Reopen if a
consolidated state loses its entry/retry action, a disclosure changes an action
effect, a populated dataset loses evidence context, or responsive browser
evidence shows overlap or full-height empty framing.

## 2026-07-19 — Task 4B flagship-workbench critic pass

Decision under review: reduce simultaneous control density in Deep-Dive, Model
Builder, IC Book, and Report Studio without weakening analyst authority,
evidence reachability, immutable publication, or desktop/tablet proofing.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-644 | Analytical-navigation reviewer | Collapsing seven Deep-Dive layers into three groups can hide modules or change the active live/reference decision region. | High | Resolved | Keep the finder, map every module into exactly one group, open the selected module's group, and prove all groups remain one disclosure away while existing evidence/live-reference contracts remain unchanged. |
| RT-2026-07-19-645 | Model-authority reviewer | Unmounting support drawers can discard analyst work, while moving Export can accidentally change checkpoint CAS, dirty-state, or unsaved-leave behavior. | Critical | Resolved | Drawer controls select presentation only; assumptions and scenarios continue to mutate the shared model controller. Save remains the sole primary, Export retains its existing handler under utilities, and focused regressions cover exclusivity, checkpoint behavior, history, evidence, and reset paths. |
| RT-2026-07-19-646 | Committee-workflow reviewer | Staging the agenda form can omit immutable references, submit a partial payload, or strand keyboard focus between steps. | Critical | Resolved | Retain one form state and the existing submit payload, validate the issuer/thesis boundaries before progression, move focus to each new step, expose Back plus one forward/save action, and cover permission and payload behavior in the complete IC Book cohort. |
| RT-2026-07-19-647 | Proofing-accessibility reviewer | Replacing static Report zoom choices can shrink committee text below its floor or make zoom value changes invisible to assistive technology. | Critical | Resolved | Bound proofing to 100–150%, make Fit respect the 100% floor, use one labelled native range with announced percentage, keep the preview as the named focusable horizontal scroll owner, and verify body/table/metadata floors under native 200% browser zoom. |
| RT-2026-07-19-648 | Responsive-shell reviewer | Dense flagship headers can pass unit tests yet clip the page primary at 1280px, tablet, or native 200% zoom. | High | Resolved | Use compact status presentation below the wide-workstation breakpoint without changing the primary label or effect, then gate exact production output at 1440/1280/1024/768 and native Chrome 200% with clipped-control and page-overflow assertions. |

Decision: Task 4B may close with the retained focused tests and browser
harnesses. Reopen if any Deep-Dive module becomes unreachable, switching Model
support surfaces loses controller state, an agenda step changes the final
payload, Report Fit drops below the proofing floor, or any page primary leaves
the desktop/tablet viewport.

### Task 4B independent-review repair addendum

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-649 | Catalog-integrity reviewer | The finder exposed all 27 modules while the three groups omitted CP-4C, CP-RENDER, CP-EXTRACT, and CP-DB, so a valid selection could expand a group that did not contain it. | Critical | Resolved with one derived partition | `DEEP_DIVE_MODULES` is now the shared Finder/workbench catalog. The three groups derive from canonical module layers; L0/ORCH/L1/INFRA map to Foundation, L2/L3/L4 to Analysis, and L5/L6 to Governance & Debate. Set equality, uniqueness, semantic assignments, and one-expanded-containing-group invariants cover every finder result. |
| RT-2026-07-19-650 | Workflow-evidence reviewer | Cold-route screenshots cannot prove populated Deep-Dive grouping or the staged IC form, and a visible fixture 404 undermines the claimed state. | High | Resolved with retained workflow harness | `validate-task4b-workflows.mjs` selects CP-4C through the real keyboard finder and opens Add agenda item through Tab/Enter at 1440/1280/1024/768. The shared browser fixture now returns the bounded empty analyst-opinion history used by IC Book; captures contain the populated Analysis group and open References step without a 404. |
| RT-2026-07-19-651 | Scroll-ownership reviewer | Populated CP-4C revealed eight horizontally overflowing output tables that were absent from cold-state axe evidence and unreachable by keyboard. | Critical | Resolved through actual-overflow ownership | Each output table measures horizontal overflow with resize/mutation observation and becomes a named focus target only while it clips. A regression proves the target appears on overflow and disappears when content fits; both populated browser matrices report zero serious nodes. |
| RT-2026-07-19-652 | Motion/reproducibility reviewer | Screenshots without machine-readable standard and reduced-motion results cannot substantiate the responsive workflow claim or be independently rerun. | High | Resolved with persisted evidence | The retained harness emits compact JSON plus screenshots and runs the same keyboard, axe, document-overflow, and clipped-control assertions under normal and reduced-motion media. Both eight-cell matrices are persisted under `DESIGN-IS-2026-07-19/captures/after/`. |

Decision: the independent Task 4B objection is closed. Reopen if the Finder and
group catalog cease sharing one source, any module appears zero or multiple
times, an overflowing output table loses its conditional focus contract, or a
workflow-state matrix gains an accessibility/layout failure.

### Task 4A reviewer-repair addendum

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-640 | Visual-system reviewer | Raising the Portfolio eyebrow from 9 px to 10 px preserves the same bespoke uppercase dialect instead of removing it. | High | Resolved | Removed every `portfolio-lab__eyebrow` render and rule; retained labels now use the shared `caos-panel-title` semantic tier. Focused DOM assertions and a zero-result source scan cover the contract. |
| RT-2026-07-19-641 | Cold-state reviewer | Hiding only stress leaves Context, Evidence Atlas, cited-brief, and dataset frames mounted around the no-portfolio explanation. | Critical | Resolved | The no-selection branch mounts one `PortfolioSetupState` as the sole Persona primary. An explicit DOM inventory prohibits every auxiliary frame/control and proves the setup message occurs once. |
| RT-2026-07-19-642 | Overflow-ownership reviewer | An absolute More popup inside the horizontally scrolling Sector tab rail can be clipped even when the closed-state route passes layout scans. | Critical | Resolved | More is now a sibling of a dedicated `[data-sector-tabs-scroll]` rail. The retained browser harness opens it and verifies effective ancestor clipping, viewport bounds, and ownership at four widths plus native 200%. |
| RT-2026-07-19-643 | Reproducibility reviewer | Temporary screenshots and prose claims do not let a later reviewer rerun or audit the zoom/menu gate. | High | Resolved | Retained `validate-task4a-portfolio-sector.mjs`, documented its deterministic command, and saved compact machine-readable output under `DESIGN-IS-2026-07-19/captures/after/`. |

Decision: Task 4A can close only with the retained harness, compact JSON,
144-test consolidated regression, and affected axe/layout matrix cited in its
report. Reopen if More returns under scroll ownership or a no-portfolio branch
mounts analytical supporting panes.

## 2026-07-19 — Report Studio authority-notice and scenario-closure critic pass

Decision under review: make the deliverables notice reflect the active report
authority, then close the 28-feature Report Studio scenario matrix using exact
frontend, server, browser, accessibility, and route-performance evidence.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-635 | Authority reviewer | The unconditional Atlas Forge QA-117 footer can appear beside live issuer reports and falsely imply a reference-only hold applies to the active run. | Critical | Resolve with explicit authority | Pass reference/live authority into `ReportList`; retain the CP-5 notice only for the reference template, show the real live committee hold when present, and otherwise state that live deliverables follow the active run gate. |
| RT-2026-07-19-636 | Evidence-governance reviewer | A route-wide axe or performance result could be relabelled as proof of immutable export, vault authorization, or server publication gates. | Critical | Resolve by evidence boundaries | Use route evidence only for responsive geometry, shared authentication, and cold-load behavior. Map immutable export, vault, ownership, rate, and committee gates only to exact component or server assertions. |
| RT-2026-07-19-637 | Responsive reviewer | Initial-route geometry can miss utility-drawer and sequenced-rail controls below the phone fold. | High | Resolve with capability-preserving source and interaction evidence | Retain the implemented column sequencing, verify every rendered control is unclipped in the exact phone scan, and map behavior-specific mobile claims only where the corresponding route/component assertion remains operable. |
| RT-2026-07-19-638 | Performance reviewer | One cold-load sample can hide variance, and a route timing result says nothing about request backpressure or export concurrency. | High | Resolve with repeated and layered evidence | Use five cold-cache constrained-mobile samples for route p75; keep renderer concurrency caps, pending-click suppression, autosave serialization, and endpoint rate limits as separate exact nodes. |
| RT-2026-07-19-639 | Applicability reviewer | Forcing mobile scenarios onto backend-only `/runs/{id}/report` contracts creates meaningless evidence and inflates coverage. | High | Resolve as explicit N/A | Mark only reports-26 and reports-27 responsive-not-applicable; their UI-consuming publication workflow remains covered by Report Studio route features. |

Decision: proceed with the authority-aware notice and assertion-level mapping.
Reopen if reference copy leaks into a live issuer, backend gates inherit route
evidence, a phone-only capability becomes unreachable, or the 28-by-seven gate
can pass without exact evidence for every applicable row.

## 2026-07-20 — Task 4C workflow-control critic pass

Decision under review: replace engine-centric Pipeline, Monitor, and Settings
composition with analyst-facing stages and controls while preserving every
execution, governance, permission, and persistence contract.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-653 | Dependency-model reviewer | Aggregating engine layers into analyst stages can reorder execution or omit modules, while bundled edges may falsely imply module-level dependencies. | Critical | Resolve with derived parity | Keep runtime plans untouched; map every canonical module into exactly one ordered stage, prove set equality and order, and label bundles as stage transfers with counts. |
| RT-2026-07-20-654 | Graph-accessibility reviewer | Dense labels or aggressive selection dimming can make the non-selected graph unreadable and leave a pointer-only map. | High | Resolve with peer semantics | Put full module labels before CP codes, retain keyboard node actions, keep unrelated nodes legible, and render the same ordered inventory as a semantic table. |
| RT-2026-07-20-655 | Governance reviewer | Suppressing an empty alert visualization can also suppress QA governance or conceal the distinction between no alerts and an unavailable feed. | Critical | Resolve by narrow data gating | Remove only the zero-row severity chart/table toggle; retain one explicit live-state message and keep the QA control-plane dataset in its persona-leading region. |
| RT-2026-07-20-656 | Settings-compatibility reviewer | Three primary tabs can orphan stored fields, break bookmarked `?tab=` URLs, or move actions across permission boundaries. | Critical | Resolve with alias and effect inventories | Use an explicit legacy-to-primary alias map, retain all existing panels and handlers under the three outcomes, and regression-test inventory, saved values, permissions, and mutation payloads. |
| RT-2026-07-20-657 | Diagnostics-disclosure reviewer | Moving implementation vocabulary can either leave code constants in primary copy or expose secret values in an expanded diagnostics surface. | Critical | Resolve with bounded disclosure | Keep existing non-secret configuration/status values under a native collapsed disclosure; expose no credential material and scan primary tab copy for environment/code vocabulary. |
| RT-2026-07-20-658 | Workflow-evidence reviewer | Cold screenshots and permissive fixtures can pass while populated workflows 404 or silently use an unintended route. | Critical | Resolve with failure-persistent browser proof | Exercise populated Pipeline, QA Monitor, and legacy Settings aliases by keyboard; prove fixture identity and exact/query route handling; fail on and persist every HTTP status at or above 400. |
| RT-2026-07-20-659 | Parallel-WIP reviewer | Broad page rewrites could erase accepted Monitor and Settings work already present in the dirty tree. | High | Resolve by surgical integration | Preserve existing outcome-copy and empty/governance branches, patch only the stage/tab composition seams, then inspect the scoped diff against `origin/main`. |

Decision: proceed with the bounded stage catalog, peer table, narrow empty-state
suppression, explicit aliases, and failure-persistent workflow harness. Reopen if
any canonical module or setting disappears, runtime ordering changes, QA loses
its leading governance surface, diagnostics expose secrets, or browser evidence
contains an unhandled HTTP failure.

## 2026-07-19 — P5 final verification and design-audit critic pass

Decision under review: declare the desktop/tablet remediation complete only
after a full all-route regression matrix and independent `$design-is` and
`$impeccable` evidence passes report no unresolved in-scope fault.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-19-660 | Evidence-validity reviewer | Cold-state screenshots alone can miss populated workflows, persona-specific priorities, open disclosures, and browser-only focus/overflow failures. | Critical | Resolve with layered evidence | Combine all-route viewport/axe evidence with populated Task 4A/4B/4C workflow harnesses, 18×3 persona assertions, keyboard walks, reduced motion, and native 200% zoom. Do not use one evidence type to stand in for another. |
| RT-2026-07-19-661 | Audit-independence reviewer | Letting the implementation author score its own chosen examples can hide the worst route and inflate Rams or Nielsen results. | Critical | Resolve through independent evidence fan-out | Use the five `$design-is` evidence roles, require exact sources and known gaps, score the worst representative instance, and keep Rams synthesis with the orchestrator. Run the `$impeccable` technical audit separately. |
| RT-2026-07-19-662 | Scope reviewer | Treating the excluded phone redesign as a release requirement would silently expand scope, while ignoring shared phone regressions could ship a broken shell. | High | Resolve by explicit boundary | Exclude phone-specific authoring, navigation, and review contracts; retain only mount, landmark, crash, existing-axe, and shared semantic smoke. Fix a shared failure without inventing a phone workflow. |
| RT-2026-07-19-663 | Truth-contract reviewer | A polished screenshot can still conceal seeded/live substitution, misleading action labels, or completion states that overclaim persistence or approval. | Critical | Resolve with exact behavior assertions | Re-run live/reference isolation, renamed-action, notification destination, upload-outcome, completion-axis, and authority tests; Copy & Honesty evidence must cite both label and behavior. |
| RT-2026-07-19-664 | Performance reviewer | A passing build and fast localhost sample do not prove changed routes stayed within the agreed startup-JS and long-task budget. | High | Resolve with bounded comparison | Report raw and encoded initial bytes plus attributed long tasks using the retained performance harness; compare to the recorded pre-remediation baseline where available and label any missing field telemetry as a limitation. |
| RT-2026-07-19-665 | Dirty-tree reviewer | The repository contains extensive parallel WIP; broad cleanup, staging, or a generated-file sweep could destroy unrelated work. | Critical | Resolve by non-destructive verification | Make only evidence or narrowly justified remediation edits, use `apply_patch`, inspect scoped diffs, do not stage or commit, and preserve every unrelated file. |

Decision: proceed with the locked 18-route evidence matrix and independent
audits. Completion is prohibited while any P0/P1, WCAG AA violation,
truth-contract mismatch, in-scope fault, or unexplained acceptance-gate failure
remains.

### P5 closure addendum — 2026-07-20

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-666 | Performance reviewer | The first P5 capture showed Reference Report at 640.8KiB encoded JS, which exceeded the recorded baseline and prohibited completion. | Critical | Resolved | Removed Report's startup dependency on the editor-grade G2 runtime and introduced an accessible first-party SVG/table renderer. Final Report JS is 261.3KiB, about 24.6% below the 354,855B comparator; visual, component, build, and browser gates pass. |
| RT-2026-07-20-667 | Zoom/reflow reviewer | A clean 768px synthetic matrix did not prove native 200% zoom; the 720px CSS viewport exposed an absent skip target and Command controls beyond the viewport. | Critical | Resolved | Compact skip navigation is target-aware, panel headers share the stacked reflow through 767px, and the coverage grid fits its guttered owner. The rerun passes all 18 routes at native/observed 2.0× with no clipping, overflow, or collisions. |
| RT-2026-07-20-668 | Design-system reviewer | Static source audit still found two undocumented graph-label colors despite the literal-color closure claim. | High | Resolved | Replaced both with `--caos-muted` and `--caos-text`. Impeccable detector now returns `[]`; Query visualization tests pass. |
| RT-2026-07-20-669 | Change-attribution reviewer | GitNexus `origin/main` comparison could fail in the unusually large parallel dirty tree, making a clean-scope claim unverifiable. | High | Accepted tool limitation with compensating evidence | The compare failed closed with `spawnSync git ENOBUFS`; the all-worktree scan completed at CRITICAL aggregate risk (716 symbols, 184 files, 46 processes) but includes unrelated WIP. No stage/commit occurred; exact impact was run before symbol edits, and 1,829 frontend tests, lint, TypeScript, build, browser matrices, and prior 2,592-test server run provide regression evidence. |

Decision: P5 may close. There are zero unresolved in-scope fault-register
findings. Absolute Portfolio startup weight, Model initial DOM, and Command CLS
are recorded as a bounded future REFINE opportunity, not silently promoted into
this remediation scope.

## 2026-07-20 — Impeccable performance-optimization critic pass

Decision under review: remove Portfolio's editor-grade chart runtime from the
startup path, then use measured evidence to decide whether Model DOM and Command
layout stabilization warrant similarly bounded changes.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-670 | Analytical-truth reviewer | A lightweight renderer can distort negative headroom, silently omit rows, or make distinct chart modes look equivalent. | Critical | Resolve with data-derived geometry | Derive every bar from the complete tabular fallback, retain a visible zero baseline for signed values, print each label and value, and preserve the mode title, unit, status, note, sources, and full equivalent table. |
| RT-2026-07-20-671 | Accessibility reviewer | Removing G2 can also remove the named image, summary relationship, keyboard table disclosure, or non-color status meaning. | Critical | Resolve with semantic parity | Keep the labelled figure and image region, `aria-describedby` summary, text status/glyph, native table-toggle button, and the existing `DominantTableRegion` fallback contract; add exact interaction tests. |
| RT-2026-07-20-672 | Performance reviewer | A code split can appear successful while the G2 chunk remains in Portfolio's route graph or another new dependency replaces it. | High | Resolve with production measurement | Remove Portfolio's runtime import of `SemanticVisualization`, inspect emitted route chunks, and repeat the retained production performance audit. Accept only measured startup JS below 500 KiB without a new long task. |
| RT-2026-07-20-673 | Model-workflow reviewer | Row virtualization can reduce DOM by breaking `aria-activedescendant`, paste ranges, arrow navigation, sticky labels, or source selection for off-screen cells. | Critical | Defer pending isolated design | Do not couple Model virtualization to the Portfolio repair. Prototype and test a virtual focus/scroll-to-selection contract separately before any Model edit. |
| RT-2026-07-20-674 | Responsive reviewer | Reserving Command height to suppress CLS can create a blank artifact frame or excessive tablet whitespace when the digest is empty. | High | Defer pending lifecycle trace | Measure the decision region from first paint through settled data and identify the shifting node before applying a breakpoint-aware minimum; reject a blind fixed-height patch. |
| RT-2026-07-20-675 | Dirty-tree reviewer | Broad dependency removal or shared chart rewrites can collide with accepted Monitor, RV, Research, and Deep-Dive work. | Critical | Resolve by route-local substitution | Leave the shared G2 renderer and package intact for other consumers; add one Portfolio-specific first-party renderer and patch only the Portfolio composition seam plus scoped styles/tests. |

Decision: proceed with the route-local Portfolio substitution and re-measure.
Model and Command optimization remain gated on separate evidence and must not be
declared complete from Portfolio results.

## 2026-07-20 — Pre-deployment latest-state reconciliation critic pass

Decision under review: promote the 19–20 July quality, browser, accessibility,
capacity, and data-mode work into the operative pre-deployment plan without
confusing a strong moving-worktree snapshot with an immutable release decision.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-676 | Release-integrity reviewer | The quality tracker reports 98% confidence, 683/683 features with direct automation, and zero open defects, but the application commit `f4c790f4` contains production files newer than the workbook seal. Treating the workbook as current release evidence would approve bytes it did not observe. | Critical | Resolved in plan design | Preserve the workbook as a dated 2026-07-19 evidence seal. The application tree is now commit-pinned, but the operative verdict remains NO-GO until H0 creates the canonical image/config manifest and L23/L27 regenerate the inventories and browser evidence against its digest. |
| RT-2026-07-20-677 | Test-governance reviewer | “Direct automation” can mean one exact assertion while 1,207 scenario rows remain Designed and 388 rely on suite evidence; it is not proof that every control succeeds, persists, fails safely, and recovers. | Critical | Resolved in evidence wording | Report the complete scenario-status distribution, keep source/control inventory separate from executed effect coverage, and require the missing route journeys plus current three-browser no-retry run before closing PD-02/PD-03. |
| RT-2026-07-20-678 | Accessibility reviewer | The prior 36-cell route matrix was clean, but the current export now has two serious target-size nodes and two narrow-layout failures. Carrying forward the older clean status would conceal a release regression. | Critical | Confirmed blocker | Archive `axe-2026-07-20.json`; add PD-10; require zero axe nodes, scan errors, clipped controls, and layout failures at desktop, 390px, coarse pointer, reduced motion, and native 200% zoom on the frozen candidate. |
| RT-2026-07-20-679 | Capacity reviewer | Three successful 300-user Postgres/two-worker repetitions after the middleware/pool fix are strong headroom evidence, but they used a dirty local topology, offline providers, 30 issuers, and did not prove the target image, storage, authenticated heavy-job burst, or host recovery. | High | Resolved in scope | Credit the result as fault-remediation evidence and strong support that 15 mixed users are below the measured read-path knee. Keep PD-07 open for the immutable target’s 15-principal heavy-operation/fault run and host telemetry. |
| RT-2026-07-20-680 | Code-health reviewer | The refreshed dependency walk still identifies 17 runtime-unreachable frontend paths, including large duplicate RV surfaces and a newly test-only color policy module; deleting them mechanically could remove framework/dynamic seams, while retaining them without owners invites fixes in code users never execute. | High | Confirmed blocker | Keep all 17 as candidates only. L24 requires owner-by-owner remove/restore/retained-support disposition and a post-disposition lint/type/unit/build/browser rerun. |
| RT-2026-07-20-681 | Data-governance reviewer | The new LIVE/REFERENCE controls improve authority disclosure but do not change custody: source bytes live in the vault, structured work product in Postgres, transient drafts in browser storage, and logs/backups in operator stores. | Critical | Resolved in storage wording; target control open | Retain the record-class custody matrix and prohibit “all data is in the vault.” PD-08 remains non-waivable until target encryption, retention/legal hold, paired backup freshness, alerting, and remote-only restore are evidenced. |
| RT-2026-07-20-682 | Recovery reviewer | Shared root/global error components and unit tests can be a valid alternative to eighteen bespoke boundaries, but six segment boundaries plus component tests do not prove that route failures preserve issuer/context/draft state in a real browser. | High | Confirmed blocker | Reframe PD-05 around deliberate boundary equivalence rather than raw boundary count. Close only with injected browser failures, preserved analyst context, named failed operation, and successful retry across every route class. |
| RT-2026-07-20-683 | Inventory reviewer | The 173-handler workbook count is broader than the older 137-route GitNexus map because aliases and current uncommitted handlers are represented differently. Publishing one number without method/alias semantics would create false drift. | High | Resolved in canonical-inventory rule | Use the current AST-derived tracker as the release inventory, retain method and trailing-slash aliases as distinct handler rows, and regenerate GitNexus/route parity after the candidate is frozen; explain count semantics in the closure report. |

Decision: update the plan and audit records, but retain **NO-GO**. The 19 July
E2E and 300-user results close historical defects on their tested snapshots;
the commit-pinned current application is stronger than the earlier moving tree,
but the current accessibility, target-host, data-custody, canonical-image, and
release-provenance gates remain open.

## 2026-07-20 — Report deliverable quality-restoration critic pass

Decision under review: restore the pre-`f4c790f4` filed-document density in
Report Studio preview without changing report truth, workflow chrome, or any
non-report surface.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-684 | Typography reviewer | Blindly shrinking all report text would recreate the older density but make editing and printed exports unreadable. | High | Resolve by mode separation | Apply the historical compact scale only to non-editing screen preview; retain the existing proofing/edit and print floors. |
| RT-2026-07-20-685 | Document-integrity reviewer | A visual rollback could also remove authority, freshness, evidence, immutable-section, or watermark behavior added after the older captures. | Critical | Resolve by CSS-only restoration | Change only `.rd-*` presentation rules; retain current JSX, data builders, authority blocks, citations, and export gates. |
| RT-2026-07-20-686 | Table reviewer | The enlarged scale causes the transaction table to wrap into scan-hostile fragments, but aggressive fixed widths could truncate issuer or instrument text. | High | Resolve through historical scale | Restore the proven prior font ratios and column spacing without adding clipping, ellipsis, or hard column widths. |
| RT-2026-07-20-687 | Accessibility reviewer | Compact visible ink can reduce citation and edit-control targets below the keyboard/touch contract. | Critical | Resolve by preserving controls | Keep counter-scaled 24px citation/revert hit areas and focus treatment unchanged; only inner document type changes. |
| RT-2026-07-20-688 | Print reviewer | Screen improvements can silently degrade PDF pagination or print sizes because the same `.rd-*` selectors feed the print portal. | Critical | Resolve by screen scoping | Scope the historical scale to `@media screen` and `.rd-paper:not(.rd-editing)`; leave print-root overrides intact and verify generated pagination. |
| RT-2026-07-20-689 | Scope reviewer | Editing shared shell, Report Studio controls, builders, or other surfaces would exceed the user's explicit report-only boundary. | Critical | Resolve by selector boundary | Touch only the report document CSS plus report-specific tests/evidence; do not change page composition, navigation, data, or workflow actions. |

Decision: proceed with a non-editing screen-preview type restoration. Reopen if
any report data, authority label, citation target, print floor, editor behavior,
or non-report surface changes.

## 2026-07-20 — Earnings Update analytical-density critic pass

Decision under review: expand the Earnings Update deliverable to an eight-quarter
operating dashboard, LTM analyst-model comparison, and rolling-LTM leverage view
without changing another report or any Report Studio workflow behavior.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-690 | Credit analyst | A denser top sheet can present quarterly and LTM figures as comparable when their bases differ. | Critical | Resolve with explicit bases | Put quarter, QoQ, YoY, LTM, and LTM YoY in named columns; reserve basis-point deltas for margin rows and multiple deltas for leverage/coverage. |
| RT-2026-07-20-691 | Model-governance reviewer | Reusing the existing quarterly saved-base variance would continue the false implication that the analyst model is a quarter model. | Critical | Resolve with LTM-only comparison | Replace the variance section with a clearly titled saved-analyst-LTM versus actual-LTM table and state the as-of period in both columns. |
| RT-2026-07-20-692 | Data-truth reviewer | Eight leverage points cannot be manufactured when the rolling-LTM calculation begins only after four normalized quarters. | Critical | Resolve by honest availability | Render the six available rolling-LTM periods (Dec-24 through Mar-26), disclose why earlier periods are absent, and never backfill invented leverage. |
| RT-2026-07-20-693 | Visualization reviewer | Four leverage/coverage lines with no point values are hard to read; adding labels can create collisions and illegible ink. | High | Resolve with report-scale chart geometry | Use one shared scale, distinct signal colors, period-aligned series, visible formatted point values, a text legend, and a taller chart region. |
| RT-2026-07-20-694 | Accessibility reviewer | A long-form equivalent table forces screen-reader users to reconstruct each period and conflicts with the visual comparison. | Critical | Resolve with opt-in transpose | Add an opt-in report-chart table orientation that renders metric rows and period column headers; leave every existing chart table unchanged. |
| RT-2026-07-20-695 | Scope reviewer | A shared visualization rewrite could alter other deliverables despite the report-only request. | Critical | Resolve by additive flags and exact tests | Gate point labels and transposed tables behind new chart-section flags used only by Earnings Update; retain all existing defaults and add non-regression assertions. |

Decision: proceed with the Earnings Update-only data contract and additive chart
flags. Reopen if another deliverable changes, unavailable leverage is synthesized,
or the analyst comparison returns to quarterly basis.

## 2026-07-20 — Committee-deliverable editorial refactor critic pass

Decision under review: give each Reference-mode committee paper one distinct
decision job, shorten the IC memo, turn Monitoring into an exceptions report,
add governed scenario/trade/evidence papers from existing data, and preserve the
Report Studio shell unchanged.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-696 | Committee-chair reviewer | Removing repeated diligence material can make the memo shorter while also deleting the facts needed to challenge the recommendation. | Critical | Resolve through layered papers | Lead with decision, sizing, contested claims, downside, and approval conditions; retain exact supporting facts in named scenario, covenant, earnings, evidence, and model papers rather than deleting them from the packet. |
| RT-2026-07-20-697 | Truth-contract reviewer | A polished Monitoring exceptions sheet can imply live observations even though the report builder contains seeded reference facts and no observation service. | Critical | Resolve with explicit reference/as-of language | Label every observation as a reference observation with an as-of date, distinguish observed, pending, and unresolved states, and never describe the paper as a live feed or successful current check. |
| RT-2026-07-20-698 | Evidence-governance reviewer | Adding evidence counts or a QA certificate can falsely imply claim-level coverage that the current report DSL cannot compute. | Critical | Resolve through bounded claims | Publish the document inventory, registered evidence IDs, open QA item, and explicit limitation that claim-level coverage is not computed; do not convert counts into a pass state. |
| RT-2026-07-20-699 | Analytical-visualization reviewer | Adding charts to every paper would replace one form of ceremony with another and can obscure exact legal or financial values. | High | Resolve by medium discipline | Use charts only for time paths, capacity composition, recovery erosion, or scenario comparison; keep transaction terms, exact clauses, triggers, and the raw model tabular. |
| RT-2026-07-20-700 | Consumer-compatibility reviewer | Renaming or adding deliverables can break id-based selection, first-report fallback, frozen previews, or Pipeline/Deep-Dive consumers. | Critical | Resolve with stable identifiers and dispatch tests | Preserve all six existing ids and fallback order, append new ids, keep the shared `Report`/`Section` contract unchanged, and assert exact dispatch for every returned paper. |
| RT-2026-07-20-701 | Earnings-basis reviewer | Separating quarterly and LTM credit data can accidentally remove the eight-quarter operating detail or recreate unavailable historical leverage. | Critical | Resolve with explicit bases and honest periods | Keep the transposed eight-quarter table, move leverage/coverage into named rolling-LTM regions, show only the six available periods, and retain the saved-analyst LTM comparison. |
| RT-2026-07-20-702 | Scope/parallel-WIP reviewer | Shared report CSS, renderer changes, or broad cleanup could alter Report Studio chrome or overwrite the earlier Earnings work and unrelated QA WIP. | Critical | Resolve by builder-local implementation | Reuse the existing report DSL and lightweight chart primitives; edit the builder and focused tests only unless rendered evidence proves a report-paper defect, and inspect scoped diffs without staging unrelated files. |

Decision: proceed with stable report ids, explicit Reference observation
language, bounded evidence claims, chart/table/narrative discipline, and
builder-level regression tests. Reopen if the shell changes, a seeded fact is
described as live, evidence counts are presented as coverage, or a supporting
fact becomes unreachable from the committee packet.

## 2026-07-20 — Snapshot restoration and consolidated IC memo critic pass

Decision under review: restore the pre-editorial Credit Snapshot as page one,
retain the newer decision view as page two, and expand the IC Credit Memo into a
consolidated Deep-Dive record with a deliberately short historical/LTM/scenario
model.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-703 | Portfolio-manager reviewer | Putting the original binder-style snapshot first can bury the action and make page two feel like an appendix rather than the decision. | High | Accepted by explicit user direction with navigation guard | Restore the original page verbatim in structure, label the newer page `Decision View`, and retain its decision-at-a-glance opening so the two-page document has distinct reference and action layers. |
| RT-2026-07-20-704 | Committee-chair reviewer | A consolidated memo can become a document dump that repeats every supporting paper without a committee narrative. | Critical | Resolve with six named decision stages | Organize the memo as Decision, Business & Earnings, Risk & Challenge, Capital & Documentation, Compact Model, and Committee Controls; include only the evidence needed to challenge or authorize the recommendation. |
| RT-2026-07-20-705 | Model-governance reviewer | Calling the model short while carrying the full raw appendix would contradict the requested deliverable and recreate the earlier overload. | Critical | Resolve with a bounded period-and-line contract | Include FY22A–FY25A, latest LTM, FY26e–FY28e base, and FY26e–FY28e downside across a compact set of operating, cash-flow, balance-sheet, leverage, and coverage rows; leave the full model in Model Appendix. |
| RT-2026-07-20-706 | Truth-contract reviewer | A compact table can imply that historical, LTM, and forecast columns share the same status or source basis. | Critical | Resolve with visible period groups and basis note | Mark Historic, Latest LTM, Base case, and Downside case column groups, use actual/estimate suffixes, and disclose that Reference inputs are seeded unless a persisted CP-1 anchor is supplied. |
| RT-2026-07-20-707 | Renderer reviewer | Adding page groups to Credit Snapshot would make the shared paged masthead falsely label it `IC CREDIT MEMO`. | High | Resolve with report-derived masthead identity | Render the paged masthead from the actual report title; add a renderer regression assertion so Snapshot and Memo keep their own identities. |
| RT-2026-07-20-708 | Scope/parallel-WIP reviewer | Restoring removed helpers or touching shared paper rendering can collide with the larger dirty tree and alter unrelated surfaces. | Critical | Resolve with narrow symbol restoration | Reintroduce only the report-paper helpers required by Snapshot/Memo, change only the paged-paper title string in the renderer, update focused tests, and do not stage or commit unrelated work. |

Decision: proceed with the user-directed two-page Snapshot and six-stage IC
Memo. Reopen if the current decision view is lost, the compact model omits any
requested basis, the full raw model returns to the memo, or another Report
Studio surface changes.

## 2026-07-20 — Snapshot recommendation and analyst-thesis custody critic pass

Decision under review: apply the supplied five-point recommendation guidance to
Credit Snapshot only, separate the system-generated thesis from the analyst's
authored thesis, and make a manual thesis version durable in both Postgres and
the configured analyst vault before it appears as saved report composition.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-709 | Methodology reviewer | The supplied image defines three ordinal scales but no formula for combining fundamentals and valuation. Inventing an average or lookup rule would turn visual guidance into an unsupported model. | Critical | Resolve without inference | Present the three scales exactly as guidance, state that the recommendation is a joint analyst assessment, and do not calculate or imply a mechanical mapping. |
| RT-2026-07-20-710 | Deliverable-scope reviewer | `companySummarySections` also feeds the IC Memo, so a shared edit could silently alter a deliverable the user did not ask to change. | Critical | Resolve with a Snapshot-only option | Gate the COAS recommendation profile and methodology table behind an explicit Snapshot option; keep the Memo's existing company summary unchanged. |
| RT-2026-07-20-711 | Authorship reviewer | Renaming the generated paragraph while leaving it in the editable Investment Thesis field would continue to blur system analysis with the analyst's own view. | Critical | Resolve with two fields | Move the existing generated narrative to `COAS THESIS` immediately above Credit Summary; keep `INVESTMENT THESIS` in its prior location with an empty, clearly authorable body and unchanged catalysts block. |
| RT-2026-07-20-712 | Data-custody reviewer | Report-draft autosave is a Postgres composition record, not a vault write. Claiming that an inline edit is vaulted merely because it appears after reload would be false. | Critical | Resolve with vault-gated manual versions | Route non-empty analyst-thesis edits through the existing manual thesis-version API, require a configured writable vault, write an append-only Analyst-Memos note, then accept the report overlay only after that operation succeeds. |
| RT-2026-07-20-713 | Workflow reviewer | Making the shared `create_thesis_version` helper always require a vault would break decision and committee system events that create governed thesis history without direct user authorship. | Critical | Resolve at the public manual route | Keep the shared helper DB-only. Add vault custody only to user-authored `POST /api/thesis` manual submissions so automated decision/alert paths retain their current contract. |
| RT-2026-07-20-714 | Failure-consistency reviewer | A filesystem write and database transaction cannot be committed atomically; a late DB commit failure can leave an orphan note, while accepting the report edit before the vault succeeds can leave a false saved state. | High | Mitigate and fail closed in UI | Check configuration before creating the row, write after the version is flushed, fail the request if the vault write fails, and only add the Report Studio edit after a successful response. Preserve append-only notes for reconciliation rather than risk deleting a durable analyst record after an ambiguous commit failure. |
| RT-2026-07-20-715 | Accessibility reviewer | A truly empty contenteditable paragraph can collapse to an invisible target, so the requested blank field may not be discoverable by keyboard or sighted users. | High | Resolve with non-persisted placeholder | Add an accessible placeholder and minimum editable area in edit mode; keep the persisted base value empty so placeholder copy never enters the report or vault. |
| RT-2026-07-20-716 | Reference-truth reviewer | Reference mode can tempt the UI to simulate a successful vault save even when its fixture issuer is absent from the live database. | Critical | Resolve by using the real API boundary | Never synthesize success. Submit against the report's issuer id and restore the blank field with an explicit failure message if tenancy, issuer existence, or vault configuration rejects it. |

Decision: proceed with a Snapshot-only methodology, explicit system-versus-
analyst thesis fields, and fail-closed manual thesis custody. Reopen if any
combination formula is invented, the Memo changes, a blank placeholder is
persisted, or Report Studio claims success before both the thesis version and
vault note have been accepted.

## 2026-07-20 — Snapshot thesis hierarchy refinement critic pass

Decision under review: leave the analyst-authored Investment Thesis as the only
thesis in its authoring area, reserve visible writing space above catalysts, and
move the generated COAS Thesis into the left summary column directly above the
Credit Summary.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-717 | Authorship reviewer | Moving the analyst field into a nested column would change its stable edit path and could bypass the existing vault-backed save contract. | Critical | Resolve by keeping it top-level | Keep `issuer-investment-thesis` as the same top-level section; move only the generated COAS paragraph into the summary column. |
| RT-2026-07-20-718 | Committee-document reviewer | Moving Credit Summary lower without a clear local hierarchy could separate the section from the system conclusion it is meant to substantiate. | High | Resolve through adjacency | Put COAS Thesis first and Credit Summary second in the same left column, while Financials remains the parallel right column. |
| RT-2026-07-20-719 | Report-renderer reviewer | A blank thesis value collapses in preview, so the document can satisfy the data contract while still providing no visible writing area. | High | Resolve with field-scoped space | Add a report-field marker and reserve 3.25em only for the analyst thesis body; do not persist filler text or change other report sections. |
| RT-2026-07-20-720 | Scope reviewer | Shared report styling could alter another deliverable or Report Studio chrome. | Critical | Resolve with an exact selector | Scope the minimum height to `[data-report-field="issuer-investment-thesis"]`; keep all shell, workflow, and other deliverable composition unchanged. |

Decision: proceed with the field-scoped paper spacing and Snapshot-only section
move. Reopen if the analyst edit path changes, COAS Thesis remains in the
authoring area, or another deliverable's layout changes.

## 2026-07-20 — Snapshot methodology removal critic pass

Decision under review: remove the Recommendation Methodology table from Credit
Snapshot without changing the recommendation itself.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-721 | Credit analyst | Removing the table could accidentally remove the requested CLO, Indexed Loans, and Index HY recommendation rows that use the same Snapshot option. | High | Resolve by section-only removal | Retain the Snapshot-specific recommendation rows and remove only the methodology section from the returned section list. |
| RT-2026-07-20-722 | Scope reviewer | A shared summary-builder edit could change the IC Memo. | High | Resolve with regression coverage | Assert the Memo recommendation remains unchanged and neither deliverable contains the removed methodology title. |

Decision: proceed with section-only removal. Reopen if any recommendation row
changes or if the IC Memo is altered.

## 2026-07-20 — PD-10 narrow-shell, containment, and selection critic pass

Decision under review: close the current PD-10 rendered defects with two
shared but breakpoint-scoped layout constraints: give a very narrow
fine-pointer header a second row, and cap narrow PersonaWorkbench primary slots
to their available inline size so dense tables keep their own scroll region;
also prevent a settled Report Studio preview from reapplying an already-served
deep-link selection over the analyst's newer choice.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-723 | Navigation reviewer | Wrapping the shared header can hide the primary action or make the current workflow inaccessible on routes other than Decisions and Settings. | Critical | Resolve with a narrow fine-pointer scope and full route matrix | Scope the second-row rule to `max-width: 480px` with a fine pointer, keep identity and action in normal DOM order, and run all 18 routed surfaces at desktop and 390px after the change. |
| RT-2026-07-20-724 | Dense-table reviewer | Constraining the primary slot can compress a specialist table until columns or controls disappear instead of becoming reachable by horizontal scroll. | Critical | Resolve by preserving descendant scroll ownership | Set only the slot's inline size/max-inline-size; do not change table minimum widths or column contracts. The rendered gate must report no clipped controls and the existing table scroll owners must remain keyboard-focusable. |
| RT-2026-07-20-725 | Capability reviewer | A phone fix could replace Command or Monitor functionality with a summary and pass geometry while removing analyst actions. | Critical | Resolve without conditional rendering | Make no React or route-composition changes. Verify the Command worklist controls and Monitor Ack/Assign/Resolve/desktop-handoff controls remain rendered and reachable. |
| RT-2026-07-20-726 | Zoom and pointer reviewer | A rule tuned to Playwright's default fine pointer may pass the audit while breaking the coarse-pointer phone or native 200% zoom contracts named by PD-10. | High | Resolve with separate modes | Keep the existing coarse-pointer chip-hiding contract unchanged, then verify coarse-pointer 390px plus the existing native/synthetic 200% zoom lane in addition to the default matrix. |
| RT-2026-07-20-727 | Report-proofing reviewer | The filed-preview density layer can preserve geometry while leaving Report Studio prose and tables below the repository's own legibility floor at native 200% browser zoom. | Critical | Resolve with a zoom-shaped proofing override | Preserve compact filed density on ordinary desktop screens, but restore the base report type scale in the narrow fine-pointer viewport produced by native 200% zoom; rerun the dedicated headed-Chrome audit across all 18 routes. |
| RT-2026-07-20-728 | Report-authority reviewer | Treating the query-string report as permanently authoritative can overwrite a deliberate immutable-version selection after an unrelated preview rebuild; treating it as one-shot intent can instead make the URL appear stale. | High | Resolve in favor of explicit analyst action and prove provenance rebinding | Apply the deep link when its target becomes available or when the parameter changes, then let the analyst's later selection win. Verify `aria-current`, exact artifact freshness, shared run identity, and 10 consecutive zero-retry transitions. Keep URL synchronization as a separate navigation-contract decision rather than silently mutating history in this fix. |

Decision: proceed with breakpoint-scoped CSS and reopen if any routed surface
loses its primary action, a dense table loses its scroll owner, or either
pointer/zoom mode remains unverified. Reopen the report-selection decision if
the route contract is changed to require every in-page selection in browser
history.

## 2026-07-20 — PD-04 reachability disposition critic pass

Decision under review: remove production modules whose only incoming edges are
tests or another unreachable module, remove their false-signal tests, and retain
the color-literal policy as an explicitly owned test-support seam.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-729 | Framework reviewer | A file with no static importer may still be a Next.js root, dynamic import target, script input, or string-addressed registry member. | Critical | Resolve before deletion | Check framework routes, `dynamic()`/`import()` forms, scripts, package metadata, string references, and GitNexus incoming edges. None of the removal candidates is a route/config root or dynamic target; all primary-export impacts are LOW with no indexed process participation. |
| RT-2026-07-20-730 | Product reviewer | Removing the old Sector RV or Query components could silently remove a promised analyst capability even if the current route does not import them. | Critical | Resolve against the mounted replacement and promise ledger | `/sector-rv` mounts `RVScreenerWorkbench`; the old Command `SectorRV` cluster is superseded and explicitly listed as non-runtime in the mock/review ledgers. The abandoned two-lane `LaneRouter` conflicts with the mounted three-lane Query workbench. Removal makes the runtime promise clearer rather than reducing it. |
| RT-2026-07-20-731 | QA reviewer | Deleting tests with dead implementations can make the suite greener by shrinking evidence rather than improving shipped coverage. | High | Resolve with explicit test-count accounting | Delete only tests whose subject is removed, trim mixed test files surgically, report the expected test-count reduction, and require every remaining test to pass with retries disabled. Do not present the lower count as coverage growth. |
| RT-2026-07-20-732 | Governance reviewer | `color-literal-policy.ts` is production-unreachable by design but enforces a release policy; deleting it would weaken the token gate. | High | Retain with rationale | Classify it as an owned test-support seam. Keep its full production-tree scan and record that test-only reachability is intentional; do not suppress or pretend it is runtime code. |
| RT-2026-07-20-733 | Recovery reviewer | Shared `EvidenceInspector` and `RecoveryState` names look architectural; future recovery/error plans may assume they are already live. | High | Remove stale prototypes and preserve live primitives | Verify no production consumer and retain the mounted `SurfaceState`, `DecisionHeader`, `ConclusionAuthority`, and route-specific evidence/recovery implementations. Update mixed smoke tests so they cover only shipped surfaces. |

Decision: proceed with the verified removal set and one retained test-support
seam. Reopen if build output, route inventory, direct/dynamic reference scans,
or no-retry tests reveal any runtime dependency.

## 2026-07-20 — L27 routed-journey expansion critic pass

Decision under review: add deterministic browser journeys for Decisions,
Portfolios, Issuer Profile, Sector RV, and Sponsors, include them in the
production-like three-browser runner, and add recovery assertions without
weakening the immutable-candidate gate.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-734 | Integration reviewer | Frontend-intercepted API fixtures prove browser behavior, not that the FastAPI implementation, migrations, and seeded H0 data satisfy the same contracts. Treating these tests as PD-02 closure would be false assurance. | Critical | Keep the evidence boundary explicit | Use deterministic fixtures as per-PR route-contract coverage only. Keep PD-02 open until the same primary journeys and affected states pass without retry against the frozen H0 image and its real API/data setup. |
| RT-2026-07-20-735 | Test-isolation reviewer | A broad Playwright glob can miss an Axios request without a query delimiter and silently read a developer database, making a green run non-deterministic. | Critical | Fail closed on every local fixture | Match exact URL pathnames or anchored pathname regexes, register a final `/api/` oracle, allow only authentication calls through, and assert that the unhandled-request ledger is empty in every journey. |
| RT-2026-07-20-736 | State reviewer | Sharing one analysis context or analyst identity across routes/browsers can let a prior journey overwrite selection state and make later tests order-dependent. | High | Isolate route state | Give every route fixture a distinct context and keep tests independent. The production-like runner continues to allocate browser-specific principals and storage states. |
| RT-2026-07-20-737 | Release-runner reviewer | Adding specs to the default Playwright discovery while omitting them from the hard-coded production-like lanes recreates the current partial-suite problem. | Critical | Update the checked-in lane inventory | Add the routed-journey spec to an explicit inventory lane and retain `--retries=0` for every browser project. Do not claim H0 coverage from the default retry-enabled config. |
| RT-2026-07-20-738 | Recovery reviewer | API error-state retries are not equivalent to a Next.js segment error boundary. Adding a test-only production throw switch would itself create an unsafe hidden interface. | Critical | Separate the two claims | Add honest route-level failure/preservation/retry coverage where the shipped UI exposes it. Do not add a production backdoor. Keep PD-05 open until a browser-safe boundary-injection method proves the shared/root/segment equivalence on H0. |
| RT-2026-07-20-739 | QA reviewer | One oversized test can claim five journeys while only checking page headings, adding runtime without behavioral evidence. | High | Require one primary interaction per route | Each route must assert a route-specific dataset and complete at least one real control transition; recovery coverage must assert preserved selection plus successful retry, not only an error label. |
| RT-2026-07-20-740 | Authentication reviewer | A fourth production-like lane would authenticate all three configured projects during each of twelve single-project invocations, consuming 36 shared credential attempts and crossing the 30/minute backstop before the browser work begins. | Critical | Constrain setup to the invoked project | The runner passes its fixed browser project through `E2E_ONLY_PROJECT`; global setup requires exactly one matching project in that mode. The four-lane matrix now consumes 12 setup logins, while ordinary all-project invocations retain the default three-project behavior. |
| RT-2026-07-20-741 | Test-isolation reviewer | A sparse analysis-context patch fixture that replaces nested objects instead of using the server's deep-merge semantics can alternately erase sponsor artifact and surface state, producing a request loop that continues after the visible assertions and may escape during teardown. | Critical | Mirror merge semantics and require convergence before evidence capture | The fixture recursively merges sparse nested fields while ignoring `expected_revision`, matching the server contract. The Sponsor case counts exact intercepted context PATCHes and waits for exactly one synchronization write before checking unhandled requests, page exceptions, and console errors. Generic `networkidle` is rejected because Profile/Sponsors maintain prefetch traffic. The isolated server log is inspected after shutdown; a late API request is a failed fixture-boundary gate even if it returned 404. |

Decision: proceed with the deterministic route-contract layer and runner
inventory update, but do not close PD-02 or PD-05 from intercepted fixtures.
Reopen if any unhandled API request can fall through, a journey shares mutable
state, or the production-like runner does not execute the new cases with zero
retries in Chromium, Firefox, and WebKit.

## 2026-07-20 — PD-05 browser-boundary injection critic pass

Decision under review: prove the shipped Next.js global and shared route-error
contracts in a real browser by rewriting one exact exported JavaScript response
inside Playwright, arming a session-scoped one-shot render failure, and then
verifying recovery against the real authenticated API without adding any
runtime fault flag or test branch to production source.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-742 | Security reviewer | A query parameter, environment flag, global production hook, or checked-in throw branch would create a hidden denial-of-service interface in the release artifact. | Critical | Resolve outside production source | Inject only by Playwright response rewriting after the browser requests a same-origin exported chunk. Production source and built bytes contain no fault switch; the test fails unless one exact compiled component-body token is found. |
| RT-2026-07-20-743 | Framework reviewer | Throwing from an API callback or event handler does not exercise a React/Next error boundary and could falsely close PD-05. | Critical | Throw during component render | Patch the reports page's exported render function for the segment case and `WorkflowRail` for the root-layout case. Require the shipped `RouteErrorBoundary` and `global-error` copy respectively before retrying. |
| RT-2026-07-20-744 | Build-integrity reviewer | A loose string replacement can patch the wrong chunk, patch several modules, or silently stop working after minifier changes. | Critical | Fail closed on exact cardinality | Identify target and boundary chunks by route-specific sentinels, require exactly one compiled component-body match and one reset-handler match, rewrite only the first response for each, record both URLs, and assert exactly two rewrites. A missing or ambiguous token aborts the browser test rather than degrading to a green no-fault run. |
| RT-2026-07-20-745 | State reviewer | A successful retry can still discard the selected issuer, analysis context, report selection, or server draft while the generic error screen appears healthy. | Critical | Seed and reread durable state | Create an owned analysis context and revision-1 report draft through the authenticated API; let the page reach its committed pre-failure baseline, then assert the exact URL/context, selected `memo` deliverable, source preference, edit count, and persisted payload survive recovery. |
| RT-2026-07-20-746 | Side-effect reviewer | Hydration plus boundary reset can mount the route twice and duplicate autosave, context patch, publication, or other writes. | Critical | Count exact browser writes and revision delta | Record the settled pre-failure draft revision and mutation ledger, require the failure-triggering render to add no write, then require exactly one recovery autosave, no publication write, no repeated mutation path, and a final revision exactly one above baseline. |
| RT-2026-07-20-747 | Recovery-loop reviewer | A transient one-shot throw may disappear during React's internal render retry before the error fallback commits; a persistent throw can instead loop forever when the analyst selects retry. | High | Persist until the explicit boundary reset | The exported chunk is inert during hydration and throws on every render only after the test arms it. The test-delivered boundary chunk wraps the shipped reset handler solely to mark the injector consumed immediately before calling Next's real `reset()`, producing a stable visible fallback followed by one recoverable retry. |
| RT-2026-07-20-748 | Evidence reviewer | One reports test cannot prove that six source files with similar markup remain equivalent. | High | Bind browser proof to the shared implementation map | Retain the source-level six-surface delegation test and require all six exported boundary chunks to carry the same shipped recovery body. The browser segment case proves that shared implementation; the root/shared-layout case separately proves `global-error`. |

Decision: proceed with test-only chunk response rewriting and keep PD-05 scoped
to the current working tree until all three browser engines pass without retry.
Do not claim H0 closure until the same lane is rerun against the frozen image
digest. Reopen if production source gains a fault hook, cardinality is not exact,
the persisted draft advances by more than one revision from its pre-failure baseline, or any engine requires a
Playwright retry.

## 2026-07-20 — PD-01 immutable app-resource critic pass

Decision under review: change only the application image to use a repository-
root, deny-by-default build context, bake the exact methodology and RV reference
resources consumed at runtime, and gate CI with a probe executed as the image's
non-root runtime user. Do not deploy or broaden the backup-service contexts in
this tranche.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-749 | Supply-chain reviewer | Widening the app context from `caos/` to the repository root can send `.git`, credentials, local databases, virtualenvs, test output, and agent artifacts to BuildKit even if the Dockerfile never copies them. | Critical | Resolve with an allow-list context API | Add a repository-root `.dockerignore` that denies `**` first and re-includes only the frontend build inputs, runtime server files, exact prompt inputs, the RV JSON, and the app Dockerfile. Retain `caos/.dockerignore` for the still-`caos/` backup contexts. |
| RT-2026-07-20-750 | Runtime-integrity reviewer | A host bind mount makes prompt bytes and permissions independent of the image digest, so an H0 digest would not identify the methodology actually used. | Critical | Bake resources into the image | Copy `Modular OS` into `/Modular OS` and the single RV JSON into the consumer's exact `/frontend/src/lib/command/market-data.json` path. Add no production bind mount. |
| RT-2026-07-20-751 | Prompt-governance reviewer | Copying only `*_ACTIVE_PROMPT.md` files is insufficient for CP-2G/CP-4D, whose loader requires exact manifest membership, shared governance preamble, and valid hashes. | Critical | Re-include complete governed bundles | The root allow-list includes every legacy Active Prompt, full CP-2G and CP-4D directories, and `CP-COMMON_PREAMBLE.md`. The in-image probe imports `load_prompt_bundle` for both specialized modules so missing, extra, or hash-drifted members fail. |
| RT-2026-07-20-752 | Build reviewer | A Dockerfile `test -f` running as root can pass while UID 10001 cannot read the resource or while the real Python consumer resolves another path. | Critical | Probe through consumer imports as the runtime user | Run the reusable probe with the image's configured user and import `prompt_corpus_fingerprint`, `load_prompt_bundle`, and `routes.rv._REFERENCE_PATH`. Require a non-`noprompts` fingerprint, both bundles, valid JSON, and a non-empty row set. |
| RT-2026-07-20-753 | Context-isolation reviewer | Changing every Compose build to repository-root paths in one patch can break backup and backup-sync Dockerfiles whose `COPY deploy/...` paths assume the existing `caos/` context. | High | Keep this tranche app-only | Change only `services.app.build.context` and the CI app-image context. Leave both backup contexts and `caos/.dockerignore` intact; broader hardening remains a separately reviewed rollout. |
| RT-2026-07-20-754 | CI reviewer | `docker/build-push-action` with `push: false` does not automatically make an image available to a later `docker run`, so a documented probe step could never execute. | High | Load and tag the CI image explicitly | Set a local CI tag and `load: true`, then invoke the checked-in probe script against that tag. The Dockerfile also runs the same consumer-level probe during build for defense in depth. |
| RT-2026-07-20-755 | Frontend reviewer | A deny-by-default context can omit a Next configuration or source parent and make the build fail for context-policy reasons unrelated to the application. | High | Re-include the complete production build input set | Re-include package manifests, Next/PostCSS/Tailwind/TypeScript configuration, `next-env.d.ts`, and the complete `src` tree while re-excluding test/spec trees. Prove the real multi-stage image build rather than reasoning from patterns. |
| RT-2026-07-20-756 | Release-governance reviewer | A green local image proves resource layout but not a canonical H0 commit, pushed digest, schema/config/flag manifest, SBOM, or vulnerability decision. | Critical | Keep PD-01 partially open | Record resource-layout closure separately. Do not call PD-01 or release green until branch reconciliation and the digest-addressed H0 provenance bundle are complete. |

Decision: proceed with the app-only immutable-resource patch and fail-closed
consumer probe. Reopen on any context inclusion outside the allow-list, any
runtime-user read/import failure, specialized-bundle mismatch, missing RV rows,
or divergence between local Compose and CI build contexts. Do not deploy from
this dirty working tree.

Follow-up execution found and resolved one objection in the proposed context
policy itself:

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-757 | Build-context reviewer | Denying `**` and then negating a parent directory is not sufficient: the first real build sent 4.86 GB because re-included `caos/` parents reopened cached, virtualenv, output, and tool descendants. A visually allow-listed file could therefore coexist with an overbroad transmitted context. | Critical | Resolved and negative-control verified | Abort the build, immediately re-exclude `parent/**` after every parent negation, then re-include only exact descendants. A fresh isolated BuildKit instance measured the corrected uncached context at 3.88 MB; the real final image then built and its runtime-user resource/exclusion probes passed. The same correction is applied to the hardening blueprint example. |

## 2026-07-20 — PD-06 runtime-seam planning critic pass

Decision under review: close PD-06 through two separately executable L-sized
plans. C3 extends the existing durable alert substrate into a rule, evaluation,
in-app, and rendered-email-intent pipeline. C5 extends the existing immutable
`MarketSnapshot`/`MarketInstrument` store and RV read model with a provider
chain. C13 records equivalent live services for CP-RENDER, implements CP-SR and
CP-MON as independent services, and retires unsupported spec-only runtime
promises rather than presenting them as implemented engine modules.

Measurement clarification: RT-2026-07-20-760's 154-direct figure is the
historical planning-worktree snapshot captured for that objection. The frozen
C3 contract records the fresh isolated/base-index measurement of 83 direct
callers (with the stated lower-bound qualification for `AlertEvent`/`AlertState`).

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-20-758 | Data-model reviewer | The old plan describes alert persistence and a quote store as absent, but the current tree already has `AlertEvent`, `AlertState`, `MarketSnapshot`, `MarketInstrument`, RV screens, and manual workbook import. Following it literally would create split-brain stores. | Critical | Resolve by extending current substrates | C3 must preserve the `NotificationEvent`/Watchtower distinction and extend `AlertEvent` additively. C5 must write normalized provider observations into immutable market snapshots and instruments; no parallel `market_quotes` table is permitted. |
| RT-2026-07-20-759 | Workflow-semantics reviewer | Routine run-completion notifications and credit-change alerts have different meaning, lifecycle, and escalation. Unifying them would let an operational completion masquerade as a credit signal. | Critical | Keep event classes separate | `NotificationEvent` remains the analyst-owned workflow feed. Watch rules may evaluate a completed run's governed outputs, but only qualifying observations become `AlertEvent` rows through the C3 evaluation/sink pipeline. |
| RT-2026-07-20-760 | Database-impact reviewer | `AlertEvent` is a CRITICAL GitNexus surface with 154 direct indexed dependents; an in-place schema/semantic rewrite can break unrelated analysis, lineage, and UI paths. | Critical | Additive migration and compatibility gate | Prefer related `WatchRule`, evaluation, and delivery-intent tables plus additive nullable ownership/version fields. Require fresh symbol impact, migration up/down rehearsal, legacy-row response compatibility, and full alert/analysis regression before changing existing semantics. |
| RT-2026-07-20-761 | Truth-contract reviewer | Monitor currently derives some live counts/context from an autonomy draft while the inbox can refresh and read persisted alert events. Two live authorities can disagree while both show a LIVE badge. | Critical | One persisted read authority | After C3 materialization, all live counts, filters, phone triage, selection, and inbox rows must consume the persisted alert-event query contract. The autonomy draft is an input to evaluation, not a second UI read model. Reference replay stays explicitly separate. |
| RT-2026-07-20-762 | Idempotency reviewer | A key based only on rule and issuer suppresses genuinely new observations; a key containing wall-clock generation time replays duplicates on every evaluation. | Critical | Versioned observation identity | Define the event identity from rule version, scope, signal type, subject, and immutable fact/source observation identity. Re-evaluation is idempotent; a changed source fact/version creates a new event. Test retries, concurrent evaluators, and rule-version changes. |
| RT-2026-07-20-763 | Transaction reviewer | Calling email or another sink inside the event transaction can hold locks, replay side effects after rollback, or persist an event with no auditable delivery state. | Critical | Transactional outbox boundary | Persist the event and delivery intents atomically. Dispatch outside the transaction with leases, bounded retries, terminal failure state, and idempotency keys. `InAppSink` materializes the persisted inbox path; the Phase-1 `EmailSink` records a rendered intent only. |
| RT-2026-07-20-764 | Communications reviewer | A stub that logs a subject/body or reports success can leak confidential content and be mistaken for a sent enterprise email. | Critical | Honest rendered-intent state | Store rendered subject/body in the governed outbox, log identifiers/status only, and label the result `rendered_intent`/`not_sent`. No UI copy may say delivered, connected, or sent until the enterprise transport returns verifiable acceptance. |
| RT-2026-07-20-765 | Authorization reviewer | Watch rules, alert events, outbox records, and market snapshots can cross analysts or teams if new endpoints copy the current broad list patterns without a deliberate visibility policy. | Critical | Decide and stamp scope before writes | Every new record carries owner/team visibility derived from `CallerIdentity`; reads and mutations use the existing tenancy helpers and 404 masking. The plan requires same-team, cross-team, cross-analyst, and principal-switch tests before activation. |
| RT-2026-07-20-766 | Scheduler reviewer | Multiple web/worker processes can evaluate the same scheduled rule or EDGAR poll concurrently, producing duplicate events or an alert storm. | High | Durable claims plus idempotent evaluation | Scheduled work uses a persisted claim/lease and the same observation idempotency key as event-driven work. No in-process timer or per-worker cron is accepted as the production scheduler contract. |
| RT-2026-07-20-767 | Analytical-governance reviewer | The current Sector Review create route synchronously persists a partial/reference adapter with unavailable dimensions. Renaming its method to CP-SR would falsely turn gaps into implementation. | Critical | Build an asynchronous source-backed service | Keep partial/reference reviews unpublishable. The CP-SR service must produce the six scored dimensions, comparables, recovery evidence, source register, uncertainties, and immutable version before readiness can become `ready`; ratification remains a separate human gate. |
| RT-2026-07-20-768 | Feedback-loop reviewer | The sanctioned CP-SR↔CP-MON relationship can recurse indefinitely when an alert triggers a sector refresh whose early warnings create another alert. | Critical | Bounded correlation contract | Carry correlation/root-cause identifiers and hop count; suppress a same-observation return edge; never auto-ratify or auto-publish. Add cycle-termination and duplicate-handoff tests. |
| RT-2026-07-20-769 | Market-data reviewer | Silent Bloomberg→manual fallback can blend sources, preserve stale rows as current, or make a partial refresh look like a complete live snapshot. | Critical | Immutable single-source manifests | Each provider attempt produces a complete explicit result (`ready`, `partial`, `unavailable`) with source, as-of, coverage, errors, and freshness. Manual fallback creates its own snapshot/manifest and label; row provenance cannot be silently overwritten or mixed. |
| RT-2026-07-20-770 | Vendor/licensing reviewer | The repository has no licensed Bloomberg transport decision or checked-in official SDK contract. Inventing BLPAPI/HAPI method names in the plan would create an unimplementable adapter. | Critical | Block the transport-specific phase | Define and test only the CAOS provider protocol plus recorded normalized fixtures until the enterprise owner supplies the licensed transport decision and official SDK/API documentation. The selected adapter then copies those exact APIs; credentials/entitlements and live parallel validation remain explicitly outstanding. |
| RT-2026-07-20-771 | Secrets reviewer | A Settings connection panel can accidentally persist, return, or log Bloomberg/mail credentials and make a saved Boolean look like a verified connection. | Critical | Secret-reference control plane | Credentials remain in the deployment secret store/environment, never analyst JSON or API responses. Expose only configured/last-test/status/error-class metadata; mask identifiers and require an admin/write role for tests and refreshes. |
| RT-2026-07-20-772 | Runtime-promise reviewer | Generic upload parsing is not equivalent to CP-EXTRACT's promised role as the sole parser of module `.docx` JSON appendices; the application does not use that document boundary. Calling it equivalent would preserve a false promise. | Critical | Retire the inapplicable promise | Record CP-EXTRACT as architecturally retired for the direct structured-payload runtime, remove its production registry/control claims, and retain upload extraction under its real ingestion contract. CP-RENDER may map to Report Studio only after its run/checkpoint/preview/version/export evidence is cited. |
| RT-2026-07-20-773 | Release-evidence reviewer | Recorded provider fixtures, mocked browser APIs, or current-tree unit tests cannot prove enterprise activation or close PD-06 on released bytes. | Critical | Layer evidence and keep NO-GO | Per-PR tests prove internal contracts; C-exit tests prove offline activation/failure; H0 must bind real API/data E2E and exact flags to the digest. Enterprise mail and Bloomberg acceptance stay visibly pending until H4/live parallel evidence exists. |
| RT-2026-07-20-774 | Parallel-WIP reviewer | Implementing migrations and shared registry changes in the current mixed worktree would couple PD-06 to unrelated deletions, report edits, and release artifacts. | Critical | Plan-only tranche | This tranche writes plans, the promise map, and status documentation only. Code implementation begins from reconciled scope with fresh impacts; nothing is staged, committed, or deployed here. |

Decision: proceed with separate C3 and C5 plans plus a C13 promise map. Reopen
if implementation creates parallel stores, merges workflow and credit events,
lets a stub imply delivery, invents a vendor API, mutates the CRITICAL
`AlertEvent` surface without additive compatibility proof, or treats fixture
evidence as H0/live activation.

## 2026-07-22 — PD-06 CP-RENDER/CP-EXTRACT disposition execution critic pass

Decision under review: execute the RT-2026-07-20-772 dispositions on the
reconciled tree — retire CP-EXTRACT (remove its registry spec and production
consumer stamps) and record Report Studio as CP-RENDER's equivalent service
(remove its spec under the CP-DB documented-omission precedent, clean consumer
stamps, cite run/version/export evidence in the promise map). CP-SR/CP-MON
spec-only honesty is untouched.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-775 | Corpus-fidelity reviewer | Removing the two Infra nodes stops the live route plan from mirroring the corpus mesh (engine item #8 "full-mesh honesty"). | High | Resolve via the CP-DB precedent | Mesh honesty means honest about what the engine will run. CP-DB is already a documented omission because the DB stack IS its implementation; Report Studio IS CP-RENDER's implementation and CP-EXTRACT is architecturally retired (RT-772). Both omissions are documented at the registry with dated rationale; the corpus mesh remains fully documented in Modular OS and the seeded Pipeline reference DAG (spec-truth per MOCK_LEDGER). |
| RT-2026-07-22-776 | API-contract reviewer | Consumers may depend on the four Not-Implemented readiness rows in run payloads. | Medium | Resolve with evidence | Frontend renders readiness rows per-item with no pinned count and has zero live references to the two IDs (only seeded mock + a type). `_coverage` counts `implemented` only; `DECLARATION_INDEX` orders persisted outputs only. Contract tests updated to assert documented absence; full server suite gates the change. |
| RT-2026-07-22-777 | Evidence reviewer | An equivalence decision without cited runtime evidence repeats the overclaim RT-772 warned against. | Critical | Resolve in the promise map | The map cites Report Studio's committee gate (engine/report.py), immutable versions with stored document-hash verification and approved source-manifest binding (routes/reports.py), the honest-unavailable API contract test (test_engine: /modules/CP-RENDER → 404), and the browser report flow. Production-data browser export evidence on frozen H0 explicitly remains open — the decision is recorded, not the H0 proof. |
| RT-2026-07-22-778 | Parallel-work reviewer | The C3 worktree (CP-MON runtime build) will also edit the registry and the spec-only test pin — merge conflict risk. | Medium | Accept, bounded | Edits are confined to the Infra spec block, consumer-stamp literals, and one assert line; any conflict is line-local and semantically trivial (both sides shrink the same set). Commit message flags the seam for the C3 owner. |
| RT-2026-07-22-779 | Lineage reviewer | Emptying `downstream_consumers` loses the true fact that CP-5/CP-6E output feeds committee export. | Low | Resolve by naming the service where it is owned | The real consumer is the Report Studio export service, which module-ID vocabulary cannot express without inventing a token the graph would treat as a module. querygraph never rendered these edges (consumers draw only when present in the run). The service relationship is recorded at engine/report.py, the registry omission note, and the promise map. |

Decision: proceed. Reopen if any suite or golden pins the removed rows, or if
the C3 tranche lands a conflicting registry shape first (rebase and re-verify
rather than force-merge).

## 2026-07-22 — H0 release-manifest generator critic pass

Decision under review: implement PD-01's completion-gate tooling as one
stdlib-only script, `caos/deploy/build_release_manifest.py`, that assembles the
H0 release manifest (candidate identity, image digests, schema head, sanitized
config fingerprint, explicit feature-flag states, Modular OS in-image probe
evidence, SBOMs, vulnerability scans, CI evidence links) plus a digest-pinned
compose override, with a diagnostic mode and a fail-closed `--strict` H0 mode.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-780 | Secrets reviewer | A "config fingerprint" that hashes live env files or prints flag sources could capture secrets in a long-lived release record. | Critical | Resolve by construction | Fingerprint hashes only tracked non-secret deploy files (compose, Dockerfiles, Caddyfile, oauth2-proxy.cfg, clamd.conf, .dockerignore, .env.example schema). Live `.env` is never read; flag states enter only as explicit `--flag NAME=STATE` arguments; values are never echoed from the environment. |
| RT-2026-07-22-781 | Fake-green reviewer | A diagnostic run on a dirty tree could be mistaken for H0 evidence, repeating the "evidence not bound to released bytes" defect PD-09 exists to prevent. | Critical | Resolve with modes | Every manifest stamps `mode`; `--strict` refuses a dirty tree, a HEAD not equal to `origin/main`, any unresolved image digest, any missing flag state, and any `unavailable` section. Diagnostic manifests say so in the filename and body. |
| RT-2026-07-22-782 | Tooling reviewer | Silent degradation when npm/pip-audit/docker scout are absent would produce a manifest that looks complete but is not. | High | Resolve with per-section status | Every section records `status: recorded` or `status: unavailable` with the exact reason and command; strict mode fails on any unavailable section. No section is omitted. |
| RT-2026-07-22-783 | Scope reviewer | Building rehearsal legs (DB restore, backup verify) into the script would fake host-bound evidence the plan assigns to the target host. | Medium | Resolve by exclusion | The script covers only the machine-derivable manifest legs; restore/upgrade rehearsal, off-host backup, and image scan disposition remain named manual H0 steps and the manifest records them as explicit open slots. |

Decision: proceed; new file only, zero collision with the C3 tranche. Reopen if
H0 adopts a registry (digest source becomes the registry, not local inspect) or
if the flag inventory moves out of `config.py`.

## 2026-07-22 — CP-SR implementation-plan critic pass

Decision under review: write the standalone CP-SR implementation plan
(caos/docs/CP_SR_IMPLEMENTATION_PLAN.md) that PD-06's closure checklist
requires, structured as deterministic-first synthesis over the existing
versioned-dossier substrate, executed as an asynchronous claimed job, with
email intake and licensed market data explicitly out of scope. Plan only —
execution starts from reconciled scope after the C3 tranche lands.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-784 | Migration-collision reviewer | CP-SR schema work started now would race the in-flight C3 worktree for the next Alembic revision and the shared claim/scheduler substrate. | Critical | Resolve by sequencing | The plan documents its schema needs but execution is gated on C3 landing; CP-SR reuses whatever claim/lease substrate C3 establishes rather than inventing a second one (RT-766 parity). |
| RT-2026-07-22-785 | Synthesis-honesty reviewer | An LLM-first six-dimension synthesis could fabricate sector scores where sources are thin, exactly what the readiness gate exists to prevent. | Critical | Resolve in the contract | Each dimension is deterministic-first: computed from vault-derived evidence and CP-1 facts with an LLM narrative lane that is fault-isolated and abstains (dimension stays `unavailable`) when the source register cannot support it. A dossier reaches `ready` only when every dimension is scored from cited evidence; partial dossiers stay unpublishable (RT-767). |
| RT-2026-07-22-786 | Scope reviewer | Including corpus Step A.2 (email intelligence) or Bloomberg-fed comparables would couple CP-SR to seams PD-06 already blocks. | High | Resolve by exclusion | Email intake and licensed market data are named non-goals; the source register runs on vault documents and analyst-supplied market snapshots only, and the plan states the corpus deviation explicitly. |
| RT-2026-07-22-787 | Trigger-loop reviewer | The corpus CP-MON→CP-SR refresh hook could recreate the unbounded alert↔refresh recursion RT-768 killed. | High | Resolve by inheritance | Refresh triggers carry the correlation/hop-count contract RT-768 defined; a same-observation return edge is suppressed and nothing auto-ratifies or auto-publishes. |

Decision: proceed with the plan document; reopen at execution pickup if C3's
landed substrate differs from the plan's assumptions.

## 2026-07-22 — Bloomberg descope + CP-SR Phase-1 deferral critic pass

Decision under review (user product decisions, 2026-07-22): (1) remove the
Bloomberg API build requirement from the pre-deployment plan — supersede the
2026-07-03 "connector built in-plan" decision — and group Bloomberg entirely
with the enterprise email connection as the enterprise-side final activation
step (H4); Phase-1 ships on the existing fixed/manual market data (immutable
`market_snapshots` 0055 store + analyst XLSX import lane + the immutable RV
reference snapshot). (2) Record a CP-SR Phase-1 deferral: the sector-review
surface keeps its honest partial/reference states with `ready` unreachable;
the S0–S5 build becomes the first post-pilot item.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-788 | Market-data honesty reviewer | Shipping on fixed/manual data risks stale marks being read as current, the exact blending RT-769 killed. | Critical | Resolve with existing labels | The shipped lane already carries immutable snapshots, explicit as-of dates, and analyst-supplied labeling; Sector RV keeps per-result LIVE/DEMO/REFERENCE authority. No provider chain means no silent fallback path exists at all — the failure mode RT-769 targeted cannot occur. Reopen if any surface presents snapshot data without its as-of/source label. |
| RT-2026-07-22-789 | Vendor reviewer | Deleting Bloomberg build work could orphan the H4 activation runbook contract (H3 package promises a connector "already built"). | High | Resolve by rescoping H4 | H4's activation package is rewritten from "activate the built connector" to "build-and-activate with enterprise transport docs in hand" — which RT-770 already argued is the only honest sequence (no licensed transport decision exists to code against). The fixture-backed provider was speculative build; removing it deletes dead-on-arrival code risk, not evidence. |
| RT-2026-07-22-790 | Promise-honesty reviewer | A CP-SR deferral could be read as renaming a gap as implementation (RT-767's exact warning). | Critical | Resolve by disposition class | The deferral is recorded as DEFERRED, not resolved: the map row stays materially incomplete on its face, the surface keeps unreachable `ready` and labeled partial/reference states, and the written S0–S5 plan remains the closure path. Nothing is relabeled as live. PD-06 closes only on honest-state evidence for the deferred rows plus the executed C3/CP-RENDER legs. |
| RT-2026-07-22-791 | Pilot-value reviewer | Deferring CP-SR could strip the pilot of a promised workflow analysts expect. | Medium | Accept with eyes open | The pilot's value is issuer-level analysis + Monitor/alerts (C3). The sector surface remains usable read-only with honest labels. The deferral is the user's explicit scope call, recorded here; reopen at the first post-pilot planning pass. |

Decision: proceed. Reopen RT-788 if any consumer renders snapshot data without
provenance, RT-790 if any surface or doc presents CP-SR as implemented.

## 2026-07-21 — C3 persisted-Monitor correction critic pass

Decision under review: accept the Task 7 persisted Monitor interface and its
decision-reopen integration as the sole Live alert authority before starting
the default-off activation tranche.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-21-775 | Authorization reviewer | A C3 alert key is a hash and carries no issuer id, so the legacy substring check rejects valid governed alerts while malformed C3-like strings can evade a persistence/visibility check. | Critical | Resolved | Exact lowercase `c3:<64 hex>` keys now require a persisted `AlertEvent` joined to an `AlertEventContext`, matching both decision issuer fields and the caller visibility predicate. Missing, foreign, malformed, and hidden keys share one generic 422 response; legacy issuer-bearing keys retain compatibility. |
| RT-2026-07-21-776 | Analysis-context reviewer | Treating artifact and Monitor surface selection as one whole-object write suppresses independent repair, cannot explicitly clear stale ids, and risks overwriting unrelated context fields. | Critical | Resolved | Selection sync now emits sparse independent patches, supports explicit `null`, fingerprints context revision/state, avoids replay after persistent failure, and has exact partial/null regressions. |
| RT-2026-07-21-777 | Concurrency reviewer | A lifecycle 409 followed by blind Retry can replay a stale action; a sibling PATCH can also settle before, during, or after reconciliation and overwrite newer persisted lifecycle state or resolution notes. | Critical | Resolved | A global reload-authority barrier closes all writes, preserves the ready view and drafts, captures and drains pre-conflict PATCHes, fences request/epoch/unmount supersession, then issues the final authoritative GET. Successful reconciliation clears captured selection and requires fresh analyst intent; failed reconciliation keeps the barrier and reload control visible. |
| RT-2026-07-21-778 | Selection-race reviewer | Rapid A→B selection can enqueue duplicate B analysis patches, while removal of a pending URL target can leave URL, artifact, and surface selections permanently stale. | High | Resolved | Per-context/event in-flight targets defer duplicate repairs with a guarded rerun, and ready authority reconciles pending requests before the observed-request shortcut. URL and both analysis targets clear exactly once when the target disappears. |
| RT-2026-07-21-779 | Batch-workflow reviewer | The generic batch toolbar bypasses controller-level conflict reconciliation; concurrent batch failures can retain contradictory Retry copy under a global authority barrier, and clearing a pending batch can hide its outcome. | Critical | Resolved | The persisted batch toolbar delegates to `acknowledgeSelected`, normalizes both failure/barrier orderings to reload-and-review copy, suppresses blind Retry, and makes visible clear plus Escape inert while pending. Batch conflict success clears captured membership and demands a fresh selection. |
| RT-2026-07-21-780 | Accessibility and mobile reviewer | A failed conflict refresh can unmount analyst input or leave no reachable reload action on phone when the current filtered event disappears. | High | Resolved | Preserve-ready refresh leaves draft controls mounted, desktop and phone render explicit reload-authority controls, and phone keeps the control above the empty filtered state. Final normal/reduced-motion axe matrices at 1440x900 and 390x844 report zero violations, scan/layout failures, clipping, target failures, or collisions. |

Decision: accept the corrected Task 7 interface. Independent final review found
no remaining Critical, High, Medium, or Low issue after all eight original
defects and the follow-up ordering regressions were re-evaluated. Reopen if a
mutation can publish across the reload-authority barrier, a C3 decision reopen
does not prove visible issuer context, or any UI offers stale Retry authority.

## 2026-07-21 — C3 default-off activation and candidate-evidence critic pass

Decision under review: expose the completed C3 watch-rule/runtime seam behind
one deployment-global, default-false flag while retaining migration 0066 and
all historical alert-event authority during rollback.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-21-781 | Route-boundary saboteur | A flag check inside a handler or after request dependencies can still validate inputs, consume quota, resolve identity, or open a database session while the feature is supposedly off; differing errors also disclose the hidden API. | Critical | Resolved | A raw ASGI exact-prefix gate now runs before request-body limiting and routing, while the router dependency remains as defense in depth. Disabled watch-rule requests return one generic `404 Not Found` without entering the downstream app or consuming `receive`; schema-valid route probes plus exploding database/quota sentinels remain covered. |
| RT-2026-07-21-782 | Runtime-side-effect saboteur | Completed-run, scheduled, or dispatch gating after normalization, clock reads, snapshots, claims, registry access, or sink lookup can mutate durable attempts while off. | Critical | Resolved | Each runtime entry checks the Boolean first and returns the frozen compatibility-neutral off result: zero-count `evaluated`, `no_claim`, or `None`. Invalid `now`/cursor values and exploding clocks, factories, registries, and sinks prove no downstream boundary is crossed. |
| RT-2026-07-21-783 | Compatibility reviewer | Requiring the new settings field, or coupling settings discovery to the combined Monitor authority, can break mixed-version clients and hide historical alerts when settings is missing, malformed, or unavailable. | Critical | Resolved | `alert_rules_v1_enabled` is optional in the client contract and exact `true` is the only enabling value. The independent `checking`/`enabled`/`disabled`/`unavailable` rule state leaves persisted alert reads and mutations live; false, missing, malformed, and failed settings make zero watch-rule calls while the desktop and phone inbox remain usable. |
| RT-2026-07-21-784 | New-hire/UI-state reviewer | Reusing rule-list loading/error state for deployment activation can leave a permanent spinner or offer New/Edit/Retry authority when the deployment is known off. | High | Resolved | Explicit deployment-off and activation-unverified states expose no rule-management controls. The settings-only retry preserves alert authority and has regression coverage for false, failure/retry, and transition to exact true. |
| RT-2026-07-21-785 | Release-configuration reviewer | Enabling the flag in a job-wide/global environment erases the observable default-off contract and silently enables C3 in unrelated suites. | High | Resolved | Compose and both environment examples are explicitly false. CI sets true only on the real-API E2E server subprocess, scoped tests opt in locally, the browser lane uses `--retries=0`, and a repository audit finds the CI subprocess as the sole committed true-valued deployment occurrence. |
| RT-2026-07-21-786 | Evidence-retention reviewer | Calling a successful Alembic downgrade the production rollback path would delete rule, evaluation, context, and delivery-intent evidence. | Critical | Resolved | Production rollback is documented as flag-off with migrations 0066 through 0068 retained at head 0068. The earlier 0066→0065→0066 path ran only against a disposable SQLite database, the populated legacy alert/state preservation selector passed, and the result is labeled destructive local rehearsal rather than operational rollback. |
| RT-2026-07-21-787 | Evidence-truth reviewer | Local API, fixture, browser, or axe results can be mistaken for immutable H0, production PostgreSQL, target-host, external-scheduler, or enterprise-delivery evidence. | Critical | Resolved | Candidate evidence records branch/commit, local topology, SQLite dialect, exact flags, commands, zero-retry browser counts, injected failure, and warnings. CP-MON remains PROVISIONAL, PD-06 remains OPEN, NO-GO remains in force, and live PostgreSQL/H0, real external operation, flag observation, enterprise transport, and target-host proof remain explicit blockers. |
| RT-2026-07-21-788 | Framework-order reviewer | FastAPI decodes JSON before solving router dependencies. While the flag is off, malformed JSON can therefore return `422` and invalid encoded JSON can return `400`, disclosing the hidden surface before the existing guard runs. The recorded RED defect is body decoding; method behavior is not used as RED evidence. | Critical | Resolved | `AlertRulesActivationGateMiddleware` is ordered `HTTPPolicy → activation gate → request-body limit → routing`. The original malformed-JSON `422` was captured RED. GREEN covers malformed JSON, invalid UTF-8, and `application/*+json` across create, patch, and evaluate; a raw receive/downstream sentinel; exact-prefix and legacy-alert boundaries; flag-on pass-through; HTTP-policy `403`/`401` precedence; and intentional flag-off `404` before flag-on `413` body limiting. |

Decision: accept the corrected default-off activation boundary as
candidate-local/offline evidence. All eight objections were captured and
verified through focused server/frontend suites, the full Monitor real-API
browser matrix, local axe scans, configuration audit, and disposable migration
rehearsal. Migrations 0066 through 0068 remain applied at head 0068 under production rollback; the flag
gates only watch-rule activation boundaries and never the legacy persisted
alert-event/state APIs. This decision does not satisfy H0, close PD-06, authorize
flag activation, or change the release NO-GO.

## 2026-07-21 — C3 whole-branch runtime correction critic pass

Decision under review: correct the final whole-branch review findings without
adding a process-local scheduler, weakening tenant scope, bypassing immutable
evidence controls, or changing the default-off / NO-GO release posture.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-21-789 | Privacy reviewer | Analyst erasure removes the profile but leaves raw C3 owner stamps, C3-authored alert attribution, and enabled rules that continue producing data for the erased principal. Updating immutable rule versions is rejected by the database trigger. | Critical | Resolved and verified | The privileged erasure path dependency-deletes the analyst-owned intent/context/evaluation/version/rule graph, then redacts retained shared alert/lifecycle attribution. Tests prove no raw identity, active owned rule, or orphan survives; ordinary product paths retain RESTRICT/no-delete semantics. |
| RT-2026-07-21-790 | Scope/provenance reviewer | Run validation returns after an issuer match, so a rule scoped to both issuer and portfolio can persist a same-issuer run from the wrong portfolio, wrong team, or a book that does not hold the issuer. | Critical | Resolved and verified | Issuer and portfolio scope are validated independently inside the transaction, including exact portfolio team and holding authority. Wrong issuer, portfolio, team, or holding rejects before materialization and leaves no partial event/context/intent graph. |
| RT-2026-07-21-791 | Durability/fan-out reviewer | The post-commit completed-run hook is fire-once and exception-swallowing, while one rule/observation failure aborts all later matches. Crash, transient error, or flag-off completion has no bounded replay seam. | Critical | Resolved and verified | A flag-gated operator CLI runs one bounded cursor page of idempotent completed-run reconciliation without a timer or startup hook. Per-observation failures are isolated and sanitized, cancellation propagates, and tests cover flag-off/restart catch-up, page replay, and later-run/rule progress. |
| RT-2026-07-21-792 | Persistence-contract reviewer | Wire JSON limits use canonical UTF-8, but SQLite/PostgreSQL CHECKs measure dialect serialization. A wire-valid near-limit object can therefore fail at flush and surface as a 500. | High | Resolved and verified | Additive revision `0067` retains canonical wire limits as authority while installing finite dialect-specific storage envelopes. A concrete near-limit evaluation persists, raw overflow is rejected, and SQLite plus PostgreSQL DDL are asserted. |
| RT-2026-07-21-793 | Batch-concurrency reviewer | Live row selection and filters remain mutable during a batch lifecycle request, while non-conflict failures are published only when the failed ids still exactly match the current selection. A deselect or filter change can therefore hide a failed mutation. | High | Resolved and verified | The controller captures and fences batch identity until every PATCH settles; selection and filter retargeting cannot hide the outcome. Failures publish from the captured batch and leave failed-only authority regardless of intervening view intent. |
| RT-2026-07-21-794 | Retry-authority reviewer | Desktop and phone retry closures retain the original lifecycle payload while assignee/resolution drafts remain editable during the request. A failed Alice request followed by a visible Bob edit can retry Alice and then clear Bob. | High | Resolved and verified | Desktop and phone lock the relevant draft while its request is pending. On failure they retain visible input and rebuild Retry from the current displayed intent, with synchronous duplicate fencing and explicit dismissal custody. |
| RT-2026-07-21-795 | Rule-editor concurrency reviewer | Save disables only the Save button; Escape, backdrop, Close, Cancel, and fields remain active. The dialog can claim cancellation while an enabled rule still commits, or show success for values edited after submission. | High | Resolved and verified | An in-flight save is a modal authority barrier: fields and every dismissal path are inert, the submitted snapshot stays visible, and success/failure settles before close or further edits are allowed. |
| RT-2026-07-21-796 | Capability reviewer | Same-team rules are intentionally readable but PATCH is owner/admin-only. The API exposes no mutation capability, so every shared rule renders Edit and leads to a masked 404. | Medium | Resolved and verified | Every safe rule response carries server-derived `can_mutate`; owner/admin writers receive true and shared, viewer, or legacy authority receives false. The client renders false as labelled read-only state and never infers authority locally. |
| RT-2026-07-21-797 | Collection-capability reviewer | Per-rule mutation authority cannot answer whether the current caller may create a new rule. A read-only viewer still receives an active New rule dialog and learns the denial only after a 403 submission. | High | Resolved and verified | The list response carries server-derived `X-Watch-Rule-Can-Create`. The controller requires exact, consistent true across the complete cursor drain and fails closed while missing, inconsistent, loading, false, or unavailable, so no New-rule authority is exposed. |
| RT-2026-07-21-798 | Modal-accessibility reviewer | Disabling the focused Save button during an in-flight request can move browser focus to `body`, outside the `aria-modal` dialog, until another keyboard action repairs the trap. | High | Resolved and verified | Pending Save remains focusable with `aria-disabled` and a busy label, a synchronous guard rejects activation, and all other mutable/dismissal controls are disabled. Tests keep focus inside the modal for the unresolved request. |
| RT-2026-07-21-799 | Retained-record privacy reviewer | Erasure redacts structured evidence but retained alert `kind`, `title`, and `impact` can still contain the erased analyst id or email, while replacing identity-bearing dictionary keys with one pseudonym can collapse distinct evidence entries. | Critical | Resolved and verified | Erasure redacts retained alert free text, structured authority/evidence, lifecycle text, and retained delivery payload/destination fields. Changed dictionary keys receive deterministic collision-safe digests; tests prove distinct entries and unrelated bystander records survive without the erased identity. |
| RT-2026-07-21-800 | Historical-replay reviewer | Reconciliation evaluates old completed runs against today's enabled/current rule version, fabricating backdated alerts for rules created or edited after the run. | Critical | Resolved and verified | Completed-run selection rejects a rule or current immutable version created or edited after the run's observation time. Post-run create/edit cases produce no evaluation or alert during reconciliation. |
| RT-2026-07-21-801 | Migration-path reviewer | Correcting the committed `0066` JSON CHECK text in place does not update databases already stamped at `0066`. | High | Resolved and verified | Revision `0066` retains its original semantics; additive `0067` replaces only the JSON CHECK envelopes. An actual old-`0066` database rejects the near-limit dialect rendering before upgrade and accepts it after upgrade. |
| RT-2026-07-21-802 | Observation-isolation reviewer | Building all findings under one rule-level exception boundary lets one malformed finding discard valid sibling observations. | High | Resolved and verified | Finding construction and evaluation failures are isolated per observation with sanitized telemetry. A malformed finding beside a valid sibling records one failure while the valid observation proceeds durably. |
| RT-2026-07-21-803 | Workflow-authority reviewer | An individual alert mutation does not fence batch acknowledgment, so Assign and batch Ack can overlap and a later Retry can erase the newly persisted assignee. | Critical | Resolved and verified | The persisted controller enforces a two-way barrier: ordinary row mutations cannot start during a batch, and a batch cannot start while any row mutation is pending. Desktop, phone, and header affordances expose the same reason and no second PATCH begins. |
| RT-2026-07-21-804 | Partial-failure reviewer | Under the default All filter, a partial batch failure leaves both successful and failed rows selected; Retry therefore replays already-successful PATCHes against potentially newer state. | Critical | Resolved and verified | After the captured batch settles, selection and retry identity retain failed ids only. Retry emits exactly the failed PATCHes and never replays a successful sibling. |
| RT-2026-07-21-805 | Deferred-outcome reviewer | Switching Alerts to Governance while an individual write is pending unmounts row-local error, draft, and retry custody, allowing a late non-conflict failure to disappear. | Critical | Resolved and verified | Dataset tabs and secondary governance navigation are fenced while workflow custody is pending; direct URL or breakpoint changes retain the Alerts dataset and mounted draft/error/retry until success or explicit dismissal. |
| RT-2026-07-21-806 | Revocation reviewer | Conflict reload can return a rule whose mutation capability was revoked, but the editor keeps its writable modal open and permits another masked-denial update attempt. | High | Resolved and verified | A conflict reload with missing/false `can_mutate`, or a masked 403/404, refreshes the collection, closes and clears the editor, and publishes an honest read-only notice. No second PATCH is available. |
| RT-2026-07-21-807 | Fixture-isolation reviewer | Browser surface fixtures fall through for watch-rule and alert-event mutations, so activating a control can reach a developer's live API instead of deterministic fixture state. | High | Resolved and verified | Browser fixtures own the complete alert-event and watch-rule URL prefixes for every method, fulfill supported mutations from fresh local state, and fail closed on unsupported methods without live-backend fallthrough. |
| RT-2026-07-21-808 | Migration-failure reviewer | A `0067`-valid but `0066`-oversize row makes SQLite downgrade fail after the immutable-version trigger is removed, leaving a half-migrated database that permits history mutation and cannot be retried cleanly. | Critical | Resolved and verified | Revision `0067` preflights every narrowing constraint before DDL. Refusal leaves the revision, constraints, tables, immutable-version trigger, and rows untouched, so the database remains retryable. |
| RT-2026-07-21-809 | Historical-scope reviewer | Reconciliation checks current portfolio membership, so a holding added after a run can fabricate a backdated portfolio alert; mutable portfolio state cannot be treated as historical authority. | Critical | Resolved and verified | Issuer, portfolio, and holding creation must predate the observation, and a portfolio updated after it is rejected. The same effective-time scope fence runs again at materialization; post-run holdings/updates cannot create a backdated alert. |
| RT-2026-07-21-810 | Scheduler-resume reviewer | The fifth scheduled failure auto-pauses with `claim_attempt_count = 5`, but ordinary resume leaves that terminal count intact while claims require `< 5`; the UI says resumed although the rule remains inert. | Critical | Resolved and verified | An explicit authorized terminal resume atomically resets `claim_attempt_count` to zero while preserving schedule cursor and last-evaluated evidence. The resumed rule is immediately eligible for a fresh claim. |
| RT-2026-07-21-811 | SQLite-integrity reviewer | Runtime SQLite connections omit `PRAGMA foreign_keys=ON`, so C3 orphan evaluations, contexts, and intents can commit even though migration tests manually enforce the declared FKs. | High | Resolved and verified | Every application SQLite connection enables foreign keys alongside its existing pragmas; the test transaction hook defers ordering without disabling commit-time integrity. Runtime-engine tests reject unresolved orphans; PostgreSQL behavior is unchanged. |
| RT-2026-07-21-812 | Recovery-watermark reviewer | A clean terminal reconciliation page returns no new cursor, so recurring operators must replay that terminal page rather than persist a terminal high-water mark. | Medium | Resolved by bounded contract | The CLI, service contract, and tests state that `next_cursor = null` is a clean terminal page and the input cursor must be retained. Recurring operation intentionally replays that bounded idempotent page until a future durable watermark protocol is introduced. |

Decision: accept the RT-789..812 implementation corrections after targeted and
independent whole-branch review found no remaining implementation defect in
this set. This is candidate-local evidence only: CP-MON stays **PROVISIONAL**,
PD-06 stays **OPEN**, and the release remains **NO-GO** pending live PostgreSQL,
H0 exact-image/config binding, external operation and flag observation,
enterprise transport, and target-host evidence.

## 2026-07-22 — C3 watch-rule create idempotency critic pass

Decision under review: make `POST /watch-rules` safe to retry after an
ambiguous response while preserving transaction ownership and tenant authority.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-813 | Concurrency reviewer | A select-before-insert retry check is racy across app replicas: two requests can both observe no prior row and create distinct rules and version-1 records. Catching the unique failure after an ordinary flush also poisons the caller-owned transaction. | Critical | Resolved and verified | A database unique key over tenant, owner, and create idempotency key backs a dialect-native conflict-do-nothing insert. Only the winner creates version 1; the loser reads the winner without rollback or commit. Concurrent-session and outer-transaction tests pass. |
| RT-2026-07-22-814 | Authority reviewer | A globally unique key lets one analyst's opaque key collide with or reveal another analyst's request, while a tenant-only key prevents distinct users from safely choosing common client-generated values. | High | Resolved and verified | The key is persisted under the same derived tenant and owner scope used by the rule. Replays query that complete scope, and tests prove the same key remains independent for another principal and tenant. |
| RT-2026-07-22-815 | Request-identity reviewer | Returning a prior rule for the same key but a changed body silently accepts stale analyst intent; hashing raw wire bytes makes harmless JSON ordering or timestamp spelling differences conflict. | Critical | Resolved and verified | Every public `POST /watch-rules` requires a valid 1..128-character `Idempotency-Key`; a missing header is rejected. The server hashes the fully validated semantic command as canonical finite JSON with normalized UTC datetimes. Exact intent replays the rule, changed intent returns stable `409 watch_rule_idempotency_conflict`, and legacy nullable rows cannot match a keyed request. |

Decision: accept the required-header, additive scoped-key implementation. Route,
missing-header, service, concurrent-session, migration, and
transaction-neutrality tests pass.
Production rollback remains flag-off with migrations retained; dropping retry
identity is not an operational rollback path.

## 2026-07-22 — C3 exact-tree authority and persistence critic pass

Decision under review: reconcile the final frontend authority, retained-record
privacy, and persistence-boundary findings without enlarging the Phase-1
activation or release claim.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-816 | Capability-invalidation reviewer | A viewer or newly revoked writer can retain alert/rule mutation controls when a capability header is missing or inconsistent across pages, or when a masked 403/404 arrives after the initial list. | Critical | Resolved and verified | Alert and rule list drains require exact, consistent server capability across every page and fail closed otherwise. Masked 403/404 invalidates local authority, refreshes persisted state, closes/clears writable rule drafts where applicable, and exposes no retrying mutation. |
| RT-2026-07-22-817 | Create-recovery reviewer | Reusing a create operation key with changed draft intent returns 409; routing that response through edit-version conflict recovery can offer a misleading reload or repeat the create. | High | Resolved and verified | Exact `watch_rule_idempotency_conflict` during create closes and clears the draft, discards the operation key, refreshes the collection, and tells the analyst to review the already-persisted rule. It never offers edit-only conflict reload and issues no second create. |
| RT-2026-07-22-818 | Case-fold privacy reviewer | Operator erasure can miss a mixed-case email, and retained bystander-owned delivery content can preserve a differently cased copy of the erased address. Treating analyst ids as case-insensitive would over-redact unrelated identifiers. | Critical | Resolved and verified | Operator lookup compares email case-insensitively and passes the profile's stored canonical email to erasure. Email redaction is case-insensitive across retained payload/destination text, analyst-id matching remains exact, and tests prove mixed-case subject email is scrubbed while unrelated bystander identity and case-variant ids survive. |
| RT-2026-07-22-819 | JSON-boundary reviewer | Frozen Pydantic models are only shallowly immutable: nested mutation or `model_copy` can inject U+0000 after construction and reach PostgreSQL JSONB despite the wire validator. | Critical | Resolved and verified | Evaluation claims and delivery completion require the exact contract model, then deep-own and revalidate it through canonical model JSON before the first await/database call. Nested-mutation and `model_copy` regressions reject the domain operation and execute no SQL. |
| RT-2026-07-22-820 | Evidence-authority reviewer | Combining multiple chunk ids, or treating typed run/QA references as chunks, can fabricate a source extract that no persisted governed record supports. | High | Resolved and verified | Monitor evidence opens one explicit primary chunk when present; otherwise it opens the exact governed run/QA-finding evidence. Typed run/QA ids never enter chunk controls, chunk routes encode the id, and multiple chunks are not silently aggregated into one conclusion. |
| RT-2026-07-22-821 | Decision-coherence reviewer | Selecting the newest headline, impact, action, and timestamp independently can assemble a decision banner from different alert observations. | Critical | Resolved and verified | One actionable persisted observation is selected and its headline, impact, action, and as-of travel together. Historical/resolved rows cannot donate newer-looking fields, and loading, outage, empty, and missing-time states remain distinct. |
| RT-2026-07-22-822 | Selection-authority reviewer | Resolved or filtered-out alerts, deep-linked phone rows, or stale desktop selection hidden by Governance can retain batch acknowledgment authority. | Critical | Resolved and verified | Batch selection is limited to visible open alerts. Deep-link hydration does not grant batch authority, hidden rows cannot be selected, and desktop selection is cleared before phone or Governance can hide the controls. |
| RT-2026-07-22-823 | Scale reviewer | Draining and rendering full alert history plus fetching decision context per material row can pass correctness tests while exceeding a production-volume latency/query budget. | High | Accepted residual; activation blocker | Phase 1 is explicitly a low-volume pilot. Higher-volume activation requires server-windowed history, batched decision context, and target-host load evidence; the present correctness implementation is not capacity evidence. |

Decision: accept the corrected C3 exact-tree authority and persistence contracts
as local implementation evidence. The accepted scale residual and release
evidence gaps remain binding: CP-MON is **PROVISIONAL**, PD-06 is **OPEN**, and
release is **NO-GO** until live PostgreSQL, H0 exact-image/config binding,
external operation and flag observation, enterprise transport, target-host
browser/accessibility, and target-volume evidence are complete.

## 2026-07-22 — C3 final migration, identity, and JSON-boundary critic pass

Decision under review: close the final whole-diff objections without changing
the default-off activation boundary, broadening the release claim, or silently
re-keying existing analyst-owned records.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-22-824 | Migration-safety reviewer | The `0067` and `0068` downgrade preflights returned early in Alembic offline mode, after which unconditional destructive DDL could be emitted without inspecting live rows. | High | Resolved and verified | Both revisions now fail closed in offline downgrade before any operation. Regression and direct PostgreSQL-dialect SQL rehearsals exit non-zero and emit no `DROP`; online disposable downgrade still performs its live preflight and preserves the populated refusal contract. |
| RT-2026-07-22-825 | Identity/privacy reviewer | A proxy email could resolve a persisted Analyst while C3 ownership was still stamped from a distinct forwarded username, so UUID/email-based self or operator erasure missed the private graph. | High | Resolved and verified | A matched proxy keeps its historical global `caller.id` from the forwarded user (email fallback) and carries the persisted Analyst UUID separately as `profile_id`. Only C3-scoped dependencies substitute that UUID for rule/evaluation/context/intent and C3 state ownership. Self-erasure always supplies the profile UUID and canonical email, and adds the active forwarded-user/email principal **only when `X-Forwarded-Email` case-insensitively matches the authenticated `caller.email`** (RT-832) — a mismatched forwarded email cannot broaden erasure; operator email erasure resolves the UUID-owned C3 graph. |
| RT-2026-07-22-826 | PostgreSQL JSON reviewer | `SignalObservation` rejected U+0000 in nested detail but not in `source_identity`, `categorical_value`, or `source_artifact_refs`; manual evaluation could therefore raise after request validation and surface a 500. | High | Resolved and verified | All three string-bearing fields now use the same deep JSONB-compatibility validator. Constructor and HTTP regressions reject every variant; the route returns 422 and persists no evaluation/event/context/intent. Safe multibyte oversized-artifact fixtures retain the omission-threshold coverage. |
| RT-2026-07-22-827 | Rollout/compatibility reviewer | Canonicalizing every profile-less proxy caller from `X-Forwarded-User` to email would close erasure lookup for new data but strand existing user-stamped records across `get_identity`'s CRITICAL call graph. Leaving the old key while permitting C3 writes would preserve the original split-owner privacy defect. | High | Resolved and verified | The broad global identity-key flip was rejected: matched and unmatched proxy callers retain the historical forwarded-user `caller.id`, and cookie/local behavior is unchanged. A profile-backed marker and separate `profile_id` are set only after one persisted Analyst resolves. All five watch-rule handlers require that capability, return 403 for an unmatched proxy, and use the profile UUID only inside C3; tests prove zero C3 writes for the denied caller. Erasure principal inclusion follows the conditional forwarded-email match rule (RT-825/832). |
| RT-2026-07-22-828 | Account-integrity reviewer | Exact-case database email uniqueness permits legacy case-variant Analyst rows, while case-insensitive lookup with `scalar_one_or_none()` raises `MultipleResultsFound`; identity, SSO profile creation, and operator erasure could fail unpredictably. | Medium | Resolved and verified | Each case-insensitive lookup reads at most two ordered rows and fails closed on ambiguity without mutation or erasure. SSO creation normalizes email before insert, so the existing exact unique index closes future case-variant races; an unambiguous legacy mixed-case profile is normalized and reattached to the same UUID. Case-insensitive matching feeds erasure only through the conditional identity rules (RT-825/832), never through substring or broadened matches. |
| RT-2026-07-22-829 | Adjacent-alert authorization reviewer | Blocking unmatched proxies only at `/watch-rules` still leaves contextual C3 alerts, orphan `c3:` rows, and lifecycle state reachable or adoptable through the legacy alert routes—especially with tenancy disabled or an `UNASSIGNED` team snapshot. | High | Resolved and verified | Profile-less proxy callers now see neither contextual nor orphan `c3:` alerts/states with tenancy on or off; hidden C3 state is excluded from lists and C3 state mutation returns masked 404 before rate limiting or persistence. Legacy alert reads and caller-owned orphan legacy state remain compatible. Matched-proxy C3 state stamps the profile UUID; legacy state keeps the historical global `caller.id`. |
| RT-2026-07-22-830 | Unicode/privacy reviewer | SQLite's built-in `lower()` is ASCII-limited, so a non-ASCII case variant could evade the intended exact case-insensitive identity, SSO, operator-erasure, or document-erasure match even when Python normalization considered the values equal. | High | Resolved and verified | Every application SQLite connection registers deterministic `caos_unicode_lower`, and the shared exact-equality predicate selects that function for SQLite and `lower()` for PostgreSQL. Identity, profile creation, operator erasure, and document erasure all use the shared predicate; Unicode SQLite regressions prove profile and document cleanup without substring matching. The same case-insensitive predicate backs the RT-832 forwarded-email match, so a non-ASCII case variant cannot bypass the conditional self-erasure rule either. |
| RT-2026-07-22-831 | Rendered-truth reviewer | The zero-finding axe matrix passed while the 1440×900 screenshots showed "New rule" and "READ ONLY" rendered outside the Monitor inspector rail — the automated gate did not measure supporting-rail horizontal overflow, so a visually clipped desktop layout produced a green artifact (a visual false negative). | High | Resolved and verified | The gate was reopened, not annotated over: WatchRuleEditor/MonitorInspector grid and min-width constraints were repaired; `a11y-axe.mjs` now measures unexpected horizontal overflow on supporting context/inspector rails, and its RED run against the old layout proved the defect (inspector clientWidth 240 vs scrollWidth 273 — 33px overflow) before the corrected layout passed 1/1; a three-engine `monitor-08` inspector-bounds regression pins the contract; the full normal/reduced 1440×900 + 390×844 matrix was recaptured zero-finding and all four screenshots were re-inspected. |
| RT-2026-07-22-832 | Erasure-precedence reviewer | Cookie-authenticated self-erasure could include a forwarded-user/email principal taken from proxy headers even when that principal was not the authenticated caller — a stale or attacker-influenced `X-Forwarded-Email` could then broaden erasure into another identity's records. | High | Resolved and verified | `delete_profile` always supplies the profile UUID and canonical email, and adds the active forwarded-user/email principal only when `X-Forwarded-Email` case-insensitively matches the authenticated `caller.email` (shared RT-830 predicate semantics); a mismatched forwarded email cannot broaden erasure. Two fails-pre-fix cookie regressions pin the rule (1 failed / 1 passed before the fix; 2 passed after). |

Decision: accept the contained corrections after an independent whole-diff
review found no remaining High/Critical code defect. The final authoritative
server suite (2,919 passed, 15 skipped), three-engine real-API journey (18/18),
migration rehearsal, and the recaptured desktop/phone accessibility matrices
(post-RT-831 hardened harness) are green. A
pre-existing limitation remains explicit: operator erasure by email cannot
infer a distinct historical forwarded-user alias in non-C3 records because the
Analyst row does not store that proxy subject; active self-erasure supplies the
alias, and operator erasure of the UUID-owned C3 graph is complete. This remains
candidate-local evidence only:
CP-MON is **PROVISIONAL**, PD-06 is **OPEN**, and release is **NO-GO** pending
live PostgreSQL, H0 exact-image/config binding, external operation and flag
observation, enterprise transport, target-host capacity/fault evidence, and the
accepted low-volume scale closure.

## 2026-07-23 — live analytical charts and market-history critic pass

Decision under review: expose persisted Deep-Dive module charts and issuer
loan-mark / discount-margin history without turning incomplete runtime data into
apparently authoritative analysis.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-23-833 | Analytical-authority reviewer | A chart registry can silently fall back to design fixtures or partially shaped payloads, making illustrative data look like live engine output. | Critical | Resolved and verified | Live charts have a separate runtime-only registry, require the expected finite payload fields, label themselves as live engine output, and degrade to no chart for unknown, thin, or malformed payloads. Focused builder and interaction tests pin those states. |
| RT-2026-07-23-834 | Numeric/provenance reviewer | `NaN`, infinities, missing units, or weak source labels can produce misleading marks and committee-unfit summaries. | High | Resolved and verified | Runtime chart builders accept only finite numbers, omit unknown units instead of inventing one, retain source identifiers, and generate an accessible textual summary plus equivalent columns from the same data rows. |
| RT-2026-07-23-835 | Compatibility reviewer | Requiring `market_history` in every client fixture and cached response breaks older payloads even though the profile can safely render an empty state. | Medium | Resolved and verified | The server response remains explicit, while the TypeScript client boundary accepts an omitted legacy field and normalizes it to an empty history before rendering. Type checking and profile regressions cover the compatibility path. |
| RT-2026-07-23-836 | Scale/tenancy reviewer | An unbounded history query can grow indefinitely; broadening it across analysts can also expose another desk's private snapshot. | High | Resolved and verified | The query retains issuer and caller/public ownership predicates, fetches only the latest 120 rows, and reverses that bounded result for oldest-to-newest chart display. Server route tests and lint cover the query path. |
| RT-2026-07-23-837 | Regression reviewer | The combined Deep-Dive/Profile WIP touches high-risk shared UI and API flows and could merge on narrow visual evidence alone. | High | Resolved and verified | Merge is gated on GitNexus change detection, frontend lint/type/unit/build gates, focused server route tests and lint, PR CI, and post-merge main verification. |

Decision: accept the contained live-chart and bounded market-history additions
after the listed local and hosted gates pass. Missing or malformed analytical
data must remain an explicit empty state; no demo fixture is an authorized
fallback on a live run.

## 2026-07-23 — First-run UX intervention batch (post-freeze)

**Decision:** apply the 2026-07-23 UX/IA audit interventions — Pipeline moves
to the Intake & Runs nav group; signup staged into identity → security with
coverage/location dropped; intake result step pushes "Watch run in Pipeline";
PM/QA cold-start states teach the prerequisite path; IC-decision drawer nudges
watch-rule creation; onboarding doc reframed to five stages / six flagship
concepts and its golden path corrected to Directory → Upload → Pipeline.

| ID | Date | Decision / Plan | Objection | Impact | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| RT-2026-07-23-01 | 2026-07-23 | Pipeline → Intake & Runs group | Moving Pipeline breaks steady-state muscle memory and any test or spec pinning it to the Monitor group. | Medium | Resolved | Every nav consumer derives from `NAV_GROUPS` (ConceptNav, ConceptHotkeys, WorkflowRail, palette); grep found no unit or e2e assertion pinning `/pipeline` to `monitor`; `nav.test.ts` now pins `/pipeline` → `intake` deliberately. |
| RT-2026-07-23-02 | 2026-07-23 | Staged signup | A client-side step split could desync from the server contract or strand a user mid-registration. | High | Resolved | The split is presentation-only: one `POST /api/auth/register` fires on the final step; identity values persist across Back; `LoginLanding.test.tsx` walks both steps including the Back path and asserts the single register payload. |
| RT-2026-07-23-03 | 2026-07-23 | Drop coverage/location from signup | Silently loses profile-metadata capture with no replacement surface. | Medium | Accepted | Both fields are write-only today (no UI or server read path); `RegisterRequest` keeps them Optional (auth.py:109-110) and the columns remain (migration 0017), so capture returns intact with a future profile editor. |
| RT-2026-07-23-04 | 2026-07-23 | Decision→watch-rule nudge | Adds a network call to the decision path and could over- or under-claim rule coverage. | Medium | Resolved | The check fires only after the decision persists and is failure-silent (never blocks recording); coverage counts issuer-scoped + team-scoped rules; portfolio-scoped rules are conservatively not counted, and the copy claims only "no issuer or team watch rule". |
| RT-2026-07-23-05 | 2026-07-23 | Landing UI changes while H0 candidate `3b66da67` is frozen | Merging would invalidate the frozen release candidate. | High | Resolved | Ships as a post-freeze draft PR on `claude/start-5t1kuy` (same pattern as #169/#191); nothing merges to `main` before the release decision. |

## 2026-07-26 — Report Studio paper-tranche accessibility critic pass

Decision under review: replace the dark-workspace tranche ramp inside the light
Report Studio tear-sheet and add a boundary between adjacent stacked segments.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-07-26-838 | Contrast reviewer | Reusing the dark-workspace ramp puts paper-coloured 10px value labels on fills that measure only 1.71–4.36:1, below the WCAG AA 4.5:1 floor. | High | Resolved and verified | A dedicated `--paper-tranche-*` ramp clears 4.5:1 against the default paper and every analyst-selectable sheet colour. Token-parity and contrast tests pass for all five tranches. |
| RT-2026-07-26-839 | Color-vision reviewer | Uniformly darkening the series can collapse adjacent category separation, while an unconditional SVG stroke can repaint a very narrow segment. | High | Resolved and verified | Hue and lightness remain staggered, and a paper-coloured hairline separates ordinary segments. The stroke is suppressed at widths of 2px or less so it cannot consume a sliver. |
| RT-2026-07-26-840 | Token-integrity reviewer | A misspelled CSS variable fails silently to the property's initial value; the existing `--tranche-equity` typo rendered black and could recur outside this chart. | High | Resolved and verified | Production policy tests now require every `--caos-*`, `--tranche-*`, and `--paper-*` `var()` reference to resolve to a definition in `globals.css`. |
| RT-2026-07-26-841 | Regression reviewer | A readability rewrite of cumulative SVG geometry can subtly change floating-point order, label thresholds, or the narrow-segment boundary. | Medium | Resolved and verified | The rewrite tournament retained the same ordered reduction and cumulative update, the exact `> 2` and `>= 86` thresholds, and the same SVG contract. Focused visualization/token tests (10/10), TypeScript, GitNexus impact review, and the real `/reports` axe/layout scan are green. |

Decision: accept the paper-specific ramp and bounded segment hairline. The
change is limited to Report Studio presentation; it does not alter report data,
ordering, calculations, or the dark-workspace tranche semantics.

## 2026-08-19 — Clean-slate documentation path reconciliation

Decision under review: remove pre-clean-slate audits and update the remaining
repository guidance for the current CAOS tree.

| ID | Objection | Impact | Status | Resolution |
|----|-----------|--------|--------|------------|
| RT-2026-08-19-001 | Historical review records still cite deleted `caos/docs/` briefs and old `caos/frontend/src/` files. Recreating those paths would make obsolete architecture look active. | Medium | Resolved | Obsolete audit artifacts were removed. The append-only records remain historical, and this note marks those paths as non-authoritative. Current guidance is in `README.md`, `caos/README.md`, `PRODUCT.md`, `DESIGN.md`, and `CLAUDE.md`. |

## 2026-08-19 — Issuer-first source and metric refresh critic pass

Decision under review: make the issuer registry the routine entry point for search, source maintenance, and explicit metric refresh while retaining cases as frozen governance boundaries.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-19-002 | Saboteur | A late or partial refresh can replace newer live metrics, mix old and new values, or leave the live pointer on an incomplete snapshot. | Critical | Resolved in design; implementation gate | Each refresh pins one immutable issuer source set. Only one refresh may run per issuer. Publication inserts the complete metric snapshot and updates the live pointer in one transaction after the route and quality gate succeed. Failed or partial work never changes the pointer. A newer uploaded source set remains visibly pending. |
| RT-2026-08-19-003 | Analytical-authority reviewer | Immediate publication can make incomplete extraction look authoritative or silently retain stale values for metrics absent from the new source set. | Critical | Resolved in design; implementation gate | Publication requires a successful governed Full Credit Screen and its quality gate. Every catalog metric records a value or an explicit unavailable status for the pinned source set. The publisher never fills missing values from an older snapshot. The interface shows the source-set version, refresh time, quality state, and changes from the prior snapshot. |
| RT-2026-08-19-004 | Security auditor | Moving sources above cases can expose issuer documents through search or direct object identifiers to authenticated users outside the intended authority boundary. | High | Resolved in design; implementation gate | Issuer reads stay inside the authenticated self-hosted deployment. Writes require ANALYST, APPROVER, or ADMIN. Source access resolves through an authorized issuer or case source set before returning metadata or content. Existing malware, archive, size, and vault controls remain mandatory. Case-local notes never enter the issuer library implicitly. |
| RT-2026-08-19-005 | New hire | If issuer and case ownership overlap, future code will not know where sources, metrics, recommendations, and reports belong. | High | Resolved in design; implementation gate | The issuer owns reusable documents and live screening metrics. A case pins issuer source-set and metric-snapshot identifiers at creation, then owns its runs, artifacts, notes, assumptions, recommendations, approvals, and reports. Later issuer refreshes cannot mutate existing cases. |
| RT-2026-08-19-006 | Identity-integrity reviewer | Search-first creation can produce duplicate issuers through ticker case, aliases, legal-name variants, or concurrent requests. | High | Resolved in design; implementation gate | Creation normalizes ticker and names, rejects an exact in-scope ticker conflict, shows likely name or alias matches before creation, and uses database constraints plus idempotent create handling. Phase 1 never auto-merges issuers. Existing cases backfill to distinct issuers to avoid accidental consolidation. |
| RT-2026-08-19-007 | Operations reviewer | Rebuilding the legacy dictionary as a second authority can restore divergent metric definitions and provenance precedence across surfaces. | High | Resolved in design; implementation gate | Metric snapshots are projections from governed typed run outputs, not an independent write surface. One versioned catalog defines key, label, unit, polarity, basis, and extraction rule. No manual metric editing, seeded live values, or surface-specific precedence is in scope. |

Decision: accept the issuer-first design subject to these implementation gates. The design restores routine issuer search and maintenance without reviving the legacy dictionary as an authority. Application work must prove atomic publication, direct-object authorization, immutable case pinning, duplicate prevention, and no stale-value carry-forward before release.

## 2026-08-19 — Adversarial UX hardening critic pass

Decision under review: make the existing case workspace honest under reload, narrow layouts, failed API calls, evidence deep-links, and unsaved report edits without changing the underlying authority model.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-19-008 | Saboteur | URL-derived state can diverge from server-rendered markup and silently overwrite a deep-linked run during initial case loading. | High | Resolved | Query state now hydrates after the deterministic server render, preserves an explicit run id, and mirrors state back to the URL only after hydration. A browser smoke test confirms the run query survives loading and no hydration warning is emitted. |
| RT-2026-08-19-009 | Evidence auditor | An artifact link that only changes the client URL but has no case-authorized detail route leaves the analyst at a decorative evidence rail. | High | Resolved | Added a case-authorized artifact detail route and renders the artifact summary, lineage, evidence references, and expanded source blocks. The route returns 404 for a missing artifact and was verified with FastAPI TestClient. |
| RT-2026-08-19-010 | Workflow reviewer | A report draft can be lost by SPA navigation or a case switch even if the browser unload warning exists. | High | Resolved | Drafts are session-scoped, visibly marked unsaved, guarded on internal links and case changes, and retained until an explicit freeze succeeds. Browser verification confirms a dismissed discard prompt keeps the current route and draft. |
| RT-2026-08-19-011 | Accessibility reviewer | A desktop-only gate prevents keyboard, zoom, and reflow access below 900px; async failures are indistinguishable from empty data. | High | Resolved | Replaced the gate with a horizontal mobile rail and stacked panels, added explicit loading/error states, and re-ran the axe suite across all nine destinations with zero violations. |

Decision: accept the hardening pass subject to continued API-backed browser testing for real accepted snapshots and report approval flows. No authority or recommendation semantics were widened by the UX changes.

## 2026-08-19 — CI workflow alignment critic pass

Decision under review: align the repository's pull-request and scheduled QA
workflows with the current CAOS tree so the gates execute real checks instead of
referencing removed suites, scripts, and lockfiles.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-19-012 | Coverage reviewer | Removing stale jobs could silently reduce validation coverage. | High | Resolved | Preserve the actual frontend lint/typecheck/build, backend pytest/ruff, security audit, deploy asset, corpus, and Docker-image checks. Remove only jobs whose inputs do not exist in this repository. |
| RT-2026-08-19-013 | Release engineer | Without a requirements lock, CI may become non-reproducible. | Medium | Accepted | The current supported dependency contract is the two checked-in requirements files; no lockfile is present. Keep dependency ranges explicit and track lock adoption as a separate release-hardening task rather than pretending the missing lock is enforced. |
| RT-2026-08-19-014 | Security auditor | A route audit that scans deleted modules can fail loudly but still provide no assurance about live routes. | Critical | Resolved | Point the audit at `caos/server/caos/http.py`, retain the fail-closed parser behavior, and require every live route except health to use the current identity/case authorization helpers. |
| RT-2026-08-19-015 | Operations reviewer | Docker, image scanning, and full-history secrets cannot be proven on this workstation. | Medium | Accepted | Keep those checks in CI/nightly and record local Docker-daemon absence as an execution limitation; local equivalents cover static configuration and available application checks. |

Decision: accept the alignment. No product behavior or authority boundary changes;
the change restores trustworthy execution of the repository's existing quality
controls and makes unverified remote-only checks explicit.

## 2026-08-20 — Deep-Dive focus review critic pass

Decision under review: replace persistent Deep-Dive module and evidence columns
with a narrative-first focus canvas, compact controls, and contextual drawers
while preserving the legacy evidence-chip interaction.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-20-001 | Evidence auditor | Hiding the evidence rail could make lineage less discoverable and encourage analysts to read unsupported prose. | High | Resolved in design | Evidence chips remain inline after every material claim; a named Sources control stays in the global header; both open the source in one interaction without permanently narrowing the canvas. |
| RT-2026-08-20-002 | Legacy-workflow reviewer | Replacing legacy `E-xx` chips with verbose page-labelled pills would weaken scanability and lose cross-highlight behaviour. | High | Resolved in design | Preserve compact stable IDs, blue/amber severity treatments, matching-ID synchronization on hover/focus, and exact-source activation. Page and section detail moves to the drawer. |
| RT-2026-08-20-003 | QA reviewer | Moving QA off-canvas could hide a material exception behind a favourable `passed` label. | High | Resolved in design | The header always shows the textual QA state and critical count when non-zero. Warning evidence carries an amber glyph, and the QA drawer leads with exceptions before passed checks. |
| RT-2026-08-20-004 | Accessibility reviewer | Overlay drawers can trap focus incorrectly, lose the analyst's place, or become unusable at zoom and narrow widths. | High | Resolved in design; implementation gate | Use native dialog semantics, Escape close, focus containment and trigger restoration; drawers fit the viewport without horizontal overflow. Verify with axe, keyboard tests, narrow reflow, and zoom. |
| RT-2026-08-20-005 | Analytical-integrity reviewer | A polished chart shell could tempt the client to invent series values that are absent from the current artifact payload. | Critical | Resolved in design; implementation gate | Render only governed values carried by an accessible visual payload. Extend the server contract where necessary; never infer or fabricate chart series in the client. |
| RT-2026-08-20-006 | Workflow reviewer | Removing persistent module navigation can make cross-module comparison slower. | Medium | Accepted with mitigation | The module selector remains fixed immediately below the global header and exposes position in the set. Prior-snapshot comparison is one secondary action; persistent columns are not justified by the review task. |

Decision: accept the focus-view design subject to exact snapshot-pinned evidence
resolution, governed visual data, drawer focus restoration, and accessibility
verification. The design intentionally excludes portfolio, coverage, committee,
and authoring workflows.

## 2026-08-22 — Application-wide Analyst Workbench critic pass

Decision under review: reorganize CAOS around an issuer-first Analyst Workbench with workflow navigation, curated conclusion-first layouts, linked visual analysis, contextual evidence and QA, and accepted-snapshot authority.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-22-001 | Saboteur | A stale issuer or case selection can bind a workflow to the wrong snapshot while the shell still displays the prior context. | Critical | Resolved in design; implementation gate | Every workflow request carries explicit issuer, case, and accepted-authority identifiers. Context changes cancel or ignore stale responses and clear incompatible selections before rendering. |
| RT-2026-08-22-002 | Analytical-integrity reviewer | Tableau-style linked highlighting can imply a relationship that the governed payload does not establish. | Critical | Resolved in design; implementation gate | Linked content requires typed relationships supplied by governed payloads. The client cannot infer links from matching labels, colours, positions, or values. |
| RT-2026-08-22-003 | Security auditor | Universal issuer, case, and evidence search can disclose unauthorized names or direct-object identifiers before the user opens a result. | Critical | Resolved in design; implementation gate | Search applies authorization before returning result labels. Palette and drawer actions use the same authorized routes as visible actions. Direct identifiers cannot broaden access. |
| RT-2026-08-22-004 | QA reviewer | Compact QA chrome can hide a material exception behind a favourable aggregate status. | High | Resolved in design | Critical and warning states remain visible on the resting canvas. The QA drawer lists exceptions before passed checks, and status never relies on colour alone. |
| RT-2026-08-22-005 | Workflow reviewer | Replacing eight destinations with six workflows can break bookmarks, deep links, and user muscle memory. | High | Resolved in design; implementation gate | Existing routes redirect to workflow destinations while preserving authorized issuer, case, run, artifact, and source identifiers. Migration ships in bounded phases with explicit redirect tests. |
| RT-2026-08-22-006 | New hire | Adding shell, palette, drawers, linked state, redirects, and workflow surfaces inside the current `Workspace.tsx` monolith will make every later change harder. | High | Resolved in design; implementation gate | The implementation plan must separate the shell, workflow surfaces, and contextual inspectors by existing responsibilities. It must avoid speculative layers and preserve current contracts. |
| RT-2026-08-22-007 | Accessibility reviewer | A desktop-first terminal can become unusable at 200% zoom, narrow widths, or with keyboard-only navigation. | High | Resolved in design; implementation gate | Each migration phase requires 1440 px, 1024 px, 200% zoom, keyboard, reduced-motion, chart-equivalent, and axe verification before consolidation. |
| RT-2026-08-22-008 | Performance reviewer | Cross-workflow context and large analytical surfaces can trigger redundant refetches or retain sensitive cached data after an identity change. | High | Resolved in design; implementation gate | Cache only accepted authority within its issuer, case, and identity scope. Clear scoped caches on identity or authorization changes and measure performance against the current baseline. |

Decision: accept the application-wide Analyst Workbench design subject to explicit authority binding, authorized search, typed linked relationships, route compatibility, bounded component responsibilities, and phased accessibility verification.

## 2026-08-22 — Analyst Workbench adversarial-fix critic pass

Decision under review: close the navigation, authority-race, routing, drawer, and QA gaps found in the application-wide workbench implementation.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-22-009 | Authority reviewer | A delayed run-creation response can attach Case A's new run after the analyst has switched to Case B. | Critical | Resolved | Run creation now captures both case identity and request generation; case changes invalidate the generation, stale success/error/finally paths are ignored, and a delayed-response browser check verifies that Case B retains its own execution. |
| RT-2026-08-22-010 | Security reviewer | Malformed initial case/run identifiers can trigger unauthorized detail requests before the authorized case list resolves, then leave the shell loading forever. | Critical | Resolved | Case and run detail effects now require membership in the authorized case list. Case-list reconciliation consumes invalid route authority, selects an authorized fallback through the normal boundary, and clears incompatible run state. |
| RT-2026-08-22-011 | Navigation reviewer | A persistent client shell that discards route children makes the page boundary dead code; naïvely restoring children can instead hide or duplicate destination content. | High | Resolved | The root layout owns one persistent shell, known route pages validate and return an empty boundary, unknown routes render only the not-found boundary, and browser/build checks cover both paths. |
| RT-2026-08-22-012 | Accessibility reviewer | Drawer links can navigate while leaving the modal over the destination, and evidence links can immediately reopen the same drawer from query state. | High | Resolved | Drawer navigation uses native dialog close, evidence navigation targets the source row by fragment rather than drawer-opening query state, and browser checks verify the modal is dismissed and the target is visible. |
| RT-2026-08-22-013 | QA reviewer | Fixed smoke fixtures make repeat runs fail on uniqueness constraints, while performance measurements that only log values cannot prevent regressions. | High | Resolved | Smoke fixtures use unique per-run identifiers, the suite passes twice against one persistent server, and DCL/FCP are enforced against positive configurable budgets. |

Decision: accept the fixes. Release remains gated on the repeatable workbench smoke suite, strict frontend checks, accessibility validation, and change-scope review.

## 2026-08-22 — Backup pair publication critic pass

Decision under review: preserve the existing `caos.dump` / `vault.tgz` operator
interface while preventing an interrupted or concurrent backup from being
silently restored as a mixed pair.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-22-014 | Durability reviewer | Two independent file moves can expose a new dump with an old vault if the process dies or another publisher interleaves. | Critical | Resolved in design | Serialize publishers with an atomic destination lock and publish a checksum manifest last. Restore verifies the standard pair against the manifest before it creates any drill target. |
| RT-2026-08-22-015 | Compatibility reviewer | Replacing the pair with a generation directory or new pointer path would break the documented operator interface. | High | Resolved | Keep `caos.dump` and `vault.tgz` at their existing paths; add only the companion manifest. Generic manually supplied restore pairs remain supported without a manifest. |
| RT-2026-08-22-016 | Operations reviewer | A process killed while holding a lock can prevent the next backup indefinitely. | Medium | Accepted with mitigation | The lock fails closed with an explicit operator-review error. Automatic stale-lock removal is unsafe because a live long-running dump cannot be distinguished reliably. |
| RT-2026-08-22-017 | Security reviewer | A checksum manifest might be mistaken for tamper-proof provenance. | Medium | Accepted | The manifest detects accidental mixed publication, not malicious backup-store modification. Access control and durable remote backup integrity remain separate operational controls. |

Decision: accept the lock-plus-manifest design. It keeps the public backup paths,
serializes writers, and turns the unavoidable multi-file crash window into a
safe restore refusal rather than silent mixed-state recovery.

## 2026-08-22 — Production-scale local dataset and full-inventory critic pass

Decision under review: treat the sanitized PostgreSQL/ClamAV fixture and the
analyst plus PM/QA route inventory as the local production-readiness baseline.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-22-018 | Data-integrity reviewer | A dump taken while the API or worker is still writing can disagree with the source vault even when `pg_restore` succeeds. | Critical | Resolved | Stop both application processes before the final dump, then restore the frozen custom-format dump into a fresh database and verify revision and cardinalities. The fixture README records the final checksum and sanitized vault path. |
| RT-2026-08-22-019 | Concurrency reviewer | A merged PostgreSQL revision can be installed in memory before commit, so a failed write leaves later rollback code mutating detached objects. | Critical | Resolved | The SQL step now returns pending and database-authoritative states. Ordinary and fenced callers adopt the pending state only after commit and restore the authoritative state on failure. A revision-merge/commit-failure regression covers both paths. |
| RT-2026-08-22-020 | Scale reviewer | Calling 218 cases and 130 sources “production scale” can hide that the current state envelope, case table, and source table are not paginated or horizontally scalable. | High | Accepted with explicit ceiling | The 24-reader burst is gated at p95 under 1.5 seconds and the dense DOM is checked for alerts, stuck loading, accessibility, and overflow. The fixture README names the single-API-process topology, multi-writer CAS, and pagination thresholds as external gates; it does not claim arbitrary scale. |
| RT-2026-08-22-021 | QA reviewer | “Every control” can be overstated if hundreds of repeated Select buttons and source summaries are merely counted. | High | Resolved by scope definition | Inventory every visible element for both identities, exercise every distinct control behavior, and treat repeated row controls as one implementation equivalence class. Record the distinction in the handoff rather than claiming every duplicate row was clicked. |
| RT-2026-08-22-022 | Security reviewer | Synthetic identity headers can prove application RBAC while bypassing the real OIDC redirect, MFA, and oauth2-proxy exchange. | High | Accepted external gate | Verify trusted-edge rejection, role resolution, cross-case isolation, analyst 403, admin membership, and Approver ratification locally. Keep the real IdP/step-up exchange explicitly unverified and required before deployment. |
| RT-2026-08-22-023 | Analytical-authority reviewer | A visually complete Model Builder could conceal that official CP-MODEL authority remains unavailable. | Critical | Resolved | Preserve and test the explicit blocked state. Do not seed fabricated model output into the dataset. Signed corrected Deploy V authority remains a named external gate. |

Decision: accept the local baseline within its documented topology and scale.
The dump is frozen and restore-proven, all eight product destinations pass for
both identities, and the remaining IdP, official-model, and horizontal-writer
gates are explicit rather than represented as locally complete.

## 2026-08-22 — Production-scale completion-audit addendum

Decision under review: close the local readiness goal after the second full
inventory pass and publish the rebuilt fixture as the reusable baseline.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-22-024 | Analytical-authority reviewer | Pathway names and accepted statuses can all be present while the accepted snapshots contain no artifacts, making a superficially complete fixture analytically empty. | Critical | Resolved | The completion audit now requires each of the six pathways to have a succeeded accepted run whose nonempty node set is entirely succeeded and artifact-bound. All six pathways were re-executed under the fixed worker, yielding 44/44 durable node artifacts; latest and visible authority point to repaired snapshots. Older empty snapshots remain explicitly labeled regression evidence rather than being silently erased. |
| RT-2026-08-22-025 | QA reviewer | A one-off manual inventory cannot prove repeatability, and route interception can race page teardown to produce false product failures. | High | Resolved | The inventory is a checked-in runnable harness with exact URL predicates and fixture-identity assertions. It releases delayed routes, waits for network idle, and passed twice consecutively across 16 loaded combinations, 46 controlled state probes, all four role identities, and the staged load/recovery gate. |
| RT-2026-08-22-026 | Portability reviewer | Source records contain absolute local vault paths, so restoring the dump under another checkout root does not automatically relocate source bytes. | Medium | Accepted with explicit boundary | This is a local fixture, not a portable deployment backup. Restore at the documented checkout path or rewrite the synthetic `vault_path` prefix as a deliberate local migration and re-run the 143-reference existence/hash check. No cross-host portability claim is made. |
| RT-2026-08-22-027 | Release reviewer | A fresh Next.js build can leave the FastAPI static directory serving stale build IDs even though source lint and build pass. | High | Resolved | The final build is synchronized into the server static directory, directory parity is exact, and a live authenticated route was checked to reference only assets present in the deployed directory before the runtime was frozen. |

Decision: close the local pass. The frozen revision and every restored state
cardinality match, all 143 vault references resolve with matching hashes, the
secret scan is clean, and no high-impact local objection remains open.

## 2026-08-23 — Production-scale rerun and narrow-reflow critic pass

Decision under review: close the production-like local rerun after correcting
responsive reachability, Report Studio reflow, and scanner lifecycle failures.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-23-028 | Accessibility reviewer | The narrow shell hides workflow tool links, leaving Cases and Run Console unreachable even though their routes render correctly. | High | Resolved | Add only the tool-only destinations to the existing command palette, preserve case/run query authority, and verify both links for analyst and PM/QA users at 375px. |
| RT-2026-08-23-029 | Report reviewer | A full snapshot digest can widen the light paper proof beyond the viewport and create page-level horizontal scrolling. | High | Resolved | Reuse the existing monospace wrapping utility on the snapshot digest and retain a 375px Report Studio overflow assertion in the workbench smoke test. |
| RT-2026-08-23-030 | Operations reviewer | The mounted ClamAV configuration omits the Unix socket required by the official image lifecycle and the Compose healthcheck; TCP scanning works briefly, then the scanner exits after its socket wait. | Critical | Resolved | Restore `LocalSocket /tmp/clamd.sock` while retaining TCP 3310, add a configuration regression, and verify Compose-equivalent `clamdscan --ping` health plus application source intake. |
| RT-2026-08-23-031 | Performance reviewer | A single 24-reader run can breach the 1.5-second p95 gate because local host scheduling queues every endpoint uniformly, obscuring whether one API route regressed. | High | Resolved by bounded diagnosis | Keep the gate unchanged, repeat the exact stage with per-endpoint timing, and require a clean complete rerun. No endpoint dominated and no request failed; the final complete runs passed at 1,105.3ms and 1,159.5ms p95 with 49.0ms and 36.6ms recovery. |

Decision: close the local rerun. The final production image, corrected scanner,
both role journeys, all 16 loaded route combinations, all 46 controlled states,
54 rendered axe combinations, 16 narrow-touch combinations, vault hashes,
secret scan, and staged load/recovery gate pass. Real IdP exchange, signed model
authority, and horizontal multi-writer scale remain the existing external gates.

## 2026-08-23 — Hybrid CP-DR agent runtime critic pass

Decision under review: keep the governed Deploy V DAG as the sole supervisor and
enable one bounded, source-bound CP-DR specialist agent inside its existing node.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-23-032 | Methodology-authority reviewer | CP-DR contains conflicting CP-0 language; treating CP-0 as optional could break the runtime catalog and invocation envelope. | Critical | Resolved in design | The pilot follows the stricter catalog/runtime/envelope contract and requires an accepted CP-0 artifact until signed authority resolves the conflict. |
| RT-2026-08-23-033 | Research-governance reviewer | Starting research immediately would fabricate plan approval because the analyst never saw the generated 3–5 workstreams or their disconfirming tests. | Critical | Resolved in design | CP-DR generates the plan without substantive evidence access, pauses the run with the exact plan hash, and resumes only after case-authorized analyst approval. Scope changes require a new run. |
| RT-2026-08-23-034 | Data-governance reviewer | Confidential credit documents could leave the deployment under an unapproved retention or processing arrangement. | Critical | Resolved as activation gate | Provider activation requires an approved commercial processing arrangement and ZDR configuration. The key exists only in the worker; Phase 1 excludes Files, remote MCP, managed agents, web, shell, and code execution. |
| RT-2026-08-23-035 | Prompt-injection reviewer | Document instructions could widen tools, change methodology authority, or induce cross-case reads. | Critical | Resolved in design | Source text remains lower-authority untrusted data. One typed read-only evidence tool validates case, pinned source set, source and block IDs, and cumulative budgets; the model cannot supply authority fields. |
| RT-2026-08-23-036 | Analytical-contract reviewer | The host's shallow typed payload and Markdown renderer do not match the vendored CP-DR canonical schema, so schema-valid provider JSON could still become a non-canonical artifact. | Critical | Resolved as Phase 0 blocker | Reconcile the CP-DR payload, YAML envelope, ordered sections, citation rules, and vendored validators before any provider-backed artifact can be persisted or accepted. |
| RT-2026-08-23-037 | Concurrency reviewer | The current 60-second lease can expire during a normal provider call, allowing stale events or paid work that cannot persist. | High | Resolved in design | Add fenced lease renewal and fenced lifecycle events. Loss of ownership stops tools, discards the result, and emits no stale terminal event. |
| RT-2026-08-23-038 | Cost-abuse reviewer | SDK retries, repair loops, and repeated evidence reads could multiply spend or exhaust context without a product-visible limit. | High | Resolved in design | Disable SDK retries; allow one host retry and one validation repair inside fixed turn, tool, evidence, token, wall-time, and concurrency ceilings. Record usage for every attempt. |
| RT-2026-08-23-039 | Persistence reviewer | Raw transcripts, source excerpts, or token streaming would bloat the revisioned state envelope and expand sensitive-data retention. | High | Resolved in design | Persist only operational metadata, digests, referenced block IDs, and final canonical output. Store no hidden reasoning or duplicate source text; keep events coarse. |
| RT-2026-08-23-040 | Quality reviewer | A technically valid research artifact can still be generic, weakly cited, or worse than the existing path. | High | Resolved as rollout gate | A 20-case blinded evaluation requires full material-claim citation coverage, zero unsupported material claims, 19/20 completion, bounded latency, complete telemetry, and 80% of outputs at 4/5 or better and above baseline. |
| RT-2026-08-23-041 | Rollback reviewer | Falling back to the current generic CP-DR summary after provider failure would present placeholder prose as successful research. | High | Resolved in design | Provider and validation failures are explicit. Disabling or rolling back CP-DR makes the pathway visibly unavailable; it never substitutes the generic summary. |
| RT-2026-08-23-042 | Complexity reviewer | Adding a generic agent framework or provider abstraction before one module proves value would create more architecture than product capability. | Medium | Resolved in design | Extend the existing Anthropic gateway directly and use a static CP-DR allowlist. Every provider or module expansion requires a separate design and evaluation. |

Decision: accept the bounded CP-DR hybrid design subject to its Phase 0 authority
reconciliation, analyst plan approval, provider-data activation gate, and shadow
evaluation thresholds. No other module or provider is approved by this pass.

## 2026-08-23 — Hybrid CP-DR implementation-plan critic pass

Decision under review: execute the approved hybrid design through a seven-phase
plan that keeps the feature disabled until authority, fencing, security, quality,
and rollout gates pass.

| ID | Perspective | Objection | Impact | Status | Resolution / disposition |
|----|-------------|-----------|--------|--------|--------------------------|
| RT-2026-08-23-043 | Methodology-authority reviewer | CP-DR authority is internally inconsistent on CP-0, FULL/LITE scope, issuer/sector/theme identity, plan canonicalization, reporting period, nested row schemas, and stage-zero CP-PARSE identity. Coding through these gaps could create a host contract that cannot reproduce the signed bundle. | Critical | Resolved as Phase 0 gate | Freeze the stricter intersection before code: accepted CP-0, FULL issuer-only, supplied-only, standard budget, exact plan approval, canonical sorted-JSON hash, deterministic scope key and reporting-period mapping, strict host row schemas, and host-only CP-PARSE identity. Do not hand-edit integrity-pinned vendor files. |
| RT-2026-08-23-044 | Authorization reviewer | `require_case(..., write=True)` checks global identity role but not the stored role on that case. Adding plan approval would inherit a privilege mismatch, and the root fix has a CRITICAL GitNexus blast radius across 33 symbols and 32 flows. | Critical | Resolved as isolated prerequisite | Phase 1 fixes the shared guard before any CP-DR endpoint and runs a complete stored-role × global-role write matrix plus route security and full server regression. Later phases cannot start until this gate passes. |
| RT-2026-08-23-045 | Cost/reliability reviewer | Messages has no documented idempotency key. Retrying a timeout can duplicate provider cost while actual usage remains unknown, and a reclaimed in-flight run could repeat it again. | Critical | Resolved in design detail | Pre-count and reserve input/output budgets before each request, persist an in-flight digest, keep unknown timeout reservations charged, retry only inside the remaining run budget, and fail closed when reclaim finds unresolved in-flight work. |
| RT-2026-08-23-046 | Concurrency reviewer | Run-attached research state avoids a migration, but whole-envelope PostgreSQL persistence and a long model call can still produce stale state, false events, or budget resets. | High | Resolved in phased foundation | Land renewable 60-second leases, a 20-second heartbeat, fenced worker events/audits, persisted cumulative budgets, and a real PostgreSQL takeover test before any provider integration. |
| RT-2026-08-23-047 | Data-governance reviewer | Sharing provider configuration between the API and worker could leak the key to the public app container or make disabled deployments impossible to boot. | Critical | Resolved in deployment contract | Both services receive only feature/pilot/model settings; `ANTHROPIC_API_KEY` is optional and worker-only. Health never calls the provider or exposes pilot/key state. Live testing remains blocked on approved processing and organization-level ZDR. |
| RT-2026-08-23-048 | Analytical-contract reviewer | The vendored CP-DR directory has no completeness validator, and the host's current generic payload/Markdown shape is incompatible with the canonical handoff. Treating the missing script as real or persisting before full validation would manufacture false completion. | Critical | Resolved in implementation sequence | Correct the design reference; add a strict host semantic-completeness gate, reuse the actual vendored confidence scorer and handoff validator, and permit fenced persistence only after canonical filename, YAML, identity, citations, six H2s, and numerical context pass. |
| RT-2026-08-23-049 | Product/accessibility reviewer | A generic paused badge can mislabel pending plan approval as missing sources, and a long workstream/hash review can become inaccessible or unusable at the narrow desk layout. | High | Resolved in UI gate | Branch on explicit pause codes, show every plan field and full hash, use native labeled controls and semantic tables/lists, preserve text alongside status color, and add a deterministic pending-plan fixture to workbench and axe checks at 375px. |
| RT-2026-08-23-050 | Scope reviewer | Implementing LITE, sector/theme research, web access, another provider, or additional agent modules under the same rollout would bypass unresolved methodology and evaluation gates. | High | Resolved by hard boundary | Phase 1 is FULL issuer-only CP-DR with supplied sources. All listed expansions require a new design, authority review, evaluation corpus, and red-team gate. |

Decision: accept the implementation plan subject to its ordered exit gates. The
authorization, lease/fencing, canonical-artifact, ZDR, 20-case shadow, and
rollback gates are blocking; passing later aggregate tests cannot waive an
earlier critical failure.
