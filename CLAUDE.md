# CAOS — Agent Guide

Guidance for AI coding agents (Claude Code, Codex, and peers) working in this
repository. This is the single canonical source: `AGENTS.md` is a symlink to
`CLAUDE.md`, so the two never drift.

## Project

**CAOS — Credit Agent OS**: an institutional leveraged-finance credit analysis
platform. A Next.js 16 analyst UI with 15 destinations in five workflow groups
(Intake / Analyze / Decide / Publish / Monitor — anchored by Command Center,
Pipeline, Deep-Dive, Model Builder, Report Studio, Monitor, plus the global
Ask ⌘K launcher; `frontend/src/lib/nav.ts` is the source of truth) backed by a
FastAPI service, deployed
as a self-hosted Docker stack (Caddy → oauth2-proxy → FastAPI → Postgres). The analytical methodology is the 27-module
"Modular OS" prompt corpus under `Modular OS/`. The app lives under `caos/`
(`frontend/` Next.js, `server/` FastAPI). See [caos/README.md](caos/README.md)
and [caos/docs/](caos/docs/) for architecture and current build status.

The full design reference also lives in [.impeccable.md](.impeccable.md); the
Design Context below is kept in sync with it.

## Engine conventions

**Guard CP-1 figures with `is_finite_number` before dividing/multiplying.** Any
engine computation that divides or multiplies a CP-1-derived value (leverage, net
debt, EBITDA, coverage) must gate the input through
`engine.periods.is_finite_number(x)` first. A plain `isinstance(x, (int, float))`
check passes a `NaN` (and `bool(NaN)` is `True`), so a NaN slips past the guard
and poisons the divide — leaking `NaN` into the payload (silent wrong reads
downstream) or crashing on a zero denominator. `is_finite_number` rejects
`NaN`/`±inf` while accepting `bool`/`0`. Also guard a denominator that can reach
`0` (e.g. `ebitda * (1 - pct)` when `pct → 1`) — return `None`/degrade rather than
divide. This pattern recurs across CP-2B/2E/2F/3B/3D and the Altman score.

## Red-team decision gate

Before committing to an architecture, interface, or rollout plan, record a
critic pass in [.agent-reviews/redteam.md](.agent-reviews/redteam.md). Fix and
verify each high-impact objection, or document why the risk is accepted.

