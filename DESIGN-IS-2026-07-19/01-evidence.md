# CAOS all-surface frontend evidence

## Method and provenance

- Audited all 18 routed entries under `caos/frontend/src/app`, the shared
  navigation/shell, PersonaWorkbench composition, global Ask, evidence viewers,
  responsive contracts, and Report Studio paper output.
- Current rendered evidence was captured on 2026-07-19 at 1440×900 and 390×844
  with the repository Playwright/axe harness. The matrices are in
  `/tmp/caos-a11y-desktop/` and `/tmp/caos-a11y-narrow/` for this run.
- Current source was read across every route and shared component. Captures dated
  2026-07-13 were used only as regression history, never as current proof.
- Impeccable Assessment A and Assessment B were isolated. Assessment B ran the
  deterministic detector before its report was read; it returned `[]` over all
  69 scannable route-markup files.
- GitNexus semantic discovery was attempted, but the repository FTS indexes were
  unavailable. Deterministic source enumeration and rendered inspection were the
  fallback. No application code was changed by this audit.

## Structural evidence

The AST inventory found **560 interactive declaration sites** across production
TSX: 458 route-owned and 102 shared. Counts are declaration sites rather than
runtime instances; mapped rows can render more controls.

| Surface | Interactive sites | Surface | Interactive sites |
|---|---:|---|---:|
| `/` | 0 | `/command` | 48 |
| `/decisions` | 46 | `/deepdive` | 31 |
| `/issuers` | 19 | `/issuers/profile` | 28 |
| `/model` | 79 | `/monitor` | 19 |
| `/pipeline` | 17 | `/portfolios` | 17 |
| `/query` | 29 | `/reports` | 31 |
| `/research` | 12 | `/sector` | 15 |
| `/sector-rv` | 20 | `/settings` | 18 |
| `/sponsors` | 7 | `/upload` | 22 |
| shared chrome/primitives | 102 | **Total** | **560** |

- Maximum lexical JSX depth is **14** in Settings, beginning at
  `caos/frontend/src/app/settings/page.tsx:519` and reaching the configuration
  value branch at `:763-796`.
- **19 excess same-purpose affordances** were present in the default desktop
  structure: 11 repeated Deep-Dive evidence openers
  (`components/deepdive/OutputRegister.tsx:212-367`,
  `components/deepdive/tabs.tsx:112-487`), six duplicate ReportDoc/lineage source
  openers (`components/reports/ReportDoc.tsx:273-300`,
  `components/reports/panels.tsx:114-128`), duplicate “Add agenda item”
  (`components/decisions/ICBookWorkbench.tsx:641,1094-1099`), and duplicate
  Research run actions (`app/research/page.tsx:224-240,426-432,535-546`).
- Production UI had **0 detected dead props and 0 unused imports**. Lint was
  clean; the five unused imports reported by strict TypeScript were test-only.
- The shared frame is genuinely reused: `EnterprisePage` has 21 incoming route
  callers and defines the identity/status/action/context/utility/finalization
  anatomy (`components/shared/EnterprisePage.tsx:14-65`).

## Visual evidence

### System measurements

- Workspace spacing tokens are **[4, 8, 12, 16, 24, 32] px**
  (`app/globals.css:47-52`), with local 6/10/14 px exceptions.
- Workspace type scale is **[10, 11, 12, 13, 16, 18, 22, 30] px**
  (`tailwind.config.js:43-59`). The display alias appears once, hero three times,
  and the screen identity itself is commonly 12 px
  (`components/shared/ShellIdentity.tsx:47-50`).
- Uppercase tracked micro-label grammar appears **373** times across app and
  components. Panel headings are 11 px (`components/shared/Panel.tsx:39-55`),
  while workbench headings are 13 px (`components/shared/WorkbenchToolbar.tsx:48-54`).
- Report output adds many type rungs. The on-screen model appendix is only
  **5.3–7 px** (`app/globals.css:651-674`); Report paper labels/body/tables are
  generally 8–9.5 px (`:626-649`).
- Comment-stripped `globals.css` references **64 literal colors**. The perceived
  workspace remains restrained, but paper/alpha/special-case values are locally
  hard-coded rather than fully token-bound.

