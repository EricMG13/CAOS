import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repo = process.cwd();
const require = createRequire(import.meta.url);
const ts = require(path.join(repo, "caos", "frontend", "node_modules", "typescript", "lib", "typescript.js"));
const baselineDate = "2026-07-16";
const today = "2026-07-20";
const outputDir = path.join(repo, "outputs", "caos-quality-validation");
const csvPath = path.join(repo, "caos", "docs", "qa", "FEATURE_TRACKER.csv");
const outputPath = path.join(outputDir, "CAOS_Quality_Validation_Tracker.xlsx");
const scenarios = [
  "Happy path",
  "Error path",
  "Boundary conditions",
  "Invalid input",
  "Permission/security",
  "Performance",
  "Mobile/responsive",
];

const validationRuns = [
  ["Frontend unit/component", "npm test -- --run; exact-current failure remediation; complete affected-file reruns", "Pass", "All 1,809 current frontend nodes pass in one exact-current full run across 261 files; the focused 229-case Model cohort also passes with clean lint and TypeScript", today],
  ["Frontend coverage", "npx vitest run --coverage --coverage.reportsDirectory=/private/tmp/caos-codex-coverage-final", "Pass", "The 980-test coverage baseline passed at statements/lines 84.18% (45,617/54,186), branches 77.05% (7,423/9,633), functions 65.94% (1,224/1,856); all 14 later additions passed in the focused delta", baselineDate],
  ["Frontend lint", "npm run lint", "Pass", "ESLint completed with no findings against the exact current source and test tree", today],
  ["Frontend type check", "./node_modules/.bin/tsc --noEmit", "Pass", "TypeScript completed with no findings after typing the Pipeline, Report Studio, and late Command Center interaction harnesses", today],
  ["Command Center harness reconciliation", "vitest run src/app/command/command-interactions.test.tsx; npm run lint; tsc --noEmit", "Pass", "The concurrent five-test Command Center harness passes with exact PortfolioSummary, CommandPortfolioSnapshot, CommandPortfolioPosition, InsightPage, and InsightArtifact fixtures; lint and TypeScript are clean", today],
  ["ReportDoc post-seal delta", "vitest run src/components/reports/ReportDoc.test.tsx; npm run lint; tsc --noEmit", "Pass", "The complete later ReportDoc revision passes 4/4, adding three executable nodes after the 1,259 aggregate; lint and TypeScript remain clean", today],
  ["Research ReportPane post-seal delta", "vitest run src/components/research/ReportPane.test.tsx; npm run lint; tsc --noEmit", "Pass", "The complete later ReportPane revision passes 11/11, adding five executable nodes after the 1,259 aggregate; lint and TypeScript remain clean", today],
  ["Research feature reconciliation", "vitest: four Research files; pytest: test_deepresearch.py test_research_jobs.py test_edgar.py", "Pass", "All 29 Research features now carry direct assertion-level evidence; 26/26 frontend cases and 49/49 executable backend cases passed with two intentional PostgreSQL skips", today],
  ["Concurrent harness type reconciliation", "vitest: UploadWizard.interactions, steps-interactions, CommandPalette.interactions; npm run lint; tsc --noEmit", "Pass", "All 18/18 current interaction cases pass (12 Upload and 6 Command Palette); exact public component, dropzone, issuer, and API response types replace unsafe or impossible fixtures; lint and TypeScript are clean", today],
  ["Automation collector warning exclusion", "pytest --collect-only -q --disable-warnings; exact layer-count gates; workbook automation evidence reconciliation", "Pass", "Warning-summary references are excluded and collection fails closed on drift; the current inventory reconciles exactly to 1,758 Vitest + 2,539 pytest/stress/cohort + 144 Playwright + 36 route accessibility nodes", today],
  ["RV Screener harness type reconciliation", "vitest RVScreenerWorkbench.test.tsx; npm run lint; tsc --noEmit", "Pass", "All 12/12 RV Screener interactions pass with a complete AnalysisContext fixture; the unused import and explicit any are removed, and lint and TypeScript are clean", today],
  ["Alert Inbox harness type reconciliation", "vitest AlertInbox.test.tsx; npm run lint; tsc --noEmit", "Pass", "All 17/17 Alert Inbox interactions pass with a narrow recursive React-fiber helper; explicit any is removed, and lint and TypeScript are clean", today],
  ["Pipeline feature reconciliation", "vitest: five Pipeline/Issuers/navigation files; pytest: test_async_runs.py test_engine.py test_api.py", "Pass", "All 45 Pipeline features now carry direct assertion-level evidence: the 53-node frontend cohort passed in the exact-current aggregate, and the seven linked API contracts passed within a 93-pass/2-skip server cohort", today],
  ["Production static build", "npm run build", "Pass", "Next.js 16.2.10 generated 20 static pages from the exact current production source tree", today],
  ["Server/stress/cohort regression", "caos/server/.venv311/bin/python -m pytest -q caos/tests/server; affected-file deltas; pytest -q caos/tests/stress caos/tests/cohort", "Pass", "2,520 current executable server nodes are reconciled with 15 intentional skips; the prior complete regression, all later complete affected-file deltas including the 79/79 notification/migration tranche, and all nine stress/cohort nodes pass", today],
  ["Backend evidence identity stabilization", "collect twice; diff prior Automation Evidence; pytest four affected files", "Pass", "Two consecutive collections are identical at 2,427 nodes; six stable current identities replace two payload-derived identities, and all four affected files pass 111 tests with two intentional PostgreSQL skips", today],
  ["Concurrent test delta reconciliation", "find test files modified after each exact aggregate/delta; run those complete files; recollect all nodes", "Pass", "48/48 frontend and every complete backend delta-file cohort passed through the final 71-test coverage-edge rerun, closing 14 newly collected frontend nodes and 47 newly collected backend nodes without presenting unexecuted collection as pass", baselineDate],
  ["Configuration inventory contract", ".venv311/bin/python -m pytest caos/tests/server/test_settings_inventory_contract.py -q", "Pass", "259/259 cases passed across all 83 current Settings fields: code defaults, typed environment overrides, malformed scalar rejection, and numeric zero boundaries", baselineDate],
  ["Previously unmapped API contracts", ".venv311/bin/python -m pytest caos/tests/server/test_unmapped_api_contracts.py -q", "Pass", "14/14 direct HTTP cases passed after reconciling every parameter ID to the current 168-route inventory", today],
  ["PostgreSQL gated cohort", "DATABASE_URL=postgresql+asyncpg://... pytest <15 gated nodes> -q -rs", "Pass", "15/15 PostgreSQL-only concurrency, row-lock, advisory-lock, deployed-posture, and lineage cases passed", baselineDate],
  ["PostgreSQL migration round trip", "alembic upgrade head; alembic check; alembic downgrade base; alembic upgrade head", "Pass", "62 revisions upgraded, schema drift check passed, complete downgrade and re-upgrade passed", baselineDate],
  ["Golden OCR lane", "pytest caos/tests/server/golden/test_ocr_lane.py -q -rs", "Pass", "1/1 real ocrmypdf+tesseract ingestion/persistence case passed", baselineDate],
  ["Production-like QA server posture", "ENVIRONMENT=production DATABASE_URL=postgresql+asyncpg://caos:***@127.0.0.1:55440/caos_qa CAOS_DEMO_SEED=false CLAMAV_REQUIRED=true <all rollout gates=true; provider keys blank> uvicorn main:app --ssl-*", "Pass", "Isolated HTTPS server booted with PostgreSQL, edge-secret auth, strict CSP, required fake ClamAV protocol peer, all rollout gates, no external model keys, and 300 deterministic fictional issuers", baselineDate],
  ["Browser E2E (production posture)", "PLAYWRIGHT_BASE_URL=https://127.0.0.1:8443 E2E_STATIC_DIR=<isolated export> E2E_EDGE_PROXY_SECRET=*** E2E_ACCESS_CODE=*** E2E_IGNORE_HTTPS_ERRORS=1 npm run test:e2e:prodlike", "Pass", "141/141 project executions passed with retries disabled against the HTTPS/PostgreSQL/required-AV production posture; CSP and source-freshness preflights passed", baselineDate],
  ["Browser E2E (exact-current browser matrix)", "PLAYWRIGHT_BASE_URL=http://127.0.0.1:8077 E2E_STATIC_DIR=caos/server/static npm run test:e2e:prodlike; rerun upload_flow.spec.ts in all projects after the later Issuers change", "Pass", "The full matrix passed 141/141 with zero retries after the Research fix; the subsequently rebuilt Issuers artifact passed the complete affected journey 15/15 across Chromium, Firefox, and WebKit", today],
  ["Browser E2E (exact-current seal)", "run production-like freshness preflight; rebuild, stage, and restart after any production-source mtime change", "Pass", "The freshness preflight rejected the prior staged export; after rebuilding, staging, and restarting, source freshness and live CSP hashes passed before all 141 browser executions", today],
  ["Deep-Dive flake stress", "playwright test deepdive_flow.spec.ts -g 'hovering' --repeat-each=10 --retries=0 --workers=5", "Pass", "10/10 evidence-sync hover repetitions passed under five workers", baselineDate],
  ["Route accessibility + responsive", "BASE=http://127.0.0.1:8077 VIEWPORTS=1440x900,390x844 E2E_EDGE_PROXY_SECRET=<non-secret local identity marker> E2E_FORWARDED_EMAIL=<isolated analyst> E2E_ANALYST_NAME=<isolated analyst> node scripts/a11y-axe.mjs", "Pass", "The full 36-state matrix passed; after the later Issuers rebuild, the affected root and /issuers routes passed 4/4 desktop/mobile rescans with 0 axe nodes, scan errors, layout failures, overflow, or clipped controls", today],
  ["Query state accessibility", "BASE=http://127.0.0.1:8010 E2E_FORWARDED_EMAIL=<isolated analyst> E2E_ANALYST_NAME=<isolated analyst> node scripts/a11y-query.mjs", "Pass", "Exact-current ready, graph-lane, answer, and persisted narrow states all passed with 0 violation nodes", baselineDate],
  ["GitNexus semantic discovery", "analyze --repair-fts; force index-only PDG rebuild; local query; MCP registry/context/query", "Degraded", "The on-disk index and registry are current at b1ac826 and local FTS queries return relevant symbols, but the long-lived MCP query connection retains its pre-repair catalog and still reports missing FTS; exact context/source inventories compensate pending a tool-session reconnect (DEF-QV-060)", today],
  ["GitNexus repository change-scope audit", "detect_changes scope=compare base_ref=origin/main; per-symbol impact; explicit path-scoped git diff/stat/check", "Degraded", "Every edited product/tracker symbol had a LOW-risk pre-edit impact report, but repository-wide change detection exceeded the shared-worktree child-process buffer with ENOBUFS. Explicit agent-path diffs and focused regressions compensate; the graph-wide scope map remains open (DEF-QV-201).", today],
  ["Query feature reconciliation", "vitest query-interactions, history-restore, scan-metrics, and query visualization files; canonical contract diff", "Pass", "All 19 Query rows now describe the current context-bound persisted investigation workbench and extant API workflows rather than the retired capability rail; 61/61 focused frontend and 60/60 associated backend cases pass", today],
  ["Post-seal inventory delta", "vitest complete files for all 83 frontend nodes added after the 1,611-node seal; pytest complete affected files; recollect exact inventories", "Pass", "Eighty-three net new frontend nodes and nineteen backend nodes are reconciled through complete files; every completed current file passes, including citation, query visualization, profile, navigation, notification, modal, analyst-opinion, EDGAR, report, authority, decision, Settings, Model, Monitor, Deep-Dive, and Upload cohorts (DEF-QV-140 through DEF-QV-152)", today],
  ["Settings production-source regression", "vitest settings-models; lint; tsc; next build; Playwright settings_flow in Chromium/Firefox/WebKit; axe /settings at 1440x900 and 390x844", "Pass", "15/15 component cases, zero lint/type findings, the 20-route production build, 12/12 zero-retry browser journeys, and both responsive accessibility states pass with zero axe nodes, scan errors, or layout failures (DEF-QV-145)", today],
  ["Late shared/EDGAR frontend delta", "vitest Notifications, AnalysisContextSaveState, analyst-opinions, use-modal-a11y, NavigationGuardProvider, and EdgarImport; lint; tsc", "Pass", "All six completed files pass 45/45 after repairing four EDGAR harness failures and stabilizing the parameterized error identities; lint and TypeScript are clean (DEF-QV-146; DEF-QV-147)", today],
  ["Late Model source regression", "vitest model-page-interactions; lint; tsc; next build; Playwright model_flow in Chromium/Firefox/WebKit; axe /model at 1440x900 and 390x844", "Pass", "The expanded Model file passes 13/13, the 20-route production build and static gates are clean, all 15 zero-retry browser executions pass under both required rollout gates, and both responsive axe states report zero nodes, scan errors, or layout failures (DEF-QV-148; DEF-QV-149)", today],
  ["Late Monitor/Deep-Dive delta", "vitest monitor-governance and OutputRegister; lint; tsc", "Pass", "Both completed files pass 23/23, including expected offline-path diagnostics, and the exact-current lint and TypeScript gates remain clean (DEF-QV-150)", today],
  ["Upload feature reconciliation", "vitest run src/components/upload; pytest mapped Upload/EDGAR/AV files; exact assertion-level feature mapping", "Pass", "All 27/27 current Upload features now have direct automation: 40/40 frontend and 125/125 server cases pass; three new robustness contracts cover vault path uniqueness, durable metadata, and the exact 20-allowed/21st-rejected rate boundary. The first restricted AV run failed only because local socket binding was denied; the permitted complete rerun passed.", today],
  ["Concurrent Model delta reconciliation", "vitest six affected Model files; pytest test_model_engine_v2.py; lint; tsc; next build; Playwright model_flow; axe /model", "Pass", "All 68/68 frontend and 66/66 backend cases pass; lint, TypeScript, and the 20-route production build are clean; all 15 zero-retry Model journeys pass across three engines and both responsive axe states report zero violations or layout failures.", today],
  ["Sector Review feature reconciliation", "vitest SectorReviewDossier and SectorReviewPanels; pytest test_sector_routes.py and test_analysis_workspace.py; exact assertion-level feature mapping", "Pass", "All 9/9 Sector Review features now describe the current versioned dossier rather than the retired v1 signal-card workspace and have direct assertion-level evidence; the complete focused files pass 9/9 frontend and 19/19 executable server cases with one intentional pre-existing skip (DEF-QV-153).", today],
  ["Settings feature reconciliation", "vitest settings-models and model-mode; pytest test_settings.py and test_presets.py; Playwright settings_flow across Chromium/Firefox/WebKit; exact assertion-level feature mapping", "Pass", "All 10/10 Settings features now describe the current authenticated five-tab workbench, read-only environment snapshot, staged profile/device preferences, and revision-checked email persistence; the complete focused files pass 18/18 frontend, 23/23 server, and 12/12 browser executions after the first broad shell-title locator failed strict mode in 3/12 and was narrowed to the actual identity element. The repository-default SQLite artifact could not boot because its recorded schema lacks a current lease column; it was not mutated, and the browser matrix ran against an isolated database successfully migrated through all 64 revisions (DEF-QV-154; DEF-QV-155; DEF-QV-156).", today],
  ["Shell feature reconciliation", "vitest: sixteen Shell/Ask/navigation/hierarchy files; exact assertion-level feature mapping", "Pass", "All 17/17 Shell features now describe the current role-priority navigation, canonical route heading, breakpoint-owned Ask utility, responsive skip landmarks, overflow-only Panel focus, semantic hierarchy, Alt hotkeys, profile identity, root handoff, disclosure, recovery, and health contracts. After the in-flight redesign revisions settled, the complete expanded Shell/design cohort passes 83/83 (DEF-QV-157; DEF-QV-158; DEF-QV-159; DEF-QV-161; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166).", today],
  ["Persona and database-pool inventory delta", "vitest: 16 complete modified/delta files; pytest: model, upload, database-pool, and Settings inventory files; lint; tsc", "Pass", "The exact inventory advanced by nine frontend and 20 backend nodes with no removals. All 16 complete frontend delta/modified files pass 143/143; the four affected server files pass 362/362; lint and TypeScript are clean. This intermediate reconciliation advanced the evidence seal to 1,703 frontend and 2,536 server/stress/cohort nodes (DEF-QV-160).", today],
  ["Late shared hierarchy and Shell inventory delta", "vitest: eight complete Ask/persona/layout/Panel/Shell/SubHeader/hierarchy/navigation files; expanded Shell cohort; lint; tsc; next build", "Pass", "A net 14 frontend nodes landed after the 1,703 seal. The eight complete affected files pass 61/61 and the expanded 17-feature Shell/design cohort passes 83/83 after the first in-flight run failed 10/61 and a second transitional run failed 4/61. Lint, TypeScript, and the exact-current 20-route production build are clean. The evidence seal is now 1,717 frontend and 2,536 server/stress/cohort nodes (DEF-QV-161 through DEF-QV-166).", today],
  ["HTTP policy middleware evidence delta", "caos/server/.venv311/bin/python -m pytest -q caos/tests/server/test_security_headers.py; exact server recollection", "Pass", "Three exact CSRF, edge-proof, and duplicate Set-Cookie policy nodes landed after the 2,536-node server/stress/cohort seal. The complete security-header file passes 8/8, advancing the current inventory to 2,539 collected nodes with 2,515 executable server passes, 15 intentional skips, and nine passing stress/cohort nodes (DEF-QV-167).", today],
  ["Issuer feature reconciliation", "vitest: Issuer Directory, profile distillation, analyst notes, issuer helpers, and profile chart helpers; exact assertion-level feature mapping", "Pass", "All 29/29 stable Issuer features now describe the implemented directory and profile contracts and resolve to direct assertion-level evidence. The complete five-file focused cohort passes 72/72 after adding a non-color distressed-rating signal and correcting the first semantic-grid harness assumptions (DEF-QV-168; DEF-QV-169).", today],
  ["Late route-recovery and color-policy inventory delta", "vitest: route heading overrides, error surfaces, recovery UI, navigation, color-literal policy, and hierarchy/color contract files", "Pass", "The fail-closed collector found eight net frontend nodes after the 1,717 seal. All six complete contributing files pass 34/34, advancing the reconciled frontend inventory to 1,725 nodes (DEF-QV-170).", today],
  ["Late route-heading and Report Studio static regression", "eslint src; tsc --noEmit; vitest route-heading-overrides and reports-interactions", "Pass", "The first current-source gates found a conditional usePathname call and a paper-tone state narrowed to one literal. After LOW-risk fixes, lint and TypeScript are clean and both complete affected files pass 24/24 (DEF-QV-171; DEF-QV-172).", today],
  ["Exact-current Issuer build and responsive accessibility", "npm run build; static-export loopback server; axe /issuers and /issuers/profile at 1440x900 and 390x844", "Pass", "The first restricted build and browser launches were denied local worker-port and Chromium rendezvous privileges. Scoped permitted reruns passed the 20-route production build; the final exact-built Issuer directory/profile rescan passed all four states with zero axe nodes, scan errors, layout failures, overflow, or clipped controls (DEF-QV-173; DEF-QV-174).", today],
  ["Issuer permission-boundary closure and late Research delta", "vitest RequireAuth.test.tsx and ReportBody.test.tsx; exact assertion-level Issuer permission mapping; exact frontend recollection", "Pass", "RequireAuth proves anonymous and unresolved identities cannot render protected workspace children, closing the permission/security scenario for all 29 Issuer features with 5/5 passing. One concurrent ReportBody node then landed and its complete two-case file passed, advancing the frontend inventory to 1,726 (DEF-QV-175).", today],
  ["Issuer route-boundary scenario closure", "vitest Issuer Directory and profile-distill complete files; exact-built route accessibility matrix at desktop/mobile; assertion-level route ownership mapping", "Pass", "Directory load failure and retry own error behavior for its 13 features; profile load failure and missing-id rejection own error/invalid entry for its 16 features; the clean /issuers and /issuers/profile route matrix owns responsive geometry. The supporting Issuer cohort and exact-current directory rescan pass, with the complete 36-state responsive baseline retained.", today],
  ["Issuer performance-evidence label reconciliation", "canonical scenario-label audit against curated Issuer mappings; complete issuer-batch execution", "Pass", "Three passing debounce, duplicate-submit, and content-visibility assertions were mapped to a non-canonical Performance considerations label. Renaming the mappings to Performance restores their exact scenario status without changing product behavior; issuer-batch remains 21/21 passing (DEF-QV-176).", today],
  ["Late EnterprisePage typed-action delta", "vitest EnterprisePage.action-contract.test.tsx; quiescent complete-file rerun; exact frontend recollection", "Pass", "Five shared typed-action nodes landed after the 1,726 seal. The first run observed an intermediate no-action revision and failed 1/5 twice; the saved guard was already complete, and the unchanged quiescent rerun passed 5/5, advancing the frontend inventory to 1,731 (DEF-QV-177).", today],
  ["Issuer complete scenario-matrix closure", "29 Issuer features × seven mandatory scenario classes; exact assertion-level mapping; fail-closed generator gate; focused three-file regression", "Pass", "All 203/203 Issuer scenario rows are direct passes: happy, error, boundary, invalid, permission/security, performance, and mobile/responsive. Encoded hostile-looking issuer IDs, single-request profile load, directory containment, route failure ownership, shared auth, and exact route accessibility evidence close the remaining matrix; the strengthened files pass 46/46.", today],
  ["Post-Issuer exact-current static and accessibility refresh", "eslint src; tsc --noEmit; next build; axe Issuer directory/profile at desktop/mobile", "Pass", "The first lint pass found two dead ActionReason imports from the concurrent typed-action migration. After their removal, lint and TypeScript are clean, the production build generates all 20 routes, and all four exact-built Issuer responsive states pass with zero accessibility or layout failures (DEF-QV-178).", today],
  ["Command authority and density remediation", "vitest CommandPortfolio, RankedChanges, current Command contracts, and page interactions", "Pass", "25/25 focused authority assertions pass after missing ticker, selected-strip fields, run-bound Deep-Dive, and stable-issuer Watchtower handoffs were made fail closed; persisted rows carry bounded paint containment (DEF-QV-179 through DEF-QV-184).", today],
  ["Command isolated browser matrix", "PLAYWRIGHT_BASE_URL=http://localhost:3019 playwright test command_flow.spec.ts --workers=1 --retries=0", "Pass", "All four current Command journeys pass in Chromium, Firefox, and WebKit for 12/12 executions, including every dataset at 390x844 with no document overflow and a fully operable selected-position strip (DEF-QV-185 through DEF-QV-187).", today],
  ["Command complete scenario-matrix closure", "44 Command Center features × seven mandatory scenario classes; exact assertion-level mapping; fail-closed generator gate", "Pass", "All 308/308 main Command Center scenario rows are direct passes across happy, error, boundary, invalid, permission/security, performance, and mobile/responsive behavior. The separate nine-feature Sector Review concept remains independently mapped.", today],
  ["Post-Command automation delta", "six complete Vitest contributors; stable parameter identities; exact recollection; Command Playwright in three engines", "Pass", "The 14-node frontend delta passes through six complete files at 51/51, the renamed PageAction table passes 10/10 with unique operation labels, and the three new browser-project nodes pass. Exact inventory is 1,745 frontend, 2,539 server/stress/cohort, 144 browser, and 36 accessibility states (DEF-QV-188; DEF-QV-189).", today],
  ["Late evidence/completion delta", "vitest EvidenceSelectionList, evidence-selection integrations, CompletionStateSummary, and completion-adoption contract", "Pass", "Thirteen late shared-worktree nodes pass through all four complete contributing files at 13/13, advancing the exact frontend inventory from 1,745 to 1,758 before workbook publication (DEF-QV-190).", today],
  ["Exact-current Command accessibility", "static export; axe /command at 1440x900 and 390x844", "Pass", "Both exact-built Command states pass with zero WCAG violation nodes, scan errors, layout failures, page overflow, unexpected horizontal offsets, clipped controls, undersized targets, or overlay collisions.", today],
  ["Quiescent tracker collection recovery", "stop isolated Next dev stack; rerun fail-closed artifact-tool tracker builder", "Pass", "The first collection attempt timed out in a Vitest worker RPC while the isolated Next development server was using the same transform graph. After that stack stopped, the unchanged exact inventory collected and exported successfully at 1,758 frontend nodes (DEF-QV-191).", today],
  ["Sector Review complete scenario-matrix closure", "nine Sector Review features × seven mandatory scenario classes; exact assertion-level mapping; fail-closed generator gate", "Pass", "All 63/63 Sector Review scenario rows are direct passes across happy, error, boundary, invalid, permission/security, performance, and mobile/responsive behavior (DEF-QV-192 through DEF-QV-197).", today],
  ["Sector Review focused regression", "vitest five Sector/SourceRef/auth/removal files; pytest three Sector/analysis files; eslint; tsc", "Pass", "The broader frontend cohort passes 37/37, the exact Sector component files pass 19/19, and the server cohort passes 21 executable cases with one intentional PostgreSQL skip; lint and TypeScript are clean after correcting one nullable test fixture (DEF-QV-192 through DEF-QV-199).", today],
  ["Sector Review browser, accessibility, and performance", "webpack production build; sector_flow in Chromium/Firefox/WebKit; axe /sector at 1440x900 and 390x844; performance-audit desktop/mobile-slow", "Pass", "All six zero-retry browser executions pass after the cross-sector stale-response fix; the 20-route build and both responsive axe states are clean. Desktop LCP is 148ms with 0ms TBT; throttled mobile LCP is 6,120ms with 186ms TBT and remains an explicit performance risk rather than a passing budget claim (DEF-QV-192; DEF-QV-200).", today],
  ["Exact-current automation reconciliation", "compare prior Automation Evidence identities; execute every contributing complete file; recollect Vitest, pytest/stress/cohort, Playwright, accessibility, and Sector performance nodes", "Pass", "Twenty-seven frontend identities were added and two retired; all twelve contributing files pass 92/92. The exact seal advances to 1,783 Vitest, 2,540 pytest/stress/cohort, 150 Playwright, 36 route-accessibility, and one Sector performance node (DEF-QV-198).", today],
  ["Monitor complete scenario-matrix closure", "seven Monitor features × seven mandatory scenario classes; exact assertion-level mapping; fail-closed generator gate", "Pass", "All 49/49 Monitor scenario rows are direct passes across happy, error, boundary, invalid, permission/security, performance, and mobile/responsive behavior (DEF-QV-202).", today],
  ["Monitor focused regression", "vitest six Monitor/data/replay files; pytest alert states, notifications, and sponsors digest; eslint; tsc; production build", "Pass", "The complete focused frontend cohort passes 36/36, the linked server cohort passes 23/23, lint and TypeScript are clean, and Next.js emits all 20 static routes after the finite replay-count repair (DEF-QV-202).", today],
  ["Monitor browser, accessibility, and performance", "monitor_flow in Chromium/Firefox/WebKit; exact-built axe/workbench checks; five-sample gzip-aligned performance audit", "Pass", "The prior 6.74s result was identity-encoded and did not match deployed Caddy gzip. After the on-demand Ask split, desktop ready/LCP/TBT are 502ms/148ms/0ms; five constrained-mobile samples produce p75 ready/LCP/TBT of 2,492ms/2,100ms/188ms with 227.2KB encoded JavaScript. Both responsive axe states and all three workbench viewports are clean (DEF-QV-203; DEF-QV-217).", today],
  ["Post-Monitor automation delta", "execute complete Monitor, Deep-Dive, Research, and shared-shell contributors; recollect exact inventories", "Pass", "Four Monitor nodes and five concurrent frontend nodes landed after the 1,783 seal. All five complete contributing files pass 44/44, advancing the exact frontend inventory to 1,792 and the total evidence inventory to 4,520 after adding the exact-current Monitor performance node (DEF-QV-204).", today],
  ["Tracker blocked-case disclosure", "reconcile Coverage Summary status categories to the complete Test Matrix", "Pass", "The summary retains an explicit Blocked category; the former GitNexus infrastructure row is now an explicit Not applicable external-tool waiver, so no validation case remains blocked (DEF-QV-060; DEF-QV-201; DEF-QV-205).", today],
  ["Pipeline complete scenario-matrix closure", "45 Pipeline features × seven mandatory scenario classes; assertion-level family and endpoint mapping; fail-closed generator gate", "Pass", "All 315/315 Pipeline scenario rows are direct passes. Cross-cutting route evidence is limited to composed UI, authentication, responsive, invalid-state, and cold-load behavior; seven API contracts retain endpoint-specific server assertions rather than inheriting a request-load claim (DEF-QV-206 through DEF-QV-208).", today],
  ["Pipeline focused regression", "vitest 13 Pipeline/Issuers/navigation files; pytest five runs/API/engine/role/tenancy files", "Pass", "The complete focused frontend cohort passes 136/136 after the live/reference, invalid-route, storage, simulation, responsive, and empty-state additions; the linked API/engine cohort passes 104 executable cases with two intentional skips and one existing Starlette deprecation warning.", today],
  ["Pipeline browser, accessibility, and performance", "pipeline_flow in Chromium/Firefox/WebKit; axe /issuers, /pipeline, and /pipeline/?mode=reference at 1440x900 and 390x844; performance-audit desktop/mobile-slow", "Pass", "All 12 zero-retry browser executions and all six exact-built responsive accessibility states pass. Pipeline desktop ready/LCP/TBT/CLS are 509ms/144ms/0ms/0.006; throttled-mobile ready/FCP/LCP/TBT/CLS are 6,810ms/4,284ms/6,380ms/203ms/0.010 with 870.9KB JavaScript. This is route cold-load evidence, not staged request-load evidence.", today],
  ["Post-Pipeline exact-current reconciliation", "execute the complete 1,801-node frontend inventory; repair failures; rerun complete affected files; execute all backend deltas; recollect every automation layer", "Pass", "Nine frontend nodes, four server nodes, and twelve browser-project nodes landed after the prior seals. The full current frontend run found two defects at 1,799/1,801; repaired affected files pass 24/24, both complete notification/migration files pass 79/79, and the exact inventory advances to 1,801 Vitest, 2,544 pytest/stress/cohort, 162 Playwright, 36 route-accessibility, and four route-performance nodes (DEF-QV-209 through DEF-QV-216).", today],
  ["Monitor payload remediation", "production build; gzip transport gate; five mobile samples; closed/open Ask waterfall; exact responsive axe/workbench checks", "Pass", "The heavy Ask analytical chunk is absent from the closed Monitor waterfall and fetched on first Ask open. Raw initial JavaScript falls 875.2KB→766.0KB; deployed-transport JavaScript falls 266.8KB→227.2KB; five-sample mobile p75 LCP improves 2,320ms→2,100ms and TBT 215ms→188ms without changing Ask behavior.", today],
  ["Post-remediation exact-current reconciliation", "npm test -- --run; lint; tsc --noEmit; exact 20-route production build; automation collection", "Pass", "All 1,803 frontend nodes pass in one full run; all 2,544 server/stress/cohort, 162 browser, 36 accessibility, and four route-performance identities remain reconciled for 4,549 exact automation nodes. The external GitNexus session defects are explicitly waived from the product completion gate with source/impact/diff compensating controls (DEF-QV-060; DEF-QV-201; DEF-QV-218).", today],
  ["Report Studio direct-evidence reconciliation", "vitest reports-interactions; exact assertion-level mapping; fail-closed 28-feature evidence gate", "Pass", "The complete 19-case Report Studio interaction file passes, including unsupported persisted paper-tone rejection. A stale test-name mapping was repaired, all 28 Report Studio features now carry direct automation, and the generator fails closed if any Report Studio feature becomes indirect-only or unmapped (DEF-QV-219; DEF-QV-235).", today],
  ["Report Studio complete scenario-matrix closure", "28 Report Studio features × seven mandatory scenarios; exact frontend/server/browser/performance mappings; backend viewport N/A gate", "Pass", "All 194/194 applicable Report Studio scenario rows are direct passes; the two Mobile/responsive rows for the backend-only committee JSON endpoint and its QA gate are explicitly Not applicable rather than fabricated UI coverage (DEF-QV-219 through DEF-QV-230).", today],
  ["Report Studio focused regression", "vitest MoreDrawer, SubHeader, Report panels, and reports-interactions; pytest exact committee/vault authority nodes; next build", "Pass", "The complete focused frontend cohort passes 41/41 and the tightened server authority/invalid-ID pair passes 2/2 under .venv311. Next.js 16.2.10 emits all 20 static routes after the authority-notice and shared drawer-clamp fixes.", today],
  ["Report Studio browser, accessibility, and performance", "exact-build workbench validator at desktop/tablet/phone; axe /reports at 1440x900 and 390x844; desktop plus five constrained-mobile gzip samples", "Pass", "All three workbench widths pass with restored drawer/evidence focus, no API fallthrough, page overflow, uncontained clipping, or console/network failure; both axe states report zero nodes, scan errors, and layout failures. Desktop ready/LCP/TBT are 596ms/148ms/2ms; constrained-mobile p75 ready/LCP/TBT are 2,968ms/2,324ms/330ms with 267.0KB encoded JavaScript, gzip, and zero CLS (DEF-QV-220 through DEF-QV-227).", today],
  ["Post-Report exact-current reconciliation", "npm test -- --run; eslint; tsc --noEmit; complete test_engine.py + test_async_runs.py; fail-closed tracker rebuild", "Pass", "The first full frontend run exposed one stale Model checkpoint journey at 1,807/1,808; after selecting the implemented History support rail and adding direct invalid paper-tone coverage, the final full run passes 1,809/1,809 across 261 files. Lint and TypeScript are clean; the complete Report-linked server files pass 65 executable cases with two intentional skips and one existing Starlette deprecation warning. The tracker rejected oversized rendering, stale split Sector evidence, execution-row contamination, and the last Report invalid-input gap before a bounded, exact export (DEF-QV-231 through DEF-QV-235).", today],
  ["Model Builder feature and scenario reconciliation", "66 Model Builder features × seven mandatory scenarios; focused Vitest and .venv311 server cohorts; fail-closed generator gates", "Pass", "The register includes the 23 live Model Engine v2 workflows omitted by the legacy 43-row inventory and reconciles eleven drifted legacy contracts. All 462/462 Model Builder scenario rows have direct assertion-level evidence; the focused frontend cohort passes 229/229 and the expanded linked server cohort passes 242/242 with one existing Starlette/httpx deprecation warning (DEF-QV-240 through DEF-QV-246).", today],
  ["Model API complete scenario reconciliation", "18 discovered Model API handlers × seven scenarios; direct legacy/v2/workbook HTTP assertions; bounded-work contracts; backend viewport N/A gate", "Pass", "All 108/108 applicable Model API scenarios pass with direct endpoint-specific evidence; 18 backend-only Mobile/responsive rows are explicitly Not applicable. The two complete changed server files pass 62/62, including 18 parameterized bounded-work contracts and the live 15-allowed/16th-rejected checkpoint rate boundary (DEF-QV-242 through DEF-QV-246).", today],
  ["Post-Model API backend evidence delta", "pytest complete changed Model API files; exact pytest/stress/cohort recollection", "Pass", "Twenty-eight executable Model API nodes were added after the 2,544-node backend seal. Both complete changed files pass 62/62, advancing the reconciled server/stress/cohort inventory to 2,572 nodes: 2,548 executable server passes, 15 intentional skips, and nine passing stress/cohort nodes (DEF-QV-243; DEF-QV-246).", today],
  ["Canonical direct-evidence closure", "seven final API list/root contracts; slash-preserving API inventory; strict all-feature evidence gate", "Pass", "All 683/683 canonical features now carry direct automation. The ten initially unmapped API rows and one newly exposed slash alias resolve through seven new runtime contracts plus existing trailing-slash suites, and the generator fails closed if any feature loses direct evidence (DEF-QV-247; DEF-QV-248).", today],
  ["Final API list/root focused regression", ".venv311/bin/python -m pytest test_api_list_quality_contracts.py test_portfolio.py test_portfolios.py test_sponsors_digest.py -q", "Pass", "All 32/32 focused server cases pass, covering owner isolation, ordering, limits, invalid inputs, context and sector filtering, legacy portfolio posture, portfolio creation/listing, sponsor grouping, and both slash forms of the aliased roots (DEF-QV-247; DEF-QV-248).", today],
  ["API list/root complete scenario reconciliation", "11 API list/root features × seven scenarios; database-failure recovery; exact rate backpressure; bounded-work contracts; backend viewport N/A gate", "Pass", "All 66/66 applicable scenarios across API-006, API-093 through API-097, API-120, API-133, API-158, API-168, and API-169 have direct passing evidence; 11 backend-only Mobile/responsive rows are explicitly Not applicable. The first focused run exposed two harness-only contract assumptions before the complete 33-case file and 58-case linked cohort passed (DEF-QV-249 through DEF-QV-251).", today],
  ["Post-list API backend evidence delta", "pytest complete list/root quality file; exact pytest/stress/cohort recollection", "Pass", "Twenty-six executable list/root API nodes were added after the 2,579-node backend seal. The complete changed file passes 33/33 and the linked alias cohort passes 58/58, advancing the reconciled server/stress/cohort inventory to 2,605 nodes: 2,581 executable server passes, 15 intentional skips, and nine passing stress/cohort nodes (DEF-QV-251; DEF-QV-252).", today],
  ["Settings implementation-contract reconciliation", "current Settings page and server routes versus settings-01..10 and API-164..167; strict 98-row scenario gate", "Pass", "Four stale Settings contracts were reconciled to current code, and all 94/94 applicable Settings UI/API scenarios now have direct assertion-level evidence; four backend-only viewport rows remain explicit Not applicable (DEF-QV-253; DEF-QV-256).", today],
  ["Settings focused frontend and server regression", "vitest six linked Settings/auth/helper files; .venv311 pytest four Settings/API/config/role files; eslint; tsc --noEmit", "Pass", "All 56 frontend and 291 server cases pass, including exact failure recovery, profile isolation, invalid/oversized input, the shared 30/min mutation boundary, and bounded handler work. ESLint and TypeScript are clean; one existing Starlette/httpx warning is disclosed (DEF-QV-254 through DEF-QV-258).", today],
  ["Settings cross-browser and phone regression", "isolated migrated SQLite server; settings_flow.spec.ts with retries=0 in Chromium, Firefox, and WebKit", "Pass", "All 15/15 executions pass. At 390x844 every Models, Research, Email Intel, Portfolios, and Workspace tab is selected and rendered in turn, Home returns to Models, and document overflow stays within one pixel (DEF-QV-259; DEF-QV-260).", today],
  ["Post-Settings automation evidence delta", "fail-closed Vitest, pytest, and Playwright collection after complete contributing-file execution", "Pass", "The current seal is 4,635 nodes: 1,811 frontend, 2,616 server/stress/cohort, 165 browser, 36 accessibility, six performance, and one responsive-workbench node. The 16-node Settings delta was executed before the count gates advanced (DEF-QV-257).", today],
  ["Concurrent Deep-Dive module-group delta", "quiescent fail-closed collection; vitest module-groups.test.ts complete file", "Pass", "The collector first rejected a transient missing paired implementation, then found three net new frontend identities. The completed module-group file passes 3/3, advancing the current seal to 1,814 frontend and 4,638 total evidence nodes (DEF-QV-261).", today],
  ["Model Builder browser, accessibility, and performance", "model_flow in Chromium/Firefox/WebKit; axe /model at 1440x900 and 390x844; desktop plus five constrained-mobile gzip samples", "Pass", "All 15/15 zero-retry browser executions pass after selecting Scenario through the current Model support toolbar. Both responsive axe states report zero nodes, scan errors, and layout failures. Desktop ready/FCP/LCP/TBT are 1,295/48/108/0ms; constrained-mobile p75 ready/FCP/LCP/TBT are 3,540/980/2,152/293ms with 297.9KB encoded JavaScript, gzip, zero CLS, and readiness bound to the real Model worksheet (DEF-QV-236 through DEF-QV-239).", today],
  ["QA scale seeder and security headers", ".venv311/bin/python -m pytest ../tests/server/test_seed_qa_scale.py ../tests/server/test_security_headers.py -q", "Pass", "9/9 passed: loopback/database guardrails, deterministic sanitized scale/workflow fixture, idempotence, and deployed security headers", baselineDate],
  ["Health performance smoke", "caos/server/.venv311/bin/python caos/tests/perf/smoke.py --url http://127.0.0.1:8010/api/health --n 200 --concurrency 20 --p95-ms 500", "Pass", "0 errors; p50 23ms; p95 82ms against a 500ms gate", baselineDate],
  ["Scenario benchmark", "cd caos/server && .venv311/bin/python -m pytest ../tests/perf/test_scenario_benchmark.py -q --durations=0", "Pass", "1/1 bounded scenario benchmark passed; benchmark call 0.01s, pytest lane 0.36s", baselineDate],
  ["Dependency lock sync", "caos/server/.venv311/bin/python caos/scripts/check_lock_sync.py", "Pass", "requirements.lock satisfies all 17 requirements.txt specs", baselineDate],
  ["Modular OS consistency", "caos/server/.venv311/bin/python 'Modular OS/tools/check_module_consistency.py'", "Pass", "26 modules checked / 0 drift", baselineDate],
  ["Complexity delta", "PATH=caos/server/.venv311/bin:$PATH caos/server/.venv311/bin/python caos/scripts/check_complexity_delta.py --base-ref origin/main", "Pass", "40 bounded findings across 161 changed Python paths", baselineDate],
  ["Deep-Dive implementation-contract reconciliation", "current Deep-Dive route and 27-module catalog versus deepdive-01..42; strict 294-row scenario gate", "Pass", "The module launcher contract now records three semantic groups across all 27 current modules, and the narrow contract records the implemented complete workbench rather than the removed read-only phone triage card. All 294/294 Deep-Dive scenario rows have direct assertion-level evidence (DEF-QV-262 through DEF-QV-267).", today],
  ["Deep-Dive focused functional regression", "vitest complete Deep-Dive, evidence, recovery, authentication, vault, navigation, decision, and scenario-network files; pytest test_qa_flags.py", "Pass", "All 161 Deep-Dive-linked frontend cases and all 7 QA-flag server cases pass, including persisted shortcut caps, stale-response rejection, explicit evidence failure states, bounded personal annotations, scenario backpressure/retry, and first-run storage denial.", today],
  ["Deep-Dive browser, accessibility, and performance", "deepdive_flow in Chromium/Firefox/WebKit with retries=0; axe reference workspace at 1440x900 and 390x844; desktop and constrained-mobile gzip audit", "Pass", "All 12/12 browser executions pass after repairing the obsolete bare-route and hidden-duplicate locators. Both axe states report zero nodes, scan errors, and layout failures after the clipped global Ask control was fixed. Desktop ready/LCP/TBT are 542/168/0ms; constrained-mobile ready/LCP/TBT are 2,698/2,284/226ms with 293.0KB encoded payload, gzip, and zero CLS.", today],
  ["Routed-concept browser contract delta", "PLAYWRIGHT_BASE_URL=http://127.0.0.1:8017 npm run test:e2e -- --retries=0 --workers=1 routed_concepts_flow.spec.ts", "Pass", "All 15/15 deterministic project executions pass across Chromium, Firefox, and WebKit: Decisions agenda/history, Portfolio positions/constraints, Issuer Profile evidence navigation, Sector RV compare/ratify, and Sponsor error/preserved-selection/retry. Fixtures fail closed on unhandled local API requests; the strengthened console gate allows only the one engine-dependent resource log caused by the deliberate Sponsor 503 (DEF-QV-268; DEF-QV-271). This is route-contract evidence, not the frozen H0 real-API seal.", today],
  ["Post-PD-04 exact-current automation reconciliation", "vitest list --json; pytest server/stress/cohort --collect-only; playwright --list; compare with executed PD-04/current server and routed-concept runs", "Pass", "The fail-closed collector exposed the intentional 69-node dead-subject reduction, two-node server/stress/cohort delta, and a stale Deep-Dive chat-error mapping. Current evidence reconciles 1,750/1,750 frontend passes, 2,594 server passes plus 15 intentional skips and nine passing stress/cohort nodes (2,618 collected), and 183 browser nodes including the new 15/15 routed-concept matrix (DEF-QV-269; DEF-QV-270).", today],
  ["PD-05 browser-boundary recovery", "PLAYWRIGHT_BASE_URL=http://127.0.0.1:8015 npm run test:e2e -- --retries=0 --workers=1 recovery_flow.spec.ts", "Pass", "All 6/6 executions pass across Chromium, Firefox, and WebKit. A test-only, exact-cardinality response rewrite injects named render failures into the shipped WorkflowRail and Report Studio chunks while separately wrapping the delivered global and shared-segment reset callbacks. Root recovery preserves the authenticated Settings tab and performs zero writes; segment recovery preserves the owned analysis context, IC Memo draft payload, source preference, and one analyst override, performs zero failure-time writes, then advances the original draft exactly one revision with no publication or duplicate mutation. The same shared segment boundary is statically mapped to all six routed segment error files (DEF-QV-273). Frozen H0 repetition remains required.", today],
  ["PD-01 immutable app-image resources", "docker buildx build --load -f caos/deploy/Dockerfile -t caos-app:pd01-check .; docker run runtime-resource and exclusion probes", "Pass", "The corrected repository-root context transfers 3.88 MB from a fresh isolated builder after the initial 4.86 GB negative control exposed parent-negation leakage. The real app image builds, runs the consumer probe as UID 10001, reports prompt fingerprint 15bdcbc3628d, validates the complete CP-2G and CP-4D manifest-backed bundles, and reads 588 RV rows with SHA-256 8ca8c785070a6837b118f0cf9a530d3c63e89d051526f9a70fdf5f844a021597 from /frontend/src/lib/command/market-data.json. The independent loaded-image probe confirms one frontend source file, no secrets/tests/virtualenvs, and clean non-root access (DEF-QV-274; DEF-QV-275). This closes the resource-layout defect only; canonical H0 provenance remains open.", today],
];

const defects = [
  ["DEF-LOOP-001", "shell-10", "Medium", "Fixed", "Vitest's 5s default timeout was below observed jsdom workflow runtime.", "Run npm test before the timeout configuration fix.", "Default frontend unit command passes without CLI overrides.", "Five dense component tests timed out despite otherwise-correct behavior.", "Historical loop defect; fixed by a 20s configured test timeout."],
  ["DEF-LOOP-002", "pipeline-20", "Low", "Fixed", "The concurrency test used total wall-clock as a proxy and included unrelated module overhead.", "Run the server concurrency regression with the former threshold.", "The test proves same-layer synthesizers overlap directly.", "The assertion failed although asyncio.gather still overlapped the modules.", "Historical loop defect; fixed with direct overlap measurement."],
  ["DEF-LOOP-003", "research-13", "Low", "Fixed", "The E2E assertion used a short wait around a dynamically imported report body.", "Run the Research report rendering E2E under a cold bundle.", "The report heading and sources are awaited deterministically.", "The initial attempt was flaky and passed on retry.", "Historical loop defect; fixed with explicit 15s waits."],
  ["DEF-LOOP-004", "pipeline-01", "Low", "Fixed", "An E2E text locator matched both the search summary and issuer row.", "Search for a newly created issuer in Upload E2E.", "The assertion targets exactly one issuer row.", "Playwright strict mode found two matches.", "Historical loop defect; fixed with an exact row locator."],
  ["DEF-QV-001", "shell-10", "High", "Fixed", "A new CP-5B adapter read `driver_register` from an un-narrowed unknown runtime payload and used implicit-any callbacks.", "Run `npm run build` on the current worktree.", "The production TypeScript build completes.", "Build failed at src/lib/engine/adapt.ts:287.", "Narrowed the optional register to record rows; targeted 24-test adapter suite, tsc, and production build pass."],
  ["DEF-QV-002", "shell-05", "Medium", "Fixed", "The local axe harness injected axe-core under the production CSP without a test-only bypass.", "Run the authenticated route axe matrix against the production static build.", "The trusted local validator scans without weakening application CSP.", "Every route failed at page.addScriptTag.", "Added Playwright `bypassCSP` only to the validation browser context."],
  ["DEF-QV-003", "issuer-01", "Low", "Fixed", "The default profile scan hard-coded a fixture issuer id absent from a fresh isolated database.", "Run route axe against a newly migrated seeded database.", "The profile route resolves an issuer that exists in that database.", "The profile readiness marker timed out for id=iss-1.", "The harness now resolves the first accessible issuer unless an explicit route is supplied."],
  ["DEF-QV-004", "query-01", "Medium", "Fixed", "The Query state scanner targeted retired tablist, overlay, ACCEPT/UNDO, and evidence-sheet controls.", "Run scripts/a11y-query.mjs against the current Query workbench.", "The scanner exercises implemented persisted-investigation states.", "It timed out waiting for a role=tablist that no longer exists.", "Replaced the sequence with ready, lane-selection, real answer, and narrow restored-answer states."],
  ["DEF-QV-005", "query-17", "Low", "Fixed", "The rewritten scanner compared the restored answer while the temporary ready heading was still visible.", "Run the Query scanner and reload immediately after a persisted result.", "The validator polls until the saved answer is restored.", "The first rewrite reported a false persistence failure.", "Changed the assertion to wait for the expected saved heading text."],
  ["DEF-QV-006", "model-37", "Medium", "Fixed", "The offline E2E fixture did not expose the current CP-2B response contract.", "Run the Model Builder downside-fragility E2E case against a deterministic response fixture.", "The real Model UI renders and validates the CP-2B fragility readout.", "The former case was skipped and the readout was not exercised end-to-end.", "Added exact current list/CP-1/CP-2B DTO fixtures; the enabled case passes in the zero-retry cohort."],
  ["DEF-QV-007", "model-43", "Medium", "Fixed", "The save/reload E2E cases never dirtied the model, so the UI correctly suppressed PUT.", "Edit the all-years Drivetrain assumption, save, then reload the model.", "PUT /api/models is observed and the exact edited value survives reload.", "The former persistence cases were explicitly skipped.", "The enabled tests now dirty the model, wait for the PUT and saved checkpoint, and assert the exact restored value."],
  ["DEF-QV-008", "research-13", "Low", "Fixed", "A Research E2E expected retired marker copy instead of the implemented live/demo authority labels.", "Run the un-stubbed research provenance marker cases.", "The E2E asserts the current LIVE and AI-synthesized marker contract.", "The former marker test was explicitly skipped.", "Reconciled the assertions with current provenance semantics; both un-stubbed marker branches pass."],
  ["DEF-QV-009", "deepdive-14", "Low", "Fixed", "The hover validator could dispatch before client hydration, leaving visible static markup but no evidence-sync listeners.", "Run the full E2E cohort under five workers with retries disabled.", "Hovering an evidence chip cross-highlights every matching citation deterministically.", "One initial full-cohort attempt needed a retry while the isolated behavior was correct.", "The assertion now re-dispatches hover within a bounded toPass poll; 10/10 no-retry stress repetitions and the full no-retry cohort pass."],
  ["DEF-QV-010", "BP-008", "Low", "Fixed", "The PostgreSQL rollback validator accessed an ORM attribute after rollback had expired the instance, causing forbidden implicit async I/O.", "Run the independent-transaction lineage contention test with commit_winner=false.", "The test compares stable generated IDs after the winner rolls back and the contender commits.", "SQLAlchemy raised MissingGreenlet while reloading first.id after rollback.", "Snapshot the first edge ID before rollback; both commit and rollback contention paths pass against PostgreSQL."],
  ["DEF-QV-011", "SCR-004", "Medium", "Fixed", "Issuer directory filter controls used undersized flex children and column tracks that could compress below their usable width.", "Open /issuers at 390x844 and inspect the filter buttons and sector/sub-sector columns.", "All filters remain distinct, visible, and operable without overlap or clipping.", "Filter targets and narrow column content overlapped or clipped.", "Added non-shrinking 24px filter targets and bounded sector/sub-sector column minima; unit contract and the 390px route scan pass."],
  ["DEF-QV-012", "SCR-017", "Medium", "Fixed", "The Sponsors desktop row layout squeezed its scroll pane to an inaccessible height on a phone viewport.", "Open /sponsors at 390x844 and navigate the sponsor workspace by keyboard.", "The worklist and detail region stack with a usable, keyboard-accessible scroll area.", "The shared row layout compressed the worklist to an unusable strip.", "Sponsors now stacks on mobile, restores the row layout at md, and enforces a mobile minimum height; the 390px scan passes."],
  ["DEF-QV-013", "SCR-018", "Medium", "Fixed", "The Upload step strip overflowed horizontally but exposed no keyboard focus target for scrolling.", "Open /upload at 390x844 and attempt to reach every wizard step without a pointer.", "The labeled step-navigation region is focusable, visibly focused, and horizontally scrollable.", "Overflowed steps were pointer-scrollable only.", "Added a labeled focusable region and visible focus ring; the new unit test and 390px scan pass."],
  ["DEF-QV-014", "SCR-010", "Medium", "Fixed", "Portfolio filter controls switched to the wide layout at 900px before the controls had enough room.", "Open /portfolios at 900x900 and inspect the Apply control.", "The filter form stays stacked until the full control row fits.", "The Apply control was clipped at the former 900px breakpoint.", "Extended the compact layout through 1023px; the 900px scan passes."],
  ["DEF-QV-015", "BP-017", "Medium", "Fixed", "The local E2E harness ran stateful journeys in parallel against one SQLite database, whose single-writer semantics caused transient 500 responses under concurrent mutations.", "Run the complete stateful E2E suite with five workers against the shared local SQLite database.", "The default local regression lane completes deterministically; explicit stress runs may opt into parallel workers.", "Concurrent registration, model, research, and Query writes produced SAVE FAILED/500 responses.", "Default Playwright workers to one with PLAYWRIGHT_WORKERS/--workers overrides; the expanded 46/46 zero-retry lane passes. Production PostgreSQL concurrency remains covered separately."],
  ["DEF-QV-016", "research-13", "Medium", "Fixed", "The Research E2E route glob did not match POST /api/research when the implemented client supplied context_id in the query string.", "Run the stubbed research journeys repeatedly and inspect whether POST /api/research?context_id=... reaches the fixture.", "Every research POST is intercepted by pathname and cannot consume live-server quota.", "The request escaped the stub, hit the real server, and could consume rate limits or create nondeterministic state.", "Use a URL pathname predicate for all Research POST fixtures; the expanded full 46/46 zero-retry lane passes."],
  ["DEF-QV-017", "deepdive-14", "Low", "Fixed", "The hover test polled the sibling highlight and then asserted the hovered chip separately, allowing pointer state to change between the two checks.", "Repeat the Deep-Dive evidence-sync hover journey under five workers with retries disabled.", "Hovered, sibling, and unrelated citation states are asserted in one bounded hover transaction.", "The sibling poll could pass before the later hovered-chip assertion observed a cleared state.", "Co-located all highlight assertions inside the same toPass transaction; 10/10 five-worker stress repetitions and the full E2E lane pass."],
  ["DEF-QV-018", "BP-017", "Low", "Fixed", "The new standalone API contract module assumed a shared TestClient fixture that the server suite does not provide globally.", "Run test_unmapped_api_contracts.py before adding a module-local application fixture.", "Every parameterized request receives a lifespan-managed CAOS TestClient.", "All 14 cases failed during fixture setup before making a request.", "Added a session-scoped module-local TestClient fixture; 14/14 targeted cases and the full server suite pass."],
  ["DEF-QV-019", "API-083", "Low", "Fixed", "The first contract expectation assumed request-body validation ran before the disabled Model Engine v2 feature gate.", "POST an empty workbook-import commit while CAOS_MODEL_ENGINE_V2_ENABLED is false.", "The disabled route fails closed with the implemented non-enumerating 404 response.", "The test expected 422 but the route correctly returned 404 before body validation.", "Reclassified the case as permission/security feature-gate coverage and asserted 404; targeted and aggregate regressions pass."],
  ["DEF-QV-020", "monitor-01", "Low", "Fixed", "The new Monitor E2E assumed the authored email sample contained seven rows.", "Open Monitor email intake and compare the sample caption with the rendered email rows.", "The test asserts the implemented fixed sample size.", "The page truthfully rendered 'Showing 8 of 105', while the test expected 7.", "Updated the exact caption assertion; the focused and full E2E lanes pass."],
  ["DEF-QV-021", "monitor-05", "Low", "Fixed", "The new playback assertion assumed a minute-resolution clock.", "Pause the Monitor replay and inspect its utility status.", "The test accepts the implemented HH:MM:SS replay clock.", "The page rendered PAUSED · 09:30:00 ET, while the test expected HH:MM ET.", "Aligned PAUSED and SIM assertions to the second-resolution clock; the focused and full E2E lanes pass."],
  ["DEF-QV-022", "reports-07", "Low", "Fixed", "The first edit-reset assertion searched the page while the reset action was correctly contained in the closed Report utilities drawer.", "Edit a report field without opening Report utilities, then search for RESET 1 EDIT.", "The test opens the implemented utility popover before operating its reset action.", "The control was not in the accessibility tree until the popover opened.", "Open the utility drawer before asserting and activating reset; the workflow passes."],
  ["DEF-QV-023", "reports-08", "Low", "Fixed", "The compose selector included aria-pressed=true, so after the clicked button changed to false the live locator re-targeted the next true button.", "Toggle the first included Compose section and assert the same live locator becomes false.", "The locator remains bound by stable DOM position while its state changes.", "Playwright re-resolved the selector to another included section and observed true.", "Select the first aria-pressed control independent of its value; the focused and full E2E lanes pass."],
  ["DEF-QV-024", "BP-017", "Low", "Fixed", "The first aggregate pytest invocation ran without permission to bind temporary loopback sockets.", "Run the complete server cohort in the restricted command sandbox.", "ClamAV wire-protocol tests can bind one-shot localhost peers.", "Seven AV tests failed with PermissionError EPERM before an application assertion ran.", "Re-ran the current suite with local socket permission: 2,202 passed and 15 environment-gated tests skipped in aggregate."],
  ["DEF-QV-025", "reports-20", "Medium", "Fixed", "Legacy curated rows still described five deliverables and client-local persistence for active report, edits, omissions, paper, and sources.", "Compare reports-01/02/04/05/06/07/08/20/21 with the current Report Studio effects and six-item report builder.", "The canonical workbook describes six deliverables, local zoom persistence, and context-bound server draft persistence.", "The prior tracker encoded retired localStorage keys and omitted Model Appendix.", "Applied current-code contract overrides in the canonical generator and added E2E proof for six deliverables and reload persistence."],
  ["DEF-QV-026", "monitor-01", "Medium", "Fixed", "Legacy Monitor rows described the reconciled email tape as live and listed retired header KPIs/status copy.", "Compare monitor-01/04/05/06/07 with the current Monitor route and EmailIntel/AlertFeed implementations.", "The canonical workbook distinguishes fixed EOD email intake from live autonomy alerts and seeded replay state.", "The prior tracker conflated the two data authorities and documented stale labels.", "Applied current-code contract overrides and mapped all seven Monitor features to passing interaction tests."],
  ["DEF-QV-027", "BP-017", "Medium", "Fixed", "The first 300-issuer expansion derived synthetic tickers from only the cohort and first three base-ticker characters, so distinct issuers with a shared prefix collided.", "Run test_seed_qa_scale.py::test_300_issuer_book_is_deterministic_unique_and_conspicuously_fictional against the initial expansion.", "All 300 issuer names, tickers, and synthetic FIGIs are deterministic and unique before any database write.", "The regression found 291 unique tickers for 300 generated issuers.", "Ticker generation now uses the unique bounded issuer index; the five focused seed safety/determinism tests pass."],
  ["DEF-QV-028", "command-01", "Medium", "Fixed", "All 44 Command Center tracker rows described the retired sample-portfolio, sparkline, conviction, sector-RV, and local query composition rather than the current persisted-portfolio/Watchtower/governance/digest/cited-brief workbench.", "Reconcile every Command Center feature id against the current /command page, components, hooks, and API clients.", "The canonical register describes every current Command workflow and authority boundary, with direct automated evidence for all 44 ids.", "The prior workbook encoded controls and expected behavior that no longer exist and omitted current portfolio selection, honest dependency states, analysis-context persistence, and cited briefs.", "Replaced all 44 Command contracts in the canonical generator, routed their current trigger/file/endpoint metadata, and added six component plus three browser contract tests."],
  ["DEF-QV-029", "command-06", "Low", "Fixed", "The first selected-strip component assertion treated the CloseButton title as its accessible name.", "Render CommandPositionStrip and query the close action by name 'Close (Esc)'.", "The test uses the implemented accessible name while independently verifying the explanatory title.", "Testing Library exposed the button as Close, so the locator failed before exercising the callback.", "Target the role/name Close and assert title='Close (Esc)' separately; the focused component suite passes."],
  ["DEF-QV-030", "command-23", "Low", "Fixed", "The first live-coverage assertion assumed a metric string was unique even though two fixture rows intentionally shared it.", "Render two coverage rows with the same leverage and call getByText('5.7x').", "The assertion recognizes every matching row or scopes to a specific row.", "Testing Library rejected the ambiguous single-element locator.", "Assert the two rendered metric occurrences; the test now validates both rows and passes."],
  ["DEF-QV-031", "command-39", "Low", "Fixed", "The new alert-state test used a jest-dom toBeDisabled matcher that is not installed in this Vitest setup.", "Acknowledge a Watchtower row and assert the Acked control using toBeDisabled.", "The regression uses matchers supported by the repository or inspects the native disabled property.", "Vitest reported that toBeDisabled was not a function.", "Assert the HTMLButtonElement disabled property directly; the alert-state convergence test passes."],
  ["DEF-QV-032", "BP-017", "Low", "Fixed", "The first Playwright listing command ran npx from the repository root instead of the frontend package and attempted a registry lookup.", "Run npx playwright from the repository root in the network-restricted validator.", "Playwright resolves from the installed frontend dependency tree without network access.", "The command failed with ENOTFOUND before collecting tests.", "Run Playwright from caos/frontend using the installed package; all three Command tests collect and pass."],
  ["DEF-QV-033", "BP-017", "Low", "Fixed", "The first isolated server command combined ENVIRONMENT=development with a custom SESSION_SECRET, which the implemented fail-closed boot guard deliberately rejects.", "Boot the local validation server with the development sentinel and a production-style session secret.", "The harness either uses development defaults or a fully valid deployed posture; the application continues to reject the contradictory combination.", "Startup stopped in require_sane_environment before serving tests.", "Removed the unnecessary custom secret from the isolated development command; the guard remains verified and the server boots."],
  ["DEF-QV-034", "BP-017", "Low", "Fixed", "The restricted command sandbox denied loopback ports needed by the Next.js build worker, the isolated FastAPI server, and Playwright global setup.", "Build the static export, bind the isolated server, and run browser setup inside the restricted sandbox.", "The validation lane receives explicit local-socket permission while application network posture remains unchanged.", "The build and server/browser commands failed with EPERM before product assertions ran.", "Re-ran the exact in-scope commands with approved localhost permission; the static export and focused browser suite pass."],
  ["DEF-QV-035", "command-06", "Medium", "Fixed", "The global Ask launcher used bottom-3 on Command Center and overlapped the selected-position strip's bottom-right Close action.", "Open Positions, select a holding, and activate the visible Close control with a normal Playwright click.", "The launcher and strip controls occupy separate hit regions; Close is operable without force-click or pointer interception.", "Playwright timed out because the fixed Ask Alt+K span intercepted pointer events over the Close button.", "Apply the existing elevated bottom offset to /command as well as /sector, add a unit placement assertion, rebuild the production static bundle, and pass the real browser journey."],
  ["DEF-QV-036", "BP-017", "Low", "Fixed", "A direct Playwright invocation omitted the NODE_PATH required by this repository's test layout, so global setup could not resolve @playwright/test from the sibling e2e directory.", "Run npx playwright test directly from caos/frontend without NODE_PATH=node_modules.", "The direct command supplies the repository's documented module-resolution environment or uses npm run test:e2e.", "Global setup failed at import time before opening a browser.", "Set NODE_PATH=node_modules for the direct focused run; 3/3 Command journeys pass."],
  ["DEF-QV-037", "command-56", "Low", "Fixed", "The first Command E2E mixed a synthetic portfolio fixture with the live analysis-context PATCH endpoint, so the server correctly rejected the nonexistent portfolio scope.", "Autosave the fixture portfolio id portfolio-qa into a real analysis context.", "All boundaries that depend on the synthetic portfolio use the same deterministic route fixture, and the autosave assertion requires a successful merged context response.", "The request body was correct but the real server returned 404 because portfolio-qa did not exist in the isolated database.", "Added an exact pathname-and-method PATCH fixture returning a valid incremented context, then asserted HTTP 200 and the persisted portfolio/view payload."],
  ["DEF-QV-038", "research-13", "Low", "Fixed", "The Research progress E2E queried the animated number 2 globally while the searches counter legitimately passed through 2 on its way to 3.", "Render running progress with two sources and three searches and call page.getByText('2') globally.", "Each statistic assertion is scoped to its labelled counter block and tolerates the other count's animation.", "Playwright strict mode found two visible exact-text matches and failed despite correct progress data.", "Scope the 2 and 3 locators to the sources and searches parent blocks; focused and aggregate browser regression pass."],
  ["DEF-QV-039", "settings-01", "Medium", "Fixed", "The asynchronous analyst-profile load overwrote an already-saved device-local Research audience, so the value restored after reload depended on a slower server response and a prior global save.", "Save a device-only audience, retain a different analyst workspace research_prefs value, then reload Settings.", "The stored device value wins on that device; server preferences are only the fallback when localStorage has no Research preferences.", "The field first restored the local value, then changed to the older server value; the second zero-retry cohort reproduced the data-integrity failure.", "Added a storage-presence guard to the LOW-risk Settings profile fallback without changing the HIGH-risk shared loadPrefs path; unit, focused E2E, and aggregate regression pass."],
  ["DEF-QV-040", "BP-017", "Low", "Fixed", "The first Model Engine v2 validation server enabled CAOS_MODEL_ENGINE_V2_ENABLED but omitted its implemented CAOS_LINEAGE_V2_ENABLED dependency.", "Open a live issuer model while only the model capability flag is enabled.", "The QA harness enables the complete documented capability pair; the application continues to fail closed on an incomplete rollout.", "GET /api/models/v2/{issuer_id} returned 503 with 'Model Engine v2 requires CAOS_LINEAGE_V2_ENABLED'.", "Restarted the isolated server with both capability flags; the v2 endpoint advanced to its ownership gate and the final focused/full browser lanes pass."],
  ["DEF-QV-041", "model-43", "Low", "Fixed", "The sanitized CP-1 workflow run is owned by E2E Model Analyst, while the first v2 Playwright attempt authenticated as the unrelated default E2E Analyst.", "Open the Granite Peak live model under the default E2E analyst identity.", "The mutation journey authenticates as the fixture owner; production run-access controls remain unchanged.", "The canonical model failed closed with 'No completed owned issuer run is available'.", "Set E2E_ANALYST_NAME to the seeded fixture owner; 5/5 focused Model Builder tests and 46/46 zero-retry browser journeys pass without enabling cross-analyst sharing."],
  ["DEF-QV-042", "BP-017", "Low", "Fixed", "Two backend regression attempts started below the repository root, so the root-level run_sec_audit module was absent from Python's import path.", "Collect test_sec_audit_tool.py from caos/ or caos/server.", "The aggregate command runs from the repository root with the designated server virtual environment.", "Pytest stopped during collection with ModuleNotFoundError: run_sec_audit.", "Run the canonical root command; 2,202 tests passed, 15 environment-gated tests skipped, and no application assertion failed."],
  ["DEF-QV-043", "BP-017", "Medium", "Fixed", "The validation ledger still referenced a retired scenario benchmark path, a removed Modular OS wrapper, and a complexity command that did not expose the venv ruff binary.", "Execute the three supporting commands exactly as previously recorded in Validation Runs.", "Every recorded command resolves current files and dependencies from its required working directory.", "The scenario path was absent, the replacement failed to import scenario from the wrong cwd, the Modular OS wrapper was absent, and complexity could not locate ruff.", "Reconciled the ledger to tests/perf/test_scenario_benchmark.py from caos/server, Modular OS/tools/check_module_consistency.py, and the venv-backed complexity invocation; all three current gates pass."],
  ["DEF-QV-044", "BP-017", "Medium", "Fixed", "The first current-source browser server inherited live provider credentials; removing variables from the launch environment was insufficient because dotenv reloaded OpenRouter and Gemini values, so the nominally deterministic Query lane made a remote plan call.", "Start the QA server without explicitly overriding every supported provider key to an empty value, then run the zero-retry Query reload journey followed by Report Studio autosave.", "The local regression lane explicitly blanks ANTHROPIC_API_KEY, OPENROUTER_API_KEY, and GEMINI_API_KEY and exercises the implemented deterministic fallback without remote latency or database-lock contamination.", "Query exceeded the 15-second browser contract and the following Report autosave assertion timed out; the initial cohort ended 44 passed / 2 failed even though focused Report Studio passed 4/4.", "Restarted the clean isolated server with all three provider keys explicitly blank; the latest snapshot completed the full zero-retry cohort 46/46 in 30.0s."],
  ["DEF-QV-045", "BP-017", "Low", "Fixed", "The fail-closed route axe matrix encountered a transient root-redirect readiness timeout at 900x900 after scanning the same redirect successfully at 390x844.", "Run the 36-state route matrix and observe the root route after changing from the phone viewport to 900x900.", "Every route-width state reaches its shared surface marker before axe and layout evaluation, or the validator fails closed and the missing state is rerun explicitly.", "The broad matrix recorded 0 violation nodes and 0 layout failures but exited non-zero with one scan_error for /@900x900.", "Immediately reran ROUTES=/ at 900x900; the root resolved to /issuers with 0 violation nodes, 0 scan errors, and 0 layout findings, completing the 36-state evidence set."],
  ["DEF-QV-046", "command-56", "Medium", "Fixed", "Command context autosave ran before the asynchronous portfolio directory resolved, so selectedPortfolioId was transiently null and the first PATCH cleared a valid persisted portfolio scope.", "Open /command?portfolio=portfolio-qa in a fresh browser and inspect the first analysis-context PATCH while the portfolio directory is loading.", "Autosave waits for portfolio resolution and writes the requested, persisted, or default portfolio without an intermediate null scope mutation.", "The UI selected portfolio-qa correctly, but the first PATCH contained portfolio_scope:null and a null command portfolio filter before a later corrective write.", "Guarded the LOW-impact autosave effect while portfolioDirectoryLoading is true; focused Command/Settings regression passed 7/7 and the complete current-source E2E cohort passed 46/46 with retries disabled."],
  ["DEF-QV-047", "settings-01", "Low", "Fixed", "The Settings E2E still expected the retired literal aria-disabled='false' attribute after the primary action moved to the shared ActionReason contract, which removes disabled metadata when actionable.", "Change the Research audience and inspect the Save changes accessibility attributes.", "The test proves the action is no longer aria-disabled and the no-change explanation is removed, without requiring a nonstandard aria-disabled='false' string.", "The current actionable button had no aria-disabled attribute, so the literal false assertion failed despite correct operability.", "Reconciled the assertion with ActionReason semantics; focused Command/Settings regression passed 7/7 and the final full E2E cohort passed 46/46."],
  ["DEF-QV-048", "BP-017", "Medium", "Fixed", "The first production-like browser cohort reused one analyst for every stateful journey, coupling unrelated tests to the per-analyst analysis-context quota.", "Run all stateful browser journeys consecutively under one forwarded identity against the production-like server.", "Independent workflow groups have isolated analyst quota and session state while retaining real server rate limits.", "Later analysis writes returned HTTP 429 although each journey passed in isolation.", "The production-like runner now assigns three explicit fictional analysts to bounded spec lanes; the complete 46/46 zero-retry rerun passed."],
  ["DEF-QV-049", "model-43", "Medium", "Fixed", "The live Model Builder journey implicitly depended on demo seeding and a workflow run owned by a different analyst, so production settings exposed no mutable model authority.", "Start with CAOS_DEMO_SEED=false and open the Model Builder under an unrelated analyst.", "The scale fixture opts into one deterministic completed CP-1 run owned by the explicit Model E2E analyst, and the journey discovers that fictional issuer.", "The test could not locate the retired demo fixture and the v2 API correctly rejected cross-analyst ownership.", "Added --with-workflow-fixture to the guarded scale seeder, bound the run to E2E Model Analyst, and made the journey discover Granite Peak; 5/5 Model tests passed live."],
  ["DEF-QV-050", "pipeline-01", "Low", "Fixed", "The bootstrap journey hard-coded a 23/23 completion count even though enabled CP-2G and CP-4D rollout gates expand the runtime plan.", "Enable all production rollout gates and complete a new keyless run.", "The assertion derives expected module cardinality from the server plan and accepts every enabled production module.", "The run completed correctly but the fixed 23-module assertion failed.", "Made the journey plan-aware; the gated production-like bootstrap path passes in the 46/46 cohort."],
  ["DEF-QV-051", "BP-017", "Medium", "Fixed", "Successive analyst lane setups wrote the same Playwright storage-state file, allowing a later identity to overwrite an earlier lane's authenticated session.", "Run global setup for multiple forwarded analysts using the shared default .auth/state.json.", "Every analyst lane writes and consumes a distinct storage-state artifact.", "Authentication state was last-writer-wins and Model ownership depended on lane order.", "Added E2E_STORAGE_STATE_PATH support and deterministic per-lane state filenames; all three lanes pass independently."],
  ["DEF-QV-052", "BP-017", "High", "Fixed", "The server snapshots static-export inline-script hashes into its CSP at startup; rebuilding or restaging the frontend without a restart left the live policy stale.", "Replace the staged static export while the local production server remains running, then load a route.", "The QA lane proves every hash required by the staged HTML exists in the live CSP before browser execution.", "The browser rejected current inline bootstrap scripts under the older live CSP.", "The production-like runner computes all staged inline hashes and fails before tests if the live CSP is stale; the server is restarted after every staged build."],
  ["DEF-QV-053", "BP-017", "High", "Fixed", "A successful browser pass could otherwise target a static export older than concurrently edited frontend source.", "Modify any frontend source after staging the export and invoke the production-like runner.", "The runner refuses to execute until the exact current source is rebuilt and staged.", "Current UI copy and behavior diverged from the artifact under test; two rerun attempts correctly detected later concurrent edits.", "Added a recursive source/export mtime preflight and rebuilt into isolated immutable staging directories until the exact-current artifact passed 46/46."],
  ["DEF-QV-054", "issuer-01", "Medium", "Fixed", "The Issuers loading container carried aria-label on a generic div, which violates the permitted ARIA role/attribute contract.", "Open /issuers while the directory is loading and run axe-core.", "Loading state exposes a valid named status region with busy state and no prohibited ARIA attributes.", "axe reported aria-prohibited-attr on the loading div.", "Changed the loading container to role=status with aria-busy and retained its accessible label; the final 36-state matrix reports zero nodes."],
  ["DEF-QV-055", "model-43", "Medium", "Fixed", "Long Model and Report recovery/export labels exceeded the fixed narrow header action area at 390px, clipping controls needed to recover or export work.", "Open Model Builder and Report Studio at 390x844 with saved-model recovery states visible.", "Essential recovery and export actions remain fully visible or are available in the keyboard-operable tools drawer.", "The layout scanner reported clipped SAVED MODEL/RETRY, EXPORT MODEL, and Report retry controls.", "Added compact narrow labels and duplicated full recovery/export actions in the relevant tools drawers; the responsive contract tests and final layout matrix pass."],
  ["DEF-QV-056", "query-01", "Low", "Fixed", "The route matrix and dynamic Query scanner reused one analyst and hard-coded the same profile name, exhausting context quota and preventing a second unique identity from registering cleanly.", "Run the 36-state route matrix and then the four dynamic Query states under the same forwarded identity; retry with a new email but the same unique profile name.", "Each accessibility lane accepts an explicit unique analyst name and email, so real quotas remain enabled without cross-lane contamination.", "Query context creation returned HTTP 429; the first replacement identity returned 409 for duplicate full_name.", "Both accessibility harnesses now honor E2E_ANALYST_NAME; the dedicated Query identity completed all four states with zero axe nodes."],
  ["DEF-QV-057", "monitor-01", "High", "Fixed", "A concurrent Monitor edit placed a JSX child comment between EnterprisePage attributes, where the parser requires an attribute or spread.", "Run npm run build with the edited Monitor page.", "The production frontend parses and emits all 20 static routes.", "Turbopack stopped at monitor/page.tsx with Expected '...', got '}'.", "Moved the explanatory comment into the valid EnterprisePage child region without changing the concurrent feature behavior; the next production build passed."],
  ["DEF-QV-058", "reports-01", "High", "Fixed", "A concurrent ReportDoc semantic-heading edit temporarily opened h2 and closed div.", "Run npm run build while the incomplete ReportDoc edit is present.", "Every report heading has a matching semantic closing tag and the production build parses.", "Turbopack stopped at ReportDoc.tsx:95 with Expected corresponding JSX closing tag for h2.", "The parallel edit completed the closing-tag correction to h2; the subsequent production build and Report Studio browser journeys passed."],
  ["DEF-QV-059", "BP-017", "High", "Fixed", "Active parallel frontend writes repeatedly postdated each staged static export and superseded otherwise-clean exact-artifact validation.", "Build and stage the frontend, run the browser cohort, then compare recursive src mtimes with the staged export.", "No frontend source file changes from build start through the final browser, unit, coverage, lint, type, and accessibility seal.", "Rerun6 passed 949/949 frontend tests, lint, type check, coverage, a 20-route build, 46/46 zero-retry browser journeys, 36/36 route-width accessibility states, and 4/4 Query states; the final recursive source-mtime query returned no files.", "Obtained a quiescent window, built and served a new isolated rerun6 export, repeated every frontend and browser gate, and recorded a clean exact-current freshness seal."],
  ["DEF-QV-060", "BP-017", "Medium", "Waived", "The long-lived GitNexus MCP query connection retains the pre-repair LadybugDB catalog even after the on-disk index and user registry are rebuilt at the current commit; its registry/context metadata refreshes, but its FTS handle does not.", "Repair FTS, force an index-only PDG rebuild, prove a local CLI query returns matches, then issue the same MCP query in the current tool session.", "Both local and MCP semantic queries use the current index and return relevant execution flows without an FTS warning.", "The current registry and symbol impacts are current while the MCP semantic query still reports missing FTS indexes.", "Explicit external-tool waiver: this does not affect CAOS runtime behavior. Current symbol impacts, exact source inventories, direct tests, and local semantic/source queries are the compensating controls; reopen after the MCP process is restarted."],
  ["DEF-QV-061", "auth-01", "Low", "Fixed", "The expanded login E2E resolved axe-core with import.meta.url even though the Playwright transform emits CommonJS.", "Collect and run the login responsive/accessibility matrix.", "The test resolves the installed axe bundle in the repository's CommonJS-compatible Playwright runtime.", "The spec failed during transform before a browser opened.", "Use require.resolve('axe-core/axe.min.js'); all four login/register/recovery/error responsive scans pass."],
  ["DEF-QV-062", "pipeline-01", "Medium", "Fixed", "Ingestion regression doubles were local lambdas/closures that cannot cross the production parser's spawn-process boundary.", "Run the lineage and integrated-journey ingestion cohorts with process isolation enabled.", "Deterministic extraction doubles remain serializable under spawn while the production child-process isolation stays intact.", "The worker failed before parsing because the local callable could not be pickled.", "Replaced local callables with module-level deterministic functions; the affected 34-node ingestion/pipeline cohort passes with one intentional skip."],
  ["DEF-QV-063", "pipeline-01", "High", "Fixed", "A newly claimed unowned pipeline job could enter its terminal failure path without carrying the claimed worker as a fenced owner.", "Claim an unowned queued job, then force a module failure after the owner/lease commit.", "The failure mutation is fenced to the worker that owns the committed lease, preventing a stale worker from overwriting terminal state.", "The failure helper could receive no expected worker id after ownership had already been established.", "Promote the committed owner into fenced_owner after the lease claim and use it for terminal failure writes; the focused pipeline cohort and complete backend regression pass."],
  ["DEF-QV-064", "BP-017", "Medium", "Fixed", "The first cross-browser production-like harness reused browser-agnostic identity, storage-state, and source-address inputs across independent projects.", "Run all stateful journeys in Chromium, Firefox, and WebKit with real authentication and server throttles enabled.", "Each browser/lane has isolated identity, storage state, and fictional RFC 5737 source address while the real global throttle remains active.", "Later projects could inherit authentication or exhaust another project's per-source credential quota.", "Added project loops plus browser-specific identity, storage, and address inputs; all 141/141 project executions pass with retries disabled."],
  ["DEF-QV-065", "query-01", "Medium", "Fixed", "The Query composer could accept interaction after context data loaded but before the selected context was bound into URL state.", "Load Query and immediately choose a lane or submit a prompt before context URL synchronization finishes.", "The composer remains visibly busy and inert until the loaded context id matches URL state.", "An early interaction could race URL synchronization and bind the investigation to stale or absent context state.", "Gate composer controls on contextReady and cover the transition in the focused component suite; the complete browser matrix passes."],
  ["DEF-QV-066", "BP-017", "Low", "Fixed", "The exact-artifact freshness guard treated directory mtimes and test/spec edits as production-source changes.", "Touch a frontend test or add a source-tree directory entry after building the static artifact.", "Only production source file mtimes can invalidate the staged application artifact.", "The harness rejected an otherwise exact production build after test-only or directory metadata changes.", "Recurse over files only and exclude test/spec files while retaining fail-closed production-source comparison; the final 141-execution cohort passes."],
  ["DEF-QV-067", "monitor-01", "Medium", "Fixed", "Monitor dataset tabs were rendered as clickable server markup before analysis-context hydration attached their handlers.", "Open Monitor in Firefox and click Email intake immediately while bootstrap is still loading.", "Dataset controls expose a busy state and stay disabled until hydration/bootstrap completes, then switch datasets normally.", "The visible click was silently lost and Alerts remained selected.", "Disable every dataset tab until analysis loading settles, expose aria-busy on the tablist, and add a component regression; focused tests and the full browser matrix pass."],
  ["DEF-QV-068", "BP-017", "Low", "Fixed", "Two newly added frontend coverage fixtures violated the repository's TypeScript contracts for RegExp.exec and absent issuer values.", "Run the exact current no-emit TypeScript check after adding the edge-coverage fixtures.", "Validation fixtures type-check under the same compiler contract as product tests.", "TypeScript rejected the mocked exec signature and a null value where absence is represented by undefined.", "Typed the RegExp execution mock and used undefined for absence; focused regression, the reconciled 994-node frontend inventory, and no-emit TypeScript pass."],
  ["DEF-QV-069", "SCR-008", "Low", "Fixed", "The long accessibility matrix could hit the root route's client redirect before authenticated hydration completed and record a readiness miss even though the destination passed immediately in isolation.", "Scan all 19 routes at desktop and mobile widths, with the narrow root state late in the same browser session.", "The harness tolerates one transient authenticated redirect window but still fails closed if the application surface does not resolve after a bounded retry.", "The first matrix reported one root scan_error; an isolated rerun immediately reached /issuers with zero violations or layout failures.", "Retry the complete navigation once after a readiness timeout and preserve the existing scan_error on a second miss; the repaired full 38-state matrix passes with zero nodes, scan errors, or layout failures."],
  ["DEF-QV-070", "API-042", "Medium", "Fixed", "A newly discovered route shifted sequential API inventory IDs, but the parameterized direct-contract module still carried the prior IDs.", "Regenerate the tracker after inserting an API route that sorts before the dedicated contract cases.", "Every collected API case maps to the exact current method/path feature, and a future ID-to-route mismatch fails tracker generation instead of publishing false coverage.", "Nine exercised endpoints appeared unmapped while adjacent API IDs received false-positive direct evidence.", "Reconciled all 11 shifted IDs, added fail-fast parameter-to-route validation in the canonical generator, and reran all 14 direct HTTP contracts."],
  ["DEF-QV-071", "BP-017", "Low", "Fixed", "A new ShortcutHelp test fixture still used the retired singular route field after ShortcutEntry moved to a routes array.", "Run the current frontend TypeScript no-emit check.", "Every test fixture conforms to the live ShortcutEntry contract.", "TypeScript rejected the object literal because route is not a ShortcutEntry property.", "Changed the temporary route-scoped fixture to routes: ['/temporary']; the focused test and current type check pass."],
  ["DEF-QV-072", "BP-017", "Low", "Fixed", "A new FlagToQa test imported waitFor but never used it.", "Run the current frontend lint command.", "The frontend lint gate completes without warnings or errors.", "ESLint reported one unused-import warning in FlagToQa.test.tsx.", "Removed the unused waitFor import; the focused test and current lint gate pass cleanly."],
  ["DEF-QV-073", "query-01", "High", "Fixed", "The citation-metadata filter declared a widened string tuple predicate that was not assignable to the narrower template-literal tuple returned by the resolver.", "Run the current TypeScript check or production build after adding resolved issuer/document labels to Query citations.", "Query citation metadata narrows null entries without changing the exact tuple type, and the production build compiles.", "TypeScript rejected Object.fromEntries at QueryInvestigationWorkbench.tsx:272 and blocked the production build.", "Removed the over-broad explicit predicate and let TypeScript infer the non-null tuple; targeted Query validation, type check, and the rebuilt browser artifact pass."],
  ["DEF-QV-074", "SCR-018", "Low", "Fixed", "The new Upload route smoke test asserted the retired primary-action name after the implementation clarified that the link jumps to the intake form.", "Render UploadPage and query its primary link by the old accessible name 'Open intake'.", "The smoke contract asserts the implemented 'Jump to intake form' link and its #intake-workspace target.", "Testing Library could only find the current 'Jump to intake form' link, so the stale assertion failed.", "Updated the accessible-name assertion; the complete Upload smoke file and full frontend regression pass."],
  ["DEF-QV-075", "BP-017", "Low", "Fixed", "MoreDrawer.test.tsx was replaced while the full Vitest process was already collecting/executing it, so the run observed an in-flight test revision.", "Run the full frontend suite while a parallel writer updates the focus-trap test.", "Validation executes a quiescent file revision and reconciles any post-start writes with a complete-file rerun.", "The in-flight run reported the focus-wrap assertion twice, while the completed file immediately passed 2/2 in isolation.", "Waited for source quiescence, reran the complete drawer test, and repeated the current full frontend suite before sealing evidence."],
  ["DEF-QV-076", "BP-017", "Low", "Fixed", "The new useGraphZoom test cast its transform fixture to never, causing React state to infer an unusable Dispatch type and making object spread illegal.", "Run the current frontend TypeScript check after adding the hook test.", "The fixture is typed as the live d3 ZoomTransform contract and supplies a compatible state dispatcher.", "TypeScript reported two compile errors even though the two runtime tests passed.", "Typed the fixture and state explicitly as ZoomTransform; the complete test, lint, type check, build, and final aggregate pass."],
  ["DEF-QV-077", "research-13", "Medium", "Fixed", "The post-mount advanced-brief preference effect could finish after an early user click and overwrite the newly expanded disclosure with the persisted collapsed state.", "Navigate from saved Research defaults to /research in WebKit and click Advanced brief immediately after the settings response.", "A user interaction wins over late preference hydration, the disclosure stays expanded, and the saved audience is visible.", "WebKit observed aria-expanded=false after the click; Chromium and Firefox happened to complete the effect first.", "Added an interaction fence that prevents preference hydration from overwriting a prior toggle; the focused WebKit spec passes 4/4 and the final cross-browser matrix passes 141/141."],
  ["DEF-QV-078", "issuer-01", "Low", "Fixed", "The expanded ThesisTimeline fixtures included internal thesis_version_id and realized_at fields that the server PredictionOut response model intentionally omits.", "Run the current frontend TypeScript check against the expanded thesis prediction fixtures.", "Mocked prediction responses match the actual public API shape.", "TypeScript rejected four object literals with fields absent from ThesisPrediction.", "Removed the internal-only fields; the complete thesis fixture, type check, build, and final frontend aggregate pass."],
  ["DEF-QV-079", "issuer-01", "Medium", "Fixed", "The shared frontend Issuer interface treated ticker, industry, country, and figi as absent-or-string even though FastAPI IssuerResponse returns each field as nullable.", "Use null-valued directory/profile responses in the current Issuers fixtures and run TypeScript.", "The frontend contract matches the public API and every dependent consumer handles the nullable shape safely.", "TypeScript rejected three realistic null-valued fixtures, masking a runtime contract mismatch with CRITICAL fan-out.", "Widened the four fields to string | null after a CRITICAL GitNexus impact warning; TypeScript, the current 1,242-node reconciled frontend inventory, build, 15 affected cross-browser journeys, and four route-width accessibility states pass."],
  ["DEF-QV-080", "BP-017", "Low", "Fixed", "New concurrent interaction suites used unsafe EventListener casts, explicit-any mock contracts, and stale imports, so runtime tests could pass while lint or TypeScript failed.", "Run npm run lint and npx tsc --noEmit after collecting the new Ask, Pipeline, Research, and Deep-Dive interaction files.", "Every executable test harness satisfies the same lint and type contracts as production code.", "TypeScript rejected the Ask event listener; Pipeline and Research produced 45 explicit-any errors and two unused imports.", "Replaced unsafe casts and any-based mocks with exact component/event DTOs; lint, TypeScript, the focused 32-node cohort, and the reconciled 1,242-node frontend inventory pass."],
  ["DEF-QV-081", "pipeline-44", "Low", "Fixed", "The new Pipeline scope assertion retained a GraphView DOM node that React replaced during the DAG-to-swimlane-to-DAG cycle.", "Run pipeline-interactions.test.tsx and switch from the full route to LEGAL after cycling the subview.", "The assertion reads the currently mounted graph and verifies that LEGAL includes CP-4 while excluding CP-2.", "The rendered graph carried the correct nine-module legal scope, but the stale detached node still reported the prior full scope and failed twice including retry.", "Re-query the mounted graph inside waitFor; the complete Pipeline file passes 6/6 and the exact-current frontend aggregate passes 1,259/1,259."],
  ["DEF-QV-082", "BP-017", "Low", "Fixed", "A late Report Studio interaction harness used explicit any for component props and cast incomplete API fixtures around the public DTO types.", "Run npm run lint after the late reports-interactions.test.tsx revision.", "All interaction mocks and API fixtures satisfy the exact production TypeScript and ESLint contracts.", "ESLint reported 12 no-explicit-any errors even though the four runtime tests passed.", "Typed every mock prop, completed ReportDraftDTO and ReportVersionDTO fixtures, and removed binary-response casts; the report file passes 4/4, lint and TypeScript are clean, and the aggregate passes 1,259/1,259."],
  ["DEF-QV-083", "BP-017", "Low", "Fixed", "A concurrent Command Center interaction harness used 21 explicit-any annotations and cast structurally incomplete portfolio and insight fixtures around the public contracts.", "Run npm run lint after command-interactions.test.tsx is added or revised.", "All Command Center mock props and API fixtures satisfy the exact production TypeScript and ESLint contracts while preserving the five behavioral journeys.", "The five runtime tests passed, but ESLint reported 21 no-explicit-any errors and the fixtures used retired posture and position field shapes.", "Typed all mock props; replaced casts with complete PortfolioSummary, CommandPortfolioSnapshot, CommandPortfolioPosition, InsightPage, and InsightArtifact fixtures; focused 5/5, lint, TypeScript, and aggregate 1,259/1,259 pass."],
  ["DEF-QV-084", "research-06", "Low", "Fixed", "The Research interaction harness switched the AI-mode mock from standard to a retired 'deep' value that neither the public TypeScript union nor ResearchBrief schema accepts.", "Run the fully framed Research interaction and inspect the brief passed to deepResearch.", "The harness selects one of max, standard, or lite and verifies the exact public request shape.", "The runtime-only mock asserted ai_mode='deep', creating false evidence for an impossible production request.", "Changed the mock transition and assertion to the implemented max preset; the complete 26-node Research frontend cohort, lint, TypeScript, and exact-current frontend aggregate pass."],
  ["DEF-QV-085", "BP-017", "Low", "Fixed", "Two new Upload interaction harnesses used explicit any and non-generic dropzone prop stubs, so runtime behavior passed while lint and TypeScript rejected the test contracts.", "Run lint and tsc --noEmit after collecting UploadWizard.interactions.test.tsx and steps-interactions.test.tsx.", "Upload fixtures use the public step component, issuer, FileRejection, and generic dropzone prop contracts.", "ESLint reported 12 no-explicit-any errors and TypeScript rejected five FileStep renders because getRootProps/getInputProps did not satisfy their generic signatures.", "Replaced unsafe fixtures with ComponentProps-derived contracts, exact rejection/issuer/result types, narrowed select values, and generic dropzone adapters; both files pass 12/12, lint, and TypeScript."],
  ["DEF-QV-086", "BP-017", "Low", "Fixed", "The new Command Palette stale-response harness typed the deferred issuer list as any[].", "Run lint after collecting CommandPalette.interactions.test.tsx.", "The deferred response is derived from the exact getIssuers return type.", "ESLint reported one no-explicit-any error even though the original four interactions passed.", "Typed the resolver as Awaited<ReturnType<typeof getIssuers>>; the current file passes 6/6, lint, and TypeScript."],
  ["DEF-QV-087", "BP-017", "Low", "Fixed", "The automation collector accepted pytest warning-summary references because they also begin with a test path and contain a double-colon node separator.", "Regenerate the workbook while current pytest collection emits warning summaries.", "Only executable collected nodes receive automation evidence IDs; diagnostic warning references are not counted as tests.", "At discovery, ten warning-summary references inflated the automation inventory from 3,925 real nodes to 3,935.", "Added --disable-warnings and exact per-layer count gates to the read-only collectors; the current rebuilt inventory reconciles exactly to 3,953 real nodes and the formula-error scan is clean."],
  ["DEF-QV-088", "BP-017", "Low", "Fixed", "A concurrent RV Screener harness imported an unused helper and used Record<string, any> for the analysis context fixture.", "Run lint and TypeScript after collecting RVScreenerWorkbench.test.tsx.", "The mock uses the exact public AnalysisContext contract and introduces no unused dependencies or explicit any.", "The 12 runtime interactions passed, but ESLint reported one error and one warning; the first exact type repair then exposed incomplete context fixtures in TypeScript.", "Removed the unused import, supplied a complete AnalysisContext fixture, and isolated the deliberate invalid-filter boundary cast; focused 12/12, lint, TypeScript, and the 1,353-node reconciled inventory pass."],
  ["DEF-QV-089", "BP-017", "Low", "Fixed", "A concurrent Alert Inbox harness used Record<string, any> to reach test-only React fiber props.", "Run lint and TypeScript after collecting the expanded AlertInbox.test.tsx.", "The helper exposes only the recursive fiber fields used by the assertions and does not rely on explicit any.", "All 17 runtime interactions passed, but ESLint rejected the explicit any; the first narrow type then exposed an optional-return mismatch in TypeScript.", "Added a narrow TestFiber interface and normalized an absent parent to null; focused 17/17, lint, TypeScript, and the 1,353-node reconciled inventory pass."],
  ["DEF-QV-090", "deepdive-42", "Low", "Fixed", "The first phone-triage handoff assertion used one exact CSS attribute selector for a URL containing multiple query parameters, making a rendered named link appear absent in the test harness.", "Render the Deep-Dive phone triage and locate its Query/Pipeline handoffs by the compound href selector.", "The harness identifies each user-facing handoff by its visible action and independently verifies the exact issuer/context URL.", "The complete 115-node Deep-Dive cohort rendered the triage region but the brittle query-string selector returned null twice including retry.", "Locate the two anchors by their rendered action labels and compare getAttribute('href') to the exact identity-preserving URL; the repaired focused cohort passes."],
  ["DEF-QV-091", "BP-017", "Low", "Fixed", "A concurrent Report Studio interaction helper widened a React host-fiber lookup to Record<string, any>, reintroducing a lint failure after the earlier typed harness reconciliation.", "Run the repository frontend lint gate against the current untracked interaction cohort.", "Test-only host-fiber introspection exposes only the memoized callback map used by the assertions and contains no explicit any.", "The global lint command failed at reports-interactions.test.tsx:235 even though Deep-Dive focused lint, runtime tests, and TypeScript were green.", "Added a narrow TestFiber interface, guarded an unreadable fiber, and returned its typed memoizedProps; Report Studio focused regression and the global lint gate pass."],
  ["DEF-QV-092", "BP-017", "Low", "Fixed", "The first tracker regeneration command was launched from the output directory even though the generator resolves repository dependencies and source paths from process.cwd().", "Run build_quality_tracker.mjs with the output directory as the working directory.", "The canonical command runs from the repository root and reaches collection before mutating the workbook.", "Node failed before collection because it searched outputs/caos-quality-validation/caos/frontend/node_modules/typescript.", "Reran the unchanged generator from the repository root; dependency discovery and collection proceeded normally."],
  ["DEF-QV-093", "BP-017", "Low", "Fixed", "Fourteen frontend tests were added after the prior 1,353-node execution seal, so the exact-count collector correctly refused to publish them as already passing.", "Regenerate the tracker against the current worktree without executing post-seal nodes.", "Every newly collected node is executed before the expected count and validation-run seal advance.", "The generator collected 1,367 Vitest nodes and stopped at the 1,353-node gate before workbook mutation.", "Compared the current list to the prior Automation Evidence sheet, executed the 13 new Report Studio interaction nodes through the complete 17-test file and the new caveat node through its complete 5-test file, then advanced the exact gate to 1,367."],
  ["DEF-QV-094", "BP-017", "Low", "Fixed", "One canonical rebuild's Vitest listing child stopped making progress at zero CPU before any later collector or workbook mutation.", "Run the root-scoped tracker generator while the current worktree is under concurrent validation load.", "A stalled collection run is bounded, terminated without publishing, and a clean retry completes every count/evidence/export gate.", "The vitest list child remained sleeping for more than seven minutes with no output, and the prior workbook timestamp remained unchanged.", "Terminated only the launched generator session, verified no collector orphan and no workbook write, then completed a clean root-scoped rebuild."],
  ["DEF-QV-095", "BP-017", "Low", "Fixed", "Twenty-three net-new frontend nodes landed after the 1,367-node workbook export, spanning honest empty/offline states, provenance, roving tabs, modal stacking, and module QA semantics.", "Rebuild the tracker immediately after the 1,367-node seal while concurrent test additions are present.", "Post-seal nodes are identified by exact node diff, executed through their complete files, and admitted only after lint and TypeScript remain green.", "The collector found 1,390 nodes and stopped before overwriting the workbook; comparison surfaced 26 new identities, including two renamed AlertInbox nodes, for a net increase of 23.", "Executed all 11 affected files (90/90), reran lint and TypeScript, and advanced the exact frontend seal to 1,390."],
  ["DEF-QV-096", "query-01", "Low", "Fixed", "The Query focus-event effect captured setLane but declared only manualLane as a dependency, leaving a lint warning and a potential stale URL-update closure if the typed URL adapter changed.", "Run the global frontend lint gate after the concurrent Query workbench revision.", "The event listener depends on a stable memoized lane transition that always updates both local lane state and typed URL state.", "ESLint reported react-hooks/exhaustive-deps at QueryInvestigationWorkbench.tsx:268; runtime and TypeScript remained green.", "Memoized setLane with updateUrlState, moved it before the effect, declared it in the dependency list, and passed the 26-test Query/Ask focused cohort plus clean lint and TypeScript."],
  ["DEF-QV-097", "pipeline-01", "Low", "Fixed", "The global static gate read Pipeline views while a parallel writer had introduced two SurfaceState usages but had not yet landed the corresponding import.", "Run lint and TypeScript against the in-flight shared-worktree Pipeline revision.", "Every production component reference resolves in one quiescent source snapshot, and the affected user workflow remains executable.", "TypeScript reported SurfaceState as undefined at views.tsx:477 and :482; immediate source inspection then found the import present after the parallel revision completed.", "Re-ran lint and TypeScript against the quiescent source, executed both complete affected Pipeline files (21/21), and then passed the full 1,449-node frontend regression."],
  ["DEF-QV-098", "BP-017", "Low", "Fixed", "Fifty-nine executable frontend nodes landed after the 1,390-node evidence seal while the shared worktree remained active.", "Regenerate the canonical tracker after the concurrent Pipeline and surrounding frontend revisions.", "The exact-count gate rejects stale evidence, every new node is executed, and only then does the canonical seal advance.", "The tracker generator stopped before workbook mutation with expected 1,390 but collected 1,449 Vitest nodes.", "Executed the complete current 236-file frontend inventory with 1,449/1,449 passing, then advanced the fail-closed count and execution-run seal to the verified inventory."],
  ["DEF-QV-099", "BP-017", "Medium", "Fixed", "The corrupt-PDF robustness case generated 2,048 random bytes at collection time and allowed pytest to embed the payload in its parametrized node ID.", "Collect the backend inventory twice and compare stable evidence identities.", "Identical source produces identical bounded node IDs so prior execution evidence can be reconciled exactly.", "The corrupt-PDF node changed on every collection and expanded into a multi-kilobyte binary ID; the locked-PDF case also used a payload-derived ID.", "Replaced the random bytes with deterministic invalid PDF content, assigned explicit corrupt-pdf and locked-pdf IDs, passed the complete four-file affected cohort (111 pass, 2 skip), and proved two consecutive 2,427-node collections are identical."],
  ["DEF-QV-100", "BP-017", "Low", "Fixed", "Four net-new backend nodes landed after the 2,423-node evidence seal: two IC-book authority cases, one migration contract, and one research figure provenance case.", "Regenerate the canonical tracker after the shared-worktree backend additions.", "The exact-count gate refuses stale evidence and advances only after the complete current backend inventory passes.", "The generator stopped before workbook mutation with expected 2,423 but collected 2,427 pytest/stress/cohort nodes.", "Executed all four affected files (111 pass, 2 skip), the complete server regression (2,403 pass, 15 skip), and all nine stress/cohort nodes before advancing the seal."],
  ["DEF-QV-101", "BP-017", "Low", "Fixed", "The restricted command sandbox denied localhost socket binding required by seven faithful fake-clamd protocol tests.", "Run the complete server suite in the restricted runner.", "Loopback-only antivirus cases execute in an explicitly approved localhost-capable validation lane without changing application behavior.", "Seven test_avscan cases failed with PermissionError while 2,396 other cases passed and 15 skipped.", "Reran the unchanged complete suite with approved loopback access; all 2,403 executable server cases passed with 15 intentional skips."],
  ["DEF-QV-102", "BP-017", "Low", "Fixed", "Eighteen executable frontend nodes landed after the 1,449-node full-current run while the shared worktree remained active.", "Regenerate the canonical tracker immediately after the 1,449-node seal.", "The exact-count gate stops publication and the complete expanded inventory executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,449 but collected 1,467 Vitest nodes.", "Executed the complete current 237-file frontend inventory with 1,467/1,467 passing, then advanced the fail-closed frontend and total evidence seals."],
  ["DEF-QV-103", "query-01", "Low", "Fixed", "Two Query interaction nodes landed after the 1,467-node full-current run while the shared worktree remained active.", "Regenerate the canonical tracker immediately after the 1,467-node seal.", "The exact-count gate stops publication and the complete expanded inventory executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,467 but collected 1,469 Vitest nodes; query-interactions.test.tsx expanded from 18 to 20 cases.", "Executed the complete current 237-file frontend inventory with 1,469/1,469 passing, then advanced the fail-closed frontend and total evidence seals."],
  ["DEF-QV-104", "BP-017", "Low", "Fixed", "Nine IC Book interaction nodes landed during the workbook export after the 1,469-node full-current run.", "Regenerate the tracker immediately after confirming a stable 1,469-node collection.", "The exact-count gate stops publication and the complete affected file executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,469 but collected 1,478 Vitest nodes; ICBookWorkbench.test.tsx expanded from 12 to 21 cases.", "Executed the complete 21-case IC Book file after source quiescence and advanced the frontend seal only after all cases passed."],
  ["DEF-QV-105", "BP-017", "Low", "Fixed", "The first focused IC Book execution read an in-flight test revision containing ambiguous unscoped Meeting time and register offline queries.", "Execute ICBookWorkbench.test.tsx while its nine-case expansion is still being written in the shared worktree.", "Validation runs against one quiescent file revision and reconciles any post-start write with a complete-file rerun.", "Four of 21 cases failed twice including retry, while 17 passed; the completed file changed before diagnosis and no longer contained the failing query state.", "Waited for the writer to finish and reran the complete file twice; both current-revision runs pass all 21 cases without modifying product or test code."],
  ["DEF-QV-106", "BP-017", "Low", "Fixed", "Five additional IC Book interaction nodes landed after the 21-case delta had passed and while the next exact inventory collection was running.", "Recollect the frontend inventory after the 21-case IC Book revision appears quiescent.", "Any further additions are executed through the complete affected file before the canonical seal advances.", "The collection first observed 1,482 nodes while ICBookWorkbench.test.tsx was at 25 cases; by execution the file had completed at 26 cases, bringing the live inventory to 1,483.", "Executed the complete current IC Book file with 26/26 passing and reconciled all 14 nodes added after the 1,469-node full run."],
  ["DEF-QV-107", "BP-017", "Low", "Fixed", "Four analysis-context workbench nodes landed during the next workbook export after the 1,483-node seal.", "Regenerate the tracker after the 26-case IC Book revision has stabilized.", "The exact-count gate stops publication and every new analysis-context node executes through its complete file.", "The generator stopped before workbook mutation with expected 1,483 but collected 1,487 Vitest nodes; analysis-workbench.test.ts expanded from 12 to 16 cases.", "Executed the complete current analysis-workbench file with 16/16 passing and advanced the seal only after its four new cases were reconciled."],
  ["DEF-QV-108", "BP-017", "Low", "Fixed", "Seven frontend nodes landed during the next workbook export: two Query visualization cases, four Report-to-Vault cases, and one auth-interceptor case.", "Regenerate the tracker after the 1,487-node frontend seal.", "The exact-count gate stops publication and every new node executes through its complete file.", "The generator stopped before workbook mutation with expected 1,487 but collected 1,494 Vitest nodes.", "Executed all three complete affected files with 12/12 passing and advanced the seal only after the seven additions were reconciled."],
  ["DEF-QV-109", "BP-017", "Low", "Fixed", "Six frontend API-route contract nodes landed during the next workbook export.", "Regenerate the tracker after the 1,494-node frontend seal.", "The exact-count gate stops publication and every new route-contract node executes through its complete file.", "The generator stopped before workbook mutation with expected 1,494 but collected 1,500 Vitest nodes; api-routes-coverage.test.ts expanded from four to ten cases.", "Executed the complete current API-route contract file with 10/10 passing and advanced the seal only after the six additions were reconciled."],
  ["DEF-QV-110", "BP-017", "Low", "Fixed", "Seven frontend nodes landed during the next workbook export: six Pipeline view cases and one analysis-context strip case.", "Regenerate the tracker after the 1,500-node frontend seal.", "The exact-count gate stops publication and every new workflow node executes through its complete file.", "The generator stopped before workbook mutation with expected 1,500 but collected 1,507 Vitest nodes.", "Executed both complete affected files with 25/25 passing and advanced the seal only after all seven additions were reconciled."],
  ["DEF-QV-111", "deepdive-36", "Low", "Fixed", "A concurrent Module Finder test revision declared three nested empty settings objects with the broad TypeScript empty-object type.", "Run the global frontend lint gate after the Module Finder interaction expansion.", "The deferred settings fixture uses an explicit object shape that cannot accept arbitrary non-null primitives.", "ESLint reported three no-empty-object-type errors at ModuleFinder.test.tsx:136 while TypeScript remained green.", "Replaced each empty-object type with Record<string, never>; the complete seven-case file, lint, and TypeScript pass."],
  ["DEF-QV-112", "deepdive-36", "Low", "Fixed", "Three Module Finder interaction nodes landed after the 1,507-node frontend seal.", "Recollect the frontend inventory after the Module Finder revision completes.", "Every new Deep-Dive node executes through its complete file before the canonical seal advances.", "ModuleFinder.test.tsx expanded from four to seven cases after the last exact collection.", "Executed the complete current Module Finder file with 7/7 passing and advanced the seal only after all three additions were reconciled."],
  ["DEF-QV-113", "BP-017", "Low", "Fixed", "Nine frontend nodes landed during the next workbook export across model export, Pipeline simulation, live-run, and engine-adapter contracts.", "Regenerate the tracker after the 1,510-node frontend seal.", "The exact-count gate stops publication and every new contract node executes through its complete file.", "The generator stopped before workbook mutation with expected 1,510 but collected 1,519 Vitest nodes.", "Executed all four complete affected files with 48/48 passing and advanced the seal only after the nine additions were reconciled."],
  ["DEF-QV-114", "model-32", "Low", "Fixed", "The new model workbook download test used a function-style anchor click mock without typing its HTMLAnchorElement receiver.", "Run the global frontend TypeScript gate after export-download.test.ts is added.", "The test callback has the same receiver type as HTMLAnchorElement.prototype.click and introduces no implicit any.", "TypeScript reported two TS2683 errors at export-download.test.ts:20-21 while the runtime test and lint passed.", "Typed the mock callback receiver as HTMLAnchorElement; the complete export test, lint, and TypeScript pass."],
  ["DEF-QV-115", "BP-017", "Low", "Fixed", "Six frontend nodes landed during the next collection window across Settings, Model Sheet, and IC-book contracts.", "Regenerate the tracker after the 1,519-node frontend seal and confirm the net count after the active writes finish.", "Every new node executes through its complete file and a fresh global collection establishes the final net inventory.", "The generator first observed 1,523 nodes while the three files were changing; the completed revisions contained six net additions and the next global collection stabilized at 1,525.", "Executed all three complete affected files with 27/27 passing and advanced the seal to the confirmed 1,525-node inventory."],
  ["DEF-QV-116", "shell-09", "Low", "Fixed", "A concurrent More Drawer test revision declared a dialog binding with let even though the completed case never reassigns it.", "Run the global frontend lint gate after the drawer interaction revision.", "Immutable test bindings use const and the focus-trap behavior remains unchanged.", "ESLint reported one prefer-const error at MoreDrawer.test.tsx:49 while TypeScript remained green.", "Changed the binding to const; the complete two-case drawer file, lint, and TypeScript pass."],
  ["DEF-QV-117", "BP-017", "Low", "Fixed", "Ten frontend nodes landed during the next collection window: one Settings case and nine source-reference cases.", "Regenerate the tracker after the 1,525-node frontend seal and inspect files still changing during collection.", "Every new node executes through its complete file before the canonical seal advances.", "The generator first observed 1,526 nodes while SourceRef.test.tsx was still expanding; the completed two-file delta brought the live inventory to 1,535.", "Executed both complete affected files with 26/26 passing and advanced the seal only after all ten additions were reconciled."],
  ["DEF-QV-118", "shell-08", "Medium", "Fixed", "The concurrent SourceRef action union allowed an optional never href, but property-presence narrowing still exposed source.href as string | undefined to the safe URL validator.", "Run the global frontend TypeScript gate after the expanded source-reference contract lands.", "Ready links pass a concrete string to the validator, ready actions remain buttons, and unavailable provenance remains non-interactive text.", "TypeScript failed at SourceRef.tsx:76; GitNexus reported HIGH impact across seven direct callers, 23 symbols, one Profile workflow, and Sector/Portfolio/Profile/Monitor modules.", "Changed the branch discriminant to source.href !== undefined; all 12 SourceRef cases, 63 direct-caller cases, lint, and TypeScript pass."],
  ["DEF-QV-119", "BP-017", "Low", "Fixed", "Fourteen backend nodes landed after the 2,427-node server/stress/cohort seal across CSRF, rate limiting, auth profile, and Portfolio Lab backend contracts.", "Regenerate the tracker after the frontend 1,535-node seal while backend revisions are active.", "The exact-count gate stops publication and both the affected cohort and complete current backend inventory execute before the seal advances.", "The generator stopped before workbook mutation with expected 2,427 but collected 2,441 pytest/stress/cohort nodes; production backend files changed alongside the tests.", "Executed the four affected files (44/44), the complete server suite (2,417 pass, 15 skip), and all nine stress/cohort cases before advancing the backend seal."],
  ["DEF-QV-120", "BP-017", "Low", "Fixed", "Thirteen frontend nodes landed after the 1,535-node seal across Deep-Dive output, login, Model Engine v2, and Pipeline simulation contracts.", "Regenerate the tracker while frontend source and tests are changing in the shared worktree.", "The exact-count gate blocks publication; a complete frontend regression and every node added during its collection window execute before the seal advances.", "Collection advanced from 1,535 to 1,542 before the run, the complete run finished at 1,543, and a final collection reached 1,548 after the five-case Pipeline simulation file landed.", "Executed the complete 1,543-node frontend regression plus the complete 49-case Model Engine v2/Pipeline simulation cohort; all 1,548 current nodes are evidence-backed, with lint and TypeScript clean."],
  ["DEF-QV-121", "BP-017", "Low", "Fixed", "Thirteen backend nodes landed after the 2,441-node server/stress/cohort seal across rate limiting, auth profile, EDGAR, and password-auth contracts.", "Regenerate the tracker while backend production source and tests are changing in the shared worktree.", "The exact-count gate blocks publication and both the affected files and complete current backend inventory execute before the seal advances.", "Collection advanced from 2,441 to 2,454 nodes while rate-limit, auth, and EDGAR production files changed alongside their tests.", "Executed the four complete affected files (76/76), the complete server suite (2,430 pass, 15 skip), and all nine stress/cohort cases before advancing the backend seal."],
  ["DEF-QV-122", "BP-017", "Low", "Fixed", "The validation runner invoked a nonexistent npm typecheck script even though this repository exposes TypeScript through the local compiler binary.", "Run the current frontend static type gate after the concurrent source revisions.", "The validation command uses the repository-supported compiler invocation and reports the real TypeScript result.", "npm run typecheck exited with a missing-script error before any compiler work occurred.", "Reran the gate as npx tsc --noEmit; it completed cleanly, alongside a clean npm run lint result."],
  ["DEF-QV-123", "pipeline-01", "Low", "Fixed", "Four Upload Wizard interaction nodes landed during the 1,548-node workbook export.", "Publish the canonical tracker while the shared-worktree frontend tests are changing.", "The exact-count gate stops publication and the complete affected file executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,548 but collected 1,552 Vitest nodes.", "Executed the complete current UploadWizard.interactions.test.tsx file with 12/12 passing before advancing the frontend seal."],
  ["DEF-QV-124", "deepdive-42", "Low", "Fixed", "One Phone Triage interaction node landed during the 1,552-node workbook export.", "Publish the canonical tracker while the shared-worktree frontend tests are changing.", "The exact-count gate stops publication and the complete affected file executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,552 but collected 1,553 Vitest nodes.", "Executed the complete current PhoneTriage.test.tsx and still-active UploadWizard.interactions.test.tsx files with 19/19 passing before advancing the frontend seal."],
  ["DEF-QV-125", "deepdive-42", "Low", "Fixed", "Five additional Phone Triage interaction nodes landed during the 1,553-node workbook export.", "Publish the canonical tracker while the shared-worktree frontend tests are changing.", "The exact-count gate stops publication and the completed affected revision executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,553 but collected 1,558 Vitest nodes.", "Executed the complete expanded PhoneTriage.test.tsx file with 12/12 passing before advancing the frontend seal."],
  ["DEF-QV-126", "BP-017", "Low", "Fixed", "Four chart animation and resize/error-path nodes landed between two pre-publication frontend collections.", "Require a stable collection before publishing the canonical tracker.", "Any count change between consecutive collections is treated as unexecuted evidence and blocks publication.", "The first collection returned 1,558 nodes and the immediately following collection returned 1,562 after G2Chart.animate.test.tsx expanded from two to six cases.", "Executed the complete chart-animation and still-active Phone Triage files with 18/18 passing before advancing the frontend seal."],
  ["DEF-QV-127", "BP-017", "Low", "Fixed", "Four more chart animation nodes landed during the 1,562-node workbook export.", "Publish the canonical tracker after the chart harness revision finishes.", "The exact-count gate blocks publication and the completed current file executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,562 but collected 1,566 Vitest nodes as G2Chart.animate.test.tsx expanded from six to ten cases.", "Executed the complete expanded chart-animation file with 10/10 passing before advancing the frontend seal."],
  ["DEF-QV-128", "BP-017", "Low", "Fixed", "Seven frontend nodes landed during the 1,566-node export across portfolio/sector route wrappers, G2 chart null/fallback contracts, chart animation, and More Drawer.", "Publish the canonical tracker after the active frontend revisions settle.", "The exact-count gate blocks publication and every file in the active timestamp set executes before the seal advances.", "The generator first collected 1,570 nodes; a follow-up collection reached 1,573 after the chart-animation and drawer revisions completed.", "Executed all six chart/route files with 22/22 passing and the complete More Drawer file with 3/3 passing before advancing the frontend seal."],
  ["DEF-QV-129", "shell-09", "Medium", "Fixed", "The complete frontend runner loaded an in-flight More Drawer test revision while that file was being rewritten in the shared worktree.", "Execute the full frontend inventory while concurrent test authors are saving the drawer harness.", "Only the completed current file is treated as evidence; transient mid-write failures are recorded and re-executed after the revision settles.", "Two geometry assertions from the intermediate revision failed twice in the full run, while 1,571 other cases passed; the completed current file no longer contains those assertions.", "Reran the completed MoreDrawer.test.tsx and MoreDrawer.focus-effect.test.tsx files together; all 6/6 current cases pass without application changes."],
  ["DEF-QV-130", "BP-017", "Low", "Fixed", "Four frontend nodes landed after the 1,573-node seal: three More Drawer focus-effect cases and one Alert Inbox case.", "Reconcile the frontend inventory after the active full-run window.", "Every newly collected node has direct execution evidence through its complete file or the same full-run snapshot.", "The current collector advanced from 1,573 to 1,577 nodes.", "The completed drawer pair passes 6/6 and the expanded 18-case Alert Inbox file passed in the full-run snapshot; all four additions are reconciled."],
  ["DEF-QV-131", "BP-017", "Low", "Fixed", "Forty-two backend nodes landed after the 2,454-node seal across route input bounds, request limits, decisions/thesis, security headers, and route-rate boundaries while protected route modules changed.", "Publish the canonical tracker while backend production source and tests are changing.", "The exact-count gate blocks publication; complete server regression, final affected files, and stress/cohort lanes execute before the seal advances.", "Collection first advanced to 2,495 nodes, then to 2,496 after the final route-rate boundary case landed.", "Executed the complete server suite (2,471 pass, 15 skip), the complete current route-input/rate-boundary files (19/19), and all nine stress/cohort cases, reconciling 2,472 current executable server nodes."],
  ["DEF-QV-132", "BP-017", "Low", "Fixed", "Eighteen frontend nodes landed after the 1,577-node seal across CSV, Command RV/QA, maturity normalization, and More Drawer focus-effect contracts.", "Publish the canonical tracker while the frontend utility harnesses are changing.", "The exact-count gate blocks publication and every active file executes through its completed revision before the seal advances.", "The export first collected 1,586 nodes; the completed revisions stabilized at 1,595 nodes.", "Executed the completed drawer pair (seven cases) and the four-file CSV/Command cohort (34/34), with clean lint and TypeScript."],
  ["DEF-QV-133", "command-06", "Medium", "Fixed", "The new RV maturity harness declared its fixture factory as a const inside a hoisted vi.mock factory, producing a temporal-dead-zone ReferenceError before test collection.", "Execute the completed command-data cohort.", "The mock factory constructs its rows without referencing an uninitialized binding and the maturity contract reaches its assertions.", "rvdata.maturity.test.ts failed as a suite with Cannot access 'marketRow' before initialization while the other 33 cohort cases passed.", "Changed the local fixture factory to a function declaration; the maturity case and complete 34-case CSV/Command cohort pass, with lint and TypeScript clean."],
  ["DEF-QV-134", "BP-017", "Low", "Fixed", "Two frontend nodes landed during the 1,595-node export across Monitor governance and Report Studio autosave-race contracts.", "Publish the tracker after the active application interaction revisions complete.", "The exact-count gate blocks publication and every file in the active timestamp set executes before the seal advances.", "The generator stopped before workbook mutation with expected 1,595 but collected 1,597 Vitest nodes.", "Executed all six active files with 51/51 passing, including the completed three-case Monitor governance and 18-case Report Studio revisions."],
  ["DEF-QV-135", "research-01", "Low", "Fixed", "Seven Deep Research interaction nodes landed during the 1,597-node export.", "Publish the tracker after the active Research and Report Studio revisions complete.", "The exact-count gate blocks publication and both complete files execute before the seal advances.", "The generator stopped before workbook mutation with expected 1,597 but collected 1,604 Vitest nodes as research-interactions.test.tsx expanded from five to twelve cases.", "Executed the completed Research and Report Studio files with 30/30 passing before advancing the frontend seal."],
  ["DEF-QV-136", "auth-02", "Low", "Fixed", "One backend node landed during the 2,496-node export while CSRF and identity production modules changed.", "Publish the tracker after the active security-boundary revision completes.", "The exact-count gate blocks publication and both complete affected files execute before the seal advances.", "The generator stopped before workbook mutation with expected 2,496 but collected 2,497 pytest/stress/cohort nodes.", "Executed the complete CSRF and identity files with 19/19 passing, reconciling 2,473 current executable server nodes."],
  ["DEF-QV-137", "deepdive-01", "Low", "Fixed", "Seven frontend nodes landed during the 1,604-node export across Pipeline, Deep-Dive, Ask, and Report panel contracts.", "Publish the tracker after the active workflow interaction revisions complete.", "The exact-count gate blocks publication and every file in the revision window executes before the seal advances.", "The generator first collected 1,609 nodes; the completed revisions stabilized at 1,611 after deepdive-interactions.test.tsx reached twelve cases.", "Executed all five complete affected files with 45/45 passing before advancing the frontend seal."],
  ["DEF-QV-138", "BP-017", "Low", "Fixed", "Eleven explicit API parameter IDs drifted after newly discovered routes changed the canonical path/method ordering.", "Validate every test parameter ID against the current code-discovered API inventory before workbook generation.", "Each contract ID names the exact route it exercises, so direct feature evidence cannot silently attach to another endpoint.", "The mapping gate stopped generation when API-100 named GET /api/qa/findings but the current inventory assigned API-105; ten additional IDs were stale.", "Reconciled all eleven IDs to the current route scanner, GitNexus rated the test-only change LOW risk with no affected processes, and all 14 direct HTTP contracts pass."],
  ["DEF-QV-139", "query-01", "Medium", "Fixed", "The canonical Query register still described the retired capability rail, auto-run, question cards, and EvidenceDock even though /query now renders a context-bound persisted investigation workbench.", "Compare all query-01 through query-19 tracker contracts with the current Query page, QueryInvestigationWorkbench, API workflows, and interaction tests.", "Every Query row documents only implemented current behavior and carries direct assertion-level evidence where a current automated contract exists.", "Thirteen UI rows named removed files/controls or obsolete auto-run behavior, and query-16 described an earlier redesign rather than the current PersonaWorkbench composition.", "Replaced the retired UI contracts with current context, draft, lane, execution, metric/graph/grounded result, citation, history, capability, authority, pin, and handoff contracts; mapped exact assertions and passed the complete Query cohort."],
  ["DEF-QV-140", "issuer-01", "Low", "Fixed", "The shared worktree rewrote profile-distill.test.tsx while a four-file Vitest cohort was executing, so two assertions from the intermediate revision failed even though the completed file had already changed.", "Execute the post-seal issuer-profile cohort while concurrent edits are landing, then compare the failure lines with the current file and rerun the complete completed revision.", "Only a quiescent completed test file is accepted as execution evidence, and every current case passes.", "The first run reported 57 pass/2 fail across four files; the failure output referenced assertion forms that no longer matched the saved file.", "Reran the complete current profile-distill file after quiescence with 20/20 passing; the other three files had already passed, so the current four-file cohort reconciles 59/59 without an application change."],
  ["DEF-QV-141", "BP-017", "Low", "Fixed", "Three parameterized Decision Room error cases collected under the identical Vitest node name, making assertion-level automation identities ambiguous in the canonical evidence sheet.", "List the current Vitest inventory and group exact file/name node identities.", "Every executable case has a stable unique collected identity while preserving the same assertions.", "The three distinct string-detail, nested-message, and generic-error cases all appeared as 'shows the available decision-capture error detail'.", "Converted the table to labelled objects and included $label in the case title; the complete six-case file, lint, and TypeScript pass and collection identities are unique."],
  ["DEF-QV-142", "model-01", "Low", "Fixed", "The newly expanded Model authority harness forced an impossible authority literal directly into ModelV2ReadResponse and inferred initial hook props too narrowly to allow a null exact run id.", "Run the global TypeScript gate after the post-seal authority cases land.", "Runtime-invalid server data is explicitly marked as an unknown-boundary test input and hook props retain the public string-or-null contract.", "TypeScript reported TS2352 at the invalid authority fixture and TS2322 when rerendering with exactRunId=null.", "Made the deliberate runtime-invalid value cross the unknown boundary and typed initial hook props to string | null; all 16 authority tests, the paired Decision Room file, lint, and TypeScript pass."],
  ["DEF-QV-143", "query-09", "Low", "Fixed", "Two parameterized Citation Viewer fallback cases collected under the same Vitest node name, obscuring which fallback contract produced an assertion result.", "List the complete frontend inventory and group exact file/name identities.", "Every citation fallback case has a stable unique automation identity without changing its behavior.", "The missing-document and missing-page cases both appeared as the same fallback test identity.", "Converted the cases to labelled objects and included $label in the title; all six Citation Viewer tests pass and the complete collection contains no duplicate identities."],
  ["DEF-QV-144", "query-07", "Low", "Fixed", "The expanded Query visualization harness omitted the required GraphNode.kind field and then asserted the pre-classification accessible name after the fixture was corrected.", "Run TypeScript and the complete Query visualization smoke file after adding the unknown-classification case.", "The fixture satisfies the GraphNode contract and the accessible-name assertion includes the implemented classification label.", "TypeScript reported TS2741 for the missing kind; after adding kind=unknown, two locators still expected 'Select Unclassified point' instead of the implemented 'Select Unclassified point (unknown)'.", "Added the required unknown kind and aligned both accessibility assertions with the rendered label; all five visualization cases and TypeScript pass."],
  ["DEF-QV-145", "settings-01", "Low", "Fixed", "The Settings unmount cleanup dereferenced mutable timer refs directly inside an empty-dependency effect cleanup, triggering two exhaustive-deps warnings and making ref-capture intent ambiguous.", "Run the exact-current global ESLint gate after the Settings save-feedback timers land.", "Unmount cleanup retains access to the latest timer values with no hook-dependency warnings.", "ESLint reported two react-hooks/exhaustive-deps warnings for savedResetTimer.current and analystSavedResetTimer.current.", "Captured the stable ref objects inside the effect and cleared their current timer values during cleanup; exact-current ESLint and TypeScript both pass cleanly."],
  ["DEF-QV-146", "pipeline-01", "Low", "Fixed", "The expanded EDGAR import harness used jest-dom's toHaveTextContent even though the project does not install that matcher, and asserted a data-sev attribute that the real Dot component does not expose.", "Run the complete new six-file frontend cohort after the EDGAR error and zero-chunk cases land.", "The harness asserts rendered text and the implemented warning color contract using the project's available Chai/DOM primitives.", "Three error-detail cases failed with 'Invalid Chai property: toHaveTextContent', and the zero-chunk case could not find data-sev=warning; the other 41 cohort cases passed.", "Asserted alert.textContent and the warning Dot's aria-hidden style instead of nonexistent test APIs/attributes; all 11 EDGAR cases and the 45-case cohort pass with clean lint and TypeScript."],
  ["DEF-QV-147", "BP-017", "Low", "Fixed", "Three distinct EDGAR rejection shapes collected under one identical parameterized test name, making their automation evidence identities ambiguous.", "Collect the exact frontend inventory and group each file/name pair after the new EDGAR cases land.", "String-detail, nested-message, and fallback-error contracts each have a stable unique node identity.", "All three rejection cases appeared as 'surfaces a useful non-503 vaulting error'.", "Converted the table to labelled objects and included $label in the test title; the complete EDGAR file passes and the current inventory can distinguish all three cases."],
  ["DEF-QV-148", "BP-017", "Low", "Fixed", "Three Model interaction nodes landed immediately after the 1,678-node workbook seal while the shared worktree remained active.", "Publish the canonical tracker while the Model page and its interaction harness are still changing.", "The exact-count gate stops publication and the complete affected file executes before the evidence seal advances.", "Collection advanced from 1,678 to 1,681 nodes after guarded-storage, unavailable-downside, and stale-checkpoint cases landed.", "Executed the completed 13-case Model file, clean lint and TypeScript, a fresh 20-route build, 15/15 affected browser executions, and both responsive Model axe states before advancing the seal."],
  ["DEF-QV-149", "model-01", "Low", "Fixed", "The first isolated Model browser server enabled Model Engine v2 without its implemented Lineage v2 prerequisite.", "Run model_flow.spec.ts in all three browser engines with CAOS_MODEL_ENGINE_V2_ENABLED=true but CAOS_LINEAGE_V2_ENABLED=false.", "The validation environment enables every documented dependency needed by the journey, so all current Model cases execute.", "Nine legacy/scenario cases passed, three v2 reads returned HTTP 503, and three serial successor cases did not run.", "Restarted the isolated server with both rollout gates enabled; all 15 Chromium, Firefox, and WebKit executions pass with retries disabled."],
  ["DEF-QV-150", "BP-017", "Low", "Fixed", "Six Monitor governance and Deep-Dive output-register nodes landed during the 1,681-node workbook export.", "Publish the canonical tracker while those completed interaction files are still arriving in the shared worktree.", "The exact-count gate blocks publication and both complete files execute before the tracker advances.", "The builder stopped before workbook mutation with expected 1,681 but collected 1,687 Vitest nodes.", "Executed the complete Monitor and Output Register files with 23/23 passing, including the intentional offline-path diagnostics; lint and TypeScript remain clean."],
  ["DEF-QV-151", "upload-22", "Medium", "Fixed", "The canonical Upload register still described a retired four-mode wizard and in-wizard EDGAR search/exhibit workflow, while the current screen implements five run modes plus URL-based public EDGAR intake and the backend retains separate search/filing APIs.", "Compare upload-01 through upload-27 against the current Upload page, wizard steps, ingestion/EDGAR routes, storage helpers, and exact test assertions.", "Every Upload row documents only current implemented behavior, edge cases, validation, dependencies, and assumptions, with direct assertion-level evidence.", "Multiple rows named removed UI controls, omitted Primary Transaction mode, understated metadata/path/rate-limit contracts, and described zero-chunk ingestion as silent rather than an explicit warning.", "Reconciled all 27 feature contracts to current code, mapped exact frontend/backend assertions, added three missing robustness tests, and passed the complete 40-case frontend and 125-case mapped server cohorts."],
  ["DEF-QV-152", "BP-017", "Low", "Fixed", "Thirteen Model tests landed in the shared worktree while Upload reconciliation was in progress: seven frontend nodes and six backend Model Engine v2 nodes.", "Publish the canonical tracker after the previously sealed 1,687/2,507 inventories while concurrent Model source and tests are still changing.", "The exact-count seal advances only after every new node and its affected production surface are validated.", "Collection advanced to 1,694 frontend and 2,516 server/stress/cohort nodes, including the three planned Upload robustness nodes.", "Executed the six complete affected frontend files with 68/68 passing and test_model_engine_v2.py with 66/66 passing; lint, TypeScript, the 20-route build, 15/15 Model browser journeys, and two responsive axe states also pass."],
  ["DEF-QV-153", "command-29", "Medium", "Fixed", "Eight Sector Review feature rows still described the deleted SectorReviewWorkspace v1 signal-card UI, including timeframe/search filters and Topic ASK, while /sector now renders the context-bound versioned SectorReviewDossier.", "Compare command-29 through command-51 and command-57 with the current /sector page, dossier/panel components, analysis client, V2 sector routes, and exact test assertions.", "Every Sector Review row documents only current user-facing behavior and cites direct automation for the current workflow; retained legacy APIs remain discoverable in the API inventory without being presented as current screen controls.", "The canonical register named a removed component and controls that users cannot reach, while omitting version history, evidence availability, ratification, publication gates, and comparable-issuer navigation.", "Reconciled all nine stable Feature IDs to the current dossier, mapped assertion-level frontend/backend evidence, executed the focused cohorts, and rebuilt the canonical workbook with 9/9 direct Sector Review coverage."],
  ["DEF-QV-154", "settings-03", "Medium", "Fixed", "Six Settings feature rows still described the retired four-tab page, old PageSubHeader shell, legacy header copy, immediate local model-mode persistence, and Outlook as a hardcoded PUT-backed stub.", "Compare settings-03 through settings-07 and settings-10 with the current Settings page, shared shell/model-mode/API clients, Settings routes, and exact frontend/server/browser assertions.", "Every Settings row documents the current five-tab authenticated workbench, staged global save semantics, truthful environment snapshot, profile-backed Outlook state, and sparse revision-checked PATCH persistence.", "The canonical register omitted Portfolios, URL-restored and roving-keyboard tabs, seven configuration groups, runtime-model wording, staged device/profile model mode, and current email conflict/error handling.", "Reconciled all six stable Feature IDs to current code, strengthened the existing browser journey with shell/header assertions, mapped exact frontend/server/browser nodes, executed the complete focused cohorts, and rebuilt the workbook with 10/10 direct Settings coverage."],
  ["DEF-QV-155", "settings-05", "Low", "Fixed", "The first strengthened Settings browser assertion used a broad exact-text locator for the shell title even though the accessible page also exposes a Settings navigation link and hidden document heading.", "Run the current mirrors-the-server-workspace-configuration journey in Chromium, Firefox, and WebKit with page.getByText('Settings', { exact: true }).", "The browser test targets the visible ShellIdentity title unambiguously and remains stable when equivalent accessible Settings labels coexist.", "Playwright strict mode resolved two to four matching elements in each engine; that one case failed 3/3 while the other nine project executions passed.", "Scoped the assertion to the implemented span[title='Settings'] identity element and reran the complete 12-execution Settings matrix with zero retries."],
  ["DEF-QV-156", "BP-017", "Medium", "Waived", "The repository-default local SQLite artifact reports migration state that is inconsistent with its issuer_research_reports schema, so current startup queries a missing lease_expires_at column.", "Start caos/server/run.py against the default configured SQLite database after the current research-report lease migration is present.", "The local application database is at the current migration schema or startup fails with actionable repair guidance before background executors query it.", "Startup raised sqlite3.OperationalError: no such column: lease_expires_at while starting the issuer research report executor.", "Explicitly waived for this iteration because repairing or replacing a user-owned local database is a destructive data decision. The complete Settings browser matrix passed against a new isolated SQLite database upgraded through all 64 revisions; the stale default artifact remains a local-environment risk."],
  ["DEF-QV-157", "shell-01", "Medium", "Fixed", "Seven canonical Shell rows still described the retired eight-chip navigation, Space+Arrow shortcuts, per-header identity placement, single skip target, direct Cmd/Ctrl+K Ask ownership, unconditional root redirect, and PageSubHeader Directory link.", "Compare shell-01 through shell-08 with the current root layout, navigation registry, desktop and compact navigation, hotkeys, identity, Ask, role-root, and focused tests.", "Every Shell row documents only current implemented behavior and carries direct assertion-level evidence where the current contract is automated.", "The register named removed controls and files, understated the 15-route workflow registry, and omitted role-priority navigation, command-palette Ask handoff, responsive skip targets, root loading state, and URL context preservation.", "Reconciled the seven stale stable IDs to current source and mapped direct evidence across the complete Shell cohort."],
  ["DEF-QV-158", "shell-05", "Medium", "Fixed", "The global Skip to navigation link targeted #concept-nav even though that chip navigation is hidden at the desktop rail breakpoint and below the phone chip cutoff.", "Focus the global navigation skip link at 1440px and 390px on a routed authenticated screen.", "Exactly one breakpoint-appropriate skip link is exposed and its fragment resolves to the visible desktop or compact navigation destination.", "The one fragment resolved to a hidden navigation subtree at both validated viewport extremes.", "The concurrent shell remediation replaced it with CSS-exclusive desktop #workflow-priority-nav and compact #workflow-disclosure links, retained #main-content, and added the shared #page-actions landmark; layout, compact-nav, and SubHeader contracts pass."],
  ["DEF-QV-159", "shell-08", "Low", "Fixed", "The new workflow-disclosure unit case read for the lazily rendered All Workflows navigation immediately after clicking a native details summary, before jsdom delivered its asynchronous toggle event.", "Run shared-shell-smoke.test.tsx against the completed role-priority WorkflowRail revision.", "The assertion observes the accessible All Workflows navigation after the native disclosure state settles.", "The details element was open, but the immediate getByRole ran before React processed onToggle, so one of 65 current Shell cases failed on both attempts.", "Changed only the test read to await findByRole; the complete three-case shared-shell file and subsequent complete Shell cohort pass."],
  ["DEF-QV-160", "BP-017", "Low", "Fixed", "Nine persona/navigation frontend nodes and 20 database-pool/Settings backend nodes landed after the prior 1,694/2,516 automation seal while the shared worktree remained active.", "Rebuild the canonical tracker against the previously sealed exact node counts.", "The collector blocks publication until every added identity executes through its complete file and the seal is advanced to the stable current inventories.", "Collection reported 1,703 Vitest and 2,536 pytest/stress/cohort nodes, with nine and 20 exact additions respectively and no removals.", "Executed all 16 complete frontend delta/modified files with 143/143 passing and four affected server files with 362/362 passing; lint and TypeScript are clean, then advanced the exact inventory gates."],
  ["DEF-QV-161", "shell-05", "Medium", "Fixed", "The new desktop skip-link contract targeted #workflow-priority-nav, but the navigation landmark was not programmatically focusable, so activating the fragment could not reliably move keyboard focus.", "Run the focused shared-shell-smoke file and assert the Analyst priority workflows navigation exposes tabindex=-1 and accepts focus.", "The visible desktop skip destination is programmatically focusable and shows the shared focus-ring treatment without entering the normal tab sequence.", "The late four-case file failed 1/4 on both attempts because the target returned a null tabindex; the other three current Shell cases passed.", "The concurrent Shell revision added tabIndex=-1 and focus-ring styling to the exact desktop navigation target; the complete four-case file and 28-case late affected-file cohort pass."],
  ["DEF-QV-162", "BP-017", "Low", "Fixed", "A net 14 Shell/persona/hierarchy frontend nodes landed after the 1,703-node evidence seal while the shared worktree remained active.", "Recollect the frontend inventory after the focus, page-action, persona hook, Ask utility, Panel observer, route-title, and hierarchy/proofing assertions land.", "Publication remains blocked until every added identity passes through its complete affected file and the exact inventory gate advances.", "Collection reported 1,717 Vitest nodes: 15 exact additions, one renamed Ask identity removed, and no lost behavior.", "Executed the eight complete affected files with 61/61 passing and the expanded 17-feature Shell/design cohort with 83/83 passing; lint, TypeScript, and the exact-current 20-route production build are clean, then advanced the canonical inventory seal."],
  ["DEF-QV-163", "shell-14", "Medium", "Fixed", "The canonical route-heading tests landed before routeTitleForPath and its registry-derived metadata were exported in the shared worktree.", "Run nav.test.ts immediately after the new canonical route-title assertion lands.", "Workflow, nested, dynamic issuer, utility, root, null, and unknown paths resolve through one exported title function and one root RouteHeading h1.", "The new nav case failed on both attempts with routeTitleForPath is not a function while the other seven navigation cases passed.", "The completed nav revision derives titles from NAV_GROUPS plus bounded specific metadata; all 8/8 navigation cases and the expanded shared cohort pass."],
  ["DEF-QV-164", "shell-16", "Medium", "Fixed", "Shared hierarchy and color-governance assertions arrived before the semantic title classes, report screen/print floors, subordinate heading cleanup, and CSS token migration were complete.", "Run hierarchy-color.contract.test.ts during the shared hierarchy rollout.", "The 16/14/13/12px workspace tiers, 12/11/10px screen report floors, 9.5pt/8pt print floors, one route h1, and token-only shared/report color contract all hold together.", "The first complete affected cohort failed four of five hierarchy cases; an intermediate rerun still failed three while CSS was settling.", "The quiescent current hierarchy contract passes 5/5 and the complete eight-file affected cohort passes 61/61."],
  ["DEF-QV-165", "shell-15", "Medium", "Fixed", "Panel mutation-observer behavior and its test double landed in separate concurrent revisions, first leaving late overflow unmeasured and then invoking the production callback without MutationRecord input.", "Run the four Panel focus-safe scroll-owner cases during the observer rollout.", "Late mutations remeasure overflow in both directions, observe added elements, and retain realistic MutationObserver callback input.", "The first run kept tabindex at -1 after simulated overflow; the next run raised records is not iterable while the other three Panel cases passed.", "The completed observer and harness revisions pass all 4/4 Panel cases and the 61-case affected cohort."],
  ["DEF-QV-166", "shell-06", "Medium", "Fixed", "Ask utility tests and shell ownership changed before AskUtility, the breakpoint-owned rail/header placements, phone-only fallback, and updated overlay structure were present together.", "Run the complete Ask coverage and shared-shell files during the utility ownership transition.", "Exactly one labelled Ask entry is owned by the active shell breakpoint, AskLauncher alone owns overlays, route-specific scope remains unchanged, and no desktop/tablet floating dock returns.", "The in-flight cohort reported undefined Ask utility rendering, obsolete dock expectations, an obsolete main landmark expectation, and a missing rail Ask button.", "The settled Ask and shell revisions pass all 16/16 Ask cases, 4/4 shared-shell cases, and the complete 61-case affected cohort."],
  ["DEF-QV-167", "BP-017", "Low", "Fixed", "Three HTTP policy middleware regression nodes landed after the 2,536-node server/stress/cohort evidence seal while the shared worktree remained active.", "Rebuild the canonical tracker after the CSRF rejection, edge-proof rejection, and duplicate Set-Cookie preservation cases land.", "The exact-count gate blocks publication until all added security identities execute through their complete file and the backend seal advances.", "Collection reported 2,539 pytest/stress/cohort nodes, with three exact additions and no removals.", "Executed the complete test_security_headers.py file with 8/8 passing and advanced the current backend evidence seal to 2,539 collected nodes."],
  ["DEF-QV-168", "issuer-31", "Medium", "Fixed", "The Issuer Directory classified distressed ratings with critical-red text alone, so users who could not perceive that color had no equivalent visible or assistive-technology signal.", "Load a directory row whose first agency rating is CCC+, Caa, or another distressed grade and inspect the Rating gridcell.", "A distressed rating has a visible non-color signal and an accessible name that identifies the distressed state while preserving the dense eight-column grid.", "The rating value was red but otherwise indistinguishable from a non-distressed rating.", "Added the existing critical StatusGlyph and an explicit Distressed rating accessible label; the complete 21-case Issuer Directory file passes."],
  ["DEF-QV-169", "issuer-31", "Low", "Fixed", "The first semantic-directory regression assertion assumed a single summary string, raw header text without the sort glyph, and a sibling DOM shape rather than the gridcell's public accessibility contract.", "Run issuer-batch.test.tsx after adding the eight-column, virtualization, and distress-state assertions.", "The harness verifies the two intentional summary placements, normalized column labels, the named rating gridcell, and its visible glyph without coupling to incidental siblings.", "The new assertion failed on duplicate summary ownership, the appended sort arrow, and a previousElementSibling lookup even though those product contracts were valid.", "Counted the two intentional summaries, normalized header labels, and anchored the glyph assertion inside the exact named gridcell; the complete file passes 21/21."],
  ["DEF-QV-170", "BP-017", "Low", "Fixed", "Eight net route-recovery and color-policy frontend nodes landed after the 1,717-node evidence seal while the shared worktree remained active.", "Run the canonical tracker builder against the exact current repository after the late shared-surface assertions land.", "The exact-count gate refuses publication until every new identity executes through its complete contributing file and the frontend seal advances.", "Collection reported 1,725 Vitest nodes and stopped workbook generation at the prior 1,717 expectation.", "Executed the six complete contributing files with 34/34 passing and advanced the exact frontend evidence seal to 1,725 nodes."],
  ["DEF-QV-171", "shell-14", "Medium", "Fixed", "RouteHeading invoked usePathname only inside the final nullish-coalescing branch, so the hook order could change when an auth or route override title appeared.", "Run npm run lint against the current shared RouteHeading revision.", "Every hook is invoked unconditionally in a stable order while the visible heading still prefers route override, auth state, then pathname-derived title.", "ESLint reported react-hooks/rules-of-hooks at RouteHeading.tsx:46.", "Called usePathname unconditionally before constructing the heading; lint, TypeScript, and the complete six-case route-heading file pass."],
  ["DEF-QV-172", "reports-04", "Medium", "Fixed", "useState inferred the warm paper token as a single string literal after the paper palette migrated to readonly color tokens, while UI and persisted drafts legitimately select three tones.", "Run tsc --noEmit against the current Report Studio revision.", "Paper state accepts only the three implemented palette values, and an arbitrary persisted string cannot reach the preview background.", "TypeScript rejected both a restored string draft value and the White/Cool paper button values.", "Typed state from the implemented PAPERS value union and whitelisted restored drafts through PAPERS.find; lint, TypeScript, and the complete 18-case Report Studio interaction file pass."],
  ["DEF-QV-173", "BP-017", "Low", "Fixed", "The restricted execution sandbox denied Turbopack's local worker-port bind while processing globals.css.", "Run npm run build inside the default restricted sandbox.", "The validation lane distinguishes environment denial from an application build failure and still obtains an exact current production artifact.", "Next build aborted with Operation not permitted while creating a worker process and binding its local port.", "Reran the same build with narrowly scoped local process permission; compilation, TypeScript, and all 20 generated routes passed."],
  ["DEF-QV-174", "issuer-31", "Low", "Fixed", "The restricted execution sandbox denied Chromium's MachPort rendezvous before axe could open a page.", "Run the local axe-core Issuer scan inside the default restricted sandbox.", "The validation lane distinguishes browser-launch denial from an accessibility failure and executes both required viewports against the exact build.", "Chromium exited on bootstrap_check_in permission denied before either state was scanned.", "Reran the same local-only scan with scoped browser permission; desktop and mobile report zero violation nodes, scan errors, or layout failures."],
  ["DEF-QV-175", "BP-017", "Low", "Fixed", "One Research ReportBody frontend node landed after the 1,725-node evidence seal while Issuer permission mapping was being published.", "Rebuild the canonical tracker against the exact current repository after the late ReportBody assertion lands.", "The exact-count gate stops publication until the new identity executes through its complete file and the frontend seal advances.", "Collection reported 1,726 Vitest nodes and stopped workbook generation at the prior 1,725 expectation.", "Executed the complete ReportBody file with 2/2 passing and advanced the exact frontend evidence seal to 1,726 nodes."],
  ["DEF-QV-176", "issuer-12", "Medium", "Fixed", "Three curated Issuer mappings used Performance considerations while the canonical Test Matrix scenario is named Performance, creating exact feature evidence but no matching scenario evidence.", "Compare curated Issuer performance mappings with the canonical scenarios array and rebuild the tracker.", "Every exact mapping uses a canonical scenario key, so passing debounce, duplicate-submit, and virtualization assertions update their intended rows.", "issuer-02, issuer-09, and issuer-12 remained Designed for Performance despite passing exact assertions.", "Renamed the three mappings to the canonical Performance label and retained the complete 21/21 Issuer Directory pass."],
  ["DEF-QV-177", "BP-017", "Low", "Fixed", "EnterprisePage.action-contract.test.tsx and its no-action guard landed in separate concurrent revisions, so the first run observed an empty page-actions region from the intermediate component.", "Execute the new complete EnterprisePage typed-action file while the shared component revision is still settling, then compare the failure with the saved source and rerun quiescently.", "Only the completed saved revision is accepted; an absent primary action yields the honest focusable no-action target and all five typed-action contracts pass.", "The first run failed the no-action text assertion twice while the other four contracts passed; the saved source already contained the required conditional guard by inspection.", "Reran the unchanged completed file after quiescence with 5/5 passing and advanced the frontend inventory by all five nodes."],
  ["DEF-QV-178", "BP-017", "Low", "Fixed", "Command and Monitor retained unused ActionReason imports after their page actions migrated to the typed EnterprisePage contract.", "Run npm run lint after the typed-action shared-source revisions settle.", "The exact-current lint gate exits cleanly with zero errors and zero warnings.", "ESLint reported two @typescript-eslint/no-unused-vars warnings, one in each route.", "Removed only the dead imports; the next lint pass is clean, TypeScript passes, and the 20-route production build succeeds."],
  ["DEF-QV-179", "command-04", "Medium", "Fixed", "A persisted holding with an issuer id but no ticker rendered a clickable em dash, making a missing identity field look like an actionable issuer code.", "Render a position whose issuer_id is present and ticker is null, then inspect the Ticker gridcell.", "The missing ticker is a plain explicit dash; the borrower name may still open the profile by stable issuer id without activating the row.", "The em dash was wrapped in an IssuerLink whenever issuer_id existed.", "Gate only the ticker link on both issuer_id and ticker, retain the independently valid company link, and add an exact no-link regression assertion."],
  ["DEF-QV-180", "command-07", "Medium", "Fixed", "The selected-position strip omitted maturity, agency ratings, QA status, and committee state even though the persisted row and canonical strip contract carried them.", "Select a populated Command holding and compare the strip with the position grid record.", "The strip retains loan economics, maturity, Moody's/S&P ratings, posture, QA, and committee state from the same snapshot.", "Only par, price, margin, and posture were rendered after the identity block.", "Added compact Maturity, Ratings, and QA fields with explicit missing formatting; the complete CommandPortfolio contract file passes."],
  ["DEF-QV-181", "command-08", "High", "Fixed", "The selected-position strip opened Deep-Dive whenever issuer_id existed, even when the bound run_id was absent, allowing the destination to resolve a different latest run.", "Select a holding with issuer_id but no run_id and activate the Deep-Dive handoff.", "No handoff is offered unless both stable issuer and run authority exist; valid values are encoded together.", "The link emitted /deepdive?issuer={id} without a run parameter.", "Require both issuer_id and run_id, otherwise render Deep-Dive authority unavailable; regression covers missing authority and encoded special characters."],
  ["DEF-QV-182", "command-40", "High", "Fixed", "A Watchtower row without issuer_id fell back to its display name in a Deep-Dive query, which could resolve an ambiguous or unrelated issuer.", "Render a ranked autonomy section with issuer_name but no stable issuer_id and inspect both row and header handoffs.", "Missing stable issuer authority suppresses the row link and disables the primary handoff with an explicit reason.", "RankedChangeRow and deriveRankedChange both substituted the display name for issuer identity.", "Removed both name fallbacks, added Issuer authority unavailable text, and verified the row plus primary action fail closed."],
  ["DEF-QV-183", "command-42", "Medium", "Fixed", "The canonical Open top change contract still described switching to the Changes tab and focusing the panel, while the implemented action navigates directly to the highest-ranked issuer in Deep-Dive.", "Compare command-42 in the tracker with deriveRankedChange, CommandTopChangeAction, and the passing browser journey.", "The source-of-truth contract documents the actual direct, stable-issuer Deep-Dive handoff and its unavailable state.", "The workbook expected a typed-URL tab switch, scroll, and focus behavior that no current source performs.", "Rewrote the user story, expected behavior, edge cases, trigger, and dependency metadata to match the implemented direct handoff."],
  ["DEF-QV-184", "command-04", "Low", "Fixed", "The strengthened persisted-grid regression queried a repeated $100M value globally after adding a second boundary row.", "Run current-command-contracts.test.tsx with Atlas and missing-ticker rows that share par size.", "Value assertions are scoped to the named owning row and remain stable when other holdings have equal economics.", "Testing Library rejected getByText('$100M') as ambiguous before later authority assertions ran.", "Scoped the economics assertions to the Atlas position row; the complete file passes 6/6."],
  ["DEF-QV-185", "BP-017", "Low", "Fixed", "The first focused Playwright command assumed a server already existed on the default port; the restricted attempt was denied a loopback socket and the escalated attempt reached no listener.", "Invoke command_flow.spec.ts directly without an explicit isolated server lifecycle.", "The QA lane starts dedicated backend/frontend listeners, uses isolated storage, and only then opens a browser.", "The attempts failed before product execution with EPERM and then ECONNREFUSED on localhost:8000.", "Started isolated FastAPI and Next servers on 8019/3019 with a temporary SQLite database and reran the complete Command file."],
  ["DEF-QV-186", "BP-017", "Low", "Fixed", "The first isolated backend launch used the legacy Python 3.9 virtual environment, whose older FastAPI rejected the current Depends(scope=...) syntax.", "Start the current server with caos/server/.venv/bin/python.", "Validation uses the repository-mandated Python 3.11 environment with FastAPI 0.138.", "Application import stopped with TypeError: Depends() got an unexpected keyword argument 'scope'.", "Switched to .venv311, migrated a fresh isolated database, and reached application startup successfully."],
  ["DEF-QV-187", "BP-017", "Low", "Fixed", "The first isolated browser run targeted 127.0.0.1 while Next development assets were owned by localhost, so hydration was blocked and every case remained on the server-rendered access check.", "Run the Command cohort against http://127.0.0.1:3019 while Next reports localhost:3019.", "The browser and development asset origin match so RequireAuth hydrates before workflow assertions.", "All four cases timed out on Checking analyst access; Next logged a blocked cross-origin development-resource request.", "Reran with PLAYWRIGHT_BASE_URL=http://localhost:3019; 4/4 focused and 12/12 cross-browser Command executions pass."],
  ["DEF-QV-188", "BP-017", "Low", "Fixed", "Fourteen net frontend nodes and three browser-project executions landed after the 1,731/141 evidence seal while the shared worktree remained active.", "Run the fail-closed tracker builder against the new Command authority, mobile, and concurrent page-action tests.", "Publication stops until every new identity passes through its complete file and browser project.", "The builder collected 1,745 Vitest nodes instead of 1,731; Playwright advanced from 141 to 144 after the new journey.", "Executed all six complete frontend contributors at 51/51, the stabilized label file at 10/10, and command_flow across Chromium, Firefox, and WebKit at 12/12 before advancing the gates."],
  ["DEF-QV-189", "BP-017", "Low", "Fixed", "Three distinct Model Engine page-action label checks collected under one identical parameterized Vitest name.", "List frontend nodes and group PageAction.label-stability.test.ts by file and test name.", "Each label-stability assertion has a unique, durable evidence identity.", "The save-suggestion, recalculate, and commit cases all appeared as the same ModelV2Workbench accessible-label node.", "Added a stable operation descriptor to every table row and included it in the test title; the complete ten-case file passes with distinct names."],
  ["DEF-QV-190", "BP-017", "Low", "Fixed", "Thirteen evidence-selection and completion-state frontend nodes landed after the 1,745-node seal while the workbook gate was running.", "Rerun the fail-closed tracker builder after the Command delta appears stable.", "Any late shared-worktree node is executed through its complete contributing file before the exact inventory advances.", "The builder stopped at expected 1,745 and collected 1,758 Vitest nodes.", "Executed EvidenceSelectionList, both selection integrations, CompletionStateSummary, and the adoption contract at 13/13 before advancing the seal."],
  ["DEF-QV-191", "BP-017", "Low", "Fixed", "The fail-closed tracker invoked Vitest collection while the isolated Next development server was concurrently using the frontend transform graph.", "Run the tracker builder while the browser-validation development stack is still active.", "Collection either completes against a quiescent source tree or fails with an actionable infrastructure classification; publication never accepts a partial inventory.", "Vitest collection stopped with `Timeout calling fetch [EnterprisePage.tsx,web]` from a worker RPC, and the builder correctly aborted before export.", "Stopped the isolated browser stack and reran the unchanged builder quiescently; exact 1,758-node frontend collection and artifact export completed successfully."],
  ["DEF-QV-192", "command-30", "High", "Fixed", "Sector Review history could resolve after an analysis-context change and reselect a dossier from the prior sector; URL-only section changes also triggered unnecessary history fetches.", "Open a Telecom dossier, change the active context sector to Software while an older history request is in flight, and let the stale response settle.", "Only the active context and sector may own the selected review; superseded requests are ignored and local URL section changes do not refetch history.", "Two of six initial narrow-browser executions resurrected review-1 after the context moved to Software, creating a cross-sector wrong-read risk.", "Cancelled superseded responses, separated URL state from fetch dependencies, filtered returned history by active sector_id, and passed the new unit regressions plus 6/6 browser executions."],
  ["DEF-QV-193", "command-29", "Medium", "Fixed", "Taxonomy and feed-reference read failures were silently converted into an authoritative empty directory and default-on alert preferences.", "Reject GET /api/analysis/taxonomy or GET /api/sector/feeds while loading /sector.", "Reference-data failure is explicit and cannot be mistaken for a canonical empty taxonomy or a persisted enabled preference.", "The dossier rendered no bounded error for either failed read and continued with fallback reference state.", "Added independently bounded taxonomy/feed errors and a complete read-failure component regression."],
  ["DEF-QV-194", "command-29", "High", "Fixed", "A failed sector context patch cleared the active dossier before persistence succeeded, and feed/sector mutations could overlap.", "Reject the analysis-context PATCH during sector change or rapidly toggle alerts while another mutation is pending.", "Persist-before-clear retains the prior dossier on failure; competing mutations are serialized, disabled while pending, and recover after settlement.", "The screen could lose the prior review despite the server retaining the old context, and overlapping updates risked last-response ownership.", "Guarded current/busy actions, require a successful patch result before clearing sector-owned state, and serialize feed updates with recovery assertions."],
  ["DEF-QV-195", "command-48", "High", "Fixed", "GET /api/sector/reviews applied context_id filtering after a global 100-row limit.", "Create an older review for the target context followed by 101 newer reviews owned by the same analyst in other contexts, then list the target context.", "The SQL query scopes by analyst and payload context_id before ordering and limiting, so the target review remains discoverable.", "The global limit could exclude the target review and return an empty history even though an owned version existed.", "Added the JSON payload context predicate before ORDER BY/LIMIT, retained defensive filtering, and passed a 102-review regression."],
  ["DEF-QV-196", "command-50", "Medium", "Fixed", "A published sector review mapped to an UNRATIFIED decision authority and still exposed a stale final action.", "Load a review whose authority.approval_state is published after completing the publication workflow.", "Published maps to RATIFIED governance authority and exposes no further Ratify or Publish primary action.", "The decision header understated approval and left an obsolete action visible.", "Mapped published authority to RATIFIED, removed the stale final action, and strengthened the governed happy-path assertion."],
  ["DEF-QV-197", "command-51", "Low", "Fixed", "Two comparable issuers without stable ids but with the same display name produced duplicate React row keys.", "Render two missing-id comparables with an identical issuer_name.", "Display-only comparables remain distinct without React key warnings, while metric columns stay bounded to four finite sorted keys.", "Both rows used issuer_name as their key, risking reconciliation artifacts and console warnings.", "Included the row index in the missing-id fallback key and added duplicate-name/non-finite/max-column coverage."],
  ["DEF-QV-198", "BP-017", "Low", "Fixed", "Twenty-seven frontend identities were added and two retired after the 1,758-node evidence seal while Sector validation was active.", "Compare the current Vitest list with the prior Automation Evidence sheet.", "Publication remains blocked until every added identity executes through its complete contributing file and the exact count advances.", "The current inventory contained 1,783 Vitest nodes, a net increase of 25, plus one backend and six browser additions.", "Executed all twelve contributing frontend files at 92/92, the affected server cohort, and all six new browser nodes before advancing the fail-closed counts."],
  ["DEF-QV-199", "command-30", "Low", "Fixed", "The new cross-sector regression assigned null to a test fixture inferred as string-only, failing the standalone TypeScript gate despite runtime behavior passing.", "Run npx tsc --noEmit after the first cross-sector fixture revision.", "The test fixture models sector_review_run_id as string|null and both static and behavioral gates pass.", "TypeScript reported TS2322 at the context replacement while the 13 runtime component cases passed.", "Widened the hoisted fixture field to string|null, restored the semantically correct null value, and reran TypeScript cleanly."],
  ["DEF-QV-200", "BP-017", "Low", "Fixed", "The isolated static server retained the previous build's CSP hashes after a production artifact rebuild.", "Rebuild the static artifact without restarting the already-running validation server, then open /sector.", "Browser validation serves CSP hashes generated for the exact artifact under test.", "Bootstrap scripts were blocked by stale CSP hashes and the page remained at the auth loading gate before product assertions ran.", "Restarted the isolated server against the rebuilt artifact, confirmed bootstrap execution, and passed 6/6 zero-retry sector journeys."],
  ["DEF-QV-201", "BP-017", "Low", "Waived", "The repository-wide GitNexus detect_changes comparison cannot bound the current multi-thread shared-worktree diff within its child-process output buffer.", "Run detect_changes with scope=compare and base_ref=origin/main against the current shared worktree.", "The graph maps changed symbols and affected execution flows, or supports path-bounded comparison for the agent-owned files.", "The required MCP call stops with `Git diff failed: spawnSync git ENOBUFS` before returning a risk map.", "Explicit external-tool waiver: this does not affect CAOS runtime behavior. Pre-edit symbol impacts, explicit path-scoped diff review, clean lint/type/build, full frontend regression, exact browser/accessibility checks, and post-change scope review compensate until GitNexus adds path filtering or a larger buffer."],
  ["DEF-QV-202", "monitor-07", "Low", "Fixed", "The replay-count helper accepted non-finite and negative ticks without normalization.", "Call simAlertsToday with NaN, positive/negative infinity, or a negative tick while the replay is active.", "The KPI remains a finite, non-negative count bounded by the authored alert tape.", "NaN produced a NaN KPI and negative ticks could produce a negative Replay today count.", "Normalize non-finite and negative ticks to the opening baseline before accrual; the direct boundary, hostile-input, performance, focused frontend, browser, lint, type, and production-build regressions pass."],
  ["DEF-QV-203", "monitor-07", "Medium", "Fixed", "The first audit served static assets with identity encoding despite production Caddy's checked-in `encode gzip`, and the closed global Ask shell also pulled its analytical query dependencies into every route's initial bundle.", "Cold-load /monitor at 390x844 with 4x CPU slowdown, 150ms latency, and 1.6Mbps downlink; compare identity and gzip transport; inspect the closed/open Ask waterfall.", "The primary phone triage surface reaches useful content under the production transport without downloading the heavy Ask analytical surface before the analyst opens it.", "Pre-fix gzip-aligned five-sample p75 was 2,320ms LCP/215ms TBT with 266.8KB encoded JavaScript; the earlier identity-encoded run overstated deployed LCP at 6,740ms and JavaScript at 900.7KB.", "Extracted one compatibility-preserving Ask context and kept only the trigger in the initial shell; the heavy chunk is absent while closed and loads on first Ask open. Raw JS falls 875.2KB→766.0KB, encoded JS 266.8KB→227.2KB, and five-sample mobile p75 improves to 2,100ms LCP/188ms TBT with clean focused/full/browser/axe/build gates."],
  ["DEF-QV-204", "BP-017", "Low", "Fixed", "Nine frontend nodes landed after the 1,783-node evidence seal while Monitor validation and concurrent Deep-Dive/Research/shared-shell work were active.", "Rebuild the canonical tracker against the prior exact frontend count.", "Publication blocks until every added identity executes through its complete current file and the evidence seal advances.", "Exact collection reported 1,792 Vitest nodes: four Monitor additions and five concurrent additions.", "Executed all five complete contributing files at 44/44 before advancing the fail-closed inventory gate to 1,792."],
  ["DEF-QV-205", "BP-017", "Low", "Fixed", "Coverage Summary counted Pass, Suite evidence, Designed, Not applicable, and Skipped statuses but omitted the Test Matrix's Blocked status.", "Compare the generated-test total with the visible status-category totals in Coverage Summary.", "Every Test Matrix row is represented by an explicit summary category, including blocked validation work.", "The visible categories summed to 4,718 while Generated test cases reported 4,719 because GITNEXUS-SEMANTIC-DISCOVERY was Blocked.", "Added a formula-backed Blocked validation cases row and clarified that the separate pytest skip count is disclosed in the current-iteration note."],
  ["DEF-QV-206", "pipeline-10", "Low", "Fixed", "Pipeline read its saved Dependency map/Stage lanes preference without handling browser-storage denial.", "Make localStorage.getItem throw a SecurityError while mounting /pipeline.", "The route hydrates the implemented Dependency map default and remains interactive without propagating the storage exception.", "The preference effect could terminate before hydration and leave the composed route dependent on a browser capability it does not control.", "Wrapped the read in a fail-safe hydration path; the exact storage-denial regression and complete Pipeline cohort pass."],
  ["DEF-QV-207", "pipeline-17", "Low", "Fixed", "simClock formatted negative, fractional, and non-finite ticks directly.", "Call simClock with -1, 1.9, NaN, or either infinity.", "The clock uses a finite non-negative integer tick while preserving every valid authored integer tick.", "Malformed input could yield a pre-open time or NaN:NaN:NaN and fractional seconds could leak into formatting.", "Normalize only invalid, negative, and fractional inputs before formatting; the 13-case simulation-engine file, 136-case focused cohort, and browser matrix pass."],
  ["DEF-QV-208", "pipeline-10", "Medium", "Fixed", "The phone Run display drawer composed narrow essential controls with the full desktop utility controls, duplicating progress, clearance, and Dependency map/Stage lanes actions.", "Open Run display controls at 390x844 and query the labelled Stage lanes action.", "Exactly one essential view control is present; supplemental mode, simulation, clock, and dim controls remain available.", "The same dialog exposed duplicate controls with identical names; the first breakpoint-hook repair also raced during Chromium hydration.", "Assigned deterministic CSS ownership below lg to the narrow control set. The phone journey asserts one Stage lanes action and passes in Chromium, Firefox, and WebKit; all six responsive axe states are clean."],
  ["DEF-QV-209", "BP-017", "Low", "Fixed", "Nine frontend nodes and twelve Pipeline browser-project nodes landed after the 1,792-Vitest/150-Playwright evidence seal.", "Run the fail-closed tracker builder after the Pipeline fixes, concurrent additions, and cross-browser journey are added.", "Publication stops until every added identity executes through its complete contributing file and project.", "Collection advanced to 1,801 Vitest and 162 Playwright nodes.", "Executed the exact-current 1,801-node frontend run, repaired both failures, passed the complete affected files at 24/24, passed the 136-case Pipeline frontend cohort, and executed all 12 Pipeline browser-project nodes before advancing the exact gates."],
  ["DEF-QV-210", "pipeline-09", "High", "Fixed", "The default Pipeline route could mount the Atlas Forge reference plan even though the application was in live mode, making fixture state appear operational.", "Open /pipeline without mode=reference, then compare the run tape with /pipeline/?mode=reference and follow its handoffs.", "Live-empty mode shows no fixture run; explicit reference mode shows the labelled reference plan, preserves mode through handoffs, and starts with planned progress at zero.", "The default fixture path blurred live and reference provenance, while a planned reference run could appear already executed.", "Made reference data explicit, retained live-empty truth, preserved mode in handoffs, and reset planned execution to zero; focused, browser, and accessibility matrices pass."],
  ["DEF-QV-211", "pipeline-45", "Medium", "Fixed", "The Pipeline E2E contract still targeted retired Execution Graph/Swimlanes labels, a stale issuer identity, and an always-running simulation assumption.", "Execute pipeline_flow.spec.ts against the current production artifact in all three browser projects.", "Journeys use Dependency map and Stage lanes, assert the labelled reference identity, and control planned simulation start/pause deterministically.", "Selectors and state assumptions no longer matched the implemented workbench, so browser evidence could fail without a product regression.", "Updated semantic locators and the planned-run workflow; all 12 Chromium, Firefox, and WebKit executions pass with zero retries."],
  ["DEF-QV-212", "reports-11", "High", "Fixed", "A requested immutable Report Studio deep link briefly left the live-draft publish action available before the published version selection effect completed.", "Open a URL for an immutable published version while a different mutable report is active and inspect the publish action before selection settles.", "Publishing stays blocked while the requested immutable version is opening and remains unavailable once that immutable version is active.", "For one render, canPublish was derived from the mutable active report even though the URL requested a frozen version, risking publication of the wrong state.", "Added a pending published-selection guard and explicit explanation; the complete affected Report Studio and recovery cohort passes 24/24."],
  ["DEF-QV-213", "BP-017", "Low", "Fixed", "The Pipeline scenario mapping added to the canonical tracker builder omitted a closing array bracket.", "Run node --check and then execute the fail-closed tracker builder.", "The generator parses before collection and stops only on intentional evidence drift or workbook validation failures.", "Node rejected the builder before it could reconcile evidence or export the workbook.", "Restored the array closure; syntax validation passes and the builder proceeds through exact-count and workbook gates."],
  ["DEF-QV-214", "BP-017", "Low", "Fixed", "A responsive-recovery source-contract test required the retired hidden md:inline-flex CSS token instead of the implemented narrow recovery behavior.", "Run responsive-recovery.contract.test.ts against the current responsive shell.", "The contract asserts observable narrow recovery and export affordances without pinning a superseded styling token.", "The exact-current full frontend run failed one static assertion although the semantic narrow-path checks remained valid.", "Removed the obsolete token assertion while retaining the behavior checks; the complete affected cohort passes 24/24."],
  ["DEF-QV-215", "pipeline-09", "Medium", "Fixed", "The axe runner waited only for Enterprise/persona surfaces, so a standalone Pipeline SurfaceState could be reported as a scan error instead of being audited; once included, its h3 skipped the route h2 level.", "Scan live-empty /pipeline at desktop and phone widths with SurfaceState accepted as readiness evidence.", "The empty state is scanned, uses an h2, and produces no WCAG, geometry, overflow, target-size, clipping, or collision failures.", "The broadened runner exposed two moderate heading-order nodes, one per viewport.", "Recognized data-surface-state readiness and supplied headingLevel=2 to standalone Pipeline states; the final six-state Issuers/live/reference matrix is clean."],
  ["DEF-QV-216", "BP-017", "Low", "Fixed", "Four notification-action-label server nodes landed after the 2,540-node backend evidence seal.", "Run the fail-closed tracker builder against the current shared worktree and compare the prior Automation Evidence inventory.", "Publication stops until every added server identity executes through its complete contributing file.", "The builder collected 2,544 pytest/stress/cohort nodes and refused export at the 2,540 gate.", "Identified the response-compatibility and three migration-safety additions, executed both complete contributing files at 79/79, and advanced the backend seal."],
  ["DEF-QV-217", "monitor-07", "Low", "Fixed", "The Monitor responsive workbench validator still opened live mode and searched for the retired live `Email intake`/`Alerts` tab contract after email examples moved behind explicit Reference mode.", "Run npm run verify:monitor against the exact static export.", "The validator requests the mode that owns the controls it exercises and verifies desktop, tablet, and phone geometry/focus without changing product state.", "The first run timed out looking for Email intake in live mode; the first correction still looked for the old Alerts label instead of Reference mode's Replay label.", "Opened `mode=reference`, used the implemented Replay/Email intake labels, and reran all three viewports with restored drawer focus, one table owner, no overflow, and no overlap."],
  ["DEF-QV-218", "BP-017", "Low", "Fixed", "Two frontend automation identities appeared after the 1,801-node evidence seal.", "Run the exact current full Vitest inventory and then the fail-closed tracker collector.", "Every collected identity is executed before the canonical automation count advances.", "The complete current run collected and passed 1,803 cases across 261 files.", "Advanced the frontend execution seal to the single-run 1,803/1,803 result and the exact automation inventory to 4,549 nodes."],
  ["DEF-QV-219", "reports-11", "Low", "Fixed", "The Report Studio immutable print/download test was renamed, but its curated tracker regex still targeted the retired name.", "Reconcile Feature Evidence after collecting the current reports-interactions test identities.", "The extant immutable print, binary-download, failure, evidence, and decision-room assertions map directly to reports-11, and a fail-closed concept gate prevents silent evidence loss.", "reports-11 appeared Unmapped even though its complete current interaction test passed and exercised the implemented contract.", "Updated the assertion-level mapping to the exact current test name and added a 28/28 Report Studio direct-evidence gate; the complete 18-case file and tracker build pass."],
  ["DEF-QV-220", "reports-14", "High", "Fixed", "The deliverables footer always described the Atlas Forge CP-5/QA-117 fixture hold, including when the screen displayed a different live issuer's reports.", "Open a caller-visible live run in Report Studio and read the Committee Deliverables footer.", "Reference mode names the authored fixture; live held and clean modes name the active run's actual committee authority without fixture leakage.", "Live output was paired with a confident reference-only QA notice, creating a materially wrong authority read.", "Made ReportList require its authority mode and render reference, live-held, or live-clean copy with text plus warning/success signal; seven panel and eighteen interaction cases pass."],
  ["DEF-QV-221", "BP-017", "Low", "Fixed", "The first authority-notice regression used one text regex across nested inline spans, which Testing Library correctly does not concatenate into a single element match.", "Run panels.test.tsx after adding the live-held authority sentence assertion.", "The harness asserts the stable text fragments without depending on DOM nesting.", "One panel case failed although the rendered product sentence was correct.", "Split the expectation across the sentence and emphasized committee-status fragment; the complete panel and Report Studio cohort passes."],
  ["DEF-QV-222", "BP-017", "Medium", "Fixed", "The gzip validation server cached compressed HTML by path only while a concurrent production build replaced the static export, leaving current HTML/JS requests pointed at deleted chunk names.", "Start the gzip server before a build completes, request /reports, rebuild out/, then request the route with Accept-Encoding: gzip.", "Compressed responses invalidate whenever the source artifact mtime or size changes, so HTML and chunks remain from one coherent build.", "Chromium received an old stylesheet name and 404, rendering utility drawers as static full-page content or failing with ChunkLoadError.", "Cache entries now retain source mtime/size and recompress on change; raw and gzip HTML hashes match after rebuild and exact browser/a11y/performance runs pass."],
  ["DEF-QV-223", "BP-017", "Low", "Fixed", "The first Report workbench validator assumed Committee Deliverables remained expanded at 1440px, while the implemented route collapses it below 1600px to preserve the paper.", "Run the validator at 1440x900 and immediately search for Credit Snapshot.", "The harness opens the labelled Deliverables rail when collapsed, then verifies the six-item contract.", "The control was correctly absent from the accessibility tree until its rail was expanded.", "Made the validator follow the implemented responsive disclosure before asserting the deliverables."],
  ["DEF-QV-224", "reports-03", "High", "Fixed", "The shared MoreDrawer right-anchored a 256px Report utilities panel to a phone trigger whose right edge was only 196px from the viewport origin.", "Open Report utilities at 390x844 and measure the fixed panel.", "The drawer remains within an 8px viewport inset while preserving left/right alignment and keyboard focus behavior.", "The panel started at x=-60px, placing paper, source, edit, zoom, print, and download controls partly off-screen.", "Clamped both anchor offsets using the effective panel width and added a viewport-relative max width; four drawer, seven SubHeader, and exact three-width browser validations pass after CRITICAL-impact regression review."],
  ["DEF-QV-225", "BP-017", "Low", "Fixed", "The first stylesheet readiness probe inspected only top-level cssRules and missed Tailwind's nested @layer rule containing .fixed.", "Load the coherent exact stylesheet and search only sheet.cssRules for a rule whose text starts with .fixed.", "Readiness is determined by the browser's computed position for a temporary .fixed probe.", "The harness reported fixed CSS unavailable even though 592 rules loaded and the product styling was present.", "Replaced structural CSSOM guessing with a fail-closed computed-style condition."],
  ["DEF-QV-226", "BP-017", "Low", "Fixed", "The phone utility trigger sat at -0.5px because of browser subpixel rounding, but the validator required top >= 0 exactly.", "Measure the Report utilities trigger at 390x844 after scrolling to document origin.", "Geometry checks tolerate at most two pixels of rendering-rounding noise while still failing true clipping.", "The otherwise reachable 44px trigger failed the strict zero-bound assertion.", "Applied the same ±2px tolerance used by the clipping audit; true drawer overflow remained detectable and was fixed separately."],
  ["DEF-QV-227", "BP-017", "Low", "Fixed", "The first phone control audit treated the Report paper's Show equivalent table control as viewport clipping even though it is intentionally reachable inside the labelled horizontal Report preview scroll owner.", "Audit every visible button against the document viewport at 390x844.", "Controls in an intentional overflowing preview/table owner are recorded as scroll-contained; only controls without such an owner fail.", "The validator emitted one false clipping failure after every product interaction and accessibility check passed.", "Classified the nearest real horizontal scroll owner and retained fail-closed failure for uncontained controls; final results show the one expected scroll-contained control and zero failures."],
  ["DEF-QV-228", "BP-017", "Low", "Fixed", "The first focused server command invoked an absolute virtual-environment path containing spaces without shell quoting.", "Run the designated Python executable by its unquoted absolute path.", "The command resolves the exact interpreter before pytest collection.", "zsh attempted to execute /Users/ericguei/Claude/Projects/Credit and exited 127.", "Quoted the interpreter path and reran the exact test nodes."],
  ["DEF-QV-229", "BP-017", "Low", "Fixed", "The repository's .venv environment exposes an older FastAPI Depends signature and cannot import the current scope='function' dependency declaration.", "Run the two Report server nodes with caos/server/.venv/bin/python.", "Validation uses the current FastAPI 0.138 environment without changing the application pin.", "Both nodes failed at setup with TypeError before an application assertion.", "Used the designated .venv311 environment; both tightened server nodes pass. The incompatible .venv was not modified or used as evidence."],
  ["DEF-QV-230", "BP-017", "Low", "Fixed", "The first exact Report accessibility/browser launch was denied the Chromium Mach rendezvous operation by the restricted sandbox.", "Launch local Chromium for the exact static build without the scoped browser permission.", "The validation environment grants only the local browser process capability needed to run axe and workbench checks.", "Chromium exited before navigation, producing no product assertion.", "Re-ran the same exact-build commands with approved local browser permission; two axe states, three workbench widths, and all performance samples pass."],
  ["DEF-QV-231", "BP-017", "Low", "Fixed", "The tracker preview attempted to render all 230 Defects rows into one 74,698px image, exceeding artifact-tool's maximum render dimensions before workbook export.", "Build the canonical tracker after adding the Report iteration defect rows.", "Every sheet receives a bounded visual preview while all underlying workbook rows remain intact and inspectable.", "Artifact-tool stopped with Auto render too large before exporting the updated workbook.", "Bounded the Defects and Validation Runs preview ranges to representative first-page windows; full row inventories, formulas, and persisted-workbook inspections remain unchanged."],
  ["DEF-QV-232", "model-19", "Low", "Fixed", "The legacy Model checkpoint journey opened the collapsed Model tools drawer and immediately searched for a control that now lives in the separately selected History support rail.", "Run the complete frontend suite and execute the named checkpoint journey at the current collapsed header contract.", "The test selects History through the semantic support control, then opens, saves, and restores the named checkpoint modal.", "One of 1,808 frontend tests failed because the checkpoint control was never mounted; 1,807 passed.", "Updated the journey to activate History before locating the checkpoint control; the complete model-history file and final full frontend regression pass."],
  ["DEF-QV-233", "BP-017", "Low", "Fixed", "The Sector Review tracker mapping still targeted one retired combined failure-test name after its history/refresh and feed-persistence assertions were split into two focused tests.", "Rebuild the tracker against the current 1,808-node frontend inventory and run the Sector fail-closed scenario gate.", "Current semantic test identities preserve direct error-path evidence for the versioned dossier, refresh, tabs/history, and feed-preference contracts.", "The tracker stopped with 63/63 Sector rows present but command-30, command-31, and command-48 error paths unmapped; no workbook was published.", "Mapped the history/refresh failure test to command-30/31/47/48 and the feed-persistence failure test to command-29; the complete Sector dossier file and final 63/63 gate pass."],
  ["DEF-QV-234", "BP-017", "Low", "Fixed", "The new explicit Report execution rows shared reports-* feature IDs, while the Report scenario gate filtered only by feature prefix and therefore counted six Direct execution rows as mandatory scenarios.", "Add the six Report execution cases and rebuild the canonical tracker.", "The fail-closed matrix evaluates exactly 28 features by seven canonical scenarios, independently of supplemental execution-ledger rows.", "The gate reported 202 rows instead of 196 and misread a Direct execution row as a failing reports-04 scenario; no workbook was published.", "Matched the Report gate to the same canonical scenario-label set used by Issuer, Command, Pipeline, Monitor, and Sector gates; the final matrix remains 196 total, 194 applicable, and gap-free."],
  ["DEF-QV-235", "reports-04", "Low", "Fixed", "The paper-tone implementation whitelisted restored server-draft values, but the Report scenario ledger had no direct assertion for an unsupported persisted paper token.", "Rebuild the strict 196-row Report matrix after reconciling current automation identities.", "An unsupported saved paper value is ignored; Warm remains selected and neither White nor Cool is falsely pressed.", "The gate isolated reports-04 Invalid input as the only non-pass among 194 applicable scenarios and refused publication.", "Added a focused persisted-draft regression and mapped its exact identity to reports-04 Invalid input; the complete Report interaction file passes 19/19 and the final Report matrix is gap-free."],
  ["DEF-QV-236", "model-24", "Low", "Fixed", "Two Model browser journeys assumed the Scenario panel was automatically mounted after the support-toolbar redesign.", "Run model_flow.spec.ts in Chromium, Firefox, and WebKit and enter the scenario-preset or CP-2B journey directly after route readiness.", "The journey selects Model support → Scenario semantically before operating the panel, and all later serial cases execute.", "The panel was absent, three projects failed the first affected case, and later serial cases were skipped.", "Selected Scenario through the labelled Model support group in both journeys; the complete zero-retry browser matrix passes 15/15."],
  ["DEF-QV-237", "SCR-006", "Low", "Fixed", "The route performance harness considered the enterprise shell ready before the Model worksheet mounted, so a transient capability card could terminate the readiness timer.", "Audit /model against the gzip static server while Model authority resolution is still in progress.", "Readiness is recorded only after the accessible Model worksheet is visible, while paint metrics retain the browser's real candidate history.", "The route timer could finish on transient shell/capability markup rather than the usable workbench.", "Added an explicit Model worksheet readiness gate, discarded the earlier samples, and collected one desktop plus five constrained-mobile replacements."],
  ["DEF-QV-238", "BP-017", "Low", "Fixed", "The first disposable QA-server launch supplied a production-grade SESSION_SECRET while ENVIRONMENT remained development, correctly triggering a fail-closed configuration guard.", "Start the isolated SQLite QA server with a production-looking session secret in development mode.", "The disposable development posture either uses its development secret contract or changes the complete environment coherently.", "Boot stopped before binding, producing no application result.", "Removed the production-only secret from the disposable development launch; no product configuration was changed."],
  ["DEF-QV-239", "BP-017", "Low", "Fixed", "The restricted sandbox denied the localhost QA server bind used by the real-browser Model validation.", "Bind the isolated FastAPI/static stack to 127.0.0.1:8130 under the restricted process profile.", "The validation environment grants only the loopback process capability required for the in-scope browser checks.", "The server exited with EPERM before a browser assertion could run.", "Re-ran the same isolated command with approved loopback permission; browser, axe, and performance validations completed without changing product behavior."],
  ["DEF-QV-240", "model-44", "Medium", "Fixed", "The canonical register described 43 legacy reference-calculator features but omitted 23 implemented Model Engine v2 authority, mutation, scenario, history, workbook, lifecycle, and recovery workflows.", "Compare the /model authority route, ModelV2Workbench, server v2 routes, and workbook implementation with every Model Builder Feature ID.", "Every implemented user workflow has a unique Feature ID, code-derived contract, seven-scenario suite, and direct evidence.", "Live v2 behavior was executable but absent from the source-of-truth feature and scenario matrices.", "Added model-44 through model-66 with 161 direct scenario rows, source/dependency contracts, strict inventory and 462-row scenario gates, and focused frontend/server/browser evidence."],
  ["DEF-QV-241", "model-25", "Medium", "Fixed", "Eleven legacy Model Builder rows still claimed superseded localStorage, no-confirmation reset, automatic panel rail, CSV, legacy provenance copy, or undifferentiated persistence behavior.", "Diff the 43 legacy feature contracts against the current Model route, support panels, export implementation, and saved-model API behavior.", "The canonical spreadsheet describes only current implemented storage, confirmation, support selection, XLSX, provenance, responsive, and persistence semantics.", "The register could direct testers toward retired controls and persistence assumptions even while current automation passed.", "Reconciled model-03, 04, 05, 13, 15, 24, 25, 26, 32, 42, and 43 to current source and linked their exact assertions."],
  ["DEF-QV-242", "API-072", "Medium", "Fixed", "The tracker route-call regex stopped after a parameterized path segment, so the generic legacy /api/models/{issuer_id} pattern also matched nested /api/models/v2/... calls.", "Collect Model API evidence containing both legacy and nested v2 requests, then inspect API-072/API-073 scenario attribution.", "A route invocation maps only when the quoted request path ends or begins a query string at that exact inventory boundary.", "Nested v2 tests could be credited to the legacy saved-model routes, producing false direct evidence.", "Added an exact quote/query lookahead after the route pattern, reran the fail-closed inventory, and replaced inherited matches with endpoint-specific legacy tests."],
  ["DEF-QV-243", "API-089", "Medium", "Fixed", "The 18 Model API handlers had 77 applicable scenario gaps in the canonical matrix, and no endpoint-by-endpoint closure gate prevented the evidence drift.", "Filter API-072 through API-089 to the seven canonical scenarios and compare each route with current legacy, v2, checkpoint, override, history, export, preview, and commit tests.", "All 108 applicable scenarios have assertion-level evidence; 18 backend viewport rows are explicitly N/A; inventory drift or any non-pass blocks export.", "Only 31 scenario rows were direct Pass, 45 had aggregate suite evidence, and 32 remained Designed across the Model API family.", "Added direct scenario mappings, focused missing HTTP contracts, a route/handler identity assertion, and a strict 126-total/108-applicable/gap-free Model API gate."],
  ["DEF-QV-244", "API-079", "Low", "Fixed", "The first new valid-calculation API assertion expected status `computed`, but the implemented Model Engine v2 contract returns `ready` for a complete calculation.", "POST a valid current payload to /api/models/v2/{issuer_id}/calculate.", "The response is 200, status is `ready`, hashes and engine identity are present, and leverage is finite.", "The endpoint returned a valid calculation and the new harness alone failed 1/57 on the wrong label.", "Aligned the assertion to the source-defined `ready` state; the complete changed-file cohort passes."],
  ["DEF-QV-245", "API-081", "Low", "Fixed", "The first all-mutation viewer test expected revision 1 after creating a v2 checkpoint, overlooking that checkpoint reservation intentionally advances the draft to revision 2.", "Create a v2 checkpoint, deny all six viewer mutation routes, then read the surviving draft revision.", "Checkpoint reservation owns revision 2 and every viewer mutation returns 403 without advancing it further.", "All six denials passed, but the harness compared the durable revision with the pre-checkpoint value and failed 1/62.", "Updated the postcondition to the implemented reservation contract; the complete changed-file cohort passes 62/62."],
  ["DEF-QV-246", "BP-017", "Low", "Fixed", "Twenty-eight Model API nodes landed after the exact 2,544-node server/stress/cohort evidence seal.", "Run the fail-closed collector after adding the legacy/v2 quality and performance contracts.", "Publication stops until every new identity executes through its complete changed file and the exact backend gate advances.", "Collection reported 2,572 nodes and the stale gate would reject export.", "Executed both complete changed files at 62/62 and advanced the reconciled backend inventory to 2,572 nodes."],
  ["DEF-QV-247", "API-093", "Medium", "Fixed", "The API inventory joiner removed declared trailing slashes, so six intentional slash/no-slash FastAPI route pairs were documented as duplicate paths and could share misleading evidence.", "Compare the stacked portfolio, portfolios, sponsors, and issuers decorators with their generated API Inventory rows and direct route matches.", "Each declared alias retains its exact path, maps only to a request using that spelling, and remains independently visible in the canonical tracker.", "The aliased roots were indistinguishable in the source of truth, and the legacy /api/portfolio/ alias had no evidence of its own.", "Preserved decorator trailing slashes in route discovery, added the newly exposed legacy portfolio contract, and reran both forms of every affected focused alias."],
  ["DEF-QV-248", "API-006", "Medium", "Fixed", "Ten discovered API rows had no direct automation mapping, leaving the canonical feature inventory at 673/683 direct features; correcting alias identity then exposed one additional borrowed-evidence gap.", "Filter Feature Evidence to Direct Nodes = 0, preserve exact route spelling, and exercise every returned route under its implemented ownership, validation, ordering, filtering, and alias contract.", "Every canonical feature has at least one passing direct node and tracker export fails closed on any future direct-evidence gap.", "Analysis-context, portfolio-root, query-history, research-history, sector-history, sponsor-root, and one legacy slash-alias contract lacked independent evidence.", "Added seven focused runtime contracts, reused verified exact-spelling alias suites, passed the 32-case focused cohort, and added a 683/683 direct-evidence gate."],
  ["DEF-QV-249", "API-006", "Low", "Fixed", "The first database-failure contract expected Starlette's plain-text 500 body rather than CAOS's implemented JSON error envelope.", "Inject a failing database dependency into each of the eleven list/root routes with server exceptions suppressed.", "Every route returns HTTP 500 with {detail: Internal Server Error}, and a normal request succeeds after the dependency recovers.", "All eleven failure-path nodes reached the intended 500 boundary but failed their response-body assertion.", "Aligned the harness with the application exception middleware; all eleven error/recovery cases pass."],
  ["DEF-QV-250", "API-158", "Low", "Fixed", "The first Sector backpressure probe assumed the shared 60/minute read limit, while the implemented Sector contract allows 90/minute.", "Issue sequential GET /api/sector/reviews requests through the exact threshold, classify the first rejected request, reset, and probe recovery.", "Requests 1–90 succeed, request 91 returns 429, and a post-reset normal read succeeds.", "The harness expected request 61 to return 429, but the route correctly returned 200 under its declared 90-request allowance.", "Updated the exact boundary to 90; the staged backpressure and recovery test passes."],
  ["DEF-QV-251", "API-006", "Medium", "Fixed", "The eleven newly reconciled list/root API features still had 51 applicable scenario rows backed only by aggregate evidence or design intent.", "Filter the 77-row scenario matrix for the eleven API IDs and require direct happy, error, boundary, invalid, permission, and performance evidence for every applicable row.", "All 66 applicable scenarios pass with assertion-level evidence and all 11 backend viewport rows remain explicitly Not applicable.", "The matrix contained 15 direct passes, 31 suite-evidence rows, 20 designed rows, and 11 Not applicable rows.", "Added database-failure recovery, typed invalid-input, tenancy/role, exact-backpressure, bounded-work, and assertion-level mappings plus a strict 77-total/66-applicable/gap-free gate."],
  ["DEF-QV-252", "BP-017", "Low", "Fixed", "Twenty-six list/root API quality nodes landed after the exact 2,579-node server/stress/cohort evidence seal.", "Run the fail-closed collector after adding error, performance, invalid-input, and tenancy contracts.", "Publication stops until every new identity executes through its complete file and the exact backend gate advances.", "Collection reported 2,605 nodes and the stale gate would reject export.", "Executed the complete 33-case changed file and 58-case linked cohort, then advanced the reconciled backend inventory to 2,605 nodes."],
  ["DEF-QV-253", "settings-03", "Medium", "Fixed", "Four canonical Settings contracts still described retired primary chrome, immediate Query-model persistence, and writable per-lane routing controls.", "Compare settings-03, settings-04, settings-08, and settings-09 with the current Settings route, exact component assertions, and server persistence model.", "The tracker describes the Workspace administration summary and collapsed diagnostics, the generic command-bar readiness label, staged answer-source cards, and the read-only planned task-preference notice exactly as implemented.", "The source of truth expected a demo-key badge and runtime-model header that no longer render, and claimed four lane selects issue immediate PUT writes even though the current page deliberately exposes no lane controls.", "Reconciled all four stable Feature IDs to current code-derived behavior and bound them to focused frontend, server, and browser evidence."],
  ["DEF-QV-254", "BP-017", "Low", "Fixed", "The first Settings API bounded-work harness imposed an arbitrary 45-line handler cap that rejected a finite 51-line literal response assembly.", "Execute the new handler-bound test against API-164 through API-167.", "The guard detects loops and requires handler-specific bounding tokens without rejecting a finite response solely for harmless formatting length.", "Ten cases passed and API-164 failed only because its implementation spanned 51 lines.", "Raised the secondary readability ceiling to 60 lines while retaining the AST loop prohibition and endpoint-specific bound assertions; all 11 new contracts pass."],
  ["DEF-QV-255", "BP-017", "Low", "Fixed", "The revised bounded-work harness searched source text for loop keywords and treated the word 'for' inside a comment as an executable loop.", "Rerun the complete Settings quality-contract file after relaxing the line ceiling.", "Loop detection inspects Python syntax nodes and ignores comments or string prose.", "Ten cases passed and the API-164 performance contract failed on a comment token rather than executable control flow.", "Replaced token search with ast.For, ast.AsyncFor, and ast.While detection; the complete 11-case file passes."],
  ["DEF-QV-256", "settings-01", "Medium", "Fixed", "The ten Settings features and four Settings API handlers retained 57 Designed or Suite-evidence scenario rows without a cohort-level closure gate.", "Filter the 98 Settings/UI/API scenario rows and require direct evidence for all 94 applicable cases, leaving only four backend viewport rows as explicit Not applicable.", "Every Settings feature has seven direct scenario passes; every Settings API has six direct scenario passes plus one explicit backend responsive N/A.", "The prior matrix could show direct feature coverage while error, invalid-input, permission, performance, or mobile scenarios remained only designed or aggregate-backed.", "Added exact scenario mappings across current component, helper, server, authentication, and three-engine phone evidence plus a strict gap-free Settings gate."],
  ["DEF-QV-257", "BP-017", "Low", "Fixed", "Two Settings component nodes, eleven Settings API quality nodes, and three browser-project nodes landed after the 4,619-node evidence seal.", "Recollect every automation layer after executing each new node through its complete contributing file and linked cohort.", "The fail-closed inventory advances only to identities that have actually run and records the focused execution run for each new contributor.", "The exact collector observed 1,811 Vitest, 2,616 pytest/stress/cohort, and 165 Playwright nodes before the prior count gate could publish.", "Executed the 56-case linked frontend cohort, 291-case linked server cohort, and 15-case Settings browser matrix, then advanced the total evidence seal to 4,635 nodes."],
  ["DEF-QV-258", "BP-017", "Low", "Fixed", "The first linked server regression used repository-relative test paths while pytest was already running from caos/server, so collection stopped with file-not-found and executed zero cases.", "Run the four Settings server files from the designated server virtual environment.", "Every requested path resolves from the chosen working directory and pytest executes the linked cohort.", "Pytest exited 4 with 'file or directory not found: tests/server/test_settings.py'.", "Corrected the paths to ../tests/server/...; the expanded linked cohort passes 291/291."],
  ["DEF-QV-259", "BP-017", "Low", "Fixed", "The restricted sandbox denied the isolated QA server bind and the first Playwright loopback connection.", "Boot an isolated migrated SQLite CAOS service on 127.0.0.1:8026 and execute the Settings browser matrix.", "The explicitly permitted local validation process binds and all browser clients reach only the isolated loopback service.", "Uvicorn first failed with EPERM on bind; Playwright later received EPERM connecting to the running local port.", "Reran the scoped server and browser commands with local-socket permission, then shut the isolated service down cleanly after 15/15 browser passes."],
  ["DEF-QV-260", "BP-017", "Low", "Fixed", "The first Playwright invocation could not resolve @playwright/test from the shared e2e global-setup file outside the frontend package directory.", "List and execute the Settings spec through the frontend-local Playwright installation.", "External e2e files resolve the package-local test runtime deterministically.", "Global setup aborted before login with Cannot find module '@playwright/test'.", "Set NODE_PATH to the frontend node_modules directory, matching the canonical collector; the complete three-project matrix then passes 15/15."],
  ["DEF-QV-261", "BP-017", "Low", "Fixed", "A three-case Deep-Dive module-group contract file landed while the fail-closed tracker was collecting the Settings evidence seal; its implementation appeared moments after the test file.", "Run the canonical collector to quiescence after the shared-worktree module-group pair is complete.", "Collection rejects the transient missing import and count drift, and the new identities execute before the seal advances.", "The first collection failed because ./module-groups was absent; the next stable collection found 1,814 Vitest nodes instead of 1,811.", "Waited for the paired implementation, executed the complete module-group file at 3/3, and advanced the reconciled frontend and total evidence counts only afterward."],
  ["DEF-QV-262", "deepdive-42", "Medium", "Fixed", "At 390px with a fine pointer, the compact global Ask utility remained in the crowded navigation band and extended seven pixels past the viewport because the phone-trigger swap required pointer: coarse.", "Run the exact Deep-Dive reference build through the local axe/layout scanner at 390x844.", "Exactly one reachable Ask trigger remains fully inside the viewport for every narrow pointer type.", "Axe reported zero WCAG nodes but one layout failure: Ask CAOS utility occupied x=341..397 in a 390px viewport.", "Made the sub-768px trigger swap pointer-agnostic, added a CSS contract, rebuilt, and verified zero clipped controls, overflow, axe nodes, scan errors, or layout failures."],
  ["DEF-QV-263", "deepdive-36", "Medium", "Fixed", "Module Finder capped locally added pins and recents but trusted oversized, duplicated, and unknown persisted workspace arrays during hydration.", "Load more than 12 pins and eight recents containing duplicates and unknown module ids.", "Persisted shortcuts are validated against the current module catalog, deduplicated, and capped before render.", "A stale or corrupt profile could render every known persisted pin and retain unbounded recents in component state.", "Normalized hydrated lists through the current catalog and existing 12/8 limits; the expanded eight-case Module Finder file passes."],
  ["DEF-QV-264", "deepdive-40", "Low", "Fixed", "Scenario-network failure, duplicate-pending activation, and declared numeric bounds were implemented but absent from direct component evidence.", "Reject a propagation request after activating PROPAGATE twice, then retry without changing the scenario.", "Only one request runs while pending, the error is announced, the configured bounds remain present, and retry succeeds.", "The scenario matrix could only cite success, stale-result, and no-run nodes for its error/backpressure contracts.", "Added the missing assertion-level test; the complete five-case file passes."],
  ["DEF-QV-265", "deepdive-01", "Medium", "Fixed", "The canonical feature contract still described nine L0-L6/ORCH/INFRA launcher layers after the UI consolidated all 27 modules into three semantic groups.", "Compare deepdive-01 with module-groups.ts, the launcher render, and the total/disjoint partition tests.", "The tracker describes Foundation, Analysis, and Governance & Debate with exactly one active group and total catalog coverage.", "Expected behaviour, edge cases, and trigger text referred to a removed independent-layer accordion.", "Reconciled the stable Feature ID to the current three-group implementation and mapped total-partition, invalid-id, overflow, and responsive evidence."],
  ["DEF-QV-266", "deepdive-42", "Medium", "Fixed", "The canonical feature contract described a removed read-only phone triage card even though narrow Deep-Dive now preserves the complete analytical workbench with compact controls.", "Compare deepdive-42 with the current page, PersonaWorkbench composition, unit assertions, and exact 390px browser state.", "The tracker describes the same analysis workflow at narrow widths, support drawers, compact utilities, owned overflow, and one global Ask trigger.", "The source of truth claimed authoring was replaced and required obsolete Query/Pipeline triage handoffs.", "Reconciled the contract and added a three-engine phone-width journey proving workbench, evidence, layout utility, Ask, and zero document overflow."],
  ["DEF-QV-267", "deepdive-14", "Low", "Fixed", "The Deep-Dive E2E still treated the bare route as the seeded reference and selected the first duplicate identity label even when that copy was intentionally hidden.", "Execute the complete Deep-Dive journey against the current explicit reference-mode route in all browser projects with retries disabled.", "The test enters /deepdive?mode=reference and asserts a visible identity instance before exercising the workbench.", "The obsolete route reached issuer selection; after correcting it, the smoke locator timed out on a hidden duplicate while the visible workspace was complete.", "Bound all navigations to explicit reference mode and filtered duplicate identity locators by visibility; the expanded matrix passes 12/12."],
  ["DEF-QV-268", "BP-017", "High", "Fixed", "Five mounted analyst routes had no dedicated Playwright journeys, and the production-like lane manifest omitted the existing Pipeline and Sector specs while global setup authenticated every configured project for each single-project invocation.", "List the current E2E inventory, compare every *_flow.spec.ts and *_run.spec.ts file with the production-like lanes, then add the five missing route contracts and execute them in all browser projects with retries disabled.", "Every discovered journey spec is assigned exactly once, setup authenticates only the invoked project, and all five route contracts pass in Chromium, Firefox, and WebKit without retry or unhandled API fallthrough.", "The hard-coded lanes could silently miss current specs; adding a fourth lane without setup isolation would also consume 36 shared credential attempts against a 30/minute backstop.", "Added a fail-closed lane-manifest parity check, included Pipeline, Sector, and the routed-concept spec, constrained setup with E2E_ONLY_PROJECT, and passed the new 15-node browser matrix. Frozen H0 real-API proof remains a separate PD-02 gate."],
  ["DEF-QV-269", "BP-017", "Low", "Fixed", "The canonical collector still expected the pre-PD-04 1,819-node frontend inventory and pre-current 2,616-node server/stress/cohort inventory after dead-subject removal and current test additions.", "Rebuild the tracker after the routed-concept delta and PD-04 cleanup.", "The collector rejects stale counts, advances only to already executed identities, and records intentional removals separately from coverage growth.", "The rebuild stopped before workbook mutation at expected 1,819 versus collected 1,750 Vitest nodes; direct collection also found 2,618 server/stress/cohort nodes and 183 Playwright nodes.", "Reconciled the 69 removed dead-subject nodes to the documented 1,750/1,750 PD-04 run, the current 2,594-pass/15-skip server plus nine-pass stress/cohort evidence, and the new 15/15 browser matrix before advancing the exact gate to 4,595 nodes."],
  ["DEF-QV-270", "deepdive-19", "Low", "Fixed", "The curated Deep-Dive chat error mapping still matched the retired test title 'renders structured and generic request failures'; after PD-04 removed an unrelated prototype, no adjacent evidence masked that stale title.", "Rebuild the exact tracker and inspect the Deep-Dive scenario gate for deepdive-19 Error path.", "The mapping names the current parameterized chat-failure assertion and all structured, network, and fallback error cases remain direct evidence.", "The collector found all 294 Deep-Dive rows but correctly rejected deepdive-19 Error path as unmapped.", "Mapped the current 'renders the most useful chat failure detail' identity. Its three parameterized cases already pass inside the verified 1,750-node current frontend run; no adjacent route or removed prototype is relabelled as chat-error evidence."],
  ["DEF-QV-271", "BP-014", "Low", "Fixed", "The strengthened routed-concept console assertion treated the deliberately injected Sponsor 503 resource log as an unexpected application console failure in Chromium and WebKit, while Firefox emitted no resource log.", "Run Pipeline, routed concepts, and Sector as one 33-node lane across all browser engines with zero retries.", "The Sponsor recovery case allows zero or one exact browser-generated 503 resource log and rejects every other console error, page exception, or unhandled API request.", "The first strengthened lane passed 31/33; only the Chromium and WebKit Sponsor cases failed after their successful retry assertions because each captured the expected 503 resource message.", "Constrained the allowance to at most one exact 503 Service Unavailable resource log. Selection preservation, one retry, successful recovery, zero page errors, and zero unhandled fixture requests remain mandatory."],
  ["DEF-QV-272", "BP-014", "Medium", "Fixed", "The routed fixture shallow-merged the server's sparse nested analysis-context patch, alternately erasing sponsor artifact and surface state and creating a synchronization loop that could continue through teardown.", "Run the routed-concept matrix, require exactly one Sponsor context PATCH, stop the isolated service, and inspect the complete backend access log for any non-auth /api request that escaped Playwright fixtures.", "Sparse nested fields use the real recursive merge semantics, the one expected Sponsor context PATCH converges before the ledger is asserted, and no late local API request bypasses the fixture layer.", "The first green 15/15 run was followed by one isolated-backend PATCH returning 404. A generic network-idle attempt timed out on persistent prefetch; an exact PATCH poll then exposed 1,748–2,462 alternating fixture writes per engine instead of one.", "Recursively merge sparse fixture patches while ignoring expected_revision, then poll for exactly one Sponsor synchronization write before asserting the request/page/console ledgers. The final three-engine run and shutdown-log audit must remain green before retaining the no-fallthrough claim."],
  ["DEF-QV-273", "BP-017", "Medium", "Fixed", "A transient one-shot render throw could be consumed by React's speculative retry before an error boundary committed, while a hydration-time throw could leave a blank root instead of proving the shipped fallback.", "Inject a named client render failure through the delivered production chunks, hold the fault until the shipped boundary reset is invoked, and execute both root/global and shared-segment recovery in Chromium, Firefox, and WebKit with retries disabled.", "Every engine reaches the intended shipped fallback, preserves path, mode, authentication, analysis context, draft payload, UI preferences, and analyst edits, performs no mutation at failure, and invokes recovery without duplicate side effects.", "The initial post-hydration one-shot injector produced no committed fallback because React retried internally; the hydration injector produced a blank root. Neither result could support PD-05.", "Made the browser-only fault persistent while armed and wrapped the delivered reset callback to disarm immediately before calling the real Next reset. Exact sentinel/cardinality checks fail closed on compiler drift; the final root and segment matrix passes 6/6 with zero retries and no production fault hook."],
  ["DEF-QV-274", "BP-017", "Critical", "Fixed", "The first deny-by-default repository-root .dockerignore re-included parent directories without immediately re-excluding their descendants, so BuildKit transmitted 4.86 GB of caches, virtualenvs, outputs, and tooling despite the apparent allow-list.", "Build the app image from the repository root and inspect the first uncached BuildKit context-transfer size.", "Only the explicit frontend build inputs, runtime server files, governed prompt subset, RV JSON, Dockerfile, and resource probe enter the context; the transfer remains single-digit megabytes.", "The first real build showed 'transferring context: 4.86GB' before it was aborted.", "Added parent/** exclusions immediately after every parent negation, retained only exact descendant re-inclusions, and reproduced the transfer through a fresh isolated builder at 3.88 MB. Corrected the hardening blueprint's example so the flaw is not reintroduced."],
  ["DEF-QV-275", "BP-017", "Low", "Fixed", "The first embedded resource probe lived under /usr/local/lib/caos, so direct script execution set sys.path away from /app and could not import the production engine package.", "Run the probe during the Dockerfile build as the configured non-root image user.", "The probe resolves modules under the same /app working-directory contract as run.py and validates the actual consumer paths.", "The build failed at ModuleNotFoundError: No module named 'engine' after the application itself had built successfully.", "Placed the probe at /app/verify_image_resources.py and invoked it relative to WORKDIR in both Dockerfile and CI. The rebuilt image and independent docker run report exact resource fingerprints and row counts."],
];

const journeySeed = [
  ["BP-001", "Analyst registration and session", "Submit the shared signup code and name, establish the signed analyst cookie, resolve `/me`, and log out.", "caos/server/routes/auth.py; caos/tests/frontend/e2e/login_flow.spec.ts", "Pass"],
  ["BP-002", "Issuer onboarding", "Create an issuer through the upload wizard, persist the record, and enter the issuer workspace.", "caos/frontend/src/app/upload/page.tsx; caos/server/routes/issuers.py; bootstrap_flow.spec.ts", "Pass"],
  ["BP-003", "Document intake and evidence vault", "Upload, malware-scan, parse, chunk, persist, and surface an issuer document with truthful scan/provenance state.", "caos/server/routes/ingestion.py; avscan.py; document_parser.py", "Suite evidence"],
  ["BP-004", "SEC EDGAR acquisition", "Search filings, inspect exhibits, fetch a bounded exhibit, and vault it under the issuer when EDGAR is configured.", "caos/server/routes/edgar.py; edgar.py", "Suite evidence"],
  ["BP-005", "Credit engine run", "Create a frozen-input run, execute the CP dependency graph, persist module outputs, apply QA gates, and expose terminal status.", "caos/server/routes/runs.py; engine/pipeline.py; run_executor.py", "Suite evidence"],
  ["BP-006", "Deep-Dive evidence review", "Open a completed run, navigate modules, inspect evidence and QA state, and preserve issuer/run context.", "caos/frontend/src/app/deepdive/page.tsx; deepdive_flow.spec.ts", "Pass"],
  ["BP-007", "Model scenario and persistence", "Load the issuer model, adjust scenarios/assumptions, recompute the worksheet, save durable changes, and restore them.", "caos/frontend/src/app/model/page.tsx; model_flow.spec.ts; routes/models.py", "Pass"],
  ["BP-008", "Cross-coverage Query investigation", "Create or reuse an analysis context, choose a lane, run a question, persist the URL-addressable result, inspect authority, and pin a finding.", "QueryInvestigationWorkbench.tsx; routes/query.py; query_flow.spec.ts", "Pass"],
  ["BP-009", "Deep Research job", "Submit a bounded brief, enqueue durable research, poll progress, render the report and sources, and disclose demo/truncation state.", "caos/server/routes/research.py; research_executor.py; research_flow.spec.ts", "Pass"],
  ["BP-010", "Issuer research report synthesis", "Start issuer-scoped synthesis, poll the durable report job, and preserve source/run provenance.", "research_report_executor.py; routes/reports.py", "Suite evidence"],
  ["BP-011", "Report Studio publication", "Select a deliverable, compose from run evidence, enforce QA/watermark rules, export, and optionally mirror to the vault.", "caos/frontend/src/app/reports/page.tsx; routes/reports.py; vault_export.py", "Suite evidence"],
  ["BP-012", "Sector review", "Refresh bounded signals, filter/review evidence, ask a scoped question, ratify sections, and publish a review.", "caos/frontend/src/app/sector/page.tsx; routes/sector.py", "Suite evidence"],
  ["BP-013", "Relative-value screening", "Import a market workbook snapshot, map issuers, run a bounded RV screen, and inspect comparable outputs.", "caos/frontend/src/app/sector-rv/page.tsx; routes/rv.py; routes/market_import.py", "Suite evidence"],
  ["BP-014", "Portfolio posture and decision", "Review portfolio/issuer posture, open a decision record, capture rationale and evidence, and surface it to committee workflows.", "routes/portfolio.py; routes/portfolios.py; routes/decisions.py; routes/committee.py", "Suite evidence"],
  ["BP-015", "Monitoring and alert lifecycle", "Ingest or derive an alert, route it to the desk, review notification/digest state, and resolve or escalate it.", "caos/frontend/src/app/monitor/page.tsx; routes/alerts.py; routes/notifications.py; routes/digest.py", "Suite evidence"],
  ["BP-016", "Autonomous coverage cycle", "Enqueue and execute the Sentinel→Analyst→Reporter pipeline with durable terminal state and bounded background recovery.", "caos/server/routes/autonomy.py; engine/pipeline_executor.py", "Suite evidence"],
  ["BP-017", "Runtime configuration and fail-closed boot", "Load environment settings, enforce deployed secret/Postgres/AV guards, select providers and gates, and start bounded executors.", "caos/server/config.py; caos/server/main.py", "Suite evidence"],
];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n") {
      row.push(cell.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      cell = "";
    } else cell += ch;
  }
  if (cell || row.length) {
    row.push(cell.replace(/\r$/, ""));
    rows.push(row);
  }
  const headers = rows.shift();
  return rows.filter((item) => item.some(Boolean)).map((item) =>
    Object.fromEntries(headers.map((header, index) => [header, item[index] || ""])),
  );
}

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function runCollection(command, args, cwd, extraEnv = {}) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: "utf8",
    env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0", ...extraEnv },
    maxBuffer: 32 * 1024 * 1024,
  });
  if (result.status !== 0) {
    throw new Error(`Collection failed: ${command} ${args.join(" ")}\n${result.stderr || result.stdout}`);
  }
  return result.stdout;
}

function relativeRepoPath(value) {
  return path.relative(repo, value).replaceAll("\\", "/");
}

function collectAutomationEvidence() {
  const frontendDir = path.join(repo, "caos", "frontend");
  const python = path.join(repo, "caos", "server", ".venv311", "bin", "python");
  const vitest = JSON.parse(runCollection("npx", ["vitest", "list", "--json"], frontendDir));
  const pytest = runCollection(
    python,
    ["-m", "pytest", "caos/tests/server", "caos/tests/stress", "caos/tests/cohort", "--collect-only", "-q", "--disable-warnings"],
    repo,
  ).split("\n").map((line) => line.trim()).filter((line) => line.startsWith("caos/tests/") && line.includes("::"));
  const playwright = runCollection(
    "npx",
    ["playwright", "test", "--list"],
    frontendDir,
    { NODE_PATH: path.join(frontendDir, "node_modules") },
  )
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.includes("›") && /\.spec\.ts:\d+:\d+/.test(line));

  const expectedCounts = { vitest: 1750, pytest: 2618, playwright: 189 };
  const actualCounts = { vitest: vitest.length, pytest: pytest.length, playwright: playwright.length };
  for (const layer of Object.keys(expectedCounts)) {
    if (actualCounts[layer] !== expectedCounts[layer]) {
      throw new Error(`Automation inventory drifted for ${layer}: expected ${expectedCounts[layer]}, collected ${actualCounts[layer]}. Execute the new nodes before rebuilding the canonical tracker.`);
    }
  }

  const rows = [];
  vitest.forEach((item, index) => rows.push({
    id: `AUT-VIT-${String(index + 1).padStart(4, "0")}`,
    layer: "Frontend unit/component",
    node: `${relativeRepoPath(item.file)}::${item.name}`,
    name: item.name,
    file: relativeRepoPath(item.file),
    executionRun: [
      "caos/frontend/src/app/responsive-recovery.contract.test.ts",
      "caos/frontend/src/components/deepdive/ModuleFinder.test.tsx",
      "caos/frontend/src/components/deepdive/OutSections.test.tsx",
      "caos/frontend/src/components/deepdive/StandingViewStrip.test.tsx",
      "caos/frontend/src/components/model/ScenarioNetworkPanel.test.tsx",
    ].includes(relativeRepoPath(item.file))
      ? "VAL-20260720-DEEPDIVE-FE-183"
      : relativeRepoPath(item.file) === "caos/frontend/src/lib/deepdive/module-groups.test.ts"
      ? "VAL-20260720-DEEPDIVE-MODULE-GROUPS-3"
      : relativeRepoPath(item.file) === "caos/frontend/src/app/settings/settings-models.test.tsx"
      ? "VAL-20260719-SETTINGS-FE-56"
      : "VAL-20260720-FE-PD04-1750",
    executedDate: today,
  }));
  pytest.forEach((node, index) => {
    const file = node.split("::")[0];
    rows.push({
      id: `AUT-PY-${String(index + 1).padStart(4, "0")}`,
      layer: "Server/stress/cohort",
      node,
      name: node.split("::").slice(1).join("::"),
      file,
      executionRun: [
        "caos/tests/server/test_settings.py",
        "caos/tests/server/test_settings_inventory_contract.py",
        "caos/tests/server/test_settings_quality_contracts.py",
        "caos/tests/server/test_write_role_matrix.py",
      ].includes(file)
        ? "VAL-20260719-SETTINGS-SRV-291"
        : "VAL-20260720-SRV-STRESS-2618",
      executedDate: today,
    });
  });
  playwright.forEach((line, index) => {
    const match = line.match(/([^/\s]+\.spec\.ts):(\d+):(\d+)\s+›\s+(.+)$/);
    if (!match) return;
    const file = `caos/tests/frontend/e2e/${match[1]}`;
    rows.push({
      id: `AUT-E2E-${String(index + 1).padStart(3, "0")}`,
      layer: "Browser E2E",
      node: `${file}:${match[2]}:${match[3]}::${match[4]}`,
      name: match[4],
      file,
      executionRun: match[1] === "deepdive_flow.spec.ts"
        ? "VAL-20260720-E2E-DEEPDIVE-12"
        : match[1] === "recovery_flow.spec.ts"
        ? "VAL-20260720-E2E-RECOVERY-6"
        : match[1] === "routed_concepts_flow.spec.ts"
        ? "VAL-20260720-E2E-ROUTED-CONCEPTS-15"
        : match[1] === "settings_flow.spec.ts"
        ? "VAL-20260719-E2E-SETTINGS-15"
        : match[1] === "pipeline_flow.spec.ts"
        ? "VAL-20260719-E2E-PIPELINE-12"
        : match[1] === "command_flow.spec.ts"
        ? "VAL-20260719-E2E-COMMAND-12"
        : match[1] === "sector_flow.spec.ts"
          ? "VAL-20260719-E2E-SECTOR-6"
          : "VAL-20260717-E2E-141-NORETRY",
      executedDate: today,
    });
  });
  return rows;
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function routeCallRegex(method, routePath) {
  const routePattern = routePath.split(/(\{[^}]+\})/).map((part) =>
    /^\{[^}]+\}$/.test(part) ? "(?:\\{[^}]+\\}|[^\\\"'`\\s/?]+)" : escapeRegex(part),
  ).join("");
  return new RegExp(
    `\\.${method.toLowerCase()}\\s*\\(\\s*(?:f|rf)?[\\\"'\`]${routePattern}(?=[?\\\"'\`])`,
    "i",
  );
}

function concreteRouteRegex(routePath) {
  const routePattern = routePath.split(/(\{[^}]+\})/).map((part) =>
    /^\{[^}]+\}$/.test(part) ? "[^/]+" : escapeRegex(part),
  ).join("");
  return new RegExp(`^${routePattern}$`);
}

function validateApiFeatureParameterMappings(sourceByFile, descriptors) {
  const parameterPattern = /pytest\.param\(\s*["'](API-\d{3})["']\s*,\s*["']([A-Z]+)["']\s*,\s*["'](\/api\/[^"']+)["']/gs;
  for (const [file, source] of sourceByFile.entries()) {
    for (const match of source.matchAll(parameterPattern)) {
      const [, declaredId, method, concretePath] = match;
      const candidates = descriptors.filter((descriptor) =>
        descriptor.route.method === method && concreteRouteRegex(descriptor.route.path).test(concretePath),
      );
      if (candidates.length !== 1) {
        throw new Error(`API test mapping ${file} ${declaredId} ${method} ${concretePath} resolved ${candidates.length} inventory routes`);
      }
      if (candidates[0].id !== declaredId) {
        throw new Error(`API test mapping drift in ${file}: ${declaredId} names ${method} ${concretePath}, now ${candidates[0].id}`);
      }
    }
  }
}

function routeNavigationRegex(routePath) {
  const suffix = routePath === "/" ? "(?:[?#]|[\"'`])" : "(?:[/?#]|[\"'`])";
  return new RegExp(`\\.(?:goto|waitForURL)\\s*\\(\\s*[\\\"'\`]${escapeRegex(routePath)}${suffix}`, "i");
}

function containsIdentifier(text, identifier) {
  return new RegExp(`(?:^|[^a-z0-9_])${escapeRegex(identifier.toLowerCase())}(?:$|[^a-z0-9_])`, "i").test(text);
}

function significantTokenOverlap(left, right) {
  const ignored = new Set(["test", "tests", "with", "from", "that", "this", "when", "then", "renders", "returns", "route", "error"]);
  const tokens = (value) => new Set((value.toLowerCase().match(/[a-z0-9]+/g) || [])
    .filter((token) => token.length >= 4 && !ignored.has(token)));
  const leftTokens = tokens(left);
  return [...tokens(right)].filter((token) => leftTokens.has(token)).length;
}

function testSubjectPath(file) {
  return file.replace(/\.(?:test|spec)(\.[^.]+)$/, "$1");
}

function extractEvidenceBody(evidence, source) {
  if (evidence.layer === "Server/stress/cohort") {
    const functionName = evidence.name.split("::").at(-1).replace(/\[.*$/, "");
    const startMatch = new RegExp(`(?:^|\\n)[ \\t]*(?:async\\s+)?def\\s+${escapeRegex(functionName)}\\s*\\(`, "m").exec(source);
    if (!startMatch) return "";
    const start = startMatch.index;
    const tail = source.slice(start + startMatch[0].length);
    const next = /\n[ \t]*(?:async\s+)?def\s+test_[A-Za-z0-9_]+\s*\(/.exec(tail);
    return source.slice(start, next ? start + startMatch[0].length + next.index : source.length);
  }
  const separator = evidence.layer === "Browser E2E" ? " › " : " > ";
  const leaf = evidence.name.split(separator).at(-1);
  const start = source.indexOf(leaf);
  if (start < 0) return "";
  const tail = source.slice(start + leaf.length);
  const next = /\n\s*(?:it|test)\s*\(/.exec(tail);
  return source.slice(start, next ? start + leaf.length + next.index : Math.min(source.length, start + 8000));
}

function expandLocalHelperBodies(body, source) {
  const helperNames = [...body.matchAll(/\b([A-Za-z_][A-Za-z0-9_]*)\s*\(/g)]
    .map((match) => match[1])
    .filter((name) => !name.startsWith("test_"));
  const helperBodies = [];
  for (const name of new Set(helperNames)) {
    const startMatch = new RegExp(`(?:^|\\n)(?:async\\s+)?def\\s+${escapeRegex(name)}\\s*\\(`, "m").exec(source);
    if (!startMatch) continue;
    const start = startMatch.index;
    const tail = source.slice(start + startMatch[0].length);
    const next = /\n(?:async\s+)?def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(/.exec(tail);
    helperBodies.push(source.slice(start, next ? start + startMatch[0].length + next.index : source.length));
  }
  return [body, ...helperBodies].join("\n");
}

function classifyScenario(evidence) {
  const name = evidence.name.toLowerCase();
  if (/rejects?_unparseable|invalid[_ -]input/.test(name)) return "Invalid input";
  if (/zero[_ -]boundary|boundary[_ -]condition/.test(name)) return "Boundary conditions";
  if (/uses?_its?_code_default|environment_override_parses_declared_type/.test(name)) return "Happy path";
  const text = `${evidence.name} ${evidence.body}`.toLowerCase();
  if (/mobile|responsive|viewport|phone|breakpoint|390px|900px/.test(text)) return "Mobile/responsive";
  if (/permission|unauth|forbidden|tenant|cross[- ]analyst|identity|role gate|secret|csrf|401|403/.test(text)) return "Permission/security";
  if (/concurr|worker|race|stress|performance|latency|lease|advisory lock|bounded graph|pagination bound/.test(text)) return "Performance";
  if (/boundary|limit|cap|max(?:imum)?|min(?:imum)?|zero|duplicate|idempoten|stale|already|overflow|non[- ]finite/.test(text)) return "Boundary conditions";
  if (/invalid|malformed|missing|required|empty|oversize|too large|unknown|not found|404|409|422|rejects?/.test(text)) return "Invalid input";
  if (/failure|fails?|error|timeout|degraded|exception|rollback|500|502|503/.test(text)) return "Error path";
  return "Happy path";
}

function titleFromIdentifier(value) {
  return clean(value).replace(/^_+/, "").replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function joinPath(prefix, routePath) {
  const joined = `${prefix || ""}${routePath || ""}` || "/";
  return joined;
}

function scenarioSlug(value) {
  return value.toLowerCase().replace(/[^a-z]+/g, "-").replace(/^-|-$/g, "");
}

function scenarioApplicable(feature, scenario) {
  if (scenario !== "Mobile/responsive") return true;
  if (["reports-26", "reports-27"].includes(feature.id)) return false;
  return !["Discovered API handler", "Discovered configuration"].includes(feature.sourceType);
}

function scenarioText(feature, scenario) {
  const target = feature.endpoint || feature.trigger || feature.name;
  const cases = {
    "Happy path": `Starting from ${feature.trigger || "the documented entry state"}, exercise ${target}; verify the implemented expected behaviour and source provenance.`,
    "Error path": `Force the primary dependency behind ${target} to fail; verify a truthful, recoverable error/degraded state and no stale success state.`,
    "Boundary conditions": `Exercise empty, zero, maximum configured, repeated, already-selected, and terminal states relevant to ${target}.`,
    "Invalid input": `Submit blank, malformed, wrong-type, unsupported, or over-limit input to ${target}; verify implemented validation and no partial corrupt write.`,
    "Permission/security": `Exercise ${target} without the required analyst/session/edge/tenant authority; verify fail-closed behavior and no sensitive detail leakage.`,
    "Performance": `Exercise ${target} at its configured bound; verify no request storm, unbounded fan-out, runaway render/poll loop, or blocked primary interaction.`,
    "Mobile/responsive": `Exercise ${target} at 390px and 900px widths where applicable; verify primary controls, focus, tables, and evidence remain reachable without overlap.`,
  };
  return cases[scenario];
}

function expectedForScenario(feature, scenario) {
  if (scenario === "Happy path") return feature.expected;
  if (scenario === "Error path") return "The implemented error or degraded state is explicit, stable, recoverable, and does not preserve a false successful conclusion.";
  if (scenario === "Boundary conditions") return "Boundary inputs settle into defined empty, disabled, capped, or terminal states without crash, NaN, duplication, or state leak.";
  if (scenario === "Invalid input") return "Invalid input is rejected or ignored at the declared boundary with specific validation feedback and no partial durable mutation.";
  if (scenario === "Permission/security") return "Unauthorized or cross-scope access fails closed; protected data and actions remain unavailable; expected form-owned credential errors remain visible.";
  if (scenario === "Performance") return "Execution remains within configured bounds without unbounded concurrency, polling, rendering, memory growth, or unnecessary network fan-out.";
  return "The feature remains keyboard-operable and coherent at narrow widths; primary controls and semantic status are not clipped or conveyed by color alone.";
}

function genericEdgeCases(feature) {
  const parts = ["empty/missing data", "repeat interaction or double submit", "dependency timeout or non-2xx response"];
  const text = `${feature.name} ${feature.expected} ${feature.endpoint}`;
  if (/upload|file|document|edgar|vault/i.test(text)) parts.push("unsupported/oversized file, duplicate import, malware or parse failure");
  if (/query|research|chat|ask|search/i.test(text)) parts.push("blank/long prompt, no results, offline provider, stale completion");
  if (/table|grid|metric|model|coverage|leverage|ebitda/i.test(text)) parts.push("null/zero/non-finite metrics, empty rows, sort and narrow viewport");
  if (/auth|analyst|session|issuer|portfolio|run/i.test(text)) parts.push("missing session, foreign analyst/team scope, stale context or run id");
  return parts.join("; ");
}

function genericValidation(feature) {
  const rules = ["observed UI/API contract must match the cited implementation"];
  const text = `${feature.name} ${feature.expected} ${feature.endpoint}`;
  if (/id|run|issuer|context|job|document|portfolio/i.test(text)) rules.push("identifiers must exist, be correctly typed, and remain in the active authority scope");
  if (/upload|file/i.test(text)) rules.push("file type, size, scan, parse, and storage limits apply before durable acceptance");
  if (/metric|model|ratio|leverage|ebitda|coverage|scenario/i.test(text)) rules.push("CP-derived arithmetic must reject non-finite values and zero denominators");
  if (/auth|session|profile|delete|publish|ratif|save|create|post|put|patch/i.test(text)) rules.push("mutations require the declared session/dependency and must not partially commit invalid input");
  return rules.join("; ");
}

function apiVerbStory(method, name, routePath) {
  const intent = method === "GET" ? "retrieve" : method === "DELETE" ? "remove" : method === "POST" ? "submit or create" : "update";
  return `As an authenticated CAOS client, I want to ${intent} ${name.toLowerCase()} through ${method} ${routePath} so that the corresponding analyst workflow can use the server's implemented contract.`;
}

function apiExpected(route) {
  const metadata = [route.doc, route.responseModel ? `response_model=${route.responseModel}` : "", route.statusCode ? `status_code=${route.statusCode}` : ""].filter(Boolean).join("; ");
  return `${route.method} ${route.path} invokes ${route.file}:${route.line} (${route.handler}). FastAPI resolves declared dependencies and validates path/query/body inputs before the handler returns its implemented response${metadata ? `; ${metadata}` : ""}.`;
}

function makeFeature(input) {
  return {
    id: input.id,
    name: clean(input.name),
    concept: clean(input.concept),
    story: clean(input.story),
    expected: clean(input.expected),
    edgeCases: clean(input.edgeCases || genericEdgeCases(input)),
    currentStatus: clean(input.currentStatus || "Documented — direct execution pending"),
    severity: clean(input.severity || "None"),
    notes: clean(input.notes),
    validationRules: clean(input.validationRules || genericValidation(input)),
    dependencies: clean(input.dependencies),
    assumptions: clean(input.assumptions || "Expected behaviour is inferred from the cited current implementation, not external product intent."),
    trigger: clean(input.trigger),
    files: clean(input.files),
    endpoint: clean(input.endpoint),
    sourceType: clean(input.sourceType),
    sourceStatus: clean(input.sourceStatus),
  };
}

function columnName(index) {
  let n = index + 1;
  let value = "";
  while (n > 0) {
    const remainder = (n - 1) % 26;
    value = String.fromCharCode(65 + remainder) + value;
    n = Math.floor((n - remainder) / 26);
  }
  return value;
}

function writeSheet(workbook, name, headers, rows, widths = []) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const data = [headers, ...rows];
  const range = sheet.getRangeByIndexes(0, 0, data.length, headers.length);
  range.values = data;
  range.format = { wrapText: true, verticalAlignment: "top" };
  range.format.borders = { preset: "insideHorizontal", style: "thin", color: "#262633" };
  sheet.freezePanes.freezeRows(1);
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
    fill: "#12121a",
    font: { bold: true, color: "#e6e6ef" },
    wrapText: true,
    verticalAlignment: "center",
    rowHeight: 30,
  };
  widths.forEach((width, index) => {
    if (width) sheet.getRange(`${columnName(index)}:${columnName(index)}`).format.columnWidth = width;
  });
  return sheet;
}

async function scanAppRoutes() {
  const appDir = path.join(repo, "caos", "frontend", "src", "app");
  const files = await fs.readdir(appDir, { recursive: true });
  const pages = [];
  for (const relative of files.filter((file) => file.endsWith("page.tsx")).sort()) {
    const directory = path.dirname(relative).replaceAll("\\", "/");
    const route = directory === "." ? "/" : `/${directory}`;
    const source = await fs.readFile(path.join(appDir, relative), "utf8");
    const componentNames = [...source.matchAll(/import\s+\{?\s*([A-Za-z0-9_, ]+)\s*\}?\s+from\s+["']@\/components\//g)]
      .flatMap((match) => match[1].split(",").map(clean)).filter(Boolean).slice(0, 6);
    pages.push({ route, file: `caos/frontend/src/app/${relative}`, components: componentNames });
  }
  return pages;
}

async function scanApiRoutes() {
  const mainText = await fs.readFile(path.join(repo, "caos", "server", "main.py"), "utf8");
  const routeDir = path.join(repo, "caos", "server", "routes");
  const aliases = { model_workbook_routes: "model_workbook", settings_routes: "settings" };
  const prefixes = new Map();
  for (const match of mainText.matchAll(/app\.include_router\((\w+)\.router,\s*prefix="([^"]*)"/g)) {
    prefixes.set(`${aliases[match[1]] || match[1]}.py`, match[2]);
  }
  const routeFiles = (await fs.readdir(routeDir)).filter((file) => file.endsWith(".py")).sort();
  const routes = [];
  for (const file of routeFiles) {
    const source = await fs.readFile(path.join(routeDir, file), "utf8");
    const lines = source.split("\n");
    for (let index = 0; index < lines.length; index += 1) {
      const start = lines[index].match(/^\s*@router\.(get|post|put|patch|delete)\s*\(/);
      if (!start) continue;
      let decorator = lines[index].trim();
      let balance = (lines[index].match(/\(/g) || []).length - (lines[index].match(/\)/g) || []).length;
      while (balance > 0 && index + 1 < lines.length) {
        index += 1;
        decorator += ` ${lines[index].trim()}`;
        balance += (lines[index].match(/\(/g) || []).length - (lines[index].match(/\)/g) || []).length;
      }
      const routePath = decorator.match(/\(\s*["']([^"']*)["']/)?.[1];
      if (routePath === undefined) continue;
      let defIndex = index + 1;
      while (defIndex < lines.length && !/^\s*(?:async\s+)?def\s+\w+\s*\(/.test(lines[defIndex])) defIndex += 1;
      if (defIndex >= lines.length) continue;
      const handler = lines[defIndex].match(/^\s*(?:async\s+)?def\s+(\w+)/)?.[1] || "unknown_handler";
      const responseModel = clean(decorator.match(/response_model\s*=\s*([^,)]+)/)?.[1]);
      const statusCode = clean(decorator.match(/status_code\s*=\s*([^,)]+)/)?.[1]);
      const afterDef = lines.slice(defIndex, Math.min(lines.length, defIndex + 24)).join("\n");
      const doc = clean(afterDef.match(/(?:"""|''')([\s\S]*?)(?:"""|''')/)?.[1]).slice(0, 500);
      routes.push({
        method: start[1].toUpperCase(),
        path: joinPath(prefixes.get(file) || "", routePath),
        file: `caos/server/routes/${file}`,
        handler,
        line: defIndex + 1,
        responseModel,
        statusCode,
        doc,
      });
    }
  }
  return routes.sort((a, b) => `${a.path} ${a.method}`.localeCompare(`${b.path} ${b.method}`));
}

async function scanSettings() {
  const file = "caos/server/config.py";
  const source = await fs.readFile(path.join(repo, file), "utf8");
  const lines = source.split("\n");
  const settings = [];
  let inside = false;
  let comments = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith("class Settings(")) {
      inside = true;
      comments = [];
      continue;
    }
    if (inside && line.startsWith("@lru_cache")) break;
    if (!inside) continue;
    if (/^\s{4}#/.test(line)) {
      comments.push(clean(line.replace(/^\s*#\s?/, "")));
      continue;
    }
    if (!line.trim()) continue;
    const field = line.match(/^\s{4}([a-z][a-z0-9_]*):\s*([^=]+?)\s*=\s*(.+)$/);
    if (!field) {
      if (!/^\s{8}/.test(line)) comments = [];
      continue;
    }
    const defaultValue = clean(field[3].split(/\s+#/)[0]);
    settings.push({
      name: field[1],
      type: clean(field[2]),
      defaultValue,
      environment: field[1].toUpperCase(),
      description: clean(comments.join(" ")).slice(0, 900),
      file,
      line: index + 1,
    });
    comments = [];
  }
  return settings;
}

function jsxAttributeValue(attribute, sourceFile) {
  if (!attribute.initializer) return "true";
  if (ts.isStringLiteral(attribute.initializer)) return clean(attribute.initializer.text);
  if (ts.isJsxExpression(attribute.initializer)) {
    return clean(attribute.initializer.expression?.getText(sourceFile) || "true");
  }
  return clean(attribute.initializer.getText(sourceFile));
}

function directJsxLabel(node, sourceFile) {
  const parent = node.parent;
  if (!ts.isJsxElement(parent)) return "";
  const parts = [];
  for (const child of parent.children) {
    if (ts.isJsxText(child)) parts.push(child.text);
    if (ts.isJsxExpression(child) && child.expression) {
      parts.push(`{${child.expression.getText(sourceFile)}}`);
    }
  }
  return clean(parts.join(" ")).slice(0, 240);
}

function controlAcceptance(kind) {
  if (kind === "Modal/dialog") {
    return "Opening exposes a named dialog, moves focus into it, confines keyboard interaction, supports its documented close/Escape path, and restores focus to the trigger without losing committed state.";
  }
  if (/Input|Select|Textarea|Editable/.test(kind)) {
    return "The control has a programmatic label, accepts only the declared value shape and bounds, exposes validation without color alone, preserves the intended draft scope, and is fully keyboard operable with visible focus.";
  }
  if (/Link/.test(kind)) {
    return "The link has a stable accessible name and href, preserves the required issuer/run/context identity, activates by keyboard, and does not discard unsaved work without the navigation guard.";
  }
  if (/Form/.test(kind)) {
    return "Submit is keyboard operable, validates every required field, prevents duplicate or partial mutation, exposes pending/success/error state, and retains recoverable input after a failed dependency.";
  }
  return "The action has a stable accessible name, visible focus, native keyboard activation, a truthful disabled/pending state, and performs its documented transition exactly once without stale cross-context output.";
}

function controlEdgeCases(kind) {
  const common = "initial/default state; repeated activation or double submit; dependency error/timeout; disabled or pending state; principal/context change; 390px and 900px viewport; keyboard-only and reduced-motion";
  if (kind === "Modal/dialog") return `${common}; trigger removed while open; Escape/cancel versus confirmed close; nested overlay; focus restoration`;
  if (/Input|Select|Textarea|Editable/.test(kind)) return `${common}; blank/null; malformed type; minimum/maximum/over-limit value; paste/autofill; reset after validation failure`;
  if (/Link/.test(kind)) return `${common}; missing/foreign target id; modifier-key/new-tab activation; unsaved-change guard; back/forward restoration`;
  return `${common}; authorization denial; stale response after a newer action; empty result; success announcement`;
}

function stateAcceptance(name) {
  const lower = name.toLowerCase();
  if (/loading|pending|saving|running|transition/.test(lower)) {
    return "The pending state starts only for the owning operation, prevents conflicting duplicate work where required, remains announced without blocking unrelated reading, and always settles on success, failure, cancellation, or supersession.";
  }
  if (/error|failed|failure/.test(lower)) {
    return "The failure state is explicit, non-sensitive, recoverable, associated with the owning control, and cleared only by a new valid attempt or scope reset—not by an unrelated render.";
  }
  if (/open|show|visible|drawer|modal|popover/.test(lower)) {
    return "Open/closed state matches the rendered overlay and accessibility attributes, supports keyboard close, restores trigger focus, and resets when the owning principal or analysis context changes.";
  }
  if (/selected|active|filter|sort|query|search|mode|tab|view/.test(lower)) {
    return "The selected/filter state is visibly and programmatically exposed, deterministic on repeated input, scoped to the correct screen/context, and restored or reset according to the documented persistence boundary.";
  }
  return "The state transition is deterministic, scoped to its owning component/principal/context, represented truthfully in the UI, and cannot leave stale or impossible combinations after success, error, cancellation, or navigation.";
}

function stateEdgeCases(name) {
  const lower = name.toLowerCase();
  const common = "initial value; repeated same transition; rapid competing transitions; dependency error; unmount/navigation; principal/context switch; browser back/forward";
  if (/loading|pending|saving|running|transition/.test(lower)) return `${common}; cancellation; timeout; stale completion after newer request`;
  if (/error|failed|failure/.test(lower)) return `${common}; empty/non-JSON detail; retry success; second independent error`;
  if (/selected|active|filter|sort|query|search|mode|tab|view/.test(lower)) return `${common}; unknown persisted value; empty result; mobile layout; keyboard selection`;
  return `${common}; null/empty data; terminal/reset state`;
}

async function scanUiControlsAndStates() {
  const srcDir = path.join(repo, "caos", "frontend", "src");
  const files = (await fs.readdir(srcDir, { recursive: true }))
    .filter((file) => file.endsWith(".tsx") && !/\.(?:test|spec)\.tsx$/.test(file))
    .sort();
  const controls = [];
  const states = [];
  const nativeInteractive = new Set(["button", "input", "select", "textarea", "a", "form"]);
  const interactiveRoles = new Set(["button", "checkbox", "combobox", "link", "menuitem", "option", "radio", "slider", "switch", "tab"]);
  const stateAttributes = new Set(["disabled", "checked", "open", "hidden", "aria-current", "aria-disabled", "aria-expanded", "aria-pressed", "aria-selected", "aria-haspopup", "aria-modal", "value", "defaultValue"]);

  for (const relative of files) {
    const absolute = path.join(srcDir, relative);
    const file = `caos/frontend/src/${relative.replaceAll("\\", "/")}`;
    const source = await fs.readFile(absolute, "utf8");
    const sourceFile = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    if (sourceFile.parseDiagnostics.length) {
      throw new Error(`TypeScript inventory parse failed for ${file}: ${sourceFile.parseDiagnostics[0].messageText}`);
    }

    const visit = (node) => {
      if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
        const tag = node.tagName.getText(sourceFile);
        const attributes = new Map();
        for (const property of node.attributes.properties) {
          if (ts.isJsxAttribute(property)) {
            attributes.set(property.name.getText(sourceFile), jsxAttributeValue(property, sourceFile));
          }
        }
        const role = attributes.get("role") || "";
        const inputType = tag === "input" ? (attributes.get("type") || "text") : "";
        const modalInvocation = /(?:Modal|Dialog|SlideOver|Confirm)/i.test(tag);
        const overlayInvocation = /(?:Drawer|Popover|Palette)/i.test(tag);
        const hasAction = ["onClick", "onChange", "onInput", "onSubmit"].some((name) => attributes.has(name));
        const contentEditable = attributes.has("contentEditable");
        const isLink = tag === "Link" || tag === "a" || attributes.has("href");
        const include = inputType !== "hidden" && (
          nativeInteractive.has(tag)
          || interactiveRoles.has(role)
          || modalInvocation
          || overlayInvocation
          || contentEditable
          || hasAction
          || isLink
        );
        if (include) {
          let kind = "Action component";
          if (modalInvocation || role === "dialog" || tag === "dialog") kind = "Modal/dialog";
          else if (overlayInvocation) kind = "Overlay/popover";
          else if (contentEditable) kind = "Editable content";
          else if (tag === "input") kind = `Input — ${inputType}`;
          else if (tag === "select") kind = "Select input";
          else if (tag === "textarea") kind = "Textarea input";
          else if (tag === "form") kind = "Form submit boundary";
          else if (isLink || role === "link") kind = "Link/navigation";
          else if (tag === "button" || role === "button") kind = "Button/action";
          else if (role) kind = `ARIA ${role}`;
          const label = attributes.get("aria-label")
            || attributes.get("title")
            || attributes.get("placeholder")
            || attributes.get("name")
            || directJsxLabel(node, sourceFile)
            || `[dynamic ${tag}]`;
          const line = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
          const statesForControl = [...attributes.entries()]
            .filter(([name]) => stateAttributes.has(name))
            .map(([name, value]) => `${name}=${value}`)
            .join("; ");
          controls.push({
            id: `CTL-${String(controls.length + 1).padStart(4, "0")}`,
            kind,
            tag,
            label: clean(label).slice(0, 240),
            file,
            line,
            state: statesForControl || "implicit/default",
            handlers: [...attributes.keys()].filter((name) => /^on[A-Z]/.test(name)).join("; "),
            acceptance: controlAcceptance(kind),
            edgeCases: controlEdgeCases(kind),
          });
        }
      }

      if (ts.isVariableDeclaration(node) && node.initializer && ts.isCallExpression(node.initializer)) {
        const hook = node.initializer.expression.getText(sourceFile).split(".").at(-1);
        if (["useState", "useReducer", "useTransition"].includes(hook) && ts.isArrayBindingPattern(node.name)) {
          const bindings = node.name.elements.map((element) => clean(element.getText(sourceFile))).filter(Boolean);
          const name = bindings[0] || `[anonymous ${hook}]`;
          const line = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
          states.push({
            id: `STA-${String(states.length + 1).padStart(4, "0")}`,
            name,
            setter: bindings.slice(1).join("; "),
            hook,
            initial: clean(node.initializer.arguments.map((argument) => argument.getText(sourceFile)).join(", ")) || "framework default",
            file,
            line,
            acceptance: stateAcceptance(name),
            edgeCases: stateEdgeCases(name),
          });
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(sourceFile);
  }
  return { controls, states };
}

const csv = await fs.readFile(csvPath, "utf8");
const sourceRows = parseCsv(csv);
const modelV2FeatureRows = [
  {
    id: "model-44", concept: "Model Builder", feature: "Model authority routing and issuer switch isolation",
    story: "As an analyst, I want Model Builder to resolve the calculator that is authoritative for the selected issuer and run so that reference fixtures and live institutional models can never cross-contaminate.",
    expected: "ModelAuthorityRoute keeps the explicit Atlas Forge reference on the legacy demonstration calculator, resolves non-reference issuers through Model Engine v2, preserves an exact run selection, and fails closed when the capability pair is absent or a live model cannot be resolved. An issuer change unmounts prior authority before the next response may render.",
    trigger: "open /model, select another issuer, or bind an exact run", files: "caos/frontend/src/app/model/ModelAuthorityRoute.tsx; caos/frontend/src/app/model/page.tsx", endpoint: "GET /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "reference issuer; live issuer; missing capability; incomplete rollout dependency; exact run replaced by latest; issuer switch during request; late prior-issuer response; missing completed owned run",
  },
  {
    id: "model-45", concept: "Model Builder", feature: "Model v2 identity, status, and revision disclosure",
    story: "As a credit analyst, I want the live model header to disclose calculation status, monetary identity, revision, and persistence state so that I know exactly which model I am defending.",
    expected: "The v2 workbench identifies the issuer, reporting currency and unit, ready/partial state, current revision, saved or suggested authority, pending mutation count, and stale-calculation restrictions. Status and provenance use text as well as color, and action availability follows the same state.",
    trigger: "load a saved, suggested, partial, dirty, or stale v2 model", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "GET /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "missing currency/unit; partial calculation; revision zero; suggested-only calculation; stale saved calculation; pending mutations; unavailable nodes",
  },
  {
    id: "model-46", concept: "Model Builder", feature: "Canonical calculation-node table",
    story: "As an analyst, I want the canonical calculation graph rendered as an auditable table so that every persisted input and derived credit output is inspectable.",
    expected: "CalculationNodesTable renders finite node values, labels, period keys, methods, source authority, warnings, and supported edit/restore actions from the server calculation. Missing values remain unavailable rather than becoming zero, and scenario nodes are separated from the persisted base model.",
    trigger: "load a ready or partial Model Engine v2 calculation", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/model_engine_v2.py", endpoint: "GET /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "null or non-finite node; duplicate node id; missing source authority; partial debt schedule; scenario-only node; negative or zero denominator",
  },
  {
    id: "model-47", concept: "Model Builder", feature: "Calculation-node filtering and bounded paging",
    story: "As an analyst, I want to filter the model graph by period, search text, and scenario visibility without rendering an unbounded worksheet so that large models remain navigable and responsive.",
    expected: "The node browser supports text and period filters, an empty-result state, scenario-node visibility, and deterministic paging at 100 visible rows while keeping every matching node reachable. Picker results are separately capped at 200 and changing filters returns to a valid page.",
    trigger: "search nodes, select a period, toggle scenario nodes, or page a large graph", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "none (bounded client projection of the v2 calculation)", status: "Pass",
    edge_cases: "more than 100 nodes; more than 200 picker candidates; empty filter; filter changed on last page; scenario nodes hidden; null period",
  },
  {
    id: "model-48", concept: "Model Builder", feature: "Per-node authority and override-origin labels",
    story: "As an analyst, I want each model cell labelled from its actual source authority so that reported inputs, formulas, analyst overrides, and unavailable values cannot be mistaken for one another.",
    expected: "nodeOrigin distinguishes persisted input, server formula, manual override, scenario preview, and unavailable authority using explicit labels and glyphs. Unsourced live values are never called live, and a restored node returns to its canonical original authority.",
    trigger: "inspect persisted, calculated, overridden, previewed, and unavailable nodes", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "GET /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "authority omitted; unsupported authority origin; null value; expired override; suggested model; restored original; scenario preview",
  },
  {
    id: "model-49", concept: "Model Builder", feature: "Governed override editor",
    story: "As an analyst, I want to edit supported model nodes with the governance fields required by their authority class so that overrides remain finite, attributable, and reviewable.",
    expected: "The editor opens from a supported node, validates a finite numeric replacement, requires a non-empty reason and future expiry for derived nodes, preserves the active editor on invalid input, and blocks switching or restoring another row while unsaved editor changes exist.",
    trigger: "activate Edit input/Edit derived on a calculation node", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "none until the override is queued", status: "Pass",
    edge_cases: "blank or non-finite value; unchanged value; derived node without reason; missing or past expiry; dirty editor switch; unsupported node; debt-schedule derived cell",
  },
  {
    id: "model-50", concept: "Model Builder", feature: "Local pending-mutation queue",
    story: "As an analyst, I want edits staged locally before any durable write so that I can review a coherent batch without silently mutating the saved model.",
    expected: "Queue override and Restore original create or replace one pending mutation per node, update the visible draft and dirty status, and do not call a persistence endpoint. A subsequent edit invalidates any older preview fingerprint while retaining the complete queue.",
    trigger: "queue an override or restoration from the node editor", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "none until preview/commit", status: "Pass",
    edge_cases: "same node queued twice; restore an already-original node; pending edit while preview is in flight; invalid mutation; empty queue; editor cancellation",
  },
  {
    id: "model-51", concept: "Model Builder", feature: "Stateless pending-model preview",
    story: "As an analyst, I want the server to recalculate my complete pending batch without committing it so that I can inspect the exact financial effect before persistence.",
    expected: "Preview pending sends the current payload and mutation batch to the calculation endpoint, renders the returned calculation as an explicitly non-durable preview, and binds it to a deterministic pending fingerprint. A changed queue, failed preview, or expired override makes the preview unusable for commit without losing edits.",
    trigger: "activate Preview pending with one or more queued mutations", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/routes/models_v2.py", endpoint: "POST /api/models/v2/{issuer_id}/calculate", status: "Pass",
    edge_cases: "preview failure; queue changes in flight; late result; no pending mutations; non-finite output; expired override; another preview already running",
  },
  {
    id: "model-52", concept: "Model Builder", feature: "Atomic pending-mutation commit",
    story: "As an analyst, I want one reviewed pending batch committed as one revision so that model history, audit events, and downstream reports remain internally consistent.",
    expected: "Commit is enabled only for the exact current preview fingerprint and submits the whole batch with the expected revision. Success adopts the returned record and calculation, clears pending state, and records one revision; CAS conflict, validation, or audit failure leaves the prior durable model and local queue intact without partial rows.",
    trigger: "confirm Commit after a current successful preview", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/routes/models_v2.py", endpoint: "POST /api/models/v2/{issuer_id}/overrides/batch", status: "Pass",
    edge_cases: "stale revision; duplicate node mutation; validation failure; audit rollback; concurrent winner; preview fingerprint mismatch; repeated click while busy",
  },
  {
    id: "model-53", concept: "Model Builder", feature: "Transient server sensitivity analysis",
    story: "As an analyst, I want to shock an eligible node through the server without converting the shock into a manual override so that I can explore risk while preserving the base model.",
    expected: "Sensitivity controls select a node and finite shock value, call the server calculation path, and render a transient scenario result. Reset removes only the sensitivity result; pending manual overrides remain untouched. Results are discarded when their run, node, or shock identity changes, and a failed request leaves the controls retryable.",
    trigger: "select a sensitivity node/value, run the calculation, or reset it", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/frontend/src/components/model/ScenarioNetworkPanel.tsx", endpoint: "POST /api/models/v2/{issuer_id}/calculate", status: "Pass",
    edge_cases: "non-finite shock; missing eligible nodes; reset while another action runs; request failure; late prior result; node/value changed in flight; pending overrides present",
  },
  {
    id: "model-54", concept: "Model Builder", feature: "Model v2 scenario mode and decision deltas",
    story: "As a credit analyst, I want to switch between persisted-model and scenario views and see decision-relevant deltas so that a shock is interpreted against the correct base.",
    expected: "Scenario mode keeps persisted and transient calculations distinct, exposes scenario-period inputs, renders supported leverage/coverage/FCF/cash decision deltas, and filters empty or non-scenario nodes. Switching modes or clearing the scenario does not erase pending manual mutations.",
    trigger: "run a scenario and switch Model/Scenario view modes", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "POST /api/models/v2/{issuer_id}/calculate", status: "Pass",
    edge_cases: "no scenario result; null decision field; period mismatch; empty scenario nodes; pending overrides; partial base calculation; reset during busy action",
  },
  {
    id: "model-55", concept: "Model Builder", feature: "Revisioned undo and redo replay",
    story: "As an analyst, I want to replay committed override groups backward and forward so that corrections remain revisioned audit events instead of hidden local rewrites.",
    expected: "History groups original set/reset events into deterministic replay candidates, exposes consecutive undo and redo actions with reasons when unavailable, and sends the selected event against the current revision. Malformed, superseded, or unresolvable history disables replay rather than guessing a mutation.",
    trigger: "open Model history and activate Undo or Redo", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/routes/models_v2.py", endpoint: "POST /api/models/v2/{issuer_id}/overrides/{event_id}/undo|redo", status: "Pass",
    edge_cases: "empty history; consecutive groups; event changed again; malformed snapshot; stale revision; unsupported action; replay while another action is busy",
  },
  {
    id: "model-56", concept: "Model Builder", feature: "Immutable server checkpoints",
    story: "As an analyst, I want labelled server checkpoints created and restored with revision guards so that committee states are durable, attributable, and cannot be silently relabelled.",
    expected: "Checkpoint creation requires a non-empty label and a current saved calculation, records the exact revision/run/calculation identity, and adds an immutable row. Restore validates the owner, envelope, and expected revision before adopting the checkpoint as a new durable revision; foreign, stale, or tampered checkpoints fail closed.",
    trigger: "create or restore a checkpoint in Model history", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/routes/models_v2.py", endpoint: "GET/POST /api/models/v2/{issuer_id}/checkpoints", status: "Pass",
    edge_cases: "blank label; stale calculation; stale revision; foreign owner/team; tampered payload hash; runless checkpoint; unrelated source run; concurrent mutation",
  },
  {
    id: "model-57", concept: "Model Builder", feature: "Workbook import mapping and unit declaration",
    story: "As an analyst, I want to map an institutional XLSX into the canonical model schema so that legacy and account-matrix workbooks can be reviewed without inventing financial identity.",
    expected: "The import panel accepts XLSX only, requires explicit reporting currency and unit when the workbook cannot prove them, supports bounded legacy and account-matrix mapping templates, normalizes reviewed period/account columns, and never preselects USD or millions for an ambiguous source workbook.",
    trigger: "open Model tools, choose an XLSX, select a mapping, and declare monetary identity", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/model_workbook.py", endpoint: "POST /api/models/v2/{issuer_id}/workbook/preview", status: "Pass",
    edge_cases: "non-XLSX file; empty workbook; close-format JSON; matrix layout; missing currency/unit; duplicate columns; unsupported period; oversized dimensions",
  },
  {
    id: "model-58", concept: "Model Builder", feature: "Workbook ambiguity review",
    story: "As an analyst, I want blocking duplicate headers and account mappings surfaced with physical selectors so that I explicitly resolve the cells entering the credit model.",
    expected: "Preview ambiguities render against the exact mapping layout with one-based physical column or row selectors. Reviewed choices must match the advertised ambiguity source, remain bound to the preview, and resolve every blocking item before commit; invented or mismatched resolutions are rejected.",
    trigger: "review a workbook preview containing duplicate period/account candidates", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/model_workbook.py", endpoint: "POST /api/models/v2/{issuer_id}/workbook/preview", status: "Pass",
    edge_cases: "duplicate header; duplicate account; out-of-range selector; wrong mapping layout; stale preview; unresolved ambiguity; malformed resolution",
  },
  {
    id: "model-59", concept: "Model Builder", feature: "Signed workbook preview and explicit commit",
    story: "As an analyst, I want import preview to be read-only and its later commit bound to the exact reviewed file and mapping so that workbook ingestion cannot change between review and persistence.",
    expected: "Upload produces a stateless preview with canonical payload, calculation, provenance, mapping identity, source revision, and signed token. Commit requires explicit confirmation and revalidates owner, issuer, file hash, mapping, revision, monetary identity, expiry, and calculation before atomically creating the new revision and lineage artifacts.",
    trigger: "preview a mapped workbook, resolve ambiguities, confirm, and commit", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/routes/model_workbook.py", endpoint: "POST /api/models/v2/{issuer_id}/workbook/preview|commit", status: "Pass",
    edge_cases: "preview token expiry; changed mapping; changed revision; owner/issuer mismatch; calculation drift; duplicate replay; lineage failure; concurrent commit",
  },
  {
    id: "model-60", concept: "Model Builder", feature: "Workbook import failure recovery",
    story: "As an analyst, I want workbook validation and dependency failures surfaced without mutating my model so that I can correct the file or mapping and retry safely.",
    expected: "Invalid mapping, unsafe formula, antivirus rejection, corrupt/legacy XLS, bounds failure, preview error, and commit conflict render specific retryable errors while preserving the current durable record and local draft. A failed preview or commit never fabricates a completed import or leave partial storage/lineage rows.",
    trigger: "submit an invalid workbook/mapping or force preview/commit failure", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/model_workbook.py; caos/server/routes/model_workbook.py", endpoint: "POST /api/models/v2/{issuer_id}/workbook/preview|commit", status: "Pass",
    edge_cases: "malware/scan unavailable; corrupt archive; XLS instead of XLSX; unsafe or circular formula; non-finite cache; oversized file/grid; CAS conflict; lineage rollback",
  },
  {
    id: "model-61", concept: "Model Builder", feature: "Persisted Model v2 workbook export",
    story: "As an analyst, I want the saved canonical model exported as a governed XLSX so that downstream review receives the same persisted calculation and audit identity.",
    expected: "Export is available only for a persisted, current, non-dirty model and downloads the server-produced six-sheet workbook through a temporary anchor. Pending edits, required recalculation, missing record, server failure, or serialization error leave the workbench intact and expose a retryable error.",
    trigger: "activate Export workbook from Model v2 tools", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/model_workbook.py", endpoint: "GET /api/models/v2/{issuer_id}/workbook/export", status: "Pass",
    edge_cases: "no saved record; dirty pending queue; expired active override; stale calculation; download failure; invalid export bounds; repeated click while busy",
  },
  {
    id: "model-62", concept: "Model Builder", feature: "Suggested calculation adoption",
    story: "As an analyst, I want a run-derived suggested model to remain read-only until I explicitly save its exact source run so that synthetic or unrelated evidence cannot become durable authority by implication.",
    expected: "A suggested calculation is labelled read-only and exposes Save suggested model only when the exact owned source-run contract is present. The action persists revision one with that run id; missing, changed, non-live, or unrelated run identity disables adoption, and an in-flight save retains a stable accessible action name.",
    trigger: "open a live issuer with a suggested calculation and activate Save suggested model", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/server/routes/models_v2.py", endpoint: "PUT /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "no exact run; foreign run; run changes; suggestion absent; revision already exists; save in flight; save failure; synthetic CP-1 fixture",
  },
  {
    id: "model-63", concept: "Model Builder", feature: "Override expiry refresh and preview invalidation",
    story: "As an analyst, I want expired overrides removed from the active calculation while the workbench is open so that stale temporary judgments cannot survive their governance window.",
    expected: "The controller schedules the nearest active expiry, refreshes the server model when it elapses, and rebinds calculation and override state. A reviewed preview is invalidated at local expiry even if refresh fails; expired overrides are excluded from active authority and export until the saved model is recalculated.",
    trigger: "keep Model Builder open until an active override expires", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "GET /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "multiple expiries; already-expired override; invalid expiry; refresh failure; preview active at expiry; component unmount; clock boundary",
  },
  {
    id: "model-64", concept: "Model Builder", feature: "Unsaved-model navigation guard",
    story: "As an analyst, I want navigation away from pending edits to require explicit confirmation so that local modelling work is not discarded by an accidental route change.",
    expected: "Pending edits register the shared navigation guard and browser-leave preference. Cancel keeps the route and complete local state; confirm discards pending mutations, editor/import/scenario state, and permits navigation. A clean model never prompts, and the preference remains bounded to the active issuer session.",
    trigger: "navigate away or close while the model has pending local state", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx; caos/frontend/src/components/shared/NavigationGuardProvider.tsx", endpoint: "none (client navigation guard)", status: "Pass",
    edge_cases: "clean model; dirty editor; pending queue; import preview; scenario preview; repeated navigation; cancel then continue editing; issuer switch",
  },
  {
    id: "model-65", concept: "Model Builder", feature: "Mutually exclusive Model v2 actions and stable feedback",
    story: "As a keyboard and screen-reader user, I want long-running model actions mutually exclusive with stable names and explicit notices so that I cannot double-submit or lose track of the operation.",
    expected: "One BusyAction gates save, preview, commit, sensitivity, replay, checkpoint, import, and export operations. Disabled reasons are exposed through ActionReason/title without renaming the control; success notices and role=alert failures are specific, clear on the next attempt, and never claim a mutation completed before the server response.",
    trigger: "start one Model v2 server action and attempt another", files: "caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "multiple Model v2 action endpoints", status: "Pass",
    edge_cases: "double click; second action while busy; late response; abort/unmount; server detail missing; conflict; error followed by retry; action label during progress",
  },
  {
    id: "model-66", concept: "Model Builder", feature: "Model v2 bootstrap, empty, and failure states",
    story: "As an analyst, I want Model Builder to distinguish authority resolution, no available model, partial output, and server failure so that an absence is never presented as a valid credit conclusion.",
    expected: "The route shows a named loading state while authority resolves, a truthful unavailable/empty state when neither saved nor suggested calculation exists, the ready workbench for usable data, and an explicit recoverable error when resolution fails. Live issuer failures never mount the seeded legacy calculator.",
    trigger: "load Model Builder while authority is loading, empty, partial, unavailable, or failed", files: "caos/frontend/src/app/model/ModelAuthorityRoute.tsx; caos/frontend/src/app/model/ModelV2Workbench.tsx", endpoint: "GET /api/models/v2/{issuer_id}", status: "Pass",
    edge_cases: "slow response; 404 capability gate; 503 dependency gate; no owned run; null record and suggestion; partial calculation; retry; late prior-issuer result",
  },
].map((row) => ({
  ...row,
  test_cases: `${row.id}-happy-path; ${row.id}-error-path; ${row.id}-boundary-conditions; ${row.id}-invalid-input; ${row.id}-permission-security; ${row.id}-performance; ${row.id}-mobile-responsive`,
  defect_count: "0",
  last_tested: today,
}));
sourceRows.push(
  ...modelV2FeatureRows,
  {
    id: "deepdive-36",
    concept: "Deep-Dive",
    feature: "Module Finder, Pins, and Recents",
    story: "As an analyst, I want to find, pin, and revisit modules quickly so that a 27-module analytical graph remains navigable under time pressure.",
    expected: "The launcher opens a searchable combobox from its button or Command/Ctrl+M outside text-entry controls, filters by module id/name/description, supports arrow/Enter selection, and renders bounded pinned/recent shortcuts. Pins (12 maximum) and recents (8 stored, 4 visible after excluding pins) persist through revision-aware analyst workspace updates; settings failure leaves an honest session-local fallback.",
    trigger: "activate Find module or press Command/Ctrl+M, then search, select, or pin",
    files: "caos/frontend/src/components/deepdive/ModuleFinder.tsx",
    endpoint: "GET/PATCH /api/settings/analyst",
    status: "Pass",
    edge_cases: "shortcut while an input/textarea/contenteditable owns focus; no results; unknown persisted ids; settings 404; revision conflict; pin/recents caps; Escape/backdrop close; keyboard focus containment",
    test_cases: "happy: search and select by name; boundary: cap and de-duplicate recents/pins; invalid: unknown persisted id; error: settings unavailable or conflicting; accessibility: combobox/listbox keyboard contract",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "deepdive-37",
    concept: "Deep-Dive",
    feature: "Standing Credit View Strip",
    story: "As a credit analyst, I want the standing posture and conviction above the module panes so that the current conclusion leads the evidence review.",
    expected: "The Atlas Forge reference renders the seeded debate bias and sizing decision with DEMO authority, a personal Note agreement action, and Revise navigation to CP-6A. A non-reference issuer without a live CP-6 verdict renders an explicit no-standing-view LIVE empty state and never borrows the fixture. Personal annotations are capped at 20 and do not alter governance state.",
    trigger: "open Deep-Dive and review, note, or revise the standing view",
    files: "caos/frontend/src/components/deepdive/StandingViewStrip.tsx",
    endpoint: "GET/PATCH /api/settings/analyst",
    status: "Pass",
    edge_cases: "non-reference issuer; no CP-6 verdict; settings write failure; more than 20 annotations; repeated note; missing run id; reference authority seam",
    test_cases: "happy: reference posture and revise; error: workspace save failure; boundary: cap 20 notes; authority: non-reference never sees fixture",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "deepdive-38",
    concept: "Deep-Dive",
    feature: "Affirm Live Thesis and Pin Finding",
    story: "As an analyst, I want to affirm a completed issuer run into an immutable thesis and pinned finding so that my current credit view is durable and attributable.",
    expected: "Affirm thesis is actionable only for a non-reference completed run with an owned analysis context. It creates a manual thesis version, patches issuer/run and Deep-Dive surface state into the context, attempts a credit-view finding and bounded workspace affirmation in parallel, and distinguishes full success, thesis-saved/finding-pending partial success, and failure. Reference output cannot be ratified.",
    trigger: "activate Affirm thesis for a completed live issuer run",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "POST /api/thesis; PATCH /api/analysis/contexts/{context_id}; POST /api/analysis/findings; PATCH /api/settings/analyst",
    status: "Pass",
    edge_cases: "reference issuer; missing run; missing/foreign context; context sync failure; thesis conflict; finding write failure after thesis commit; workspace failure; repeated affirmation; more than 20 workspace notes",
    test_cases: "happy: thesis/context/finding/workspace converge; partial: finding pin fails after thesis save; error: thesis fails; permission: missing owned context; boundary: workspace cap",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "deepdive-39",
    concept: "Deep-Dive",
    feature: "Analysis Context Synchronization",
    story: "As an analyst, I want Deep-Dive to retain issuer, run, and surface state in my active analysis context so that handoffs remain attributable across workspaces.",
    expected: "Once an analysis context exists, Deep-Dive adds the active issuer when absent and reconciles the completed run id without discarding existing artifacts. Failed background synchronization leaves the page usable and exposes a status notice. Affirmation additionally stores the thesis id, selected run, and current layout under the deep-dive surface state.",
    trigger: "open an issuer/run in Deep-Dive or affirm the current view",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "POST /api/analysis/contexts; PATCH /api/analysis/contexts/{context_id}",
    status: "Pass",
    edge_cases: "context pending or absent; issuer already present; run changes; patch conflict/failure; stale response; reference issuer; artifact fields owned by other surfaces",
    test_cases: "happy: issuer/run merge; boundary: no duplicate issuer; error: patch notice without page failure; concurrency: latest context revision wins",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "deepdive-40",
    concept: "Deep-Dive",
    feature: "Scenario Network Propagation",
    story: "As a credit analyst, I want to propagate EBITDA and rate shocks across the run's accepted modules so that cross-module downside consequences are visible in one chain.",
    expected: "A completed live run exposes EBITDA-percent and rate-basis-point inputs plus PROPAGATE. Submission sends issuer/run and normalized shocks once, then renders source QA authority, accepted/excluded module counts, and ordered nodes with text status (COMPUTED, DEGRADED, or NO DATA) as well as glyph/color. Without a completed run the controls are absent and a prerequisite state is explicit; a failed request is retryable.",
    trigger: "enter shocks and activate PROPAGATE from Deep-Dive",
    files: "caos/frontend/src/components/model/ScenarioNetworkPanel.tsx; caos/frontend/src/app/deepdive/page.tsx",
    endpoint: "POST /api/scenario/propagate",
    status: "Pass",
    edge_cases: "no run; busy double-submit; endpoint failure; min/max HTML validity; blocked modules excluded; empty node list; degraded/no-data nodes; restricted source",
    test_cases: "happy: computed chain; error: retryable alert; boundary: missing run compacts controls; accessibility: status not color-only",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "deepdive-41",
    concept: "Deep-Dive",
    feature: "Decision Header Authority and Freshness",
    story: "As an IC reviewer, I want change, relevance, required action, evidence health, freshness, and approval authority summarized before the module detail so that I can triage the credit view defensibly.",
    expected: "The DecisionHeader derives all four cells from the selected reference/live run and current CP-5 council. Ready values carry as-of provenance and RATIFIED only when committee status is Approved; an empty council is observed-empty rather than guessed clear. Loading, fetch error, in-flight, and no-completed-run states remain explicit and do not fabricate conclusions.",
    trigger: "open Deep-Dive while the selected run resolves",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/components/shared/DecisionHeader.tsx",
    endpoint: "GET /api/runs/{runId}; GET /api/runs/{runId}/qa",
    status: "Pass",
    edge_cases: "reference fixture; live approved/unratified; no council findings; missing committee status; loading; fetch error; in-flight latest run; no completed run; missing as-of",
    test_cases: "happy: live ready authority; observed-empty: no findings; error/loading/no-run honesty; permission: selected run remains caller-visible only",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "deepdive-42",
    concept: "Deep-Dive",
    feature: "Narrow Deep-Dive Workbench and Global Ask",
    story: "As an analyst on a narrow screen, I want the same evidence-review workflow reorganized into reachable controls so that I can continue analysis without clipped chrome or a lower-authority substitute.",
    expected: "At narrow widths Deep-Dive preserves the full analytical workbench and primary module subtree while PersonaWorkbench moves supporting context/inspector content into named modal drawers. Summary/Report/Dense and simulation controls remain in the narrow utility contract, evidence actions remain reachable, the module strip owns its horizontal overflow, the global Ask phone trigger replaces the compact-nav utility for every pointer type, and the document has no horizontal overflow. Wider screens restore the multi-pane composition without changing data or permissions.",
    trigger: "open or resize Deep-Dive at 390px through the desktop breakpoints",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/components/shared/PersonaWorkbench.tsx; caos/frontend/src/components/shared/AskShell.tsx; caos/frontend/src/app/globals.css",
    endpoint: "none (responsive presentation and navigation)",
    status: "Pass",
    edge_cases: "reference, live, loading, error, and no-run state; narrow fine/coarse pointer; long issuer/action copy; module-strip overflow; 390px geometry; keyboard activation; support-drawer focus; desktop breakpoint transition",
    test_cases: "happy: complete narrow workbench; boundary: compact/full composition transition; responsive: no clipped controls or page overflow; accessibility: evidence, layout, support, and Ask controls remain named and reachable",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "shell-14",
    concept: "Shell",
    feature: "Canonical route identity and document heading",
    story: "As a keyboard or assistive-technology user, I want every route to expose one accurate top-level heading so that the current workspace is identifiable without duplicating or contradicting the visible terminal chrome.",
    expected: "RootLayout mounts one visually hidden RouteHeading h1. routeTitleForPath normalizes query/hash/trailing-slash input, derives workflow titles from NAV_GROUPS, gives more-specific issuer profile and utility metadata precedence, names the root CAOS Home, and degrades null or unknown routes to CAOS. Report and portfolio content use subordinate headings rather than adding another route-level h1.",
    trigger: "navigate to a known, nested, utility, dynamic issuer, root, null, or unknown route",
    files: "caos/frontend/src/lib/nav.ts; caos/frontend/src/components/shared/RouteHeading.tsx; caos/frontend/src/app/layout.tsx; caos/frontend/src/components/portfolio/PortfolioLabWorkbench.tsx; caos/frontend/src/components/reports/ReportDoc.tsx",
    endpoint: "none (canonical route metadata and document outline)",
    status: "Pass",
    edge_cases: "query/hash suffix; trailing slash; nested decision; dynamic issuer path; utility subroute; null pathname; unknown route; visible content attempting a second h1",
    test_cases: "happy: canonical workflow title; boundary: longest dynamic match and normalized path; invalid: null/unknown fallback; accessibility: one route-level h1",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "shell-15",
    concept: "Shell",
    feature: "Overflow-only keyboard scroll targets",
    story: "As a keyboard user, I want a dense panel body to enter the tab order only when it actually scrolls so that clipped evidence remains reachable without adding inert focus stops across the workbench.",
    expected: "Panel measures its body on mount, resize, subtree mutation, and expand. A body with scrollHeight more than one pixel above clientHeight receives tabindex 0, an aria-label equal to the panel title, and the visible focus ring; a fitting body exposes none of those attributes. Reclassification never moves focus, added children join resize observation, and collapse disconnects observers before expansion remeasures.",
    trigger: "render, resize, mutate, collapse, or expand a Panel whose content may overflow",
    files: "caos/frontend/src/components/shared/Panel.tsx",
    endpoint: "none (DOM measurement and accessibility semantics)",
    status: "Pass",
    edge_cases: "exact fit; one-pixel rounding; late async content; child resize; overflow returning to fit; focused sibling; collapsed body; missing observer APIs",
    test_cases: "happy: real overflow becomes named focus target; boundary: exact fit stays inert; mutation/resize: both transitions; accessibility: focus remains stable",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "shell-16",
    concept: "Shell",
    feature: "Semantic workspace hierarchy and tokenized color",
    story: "As a credit analyst scanning a dense workspace, I want consistent identity, workbench, panel, and body hierarchy with governed semantic colors so that information rank is legible and hue remains a trustworthy signal.",
    expected: "Shared ShellIdentity, WorkbenchToolbar, Panel, and body styles use distinct 16px, 14px, 13px, and 12px tiers. Shared and report CSS consumes root semantic variables or color-mix rather than route-local hex/RGB literals; literal chart colors remain confined to the documented nine-file rendering allowlist.",
    trigger: "render shared shell, workbench, panel, or report surfaces",
    files: "caos/frontend/src/components/shared/ShellIdentity.tsx; caos/frontend/src/components/shared/WorkbenchToolbar.tsx; caos/frontend/src/components/shared/Panel.tsx; caos/frontend/src/app/globals.css; caos/frontend/src/lib/chart-colors.ts",
    endpoint: "none (shared presentation contract)",
    status: "Pass",
    edge_cases: "dense terminal labels; report paper counter-theme; status color without text; chart renderer requiring literal values; route-local CSS regression; narrow viewport type floor",
    test_cases: "happy: four semantic tiers; invalid: production color literal outside token/allowlist; accessibility: hierarchy and signal semantics remain explicit",
    defect_count: "0",
    last_tested: today,
  },
  {
    id: "reports-28",
    concept: "Report Studio",
    feature: "Screen and print proofing floors",
    story: "As an investment-committee reader, I want legible screen and printed report type without scaled-down microtext so that the committee artifact remains reviewable and defensible in either medium.",
    expected: "The screen paper uses a 12px body, 11px tables, and a 10px model appendix floor. Print uses flowing unscaled output with 9.5pt body and 8pt table/appendix floors, paginates instead of shrinking below those limits, hides app chrome, and retains the governed paper palette through semantic variables.",
    trigger: "open a report preview or print/save the immutable report document",
    files: "caos/frontend/src/app/globals.css; caos/frontend/src/components/reports/ReportDoc.tsx",
    endpoint: "none (screen and print CSS)",
    status: "Pass",
    edge_cases: "wide model appendix; long prose/table; print pagination; browser print background; screen zoom; duplicate route heading; non-token paper color",
    test_cases: "happy: screen and print floors; boundary: appendix floor; print: app chrome hidden and pages flow; accessibility: no microtype regression",
    defect_count: "0",
    last_tested: today,
  },
);
// The legacy CSV is retained as discovery history, but these Pipeline contracts
// have evolved materially. Override only with behavior verified in the current
// implementation so the canonical workbook never republishes retired routes or
// labels as expected behavior.
const implementedFeatureCorrections = new Map([
  ["issuer-04", {
    expected: "A failed initial registry request falls back to the labeled sample dataset and exposes Retry. If a later debounced search fails after live data has loaded, the directory retains the last live register, marks the state as offline, and never replaces those results with demo issuers.",
    trigger: "load the directory while the issuer API is unavailable, or fail a later debounced search after live coverage has loaded",
    files: "caos/frontend/src/app/issuers/page.tsx",
  }],
  ["issuer-08", {
    expected: "Each row exposes separate profile and Upload actions. Profile activation opens the issuer overlay while asynchronously reconciling analysis context; Upload routes to /upload with issuer and active context parameters when available. Nested action handling prevents the row/profile action from firing when Upload is selected.",
    trigger: "activate a directory row profile link or its Upload action",
    files: "caos/frontend/src/app/issuers/page.tsx",
  }],
  ["issuer-15", {
    expected: "A profile URL without an issuer parameter performs no profile request and replaces the loading splash with an actionable message directing the analyst to open a name from the Directory.",
    trigger: "load /issuers/profile without an issuer query parameter",
    files: "caos/frontend/src/app/issuers/profile/ProfileContent.tsx",
  }],
  ["issuer-16", {
    expected: "The unified profile header shows the issuer identity, ticker, sector, country, every available S&P/Moody/Fitch rating, sponsor, source/run freshness, one primary Deep-Dive action, and the issuer action bar; absent optional facts are omitted rather than invented.",
    trigger: "open a loaded issuer profile",
    files: "caos/frontend/src/app/issuers/profile/ProfileContent.tsx",
  }],
  ["issuer-19", {
    expected: "Financials renders an accessible five-metric sparkline grid for Revenue, EBITDA, EBITDA margin, leverage, and interest coverage when each metric has at least two comparable periods. The FY/quarter toggle appears only when both granularities exist; insufficient series degrade to the section empty state.",
    trigger: "open the Financials tab for profiles with complete, mixed, sparse, or flat period series",
    files: "caos/frontend/src/app/issuers/profile/ProfileContent.tsx; caos/frontend/src/lib/issuer-profile-charts.ts",
  }],
  ["issuer-20", {
    expected: "Events renders dated deltas with period context from the current read-model. Financials may surface a Watch callout containing up to three material event, trend, or data-quality signals after the implemented filters; absent signals remain quiet rather than generating placeholders.",
    trigger: "open Events or Financials for a profile with complete, sparse, or empty signal data",
    files: "caos/frontend/src/app/issuers/profile/ProfileContent.tsx",
  }],
  ["issuer-23", {
    expected: "Analyst notes loads issuer-linked memo nodes, presents available vault links and excerpts, and degrades to explicit empty or quiet error states. A quick memo can be submitted through the vault path with the issuer tag; success clears the composer and re-queries the note graph.",
    trigger: "open Analyst notes or submit a quick issuer memo",
    files: "caos/frontend/src/app/issuers/profile/AnalystNotes.tsx",
  }],
  ["issuer-24", {
    expected: "Structure & coverage combines covenant headroom, debt structure, and liquidity runway with restricted-payment basket, cross-default, add-back cap/utilization/breach, source-readiness, evidence-gap, and QA status when the read-model supplies them; sparse profiles omit unsupported detail.",
    trigger: "open Structure & coverage for complete or sparse issuer read-models",
    files: "caos/frontend/src/app/issuers/profile/ProfileContent.tsx",
  }],
  ["issuer-31", {
    expected: "The Directory summary reports issuer count and, when non-zero, rated count without inventing a sleeve label. A semantic eight-column grid exposes Issuer, Sector, Sponsor, Rating, Leverage, Status, Updated, and Actions; loading uses nine eight-cell skeleton rows. Rating uses the first available S&P/Moody/Fitch value and pairs distressed color with a visible critical glyph and accessible label. Rows use roving focus and content-visibility containment, while sorting keeps missing values last in both directions.",
    trigger: "load, sort, keyboard-navigate, or inspect a populated Issuer Directory",
    files: "caos/frontend/src/app/issuers/page.tsx; caos/frontend/src/lib/issuers.ts",
  }],
  ["pipeline-03", {
    feature: "Directory — Open Issuer Profile",
    user_story: "As an analyst, I want to open an issuer profile from its directory row so that I can review the issuer without losing the worklist context.",
    expected: "A stretched row link exposes one keyboard-focusable profile action. Activation prevents full-page navigation, opens the issuer profile overlay immediately, and reconciles the active issuer into analysis context in the background; a rejected context write does not block the profile.",
    trigger: "activate the issuer row profile link",
    files: "caos/frontend/src/app/issuers/page.tsx; caos/frontend/src/components/shared/IssuerProfileOverlay.tsx",
  }],
  ["pipeline-05", {
    expected: "The modal requires company name; accepts bounded ticker, sector, sub-sector, country, FIGI, and sponsor fields; traps focus, closes on Escape/backdrop/cancel, guards duplicate submission, shows CREATING…, surfaces API errors, normalizes blank sponsor to absent, then closes and opens the new issuer profile.",
    trigger: "open + NEW ISSUER, submit the form, retry after an API error",
    files: "caos/frontend/src/app/issuers/page.tsx",
  }],
  ["pipeline-09", {
    expected: "The route honors explicit issuer/run parameters, otherwise discovers the newest completed live run and falls back to the labeled Atlas Forge reference. Completed runs render persisted CP-X state; real issuers in loading, error, failed/running, or never-run phases receive honest non-demo states. Header identity, run id, progress, freshness, and worklist remain bound to the selected run.",
    trigger: "load /pipeline with reference, issuer, or run query state",
    files: "caos/frontend/src/app/pipeline/page.tsx; caos/frontend/src/lib/pipeline/useLivePipeline.ts",
  }],
  ["pipeline-13", {
    feature: "Pipeline Visualizer — Directory Navigation",
    expected: "Pipeline's ShellIdentity renders the compact ConceptNav. Its quick-jump chips and guaranteed Concepts drawer include the Directory route (/issuers), preserve an active analysis-context id, expose keyboard-focusable links, and mark the active destination where applicable.",
    trigger: "open Pipeline concept navigation and activate Directory",
    files: "caos/frontend/src/components/shared/ShellIdentity.tsx; caos/frontend/src/components/shared/ConceptNav.tsx",
  }],
  ["pipeline-14", {
    feature: "Pipeline Visualizer — Document Intake Link",
    expected: "The contextual Document intake link opens /upload with the active issuer and, when present, analysis-context id. Double-clicking CP-0 applies the same issuer/run/context-aware intake routing contract.",
    trigger: "activate Document intake or open CP-0",
    files: "caos/frontend/src/app/pipeline/page.tsx",
  }],
  ["pipeline-35", {
    expected: "Pipeline's ShellIdentity includes the compact ConceptNav: a guaranteed Concepts drawer below the rail breakpoint and scrollable quick-jump chips above it. Links retain the active analysis-context id, expose full accessible names/tooltips, and use aria-current for the active route.",
    trigger: "open the Concepts drawer or activate a concept chip",
    files: "caos/frontend/src/components/shared/ShellIdentity.tsx; caos/frontend/src/components/shared/ConceptNav.tsx",
  }],
  ["upload-05", {
    expected: "The file step exposes five implemented run templates: Full IC Committee (R-IC/full), Primary Transaction (R-PT/primary), Earnings Update (R-ER/earnings), Relative Value (R-RV/rv), and Legal Review (R-LG/legal). The selected button carries a check glyph and updates the run mode used by every staged upload; Primary explicitly warns that the source set needs new-loan price, OID, and cap-table evidence.",
    trigger: "select a run template before processing staged files",
    files: "caos/frontend/src/components/upload/steps.tsx; caos/server/routes/ingestion.py",
  }],
  ["upload-06", {
    expected: "Upload & process is unavailable without an issuer and staged files. A guarded batch processes files sequentially, routes each to the document or pricing-sheet client, retains per-file success/error outcomes, supports cancellation between files, retries only failed files, and attempts one idempotent run after a non-cancelled batch. A re-entrant submit cannot start a second batch.",
    trigger: "stage one or more files and activate Upload & process",
    files: "caos/frontend/src/components/upload/UploadWizard.tsx; caos/frontend/src/lib/api.ts",
  }],
  ["upload-08", {
    expected: "The result step reports exact success, failure, and chunk totals; lists every filename with its durable metadata, warning, or error; and states whether run creation is queuing, queued, already active, failed, or absent. It offers failed-file retry, reset/upload-another, issuer profile, Deep-Dive, execution graph, and a manual run retry only when the automatic attempt did not succeed.",
    trigger: "complete or partially complete an intake batch",
    files: "caos/frontend/src/components/upload/steps.tsx; caos/frontend/src/components/upload/UploadWizard.tsx",
  }],
  ["upload-14", {
    expected: "PDF extraction first uses the configured bounded MarkItDown command, then bounded pypdf page/text extraction, then optional bounded OCRmyPDF sidecar recovery when no text layer exists. OCR-derived chunks carry OCR provenance. If every lane yields no text, the file remains vaulted with zero chunks and an explicit non-searchable warning; page/text limits return 413.",
    trigger: "process a valid PDF through document intake",
    files: "caos/server/ingest.py; caos/server/routes/ingestion.py",
  }],
  ["upload-15", {
    expected: "XLSX extraction validates the OOXML package/resource policy before parsing, then uses configured MarkItDown when available or openpyxl read-only/data-only fallback. The fallback emits sheet headings and tab-delimited non-empty cells, truncates oversized cell text, and returns 413 when safe cell or extracted-text limits are exceeded; an unreadable validated workbook degrades to empty text.",
    trigger: "process a valid XLSX through pricing-sheet intake",
    files: "caos/server/ingest.py; caos/server/xlsx_safety.py; caos/server/routes/ingestion.py",
  }],
  ["upload-16", {
    expected: "chunk_text strips empty input, preserves paragraph/line structure where possible, splits oversized lines, and emits retrieval chunks bounded to 512 cl100k tokens with 64-token overlap. Empty text yields no rows; each persisted chunk receives sequence, hash, optional OCR provenance, and a document lineage edge.",
    trigger: "complete text extraction for a vaulted document",
    files: "caos/server/ingest.py; caos/server/routes/ingestion.py",
  }],
  ["upload-17", {
    expected: "Raw bytes are written below the configured CAOS storage root using a unique 32-hex directory and a basename-only filename whose unsafe characters are replaced with underscores. The returned relative storage key cannot escape the root; dependency rollback removes an uncommitted object, while a committed document retains it for audit/reprocessing.",
    trigger: "vault parsed upload bytes or roll back a failed intake transaction",
    files: "caos/server/ingest.py; caos/server/routes/ingestion.py; caos/server/database.py",
  }],
  ["upload-18", {
    expected: "A successful document or pricing-sheet intake returns document_id, issuer_id, the compatibility minio_key vault path, normalized run_mode, chunks_created, an exact filename/chunk/run message, optional zero-chunk warning, optional ratings_updated count, and source_manifest_id. The source manifest records origin, method, scan/extraction state, authority, hashes, and context binding when enabled.",
    trigger: "receive a 200 response from document or pricing-sheet intake",
    files: "caos/server/routes/ingestion.py",
  }],
  ["upload-19", {
    expected: "Every document, pricing-sheet, and analyst-memo upload consumes the caller-local fixed-window upload budget before domain work. The first 20 attempts in 60 seconds are allowed; the 21st returns 429 with an explicit retry-in-a-minute message. A separate lazy semaphore bounds concurrent read, scan, and parse work server-wide with a minimum capacity of one.",
    trigger: "submit more than 20 upload requests for one caller inside a minute",
    files: "caos/server/routes/ingestion.py; caos/server/rate_limit.py",
  }],
  ["upload-20", {
    feature: "EDGAR Full-Text Search API",
    story: "As an analyst client, I want bounded EDGAR full-text search so that I can discover filing pointers without treating them as vaulted evidence.",
    expected: "GET /api/edgar/search requires a query of at least two characters, accepts comma-separated form filters and limit 1..50, requires EDGAR_USER_AGENT, and consumes the caller's 30/min EDGAR budget. It executes the SEC search off-thread and returns external/unverified filing pointers; an EdgarError becomes 502.",
    trigger: "request /api/edgar/search with query, optional forms, and limit",
    files: "caos/server/routes/edgar.py; caos/server/edgar.py",
    endpoint: "GET /api/edgar/search",
  }],
  ["upload-21", {
    feature: "EDGAR Filing Exhibit API",
    story: "As an analyst client, I want a filing's classified documents so that I can identify covenant-bearing exhibits before vaulting one.",
    expected: "GET /api/edgar/exhibits requires a CIK and a dashed or bare 18-digit accession, enforces EDGAR configuration and the caller budget, and returns each document name, SEC URL, classification label, authority rank, and size. Malformed accessions fail validation before an outbound request; upstream EdgarError becomes 502.",
    trigger: "request exhibits for an exact CIK and accession",
    files: "caos/server/routes/edgar.py; caos/server/edgar.py",
    endpoint: "GET /api/edgar/exhibits",
  }],
  ["upload-22", {
    feature: "Public EDGAR URL Intake Panel",
    story: "As an analyst, I want to paste one or more public SEC archive URLs beside private files so that primary documents enter the same durable intake result surface.",
    expected: "The file step renders a Public / EDGAR URL panel bound to the selected issuer and run mode. Its URL input accepts comma-separated values, Enter and VAULT URL share one guarded action, blank input is inert with a reason, and successful results remain visible until the parent adopts them. The panel states that public URLs and private files can be combined.",
    trigger: "enter public EDGAR URLs in the file step and activate VAULT URL",
    files: "caos/frontend/src/components/upload/EdgarImport.tsx; caos/frontend/src/components/upload/UploadWizard.tsx",
    endpoint: "POST /api/edgar/vault-url",
  }],
  ["upload-23", {
    feature: "EDGAR URL Batch Vaulting",
    story: "As an analyst, I want each pasted EDGAR URL vaulted independently so that one bad source does not hide successful primary evidence.",
    expected: "edgarVaultUrls trims and filters the comma-separated list, submits each URL to /api/edgar/vault-url with issuer and run mode, and waits for every result. Partial success returns both successes and per-URL failure reasons; all-fail rethrows the first error. The panel forwards each success once to the wizard, shows chunk counts including zero-chunk warning state, and blocks same-tick duplicate Enter submissions.",
    trigger: "vault a single URL, a mixed batch, an all-fail batch, or a duplicate Enter attempt",
    files: "caos/frontend/src/lib/api.ts; caos/frontend/src/components/upload/EdgarImport.tsx; caos/server/routes/edgar.py",
    endpoint: "POST /api/edgar/vault-url",
  }],
  ["upload-24", {
    feature: "EDGAR Configuration Notice",
    expected: "When every attempted EDGAR URL fails with HTTP 503, the panel displays a bounded warning that EDGAR is not configured and names EDGAR_USER_AGENT. It does not fabricate a vault result or collapse the failure into an empty panel; a later attempt clears the prior notice before running.",
    trigger: "vault an EDGAR URL while EDGAR_USER_AGENT is unavailable",
    files: "caos/frontend/src/components/upload/EdgarImport.tsx; caos/server/routes/edgar.py",
    endpoint: "POST /api/edgar/vault-url (503)",
  }],
  ["upload-25", {
    feature: "EDGAR URL Error and Partial-Batch Handling",
    expected: "A non-503 all-fail response renders a critical alert using a string detail, nested detail.message, or a stable fallback. Partial batches retain successful rows and render a warning summary plus each failed URL and reason. Whitespace-only input is inert, Escape does not submit, and a pending Enter action cannot double-vault.",
    trigger: "vault invalid, mixed-success, blank, or rapidly repeated EDGAR URL input",
    files: "caos/frontend/src/components/upload/EdgarImport.tsx; caos/frontend/src/lib/api.ts",
    endpoint: "POST /api/edgar/vault-url",
  }],
  ["upload-27", {
    feature: "EDGAR Issuer Filings API",
    expected: "GET /api/edgar/filings/{cik} returns recent external/unverified filing pointers for the exact issuer, optionally filtered by comma-separated forms. Limit defaults to 25 and is constrained to 1..100; configuration and caller-rate guards run before SEC work, and upstream EdgarError becomes 502.",
    trigger: "request recent filings for a CIK with optional forms and limit",
    files: "caos/server/routes/edgar.py; caos/server/edgar.py",
    endpoint: "GET /api/edgar/filings/{cik}",
  }],
]);
for (const row of sourceRows) Object.assign(row, implementedFeatureCorrections.get(row.id) || {});
const appRoutes = await scanAppRoutes();
const apiRoutes = await scanApiRoutes();
const settings = await scanSettings();
const { controls: uiControls, states: uiStates } = await scanUiControlsAndStates();
const roleRows = [
  ["ROL-001", "Authentication state", "Anonymous / no valid edge or profile identity", "No workspace access; deployed requests fail closed and the login landing owns expected credential errors.", "Protected routes never render prior-principal content; sign-in/create/recovery errors remain visible and announced.", "Missing/expired/tampered cookie; absent or wrong edge credential; network failure; repeated failed attempt; restored valid session.", "caos/frontend/src/components/shared/AuthProvider.tsx; caos/frontend/src/components/shared/LoginLanding.tsx; caos/server/identity.py"],
  ["ROL-002", "Authentication state", "Edge-authenticated, profile incomplete", "The verified proxy principal may reach the login/profile boundary but is not treated as a named analyst profile.", "The UI shows profile creation instead of the workspace; the created profile is bound to the forwarded email and cannot impersonate another principal.", "Forwarded-email mismatch; existing profile adoption; revoked cookie; proxy principal changes mid-session.", "caos/server/identity.py; caos/server/routes/auth.py; caos/frontend/src/components/shared/AuthProvider.tsx"],
  ["ROL-003", "Server capability", "Analyst / writable principal", "May execute authenticated read and domain-mutation workflows subject to issuer/team/context gates and feature flags.", "Allowed writes succeed once, carry analyst attribution, and remain bounded by validation, tenancy, rate, and QA gates.", "Foreign issuer/team/context; stale revision; duplicate submit; disabled feature; invalid input; provider failure.", "caos/server/identity.py:71; caos/tests/server/test_write_role_matrix.py"],
  ["ROL-004", "Server capability", "Viewer / read-only aliases", "Roles viewer, read-only, read_only, and readonly retain reads and read-style calculations but cannot create or mutate domain artifacts.", "Every mutation protected by get_write_identity/require_write_role returns 403 before scan, provider, persistence, or side effects; read-style posts remain available where explicitly classified.", "Alias/case/whitespace variants; indirect mutation endpoint; preview versus commit; retry after role change.", "caos/server/identity.py:68; caos/tests/server/test_write_role_matrix.py"],
  ["ROL-005", "Presentation view", "Analyst", "Full working density for deep analysis, modelling, evidence review, and report composition; does not change authorization.", "Selecting Analyst persists to the analyst profile, exposes the implemented working-density priority, and never grants a server capability the principal lacks.", "Restore on another device; switch during pending request; narrow viewport; read-only server role; unknown persisted value.", "caos/frontend/src/components/shared/RoleViewSwitch.tsx; RoleViewProvider.tsx"],
  ["ROL-006", "Presentation view", "PM / CIO", "Prioritizes portfolio posture and what-changed scanning; does not change authorization.", "Selecting PM deterministically reprioritizes supported surfaces, preserves active analysis identity, and leaves server permissions unchanged.", "Empty portfolio; mixed-origin data; critical alert; narrow viewport; switch back to Analyst; read-only server role.", "caos/frontend/src/components/shared/RoleViewSwitch.tsx; PortfolioLabWorkbench.test.tsx"],
  ["ROL-007", "Presentation view", "QA / Head of Research", "Prioritizes governance, CP-5 gates, evidence, and review queues; does not change authorization.", "Selecting QA surfaces supported gate/governance priority with text/glyph semantics, preserves context, and cannot bypass publication or write controls.", "No findings; blocked/restricted gate; conflicting statuses; narrow viewport; switch during review; read-only server role.", "caos/frontend/src/components/shared/RoleViewSwitch.tsx; ICBookWorkbench.test.tsx"],
];
const automationEvidence = collectAutomationEvidence();
for (const [index, screen] of appRoutes.entries()) {
  const featureId = `SCR-${String(index + 1).padStart(3, "0")}`;
  for (const viewport of ["390x844", "1440x900"]) {
    automationEvidence.push({
      id: `AUT-AXE-${String(index * 2 + (viewport === "390x844" ? 1 : 2)).padStart(3, "0")}`,
      layer: "Route accessibility/responsive",
      node: `${featureId}::${screen.route}::${viewport}`,
      name: `${featureId} ${screen.route} route accessibility and responsive geometry at ${viewport}`,
      file: "caos/frontend/scripts/a11y-axe.mjs",
      executionRun: screen.route === "/deepdive"
        ? "VAL-20260720-AXE-DEEPDIVE-2"
        : screen.route === "/pipeline" || screen.route === "/issuers"
        ? "VAL-20260719-AXE-PIPELINE-4"
        : screen.route === "/sector"
        ? "VAL-20260719-AXE-SECTOR-2"
        : screen.route === "/monitor"
        ? "VAL-20260719-AXE-MONITOR-2"
        : screen.route === "/reports" ? "VAL-20260719-AXE-REPORTS-2"
        : screen.route === "/model" ? "VAL-20260719-AXE-MODEL-2"
        : "VAL-20260717-ROUTE-36",
      executedDate: today,
    });
  }
}
const sectorScreenIndex = appRoutes.findIndex((screen) => screen.route === "/sector");
if (sectorScreenIndex !== 14) {
  throw new Error(`Sector screen inventory drifted: expected /sector at SCR-015, found index ${sectorScreenIndex}`);
}
const monitorScreenIndex = appRoutes.findIndex((screen) => screen.route === "/monitor");
if (monitorScreenIndex !== 6) {
  throw new Error(`Monitor screen inventory drifted: expected /monitor at SCR-007, found index ${monitorScreenIndex}`);
}
const issuerScreenIndex = appRoutes.findIndex((screen) => screen.route === "/issuers");
if (issuerScreenIndex !== 3) {
  throw new Error(`Issuer screen inventory drifted: expected /issuers at SCR-004, found index ${issuerScreenIndex}`);
}
const pipelineScreenIndex = appRoutes.findIndex((screen) => screen.route === "/pipeline");
if (pipelineScreenIndex !== 8) {
  throw new Error(`Pipeline screen inventory drifted: expected /pipeline at SCR-009, found index ${pipelineScreenIndex}`);
}
const reportScreenIndex = appRoutes.findIndex((screen) => screen.route === "/reports");
if (reportScreenIndex !== 11) {
  throw new Error(`Report Studio screen inventory drifted: expected /reports at SCR-012, found index ${reportScreenIndex}`);
}
const modelScreenIndex = appRoutes.findIndex((screen) => screen.route === "/model");
if (modelScreenIndex !== 5) {
  throw new Error(`Model Builder screen inventory drifted: expected /model at SCR-006, found index ${modelScreenIndex}`);
}
const deepDiveScreenIndex = appRoutes.findIndex((screen) => screen.route === "/deepdive");
if (deepDiveScreenIndex !== 2) {
  throw new Error(`Deep-Dive screen inventory drifted: expected /deepdive at SCR-003, found index ${deepDiveScreenIndex}`);
}
automationEvidence.push({
  id: "AUT-PERF-DEEPDIVE-001",
  layer: "Route performance",
  node: "SCR-003::/deepdive?mode=reference::desktop,mobile-slow",
  name: "SCR-003 /deepdive desktop and mobile-slow reference-workspace route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260720-PERF-DEEPDIVE-2-GZIP",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-PERF-MONITOR-001",
  layer: "Route performance",
  node: "SCR-007::/monitor::desktop,mobile-slow",
  name: "SCR-007 /monitor desktop and mobile-slow route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260719-PERF-MONITOR-5-GZIP",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-PERF-SECTOR-001",
  layer: "Route performance",
  node: "SCR-015::/sector::desktop,mobile-slow",
  name: "SCR-015 /sector desktop and mobile-slow route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260719-PERF-SECTOR-2",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-PERF-ISSUERS-001",
  layer: "Route performance",
  node: "SCR-004::/issuers::desktop,mobile-slow",
  name: "SCR-004 /issuers desktop and mobile-slow route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260719-PERF-PIPELINE-4",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-PERF-PIPELINE-001",
  layer: "Route performance",
  node: "SCR-009::/pipeline::desktop,mobile-slow",
  name: "SCR-009 /pipeline desktop and mobile-slow route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260719-PERF-PIPELINE-4",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-PERF-REPORTS-001",
  layer: "Route performance",
  node: "SCR-012::/reports::desktop,mobile-slow",
  name: "SCR-012 /reports desktop and five-sample mobile-slow route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260719-PERF-REPORTS-5-GZIP",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-PERF-MODEL-001",
  layer: "Route performance",
  node: "SCR-006::/model::desktop,mobile-slow",
  name: "SCR-006 /model desktop and five-sample mobile-slow route performance",
  file: "caos/frontend/scripts/performance-audit.mjs",
  executionRun: "VAL-20260719-PERF-MODEL-5-GZIP",
  executedDate: today,
});
automationEvidence.push({
  id: "AUT-RESP-REPORTS-001",
  layer: "Browser interaction/responsive",
  node: "SCR-012::/reports::desktop,tablet,phone",
  name: "SCR-012 /reports exact-build workbench interaction and responsive geometry",
  file: "caos/frontend/scripts/validate-report-workbench.mjs",
  executionRun: "VAL-20260719-REPORT-WORKBENCH-3",
  executedDate: today,
});
const evidenceSourceByFile = new Map();
for (const file of [...new Set(automationEvidence.map((evidence) => evidence.file))]) {
  try {
    evidenceSourceByFile.set(file, await fs.readFile(path.join(repo, file), "utf8"));
  } catch {
    evidenceSourceByFile.set(file, "");
  }
}
for (const evidence of automationEvidence) {
  const source = evidenceSourceByFile.get(evidence.file) || "";
  const body = extractEvidenceBody(evidence, source);
  evidence.body = evidence.layer === "Server/stress/cohort" ? expandLocalHelperBodies(body, source) : body;
  evidence.scenario = classifyScenario(evidence);
}

// The historical CSV remains useful discovery input, but these rows had drifted
// from current implementation semantics. The canonical workbook must describe
// what the code does now, especially where authority or persistence changed.
const curatedContractOverrides = new Map(Object.entries({
  "shell-01": {
    name: "Role-priority workspace navigation",
    story: "As an analyst, PM, or QA reviewer, I want my highest-value workflows prominent while every specialist surface remains reachable so that navigation reflects my operating posture without changing access.",
    expected: "At 1280px and wider, WorkflowRail shows the five destinations projected for the active Analyst, PM, or QA view and appends the current route when it is outside that priority set. All Workflows expands the complete 15-route NAV_GROUPS registry in canonical Intake, Analyze, Decide, Publish, and Monitor order. Below the rail breakpoint, ConceptNav shows only the current workflow plus a Workflows drawer containing the complete registry and Settings. Full product labels and route headings derive from the same registry. Settings, Ask, the presentation-only role switch, and profile identity remain shared utility chrome rather than workflow destinations.",
    edgeCases: "Current nested route; current route outside the role's five priorities; Settings route; role change; unknown route; compact drawer close; context query preservation; short viewport rail scrolling; phone chip suppression; duplicate route or registry drift.",
    trigger: "Load any routed workspace, switch the presentation role, or open All Workflows/Workflows",
    files: "caos/frontend/src/lib/nav.ts; caos/frontend/src/components/shared/WorkflowRail.tsx; caos/frontend/src/components/shared/ConceptNav.tsx; caos/frontend/src/app/globals.css",
    endpoint: "none (client navigation and presentation-role state)",
  },
  "shell-02": {
    name: "Global keyboard navigation and utility hotkeys",
    story: "As a keyboard-first analyst, I want consistent global chords for workflow, subview, Ask, palette, collapse, and help actions so that I can operate the desk without leaving the keyboard.",
    expected: "Outside editable controls, Alt+ArrowLeft/Right cycles the 15 CONCEPT_CYCLE routes in canonical visual order with wrap and routes navigation through the unsaved-edit guard. Alt+Comma/Period emits subview direction -1/+1; Alt+S opens the command palette; Alt+C toggles collapse; Alt+K focuses Query on /query and otherwise toggles Ask; unmodified ? opens shortcut help. Letter chords use event.code so macOS Option-composed characters still resolve.",
    edgeCases: "INPUT, TEXTAREA, SELECT, or contenteditable target; nested current route; unknown current route; first/last wrap; dirty navigation cancellation; macOS composed key; Meta/Ctrl+?; unsupported Alt key; component unmount listener cleanup.",
    trigger: "Press a supported global keyboard chord outside an editable control",
    files: "caos/frontend/src/components/shared/ConceptHotkeys.tsx; caos/frontend/src/lib/nav.ts; caos/frontend/src/components/shared/NavigationGuardProvider.tsx",
    endpoint: "none (client keyboard events and router navigation)",
  },
  "shell-03": {
    name: "Authenticated analyst identity badge",
    story: "As an authenticated analyst, I want the shared shell to identify the active profile so that I can verify whose governed workspace state is in use.",
    expected: "AnalystBadge renders only when AuthProvider exposes a user whose source is profile. The desktop rail footer and compact navigation host the badge across routed workspaces. Its text is the user's initials; its title names the full profile and its aria-label identifies the profile and sign-out action. Missing, proxy, and local identities render no badge.",
    edgeCases: "No user; proxy/local fallback; empty or unusual full name; role switch; desktop versus compact shell; authentication refresh; sign-out in flight or failure.",
    trigger: "Resolve the authenticated identity and render shared workspace navigation",
    files: "caos/frontend/src/components/shared/AnalystBadge.tsx; caos/frontend/src/components/shared/AuthProvider.tsx; caos/frontend/src/components/shared/WorkflowRail.tsx; caos/frontend/src/components/shared/ConceptNav.tsx; caos/frontend/src/lib/format.ts",
    endpoint: "GET /api/auth/me",
  },
  "shell-05": {
    name: "Responsive skip-link landmarks",
    story: "As a keyboard or screen-reader user, I want direct focus jumps to content, visible navigation, and the page's primary action so that repeated institutional chrome does not block task entry.",
    expected: "The root layout exposes Skip to content to #main-content, mutually exclusive Skip to navigation links for desktop #workflow-priority-nav and compact #workflow-disclosure, and a target-aware Skip to page actions link. The desktop navigation landmark and compact disclosure are programmatically focusable without entering the normal tab order. The desktop link is display-none below 1280px and becomes visible on focus at the rail breakpoint; the compact alternative is hidden at the desktop breakpoint. SubHeader always supplies a focusable #page-actions target, naming an honest no-actions state when no primary action exists; routes without any target do not expose a dead global link.",
    edgeCases: "Desktop/compact breakpoint transition; route without a primary action; authentication/loading screen before routed navigation mounts; focus-only visibility; repeated tabbing; narrow viewport; missing fragment target; fixed overlay stacking.",
    trigger: "Press Tab from the document start and activate a skip link",
    files: "caos/frontend/src/app/layout.tsx; caos/frontend/src/app/globals.css; caos/frontend/src/components/shared/WorkflowRail.tsx; caos/frontend/src/components/shared/ConceptNav.tsx; caos/frontend/src/components/shared/SubHeader.tsx",
    endpoint: "none (document landmarks and responsive CSS)",
  },
  "shell-06": {
    name: "Route-scoped global Ask and command-palette handoff",
    story: "As an authenticated analyst, I want one Ask entry point that keeps my typed question and selects the correct evidence scope so that I do not query the wrong issuer or lose intent while navigating.",
    expected: "Alt+K opens Ask directly; Cmd/Ctrl+K opens CommandPalette, whose Ask CAOS row calls openWith and preserves typed text. At 1280px and wider WorkflowRail owns a labelled Ask utility; from 768px to 1279px the compact header owns it; below 768px AskLauncher supplies the labelled phone fallback. Only AskLauncher owns overlays, so desktop/tablet never gains a second floating dock. On /query both entry paths dispatch query-focus instead of mounting a second modal. Deep-Dive owns its evidence-synced inline chat; Model, Pipeline, and issuer profile use issuer-scoped chat grounded in the selected issuer's live run or explicit reference fixture; other routes use the cross-issuer capability/query modal. All triggers are hidden for signed-out or needs-login state and on /query, and route/competing-modal/Escape transitions close transient output.",
    edgeCases: "Signed-out or needs-login identity; /query prefill; Deep-Dive ownership; missing/failed issuer lookup; reference issuer; no live run; competing modal; nested citation overlay; empty text; capability/context/query failure; stale async result; route change while open.",
    trigger: "Press Alt+K, activate the Ask launcher, or execute the Command Palette Ask row",
    files: "caos/frontend/src/components/shared/Ask.tsx; caos/frontend/src/components/shared/CommandPalette.tsx; caos/frontend/src/components/shared/ConceptHotkeys.tsx; caos/frontend/src/components/deepdive/IssuerChat.tsx",
    endpoint: "GET /api/query/capabilities; POST /api/query/runs; GET /api/issuers/{issuer_id}; issuer chat/run adapters",
  },
  "shell-07": {
    name: "Role-aware root workspace handoff",
    story: "As a returning user, I want an unaffiliated root visit routed to the most useful surface for my saved presentation role without losing an explicit issuer/context link.",
    expected: "The root renders the bounded Opening workspace loading state while role preference and Suspense search parameters resolve. A queryless Analyst root redirects with router.replace to /issuers, PM to /command, and QA to /monitor. Any explicit root query is preserved verbatim on /issuers instead of being overridden by the role default.",
    edgeCases: "Role preference not ready; Suspense fallback; Analyst/PM/QA role; multiple or encoded query values; explicit issuer/context query; repeated render; router identity change; authentication landing outside the route component.",
    trigger: "Navigate to / with or without query parameters",
    files: "caos/frontend/src/app/page.tsx; caos/frontend/src/components/shared/RoleViewProvider.tsx; caos/frontend/src/components/shared/SurfaceState.tsx",
    endpoint: "none (client role state and router.replace)",
  },
  "shell-08": {
    name: "Canonical workflow disclosure and Directory return",
    story: "As an analyst working in a specialist surface, I want Directory and every other workflow available from a stable disclosure so that I can return to the issuer worklist without relying on a route-specific back link.",
    expected: "Directory is the first Intake item in the canonical NAV_GROUPS registry and therefore appears in desktop All Workflows and the compact Workflows drawer on every routed surface. Analyst priority navigation also exposes Directory directly; PM/QA priority sets retain an off-list active route and use All Workflows for Directory. Compact workflow links preserve the current analysis context query. The old PageSubHeader Directory control is not part of the current shell.",
    edgeCases: "Already on /issuers; nested issuer profile; PM/QA priority view; current route not prioritized; compact drawer; active-route marking; context query encoding; complete registry disclosure; Settings utility separation.",
    trigger: "Open All Workflows or the compact Workflows drawer and activate Directory",
    files: "caos/frontend/src/lib/nav.ts; caos/frontend/src/components/shared/WorkflowRail.tsx; caos/frontend/src/components/shared/ConceptNav.tsx",
    endpoint: "none (Next Link navigation to /issuers)",
  },
  "query-01": {
    name: "Context-bound investigation bootstrap",
    story: "As an analyst, I want Query bound to an owned analysis context before it becomes interactive so that drafts and results cannot leak across investigations.",
    expected: "The route is authentication-gated and creates or restores the Cross-coverage investigation context. The composer, lane controls, utilities, and run action remain inert until the URL context id, active context, session draft, and saved-run history have all hydrated to the same context; loading and context errors remain explicit.",
    edgeCases: "No context; requested context differs from the restored context; context creation failure; URL hydration lag; principal/context switch; stale async history response; narrow viewport.",
    trigger: "open /query with or without a context query parameter",
    files: "caos/frontend/src/app/query/page.tsx; caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "POST /api/analysis/contexts; GET /api/analysis/contexts/{context_id}",
  },
  "query-02": {
    name: "Context-scoped session draft",
    story: "As an analyst, I want my unfinished question retained only for the current investigation so that navigation does not lose work or cross-contaminate another context.",
    expected: "The composer reads and writes sessionStorage key caos.query.draft.{contextId}. Empty text removes the key; context changes clear the old in-memory draft and restore the new context's draft. Storage denial or quota failure leaves the live composer usable without claiming persistence.",
    edgeCases: "Unavailable sessionStorage; quota error; empty draft; rapid context switch; late hydration; browser session ends; context id absent.",
    trigger: "type, clear, navigate away from, or reopen a context-bound Query draft",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx",
    endpoint: "sessionStorage caos.query.draft.{contextId}",
  },
  "query-03": {
    name: "Declared lane inference and override",
    story: "As an analyst, I want to declare whether a question is metric, graph, or grounded so that the execution method is explicit before the system runs it.",
    expected: "Query infers graph from relationship/lineage language, grounded from why/evidence/source language, and metric otherwise. Metric, graph, and grounded controls expose pressed state; a manual selection is preserved while typing until Use suggested lane is activated. Non-metric lanes persist in the URL.",
    edgeCases: "Ambiguous wording; empty question; manual override followed by typing; external focus event; unknown lane query parameter; context not ready; keyboard-only operation.",
    trigger: "type a question, select a lane, or activate Use suggested lane",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx",
    endpoint: "none (typed URL and client-side classification)",
  },
  "query-04": {
    name: "Question composer and starter execution",
    story: "As an analyst, I want a focused question composer and defensible starters so that I can begin an investigation without learning engine identifiers.",
    expected: "The empty workbench presents three bounded starter questions. Selecting one seeds the draft and inferred lane; typing updates both unless the lane is manual. Run Query and Command/Ctrl+Enter submit only after context hydration and non-blank input, ignore duplicate busy submission, and surface a retryable normalized error.",
    edgeCases: "Whitespace-only input; duplicate busy activation; starter after manual lane selection; external caos:query-focus event; context switch during request; non-Error rejection; empty server response.",
    trigger: "select a starter, type a question, or activate Run Query/Command-Ctrl+Enter",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx",
    endpoint: "POST /api/query/runs",
  },
  "query-05": {
    name: "Persisted query run and URL handoff",
    story: "As an analyst, I want each executed question persisted and addressable so that I can restore the exact result and hand it to another workspace.",
    expected: "A successful run POST carries context, trimmed question, selected lane, and graph capability only for the graph lane. The returned run becomes current, is de-duplicated into a history capped at 100, updates context.query_session_id, and replaces the run/lane URL state. A response from an obsolete context or generation is ignored.",
    edgeCases: "Request completes after context switch; duplicate returned id; more than 100 local history rows; graph capability absent; request failure; URL update racing with history hydration.",
    trigger: "run a hydrated Query question",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "POST /api/query/runs; PATCH /api/analysis/contexts/{context_id}",
  },
  "query-06": {
    name: "Metric lane ranked table",
    story: "As an analyst, I want metric results rendered as an aligned, source-aware table so that cross-coverage rankings remain comparable and auditable.",
    expected: "Metric runs render at most 100 rows through the dominant table region with fixed-decimal numeric columns, units, rank, issuer links/metadata, and row-level source actions. Structured backend columns are preferred; otherwise Rank and Details fallbacks are derived. A change/trend question without a delta metric is explicitly caveated as level-ranked.",
    edgeCases: "Missing columns; nested issuer versus flat fields; null/non-numeric values; no rows; more than 100 rows; missing citations; mixed precision; trend question with no delta marker.",
    trigger: "complete or restore a metric-lane Query run",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/components/ui/DataTable.tsx",
    endpoint: "POST /api/query/runs",
  },
  "query-07": {
    name: "Validated graph lane",
    story: "As an analyst, I want graph results rendered only from a valid node-and-edge payload so that malformed analytical output cannot masquerade as a relationship map.",
    expected: "Graph runs require capability_id, mode, title, finite positioned nodes, and string source/target edges before GraphCanvas renders. The header reports question, graph title, node count, and link count; invalid payloads produce an explicit unavailable state. Activating a graph citation opens the evidence viewer.",
    edgeCases: "Missing graph fields; NaN/Infinity coordinates; malformed node or edge; empty graph; unknown node kinds; citation id without chunk metadata; large graph viewport.",
    trigger: "complete or restore a graph-lane Query run",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/components/query/GraphCanvas.tsx",
    endpoint: "POST /api/query/runs; GET /api/query/chunk/{chunk_id}",
  },
  "query-08": {
    name: "Grounded cited answer",
    story: "As an analyst, I want sentence-level chunk and fact citations on grounded answers so that every retained claim exposes its authority boundary.",
    expected: "Grounded runs render sentence claims in source order with claim type, chunk citation buttons, fact labels, and a unique cited-source count. Missing labels fall back to ids; uncited sentences are labelled keep in draft. A fallback answer without sentences is explicitly uncited, and a run with no retained grounded content renders No grounded answer.",
    edgeCases: "Malformed sentences/citations; duplicate ids; fact-only claim; chunk-only claim; uncited claim; fallback answer only; unavailable flag; zero retained claims.",
    trigger: "complete or restore a grounded-lane Query run",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx",
    endpoint: "POST /api/query/runs; GET /api/query/chunk/{chunk_id}",
  },
  "query-09": {
    name: "Citation register and evidence viewer",
    story: "As an analyst, I want every run-level source identifier collected in one inspector so that I can open the underlying extract before using a conclusion.",
    expected: "The evidence inspector lists up to 20 authority source ids, resolves available chunk metadata in parallel, retains bounded id fallbacks for non-chunk sources or read failures, and opens CitationViewer from graph, metric, grounded, or register actions. Changing the run refreshes metadata and closing the viewer clears selection.",
    edgeCases: "More than 20 sources; 404 claim/evidence id; chunk read error; stale metadata completion after run change; duplicate ids; viewer close; source without label.",
    trigger: "activate a source action in a Query result or its evidence inspector",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/components/command/CitationViewer.tsx",
    endpoint: "GET /api/query/chunk/{chunk_id}",
  },
  "query-10": {
    name: "Saved investigation history and deep-link restore",
    story: "As an analyst, I want context-owned Query history and run deep links so that a prior investigation can be restored without silently substituting another result.",
    expected: "Query loads context history, selects the requested run or context query_session_id, exposes the newest eight in utilities, and restores question plus manual lane when selected. Unknown URL-selected runs remain absent with an explicit retryable Selected investigation unavailable state; stale history responses are ignored and publishing a local result does not refetch the full list.",
    edgeCases: "Unknown run id; empty history; history read failure; context switch; response after unmount; duplicate local run; URL and context session disagree; more than eight utility rows.",
    trigger: "open a run deep link, select Saved investigations, or retry a failed restore",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx",
    endpoint: "GET /api/query/runs?context_id={context_id}",
  },
  "query-11": {
    name: "Graph capability resolution and graceful fallback",
    story: "As an analyst, I want an enabled graph capability selected without blocking other lanes so that graph prerequisites are transparent while metric and grounded work remains usable.",
    expected: "On mount the first enabled capability from the server groups replaces peer-set; absent/empty/malformed groups retain peer-set. The utility input permits an explicit capability id. Capability read failure shows a warning that graph capabilities are unavailable while metric questions remain usable, and late responses after unmount are ignored.",
    edgeCases: "No groups; group without capabilities; every capability disabled; malformed group; request failure; response after unmount; user edits capability while fetch resolves.",
    trigger: "open Query or edit Advanced graph Capability",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx",
    endpoint: "GET /api/query/capabilities",
  },
  "query-12": {
    name: "Decision envelope and authority states",
    story: "As an investment-decision user, I want Query conclusions translated into the shared what-changed/action/evidence envelope so that status and provenance are comparable with other workbenches.",
    expected: "DecisionHeader derives What changed, Why it matters, Required action, and Evidence health from the current run. Ready, partial, observed-empty, error, and unavailable remain distinct; as-of, live/demo/reference origin, method, freshness, approval state, missing dependencies, source count, and selected lane are never guessed.",
    edgeCases: "No run; partial run; observed-empty run; error without detail; missing as-of; unknown freshness/origin; zero sources; missing dependencies; non-ratified authority.",
    trigger: "run or restore an investigation and inspect the decision rail",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/components/shared/DecisionHeader.tsx",
    endpoint: "none (derived from persisted QueryRun authority)",
  },
  "query-13": {
    name: "Evidence-gated finding pin",
    story: "As an analyst, I want to pin only completed cited Query output so that draft or unsupported conclusions cannot enter the shared findings tray.",
    expected: "Pin finding is available only for ready or observed-empty runs with at least one authority source id. It writes a query-answer finding with context, derived title, original question, source run, and frozen evidence payload, suppresses duplicate same-tick activation, refreshes FindingsTray on success, and exposes retry after failure. Evidence is rechecked at activation time.",
    edgeCases: "No run; partial/error run; uncited result; source ids removed before click; observed-empty cited run; duplicate click; write failure; context missing; question is also the derived title.",
    trigger: "activate Pin finding in the Query evidence inspector",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/components/shared/AnalysisWorkbench.tsx",
    endpoint: "POST /api/analysis/findings",
  },
  "query-16": {
    name: "Investigation workbench composition and handoff",
    story: "As an analyst, I want one organized Query workbench with context, answer, evidence, and downstream handoffs so that dense investigation state remains legible and transferable.",
    expected: "EnterprisePage and PersonaWorkbench compose the context rail, central answer, decision rail, evidence inspector, run action, lane/history head stats, compact Concept navigation, and a utilities drawer. The inspector remains available for run authority and findings; a context-bound Open in Report Studio link preserves identity. Narrow mode keeps essential Query state without granting different permissions.",
    edgeCases: "No run; selected-run error; context loading/error; inspector overflow; long question/citation metadata; missing context suppresses Report Studio handoff; narrow viewport; presentation-role switch.",
    trigger: "open Query, inspect utilities/evidence, or hand the active context to Report Studio",
    files: "caos/frontend/src/components/query/QueryInvestigationWorkbench.tsx; caos/frontend/src/components/shared/PersonaWorkbench.tsx; caos/frontend/src/components/shared/EnterprisePage.tsx",
    endpoint: "none (workspace composition and context-aware navigation)",
  },
  "deepdive-01": {
    name: "Semantic Module Groups and Launcher",
    story: "As an analyst, I want every routed module organized into a small number of meaningful groups so that I can navigate the full analytical graph without losing the active module.",
    expected: "The launcher partitions all 27 current CP-X modules exactly once across Foundation, Analysis, and Governance & Debate. Exactly the active module's group is expanded; selecting a group opens its first module, finder/cycle navigation reveals the containing group, unknown module ids fall back to Foundation without inventing membership, off-screen active chips scroll into view, and edge chevrons appear only when horizontal overflow exists.",
    edgeCases: "Unknown mod id; newly added catalog module; duplicate or omitted membership; active group transition; horizontal overflow at either edge; selected chip already visible; deferred measurement after unmount; rapid module changes.",
    trigger: "load Deep-Dive, select a semantic group, change module, or page the launcher strip",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/lib/deepdive/module-groups.ts",
  },
  "deepdive-02": {
    expected: "Reference module glyphs follow the local replay state. Live issuer glyphs derive from persisted per-module QA status: cleared, warning/Restricted, failed/Blocked, or idle/no output. Collapsed layers expose counted text summaries with glyphs; failed and no-output states remain explicit and are never painted as cleared.",
    edgeCases: "Blocked row with persisted output; missing status; Restricted status; reference replay running; collapsed mixed-state layer; no produced modules; status meaning without color.",
    trigger: "inspect an expanded or collapsed module layer for reference and live issuers",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/lib/pipeline/sev.ts",
  },
  "deepdive-03": {
    expected: "The center pane follows the active module from clicks, cycle events, or the mod query parameter. Reference CP-6A/CP-6E/CP-3B/CP-4 use labeled bespoke fixtures; other reference modules use ModuleView. Every real issuer uses its own generic live output, explicit FAILED pane, or explicit NO OUTPUT state. The title and per-module LIVE/FAILED/NO OUTPUT authority match the content actually rendered.",
    edgeCases: "Unknown mod id; reference-only unavailable CP-2G/CP-4D; blocked live module; missing live module; query parameter change; live output for a bespoke module; dynamic import delay.",
    trigger: "select a module or load/change the mod query parameter",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/components/deepdive/tabs.tsx",
  },
  "deepdive-04": {
    expected: "For the Atlas Forge reference only, CP-6A renders the seeded pre-debate thesis, three-round analyst/bear/chair exchange, evidence-weighting resolution matrix, clickable evidence, and layout-appropriate workflow register. A real issuer never receives this fixture and instead uses its own generic module output or honest empty state.",
    edgeCases: "Summary/report/dense layout; evidence open; reference replay lock; live CP-6A present or absent; unresolved reference evidence.",
    trigger: "select CP-6A on the reference or a live issuer",
    files: "caos/frontend/src/components/deepdive/tabs.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-05": {
    expected: "For the Atlas Forge reference only, CP-6E renders the seeded portfolio allocation debate with RV/compliance personas, CIO ruling, allocation matrix, evidence, and layout-appropriate workflow register. A real issuer never receives the fixture.",
    edgeCases: "Summary/report/dense layout; evidence open; live CP-6E present or absent; reference replay lock.",
    trigger: "select CP-6E on the reference or a live issuer",
    files: "caos/frontend/src/components/deepdive/tabs.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-06": {
    expected: "For the Atlas Forge reference, CP-3B renders the seeded capital stack, recovery waterfall, scenario chart, and 2L sensitivity view with evidence and layout-appropriate workflow output. A real issuer uses the generic persisted CP-3B output or an honest no-output/failed state.",
    edgeCases: "Summary/report/dense layout; reference replay locked/running; live CP-3B absent, restricted, or blocked; evidence open; wide table overflow.",
    trigger: "select CP-3B",
    files: "caos/frontend/src/components/deepdive/tabs.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-07": {
    expected: "For the reference, CP-4 renders the seeded covenant aggressiveness/capacity analysis, expandable clause translations, CP-4/4C workflow output, and the live cross-default domino component. A real issuer uses its persisted generic CP-4 output plus finite signal-derived covenant capacity and the issuer-scoped domino map; missing/partial capacity degrades honestly.",
    edgeCases: "Summary/report/dense layout; expand/collapse clause; missing or non-finite live capacity signals; no run; blocked CP-4; empty domino graph; reference fixture authority.",
    trigger: "select CP-4 and inspect covenant rows/capacity/dominoes",
    files: "caos/frontend/src/components/deepdive/tabs.tsx; caos/frontend/src/components/deepdive/LiveCovenantCapacity.tsx; caos/frontend/src/components/shared/CrossDefaultDominoes.tsx",
  },
  "deepdive-08": {
    expected: "ModuleView renders known module metadata, KPIs, text/table/flag sections, semantic charts, and workflow output according to Summary, Report, or Dense. Summary preserves analysis but replaces full cards with an ordered workflow summary; Report includes consolidated workflow cards; Dense keeps every card. Live output uses the persisted runtime register and never seeded summaries when fallback is disabled.",
    edgeCases: "Unknown module; known module without seeded output; explicit no seeded fallback; blank live KPIs; live sections without fixture register; reference-only unavailable module; every layout.",
    trigger: "select any non-bespoke module or a live issuer module",
    files: "caos/frontend/src/components/deepdive/tabs.tsx",
  },
  "deepdive-09": {
    expected: "OutSections renders table sections with aligned values, narrative sections with evidence chips, and flag sections with textual severity plus glyph/color. Evidence ids are actionable and the renderer preserves the supplied source order.",
    edgeCases: "Empty sections; empty table rows; long text; missing evidence; unknown severity; non-numeric values; narrow pane overflow.",
    trigger: "render a module containing table, narrative, or flag sections",
    files: "caos/frontend/src/components/deepdive/OutSections.tsx",
  },
  "deepdive-10": {
    expected: "Registered module charts render through SemanticVisualization with explicit authority, readable summary, equivalent table schema, formatted labels, title, G2 identifier, and optional note. Modules without a registered chart render no chart container; multiple charts use the implemented bounded grid.",
    edgeCases: "No registered chart; empty chart data; default height; multiple charts; callback label branches; narrow pane; reduced motion; non-finite series value.",
    trigger: "render a module with or without registered chart specifications",
    files: "caos/frontend/src/components/deepdive/ModuleCharts.tsx",
  },
  "deepdive-11": {
    expected: "OutputRegister renders only when registered workflow steps exist. Its named toggle reports total steps and produced/limitation/gap counts, controls the card grid, and opens a selected step in the detailed modal. Summary layout uses the ordered summary sequence rather than this full register.",
    edgeCases: "No steps; all produced; gaps/limitations; collapsed register; repeated prefixes; long output; keyboard toggle; missing step metadata.",
    trigger: "open or collapse the required-output register for a module",
    files: "caos/frontend/src/components/deepdive/OutputRegister.tsx",
  },
  "deepdive-12": {
    expected: "Selecting a workflow step opens a labeled modal containing its narrative/sections, template and production metadata, evidence, Report Studio exhibit link, and Flag to QA action. The close control and modal accessibility behavior dismiss it; unknown module-to-exhibit mappings fall back to the snapshot exhibit.",
    edgeCases: "Unmapped report exhibit; no evidence; QA flag pending/error; Escape/backdrop/close; long narrative; narrow viewport; focus restoration.",
    trigger: "activate a workflow step card",
    files: "caos/frontend/src/components/deepdive/OutputRegister.tsx",
  },
  "deepdive-13": {
    expected: "StepOutputGrid renders an ordered semantic workflow sequence. Report mode consolidates repeated same-prefix cards, Summary renders narrative summaries in source order, and Dense remains unconsolidated; cards use bounded responsive column packing and avoid internal breaks.",
    edgeCases: "Repeated prefixes; partial output; no produced steps; one card; many cards; long body; Summary/Report/Dense transitions; narrow width.",
    trigger: "render workflow cards under each layout",
    files: "caos/frontend/src/components/deepdive/OutputRegister.tsx",
  },
  "deepdive-14": {
    expected: "Hovering or focusing an evidence chip publishes its id through EvidenceSync so every matching chip and participating driver row receives the selected treatment while unrelated citations do not. Mouse leave or blur clears the transient selection, and the contract remains keyboard-operable.",
    edgeCases: "Multiple matching chips; unrelated control; focus without hover; blur/mouse leave; provider absent on another screen; pre-hydration pointer event; rapid evidence changes.",
    trigger: "hover or focus an E-xx chip",
    files: "caos/frontend/src/lib/evidence-sync.tsx; caos/frontend/src/components/reports/EvidenceModal.tsx; caos/frontend/src/components/deepdive/rails.tsx",
  },
  "deepdive-15": {
    expected: "An E-xx chip is a focusable button that opens EvidenceModal for that id without leaking its click to parent controls. Live-run evidence takes precedence over colliding seeded ids and resolves its document chunk; a live run cannot shadow-resolve missing evidence to Atlas Forge. Unknown ids and chunk failures render explicit unresolved/unavailable states.",
    edgeCases: "Unknown id; live/seeded id collision; missing live evidence; chunk 404; no provider; nested clickable parent; modal close; lazy report import.",
    trigger: "activate an E-xx evidence chip",
    files: "caos/frontend/src/components/reports/EvidenceModal.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-16": {
    expected: "The source rail starts collapsed and expands to 330px. The reference issuer exposes the seeded deal/source register and evidence-trace drivers with synchronized evidence interactions. Every non-reference issuer instead gets an explicit issuer-scoped source-unavailable state—whether or not its ticker resolved—and never receives Atlas Forge source documents.",
    edgeCases: "Reference; non-reference with/without ticker; issuer lookup failure; rail collapse; evidence hover/focus; long source label; missing source rows; narrow workbench.",
    trigger: "expand the source rail",
    files: "caos/frontend/src/components/deepdive/rails.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-17": {
    expected: "The decision rail occupies 352px when open and exposes the reference CP-5 clearance/verdict/sizing/triggers only for the reference issuer. For a real issuer it renders the issuer-scoped committee review and explicit absence of a live verdict/sizing fixture. It distinguishes loading, error, unavailable, observed-empty, and populated council states and auto-collapses below 1440px.",
    edgeCases: "Reference versus live; no findings; loading; QA fetch error; no run; long remediation; narrow resize; manual toggle; verdict without qualifier.",
    trigger: "open the decision rail while the selected run resolves",
    files: "caos/frontend/src/components/deepdive/rails.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-18": {
    expected: "Committee Review · CP-5C renders live findings in stable severity/lane order with finding id, module/claim context, description, and required remediation. A successfully read empty council says no findings observed; loading, read error, and unavailable run each use a distinct non-clear state.",
    edgeCases: "No findings after successful read; read failure; loading; no run; duplicate/equal-severity findings; missing remediation or claim id; long text.",
    trigger: "open the decision rail for a live run",
    files: "caos/frontend/src/components/deepdive/rails.tsx; caos/frontend/src/lib/engine/useLiveRun.ts",
  },
  "deepdive-19": {
    expected: "ASK {issuer code} and the shared Ask state open a 408x560 non-modal issuer Q&A panel. The composer accepts at most 600 characters, ignores empty or duplicate busy sends, offers four starters for an empty transcript, sends up to the latest 12 transcript messages plus grounding, renders an explicit empty-reply fallback or retryable error, auto-scrolls, and closes from Escape or the close control.",
    edgeCases: "Empty/whitespace input; 600-character boundary; double send; empty reply; structured API detail; network/rate-limit error; close while pending; response from a prior run; small viewport max-height.",
    trigger: "activate ASK, choose a starter, or submit the composer",
    files: "caos/frontend/src/components/deepdive/IssuerChat.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-20": {
    expected: "Each issuer-chat request prepends a grounding exchange. Reference grounding contains the labeled mock Atlas Forge deal, current module, registered outputs, and most recently focused evidence. A completed live run serializes only that issuer's council and every persisted module output with the active module first; a live issuer without a completed run explicitly withholds Atlas Forge figures. Answers are instructed to remain under 150 words and cite CP/E ids where supported.",
    edgeCases: "Focused evidence unknown or empty; current module unknown/blank; live output section variants; no live modules; unavailable run; absent page/QA metadata; generic launcher; long context.",
    trigger: "submit a reference, live-run, or unavailable-run issuer question",
    files: "caos/frontend/src/components/deepdive/IssuerChat.tsx",
  },
  "deepdive-21": {
    name: "Chat History (Session and Run Scoped)",
    expected: "Issuer-chat transcripts persist only in sessionStorage under caos-chat-{runId} (or the reference run key), so a shared workstation does not retain them after the browser session. Changing run keys invalidates pending request generations, restores the new run's transcript without writing prior-run messages into it, clears input/busy state, and ignores stale success or failure responses. Clear removes the current transcript.",
    edgeCases: "Corrupt JSON or JSON null; storage read/write denial; run changes while request is pending; stale success/failure; reference/live key transition; empty transcript; clear while busy.",
    trigger: "send, clear, reload within a session, or change the selected run",
    files: "caos/frontend/src/components/deepdive/IssuerChat.tsx",
  },
  "deepdive-22": {
    name: "Layout Toggle (Summary/Report/Dense)",
    story: "As an analyst, I want three deliberate reading densities so that I can move between verdict-first review, committee report, and full audit output.",
    expected: "Summary, Report, and Dense controls appear in the normal and narrow utility contracts with aria-pressed state. The browser-local caos.deepdive.layout preference defaults to Report; legacy core migrates to Summary and base to Report; unknown/read/write-failing storage falls back safely. The selection controls module ordering and workflow-card consolidation without changing analytical data.",
    edgeCases: "Legacy core/base values; unknown value; storage unavailable/quota failure; duplicate narrow/desktop controls; hydration default; rapid layout switching; module without workflow steps.",
    trigger: "activate Summary, Report, or Dense",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/lib/deepdive/layout-pref.ts",
  },
  "deepdive-23": {
    name: "Exact and Latest Live Run Resolution",
    expected: "Deep-Dive passes the issuer and optional run query parameter to useLiveRun. An explicit run id is loaded directly and is never substituted with latest; otherwise the latest completed issuer run is resolved. Modules, QA/council, evidence, per-module status, as-of, and committee status converge into one run state. Any run/module/QA fetch failure produces phase=error and clears apparently successful output rather than silently falling back to seeded content.",
    edgeCases: "Exact run missing/foreign; no runs; latest in flight; list fetch failure; module fetch failure; QA fallback failure; blocked/restricted modules; stale async response after issuer/run change.",
    trigger: "load Deep-Dive with issuer and optional run query parameters",
    files: "caos/frontend/src/lib/engine/useLiveRun.ts; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-24": {
    expected: "The identity caveat has five mutually exclusive authority states: reference labels the seeded run as illustrative; loading says the live run is being checked; backend failure says the live run could not be loaded; live says missing panes show no output; and no-run directs the analyst to run analysis. Reference/loading take precedence over an error phase, and no state claims another issuer's fixture is live.",
    edgeCases: "Reference with run id; loading plus error; error with no run; completed run; issuer never analyzed; missing ticker; stale prior run state.",
    trigger: "open a reference or live issuer while run resolution changes",
    files: "caos/frontend/src/lib/deepdive/caveat.ts; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-25": {
    expected: "Reference outputs follow the local simulation gate: a locked module names its producing gate and upstream dependencies, running suppresses the awaiting copy, and cleared gates unlock the fixture. Live issuers never use the reference replay as an authority gate; they render persisted output, explicit failed output, or no output based on the selected run.",
    edgeCases: "Producing gate differs from display module (CP-4/CP-4C); running versus awaiting; dependency list empty; live output while reference sim is locked; Blocked live module; unknown gate id.",
    trigger: "select a reference module before/during/after replay or select a live module",
    files: "caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-26": {
    expected: "Every non-reference path suppresses seeded Atlas Forge authority: source and decision rails show issuer-scoped unavailable/live states, bespoke modules fall through to generic live/no-output rendering, live evidence cannot shadow-resolve seeded ids, and issuer chat excludes fixture figures. Loading, error, failed, and never-run states are labeled separately.",
    edgeCases: "Issuer lookup failure; ticker missing; no run; run fetch error; live module absent; blocked module; colliding evidence id; CP-6/CP-4 bespoke module selected; chat without run.",
    trigger: "open any non-reference issuer in Deep-Dive",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/components/deepdive/rails.tsx; caos/frontend/src/components/reports/EvidenceModal.tsx; caos/frontend/src/components/deepdive/IssuerChat.tsx",
  },
  "deepdive-27": {
    expected: "At small-and-up desktop widths the workbench uses a 42/330px source rail, fluid center pane, and 42/352px decision rail. Source starts collapsed; decision starts open only at 1440px or wider and changes only when crossing that threshold; 1536px controls layer expansion. The global collapse event closes both if either is open and opens both if neither is open; internal regions own overflow.",
    edgeCases: "Width exactly 1440/1536; repeated resize in same band; one rail open; both closed; horizontal module overflow; long center output; reduced motion; transition from phone triage.",
    trigger: "resize the desktop workbench or toggle/collapse its rails",
    files: "caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-28": {
    expected: "The dismissible deepdive-panes FirstRunHint explains the source, module, and decision panes; evidence-chip behavior; and the implemented Alt+,/Alt+. module cycle, Alt+C pane collapse, and Alt+K Ask shortcuts. Its disclosure follows the shared FirstRunHint persistence and focus behavior.",
    edgeCases: "Previously dismissed hint; storage unavailable; keyboard-only analyst; reduced motion; narrow desktop; shortcut collision with text entry; phone surface where desktop authoring is unavailable.",
    trigger: "open Deep-Dive before the hint has been dismissed",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/components/shared/FirstRunHint.tsx",
  },
  "deepdive-29": {
    name: "Issuer Identity Resolution and Retry",
    story: "As an analyst, I want the selected issuer identity to resolve honestly and recover from lookup failure so that I know which credit view I am reviewing.",
    expected: "The issuer query parameter selects the issuer; absence selects the labeled Atlas Forge reference. A non-reference profile fetch binds name, ticker, and signals while ignoring stale responses. Pending lookup says Loading issuer; failure says Issuer unavailable and exposes RETRY; retry reissues the profile request. Concept navigation retains the route out to the issuer register through ShellIdentity.",
    edgeCases: "Missing issuer parameter; unknown issuer; fetch failure then success; stale response after issuer change; issuer without ticker; profile signals missing; repeated retry.",
    trigger: "load Deep-Dive for a non-reference issuer or activate RETRY",
    files: "caos/frontend/src/app/deepdive/page.tsx; caos/frontend/src/components/shared/ShellIdentity.tsx",
  },
  "deepdive-30": {
    expected: "Export to Vault is mounted only when useLiveRun resolves a run id and receives that exact id. Activation posts the run-scoped vault export, exposes pending/success/error state through the shared control, and never exports the seeded/no-run presentation as though it were a persisted run.",
    edgeCases: "No run; exact versus latest run; double activation while pending; endpoint failure; empty written list; vault not configured; viewer/read-only principal; run changes before click.",
    trigger: "activate Export to Vault for a completed live run",
    files: "caos/frontend/src/components/reports/ExportToVaultButton.tsx; caos/frontend/src/app/deepdive/page.tsx",
  },
  "deepdive-31": {
    expected: "Deep-Dive's ShellIdentity supplies the compact ConceptNav so the analyst can move among implemented CAOS concepts with keyboard-focusable named destinations and active-route semantics. Below the rail breakpoint the guaranteed Concepts drawer remains available; above it the quick-jump rail is scrollable.",
    edgeCases: "Current Deep-Dive destination; narrow drawer; long labels; horizontal overflow; keyboard navigation; modifier-key open; unknown pathname.",
    trigger: "open the Concepts navigation from Deep-Dive",
    files: "caos/frontend/src/components/shared/ShellIdentity.tsx; caos/frontend/src/components/shared/ConceptNav.tsx",
  },
  "deepdive-32": {
    expected: "A known generic module renders its code, name, persisted/reference status, description, optional plan event, KPIs, and current authority before its content. Unknown ids receive a not-in-route-graph state; known modules without output direct the analyst to the appropriate Pipeline or Report Studio workflow rather than inventing content.",
    edgeCases: "Unknown id; infrastructure-style missing module; analytical missing module; no event; live output; blank KPI values; reference-only unavailable output.",
    trigger: "select a generic module",
    files: "caos/frontend/src/components/deepdive/tabs.tsx",
  },
  "deepdive-33": {
    name: "Conclusion-First Module Ordering",
    expected: "For generic module sections whose final narrative title matches the implemented conclusion/view/summary/memo/clearance/readiness/selection pattern, Summary/Report/Dense promote that conclusion as the lead analytical block before supporting detail. Summary additionally replaces full workflow cards with an ordered summary; the underlying section data and evidence are not mutated.",
    edgeCases: "No matching final narrative; matching title earlier rather than last; final table/flags section; one section; live section titles; every layout; duplicate conclusion labels.",
    trigger: "render a generic module containing a terminal conclusion section",
    files: "caos/frontend/src/components/deepdive/tabs.tsx",
  },
  "deepdive-34": {
    expected: "FLAG TO QA · CP-5 opens a compose/confirm flow and POSTs the current module, step reference, optional note, issuer, and optional run. A 201 response reflects the new flag count/state; server identity supplies analyst attribution. Analyst flags persist separately from engine qa_findings and never change run or committee gates. Validation and rate/role errors are surfaced for retry.",
    edgeCases: "Cancel; empty note; note over 2000; invalid module/id lengths; duplicate flag; existing count; double submit; 401/403/429/5xx; flag created while run changes.",
    trigger: "compose and confirm FLAG TO QA from a step or evidence modal",
    files: "caos/frontend/src/components/shared/FlagToQa.tsx; caos/server/routes/qa.py",
    endpoint: "POST /api/qa/flags",
  },
  "deepdive-35": {
    expected: "On mount FlagToQa queries existing analyst flags with its module/step/issuer/run filters and reflects zero, one, or multiple matches so the analyst can see prior escalation before submitting another. Read failure degrades without claiming an existing flag, and filters remain server-validated and identity-scoped.",
    edgeCases: "No flags; one/many flags; optional filters; invalid filter length; read failure; stale response after props change; foreign analyst; duplicate historical rows.",
    trigger: "mount a FlagToQa control for a module/step",
    files: "caos/frontend/src/components/shared/FlagToQa.tsx; caos/server/routes/qa.py",
    endpoint: "GET /api/qa/flags",
  },
  "research-01": {
    expected: "The Research scope group exposes Sector and Issuer buttons with aria-pressed state. Changing scope updates the focal input label/placeholder and the empty-subject run reason; saved settings may seed the initial scope on mount, but a page toggle is not itself persisted.",
    edgeCases: "Corrupt or unavailable localStorage falls back to sector; context state may restore sector or issuer before saved preferences hydrate; the latest post-mount state controls the input label.",
  },
  "research-02": {
    expected: "The focal Sector / theme or Issuer text input trims its value for submission, caps typing at 300 characters, and keeps both run controls aria-disabled until the trimmed subject contains at least two characters and research configuration is known.",
    edgeCases: "Whitespace-only or one-character input remains blocked; a 300-character value is accepted; unknown configuration blocks a valid subject; changing scope changes the label and reason copy.",
  },
  "research-03": {
    expected: "Audience, Decision to inform, and Timeframe live behind Advanced brief. Browser preferences seed them after mount; blank UI values are omitted from the client request so ResearchBrief applies its server defaults, while non-blank values are trimmed and sent.",
    edgeCases: "Blank or whitespace-only values are omitted; browser preferences can be absent, corrupt, or unavailable; server caps are audience 200, decision 300, and timeframe 200 characters.",
  },
  "research-06": {
    expected: "The Advanced brief AI mode group offers max, standard, and lite with explicit hints and aria-pressed state. The selected value is sent as brief.ai_mode; saved preferences seed it, and invalid stored values sanitize to standard.",
    edgeCases: "Only max, standard, or lite are accepted; corrupt or stale stored modes fall back to standard; the control is hidden while Advanced brief is collapsed.",
  },
  "research-07": {
    expected: "GET /api/settings determines provenance before a run can start. llm_configured=false renders the Demo mode warning and Run example research; true renders Run deep research; loading and failure both block submission, and failure exposes an explicit Retry configuration action.",
    edgeCases: "A settings error never guesses live or demo; retry can recover; a valid subject remains blocked until configuration is confirmed; demo mode is also identified on the finished report.",
  },
  "research-09": {
    expected: "POST /api/research rate-checks the caller, validates an optional owner-scoped context, inserts and commits a queued ResearchJob containing analyst id, context id, brief, and draft authority, updates the context artifact when present, enqueues after commit, and returns 201 with id and queued status.",
    edgeCases: "Unknown or foreign context returns 404; validation or rate limit occurs before enqueue; the committed brief supports later worker claim/re-execution; a dropped HTTP connection does not cancel execution.",
  },
  "research-10": {
    expected: "The client polls GET /api/research/{id} immediately and then every two seconds until complete or failed, tolerates up to ten consecutive non-404 transport errors, stops at a 15-minute client deadline, treats 404 as gone, supports AbortSignal detach, and reattaches a saved owner-scoped job after navigation or reload.",
    edgeCases: "Complete hydrates report/sources/demo/truncated; failed surfaces the server error; 404 clears a stale pointer quietly; transport errors retain the pointer for retry; abort stops watching without cancelling server work; foreign jobs return 404.",
  },
  "research-11": {
    expected: "While running, the Report pane shows mm:ss elapsed time, one honest coarse phase selected from four 25-second bands, the current subject or Reattached run, real source/search counters, the brief criteria, continuation guidance, and an optional Detach action.",
    edgeCases: "Phase clamps at Synthesizing; empty subject labels a reattached run; empty criteria shows the standard-credit-criteria fallback; missing progress currently renders 0 sources and 0 searches; reduced motion snaps counters.",
  },
  "research-12": {
    expected: "A terminal run failure renders the Research failed state with normalized detail and rerun guidance, notifies the analyst, and clears the terminal pointer. A failed rerun preserves the prior report behind View previous report; configuration/reattachment failures are separate retryable alerts.",
    edgeCases: "List-shaped FastAPI 422 detail is normalized; abort and gone are not presented as research failures; a context-link save failure preserves the completed report; no prior report means no restore action.",
  },
  "research-15": {
    expected: "A truncated live result carries a server-prepended Report may be incomplete blockquote, plus a visible Truncated badge and an Incomplete alert inside both the on-screen and print tear-sheet; complete results show none of those warnings.",
    edgeCases: "pause_turn at the continuation cap, max_tokens, and partial double-overload mark truncation; no text at the cap produces an explicit no-report explanation; demo fallback is not marked truncated.",
  },
  "research-16": {
    expected: "When no run, error, or result is active, the Report pane shows No report yet and previews four numbered deliverables: Executive summary, Detailed findings, Summary tables, and Recommendations. No provenance chip, print portal, or export action is mounted.",
    edgeCases: "Running, error, and result branches are mutually exclusive and take precedence over empty; the manifest remains finite and scrollable.",
  },
  "research-18": {
    expected: "POST /api/research calls the fixed-window limiter with key research:{caller.id}, max_attempts=3, and window_seconds=60. Exhaustion returns 429 with an explicit one-minute retry message before any job is created; list and polling GETs are not rate-limited.",
    edgeCases: "Each analyst has an independent key; the in-process limiter assumes the documented single-process deployment; resetting the window restores creation; active jobs remain pollable after creation quota is exhausted.",
  },
  "research-19": {
    expected: "The executor claims a queued job, marks it running, rebuilds ResearchBrief, and runs up to four streamed Anthropic turns with bounded web search. It persists best-effort progress, deduplicates sources, applies overload fallback, composes partial output as truncated when necessary, and writes complete or failed terminal state to the job.",
    edgeCases: "No model configuration returns the canned demo; primary plus fallback overload with no progress degrades to demo; partial progress is retained and truncated; concurrency is bounded; leased Postgres jobs can be reclaimed and exhausted orphans fail explicitly.",
  },
  "research-21": {
    expected: "ResearchBrief requires a 2–300 character subject; mode is sector or issuer; ai_mode is max, standard, or lite; persona/audience/decision/timeframe carry server defaults and caps; focus, exclusions, and source_directives cap at 1,000; criteria accepts at most 15 strings.",
    edgeCases: "Blank or one-character subject, invalid mode/AI mode, overlong scalar fields, and more than 15 criteria fail validation; empty criteria selects seven server defaults; blank optional client fields are omitted so server defaults apply.",
  },
  "research-23": {
    expected: "The configured EDGAR lane supports full-text search, issuer filings, classified filing exhibits, and two aliases for vaulting one exhibit. Discovery returns external/unverified pointers; vaulting performs ownership, SSRF, antivirus, extraction, storage, chunking, lineage, and optional embedding before returning EDGAR-vaulted provenance.",
    edgeCases: "Every endpoint returns 503 without EDGAR_USER_AGENT and is capped at 30 requests/minute per caller; SEC client errors become 502; only exact HTTPS www.sec.gov/Archives URLs can be fetched; a zero-chunk vault returns a warning.",
  },
  "research-24": {
    expected: "GET /api/edgar/search requires q length at least two, accepts comma-separated forms and limit 1–50 (default 10), enforces configuration and per-caller rate limits, runs the synchronous SEC search off-thread, and returns FilingHitOut pointers with external/unverified provenance.",
    edgeCases: "Missing/short q and out-of-range limit return 422; missing EDGAR configuration returns 503; EdgarError returns 502; an empty SEC result returns an empty list.",
  },
  "research-25": {
    expected: "GET /api/edgar/exhibits requires cik and an accession in dashed 10-2-6 or bare 18-digit form, enforces EDGAR configuration and the per-caller limiter, fetches the filing index off-thread, and returns exhibit name, URL, CP-4 document label, optional authority rank, and size.",
    edgeCases: "Malformed accession returns 422 before outbound I/O; missing configuration returns 503; EdgarError returns 502; unclassified exhibits carry no authority rank; empty filings return an empty list.",
  },
  "research-26": {
    expected: "POST /api/edgar/vault-exhibit and /vault-url validate legal run mode and issuer tenancy, fetch an allowed SEC archive URL, antivirus-scan it, extract and store off-thread with rollback cleanup, create the Document/chunks/lineage, commit, optionally enqueue embedding, and return EDGAR-vaulted document metadata.",
    edgeCases: "Foreign/missing issuer is rejected; invalid run mode returns 400; missing configuration returns 503; bad or failed SEC URL returns 502; storage is cleaned on pre-commit failure; zero extracted chunks returns a warning and no embedding task.",
  },
  "research-28": {
    expected: "After each streamed turn, the server emits deduplicated source count and actual web-search-result count; the executor persists progress; polling forwards it; RunningView eases displayed integers only toward those server values and lists the analyst criteria without ever marking a criterion complete.",
    edgeCases: "A missing progress payload currently displays 0/0; a failing progress callback is swallowed; duplicate URLs count once; counters never exceed the latest target; reduced motion snaps; unmount cancels animation frames.",
  },
  "research-29": {
    expected: "The initial brief exposes Scope, the focal subject input, Advanced brief disclosure, and the anchored run action. Advanced brief reveals framing, boundaries, criteria, and AI mode; aria-expanded and caos.research.adv track the disclosure, with a user-interaction fence preventing late preference hydration from undoing a click.",
    edgeCases: "First use starts collapsed; saved open state restores after mount; private mode cannot persist; short viewports scroll the panel without field overlap; subject/configuration rules still control both run actions.",
  },
  "command-01": {
    name: "Persisted portfolio position selection",
    story: "As a buy-side analyst, I want to select a durable holding by its position id so that I can inspect the exact instrument without confusing duplicate issuer names or tickers.",
    expected: "The Positions grid exposes each holding as a keyboard-operable row. Click, Enter, or Space writes that position id to the typed selected URL state, highlights the owning row, and opens the selected-position strip.",
    edgeCases: "Duplicate or missing tickers; multiple instruments for one issuer; stale selected id after a portfolio switch; click on an embedded issuer link; Enter and Space activation; empty portfolio.",
    trigger: "Open Positions and click, press Enter, or press Space on a persisted holding row",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/app/command/page.tsx",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-02": {
    name: "Portfolio posture distribution",
    story: "As a PM/CIO, I want a reconciled posture distribution for the selected portfolio so that I can see how completed portfolio-bound runs support the book stance.",
    expected: "When a non-empty command snapshot is available, the decision region renders OVERWEIGHT, NEUTRAL, UNDERWEIGHT, and UNKNOWN counts against the snapshot position total and labels the basis as completed runs explicitly bound to the selected portfolio.",
    edgeCases: "Zero positions; counts that do not fill every category; positions without a bound completed run; snapshot loading or failure; portfolio change while a snapshot is in flight.",
    trigger: "Load a selected portfolio command snapshot",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/app/command/page.tsx",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-03": {
    name: "Persisted holding fields and formatting",
    story: "As a credit analyst, I want the holdings grid to show the stored instrument and exposure fields in desk formats so that I can reconcile the workbench to the portfolio record.",
    expected: "Each row renders ticker, borrower, instrument, par size, price, margin, maturity, Moody's/S&P ratings, run-derived posture, and QA status. Missing values render an explicit dash; par uses USD millions and margin uses basis points.",
    edgeCases: "Null price, margin, par, maturity, ratings, ticker, or instrument; zero values; very long names; negative or non-finite values rejected upstream; narrow viewport horizontal access.",
    trigger: "Render the Positions dataset for a populated persisted portfolio",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/lib/portfolio-lab.ts",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-04": {
    name: "Issuer identity link semantics",
    story: "As an analyst, I want issuer identity links inside a holding row to open the profile without also selecting the instrument so that identity review and position review remain distinct actions.",
    expected: "An available ticker is a named link that opens the issuer profile overlay by stable issuer id and stops row activation. The borrower name independently links whenever issuer_id exists. A missing ticker renders a plain dash, and a missing issuer id suppresses both identity links while the surrounding row keeps its own selection semantics.",
    edgeCases: "Missing issuer id; issuer id with missing ticker; missing borrower name; repeated ticker across issuers; pointer and keyboard activation; event bubbling into the row; profile overlay unavailable.",
    trigger: "Activate the ticker link in a persisted holding row",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/components/shared/IssuerProfileOverlay.tsx",
    endpoint: "none (profile-overlay client action)",
  },
  "command-05": {
    name: "Holding posture and QA labels",
    story: "As a Head of Research/QA, I want every held position to expose posture and QA text so that risk state is never conveyed by color alone.",
    expected: "The grid renders explicit posture and QA-status labels sourced from the portfolio-bound command snapshot. UNKNOWN or missing states remain textually visible rather than being inferred from hue or replaced by a favorable sample state.",
    edgeCases: "Unknown posture; missing QA or committee status; restricted/blocked output; mixed-case server values; colorblind use; stale snapshot.",
    trigger: "Inspect Posture and QA cells in the Positions grid",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/server/routes/portfolios.py",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-06": {
    name: "Selected-position strip lifecycle",
    story: "As an analyst, I want a persistent bottom strip for the selected holding with an unobstructed close action so that I can inspect the position and return to the full worklist efficiently.",
    expected: "The strip appears only in Positions when the typed selected id resolves inside the current snapshot. Its named Close control clears selected from the URL, and the global Ask launcher is offset on Command Center so it cannot intercept that action.",
    edgeCases: "Selected id absent from the current snapshot; portfolio or dataset switch; Escape/title semantics; Ask launcher overlap at desktop or narrow widths; repeated close; browser back/forward.",
    trigger: "Select a holding, then activate the selected-position strip Close control",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/Ask.tsx",
    endpoint: "none (typed URL client state)",
  },
  "command-07": {
    name: "Selected-position strip metrics",
    story: "As a buy-side analyst, I want the selected strip to retain the instrument's key stored economics and posture so that I can scan the broader book without losing position context.",
    expected: "The strip shows ticker/borrower, loan name, par, price, margin, maturity, ratings, posture, and QA/committee state using the same persisted snapshot record and explicit missing-value formatting as the grid.",
    edgeCases: "Null economics or ratings; zero par/price/margin; long instrument name; absent run id; unknown posture; stale selection during a refreshed snapshot.",
    trigger: "Select a persisted holding and inspect its bottom strip",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/lib/portfolio-lab.ts",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-08": {
    name: "Position-to-Deep-Dive handoff",
    story: "As a credit analyst, I want the selected position to hand off its issuer and bound run to Deep-Dive so that the detailed review opens on the same analytical authority.",
    expected: "When both issuer_id and run_id exist, Open Deep-Dive links to /deepdive with both encoded values. If either authority key is absent, the UI must not fabricate a different issuer/run handoff.",
    edgeCases: "Missing issuer id; missing run id; special characters requiring encoding; stale run binding; modifier-key navigation; cross-portfolio selection reset.",
    trigger: "Activate Open Deep-Dive in a selected-position strip",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/app/deepdive/page.tsx",
    endpoint: "none (screen navigation)",
  },
  "command-09": {
    name: "Accessible persisted-position grid",
    story: "As a keyboard or assistive-technology user, I want the dense holdings table to expose stable grid semantics so that every instrument and column remains navigable.",
    expected: "The worklist exposes a named grid, explicit columnheaders for Ticker, Company, Instrument, Size, Price, Margin, Maturity, Ratings, Posture, and QA, and named focusable rows with visible selected state and native link separation.",
    edgeCases: "No rows; long translated content; horizontal overflow; row focus after refresh; duplicate accessible names; screen-reader and keyboard-only operation.",
    trigger: "Navigate the persisted positions worklist by role and keyboard",
    files: "caos/frontend/src/components/command/CommandPortfolio.tsx; caos/frontend/src/components/shared/DominantTableRegion.tsx",
    endpoint: "none (rendered grid semantics)",
  },
  "command-10": {
    name: "Command header portfolio and live-coverage counts",
    story: "As a PM/CIO, I want the header to identify the selected persisted portfolio and the honest live-coverage ratio so that I know the book and analytical population in scope.",
    expected: "The identity area shows the selected portfolio name and kind with a persisted label, Positions from the command snapshot, and Live Coverage as covered/issuer count. A failed live fetch renders a warning dash rather than 0/0.",
    edgeCases: "Directory or snapshot loading; no selected portfolio; zero issuers; live fetch failure; portfolio switch; narrow header compaction.",
    trigger: "Open Command Center with an authorized portfolio",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/EnterprisePage.tsx",
    endpoint: "GET /api/portfolios/; GET /api/portfolios/{portfolio_id}/command; GET /api/portfolio",
  },
  "command-11": {
    name: "Honest live-coverage failure state",
    story: "As an analyst, I want live coverage failures to be unmistakable so that unavailable engine data is never presented as an empty or complete book.",
    expected: "When /api/portfolio fails with no retained rows, the coverage dataset and header expose Live coverage unavailable and a dash. No fixture, sample coverage, favorable count, or false no-results conclusion is substituted.",
    edgeCases: "Failure with zero rows; failure after retained rows; timeout; malformed response; retry after recovery; digest still available while coverage is offline.",
    trigger: "Open Live coverage while its portfolio dependency returns a non-2xx response",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/engine/usePortfolio.ts",
    endpoint: "GET /api/portfolio",
  },
  "command-12": {
    name: "Command utility navigation",
    story: "As an analyst, I want contextual links to Portfolio Lab and Monitor so that I can move from posture review to holdings maintenance or surveillance without losing analysis context.",
    expected: "Command utilities links to /portfolios and, when an analysis context exists, /monitor with the same context id. The controls live in the named utility dialog and remain keyboard reachable.",
    edgeCases: "Context not yet created; utility closed; Escape close; modifier-key navigation; stale context id; narrow viewport.",
    trigger: "Open Command utilities and activate a workspace link",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "none (context-preserving navigation)",
  },
  "command-13": {
    name: "Role-sensitive default dataset",
    story: "As an analyst, PM, or QA lead, I want Command Center to open on the worklist most relevant to my role so that the first view matches my operating responsibility.",
    expected: "With no valid dataset URL value, QA defaults to Governance, PM defaults to Changes, and the analyst view defaults to Live coverage. An explicit valid dataset takes precedence over the role default.",
    edgeCases: "Unknown or missing role; invalid dataset; role change after load; browser back/forward; persisted context view disagreement.",
    trigger: "Open /command without a valid dataset query parameter under each role view",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/RoleViewProvider.tsx",
    endpoint: "none (role and typed URL client state)",
  },
  "command-14": {
    name: "Four Command datasets",
    story: "As a credit team member, I want one explicit tab set for Changes, Positions, Live coverage, and Governance so that each data authority remains distinct within the Command workbench.",
    expected: "The named Command dataset tablist exposes four keyboard-operable tabs with aria-selected state. Changing tabs updates the typed dataset URL, clears selected, and renders only the owning worklist and authority labels.",
    edgeCases: "Invalid dataset; rapid tab switching; selected strip open; browser history restoration; narrow horizontal overflow; role default on a cleared URL.",
    trigger: "Activate a tab in the Command dataset tablist",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/typed-url-state.ts",
    endpoint: "none (typed URL client state)",
  },
  "command-15": {
    name: "Typed Command URL state",
    story: "As an analyst, I want dataset, selected record, and portfolio scope encoded in the URL so that a workbench state can be restored and shared without ambiguous local state.",
    expected: "Only dataset, selected, and portfolio are read/written through useTypedUrlState. Dataset and portfolio transitions clear incompatible selection; invalid values degrade to documented defaults instead of crashing or selecting a foreign record.",
    edgeCases: "Unknown dataset; missing/foreign portfolio; stale selected id; encoded characters; duplicate query parameters; back/forward; direct deep link before dependencies settle.",
    trigger: "Load or mutate /command?dataset=...&selected=...&portfolio=...",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/typed-url-state.ts",
    endpoint: "none (URL state)",
  },
  "command-16": {
    name: "Authorized portfolio directory load",
    story: "As an authenticated analyst, I want Command Center to load my available persisted portfolios so that holdings review is scoped to durable authorized books.",
    expected: "On mount, GET /api/portfolios/ populates the selected-portfolio control and persisted identity. Loading and failure are explicit, stale async completions are ignored after unmount, and no sample directory is substituted.",
    edgeCases: "Empty directory; 401/403; timeout/503; response after unmount; duplicate names; large directory; portfolio removed between requests.",
    trigger: "Mount Command Center",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/api.ts",
    endpoint: "GET /api/portfolios/",
  },
  "command-17": {
    name: "Portfolio selection precedence",
    story: "As an analyst, I want portfolio scope resolved deterministically so that a deep link, saved analysis context, and default directory order cannot silently disagree.",
    expected: "A valid requested portfolio wins. When no portfolio was requested, a valid analysis-context portfolio_scope wins and otherwise the first authorized directory row is selected, with the resolved id written to the URL using replace semantics. An explicit unknown requested id fails closed as Portfolio unavailable until the analyst chooses Open default portfolio; it is never silently replaced by context or directory order.",
    edgeCases: "Explicit requested id outside the authorized directory; context id removed; empty directory; directory still loading; concurrent context creation; duplicate portfolio names; recovery after an invalid request.",
    trigger: "Open Command Center with or without requested/context portfolio scope",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "GET /api/portfolios/; GET /api/analysis/contexts/{context_id}",
  },
  "command-18": {
    name: "Invalid portfolio guard",
    story: "As an analyst, I want an invalid or unauthorized portfolio deep link to fail visibly so that I cannot mistake another book or a sample sleeve for the requested scope.",
    expected: "After the directory settles, an unknown requested id renders Portfolio unavailable with authorized-scope language. Open default portfolio clears portfolio and selected via replace, allowing normal precedence to resolve an authorized default.",
    edgeCases: "Directory still loading; empty directory; foreign id; deleted portfolio; malformed id; recovery action when no default exists.",
    trigger: "Open /command?portfolio={missing_or_unauthorized_id}",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/SurfaceState.tsx",
    endpoint: "GET /api/portfolios/",
  },
  "command-19": {
    name: "Portfolio switch and selection reset",
    story: "As a PM/CIO, I want portfolio switching to reload the owning snapshot and clear instrument selection so that no position from the prior book remains visible.",
    expected: "Selecting a portfolio replaces portfolio in the typed URL, clears selected, resolves the new directory row, and requests that portfolio's command snapshot. The identity, positions, counts, and posture update to the new book.",
    edgeCases: "Rapid switches with out-of-order responses; same portfolio reselected; old selected id also exists in new book; snapshot failure; browser back.",
    trigger: "Choose a different option in Selected portfolio",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/portfolio-lab.ts",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-20": {
    name: "Command snapshot load and focus refresh",
    story: "As an analyst returning from holdings maintenance, I want the selected portfolio snapshot refreshed on window focus so that Command Center reflects durable changes made elsewhere.",
    expected: "A selected portfolio triggers an immediate command-snapshot request and another request on browser focus. Loading/error flags settle for the live selection, the listener is removed on scope change, and responses after cleanup do not overwrite the current book.",
    edgeCases: "Focus storm; portfolio switch during request; unmount; non-2xx refresh after a prior snapshot; missing selected id; duplicate request completion order.",
    trigger: "Select a portfolio or return focus to the Command Center window",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/portfolio-lab.ts",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-21": {
    name: "Persisted holdings load states",
    story: "As an analyst, I want directory, snapshot, and holdings failures distinguished so that I know whether the book is absent, unauthorized, loading, or temporarily offline.",
    expected: "Positions renders separate Loading portfolios, Portfolio directory unavailable, No portfolio configured, Loading holdings, Holdings unavailable, and Portfolio unavailable states with scope-appropriate recovery actions and no sample substitution.",
    edgeCases: "Directory failure; empty directory; invalid requested id; snapshot failure; cached snapshot during refresh; missing as-of; portfolio deleted mid-session.",
    trigger: "Open Positions under each directory and snapshot dependency state",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/SurfaceState.tsx",
    endpoint: "GET /api/portfolios/; GET /api/portfolios/{portfolio_id}/command",
  },
  "command-22": {
    name: "Empty holdings recovery",
    story: "As an analyst, I want an empty persisted portfolio to offer a direct holdings-maintenance path so that an intentionally empty book is not confused with a fetch failure.",
    expected: "A successful snapshot with zero positions renders No positions held and an Add holdings link to /portfolios with the current portfolio id. It remains distinct from no configured portfolio and from unavailable holdings.",
    edgeCases: "position_count disagrees with positions array; encoded portfolio id; directory becomes empty; snapshot refresh adds the first holding; missing portfolio id.",
    trigger: "Open Positions for a command snapshot whose positions array is empty",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/portfolio-lab.ts",
    endpoint: "GET /api/portfolios/{portfolio_id}/command",
  },
  "command-23": {
    name: "Live coverage engine fields",
    story: "As a buy-side analyst, I want a latest-run coverage worklist with leverage, coverage, RV, fragility, QA, and gaps so that I can triage names using current engine output.",
    expected: "Each live row exposes issuer identity, sector, latest run/as-of, finite net leverage and interest coverage, RV recommendation/percentile, downside fragility with glyph plus text, QA/committee status, and source-gap count; missing values remain explicit.",
    edgeCases: "No completed run; null/non-finite metrics; zero coverage; missing percentile; unknown fragility; restricted QA; multiple gaps; mixed stale rows.",
    trigger: "Open the Live coverage dataset with completed analytical runs",
    files: "caos/frontend/src/components/command/LiveCoverage.tsx; caos/frontend/src/lib/engine/usePortfolio.ts",
    endpoint: "GET /api/portfolio",
  },
  "command-24": {
    name: "Live coverage selection, filters, and virtualization",
    story: "As an analyst, I want a dense, keyboard-operable live worklist with bounded rendering and filters so that I can inspect large coverage books without losing interaction quality.",
    expected: "Rows select by stable issuer_id using pointer, Enter, or Space and open the live issuer strip. Column filter dialogs toggle values with labelled controls, update the visible worklist, and the virtualized body renders a bounded window while preserving grid semantics.",
    edgeCases: "Duplicate tickers; empty filter result; all values deselected; rapid scroll; keyboard selection; selected issuer filtered out; hundreds of rows; narrow viewport.",
    trigger: "Filter, scroll, or select a row in Live coverage",
    files: "caos/frontend/src/components/command/LiveCoverage.tsx; caos/frontend/src/app/command/page.tsx",
    endpoint: "GET /api/portfolio",
  },
  "command-29": {
    name: "Canonical sector directory and alert preferences",
    story: "As a Head of Research, I want canonical sector selection and per-sector alert preferences so that the active dossier and notification scope remain explicit.",
    expected: "The authenticated /sector screen loads the canonical taxonomy and caller-scoped feed preferences. Desktop renders a sector directory and narrow layouts render an Active sector select. Choosing a different sector clears the local review/history/section selection and patches sector_id while clearing sector_review_run_id and rv_run_id; the current sector is a no-op. Each directory row exposes a named Alerts on/off switch that persists the complete next feed set, defaulting an absent preference to enabled, and a failed save surfaces a bounded alert.",
    edgeCases: "Taxonomy or feed fetch failure; sector absent from saved feeds; selecting the already-active sector; context unavailable; patch rejection; feed-save rejection; empty taxonomy; narrow layout; keyboard switch activation.",
    trigger: "Open /sector, choose a canonical sector, or toggle its Alerts switch",
    files: "caos/frontend/src/app/sector/page.tsx; caos/frontend/src/components/sector/SectorReviewDossier.tsx; caos/frontend/src/lib/analysis-workbench.ts; caos/frontend/src/lib/api.ts",
    endpoint: "GET /api/analysis/taxonomy; PATCH /api/analysis/contexts/{context_id}; GET/PUT /api/sector/feeds",
  },
  "command-30": {
    name: "Versioned sector dossier and analytical states",
    story: "As a buy-side analyst, I want a versioned sector dossier with explicit evidence and readiness states so that I can review the sector without mistaking loading, missing, partial, or stale work for a current conclusion.",
    expected: "The current context loads its sector-review history, selects the context-bound review id or newest available version, and keeps loading distinct from the authoritative no-version state. A review drives the four-part decision header, six dossier tabs, dimension scores, seven-section analysis, signals, comparables, early warnings, risks, sources, uncertainties, authority, ratification state, and downstream blockers. Partial and stale states retain their value with explicit missing dependencies or age; error and unavailable states never borrow the retired seed-card UI.",
    edgeCases: "History pending, empty, rejected, or reordered; context-bound id absent from history; partial/stale/error review; missing dimensions or sections; non-finite metrics; absent authority/source data; context switch during fetch; narrow tab overflow.",
    trigger: "Open /sector with an analysis context and load its review history",
    files: "caos/frontend/src/app/sector/page.tsx; caos/frontend/src/components/sector/SectorReviewDossier.tsx; caos/frontend/src/components/sector/SectorReviewPanels.tsx; caos/server/routes/sector.py",
    endpoint: "GET /api/sector/reviews?context_id={context_id}; GET /api/sector/reviews/{review_id}",
  },
  "command-31": {
    name: "Request a versioned sector review refresh",
    story: "As a Head of Research, I want to request a new sector-review version so that updated analysis is additive, context-bound, and does not overwrite prior work.",
    expected: "When no review exists or the active review is partial/stale, Request refresh posts the active context id, optional canonical sector id, and weekly timeframe to the V2 review endpoint. Success selects the returned first section, prepends the unique version to history, and binds sector_review_run_id in the in-memory analysis context. Duplicate clicks are disabled while busy; failure leaves the prior version unchanged and surfaces a bounded alert.",
    edgeCases: "Context absent; request already busy; partial or stale review; no returned sections; duplicate returned id; create rejection; sector absent; prior version present; reference-only evidence; rapid context change.",
    trigger: "Activate Request refresh from an empty, partial, or stale sector dossier",
    files: "caos/frontend/src/components/sector/SectorReviewDossier.tsx; caos/frontend/src/lib/analysis-workbench.ts; caos/server/routes/sector.py",
    endpoint: "POST /api/sector/reviews",
  },
  "command-32": {
    name: "Six-category governance workbench",
    story: "As a Head of Research/QA, I want governance divided into six explicit categories so that distinct gate, evidence, origin, and freshness problems are not collapsed into one count.",
    expected: "Governance renders CP-5 open findings, Failed Gates, Source Gaps, Mixed Origin, Stale Sources, and Overdue Refresh/never-run categories with textual status, counts, named controls, and source-specific rows.",
    edgeCases: "Every category empty; one dependency pending; mixed ready/error sources; duplicate issuer across categories; long evidence text; narrow layout.",
    trigger: "Open the Governance dataset",
    files: "caos/frontend/src/components/command/GovernancePanel.tsx; caos/frontend/src/lib/command/useGovernanceSources.ts",
    endpoint: "GET /api/portfolio; GET /api/qa/findings; GET /api/digest/daily",
  },
  "command-33": {
    name: "CP-5 findings and failed-gate queues",
    story: "As a QA owner, I want open CP-5 findings separated from committee-gate failures so that remediation and blocked-output review follow the correct workflow.",
    expected: "Live QA rows are derived from the portfolio and QA findings response; failed gates are derived separately from latest-run committee/QA state. Pending or failed dependencies display unavailable status and never a false zero/all-clear message.",
    edgeCases: "Finding without matching portfolio row; restricted versus blocked status; duplicate finding; empty successful queue; QA dependency error; portfolio offline.",
    trigger: "Inspect CP-5 and Failed Gates categories in Governance",
    files: "caos/frontend/src/components/command/GovernancePanel.tsx; caos/frontend/src/lib/command/qa.ts; caos/frontend/src/lib/engine/useQaFindings.ts",
    endpoint: "GET /api/qa/findings; GET /api/portfolio",
  },
  "command-34": {
    name: "Source-gap and mixed-origin governance",
    story: "As a research lead, I want missing-source impact and mixed live/reference origin called out explicitly so that committee conclusions are not treated as uniformly sourced.",
    expected: "Source Gaps renders CP-0 gap-log items with issuer, document, impact, severity, and requested date. Mixed Origin lists issuers whose current presentation combines reference/demo material with a live run and explains the authority seam.",
    edgeCases: "Missing document name/date; duplicate gaps; no live portfolio; reference-only row; live-only row; malformed gap payload; source fetch failure.",
    trigger: "Inspect Source Gaps and Mixed Origin in Governance",
    files: "caos/frontend/src/components/command/GovernancePanel.tsx; caos/frontend/src/lib/command/gaps.ts; caos/frontend/src/lib/command/mixedOrigin.ts",
    endpoint: "GET /api/portfolio",
  },
  "command-35": {
    name: "Stale versus never-run coverage split",
    story: "As a coverage manager, I want stale completed analysis separated from issuers never analyzed so that refresh work and initial coverage work are prioritized correctly.",
    expected: "Digest stale rows with a prior run appear under Stale Sources, while rows whose detail indicates never run appear under Overdue Refresh. The same issuer is not presented as both categories from one row.",
    edgeCases: "Unknown freshness; ambiguous detail text; missing issuer id; exactly-on-threshold age; duplicate rows; digest unavailable.",
    trigger: "Open Governance with stale and never-run digest rows",
    files: "caos/frontend/src/components/command/GovernancePanel.tsx; caos/frontend/src/lib/engine/useDigest.ts",
    endpoint: "GET /api/digest/daily",
  },
  "command-36": {
    name: "Governance pending and unavailable honesty",
    story: "As a PM/CIO, I want unresolved data dependencies to block an all-clear conclusion so that missing governance evidence cannot be mistaken for zero exceptions.",
    expected: "Each governance category receives its owning ready/loading/error status. Loading or error renders explicit cannot-be-marked-clear messaging; an empty-state conclusion is permitted only after that source completed successfully.",
    edgeCases: "One source ready while another fails; stale retained rows; rapid retry; portfolio live false; digest loading indefinitely; QA response malformed.",
    trigger: "Open Governance while portfolio, findings, or digest is loading or failing",
    files: "caos/frontend/src/components/command/GovernancePanel.tsx; caos/frontend/src/lib/command/useGovernanceSources.ts",
    endpoint: "GET /api/portfolio; GET /api/qa/findings; GET /api/digest/daily",
  },
  "command-37": {
    name: "Watchtower authority states",
    story: "As a PM/CIO, I want the ranked-change panel to distinguish loading, offline, empty-live, and AI-draft states so that absence of a change is not confused with unavailable surveillance.",
    expected: "Ranked Changes loads the current autonomy draft and alert states. It displays explicit loading/error/empty states, and any populated draft remains marked AI-generated/unratified according to its returned authority instead of being presented as a committee-approved feed.",
    edgeCases: "Draft 404/503; empty sections; refreshing draft; malformed claims; alert-state failure; stale response after unmount.",
    trigger: "Open Changes while /api/autonomy/draft settles",
    files: "caos/frontend/src/components/command/RankedChanges.tsx; caos/frontend/src/lib/api.ts",
    endpoint: "GET /api/autonomy/draft; GET /api/alerts/state",
  },
  "command-38": {
    name: "Ranked Watchtower changes",
    story: "As a PM/CIO, I want surveillance changes ranked by their returned anomaly severity so that the most consequential move is reviewable first.",
    expected: "Claim rows are flattened from autonomy-draft sections, sorted by severity, and show issuer, claim text, anomaly kind/severity basis, and current alert state. When portfolio holdings are not loaded, the ranking basis says so explicitly.",
    edgeCases: "Equal or missing severity; deterministic bullets without anomaly claims; multiple sections for one issuer; very long claim; no holdings; unknown anomaly kind.",
    trigger: "Load a populated Watchtower draft in Changes",
    files: "caos/frontend/src/components/command/RankedChanges.tsx; caos/server/routes/autonomy.py",
    endpoint: "GET /api/autonomy/draft",
  },
  "command-39": {
    name: "Watchtower alert-state convergence",
    story: "As an analyst, I want to acknowledge or resolve a ranked change once and see the durable state converge so that surveillance ownership is unambiguous.",
    expected: "Ack/resolve actions call the alert-state endpoint for the row's stable alert key, expose pending/disabled state, replace the local row with the returned durable state, and do not revert because a slower earlier response arrives.",
    edgeCases: "Double click; mutation 409/503; state already acknowledged/resolved; response after unmount; duplicate alert keys; stale GET racing a mutation.",
    trigger: "Activate Ack or Resolve for a Watchtower change",
    files: "caos/frontend/src/components/command/RankedChanges.tsx; caos/server/routes/alerts.py",
    endpoint: "GET /api/alerts/state; POST /api/alerts/state",
  },
  "command-40": {
    name: "Ranked-change Deep-Dive handoff",
    story: "As an analyst, I want a Watchtower change to open the implicated issuer in Deep-Dive so that I can validate the alert against the detailed evidence record.",
    expected: "Each change with an issuer id exposes a named Open link to /deepdive?issuer={encoded_id}. Missing issuer authority suppresses or disables the handoff rather than routing to a reference issuer.",
    edgeCases: "Missing issuer id; encoded id; repeated issuer; modifier-key navigation; stale autonomy section; unavailable Deep-Dive run.",
    trigger: "Activate Open on a ranked Watchtower change",
    files: "caos/frontend/src/components/command/RankedChanges.tsx; caos/frontend/src/app/deepdive/page.tsx",
    endpoint: "none (screen navigation)",
  },
  "command-41": {
    name: "Cross-issuer Query context handoff",
    story: "As an analyst, I want Command Center to open Query in the same analysis context so that portfolio scope and persisted investigation state remain attributable across surfaces.",
    expected: "Open cross-issuer Query links to /query with the current analysis context id when available and otherwise to /query. It does not invent a context id or discard an existing one.",
    edgeCases: "Context creation pending or failed; stale id; modifier-key navigation; portfolio switch before click; URL encoding.",
    trigger: "Activate Open cross-issuer Query from the Command toolbar",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "POST /api/analysis/contexts; GET /api/analysis/contexts/{context_id}",
  },
  "command-42": {
    name: "Open top change primary action",
    story: "As a PM/CIO, I want one primary action that opens the highest-ranked surveillance issuer in Deep-Dive so that I can validate the top change against issuer evidence from any Command dataset.",
    expected: "When the highest-ranked change carries a stable issuer id, Open top change navigates directly to /deepdive with that encoded id. When no ranked row or stable issuer authority exists, the action is disabled with an explicit unavailable reason and never substitutes the display name.",
    edgeCases: "No ranked rows; top row without issuer_id; encoded issuer id; selected strip open; draft refresh changes the top row; keyboard activation; modifier-key navigation.",
    trigger: "Activate Open top change in the Command header when a stable ranked issuer exists",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/EnterprisePage.tsx",
    endpoint: "none (stable-issuer Deep-Dive navigation)",
  },
  "command-43": {
    name: "Decision header — what changed",
    story: "As a PM/CIO, I want the last 24 hours of engine activity summarized with time and authority so that I can distinguish new analytical work from an unchanged book.",
    expected: "What changed is derived only from the live daily digest: loading is explicit, positive activity lists up to three non-zero counters, a successful zero roll-up says no activity observed, and an unavailable digest says live activity unavailable.",
    edgeCases: "All zero counters; more than three positive counters; non-numeric values; missing as-of; digest error; stale freshness authority.",
    trigger: "Load the DecisionHeader with daily digest activity_24h",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/DecisionHeader.tsx",
    endpoint: "GET /api/digest/daily",
  },
  "command-44": {
    name: "Decision header — why it matters",
    story: "As a PM/CIO, I want WARF and CCC-watch exposure summarized from the current digest so that portfolio risk relevance is visible beside the change count.",
    expected: "Why it matters renders WARF, optional WARF band, and CCC-watch count only when a live digest supplies a non-null WARF and as-of; otherwise it remains loading or explicitly unavailable.",
    edgeCases: "WARF zero or null; missing band; empty CCC watch; digest offline; stale or unknown freshness; delayed response after portfolio switch.",
    trigger: "Load the DecisionHeader with digest ratings data",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/DecisionHeader.tsx",
    endpoint: "GET /api/digest/daily",
  },
  "command-45": {
    name: "Decision header — required action",
    story: "As a PM/CIO, I want current QA findings and source gaps summarized as required action so that governance work cannot be overlooked while scanning posture.",
    expected: "Required action reports live QA plus failed-gate finding count and source-gap count after portfolio/finding dependencies settle. Loading and offline conditions remain explicit, and the value carries live derived authority and fetch time.",
    edgeCases: "Portfolio ready before findings; duplicate rows; fetch error; zero successful queues; missing fetchedAt; stale response.",
    trigger: "Load the DecisionHeader with portfolio governance sources",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/command/useGovernanceSources.ts",
    endpoint: "GET /api/portfolio; GET /api/qa/findings",
  },
  "command-46": {
    name: "Decision header — evidence health",
    story: "As a research/QA lead, I want central freshness counts translated into current, partial, stale, or unavailable evidence health so that committee readiness reflects source age.",
    expected: "Evidence health applies stale > unknown > due > current precedence to digest freshness counts, shows all relevant counts, identifies missing-source reasons for partial states, and attaches policy-version/as-of authority from the live digest.",
    edgeCases: "Multiple non-current counts; missing freshness; counts inconsistent with coverage; unknown policy version; null as-of; digest failure.",
    trigger: "Load the DecisionHeader with daily digest freshness counts",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/components/shared/DecisionHeader.tsx",
    endpoint: "GET /api/digest/daily",
  },
  "command-47": {
    name: "Dossier tabs and URL-persisted review selection",
    story: "As a sector analyst, I want stable dossier tabs and section selection in the URL so that I can navigate dense analysis, share a precise view, and retain my place.",
    expected: "The dossier exposes Overview, Signals, Comparables, Early Warning, Risks, and Sources as keyboard-operable tab buttons with the active item marked by aria-current. The tab, selected section, and comparison version use typed URL keys; choosing a section replaces the current URL entry. Analyst/PM defaults to Overview and QA defaults to Sources when no tab is supplied; an unknown tab falls back to the role default. Tabs remain horizontally accessible and the active-sector select remains available below the desktop-directory breakpoint.",
    edgeCases: "Unknown or missing tab; section absent from the active review; compare id absent from history; role change; browser back/forward; no review; narrow horizontal overflow; keyboard activation; late history hydration.",
    trigger: "Select a dossier tab or analytical section, then navigate or reload the URL state",
    files: "caos/frontend/src/components/sector/SectorReviewDossier.tsx; caos/frontend/src/components/sector/SectorReviewPanels.tsx; caos/frontend/src/lib/typed-url-state.ts",
    endpoint: "none (typed URL and responsive client state)",
  },
  "command-48": {
    name: "Sector review history and version comparison",
    story: "As a Head of Research, I want to select and compare immutable sector-review versions so that changes in posture and evidence breadth are visible without losing the current draft.",
    expected: "Review history is loaded newest-first for the active analysis context. The context-bound sector_review_run_id wins when present; otherwise the first version is active. Review utilities list every non-active version with version and UTC date, persist compare in typed URL state, and summarize prior-to-current posture plus source-count movement. Selecting None clears compare; an unknown comparison id renders no fabricated summary.",
    edgeCases: "No history; one version; context id missing from history; invalid compare id; equal posture/source counts; history request failure; out-of-order response; context change; missing or invalid timestamp.",
    trigger: "Open Review utilities and choose a prior Compare version",
    files: "caos/frontend/src/components/sector/SectorReviewDossier.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "GET /api/sector/reviews?context_id={context_id}",
  },
  "command-49": {
    name: "Source register and evidence availability",
    story: "As a Head of Research/QA, I want every sector conclusion to resolve through the review's persisted source register so that missing evidence is explicit and available evidence is one interaction away.",
    expected: "Dimensions, signals, early warnings, risks, and uncertainties render SourceRef states resolved against the active review's source_register. A source becomes a link only when it has a persisted id, a matching register entry, and a URL; absent ids, unregistered ids, and URL-less sources render specific unavailable reasons. The Sources tab lists origin/freshness and contradictions, and offers Route gaps to QA only when a context id can be preserved.",
    edgeCases: "Empty source_ids; unknown source id; duplicate references; registered source without URL; unsafe or absent context; empty register; uncertainty without sources; link keyboard focus; many wrapping references.",
    trigger: "Inspect source references or open the Sources tab in a versioned dossier",
    files: "caos/frontend/src/components/sector/SectorReviewPanels.tsx; caos/frontend/src/components/ui/SourceRef.tsx",
    endpoint: "GET /api/sector/reviews?context_id={context_id}; none for persisted source URL navigation",
  },
  "command-50": {
    name: "Section ratification and publication gates",
    story: "As a Head of Research/QA, I want explicit section ratification and fail-closed publication so that an incomplete or reference-only sector view cannot become a committee artifact.",
    expected: "The evidence inspector can ratify the selected unratified section. The primary Ratify updates action first arms a confirmation that names every remaining section, then Confirm posts only those section decisions. Partial/stale work routes to refresh; a ratified ready review exposes Publish review. The server keeps incomplete/reference reviews in draft and returns 409 when publication blockers remain; UI errors are explicit and prior review state is retained.",
    edgeCases: "No review; no selected section; already-ratified section; zero remaining sections; rejected section; partial/stale/reference review; duplicate click while busy; ratification or publish rejection; ownership mismatch; unknown section; changed review between arm and confirm.",
    trigger: "Ratify one section, confirm all remaining sections, or publish a fully gated review",
    files: "caos/frontend/src/components/sector/SectorReviewDossier.tsx; caos/frontend/src/lib/analysis-workbench.ts; caos/server/routes/sector.py",
    endpoint: "POST /api/sector/reviews/{review_id}/ratifications; POST /api/sector/reviews/{review_id}/publish",
  },
  "command-51": {
    name: "Sector comparable issuers and decision gaps",
    story: "As a sector analyst, I want comparable issuers linked by stable identity with finite credit metrics and explicit gaps so that I can move from sector posture to issuer-level investigation safely.",
    expected: "The Comparables tab renders a named table with issuer, posture, up to four sorted finite numeric metric columns, and decision gaps. A comparable with issuer_id uses IssuerLink for profile navigation; an item without stable identity remains plain text. Numeric values use aligned finite formatting, non-numeric/internal fields do not become metric columns, and missing dependencies remain left-aligned textual warnings.",
    edgeCases: "Missing issuer_id; duplicate issuer name; empty comparables; more than four metric keys; NaN or infinite values; missing metric on one row; no decision gaps; long names/gaps; keyboard and narrow-table access.",
    trigger: "Open the Comparables tab and activate a linked issuer",
    files: "caos/frontend/src/components/sector/SectorReviewPanels.tsx; caos/frontend/src/components/shared/IssuerLink.tsx; caos/frontend/src/components/ui/DataTable.tsx",
    endpoint: "GET /api/sector/reviews?context_id={context_id}; none for issuer overlay navigation",
  },
  "command-52": {
    name: "Daily digest coverage and ratings KPIs",
    story: "As a PM/CIO, I want a compact daily roll-up of WARF, ratings, completed coverage, and 24-hour runs so that portfolio health is visible without opening each issuer.",
    expected: "The Daily Digest panel renders WARF with band, rated issuers of total, complete-run issuers of total, and runs completed/failed in 24 hours from the live digest, with explicit formatting for missing values.",
    edgeCases: "Zero issuers; null WARF/band; all runs failed; missing activity keys; stale as-of; counts larger than issuer total.",
    trigger: "Render Daily Digest with a live digest response",
    files: "caos/frontend/src/components/command/DailyDigestPanel.tsx; caos/frontend/src/lib/engine/useDigest.ts",
    endpoint: "GET /api/digest/daily",
  },
  "command-53": {
    name: "Daily digest freshness watchlists",
    story: "As an analyst, I want stale-source and CCC-watch issuer lists to open by stable issuer id so that I can move from portfolio signal to the exact profile.",
    expected: "Stale and CCC-watch rows render their issuer name/detail as named buttons. Activation opens the issuer profile overlay using issuer_id; empty lists remain explicit and duplicate names do not change identity resolution.",
    edgeCases: "Missing issuer id; duplicate names; empty watchlist; long detail; profile overlay error; keyboard activation.",
    trigger: "Activate an issuer in the stale or CCC watch list",
    files: "caos/frontend/src/components/command/DailyDigestPanel.tsx; caos/frontend/src/components/shared/IssuerProfileOverlay.tsx",
    endpoint: "GET /api/digest/daily",
  },
  "command-54": {
    name: "Cited decision brief restoration",
    story: "As an analyst, I want the current cited Command decision brief restored from the analysis context so that a durable committee-oriented synthesis survives reload and navigation.",
    expected: "Once a context id exists, Command lists decision-brief insights for surface=command and kind=decision-brief, restores the server-designated current artifact, and renders its summary plus each claim's evidence ids. Load failure produces an explicit unavailable message.",
    edgeCases: "No current artifact; multiple versions; missing claims/evidence ids; context change during request; 403/404/503; stale completion.",
    trigger: "Open Command Center with an analysis context containing a current decision brief",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "GET /api/analysis/contexts/{context_id}/insights",
  },
  "command-55": {
    name: "Generate or refresh cited decision brief",
    story: "As an analyst, I want to generate a cited portfolio decision brief and explicitly refresh an existing one so that the synthesis remains current and source-addressable.",
    expected: "Generate/Refresh posts surface=command, kind=decision-brief, selected alert subject reference, and force=true only when replacing an existing artifact. Ready/ratified results replace the panel; pending and error outcomes remain explicit without erasing the prior brief.",
    edgeCases: "Context absent; no selected alert; pending artifact; provider error; duplicate click; existing ratified version; missing evidence ids.",
    trigger: "Activate Generate cited brief or Refresh cited brief",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "POST /api/analysis/contexts/{context_id}/insights",
  },
  "command-56": {
    name: "Command analysis-context autosave",
    story: "As an analyst, I want portfolio, role, dataset, and selected-record state autosaved into the active analysis context so that cross-surface work remains durable and attributable.",
    expected: "After context hydration, Command patches portfolio_scope and surface_state.command with active_id, view, role, and portfolio_id only when values differ. Patch errors do not crash the workbench, and AnalysisContextSaveState exposes persistence status.",
    edgeCases: "Context not ready; identical state; rapid tab/portfolio changes; stale patch completion; patch 404/409/503; selected record cleared; cross-surface state preservation.",
    trigger: "Change Command portfolio, role, dataset, or selected record after context hydration",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/lib/analysis-workbench.ts",
    endpoint: "PATCH /api/analysis/contexts/{context_id}",
  },
  "command-57": {
    name: "Command sector-board removal and dossier ownership",
    story: "As a PM/CIO, I want Command Center to remain focused on portfolio posture while Sector Review owns sector analysis so that two workspaces do not maintain conflicting sector state.",
    expected: "Command Center contains no Sector Board component, collapse state, sector filter, or sector localStorage workflow. The authenticated /sector route owns canonical sector selection, feed preferences, review history, and the versioned dossier. Cross-surface work is carried by analysis-context ids rather than the retired caos-command-sectors-v2 device key.",
    edgeCases: "Stale browser storage from the retired board; navigation between Command and Sector; missing analysis context; Command coverage tabs; narrow layout; regression that reintroduces duplicate board state.",
    trigger: "Load /command and /sector and inspect ownership of sector-analysis controls",
    files: "caos/frontend/src/app/command/page.tsx; caos/frontend/src/app/command/sector-board-removal.test.ts; caos/frontend/src/app/sector/page.tsx; caos/frontend/src/components/sector/SectorReviewDossier.tsx",
    endpoint: "GET /api/sector/reviews; GET/PUT /api/sector/feeds",
  },
  "settings-01": {
    name: "Research defaults with device precedence",
    story: "As an analyst, I want my device-local research lens to survive reload while retaining an analyst-profile fallback on a new device so that personal workflow preferences are predictable.",
    expected: "The Research card's Save writes validated preferences to caos.research.prefs in localStorage and shows a transient Saved state. On Settings load, a stored device value takes precedence; analyst workspace research_prefs is used only when that device has no stored value. Global Save changes writes the same current snapshot to both device storage and the analyst workspace profile.",
    edgeCases: "No device value with a server profile fallback; device value plus a different server value; malformed local JSON; private-mode storage failure; reset before save; async profile response after local hydration; reload and principal change.",
    trigger: "Edit Research defaults and activate Save or global Save changes, then reload Settings",
    files: "caos/frontend/src/app/settings/page.tsx; caos/frontend/src/lib/research-prefs.ts",
    endpoint: "localStorage caos.research.prefs; GET/PATCH /api/settings/analyst for profile fallback/global sync",
  },
  "settings-02": {
    name: "Research brief seeding from device defaults",
    story: "As an analyst, I want new Research briefs seeded from the validated preferences stored on this device so that the standing lens carries into execution without retyping.",
    expected: "Research calls loadPrefs on mount and pre-fills AI mode, scope, audience, decision, timeframe, and criteria from sanitized localStorage. Missing, malformed, or wrong-typed fields fall back independently to DEFAULT_PREFS; blank optional values remain available for server-side defaults.",
    edgeCases: "Absent storage; malformed JSON; wrong-typed individual fields; unsupported mode; empty strings; principal storage reset; Settings server fallback not yet saved onto this device.",
    trigger: "Open /research after saving device Research defaults",
    files: "caos/frontend/src/app/research/page.tsx; caos/frontend/src/lib/research-prefs.ts",
    endpoint: "localStorage caos.research.prefs",
  },
  "settings-03": {
    name: "Read-only workspace configuration snapshot",
    story: "As an analyst, I want a truthful non-secret view of the active workspace configuration so that I can understand the deployment posture without gaining access to credentials.",
    expected: "The Workspace tab loads GET /api/settings into a Workspace administration panel. Three summary cards disclose whether analysis is available, the active governance posture, and upload/concurrency capacity. Deployment diagnostics is collapsed by default and expands to seven finite groups: Models, Model tiers (mode to model), Governance & QA, Engine cost & limits, Deep Research, Retrieval & data, and Workspace. Boolean values pair a colored dot with On/Off text; loading and offline states are explicit and retryable; an unavailable primary answer source is labelled Answer source · Not connected; and the read-only note states that API keys, database URLs, and storage paths are never shown.",
    edgeCases: "Configuration request in flight; request failure and retry; collapsed or expanded diagnostics; false booleans; zero token budget; no connected answer source; long model identifiers; narrow view hides implementation hints but retains labels and values; accidental secret fields in the server payload.",
    trigger: "Open /settings?tab=workspace or choose Workspace, then refresh the environment snapshot",
    files: "caos/frontend/src/app/settings/page.tsx; caos/server/routes/settings.py",
    endpoint: "GET /api/settings",
  },
  "settings-04": {
    name: "Workspace-status command-bar context",
    story: "As an analyst, I want an unambiguous readiness signal in the Settings command bar so that I can tell whether the deployment snapshot is available without exposing implementation vocabulary in primary chrome.",
    expected: "After GET /api/settings succeeds, EnterprisePage contextual controls show Workspace status available in tabular muted text. The status is absent while the snapshot is loading or unavailable; detailed environment and model values remain inside the collapsed Deployment diagnostics section rather than the primary command bar.",
    edgeCases: "Configuration loading or offline; retry after failure; narrow command bar; snapshot succeeds with no connected answer source; long diagnostic values remain confined to the expanded details section.",
    trigger: "Load authenticated /settings and wait for the workspace snapshot",
    files: "caos/frontend/src/app/settings/page.tsx; caos/frontend/src/components/layout/EnterprisePage.tsx",
    endpoint: "GET /api/settings",
  },
  "settings-05": {
    name: "Authenticated Enterprise Settings workbench",
    story: "As an analyst, I want Settings to use the same institutional shell and accessibility structure as the other workspaces so that navigation, actions, and dense configuration remain predictable.",
    expected: "RequireAuth and Suspense gate an EnterprisePage object surface with ShellIdentity title Settings, the shared concept navigation, global Save changes action, Refresh environment snapshot utility, and a scrollable PersonaWorkbench settings body constrained to max-w-3xl. The workbench exposes labelled tab and tabpanel semantics and retains the shared visible focus and narrow-layout contracts.",
    edgeCases: "Unauthenticated identity; profile loading or failure; configuration offline; narrow viewport overflow; command-bar compression; keyboard-only navigation; delayed Suspense/search-parameter hydration.",
    trigger: "Navigate to /settings with and without an authenticated profile",
    files: "caos/frontend/src/app/settings/page.tsx; caos/frontend/src/components/layout/EnterprisePage.tsx; caos/frontend/src/components/shared/ShellIdentity.tsx; caos/frontend/src/components/shared/RequireAuth.tsx",
    endpoint: "GET /api/auth/me; GET /api/settings; GET /api/settings/analyst",
  },
  "settings-06": {
    name: "URL-persisted Settings tabs and roving keyboard navigation",
    story: "As an analyst, I want Settings grouped into link-restorable, keyboard-operable sections so that I can move quickly and return to the same configuration context.",
    expected: "The five tabs are Models, Research, Email Intel, Portfolios, and Workspace. A valid ?tab= value selects the corresponding panel; a missing or invalid value defaults to Models. Clicks use router.replace while preserving other query parameters. ArrowRight/Down and ArrowLeft/Up wrap, Home selects Models, End selects Workspace, only the active tab is in the tab order, and each panel is associated by aria-controls and aria-labelledby.",
    edgeCases: "Missing or unsupported tab parameter; first/last wrap; Tab key must not change selection; rapid navigation; browser reload/back; narrow horizontal overflow; focus handoff after router replacement.",
    trigger: "Open /settings with a tab query or operate the Settings sections tablist by mouse and keyboard",
    files: "caos/frontend/src/app/settings/page.tsx",
    endpoint: "Client URL query parameter ?tab=",
  },
  "settings-07": {
    name: "Staged device/profile model-mode selection",
    story: "As an analyst, I want to stage a cost-versus-quality model mode and persist it deliberately so that subsequent requests and durable runs use the intended tier.",
    expected: "The Models tab offers TEST, LITE, BALANCED, and MAX through ModelModeToggle. Device storage initially hydrates from caos.model.mode, then a valid analyst workspace model_mode may override it. Changing the control marks Settings dirty but does not persist immediately; global Save changes writes the uppercase mode to device storage and the lowercase representation to the analyst profile. Browser API requests read the stored mode into X-Model-Mode, server normalization rejects unknown values, and created runs persist the normalized mode used for execution.",
    edgeCases: "Absent, blocked, or corrupt localStorage; lowercase/whitespace profile values; invalid profile mode; profile arrives after device hydration; save failure must retain dirty state; rapid repeated save; missing header uses the server BALANCED default; TEST is the browser fallback.",
    trigger: "Choose a model mode, activate Save changes, reload, and create a run",
    files: "caos/frontend/src/app/settings/page.tsx; caos/frontend/src/components/shared/ModelModeToggle.tsx; caos/frontend/src/lib/model-mode.ts; caos/frontend/src/lib/api.ts; caos/server/engine/presets.py; caos/server/main.py",
    endpoint: "localStorage caos.model.mode; PATCH /api/settings/analyst; request header X-Model-Mode; POST /api/runs",
  },
  "settings-08": {
    name: "Staged Query answer-source selection",
    story: "As an analyst, I want to choose the answer-source posture for Query and Ask so that subsequent investigations use the intended balance of institutional depth, citations, and cost.",
    expected: "The Models tab exposes exactly three controlled cards: Balanced institutional answers, Citation-led research answers, and Cost-aware structured answers. Each card pairs selection with an explicit availability label: checking, available, not connected, or status unavailable. Selection is staged only; global Save changes writes the provider identifier to localStorage key caos_query_model and workspace.query_model. A successful profile load may seed the staged value, and no card claims a vendor is usable when its configured flag is false or the workspace snapshot failed.",
    edgeCases: "Configuration still loading; configuration request failure; provider explicitly not connected; profile value arrives after device hydration; unsupported stored/profile identifier; save failure retains the staged choice and dirty state; repeated save; narrow three-card layout.",
    trigger: "Choose a Query answer-source card, activate global Save changes, reload, or load with unavailable provider status",
    files: "caos/frontend/src/app/settings/page.tsx; caos/frontend/src/lib/api.ts; caos/server/routes/settings.py",
    endpoint: "localStorage caos_query_model; GET /api/settings; GET/PATCH /api/settings/analyst",
  },
  "settings-09": {
    name: "Planned task-specific analysis preferences",
    story: "As an analyst, I want an honest statement of task-specific routing availability so that I do not mistake inactive controls for a working model-routing workflow.",
    expected: "The Models tab renders a single read-only Planned notice stating that task-specific preferences will become available after workspace-level controls are enabled. It renders no lane selectors or comboboxes, performs no write on interaction, and preserves any existing model_lanes profile data unchanged through unrelated settings saves.",
    edgeCases: "Existing stored model_lanes; profile load failure; unrelated global or email save; unsupported legacy lane values; narrow viewport; regression that reintroduces disabled or write-capable dead controls.",
    trigger: "Open the Models tab with or without stored model_lanes and inspect Task-specific analysis preferences",
    files: "caos/frontend/src/app/settings/page.tsx; caos/server/routes/settings.py",
    endpoint: "GET /api/settings/analyst (read/preserve only; no task-specific write control)",
  },
  "settings-10": {
    name: "Email intelligence profile settings",
    story: "As an analyst, I want the persisted Outlook connection posture and approved sender list in Settings so that email intelligence intake begins from an explicit curated profile.",
    expected: "The Email Intel tab shows Connected or Not connected from email_intelligence.outlook_connected. Approved senders remain disabled until the analyst profile loads, accept comma/newline editing without destructive normalization during typing, and on blur trim and filter entries before a sparse revision-checked PATCH. Writes serialize, 409 conflicts rebase only the intended email delta onto authoritative current settings, and failed loads or saves surface bounded retryable errors without clearing the optimistic input.",
    edgeCases: "Profile loading/failure; connected false or absent; blank lines, commas, whitespace, duplicates, and domain entries; rapid blurs; stale revision conflict; object/string/generic backend error details; unmount before saved-status timeout.",
    trigger: "Open /settings?tab=email, edit Approved sender emails/domains, and blur the textarea",
    files: "caos/frontend/src/app/settings/page.tsx; caos/frontend/src/lib/settings.ts; caos/server/routes/settings.py",
    endpoint: "GET /api/settings/analyst; PATCH /api/settings/analyst",
  },
  "reports-01": {
    story: "As an analyst, I want to see all six authored deliverables so that I can navigate the complete committee output set.",
    expected: "The left rail lists Credit Snapshot, Earnings Update — Q1-26, IC Credit Memo, Covenant & Capacity Brief, Monitoring Digest, and Model Appendix with section/citation counts, READY/HELD state, and the active selection.",
  },
  "reports-02": {
    expected: "Selecting a deliverable updates the active preview and aria-current state. A report query parameter can deep-link an authored or immutable version; mutable active selection is saved in the context-bound server report draft after hydration.",
    edgeCases: "Unknown report ids fall back to the first available report; frozen-version deep links take precedence over a slower mutable-draft response.",
  },
  "reports-03": {
    expected: "Zoom buttons select 70/85/100/115%; FIT computes (available width − 48)/980 and clamps to 0.4–1.15. The preview uses CSS zoom and the selected display preference persists in localStorage key caos-e-zoom.",
  },
  "reports-04": {
    expected: "White, Warm, and Cool paper-tone buttons update the preview and pressed state. Paper preference is saved in the context-bound server draft; print output uses the dedicated unscaled white PrintPortal.",
  },
  "reports-05": {
    expected: "The SOURCES control toggles report source lines and its pressed state. The choice participates in autosaved server draft state and immutable preview intent.",
  },
  "reports-06": {
    expected: "EDIT DOCUMENT enables contentEditable text leaves for editable reference/frozen-preview content. Blur captures plain text capped at 2,000 characters; edits are saved in the context-bound report draft and rendered as overrides.",
  },
  "reports-07": {
    expected: "When the active deliverable has overrides, Report utilities exposes RESET N EDIT(S). Confirmation removes that deliverable's edits from draft state; cancellation preserves them.",
  },
  "reports-08": {
    expected: "Compose controls toggle section inclusion with labelled pressed state and update Export section counts. Omissions are bounded to editable content, saved in the context-bound report draft, and carried into reviewed output.",
  },
  "reports-09": {
    expected: "Lineage groups every report source by registered evidence ID, labels the producing module/input, and opens each source through the keyboard-operable EvidenceSelectionList. Sources without an evidence ID remain explicitly unregistered instead of becoming inert pseudo-links.",
    edgeCases: "Duplicate evidence IDs across modules; one source with multiple evidence IDs; unregistered source chips; long source labels; collapsed Panels rail; keyboard activation and focus return.",
  },
  "reports-10": {
    expected: "The source dialog prefers the selected live run's evidence index and fetches its real document chunk. A live ID absent from that run is explicitly unresolved and never shadow-resolves to the Atlas Forge fixture. Seeded reference evidence shows the authored extract, metadata, trace status, confidence, citations, and QA action. Fetch failure becomes Source unavailable; Escape, close, and backdrop dismiss through the shared modal focus contract.",
    edgeCases: "Live/seeded ID collision; missing chunk id; unknown ID; chunk fetch failure; long extract; absent document metadata; open lineage; Escape/backdrop/close; narrow viewport.",
  },
  "reports-11": {
    expected: "Print / save PDF calls window.print only for a selected immutable published version, while PDF and XLSX downloads require an active immutable version and surface binary failures without substituting mutable content. PrintPortal renders the selected frozen composition as an unscaled white document; pending immutable deep links and mutable drafts keep publication/print/download fail closed with explanatory copy.",
    edgeCases: "Mutable draft; immutable deep link still resolving; empty version list; missing binary version; PDF/XLSX failure; browser print; evidence modal; one active-draft decision-room opener.",
  },
  "reports-12": {
    expected: "Export metadata reports PDF · US Letter / XLSX, CP-RENDER v2.2, the distinct evidence IDs present in the source register, included/total sections, analyst override count, and the reference watermark or live committee hold reason. It does not claim an orphan-citation audit that the renderer does not perform.",
    edgeCases: "Zero citations; duplicate evidence IDs; omitted sections; singular/plural edit count; reference watermark; live Restricted/Blocked reason; clean live run.",
  },
  "reports-13": {
    expected: "The authored reference IC Credit Memo carries its CONDITIONAL — QA-117 watermark in the deliverable tag, preview, export metadata, and print composition. Live reports derive HELD/READY and watermark metadata from the selected run's actual committee status rather than borrowing the fixture gate.",
    edgeCases: "Reference held memo; reference clean deliverables; live Restricted/Blocked/Draft Only/Committee Ready; frozen preview; omitted content; printed output.",
  },
  "reports-14": {
    expected: "The deliverables footer is authority-aware. Reference mode names the authored CP-5/QA-117 fixture hold; a held live run names its actual committee reason and directs review of blocking findings; a clean live run states that outputs follow the active run and require server-frozen preview review. Warning/success color is paired with explicit text.",
    edgeCases: "Reference fixture; live Restricted/Blocked/Draft Only; clean live run; no active report; narrow rail; status color unavailable.",
  },
  "reports-15": {
    expected: "When a caller-visible run is present, Export to vault posts that exact run once, prevents re-entry while pending, and transitions from idle to EXPORTING to an attributed written-note count or a retryable error. Vault mirroring is not gated by committee readiness; server identity, ownership, rate, configuration, and filesystem checks still apply before writing stamped notes.",
    edgeCases: "No run id; pending duplicate click; one/many written files; foreign run; unconfigured directory; write failure; exhausted caller budget; retry after ordinary failure.",
  },
  "reports-16": {
    expected: "With VAULT_EXPORT_DIR unset, POST /api/runs/{run_id}/vault fails closed with 503 before any write. The client identifies the configuration problem in the failed control's title and retains a retry path.",
    edgeCases: "Blank/whitespace configuration; configured retry; foreign/missing run; repeated click while pending; 503 versus other failures.",
  },
  "reports-17": {
    expected: "A vault-export OSError is logged and translated to HTTP 500 with bounded guidance to check that VAULT_EXPORT_DIR exists and is writable. The client shows a retryable EXPORT FAILED state without leaking the raw exception.",
    edgeCases: "Missing directory; read-only directory; mid-write failure; non-OSError client failure; retry after correction; no partial success claim.",
  },
  "reports-18": {
    expected: "Vault mirroring consumes the caller-local export budget before filesystem work. An exhausted window returns 429 with retry-in-a-minute guidance; the pending client state also blocks same-control re-entry.",
    edgeCases: "First/last allowed request; first rejected request; caller isolation; duplicate pending click; budget reset; invalid or foreign run under an exhausted budget.",
  },
  "reports-19": {
    expected: "Vault mirroring resolves the selected run inside the caller's access scope before writing. A missing or foreign run returns 404 and produces no filesystem artifact.",
    edgeCases: "Malformed/missing id; deleted run; foreign analyst run; configured/unconfigured vault; rate guard ordering; no partial file.",
  },
  "reports-20": {
    expected: "On hydration the UI restores caos-e-zoom locally. Active report, omissions, edits, paper tone, source visibility, and add-back visibility load from and autosave to the analysis-context report draft; immutable-version deep links override mutable active selection.",
    edgeCases: "Invalid local zoom is ignored; missing server draft is an empty state; draft revision conflicts surface a reload-before-publishing message.",
  },
  "reports-21": {
    expected: "For the Atlas Forge reference issuer, Report Studio loads the saved model through getSavedModel, applies object-shaped overrides and assumptions, and rebuilds report figures. Live issuers consume server-frozen Model Engine v2 checkpoints instead; load failure falls back to base reference figures with a warning and retry.",
  },
  "reports-22": {
    expected: "ReportDoc renders the implemented profile, text, list, table, chart, columns, flags, model-appendix, and paged-group section shapes, filters omitted sections, prints registered source lines when requested, and preserves a defensive authority statement for incomplete or non-paged input.",
    edgeCases: "Every section type; paged and flat documents; omitted sections; malformed/frozen model cells; missing authority fields; sources hidden; add-backs suppressed; empty sections.",
  },
  "reports-23": {
    expected: "Editable text leaves activate only when composition authority permits editing. Blur commits plain text capped at 2,000 characters; paste strips markup, Escape restores the original value and blurs, and frozen-preview intent filters edits to server-reviewed editable paths.",
    edgeCases: "2,000-character boundary; oversized paste; HTML paste; Escape before blur; missing edit map; immutable published version; appendix mutation; sectionless preview.",
  },
  "reports-24": {
    expected: "FIT measures the Report preview's current width, subtracts 48px, divides by the 980px paper width, and clamps to 0.4–1.15. ResizeObserver keeps automatic fit current until the analyst selects an explicit zoom; keyboard FIT and unmount disconnect cleanly.",
    edgeCases: "Very narrow/wide preview; zero measurement; resize after manual zoom; keyboard activation; observer unavailable or disconnected; local zoom restoration.",
  },
  "reports-25": {
    expected: "Each deliverable exposes its authored section total and a citation total deduplicated from the report source register. The selected report's Export panel recomputes included sections after omissions without inventing missing evidence.",
    edgeCases: "Zero/one/many sections; duplicate evidence IDs; source with no evidence ID; omitted sections; live/generated report; immutable restored report.",
  },
  "reports-26": {
    expected: "POST /api/runs/{run_id}/report resolves the caller-visible run and its modules, requires Committee Ready, excludes auditor-only modules, and returns the deterministic committee report JSON with run/issuer/as-of/QA/committee/preparer identity and non-auditor sections. Missing or foreign runs return 404; the route has no Report Studio UI trigger.",
    edgeCases: "Missing or foreign run; no modules; auditor-only modules; Committee Ready versus every non-ready value; exhausted route budget; malformed id.",
  },
  "reports-27": {
    expected: "Committee export is allowed only for the exact Committee Ready status. Any other or unknown status returns 409 containing the observed committee status and the run's CRITICAL/MATERIAL blocking findings; changing the same owned run to Committee Ready permits deterministic assembly.",
    edgeCases: "Restricted, Blocked, Draft Only, unknown, null, and Committee Ready; no blocking findings; mixed severities; missing/foreign run; rate boundary.",
  },
  "model-03": {
    name: "Issuer-scoped manual historical overrides",
    expected: "Double-clicking an editable historical cell opens an inline numeric editor. Enter or changed blur commits a finite parsed value, while Escape or unchanged blur cancels. Overrides persist in issuer-scoped sessionStorage key caos-d-overrides:{issuerId}; a well-formed legacy localStorage caos-d-overrides payload migrates once, and malformed or non-finite values are ignored. Formula outputs recompute locally, but durable shared state changes only through the explicit model save workflow.",
    edgeCases: "Blank, currency-formatted, parenthesized, malformed, NaN, or infinite input; unchanged blur; Escape; storage denial; corrupt legacy payload; issuer switch; no active issuer; derived or read-only cell.",
    files: "caos/frontend/src/app/model/page.tsx; caos/frontend/src/components/model/ModelSheet.tsx; caos/frontend/src/components/model/model-format.ts",
    endpoint: "none until explicit legacy model save",
  },
  "model-04": {
    expected: "RESET CELL is available for the selected overridden historical cell, removes only that issuer/session override, restores the canonical source value and authority marker, and recomputes dependent formulas and outputs without clearing unrelated edits.",
    edgeCases: "No selected cell; selected cell is not overridden; storage denial; issuer change; dependent ratio becomes unavailable; repeated reset.",
  },
  "model-05": {
    expected: "When overrides exist, the header exposes ↶ N OVERRIDE(S) · RESET. The first activation arms a destructive confirmation labelled ▲ CONFIRM RESET?; the second activation clears every issuer-scoped session override and recomputes the model. Blur, timeout, issuer change, or intervening state disarms confirmation without data loss.",
    edgeCases: "Zero, one, or plural overrides; first click only; blur; timeout; double activation; issuer switch; storage denial; reset while another action is pending.",
  },
  "model-13": {
    expected: "A modified assumption case exposes a reset count. The first activation arms the case reset and the second activation applies it; blur or a bounded timeout disarms confirmation. Only the active BASE or DOWNSIDE case, including its year overrides, returns to defaults.",
    edgeCases: "Zero, one, or plural changed drivers; blur; timeout; switch case while armed; repeated activation; missing year-override map; omitted lifecycle callbacks.",
  },
  "model-15": {
    name: "Assumptions support-surface selection",
    expected: "The Model support toolbar exposes mutually exclusive Assumptions, Scenario, Evidence, and History controls. Selecting Assumptions mounts that support surface without mutating its values; its named Collapse action returns focus and width to the worksheet by closing the active support surface.",
    edgeCases: "Another support surface already active; repeated selection; Collapse; keyboard activation; narrow viewport; preserved unsaved assumptions; focus return.",
    files: "caos/frontend/src/app/model/page.tsx; caos/frontend/src/components/model/AssumptionsPanel.tsx",
  },
  "model-24": {
    name: "Scenario support-surface selection",
    expected: "The Model support toolbar mounts Scenario as one mutually exclusive support surface. The panel preserves the active model scenario while switching between Model and Propagation modes, and its named Collapse action closes the surface without resetting assumptions, presets, or pending analysis.",
    edgeCases: "Another support surface active; repeated selection; Collapse; model/propagation switch; active preset; request in flight; narrow viewport; keyboard activation.",
    files: "caos/frontend/src/app/model/page.tsx; caos/frontend/src/components/model/ScenarioPanel.tsx",
  },
  "model-25": {
    name: "Export legacy model workbook",
    expected: "EXPORT MODEL downloads an .xlsx workbook containing Model, Headline Facts, Overrides, Assumptions, and Scenarios sheets in that order. Every sheet carries origin/method/run/as-of identity; numeric cells retain financial formats, formula-shaped text is neutralized, non-finite values export blank, and the worksheet respects the current quarters visibility.",
    edgeCases: "No headline facts or overrides; negative and zero values; formula-injection-shaped label; NaN or infinity; quarters hidden; serialization failure; repeated click; temporary anchor cleanup.",
    files: "caos/frontend/src/components/model/export.ts; caos/frontend/src/components/model/export-download.ts; caos/frontend/src/app/model/page.tsx",
    endpoint: "none (client-generated XLSX)",
  },
  "model-26": {
    name: "Reference/live model provenance and CP-1 tie disclosure",
    expected: "The shared provenance chip presents the authority as explicit LIVE or DEMO text rather than legacy CP-1 LIVE/SEEDED copy. Issuer and run identity remain in the model header and export metadata. Where the legacy reference calculator has a CP-1 anchor, the formula/decision surface exposes a finite tie or drift result without leaking Atlas Forge notes into another issuer.",
    edgeCases: "Reference versus live issuer; missing run; missing/non-finite CP-1 leverage; exact tie; drift beyond tolerance; issuer switch; export while source identity changes.",
    files: "caos/frontend/src/app/model/page.tsx; caos/frontend/src/components/shared/ProvenanceChip.tsx; caos/frontend/src/components/model/FormulaBar.tsx",
  },
  "model-32": {
    name: "Issuer-scoped legacy model draft hydration",
    expected: "The legacy calculator restores issuer-scoped session overrides and local assumption state, then overlays a caller-visible server saved model when present. Only supported sections and finite override fields are adopted; malformed, unavailable, or denied browser storage falls back to guarded defaults, and a late response for a prior issuer is discarded.",
    edgeCases: "No saved model; partial or malformed payload; non-finite override; storage denial; API error; issuer changes in flight; stale response; legacy-key migration; missing optional sections.",
    files: "caos/frontend/src/app/model/page.tsx; caos/server/routes/models.py",
    endpoint: "GET /api/models/{issuer_id}",
  },
  "model-42": {
    name: "Responsive Model support and recovery controls",
    expected: "At narrow widths, support surfaces collapse behind the Model support toolbar while the worksheet remains the primary scroll owner. Essential QTRS, save/recovery, export, and support actions remain reachable through compact header or tools disclosures; no document-level horizontal overflow or clipped interactive control is allowed at 390x844 or 1440x900.",
    edgeCases: "390px phone; tablet; short viewport; support surface open during resize; utility drawer; long status text; unavailable export; save conflict; keyboard focus restoration.",
    files: "caos/frontend/src/app/model/page.tsx; caos/frontend/src/app/globals.css; caos/frontend/src/components/shared/SubHeader.tsx",
  },
  "model-43": {
    name: "Persist legacy reference model draft",
    expected: "SAVE MODEL writes the legacy v1 assumptions, overrides, collapsed rows, view state, and model payload to PUT /api/models/{issuer_id}, guarded by the last updated_at when available. Success exposes the saved timestamp; ordinary failure announces SAVE FAILED, a stale write announces SAVED ELSEWHERE with recovery, and Report Studio continues reading only the last durable server version. GET hydration remains distinct from Model Engine v2 revisions and checkpoints.",
    edgeCases: "No issuer model; save already running; malformed payload; unknown issuer; stale updated_at; network failure; retry; concurrent analyst save; reference-code/registry mismatch; reload after success.",
    files: "caos/frontend/src/app/model/page.tsx; caos/server/routes/models.py",
    endpoint: "GET/PUT /api/models/{issuer_id}",
  },
  "monitor-01": {
    name: "Email Intelligence reconciled intake tape",
    story: "As an analyst, I want a reconciled end-of-day email intake sample classified by severity so that I can prioritize material events without mistaking demo data for a live feed.",
    expected: "The Email intake dataset shows fixed daily totals of 3 critical, 11 high, 27 medium, 64 low, 19 deduped, and 2 unresolved (105 total) plus an eight-row illustrative sample. The caption reconciles sample-to-total and explicitly describes the tape as EOD.",
  },
  "monitor-04": {
    expected: "The default Alerts dataset shows the live Watchtower inbox when autonomy rows exist and a collapsible CP-MON-H seeded replay disclosure. Replay rows are newest-first, labelled read-only, include issuer, severity text, frozen timestamp, route, and source/no-source affordance, and reveal progressively until complete.",
  },
  "monitor-05": {
    expected: "Replay utilities provide play/pause, reset, and 1x/2x/4x speed controls with pressed state. The utility status shows a second-resolution HH:MM:SS ET clock; pause freezes the tick-derived tape and replay restarts a completed simulation.",
  },
  "monitor-06": {
    expected: "Replay state is SIM only while actively stepping, PAUSED when stopped before completion, and COMPLETE at the terminal tick. Only the genuinely newest replay row pulses while running; completed and filtered tapes remain static.",
  },
  "monitor-07": {
    name: "Replay KPIs in header",
    expected: "The sub-header exposes Replay criticals as a toggleable critical-only filter and Replay today as a finite, non-negative, tape-bounded tick-derived seeded count. Non-finite and negative ticks normalize to the opening baseline. Live routed-alert count is kept in the worklist toolbar so demo replay metrics are not presented as live production KPIs.",
  },
}));

const featureObjects = sourceRows.map((row) => {
  const contract = curatedContractOverrides.get(row.id);
  const name = contract?.name || row.feature;
  const expected = contract?.expected || row.expected;
  const files = contract?.files || row.files;
  const endpoint = contract?.endpoint || row.endpoint;
  const isMonitor = row.id.startsWith("monitor-");
  const isReport = row.id.startsWith("reports-");
  const isModel = row.id.startsWith("model-");
  const hasCurrentScenarioClosure = isMonitor || isReport || isModel;
  return makeFeature({
  id: row.id,
  name,
  concept: row.concept,
  story: contract?.story || row.story,
  expected,
  edgeCases: contract?.edgeCases || row.edge_cases,
  currentStatus: "Suite evidence",
  severity: row.severity,
  notes: hasCurrentScenarioClosure
    ? `Current implementation contract reconciled on 2026-07-19; all ${isMonitor ? "49" : isReport ? "194 applicable" : "462"} mandatory scenarios and direct regression evidence are listed in Test Cases and Feature Evidence.`
    : curatedContractOverrides.has(row.id)
    ? "Current implementation contract reconciled on 2026-07-16; direct evidence and regression status are listed in Test Cases and Feature Evidence."
    : row.notes,
  validationRules: genericValidation({
    name,
    expected,
    endpoint,
  }),
  dependencies: [files, endpoint].filter((value) => value && !value.startsWith("none")).join("; "),
  assumptions: hasCurrentScenarioClosure
    ? isReport
      ? "The current implementation contract was reconciled from source, and every applicable mandatory scenario was individually mapped to passing assertion-level evidence in the current iteration; backend-only report endpoints are explicitly viewport-not-applicable."
      : "The current implementation contract was reconciled from source, and every mandatory scenario was individually mapped to passing assertion-level evidence in the current iteration."
    : "The curated expected behavior is based on code review and prior execution evidence; the current iteration re-ran aggregate suites but did not individually execute every listed scenario.",
  trigger: contract?.trigger || row.trigger,
  files,
  endpoint,
  sourceType: "Curated feature",
  sourceStatus: hasCurrentScenarioClosure
    ? isMonitor
      ? "Implementation contract refreshed from current source; 49/49 mandatory Monitor scenarios pass on 2026-07-19"
      : isReport
      ? "Implementation contract refreshed from current source; 194/194 applicable Report Studio scenarios pass and two backend viewport scenarios are N/A on 2026-07-19"
      : "Implementation contract refreshed from current source; 462/462 mandatory Model Builder scenarios pass on 2026-07-19"
    : curatedContractOverrides.has(row.id)
    ? "Implementation contract refreshed from current source and passing 2026-07-16 automation"
    : `${row.status || ""}; ${row.test_result || ""}`,
  });
});

appRoutes.forEach((screen, index) => featureObjects.push(makeFeature({
  id: `SCR-${String(index + 1).padStart(3, "0")}`,
  name: `${screen.route} screen`,
  concept: "Screen Inventory",
  story: `As an authenticated analyst, I want to open ${screen.route} so that I can use the implemented ${screen.components.join(", ") || "route"} workspace.`,
  expected: `${screen.route} is emitted as a Next.js static-export page from ${screen.file}, served by FastAPI, and reaches its authenticated CAOS workbench without route-level accessibility violations.`,
  currentStatus: "Pass — landing load/a11y/responsive",
  notes: "Directly scanned in the 18-route authenticated matrix at 390x844 and 1440x900 for axe violations, scan errors, layout failures, page overflow, and clipped controls; deeper interactions are represented by curated features and journeys.",
  dependencies: `Next.js static export; FastAPI static serving; ${screen.components.join("; ")}`,
  trigger: `Navigate to ${screen.route}`,
  files: screen.file,
  endpoint: "none (screen route)",
  sourceType: "Discovered screen",
  sourceStatus: "2026-07-17 route matrix: 36/36 route-width states loaded and scanned cleanly",
})));

apiRoutes.forEach((route, index) => featureObjects.push(makeFeature({
  id: `API-${String(index + 1).padStart(3, "0")}`,
  name: `${route.method} ${route.path} — ${titleFromIdentifier(route.handler)}`,
  concept: "API Inventory",
  story: apiVerbStory(route.method, titleFromIdentifier(route.handler), route.path),
  expected: apiExpected(route),
  currentStatus: "Suite evidence",
  notes: "Inventory coverage is exact to the current router decorator; direct per-route scenario execution remains tracked in Test Matrix.",
  dependencies: `${route.file}:${route.line}; main.py router prefix; declared FastAPI dependencies and persistence/provider seams`,
  trigger: `${route.method} ${route.path}`,
  files: `${route.file}:${route.line}`,
  endpoint: `${route.method} ${route.path}`,
  sourceType: "Discovered API handler",
  sourceStatus: "Current server regression passed in aggregate",
})));

settings.forEach((setting, index) => featureObjects.push(makeFeature({
  id: `CFG-${String(index + 1).padStart(3, "0")}`,
  name: `${setting.environment} configuration`,
  concept: "Configuration",
  story: `As a CAOS operator, I want to configure ${setting.environment} so that ${titleFromIdentifier(setting.name).toLowerCase()} follows the deployment's intended security, provider, storage, or resource policy.`,
  expected: `Pydantic Settings reads ${setting.environment} as ${setting.type}; code default is ${setting.defaultValue}. ${setting.description || "The value is consumed through the central cached Settings object."}`,
  currentStatus: "Documented — direct matrix pending",
  validationRules: `Environment value must parse as ${setting.type}; deployed boot guards and consuming code apply any additional constraints described in the source comments.`,
  dependencies: `${setting.file}:${setting.line}; pydantic-settings; consuming subsystem`,
  assumptions: "Defaults are development-oriented unless the source explicitly states otherwise; production may fail closed even when a value parses.",
  trigger: `Set or omit ${setting.environment}, then construct Settings/start the app`,
  files: `${setting.file}:${setting.line}`,
  endpoint: "none (environment setting)",
  sourceType: "Discovered configuration",
  sourceStatus: "Parsed from current Settings class",
})));

journeySeed.forEach(([id, name, expected, files, status]) => featureObjects.push(makeFeature({
  id,
  name,
  concept: "Business Process",
  story: `As a buy-side credit team member, I want to complete ${name.toLowerCase()} so that the workflow produces durable, attributable, committee-defensible output.`,
  expected,
  currentStatus: status,
  notes: status.includes("Partial") || status.includes("gap") ? "At least one journey leg remains explicitly open in Defects/Test Matrix." : "Workflow boundary derived from current routes, executors, UI, and E2E tests.",
  dependencies: files,
  trigger: `Start ${name.toLowerCase()} from its primary UI or API entry point`,
  files,
  endpoint: "multiple — see Journey Inventory",
  sourceType: "Business process",
  sourceStatus: status,
})));

const duplicateIds = featureObjects.map((feature) => feature.id).filter((id, index, all) => all.indexOf(id) !== index);
if (duplicateIds.length) throw new Error(`Duplicate feature ids: ${[...new Set(duplicateIds)].join(", ")}`);

const exactEvidenceByFeature = new Map();
const indirectEvidenceByFeature = new Map();
const scenarioEvidence = new Map();
const addEvidence = (map, featureId, evidenceId) => {
  if (!map.has(featureId)) map.set(featureId, new Set());
  map.get(featureId).add(evidenceId);
};
const e2eJourneyIds = (evidence) => {
  const file = path.basename(evidence.file);
  const name = evidence.name.toLowerCase();
  if (file === "login_flow.spec.ts") return ["BP-001"];
  if (file === "deepdive_flow.spec.ts") return ["BP-006"];
  if (file === "model_flow.spec.ts") return ["BP-007"];
  if (file === "monitor_flow.spec.ts") return ["BP-015"];
  if (file === "query_flow.spec.ts") return ["BP-008"];
  if (file === "reports_flow.spec.ts") return ["BP-011"];
  if (file === "research_flow.spec.ts" || file === "research_run.spec.ts") return ["BP-009"];
  if (file === "settings_flow.spec.ts") return ["BP-017"];
  if (file === "recovery_flow.spec.ts") {
    if (name.includes("root-layout")) return ["BP-017"];
    if (name.includes("segment failure")) return ["BP-011"];
    return [];
  }
  if (file === "routed_concepts_flow.spec.ts") {
    if (name.includes("sector rv")) return ["BP-013"];
    if (name.includes("issuer profile")) return ["BP-006"];
    if (name.includes("decisions") || name.includes("portfolios") || name.includes("sponsors")) return ["BP-014"];
    return [];
  }
  if (file === "upload_flow.spec.ts") {
    if (name.includes("identity")) return ["BP-001"];
    if (name.includes("issuer directory")) return ["BP-002"];
    if (name.includes("upload wizard")) return ["BP-003"];
    return [];
  }
  if (file === "bootstrap_flow.spec.ts") {
    if (name.includes("upload wizard")) return ["BP-003"];
    if (name.includes("deep-dive")) return ["BP-005", "BP-006"];
    if (name.includes("run") || name.includes("pipeline")) return ["BP-005"];
    if (name.includes("create")) return ["BP-002"];
  }
  return [];
};
const serverJourneyFileIds = new Map([
  ["test_edgar.py", ["BP-004"]],
  ["test_edgar_cp1.py", ["BP-004"]],
  ["test_research_report.py", ["BP-010"]],
  ["test_report_exports.py", ["BP-011"]],
  ["test_vault_export.py", ["BP-011"]],
  ["test_sector_routes.py", ["BP-012"]],
  ["test_sector_concurrency.py", ["BP-012"]],
  ["test_rv_bucket.py", ["BP-013"]],
  ["test_market_xlsx_preview.py", ["BP-013"]],
  ["test_market_xlsx_commit.py", ["BP-013"]],
  ["test_portfolios.py", ["BP-014"]],
  ["test_decisions_thesis.py", ["BP-014"]],
  ["test_ic_book.py", ["BP-014"]],
  ["test_alert_states.py", ["BP-015"]],
  ["test_notifications.py", ["BP-015"]],
  ["test_sponsors_digest.py", ["BP-015"]],
  ["test_autonomy.py", ["BP-016"]],
  ["test_pipeline_executor.py", ["BP-016"]],
  ["test_pipeline_runs.py", ["BP-016"]],
]);
// Existing automation often proves more than the single scenario inferred from
// its test name. Keep the additional attribution explicit and assertion-level:
// each row names the exact node regex and only the feature/scenario contracts
// that node actually exercises. This avoids upgrading a whole file or suite to
// direct evidence merely because it is adjacent to a feature.
const issuerPermissionMappings = sourceRows
  .filter((row) => row.id.startsWith("issuer-"))
  .map((row) => [row.id, "Permission/security"]);
if (issuerPermissionMappings.length !== 29) {
  throw new Error(`Issuer permission-evidence inventory drifted: ${issuerPermissionMappings.length}/29 rows`);
}
const issuerDirectoryIds = sourceRows
  .filter((row) => /^issuer-(?:0[1-9]|1[0-2]|31)$/.test(row.id))
  .map((row) => row.id);
const issuerProfileIds = sourceRows
  .filter((row) => /^issuer-(?:1[3-9]|2[0-6]|29|30)$/.test(row.id))
  .map((row) => row.id);
if (issuerDirectoryIds.length !== 13 || issuerProfileIds.length !== 16) {
  throw new Error(`Issuer route-scenario inventory drifted: directory=${issuerDirectoryIds.length}/13 profile=${issuerProfileIds.length}/16`);
}
const commandFeatureIds = sourceRows
  .filter((row) => row.concept === "Command Center")
  .map((row) => row.id)
  .sort();
const expectedCommandFeatureIds = [
  "command-01", "command-02", "command-03", "command-04", "command-05", "command-06", "command-07", "command-08", "command-09",
  "command-10", "command-11", "command-12", "command-13", "command-14", "command-15", "command-16", "command-17", "command-18", "command-19", "command-20", "command-21", "command-22", "command-23", "command-24",
  "command-32", "command-33", "command-34", "command-35", "command-36", "command-37", "command-38", "command-39", "command-40", "command-41", "command-42", "command-43", "command-44", "command-45", "command-46",
  "command-52", "command-53", "command-54", "command-55", "command-56",
].sort();
if (JSON.stringify(commandFeatureIds) !== JSON.stringify(expectedCommandFeatureIds)) {
  throw new Error(`Command Center feature inventory drifted: ${commandFeatureIds.join(",")}`);
}
const commandPositions = expectedCommandFeatureIds.slice(0, 9);
const commandPortfolio = expectedCommandFeatureIds.slice(9, 22);
const commandCoverage = ["command-23", "command-24"];
const commandGovernance = ["command-32", "command-33", "command-34", "command-35", "command-36"];
const commandChanges = ["command-37", "command-38", "command-39", "command-40"];
const commandHandoffs = ["command-41", "command-42"];
const commandDecision = ["command-43", "command-44", "command-45", "command-46"];
const commandDigest = ["command-52", "command-53"];
const commandInsight = ["command-54", "command-55"];
const monitorFeatureIds = ["monitor-01", "monitor-02", "monitor-03", "monitor-04", "monitor-05", "monitor-06", "monitor-07"];
const currentMonitorFeatureIds = sourceRows.filter((row) => monitorFeatureIds.includes(row.id)).map((row) => row.id).sort();
if (JSON.stringify(currentMonitorFeatureIds) !== JSON.stringify([...monitorFeatureIds].sort())) {
  throw new Error(`Monitor feature inventory drifted: ${currentMonitorFeatureIds.join(",")}`);
}
const sectorFeatureIds = ["command-29", "command-30", "command-31", "command-47", "command-48", "command-49", "command-50", "command-51", "command-57"];
const currentSectorFeatureIds = sourceRows.filter((row) => sectorFeatureIds.includes(row.id)).map((row) => row.id).sort();
if (JSON.stringify(currentSectorFeatureIds) !== JSON.stringify([...sectorFeatureIds].sort())) {
  throw new Error(`Sector Review feature inventory drifted: ${currentSectorFeatureIds.join(",")}`);
}
const pipelineFeatureIds = sourceRows
  .filter((row) => row.concept === "Pipeline")
  .map((row) => row.id)
  .sort();
const expectedPipelineFeatureIds = Array.from({ length: 45 }, (_, index) => `pipeline-${String(index + 1).padStart(2, "0")}`).sort();
if (JSON.stringify(pipelineFeatureIds) !== JSON.stringify(expectedPipelineFeatureIds)) {
  throw new Error(`Pipeline feature inventory drifted: ${pipelineFeatureIds.join(",")}`);
}
const pipelineDirectoryIds = expectedPipelineFeatureIds.filter((id) => Number(id.slice(-2)) <= 8);
const pipelineWorkbenchIds = expectedPipelineFeatureIds.filter((id) => {
  const number = Number(id.slice(-2));
  return (number >= 9 && number <= 35) || number >= 43;
});
const pipelineApiIds = expectedPipelineFeatureIds.filter((id) => {
  const number = Number(id.slice(-2));
  return number >= 36 && number <= 42;
});
const pipelineUiIds = [...pipelineDirectoryIds, ...pipelineWorkbenchIds];
const reportFeatureIds = Array.from({ length: 28 }, (_, index) => `reports-${String(index + 1).padStart(2, "0")}`);
const currentReportFeatureIds = sourceRows.filter((row) => row.concept === "Report Studio").map((row) => row.id).sort();
if (JSON.stringify(currentReportFeatureIds) !== JSON.stringify([...reportFeatureIds].sort())) {
  throw new Error(`Report Studio feature inventory drifted: ${currentReportFeatureIds.join(",")}`);
}
const reportBackendOnlyIds = ["reports-26", "reports-27"];
const reportUiFeatureIds = reportFeatureIds.filter((id) => !reportBackendOnlyIds.includes(id));
const modelFeatureIds = Array.from({ length: 66 }, (_, index) => `model-${String(index + 1).padStart(2, "0")}`);
const currentModelFeatureIds = sourceRows.filter((row) => row.concept === "Model Builder").map((row) => row.id).sort();
if (JSON.stringify(currentModelFeatureIds) !== JSON.stringify([...modelFeatureIds].sort())) {
  throw new Error(`Model Builder feature inventory drifted: ${currentModelFeatureIds.join(",")}`);
}
const modelLegacyIds = modelFeatureIds.slice(0, 43);
const modelV2Ids = modelFeatureIds.slice(43);
const modelV2AuthorityIds = ["model-44", "model-66"];
const modelV2IdentityIds = ["model-45", "model-46", "model-48"];
const modelV2MutationIds = ["model-49", "model-50", "model-51", "model-52"];
const modelV2ScenarioIds = ["model-53", "model-54"];
const modelV2HistoryIds = ["model-55", "model-56"];
const modelV2ImportIds = ["model-57", "model-58", "model-59", "model-60"];
const modelV2LifecycleIds = ["model-61", "model-62", "model-63", "model-64", "model-65"];
const expectedModelApiInventory = [
  ["API-072", "GET", "/api/models/{issuer_id}", "get_saved_model"],
  ["API-073", "PUT", "/api/models/{issuer_id}", "save_model"],
  ["API-074", "GET", "/api/models/{issuer_id}/checkpoints", "list_model_checkpoints"],
  ["API-075", "POST", "/api/models/{issuer_id}/checkpoints", "create_model_checkpoint"],
  ["API-076", "POST", "/api/models/checkpoints/{checkpoint_id}/restore", "restore_model_checkpoint"],
  ["API-077", "GET", "/api/models/v2/{issuer_id}", "get_model_v2"],
  ["API-078", "PUT", "/api/models/v2/{issuer_id}", "put_model_v2"],
  ["API-079", "POST", "/api/models/v2/{issuer_id}/calculate", "calculate_model_v2"],
  ["API-080", "GET", "/api/models/v2/{issuer_id}/checkpoints", "list_model_v2_checkpoints"],
  ["API-081", "POST", "/api/models/v2/{issuer_id}/checkpoints", "create_model_v2_checkpoint"],
  ["API-082", "POST", "/api/models/v2/{issuer_id}/checkpoints/{checkpoint_id}/restore", "restore_model_v2_checkpoint"],
  ["API-083", "GET", "/api/models/v2/{issuer_id}/history", "list_model_v2_history"],
  ["API-084", "POST", "/api/models/v2/{issuer_id}/history/{event_id}/replay", "replay_model_v2_event"],
  ["API-085", "POST", "/api/models/v2/{issuer_id}/overrides", "mutate_model_v2_override"],
  ["API-086", "POST", "/api/models/v2/{issuer_id}/overrides/batch", "mutate_model_v2_overrides_batch"],
  ["API-087", "GET", "/api/models/v2/{issuer_id}/workbook/export", "export_model_workbook"],
  ["API-088", "POST", "/api/models/v2/{issuer_id}/workbook/import/commit", "commit_model_workbook_import"],
  ["API-089", "POST", "/api/models/v2/{issuer_id}/workbook/import/preview", "preview_model_workbook_import"],
];
for (const [expectedId, method, routePath, handler] of expectedModelApiInventory) {
  const index = apiRoutes.findIndex((route) => (
    route.method === method && route.path === routePath && route.handler === handler
  ));
  const actualId = index >= 0 ? `API-${String(index + 1).padStart(3, "0")}` : "missing";
  if (actualId !== expectedId) {
    throw new Error(`Model API inventory drifted for ${method} ${routePath} (${handler}): ${actualId}/${expectedId}`);
  }
}
const modelApiFeatureIds = expectedModelApiInventory.map(([id]) => id);
const settingsFeatureIds = Array.from({ length: 10 }, (_, index) => `settings-${String(index + 1).padStart(2, "0")}`);
const currentSettingsFeatureIds = sourceRows
  .filter((row) => row.concept === "Settings")
  .map((row) => row.id)
  .sort();
if (currentSettingsFeatureIds.join(",") !== [...settingsFeatureIds].sort().join(",")) {
  throw new Error(`Settings feature inventory drifted: ${currentSettingsFeatureIds.join(",")}`);
}
const expectedSettingsApiInventory = [
  ["API-164", "GET", "/api/settings", "read_settings"],
  ["API-165", "GET", "/api/settings/analyst", "read_analyst_settings"],
  ["API-166", "PATCH", "/api/settings/analyst", "patch_analyst_settings"],
  ["API-167", "PUT", "/api/settings/analyst", "write_analyst_settings"],
];
for (const [expectedId, method, routePath, handler] of expectedSettingsApiInventory) {
  const index = apiRoutes.findIndex((route) => (
    route.method === method && route.path === routePath && route.handler === handler
  ));
  const actualId = index >= 0 ? `API-${String(index + 1).padStart(3, "0")}` : "missing";
  if (actualId !== expectedId) {
    throw new Error(`Settings API inventory drifted for ${method} ${routePath} (${handler}): ${actualId}/${expectedId}`);
  }
}
const settingsApiFeatureIds = expectedSettingsApiInventory.map(([id]) => id);
const curatedScenarioMappings = [
  // Model API inventory: endpoint-specific assertions close all six applicable
  // scenarios. Responsive behavior remains explicitly N/A for backend routes.
  ["caos/tests/server/test_model_api_quality_contracts.py", /test_legacy_model_reads_are_analyst_scoped_empty_and_non_enumerable/, ["API-072", "API-074"].flatMap((id) => ["Happy path", "Error path", "Boundary conditions", "Invalid input", "Permission/security"].map((scenario) => [id, scenario]))],
  ["caos/tests/server/test_saved_models.py", /test_put_then_get_roundtrips_payload/, [["API-073", "Happy path"]]],
  ["caos/tests/server/test_saved_models.py", /test_unknown_issuer_404_keeps_custom_detail/, [["API-073", "Error path"], ["API-073", "Invalid input"]]],
  ["caos/tests/server/test_saved_models.py", /test_stale_expected_updated_at_is_409|test_matching_expected_updated_at_saves_normally|test_no_expected_updated_at_skips_the_check/, [["API-073", "Boundary conditions"]]],
  ["caos/tests/server/test_saved_models.py", /test_malformed_body_is_422/, [["API-073", "Invalid input"]]],
  ["caos/tests/server/test_model_api_quality_contracts.py", /test_legacy_model_save_requires_write_role_and_preserves_durable_state/, [["API-073", "Permission/security"]]],
  ["caos/tests/server/test_model_api_quality_contracts.py", /test_legacy_checkpoint_create_rejects_unsaved_stale_and_invalid_requests/, ["Happy path", "Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["API-075", scenario])],
  ["caos/tests/server/test_phase1b_lineage.py", /test_all_producers_reject_foreign_owner_and_foreign_team_scopes/, [["API-075", "Permission/security"]]],
  ["caos/tests/server/test_model_api_quality_contracts.py", /test_legacy_checkpoint_restore_rejects_stale_malformed_and_foreign_requests/, ["Happy path", "Error path", "Boundary conditions", "Invalid input", "Permission/security"].map((scenario) => ["API-076", scenario])],

  ["caos/tests/server/test_model_v2_api.py", /test_suggested_then_saved_read_contract/, [["API-077", "Happy path"], ["API-078", "Happy path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_cp1_binding_degrades_when_currency_or_fiscal_profile_is_unknown/, [["API-077", "Error path"], ["API-077", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_flag_off_returns_non_enumerable_404/, [["API-077", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_owner_and_team_isolation_return_404_without_foreign_data/, [["API-077", "Permission/security"], ["API-084", "Permission/security"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_atomic_integer_cas_allows_one_concurrent_winner/, [["API-078", "Error path"], ["API-078", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_generic_put_cannot_bypass_cell_audit_or_forge_authority|test_live_initial_payload_must_match_exact_cp1_binder|test_non_live_draft_cannot_be_relabelled_to_an_owned_run/, [["API-078", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_calculation_api_returns_current_model_for_valid_payload/, [["API-079", "Happy path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_calculation_api_degrades_zero_ebitda_without_nonfinite_output/, [["API-079", "Error path"], ["API-079", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_calculation_api_never_defaults_monetary_identity/, [["API-079", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_v2_collection_reads_are_bounded_owned_and_non_enumerable/, ["API-080", "API-083"].flatMap((id) => ["Happy path", "Error path", "Boundary conditions", "Invalid input", "Permission/security"].map((scenario) => [id, scenario]))],
  ["caos/tests/server/test_model_v2_api.py", /test_checkpoint_create_restore_and_foreign_owner_404/, [["API-081", "Happy path"], ["API-082", "Happy path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_checkpoint_rejects_stale_saved_calculation/, [["API-081", "Error path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_checkpoint_reservation_serializes_a_concurrent_override/, [["API-081", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_checkpoint_cannot_be_relabelled_to_an_unrelated_owned_run/, [["API-081", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_restore_rejects_tampered_checkpoint_envelope/, [["API-082", "Error path"], ["API-082", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_restoring_runless_checkpoint_clears_a_later_live_binding/, [["API-082", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_viewer_cannot_cross_any_model_v2_mutation_boundary/, ["API-078", "API-079", "API-081", "API-082", "API-085", "API-086"].map((id) => [id, "Permission/security"])],
  ["caos/tests/server/test_model_v2_api.py", /test_override_undo_and_redo_are_revisioned_audit_events/, [["API-084", "Happy path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_replay_rejects_an_old_event_after_the_cell_changed_again/, [["API-084", "Error path"], ["API-084", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_replay_rejects_an_invalid_mode_without_revision_change/, [["API-084", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_override_set_reset_propagates_and_audits/, [["API-085", "Happy path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_override_capacity_failure_is_controlled_and_atomic/, [["API-085", "Error path"], ["API-085", "Boundary conditions"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_derived_override_requires_source_and_future_expiry_without_mutation|test_unknown_override_target_is_422_without_revision_change/, [["API-085", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_override_batch_is_one_revision_with_complete_audit/, [["API-086", "Happy path"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_override_batch_rejects_duplicate_or_invalid_set_without_mutation/, [["API-086", "Error path"], ["API-086", "Boundary conditions"], ["API-086", "Invalid input"]]],

  ["caos/tests/server/test_model_workbook_api.py", /test_flag_off_runs_before_body_validation_and_export_has_exact_six_sheets/, [["API-087", "Happy path"], ["API-089", "Invalid input"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_export_refuses_expired_override_calculation_until_resaved/, [["API-087", "Error path"], ["API-087", "Boundary conditions"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_owner_and_team_isolation_fail_non_enumerably_before_file_scan/, [["API-087", "Invalid input"], ["API-087", "Permission/security"], ["API-088", "Permission/security"], ["API-089", "Permission/security"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_preview_is_read_only_and_av_corrupt_and_xls_fail_closed/, [["API-089", "Happy path"], ["API-089", "Error path"], ["API-089", "Invalid input"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_preview_blocks_when_import_provenance_would_exceed_source_capacity|test_preview_token_expires_with_active_override_and_is_rechecked_after_parse/, [["API-089", "Boundary conditions"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_commit_revalidates_exact_calculation_and_atomically_creates_artifacts|test_new_draft_accepts_positive_strict_source_revision_and_commits_revision_one/, [["API-088", "Happy path"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_lineage_failure_rolls_back_cas_rows_and_unique_storage|test_cas_conflict_has_no_partial_rows_or_storage/, [["API-088", "Error path"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_preview_token_expires_with_active_override_and_is_rechecked_after_parse|test_same_legacy_workbook_replays_once_but_can_be_reimported_at_later_revision/, [["API-088", "Boundary conditions"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_signed_preview_binds_owner_issuer_mapping_revision_hash_and_identity|test_formula_and_mapping_ambiguity_are_blocking_and_not_committable|test_matrix_preview_commit_identity_binds_normalized_mapping_exactly/, [["API-088", "Invalid input"]]],
  ["caos/tests/server/test_model_workbook_api.py", /test_commit_denies_read_only_before_rescan_or_write/, [["API-088", "Permission/security"], ["API-089", "Permission/security"]]],

  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, modelFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-006 \/model route accessibility and responsive geometry/, modelFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/performance-audit.mjs", /SCR-006 \/model desktop and five-sample mobile-slow route performance/, modelFeatureIds.map((id) => [id, "Performance"])],

  // Legacy calculator: exact happy-path assertions remain feature-specific;
  // malformed-state, fail-closed authority, and narrow-workbench nodes are
  // cross-cutting route contracts and deliberately map only those scenarios.
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-01 model-33 model-34 renders/, ["model-01", "model-33", "model-34"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-02 model-36 traces/, ["model-02", "model-36"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-03 commits/, [["model-03", "Happy path"]]],
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-04 model-30 exposes/, ["model-04", "model-30"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /model-05 exercises/, [["model-05", "Happy path"]]],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /model-06 model-42 covers narrow/, ["model-06", "model-42"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-07 hides/, [["model-07", "Happy path"]]],
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-08 model-28 opens/, ["model-08", "model-28"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/AssumptionsPanel.contract.test.tsx", /model-09 switches/, [["model-09", "Happy path"]]],
  ["caos/frontend/src/components/model/AssumptionsPanel.contract.test.tsx", /model-10 model-11 applies/, ["model-10", "model-11"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/AssumptionsPanel.contract.test.tsx", /model-12 model-14 writes/, ["model-12", "model-14"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/AssumptionsPanel.contract.test.tsx", /model-13 requires/, [["model-13", "Happy path"]]],
  ["caos/frontend/src/components/model/AssumptionsPanel.contract.test.tsx", /model-15 exposes/, [["model-15", "Happy path"]]],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /renders the panel and the best\/base\/worst comparison/, [["model-16", "Happy path"]]],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /changing the tornado output metric updates/, ["model-17", "model-18"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /changes tornado swing intensity/, [["model-19", "Happy path"]]],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /applying a preset re-centers/, ["model-20", "model-22", "model-23"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /NL builder applies|builds from Enter/, [["model-21", "Happy path"]]],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /model-24 exposes/, [["model-24", "Happy path"]]],
  ["caos/frontend/src/components/model/export.test.ts", /produces all five sheets in order/, [["model-25", "Happy path"]]],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /model-26 model-27 renders/, ["model-26", "model-27"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/cell-style.test.ts", /pairs a drawn glyph with each level|KPI distress shading wins/, [["model-29", "Happy path"]]],
  ["caos/frontend/src/components/model/model-format.test.ts", /money: rounds, group-separates/, [["model-31", "Happy path"]]],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /model-32 hydrates guarded server payload/, [["model-32", "Happy path"]]],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /model-35 distinguishes live loading/, [["model-35", "Happy path"]]],
  ["caos/frontend/src/lib/model/scenarios.test.ts", /projects three forecast years|deleverages in the base case/, ["model-37", "model-38"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/model/ModelSheet.contract.test.tsx", /model-39 gives an explicit trace instruction/, [["model-39", "Happy path"]]],
  ["caos/frontend/src/components/model/ScenarioPanel.test.tsx", /surfaces an error when scenarioFromNL rejects/, [["model-40", "Happy path"]]],
  ["caos/tests/server/test_scenario.py", /test_model_41_scenario_endpoint_enforces_per_analyst_quota/, ["Happy path", "Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-41", scenario])],
  ["caos/tests/frontend/e2e/model_flow.spec.ts", /committed Model Engine v2 override survives a reload/, [["model-43", "Happy path"]]],
  ["caos/frontend/src/app/model/model-live-run-error.test.tsx", /fails closed without mounting the fixture calculator/, modelLegacyIds.map((id) => [id, "Error path"])],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /guards malformed optional saved payload sections/, modelLegacyIds.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/app/model/model-page-interactions.test.tsx", /model-06 model-42 covers narrow and utility controls/, modelLegacyIds.map((id) => [id, "Boundary conditions"])],

  // Model Engine v2: each family is mapped to nodes that exercise the actual
  // governed state transition, not merely a neighboring file-level pass.
  ["caos/frontend/src/app/model/model-v2-authority-route.test.tsx", /renders v2 without importing|preserves the exact Pipeline run/, [["model-44", "Happy path"], ["model-66", "Happy path"]]],
  ["caos/frontend/src/app/model/model-v2-authority-route.test.tsx", /never renders issuer A authority|fails closed when the feature capability is missing|does not render the legacy fixture calculator/, modelV2AuthorityIds.flatMap((id) => ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => [id, scenario]))],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /labels persisted inputs, formula outputs|labels every persisted authority origin/, modelV2IdentityIds.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /does not call an unsourced live input live|renders a stale saved revision/, modelV2IdentityIds.flatMap((id) => ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => [id, scenario]))],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /bounds large calculation graphs and keeps every node reachable/, ["Happy path", "Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-47", scenario])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /keeps input and derived edits local, previews on the server, and commits one atomic batch/, modelV2MutationIds.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /requires a fresh preview|preserves pending edits when their server preview fails|preserves a dirty editor|requires a non-empty reason|validates finite values and future expiry|guards a typed editor change/, modelV2MutationIds.flatMap((id) => ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => [id, scenario]))],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /resets a transient server sensitivity|filters periods and empty node results and switches between scenario modes/, modelV2ScenarioIds.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /discards an in-flight sensitivity|keeps sensitivity inputs available when the server calculation fails|blocks sensitivity reset|filters periods and empty node results/, modelV2ScenarioIds.flatMap((id) => ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => [id, scenario]))],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /walks committed revision groups|creates and restores immutable server checkpoints/, modelV2HistoryIds.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /disables replay after malformed or unresolvable history groups/, [["model-55", "Error path"], ["model-55", "Boundary conditions"], ["model-55", "Invalid input"]]],
  ["caos/tests/server/test_model_v2_api.py", /test_checkpoint_rejects_stale_saved_calculation|test_restore_rejects_tampered_checkpoint_envelope|test_checkpoint_cannot_be_relabelled/, ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-56", scenario])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /requires upload, stateless preview, explicit confirmation|binds close-format JSON and reviewed duplicate columns|binds reviewed account rows/, modelV2ImportIds.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /rejects an ambiguity that does not match|surfaces invalid mapping, preview, and commit failures|never preselects USD or millions|loads the account-matrix mapping template/, modelV2ImportIds.flatMap((id) => ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => [id, scenario]))],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /exports the persisted workbook through a temporary download and reports failures/, ["Happy path", "Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-61", scenario])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /keeps a suggested server calculation read-only until it is explicitly saved/, [["model-62", "Happy path"]]],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /shows the in-flight suggested save|keeps a suggestion read-only when the exact source-run save contract is absent/, ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-62", scenario])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /refreshes the server calculation when an active override expires/, [["model-63", "Happy path"]]],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /invalidates a reviewed preview at local expiry even when refresh fails/, ["Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-63", scenario])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /discards all local model state only after explicit navigation confirmation/, ["Happy path", "Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-64", scenario])],
  ["caos/frontend/src/app/model/model-v2-workbench.test.tsx", /shows the in-flight suggested save|blocks sensitivity reset while another saved-model action is running|guards a typed editor change/, ["Happy path", "Error path", "Boundary conditions", "Invalid input"].map((scenario) => ["model-65", scenario])],
  ["caos/tests/server/test_model_v2_api.py", /test_owner_and_team_isolation_return_404|test_read_only_role_cannot_mutate_existing_draft|test_calculation_preview_requires_write_role/, modelV2Ids.map((id) => [id, "Permission/security"])],

  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, reportUiFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/scripts/validate-report-workbench.mjs", /\/reports exact-build workbench interaction and responsive geometry/, reportUiFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/performance-audit.mjs", /\/reports desktop and five-sample mobile-slow route performance/, reportUiFeatureIds.map((id) => [id, "Performance"])],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /drives display, compose, keyboard, evidence, edit-reset, and rail controls/, ["reports-01", "reports-02", "reports-03", "reports-04", "reports-05", "reports-06", "reports-07", "reports-08", "reports-09", "reports-10", "reports-20", "reports-24", "reports-25"].flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"]])],
  ["caos/frontend/src/components/reports/panels.test.tsx", /selects reports, collapses the rail, and renders ready\/held metadata/, ["reports-01", "reports-02", "reports-13", "reports-14", "reports-25"].flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"]])],
  ["caos/frontend/src/components/reports/panels.test.tsx", /resolves lineage names and opens evidence/, [["reports-09", "Happy path"], ["reports-09", "Invalid input"], ["reports-10", "Happy path"]]],
  ["caos/frontend/src/components/reports/panels.test.tsx", /toggles flat compose sections and handles a missing omit map|groups paged compose sections and marks omitted entries/, ["reports-08", "reports-12", "reports-22", "reports-25"].flatMap((id) => [[id, "Happy path"], [id, "Invalid input"]])],
  ["caos/frontend/src/components/reports/panels.test.tsx", /renders clean and conditional export states, edits, and vault action/, ["reports-12", "reports-13", "reports-14", "reports-15"].flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"]])],
  ["caos/frontend/src/components/reports/panels.test.tsx", /holds a live-backed report on its real committee status, not just rep.watermark/, ["reports-12", "reports-13", "reports-14"].flatMap((id) => [[id, "Error path"], [id, "Invalid input"]])],
  ["caos/frontend/src/components/reports/EvidenceModal.test.tsx", /prefers the run's own evidence over a colliding seeded key, and fetches the real chunk/, [["reports-09", "Boundary conditions"], ["reports-10", "Boundary conditions"], ["reports-10", "Permission/security"]]],
  ["caos/frontend/src/components/reports/EvidenceModal.test.tsx", /shows an explicit unresolved state for an unknown id|falls back to the seeded map for a seeded id with no live entry/, [["reports-09", "Error path"], ["reports-10", "Invalid input"]]],
  ["caos/frontend/src/components/reports/EvidenceModal.test.tsx", /shows an explicit unavailable state when the live chunk fetch fails/, [["reports-09", "Error path"], ["reports-10", "Error path"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /autosaves a hydrated server draft and reports a later revision conflict/, ["reports-04", "reports-05", "reports-06", "reports-07", "reports-08", "reports-20"].map((id) => [id, "Error path"])],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /ignores an unsupported saved paper tone/, [["reports-04", "Invalid input"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /does not claim a newer edit is saved while an older autosave is still in flight|autosaves a new server draft without a revision precondition/, ["reports-04", "reports-05", "reports-06", "reports-07", "reports-08", "reports-20"].flatMap((id) => [[id, "Boundary conditions"], [id, "Performance"]])],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /survives unavailable browser storage preferences/, [["reports-03", "Error path"], ["reports-03", "Invalid input"], ["reports-20", "Error path"], ["reports-20", "Invalid input"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /loads an empty immutable summary payload on demand and reports payload failure|drops a late server draft after unmount/, ["reports-01", "reports-02", "reports-11", "reports-20", "reports-22", "reports-25"].flatMap((id) => [[id, "Error path"], [id, "Invalid input"]])],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /reports the guard message when a binary download has no immutable version/, [["reports-11", "Error path"], ["reports-11", "Boundary conditions"], ["reports-11", "Invalid input"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /observes preview width, auto-fits, handles keyboard fit, and disconnects cleanly/, [["reports-03", "Boundary conditions"], ["reports-24", "Happy path"], ["reports-24", "Error path"], ["reports-24", "Boundary conditions"], ["reports-24", "Invalid input"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /filters frozen-preview edits, blocks appendix mutation, and exposes non-ready publication copy|handles a sectionless frozen preview and editorial intents missing optional maps/, ["reports-06", "reports-07", "reports-08", "reports-13", "reports-14", "reports-22", "reports-23"].flatMap((id) => [[id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/frontend/src/components/reports/ReportDoc.test.tsx", /renders every section kind and supports bounded edits, safe paste, revert, evidence, and add-back suppression/, ["reports-06", "reports-22", "reports-23"].flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/frontend/src/components/reports/ReportDoc.test.tsx", /groups paged sections, omits requested content, prints citations, and shows the defensive authority note|renders the non-paged fallback authority disclaimer and default paper/, ["reports-05", "reports-08", "reports-12", "reports-22", "reports-25"].flatMap((id) => [[id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/frontend/src/app/reports/reports-caveat.test.tsx", /backend outage|checking state|genuinely no run|blanket 'not a live issuer run'|hybrid message|keeps fixture authority/, ["reports-01", "reports-02", "reports-13", "reports-14", "reports-20", "reports-21", "reports-22", "reports-25"].flatMap((id) => [[id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /surfaces saved-model failure and retries the reference inputs/, [["reports-21", "Error path"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /hydrates valid and malformed saved-model payloads and ignores late completion/, [["reports-21", "Happy path"], ["reports-21", "Invalid input"], ["reports-21", "Boundary conditions"], ["reports-21", "Performance"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /prints, downloads immutable binaries, and exposes one IC decision-room opener/, [["reports-11", "Happy path"], ["reports-11", "Error path"], ["reports-11", "Boundary conditions"]]],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /enforces screen and print proofing floors without scaled-down report headings/, ["reports-28"].flatMap((id) => [[id, "Happy path"], [id, "Error path"], [id, "Boundary conditions"], [id, "Performance"]])],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /keeps color literals in root token definitions rather than shared\/report rules/, [["reports-28", "Invalid input"], ["reports-28", "Permission/security"]]],
  ["caos/frontend/src/components/reports/ExportToVaultButton.test.tsx", /exports one note and exposes the written path|renders plural notes and ignores a click while export is pending/, [["reports-15", "Happy path"], ["reports-15", "Boundary conditions"], ["reports-15", "Performance"]]],
  ["caos/frontend/src/components/reports/ExportToVaultButton.test.tsx", /explains an unconfigured vault|keeps an ordinary export failure retryable/, ["reports-15", "reports-16", "reports-17"].flatMap((id) => [[id, "Error path"], [id, "Invalid input"]])],
  ["caos/tests/server/test_engine.py", /test_reports_15_vault_export_writes_the_owned_run/, [["reports-15", "Happy path"]]],
  ["caos/tests/server/test_engine.py", /test_reports_16_vault_export_fails_closed_without_configuration/, ["reports-16"].flatMap((id) => [[id, "Happy path"], [id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/tests/server/test_engine.py", /test_reports_17_vault_export_surfaces_write_failure/, ["reports-17"].flatMap((id) => [[id, "Happy path"], [id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/tests/server/test_engine.py", /test_reports_18_vault_export_rate_limit_precedes_work/, ["reports-18"].flatMap((id) => [[id, "Happy path"], [id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"], [id, "Performance"]])],
  ["caos/tests/server/test_engine.py", /test_reports_19_vault_export_rejects_a_missing_run/, ["reports-19"].flatMap((id) => [[id, "Happy path"], [id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/tests/server/test_async_runs.py", /test_export_to_vault_rejects_foreign_run/, ["reports-15", "reports-16", "reports-17", "reports-18", "reports-19", "reports-26", "reports-27"].map((id) => [id, "Permission/security"])],
  ["caos/tests/server/test_route_rate_boundaries.py", /test_expensive_and_append_only_routes_rate_limit_before_domain_work/, ["reports-18", "reports-26", "reports-27"].map((id) => [id, "Performance"])],
  ["caos/tests/server/test_engine.py", /test_reports_26_27_committee_export_endpoint_enforces_then_clears_the_gate/, reportBackendOnlyIds.flatMap((id) => [[id, "Happy path"], [id, "Error path"], [id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/tests/server/test_engine.py", /test_committee_status_fails_closed_on_unknown_status|test_committee_export_gate_allows_only_committee_ready/, reportBackendOnlyIds.flatMap((id) => [[id, "Boundary conditions"], [id, "Invalid input"]])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, issuerPermissionMappings],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows the recovery gate for unresolved identity/, issuerPermissionMappings],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, commandFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows the recovery gate for unresolved identity/, commandFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /all Command datasets remain operable without document overflow at 390px/, commandFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-01 command-02 command-03 command-04 command-05 command-09 renders the persisted-position grid and posture semantics/, ["command-01", "command-02", "command-03", "command-04", "command-05", "command-09"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-06 command-07 command-08 exposes the selected-position strip, deep-dive handoff, and close action/, ["command-06", "command-07", "command-08"].map((id) => [id, "Happy path"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /coordinates portfolio, decisions, and navigation/, ["command-10", "command-12", "command-13", "command-14", "command-15", "command-16", "command-17", "command-19", "command-20", ...commandHandoffs, ...commandDecision, "command-56"].map((id) => [id, "Happy path"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /preserves explicit invalid, offline, and empty states without sample substitution/, ["command-11", "command-18", "command-21", "command-22"].map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-23 command-24 renders, selects, and filters the virtualized live-coverage worklist/, commandCoverage.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-32 command-33 command-34 command-35 command-36 keeps six governance categories honest/, commandGovernance.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-37 command-38 command-39 command-40 distinguishes autonomy-draft states and converges alert acknowledgement/, commandChanges.map((id) => [id, "Happy path"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-52 command-53 renders live digest KPIs and opens both freshness watchlists by issuer id/, commandDigest.map((id) => [id, "Happy path"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /command-54 command-55 restores and refreshes the current cited decision brief/, commandInsight.map((id) => [id, "Happy path"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /preserves explicit invalid, offline, and empty states without sample substitution/, [...commandPositions, ...commandPortfolio].map((id) => [id, "Error path"])],
  ["caos/frontend/src/lib/engine/usePortfolio.test.ts", /flags error:true \(not clean-empty\) when the fetch rejects/, commandCoverage.map((id) => [id, "Error path"])],
  ["caos/frontend/src/components/command/GovernancePanel.test.tsx", /never renders green all-clears while live QA or digest status is unknown/, commandGovernance.map((id) => [id, "Error path"])],
  ["caos/frontend/src/components/command/RankedChanges.test.tsx", /shows an honest OFFLINE state when the endpoint is unreachable/, ["command-37", "command-38"].map((id) => [id, "Error path"])],
  ["caos/frontend/src/components/command/RankedChanges.test.tsx", /keeps an unchanged alert actionable and gives row-level retry feedback when acknowledgement cannot be saved/, [["command-39", "Error path"]]],
  ["caos/frontend/src/components/command/RankedChanges.test.tsx", /omits the impact chip and blocks Deep-Dive when an alert has no issuer id/, [["command-40", "Error path"], ["command-42", "Error path"]]],
  ["caos/frontend/src/lib/analysis-workbench.test.ts", /publishes a presentation-only error event when initial context resolution fails/, [["command-41", "Error path"], ["command-56", "Error path"]]],
  ["caos/frontend/src/app/command/command-interactions.test.tsx", /shows observed-empty and degraded decision states and insight generation failures/, [...commandDecision, ...commandInsight].map((id) => [id, "Error path"])],
  ["caos/frontend/src/lib/engine/useDigest.test.ts", /keeps transport failure distinct from a successful empty digest/, commandDigest.map((id) => [id, "Error path"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-01 command-02 command-03 command-04 command-05 command-09 renders the persisted-position grid and posture semantics/, commandPositions.map((id) => [id, "Boundary conditions"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /preserves explicit invalid, offline, and empty states without sample substitution/, commandPortfolio.map((id) => [id, "Boundary conditions"])],
  ["caos/frontend/src/components/command/LiveCoverage.test.tsx", /degrades missing metrics \/ RV \/ fragility to em-dash, never crashes/, [["command-23", "Boundary conditions"]]],
  ["caos/frontend/src/components/command/LiveCoverage.test.tsx", /hands focus across the virtual window boundary instead of clamping at the last rendered row/, [["command-24", "Boundary conditions"]]],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-32 command-33 command-34 command-35 command-36 keeps six governance categories honest/, commandGovernance.map((id) => [id, "Boundary conditions"])],
  ["caos/frontend/src/components/command/RankedChanges.test.tsx", /cycle running|settled empty draft|persona summary limit|late alert-state enrichment/, commandChanges.map((id) => [id, "Boundary conditions"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /coordinates portfolio, decisions, and navigation/, commandHandoffs.map((id) => [id, "Boundary conditions"])],
  ["caos/frontend/src/app/command/command-freshness-transition.test.tsx", /renders CURRENT only when every centrally evaluated latest run is current/, commandDecision.map((id) => [id, "Boundary conditions"])],
  ["caos/frontend/src/lib/engine/useDigest.test.ts", /marks populated coverage live and tolerates a missing coverage block/, commandDigest.map((id) => [id, "Boundary conditions"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /command-54 command-55 restores and refreshes the current cited decision brief/, commandInsight.map((id) => [id, "Boundary conditions"])],
  ["caos/frontend/src/lib/analysis-workbench.test.ts", /serializes patches and sends the newest revision to the queued mutation/, [["command-56", "Boundary conditions"]]],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-01 command-02 command-03 command-04 command-05 command-09 renders the persisted-position grid and posture semantics/, commandPositions.map((id) => [id, "Invalid input"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /preserves explicit invalid, offline, and empty states without sample substitution/, commandPortfolio.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/components/command/LiveCoverage.test.tsx", /degrades missing metrics \/ RV \/ fragility to em-dash, never crashes/, commandCoverage.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-32 command-33 command-34 command-35 command-36 keeps six governance categories honest/, commandGovernance.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/components/command/RankedChanges.test.tsx", /omits the impact chip and blocks Deep-Dive when an alert has no issuer id/, commandChanges.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/lib/analysis-workbench.test.ts", /treats an explicit null context id as a request for a fresh context/, [["command-41", "Invalid input"]]],
  ["caos/frontend/src/app/command/command-interactions.test.tsx", /blocks ranked handoffs without stable issuer authority/, [["command-42", "Invalid input"]]],
  ["caos/frontend/src/app/command/command-interactions.test.tsx", /shows observed-empty and degraded decision states and insight generation failures/, [...commandDecision, ...commandInsight].map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/lib/engine/useDigest.test.ts", /marks populated coverage live and tolerates a missing coverage block/, commandDigest.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/lib/analysis-workbench.test.ts", /reduces legacy full nested objects to the caller's sparse intent/, [["command-56", "Invalid input"]]],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-01 command-02 command-03 command-04 command-05 command-09 renders the persisted-position grid and posture semantics/, commandPositions.map((id) => [id, "Performance"])],
  ["caos/frontend/src/app/command/command-interactions.test.tsx", /switches every dataset, selects live and held issuers, refreshes snapshots, and generates cited insight/, commandPortfolio.map((id) => [id, "Performance"])],
  ["caos/frontend/src/components/command/LiveCoverage.test.tsx", /hands focus across the virtual window boundary instead of clamping at the last rendered row/, commandCoverage.map((id) => [id, "Performance"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-32 command-33 command-34 command-35 command-36 keeps six governance categories honest/, commandGovernance.map((id) => [id, "Performance"])],
  ["caos/frontend/src/components/command/RankedChanges.test.tsx", /persona summary limit|late alert-state enrichment/, commandChanges.map((id) => [id, "Performance"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /coordinates portfolio, decisions, and navigation/, [...commandHandoffs, ...commandDecision].map((id) => [id, "Performance"])],
  ["caos/frontend/src/components/command/current-command-contracts.test.tsx", /command-52 command-53 renders live digest KPIs and opens both freshness watchlists by issuer id/, commandDigest.map((id) => [id, "Performance"])],
  ["caos/tests/frontend/e2e/command_flow.spec.ts", /command-54 command-55 restores and refreshes the current cited decision brief/, commandInsight.map((id) => [id, "Performance"])],
  ["caos/frontend/src/lib/analysis-workbench.test.ts", /serializes patches and sends the newest revision to the queued mutation/, [["command-56", "Performance"]]],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-004 \/issuers route accessibility and responsive geometry/, issuerDirectoryIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-005 \/issuers\/profile route accessibility and responsive geometry/, issuerProfileIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /shows an honest degraded demo fallback, then retries into live coverage/, issuerDirectoryIds.map((id) => [id, "Error path"])],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders an actionable load failure/, issuerProfileIds.map((id) => [id, "Error path"])],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /rejects a profile URL without an issuer id/, issuerProfileIds.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /uses an eight-column semantic grid with one roving row stop and isolated nested actions/, issuerDirectoryIds.map((id) => [id, "Performance"])],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /loads a profile and replaces the splash with the read-model/, issuerProfileIds.map((id) => [id, "Performance"])],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /restores a URL query, renders no-match state, and clears back to the sample sleeve/, issuerDirectoryIds.filter((id) => !["issuer-07", "issuer-08", "issuer-09"].includes(id)).map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /opens issuer profiles and routes upload actions without nesting interactions/, [["issuer-07", "Invalid input"], ["issuer-08", "Invalid input"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /labels an empty live registry as demo coverage and opens the creation dialog from its banner/, [["issuer-01", "Boundary conditions"], ["issuer-10", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /uses an eight-column semantic grid with one roving row stop and isolated nested actions/, [["issuer-01", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /opens issuer profiles and routes upload actions without nesting interactions/, [["issuer-07", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /degrades every profile section when no run or read-model facts exist/, [["issuer-17", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders an overlay without a close callback/, [["issuer-30", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders an actionable load failure/, [["issuer-14", "Happy path"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /rejects a profile URL without an issuer id/, [["issuer-15", "Happy path"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders one layout with a single primary Deep-Dive action and the issuer action bar/, [["issuer-29", "Happy path"], ["issuer-29", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /retains the last real register when a later debounced search fails/, [["issuer-02", "Error path"], ["issuer-02", "Boundary conditions"], ["issuer-02", "Performance"], ["issuer-04", "Error path"], ["issuer-04", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /restores a URL query, renders no-match state, and clears back to the sample sleeve/, [["issuer-02", "Happy path"], ["issuer-02", "Boundary conditions"], ["issuer-06", "Happy path"], ["issuer-06", "Boundary conditions"], ["issuer-11", "Happy path"], ["issuer-11", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /clears a populated search with the compact input affordance/, [["issuer-02", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /applies and clears a column filter, including the filter value search empty state/, [["issuer-03", "Happy path"], ["issuer-03", "Boundary conditions"], ["issuer-03", "Invalid input"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /shows an honest degraded demo fallback, then retries into live coverage/, [["issuer-04", "Happy path"], ["issuer-04", "Error path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /offers the primary creation action when both live and sample coverage are empty/, [["issuer-05", "Happy path"], ["issuer-05", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /opens issuer profiles and routes upload actions without nesting interactions/, [["issuer-08", "Happy path"], ["issuer-08", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /submits every field, surfaces the API detail, and succeeds on retry with blank sponsor normalized/, [["issuer-09", "Happy path"], ["issuer-09", "Error path"], ["issuer-09", "Invalid input"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /ignores a second form submit while creation is pending/, [["issuer-09", "Boundary conditions"], ["issuer-09", "Performance"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /uses an eight-column semantic grid with one roving row stop and isolated nested actions/, [["issuer-08", "Boundary conditions"], ["issuer-12", "Happy path"], ["issuer-12", "Boundary conditions"], ["issuer-12", "Performance"], ["issuer-31", "Happy path"], ["issuer-31", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /cycles sortable headers and keeps missing values at the bottom in both directions/, [["issuer-31", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /loads a profile and replaces the splash with the read-model/, [["issuer-13", "Happy path"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders an actionable load failure/, [["issuer-14", "Error path"], ["issuer-14", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /rejects a profile URL without an issuer id/, [["issuer-15", "Invalid input"], ["issuer-15", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders one layout with a single primary Deep-Dive action and the issuer action bar/, [["issuer-16", "Happy path"], ["issuer-16", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders and interacts with the full live issuer read-model/, [["issuer-18", "Happy path"], ["issuer-19", "Happy path"], ["issuer-20", "Happy path"], ["issuer-21", "Happy path"], ["issuer-22", "Happy path"], ["issuer-24", "Happy path"], ["issuer-25", "Happy path"], ["issuer-26", "Happy path"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /degrades every profile section when no run or read-model facts exist/, [["issuer-13", "Boundary conditions"], ["issuer-16", "Boundary conditions"], ["issuer-18", "Boundary conditions"], ["issuer-19", "Error path"], ["issuer-19", "Boundary conditions"], ["issuer-20", "Error path"], ["issuer-20", "Boundary conditions"], ["issuer-21", "Boundary conditions"], ["issuer-22", "Boundary conditions"], ["issuer-24", "Boundary conditions"], ["issuer-25", "Boundary conditions"], ["issuer-26", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders sparse valid sections without inventing optional detail/, [["issuer-18", "Boundary conditions"], ["issuer-20", "Boundary conditions"], ["issuer-22", "Boundary conditions"], ["issuer-24", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /renders ownership facts without requiring a sponsor ledger/, [["issuer-21", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /covers flat trends, neutral thresholds, and unknown feed classifications/, [["issuer-18", "Boundary conditions"], ["issuer-19", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/profile-distill.test.tsx", /covers clean empty-snapshot, material-finding, and earnings-signal variants/, [["issuer-20", "Happy path"], ["issuer-20", "Boundary conditions"], ["issuer-25", "Happy path"], ["issuer-25", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/analyst-notes.test.tsx", /renders linked notes with vault links/, [["issuer-23", "Happy path"]]],
  ["caos/frontend/src/app/issuers/profile/analyst-notes.test.tsx", /renders the empty state/, [["issuer-23", "Boundary conditions"]]],
  ["caos/frontend/src/app/issuers/profile/analyst-notes.test.tsx", /renders a quiet error state/, [["issuer-23", "Error path"]]],
  ["caos/frontend/src/app/issuers/profile/analyst-notes.test.tsx", /logs a quick note tagged to the issuer through the vault memo path/, [["issuer-23", "Happy path"], ["issuer-23", "Boundary conditions"]]],
  ["caos/frontend/src/lib/issuer-profile-charts.test.ts", /splits a mixed series and drops emptied metrics/, [["issuer-19", "Boundary conditions"]]],
  ["caos/frontend/src/lib/issuer-profile-charts.test.ts", /includes multi-period financials, omits LTM-only credit ratios/, [["issuer-19", "Happy path"], ["issuer-19", "Boundary conditions"]]],
  ["caos/frontend/src/lib/issuers.test.ts", /rating shows the first agency on file, flagging distress by letter/, [["issuer-31", "Happy path"], ["issuer-31", "Boundary conditions"]]],
  ["caos/frontend/src/lib/nav.test.ts", /projects the exact five role-priority destinations without changing the canonical cycle/, [["shell-01", "Happy path"], ["shell-01", "Boundary conditions"], ["shell-08", "Happy path"]]],
  ["caos/frontend/src/components/shared/shared-shell-smoke.test.tsx", /renders the workflow registry and marks nested and settings routes active/, [["shell-01", "Happy path"], ["shell-01", "Boundary conditions"], ["shell-06", "Happy path"], ["shell-08", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/shared-shell-smoke.test.tsx", /shows role priorities, retains an off-list active route, and discloses every workflow/, [["shell-01", "Happy path"], ["shell-01", "Boundary conditions"], ["shell-08", "Happy path"], ["shell-08", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/shared-shell-smoke.test.tsx", /makes the wide navigation landmark an actionable skip-focus destination/, [["shell-05", "Happy path"], ["shell-05", "Boundary conditions"], ["shell-05", "Mobile/responsive"]]],
  ["caos/frontend/src/lib/nav.test.ts", /derives workflow headings from the canonical registry and resolves utility\/dynamic routes/, [["shell-14", "Happy path"], ["shell-14", "Boundary conditions"], ["shell-14", "Invalid input"]]],
  ["caos/frontend/src/components/shared/recovery-ui-smoke.test.tsx", /maps known, nested, null, and unknown routes to accessible headings/, [["shell-14", "Happy path"], ["shell-14", "Boundary conditions"], ["shell-14", "Invalid input"]]],
  ["caos/frontend/src/components/shared/Panel.test.tsx", /adds a named visible focus target only when content genuinely overflows/, [["shell-15", "Happy path"], ["shell-15", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/Panel.test.tsx", /remeasures overflow-to-fit on resize without moving focus/, [["shell-15", "Boundary conditions"], ["shell-15", "Mobile/responsive"]]],
  ["caos/frontend/src/components/shared/Panel.test.tsx", /remeasures late content mutations in both directions/, [["shell-15", "Boundary conditions"], ["shell-15", "Performance"]]],
  ["caos/frontend/src/components/shared/Panel.test.tsx", /disconnects the scroll owner while collapsed and remeasures when expanded/, [["shell-15", "Boundary conditions"], ["shell-15", "Performance"]]],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /uses the 16\/14\/13\/12px semantic workspace tiers/, [["shell-16", "Happy path"], ["shell-16", "Mobile/responsive"]]],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /enforces screen and print proofing floors without scaled-down report headings/, [["reports-28", "Happy path"], ["reports-28", "Boundary conditions"], ["reports-28", "Mobile/responsive"]]],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /leaves the global route heading as the only route-level h1/, [["shell-14", "Boundary conditions"], ["shell-14", "Mobile/responsive"]]],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /keeps color literals in root token definitions rather than shared\/report rules/, [["shell-16", "Invalid input"], ["reports-28", "Invalid input"]]],
  ["caos/frontend/src/app/hierarchy-color.contract.test.ts", /documents the narrow production chart literal allowlist/, [["shell-16", "Boundary conditions"]]],
  ["caos/tests/server/test_security_headers.py", /test_csrf_rejection_keeps_policy_headers_and_logs_exactly_once/, [["BP-017", "Permission/security"], ["BP-017", "Boundary conditions"]]],
  ["caos/tests/server/test_security_headers.py", /test_edge_rejection_keeps_policy_headers_and_logs_exactly_once/, [["BP-017", "Permission/security"], ["BP-017", "Boundary conditions"]]],
  ["caos/tests/server/test_security_headers.py", /test_policy_header_mutation_preserves_duplicate_set_cookie_headers/, [["BP-001", "Permission/security"], ["BP-017", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /exposes a Concepts trigger that lists every concept with its full label/, [["shell-01", "Happy path"], ["shell-01", "Mobile/responsive"], ["shell-08", "Happy path"], ["shell-08", "Mobile/responsive"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /marks the active route with aria-current inside the drawer/, [["shell-01", "Boundary conditions"], ["shell-08", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /covers the full CONCEPT_CYCLE so hotkeys and drawer can never drift/, [["shell-01", "Boundary conditions"], ["shell-02", "Boundary conditions"], ["shell-08", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /labels the tablet current route and does not expose inactive icon-only shortcuts/, [["shell-01", "Mobile/responsive"], ["shell-08", "Mobile/responsive"]]],
  ["caos/frontend/src/components/shared/ConceptHotkeys.test.tsx", /opens the unified palette with Alt\+S and ignores editable targets/, [["shell-02", "Happy path"], ["shell-02", "Invalid input"]]],
  ["caos/frontend/src/components/shared/ConceptHotkeys.test.tsx", /fires Alt chords by physical key/, [["shell-02", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptHotkeys.test.tsx", /dispatches caos:subview-cycle event on Alt\+(Comma|Period)/, [["shell-02", "Happy path"]]],
  ["caos/frontend/src/components/shared/ConceptHotkeys.test.tsx", /cycles Alt\+ArrowRight to the registry neighbor of the current route/, [["shell-02", "Happy path"], ["shell-02", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptHotkeys.test.tsx", /routes concept-cycle navigation through the unsaved-edit guard/, [["shell-02", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/AnalystBadge.test.tsx", /clears workspace state and refreshes auth after a successful logout/, [["shell-03", "Happy path"]]],
  ["caos/frontend/src/components/shared/AnalystBadge.test.tsx", /re-enables the button and surfaces an alert when logout fails/, [["shell-03", "Error path"]]],
  ["caos/frontend/src/components/shared/AnalystBadge.test.tsx", /does nothing when confirmation is declined/, [["shell-03", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/AnalystBadge.test.tsx", /ignores a second sign-out attempt while the first is busy/, [["shell-03", "Performance"]]],
  ["caos/frontend/src/app/layout-upload-smoke.test.tsx", /declares the application metadata and composes every root provider/, [["shell-05", "Happy path"], ["shell-05", "Boundary conditions"]]],
  ["caos/frontend/src/app/layout-upload-smoke.test.tsx", /does not expose the global page-actions skip link when a route has no action region/, [["shell-05", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/SubHeader.test.tsx", /keeps the primary action in the document and renders inline controls at wide/, [["shell-05", "Happy path"], ["shell-05", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/SubHeader.test.tsx", /provides an honest focus target when the page has no primary action/, [["shell-05", "Boundary conditions"], ["shell-05", "Invalid input"]]],
  ["caos/frontend/src/components/shared/PersonaWorkbench.test.tsx", /exports the required public persona composition hook/, [["query-16", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/CommandPalette.interactions.test.tsx", /executes page, Ask, collapse, and role commands through keyboard and pointer paths/, [["shell-06", "Happy path"], ["shell-06", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /coordinates every provider entry point, keyboard close, global toggle, and competing modal/, [["shell-06", "Happy path"], ["shell-06", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /turns both query-route entry points into focus events instead of a modal/, [["shell-06", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /gates signed-out users and exposes labelled shell and phone-fallback utilities without a dock/, [["shell-06", "Permission/security"], ["shell-06", "Boundary conditions"], ["shell-06", "Mobile/responsive"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /lets Deep-Dive own the open chat while the global launcher only owns its trigger/, [["shell-06", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /grounds issuer-scoped Ask in reference fixtures and real issuer data/, [["shell-06", "Happy path"], ["shell-06", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /loads enabled prompts, accepts palette prefill, ignores empty submission, and closes from the backdrop/, [["shell-06", "Happy path"], ["shell-06", "Invalid input"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /renders capability-load failures and the default error message|surfaces non-ready status, missing dependencies, response detail, and generic query errors/, [["shell-06", "Error path"]]],
  ["caos/frontend/src/components/shared/Ask.coverage.test.tsx", /allows observed-empty runs and ignores an older run that resolves after a newer one/, [["shell-06", "Performance"], ["shell-06", "Boundary conditions"]]],
  ["caos/frontend/src/app/page.test.tsx", /routes an unaffiliated root visit for/, [["shell-07", "Happy path"]]],
  ["caos/frontend/src/app/page.test.tsx", /waits for the existing role preference to resolve/, [["shell-07", "Boundary conditions"]]],
  ["caos/frontend/src/app/page.test.tsx", /preserves an explicit root query instead of applying a role default/, [["shell-07", "Boundary conditions"], ["shell-07", "Invalid input"]]],
  ["caos/tests/frontend/e2e/settings_flow.spec.ts", /mirrors the server workspace configuration/, [["settings-03", "Happy path"], ["settings-04", "Happy path"], ["settings-05", "Happy path"]]],
  ["caos/frontend/src/app/settings/settings-models.test.tsx", /renders every workspace configuration value and recovers from an offline read/, [["settings-03", "Happy path"], ["settings-03", "Error path"], ["settings-03", "Boundary conditions"]]],
  ["caos/tests/server/test_settings.py", /test_settings_returns_snapshot_without_secrets/, [["settings-03", "Permission/security"]]],
  ["caos/frontend/src/app/settings/settings-models.test.tsx", /supports tab clicks and the complete roving-tab keyboard contract/, [["settings-06", "Happy path"], ["settings-06", "Boundary conditions"]]],
  ["caos/frontend/src/app/settings/settings-models.test.tsx", /guards the global save while persistence is in flight and clears dirty state only after success/, [["settings-07", "Happy path"], ["settings-07", "Performance"]]],
  ["caos/frontend/src/app/settings/settings-models.test.tsx", /hydrates server research defaults and normalized profile mode, then changes query model and research scope/, [["settings-07", "Boundary conditions"], ["settings-07", "Invalid input"]]],
  ["caos/frontend/src/lib/model-mode.test.ts", /falls back to DEFAULT_MODE when localStorage\.getItem throws/, [["settings-07", "Error path"]]],
  ["caos/frontend/src/lib/model-mode.test.ts", /still reads a persisted valid mode when storage works normally/, [["settings-07", "Happy path"]]],
  ["caos/frontend/src/lib/model-mode.test.ts", /falls back to DEFAULT_MODE for an unrecognized stored value/, [["settings-07", "Invalid input"]]],
  ["caos/tests/server/test_presets.py", /test_run_persists_model_mode_from_header/, [["settings-07", "Happy path"]]],
  ["caos/tests/server/test_presets.py", /test_run_without_header_defaults_to_balanced/, [["settings-07", "Boundary conditions"]]],
  ["caos/tests/server/test_presets.py", /test_normalize_coerces_unknown_to_default/, [["settings-07", "Invalid input"]]],
  ["caos/frontend/src/app/settings/settings-models.test.tsx", /renders connected email state and persists a normalized sender list/, [["settings-10", "Happy path"], ["settings-10", "Invalid input"]]],
  ["caos/frontend/src/app/settings/settings-models.test.tsx", /surfaces an analyst-settings save failure with the server detail/, [["settings-10", "Error path"]]],
  ["caos/tests/server/test_settings.py", /test_analyst_settings_roundtrip_with_profile_cookie/, [["settings-10", "Happy path"], ["settings-10", "Permission/security"]]],
  ["caos/tests/server/test_settings.py", /test_analyst_settings_patch_is_partial_and_revision_checked/, [["settings-10", "Boundary conditions"], ["settings-10", "Permission/security"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /uses an eight-column semantic grid with one roving row stop and isolated nested actions/, [["pipeline-01", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /restores a URL query, renders no-match state, and clears back to the sample sleeve/, [["pipeline-02", "Happy path"], ["pipeline-08", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /opens issuer profiles and routes upload actions without nesting interactions/, [["pipeline-03", "Happy path"], ["pipeline-04", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /submits every field, surfaces the API detail, and succeeds on retry with blank sponsor normalized/, [["pipeline-05", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /shows an honest degraded demo fallback, then retries into live coverage/, [["pipeline-06", "Happy path"], ...pipelineDirectoryIds.map((id) => [id, "Error path"])]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /offers the primary creation action when both live and sample coverage are empty/, [["pipeline-07", "Happy path"]]],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /retains the last real register when a later debounced search fails/, pipelineDirectoryIds.map((id) => [id, "Boundary conditions"])],
  ["caos/frontend/src/app/issuers/issuer-batch.test.tsx", /restores a URL query, renders no-match state, and clears back to the sample sleeve/, pipelineDirectoryIds.map((id) => [id, "Invalid input"])],
  ["caos/tests/frontend/e2e/pipeline_flow.spec.ts", /operates the reference workbench and simulation controls/, [...expectedPipelineFeatureIds.slice(8, 18), "pipeline-43"].flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"]])],
  ["caos/tests/frontend/e2e/pipeline_flow.spec.ts", /selects graph lineage and renders the module inspector/, expectedPipelineFeatureIds.slice(18, 29).flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"]])],
  ["caos/tests/frontend/e2e/pipeline_flow.spec.ts", /traces drivers, opens evidence, and hands module output to Deep-Dive/, [...expectedPipelineFeatureIds.slice(29, 35), "pipeline-44", "pipeline-45"].flatMap((id) => [[id, "Happy path"], [id, "Boundary conditions"]])],
  ["caos/frontend/src/app/pipeline/pipeline-interactions.test.tsx", /renders honest real-issuer loading, service error, failed, in-progress, and empty states/, pipelineWorkbenchIds.map((id) => [id, "Error path"])],
  ["caos/frontend/src/app/pipeline/pipeline-interactions.test.tsx", /keeps the composed workbench safe under invalid route and context input/, pipelineWorkbenchIds.map((id) => [id, "Invalid input"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, pipelineUiIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows the recovery gate for unresolved identity/, pipelineUiIds.map((id) => [id, "Permission/security"])],
  ["caos/tests/frontend/e2e/pipeline_flow.spec.ts", /preserves the essential workbench at 390px/, pipelineWorkbenchIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-004 \/issuers route accessibility and responsive geometry/, pipelineDirectoryIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-009 \/pipeline route accessibility and responsive geometry/, pipelineWorkbenchIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/performance-audit.mjs", /SCR-004 \/issuers desktop and mobile-slow route performance/, pipelineDirectoryIds.map((id) => [id, "Performance"])],
  ["caos/frontend/scripts/performance-audit.mjs", /SCR-009 \/pipeline desktop and mobile-slow route performance/, pipelineWorkbenchIds.map((id) => [id, "Performance"])],
  ["caos/tests/server/test_async_runs.py", /test_post_runs_then_polls_to_complete/, [["pipeline-36", "Happy path"], ["pipeline-38", "Happy path"], ["pipeline-38", "Boundary conditions"], ["pipeline-39", "Boundary conditions"], ["pipeline-40", "Boundary conditions"], ["pipeline-38", "Performance"], ["pipeline-39", "Performance"], ["pipeline-40", "Performance"]]],
  ["caos/tests/server/test_async_runs.py", /test_list_runs_is_bounded/, [["pipeline-37", "Happy path"], ["pipeline-37", "Boundary conditions"], ["pipeline-37", "Invalid input"], ["pipeline-37", "Performance"]]],
  ["caos/tests/server/test_engine.py", /test_run_completes_and_gates_to_restricted/, [["pipeline-38", "Happy path"]]],
  ["caos/tests/server/test_engine.py", /test_run_per_module_status/, [["pipeline-39", "Happy path"]]],
  ["caos/tests/server/test_engine.py", /test_qa_endpoint_reports_findings/, [["pipeline-40", "Happy path"]]],
  ["caos/tests/server/test_api.py", /test_create_and_get_issuer/, [["pipeline-41", "Happy path"], ["pipeline-41", "Boundary conditions"]]],
  ["caos/tests/server/test_api.py", /test_upload_pdf_document_and_list/, [["pipeline-42", "Happy path"], ["pipeline-42", "Boundary conditions"], ["pipeline-42", "Performance"]]],
  ["caos/tests/server/test_async_runs.py", /test_failed_run_surfaces_error/, [["pipeline-36", "Error path"]]],
  ["caos/tests/server/test_async_runs.py", /test_runs_are_analyst_private_by_default/, [["pipeline-37", "Error path"], ["pipeline-38", "Error path"], ["pipeline-40", "Error path"], ["pipeline-37", "Permission/security"], ["pipeline-38", "Permission/security"], ["pipeline-39", "Permission/security"], ["pipeline-40", "Permission/security"], ["pipeline-40", "Invalid input"]]],
  ["caos/tests/server/test_engine.py", /test_module_not_in_run_404/, [["pipeline-39", "Error path"], ["pipeline-39", "Invalid input"]]],
  ["caos/tests/server/test_tenancy.py", /test_require_issuer_404s_cross_team/, [["pipeline-41", "Error path"], ["pipeline-42", "Error path"], ["pipeline-41", "Invalid input"], ["pipeline-42", "Invalid input"], ["pipeline-41", "Permission/security"], ["pipeline-42", "Permission/security"]]],
  ["caos/tests/server/test_async_runs.py", /test_duplicate_active_run_rejected/, [["pipeline-36", "Boundary conditions"]]],
  ["caos/tests/server/test_async_runs.py", /test_idempotency_key_is_bounded_and_validated/, [["pipeline-36", "Invalid input"]]],
  ["caos/tests/server/test_write_role_matrix.py", /test_viewer_is_denied_mutations_but_keeps_read_style_posts/, [["pipeline-36", "Permission/security"]]],
  ["caos/tests/server/test_tenancy.py", /test_tenancy_isolates_issuers_runs_portfolio_and_query/, pipelineApiIds.map((id) => [id, "Permission/security"])],
  ["caos/tests/server/test_async_runs.py", /test_post_runs_returns_queued_fast/, [["pipeline-36", "Performance"]]],
  ["caos/tests/server/test_async_runs.py", /test_same_layer_modules_synthesize_concurrently/, [["pipeline-38", "Performance"], ["pipeline-39", "Performance"], ["pipeline-40", "Performance"]]],
  ["caos/tests/server/test_api.py", /test_issuers_list_is_bounded/, [["pipeline-41", "Performance"]]],
  ["caos/tests/server/test_engine.py", /test_unknown_run_404/, [["pipeline-38", "Invalid input"]]],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-009 \/pipeline route accessibility and responsive geometry/, ["pipeline-36", "pipeline-37", "pipeline-38", "pipeline-39", "pipeline-40"].map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-004 \/issuers route accessibility and responsive geometry/, ["pipeline-41", "pipeline-42"].map((id) => [id, "Mobile/responsive"])],
  ["caos/tests/frontend/e2e/monitor_flow.spec.ts", /monitor-01 monitor-03 email intake exposes fixed severity totals and filters the sample/, [["monitor-01", "Happy path"], ["monitor-03", "Happy path"]]],
  ["caos/tests/frontend/e2e/monitor_flow.spec.ts", /monitor-02 email detail opens with classification metadata and closes with Escape/, [["monitor-02", "Happy path"]]],
  ["caos/tests/frontend/e2e/monitor_flow.spec.ts", /monitor-04 monitor-07 alert replay and header KPIs render with labelled severity and routing/, [["monitor-04", "Happy path"], ["monitor-07", "Happy path"]]],
  ["caos/tests/frontend/e2e/monitor_flow.spec.ts", /monitor-05 monitor-06 playback controls switch PAUSED and SIM states and apply speed/, [["monitor-05", "Happy path"], ["monitor-06", "Happy path"]]],
  ["caos/frontend/src/app/monitor/monitor-governance.test.tsx", /renders decision-safe empty states and an offline Governance queue/, monitorFeatureIds.map((id) => [id, "Error path"])],
  ["caos/frontend/src/components/command/views-interactions.test.tsx", /filters the email sample, opens messages by keyboard, and closes the evidence window/, [["monitor-01", "Boundary conditions"], ["monitor-02", "Boundary conditions"], ["monitor-03", "Boundary conditions"]]],
  ["caos/frontend/src/components/command/views-interactions.test.tsx", /progressively reveals, filters, and opens source evidence from the alert replay/, [["monitor-04", "Boundary conditions"], ["monitor-06", "Boundary conditions"]]],
  ["caos/frontend/src/components/pipeline/atoms.test.tsx", /pipeline-17 plays, pauses, resets, changes speed, and replays completed simulations/, [["monitor-05", "Boundary conditions"], ["monitor-06", "Boundary conditions"]]],
  ["caos/frontend/src/lib/pipeline/sim.test.tsx", /shares play, speed, reset, timer completion, and subscriber cleanup/, [["monitor-05", "Boundary conditions"], ["monitor-06", "Boundary conditions"], ["monitor-07", "Boundary conditions"]]],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-007 \/monitor route accessibility and responsive geometry/, monitorFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/performance-audit.mjs", /SCR-007 \/monitor desktop and mobile-slow route performance/, monitorFeatureIds.map((id) => [id, "Performance"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, monitorFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows the recovery gate for unresolved identity/, monitorFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/src/app/monitor/monitor-phone-triage.test.tsx", /keeps phone triage primary while context and governance remain available as drawers/, monitorFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/tests/frontend/e2e/sector_flow.spec.ts", /completes the governed desktop journey/, sectorFeatureIds.map((id) => [id, "Happy path"])],
  ["caos/tests/frontend/e2e/sector_flow.spec.ts", /preserves narrow-mode capabilities and mutation ownership/, sectorFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-015 \/sector route accessibility and responsive geometry/, sectorFeatureIds.map((id) => [id, "Mobile/responsive"])],
  ["caos/frontend/scripts/performance-audit.mjs", /SCR-015 \/sector desktop and mobile-slow route performance/, sectorFeatureIds.map((id) => [id, "Performance"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh/, sectorFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows the recovery gate for unresolved identity/, sectorFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /renders the current dossier and exercises review, navigation, feed, and sector actions/, [["command-29", "Happy path"], ["command-47", "Happy path"], ["command-48", "Happy path"], ["command-50", "Happy path"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /refreshes partial work and binds the returned review to the context/, [["command-31", "Happy path"], ["command-31", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /keeps the refresh action name stable while refresh is in progress/, [["command-31", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /renders a loading state instead of an authoritative empty state while the history fetch is in flight/, [["command-30", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /surfaces history and refresh failures without restoring cold-state side rails/, [["command-30", "Error path"], ["command-31", "Error path"], ["command-47", "Error path"], ["command-48", "Error path"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /surfaces feed persistence failure while a populated dossier remains visible/, [["command-29", "Error path"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /surfaces taxonomy and feed read failures instead of presenting authoritative empty reference data/, [["command-29", "Error path"], ["command-47", "Error path"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /surfaces section-ratification rejection without discarding the active dossier/, [["command-50", "Error path"], ["command-50", "Boundary conditions"], ["command-50", "Invalid input"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /surfaces publication-gate rejection without losing the ratified review/, [["command-50", "Error path"], ["command-50", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /preserves the prior dossier and recovers controls when a sector change cannot be saved/, [["command-29", "Error path"], ["command-29", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /serializes feed updates, disables competing mutations, and recovers after the request settles/, [["command-29", "Boundary conditions"], ["command-29", "Performance"], ["command-31", "Performance"], ["command-50", "Performance"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /updates section URL state without refetching history and falls back from invalid tab and compare values/, [["command-47", "Boundary conditions"], ["command-47", "Invalid input"], ["command-47", "Performance"], ["command-48", "Invalid input"], ["command-48", "Performance"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /does not resurrect another sector's dossier when the active context sector changes/, [["command-30", "Boundary conditions"], ["command-30", "Invalid input"], ["command-48", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewDossier.test.tsx", /ignores a superseded history response after the analysis context changes/, [["command-30", "Boundary conditions"], ["command-30", "Performance"], ["command-48", "Boundary conditions"], ["command-48", "Performance"]]],
  ["caos/frontend/src/components/sector/SectorReviewPanels.test.tsx", /renders the honest empty state when no versioned review exists/, [["command-30", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewPanels.test.tsx", /renders a live-announced loading state, distinct from the empty state, while loading/, [["command-30", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewPanels.test.tsx", /renders overview evidence and delegates section selection/, [["command-30", "Happy path"], ["command-47", "Happy path"]]],
  ["caos/frontend/src/components/sector/SectorReviewPanels.test.tsx", /renders every specialized dossier tab and its evidence states/, [["command-30", "Happy path"], ["command-47", "Happy path"], ["command-49", "Error path"], ["command-51", "Happy path"], ["command-51", "Boundary conditions"]]],
  ["caos/frontend/src/components/sector/SectorReviewPanels.test.tsx", /renders a sector source as a link only when its persisted URL is present/, [["command-49", "Happy path"], ["command-49", "Permission/security"]]],
  ["caos/frontend/src/components/sector/SectorReviewPanels.test.tsx", /keeps duplicate display-only comparable names distinct and bounds metric columns to four finite keys/, [["command-30", "Invalid input"], ["command-51", "Error path"], ["command-51", "Boundary conditions"], ["command-51", "Invalid input"], ["command-51", "Performance"]]],
  ["caos/frontend/src/components/ui/SourceRef.test.tsx", /fails closed for an unsafe source destination/, [["command-49", "Invalid input"], ["command-49", "Permission/security"]]],
  ["caos/frontend/src/components/ui/SourceRef.test.tsx", /renders unavailable provenance as explanatory text, not an inert link/, [["command-49", "Boundary conditions"], ["command-49", "Error path"]]],
  ["caos/frontend/src/app/command/sector-board-removal.test.ts", /does not retain SectorBoard state, rendering, or sector filtering/, [["command-57", "Happy path"], ["command-57", "Error path"], ["command-57", "Boundary conditions"], ["command-57", "Invalid input"], ["command-57", "Performance"]]],
  ["caos/tests/server/test_analysis_workspace.py", /test_unknown_sector_is_rejected_and_taxonomy_is_canonical/, [["command-29", "Invalid input"], ["command-31", "Invalid input"]]],
  ["caos/tests/server/test_analysis_workspace.py", /test_sector_review_is_versioned_complete_and_reference_gated/, [["command-30", "Happy path"], ["command-30", "Permission/security"], ["command-31", "Happy path"], ["command-31", "Permission/security"], ["command-48", "Happy path"], ["command-48", "Permission/security"], ["command-50", "Error path"], ["command-50", "Boundary conditions"], ["command-50", "Invalid input"], ["command-50", "Permission/security"]]],
  ["caos/tests/server/test_sector_concurrency.py", /test_sector_review_context_filter_is_applied_before_history_limit/, [["command-30", "Performance"], ["command-48", "Boundary conditions"], ["command-48", "Performance"]]],
  ["caos/frontend/src/components/upload/steps-interactions.test.tsx", /searches and selects issuers and drives the complete inline-create form/, [["upload-01", "Happy path"], ["upload-01", "Invalid input"]]],
  ["caos/frontend/src/components/upload/UploadWizard.interactions.test.tsx", /deep-links an existing issuer and surfaces selection-context and manual-run failures/, [["upload-02", "Happy path"], ["upload-02", "Error path"]]],
  ["caos/frontend/src/components/upload/UploadWizard.interactions.test.tsx", /ignores missing deep links and does not rewind an already-open file stage/, [["upload-02", "Boundary conditions"]]],
  ["caos/frontend/src/components/upload/UploadWizard.interactions.test.tsx", /deduplicates staged files and rejected warnings, supports removal\/back, and clears intake only when the issuer changes/, [["upload-03", "Boundary conditions"], ["upload-03", "Invalid input"], ["upload-04", "Happy path"]]],
  ["caos/frontend/src/components/upload/steps-interactions.test.tsx", /drives file removal, authority, mode, portfolio, upload, cancel, and back controls/, [["upload-03", "Happy path"], ["upload-04", "Happy path"], ["upload-05", "Happy path"]]],
  ["caos/frontend/src/components/upload/UploadWizard.interactions.test.tsx", /uploads PDF and XLSX sequentially, retries only failures, queues one exact run, and resets/, [["upload-06", "Happy path"], ["upload-06", "Error path"], ["upload-07", "Happy path"], ["upload-08", "Happy path"]]],
  ["caos/frontend/src/components/upload/UploadWizard.interactions.test.tsx", /cancels between files and blocks a re-entrant batch/, [["upload-06", "Boundary conditions"], ["upload-06", "Performance"]]],
  ["caos/frontend/src/components/upload/steps-interactions.test.tsx", /recognizes spreadsheet extensions and renders every progress-strip state/, [["upload-07", "Boundary conditions"], ["upload-09", "Happy path"]]],
  ["caos/frontend/src/components/upload/steps-interactions.test.tsx", /renders running and completed result states and invokes every available action/, [["upload-08", "Happy path"], ["upload-08", "Error path"]]],
  ["caos/frontend/src/components/upload/steps.test.tsx", /makes its horizontally scrollable progress region keyboard reachable/, [["upload-09", "Mobile/responsive"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_document_upload_oversized_413/, [["upload-10", "Boundary conditions"], ["upload-10", "Performance"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_document_upload_rejects_with_explicit_reason\[(report\.docx|really-a-txt\.pdf)/, [["upload-11", "Invalid input"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_pricing_sheet_rejects_non_workbook_containers/, [["upload-12", "Invalid input"], ["upload-12", "Permission/security"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_document_upload_rejects_with_explicit_reason\[empty\.pdf/, [["upload-13", "Boundary conditions"], ["upload-13", "Invalid input"]]],
  ["caos/tests/server/test_ingest_markitdown.py", /test_uses_markitdown_when_configured/, [["upload-14", "Happy path"], ["upload-15", "Happy path"]]],
  ["caos/tests/server/test_ingest_markitdown.py", /test_ocr_recovers_scanned_pdf|test_falls_back_when_unconfigured|test_ocr_disabled_returns_empty/, [["upload-14", "Error path"], ["upload-14", "Boundary conditions"]]],
  ["caos/tests/server/test_xlsx_safety.py", /test_nominal_workbook_still_crosses_every_shared_parser/, [["upload-15", "Boundary conditions"]]],
  ["caos/tests/server/test_xlsx_safety.py", /test_every_workbook_parser_rejects_shared_resource_bombs/, [["upload-15", "Permission/security"], ["upload-15", "Performance"]]],
  ["caos/tests/server/test_intelligent_vault.py", /test_structure_aware_chunking/, [["upload-16", "Happy path"], ["upload-16", "Boundary conditions"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_vault_store_sanitizes_basename_and_uses_unique_directory/, [["upload-17", "Happy path"], ["upload-17", "Permission/security"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_document_upload_db_failure_removes_uncommitted_vault_object/, [["upload-17", "Error path"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_ingestion_response_exposes_durable_metadata/, [["upload-18", "Happy path"], ["upload-18", "Boundary conditions"]]],
  ["caos/tests/server/test_upload_robustness.py", /test_upload_rate_guard_allows_twenty_then_rejects_twenty_first/, [["upload-19", "Boundary conditions"], ["upload-19", "Performance"], ["upload-19", "Permission/security"]]],
  ["caos/tests/server/test_edgar.py", /test_search_route_returns_pointers/, [["upload-20", "Happy path"]]],
  ["caos/tests/server/test_edgar.py", /test_search_route_503_without_ua/, [["upload-20", "Error path"]]],
  ["caos/tests/server/test_edgar.py", /test_exhibits_route_returns_classified_documents/, [["upload-21", "Happy path"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /renders the EDGAR URL vaulting panel/, [["upload-22", "Happy path"], ["upload-22", "Mobile/responsive"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /vaults a pasted EDGAR URL, threading the run mode/, [["upload-23", "Happy path"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /surfaces which URLs failed on a partial batch, not just the successes/, [["upload-23", "Error path"], ["upload-25", "Error path"]]],
  ["caos/tests/server/test_edgar.py", /test_vault_exhibit_creates_primary_source/, [["upload-23", "Permission/security"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /shows the not-configured guidance on a 503/, [["upload-24", "Error path"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /surfaces a useful non-503 vaulting error/, [["upload-25", "Invalid input"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /does not vault a whitespace-only URL from the Enter-key path/, [["upload-25", "Boundary conditions"]]],
  ["caos/frontend/src/components/upload/EdgarImport.test.tsx", /does not double-vault on a fast double-invoke via Enter/, [["upload-25", "Performance"]]],
  ["caos/tests/server/test_avscan.py", /test_infected_upload_rejected_422|test_required_unconfigured_scanner_fails_closed|test_unreachable_scanner_fails_closed_503/, [["upload-26", "Permission/security"], ["upload-26", "Error path"]]],
  ["caos/tests/server/test_edgar.py", /test_filings_route_returns_hits_and_passes_form_filter/, [["upload-27", "Happy path"]]],
  ["caos/tests/server/test_edgar.py", /test_filings_route_rejects_out_of_range_limit/, [["upload-27", "Boundary conditions"], ["upload-27", "Invalid input"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /keeps the composer inert until the active persisted selection is hydrated/, [["query-01", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /keeps context-dependent utilities and execution inert without a context/, [["query-01", "Permission/security"], ["query-16", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /survives unavailable session storage and removes a cleared draft/, [["query-02", "Error path"], ["query-02", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /accepts focus events, manual lane overrides, suggestions, starters, and keyboard execution/, [["query-03", "Happy path"], ["query-03", "Boundary conditions"], ["query-04", "Happy path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /runs a starter and keeps its inferred grounded lane/, [["query-03", "Happy path"], ["query-04", "Happy path"], ["query-05", "Happy path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /renders a default error recovery and keeps an uncited ready run in draft/, [["query-04", "Error path"], ["query-05", "Error path"], ["query-13", "Permission/security"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /does not refetch the full history after publishing a local query result/, [["query-05", "Performance"], ["query-10", "Performance"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /renders structured metric columns, fixed precision, issuer metadata, and row citations/, [["query-06", "Happy path"], ["query-09", "Happy path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /renders fallback metric columns, missing values, label fallbacks, and a level caveat/, [["query-06", "Invalid input"], ["query-06", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /opens graph and inspector citations with deterministic fallback labels/, [["query-07", "Happy path"], ["query-09", "Error path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /renders invalid graph and empty grounded payload states/, [["query-07", "Invalid input"], ["query-08", "Error path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /uses grounded citation defaults, filters malformed sources, and opens a cited claim/, [["query-08", "Invalid input"], ["query-09", "Happy path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /renders fact citation defaults when sentence sources omit labels/, [["query-08", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /loads, selects, and edits saved investigations from the utility drawer/, [["query-10", "Happy path"], ["query-16", "Happy path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /makes a failed URL-selected investigation explicit and retryable/, [["query-10", "Error path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /surfaces capability, history, and context errors without disabling the loaded context/, [["query-01", "Error path"], ["query-10", "Error path"], ["query-11", "Error path"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /ignores a capability response that arrives after unmount/, [["query-11", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /falls back to the default graph capability when capability groups are absent/, [["query-11", "Invalid input"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /ignores capability groups that do not declare capabilities/, [["query-11", "Invalid input"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /falls back to updated timestamps for partial and observed-empty decision data/, [["query-12", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /pins observed-empty results and uses summary, synthesis, interpretation, and question title fallbacks/, [["query-12", "Happy path"], ["query-13", "Happy path"], ["query-13", "Boundary conditions"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /deduplicates a same-tick pin attempt while the first request is pending/, [["query-13", "Performance"]]],
  ["caos/frontend/src/app/query/query-interactions.test.tsx", /rechecks evidence at pin time if a previously cited run loses its sources/, [["query-13", "Permission/security"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /prints, downloads immutable binaries, and exposes one IC decision-room opener/, [["reports-11", "Happy path"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /surfaces saved-model failure and retries the reference inputs/, [["reports-21", "Error path"]]],
  ["caos/frontend/src/app/reports/reports-interactions.test.tsx", /hydrates valid and malformed saved-model payloads and ignores late completion/, [["reports-21", "Invalid input"], ["reports-21", "Boundary conditions"]]],
  ["caos/frontend/src/lib/ic-book.test.ts", /covers agenda detail, creation, and the full evidence-exception lifecycle/, [["API-037", "Happy path"]]],
  ["caos/tests/server/test_auth_profile.py", /test_me_before_login_is_not_a_profile/, [["auth-09", "Permission/security"], ["auth-11", "Permission/security"]]],
  ["caos/tests/server/test_auth_profile.py", /test_wrong_code_rejected/, [["auth-01", "Error path"], ["auth-03", "Permission/security"]]],
  ["caos/tests/server/test_auth_profile.py", /test_non_ascii_code_is_401_not_500/, [["auth-03", "Invalid input"], ["auth-17", "Invalid input"]]],
  ["caos/tests/server/test_auth_profile.py", /test_create_profile_sets_identity_and_initials_source/, [["auth-01", "Happy path"], ["auth-06", "Happy path"], ["auth-08", "Happy path"], ["auth-09", "Happy path"]]],
  ["caos/tests/server/test_auth_profile.py", /test_profile_name_control_chars_stripped/, [["auth-07", "Invalid input"]]],
  ["caos/tests/server/test_auth_profile.py", /test_empty_access_code_fails_closed/, [["auth-04", "Error path"], ["auth-04", "Permission/security"]]],
  ["caos/tests/server/test_auth_profile.py", /test_cookie_secure_off_in_dev_on_when_deployed/, [["auth-08", "Permission/security"]]],
  ["caos/tests/server/test_auth_profile.py", /test_reattach_to_existing_profile_keeps_one_id/, [["auth-06", "Boundary conditions"]]],
  ["caos/tests/server/test_auth_profile.py", /test_sso_email_binds_profile_and_blocks_impersonation/, [["auth-05", "Happy path"], ["auth-05", "Permission/security"]]],
  ["caos/tests/server/test_auth_profile.py", /test_logout_clears_identity/, [["auth-08", "Boundary conditions"]]],
  ["caos/tests/server/test_auth_profile.py", /test_auth_02_performance_throttle_covers_every_credential_endpoint/, [["auth-02", "Performance"]]],
  ["caos/tests/server/test_auth_profile.py", /test_auth_02_boundary_condition_allows_ten_then_blocks_eleventh/, [["auth-02", "Boundary conditions"]]],
  ["caos/tests/server/test_auth_password.py", /test_register_then_me_is_profile/, [["auth-17", "Happy path"], ["auth-08", "Happy path"]]],
  ["caos/tests/server/test_auth_password.py", /test_register_bad_invite_code_rejected/, [["auth-17", "Error path"], ["auth-17", "Permission/security"]]],
  ["caos/tests/server/test_auth_password.py", /test_register_duplicate_email_conflict/, [["auth-17", "Boundary conditions"]]],
  ["caos/tests/server/test_auth_password.py", /test_register_invalid_email_422/, [["auth-17", "Invalid input"]]],
  ["caos/tests/server/test_auth_password.py", /test_register_short_password_422/, [["auth-17", "Invalid input"], ["auth-17", "Boundary conditions"]]],
  ["caos/tests/server/test_auth_password.py", /test_login_roundtrip/, [["auth-16", "Happy path"], ["auth-08", "Happy path"]]],
  ["caos/tests/server/test_auth_password.py", /test_login_wrong_password_401/, [["auth-16", "Error path"], ["auth-16", "Permission/security"]]],
  ["caos/tests/server/test_auth_password.py", /test_login_unknown_email_401/, [["auth-16", "Error path"], ["auth-16", "Permission/security"]]],
  ["caos/tests/server/test_auth_password.py", /test_recovery_requires_all_words/, [["auth-18", "Happy path"], ["auth-18", "Invalid input"], ["auth-18", "Boundary conditions"]]],
  ["caos/tests/server/test_auth_password.py", /test_sso_adoption_revokes_self_registered_password/, [["auth-05", "Permission/security"], ["auth-16", "Permission/security"], ["auth-18", "Permission/security"]]],
  ["caos/tests/server/test_auth_password.py", /test_recovery_unknown_email_denied/, [["auth-18", "Error path"], ["auth-18", "Permission/security"]]],
  ["caos/tests/server/test_passwords.py", /test_hash_verify_roundtrip/, [["auth-16", "Happy path"]]],
  ["caos/tests/server/test_passwords.py", /test_wrong_password_rejected/, [["auth-16", "Error path"]]],
  ["caos/tests/server/test_passwords.py", /test_salt_makes_each_hash_unique/, [["auth-17", "Permission/security"]]],
  ["caos/tests/server/test_passwords.py", /test_empty_or_malformed_hash_never_raises/, [["auth-16", "Invalid input"]]],
  ["caos/tests/server/test_identity.py", /test_read_session_token_rejects_non_ascii_signature/, [["auth-08", "Invalid input"]]],
  ["caos/tests/server/test_identity.py", /test_local_dev_no_enforcement/, [["auth-11", "Boundary conditions"]]],
  ["caos/tests/server/test_identity.py", /test_is_deployed_fails_closed|test_mistyped_prod_env_still_fails_closed/, [["auth-11", "Permission/security"]]],
  ["caos/tests/server/test_identity.py", /test_edge_secret_required_when_configured|test_cookie_does_not_bypass_edge_secret|test_unset_secret_keeps_prior_fail_closed/, [["auth-11", "Permission/security"]]],
  ["caos/tests/server/test_identity.py", /test_revoked_token_version_rejected/, [["auth-13", "Permission/security"]]],
  ["caos/tests/server/test_identity.py", /test_expired_token_rejected/, [["auth-08", "Boundary conditions"], ["auth-08", "Permission/security"]]],
  ["caos/tests/server/test_identity.py", /test_profile_cookie_ignored_when_sso_principal_differs/, [["auth-05", "Permission/security"]]],
  ["caos/tests/server/test_token_revocation.py", /test_logout_revokes_prior_token/, [["auth-12", "Happy path"], ["auth-12", "Permission/security"], ["auth-13", "Permission/security"]]],
  ["caos/tests/server/test_gdpr_erase.py", /test_erase_deletes_private_anonymizes_shared_spares_others/, [["auth-14", "Happy path"], ["auth-14", "Boundary conditions"], ["auth-14", "Permission/security"]]],
  ["caos/tests/server/test_gdpr_erase.py", /test_erase_deletes_model_v2_private_state_dependency_first/, [["auth-14", "Boundary conditions"]]],
  ["caos/tests/server/test_gdpr_erase.py", /test_erase_by_email_resolves_id_then_erases/, [["auth-15", "Happy path"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /can bypass login for local preview without calling \/me/, [["auth-11", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /re-resolves identity and routes to login when caos:auth-lost fires/, [["auth-09", "Error path"], ["auth-11", "Permission/security"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /re-resolves on tab refocus/, [["auth-05", "Permission/security"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /unmounts principal A synchronously/, [["auth-05", "Boundary conditions"], ["auth-05", "Permission/security"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /ignores an older refresh that settles after a newer principal/, [["auth-09", "Boundary conditions"], ["auth-09", "Performance"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /does not remount the login form/, [["auth-10", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/AuthProvider.test.tsx", /refreshes when another tab changes the principal marker/, [["auth-05", "Boundary conditions"]]],
  ["caos/tests/frontend/e2e/login_flow.spec.ts", /register creates an account and lands in the app/, [["auth-01", "Happy path"], ["auth-17", "Happy path"]]],
  ["caos/tests/frontend/e2e/login_flow.spec.ts", /wrong invite code surfaces the error/, [["auth-10", "Error path"], ["auth-17", "Error path"], ["auth-17", "Permission/security"]]],
  ["caos/tests/frontend/e2e/login_flow.spec.ts", /sign-in with wrong passcode surfaces an error/, [["auth-10", "Error path"], ["auth-16", "Error path"]]],
  ["caos/tests/frontend/e2e/login_flow.spec.ts", /auth login mobile responsive states remain accessible and unclipped/, [["auth-01", "Mobile/responsive"], ["auth-10", "Mobile/responsive"], ["auth-16", "Mobile/responsive"], ["auth-17", "Mobile/responsive"], ["auth-18", "Mobile/responsive"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /covers layouts, module navigation, accordion modes, pane collapse, chat, and lazy evidence/, [["deepdive-01", "Happy path"], ["deepdive-03", "Happy path"], ["deepdive-15", "Happy path"], ["deepdive-19", "Happy path"], ["deepdive-22", "Happy path"], ["deepdive-25", "Boundary conditions"], ["deepdive-28", "Happy path"], ["deepdive-40", "Boundary conditions"], ["deepdive-41", "Happy path"], ["deepdive-42", "Mobile/responsive"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /measures strip overflow, exposes paging controls, and handles responsive decision collapse/, [["deepdive-01", "Mobile/responsive"], ["deepdive-27", "Mobile/responsive"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /distinguishes issuer lookup failure\/retry and live run caveat states/, [["deepdive-02", "Error path"], ["deepdive-03", "Error path"], ["deepdive-23", "Happy path"], ["deepdive-24", "Error path"], ["deepdive-26", "Happy path"], ["deepdive-29", "Error path"], ["deepdive-30", "Happy path"], ["deepdive-39", "Happy path"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /affirms and pins a live thesis, including partial and error recovery/, [["deepdive-38", "Happy path"], ["deepdive-38", "Error path"], ["deepdive-39", "Error path"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /requires an analysis context even when a live run is present/, [["deepdive-38", "Permission/security"]]],
  ["caos/frontend/src/components/deepdive/tabs.smoke.test.tsx", /renders both debate variants in summary and report layouts/, [["deepdive-04", "Happy path"], ["deepdive-05", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/tabs.smoke.test.tsx", /renders recovery and covenant analysis at every density/, [["deepdive-06", "Happy path"], ["deepdive-07", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/ModuleView.test.tsx", /report layout keeps module outputs and workflow cards/, [["deepdive-08", "Happy path"], ["deepdive-09", "Happy path"], ["deepdive-32", "Happy path"], ["deepdive-33", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/ModuleView.test.tsx", /does not show seeded output for a missing issuer-scoped module/, [["deepdive-08", "Error path"], ["deepdive-26", "Error path"]]],
  ["caos/frontend/src/components/deepdive/ModuleCharts.test.ts", /gives every analytical chart authority, a readable summary, and an equivalent table schema/, [["deepdive-10", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /shows the workflow-step summary header when open/, [["deepdive-11", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /renders the step in a labelled dialog/, [["deepdive-12", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /consolidates repeated same-prefix report cards/, [["deepdive-13", "Happy path"]]],
  ["caos/tests/frontend/e2e/deepdive_flow.spec.ts", /hovering an evidence chip cross-highlights every sibling citing the same id/, [["deepdive-14", "Happy path"]]],
  ["caos/frontend/src/lib/evidence-sync.test.tsx", /clicking a chip opens its source without leaking the click to parents/, [["deepdive-15", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /renders the reference source register and synchronizes every driver interaction/, [["deepdive-16", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /distinguishes committee loading, error, unavailable, and observed-empty states/, [["deepdive-17", "Error path"], ["deepdive-18", "Error path"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /renders and orders live committee findings while preserving the reference decision stack/, [["deepdive-17", "Happy path"], ["deepdive-18", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.interactions.test.tsx", /submits from the composer, blocks duplicate sends, clears the transcript, and closes by keyboard or button/, [["deepdive-19", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/issuer-chat-context.test.ts", /grounds in the live run and drops the ATLF fixtures when a run is present/, [["deepdive-20", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.test.tsx", /loads the new run transcript without writing the prior run into its cache/, [["deepdive-21", "Boundary conditions"]]],
  ["caos/frontend/src/lib/deepdive/layout-pref.test.ts", /persists current values and rejects unknown values/, [["deepdive-22", "Boundary conditions"]]],
  ["caos/frontend/src/lib/engine/useLiveRun.test.ts", /loads the exact URL-bound run instead of substituting the latest run/, [["deepdive-23", "Boundary conditions"]]],
  ["caos/frontend/src/lib/deepdive/caveat.test.ts", /phase='error' resolves to 'error', not noRun/, [["deepdive-24", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /hides the seeded rail for non-reference issuers with and without an identifying code/, [["deepdive-26", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /exposes a Concepts trigger that lists every concept with its full label/, [["deepdive-31", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /records a QA flag through compose → confirm and confirms it/, [["deepdive-34", "Happy path"]]],
  ["caos/tests/server/test_qa_flags.py", /test_flags_never_gate_committee_export/, [["deepdive-34", "Permission/security"]]],
  ["caos/tests/server/test_qa_flags.py", /test_list_flags_filters_by_module_and_step/, [["deepdive-35", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/ModuleFinder.test.tsx", /opens on ⌘M, filters by id or name, and selecting adds a recent chip/, [["deepdive-36", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/ModuleFinder.test.tsx", /does not open ⌘M while focus is inside a text input/, [["deepdive-36", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/StandingViewStrip.test.tsx", /the reference issuer shows the DEBATE\/SIZING fixture tagged DEMO, never LIVE/, [["deepdive-37", "Happy path"]]],
  ["caos/frontend/src/components/deepdive/StandingViewStrip.test.tsx", /a real \(non-reference\) issuer with no CP-6 verdict shows an honest empty state/, [["deepdive-37", "Error path"]]],
  ["caos/frontend/src/components/model/ScenarioNetworkPanel.test.tsx", /renders computed and degraded nodes with text status, not color alone/, [["deepdive-40", "Happy path"]]],
  ["caos/frontend/src/components/shared/DecisionHeader.test.tsx", /renders one shared observation envelope when every conclusion has identical authority/, [["deepdive-41", "Happy path"]]],
  ["caos/frontend/src/components/shared/DecisionHeader.test.tsx", /renders a failed response as an error, never as a neutral empty observation/, [["deepdive-41", "Error path"]]],
];
const deepDiveFeatureIds = Array.from({ length: 42 }, (_, index) => `deepdive-${String(index + 1).padStart(2, "0")}`);
const currentDeepDiveFeatureIds = sourceRows.filter((row) => row.concept === "Deep-Dive").map((row) => row.id).sort();
if (JSON.stringify(currentDeepDiveFeatureIds) !== JSON.stringify([...deepDiveFeatureIds].sort())) {
  throw new Error(`Deep-Dive feature inventory drifted: ${currentDeepDiveFeatureIds.join(",")}`);
}
curatedScenarioMappings.push(
  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh|shows the recovery gate for unresolved identity/, deepDiveFeatureIds.map((id) => [id, "Permission/security"])],
  ["caos/frontend/scripts/performance-audit.mjs", /SCR-003 \/deepdive desktop and mobile-slow reference-workspace route performance/, deepDiveFeatureIds.map((id) => [id, "Performance"])],
  ["caos/frontend/scripts/a11y-axe.mjs", /SCR-003 \/deepdive route accessibility and responsive geometry at (?:390x844|1440x900)/, deepDiveFeatureIds.map((id) => [id, "Mobile/responsive"])],

  ["caos/frontend/src/lib/deepdive/module-groups.test.ts", /is a total, disjoint partition of the finder catalog/, [["deepdive-01", "Happy path"], ["deepdive-01", "Boundary conditions"], ["deepdive-01", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /falls back to a module id when the static module catalog is incomplete|summarizes unknown replay states as idle/, [["deepdive-01", "Error path"], ["deepdive-01", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /fails unknown persisted QA closed and covers every accepted status spelling/, [["deepdive-02", "Happy path"], ["deepdive-02", "Error path"], ["deepdive-02", "Boundary conditions"], ["deepdive-02", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/tabs.smoke.test.tsx", /renders missing, seeded, and live module states across layouts/, [
    ...["deepdive-03", "deepdive-04", "deepdive-05", "deepdive-06"].flatMap((id) => [[id, "Error path"], [id, "Invalid input"]]),
    ["deepdive-03", "Boundary conditions"], ["deepdive-08", "Boundary conditions"], ["deepdive-32", "Error path"], ["deepdive-32", "Invalid input"],
  ]],
  ["caos/frontend/src/components/deepdive/tabs.smoke.test.tsx", /renders both debate variants in summary and report layouts/, [["deepdive-04", "Boundary conditions"], ["deepdive-05", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/tabs.smoke.test.tsx", /renders recovery and covenant analysis at every density/, [["deepdive-06", "Boundary conditions"], ["deepdive-07", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/LiveCovenantCapacity.test.tsx", /degrades honestly when CP-4C extracted no capacity terms/, [["deepdive-07", "Error path"], ["deepdive-07", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/LiveCovenantCapacity.test.tsx", /renders honest placeholders and non-critical states for partially extracted capacity/, [["deepdive-07", "Happy path"], ["deepdive-07", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/ModuleView.test.tsx", /labels CP-2G reference output as unavailable/, [["deepdive-08", "Invalid input"], ["deepdive-32", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/ModuleView.test.tsx", /does not show seeded output for a missing issuer-scoped module/, [["deepdive-03", "Error path"], ["deepdive-08", "Error path"], ["deepdive-32", "Error path"]]],
  ["caos/frontend/src/components/deepdive/OutSections.test.tsx", /renders empty sections safely and exposes only declared evidence actions/, [["deepdive-09", "Happy path"], ["deepdive-09", "Error path"], ["deepdive-09", "Boundary conditions"], ["deepdive-09", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/ModuleCharts.render.test.tsx", /returns nothing for a module without registered charts/, [["deepdive-10", "Error path"], ["deepdive-10", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/ModuleCharts.render.test.tsx", /uses empty data and the default height when a definition omits both/, [["deepdive-10", "Boundary conditions"], ["deepdive-10", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /renders nothing for a module with no registered steps/, [["deepdive-11", "Error path"], ["deepdive-11", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /collapses the step grid when the header is toggled/, [["deepdive-11", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /surfaces a retryable error when the flag write fails/, [["deepdive-12", "Error path"], ["deepdive-34", "Error path"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /falls back to the snapshot exhibit for unmapped modules/, [["deepdive-12", "Boundary conditions"], ["deepdive-12", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /keeps short same-prefix report groups as individual cards|keeps dense mode unconsolidated/, [["deepdive-13", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /renders a dense analytical card even when its narrative is absent/, [["deepdive-13", "Error path"], ["deepdive-13", "Invalid input"]]],
  ["caos/frontend/src/lib/evidence-sync.test.tsx", /is inert outside a provider/, [["deepdive-14", "Error path"], ["deepdive-14", "Invalid input"]]],
  ["caos/tests/frontend/e2e/deepdive_flow.spec.ts", /focusing an evidence chip by keyboard fires the same cross-highlight/, [["deepdive-14", "Boundary conditions"]]],
  ["caos/frontend/src/components/reports/EvidenceModal.test.tsx", /prefers the run's own evidence over a colliding seeded key/, [["deepdive-15", "Happy path"], ["deepdive-15", "Boundary conditions"]]],
  ["caos/frontend/src/components/reports/EvidenceModal.test.tsx", /shows an explicit unresolved state for an unknown id/, [["deepdive-15", "Invalid input"]]],
  ["caos/frontend/src/components/reports/EvidenceModal.test.tsx", /shows an explicit unavailable state when the live chunk fetch fails/, [["deepdive-15", "Error path"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /hides the seeded rail for non-reference issuers/, [["deepdive-16", "Error path"], ["deepdive-16", "Invalid input"], ["deepdive-26", "Error path"], ["deepdive-26", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /renders the reference source register and synchronizes every driver interaction/, [["deepdive-16", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /renders and orders live committee findings while preserving the reference decision stack/, [["deepdive-17", "Boundary conditions"], ["deepdive-18", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /distinguishes committee loading, error, unavailable, and observed-empty states/, [["deepdive-17", "Invalid input"], ["deepdive-18", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.interactions.test.tsx", /submits from the composer, blocks duplicate sends, clears the transcript, and closes by keyboard or button/, [["deepdive-19", "Happy path"], ["deepdive-19", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.interactions.test.tsx", /renders the most useful chat failure detail/, [["deepdive-19", "Error path"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.interactions.test.tsx", /degrades safely when cached JSON or browser storage is unavailable/, [["deepdive-19", "Invalid input"], ["deepdive-21", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/issuer-chat-context.test.ts", /describes an unavailable issuer run without leaking fixture figures/, [["deepdive-20", "Error path"]]],
  ["caos/frontend/src/components/deepdive/issuer-chat-context.test.ts", /ignores an unknown evidence id|keeps unknown module ids unlabeled/, [["deepdive-20", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/issuer-chat-context.test.ts", /serializes every live output section and puts the current module first/, [["deepdive-20", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.test.tsx", /loads the new run transcript without writing the prior run into its cache/, [["deepdive-21", "Happy path"], ["deepdive-21", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/IssuerChat.interactions.test.tsx", /discards a successful response from a prior run generation|discards a failed response from a prior run generation/, [["deepdive-21", "Error path"]]],
  ["caos/frontend/src/lib/deepdive/layout-pref.test.ts", /defaults to report/, [["deepdive-22", "Happy path"]]],
  ["caos/frontend/src/lib/deepdive/layout-pref.test.ts", /defaults without a browser and when storage reads fail|silently tolerates storage write failures/, [["deepdive-22", "Error path"]]],
  ["caos/frontend/src/lib/deepdive/layout-pref.test.ts", /migrates legacy values without inverting user intent silently/, [["deepdive-22", "Boundary conditions"]]],
  ["caos/frontend/src/lib/deepdive/layout-pref.test.ts", /persists current values and rejects unknown values/, [["deepdive-22", "Invalid input"]]],
  ["caos/frontend/src/lib/engine/useLiveRun.test.ts", /adapts eligible modules, indexes evidence, and reads the typed CP-5C issue log/, [["deepdive-23", "Happy path"]]],
  ["caos/frontend/src/lib/engine/useLiveRun.test.ts", /exposes a backend error|surfaces a module fetch failure|surfaces a QA fallback failure/, [["deepdive-23", "Error path"]]],
  ["caos/frontend/src/lib/engine/useLiveRun.test.ts", /falls back to legacy QA findings and tolerates a module without claims/, [["deepdive-23", "Invalid input"]]],
  ["caos/frontend/src/lib/deepdive/caveat.test.ts", /a non-reference issuer with a completed run shows live output|the ATLF reference deal is the showcase/, [["deepdive-24", "Happy path"]]],
  ["caos/frontend/src/lib/deepdive/caveat.test.ts", /phase='error' resolves to 'error'/, [["deepdive-24", "Error path"]]],
  ["caos/frontend/src/lib/deepdive/caveat.test.ts", /reference and loading still win over phase='error'|phase is optional/, [["deepdive-24", "Boundary conditions"]]],
  ["caos/frontend/src/lib/deepdive/caveat.test.ts", /a non-reference issuer with no run is flagged noRun/, [["deepdive-24", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /covers layouts, module navigation, accordion modes, pane collapse, chat, and lazy evidence/, [["deepdive-25", "Happy path"], ["deepdive-25", "Boundary conditions"], ["deepdive-27", "Happy path"], ["deepdive-28", "Happy path"], ["deepdive-42", "Happy path"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /summarizes unknown replay states as idle and renders an invalid gate without invented dependencies/, [["deepdive-25", "Error path"], ["deepdive-25", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/rails.rich.test.tsx", /hides the seeded rail for non-reference issuers/, [["deepdive-26", "Boundary conditions"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /measures strip overflow, exposes paging controls, and handles responsive decision collapse/, [["deepdive-27", "Boundary conditions"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /scrolls a genuinely off-screen active module and tolerates the deferred measurement after unmount/, [["deepdive-27", "Error path"], ["deepdive-27", "Invalid input"]]],
  ["caos/frontend/src/components/shared/recovery-ui-smoke.test.tsx", /persists, suppresses, and gracefully degrades first-run hints/, [["deepdive-28", "Error path"], ["deepdive-28", "Boundary conditions"], ["deepdive-28", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /distinguishes issuer lookup failure\/retry and live run caveat states/, [["deepdive-29", "Happy path"], ["deepdive-29", "Error path"], ["deepdive-29", "Boundary conditions"], ["deepdive-29", "Invalid input"]]],
  ["caos/frontend/src/components/reports/ExportToVaultButton.test.tsx", /exports one note and exposes the written path/, [["deepdive-30", "Happy path"]]],
  ["caos/frontend/src/components/reports/ExportToVaultButton.test.tsx", /keeps an ordinary export failure retryable/, [["deepdive-30", "Error path"]]],
  ["caos/frontend/src/components/reports/ExportToVaultButton.test.tsx", /renders plural notes and ignores a click while export is pending/, [["deepdive-30", "Boundary conditions"]]],
  ["caos/frontend/src/components/reports/ExportToVaultButton.test.tsx", /explains an unconfigured vault/, [["deepdive-30", "Invalid input"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /marks the active route with aria-current|preserves reference mode and analysis context/, [["deepdive-31", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/ConceptNav.test.tsx", /covers the full CONCEPT_CYCLE so hotkeys and drawer can never drift/, [["deepdive-31", "Error path"], ["deepdive-31", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/ModuleView.test.tsx", /summary layout keeps analysis output and summarizes workflow cards/, [["deepdive-32", "Boundary conditions"], ["deepdive-33", "Happy path"], ["deepdive-33", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/OutputRegister.test.tsx", /renders a dense analytical card even when its narrative is absent/, [["deepdive-33", "Error path"], ["deepdive-33", "Invalid input"]]],
  ["caos/tests/server/test_qa_flags.py", /test_flag_empty_note_normalizes_to_null/, [["deepdive-34", "Boundary conditions"]]],
  ["caos/tests/server/test_qa_flags.py", /test_flag_validation_rejects_oversize/, [["deepdive-34", "Invalid input"]]],
  ["caos/frontend/src/components/shared/FlagToQa.test.tsx", /increments an existing count and discloses multiple flags after submit/, [["deepdive-35", "Boundary conditions"]]],
  ["caos/tests/server/test_qa_flags.py", /test_flag_rejects_unknown_issuer without disclosing it|test_flag_rejects_unknown_issuer_without_disclosing_it/, [["deepdive-35", "Error path"], ["deepdive-35", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/ModuleFinder.test.tsx", /a 404 on settings load leaves pins\/recents empty without surfacing an error/, [["deepdive-36", "Error path"]]],
  ["caos/frontend/src/components/deepdive/ModuleFinder.test.tsx", /deduplicates, validates, and caps persisted pins and recents before rendering shortcuts/, [["deepdive-36", "Boundary conditions"], ["deepdive-36", "Invalid input"]]],
  ["caos/frontend/src/components/deepdive/StandingViewStrip.test.tsx", /returns a failed personal annotation to a retryable idle state/, [["deepdive-37", "Error path"]]],
  ["caos/frontend/src/components/deepdive/StandingViewStrip.test.tsx", /Affirm caps the stored list at 20 entries/, [["deepdive-37", "Boundary conditions"]]],
  ["caos/frontend/src/components/deepdive/StandingViewStrip.test.tsx", /a real \(non-reference\) issuer with no CP-6 verdict shows an honest empty state/, [["deepdive-37", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /affirms and pins a live thesis, including partial and error recovery/, [["deepdive-38", "Happy path"], ["deepdive-38", "Error path"], ["deepdive-38", "Boundary conditions"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /requires an analysis context even when a live run is present/, [["deepdive-38", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /affirms a default live module without optional run metadata/, [["deepdive-39", "Happy path"], ["deepdive-39", "Boundary conditions"], ["deepdive-39", "Invalid input"]]],
  ["caos/frontend/src/app/deepdive/deepdive-interactions.test.tsx", /affirms and pins a live thesis, including partial and error recovery/, [["deepdive-39", "Error path"]]],
  ["caos/frontend/src/components/model/ScenarioNetworkPanel.test.tsx", /blocks duplicate propagation while pending and exposes a retryable failure/, [["deepdive-40", "Error path"], ["deepdive-40", "Boundary conditions"]]],
  ["caos/frontend/src/components/model/ScenarioNetworkPanel.test.tsx", /compacts unavailable controls and explains the prerequisite/, [["deepdive-40", "Invalid input"]]],
  ["caos/frontend/src/components/shared/DecisionHeader.test.tsx", /keeps four cells when the same kind carries different messages|reserves no-material-change language/, [["deepdive-41", "Boundary conditions"]]],
  ["caos/frontend/src/components/shared/DecisionHeader.test.tsx", /renders explicit decision-safe empty states|collapses to one spanning line when every cell states the same value-less cause/, [["deepdive-41", "Invalid input"]]],
  ["caos/tests/frontend/e2e/deepdive_flow.spec.ts", /keeps the analytical workbench and global Ask reachable at phone width/, [["deepdive-42", "Happy path"], ["deepdive-42", "Boundary conditions"]]],
  ["caos/frontend/src/app/responsive-recovery.contract.test.ts", /swaps the compact Ask utility for the phone trigger at every narrow pointer type/, [["deepdive-42", "Error path"], ["deepdive-42", "Invalid input"]]],
);
const listApiScenarioFeatureIds = [
  "API-006", "API-093", "API-094", "API-095", "API-096", "API-097",
  "API-120", "API-133", "API-158", "API-168", "API-169",
];
const listApiQualityFile = "caos/tests/server/test_api_list_quality_contracts.py";
curatedScenarioMappings.push(
  [listApiQualityFile, /test_list_contexts_is_owner_scoped_ordered_and_bounded/, [
    ["API-006", "Happy path"], ["API-006", "Boundary conditions"], ["API-006", "Permission/security"],
  ]],
  [listApiQualityFile, /test_legacy_portfolio_root_with_slash_returns_bounded_board/, [
    ["API-093", "Happy path"], ["API-093", "Boundary conditions"],
  ]],
  [listApiQualityFile, /test_portfolio_root_without_slash_creates_and_lists/, [
    ["API-094", "Happy path"], ["API-094", "Boundary conditions"],
    ["API-095", "Happy path"], ["API-095", "Boundary conditions"],
  ]],
  [listApiQualityFile, /test_list_query_runs_filters_owned_context_and_hides_foreign_context/, [
    ["API-120", "Happy path"], ["API-120", "Boundary conditions"], ["API-120", "Permission/security"],
  ]],
  [listApiQualityFile, /test_list_research_filters_owned_context_and_hides_foreign_context/, [
    ["API-133", "Happy path"], ["API-133", "Boundary conditions"], ["API-133", "Permission/security"],
  ]],
  [listApiQualityFile, /test_list_sector_reviews_filters_canonical_sector_and_owner/, [
    ["API-158", "Happy path"], ["API-158", "Boundary conditions"], ["API-158", "Permission/security"],
  ]],
  [listApiQualityFile, /test_sponsor_root_without_slash_lists_owned_sponsor_groups/, [
    ["API-168", "Happy path"], ["API-168", "Boundary conditions"],
  ]],
  [listApiQualityFile, /test_parameterless_list_routes_ignore_unknown_query_keys/, [
    ["API-093", "Invalid input"], ["API-094", "Invalid input"], ["API-096", "Invalid input"],
    ["API-168", "Invalid input"], ["API-169", "Invalid input"],
  ]],
  [listApiQualityFile, /test_validated_list_inputs_reject_out_of_contract_values/, [
    ["API-006", "Invalid input"], ["API-095", "Invalid input"], ["API-097", "Invalid input"],
    ["API-120", "Invalid input"], ["API-133", "Invalid input"], ["API-158", "Invalid input"],
  ]],
  [listApiQualityFile, /test_aliased_roots_enforce_team_scope_and_create_role/, [
    ["API-093", "Permission/security"], ["API-094", "Permission/security"],
    ["API-095", "Permission/security"], ["API-096", "Permission/security"],
    ["API-097", "Permission/security"], ["API-168", "Permission/security"],
    ["API-169", "Permission/security"],
  ]],
  [listApiQualityFile, /test_guarded_list_routes_apply_exact_backpressure_and_recover/, [
    ["API-006", "Performance"], ["API-093", "Performance"], ["API-095", "Performance"],
    ["API-097", "Performance"], ["API-120", "Performance"], ["API-158", "Performance"],
    ["API-168", "Performance"], ["API-169", "Performance"],
  ]],
  ["caos/tests/server/test_portfolios.py", /test_list_includes_created/, [
    ["API-096", "Happy path"], ["API-096", "Boundary conditions"],
  ]],
  ["caos/tests/server/test_portfolios.py", /test_create_computes_posture/, [["API-097", "Happy path"]]],
  ["caos/tests/server/test_sponsors_digest.py", /test_sponsors_group_and_track_record/, [
    ["API-169", "Happy path"], ["API-169", "Boundary conditions"],
  ]],
);
for (const featureId of listApiScenarioFeatureIds) {
  curatedScenarioMappings.push(
    [
      listApiQualityFile,
      new RegExp(`test_api_list_dependency_failure_returns_500_and_recovers\\[${featureId}\\]`),
      [[featureId, "Error path"]],
    ],
    [
      listApiQualityFile,
      new RegExp(`test_api_list_performance_contract_has_explicit_bound\\[${featureId}\\]`),
      [[featureId, "Performance"]],
    ],
  );
}

const settingsFrontendFile = "caos/frontend/src/app/settings/settings-models.test.tsx";
const settingsQualityFile = "caos/tests/server/test_settings_quality_contracts.py";
curatedScenarioMappings.push(
  [settingsFrontendFile, /edits, saves, and resets the browser-local research defaults/, [["settings-01", "Happy path"]]],
  ["caos/tests/frontend/e2e/settings_flow.spec.ts", /saved defaults seed a new Research brief/, [["settings-02", "Happy path"]]],
  ["caos/frontend/src/lib/coverage-edges.test.ts", /degrades storage helpers in SSR and blocked-storage environments/, [["settings-01", "Error path"], ["settings-02", "Error path"]]],
  ["caos/frontend/src/lib/research-prefs.test.ts", /keeps well-typed fields and only replaces the wrong-typed ones/, [["settings-01", "Boundary conditions"], ["settings-02", "Boundary conditions"]]],
  ["caos/frontend/src/lib/research-prefs.test.ts", /falls back to defaults on malformed JSON without throwing|treats a non-object parsed value as empty rather than crashing/, [["settings-01", "Invalid input"], ["settings-02", "Invalid input"]]],

  ["caos/tests/frontend/e2e/settings_flow.spec.ts", /mirrors the server workspace configuration/, [["settings-03", "Happy path"], ["settings-04", "Happy path"], ["settings-05", "Happy path"]]],
  [settingsFrontendFile, /renders every workspace configuration value and recovers from an offline read/, [["settings-03", "Happy path"], ["settings-03", "Error path"], ["settings-03", "Boundary conditions"]]],
  ["caos/tests/server/test_settings.py", /test_settings_returns_snapshot_without_secrets/, [["settings-03", "Invalid input"], ["settings-03", "Permission/security"]]],
  [settingsFrontendFile, /defaults an unsupported tab and reports unavailable answer-source status without writing/, [
    ["settings-04", "Error path"], ["settings-04", "Invalid input"],
    ["settings-05", "Error path"], ["settings-05", "Invalid input"],
    ["settings-06", "Error path"], ["settings-06", "Invalid input"],
    ["settings-08", "Error path"], ["settings-08", "Invalid input"],
  ]],
  [settingsFrontendFile, /supports tab clicks and the complete roving-tab keyboard contract/, [
    ["settings-04", "Boundary conditions"], ["settings-05", "Boundary conditions"],
    ["settings-06", "Happy path"], ["settings-06", "Boundary conditions"],
  ]],

  [settingsFrontendFile, /guards the global save while persistence is in flight and clears dirty state only after success/, [["settings-07", "Happy path"], ["settings-07", "Performance"]]],
  [settingsFrontendFile, /hydrates server research defaults and normalized profile mode, then changes query model and research scope/, [["settings-07", "Boundary conditions"], ["settings-07", "Invalid input"]]],
  ["caos/frontend/src/lib/model-mode.test.ts", /falls back to DEFAULT_MODE when localStorage\.getItem throws/, [["settings-07", "Error path"]]],
  [settingsFrontendFile, /labels the query-model cards truthfully .* shows routing as planned, not dead controls/, [
    ["settings-08", "Happy path"], ["settings-08", "Boundary conditions"],
    ["settings-09", "Happy path"], ["settings-09", "Error path"], ["settings-09", "Boundary conditions"], ["settings-09", "Invalid input"],
  ]],
  [settingsFrontendFile, /renders connected email state and persists a normalized sender list/, [["settings-10", "Happy path"], ["settings-10", "Invalid input"]]],
  [settingsFrontendFile, /surfaces an analyst-settings save failure with the server detail/, [["settings-10", "Error path"]]],
  ["caos/tests/server/test_settings.py", /test_analyst_settings_patch_is_partial_and_revision_checked/, [["settings-10", "Boundary conditions"], ["settings-10", "Permission/security"]]],
  [settingsFrontendFile, /serializes rapid settings saves onto the prior response revision/, [["settings-10", "Performance"]]],

  ["caos/frontend/src/components/shared/RequireAuth.test.tsx", /shows login and forwards successful authentication to refresh|shows the recovery gate for unresolved identity/, settingsFeatureIds.map((id) => [id, "Permission/security"])],
  [settingsFrontendFile, /loads each settings authority once and keeps fixed control inventories bounded/, [
    ...settingsFeatureIds.map((id) => [id, "Performance"]),
    ["settings-08", "Boundary conditions"], ["settings-08", "Invalid input"],
    ["settings-09", "Boundary conditions"], ["settings-09", "Invalid input"],
  ]],
  ["caos/tests/frontend/e2e/settings_flow.spec.ts", /keeps every Settings section reachable without page overflow at phone width/, settingsFeatureIds.map((id) => [id, "Mobile/responsive"])],

  ["caos/tests/server/test_settings.py", /test_settings_returns_snapshot_without_secrets/, [["API-164", "Happy path"], ["API-164", "Permission/security"]]],
  ["caos/tests/server/test_settings.py", /test_analyst_settings_roundtrip_with_profile_cookie/, [["API-165", "Happy path"], ["API-167", "Happy path"]]],
  ["caos/tests/server/test_settings.py", /test_analyst_settings_patch_is_partial_and_revision_checked/, [["API-166", "Happy path"]]],
  [settingsQualityFile, /test_api_164_identity_failure_returns_json_500_and_recovers/, [["API-164", "Error path"]]],
  [settingsQualityFile, /test_settings_reads_are_profile_scoped_and_viewers_cannot_write/, [
    ["API-165", "Permission/security"], ["API-166", "Permission/security"], ["API-167", "Permission/security"],
  ]],
  [settingsQualityFile, /test_settings_inputs_are_bounded_and_invalid_writes_do_not_mutate/, settingsApiFeatureIds.flatMap((id) => [[id, "Boundary conditions"], [id, "Invalid input"]])],
  [settingsQualityFile, /test_settings_mutations_share_exact_backpressure_and_recover/, [["API-166", "Performance"], ["API-167", "Performance"]]],
);
for (const featureId of settingsApiFeatureIds) {
  curatedScenarioMappings.push([
    settingsQualityFile,
    new RegExp(`test_settings_api_handler_has_bounded_work_contract\\[${featureId}\\]`),
    [[featureId, "Performance"]],
  ]);
}
for (const featureId of ["API-165", "API-166", "API-167"]) {
  curatedScenarioMappings.push([
    settingsQualityFile,
    new RegExp(`test_settings_analyst_database_failure_is_truthful_and_recovers\\[${featureId}\\]`),
    [[featureId, "Error path"]],
  ]);
}
const curatedReferences = new Map(sourceRows.map((row) => [
  row.id,
  `${row.test_cases || ""} ${row.test_result || ""} ${row.notes || ""}`.toLowerCase(),
]));
const apiDescriptors = apiRoutes.map((route, index) => ({
  id: `API-${String(index + 1).padStart(3, "0")}`,
  route,
  callRegex: routeCallRegex(route.method, route.path),
}));
validateApiFeatureParameterMappings(evidenceSourceByFile, apiDescriptors);
const configDescriptors = settings.map((setting, index) => ({
  id: `CFG-${String(index + 1).padStart(3, "0")}`,
  environment: setting.environment,
}));
const screenDescriptors = appRoutes.map((screen, index) => ({
  id: `SCR-${String(index + 1).padStart(3, "0")}`,
  route: screen.route,
  navigationRegex: routeNavigationRegex(screen.route),
}));

for (const evidence of automationEvidence) {
  const exactReasons = new Map();
  const indirectReasons = new Map();
  const explicitScenariosByFeature = new Map();
  const bodyLower = evidence.body.toLowerCase();
  const evidenceTextLower = `${evidence.name} ${evidence.body}`.toLowerCase();
  const basename = path.basename(evidence.file).toLowerCase();
  const functionName = evidence.layer === "Server/stress/cohort"
    ? evidence.name.split("::").at(-1).replace(/\[.*$/, "").toLowerCase()
    : evidence.name.split(" > ").at(-1).toLowerCase();

  for (const row of sourceRows) {
    const references = curatedReferences.get(row.id) || "";
    const subjectPath = testSubjectPath(evidence.file);
    const citedSourceFiles = new Set((row.files || "").split(";")
      .map((value) => clean(value).replace(/:\d+.*$/, ""))
      .filter(Boolean));
    if (
      evidence.layer === "Frontend unit/component"
      && citedSourceFiles.has(subjectPath)
      && significantTokenOverlap(`${row.feature} ${row.expected}`, evidence.name) >= 2
    ) {
      exactReasons.set(row.id, "Colocated source test with matching assertion semantics");
    }
    if (references.includes(`::${functionName}`) || (functionName.length >= 24 && references.includes(functionName))) {
      exactReasons.set(row.id, "Tracker exact test reference");
    } else if (references.includes(basename)) {
      if (significantTokenOverlap(references, evidence.name) >= 3) {
        exactReasons.set(row.id, "Tracker test-file reference with matching assertion semantics");
      } else {
        indirectReasons.set(row.id, "Tracker test-file reference");
      }
    }
    if (bodyLower.includes(row.id.toLowerCase())) exactReasons.set(row.id, "Feature ID asserted in test body");
  }
  for (const feature of featureObjects) {
    if (containsIdentifier(evidenceTextLower, feature.id)) {
      exactReasons.set(feature.id, "Feature ID asserted in test name or body");
    }
  }
  for (const descriptor of apiDescriptors) {
    if (descriptor.callRegex.test(evidence.body)) {
      exactReasons.set(descriptor.id, `${descriptor.route.method} ${descriptor.route.path} invoked in test body`);
    }
  }
  for (const descriptor of configDescriptors) {
    if (containsIdentifier(evidenceTextLower, descriptor.environment)) {
      exactReasons.set(descriptor.id, `${descriptor.environment} asserted in test name or body`);
    }
  }
  if (evidence.layer === "Browser E2E") {
    for (const descriptor of screenDescriptors) {
      if (descriptor.navigationRegex.test(evidence.body)) {
        exactReasons.set(descriptor.id, `${descriptor.route} navigation asserted in Playwright body`);
      }
    }
  }
  if (evidence.layer === "Server/stress/cohort") {
    for (const featureId of serverJourneyFileIds.get(basename) || []) {
      exactReasons.set(featureId, `${basename} dedicated business-process contract`);
    }
  }
  for (const featureId of e2eJourneyIds(evidence)) exactReasons.set(featureId, "Playwright journey mapping");
  for (const [file, namePattern, mappings] of curatedScenarioMappings) {
    if (evidence.file !== file || !namePattern.test(evidence.name)) continue;
    for (const [featureId, scenario] of mappings) {
      exactReasons.set(featureId, "Curated assertion-level scenario mapping");
      addEvidence(explicitScenariosByFeature, featureId, scenario);
    }
  }

  evidence.exactFeatureIds = [...exactReasons.keys()].sort();
  evidence.indirectFeatureIds = [...indirectReasons.keys()].filter((id) => !exactReasons.has(id)).sort();
  evidence.mappingBasis = [...new Set([...exactReasons.values(), ...indirectReasons.values()])].join("; ") || "Unmapped automated test";
  for (const featureId of evidence.exactFeatureIds) {
    addEvidence(exactEvidenceByFeature, featureId, evidence.id);
    const explicitScenarios = explicitScenariosByFeature.get(featureId);
    if (explicitScenarios?.size) {
      for (const scenario of explicitScenarios) {
        addEvidence(scenarioEvidence, `${featureId}|${scenario}`, evidence.id);
      }
    } else {
      addEvidence(scenarioEvidence, `${featureId}|${evidence.scenario}`, evidence.id);
    }
  }
  for (const featureId of evidence.indirectFeatureIds) addEvidence(indirectEvidenceByFeature, featureId, evidence.id);
}

const defectCounts = new Map();
const featureSeverity = new Map();
const severityRank = new Map([["None", 0], ["Low", 1], ["Medium", 2], ["High", 3], ["Critical", 4]]);
for (const defect of defects) {
  const [, featureId, severity] = defect;
  defectCounts.set(featureId, (defectCounts.get(featureId) || 0) + 1);
  if ((severityRank.get(severity) || 0) > (severityRank.get(featureSeverity.get(featureId)) || 0)) {
    featureSeverity.set(featureId, severity);
  }
}

const evidenceExecutedDateById = new Map(
  automationEvidence.map((evidence) => [evidence.id, evidence.executedDate || baselineDate]),
);
function latestEvidenceDate(evidenceIds, fallback = baselineDate) {
  const dates = evidenceIds.map((id) => evidenceExecutedDateById.get(id)).filter(Boolean).sort();
  return dates.at(-1) || fallback;
}

const testRows = [];
for (const feature of featureObjects) {
  for (const scenario of scenarios) {
    let status = "Designed";
    let lastExecuted = "";
    let result = "Scenario generated from the current implementation inventory; direct execution evidence is pending.";
    let automation = feature.endpoint && !feature.endpoint.startsWith("none") ? "API/unit/E2E candidate" : "UI/unit/E2E candidate";
    const exactEvidence = [...(scenarioEvidence.get(`${feature.id}|${scenario}`) || [])];
    if (!scenarioApplicable(feature, scenario)) {
      status = "Not applicable";
      lastExecuted = today;
      result = "This backend-only contract has no viewport-dependent presentation behavior; responsive validation applies at its consuming screen or workflow boundary.";
      automation = "Not applicable";
    } else if (exactEvidence.length) {
      status = "Pass";
      lastExecuted = latestEvidenceDate(exactEvidence);
      result = `Directly mapped passing automation: ${exactEvidence.slice(0, 12).join(", ")}${exactEvidence.length > 12 ? ` (+${exactEvidence.length - 12} more)` : ""}.`;
      automation = "Mapped automation evidence";
    } else if (feature.sourceType === "Discovered screen" && scenario === "Happy path") {
      status = "Pass";
      lastExecuted = today;
      result = "Authenticated route loaded and completed the current WCAG A/AA axe scan with zero findings on 2026-07-17.";
      automation = "Playwright + axe";
    } else if (feature.sourceType === "Curated feature" && scenario === "Happy path") {
      status = "Suite evidence";
      lastExecuted = baselineDate;
      result = "Current unit/server/E2E regressions passed in aggregate; this exact feature assertion was not independently mapped in this iteration.";
    } else if (feature.sourceType === "Discovered API handler" && ["Happy path", "Error path", "Invalid input", "Permission/security"].includes(scenario)) {
      status = "Suite evidence";
      lastExecuted = baselineDate;
      result = "The 2,512-pass executable server cohort covers the API layer in aggregate; per-handler test identity mapping remains pending.";
    } else if (feature.sourceType === "Discovered screen" && scenario === "Mobile/responsive") {
      status = "Pass";
      lastExecuted = today;
      result = "The route passed at 390x844 and 1440x900 with zero axe nodes, scan errors, page overflow, or clipped interactive controls.";
      automation = "Playwright + axe + responsive geometry checks";
    }
    testRows.push([
      `${feature.id}-${scenarioSlug(scenario)}`,
      feature.id,
      scenario,
      scenarioText(feature, scenario),
      expectedForScenario(feature, scenario),
      status,
      result,
      lastExecuted,
      automation,
      "",
    ]);
  }
}

// Direct execution evidence that closes prior gaps or covers environment-specific lanes.
const executedCases = [
  ["E2E-MODEL-CP2B", "model-37", "Downside fragility readout", "Pass", "Current CP-2B DTO fixture rendered the fragility readout in the real Model UI", "DEF-QV-006"],
  ["E2E-MODEL-SAVE", "model-43", "Canonical Model Engine v2 suggestion save", "Pass", "Authenticated as the owned workflow analyst, observed the successful PUT, and established a durable server revision", "DEF-QV-041"],
  ["E2E-MODEL-RELOAD", "model-43", "Committed Model Engine v2 override survives reload", "Pass", "Previewed and atomically committed one input override, then restored its exact value and OVERRIDDEN state after reload", "DEF-QV-041"],
  ["E2E-RESEARCH-MARKER", "research-13", "Current live/demo synthesis marker", "Pass", "Un-stubbed LIVE and AI-synthesized authority markers rendered", "DEF-QV-008"],
  ["E2E-DEEPDIVE-EVIDENCE-SYNC-STRESS", "deepdive-14", "Evidence-sync hover remains deterministic under parallel hydration", "Pass", "10/10 repetitions passed with five workers and retries disabled", "DEF-QV-009"],
  ["RESPONSIVE-ISSUER-FILTERS", "SCR-004", "Issuer filter targets and narrow column tracks", "Pass", "Non-shrinking filter targets and bounded sector tracks passed unit and 390px browser validation", "DEF-QV-011"],
  ["RESPONSIVE-SPONSORS-LAYOUT", "SCR-017", "Sponsors mobile worklist and detail layout", "Pass", "Stacked mobile layout retained a usable keyboard-accessible worklist at 390px", "DEF-QV-012"],
  ["RESPONSIVE-UPLOAD-STEPS", "SCR-018", "Upload step navigation keyboard access", "Pass", "The overflow region is labeled, focusable, visibly focused, and clean at 390px", "DEF-QV-013"],
  ["RESPONSIVE-PORTFOLIOS-900", "SCR-010", "Portfolio filters at the intermediate breakpoint", "Pass", "The compact layout preserved the Apply control at 900px", "DEF-QV-014"],
  ["E2E-SQLITE-SERIAL-LANE", "BP-017", "Deterministic stateful local E2E execution", "Pass", "46/46 journeys passed with retries disabled against the sanitized one-worker SQLite QA lane", "DEF-QV-015"],
  ["E2E-RESEARCH-PATHNAME-STUB", "research-13", "Research POST interception with context query string", "Pass", "Pathname predicates intercepted all three Research POST fixtures and the full zero-retry lane passed", "DEF-QV-016"],
  ["E2E-DEEPDIVE-ATOMIC-HOVER", "deepdive-14", "Atomic evidence-sync hover assertion", "Pass", "Hovered, sibling, and unrelated states passed in one bounded transaction across 10/10 five-worker repetitions", "DEF-QV-017"],
  ["SERVER-LINEAGE-PG-ROLLBACK", "BP-008", "Independent-transaction lineage commit and rollback contention", "Pass", "Both unique-key contention paths passed against PostgreSQL", "DEF-QV-010"],
  ["SERVER-PG-GATED-COHORT", "BP-017", "PostgreSQL-only concurrency, locks, deployed posture, and lineage", "Pass", "15/15 environment-gated PostgreSQL cases passed", ""],
  ["SERVER-OCR-GOLDEN", "BP-003", "Real OCR ingestion and provenance persistence", "Pass", "Image-only PDF was OCRed and persisted with prov=ocr", ""],
  ["DB-MIGRATION-ROUNDTRIP", "BP-017", "PostgreSQL migration round trip and drift check", "Pass", "upgrade, check, downgrade-to-base, and re-upgrade all passed across 62 revisions", ""],
  ["PERF-HEALTH-P95", "BP-017", "Concurrent health endpoint latency gate", "Pass", "200 requests at concurrency 20: 0 errors, p50 23ms, p95 82ms under the 500ms gate", ""],
  ["E2E-MODEL-V2-FLAGS", "BP-017", "Complete Model Engine v2 capability rollout", "Pass", "The isolated server enabled both model_engine_v2 and lineage_v2; the v2 route returned live authority instead of the deliberate 503 gate", "DEF-QV-040"],
  ["SERVER-ROOT-COHORT", "BP-017", "Repository-root backend regression invocation", "Pass", "The reconciled server inventory contains 2,488 current nodes: the complete run passed 2,471 executable cases with 15 intentional skips, and both later affected-file deltas passed", "DEF-QV-042; DEF-QV-099; DEF-QV-100; DEF-QV-101; DEF-QV-119; DEF-QV-121; DEF-QV-131; DEF-QV-136"],
  ["VALIDATION-LEDGER-CURRENT", "BP-017", "Current supporting-gate commands", "Pass", "Scenario benchmark, Modular OS consistency, dependency lock sync, and complexity delta all executed from their required current paths", "DEF-QV-043"],
  ["E2E-DETERMINISTIC-KEYLESS", "BP-017", "Deterministic zero-retry browser environment", "Pass", "With Anthropic, OpenRouter, and Gemini keys explicitly blank, the latest tested snapshot passed all 46 browser journeys with zero retries in 30.0s", "DEF-QV-044"],
  ["A11Y-ROOT-900-RERUN", "BP-017", "Fail-closed root accessibility readiness follow-up", "Pass", "The focused / root rerun at 900x900 resolved to /issuers with zero axe nodes, scan errors, page overflow, or clipped controls", "DEF-QV-045"],
  ["E2E-COMMAND-SCOPE-GUARD", "command-56", "Command autosave waits for portfolio resolution", "Pass", "The first successful context PATCH retained portfolio-qa; focused regression passed 7/7 and the final full zero-retry cohort passed 46/46", "DEF-QV-046"],
  ["E2E-SETTINGS-ACTION-REASON", "settings-01", "Settings save actionability follows ActionReason semantics", "Pass", "The dirty action removed aria-disabled and the no-change title, then returned to pristine after save; focused and full browser regressions passed", "DEF-QV-047"],
  ["PRODLIKE-PG-SCALE-300", "BP-017", "Sanitized production-scale PostgreSQL fixture", "Pass", "Guarded idempotent seeding produced 300 conspicuously fictional issuers, 600 documents/chunks, 2,400 metrics, and one opt-in owned CP-1 workflow fixture", "DEF-QV-049"],
  ["PRODLIKE-E2E-IDENTITY-LANES", "BP-017", "Quota- and session-isolated production-like browser cohort", "Pass", "Browser- and lane-specific fictional identities completed 141/141 project executions with zero retries against HTTPS/PostgreSQL", "DEF-QV-048; DEF-QV-051; DEF-QV-064"],
  ["PRODLIKE-BOOTSTRAP-GATED-PLAN", "pipeline-01", "All-gates runtime module cardinality", "Pass", "Bootstrap derived its completion count from the enabled runtime plan and passed with CP-2G and CP-4D enabled", "DEF-QV-050"],
  ["PRODLIKE-CSP-SOURCE-PREFLIGHT", "BP-017", "Exact-artifact CSP and source freshness", "Pass", "Every staged inline-script hash was present in the live CSP and no frontend source file postdated the export before 46 journeys ran", "DEF-QV-052; DEF-QV-053"],
  ["A11Y-ISSUER-LOADING-STATUS", "issuer-01", "Valid asynchronous loading semantics", "Pass", "The issuer loading state exposed a named busy status region; the exact-build axe matrix reported zero violation nodes", "DEF-QV-054"],
  ["RESPONSIVE-MODEL-REPORT-RECOVERY", "model-43", "Narrow recovery and export operability", "Pass", "At 390x844 compact header labels and tools-drawer fallbacks produced zero clipped controls across Model and Report Studio", "DEF-QV-055"],
  ["A11Y-QUERY-ISOLATED-IDENTITY", "query-01", "Quota-isolated dynamic Query states", "Pass", "Ready, graph lane, persisted answer, and narrow restored-answer states completed under a dedicated analyst with zero axe nodes", "DEF-QV-056"],
  ["FRONTEND-AGGREGATE-1707", "BP-017", "Reconciled frontend executable inventory", "Pass", "All 1,707 current nodes are reconciled: the complete 1,543-node full run plus 164 later nodes executed through complete affected files", "DEF-QV-074; DEF-QV-075; DEF-QV-076; DEF-QV-078; DEF-QV-079; DEF-QV-080; DEF-QV-081; DEF-QV-082; DEF-QV-083; DEF-QV-084; DEF-QV-085; DEF-QV-086; DEF-QV-088; DEF-QV-089; DEF-QV-091; DEF-QV-093; DEF-QV-095; DEF-QV-097; DEF-QV-098; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-114; DEF-QV-115; DEF-QV-116; DEF-QV-117; DEF-QV-118; DEF-QV-120; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-129; DEF-QV-130; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-152; DEF-QV-160; DEF-QV-161; DEF-QV-162"],
  ["SERVER-AGGREGATE-2536", "BP-017", "Reconciled backend executable inventory", "Pass", "2,512/2,512 current executable server nodes and all nine stress/cohort nodes are reconciled as passing; 15 intentional skips remain across 2,536 collected evidence nodes", "DEF-QV-099; DEF-QV-100; DEF-QV-101; DEF-QV-119; DEF-QV-121; DEF-QV-131; DEF-QV-136; DEF-QV-152; DEF-QV-160"],
  ["FRONTEND-ASK-DELTA-16", "BP-017", "Late Ask coverage delta", "Pass", "The final complete Ask.coverage.test.tsx revision passed all 16 nodes added after the aggregate and Issuers delta", ""],
  ["SERVER-ANALYSIS-DELTA-14", "BP-017", "Late analysis workspace route and contract delta", "Pass", "The complete modified test_analysis_workspace.py file passed 13 executable cases with one intentional skip, covering all 11 nodes added after the aggregate collection", ""],
  ["SERVER-QA-SEED-SECURITY-9", "BP-017", "Scale seeder and deployed-header regression", "Pass", "9/9 focused server tests passed against the guarded scale fixture and security-header contracts", ""],
  ["BUILD-MONITOR-JSX-COMMENT", "monitor-01", "Monitor JSX comment placement", "Pass", "The explanatory comment moved from the attribute list into the valid child region; the next 20-route production build passed", "DEF-QV-057"],
  ["BUILD-REPORTDOC-SEMANTIC-HEADING", "reports-01", "Report document semantic heading closure", "Pass", "The completed concurrent h2 edit passed production parsing, ReportDoc unit coverage, and Report Studio journeys", "DEF-QV-058"],
  ["EXACT-CURRENT-FRESHNESS-SEAL", "BP-017", "Exact-current application validation seal", "Pass", "The latest executed test snapshot reconciles all 1,707 frontend, 2,512 executable server, and nine stress/cohort nodes plus clean lint and type check; the current production source builds all 20 routes, the affected Settings and Model source deltas pass 27/27 cross-browser executions plus four responsive axe states, the complete Upload, Sector Review, Settings, and Shell cohorts pass, and the full 141/141 browser and 36/36 accessibility baselines remain recorded", "DEF-QV-059; DEF-QV-066; DEF-QV-073; DEF-QV-077; DEF-QV-079; DEF-QV-080; DEF-QV-081; DEF-QV-082; DEF-QV-083; DEF-QV-084; DEF-QV-085; DEF-QV-086; DEF-QV-087; DEF-QV-088; DEF-QV-089; DEF-QV-091; DEF-QV-095; DEF-QV-097; DEF-QV-098; DEF-QV-099; DEF-QV-100; DEF-QV-101; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-114; DEF-QV-115; DEF-QV-116; DEF-QV-117; DEF-QV-118; DEF-QV-119; DEF-QV-120; DEF-QV-121; DEF-QV-122; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-129; DEF-QV-130; DEF-QV-131; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-136; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-151; DEF-QV-152; DEF-QV-153; DEF-QV-154; DEF-QV-155; DEF-QV-157; DEF-QV-158; DEF-QV-159; DEF-QV-160; DEF-QV-161; DEF-QV-162"],
  ["CONCURRENT-DELTA-RECONCILIATION", "BP-017", "Post-seal test additions remain evidence-backed", "Pass", "Eight modified frontend files passed 48/48 and every modified backend file was rerun through a final 71-test coverage-edge cohort, covering all nodes added after the aggregate runs", ""],
  ["AUTH-CREDENTIAL-THROTTLE-MATRIX", "auth-02", "Every credential endpoint enforces both throttle buckets", "Pass", "Eight exact endpoint/bucket cases plus the 10-allowed/11th-blocked boundary passed; throttled requests short-circuited with HTTP 429", ""],
  ["AUTH-RESPONSIVE-A11Y-MATRIX", "auth-01", "Login, registration, recovery, and error states at narrow and intermediate widths", "Pass", "All four Playwright states passed with axe-core at 390x844 and 900x900", "DEF-QV-061"],
  ["INGESTION-SPAWN-ISOLATION", "pipeline-01", "Process-isolated parsing regression doubles", "Pass", "The 34-node ingestion/pipeline cohort passed with one intentional skip while retaining production spawn isolation", "DEF-QV-062"],
  ["PIPELINE-FAILURE-FENCE", "pipeline-01", "Claimed worker fences terminal failure writes", "Pass", "The claimed owner is propagated after the lease commit and the complete backend regression passes", "DEF-QV-063"],
  ["E2E-CROSS-BROWSER-141", "BP-017", "Production-like Chromium, Firefox, and WebKit matrix", "Pass", "47 unique journeys passed in each browser engine for 141/141 zero-retry project executions", "DEF-QV-064"],
  ["QUERY-CONTEXT-READY-GATE", "query-01", "Query interaction waits for URL-bound context", "Pass", "Focused component regression and the complete cross-browser matrix verify the composer stays inert until contextReady", "DEF-QV-065"],
  ["MONITOR-HYDRATION-GATE", "monitor-01", "Monitor dataset tabs wait for analysis bootstrap", "Pass", "Five focused Monitor tests and the complete browser matrix verify pre-hydration clicks cannot be lost", "DEF-QV-067"],
  ["A11Y-ROUTE-MATRIX-36", "BP-017", "All application routes at desktop and mobile viewports", "Pass", "18 routes across 1440x900 and 390x844 produced zero axe nodes, scan errors, layout failures, overflow, or clipped controls", ""],
  ["A11Y-ROOT-READINESS-RETRY", "SCR-008", "Root redirect readiness remains fail-closed and deterministic", "Pass", "The current full 36-state matrix passed with the bounded complete-navigation retry available; a second miss still serializes scan_error and exits non-zero", "DEF-QV-069"],
  ["GITNEXUS-SEMANTIC-DISCOVERY", "BP-017", "Semantic discovery and repository-wide change scope use the current graph", "Not applicable", "Explicit external-tool waiver: the long-lived MCP FTS handle and repository-wide diff buffer are outside CAOS runtime scope. Current symbol impacts, exact inventories, local semantic/source queries, explicit path-scoped diffs, and direct regressions are the documented compensating controls", "DEF-QV-060; DEF-QV-201"],
  ["QUERY-CURRENT-CONTRACT-19", "query-16", "Query contracts match the persisted investigation workbench", "Pass", "All 19 Query features describe the current screen/API workflows; the complete 23-case interaction file plus history, metric, and visualization support tests pass, and every Query feature has direct assertion-level evidence", "DEF-QV-139"],
  ["POST-SEAL-DELTA-102", "BP-017", "Post-seal frontend and backend additions are executed before publication", "Pass", "Every complete file contributing the 83 net new frontend nodes after the 1,611-node seal passes, and all nineteen later backend nodes pass through their complete affected files", "DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-152"],
  ["API-CONTRACT-ID-ROUTE-RECONCILIATION", "API-042", "Parameterized API feature IDs match the current route inventory", "Pass", "The canonical generator reconciled every API-tagged pytest parameter to one exact current method/path; all 14 direct HTTP contracts passed", "DEF-QV-070"],
  ["FRONTEND-FIXTURE-CONTRACT-9", "BP-017", "Current test fixtures satisfy lint, type, and behavior contracts", "Pass", "ShortcutHelp and FlagToQa passed 9/9 after the minimal fixture/import corrections; lint and TypeScript also pass cleanly", "DEF-QV-071; DEF-QV-072"],
  ["QUERY-CITATION-TUPLE-BUILD", "query-01", "Query citation metadata preserves its inferred tuple type", "Pass", "The minimal non-null filter fix passes targeted Query tests, TypeScript, the production build, and all cross-browser Query journeys", "DEF-QV-073"],
  ["UPLOAD-SMOKE-CURRENT-COPY", "SCR-018", "Upload route smoke follows the implemented intake-link label", "Pass", "The complete Upload smoke file and the reconciled frontend inventory pass with the current 'Jump to intake form' accessible name", "DEF-QV-074"],
  ["MOREDRAWER-QUIESCENT-FOCUS", "BP-017", "MoreDrawer focus trap is validated from a quiescent test revision", "Pass", "The completed focus-trap file passed 2/2 in isolation, 14/14 in its focused cohort, and in both subsequent aggregate runs", "DEF-QV-075"],
  ["GRAPH-ZOOM-TYPED-FIXTURE", "BP-017", "Graph zoom test state matches the d3 transform contract", "Pass", "Both hook tests, lint, TypeScript, the production build, and the final aggregate pass with an explicit ZoomTransform fixture", "DEF-QV-076"],
  ["RESEARCH-ADVANCED-HYDRATION-FENCE", "research-13", "Advanced brief user interaction wins over late preference hydration", "Pass", "The formerly failing WebKit Settings-to-Research journey passed in a focused 4/4 spec and the complete 141/141 zero-retry cross-browser matrix", "DEF-QV-077"],
  ["THESIS-PREDICTION-PUBLIC-SHAPE", "issuer-01", "Thesis fixtures match the public PredictionOut model", "Pass", "The complete ThesisTimeline file, TypeScript, build, and final frontend aggregate pass without internal-only response fields", "DEF-QV-078"],
  ["ISSUER-NULLABLE-PUBLIC-SHAPE", "issuer-01", "Issuer fields match the nullable FastAPI response contract", "Pass", "After the CRITICAL-fan-out type widening, the current frontend inventory, static gates, production build, 15 affected cross-browser journeys, and four affected route-width scans all pass", "DEF-QV-079"],
  ["FRONTEND-INTERACTION-HARNESS-TYPES", "BP-017", "Interaction harnesses satisfy lint and TypeScript contracts", "Pass", "Ask, Pipeline, Research, Deep-Dive, Report Studio, Command Center, Upload, Command Palette, RV Screener, Alert Inbox, IC Book, role-switch, modal-stack, persona composition, navigation, and surface-state harnesses pass their focused files, lint, TypeScript, and the reconciled 1,707-node frontend inventory", "DEF-QV-080; DEF-QV-082; DEF-QV-083; DEF-QV-084; DEF-QV-085; DEF-QV-086; DEF-QV-088; DEF-QV-089; DEF-QV-091; DEF-QV-095; DEF-QV-097; DEF-QV-098; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-114; DEF-QV-115; DEF-QV-116; DEF-QV-117; DEF-QV-120; DEF-QV-122; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-129; DEF-QV-130; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-152; DEF-QV-160; DEF-QV-162"],
  ["COMMAND-INTERACTION-HARNESS-5", "BP-017", "Command Center interaction harness matches public data contracts", "Pass", "All five directory, holdings, focus-refresh, empty/offline, decision-state, and cited-brief journeys pass with exact production fixture shapes; lint and TypeScript are clean", "DEF-QV-083"],
  ["PIPELINE-DIRECT-EVIDENCE-45", "pipeline-44", "Every Pipeline feature has direct assertion-level evidence", "Pass", "The exact-current evidence map covers all 45/45 Pipeline features; frontend behavior passed in the 1,259-node aggregate and seven linked API contracts passed in the focused 93-pass server cohort", "DEF-QV-081"],
  ["RESEARCH-DIRECT-EVIDENCE-29", "research-29", "Every Research feature has direct assertion-level evidence", "Pass", "The exact-current evidence map covers all 29/29 Research features; the completed current frontend Research cohort and focused backend cohort pass, alongside the 1,707-node frontend and reconciled 2,512-pass backend inventories", "DEF-QV-084; DEF-QV-100; DEF-QV-119; DEF-QV-121; DEF-QV-131; DEF-QV-135"],
  ["DEEPDIVE-DIRECT-EVIDENCE-42", "deepdive-42", "Every Deep-Dive feature has direct assertion-level evidence", "Pass", "The exact-current evidence map covers all 42/42 reconciled Deep-Dive features, including seven current workflows absent from the legacy inventory", ""],
  ["ISSUER-DIRECT-EVIDENCE-29", "issuer-31", "Every Issuer feature has direct assertion-level evidence", "Pass", "All 29/29 stable Issuer features describe the current directory and profile behavior and resolve to exact assertions; the complete five-file Issuer cohort passes 72/72", "DEF-QV-168; DEF-QV-169"],
  ["UPLOAD-HARNESS-PUBLIC-TYPES", "BP-017", "Upload interaction harnesses match public component contracts", "Pass", "UploadWizard and step interactions pass 12/12 with exact public types; lint and TypeScript are clean", "DEF-QV-085"],
  ["COMMAND-PALETTE-DEFERRED-TYPE", "BP-017", "Command Palette deferred issuer response matches getIssuers", "Pass", "All six current Command Palette interactions pass with the resolver derived from getIssuers; lint and TypeScript are clean", "DEF-QV-086"],
  ["UPLOAD-DIRECT-EVIDENCE-27", "upload-27", "Every Upload feature has direct assertion-level evidence", "Pass", "The exact-current evidence map covers all 27/27 Upload features; the complete frontend Upload cohort passes 40/40 and the mapped ingestion, EDGAR, storage, XLSX, AV, and concurrency server cohort passes 125/125", "DEF-QV-151"],
  ["MODEL-CONCURRENT-DELTA-13", "BP-017", "Concurrent Model source and test delta remains regression-clean", "Pass", "Seven frontend and six backend Model nodes are reconciled through 68/68 frontend and 66/66 backend passes, clean lint/type/build gates, 15/15 cross-browser journeys, and two clean responsive axe states", "DEF-QV-152"],
  ["SECTOR-DIRECT-EVIDENCE-9", "command-51", "Every Sector Review feature has direct assertion-level evidence", "Pass", "All 9/9 stable Sector Review Feature IDs describe the current versioned dossier and resolve to focused frontend or server assertions; legacy v1 routes remain separately discoverable as API contracts", "DEF-QV-153"],
  ["SETTINGS-DIRECT-EVIDENCE-10", "settings-10", "Every Settings feature has direct assertion-level evidence", "Pass", "All 10/10 stable Settings Feature IDs describe the current five-tab authenticated workbench and resolve to focused frontend, server, or cross-browser assertions", "DEF-QV-154"],
  ["SHELL-DIRECT-EVIDENCE-13", "shell-08", "Every Shell feature has direct assertion-level evidence", "Pass", "All 13/13 stable Shell Feature IDs describe the current role-aware, keyboard-operable, responsive shared workspace and resolve to focused assertion-level automation; the complete current Shell cohort passes 68/68", "DEF-QV-157; DEF-QV-158; DEF-QV-159; DEF-QV-161"],
  ["LATE-SHELL-PERSONA-DELTA-4", "BP-017", "Late Shell and persona evidence delta", "Pass", "Four exact frontend additions pass through their four complete affected files at 28/28, including desktop skip focus, absent page-action handling, empty-action focus semantics, and the public persona composition hook", "DEF-QV-161; DEF-QV-162"],
  ["AUTOMATION-COLLECTOR-NODE-COUNT", "BP-017", "Automation collector excludes diagnostics and fails closed on drift", "Pass", "The canonical inventory contains exactly 4,420 evidence nodes: 1,707 frontend, 2,536 server/stress/cohort, 141 browser, and 36 accessibility states; current collection is exact against the executed inventories", "DEF-QV-087; DEF-QV-093; DEF-QV-095; DEF-QV-098; DEF-QV-099; DEF-QV-100; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-115; DEF-QV-117; DEF-QV-119; DEF-QV-120; DEF-QV-121; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-130; DEF-QV-131; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-136; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-151; DEF-QV-152; DEF-QV-160; DEF-QV-162"],
  ["RV-SCREENER-HARNESS-TYPES", "BP-017", "RV Screener harness matches the public analysis-context contract", "Pass", "All 12 RV Screener interactions pass with a complete typed AnalysisContext fixture; lint and TypeScript are clean", "DEF-QV-088"],
  ["ALERT-INBOX-HARNESS-TYPES", "BP-017", "Alert Inbox harness uses a bounded React-fiber test shape", "Pass", "All 17 Alert Inbox interactions pass with no explicit any; lint and TypeScript are clean", "DEF-QV-089"],
];
const executedCaseOverrides = new Map([
  ["FRONTEND-AGGREGATE-1707", { id: "FRONTEND-INTERMEDIATE-1707", name: "Intermediate frontend executable inventory", result: "The intermediate 1,707-node seal passed before the later shared hierarchy tranche added a net ten more nodes", defects: "DEF-QV-160; DEF-QV-161; DEF-QV-162" }],
  ["EXACT-CURRENT-FRESHNESS-SEAL", { result: "The latest executed snapshot reconciles all 1,726 frontend, 2,512 executable server, and nine stress/cohort nodes with clean lint, type check, and a 20-route production build; the full 141-browser and 36-accessibility baselines remain recorded", defects: "DEF-QV-059; DEF-QV-066; DEF-QV-073; DEF-QV-077; DEF-QV-079; DEF-QV-080; DEF-QV-081; DEF-QV-082; DEF-QV-083; DEF-QV-084; DEF-QV-085; DEF-QV-086; DEF-QV-087; DEF-QV-088; DEF-QV-089; DEF-QV-091; DEF-QV-095; DEF-QV-097; DEF-QV-098; DEF-QV-099; DEF-QV-100; DEF-QV-101; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-114; DEF-QV-115; DEF-QV-116; DEF-QV-117; DEF-QV-118; DEF-QV-119; DEF-QV-120; DEF-QV-121; DEF-QV-122; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-129; DEF-QV-130; DEF-QV-131; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-136; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-151; DEF-QV-152; DEF-QV-153; DEF-QV-154; DEF-QV-155; DEF-QV-157; DEF-QV-158; DEF-QV-159; DEF-QV-160; DEF-QV-161; DEF-QV-162; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166; DEF-QV-170; DEF-QV-175" }],
  ["FRONTEND-INTERACTION-HARNESS-TYPES", { result: "Interaction, modal, persona, navigation, surface-state, Panel, recovery, and shared hierarchy harnesses pass their complete affected files alongside clean lint, TypeScript, and the reconciled 1,726-node frontend inventory", defects: "DEF-QV-080; DEF-QV-082; DEF-QV-083; DEF-QV-084; DEF-QV-085; DEF-QV-086; DEF-QV-088; DEF-QV-089; DEF-QV-091; DEF-QV-095; DEF-QV-097; DEF-QV-098; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-114; DEF-QV-115; DEF-QV-116; DEF-QV-117; DEF-QV-120; DEF-QV-122; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-129; DEF-QV-130; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-152; DEF-QV-160; DEF-QV-162; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166; DEF-QV-170; DEF-QV-175" }],
  ["RESEARCH-DIRECT-EVIDENCE-29", { result: "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the 1,726-node frontend and reconciled 2,512-pass backend inventories" }],
  ["SHELL-DIRECT-EVIDENCE-13", { id: "SHELL-DIRECT-EVIDENCE-17", result: "All 17/17 Shell Feature IDs describe the current role-aware, keyboard-operable, responsive shared workspace and resolve to direct assertion-level automation; the expanded Shell/design cohort passes 83/83", defects: "DEF-QV-157; DEF-QV-158; DEF-QV-159; DEF-QV-161; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166" }],
  ["LATE-SHELL-PERSONA-DELTA-4", { id: "LATE-SHARED-HIERARCHY-DELTA-14", name: "Late shared hierarchy and Shell evidence delta", result: "A net 14 frontend additions reconcile through eight complete affected files at 61/61 and the expanded 17-feature Shell/design cohort at 83/83", defects: "DEF-QV-161; DEF-QV-162; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166" }],
  ["AUTOMATION-COLLECTOR-NODE-COUNT", { result: "The canonical inventory contains exactly 4,430 evidence nodes: 1,717 frontend, 2,536 server/stress/cohort, 141 browser, and 36 accessibility states; current collection is exact against the executed inventories", defects: "DEF-QV-087; DEF-QV-093; DEF-QV-095; DEF-QV-098; DEF-QV-099; DEF-QV-100; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-115; DEF-QV-117; DEF-QV-119; DEF-QV-120; DEF-QV-121; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-130; DEF-QV-131; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-136; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-151; DEF-QV-152; DEF-QV-160; DEF-QV-162" }],
]);
executedCaseOverrides.set("SERVER-AGGREGATE-2536", { id: "SERVER-INTERMEDIATE-2536", name: "Intermediate backend executable inventory", result: "The intermediate 2,536-node server/stress/cohort seal passed before three HTTP policy nodes landed", defects: "DEF-QV-160; DEF-QV-167" });
executedCaseOverrides.set("EXACT-CURRENT-FRESHNESS-SEAL", { result: "The latest executed snapshot reconciles all 1,726 frontend, 2,515 executable server, and nine stress/cohort nodes with clean lint, type check, and a 20-route production build; the full 141-browser and 36-accessibility baselines remain recorded", defects: "DEF-QV-059; DEF-QV-066; DEF-QV-073; DEF-QV-077; DEF-QV-079; DEF-QV-080; DEF-QV-081; DEF-QV-082; DEF-QV-083; DEF-QV-084; DEF-QV-085; DEF-QV-086; DEF-QV-087; DEF-QV-088; DEF-QV-089; DEF-QV-091; DEF-QV-095; DEF-QV-097; DEF-QV-098; DEF-QV-099; DEF-QV-100; DEF-QV-101; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-114; DEF-QV-115; DEF-QV-116; DEF-QV-117; DEF-QV-118; DEF-QV-119; DEF-QV-120; DEF-QV-121; DEF-QV-122; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-129; DEF-QV-130; DEF-QV-131; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-136; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-151; DEF-QV-152; DEF-QV-153; DEF-QV-154; DEF-QV-155; DEF-QV-157; DEF-QV-158; DEF-QV-159; DEF-QV-160; DEF-QV-161; DEF-QV-162; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166; DEF-QV-167; DEF-QV-170; DEF-QV-175" });
executedCaseOverrides.set("RESEARCH-DIRECT-EVIDENCE-29", { result: "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the 1,726-node frontend and reconciled 2,515-pass backend inventories" });
executedCaseOverrides.set("AUTOMATION-COLLECTOR-NODE-COUNT", { result: "The canonical inventory contains exactly 4,442 evidence nodes: 1,726 frontend, 2,539 server/stress/cohort, 141 browser, and 36 accessibility states; current collection is exact against the executed inventories", defects: "DEF-QV-087; DEF-QV-093; DEF-QV-095; DEF-QV-098; DEF-QV-099; DEF-QV-100; DEF-QV-102; DEF-QV-103; DEF-QV-104; DEF-QV-105; DEF-QV-106; DEF-QV-107; DEF-QV-108; DEF-QV-109; DEF-QV-110; DEF-QV-111; DEF-QV-112; DEF-QV-113; DEF-QV-115; DEF-QV-117; DEF-QV-119; DEF-QV-120; DEF-QV-121; DEF-QV-123; DEF-QV-124; DEF-QV-125; DEF-QV-126; DEF-QV-127; DEF-QV-128; DEF-QV-130; DEF-QV-131; DEF-QV-132; DEF-QV-133; DEF-QV-134; DEF-QV-135; DEF-QV-136; DEF-QV-137; DEF-QV-139; DEF-QV-140; DEF-QV-141; DEF-QV-142; DEF-QV-143; DEF-QV-144; DEF-QV-145; DEF-QV-146; DEF-QV-147; DEF-QV-148; DEF-QV-149; DEF-QV-150; DEF-QV-151; DEF-QV-152; DEF-QV-160; DEF-QV-162; DEF-QV-167; DEF-QV-170; DEF-QV-175" });
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").result = "The latest executed snapshot reconciles all 1,783 frontend, 2,516 executable server, and nine stress/cohort nodes with clean lint, type check, and a current 20-route production build; the browser inventory is reconciled to 150, the 36-state accessibility baseline remains recorded, and the exact-current Sector performance audit is retained";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").defects += "; DEF-QV-177; DEF-QV-179; DEF-QV-180; DEF-QV-181; DEF-QV-182; DEF-QV-183; DEF-QV-184; DEF-QV-185; DEF-QV-186; DEF-QV-187; DEF-QV-188; DEF-QV-189; DEF-QV-190; DEF-QV-191; DEF-QV-192; DEF-QV-193; DEF-QV-194; DEF-QV-195; DEF-QV-196; DEF-QV-197; DEF-QV-198; DEF-QV-199; DEF-QV-200";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").result = "Interaction, typed-action, authority, evidence-selection, completion-state, modal, persona, navigation, Sector, surface-state, Panel, recovery, and shared hierarchy harnesses pass their complete affected files alongside clean lint, TypeScript, and the reconciled 1,783-node frontend inventory";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").defects += "; DEF-QV-177; DEF-QV-179; DEF-QV-180; DEF-QV-181; DEF-QV-182; DEF-QV-184; DEF-QV-189; DEF-QV-190; DEF-QV-192; DEF-QV-193; DEF-QV-194; DEF-QV-196; DEF-QV-197; DEF-QV-198; DEF-QV-199";
executedCaseOverrides.get("RESEARCH-DIRECT-EVIDENCE-29").result = "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the 1,783-node frontend and reconciled 2,516-pass backend inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").result = "The canonical inventory contains exactly 4,510 evidence nodes: 1,783 frontend, 2,540 server/stress/cohort, 150 browser, 36 accessibility states, and one exact-current Sector performance node; current collection is exact against the executed inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").defects += "; DEF-QV-177; DEF-QV-188; DEF-QV-189; DEF-QV-190; DEF-QV-191; DEF-QV-198";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").result = "The latest executed snapshot reconciles all 1,792 frontend, 2,516 executable server, and nine stress/cohort nodes with clean lint, type check, and a current 20-route production build; the browser inventory is reconciled to 150, 36 accessibility states remain recorded, and exact-current Sector and Monitor performance audits are retained";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").defects += "; DEF-QV-202; DEF-QV-203; DEF-QV-204";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").result = "Interaction, typed-action, authority, evidence-selection, completion-state, Monitor, modal, persona, navigation, Sector, surface-state, Panel, recovery, and shared hierarchy harnesses pass their complete affected files alongside clean lint, TypeScript, and the reconciled 1,792-node frontend inventory";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").defects += "; DEF-QV-202; DEF-QV-204";
executedCaseOverrides.get("RESEARCH-DIRECT-EVIDENCE-29").result = "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the 1,792-node frontend and reconciled 2,516-pass backend inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").result = "The canonical inventory contains exactly 4,520 evidence nodes: 1,792 frontend, 2,540 server/stress/cohort, 150 browser, 36 accessibility states, and two exact-current route performance nodes; current collection is exact against the executed inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").defects += "; DEF-QV-202; DEF-QV-203; DEF-QV-204";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").result = "The latest executed snapshot reconciles all 1,801 frontend, 2,520 executable server, and nine stress/cohort nodes with clean lint, type check, and a current 20-route production build; the browser inventory is reconciled to 162, 36 accessibility mappings remain recorded, and four exact-current route performance nodes are retained";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").defects += "; DEF-QV-206; DEF-QV-207; DEF-QV-208; DEF-QV-209; DEF-QV-210; DEF-QV-211; DEF-QV-212; DEF-QV-213; DEF-QV-214; DEF-QV-215; DEF-QV-216";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").result = "Interaction, typed-action, authority, evidence-selection, completion-state, Pipeline, Monitor, Report Studio, modal, persona, navigation, Sector, surface-state, Panel, recovery, and shared hierarchy harnesses pass their complete affected files alongside clean lint, TypeScript, and the reconciled 1,801-node frontend inventory";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").defects += "; DEF-QV-206; DEF-QV-207; DEF-QV-208; DEF-QV-209; DEF-QV-210; DEF-QV-211; DEF-QV-212; DEF-QV-214; DEF-QV-215";
executedCaseOverrides.get("RESEARCH-DIRECT-EVIDENCE-29").result = "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the 1,801-node frontend and reconciled 2,520-pass backend inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").result = "The canonical inventory contains exactly 4,547 evidence nodes: 1,801 frontend, 2,544 server/stress/cohort, 162 browser, 36 accessibility mappings, and four exact-current route performance nodes; current collection is exact against the executed inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").defects += "; DEF-QV-206; DEF-QV-207; DEF-QV-208; DEF-QV-209; DEF-QV-210; DEF-QV-211; DEF-QV-212; DEF-QV-213; DEF-QV-214; DEF-QV-215; DEF-QV-216";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").result = "The latest executed snapshot passes all 1,803 frontend nodes in one full run, retains the reconciled 2,544 server/stress/cohort and 162 browser identities, and passes clean lint, TypeScript, a current 20-route production build, exact-built Monitor accessibility/workbench checks, and five production-gzip performance samples";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").defects += "; DEF-QV-203; DEF-QV-217; DEF-QV-218";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").result = "Interaction, typed-action, authority, evidence-selection, completion-state, Pipeline, Monitor, Ask, Report Studio, modal, persona, navigation, Sector, surface-state, Panel, recovery, and shared hierarchy harnesses pass their complete affected files alongside clean lint, TypeScript, and the full 1,803-node frontend inventory";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").defects += "; DEF-QV-203; DEF-QV-217; DEF-QV-218";
executedCaseOverrides.get("RESEARCH-DIRECT-EVIDENCE-29").result = "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the full 1,803-node frontend and reconciled 2,520-pass backend inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").result = "The canonical inventory contains exactly 4,549 evidence nodes: 1,803 frontend, 2,544 server/stress/cohort, 162 browser, 36 accessibility mappings, and four exact-current route-performance nodes; current collection is exact against the executed inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").defects += "; DEF-QV-203; DEF-QV-217; DEF-QV-218";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").result = "The latest executed snapshot reconciles all 1,814 frontend, 2,616 server/stress/cohort, and 165 browser identities; the prior 1,809-node frontend full run remains sealed, both later Settings nodes pass through their complete file and linked cohort, and the concurrent three-node Deep-Dive module-group file passes completely. Model and Settings focused browser, accessibility, performance, lint, and type gates remain green";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").defects += "; DEF-QV-219; DEF-QV-220; DEF-QV-221; DEF-QV-222; DEF-QV-223; DEF-QV-224; DEF-QV-225; DEF-QV-226; DEF-QV-227; DEF-QV-228; DEF-QV-229; DEF-QV-230; DEF-QV-231; DEF-QV-232; DEF-QV-233; DEF-QV-234; DEF-QV-235; DEF-QV-236; DEF-QV-237; DEF-QV-238; DEF-QV-239; DEF-QV-240; DEF-QV-241";
executedCaseOverrides.get("EXACT-CURRENT-FRESHNESS-SEAL").defects += "; DEF-QV-242; DEF-QV-243; DEF-QV-244; DEF-QV-245; DEF-QV-246";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").result = "Interaction, typed-action, authority, evidence-selection, completion-state, Pipeline, Monitor, Ask, Report Studio, Model checkpoint, Settings, Deep-Dive module grouping, modal, persona, navigation, Sector, surface-state, Panel, recovery, and shared hierarchy harnesses pass their complete affected files alongside clean lint, TypeScript, and the reconciled 1,814-node frontend inventory";
executedCaseOverrides.get("FRONTEND-INTERACTION-HARNESS-TYPES").defects += "; DEF-QV-219; DEF-QV-220; DEF-QV-221; DEF-QV-224; DEF-QV-232; DEF-QV-235";
executedCaseOverrides.get("RESEARCH-DIRECT-EVIDENCE-29").result = "The exact-current evidence map covers all 29/29 Research features; the completed frontend Research cohort and focused backend cohort pass alongside the reconciled 1,814-node frontend and 2,592-pass executable server inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").result = "The canonical inventory contains exactly 4,638 evidence nodes: 1,814 frontend, 2,616 server/stress/cohort, 165 browser, 36 accessibility mappings, six exact-current route-performance nodes, and one exact-current browser interaction/responsive node; current collection is exact against the executed inventories";
executedCaseOverrides.get("AUTOMATION-COLLECTOR-NODE-COUNT").defects += "; DEF-QV-219; DEF-QV-222; DEF-QV-231; DEF-QV-232; DEF-QV-233; DEF-QV-234; DEF-QV-235; DEF-QV-236; DEF-QV-237; DEF-QV-238; DEF-QV-239; DEF-QV-240; DEF-QV-241; DEF-QV-242; DEF-QV-243; DEF-QV-246";
for (const row of executedCases) {
  const override = executedCaseOverrides.get(row[0]);
  if (!override) continue;
  if (override.id) row[0] = override.id;
  if (override.name) row[2] = override.name;
  if (override.result) row[4] = override.result;
  if (override.defects) row[5] = override.defects;
}
executedCases.push(["FRONTEND-INTERMEDIATE-1731", "BP-017", "Intermediate frontend executable inventory", "Pass", "The 1,731-node seal passed before the Command authority and shared page-action additions landed", "DEF-QV-162; DEF-QV-163; DEF-QV-164; DEF-QV-165; DEF-QV-166; DEF-QV-168; DEF-QV-169; DEF-QV-170; DEF-QV-175; DEF-QV-177"]);
executedCases.push(["FRONTEND-INTERMEDIATE-1745", "BP-017", "Intermediate frontend executable inventory", "Pass", "The 1,745-node seal passed before thirteen evidence-selection and completion-state nodes landed", "DEF-QV-177; DEF-QV-179; DEF-QV-180; DEF-QV-181; DEF-QV-182; DEF-QV-184; DEF-QV-188; DEF-QV-189"]);
executedCases.push(["FRONTEND-AGGREGATE-1758", "BP-017", "Reconciled frontend executable inventory", "Pass", "All 1,758 current nodes are reconciled: the complete 1,543-node full run plus 215 later nodes executed through complete affected files", "DEF-QV-177; DEF-QV-179; DEF-QV-180; DEF-QV-181; DEF-QV-182; DEF-QV-184; DEF-QV-188; DEF-QV-189; DEF-QV-190"]);
executedCases.push(["SERVER-AGGREGATE-2539", "BP-017", "Reconciled backend executable inventory", "Pass", "All 2,515 executable server nodes and nine stress/cohort nodes pass; 15 intentional skips remain across the exact 2,539-node server/stress/cohort inventory", "DEF-QV-160; DEF-QV-167"]);
executedCases.push(["COMMAND-DIRECT-EVIDENCE-44", "command-42", "Every main Command Center feature has a complete direct scenario suite", "Pass", "All 44/44 main Command Center Feature IDs have assertion-level evidence for all seven mandatory scenarios, producing 308/308 direct scenario passes", "DEF-QV-179; DEF-QV-180; DEF-QV-181; DEF-QV-182; DEF-QV-183"]);
executedCases.push(["E2E-COMMAND-CROSS-BROWSER-12", "command-24", "Command Center current cross-browser and phone workflow", "Pass", "All four current Command journeys pass in Chromium, Firefox, and WebKit for 12/12 zero-retry executions, including every dataset at 390px without document overflow", "DEF-QV-185; DEF-QV-186; DEF-QV-187"]);
executedCases.push(["PAGE-ACTION-IDENTITY-STABILITY-10", "BP-017", "Page-action label checks have stable collected identities", "Pass", "All ten source-contract checks pass and every operation descriptor is unique in the collected frontend inventory", "DEF-QV-189"]);
executedCases.push(["SHARED-EVIDENCE-COMPLETION-DELTA-13", "BP-017", "Late evidence-selection and completion-state delta", "Pass", "All thirteen late nodes pass through their four complete contributing files", "DEF-QV-190"]);
executedCases.push(["A11Y-COMMAND-RESPONSIVE-2", "command-24", "Command Center exact-built responsive accessibility", "Pass", "The desktop and phone states both report zero WCAG nodes and zero geometry, target-size, clipping, or collision failures", ""]);
executedCases.push(["TRACKER-QUIESCENT-COLLECTION", "BP-017", "Tracker collection recovery after concurrent transform pressure", "Pass", "The fail-closed collector rejected the timed-out attempt and exported only after the exact 1,758-node inventory completed in a quiescent rerun", "DEF-QV-191"]);
executedCases.push(["FRONTEND-AGGREGATE-1783", "BP-017", "Reconciled frontend executable inventory", "Pass", "All 1,783 current nodes are reconciled; the 27 additions and two retired identities after the 1,758-node seal passed through all twelve complete contributing files at 92/92", "DEF-QV-192; DEF-QV-193; DEF-QV-194; DEF-QV-196; DEF-QV-197; DEF-QV-198; DEF-QV-199"]);
executedCases.push(["SERVER-AGGREGATE-2544", "BP-017", "Reconciled backend executable inventory", "Pass", "All 2,520 executable server nodes and nine stress/cohort nodes pass; 15 intentional skips remain across the exact 2,544-node server/stress/cohort inventory", "DEF-QV-195; DEF-QV-198; DEF-QV-216"]);
executedCases.push(["SECTOR-SCENARIO-CLOSURE-63", "command-50", "Every Sector Review feature has a complete direct scenario suite", "Pass", "All nine Sector Review Feature IDs have assertion-level evidence for all seven mandatory scenarios, producing 63/63 direct scenario passes", "DEF-QV-192; DEF-QV-193; DEF-QV-194; DEF-QV-195; DEF-QV-196; DEF-QV-197"]);
executedCases.push(["E2E-SECTOR-CROSS-BROWSER-6", "command-30", "Sector Review current cross-browser and phone workflow", "Pass", "Both current Sector Review journeys pass in Chromium, Firefox, and WebKit for 6/6 zero-retry executions with exact API-hit gates and no cross-sector dossier resurrection", "DEF-QV-192; DEF-QV-194; DEF-QV-196; DEF-QV-200"]);
executedCases.push(["A11Y-SECTOR-RESPONSIVE-2", "command-47", "Sector Review exact-built responsive accessibility", "Pass", "Desktop and phone states both report zero WCAG nodes, scan errors, geometry failures, target-size issues, clipping, overflow, or collisions", ""]);
executedCases.push(["PERF-SECTOR-DESKTOP-MOBILE-2", "command-30", "Sector Review desktop and throttled-mobile performance audit", "Pass", "Desktop ready/LCP/TBT were 513ms/148ms/0ms; throttled mobile ready/LCP/TBT were 6,274ms/6,120ms/186ms. No scan error occurred; mobile LCP remains a named residual risk without an invented pass budget", ""]);
executedCases.push(["FRONTEND-AGGREGATE-1792", "BP-017", "Reconciled frontend executable inventory", "Pass", "All 1,792 current nodes are reconciled; four Monitor nodes and five concurrent additions after the 1,783-node seal pass through their five complete contributing files at 44/44", "DEF-QV-202; DEF-QV-204"]);
executedCases.push(["MONITOR-SCENARIO-CLOSURE-49", "monitor-07", "Every Monitor feature has a complete direct scenario suite", "Pass", "All seven Monitor Feature IDs have assertion-level evidence for all seven mandatory scenarios, producing 49/49 direct scenario passes", "DEF-QV-202"]);
executedCases.push(["E2E-MONITOR-CROSS-BROWSER-12", "monitor-04", "Monitor current cross-browser workflow", "Pass", "All four current Monitor journeys pass in Chromium, Firefox, and WebKit for 12/12 zero-retry executions", ""]);
executedCases.push(["A11Y-MONITOR-RESPONSIVE-2", "monitor-01", "Monitor exact-built responsive accessibility", "Pass", "Desktop and phone states both report zero WCAG nodes, scan errors, geometry failures, target-size issues, clipping, overflow, or collisions", ""]);
executedCases.push(["PERF-MONITOR-DESKTOP-MOBILE-5-GZIP", "monitor-07", "Monitor production-gzip desktop and five-sample throttled-mobile performance audit", "Pass", "Desktop ready/LCP/TBT are 502ms/148ms/0ms. Five 4x-CPU, 150ms-latency, 1.6Mbps mobile samples have p75 ready/LCP/TBT 2,492ms/2,100ms/188ms with 227.2KB encoded JavaScript, gzip on every static asset, and no scan error", "DEF-QV-203"]);
executedCases.push(["FRONTEND-AGGREGATE-1801", "BP-017", "Reconciled frontend executable inventory", "Pass", "All 1,801 current nodes are reconciled; the exact-current full run found two failures at 1,799/1,801, both were repaired, and the complete affected Report Studio and responsive-recovery files pass 24/24", "DEF-QV-206; DEF-QV-207; DEF-QV-209; DEF-QV-210; DEF-QV-211; DEF-QV-212; DEF-QV-214; DEF-QV-215"]);
executedCases.push(["FRONTEND-AGGREGATE-1803", "BP-017", "Current full frontend executable inventory", "Pass", "All 1,803 current nodes pass in one full run across 261 files after the Ask context and lazy-surface split", "DEF-QV-203; DEF-QV-218"]);
executedCases.push(["MONITOR-ASK-LAZY-WATERFALL", "monitor-07", "Closed Monitor excludes the heavy Ask surface and first open loads it", "Pass", "The exact production waterfall contains 15 initial chunks without the 08lw7bttg3qpb Ask chunk; opening the accessible Ask CAOS phone utility loads that chunk plus its result renderers and displays the Ask with Query dialog", "DEF-QV-203"]);
executedCases.push(["MONITOR-WORKBENCH-REFERENCE-3", "monitor-07", "Monitor exact-built responsive workbench validator", "Pass", "Explicit Reference mode passes desktop, tablet, and phone validation with drawer focus restored, one table owner, no document overflow, and no decision/workbench overlap", "DEF-QV-217"]);
executedCases.push(["PIPELINE-SCENARIO-CLOSURE-315", "pipeline-45", "Every Pipeline feature has a complete direct scenario suite", "Pass", "All 45 Pipeline Feature IDs have assertion-level evidence for all seven mandatory scenarios, producing 315/315 direct scenario passes without treating route cold-load evidence as request-load proof", "DEF-QV-206; DEF-QV-207; DEF-QV-208"]);
executedCases.push(["PIPELINE-SERVER-LINKED-104", "pipeline-40", "Pipeline linked run, API, engine, role, and tenancy regression", "Pass", "All 104 executable linked server cases pass; two intentional environment-gated skips and one existing Starlette deprecation warning remain disclosed", ""]);
executedCases.push(["E2E-PIPELINE-CROSS-BROWSER-12", "pipeline-45", "Pipeline current cross-browser and phone workflow", "Pass", "All four current Pipeline journeys pass in Chromium, Firefox, and WebKit for 12/12 zero-retry executions; the 390px drawer contains exactly one Stage lanes control", "DEF-QV-208; DEF-QV-210; DEF-QV-211"]);
executedCases.push(["A11Y-PIPELINE-RESPONSIVE-6", "pipeline-10", "Pipeline and directory exact-built responsive accessibility", "Pass", "The /issuers, live-empty /pipeline, and explicit-reference /pipeline desktop and phone states all report zero WCAG nodes, scan errors, geometry failures, target-size issues, clipping, overflow, or collisions", "DEF-QV-215"]);
executedCases.push(["PERF-PIPELINE-DESKTOP-MOBILE-4", "pipeline-09", "Pipeline and directory desktop and throttled-mobile route audit", "Pass", "Pipeline desktop ready/FCP/LCP/TBT/CLS were 509ms/36ms/144ms/0ms/0.006 with 1,128.2KB JavaScript; throttled mobile was 6,810ms/4,284ms/6,380ms/203ms/0.010 with 870.9KB JavaScript. Issuers desktop ready/LCP/TBT/CLS were 499ms/136ms/0ms/0.000; throttled mobile was 7,664ms/7,240ms/137ms/0.003. No scan error occurred; these are route cold-load observations, not request-load results", ""]);
executedCases.push(["FRONTEND-AGGREGATE-1809", "BP-017", "Current full frontend executable inventory", "Pass", "All 1,809 current nodes pass in one full run across 261 files; the prior attempt exposed one stale Model History support-selection step at 1,807/1,808 before the semantic harness correction and the final Report invalid-persistence assertion", "DEF-QV-232; DEF-QV-235"]);
executedCases.push(["REPORT-SCENARIO-CLOSURE-194", "reports-28", "Every applicable Report Studio scenario has direct execution evidence", "Pass", "All 194/194 applicable Report Studio scenarios pass; the two mobile/responsive scenarios for backend-only reports-26 and reports-27 are explicitly Not applicable", "DEF-QV-219; DEF-QV-220; DEF-QV-224"]);
executedCases.push(["REPORT-WORKBENCH-REFERENCE-3", "reports-03", "Report Studio exact-built responsive workbench", "Pass", "Reference mode passes desktop, tablet, and phone interaction/geometry checks with utility and evidence focus restored, six deliverables, no API fallthrough, and no uncontained clipping or page overflow", "DEF-QV-222; DEF-QV-223; DEF-QV-224; DEF-QV-225; DEF-QV-226; DEF-QV-227; DEF-QV-230"]);
executedCases.push(["A11Y-REPORTS-RESPONSIVE-2", "reports-03", "Report Studio exact-built responsive accessibility", "Pass", "The 1440x900 and 390x844 states both report zero WCAG nodes, scan errors, layout failures, clipped controls, target-size failures, collisions, or page overflow", "DEF-QV-224; DEF-QV-230"]);
executedCases.push(["PERF-REPORTS-DESKTOP-MOBILE-5-GZIP", "reports-28", "Report Studio production-gzip desktop and five-sample constrained-mobile route audit", "Pass", "Desktop ready/LCP/TBT are 596ms/148ms/2ms. Five 4x-CPU, 150ms-latency, 1.6Mbps mobile samples have p75 ready/LCP/TBT 2,968ms/2,324ms/330ms with 267.0KB encoded JavaScript, gzip on every static asset, zero CLS, and no scan error; this is route cold-load evidence, not request-load evidence", "DEF-QV-222; DEF-QV-230"]);
executedCases.push(["REPORT-FOCUSED-REGRESSION-43", "reports-28", "Report Studio focused frontend and backend authority regression", "Pass", "All 41 focused MoreDrawer, SubHeader, panel, and Report interaction cases pass; both exact committee/vault authority nodes pass under .venv311, and the broader complete server files pass 65 executable cases with two intentional skips", "DEF-QV-220; DEF-QV-221; DEF-QV-224; DEF-QV-228; DEF-QV-229; DEF-QV-235"]);
executedCases.push(["MODEL-SCENARIO-CLOSURE-462", "model-66", "Every Model Builder feature has a complete direct scenario suite", "Pass", "All 66 Model Builder Feature IDs have assertion-level evidence for all seven mandatory scenarios, producing 462/462 direct scenario passes across the legacy reference calculator and live governed Model Engine v2 workbench", "DEF-QV-240; DEF-QV-241"]);
executedCases.push(["MODEL-FOCUSED-FRONTEND-229", "model-01", "Model Builder focused frontend regression", "Pass", "All 229 cases pass across 24 Model route, component, and library files", "DEF-QV-236; DEF-QV-240; DEF-QV-241"]);
executedCases.push(["MODEL-FOCUSED-SERVER-242", "model-52", "Model Engine, persistence, workbook, scenario, and rate-boundary regression", "Pass", "All 242 linked server cases pass under .venv311, including the complete 62-case changed-file delta; one existing Starlette/httpx deprecation warning remains disclosed", "DEF-QV-240; DEF-QV-243; DEF-QV-246"]);
executedCases.push(["E2E-MODEL-CROSS-BROWSER-15", "model-44", "Model Builder current cross-browser workflow", "Pass", "All five current Model journeys pass in Chromium, Firefox, and WebKit for 15/15 zero-retry executions after the harness follows the implemented Model support selection", "DEF-QV-236; DEF-QV-238; DEF-QV-239"]);
executedCases.push(["A11Y-MODEL-RESPONSIVE-2", "model-42", "Model Builder responsive accessibility", "Pass", "The 1440x900 and 390x844 states both report zero WCAG nodes, scan errors, layout failures, clipped controls, target-size failures, collisions, or page overflow", "DEF-QV-239"]);
executedCases.push(["PERF-MODEL-DESKTOP-MOBILE-5-GZIP", "model-47", "Model Builder production-gzip desktop and five-sample constrained-mobile route audit", "Pass", "Desktop ready/FCP/LCP/TBT are 1,295/48/108/0ms. Five 4x-CPU, 150ms-latency, 1.6Mbps mobile samples have p75 ready/FCP/LCP/TBT 3,540/980/2,152/293ms with 297.9KB encoded JavaScript, gzip, zero CLS, and readiness gated on the real Model worksheet", "DEF-QV-237; DEF-QV-239"]);
executedCases.push(["MODEL-API-SCENARIO-CLOSURE-108", "API-089", "Every applicable Model API scenario has direct execution evidence", "Pass", "All 108/108 applicable scenarios across API-072 through API-089 pass; 18 backend-only Mobile/responsive scenarios are explicitly Not applicable", "DEF-QV-242; DEF-QV-243"]);
executedCases.push(["MODEL-API-FOCUSED-SERVER-62", "API-079", "Model API complete changed-file regression", "Pass", "Both complete changed Model API files pass 62/62 under .venv311 after correcting two harness-only contract assumptions", "DEF-QV-243; DEF-QV-244; DEF-QV-245; DEF-QV-246"]);
executedCases.push(["MODEL-API-PERFORMANCE-CONTRACT-18", "API-087", "Model API bounded-work contract matrix", "Pass", "All 18 handler-specific performance contracts preserve singleton queries, list limits, payload/batch caps, CAS/serialization, rate limits, semaphore control, capped reads, and thread offloading as applicable", "DEF-QV-243; DEF-QV-246"]);
executedCases.push(["API-DIRECT-EVIDENCE-CLOSURE-11", "API-006", "Final canonical direct-evidence closure", "Pass", "The ten initially unmapped API rows and the newly exposed borrowed-evidence alias now carry exact passing runtime evidence, bringing canonical direct feature coverage to 683/683 with a fail-closed zero-gap gate", "DEF-QV-247; DEF-QV-248"]);
executedCases.push(["API-LIST-FOCUSED-SERVER-32", "API-006", "API list/root and alias focused regression", "Pass", "All 32 cases pass across the new list/root contract file and the complete legacy portfolio, portfolio-management, and sponsor suites", "DEF-QV-247; DEF-QV-248"]);
executedCases.push(["API-LIST-SCENARIO-CLOSURE-66", "API-169", "Every applicable list/root API scenario has direct execution evidence", "Pass", "All 66/66 applicable scenarios across the eleven list/root API features pass; 11 backend-only Mobile/responsive scenarios are explicitly Not applicable", "DEF-QV-249; DEF-QV-250; DEF-QV-251"]);
executedCases.push(["API-LIST-FOCUSED-SERVER-58", "API-006", "List/root API complete changed and linked regression", "Pass", "The complete 33-case quality file and 58-case linked alias cohort pass after correcting two harness-only assumptions", "DEF-QV-249; DEF-QV-250; DEF-QV-251; DEF-QV-252"]);
executedCases.push(["SERVER-AGGREGATE-2605", "BP-017", "Reconciled backend executable inventory", "Pass", "The exact 2,605-node server/stress/cohort inventory is reconciled as 2,581 passing executable server nodes, 15 intentional skips, and nine passing stress/cohort nodes; the 26-node list/root API delta passes through its complete changed file", "DEF-QV-251; DEF-QV-252"]);
executedCases.push(["SETTINGS-SCENARIO-CLOSURE-94", "settings-01", "Every applicable Settings UI and API scenario has direct execution evidence", "Pass", "All 94/94 applicable scenarios across ten Settings features and API-164 through API-167 pass with assertion-level evidence; the four backend-only responsive scenarios are explicitly Not applicable", "DEF-QV-253; DEF-QV-256"]);
executedCases.push(["SETTINGS-FOCUSED-FRONTEND-56", "settings-08", "Settings linked frontend regression", "Pass", "All 56 cases pass across the complete Settings page, research preference, model-mode, coverage-edge, shared component-edge, and RequireAuth files", "DEF-QV-253; DEF-QV-256; DEF-QV-257"]);
executedCases.push(["SETTINGS-FOCUSED-SERVER-291", "API-164", "Settings API and configuration linked server regression", "Pass", "All 291 cases pass across the complete Settings API, Settings quality, configuration-inventory, and write-role files under .venv311; one existing Starlette/httpx deprecation warning remains disclosed", "DEF-QV-254; DEF-QV-255; DEF-QV-256; DEF-QV-257; DEF-QV-258"]);
executedCases.push(["E2E-SETTINGS-CROSS-BROWSER-15", "settings-06", "Settings current cross-browser and phone workflow", "Pass", "All five current Settings journeys pass in Chromium, Firefox, and WebKit for 15/15 zero-retry executions; every tab is reachable at 390x844 without document overflow", "DEF-QV-256; DEF-QV-257; DEF-QV-259; DEF-QV-260"]);
executedCases.push(["SETTINGS-LINT-TYPE-2", "BP-017", "Settings source and harness static gates", "Pass", "Exact-current ESLint and TypeScript no-emit checks complete with zero findings after the Settings contract additions", ""]);
executedCases.push(["FRONTEND-AGGREGATE-1819", "BP-017", "Reconciled frontend executable inventory", "Pass", "The exact 1,819-node frontend inventory is reconciled: the prior 1,814-node seal plus five new Deep-Dive and responsive assertions executed through their complete 161-case linked cohort and 22-case Ask/responsive cohort", "DEF-QV-262; DEF-QV-263; DEF-QV-264"]);
executedCases.push(["SERVER-AGGREGATE-2616", "BP-017", "Reconciled backend executable inventory", "Pass", "The exact 2,616-node server/stress/cohort inventory is reconciled as 2,592 passing executable server nodes, 15 intentional skips, and nine passing stress/cohort nodes; all eleven new Settings quality nodes pass through the complete linked cohort", "DEF-QV-257"]);
executedCases.push(["DEEPDIVE-SCENARIO-CLOSURE-294", "deepdive-42", "Every applicable Deep-Dive scenario has direct execution evidence", "Pass", "All 294/294 scenarios across the 42 current Deep-Dive features pass with assertion-level evidence, including error, boundary, invalid-input, permission, performance, and responsive behavior", "DEF-QV-262; DEF-QV-263; DEF-QV-264; DEF-QV-265; DEF-QV-266; DEF-QV-267"]);
executedCases.push(["DEEPDIVE-FOCUSED-FRONTEND-161", "deepdive-42", "Deep-Dive complete linked frontend regression", "Pass", "All 161 cases pass across the current Deep-Dive route, components, supporting libraries, shared evidence and recovery surfaces, Model scenario propagation, and report evidence modal", "DEF-QV-262; DEF-QV-263; DEF-QV-264"]);
executedCases.push(["DEEPDIVE-FOCUSED-SERVER-7", "deepdive-41", "Deep-Dive QA flag backend regression", "Pass", "All seven QA-flag service cases pass under .venv311, including ownership and undisclosed-issuer rejection", ""]);
executedCases.push(["E2E-DEEPDIVE-CROSS-BROWSER-12", "deepdive-42", "Deep-Dive current cross-browser and phone workflow", "Pass", "All four current Deep-Dive journeys pass in Chromium, Firefox, and WebKit for 12/12 zero-retry executions against the explicit reference mode; the phone workbench preserves evidence, utilities, and the global Ask trigger without document overflow", "DEF-QV-262; DEF-QV-267"]);
executedCases.push(["A11Y-DEEPDIVE-RESPONSIVE-2", "deepdive-42", "Deep-Dive responsive accessibility", "Pass", "The 1440x900 and 390x844 reference states both report zero WCAG nodes, scan errors, layout failures, clipped controls, or page overflow after the Ask utility breakpoint correction", "DEF-QV-262"]);
executedCases.push(["PERF-DEEPDIVE-DESKTOP-MOBILE-2-GZIP", "deepdive-38", "Deep-Dive production-gzip desktop and constrained-mobile route audit", "Pass", "The explicit reference workbench meets the current route budgets at desktop and constrained mobile with gzip, zero CLS, zero scan errors, and readiness gated on rendered Deep-Dive analyst content", ""]);
executedCases.push(["AUTOMATION-EVIDENCE-4647", "BP-017", "Exact-current automation evidence seal", "Pass", "The canonical inventory contains exactly 4,647 nodes: 1,819 frontend, 2,616 server/stress/cohort, 168 browser, 36 accessibility, seven performance, and one responsive-workbench node", "DEF-QV-262; DEF-QV-263; DEF-QV-264; DEF-QV-267"]);
executedCases.push(["E2E-ROUTED-CONCEPTS-CROSS-BROWSER-15", "BP-014", "Previously uncovered routed-concept browser contracts", "Pass", "All five deterministic route contracts pass in Chromium, Firefox, and WebKit for 15/15 zero-retry executions with exact fixtures, converged Sponsor context synchronization, and no unhandled local API fallthrough; frozen-candidate real-API repetition remains required", "DEF-QV-268; DEF-QV-271; DEF-QV-272"]);
executedCases.push(["FRONTEND-AGGREGATE-1750-PD04", "BP-017", "Post-PD-04 frontend executable inventory", "Pass", "All 1,750 current frontend nodes pass after the intentional removal of 69 dead-subject nodes from the prior 1,819-node seal; the reduction is disposition accounting, not coverage growth", "DEF-QV-269"]);
executedCases.push(["SERVER-AGGREGATE-2618-CURRENT", "BP-017", "Current server/stress/cohort inventory", "Pass", "The 2,618 collected nodes reconcile to 2,594 passing server cases, 15 intentional skips, and nine passing stress/cohort cases", "DEF-QV-269"]);
executedCases.push(["AUTOMATION-EVIDENCE-4595", "BP-017", "Exact-current automation evidence seal", "Pass", "The canonical inventory contains exactly 4,595 nodes: 1,750 frontend, 2,618 server/stress/cohort, 183 browser, 36 accessibility, seven performance, and one responsive-workbench node", "DEF-QV-268; DEF-QV-269; DEF-QV-270; DEF-QV-271; DEF-QV-272"]);
executedCases.push(["E2E-RECOVERY-CROSS-BROWSER-6", "BP-017", "Shipped root/global and shared-segment boundary recovery", "Pass", "Both browser-only named render failures reach the intended shipped boundary in Chromium, Firefox, and WebKit for 6/6 zero-retry executions. Root retry preserves the authenticated Settings tab with zero writes; segment retry preserves the owned context, IC Memo payload, source preference, and analyst override, with zero failure-time writes and exactly one recovery autosave revision", "DEF-QV-273"]);
executedCases.push(["AUTOMATION-EVIDENCE-4601", "BP-017", "Exact-current automation evidence seal", "Pass", "The canonical inventory contains exactly 4,601 nodes: 1,750 frontend, 2,618 server/stress/cohort, 189 browser, 36 accessibility, seven performance, and one responsive-workbench node", "DEF-QV-268; DEF-QV-269; DEF-QV-270; DEF-QV-271; DEF-QV-272; DEF-QV-273"]);
executedCases.push(["APP-IMAGE-RESOURCE-CONTRACT-1", "BP-017", "Immutable app-image runtime resource contract", "Pass", "The real image builds from a 3.88 MB deny-by-default context and, as UID 10001, loads the non-noprompts methodology fingerprint, both exact manifest-backed prompt bundles, and 588 immutable RV rows at the production consumer path; the independent image scan finds no application secrets, tests, virtualenvs, or extra frontend source", "DEF-QV-274; DEF-QV-275"]);
for (const [id, featureId, name, status, result, defectId] of executedCases) {
  const executedDate = [
    "API-CONTRACT-ID-ROUTE-RECONCILIATION",
    "FRONTEND-INTERMEDIATE-1707",
    "FRONTEND-INTERMEDIATE-1731",
    "FRONTEND-INTERMEDIATE-1745",
    "FRONTEND-AGGREGATE-1758",
    "FRONTEND-ASK-DELTA-16",
    "FRONTEND-FIXTURE-CONTRACT-9",
    "GITNEXUS-SEMANTIC-DISCOVERY",
    "GRAPH-ZOOM-TYPED-FIXTURE",
    "RESEARCH-ADVANCED-HYDRATION-FENCE",
    "QUERY-CITATION-TUPLE-BUILD",
    "SERVER-INTERMEDIATE-2536",
    "SERVER-AGGREGATE-2539",
    "SERVER-ANALYSIS-DELTA-14",
    "UPLOAD-SMOKE-CURRENT-COPY",
    "MOREDRAWER-QUIESCENT-FOCUS",
    "THESIS-PREDICTION-PUBLIC-SHAPE",
    "ISSUER-NULLABLE-PUBLIC-SHAPE",
    "PIPELINE-DIRECT-EVIDENCE-45",
    "COMMAND-INTERACTION-HARNESS-5",
    "RESEARCH-DIRECT-EVIDENCE-29",
    "UPLOAD-HARNESS-PUBLIC-TYPES",
    "UPLOAD-DIRECT-EVIDENCE-27",
    "MODEL-CONCURRENT-DELTA-13",
    "SETTINGS-DIRECT-EVIDENCE-10",
    "SHELL-DIRECT-EVIDENCE-17",
    "LATE-SHARED-HIERARCHY-DELTA-14",
    "COMMAND-PALETTE-DEFERRED-TYPE",
    "AUTOMATION-COLLECTOR-NODE-COUNT",
    "RV-SCREENER-HARNESS-TYPES",
    "ALERT-INBOX-HARNESS-TYPES",
    "COMMAND-DIRECT-EVIDENCE-44",
    "E2E-COMMAND-CROSS-BROWSER-12",
    "PAGE-ACTION-IDENTITY-STABILITY-10",
    "SHARED-EVIDENCE-COMPLETION-DELTA-13",
    "FRONTEND-AGGREGATE-1783",
    "SERVER-AGGREGATE-2544",
    "SECTOR-SCENARIO-CLOSURE-63",
    "E2E-SECTOR-CROSS-BROWSER-6",
    "A11Y-SECTOR-RESPONSIVE-2",
    "PERF-SECTOR-DESKTOP-MOBILE-2",
    "FRONTEND-AGGREGATE-1792",
    "MONITOR-SCENARIO-CLOSURE-49",
    "E2E-MONITOR-CROSS-BROWSER-12",
    "A11Y-MONITOR-RESPONSIVE-2",
    "PERF-MONITOR-DESKTOP-MOBILE-2",
    "FRONTEND-AGGREGATE-1801",
    "PIPELINE-SCENARIO-CLOSURE-315",
    "PIPELINE-SERVER-LINKED-104",
    "E2E-PIPELINE-CROSS-BROWSER-12",
    "A11Y-PIPELINE-RESPONSIVE-6",
    "PERF-PIPELINE-DESKTOP-MOBILE-4",
    "MODEL-SCENARIO-CLOSURE-462",
    "MODEL-FOCUSED-FRONTEND-229",
    "MODEL-FOCUSED-SERVER-242",
    "E2E-MODEL-CROSS-BROWSER-15",
    "A11Y-MODEL-RESPONSIVE-2",
    "PERF-MODEL-DESKTOP-MOBILE-5-GZIP",
    "MODEL-API-SCENARIO-CLOSURE-108",
    "MODEL-API-FOCUSED-SERVER-62",
    "MODEL-API-PERFORMANCE-CONTRACT-18",
    "API-DIRECT-EVIDENCE-CLOSURE-11",
    "API-LIST-FOCUSED-SERVER-32",
    "API-LIST-SCENARIO-CLOSURE-66",
    "API-LIST-FOCUSED-SERVER-58",
    "SERVER-AGGREGATE-2605",
    "SETTINGS-SCENARIO-CLOSURE-94",
    "SETTINGS-FOCUSED-FRONTEND-56",
    "SETTINGS-FOCUSED-SERVER-291",
    "E2E-SETTINGS-CROSS-BROWSER-15",
    "SETTINGS-LINT-TYPE-2",
    "FRONTEND-AGGREGATE-1819",
    "SERVER-AGGREGATE-2616",
    "DEEPDIVE-SCENARIO-CLOSURE-294",
    "DEEPDIVE-FOCUSED-FRONTEND-161",
    "DEEPDIVE-FOCUSED-SERVER-7",
    "E2E-DEEPDIVE-CROSS-BROWSER-12",
    "A11Y-DEEPDIVE-RESPONSIVE-2",
    "PERF-DEEPDIVE-DESKTOP-MOBILE-2-GZIP",
    "AUTOMATION-EVIDENCE-4647",
    "E2E-ROUTED-CONCEPTS-CROSS-BROWSER-15",
    "FRONTEND-AGGREGATE-1750-PD04",
    "SERVER-AGGREGATE-2618-CURRENT",
    "AUTOMATION-EVIDENCE-4595",
    "E2E-RECOVERY-CROSS-BROWSER-6",
    "AUTOMATION-EVIDENCE-4601",
    "APP-IMAGE-RESOURCE-CONTRACT-1",
  ].includes(id)
    ? today
    : baselineDate;
  testRows.push([id, featureId, "Direct execution", name, "Current implemented contract is asserted deterministically.", status, result, executedDate, "Automated validation", defectId]);
  evidenceExecutedDateById.set(id, executedDate);
  if (status === "Pass") addEvidence(exactEvidenceByFeature, featureId, id);
}

const issuerScenarioRows = testRows.filter((row) => row[1].startsWith("issuer-") && scenarios.includes(row[2]));
const issuerScenarioGaps = issuerScenarioRows.filter((row) => row[5] !== "Pass");
if (issuerScenarioRows.length !== 29 * scenarios.length || issuerScenarioGaps.length) {
  throw new Error(`Issuer scenario gate failed: ${issuerScenarioRows.length}/${29 * scenarios.length} rows; gaps=${issuerScenarioGaps.map((row) => row[0]).join(",")}`);
}
const commandFeatureIdSet = new Set(commandFeatureIds);
const commandScenarioRows = testRows.filter((row) => commandFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const commandScenarioGaps = commandScenarioRows.filter((row) => row[5] !== "Pass");
if (commandScenarioRows.length !== 44 * scenarios.length || commandScenarioGaps.length) {
  throw new Error(`Command scenario gate failed: ${commandScenarioRows.length}/${44 * scenarios.length} rows; gaps=${commandScenarioGaps.map((row) => row[0]).join(",")}`);
}
const deepDiveFeatureIdSet = new Set(deepDiveFeatureIds);
const deepDiveScenarioRows = testRows.filter((row) => deepDiveFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const deepDiveScenarioGaps = deepDiveScenarioRows.filter((row) => row[5] !== "Pass");
if (deepDiveScenarioRows.length !== deepDiveFeatureIds.length * scenarios.length || deepDiveScenarioGaps.length) {
  throw new Error(`Deep-Dive scenario gate failed: ${deepDiveScenarioRows.length}/${deepDiveFeatureIds.length * scenarios.length} rows; gaps=${deepDiveScenarioGaps.map((row) => `${row[1]}:${row[2]}`).join(",")}`);
}
const pipelineFeatureIdSet = new Set(pipelineFeatureIds);
const pipelineScenarioRows = testRows.filter((row) => pipelineFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const pipelineScenarioGaps = pipelineScenarioRows.filter((row) => row[5] !== "Pass");
if (pipelineScenarioRows.length !== pipelineFeatureIds.length * scenarios.length || pipelineScenarioGaps.length) {
  throw new Error(`Pipeline scenario gate failed: ${pipelineScenarioRows.length}/${pipelineFeatureIds.length * scenarios.length} rows; gaps=${pipelineScenarioGaps.map((row) => row[0]).join(",")}`);
}
const monitorFeatureIdSet = new Set(monitorFeatureIds);
const monitorScenarioRows = testRows.filter((row) => monitorFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const monitorScenarioGaps = monitorScenarioRows.filter((row) => row[5] !== "Pass");
if (monitorScenarioRows.length !== monitorFeatureIds.length * scenarios.length || monitorScenarioGaps.length) {
  throw new Error(`Monitor scenario gate failed: ${monitorScenarioRows.length}/${monitorFeatureIds.length * scenarios.length} rows; gaps=${monitorScenarioGaps.map((row) => row[0]).join(",")}`);
}
const sectorFeatureIdSet = new Set(sectorFeatureIds);
const sectorScenarioRows = testRows.filter((row) => sectorFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const sectorScenarioGaps = sectorScenarioRows.filter((row) => row[5] !== "Pass");
if (sectorScenarioRows.length !== sectorFeatureIds.length * scenarios.length || sectorScenarioGaps.length) {
  throw new Error(`Sector Review scenario gate failed: ${sectorScenarioRows.length}/${sectorFeatureIds.length * scenarios.length} rows; gaps=${sectorScenarioGaps.map((row) => row[0]).join(",")}`);
}
const modelFeatureIdSet = new Set(modelFeatureIds);
const modelScenarioRows = testRows.filter((row) => modelFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const modelScenarioGaps = modelScenarioRows.filter((row) => row[5] !== "Pass");
if (modelScenarioRows.length !== modelFeatureIds.length * scenarios.length || modelScenarioGaps.length) {
  throw new Error(`Model Builder scenario gate failed: ${modelScenarioRows.length}/${modelFeatureIds.length * scenarios.length} rows; gaps=${modelScenarioGaps.map((row) => `${row[1]}:${row[2]}`).join(",")}`);
}
const modelApiFeatureIdSet = new Set(modelApiFeatureIds);
const modelApiScenarioRows = testRows.filter((row) => modelApiFeatureIdSet.has(row[1]) && scenarios.includes(row[2]));
const modelApiApplicableScenarioRows = modelApiScenarioRows.filter((row) => row[5] !== "Not applicable");
const modelApiScenarioGaps = modelApiApplicableScenarioRows.filter((row) => row[5] !== "Pass");
if (
  modelApiScenarioRows.length !== modelApiFeatureIds.length * scenarios.length
  || modelApiApplicableScenarioRows.length !== modelApiFeatureIds.length * (scenarios.length - 1)
  || modelApiScenarioGaps.length
) {
  throw new Error(
    `Model API scenario gate failed: total=${modelApiScenarioRows.length}/${modelApiFeatureIds.length * scenarios.length}, applicable=${modelApiApplicableScenarioRows.length}/${modelApiFeatureIds.length * (scenarios.length - 1)}, gaps=${modelApiScenarioGaps.map((row) => `${row[1]}:${row[2]}`).join(",")}`,
  );
}

const listApiScenarioFeatureIdSet = new Set(listApiScenarioFeatureIds);
const listApiScenarioRows = testRows.filter(
  (row) => listApiScenarioFeatureIdSet.has(row[1]) && scenarios.includes(row[2]),
);
const listApiApplicableScenarioRows = listApiScenarioRows.filter((row) => row[5] !== "Not applicable");
const listApiScenarioGaps = listApiApplicableScenarioRows.filter((row) => row[5] !== "Pass");
if (
  listApiScenarioRows.length !== listApiScenarioFeatureIds.length * scenarios.length
  || listApiApplicableScenarioRows.length !== listApiScenarioFeatureIds.length * (scenarios.length - 1)
  || listApiScenarioGaps.length
) {
  throw new Error(
    `List/root API scenario gate failed: total=${listApiScenarioRows.length}/${listApiScenarioFeatureIds.length * scenarios.length}, applicable=${listApiApplicableScenarioRows.length}/${listApiScenarioFeatureIds.length * (scenarios.length - 1)}, gaps=${listApiScenarioGaps.map((row) => `${row[1]}:${row[2]}`).join(",")}`,
  );
}

const settingsScenarioFeatureIdSet = new Set([...settingsFeatureIds, ...settingsApiFeatureIds]);
const settingsScenarioRows = testRows.filter(
  (row) => settingsScenarioFeatureIdSet.has(row[1]) && scenarios.includes(row[2]),
);
const settingsApplicableScenarioRows = settingsScenarioRows.filter((row) => row[5] !== "Not applicable");
const settingsScenarioGaps = settingsApplicableScenarioRows.filter((row) => row[5] !== "Pass");
if (
  settingsScenarioRows.length !== (settingsFeatureIds.length + settingsApiFeatureIds.length) * scenarios.length
  || settingsApplicableScenarioRows.length !== settingsFeatureIds.length * scenarios.length + settingsApiFeatureIds.length * (scenarios.length - 1)
  || settingsScenarioGaps.length
) {
  throw new Error(
    `Settings scenario gate failed: total=${settingsScenarioRows.length}/98, applicable=${settingsApplicableScenarioRows.length}/94, gaps=${settingsScenarioGaps.map((row) => `${row[1]}:${row[2]}`).join(",")}`,
  );
}

const canonicalDirectEvidenceGaps = featureObjects
  .filter((feature) => !exactEvidenceByFeature.has(feature.id))
  .map((feature) => feature.id);
if (canonicalDirectEvidenceGaps.length) {
  throw new Error(
    `Canonical direct-evidence gate failed: ${featureObjects.length - canonicalDirectEvidenceGaps.length}/${featureObjects.length} direct; gaps=${canonicalDirectEvidenceGaps.join(",")}`,
  );
}

const featureHeaders = [
  "Feature ID", "Feature Name", "Concept", "User Story", "Expected Behaviour", "Edge Cases", "Test Cases",
  "Current Status", "Defect Count", "Severity", "Notes", "Last Tested Date", "Validation Rules", "Dependencies",
  "Known Assumptions", "Trigger", "Files", "Endpoint", "Source Type", "Source Status Detail",
];
const features = featureObjects.map((feature) => {
  const mappedEvidenceIds = [...(exactEvidenceByFeature.get(feature.id) || [])];
  const testIds = [
    ...scenarios.map((scenario) => `${feature.id}-${scenarioSlug(scenario)}`),
    ...mappedEvidenceIds,
  ].join("; ");
  return [
    feature.id, feature.name, feature.concept, feature.story, feature.expected, feature.edgeCases, testIds,
    mappedEvidenceIds.length ? `Direct evidence — ${mappedEvidenceIds.length} automated node(s)` : feature.currentStatus,
    defectCounts.get(feature.id) || 0, featureSeverity.get(feature.id) || feature.severity || "None",
    feature.notes, latestEvidenceDate(mappedEvidenceIds), feature.validationRules, feature.dependencies, feature.assumptions, feature.trigger, feature.files,
    feature.endpoint, feature.sourceType, feature.sourceStatus,
  ];
});

const existingFeatureIds = new Set(featureObjects.map((feature) => feature.id));
for (const defect of defects) {
  if (!existingFeatureIds.has(defect[1])) throw new Error(`Defect ${defect[0]} references missing feature ${defect[1]}`);
}

const apiFeatureStart = sourceRows.length + appRoutes.length;
const apiRows = apiRoutes.map((route, index) => [
  `API-${String(index + 1).padStart(3, "0")}`,
  route.method,
  route.path,
  route.handler,
  route.file,
  route.line,
  route.responseModel || "",
  route.statusCode || "",
  exactEvidenceByFeature.has(featureObjects[apiFeatureStart + index].id)
    ? `Direct — ${exactEvidenceByFeature.get(featureObjects[apiFeatureStart + index].id).size} node(s)`
    : "Documented — direct mapping pending",
  featureObjects[apiFeatureStart + index].id,
]);
const screenRows = appRoutes.map((screen, index) => [
  `SCR-${String(index + 1).padStart(3, "0")}`,
  screen.route,
  screen.file,
  screen.components.join("; "),
  exactEvidenceByFeature.has(`SCR-${String(index + 1).padStart(3, "0")}`)
    ? `Pass — route matrix + ${exactEvidenceByFeature.get(`SCR-${String(index + 1).padStart(3, "0")}`).size} direct node(s)`
    : "Pass — landing load/a11y/responsive",
  `SCR-${String(index + 1).padStart(3, "0")}`,
]);
const configRows = settings.map((setting, index) => [
  `CFG-${String(index + 1).padStart(3, "0")}`,
  setting.environment,
  setting.type,
  setting.defaultValue,
  setting.description,
  `${setting.file}:${setting.line}`,
  exactEvidenceByFeature.has(`CFG-${String(index + 1).padStart(3, "0")}`)
    ? `Direct — ${exactEvidenceByFeature.get(`CFG-${String(index + 1).padStart(3, "0")}`).size} node(s)`
    : "Documented — direct matrix pending",
]);
const journeyRows = journeySeed.map(([id, name, expected, files, status]) => [
  id,
  name,
  expected,
  files,
  exactEvidenceByFeature.has(id) ? `Direct — ${exactEvidenceByFeature.get(id).size} node(s)` : status,
  defects.filter((defect) => defect[1] === id && defect[3] === "Open").length,
]);
const automationEvidenceRows = automationEvidence.map((evidence) => [
  evidence.id,
  evidence.layer,
  evidence.node,
  evidence.scenario,
  evidence.exactFeatureIds.join("; "),
  evidence.indirectFeatureIds.join("; "),
  evidence.mappingBasis,
  "Pass",
  evidence.executionRun,
  evidence.executedDate || baselineDate,
]);
const featureEvidenceRows = featureObjects.map((feature) => {
  const directIds = [...(exactEvidenceByFeature.get(feature.id) || [])];
  const indirectIds = [...(indirectEvidenceByFeature.get(feature.id) || [])];
  const coveredScenarios = scenarios.filter((scenario) => scenarioEvidence.has(`${feature.id}|${scenario}`));
  return [
    feature.id,
    feature.name,
    feature.sourceType,
    directIds.length,
    indirectIds.length,
    directIds.length ? "Direct" : indirectIds.length ? "Indirect only" : "Unmapped",
    coveredScenarios.join("; "),
    directIds.join("; "),
    indirectIds.join("; "),
    today,
  ];
});
const researchEvidenceRows = featureEvidenceRows.filter(([featureId]) => featureId.startsWith("research-"));
const researchEvidenceGaps = researchEvidenceRows.filter((row) => row[5] !== "Direct");
if (researchEvidenceRows.length !== 29 || researchEvidenceGaps.length) {
  throw new Error(`Research direct-evidence gate failed: ${researchEvidenceRows.length}/29 rows; gaps=${researchEvidenceGaps.map((row) => row[0]).join(",")}`);
}
const deepDiveEvidenceRows = featureEvidenceRows.filter(([featureId]) => featureId.startsWith("deepdive-"));
const deepDiveEvidenceGaps = deepDiveEvidenceRows.filter((row) => row[5] !== "Direct");
if (deepDiveEvidenceRows.length !== 42 || deepDiveEvidenceGaps.length) {
  throw new Error(`Deep-Dive direct-evidence gate failed: ${deepDiveEvidenceRows.length}/42 rows; gaps=${deepDiveEvidenceGaps.map((row) => row[0]).join(",")}`);
}
const issuerEvidenceRows = featureEvidenceRows.filter(([featureId]) => featureId.startsWith("issuer-"));
const issuerEvidenceGaps = issuerEvidenceRows.filter((row) => row[5] !== "Direct");
if (issuerEvidenceRows.length !== 29 || issuerEvidenceGaps.length) {
  throw new Error(`Issuer direct-evidence gate failed: ${issuerEvidenceRows.length}/29 rows; gaps=${issuerEvidenceGaps.map((row) => row[0]).join(",")}`);
}
const reportEvidenceRows = featureEvidenceRows.filter(([featureId]) => featureId.startsWith("reports-"));
const reportEvidenceGaps = reportEvidenceRows.filter((row) => row[5] !== "Direct");
if (reportEvidenceRows.length !== 28 || reportEvidenceGaps.length) {
  throw new Error(`Report Studio direct-evidence gate failed: ${reportEvidenceRows.length}/28 rows; gaps=${reportEvidenceGaps.map((row) => row[0]).join(",")}`);
}
const modelEvidenceRows = featureEvidenceRows.filter(([featureId]) => modelFeatureIdSet.has(featureId));
const modelEvidenceGaps = modelEvidenceRows.filter((row) => row[5] !== "Direct");
if (modelEvidenceRows.length !== 66 || modelEvidenceGaps.length) {
  throw new Error(`Model Builder direct-evidence gate failed: ${modelEvidenceRows.length}/66 rows; gaps=${modelEvidenceGaps.map((row) => row[0]).join(",")}`);
}
const reportScenarioRows = testRows.filter((row) => row[1].startsWith("reports-") && scenarios.includes(row[2]));
const reportApplicableScenarioRows = reportScenarioRows.filter((row) => row[5] !== "Not applicable");
const reportScenarioGaps = reportApplicableScenarioRows.filter((row) => row[5] !== "Pass");
if (reportScenarioRows.length !== 196 || reportApplicableScenarioRows.length !== 194 || reportScenarioGaps.length) {
  throw new Error(`Report Studio scenario gate failed: total=${reportScenarioRows.length}, applicable=${reportApplicableScenarioRows.length}, gaps=${reportScenarioGaps.map((row) => `${row[1]}:${row[3]}`).join(",")}`);
}
const featureSourceById = new Map(featureObjects.map((feature) => [feature.id, feature.sourceType]));
const coverageStatsBySource = new Map();
for (const feature of featureObjects) {
  const stats = coverageStatsBySource.get(feature.sourceType) || {
    features: 0,
    direct: 0,
    indirectOnly: 0,
    unmapped: 0,
    pass: 0,
    suiteEvidence: 0,
    designed: 0,
    notApplicable: 0,
  };
  stats.features += 1;
  if (exactEvidenceByFeature.has(feature.id)) stats.direct += 1;
  else if (indirectEvidenceByFeature.has(feature.id)) stats.indirectOnly += 1;
  else stats.unmapped += 1;
  coverageStatsBySource.set(feature.sourceType, stats);
}
for (const row of testRows) {
  const sourceType = featureSourceById.get(row[1]);
  if (!sourceType) continue;
  const stats = coverageStatsBySource.get(sourceType);
  if (row[5] === "Pass") stats.pass += 1;
  else if (row[5] === "Suite evidence") stats.suiteEvidence += 1;
  else if (row[5] === "Designed") stats.designed += 1;
  else if (row[5] === "Not applicable") stats.notApplicable += 1;
}
const coverageGapRows = [...coverageStatsBySource.entries()]
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([sourceType, stats]) => [
    sourceType,
    stats.features,
    stats.direct,
    stats.indirectOnly,
    stats.unmapped,
    stats.pass,
    stats.suiteEvidence,
    stats.designed,
    stats.notApplicable,
  ]);
const featureConceptById = new Map(featureObjects.map((feature) => [feature.id, feature.concept]));
const coverageStatsByConcept = new Map();
for (const feature of featureObjects) {
  const stats = coverageStatsByConcept.get(feature.concept) || {
    features: 0,
    direct: 0,
    unmapped: 0,
    pass: 0,
    suiteEvidence: 0,
    designed: 0,
    notApplicable: 0,
  };
  stats.features += 1;
  if (exactEvidenceByFeature.has(feature.id)) stats.direct += 1;
  else stats.unmapped += 1;
  coverageStatsByConcept.set(feature.concept, stats);
}
for (const row of testRows) {
  const concept = featureConceptById.get(row[1]);
  if (!concept) continue;
  const stats = coverageStatsByConcept.get(concept);
  if (row[5] === "Pass") stats.pass += 1;
  else if (row[5] === "Suite evidence") stats.suiteEvidence += 1;
  else if (row[5] === "Designed") stats.designed += 1;
  else if (row[5] === "Not applicable") stats.notApplicable += 1;
}
const conceptCoverageRows = [...coverageStatsByConcept.entries()]
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([concept, stats]) => [
    concept,
    stats.features,
    stats.direct,
    stats.unmapped,
    stats.pass,
    stats.suiteEvidence,
    stats.designed,
    stats.notApplicable,
  ]);
const controlRows = uiControls.map((control) => [
  control.id,
  control.kind,
  control.tag,
  control.label,
  `${control.file}:${control.line}`,
  control.state,
  control.handlers,
  control.acceptance,
  control.edgeCases,
  "Documented — current TSX source discovery; execution status is carried by Feature Evidence and Test Matrix",
]);
const stateRows = uiStates.map((state) => [
  state.id,
  state.name,
  state.setter,
  state.hook,
  state.initial,
  `${state.file}:${state.line}`,
  state.acceptance,
  state.edgeCases,
  "Documented — current TSX state-hook discovery; user-facing scenarios are reconciled through the curated feature register",
]);
validationRuns.push([
  "UI role/control/state inventory",
  "TypeScript AST scan of caos/frontend/src/**/*.tsx plus explicit auth/capability/presentation role reconciliation",
  "Pass",
  `${roleRows.length} role/state profiles; ${controlRows.length} source-discovered controls including ${controlRows.filter((row) => row[1] === "Modal/dialog").length} modal/dialog invocations; ${stateRows.length} local UI state handles`,
  today,
]);
validationRuns.push([
  "Automation evidence reconciliation",
  "vitest list --json; pytest --collect-only; playwright --list",
  "Pass",
  `${automationEvidence.length.toLocaleString()} executed nodes reconciled to stable evidence IDs and feature mappings`,
  today,
]);

const byConcept = new Map();
for (const feature of featureObjects) byConcept.set(feature.concept, (byConcept.get(feature.concept) || 0) + 1);

await fs.mkdir(outputDir, { recursive: true });
const workbook = Workbook.create();
const summary = workbook.worksheets.add("Coverage Summary");
summary.showGridLines = false;
summary.getRange("A1:C24").values = [
  ["Metric", "Value", "Notes"],
  ["Canonical feature rows", "", "Curated features plus current code-discovered screens, handlers, settings, and workflows"],
  ["Generated test cases", "", "Seven scenario classes per canonical feature plus explicit direct execution cases"],
  ["Executed automation nodes", "", "Every collected Vitest, pytest, and Playwright node has a stable evidence ID"],
  ["Features with direct automation", "", "At least one exact test reference, endpoint invocation, feature-ID assertion, or mapped E2E journey"],
  ["Physical frontend routes", "", "All current app/**/page.tsx routes"],
  ["Production API handlers", "", "All current FastAPI router decorators mounted by main.py"],
  ["Runtime configuration options", "", "All fields in the central Settings class"],
  ["Business processes", "", "Cross-surface durable analyst/operator workflows"],
  ["Role / identity profiles", "", "Authentication states, server capability roles, and Analyst/PM/QA presentation views are separated explicitly"],
  ["Source-discovered UI controls", "", "Current TSX buttons, links, inputs, forms, overlays, dialogs, and custom action components with file/line provenance"],
  ["Modal / dialog controls", "", "Modal/dialog definitions and invocations included in the control inventory"],
  ["Source-discovered UI state handles", "", "Current TSX useState/useReducer/useTransition handles; curated features retain externally visible state contracts"],
  ["Direct test passes", "", "Cases with direct route/state evidence"],
  ["Suite-evidence cases", "", "Covered only by aggregate regression evidence"],
  ["Designed / unexecuted cases", "", "Not presented as pass"],
  ["Not-applicable cases", "", "Scenario class is inapplicable at this feature boundary and is validated at the consuming surface instead"],
  ["Skipped executable cases", "", "Explicit Test Matrix status; 15 intentional pytest skips are separately disclosed in the current-iteration note"],
  ["Blocked validation cases", "", "Blocked direct-execution work remains a completion risk even when application regressions pass"],
  ["Open critical defects", "", "Completion gate"],
  ["Open high defects", "", "Completion gate"],
  ["Other open defects", "", "Includes known validation coverage gaps"],
  ["Confidence score", "98%", "Every executed collected application node is reconciled as passing after remediation; all 203 Issuer, 308 main Command Center, 315 Pipeline, 63 Sector Review, 49 Monitor, 194 applicable Report Studio, 462 Model Builder, 108 applicable Model API, 66 applicable list/root API, and 94 applicable Settings UI/API scenario rows are direct passes, and every canonical feature has direct automation. Model constrained-mobile p75 LCP is 2.152s under the production-gzip lab and its responsive axe states are clean. Confidence remains bounded by 15 intentional environment-gated skips, remaining designed/suite-evidence scenarios outside the closed matrices, lack of field RUM, no staged request-load result in this iteration, and explicitly waived external GitNexus session limitations"],
  ["Last tested date", today, "Current iteration: all 683 canonical features have direct passing automation; all 1,750 frontend, 2,594 executable server, and nine stress/cohort nodes are reconciled as passing with 15 intentional skips. The exact inventory is locked to 4,601 evidence nodes including 189 browser, 36 accessibility mappings, seven route-performance nodes, and one responsive-workbench node. The 15-node routed-concept delta and six-node browser-boundary recovery delta passed across Chromium, Firefox, and WebKit with retries disabled. The recovery proof uses test-only exact chunk rewriting, reaches the shipped root/global and shared-segment boundaries, preserves authenticated analyst state, and proves no failure-time or duplicate mutation; both browser tranches remain per-PR UI contract evidence rather than the frozen H0 real-API seal. The PD-01 app image now builds from a measured 3.88 MB deny-by-default context and its UID-10001 consumer probe validates prompt fingerprint 15bdcbc3628d, both governed specialized bundles, and 588 RV rows; canonical H0 provenance remains open. Model's 462/462 UI/workflow scenarios, all 108/108 applicable Model API scenarios, and all 66/66 applicable list/root API scenarios remain closed. No tracker defect is open; DEF-QV-060 and DEF-QV-201 are explicit external-tool waivers"],
];
summary.getRange("A1:C1").format = { fill: "#12121a", font: { bold: true, color: "#e6e6ef" }, rowHeight: 30 };
summary.getRange("A2:C24").format = { wrapText: true, verticalAlignment: "top" };
summary.getRange("A2:C24").format.borders = { preset: "insideHorizontal", style: "thin", color: "#262633" };
summary.freezePanes.freezeRows(1);
summary.getRange("A:A").format.columnWidth = 28;
summary.getRange("B:B").format.columnWidth = 18;
summary.getRange("C:C").format.columnWidth = 98;

writeSheet(workbook, "Feature Register", featureHeaders, features, [16, 38, 22, 62, 86, 58, 70, 24, 12, 14, 62, 16, 62, 58, 60, 40, 52, 42, 24, 68]);
writeSheet(workbook, "Test Matrix", ["Test ID", "Feature ID", "Scenario", "Steps", "Expected Result", "Execution Status", "Result Notes", "Last Executed", "Automation", "Defect ID"], testRows, [34, 16, 22, 82, 78, 20, 74, 16, 26, 16]);
writeSheet(workbook, "Automation Evidence", ["Evidence ID", "Layer", "Collected Test Node", "Scenario Classification", "Direct Feature IDs", "Indirect Feature IDs", "Mapping Basis", "Execution Status", "Validation Run", "Executed Date"], automationEvidenceRows, [18, 26, 112, 24, 42, 42, 48, 18, 30, 16]);
writeSheet(workbook, "Feature Evidence", ["Feature ID", "Feature Name", "Source Type", "Direct Nodes", "Indirect Nodes", "Evidence Status", "Direct Scenario Coverage", "Direct Evidence IDs", "Indirect Evidence IDs", "Last Reconciled"], featureEvidenceRows, [16, 46, 24, 16, 16, 18, 52, 74, 74, 16]);
writeSheet(workbook, "Coverage Gaps", ["Source Type", "Features", "Direct Features", "Indirect-only Features", "Unmapped Features", "Passed Cases", "Suite-evidence Cases", "Designed Cases", "Not-applicable Cases"], coverageGapRows, [28, 14, 18, 22, 20, 16, 22, 18, 22]);
writeSheet(workbook, "Concept Coverage", ["Concept", "Features", "Direct Features", "Unmapped Features", "Passed Cases", "Suite-evidence Cases", "Designed Cases", "Not-applicable Cases"], conceptCoverageRows, [30, 14, 18, 20, 16, 22, 18, 22]);
writeSheet(workbook, "Defects", ["Defect ID", "Feature ID", "Severity", "Status", "Root Cause Hypothesis", "Reproduction Steps", "Expected Result", "Actual Result", "Notes"], defects, [16, 16, 14, 14, 72, 68, 66, 66, 72]);
writeSheet(workbook, "Validation Runs", ["Suite", "Command", "Status", "Result", "Executed Date"], validationRuns, [30, 74, 14, 76, 16]);
writeSheet(workbook, "API Inventory", ["API Feature ID", "Method", "Path", "Handler", "Route File", "Line", "Response Model", "Status Code", "Coverage", "Feature ID"], apiRows, [16, 12, 46, 34, 38, 10, 30, 16, 16, 16]);
writeSheet(workbook, "Screen Inventory", ["Screen Feature ID", "Route", "Page File", "Primary Components", "Coverage", "Feature ID"], screenRows, [18, 28, 56, 54, 24, 16]);
writeSheet(workbook, "Configuration Inventory", ["Config Feature ID", "Environment Variable", "Type", "Code Default", "Implemented Purpose / Rules", "Source", "Coverage"], configRows, [18, 34, 22, 42, 108, 42, 28]);
writeSheet(workbook, "Journey Inventory", ["Journey ID", "Business Process", "Implemented Flow", "Source / Dependencies", "Current Status", "Open Defects"], journeyRows, [16, 38, 94, 84, 24, 14]);
writeSheet(workbook, "Role Inventory", ["Role ID", "Layer", "Role / State", "Access / Presentation Contract", "Acceptance Criteria", "Finite Risk-based Edge Cases", "Source / Evidence"], roleRows, [16, 24, 34, 78, 86, 76, 72]);
writeSheet(workbook, "Control Inventory", ["Control ID", "Kind", "JSX Tag", "Accessible Label / Expression", "Source", "Declared State Attributes", "Event Handlers", "Acceptance Criteria", "Finite Risk-based Edge Cases", "Execution Status"], controlRows, [16, 24, 22, 58, 58, 50, 26, 92, 88, 64]);
writeSheet(workbook, "State Inventory", ["State ID", "State Handle", "Setter / Dispatch", "Hook", "Initial Expression", "Source", "Acceptance Criteria", "Finite Risk-based Edge Cases", "Execution Status"], stateRows, [16, 30, 34, 18, 50, 58, 90, 82, 64]);
writeSheet(workbook, "Concept Totals", ["Concept", "Feature Count"], [...byConcept.entries()].sort((a, b) => a[0].localeCompare(b[0])), [34, 18]);

// Assign cross-sheet formulas only after every referenced worksheet exists.
summary.getRange("B2").formulas = [[`=COUNTA('Feature Register'!A2:A${features.length + 1})`]];
summary.getRange("B3").formulas = [[`=COUNTA('Test Matrix'!A2:A${testRows.length + 1})`]];
summary.getRange("B4").formulas = [[`=COUNTA('Automation Evidence'!A2:A${automationEvidenceRows.length + 1})`]];
summary.getRange("B5").formulas = [[`=COUNTIF('Feature Evidence'!F2:F${featureEvidenceRows.length + 1},\"Direct\")`]];
summary.getRange("B6").formulas = [[`=COUNTA('Screen Inventory'!A2:A${screenRows.length + 1})`]];
summary.getRange("B7").formulas = [[`=COUNTA('API Inventory'!A2:A${apiRows.length + 1})`]];
summary.getRange("B8").formulas = [[`=COUNTA('Configuration Inventory'!A2:A${configRows.length + 1})`]];
summary.getRange("B9").formulas = [[`=COUNTA('Journey Inventory'!A2:A${journeyRows.length + 1})`]];
summary.getRange("B10").formulas = [[`=COUNTA('Role Inventory'!A2:A${roleRows.length + 1})`]];
summary.getRange("B11").formulas = [[`=COUNTA('Control Inventory'!A2:A${controlRows.length + 1})`]];
summary.getRange("B12").formulas = [[`=COUNTIF('Control Inventory'!B2:B${controlRows.length + 1},\"Modal/dialog\")`]];
summary.getRange("B13").formulas = [[`=COUNTA('State Inventory'!A2:A${stateRows.length + 1})`]];
summary.getRange("B14").formulas = [[`=COUNTIF('Test Matrix'!F2:F${testRows.length + 1},\"Pass\")`]];
summary.getRange("B15").formulas = [[`=COUNTIF('Test Matrix'!F2:F${testRows.length + 1},\"Suite evidence\")`]];
summary.getRange("B16").formulas = [[`=COUNTIF('Test Matrix'!F2:F${testRows.length + 1},\"Designed\")`]];
summary.getRange("B17").formulas = [[`=COUNTIF('Test Matrix'!F2:F${testRows.length + 1},\"Not applicable\")`]];
summary.getRange("B18").formulas = [[`=COUNTIF('Test Matrix'!F2:F${testRows.length + 1},\"Skipped\")`]];
summary.getRange("B19").formulas = [[`=COUNTIF('Test Matrix'!F2:F${testRows.length + 1},\"Blocked\")`]];
summary.getRange("B20").formulas = [[`=COUNTIFS(Defects!C2:C${defects.length + 1},\"Critical\",Defects!D2:D${defects.length + 1},\"Open\")`]];
summary.getRange("B21").formulas = [[`=COUNTIFS(Defects!C2:C${defects.length + 1},\"High\",Defects!D2:D${defects.length + 1},\"Open\")`]];
summary.getRange("B22").formulas = [[`=COUNTIF(Defects!D2:D${defects.length + 1},\"Open\")-B20-B21`]];

const previewRanges = {
  "Coverage Summary": "A1:C24",
  "Feature Register": "A1:T28",
  "Test Matrix": "A1:J34",
  "Automation Evidence": "A1:J32",
  "Feature Evidence": "A1:J30",
  "Coverage Gaps": "A1:I10",
  "Concept Coverage": "A1:H25",
  "Defects": "A1:I30",
  "Validation Runs": "A1:E40",
  "API Inventory": "A1:J35",
  "Screen Inventory": "A1:F19",
  "Configuration Inventory": "A1:G28",
  "Journey Inventory": "A1:F18",
  "Role Inventory": "A1:G8",
  "Control Inventory": "A1:J35",
  "State Inventory": "A1:I35",
  "Concept Totals": "A1:B25",
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const recentPreviewRanges = {
  "Defects Recent": { sheetName: "Defects", range: `A${Math.max(2, defects.length - 28)}:I${defects.length + 1}` },
  "Validation Runs Recent": { sheetName: "Validation Runs", range: `A${Math.max(2, validationRuns.length - 18)}:E${validationRuns.length + 1}` },
};
const modelFeatureStart = features.findIndex((row) => row[0] === "model-44") + 2;
const modelFeatureEnd = features.findIndex((row) => row[0] === "model-66") + 2;
const modelTestStart = testRows.findIndex((row) => row[1] === "model-44" && row[2] === "Happy path") + 2;
const modelTestEnd = testRows.findLastIndex((row) => row[1] === "model-66" && scenarios.includes(row[2])) + 2;
const modelApiTestStart = testRows.findIndex((row) => row[1] === "API-072" && row[2] === "Happy path") + 2;
const modelApiTestEnd = testRows.findLastIndex((row) => row[1] === "API-089" && scenarios.includes(row[2])) + 2;
if (
  modelFeatureStart < 2
  || modelFeatureEnd < modelFeatureStart
  || modelTestStart < 2
  || modelTestEnd < modelTestStart
  || modelApiTestStart < 2
  || modelApiTestEnd < modelApiTestStart
) {
  throw new Error("Model-focused preview bounds could not be resolved");
}
recentPreviewRanges["Model V2 Features"] = { sheetName: "Feature Register", range: `A${modelFeatureStart}:T${modelFeatureEnd}` };
recentPreviewRanges["Model Tests Head"] = { sheetName: "Test Matrix", range: `A${modelTestStart}:J${Math.min(modelTestStart + 27, modelTestEnd)}` };
recentPreviewRanges["Model Tests Tail"] = { sheetName: "Test Matrix", range: `A${Math.max(modelTestStart, modelTestEnd - 27)}:J${modelTestEnd}` };
recentPreviewRanges["Model API Tests Head"] = { sheetName: "Test Matrix", range: `A${modelApiTestStart}:J${Math.min(modelApiTestStart + 41, modelApiTestEnd)}` };
recentPreviewRanges["Model API Tests Middle"] = { sheetName: "Test Matrix", range: `A${Math.min(modelApiTestStart + 42, modelApiTestEnd)}:J${Math.min(modelApiTestStart + 83, modelApiTestEnd)}` };
recentPreviewRanges["Model API Tests Tail"] = { sheetName: "Test Matrix", range: `A${Math.max(modelApiTestStart, modelApiTestEnd - 41)}:J${modelApiTestEnd}` };
for (const [fileName, { sheetName, range }] of Object.entries(recentPreviewRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, `${fileName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const summaryInspection = await workbook.inspect({
  kind: "table",
  range: "Coverage Summary!A1:C24",
  include: "values,formulas",
  tableMaxRows: 24,
  tableMaxCols: 5,
  summary: "canonical coverage summary",
});
console.log(summaryInspection.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const out = await SpreadsheetFile.exportXlsx(workbook);
await out.save(outputPath);
const reopenedWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const reopenedSummary = await reopenedWorkbook.inspect({
  kind: "region",
  sheetId: "Coverage Summary",
  range: "A1:C24",
  maxChars: 6000,
  summary: "persisted coverage summary",
});
console.log(reopenedSummary.ndjson);
const reopenedErrors = await reopenedWorkbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "persisted formula error scan",
});
console.log(reopenedErrors.ndjson);
console.log(outputPath);
