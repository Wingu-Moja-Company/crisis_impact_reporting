# Deployment — 48-Hour Crisis Runbook

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Azure Static Web Apps (West Europe)                            │
│  PWA (reporter)        swa-crisis-pwa-ob7ravt3zfbzi             │
│  Dashboard (ops)       swa-crisis-dashboard-ob7ravt3zfbzi       │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼─────────────────────────────────────────┐
│  Azure Functions — func-crisis-pipeline-ob7ravt3zfbzi           │
│  Python 3.12 · Consumption plan (dev) / EP1 Premium (prod)      │
│  Base URL: https://func-crisis-pipeline-ob7ravt3zfbzi           │
│           .azurewebsites.net/api                                 │
│                                                                  │
│  Telegram bot — func-crisis-bot-ob7ravt3zfbzi                   │
└──────┬────────────────┬───────────────┬──────────────────────────┘
       │                │               │
┌──────▼──────┐  ┌──────▼──────┐  ┌────▼──────────────────────────┐
│  Cosmos DB  │  │  Blob Store │  │  PostgreSQL + PostGIS          │
│  crisis-    │  │  (photos)   │  │  pg-crisis-footprints-         │
│  platform   │  │             │  │  ob7ravt3zfbzi.postgres        │
│             │  │             │  │  .database.azure.com           │
└─────────────┘  └─────────────┘  └───────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│  Azure AI Services                                              │
│  Computer Vision (photo analysis) · Translator (field notes)    │
└─────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│  Key Vault — kv-crisis-ob7ravt3zfbzi                            │
│  All secrets injected via managed identity at runtime           │
└─────────────────────────────────────────────────────────────────┘
```

**Active resource group:** `rg-crisis-platform-dev` (West Europe)

| Resource | Name |
|---|---|
| Function App — pipeline | `func-crisis-pipeline-ob7ravt3zfbzi` |
| Function App — Telegram bot | `func-crisis-bot-ob7ravt3zfbzi` |
| Static Web App — PWA | `swa-crisis-pwa-ob7ravt3zfbzi` → `green-grass-00d127b03.7.azurestaticapps.net` |
| Static Web App — Dashboard | `swa-crisis-dashboard-ob7ravt3zfbzi` → `salmon-desert-0b66f1503.7.azurestaticapps.net` |
| Cosmos DB | database: `crisis-platform` |
| PostgreSQL | `pg-crisis-footprints-ob7ravt3zfbzi.postgres.database.azure.com` · db: `crisis_footprints` |
| Key Vault | `kv-crisis-ob7ravt3zfbzi` |
| Seeded crisis event | `ke-flood-dev` |

---

## Prerequisites

- Azure CLI authenticated: `az login`
- SWA CLI installed: `npm install -g @azure/static-web-apps-cli`
- Azure Functions Core Tools v4: `npm install -g azure-functions-core-tools@4`
- Access to `rg-crisis-platform-dev` (dev) or `rg-crisis-platform-prod` (prod)
- GitHub repository secrets configured (see CI/CD section below)
- Building footprints pre-loaded for the crisis region

---

## Hour 0–2: Deploy infrastructure

```bash
export CRISIS_EVENT_ID="ke-flood-2026-04"
export CRISIS_COUNTRY="KE"
export CRISIS_REGION="nairobi"
export CRISIS_NATURE="flood"

# Deploy all Azure services via Bicep
az deployment group create \
  --resource-group rg-crisis-platform-prod \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/prod.parameters.json \
  --parameters crisisEventId=$CRISIS_EVENT_ID country=$CRISIS_COUNTRY

# Create crisis event and load form schema in Cosmos DB
python scripts/create_crisis_event.py \
  --id $CRISIS_EVENT_ID \
  --name "Kenya Nairobi Floods — April 2026" \
  --country $CRISIS_COUNTRY \
  --region $CRISIS_REGION \
  --crisis-nature $CRISIS_NATURE \
  --schema-file schemas/flood-schema.json

# Verify building footprints are loaded
python scripts/verify_footprints.py --region $CRISIS_REGION --country $CRISIS_COUNTRY
```

If footprints are not loaded:

```bash
python scripts/download_footprints.py --country $CRISIS_COUNTRY --region $CRISIS_REGION \
  --output data/footprints/${CRISIS_COUNTRY,,}-${CRISIS_REGION}.geojson