**Append a new dated section at the end; never edit an existing entry.** This file
and `skill-observations/observation-log.md` are declared `merge=union` in
`.gitattributes`, so concurrent appends from different branches merge instead of
conflicting — on 2026-07-26 all three live conflicting PRs (#219, #220, #221)
conflicted on this file and nothing else, purely because every branch appends to the
same tail. Union is line-based and structure-blind: it keeps both sides. That is
correct for appends, but if you *edit* an existing entry while another branch edits
the same one, you get a silently duplicated passage rather than a conflict asking you
to choose.

## Design Context

### Users

When trade-offs force a choice, **optimize for the buy-side credit analyst** —
the person doing the deep work in Deep-Dive, Model Builder, and Report Studio,
building a defensible credit view they can stand behind in front of an
investment committee. Secondary personas: the **PM / CIO** (scans the Command
Center for posture and "what changed") and the **Head of Research / QA** (owns
coverage health, the CP-5 QA gate, governance). All work is dense, multi-window,
numbers-heavy, and money is behind a wrong read; users are specialists who value
precision over hand-holding.

### Brand Personality

**Precise, defensible, alert.** The interface should evoke four layered feelings
at once: **calm institutional authority** (committee-ready, no noise),
**trading-desk alertness** (live state and "what changed" feel immediate),
**confident clarity** (dense complexity made legible), and **trust through
transparency** (every number one click from its source). Copy is terse,
technical, and exact — label like a desk, not a brochure. No marketing language,
no emoji in product chrome.

### Aesthetic Direction

**A refined institutional terminal — a *designed* Bloomberg, not a raw one.**
Hold the dense, dark credit-desk feel while making every pixel intentional.
Inherit the established system (do not reinvent it):

- **Dark workspace, single mode.** Surfaces ramp `--caos-bg #0a0a0f` →
  `--caos-panel #11131d` → `--caos-elevated #1d2030`; hairline borders
  `--caos-border #34384a`; text `#e6e6ef`, muted `#a1a1b5`; accent blue
  `#63a1ff`.
- **Color is signal, never decoration:** warning `#f5a524`, critical `#ef4444`,
  success `#22c55e`, idle `#3f3f46`. Categorical seniority/tranche ramp (1L teal,
  2L blue, unsec amber, sub purple, equity slate) — distinct hues, no lightness
  banding.
- **Type:** Inter (sans) + JetBrains Mono (mono); all numerics `tabular-nums`
  with aligned decimals (`.tabular`); small (9–12px) uppercase letter-spaced
  labels; the 32px uppercase `<Panel>` header is the structural unit.
- **Motion:** 160ms ease-out (`.transition-caos`); pulse only for live/running
  state; always honor `prefers-reduced-motion`.
- **Output (Report Studio)** is a deliberate counterpoint: a light "paper"
  tear-sheet (ink on cream, monospace mastheads, print-ready) — looks like a
  filed institutional document.

**Anti-references:** not a friendly consumer SaaS dashboard (oversized type,
pastel cards, illustrative art, generous empty space); not a raw unstyled
terminal dump (density must always be *organized*); no decorative gradients,
glow, or skeuomorphism.

### Accessibility & Inclusion

**WCAG 2.1 AA, colorblind-safe.** Text meets 4.5:1 contrast (3:1 for large/bold);
validate the small muted labels specifically. **Status and tranche meaning is
never carried by color alone** — pair every semantic color with a glyph, label,
or position. Honor `prefers-reduced-motion` everywhere; all interactive surfaces
(including the cross-pane Evidence Sync selection) are keyboard-operable with a
visible focus ring.

### Design Principles

1. **Density with hierarchy** — earn density with grouping and rhythm, never raw
   cramming.
2. **Color is signal, not decoration** — reserve hue for status, seniority, and
   selection.
3. **Show your work** — every conclusion stays one interaction from its evidence.
4. **Motion only for life** — animate what is genuinely live; degrade gracefully
   under reduced-motion.
5. **Committee-ready by default** — when in doubt, choose what would survive
   investment-committee scrutiny. Polish means *intentional*, not *ornamented*.

## Working Conventions

- **Parallel WIP Git Staging**: Stage explicit paths only (never use wildcard `git add -A` or `git add .` unless you are sure no user changes are present). Only stage and commit files modified by the agent, preserving the user's parallel work-in-progress.
- **Git Branch Comparisons**: For `detect_changes()` and general diffs, compare against `origin/main` as the default branch/base reference, as local `main` might be stale or shallow.
- **Land work, don't stack it.** Unmerged branches are this repo's dominant source of friction: they rot at the rate `main` moves, so a branch left open for two weeks is a guaranteed conflict, and CI red you didn't cause becomes indistinguishable from CI red you did. Run `caos/scripts/git_rot.sh` before starting new work — it prints, per open PR and local branch, how far behind `origin/main` it is and whether to merge, rebase, or close. **Cut branches from `origin/main`, never local `main`** (`git fetch origin && git switch -c <name> origin/main`), and **rebase before every push**. Prefer finishing an open branch over opening another.
- **Never leave uncommitted work in a `/tmp` or `/private/tmp` worktree.** macOS purges those paths, taking the work with them and leaving a broken worktree entry. Put throwaway worktrees under `.claude/worktrees/`, and commit before you walk away. `git_rot.sh --local` flags volatile worktrees that hold uncommitted changes.
- **Turbopack Dev Cache**: Ensure `turbopackFileSystemCacheForDev: false` remains in `next.config.js` to prevent persistent development server cache crashes and high disk write overhead.
- **Accessibility Verification**: Use the local axe-core runner `node caos/frontend/scripts/a11y-axe.mjs` for actual accessibility validation rather than relying on static regex-based audits which are prone to false positives.
- **FastAPI Server Environment**: Execute the server suite and check scripts with the project virtual environment when one exists (`caos/server/.venv` or `caos/server/.venv311`); otherwise install `caos/server/requirements.txt` + `requirements-dev.txt` into a fresh venv. Do not downgrade the FastAPI pin in `requirements.txt` (currently `0.139.*` — it clears the starlette CVE set).
- **Red "Lock — requirements.lock in sync"? Run `caos/scripts/relock.sh` and commit the lock.** Dependabot bumps `requirements.txt` but cannot regenerate a pip-compile lock, so every pip dependabot PR arrives failing that gate. The gate is correct — the prod image installs from the lock, so an unpropagated bump would ship a stale package. **The lock must be regenerated in place**: pip-compile treats the existing output file as its constraint set, so writing to a fresh path drops every pin and floats the whole transitive graph to latest instead of moving the one package that actually changed. `relock.sh --check` verifies without touching the tree.

## Skill improvement observations

Capture skill-improvement opportunities as you work: when a skill's guidance is
wrong, incomplete, or could be sharper for CAOS, record it in the observation
log (`skill-observations/observation-log.md`) as an OPEN entry tagged to that
skill.

When loading any skill, check that log for OPEN observations tagged to it.
Apply their insights to the current work, even if the skill file hasn't been
updated yet. This enables immediate application of observations before they're
permanently integrated during a later review pass.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Credit-Operating-System** (26665 symbols, 48283 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> **Availability check first:** the `.gitnexus/` index is local-only (not committed), and the GitNexus MCP server is not attached in every session — cloud/CI checkouts have neither. The MUST rules below apply **only when the GitNexus MCP tools are actually available in the session**; when they are not, fall back to careful manual review (read the symbol's callers before editing, diff against `origin/main` before committing) and note in your summary that impact analysis was unavailable.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Credit-Operating-System/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Credit-Operating-System/clusters` | All functional areas |
| `gitnexus://repo/Credit-Operating-System/processes` | All execution flows |
| `gitnexus://repo/Credit-Operating-System/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
