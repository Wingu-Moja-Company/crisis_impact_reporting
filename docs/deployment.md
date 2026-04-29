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

## CI/CD — automatic deployments on push to `main`

The GitHub Actions pipeline (`.github/workflows/deploy-prod.yml`) runs on every push to `main` and deploys all four components in parallel, followed by a smoke test.

| Job | What it deploys | How |
|---|---|---|
| `deploy-functions` | `functions/` → `func-crisis-pipeline-ob7ravt3zfbzi` | `azure/functions-action@v1` |
| `deploy-functions` | `bot/` → `func-crisis-bot-ob7ravt3zfbzi` | `azure/functions-action@v1` |
| `deploy-pwa` | `pwa/dist` → `swa-crisis-pwa-ob7ravt3zfbzi` | `Azure/static-web-apps-deploy@v1` |
| `deploy-dashboard` | `dashboard/dist` → `swa-crisis-dashboard-ob7ravt3zfbzi` | `Azure/static-web-apps-deploy@v1` |
| `smoke-test` | Runs after all three above | `tests/e2e/smoke_test.py` |

### Required GitHub secrets

Set under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON (for `azure/login@v2`) |
| `API_BASE_URL` | `https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api` |
| `CRISIS_EVENT_ID` | Active crisis event ID e.g. `ke-flood-dev` |
| `EXPORT_API_KEY` | API key injected into dashboard for data export |
| `SWA_DEPLOYMENT_TOKEN_PWA` | Deployment token for `swa-crisis-pwa-ob7ravt3zfbzi` |
| `SWA_DEPLOYMENT_TOKEN_DASHBOARD` | Deployment token for `swa-crisis-dashboard-ob7ravt3zfbzi` |

---

## Manual deployment (without CI/CD)

### Azure Functions

The preferred deploy method is `func azure functionapp publish` which automatically triggers a remote Oryx build (installs `requirements.txt` on Azure):

```bash
cd functions
func azure functionapp publish func-crisis-pipeline-ob7ravt3zfbzi --python
```

Repeat with `bot/` for the Telegram bot:

```bash
cd bot
func azure functionapp publish func-crisis-bot-ob7ravt3zfbzi --python
```

If you must use `az functionapp deployment source config-zip` instead, **always include `--build-remote true`**:

```bash
cd functions
zip -r /tmp/functions_deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".git/*" -x "tests/*"
az functionapp deployment source config-zip \
  --name func-crisis-pipeline-ob7ravt3zfbzi \
  --resource-group rg-crisis-platform-dev \
  --src /tmp/functions_deploy.zip \
  --build-remote true
```

> **Warning — missing packages after zip deploy:**  
> If you deploy a zip *without* `--build-remote true`, Azure copies the source files but does
> **not** reinstall Python packages. All function endpoints will return HTTP 500 with
> `ModuleNotFoundError: No module named 'azure.cosmos'`. Recovery steps:
>
> 1. Redeploy with `--build-remote true` (triggers Oryx to run `pip install -r requirements.txt`).
> 2. Wait ~2 minutes for the build to complete, then poll until the endpoint returns 200.
>
> The app setting `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is permanently set on the function app
> as a safety net, but using `--build-remote true` explicitly is the most reliable approach.

The bot function app needs `INGEST_API_KEY` in its app settings (it is sent as `X-API-Key`
on every report submission). If deploying a fresh environment, set it once:

```bash
az functionapp config appsettings set \
  --name func-crisis-bot-ob7ravt3zfbzi \
  --resource-group rg-crisis-platform-dev \
  --settings "INGEST_API_KEY=<value from func-crisis-pipeline app settings>"
```

### PWA

```bash
cd pwa
VITE_API_BASE_URL=https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api \
VITE_CRISIS_EVENT_ID=ke-flood-dev \
npm run build

# Get deployment token
SWA_TOKEN=$(az staticwebapp secrets list \
  --name swa-crisis-pwa-ob7ravt3zfbzi \
  --resource-group rg-crisis-platform-dev \
  --query "properties.apiKey" -o tsv)

swa deploy dist --deployment-token $SWA_TOKEN --env production
```

### Dashboard

The dashboard requires three Vite env vars at build time. The easiest way to manage
these for manual deploys is `dashboard/.env.local` (git-ignored):

```ini
# dashboard/.env.local
VITE_API_BASE_URL=https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api
VITE_EXPORT_API_KEY=ITMj89SPRNlx0NkCKcKE6w2DRLcD4wAldCdrGR2k0JU
VITE_CRISIS_EVENT_ID=ke-flood-dev
```

> **Important:** `VITE_EXPORT_API_KEY` must be present at build time — it is baked into
> the JS bundle by Vite. A build without it produces a dashboard that gets 401 from every
> read endpoint and shows no reports.

```bash
cd dashboard
npm run build   # picks up .env.local automatically

SWA_TOKEN=$(az staticwebapp secrets list \
  --name swa-crisis-dashboard-ob7ravt3zfbzi \
  --resource-group rg-crisis-platform-dev \
  --query "properties.apiKey" -o tsv)

swa deploy dist --deployment-token $SWA_TOKEN --env production
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