### Contrast

| Token/pair | Ratio | Result |
|---|---:|---|
| text on elevated | 13.01:1 | Pass |
| muted on elevated | 6.36:1 | Pass |
| accent on elevated | 6.20:1 | Pass |
| warning on elevated | 7.91:1 | Pass |
| success on elevated | 7.08:1 | Pass |
| critical on elevated | **4.29:1** | **Fail for normal text** |
| workspace ink on accent button | 7.59:1 | Pass |
| paper text family on paper | 4.76:1–16.49:1 | Pass |
| paper watermark on paper | 4.31:1 | Pass only because specified at 26 px/700 |

### Current rendered hierarchy and alignment

- The dark terminal, tabular numerics, hairline grouping, and signal-only color
  are coherent at desktop. Model Builder and the light Report paper are the
  strongest goal-aligned surfaces
  (`/tmp/caos-a11y-desktop/model-1440x900.png`,
  `/tmp/caos-a11y-desktop/reports-1440x900.png`).
- Screen identity is visually subordinate to utility/status text. Route names
  are mostly 12 px, and narrow identity is explicitly allowed to truncate
  (`components/shared/SubHeader.tsx:164-167`). Current 390 px captures show
  truncated Deep-Dive, Model, Reports, Monitor, Pipeline, Research, Sponsors,
  and Portfolio identities.
- Empty routes frequently devote most of the canvas to an unpopulated panel:
  Issuers, Research, Sector, RV, Sponsors, IC Book, Portfolio, and parts of
  Command all show this at 1440×900. The empty-state copy is good, but the
  product's “dense, organized terminal” promise becomes a sparse frame.
- Portfolio Lab is visibly off-system: a 9 px “SIZING WORKBENCH” eyebrow and
  decorative 2 px side stripes (`app/globals.css:1302,1365,1368`). Its desktop
  filter row also hides part of Sort behind the adjacent View panel at 1440 px
  (`/tmp/caos-a11y-desktop/portfolios-1440x900.png`).
- Narrow mode often preserves DOM capability by lateral scrolling. Report opens
  on a clipped fixed-width paper, Pipeline on a partially visible DAG, Model on
  a dense spreadsheet, Issuers on a clipped table, and Profile/Sector on clipped
  tab bands (`/tmp/caos-a11y-narrow/*-390x844.png`). The harness found no page
  overflow because those regions own scroll; task usability still degrades.

### State inventory

| State | Evidence |
|---|---|
| empty | Shared `SurfaceState` and route-specific observed-empty worklists |
| loading | Shared polite `role=status` and skeletons |
| error | Shared alert semantics; frequent retry/escalation actions |
| success | Route-specific ready/ratified/published/affirmed only; no shared success kind |
| focus | Global visible `:focus-visible` treatment (`app/globals.css:175-186`) |
| disabled | Native disabled plus focusable `ActionReason` with reason text |
| additional | checking, not-run, unavailable, stale, partial, offline (`components/shared/SurfaceState.tsx:6-40`) |

## Copy and honesty evidence

No marketing superlatives, confirmshaming, fake scarcity, hidden cost, or forced
continuity were found. Copy is generally terse, technical, and unusually honest
about provenance. The following label/behavior or trust mismatches are verified:

- Role copy promises PM “posture / what changed first” and QA
  “governance / gates first” (`components/shared/RoleViewSwitch.tsx:11-15`). The
  configuration defines `dominantRepresentation`, `summaryDensity`, and
  `tableColumnPreset` (`lib/persona-composition.ts:55-95`), but the renderer only
  emits them as data attributes (`components/shared/PersonaWorkbench.tsx:201-206`).
  Only context/inspector open defaults materially change (`:51-55`).
- Report Studio uses “Submit to IC” and “Open IC decision” for the same
  drawer-opening behavior; neither phrase at that point performs finalization
  (`app/reports/page.tsx:977-995,1056`).
- Upload's persistent **“MNPI · restricted handling enforced”** badge is an
  unqualified end-to-end compliance assurance that this frontend-only review
  cannot substantiate (`app/upload/page.tsx:13,25`). Its completed panel can
  also say **“Intake complete · CP-0 ready”** when `okCount` is zero and every
  file failed (`components/upload/UploadWizard.tsx:423-426`;
  `components/upload/steps.tsx:450-461,571-574`).
