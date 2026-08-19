# Plugin Review — `rohitg00/awesome-claude-code-toolkit`

**Date:** 2026-06-18
**Source:** https://github.com/rohitg00/awesome-claude-code-toolkit (176+ plugins, 135 agents, 35+ skills, hooks, MCPs)
**Question asked:** review every plugin and assess whether it could improve "the operating system" or beat existing tooling.

## Interpretation & method

Two readings of "the operating system": (1) the CAOS product, (2) the Claude Code
setup we use to *build* CAOS. I assess both, but the toolkit is dev tooling, so most
findings land on (2). Filters applied:

- **Stack:** CAOS is FastAPI + Next.js 15, single self-hosted Docker app. Anything for
  mobile/blockchain/game/embedded/other languages is out of scope by construction.
- **No paid services / no lock-in** ([[caos-no-paid-services]]): any plugin requiring a
  paid API or SaaS account is flagged, not adopted.
- **Already heavily tooled:** the installed skill set already covers review, security,
  a11y, testing, architecture, cloud, memory. "Better than existing" means it must beat
  a *named* skill we already have, not just exist.

This is a fit triage from the index descriptions + CAOS knowledge — **not** a code/security
audit of each plugin. Vet any plugin's source before installing (see Tier A #2).

**Bottom line:** of 176 plugins, the installed toolkit already covers the overwhelming
majority. **One clear gap to fill (cost tracking), one situational adopt (a plugin
security scanner — useful for *this* very task), the rest are redundant, off-stack, or
unproven.**

---

## Tier A — Adopt (fills a real gap, free/local)

| Plugin | Why it beats what we have | Cost/lock-in |
|---|---|---|
| **ccusage** | We have **zero** cost/token visibility today. Reads local Claude Code `.jsonl` logs, CLI, no account. Directly serves the no-paid-services discipline by making spend legible. | Local-only, OSS. Clean. |
| **Prism Scanner** | A skill/plugin/MCP **security scanner (39+ rules)** — relevant *right now* because adopting any third-party plugin from this list means running someone else's hooks. This is the gate before Tier B. | Appears local — verify license before trusting it. |

Alternatives to ccusage if it disappoints: **cc-cost** (single-file Python) or **getburnd**
(local leak-pattern CLI). Pick one, don't stack three. `ccusage` is the lowest-friction.

---

## Tier B — Consider (situational; adopt only when the trigger fires)

| Plugin | Adopt when… | Caveat |
|---|---|---|
| **codebase-graph** / **reporecall** | context misses become a pain as the codebase grows; both do **local** tree-sitter/AST indexing — no embedding API. | YAGNI today; codebase isn't large enough to justify the moving part. |
| **claude-context** | you specifically want semantic (vector) search | needs an embedding provider → cost/lock-in risk. Prefer the local AST options above. |
| **AgentLint** | before publishing/sharing CAOS as an agent-consumable repo (33 agent-compat checks) | dev-hygiene, not product. |
| **US Business Data MCP** | **product angle** — issuer/credit reference data across US state DBs | EDGAR is already the data spine; verify it's free + reliable before it touches the pipeline. |
| **logic-lens** / **Bouncer** | you want a *different* model breaking review monoculture | we already have `adversarial-reviewer` + `/code-review ultra`; Bouncer needs a Gemini key. Low marginal value. |

---

## Tier C — Already covered (don't install; you have the equivalent)

