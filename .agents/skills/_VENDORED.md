# Vendored third-party skills

Skills copied in from upstream repos (not authored here). Pinned to the commit
each was fetched at on 2026-07-04. Re-sync = re-copy from the same upstream path.

## Per-agent CAOS mirrors (authored here, not vendored)

`commit`, `refresh-preview`, `outstanding`, and `impeccable` in this tree are
**Codex/GPT-targeted mirrors** of the canonical `.claude/skills/` versions
(same skill, `s/Claude/Codex/`, `s/Claude/GPT/`, `.claude`→`.agents` paths).
This duplication is intentional so each agent gets its own name/paths. Keep the
shared body in sync by hand when editing either copy — the only intended deltas
are agent name and skill path. (The `.claude/` copy is canonical for design
guidance; port improvements there first, then mirror.)

## Skills-audit removals (2026-07-08)

Removed per `.agent-reviews/skills-audit.md` (recoverable via git history):
byte-identical `gitnexus-debugging`/`gitnexus-impact-analysis` copies (canonical
set lives at `.claude/skills/gitnexus/`); no-CAOS-surface skills
(`error-model-validation-architect` Kotlin/Spring, `debugging-code` .NET/Rider,
`compose-ui-test-server` Compose Desktop, `implement-feature`/`codebase-audit`
Go/skillshare, `openrouter-typescript-sdk`); the 15 one-verb design skills +
`teach-impeccable` (all subsumed by the `impeccable` umbrella's sub-commands);
and `a11y-audit` (regex-based, superseded by the mandated `a11y-axe.mjs` axe-core
runner). None of these were listed in the vendored tables below.
Also fixed `senior-security`: its routing table pointed at 8 sibling security
skills that were never vendored — added an "Installed in CAOS" caveat naming the
only two present (`adversarial-reviewer`, `code-reviewer`).

**Kept after review (2026-07-08):** `security-best-practices` was briefly removed
as redundant with `owasp-security`, then restored — the two are complementary,
not duplicative: `owasp-security` owns standards + the LLM/Agentic-AI surface,
while `security-best-practices` ships **framework-exact** hardening refs that
match the CAOS stack directly (`python-fastapi-web-server-security.md`,
`javascript-typescript-nextjs-web-server-security.md`,
`javascript-typescript-react-web-frontend-security.md`). Now documented in the
table below.

| Skill dir | Upstream | Commit | License | Notes |
|-----------|----------|--------|---------|-------|
| `finding-duplicate-functions` | [obra/superpowers-lab](https://github.com/obra/superpowers-lab) `/skills/finding-duplicate-functions` | `51111f7` | MIT © Jesse Vincent | Needs `rg`+`jq`. **Extractor is TS/JS-only** — does not scan `caos/server/` Python without a forked extractor. |
| `debug-skill` | [AlmogBaku/debug-skill](https://github.com/AlmogBaku/debug-skill) `/skills/debugging-code` | `26ef325` | MIT © Almog Baku | Renamed from `debugging-code` to avoid collision with the existing JetBrains skill of that name. Drives the `dap` Go binary (install separately: `go install github.com/AlmogBaku/debug-skill/cmd/dap@latest`) + `debugpy` for Python. `install-dap.sh` fetches an unsigned prebuilt binary — prefer `go install`. |
| `constant-time-analysis` | [trailofbits/skills](https://github.com/trailofbits/skills) `/plugins/constant-time-analysis` | `cfe5d7b` | CC-BY-SA-4.0 © Trail of Bits | `ct_analyzer/` is pure-stdlib Python (zero third-party deps per `uv.lock`); run via `uv run {baseDir}/ct_analyzer/analyzer.py`. Covers Python `compare_digest`. Test fixtures trimmed. |
| `semgrep-rule-creator` | [trailofbits/skills](https://github.com/trailofbits/skills) `/plugins/semgrep-rule-creator` | `cfe5d7b` | CC-BY-SA-4.0 © Trail of Bits | Free (Semgrep OSS). Fetches ~7 Semgrep docs from raw.githubusercontent.com on invocation. |
| `variant-analysis` | [trailofbits/skills](https://github.com/trailofbits/skills) `/plugins/variant-analysis` | `cfe5d7b` | CC-BY-SA-4.0 © Trail of Bits | Inert guidance + CodeQL/Semgrep query templates (incl. `python.yaml`). Degrades to free Semgrep/ripgrep. |
| `sarif-parsing` | [trailofbits/skills](https://github.com/trailofbits/skills) `/plugins/static-analysis/skills/sarif-parsing` | `cfe5d7b` | CC-BY-SA-4.0 © Trail of Bits | Consumes SARIF scan output. `sarif_helpers.py` = pure stdlib. |

## Deliberately NOT vendored from `trailofbits/skills`
- **`static-analysis/codeql`** — CodeQL requires paid GitHub Advanced Security on private repos → violates the project no-paid-services gate. Re-add if GHAS is acquired.
- **`static-analysis/semgrep`** (standalone scanner) — redundant with `semgrep-rule-creator` + `sarif-parsing` for the free Semgrep loop.

CC-BY-SA-4.0 is a share-alike license: modifications to the ToB skill files distributed externally must be shared under the same terms. Fine for internal use; note before publishing derivatives.

## Tier-2 additions (2026-07-04, per adopt/trial verdicts)

| Skill dir | Upstream | Commit | License | Notes |
|-----------|----------|--------|---------|-------|
| `owasp-security` | [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) `/.claude/skills/owasp-security` | `f5dfa3d` | MIT © Agam More | ADOPT. Pure markdown, zero exec/network. OWASP Top 10:2025 + ASVS 5.0 + LLM/Agentic-AI 2025-26; Python + JS/TS language refs. |
| `statistical-analysis` | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) `/skills/statistical-analysis` | HEAD (2026-07-04) | MIT | TRIAL, **guidance-mode only**. 1 of 149 skills cherry-picked. `scripts/assumption_checks.py` needs scipy/statsmodels — do NOT wire into the engine; RV/percentile money-math stays hand-written under CAOS NaN discipline. |
| `security-best-practices` | [openai/skills](https://github.com/openai/skills/tree/main/skills/.curated/security-best-practices) | curated (2026-07) | see `LICENSE.txt` | KEEP. Pure markdown, zero exec/network. Framework-exact secure-by-default refs; the FastAPI + Next.js + React ones match the CAOS stack directly. Complements `owasp-security` (standards + LLM/Agentic); trigger only on explicit security-review requests for py/js/ts. |

Also vendored: `caos/server/vendor/sanitize.py` (see that dir's SOURCE.md).

**Trial CLIs (run via npx, not vendored; audit-first, not yet CI-wired):**
- `ctxlint` — `npx -y @yawlabs/ctxlint@latest .` — bundle audited (fetch()=lru-cache, spawn/child_process only in LSP/MCP modes, no egress in default lint). First run: real hygiene value (AGENTS.md↔CLAUDE.md 92% overlap, per-session token bloat, undocumented `CLAUDE_API_KEY`). BUT its "dead hook / dead permissions.allow path" errors are FALSE POSITIVES — it cannot resolve `$CLAUDE_PROJECT_DIR` or relative paths (block-dangerous-git.sh exists + is wired). **Do NOT run `--fix`.** ~7★, keep off CI.
- `agnix` — `npx --yes agnix validate <paths>` — 320★ Rust, MIT/Apache. First run = high volume, mostly stylistic phrasing opinions on hand-crafted docs. Secondary; adopt to CI only if a triaged pass finds real schema errors.

**HELD, not installed:** `presence` (sara-star-quant, 2★) — audited clean (Apache-2.0, stdlib, no-network base install, host py3.14 OK) but its `install.sh` edits GLOBAL `~/.claude/settings.json` (holds the rtk hook) + symlinks `~/.claude/plugins/`, activating a Stop hook across all projects. Awaiting explicit go-ahead on the global scope before install (warn-only mode).