- Issuer creation says it “opens its module route,” but success calls the profile
  overlay rather than route navigation (`app/issuers/page.tsx:204-209,669-675,728-730`).
- Portfolio's primary **“Run portfolio stress”** only opens the preview; the
  mutation is a later **“Confirm and persist”** action
  (`components/portfolio/PortfolioLabWorkbench.tsx:679-705,713-722`). RV's
  **“Monitor threshold”** only pins a finding rather than configuring a monitor
  threshold (`components/rv/RVScreenerWorkbench.tsx:206-217,283,405-411`).
- The mobile Monitor header retains a batch **“Acknowledge selected”** action,
  while `PhoneTriage` has no matching selection event and only exposes per-alert
  Ack/Assign/Resolve actions (`app/monitor/page.tsx:204-212,245-248`;
  `components/monitor/AlertInbox.tsx:419-440`;
  `components/monitor/PhoneTriage.tsx:176-209`).
- Notifications render every arbitrary `href` as **“Open execution graph,”** so
  label and target can diverge unless an undocumented backend invariant exists
  (`components/shared/Notifications.tsx:19-50,138-144`).
- Query, Sector, and RV display **“COMPOSITION ONLY · PERMISSIONS UNCHANGED”** as
  product chrome (`components/query/QueryInvestigationWorkbench.tsx:914-929`,
  `components/sector/SectorReviewDossier.tsx:424-445`,
  `components/rv/RVScreenerWorkbench.tsx:442-451`). It is implementation-policy
  language, not a task/status label.
- Settings exposes runtime/model routing implementation and environment-key
  language—“runtime model”, “LLM lanes”, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
  `OPENROUTER_API_KEY`—inside the analyst workspace
  (`app/settings/page.tsx:520-658`). This is operational configuration jargon,
  not credit-workflow language.
- Monitor labels the surface LIVE while rendering a seeded CP-MON-H demo replay
  inside the same Alerts dataset. The copy discloses the replay, but the visual
  co-location still asks users to continually separate real and illustrative
  events (`app/monitor/page.tsx:199-207,228-248,263-268`).
- The Monitor Email Intelligence lane is populated from static `EMAIL_TILES`,
  `EMAIL_TOTAL`, and `EMAILS` but is presented as “CP-MON intake”; its populated
  caption says “sample,” not seeded/demo/illustrative
  (`components/command/MonitorStreams.tsx:8-9,88-104,157-158`;
  `app/monitor/page.tsx:199-200,245-252,418`).
- Issuer Profile labels metrics “DEMO SEED” and repeats “Source unavailable” when
  no completed run exists, yet still gives large 2.3×/8.5×/$1.9bn values dominant
  visual weight (`app/issuers/profile/ProfileContent.tsx:702-814`). Honest labels
  do not fully neutralize the wrong-read risk.
- Strong truth patterns should be preserved: Deep-Dive explicitly distinguishes
  live/no-run/seeded output (`app/deepdive/page.tsx:540-560`); Report publish is
  gated by live run, Committee Ready state, report, and saved model checkpoint
  (`app/reports/page.tsx:750-768`); Model identifies restore/save conflicts and
  unsaved state (`app/model/page.tsx:821-856`).

## Weight and attention evidence

Primary view `/command`, current production static export, modern browser:

| Measure | Value | Method |
|---|---:|---|
| initial JS | **893,084 B raw / 271,700 B gzip-est.** | 17 modern JS resources referenced by exported HTML |
| startup requests | **19** | 1 HTML + 1 CSS + 17 JS; excludes runtime API/dynamic imports |
| TTI | **≈510 ms estimated** | 23 ms observed TTFB + 10 Mbps transfer + stated parse/hydration allowance |
| idle animations | **0** | initial auth/loading DOM; live pulses are conditional and reduced-motion gated |
| initial notifications/badges/modals | **0/0/0** | initial state and exported DOM |

Core-route JS ranges from 267,456 B gzip-est. (`/deepdive`) to 304,361 B
(`/model`); `/reports` has the most startup requests at 20. The product passes
the Rams `<500KB`/motion-gated score anchor but is not near the `<100KB` ceiling.

