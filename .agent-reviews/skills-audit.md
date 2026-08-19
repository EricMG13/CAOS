# Skills Audit — CAOS

_Audit date: 2026-07-08. Scope: all `SKILL.md` under `.claude/skills/` (10) and
`.agents/skills/` (53) = 63 skill files. Method: frontmatter + body review,
cross-tree diffing, stack-presence checks against the live `caos/` code
(118 Python files, 223 TS/TSX files; **0** Kotlin/.NET/Go/Compose files)._

CAOS is a **Next.js 15 (TS/TSX) + FastAPI (Python) + Postgres** stack. That is
the yardstick used throughout: a skill that only fires on a stack CAOS does not
have is, for this repo, dead weight regardless of its intrinsic quality.

---

## Applied — 2026-07-08

This audit was **applied** to the catalog. `.agents/skills/` went from **53 → 28**
skills. Summary of actions taken (all recoverable via git history):

- **§1 Fixed broken refs** — created `skill-observations/observation-log.md`;
  rewrote the `CLAUDE.md` "Task Observer" section to drop the mandate to invoke a
  non-existent `task-observer` skill (now an observation-log workflow that
  actually resolves).
- **§2.1 impeccable** — ported the general anti-patterns (ghost-card
  border+shadow, over-rounded cards, sketchy-SVG, stripe gradients) into the
  canonical `.claude/` copy's Absolute bans. _Note: the raw cross-tree diff
  overstated the gap — the `.claude/` copy already integrated the typographic
  ceiling (letter-spacing floor ≥ -0.04em) under General rules > Typography; only
  the anti-patterns were genuinely missing._
- **§2.2** — documented the intentional per-agent (Codex/GPT) mirrors in
  `_VENDORED.md`.
- **§2.3 + §3 + §4 + one of §5** — deleted 25 skill directories: the 2 identical
  `gitnexus-*` copies, 6 no-CAOS-surface skills, the 15 design verbs +
  `teach-impeccable`, and `a11y-audit`.
- **§5 — resolved (second pass).**
  - `a11y-audit` deleted (regex-based, superseded by the mandated axe runner).
  - `security-best-practices` — briefly deleted as redundant with
    `owasp-security`, then **restored on review**: the two are complementary, not
    duplicative. `owasp-security` owns standards + the LLM/Agentic surface;
    `security-best-practices` ships framework-exact hardening refs matching the
    CAOS stack (FastAPI + Next.js + React). Both kept; now documented in
    `_VENDORED.md`.
  - `code-reviewer` **kept** — one of only **two** live routing targets the
    `senior-security` hub still has (see finding below); deleting it would further
    gut an already-thin router.
  - `finding-duplicate-functions` **kept** — distinct semantic-dup method from
    `fallow`; both retained (fallow for breadth, this for targeted dup hunts).
  - **New finding — `senior-security` routes to 8 absent siblings.** Its "read
    this first" routing table dispatches to `security-pen-testing`,
    `incident-response`, `incident-commander`, `senior-secops`, `cloud-security`,
    `threat-detection`, `red-team`, and `ai-security` — **none vendored** here
    (only `adversarial-reviewer` + `code-reviewer` exist). Added an "Installed in
    CAOS" caveat so agents don't chase missing skills.

  `.agents/skills/` final count: **53 → 28** (after `security-best-practices`
  was restored).

---

## TL;DR — recommendation counts

| Verdict | Count | Meaning |
|---------|-------|---------|
| **Delete** | 5 | No CAOS surface, or exact redundant copy |
| **Consolidate / demote** | ~17 | Real capability, but subsumed by an umbrella skill |
| **Fix (broken reference / drift)** | 4 | Referenced-but-missing, or diverged copies |
| **Keep as-is** | remainder | Load-bearing or genuinely distinct |

The single biggest issue is **catalog bloat**: 15 one-verb design skills duplicate
capabilities the `impeccable` umbrella already advertises, and a second full skill
tree (`.agents/`) shadow-duplicates the canonical `.claude/` skills. Both inflate
the per-session skill menu (token cost + selection ambiguity) with little marginal
capability.

---

## 1. Broken references — highest priority (correctness, not taste)

These are defects: the project's own canonical guide points at skills/paths that
do not exist. They mislead every agent that reads `CLAUDE.md`.

| # | Issue | Evidence | Fix |
|---|-------|----------|-----|
| 1.1 | **`task-observer` skill is mandated but missing.** `CLAUDE.md` → "Task Observer" section says *"invoke the task-observer skill before beginning work."* No such skill exists in either tree. | `find . -path "*task-observer*"` → empty | Either add the skill or strike the mandate from `CLAUDE.md`. A standing instruction to invoke a non-existent skill wastes a tool call and erodes trust in the rest of the guide. |
| 1.2 | **`skill-observations/observation-log.md` is referenced but missing.** `CLAUDE.md` tells agents to check it for OPEN observations tagged to each loaded skill. | `ls skill-observations/` → MISSING | Create the log (even empty with a header) or remove the instruction. As written, every skill load implies a lookup that 404s. |

