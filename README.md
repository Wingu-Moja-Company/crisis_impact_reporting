# UNDP Crisis Impact Reporting Platform

**UNDP / Wazoku Innocentive — Build the Future of Crisis Mapping**

A real-time crisis damage reporting platform enabling affected communities to submit structured damage reports via Telegram or an offline-first Progressive Web App (PWA). Reports are stored, processed, and exported in humanitarian-standard formats for UNDP's RAPIDA methodology and partner organisations worldwide.

**Submission deadline:** 23 June 2026 · **Prize:** $50,000 USD · **Licence:** MIT

---

## Features

- **Dual collection channels** — Telegram bot (no app install) + offline-first PWA
- **UNDP RAPIDA compatible** — 3-tier damage schema, building-level versioning
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
│   ├── ingest/       # 15-step ingestion + validation pipeline
│   ├── export/       # GeoJSON / CSV / Shapefile / CAP feeds
│   ├── buildings/    # Footprint query + building versioning
│   ├── engagement/   # Badge system
│   └── webhooks/     # Azure Event Grid partner dispatch
├── infrastructure/   # Azure Bicep IaC
├── schemas/          # Crisis event form schemas (flood, earthquake, conflict)
├── scripts/          # Ops scripts (footprint download, crisis setup, etc.)
├── data/footprints/  # Downloaded building footprint data (git-ignored)
├── docs/             # RAPIDA mapping, partner API, deployment guide
└── tests/            # Load tests, e2e smoke tests
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Azure CLI (`az login`)
- Azure Functions Core Tools v4: `npm install -g azure-functions-core-tools@4`
- Docker Desktop (for PostGIS)

### Quick Start

```bash
# 1. Clone
git clone https://github.com/Wingu-Moja-Company/crisis_impact_reporting.git
cd crisis_impact_reporting

# 2. Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt
pip install -r functions/requirements.txt

# 3. Node environments
cd pwa && npm install && cd ..
cd dashboard && npm install && cd ..

# 4. PostGIS (Docker)
docker run -d --name postgis \
  -e POSTGRES_PASSWORD=localdev \
  -p 5432:5432 \
  postgis/postgis:16-3.4

# 5. Configure environment
cp .env.example .env
# Edit .env with dev credentials

# 6. Create local crisis event
python scripts/create_crisis_event.py \
  --id ke-flood-dev \
  --name "Dev — Kenya Flood Test" \
  --country KE --region nairobi --crisis-nature flood \
  --schema-file schemas/flood-schema.json

# 7. Start services (four terminals)
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
| SMS fallback | Africa's Talking | Feature phones, no smartphone |

---

## Data Model

Reports follow UNDP's RAPIDA damage classification:

- **Damage levels:** `minimal` · `partial` · `complete`
- **Infrastructure types:** residential · commercial · government · utility · transport · community · public_space · other
- **Crisis types:** earthquake · flood · tsunami · hurricane · wildfire · explosion · chemical · conflict · civil_unrest

All submissions are linked to a Microsoft Global Building Footprint polygon (`building_id`) for version-tracked, building-level damage history.

---

## Deployment (48-Hour Crisis Runbook)

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
| Pydantic + Pillow + Pandas + Fiona + Shapely | MIT / BSD |
| PostGIS | GPL-2.0 |
| Microsoft Global Building Footprints | ODbL |

All original code in this repository is published under the **MIT Licence**.

---

*Built for the UNDP / Wazoku Innocentive — Build the Future of Crisis Mapping challenge*
*Wingu Moja Company · Nairobi, Kenya*
