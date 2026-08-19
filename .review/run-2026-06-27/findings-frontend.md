# CAOS Frontend Adversarial Review — Judge Findings

Flagship deliverable risk dominates this batch: the two highest-ranked items are PROVEN wrong numbers on the committee-facing Credit Snapshot tear-sheet, neither caught by any test. Weighting: wrong committee-facing number > data-loss/race > keyboard/SR blocking > perf > dead code; PROVEN > ARGUED > SPECULATIVE at equal severity.

## Triaged surface

- `caos/frontend/src/lib/reports/builders.ts` — Credit Snapshot builder (cap-structure table + seniority chart): 2 PROVEN financial-display defects.
- `caos/frontend/src/lib/engine/useLatestRun.ts` — shared live-run loader behind Deep-Dive / Model Builder / Pipeline: 1 ARGUED cross-issuer bleed.
- `caos/frontend/src/app/query/page.tsx` — Query concept graph runner: 1 ARGUED out-of-order race.
- `caos/frontend/src/app/reports/page.tsx` — Report Studio restore/persist effects: 1 SPECULATIVE restore-clobber.
- `caos/frontend/src/components/pipeline/views.tsx` — Pipeline lineage rail + Inspector chips: 1 PROVEN keyboard block, 1 ARGUED color-alone.
- `caos/frontend/src/components/deepdive/rails.tsx` — Evidence-Sync rows: 1 claim OVERTURNED.
- `caos/frontend/src/components/command/SectorRV.tsx` — sector RV sort: 1 SPECULATIVE perf.

## Ranked findings

| # | id | sev | tier | verdict | file:line | claim |
|---|----|-----|------|---------|-----------|-------|
| 1 | F2 | HIGH | PROVEN | ACT | builders.ts:129 | Cap-structure renders seeded model debt chain (tdebt 2,575) vs canonical 3,270; anchor never fixes it |
| 2 | F1 | MED | PROVEN | ACT | builders.ts:168 | Sub subtotal row prints total-debt leverage xm(tdebt)=6.67x instead of xm(sub)=0.52x |
| 3 | FE-RACE-01 | MED | ARGUED | ACT | useLatestRun.ts:19 | No reset-to-loading on issuerId change — prior issuer's live run bleeds into new issuer |
| 4 | a11y-lineagepanel | MED | PROVEN | ACT | views.tsx:335 | CP-5B lineage rows are click-only divs — keyboard cannot scope the DAG (WCAG 2.1.1) |
| 5 | FE-RACE-02 | LOW | ARGUED | DEFER | query/page.tsx:73 | run() has no sequence guard — stale graph wins, rail/prompt highlight diverge |
| 6 | a11y-dot-color | LOW | ARGUED | DEFER | views.tsx:303 | Upstream-input chips convey dep run-state by bare colored Dot only |
| 7 | FE-RACE-03 | LOW | SPEC | DEFER | reports/page.tsx:95 | Async anchor re-references reports; restore effect re-fires and can clobber edits |
| 8 | PERF-SORT | LOW | SPEC | REJECT | SectorRV.tsx:80 | useSort memo busted by inline getVal — recomputes every render (not measurable) |

## Top findings in detail

### 1 — F2 (HIGH, PROVEN, ACT): wrong tranche dollars on the Credit Snapshot

**Claim:** The cap-structure table + seniority chart render the seeded cash-flow model's internal debt chain, contradicting the canonical structure used everywhere else.

**Evidence — `builders.ts:129-131`:**
```
const rcf = 55, tlb = Math.round(l1.tlb), ssn = 900, sub = 200;
const secured = rcf + tlb + ssn, tdebt = secured + sub, ...
const ev = Math.round(9.5 * structEbitda), equity = ev - tdebt;
```
`l1.tlb` resolves to TLBQ[8]=1420, `sub`=200 (model.ts qCtx), so `tdebt`=2,575.

