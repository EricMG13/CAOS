# Persona Journey Stress Test — P4 Triage

Dedup applied: one root cause hit by several personas is ONE finding with
several witnesses. F-02 was witnessed by all three personas; it is a single
finding, not three.

Ranking axis, in the prompt's order: (1) wrong number reaching IC >
(2) blocks a primary journey > (3) frequency > (4) effort.

**No finding in this run produces a wrong number that would reach IC.** That
axis came back clean — see I6/I5 in [results.md](results.md). Ranking therefore
falls to axis 2.

## FAULT — crash / 500 / hang / data loss / tenancy leak / silent wrong number

**None confirmed.**

This is the headline result and it is a real one. The environment had every
upstream dead — no EDGAR, no LLM keys, no ClamAV, no OCR — which is precisely
the condition under which a platform is most tempted to fabricate. CAOS did not.
It badged fabricated figures **FABRICATED**, declared *"scan verdict
unavailable"* rather than asserting a clean scan, stamped `model_id: "fixture"`,
and let the CP-5 gate restrict the run. A weaker product would have shown a
confident 5.68× leverage with no qualifier; this one refused.

## WORKFLOW LOGIC — weighted HIGHEST for the analyst persona

### F-01 · Directory upload action is a dead end for all 346 demo issuers — **HIGH**

Blocks: **p1 analyst** (primary persona, primary path), also p3.

The Directory renders a per-row control `aria-label="Upload documents for
<Issuer>"` on every one of its 346 demo rows. Clicking it routes to
`/upload?context=…&issuer=<TICKER>`. The wizard then reports **"Select issuer ·
0 registered"**, never names the issuer just clicked, and offers only "+ ADD NEW
ISSUER". The `issuer` query parameter is carried and **silently dropped**.

This is the prompt's named pattern three times over: an action live before its
precondition; a step demanding data the previous step never offered; a dead end.
It sits at step 1→2 of the golden path — the analyst's *first* action in the
product — and is reachable from 346 rows.

Cost to the analyst: the entry point that looks like the way in is not one. The
only recovery is to re-type, by hand, the issuer whose name they just clicked.

Reproduced on a clean p3 stack with a different issuer (`BCULC`), fresh DB.

### F-03 · Loading placeholders persisted as durable analysis-context names — **MEDIUM**

Blocks: p1 analyst (workspace hygiene).

`src/app/deepdive/page.tsx:201-202`:

```js
const dealLabel = isReference ? DEAL.deal : missingIssuer ? "Issuer selection required"
  : (issuerMeta?.name ?? (issuerErr ? "Issuer unavailable" : "Loading issuer…"));
const analysis = useAnalysisContext({ name: `${dealLabel} credit view` });
```

The context is created at mount with whatever `dealLabel` currently holds, so
transient states become permanent names. Observed in the p1 database:
**"Loading issuer… credit view"** and **"Issuer selection required credit
view"**. `"Issuer unavailable credit view"` is reachable by the same path.

Why this matters beyond cosmetics: the analysis context is the carrier that
makes findings and insight versions follow the analyst across Deep-Dive →
Reports → Command (FEAT-005). A governed workspace whose context list accrues
entries named after a loading spinner degrades the one artifact meant to hold
working state together.

## BUG — recoverable: mislabeled state, broken link, stale cache, export mismatch, a11y

### F-02 · Every route shares one browser-tab title — **MEDIUM**

Witnessed by all three personas, 16/16 route loads.

`routeTitleForPath()` (`src/lib/nav.ts:115`) resolves correct per-route titles,
but its only consumer is an `sr-only` `<h1>` (`RouteHeading.tsx:47`). The real
`document.title` is hardcoded in `src/app/layout.tsx:19` and never updated, so
all 18 destinations render **"Credit Agent OS (CAOS)"**.

`nav.ts:70-78` states the metadata exists so "navigation and **document titles**
cannot drift into competing maps" — the implementation does not meet its own
documented intent.

Weighted up, not down, for this product: CLAUDE.md defines the user's work as
"dense, multi-window". An analyst with Deep-Dive, Model Builder and Report
Studio open sees three identical tabs.

### F-04 · Flag-gated freshness endpoints called unconditionally — **LOW–MEDIUM**

`src/lib/api.ts:468-472` calls `/api/issuers/{id}/freshness`,
`/api/runs/{id}/freshness` and `/api/analysis/contexts/{id}/freshness` on every
issuer-profile load. `caos_lineage_v2_enabled` defaults **False**
(`config.py:80`), so all three 404 — 8 per profile load in the observed trace.

The backend is **correct**: the 404 is deliberate, so identifiers stay
non-enumerable whether the feature is on or off (`routes/runs.py:510`). The
defect is on the client: it does not gate the call on the feature, and the UI
collapses "feature disabled" and "genuinely unknown freshness" into one
undifferentiated **UNKNOWN**. For the PM/CIO persona, whose entire job on
Command Center is "what changed", that conflation is the wrong default.

### F-06 · Committed `qa2-backend` launch profile cannot boot — **LOW** (DX)

`.claude/launch.json`'s `qa2-backend` sets `SESSION_SECRET='qa-fixed-secret-do-
not-change'` together with `ENVIRONMENT=development`. `require_sane_environment`
(`caos/server/config.py:392`) refuses that pair outright:

> ENVIRONMENT=development but a production secret (EDGE_PROXY_SECRET /
> SESSION_SECRET) is set — refusing to boot with the dev identity fallback and
> public dev defaults active.

The guard is right; the committed profile is wrong. Booted verbatim on a spare
port to confirm. Anyone selecting that profile gets a hard startup failure.

## Not charged

**F-05** (`/monitor` ~14 s first render vs ~7–8 s peers, both p2 and p3) is left
**PLAUSIBLE**. Measured only against a cold Turbopack dev server with
`turbopackFileSystemCacheForDev: false`; a production build was not measured, so
the dev-compile cost is not separated from any product cost. Recorded so it is
not silently dropped — not asserted as a defect.

## Coverage of the 15 nav destinations

Swept across personas: `/issuers`, `/upload`, `/pipeline`, `/deepdive`,
`/model`, `/reports`, `/command`, `/portfolios`, `/decisions`, `/monitor`
(10/15), plus `/settings` and the issuer-profile route. The a11y matrix covered
all 18 routes including the five not walked in character.

**Not walked by any persona in character: `/research`, `/query`, `/sector`,
`/sector-rv`, `/sponsors`** — the Analyze group. Per the contract, uncovered
surface is reported, not hidden. They are outside all three
`ROLE_PRIORITY_HREFS` paths, so covering them needs either a fourth persona or
an explicit extension of p1's path.

## Honest summary

The run found **5 confirmed defects and 0 faults**. Five further candidates were
withdrawn under verification — including two I would have reported as real on a
first pass (the "346 sample issuers" mock count and the portfolio-creation
referral), both of which turned out to be correctly labelled and correctly
wired.

The most valuable single result is negative: under total upstream failure, CAOS
told the truth on every surface examined. The defects that remain are entry-point
and workspace-hygiene problems, not integrity problems.
