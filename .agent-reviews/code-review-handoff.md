# Code Review Handoff

Date: 2026-07-05
Repo: `/Users/ericguei/Claude/Projects/Credit Operating System`
Current state: `main` at `f5fae76b` (`fix: align query model availability with provider keys`), clean against `origin/main` when this note was written.

## Last Session Summary

The adversarial whole-codebase review found no blockers, but did find correctness/security concerns in Query model lanes and analyst memo sync/write paths.

Already fixed in current history:

- Query answer cache is scoped by capability/issuer, so the same question cannot reuse another issuer/walk answer.
- Query model availability now checks whether the resolved model has its provider key, not just whether any provider key exists.
- Gemini only counts when a configured `model_tier_*` points at a `gemini-*` model.
- Reviewer model fallback no longer selects an Anthropic reviewer when no Anthropic key exists.
- Analyst memo writes use exclusive file creation, avoiding same-title overwrite races.
- `sync_analyst_memos` keeps scan through destructive delete/insert under the existing lock.

Verification already run:

- Focused server checks: `42 passed`
- Full server suite: `954 passed, 3 skipped`; 7 AV tests failed only because the sandbox blocks localhost socket bind.
- AV scanner tests outside sandbox: `8 passed`
- `py_compile` passed with `PYTHONPYCACHEPREFIX=/private/tmp/caos-pycache`

## Resume Review Here

1. Re-check current state before trusting this file:
   - `git status --short --branch`
   - `git log -3 --oneline --decorate`
   - `git show --stat --oneline HEAD`

2. Continue unresolved adversarial review items:
   - `QueryAcceptedLink` is unique only by issuer pair. Decide whether links are intentionally pair-level or should include `capability_id`; if changing, inspect `caos/server/database.py`, `caos/server/routes/query.py`, and migration `0020_query_accepted_links.py`.
   - Evidence APIs expose chunk/module/claim/finding payloads by id to any authenticated analyst. This is acceptable only under the current single-team assumption; becomes a security finding for multi-tenant or MNPI entitlements.
   - GitNexus taint layer was absent during review. For deeper security review, run/index with PDG and rerun `explain`.
   - CSP still allows inline script/style in `caos/server/main.py`; verify that remains required by the static export path before accepting it as residual risk.
   - Frontend lint had one pre-existing warning in `caos/frontend/src/app/issuers/page.tsx` around an unnecessary `SORTABLE` dependency.

3. Before editing any symbol, follow `AGENTS.md`:
   - Run GitNexus `impact` on the target symbol.
   - Warn before touching HIGH/CRITICAL blast-radius paths.
   - Run `detect_changes({scope: "compare", base_ref: "main"})` before any commit.

## Useful Commands

Server:

```bash
/Users/ericguei/Claude/Projects/Credit\ Operating\ System/caos/server/.venv/bin/python -m pytest caos/tests/server -q
/Users/ericguei/Claude/Projects/Credit\ Operating\ System/caos/server/.venv/bin/python -m pytest caos/tests/server/test_avscan.py -q
```

Frontend:

```bash
npm run lint
npm run test -- --run
npx tsc --noEmit
```

Run frontend commands from `caos/frontend`.
