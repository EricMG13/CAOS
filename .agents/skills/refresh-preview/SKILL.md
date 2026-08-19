---
name: refresh-preview
description: Unwedge and reload the CAOS preview when the user can't see their latest changes, then prove the change with a screenshot. Use when the user says "update preview", "preview is stale", "I can't see the latest updates", "I can't see the toggle/change", "take a screenshot", "preview crashed", or "preview needs refresh".
user-invokable: true
---

# refresh-preview

Recurring pain: after rapid multi-edit churn, the QA dev bundle **wedges** —
every route sticks at the RequireAuth `Loading…` spinner even though the API
returns 200. A plain reload does **not** fix it. This is a known HMR wedge, not
a code bug.

## The fix (in order — stop at the first that works)

1. **Reload first** (cheap): `preview_eval` → `window.location.reload()`. If HMR
   already applied, you're done — skip to Prove.
2. **If still stale or stuck at `Loading…`: restart the frontend.** This clears
   the wedge:
   - `preview_stop`
   - `preview_start qa-frontend`  (config from `.Codex/launch.json`; QA frontend
     is :3010, QA backend :8010)
   - then reload.

## Prove it (never ask the user to check manually)

3. `preview_console_logs` / `preview_network` — confirm no errors, API 200s.
4. `preview_snapshot` — confirm the new content/structure is present.
5. `preview_screenshot` — send the visual proof to the user.

If the user named a specific element ("the toggle"), assert it appears in the
snapshot before screenshotting.

## Notes

- Use a **fixed `SESSION_SECRET`** for the QA backend — otherwise a backend
  restart invalidates the cookie and forces a re-login mid-check.
- QA stack is isolated (:8010 + caos_qa.db, :3010) so it won't touch the user's
  own :8000/caos.db session.