## 2. Contradictory / drifted duplicates

The `.agents/` tree is a Codex-targeted mirror of the CAOS-authored `.claude/`
skills (s/Claude/Codex/, s/Claude/GPT/). That mirroring is deliberate, but two
problems fall out of it:

| # | Issue | Evidence | Fix |
|---|-------|----------|-----|
| 2.1 | **`impeccable` has content-drifted between trees.** The `.agents/` copy carries guidance the `.claude/` copy lacks: a "Display letter-spacing ≥ -0.04em" typographic ceiling and a whole **"Codex-specific defects"** block (ghost-card border+shadow, over-rounded 32px+ cards, sketchy-SVG ban, stripe-gradient ban, meta-criticism copy). The Claude-facing copy is **missing these lessons.** | `diff .claude/skills/impeccable/SKILL.md .agents/skills/impeccable/SKILL.md` | Single-source the shared *design* body and keep only the agent-name/path lines per-tree — the same discipline `CLAUDE.md`↔`AGENTS.md` already use (symlink). Otherwise every future edit must be hand-applied twice and will keep diverging. Right now Claude gets a strictly weaker `impeccable`. |
| 2.2 | **`commit` / `refresh-preview` name-collide across trees.** Both trees define `name: commit` and `name: refresh-preview`; the harness surfaces one (the `.claude` "Claude touched" variant), so the `.agents` Codex variants are **shadowed dead weight for Claude** while still live for Codex. | frontmatter `name:` identical; only Claude/Codex wording differs | Acceptable *if* the mirror is intentional and documented. Add these CAOS-authored mirrors to `_VENDORED.md` (or a sibling "per-agent mirrors" note) so the duplication is understood as intentional, not accidental drift. |
| 2.3 | **`gitnexus-debugging` + `gitnexus-impact-analysis` are byte-identical copies.** `.agents/skills/gitnexus-*` == `.claude/skills/gitnexus/gitnexus-*` exactly, and both use the same frontmatter `name`, so they hard-collide. | `diff` → IDENTICAL for both | **Delete the two `.agents/` copies.** They add zero capability and one duplicate `name` per collision. The `.claude/skills/gitnexus/` set is the canonical one (referenced by `CLAUDE.md`'s GitNexus table). |

## 3. Delete — no CAOS surface

Vendored skills whose trigger stack does not exist anywhere in `caos/`. High
quality upstream, but for **this** repo they can never fire on real code — they
only add menu noise and false-positive selection risk.

| Skill | Targets | CAOS has it? | Note |
|-------|---------|--------------|------|
| `error-model-validation-architect` | Kotlin + Spring | 0 `.kt` | Backend is FastAPI/Python. No path to relevance. |
| `debugging-code` (JetBrains Rider) | .NET/C#/F#/VB/C++/Unity/Unreal | 0 `.cs` | Also collides conceptually with the vendored `debug-skill` (DAP). |
| `compose-ui-test-server` | Compose **Desktop** (Kotlin/JVM) | 0 gradle | UI is Next.js in a browser; drive it with `playwright-pro` / `refresh-preview`. |
| `implement-feature` (skillshare) | Go + skillshare's own `targets.yaml`/oplog/handler-split TDD | 0 `.go` | Enforces conventions from a different project; actively wrong here. |
| `codebase-audit` (skillshare) | skillshare `targets.yaml`, oplog instrumentation, CLI-flag/doc cross-val | none of those artifacts exist | Its checks assume a repo layout CAOS doesn't have. |

> Also **strongly consider deleting** `openrouter-typescript-sdk` (1271 lines —
> the largest skill in the repo). CAOS runs its own analytical engine, not the
> OpenRouter SDK. Unless there is a concrete plan to route models through
> OpenRouter, it is 1.3k lines of context-bloat that can never apply.

## 4. Consolidate / demote — the design-verb sprawl

`impeccable`'s own description explicitly claims it covers *"polish, clarify,
distill, harden, optimize, adapt, colorize, extract… bolder… quieter."* Yet each
of those exists **again** as a standalone one-verb skill. This is the largest
low-marginal-value cluster in the catalog:

`adapt`, `arrange`, `audit`, `bolder`, `clarify`, `colorize`, `critique`,
`distill`, `extract`, `harden`, `normalize`, `optimize`, `polish`, `quieter`,
`typeset` — **15 skills**, each 70–270 lines, all in `impeccable`'s stated scope.

- **Overlap:** every one is a sub-mode of `impeccable` (whose `argument-hint`
  literally lists `audit|critique·bolder|colorize|…|typeset` as arguments).
- **Cost:** 15 near-synonymous entries in the skill menu invite mis-selection
  and pad every session's skill-description budget.
- **Recommendation:** keep `impeccable` as the single design umbrella; **remove
  the 15 standalone verbs** (or, if the granular slash-commands are valued,
  reduce each to a 3-line stub that forwards into `impeccable <verb>` rather than
  re-stating the full method). Do not maintain both the umbrella and 15 forks of
  its guidance — they will drift exactly as §2.1 shows `impeccable` itself already
  has.
- `teach-impeccable` is a **one-time setup** skill ("Run once to establish
  guidelines"). CAOS already has committed design context (`CLAUDE.md` Design
  Context + `.impeccable.md`). It has served its purpose — demote/remove.

## 5. Overlapping clusters — dedupe, don't necessarily delete

These have genuine distinctions but crowd the same trigger space. Pick a primary
per cluster and make the others explicitly narrower (or route to the primary).

**Security review** — `owasp-security`, `security-best-practices`,
`senior-security`, plus the `/security-review` command.
- `owasp-security` (Top-10:2025/ASVS/LLM) and `security-best-practices` (OpenAI,
  py/js/ts) overlap heavily on "review code for vuln classes." `senior-security`
  is actually a *router* (threat-modeling owner that dispatches to siblings) — it
  is the natural hub. **Recommendation:** designate `senior-security` as the
  entry point, scope `owasp-security` to "standards checklist," and drop
  `security-best-practices` **or** `owasp-security` (they answer the same
  request). Note `security-best-practices` only supports py/js/ts — same as CAOS,
  so it's the more targeted of the two if only one survives.

**Code review** — `code-reviewer`, `adversarial-reviewer`, plus `/code-review`,
`/simplify`, `/review` commands.
- `code-reviewer` (multi-language SOLID/complexity) and `adversarial-reviewer`
  (hostile-persona pass) are complementary but both compete with the built-in
  `/code-review`. **Recommendation:** keep `adversarial-reviewer` (distinct
  method), fold `code-reviewer`'s value into the `/code-review` command path, or
  scope `code-reviewer` to languages the commands don't cover.

**Accessibility** — `a11y-audit`, `web-design-guidelines`, `impeccable` (a11y
section), plus `CLAUDE.md`'s mandated `a11y-axe.mjs` runner.
- Four things claim "check accessibility." `CLAUDE.md` already says to trust the
  local **axe-core runner** over "static regex-based audits which are prone to
  false positives" — which is exactly what `a11y-audit`'s scanner is.
  **Recommendation:** make `a11y-audit` defer to / wrap the axe runner, or demote
  it; keep `web-design-guidelines` for the broader UI-guidelines pass.

**Duplicate-function detection** — `finding-duplicate-functions` is **TS/JS-only**
(per `_VENDORED.md` it "does not scan `caos/server/` Python"). `fallow` also
reports duplication for JS/TS. Overlap on the frontend; **neither covers the
Python half.** Keep one for TS/TSX, and note the Python gap explicitly.

## 6. Limited-value / conditional keeps

| Skill | Status | Note |
|-------|--------|------|
| `statistical-analysis` | **Trial, guidance-only** | 651 lines, APA/academic stats. `_VENDORED.md` explicitly says do NOT wire its scipy scripts into the engine (money-math stays hand-written under NaN discipline). Value is narrow; keep only if analysts actually request test-selection help, else drop. |
| `postgres-best-practices` | Conditional | Supabase-flavored; CAOS runs **self-hosted** Postgres. General rules transfer; Supabase-specific ones don't. Keep but treat Supabase-isms as non-applicable. |
| `constant-time-analysis` | Niche keep | Crypto timing side-channels. CAOS isn't crypto-heavy, but it's small, self-contained (stdlib), and cheap to keep for the auth/token paths. |
| `sarif-parsing`, `semgrep-rule-creator`, `variant-analysis` | Keep as a set | These form the free-Semgrep loop `_VENDORED.md` deliberately assembled (in place of paid CodeQL). Coherent; leave intact. |
| `self-improving-agent-*` (4 skills) | Keep, but verify wiring | `remember`/`review`/`promote`/`extract` assume a `MEMORY.md` auto-memory system. Confirm that system is actually installed; if not, they're inert like §1's broken refs. |

---

## Recommended action order

1. **Fix broken references (§1)** — cheapest, highest trust-impact. Either create
   `task-observer` + `skill-observations/observation-log.md`, or remove the
   mandates from `CLAUDE.md`.
2. **Delete the 2 identical `gitnexus-*` copies (§2.3)** and the **5 no-surface
   vendored skills (§3)** — pure subtraction, zero capability lost.
3. **Single-source `impeccable` (§2.1)** so Claude stops shipping the weaker copy.
4. **Collapse the 15 design verbs into `impeccable` (§4)** — the biggest bloat win.
5. **Dedupe the security / code-review / a11y clusters (§5).**
6. Re-evaluate `openrouter-typescript-sdk` and `statistical-analysis` against
   whether they'll ever fire.

Nothing in this report was auto-applied — deletions are recommendations pending
owner sign-off, since skill removal is hard to reverse and the `.agents/` tree
also serves Codex.
