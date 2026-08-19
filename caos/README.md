# CAOS — clean-slate credit workspace

CAOS is a case-centric institutional credit-analysis workspace built around the
vendored Deploy V methodology bundle. The browser receives a static Next.js
analytical workspace; FastAPI serves `/api` and the exported UI from the same
image. PostgreSQL owns records and job state in deployment, `/vault` owns
immutable content-addressed source blobs, and the worker uses the same image as
the API process.

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

## Product boundary

The eight primary destinations are Cases, Sources, Run Console, Deep-Dive, RV
Screener, Command Center, Model Builder and Report Studio. The six user-facing
pathways are Full Credit, Earnings Update, Covenant & Refinancing, Relative
Value, Distressed & Restructuring and source-bound Deep Research. Screen and
Full are the user terms; Deploy V LITE/FULL profile identities remain internal.

The official CP-MODEL workbook remains blocked until the signed Deploy V
authority resolves the CP-2B/CP-2A artifact-owner mismatch. No provisional
workbook is labelled as an official model output.
