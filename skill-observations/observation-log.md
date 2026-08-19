# Skill Observation Log

Running log of skill-improvement observations. Each entry is tagged to a skill
and carries a status of **OPEN** (not yet integrated into the skill file) or
**CLOSED** (integrated / no longer applicable). When loading a skill, scan this
log for OPEN entries tagged to it and apply their insight to the current work,
even before the skill file itself is updated.

Format:

```
## <ISO date> — <skill-name> — [OPEN|CLOSED]
<observation and the change it implies>
```

---

## 2026-07-08 — meta (skills catalog) — CLOSED

Skills audit applied (see `.agent-reviews/skills-audit.md`). `.agents/skills/`
trimmed from 53 → 28: removed two byte-identical `gitnexus-*` copies, five
vendored skills targeting stacks CAOS does not have (Kotlin/Spring, .NET/Rider,
Compose Desktop, Go/skillshare) plus the unused OpenRouter SDK skill, the 15
one-verb design skills subsumed by the `impeccable` umbrella (+ the one-time
`teach-impeccable`), and the regex-based `a11y-audit` (superseded by the
mandated axe-core runner). Retained the security / code-review / duplicate-detection
clusters pending a routing decision — see the audit report §5.

## 2026-07-10 — commit — OPEN

Hard rule 3 hardcodes the trailer `Co-Authored-By: Claude Opus 4.8`, but the
harness now mandates the current model's trailer (`Claude Fable 5` this
session). Stale constant misattributes authorship whenever the model changes.
Change the rule to "trailer names the current model, per the harness git
guidance" instead of a pinned model string.

## 2026-07-13 — playwright-pro — OPEN

Browser fixture guidance should require an explicit no-fallthrough check for
local API interception. Playwright glob patterns that cover a query-string form
can miss the same Axios request when it has no query delimiter, silently reading
a developer's live database and making acceptance runs non-deterministic. Define
both exact and filtered request shapes (or use a URL predicate), then assert the
fixture identity/source before treating route behavior as verified.

## 2026-07-15 — code-reviewer — OPEN

The bundled whole-tree quality scanner recursively traverses in-repo virtual
environments and generated outputs: its CAOS server pass analyzed 11,286 files
until `.venv` and `.venv311` were filtered manually, producing misleading
language totals and findings. Add configurable exclude paths with safe defaults
for virtualenvs, dependency trees, build artifacts, caches, and generated files;
also label the PR analyzer explicitly as diff-only so it is not mistaken for
whole-codebase coverage.

## 2026-07-15 — turbopack — OPEN

The Next.js 16.2 guidance contains two stale diagnostics/fallback details. The
supported webpack opt-out is the `--webpack` flag on `next dev` / `next build`,
not a `bundler: "webpack"` `NextConfig` key. With
`NEXT_TURBOPACK_TRACING=1`, current Next writes the dev trace to
`.next/dev/trace-turbopack`, not a root `trace.json`. Update both examples and
prefer the documented `next experimental-analyze --output` CLI for reusable
bundle-analysis artifacts.

## 2026-07-16 — outstanding — CLOSED

The prescribed server command targets `caos/server`, which contains application
code but no pytest files and therefore exits 5 after collecting zero tests. It
also selects the Python 3.9 `.venv`, which cannot collect the current Python
3.10+ syntax and FastAPI dependency set. The server suite now lives under
`caos/tests/server`; update the command to `env -u ANTHROPIC_API_KEY
caos/server/.venv311/bin/python -m pytest caos/tests/server` and refresh the
obsolete ~317-pass baseline.

Integrated into `.agents/skills/outstanding/SKILL.md` on 2026-07-16: the skill
now targets `.venv311`, the real `caos/tests/server` suite, and the current
355-story tracker / ~1910-pass baseline.

## 2026-07-16 — gitnexus-exploring — OPEN

A local `node .gitnexus/run.cjs analyze` followed by an explicit
`--repair-fts` reported success, but the active MCP `query` endpoint still
returned an empty result with “FTS indexes are missing.” Add troubleshooting
for a stale MCP/server-side index handle (including restart/cache/branch-index
checks) after repair succeeds; the current guidance stops at reindexing and can
leave semantic exploration silently unavailable even while symbol
context/impact continues to work.

## 2026-07-17 — a11y-audit — OPEN

The ARIA reference omits the grid pattern entirely: required `row` →
`gridcell`/`rowheader` ownership, one roving row tab stop, vertical-arrow focus,
Enter activation, nested-control event isolation, and virtualized
`aria-rowcount`/`aria-rowindex`. During the CAOS grid pass, a presentational
wrapper around a stretched link still exposed the link as an illegal direct
child of `role="row"`; only the real axe runner caught it. Add an ARIA-grid
section with these ownership/keyboard/virtualization rules and require a
rendered axe verification rather than treating static markup review as enough.

## 2026-07-18 — audit — OPEN

The audit guidance needs an explicit post-gate visual and capability pass for
narrow interfaces. CAOS's document-overflow/clipped-control matrix passed every
case while fixed-height panel headers visibly overlapped their tab lists, and a
primary workflow replaced all authoring/evidence/QA/export capabilities with a
read-only summary below its desktop breakpoint. Require representative
screenshots, real coarse-pointer target measurements, and a desktop-vs-narrow
capability inventory; structural overflow and axe results alone cannot verify
responsive adaptation.

