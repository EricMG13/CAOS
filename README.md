# CAOS: Credit Agent OS

CAOS is a case-centric workspace for institutional leveraged-finance analysis. It binds controlled source sets to versioned runs, traceable artifacts, approvals, and frozen reports. This repository contains the clean-slate product baseline.

> Status: pre-production. Local development uses an in-memory store. Production requires PostgreSQL, durable source storage, edge authentication, and ClamAV.

## Product surface

CAOS organizes analyst work around eight destinations:

- Cases
- Sources
- Run Console
- Deep-Dive
- Relative Value (RV) Screener
- Command Center
- Model Builder
- Report Studio

Analysts can run six pathways at Screen or Full depth:

- Full Credit
- Earnings Update
- Covenant & Refinancing
- Relative Value
- Distressed & Restructuring
- Source-bound Deep Research

The runtime pins each run to an immutable source set. Accepted snapshots, recommendations, assumptions, and reports retain their version and evidence boundaries.

## Architecture

The browser receives a static Next.js workspace. FastAPI serves the JSON application programming interface (API) under `/api` and the exported frontend from one image.

| Path | Responsibility |
| --- | --- |
| [`caos/frontend/`](caos/frontend/) | Next.js 16 and React 19 analyst workspace |
| [`caos/server/`](caos/server/) | FastAPI service, workflow runtime, storage, and publishing |
| [`caos/server/caos/methodology/vendor/deploy_v/`](caos/server/caos/methodology/vendor/deploy_v/) | Vendored Deploy V execution authority and 22 physical skills |
| [`caos/deploy/`](caos/deploy/) | Docker, Caddy, OpenID Connect (OIDC), PostgreSQL, and ClamAV deployment |
| [`caos/tests/`](caos/tests/) | Clean-slate end-to-end contract tests |
| [`Modular OS/`](Modular%20OS/) | Broader methodology and schema reference corpus |

In production, Caddy forwards requests through `oauth2-proxy` to the app. PostgreSQL stores records and job state. A durable `/vault` volume stores immutable, content-addressed source blobs. The worker uses the same image as the API process.

## Run locally

Local development needs Python 3.11 or later, Node.js 24, and npm. Build the frontend, then start the combined app:

```bash
git clone https://github.com/EricMG13/CAOS.git
cd CAOS/caos
python3 -m venv .venv
. .venv/bin/activate
pip install -r server/requirements-dev.txt
./scripts/build_frontend.sh
PYTHONPATH=server python server/run.py
```

Open `http://localhost:8000`. Development API documentation is available at `http://localhost:8000/api/docs`.

The development adapter uses memory storage, so local boot does not require PostgreSQL. See [`caos/README.md`](caos/README.md) for the runtime boundary and deployment notes.

## Run checks

Run the server contract suite from `caos/`:

```bash
.venv/bin/python -m pytest tests/test_clean_slate.py -q
```

Run the frontend checks from `caos/frontend/`:

```bash
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

## Deploy

Production fails closed unless you provide PostgreSQL, edge, session, OIDC, and ClamAV configuration. Start from [`caos/.env.example`](caos/.env.example) and replace every placeholder, including the provider-specific `OAUTH2_PROXY_OIDC_ISSUER_URL`.

Run [`caos/server/migrate.py`](caos/server/migrate.py) against the deployment database before starting the API and worker. The supported stack is defined in [`caos/deploy/docker-compose.yml`](caos/deploy/docker-compose.yml).

## Known boundary

The official CP-MODEL workbook remains blocked until signed Deploy V authority resolves the CP-2B and CP-2A artifact-owner mismatch. CAOS does not label a provisional workbook as an official model output.

## Product principles

CAOS optimizes for the buy-side credit analyst. The interface favors dense hierarchy, evidence traceability, restrained status color, and committee-ready output. Read [`PRODUCT.md`](PRODUCT.md) for the product and design contract.
