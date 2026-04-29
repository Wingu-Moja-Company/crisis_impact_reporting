# Crisis Impact Reporting Platform

A real-time crisis damage reporting platform enabling affected communities to submit structured damage reports via Telegram or an offline-first Progressive Web App (PWA). Reports are stored, processed, and exported in humanitarian-standard formats for partner organisations worldwide.

**Licence:** MIT

---

## Features

- **Dual collection channels** — Telegram bot (no app install) + offline-first PWA
- **3-tier damage schema** — minimal / partial / complete, building-level versioning
- **6 UN languages** — AR, ZH, EN, FR, RU, ES with RTL support for Arabic
- **Offline-first** — PouchDB queues reports locally; syncs when connectivity returns
- **Building footprints** — Microsoft Global Building Footprints via Leaflet.js
- **Scale to 500,000 reports/crisis** — Cosmos DB partitioned per crisis event
- **Open data exports** — GeoJSON, CSV, Shapefile, CAP XML feed
- **Non-monetary engagement** — Badge system + coverage heatmap
- **Privacy-first** — EXIF stripped, submitters identified only by anonymised hash
- **Azure-hosted, open source** — All components MIT licenced

---

## Repository Structure

```
/
├── bot/              # Telegram bot (Python, python-telegram-bot v21+)
├── pwa/              # Offline PWA (React 18 + TypeScript + PouchDB)
├── dashboard/        # Responder dashboard (React 18 + Leaflet)
├── functions/        # Azure Functions pipeline (Python)
│   ├── ingest/       # Ingestion + validation pipeline
│   ├── export/       # GeoJSON / CSV / Shapefile / CAP feeds
│   ├── buildings/    # Footprint query + building versioning
│   ├── engagement/   # Badge system
│   └── webhooks/     # Azure Event Grid partner dispatch
├── infrastructure/   # Azure Bicep IaC
├── schemas/          # Crisis event form schemas (flood, earthquake, conflict)
├── scripts/          # Ops scripts (footprint download, crisis setup, etc.)
├── data/footprints/  # Downloaded building footprint data (git-ignored)
├── docs/             # Field mapping, partner API, deployment guide
└── tests/            # Load tests, e2e smoke tests
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Azure CLI (`az login`) — for looking up keys and managing resources
- GitHub CLI (`gh`) — for monitoring deployments

### Local development

Each component has a `.env.local` file (git-ignored) for pointing at the live dev API:

**`pwa/.env.local`**
```ini
VITE_API_BASE_URL=https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api
VITE_CRISIS_EVENT_ID=ke-flood-dev
VITE_INGEST_API_KEY=<from Azure Function App settings>
```

**`dashboard/.env.local`**
```ini
VITE_API_BASE_URL=https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api
VITE_CRISIS_EVENT_ID=ke-flood-dev
VITE_EXPORT_API_KEY=<from Azure Function App settings>
VITE_PWA_URL=https://green-grass-00d127b03.7.azurestaticapps.net
VITE_TELEGRAM_BOT_USERNAME=crisis_reporting_bot
```

```bash
# Install dependencies
pip install -r bot/requirements.txt
pip install -r functions/requirements.txt
cd pwa && npm install && cd ..
cd dashboard && npm install && cd ..

# Start services (four terminals)
cd pwa       && npm run dev   # http://localhost:3000
cd dashboard && npm run dev   # http://localhost:3001
cd functions && func start    # http://localhost:7071
python bot/main.py --poll     # Telegram bot in polling mode
```

### Running tests

```bash
cd functions && pytest tests/ -v
cd bot       && pytest tests/ -v
python tests/e2e/smoke_test.py --env local --crisis-id ke-flood-dev
```

---

## Collection Channels

| Channel | Technology | Use case |
|---|---|---|
| Telegram bot | python-telegram-bot v21+ | Messaging-first, no app install |
| Offline PWA | React 18 + PouchDB + Workbox | Zero connectivity environments |

---

## Data Model

Damage classification:

- **Damage levels:** `minimal` · `partial` · `complete`
- **Infrastructure types:** residential · commercial · government · utility · transport · community · public_space · other
- **Crisis types:** earthquake · flood · tsunami · hurricane · wildfire · explosion · chemical · conflict · civil_unrest

All submissions are linked to a Microsoft Global Building Footprint polygon (`building_id`) for version-tracked, building-level damage history.

---

## Deployment

**All deployments are handled automatically by GitHub Actions on every push to `main`.** There are no manual deployment steps for the PWA, dashboard, bot, or API functions.

```bash
git push origin main
# CI builds all components, injects secrets, deploys to Azure, runs smoke tests
# Monitor at: https://github.com/Wingu-Moja-Company/crisis_impact_reporting/actions
```

See [docs/deployment.md](docs/deployment.md) for the full runbook including required GitHub secrets, new crisis event setup, and infrastructure provisioning.

---

## Open Source Stack

| Component | Licence |
|---|---|
| python-telegram-bot | LGPL-3.0 |
| React + PouchDB + Workbox + Leaflet.js | MIT / Apache-2.0 / BSD |
| i18next + react-i18next | MIT |
| Pydantic + Pillow + Fiona + Shapely | MIT / BSD |
| PostGIS | GPL-2.0 |
| Microsoft Global Building Footprints | ODbL |

All original code in this repository is published under the **MIT Licence**.
