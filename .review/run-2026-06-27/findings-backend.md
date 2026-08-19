# CAOS Backend Adversarial Review — Findings

Run: `.review/run-2026-06-27/` · 12 findings triaged · 8 ACT, 4 DEFER, 0 rejected

> Modules under active edit this session: **`liquidity.py`** and **`macro.py`** (both have uncommitted working-tree changes). Finding **#1 lands directly in `liquidity.py`** — fix it in the same pass you are already editing it. Finding #8 (CP-2F KeyError) sits on `macro.py`'s output contract.

## Triaged surface

| lens | findings | upheld | ACT | DEFER |
|---|---|---|---|---|
| domain-analytical | 3 | 3 | 3 | 0 |
| domain-extraction | 3 | 3 | 2 | 1 |
| orchestration-errors | 3 | 3 | 0 | 3 |
| routes-security-api | 2 | 2 | 1 | 1 |
| infra/deadcode/docs | 2 | 2 | 1 | 1 |

No dedupe merges: every finding has a distinct root cause and file:line. Three findings share a single *pattern* (period-ordering via `year()` instead of `sort_key` — #2, #3; and EDGAR cross-leg freshness — #4, #5) but are kept separate because they are independent callsites with independent fixes and blast radii. See dedup notes.

## Ranked findings

| # | id | sev | tier | verdict | file:line | claim |
|---|---|---|---|---|---|---|
| 1 | liq-maturity-wall-summed-as-liquidity | MED | PROVEN | ACT | liquidity.py:124 | Debt maturity wall summed into disclosed liquidity, inflating headline figure + interest runway |
| 2 | edgar-netdebt-crossyear-contamination | HIGH | PROVEN | ACT | edgar_cp1.py:217 | Net debt mixes 3 independently-dated XBRL legs; freshness gate checks only LT-debt leg |
| 3 | edgar-stale-cash-no-freshness-gate | MED | PROVEN | ACT | edgar_cp1.py:218 | Cash leg has no freshness gate; stale cash understates leverage (risk-looks-safe direction) |
| 4 | earnings-yoy-uses-year-not-sortkey | MED | PROVEN | ACT | earnings.py:41 | Same-year FY/LTM tie on `year()` → set-hash order → spurious YoY decline + false signal |
| 5 | peers-margin-period-uses-year-not-sortkey | MED | PROVEN | ACT | peers.py:52 | `max(key=year)` picks stale closed-FY margin over live LTM, skewing peer percentile/outlier flag |
| 6 | identity-cookie-sig-typeerror-500 | LOW | PROVEN | ACT | identity.py:88 | `hmac.compare_digest` on str → TypeError 500 on non-ASCII cookie sig byte |
| 7 | run-executor-stale-docstring | LOW | ARGUED | ACT | run_executor.py:5 | Docstring says executors "added in later tasks" but both are implemented + wired |
| 8 | debate-cp2f-rate-shock-keyerror | LOW | SPEC | DEFER | debate.py:179 | `worst['rate_shock_bps']` bracket lookup with no default; only fires on malformed CP-2F |
| 9 | planner-cycle-silent-pass | LOW | PROVEN | DEFER | planner.py:244 | Registry cycle routed Full Run in dep-violating order; comment claims it never executes (false) |
| 10 | planner-dangling-dep-unflagged | LOW | PROVEN | DEFER | planner.py:191 | Dangling depends_on id → optimistic Full Run; runtime gate fail-safes by blocking |
| 11 | reported-cp1-leverage-pattern-matches-covenant | LOW | SPEC | DEFER | reported_cp1.py:45 | Broad pattern could match covenant max as actual leverage; no captured real case |
| 12 | edgar-fetch-exhibit-redirect-ssrf | LOW | SPEC | DEFER | edgar.py:250 | urlopen follows redirects unvalidated; requires open redirect on sec.gov (none found) |

## Top findings in detail

### 1 — Maturity wall summed as available liquidity (PROVEN, ACT, trivial) — **file under active edit**
**File:** `caos/server/engine/liquidity.py:124`
**Claim:** `synthesize_liquidity` sums every quantified source — including the `('Maturity wall', …)` scan row — into `disclosed_liquidity_musd`, treating a debt obligation (a USE of liquidity) as a SOURCE.
**Evidence:** line 123-124 `quantified = [f for f in found if isinstance(f["amount_musd"],(int,float))]; total = round(sum(...),1)` has no source-type filter; `total` is emitted as `disclosed_liquidity_musd` (line 137) and fed to `_interest_runway_months` (line 125). The helper's own contract (line 60) defines that arg as "undrawn revolver + cash on hand" — explicitly excluding maturities.
**Repro (verified):** cash $300M + RCF $200M + "$800M of debt matures in 2027" → `disclosed_liquidity_musd=1300.0` (should be 500) and `months_liquidity_covers_interest=156.0` (should be 60.0). Fires on ordinary 10-K phrasing — `_QUERY` actively retrieves on "maturity".
**Advocate counter (rejected):** "Module is a documented sources register that lists the maturity wall." Fails — the bug is not the `sources` list, it's summing the maturity row into a field literally named `disclosed_liquidity` and feeding it to the runway calc, contradicting the helper's own invariant.
**Action:** Filter the `Maturity wall` source out of the `quantified` sum; report maturities as a separate figure. Contract test `test_interest_runway_contract.py` tests the helper in isolation and won't break. **Effort: trivial.** Do it in this session — you already have the file open.

### 2 — EDGAR net-debt cross-year leg contamination (PROVEN, ACT, small) — **highest severity**
**File:** `caos/server/engine/edgar_cp1.py:217`
**Claim:** `total_debt = ltd_at[1] + dcur_at[1]` and `net_debt = total_debt - cash_at[1]` draw from three independent `_recent_instant()` calls that can resolve to different years, but `debt_fresh` (line 222) gates only `ltd_at[0]`. Verified in code: `dcur_at[0]` and `cash_at[0]` are never freshness-checked when `ltd_at` exists.
**Repro (verified):** fresh-2025 LT debt 1000m + stale-2021 current debt 5000m + stale-2021 cash 50m → `net_leverage_adj_ltm=18.03` labelled "at FY2025" (true ~3.0x). The 18x is driven entirely by 4-year-stale legs while `debt_fresh` passes.
**Advocate counter (rejected):** "Legs normally share a period." Fails on the module's own raison d'être — it exists to handle filers that switch/drop concepts (Viasat comment, lines 209-210). The Altman path 30 lines below already does it right (`bs_stale = any(y < ly-1 …)`).
**Blast radius:** CP-1 is the canonical reported foundation feeding CP-1B/1C/2/3/4 + the committee-facing C-EDG-LEV claim and the vaulted facts-text chunk. Wrong direction for a stale current-debt leg.
**Action:** Extend `debt_fresh` to also require `dcur_at` and `cash_at` (when present) ≥ ly-1, mirroring the `bs_stale` pattern at line 293; add a limitation flag. **Effort: small.** Leaves current leverage tests green.

### 3 — EDGAR stale-cash leg has no freshness gate (PROVEN, ACT, small)
**File:** `caos/server/engine/edgar_cp1.py:218`
**Claim:** The cash leg subtracted to form net debt has no freshness check; a discontinued cash tag understates net leverage with no limitation flag.
**Repro (verified):** fresh-2025 LT debt 1000m − stale-2021 cash 900m → `net_debt_ltm=100.0`, `net_leverage_adj=0.2x`, only the generic GAAP-proxy flag (no staleness flag). True ~2.0x — a ~10x understatement in the risk-looks-safe direction.
**Advocate counter (rejected):** "Needs cash dropped under BOTH cash concepts." Narrows frequency only. The cash leg is the lone balance-sheet input on the leverage path with no gate, contradicting the author's systematic sibling gates (`debt_fresh`, `int_fresh` #25, `bs_stale` #17), and the error direction is the dangerous one.
**Action:** Add a `cash_fresh` check on `cash_at[0]` mirroring `debt_fresh`; drop the stale cash leg or append a cash-staleness flag. **Effort: small.** Sub-issue of #2 — fix both in one pass on `edgar_cp1.py`.

### 4 — Earnings YoY uses year() not sort_key (PROVEN, ACT, trivial)
**File:** `caos/server/engine/earnings.py:41`
**Claim:** `periods = sorted(set(rev)|set(eb), key=year)` ties same-year FY/LTM labels and falls into set-hash order, placing the stale closed period after the live one → spurious YoY decline.
**Repro (verified, 1 passed):** rev {FY2024:1000, FY2025:1100, LTM_2025:1150} → order `['FY2024','LTM_2025','FY2025']`, `revenue_growth_pct=-4.3` (true +4.5%) and a false "Revenue declined" monitoring signal. `sort_key`-correct order gives LTM as latest.
**Advocate counter (rejected):** "Same-year FY+LTM never occurs." Fails — `periods.py` ships `sort_key`/`_intra_year_rank` *specifically* to break this tie; run-1 migrated `periods.latest()` and `metrics._headline_period`, earnings.py:41 was simply missed. Latent flake (non-deterministic across interpreter runs).
**Action:** `key=year` → `key=sort_key`. **Effort: trivial.** Verified to preserve ordering for every existing test label set.

### 5 — Peers margin period uses year() not sort_key (PROVEN, ACT, trivial)
**File:** `caos/server/engine/peers.py:52`
**Claim:** `max(common, key=year)` picks the stale closed-FY margin over the live LTM on a same-year tie, skewing the peer percentile and bottom-quartile outlier flag.
**Repro (verified, 2 passed against real `_own_values`):** returns `ebitda_margin=18.1` (stale FY2025) instead of 20.9 (live LTM_2025) — a 2.8pp swing that can flip the outlier flag.
**Advocate counter (rejected):** Refuted three ways; decisively, `metrics._headline_period` already seeds the peer store via `sort_key`, so the issuer's own value (year) and the peer-store values (sort_key) are selected *inconsistently* and then compared. The fix makes peers AGREE with metrics.
**Action:** import `sort_key`, change line 52 to `max(common, key=sort_key)` (ideally prefer LTM like `_headline_period`). **Effort: trivial.** No test pins current behavior.

### 6 — Cookie-sig TypeError → unauthenticated-ish 500 (PROVEN, ACT, trivial)
**File:** `caos/server/identity.py:88`
**Claim:** `hmac.compare_digest(sig, _sig(raw, secret))` compares two str outside the try; a non-ASCII byte in the cookie sig (Starlette decodes latin-1) raises TypeError → `log_unhandled` → HTTP 500.
**Repro (verified, 2 passed):** `caos_analyst=abc.def\xff` → "comparing strings with non-ASCII characters is not supported".
**Advocate counter (severity reduced):** In the proxied prod posture (oauth2-proxy, no published port) it's self-inflicted by an SSO'd user on their own malformed cookie — not a third-party bypass. No auth bypass, no data exposure. Hence LOW, not MEDIUM. But the defect is real: siblings at identity.py:145-147 and main.py:201-203 deliberately `.encode('utf-8','ignore')` to dodge exactly this; line 88 omits it.
**Action:** encode both operands to bytes, mirroring 145-147. **Effort: trivial.** 7/7 identity tests pass; base64 sigs are ASCII.

### 7 — run_executor stale docstring (ARGUED, ACT, trivial)
**File:** `caos/server/run_executor.py:5`
**Claim:** Docstring says executors "are added in later tasks" and "`get_executor()` will pick one by DB dialect" (future tense), but `InProcessExecutor` (line 98), `QueueWorker` (line 143), and `get_executor()` (line 265) are all implemented and wired at main.py:91.
**Advocate counter (rejected):** "will pick" only parses as pending; git blame shows the work shipped ~12 days prior; not a `ponytail:` simplification the ground truth tells reviewers to skip.
**Action:** Update the docstring to present tense. **Effort: trivial.** Documentation only.

## Coverage gaps (ranked by criticality)

1. **EDGAR per-leg net-debt freshness** — `test_edgar_cp1.py:153-184` exercises the LT-debt concept switch only with all legs at the same fresh year; no test covers a fresh LT-debt leg with a stale current-debt OR stale cash leg (#2, #3). Add a multi-year-leg fixture asserting either a staleness flag or suppressed leverage. **Highest criticality** — guards a HIGH committee-facing figure.
2. **Same-year FY/LTM period ordering** — no test exercises the `year()` tie in `earnings.py`/`peers.py` (#4, #5). Existing earnings tests use only distinct-year/quarter labels. Add a FY{y}+LTM_{y} fixture asserting LTM is latest in both `compute_deltas` and `_own_values`.
3. **Liquidity source-type exclusion** — no test asserts that a maturity-wall row is excluded from `disclosed_liquidity_musd` / runway (#1). Add the cash+RCF+maturity fixture from the repro.
4. **Identity cookie hardening** — no test sends a non-ASCII cookie sig byte (#6). Add a unit asserting `read_session_token` returns None (not raises) on a high-byte sig.
5. **Planner registry acyclicity / dangling-dep guard** — no acyclicity self-check on the module registry analogous to `querygraph.py:949-954` (#9, #10). A startup/CI assertion that `all_specs()` is acyclic and has no dangling `depends_on` would convert the latent gaps into loud failures.

## Rejected as churn / intended

None rejected. All 12 findings were upheld by the advocate. Four are DEFER (act later, not churn):

- **debate-cp2f-rate-shock-keyerror** (#8) — SPECULATIVE; real CP-2F (`macro.py:96-97`) always emits `rate_shock_bps` with coverage, so only a malformed/tampered payload triggers it. Cheap `.get` defensive fix if `macro.py` output contract ever loosens — relevant since macro.py is under edit.
- **planner-cycle-silent-pass** (#9) — PROVEN but zero production impact (registry proven acyclic); the only real defect is the false comment. Defer to a registry acyclicity guard.
- **planner-dangling-dep-unflagged** (#10) — PROVEN but runtime input-gate (runner.py:263-268) fail-safes by blocking; only an over-optimistic route-plan artifact. Defer with #9.
- **reported-cp1-leverage-pattern** (#11) / **edgar-fetch-exhibit-redirect-ssrf** (#12) — SPECULATIVE, no captured real trigger. Defer pending a concrete case.