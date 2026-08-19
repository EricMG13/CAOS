# CAOS production-like quality validation — 2026-07-16

## Outcome — clean exact-current seal

The sanitized local production-like rerun6 completed against one isolated static export and remained source-current through the final gate. DEF-QV-059 is fixed and the executable validation ledger is clean:

- 46/46 real-browser journeys passed with retries disabled across three isolated fictional analyst identities.
- 173/173 frontend test files and 949/949 tests passed in both the unit and coverage runs; coverage was 81.10% statements/lines, 75.68% branches, and 63.01% functions.
- Frontend lint and standalone TypeScript checking completed with no findings.
- 2,202 backend/stress/cohort tests passed; 15 environment-gated tests were skipped and remain identified in pytest output.
- 9/9 focused scale-seeder and deployed-header tests passed.
- 36/36 authenticated route/viewport states passed axe and geometry validation at 390x844 and 900x900 with zero violation nodes, scan errors, page overflow, or clipped controls.
- 4/4 dynamic Query states passed axe validation with zero violation nodes.
- The rerun6 frontend built successfully as a 20-route production static export; live CSP hashes matched and no frontend source file postdated the tested export at the final seal.

The workbook distinguishes direct execution, aggregate suite evidence, and designed-but-unexecuted finite scenario variants. No designed variant is presented as a pass without evidence.

The canonical evidence artifact is `CAOS_Quality_Validation_Tracker.xlsx`. It contains the feature, role, route, workflow, API, configuration, control, modal/dialog, state, acceptance-criteria, edge-case, defect, validation-run, and automation-evidence registers.

## Local production-like posture

The lane used only local, fictional, disposable data and services:

- PostgreSQL on loopback with a 300-issuer deterministic fictional baseline; browser and accessibility identities brought the current directory to 324 issuers.
- Baseline fixture: 600 fictional documents, 600 chunks, 2,400 financial metrics, and one opt-in completed CP-1 workflow owned by the fictional Model E2E analyst.
- `ENVIRONMENT=production`, HTTPS, edge-secret authentication, strict live CSP, required ClamAV protocol peer, all current rollout gates enabled, `CAOS_DEMO_SEED=false`, and document egress disabled.
- Anthropic, OpenRouter, Gemini, and OpenAI keys were explicitly blank, exercising deterministic keyless behavior with no model-provider traffic.
- No production systems, production credentials, sensitive data, or destructive database operations were used.

## Inventory and evidence

| Register | Count |
|---|---:|
| Canonical features | 636 |
| Physical frontend routes | 18 |
| Production API handlers | 167 |
| Runtime configuration options | 79 |
| Business workflows | 17 |
| Role / identity profiles | 7 |
| Source-discovered controls | 678 |
| Modal / dialog controls | 46 |
| Source-discovered UI state handles | 495 |
| Finite acceptance/edge scenario cases | 4,488 |
| Collected passing automation nodes | 3,249 |

The matrix is deliberately conservative: generated scenario variants that remain `Designed`, and cases labeled `Suite evidence`, are not presented as direct passes. The workbook contains the current generated counts. These labels preserve the distinction between executed evidence and future per-scenario automation depth.

## Shared causes and coherent fixes

1. **Artifact and environment drift.** Demo-only fixtures, stale static exports, stale live CSP hashes, inherited model keys, and fixed module counts made local results diverge from deployed behavior. The guarded scale seeder, exact-source mtime gate, live CSP hash preflight, explicit keyless environment, plan-aware assertions, and isolated immutable exports now fail closed before browser execution.
2. **Identity and quota coupling.** One analyst identity and one shared storage-state file coupled otherwise independent workflows to ownership and rate limits. The runner now uses three explicit analyst lanes and lane-specific session artifacts; accessibility state scans accept their own unique identity.
3. **Recovery controls under narrow layout.** Long Model/Report header actions clipped at phone width. Compact labels plus keyboard-operable tools-drawer fallbacks preserve every recovery/export action.
4. **Async-state semantics.** The Issuers loading container used a prohibited ARIA attribute on a generic element. It is now a named busy status region.
5. **Assertion drift from shared primitives.** Settings adopted the shared `ActionReason` contract, which correctly removes `aria-disabled` when actionable. The browser regression now tests operability and the presence/absence of the explanatory state instead of requiring a redundant literal `false` attribute.

Detailed reproduction, expected/actual behavior, severity, dependency, fix, and regression evidence for every observed issue are in the workbook's **Defects** and **Test Matrix** sheets. The architecture/rollout critic pass is recorded in `.agent-reviews/redteam.md`.

## Non-destructive clean handoff

The HTTPS QA app and disposable PostgreSQL container remain available locally for inspection. The PostgreSQL container was started with `--rm`; stopping it would destroy the QA database, so it was intentionally left running under the user's destructive-action constraint.
