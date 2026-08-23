# Task 1 report

## Commands and results

All commands were run from the requested locations.

| Command | Result |
| --- | --- |
| `cd caos/frontend && npm run lint -- --max-warnings=0` | PASS |
| `cd caos/frontend && npx tsc --noEmit` | PASS |
| `cd caos/frontend && npm run build` | PASS; Next.js generated the static routes |
| `cd caos && mkdir -p server/static && cp -R frontend/out/. server/static/.` | PASS |
| `cd caos && PYTHONPATH=server .venv/bin/python server/run.py` | BLOCKED: `.venv/bin/python` does not exist at the requested location |
| `cd caos/frontend &&` baseline Playwright measurement | NOT RUN: no application server could be launched; port 8000 was unavailable |
| `cd caos/frontend && npm run lint -- --max-warnings=0` after edit | PASS |
| `cd caos/frontend && node --check scripts/workbench-smoke.mjs` | PASS |
| `cd caos/frontend && npm run test:workbench` | EXPECTED RED path unavailable: Playwright could not connect to `127.0.0.1:8000` before the first workflow assertion |
| `git diff --cached --check` | PASS |
| GitNexus `detect_changes({scope: "staged"})` | PASS; 2 changed files, low risk, 0 changed symbols/processes |

The requested baseline JSON timing was not captured because the prescribed server launch is broken in this checkout: `caos/server/.venv/bin/python` resolves through a missing Python 3.14 target, and the system interpreter has no FastAPI installation.

## Contract

Added the exact `test:workbench` package script and the single-fixture Playwright browser journey from the brief. The expected application-level RED assertion is the missing `navigation[name="Workflows"]`; it could not be reached until the server dependency/environment issue is resolved.

## Files changed

- `caos/frontend/package.json`
- `caos/frontend/scripts/workbench-smoke.mjs`

Unrelated dirty-worktree files were not staged or modified by this task.

## Self-review

Confidence review covered:

1. Fixture/API sequencing — verified each request uses the IDs returned by the prior response and each required status is asserted.
2. Run polling — verified the loop has a finite 60-attempt bound and asserts terminal success before acceptance.
3. Browser cleanup — verified browser/context and API disposal are protected by `try/finally` for the browser journey.
4. Accessibility and responsive checks — verified the contract checks named roles, keyboard focus restoration, linked evidence state, console/page errors, and 720px horizontal overflow.
5. Scope — verified the staged diff contains only the two Task 1-owned files.

Rewrite tournament: skipped because this is a test-only script/config change, explicitly excluded by the skill's materiality rule.

## Commit

`b40f0ee test(frontend): define analyst workbench contract`

## Concerns

- The server virtualenv must be repaired or recreated before baseline timing and the intended first missing-workflow RED assertion can be observed.
- No timing JSON is available for Task 6 comparison until that environment is fixed.

## Follow-up environment recovery and live RED evidence

The interpreter inspection showed that `/opt/homebrew/bin/python3` is Python
3.14.6 and the `caos/server/.venv/bin/python3.14` symlink resolves to an
executable Python 3.14.6 target. The original launch failure was the brief's
relative `.venv/bin/python` path from `caos/`; this checkout has the venv under
`caos/server/.venv`, but it had no installed FastAPI packages. No repository
venv or tracked source was changed. A disposable venv was created at
`/private/tmp/caos-task1-venv` and populated from the existing
`caos/server/requirements.txt`.

Commands and results:

```text
ls -l /opt/homebrew/bin/python3 /opt/homebrew/opt/python@3.14/bin/python3.14 caos/server/.venv/bin/python caos/server/.venv/bin/python3 caos/server/.venv/bin/python3.14
Python 3.14.6
ModuleNotFoundError: No module named 'fastapi'

/opt/homebrew/bin/python3 -m venv /private/tmp/caos-task1-venv
/private/tmp/caos-task1-venv/bin/python -m pip install -r server/requirements.txt
Successfully installed ... fastapi-0.139.2 ... uvicorn-0.52.4 ...

PYTHONPATH=server /private/tmp/caos-task1-venv/bin/python -m uvicorn caos.http:app --host 127.0.0.1 --port 8010
INFO: Uvicorn running on http://127.0.0.1:8010
```

Live baseline command:

```text
node --input-type=module -e '... page.goto("http://127.0.0.1:8010/cases/", {waitUntil:"networkidle"}) ...'
{"domContentLoaded":58.60000002384186,"firstContentfulPaint":68,"caseRequests":1}
```

Live contract command:

```text
CAOS_URL=http://127.0.0.1:8010 npm run test:workbench
{"timing":{"domContentLoaded":11.199999928474426,"firstContentfulPaint":56},"caseRequests":1}
locator.waitFor: Timeout 30000ms exceeded
waiting for getByRole('navigation', { name: 'Workflows' }).getByRole('link', { name: 'Overview', exact: true }) to be visible
at scripts/workbench-smoke.mjs:68:111
```

This is the intended RED: fixture creation, run acceptance, app navigation,
timing capture, and request-count instrumentation all completed; the current
shell fails at the first missing `Workflows` navigation assertion.
