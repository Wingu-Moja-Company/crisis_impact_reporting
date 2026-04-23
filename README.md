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
- Azure CLI (`az login`)
- Azure Functions Core Tools v4: `npm install -g azure-functions-core-tools@4`
- Azure PostgreSQL (managed, pre-provisioned with PostGIS extension)

### Quick Start

```bash
# 1. Clone and enter repo
git clone <repo-url>
cd crisis_impact_reporting

# 2. Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt
pip install -r functions/requirements.txt

# 3. Node environments
cd pwa && npm install && cd ..
cd dashboard && npm install && cd ..

# 4. Configure environment
cp .env.example .env
# Edit .env with dev credentials

# 5. Create local crisis event
python scripts/create_crisis_event.py \
  --id ke-flood-dev \
  --name "Dev — Kenya Flood Test" \
  --country KE --region nairobi --crisis-nature flood \
  --schema-file schemas/flood-schema.json

# 6. Start services (four terminals)
cd pwa       && npm run dev   # http://localhost:3000
cd dashboard && npm run dev   # http://localhost:3001
cd functions && func start    # http://localhost:7071
python bot/main.py --poll     # Telegram bot in polling mode
```

### Running Tests

```bash
pytest tests/ -v
cd pwa && npm test
cd dashboard && npm test
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

See [docs/deployment.md](docs/deployment.md) for the full runbook. Summary:

```bash
# Deploy Azure infrastructure (Bicep)
az deployment group create \
  --resource-group rg-crisis-platform-prod \
  --template-file infrastructure/main.bicep \
  --parameters crisisEventId=ke-flood-2026-04 country=KE

# Create crisis event in Cosmos DB
python scripts/create_crisis_event.py \
  --id ke-flood-2026-04 --name "Kenya Nairobi Floods — April 2026" \
  --country KE --region nairobi --crisis-nature flood \
  --schema-file schemas/flood-schema.json
```

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
