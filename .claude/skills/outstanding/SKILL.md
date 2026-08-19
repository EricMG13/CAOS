---
name: outstanding
description: Report what's actually outstanding in CAOS — reconciled against the live code, not the stale tracker. Use when the user asks "what is outstanding", "what's left", "are there any outstanding items", "list outstanding tests", "Phase-1 readiness", "resolve all outstanding issues", or "continue where you left off".
user-invokable: true
---

# outstanding

The docs lie. `caos/docs/AUDIT.md` and the issue list **trail the shipped
engine** — items marked open are often already fixed in code. So never report
status from the tracker alone: grep the code first.

## Steps

1. **Read the tracker, treat as suspect:**
   - `caos/docs/AUDIT.md` (findings)
   - `caos/docs/qa/FEATURE_TRACKER.csv` (canonical 355-row per-feature status)
2. **Reconcile each "open" line against code** — grep the engine/UI for the
   symptom or fix before counting it open. Drop anything already shipped.
3. **Run the tests** for ground truth on regressions:
   `env -u ANTHROPIC_API_KEY -u GEMINI_API_KEY -u OPENROUTER_API_KEY
   caos/server/.venv311/bin/python -m pytest caos/tests/server
   caos/tests/stress caos/tests/cohort -q` (prod-parity py3.11 venv —
   never the retired py3.9 `.venv`). Baseline is ~1393 pass / 2 skip
   (2026-07-11; the 2 skips are Postgres-only tests without Docker).
4. **Report** three buckets, terse:
   - **Genuinely open** (confirmed in code) — with `file:line`.
   - **Tracker says open but already fixed** — note the stale line to clean up.
   - **Test status** — pass/fail/skip counts + any new failures.

## Scope

- Phase-1 = leveraged loans only; DM is the canonical spread metric. Don't flag
  Phase-2 / Bloomberg items as Phase-1 gaps.
- This is a **read + report** skill. Don't start fixing unless the user said
  "resolve" / "fix"; if they did, list first, then fix in priority order.
