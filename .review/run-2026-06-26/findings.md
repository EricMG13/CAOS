# Adversarial Review — CAOS engine (run-2026-06-26)

Critic-vs-advocate review. SCOPE auto-triaged to the financial engine + entry
points. Every ranked finding cites path+line and survived an advocate rebuttal;
PROVEN findings carry a runnable repro under `.review/run-2026-06-26/repro/`.
**No code was changed.**

> Provenance note: the 6-lens *parallel* fan-out hit the session token limit
> mid-run (421k burned across 7 concurrent agents). All lenses were then
> re-run **inline and sequentially** in the main loop with live repros against
> the prod-parity test venv — avoiding the concurrent-agent token burst. The
> review below is complete: domain-correctness, security, error-handling,
> concurrency/data-integrity, testability/coverage, and dead-code/deps.

## Status (post-fix, 2026-06-26)

**#1, #2, #3 FIXED** and regression-tested (full server suite 492 passed / 3 skipped):
- #1 — `covenants.py` incremental amount now binds to the clause (+ billion scaling);
  regression tests in `test_covenants.py`.
- #2 — `periods.py` gained a total `sort_key` ((year, intra-year rank); LTM stub
  above the FY it trails); `latest()` uses it. Tests in `test_periods.py`.
- #3 — `metrics._headline_period` uses the same order; new `test_metrics.py`.

**#4 (nlquery fail-open filter) — FIXED.** `validate_spec` now rejects a metric
filter with a text-only op (`ilike`) or a non-numeric value at the boundary, and
`_passes` fails closed (an unevaluable filter excludes, never admits all). Tests in
`test_nlquery.py`. Coverage: `extract_facts` is tested (`test_nlquery.py`),
`_headline_period` + `leverage_plausibility_finding` now tested (`test_metrics.py`).

**All four ranked findings resolved.** No open items from this review.

## Triaged surface (P0)

Highest-risk surface = the deterministic credit-math core under
`caos/server/engine/` + the public auth / NL-query entry points. The recovery
waterfall (`capstructure.py`) is the actively-modified hot spot but is now pinned
by a 16-case golden contract test — so the domain lens targeted the
**less-defended helpers** it and `metrics.py` depend on, where 22 of 40 engine
modules have no direct test. Security focused on the trust boundaries (auth,
NL→DB, document→LLM); concurrency on the run executor + budget.

## Ground truth (P1) — conventions checked against

Loans-only / DM canonical; net leverage = net debt / adj EBITDA (lower better,
LTM); recovery = strict absolute priority in list order, `round(x,1)` half-even,
unsized-senior sticky break; Altman Z'' double-prime cutoffs <1.1 / 1.1–2.6 / >2.6;
reported vs adjusted basis must not cross-contaminate; **safety invariant: no LLM
lane has tools or write access** (verified — see Rejected).

## Ranked findings (P4)

| # | id | sev | tier | verdict | file:line | claim |
|---|----|-----|------|---------|-----------|-------|
| 1 | covenant-incremental-first-million | MEDIUM | **PROVEN** | ACT | `caos/server/engine/covenants.py:114` | Incremental capacity = the FIRST `$N million` in the chunk; an unrelated dollar figure before the basket is taken instead, then cited `exact=True`/High. |
| 2 | latest-stale-same-year | MEDIUM | **PROVEN** | ACT | `caos/server/engine/periods.py:32` | `latest()` ties on year only; `max` keeps the FIRST-seen → stale EBITDA into distressed-EV and the leverage cross-check. |
| 3 | headline-period-first-ltm | LOW | **PROVEN** | DEFER | `caos/server/engine/metrics.py:97` | `_headline_period` returns `ltm[0]` / first same-year, not the most recent → stale headline for cross-issuer ranking. |
| 4 | nlquery-filter-fails-open | LOW | ARGUED | DEFER | `caos/server/nlquery.py:298` | `_passes` returns True for an unhandled op (`ilike` on a metric) or a non-float value → the metric filter is silently dropped, over-broadening the result. |

## Top findings in detail (P5)

### 1 — Covenant incremental amount grabs the wrong dollar figure · PROVEN · MEDIUM · ACT
`caos/server/engine/covenants.py:114-117` (`derive_covenant_terms`, keyless path)

```python
if incremental is None and "incremental" in low and ("capacity" in low or "incurrence" in low):
    m = _MILLION.search(text)            # FIRST "$N million" ANYWHERE in the chunk
    if m:
        incremental = (float(m.group(1).replace(",", "")), cid, True)   # exact=True
```
The gate only checks the words appear *somewhere*; `_MILLION` (bare
`(\d[\d,]*…)\s*million`) then grabs the first match, untethered from the clause.