**Trace (PROVEN):** `buildReports()` -> `buildModel(1,{},anchor?)` -> `l1 = sumCtx("l1","ltm",q.slice(5,9),q[8],l0)` copies debt fields from `q[8]` (tlb 1420 / sub 200 / rcf 55 / ssn 900). `creditSnapshot` then sets secured=2,375, tdebt=2,575. Rows 163-169 print Sub Notes '32 = 200 (true claim 400), TLB = 1,420 (true 1,850), Total debt = 2,575 (true 3,270 → −$695M). `equity = ev − tdebt` is overstated ~$695M; `%EV`/`Multiple` columns inherit it. The seniority chart (175-182) plots the same wrong tranche $. Canonical 3,270 is in `deal.ts` CAPSTACK and the CP-3B dashboard (`step-outputs.ts:1147-1151`) under the SAME labels. `applyAnchor` (model.ts:190-202) re-bases adj/ndebt/cash but leaves the debt stack seeded (own comment: "Debt stack (tdebt) stays seeded") — so a live run is wrong too.

**Advocate counter:** every steelman fails — anchor doesn't correct it, "it's just mock" is refuted by the canonical sibling surface using the same labels, no timing explains 1,420 vs 1,850, and it renders plausible-but-wrong (worse than a crash for a committee artifact).

**Action / effort:** SMALL — re-base the four debt locals from canonical `deal.ts` CAPSTACK (or thread them through `applyAnchor`) so table + chart + derived equity/%EV/Multiple agree with CP-3B.

### 2 — F1 (MEDIUM, PROVEN, ACT): subordinated row prints total leverage

**Claim:** The "Unsecured / subordinated" subtotal's Multiple shows total-debt leverage, not the sub multiple.

**Evidence — `builders.ts:168`:**
```
{ cells: ["Unsecured / subordinated","","","","","", fm(sub), xm(tdebt), "", ""], b:1, line:1 }
```
`xm = (d)=>(d/structEbitda).toFixed(2)+"x"`. Outstanding cell is `fm(sub)` but Multiple is `xm(tdebt)`.

**Trace (PROVEN):** with seeded values tdebt=2,575, structEbitda=386 → `xm(tdebt)`="6.67x", byte-identical to the Total debt row at line 169 directly beneath. The table's convention (rows 166, 169, 172) is Multiple = that row's own Outstanding / EBITDA; the internally consistent value here is `xm(sub)`=0.52x. The blank `% EV` cell on 168 (vs populated on sibling subtotals 166/169) corroborates a copy-paste-from-Total slip.

**Advocate counter:** the cumulative-through-seniority defense fails on the table's own convention — senior-secured (166) uses `xm(secured)` where `secured` IS its Outstanding; the column is row-Outstanding/EBITDA, not standalone-tranche.

**Action / effort:** TRIVIAL — one token: `xm(tdebt)` → `xm(sub)` at line 168.

### 3 — FE-RACE-01 (MEDIUM, ARGUED, ACT): cross-issuer bleed in Deep-Dive

**Claim:** On `issuerId` change, `useLatestRun` re-runs its effect but never resets `value` to loading, so the prior issuer's resolved run shows under the new issuer until the fetch resolves.

**Evidence — `useLatestRun.ts:19-42`:** effect depends only on `[issuerId]`; it calls `setValue(empty)`/`setValue(next)` only AFTER the awaited `listRuns(issuerId)` resolves — no synchronous `setValue(initial)` at the top. Deep-Dive has no remount key on `?issuer=` (only key in tree is IssuerChat, `page.tsx:353`).

**Trace:** in-place nav A→B preserves the component instance; during B's `listRuns` round-trip, `useLiveRun(B)` returns A's `{loading:false, runId:'runA', liveOuts:A}`. `deepDiveCaveatKind` returns "live" (caveat.ts:21) → ● LIVE badge + "live engine output" caveat render; center `ModuleView` shows A's CP-1; `ExportToVaultButton runId='runA'` — all under issuer B's chrome.

**Advocate counter:** not unconditional (first-load mounts fresh, safe) and self-heals in one RTT → ARGUED, severity HIGH→MEDIUM. But the authors fixed the identical loading-window bleed for the chat only (`page.tsx:352-353` key + comment), leaving the main analytical surface exposed — corroborating it's a real pattern.