python scripts/load_footprints.py \
  --input data/footprints/${CRISIS_COUNTRY,,}-${CRISIS_REGION}.geojson \
  --country $CRISIS_COUNTRY --region $CRISIS_REGION
python scripts/simplify_footprints.py \
  --input  data/footprints/${CRISIS_COUNTRY,,}-${CRISIS_REGION}.geojson \
  --output data/footprints/${CRISIS_COUNTRY,,}-${CRISIS_REGION}-simplified.geojson
```

---

## Hour 2–6: Configure and test

```bash
# Register Telegram bot webhook
python scripts/register_telegram_webhook.py --env prod

# Run smoke tests
python tests/e2e/smoke_test.py --env prod --crisis-id $CRISIS_EVENT_ID

# Manual checklist:
# [ ] PWA loads and is installable as a PWA
# [ ] Language toggle works for all 6 UN languages — test Arabic RTL
# [ ] Building footprints visible on map for crisis region
# [ ] Submit test report via Telegram bot — appears on dashboard within 5 seconds
# [ ] Submit test report via PWA — appears on dashboard within 5 seconds
# [ ] Test PWA offline: disable network, fill form, re-enable — report syncs
# [ ] Export CSV and GeoJSON from dashboard — files download correctly
# [ ] CAP feed returns valid XML at /v1/feeds/cap/$CRISIS_EVENT_ID.xml
# [ ] Dashboard coverage heatmap shows data
# [ ] Click a report in the feed — map popup is fully visible (not clipped at top)
# [ ] Click a marker directly on the map — popup also offsets correctly, card fully visible
# [ ] Leave dashboard open for 30 s (one poll cycle) — map position holds, photo does not flash
# [ ] Submit via Telegram bot — report appears on dashboard (bot must have INGEST_API_KEY set)
```

---

## Hour 6–12: Activate and notify

```bash
# Notify registered partner webhooks (OCHA HDX, IFRC GO, etc.)
python scripts/notify_partners.py --crisis-id $CRISIS_EVENT_ID
```

---

## CI/CD — the only deployment process

**All deployments go through GitHub Actions. Do not deploy manually.**

Push to `main` is the single trigger. GitHub Actions builds every component with the correct secrets injected and runs a smoke test before marking the deployment complete. Manual `az`, `func`, or `swa` commands bypass secrets injection, produce different build artefacts than CI, and have caused production incidents (missing API keys, wrong bundles served). They must not be used.

```
git add .
git commit -m "your change"
git push origin main
# GitHub Actions takes over — watch progress at:
# https://github.com/Wingu-Moja-Company/crisis_impact_reporting/actions
```

### What the pipeline does

| Job | Deploys | Method |
|---|---|---|
| `deploy-functions` | `functions/` → `func-crisis-pipeline-ob7ravt3zfbzi` | `azure/functions-action@v1` |
| `deploy-functions` | `bot/` → `func-crisis-bot-ob7ravt3zfbzi` | `azure/functions-action@v1` |
| `deploy-pwa` | `pwa/` built → `swa-crisis-pwa-ob7ravt3zfbzi` | `Azure/static-web-apps-deploy@v1` |
| `deploy-dashboard` | `dashboard/` built → `swa-crisis-dashboard-ob7ravt3zfbzi` | `Azure/static-web-apps-deploy@v1` |
| `smoke-test` | Runs after all three above pass | `tests/e2e/smoke_test.py` |

The PWA and dashboard are built by CI from source with all environment variables injected from GitHub secrets. The built artefacts are never committed to the repository.

### Required GitHub secrets

Set under **Settings → Secrets and variables → Actions**. All must be present or the build will produce broken bundles (missing API keys, 401 errors in production).

| Secret | Value / description |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON (for `azure/login@v2`) |
| `API_BASE_URL` | `https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api` |
| `CRISIS_EVENT_ID` | Active crisis event ID, e.g. `ke-flood-dev` |
| `INGEST_API_KEY` | Key required by `POST /v1/reports` — baked into PWA bundle and used by smoke test |
| `EXPORT_API_KEY` | Key for export/admin endpoints — baked into dashboard bundle |
| `VITE_PWA_URL` | Public URL of the PWA (`https://green-grass-00d127b03.7.azurestaticapps.net`) — used for share link buttons in admin panel |
| `VITE_TELEGRAM_BOT_USERNAME` | Telegram bot username (`crisis_reporting_bot`) — used for bot deep-link buttons in admin panel |
| `SWA_DEPLOYMENT_TOKEN_PWA` | Deployment token for `swa-crisis-pwa-ob7ravt3zfbzi` |
| `SWA_DEPLOYMENT_TOKEN_DASHBOARD` | Deployment token for `swa-crisis-dashboard-ob7ravt3zfbzi` |

