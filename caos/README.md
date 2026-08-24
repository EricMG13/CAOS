# CAOS — clean-slate credit workspace

CAOS is a case-centric institutional credit-analysis workspace built around the
vendored Deploy V methodology bundle. The browser receives a static Next.js
analytical workspace; FastAPI serves `/api` and the exported UI from the same
image. PostgreSQL owns records and job state in deployment, `/vault` owns
immutable content-addressed source blobs and model exports, and the Dockerfile
builds separate API and worker targets from one shared Python runtime. Only the
worker target contains LibreOffice.

## Local boot

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r server/requirements-dev.txt
PYTHONPATH=server uvicorn run:app --reload --port 8000
```

The development adapter uses a memory store so contract tests and a fresh boot
do not require a local database. Production refuses to boot without a
PostgreSQL URL, real edge/session secrets, and the production ClamAV endpoint.
Run `python server/migrate.py` against the deployment database before starting
the API and worker.

## Deep Research rollout

Agent-backed Deep Research is disabled by default (`CPDR_AGENT_ENABLED=false`).
The case and subject pilot allowlists also default to empty, which denies every
run even when the feature flag is enabled. Eligibility is an exact match on
either the case ID in `CPDR_PILOT_CASE_IDS` or the authenticated subject in
`CPDR_PILOT_SUBJECTS`.

To enable a pilot without rebuilding the image, set one or both allowlists,
provide `ANTHROPIC_API_KEY` to the worker environment, then set
`CPDR_AGENT_ENABLED=true` and recreate the app and worker services. The API
receives the flag, allowlists and `ANTHROPIC_MODEL` (default
`claude-sonnet-4-6`), but never the provider key; only the worker receives that
secret. A disabled deployment boots and remains healthy with an empty key. If
an otherwise eligible Deep Research run reaches a worker without the key, that
run fails explicitly with `AGENT_PROVIDER_UNAVAILABLE`; other pathways are not
affected.

To pause or roll back the pilot, set `CPDR_AGENT_ENABLED=false` and recreate the
app and worker services. Confirm `/api/health` is healthy and that Deep Research
is reported unavailable before removing the worker key or changing allowlists.

## Product boundary

The eight primary destinations are Cases, Sources, Run Console, Deep-Dive, RV
Screener, Command Center, Model Builder and Report Studio. The six user-facing
pathways are Full Credit, Earnings Update, Covenant & Refinancing, Relative
Value, Distressed & Restructuring and source-bound Deep Research. Screen and
Full are the user terms; Deploy V LITE/FULL profile identities remain internal.

Model Builder accepts only canonical Full Credit snapshots with the required
CP-1/CP-2 handoffs and a validated CP-2B projection. The worker calculates and
persists the vendored Python worksheet model first; the browser renders its
Credit Snapshot, Model, and KPIs tabs without LibreOffice. XLSX export is an
independent optional worker job, so an export failure does not demote a ready
in-app model. Reports bind to the immutable model ID, accepted snapshot, input
fingerprint, and payload hash, with an export hash added only when one exists.