**Action / effort:** SMALL — synchronously reset to `initial` (loading:true) at the top of the `[issuerId]` effect. Fixes all three consumers (useLiveRun / useModelEngine / useLivePipeline) and matches the file's own documented contract.

### 4 — a11y-lineagepanel (MEDIUM, PROVEN, ACT): keyboard-inoperable lineage rail

**Claim:** CP-5B lineage rows are click-only `<div>`s; a keyboard user cannot pick a driver to scope the DAG.

**Evidence — `views.tsx:335-339`:** `<div onClick={() => onPick(d)} className="...cursor-pointer">` with NO `tabIndex`, `role`, or `onKeyDown`. Sibling clickable rows (command PortfolioTable 88-91, EmailIntel 237-240, GraphCanvas 153) all use the shared `onActivate` helper from `@/lib/a11y`, which this file doesn't even import.

**Trace (PROVEN):** focus never lands on the rows (no focusable attr); Enter/Space can't fire `onPick` → `pickDriver` (page.tsx:75-78), so DAG scoping is mouse-only. Rows with `d.evs.length===0` have zero focusable descendants and are entirely Tab-skipped. Nested EvChip buttons call `onOpen`+`stopPropagation`, never `onPick`. axe (0 violations/12 routes) is blind to role-less click-only divs.

**Advocate counter:** all defenses fail — EvChip can't scope, evidence-less rows are fully skipped, clean axe is consistent WITH the defect.

**Action / effort:** TRIVIAL — add `role="button"` / `tabIndex={0}` / `onKeyDown={onActivate(() => onPick(d))}` + focus-ring via the existing helper; guard against double-activation with the nested EvChip buttons (already stopPropagation).

## Coverage gaps

- **Cap-structure numbers have zero test coverage.** `model.test.ts` asserts nothing on the debt stack — both F1 and F2 shipped undetected. No snapshot/golden test pins `builders.ts` output against `deal.ts` CAPSTACK or the CP-3B dashboard.
- **No cross-issuer in-place nav test** for Deep-Dive; `useLatestRun`'s reset-on-issuerId contract (its own doc comment, line 5) is unverified, and the chat-key fix has no regression test.
- **No out-of-order/race test** for `query/page` `run()`; `setGraph`/`setRunning` ordering under slow-then-fast picks is untested.
- **Keyboard-operability untested for clickable divs:** `views.test.tsx:47-52` asserts `onPick` via `fireEvent.click` only. axe CI is structurally blind to role-less divs and color-alone state — manual keyboard + colorblind passes are the only gate.
- **reports/page restore-vs-edit interleaving** has no timed/batched test; the `hydrated`-gated persist ordering under async anchor arrival is unverified.

## Rejected as churn / intended

- **a11y-evidence-sync-no-focus-ring** — OVERTURNED (advocate verdict upheld:false). The Deep-Dive driver row's `onFocus={() => setActive(d.evs[0])}` (rails.tsx:170) publishes its own first evidence id into Evidence Sync, making the row `hot` → `.caos-selected` → `box-shadow: 0 0 0 1px accent` (globals.css:95-97). A visible 1px accent ring IS drawn on keyboard focus for all 5 rows (all have non-empty distinct `evs`); no global `outline:none` reset exists. The critic's repro ("tab onto a row whose evidence isn't active") is self-defeating — focusing fires `setActive`. No WCAG 2.4.7 failure. Residual is a LOW convention nit: it uses the 1px selection box-shadow (also fires on hover) instead of the standard 2px `.focus-ring` `:focus-visible` outline used by `command/views.tsx:93` — fold into the next a11y pass, not a MEDIUM defect.
- **PERF-SECTORRV-SORT-MEMO** — REJECTED as non-actionable churn. `useSort` memo is invalidated every render by inline `getVal` arrows, but the largest dataset is 28 rows, the component is not in the 650ms sim-tick path, and re-renders only fire on click — sub-millisecond, no user-visible cost. Wrap `getVal` in `useCallback` only if the table grows ~2 orders of magnitude.