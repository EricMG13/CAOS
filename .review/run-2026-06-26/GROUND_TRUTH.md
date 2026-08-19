# Adversarial Review — Ground Truth Brief (run-2026-06-26)

SCOPE: codebase (auto-triaged to the CAOS financial engine + its public entry points).
RULE: **Change nothing under `caos/`.** All artifacts go under `.review/run-2026-06-26/`.
Repro tests may ONLY be written under `.review/run-2026-06-26/repro/`.

## How to run the test suite (prod-parity venv)
```
cd "/Users/ericguei/Claude/Projects/Credit Operating System/caos"
PYTHONPATH=server server/.venv/bin/python -m pytest <path> -q
```
- `server/.venv/bin/python` is py3.9 with pytest_asyncio. System python3 cannot collect.
- Engine imports use `from engine.x import y` with `PYTHONPATH=server`.
- Clear `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` for offline determinism.
- To repro a domain-math bug: write a standalone `test_*.py` under
  `.review/run-2026-06-26/repro/`, `import sys; sys.path.insert(0, ".../caos/server")`,
  call the engine function directly, assert the WRONG output to PROVE the defect.

## Triaged file set (highest-risk surface)
**Domain core (financial math — highest value):**
- `caos/server/engine/capstructure.py` — recovery waterfall (ACTIVELY MODIFIED +66/-22;
  golden contract test `caos/tests/server/test_recovery_waterfall_contract.py` pins 16 cases).
- `caos/server/engine/metrics.py` — METRIC_CATALOG, leverage/coverage extraction,
  `leverage_plausibility_finding` cross-check. **NO direct test.**
- `caos/server/engine/periods.py` — `year()` / `latest()` period selection. Shared by
  capstructure + metrics. **NO direct test.**
- `caos/server/engine/covenants.py` — covenant headroom/cushion math (326 lines).
- `caos/server/engine/adjusted.py` — adjusted-EBITDA reconciliation (high churn).
- `caos/server/engine/edgar_cp1.py` / `reported_cp1.py` — XBRL + reported extraction.
- `caos/server/engine/liquidity.py`, `coststructure.py`, `refinancing.py`,
  `distress.py` (Altman Z''), `downside.py`, `relval.py`, `peers.py`.

**Orchestration / entry points:**
- `caos/server/engine/runner.py` (723 ln, NO test), `planner.py`, `synth.py`,
  `querygraph.py` (993 ln, NO test), `council.py`, `debate.py`, `gate.py`.
- `caos/server/run_executor.py`, `caos/server/database.py`, `caos/server/nlquery.py`.
- `caos/server/routes/*.py`, `caos/server/identity.py`, `caos/server/engine/llm_safety.py`.

## Domain conventions the code is SUPPOSED to follow (the "correct" reference)
- **Loans-only first deploy.** Discount margin (DM) is the canonical spread metric;
  STW/Z-spread/YTW are explicitly out of scope. (Don't flag absence of YTW as a bug.)
- **Net leverage** = net debt / adjusted EBITDA, **lower is stronger**. LTM basis.
- **Interest coverage** = adjusted EBITDA / interest, higher is stronger.
- **EBITDA margin** = adj_ebitda / revenue * 100.
- **Recovery waterfall**: strict absolute priority, senior→junior, in LIST ORDER
  (caller pre-sorts on seniority_rank; the function does NOT re-sort). Each tranche
  recovers `min(claim, remaining)`; full claim reduces remaining (floored at 0).
  `recovery_pct` denominator = that tranche's own claim. Rounding = Python
  `round(x,1)` (banker's/half-even) — NOT Decimal. An unsized/zero/negative senior
  claim sets a STICKY break: that tranche and all juniors → None/None (conservative,
  never over-credit juniors). Flat distressed EV = 5.0x LTM EBITDA, sector-blind
  (a DOCUMENTED `ponytail:` simplification — not a bug; do not flag as one).
- **Altman Z''** (private-firm variant): <1.1 distress, 1.1–2.6 grey, >2.6 safe.
- **Basis discipline**: reported (EDGAR GAAP / issuer-disclosed) is canonical; adjusted
  is a SEPARATE reconciliation. A fixture-sourced CP-1 must NOT enter the cross-issuer
  store as a real run (`provenance="fixture"`).
- **Period labels** are free text (`FY24`, `Q1 2026`, `LTM_Q1_26`). `year()` normalises
  the trailing 2–4 digit year to 4 digits; `latest()` picks the value at the largest year.
- **Safety invariant** (verified pre-prod): NO LLM lane has tools or write access.
  Engine is deterministic; LLM is synthesis-only. A finding that an LLM lane can write
  or call tools would be CRITICAL.

## Seeded leads (VERIFY or REFUTE with a concrete case — do not assume true)
1. `periods.latest()` (periods.py:29-32): `max(vals, key=year)` ties on same-year
   periods; Python `max` returns the FIRST-seen max → a series like
   `{"Q1 2026": 100, "Q3 2026": 120}` returns 100 (stale Q1), not 120 (Q3). Feeds
   distressed-EV (capstructure `_distressed_ev`) and `leverage_plausibility_finding`.
   PROVE with a repro if exploitable; assess real-world input shapes.
2. `metrics._headline_period` (metrics.py:95-98): multiple LTM labels → `ltm[0]`
   (first in iteration), not most-recent. Same class as #1.
3. `leverage_plausibility_finding` (metrics.py:176-202): denominator is
   `latest(adj_ebitda)` but it's compared to `net_leverage_adj_ltm` (LTM). If
   `latest()` returns a non-LTM / stale-year EBITDA, the 5% plausibility band can
   mis-fire (false MATERIAL finding, or miss a real inconsistency).

## Output contract (every critic)
Return STRUCTURED findings only. Per finding:
- `id` (short slug), `lens`, `file` + `line`, `claim` (one specific sentence),
  `severity` (CRITICAL/HIGH/MEDIUM/LOW), `evidence` (the offending code + a CONCRETE
  failing input or reproduction), `speculative` (true if you could NOT substantiate
  with a concrete case).
No vibes. If you cannot cite path+line and a concrete case, mark `speculative: true`.