**Repro** (`repro/test_covenant_incremental_regex.py` — 1 passed):
*"…paid **$5 million** in arrangement fees. … an incurrence basket of up to
**$250 million**…"* → `incremental_musd == 5.0`, not `250.0`. The wrong figure
flows into the pro-forma net-leverage claim (`covenants.py:208-226`) shown to the
analyst with `exact=True`/"High" confidence — a confidently-cited wrong number.

**Advocate counter (considered, does not save it):** the LLM path is primary when
a key is set, so this bites only the keyless/offline deploy and the
budget-exhausted fallback. *Rebuttal:* keyless deterministic CP-1 is a shipped
mode, and the output is flagged `exact=True`/High with no "may be mis-bound"
signal. Real defect.

**Proposed fix (sketch, NOT applied):** tie the amount to the clause, and pick up
*billion* while there (a "$1.5 billion" incremental is missed entirely today):
```python
_INCR_AMT = re.compile(r"(?:incremental|incurrence)[^.]{0,140}?\$?\s*"
                       r"(\d[\d,]*(?:\.\d+)?)\s*(million|billion)", re.IGNORECASE)
# value *= 1000 when group(2) == "billion"
```
Effort: trivial. Add a `test_covenants.py` case for the preceding-figure trap.

### 2 — `latest()` returns a stale same-year value · PROVEN · MEDIUM · ACT
`caos/server/engine/periods.py:29-32`

```python
return max(vals, key=lambda kv: year(kv[0]))[1] if vals else None
```
`year()` resolves to a **year only**, so `Q1 2026`/`Q3 2026` (or `FY2025`/`LTM_2025`)
tie; Python `max` keeps the **first-seen**.

**Repro** (`repro/test_period_selection.py` — 5 passed):
`latest({"Q1 2026":100,"Q3 2026":120}) == 100.0` (stale Q1);
`latest({"FY2025":500,"LTM_2025":560}) == 500.0` (annual, not the LTM stub).

**Blast radius:** `_distressed_ev` (`capstructure.py:123`) → every CP-3B recovery %;
and `leverage_plausibility_finding` (`metrics.py:188`), which compares
`latest(adj_ebitda)` to the **LTM** leverage — a stale/annual EBITDA there can
spuriously fire or mask the MATERIAL "internally inconsistent leverage" finding.

**Advocate counter (downgrades to MEDIUM, does not reject):** the two
deterministic CP-1 paths never produce a same-year tie — fixtures key
`{FY23,FY24,FY25,LTM_Q1_26}`, EDGAR keys `{FY{y}}` one per year
(`edgar_cp1.py:202`). Reachable only via an **LLM-emitted CP-1** (open schema, #21)
or a future quarterly series. Latent, not HIGH — but a real hole in a shared helper
on the lower-trust path.

**Proposed fix (sketch):** make ordering total — break the year tie on an
intra-year rank (quarter; LTM stub newest in its year — one domain call to
confirm). Add `test_periods.py` (absent; would have caught this in two lines).

### 3 — `_headline_period` picks the first LTM, not the most recent · PROVEN · LOW · DEFER
`caos/server/engine/metrics.py:95-98`. Same root cause as #2 (`ltm[0]` / first-wins
`max`). Repro passing: `_headline_period(["LTM_Q1_2025","LTM_Q3_2025"]) ==
"LTM_Q1_2025"`. Narrower consequence (which period is tagged `headline=True`).
Today's single-LTM inputs don't trip it → DEFER, fix with #2.

### 4 — NL-query metric filter fails open · ARGUED · LOW · DEFER
`caos/server/nlquery.py:298-306`. `_passes` returns `.get(op, True)` and
`except: return True` on a non-float target → an `ilike` op on a numeric metric, or
a non-numeric value, silently **drops** the filter instead of rejecting it, so the
ranking returns more issuers than asked. Reachable only via an odd LLM-emitted
filter shape (the demo translator emits none); `=` on a continuous metric is also a
float-equality footgun. Low reachability → DEFER. Fix: reject unknown ops /
unparseable values in `validate_spec` instead of passing them through.

## Lenses run clean (finding-of-absence — the high-risk paths hold)

- **Recovery waterfall** (`capstructure.py`) — golden-tested (16 cases incl.
  half-even rounding, sticky unsized break, no-mutate). Math verified by hand.
