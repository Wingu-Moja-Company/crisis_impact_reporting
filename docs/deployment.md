# Deployment — 48-Hour Crisis Runbook

## Prerequisites

- Azure CLI authenticated: `az login`
- Access to `rg-crisis-platform-prod` resource group
- GitHub repository secrets configured (see CI/CD section)
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
# [ ] PWA loads at https://report.crisisplatform.io
# [ ] Language toggle works for all 6 UN languages — test Arabic RTL
# [ ] Building footprints visible on map for crisis region
# [ ] Submit test report via Telegram bot — appears on dashboard within 5 seconds
# [ ] Submit test report via PWA — appears on dashboard within 5 seconds
# [ ] Test PWA offline: disable network, fill form, re-enable — report syncs
# [ ] Export CSV and GeoJSON from dashboard — files download correctly
# [ ] CAP feed returns valid XML at /feeds/cap/$CRISIS_EVENT_ID.xml
# [ ] Dashboard coverage heatmap shows data
```

---

## Hour 6–12: Activate and notify

```bash
# Broadcast SMS activation via Africa's Talking
python scripts/sms_broadcast.py \
  --region $CRISIS_REGION \
  --message "Crisis reporting is now active. Submit damage reports at https://report.crisisplatform.io"

# Notify registered partner webhooks (OCHA HDX, IFRC GO, etc.)
python scripts/notify_partners.py --crisis-id $CRISIS_EVENT_ID
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

---

## CI/CD

The GitHub Actions pipeline handles all deployments automatically:

- **`pr-checks.yml`** — runs on every PR: Python tests, PWA/dashboard build, Bicep lint
- **`deploy-prod.yml`** — runs on push to `main`: deploys Bicep → Functions → PWA → Dashboard → smoke tests

Required GitHub secrets (set under Settings → Environments → production):

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | OIDC federated credential |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `SWA_DEPLOYMENT_TOKEN_PWA` | Static Web Apps token for PWA |
| `SWA_DEPLOYMENT_TOKEN_DASHBOARD` | Static Web Apps token for dashboard |
| `API_BASE_URL` | e.g. `https://api.crisisplatform.io/api` |
| `WS_URL` | e.g. `wss://api.crisisplatform.io/ws` |
| `CRISIS_EVENT_ID` | Active crisis event ID |