| Toolkit plugin(s) | Superseded by your installed skill |
|---|---|
| code-guardian, code-review-assistant, pr-reviewer, review-squad, great_cto, brooks-lint, double-check | `/code-review` (incl. `ultra` cloud multi-agent), `code-reviewer`, `adversarial-reviewer`, `ponytail-review` |
| a11y-audit, accessibility-checker, color-contrast, screen-reader-tester, ui-ux-suite | `a11y-audit`, `audit`, `polish` (and CAOS already did the WCAG pass) |
| test-writer, unit-test-generator, tailtest, sniff-qa, e2e-runner, mutation-tester, visual-regression | `playwright-pro` (+ suite), `senior-qa`, `tdd-guide`, `verify` |
| security-guidance, code-guardian, compliance-checker, claude-cybersecurity, data-privacy | `senior-secops`, `senior-security`, `security-pen-testing`, `cloud-security`, `ai-security`, `red-team`, `threat-detection`, `/security-review` |
| backend-architect, api-architect, code-architect, schema-designer, frontend-developer, ui-designer | `senior-architect`, `senior-backend`, `senior-frontend`, `senior-fullstack`, `frontend-design` |
| aws-helper, azure-helper, gcp-helper, k8s-helper, terraform-helper, deploy-pilot, devops-automator | `aws-solution-architect`, `azure-cloud-architect`, `gcp-cloud-architect`, `senior-devops` |
| claude-mem, cortex, knowledge-graph, claude-supermemory, axme-code, cozempic | built-in file memory (`MEMORY.md`) + `self-improving-agent` + `consolidate-memory`. supermemory/cortex add a paid/external dep for what you already have free. |
| refactor-engine, complexity-reducer, dead-code-finder, optimize, import-organizer | `simplify`, `ponytail-review`, `ponytail-audit` |
| ccpm, create-worktrees | worktrees already in the workflow ([[caos-parallel-wip-staging]]); harness `EnterWorktree` exists. |
| prompt-optimizer, ai-prompt-lab | `senior-prompt-engineer` |
| readme-generator, doc-forge, codebase-documenter, changelog-gen | `senior-frontend`/general skills cover this; low value to add. |
| smart-commit, commit-commands, changelog-writer | `/init`, plain git; not worth a plugin. |

---

## Tier D — Skip wholesale (won't touch CAOS)

- **Wrong stack/domain:** android-developer, ios-developer, flutter-mobile, react-native-dev,
  desktop-app, ESP32/debian/robotics/game/blockchain agents, all non-Python/TS language
  experts (Rust/Go/Java/Elixir/Haskell/Zig/…), media-streaming, e-commerce, healthcare,
  real-estate, voice-assistant, IoT. ~80+ entries — irrelevant to a web credit app.
- **Channels/novelty:** whatsapp/instagram/discord/slack bridges, jarvis, discoclaw,
  peon-ping, claude-sounds, notch-so-good, temporal-core, claude-time, idle-timing,
  background-timer, dna-claude-analysis, immich-photo-manager. Fun, not relevant.
- **Paid / external-dep / lock-in:** claude-supermemory, harness-evolver (LangSmith),
  cup (ClickUp), linear-helper, Bouncer (Gemini), anything requiring a vendor account —
  blocked by the no-paid-services rule unless a free tier is confirmed.
- **Big bundles — do NOT bulk-install:** `wshobson/agents` (112 agents/146 skills),
  `product-org-os` (150+ skills), `oh-my-claudecode` (19 agents/28 skills),
  `the-pragmatic-pm` (43 skills), `faf-skills` (31). These massively overlap your existing
  `senior-*` set and would bloat the skill list with near-duplicates. Cherry-pick a single
  named skill if you ever need one; never install the bundle.
- **Unproven / vague:** OraClaw, ejentum-mcp, nexus-agents, myclaude, production-grade,
  fractal, weft — interesting concepts, no evidence they beat the current setup; adopting
  them is speculative complexity.

---

## Recommendation

1. Install **ccusage** — fills the only real gap (spend visibility), zero lock-in.
2. Keep **Prism Scanner** on hand and run it against anything before you install it.
3. Everything else: **default to no.** Your installed toolkit already wins on review,
   security, a11y, testing, architecture, cloud, and memory. Adopt from Tier B only when
   the named trigger actually fires.

Skipped: per-plugin source/security audit (do it at install time, not now), and any of the
176 not individually named above — they fall into the Tier D category buckets.
