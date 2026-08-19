# Adversarial Review run-2 — Ground Truth (whole codebase, all lenses)

RULE: **Change nothing under `caos/`.** Repro tests ONLY under
`.review/run-2026-06-27/repro/`. Read-only review.

## Scope
Everything NOT deep-covered in run-1 (.review/run-2026-06-26/): the engine
**analytical/extraction** modules, the **routes/API** layer, **infra**, and the
**frontend**. All lenses.

## Domain conventions (the "correct" reference)
See `.review/run-2026-06-26/GROUND_TRUTH.md` (loans-only / DM canonical; net
leverage = net debt / adj EBITDA, lower better, LTM; interest coverage = adj
EBITDA / interest; EBITDA margin = adj_ebitda/revenue·100; recovery = strict
absolute priority, round(x,1) half-even; Altman Z'' double-prime <1.1/1.1–2.6/>2.6;
reported vs adjusted basis must not cross-contaminate; **SAFETY INVARIANT: no LLM
lane has side-effecting tools or write access** — a violation is CRITICAL).
Period order now total via `periods.sort_key` (year, intra-year rank; LTM stub
above the FY it trails).

## ALREADY DONE in run-1 — do NOT re-report these as new findings
**Fixed (committed):** covenant incremental regex (`covenants.py`), periods
same-year tie (`periods.py`), `_headline_period` (`metrics.py`), nlquery
`_passes` fail-open + metric-filter validation (`nlquery.py`).
**Verified CLEAN (don't re-litigate):** recovery waterfall (`capstructure.py`,
golden-tested), covenant headroom math, Altman Z'' (`distress.py`), `auth.py`
(constant-time, fail-closed, no user-enum), `llm_safety.py`, `run_executor.py`
(own-session, CancelledError, SKIP LOCKED), `budget.py` (ContextVar isolation),
`runner.py` fault isolation, `synth.py` repair/defensive-parse. The LLM-lane
`tools=` are forced structured-output + the Anthropic `advisor` consult — NOT a
safety violation.

## User is ACTIVELY EDITING (weight these — live domain math)
`liquidity.py` (interest runway), `macro.py` (rate sensitivity), `capstructure.py`,
and new contract tests `test_interest_runway_contract.py`,
`test_rate_sensitivity_contract.py`, `test_recovery_waterfall_contract.py`.

## Run the suite
```
cd "/Users/ericguei/Claude/Projects/Credit Operating System/caos"
PYTHONPATH=server server/.venv/bin/python -m pytest <path> -q
```
py3.9 venv has pytest_asyncio; clear ANTHROPIC_API_KEY/GEMINI_API_KEY for offline
determinism. Repro a bug: standalone `test_*.py` under
`.review/run-2026-06-27/repro/`, `sys.path.insert(0, ".../caos/server")`, call the
engine fn, assert the WRONG output to PROVE the defect.

## Output contract (every critic)
Per finding: `id`, `file`+`line`, `claim` (one specific sentence), `severity`
(CRITICAL/HIGH/MEDIUM/LOW), `evidence` (offending code + concrete failing
input/repro), `speculative` (true if no concrete case). No vibes; cite path+line
or mark speculative. Skip the documented `ponytail:` simplifications (intended).