## Accessibility and responsive evidence

- Desktop axe over all 18 route entries: **1 serious violation, 0 scan errors,
  0 harness layout failures**. `/reports` has a
  `scrollable-region-focusable` failure on a `flex-1 min-h-0 overflow-auto`
  panel matching the shared effect-measured `PanelBody`
  (`components/shared/Panel.tsx:5-20,59-84`).
- Phone axe at 390×844: **0 violations, 0 scan errors, 0 harness layout failures**.
- Two skip links and a primary main landmark are present
  (`app/layout.tsx:40-57`); focus rings and reduced-motion fallbacks are global.
- Default focus reaches 20 shared controls before route-specific work: two skip
  links, the CAOS link, 15 workflow destinations, Settings, and role view
  (`components/shared/WorkflowRail.tsx:18-75`, `lib/nav.ts:13-60`). This is
  keyboard-accessible but inefficient for a frequent specialist workflow.
- `/reports`' default primary action uses native `disabled` and leaves the tab
  sequence; `/sector` has no page-level primary action. The other 16 route
  entries expose a keyboard-reachable primary action.
- `RouteHeading` omits Portfolios and Decisions, causing the fallback sr-only h1
  “CAOS”; Portfolio also renders its own visible h1
  (`components/shared/RouteHeading.tsx:9-29`,
  `components/portfolio/PortfolioLabWorkbench.tsx:534`).
- Global narrow CSS raises general controls to 44 px and utility text aliases to
  12 px (`app/globals.css:620-624`), but direct paper-appendix sizes bypass that
  floor.

## Evidence by Rams principle

1. **Innovative:** Evidence-authority decision briefs, role-composed workbenches,
   and the dark-desk/light-paper pairing refresh familiar terminal/editor
   patterns (`EnterprisePage.tsx:14-65`; `DecisionHeader.tsx:135-196`). No
   five-peer novelty study was performed.
2. **Useful:** Sixteen route entries have a reachable primary action and every
   route maps to a named credit workflow; role composition and several narrow
   modes add detours rather than removing the task.
3. **Aesthetic:** The core token system is strong, but the product has more than
   five material exceptions: under-hierarchical route titles, 5.3–7 px appendix,
   Portfolio micro-style/stripes, 64 literals, sparse empty canvases, and clipped
   narrow artifacts.
4. **Understandable:** Decision brief structure is excellent; persona promises,
   Report action semantics, internal composition copy, settings jargon, compact
   navigation, and unclear lateral overflow prevent first-read clarity.
5. **Unobtrusive:** Hairline chrome and supporting drawers usually recede. The
   global rail, 102 shared interactive sites, persistent Ask dock, and crowded
   choice bands remain visible but rarely decorative.
6. **Honest:** Provenance/readiness is a major strength. The persona contract,
   Report verb/behavior mismatch, and co-located live/demo Monitor lane break
   strict 1:1 label-to-behavior mapping.
7. **Long-lasting:** Flat tonal surfaces, standard tables/editors, restrained
   motion, and signal color contain no fashionable gradient/glow/skeuomorph
   markers.
8. **Thorough:** All key state categories exist; phone axe is clean. One serious
   Report focusability defect, critical-on-elevated contrast, and non-unified
   success closure keep the edge treatment from complete.
9. **Environmentally friendly:** 271.7 KB gzip-est. primary JS, no idle motion,
   and reduced-motion support match the rubric's middle tier.
10. **As little design as possible:** 19 excess same-purpose affordances,
    15-destination global navigation, repeated decision/source chrome, and
    multiple five-plus choice bands show removable interaction weight.

## Known gaps

- No 200% current render, coarse-pointer emulation, or full keyboard traversal of
  every post-action dialog/state was run.
- Runtime API calls, dynamic imports, and route-ready TTI were not browser-traced;
  the performance figures state their parser/export boundaries.
- Empty/demo fixtures limit assessment of fully populated tables and long-text
  extremes. Current desktop and phone screenshots are authoritative only for the
  rendered states captured.
- GitNexus FTS was unavailable; source conclusions were cross-checked by exact
  references and render output rather than semantic process search.