> **If a secret is missing:** the CI build will succeed (Vite silently treats missing env vars as empty strings) but the deployed app will be broken. Symptoms: PWA submissions return 401, dashboard shows no reports. Always verify secrets are set before investigating runtime errors.

### Checking a deployment

```bash
# See the latest run and its status
gh run list --limit 5

# Watch a run live
gh run watch <run-id>

# View logs for a failed job
gh run view <run-id> --log-failed
```

### Environment variables baked into each build

Vite bakes `VITE_*` variables into the JS bundle at build time. The values come entirely from GitHub secrets — `.env.local` files are only for local development and are git-ignored.

| Variable | Used by | Secret |
|---|---|---|
| `VITE_API_BASE_URL` | PWA + Dashboard | `API_BASE_URL` |
| `VITE_CRISIS_EVENT_ID` | PWA + Dashboard | `CRISIS_EVENT_ID` |
| `VITE_INGEST_API_KEY` | PWA (report submission) | `INGEST_API_KEY` |
| `VITE_EXPORT_API_KEY` | Dashboard (all read + admin endpoints) | `EXPORT_API_KEY` |
| `VITE_PWA_URL` | Dashboard (admin panel share buttons) | `VITE_PWA_URL` |
| `VITE_TELEGRAM_BOT_USERNAME` | Dashboard (admin panel bot deep-link buttons) | `VITE_TELEGRAM_BOT_USERNAME` |

---

## Local development environment files

These files are git-ignored and only used when running `npm run dev` locally. They must never be used to drive a production deployment.

**`pwa/.env.local`**
```ini
VITE_API_BASE_URL=https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api
VITE_CRISIS_EVENT_ID=ke-flood-dev
VITE_INGEST_API_KEY=<value from Azure Function App settings>
```

**`dashboard/.env.local`**
```ini
VITE_API_BASE_URL=https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api
VITE_CRISIS_EVENT_ID=ke-flood-dev
VITE_EXPORT_API_KEY=<value from Azure Function App settings>
```

Retrieve current key values with:
```bash
az functionapp config appsettings list \
  --name func-crisis-pipeline-ob7ravt3zfbzi \
  --resource-group rg-crisis-platform-dev \
  --query "[?name=='INGEST_API_KEY' || name=='EXPORT_API_KEY'].{name:name,value:value}" \
  -o table
```

---

## Monitoring targets during active crisis

| Metric | Target | Alert threshold |
|---|---|---|
| Report ingestion rate | Sustained during crisis | 0 reports for 5 min during active event |
| Pipeline p95 latency | < 2 seconds | > 10 seconds |
| Error rate | < 0.1% | > 1% |
| Cosmos DB RU consumption | < 70% provisioned | 70% → triggers autoscale |
| Azure Functions cold starts | < 5% of invocations | Switch to Premium plan |

Monitor via Azure App Insights dashboard and the alert rules deployed in `infrastructure/modules/monitoring.bicep`.

---

## Scaling up (national crisis — 500k reports)

```bash
# Scale Cosmos DB to dedicated throughput
az cosmosdb sql container throughput update \
  --account-name <cosmos-account> \
  --database-name crisis-platform \
  --name reports \
  --resource-group rg-crisis-platform-prod \
  --max-throughput 10000

# Switch Functions to Premium EP1 if not already
az functionapp plan update \
  --name <plan-name> \
  --resource-group rg-crisis-platform-prod \
  --sku EP1
```