## 2026-07-18 — debugging-code — OPEN

The debugger-backend fallback link is broken: `SKILL.md` routes failed adapters
to `references/installing-debuggers.md`, but the installed skill contains only
`reference/tools.md`. Add the missing installation/troubleshooting reference or
correct the link, and document that macOS `debugpy --pid` injection can close at
initialization even when `debugpy` is installed; launching the program under DAP
is the reliable fallback when attach returns `waiting for initialized: EOF`.

## 2026-07-18 — a11y-audit — OPEN

The Quick Start and tools reference are out of sync with the bundled scripts:
`a11y_scanner.py` accepts `--format text|json` rather than `table|csv`, while
`contrast_checker.py` accepts `--batch CSS_FILE` rather than `--file FILE` and
uses `--suggest COLOR` with different semantics. Update the documented commands
from the scripts' live `--help` contract, and add a self-check so the Scan phase
does not fail before reaching the rendered axe gate.

## 2026-07-18 — a11y-audit — OPEN

The bundled regex scanner treats reusable components, tests, and generated audit
artifacts as standalone pages, then reports page-landmark and unlabeled-control
faults without resolving React component props or implicit labels. A whole-CAOS
scan produced 1,169 mostly non-actionable findings while the rendered axe matrix
was clean. Add include/exclude globs, distinguish route documents from component
fragments, and either resolve common JSX label patterns or classify these rules
as advisory so the loop converges on browser-confirmed faults.

## 2026-07-19 — zeroize-audit — OPEN

The installed skill bundle contains only `SKILL.md`; all referenced schemas,
workflows, prompts, compiler helpers, MCP helpers, and the mandatory PoC
generator are absent, so its documented pipeline cannot pass preflight. Package
the referenced assets with the skill and add an explicit `not_applicable`
outcome for repositories with no tracked C/C++/Rust source or valid
`compile_commands.json`/`Cargo.toml`, distinct from a zero-finding clean audit.

## 2026-07-19 — senior-qa — OPEN

The skill covers unit, integration, E2E, and coverage workflows but has no
stress/load protocol: it omits isolated-target safeguards, staged concurrency
ramps, service-level failure oracles, expected-backpressure classification,
post-load recovery checks, and mandatory reproduction of the first fault. Add a
load-testing section that distinguishes HTTP correctness from latency collapse
and requires one normal-user probe during saturation; without it, a Locust run
can report zero failures while analyst reads exceed their latency budget by an
order of magnitude.

## 2026-07-19 — spreadsheets — OPEN

The spreadsheet verification workflow should cap preview ranges for long sheets
and add an explicit tail/recent-record preview when recency matters. Rendering a
full multi-hundred-row CAOS defect ledger exceeded the renderer's maximum image
height even though workbook import and formula inspection succeeded. Document a
bounded head-plus-tail pattern so visual QA remains deterministic without
silently omitting the newest validation and defect records.

## 2026-07-20 — fallow — OPEN

The skill requires Fallow but offers only global install or `npx` when the CLI
is absent. In a managed pre-deployment review, the one-off `npx` path was
correctly rejected because it would download and execute third-party package
code outside the sandbox, while no MCP tool or vendored binary was available.
Add a no-download fallback that composes repository-native entry-point tracing,
direct import/re-export checks, framework dynamic-load review, and test/runtime
evidence; distinguish this lower-confidence disposition from a completed
Fallow scan instead of implying the workflow is blocked or inviting policy
circumvention.

## 2026-07-20 — deployments-cicd — OPEN

The generically named deployment skill is entirely Vercel-specific, including
its commands, environment variables, promotion model, and troubleshooting
matrix. It provides no routing or safe fallback for a self-hosted Docker/
Compose deployment such as CAOS. Add a platform-detection preflight and a
Docker path covering deny-by-default build contexts, immutable image digests,
in-image/runtime-user probes, SBOM and vulnerability gates, Compose validation,
promotion by exact digest, rollback, and post-start health/log inspection;
otherwise the skill name overpromises broader CI/CD applicability.

## 2026-07-22 — refresh-preview — OPEN

The skill correctly requires a fixed QA `SESSION_SECRET`, but its launch guidance
does not account for the current `require_sane_environment` guard: a custom
non-default secret under `ENVIRONMENT=development` now fails closed as a
production-secret/dev-identity contradiction. Document the valid development
choice (`dev-insecure-session-secret`, which is still fixed across restarts), or
provide the complete non-development secret set when production-parity identity
is intended. Also warn that an existing `caos_qa.db` can be migration-drifted;
preserve it and use a fresh isolated QA database rather than deleting or stamping
the schema during a preview refresh.

## 2026-07-23 — skill-installer — OPEN

The skill covers curated and GitHub-backed installation but not migration from
an existing local skill catalog such as `~/.claude/skills`. Add a local-source
workflow that validates frontmatter, adapts harness-specific instruction-file
references, refuses unresolved destination collisions, preserves disabled-skill
state in an ignored but recoverable directory, backs up global instructions,
and notes that newly installed Codex skills become discoverable on the next
turn.