- **Covenant headroom** (`covenants.py:249`) — `cushion = (1 − lev/thr)·100` is the
  correct EBITDA-decline-to-breach; secured-vs-total basis mismatch is explicitly
  flagged and directionally sound (secured ⊆ total ⇒ computed headroom is
  conservative).
- **Altman Z''** (`distress.py`) — coefficients + banding match the double-prime
  spec; denominators guarded.
- **Security** — `auth.py`: constant-time compare, fail-closed on unset code,
  dummy-hash timing equalization (no user enumeration), per-IP + un-spoofable
  global throttle, `token_version` revocation, secure-cookie-except-dev.
  `nlquery.py`: closed Pydantic spec (model never authors SQL), allowlisted
  `getattr`, SQLAlchemy-bound values — not injection-vulnerable. `llm_safety.py`:
  untrusted-wrap + `safe_chunk_id` + boundary schema validation.
- **Error handling** — `runner.py` isolates each module (`_attempt_synth` per-module
  try/except at :285; `gather` collects results, siblings survive a failure);
  `synth.py` has tool-block extraction + `JSONDecodeError` guard + one-shot repair +
  defensive `.get` defaults. `run_executor.py` never strands a run (own session,
  `CancelledError` handled, last-resort guard, isolated vault export).
- **Concurrency** — per-run budget `ContextVar` (task context copy → no cross-run
  bleed; `record()` is await-free → atomic on the loop); Postgres claim via
  `FOR UPDATE SKIP LOCKED` with the SQLite single-process constraint documented.

## Coverage gaps (untested critical paths — each is itself a finding)

1. **`periods.py` — tested, but the same-year-tie case (#2) was uncovered.**
   `test_periods.py` pins `year()` width-normalisation (#10) and `latest()` across
   widths, but not two same-year labels. Now added as a strict `xfail` documenting
   #2 (flips to a failure if someone fixes `latest()` without removing the marker).
   Per its own docstring, `latest()` has **six** `year()`-ordered consumers
   (liquidity, metrics, earnings, peers, capstructure, macro) — #2's blast radius.
2. **`metrics.py` — no test.** `extract_facts`, `leverage_plausibility_finding`,
   `_headline_period` are untested money paths feeding the cross-issuer store.
3. **`covenants.py::derive_covenant_terms` incremental branch** — `test_covenants.py`
   exists but missed the preceding-figure trap (#1).
4. **`runner.py` (723 ln), `querygraph.py` (993 ln) — no direct test.** Largest
   untested surface; fault isolation is covered by `test_runner_fault_isolation`
   but the layer-assembly / DAG paths in `querygraph` are not.
5. **`capstructure.py::synthesize_recovery_preference`** — the waterfall *function*
   is golden-tested; the async wrapper (ranking, `pct_of_structure`, limitations) is
   not.

## Rejected as churn / intended (kept visible)

| id | claim | why rejected |
|----|-------|-------------|
| llm-lane-has-tools | "LLM lanes pass `tools=` → CRITICAL safety-invariant violation (`synth.py:287,304`; `gemini.py`; `llm_client.py`)" | **False positive.** The tools are the *forced structured-output* tool `emit_module_payload` (`tool_choice` forces the model to call it to emit JSON) and the Anthropic `advisor_20260301` *model-consultation* tool (`max_uses:1`). Neither touches DB / filesystem / CAOS code. Invariant **HOLDS**. |
| flat-distress-ev | "5.0x flat distressed EV is sector-blind / too crude" | Documented `ponytail:` simplification (`capstructure.py:14`); intended, known upgrade path. |
| altman-strict-bounds | "Z'' zone strict `>`/`<` drops 2.6 and 1.1 to grey" | Matches the stated cutoffs (`distress.py:14`); immaterial at a boundary. |
| covenant-dead-guard | "`cushion … if thr else 0.0` — `thr` range-guarded 1–12, branch dead" (`covenants.py:249`) | Churn; harmless defensive guard. |
| executor-stale-docstring | "`run_executor.py:4` says executors 'added in later tasks' but both exist" | Churn; stale comment, no behaviour. |

## Recommended actions

1. **Fix #1** (covenant incremental regex) — trivial, PROVEN, bites the keyless
   deploy with a confidently-cited wrong number. Highest value/effort.
2. **Fix #2 + #3 together** (period ordering) — small; add `test_periods.py`.
3. Defer #4; fold into a `validate_spec` hardening pass.
4. Backfill tests for `periods.py` and `metrics.py` (gaps 1–2) — they directly
   enabled #2/#3.
