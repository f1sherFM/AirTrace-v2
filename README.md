# AirTrace v2

[![CI](https://github.com/f1sherFM/AirTrace-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/f1sherFM/AirTrace-v2/actions/workflows/ci.yml)
[![Production Assets](https://github.com/f1sherFM/AirTrace-v2/actions/workflows/compose-assets.yml/badge.svg)](https://github.com/f1sherFM/AirTrace-v2/actions/workflows/compose-assets.yml)
![Python](https://img.shields.io/badge/python-3.13-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-SSR%20%2B%20API-009688.svg?logo=fastapi&logoColor=white)
![Postgres](https://img.shields.io/badge/Postgres-16-336791.svg?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)
![Status](https://img.shields.io/badge/status-production%20baseline-16a34a.svg)

Standalone repository for the new AirTrace core: `v2` API, Python SSR web app, Postgres-backed alerts, Telegram delivery, and production deployment assets.

## Live Status

- Production domain: [https://nande.webhop.me](https://nande.webhop.me)
- Web UI: [https://nande.webhop.me](https://nande.webhop.me)
- API docs: [https://nande.webhop.me/docs](https://nande.webhop.me/docs)
- Health: [https://nande.webhop.me/api/v2/health](https://nande.webhop.me/api/v2/health)

## What v2 Contains

- Stable public readonly API:
  - `GET /v2/current`
  - `GET /v2/forecast`
  - `GET /v2/history`
  - `GET /v2/trends`
  - `GET /v2/health`
- Alert write paths:
  - `POST /v2/alerts`
  - `GET /v2/alerts`
  - `GET /v2/alerts/{id}`
  - `PATCH /v2/alerts/{id}`
  - `DELETE /v2/alerts/{id}`
- Python SSR web:
  - city pages
  - history and trends pages
  - compare UI
  - alerts settings UI
  - explainability blocks
- Production foundation:
  - Docker deployment profile
  - Postgres + Redis stack
  - Sentry integration
  - GitHub Actions safety net
  - VPS runbook

## Architecture

```text
api/v1/            legacy compatibility adapter
api/v2/            stable public v2 API
application/       use cases, queries, SSR web layer
domain/            AQI, NMU, confidence, pollutants
infrastructure/    DB, repositories, cache, providers
core/              app factory, lifecycle, settings
web/               Python SSR app, templates, static assets
config/            runtime config and cities mapping
docs/              roadmap, ADRs, ops and deployment docs
tests/             regression, contract, SSR, migration gates
```

## Quick Start

### Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python start_app.py
```

After startup:

- API: [http://localhost:8000](http://localhost:8000)
- Web: [http://localhost:3000](http://localhost:3000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

### Local env

The repo supports local `.env` loading. Typical local variables:

```env
ALERTS_API_KEY=...
TELEGRAM_BOT_TOKEN=...
SENTRY_DSN=...
API_BASE_URL=http://127.0.0.1:8000
```

### Production

Main deployment assets:

- [docker-compose.prod.yml](docker-compose.prod.yml)
- [Dockerfile.api](Dockerfile.api)
- [.env.production.example](.env.production.example)
- [docs/vps_deployment_runbook.md](docs/vps_deployment_runbook.md)

## Repository Notes

- `main` is the active branch for `AirTrace-v2`
- this repository is the primary home for ongoing `v2` work
- the original `Airtrace-RU` repo is now the legacy/historical reference

Split provenance:

- source repository: [Airtrace-RU](https://github.com/f1sherFM/Airtrace-RU)
- source branch: `airtrace-v2`
- source commit: `e1170d8b53c35f6d4f00dccfaa49133cf5d205a6`
- details: [docs/repository_provenance.md](docs/repository_provenance.md)

## Key Docs

- [docs/public_api_v2.md](docs/public_api_v2.md)
- [docs/production_compose_profile.md](docs/production_compose_profile.md)
- [docs/vps_deployment_runbook.md](docs/vps_deployment_runbook.md)
- [docs/post_deploy_hardening.md](docs/post_deploy_hardening.md)
- [openapi/airtrace-v2.openapi.json](openapi/airtrace-v2.openapi.json)

## Testing

Examples:

```powershell
.\.venv\Scripts\python -m pytest tests\test_stage0_ssr_smoke.py -q
.\.venv\Scripts\python -m pytest tests\test_v2_contract.py -q
.\.venv\Scripts\python -m pytest tests\test_stage5_alerts_ui.py -q
```

CI already checks:

- compile safety
- focused regression pack
- production compose assets

## Current Focus

- post-deploy hardening
- alerts UX polish
- continued cleanup of remaining legacy weight inside `v2`
