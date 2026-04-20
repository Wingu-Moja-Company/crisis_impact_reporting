@description('Azure region for all resources')
param location string

@description('Storage account name for the Functions runtime')
param storageAccountName string

@description('App Insights instrumentation key')
param appInsightsInstrumentationKey string

@description('Key Vault URI for secret references')
param keyVaultUri string

@description('SKU — Consumption for dev, Premium EP1 for production')
@allowed(['Y1', 'EP1'])
param sku string = 'EP1'

var planName    = 'plan-crisis-functions-${uniqueString(resourceGroup().id)}'
var botAppName  = 'func-crisis-bot-${uniqueString(resourceGroup().id)}'
var pipeAppName = 'func-crisis-pipeline-${uniqueString(resourceGroup().id)}'

resource hostingPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: planName
  location: location
  sku: {
    name: sku
    tier: sku == 'EP1' ? 'ElasticPremium' : 'Dynamic'
  }
  properties: { reserved: true }  // Linux
}

resource botFunctionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: botAppName
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        { name: 'AzureWebJobsStorage',              value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};...' }
        { name: 'FUNCTIONS_EXTENSION_VERSION',      value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME',         value: 'python' }
        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY',   value: appInsightsInstrumentationKey }
        { name: 'KEY_VAULT_URL',                    value: keyVaultUri }
        { name: 'TELEGRAM_BOT_TOKEN',               value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/TELEGRAM-BOT-TOKEN/)' }
      ]
    }
  }
}

resource pipelineFunctionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: pipeAppName
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        { name: 'AzureWebJobsStorage',              value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};...' }
        { name: 'FUNCTIONS_EXTENSION_VERSION',      value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME',         value: 'python' }
        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY',   value: appInsightsInstrumentationKey }
        { name: 'KEY_VAULT_URL',                    value: keyVaultUri }
      ]
    }
  }
}

output botFunctionAppName      string = botFunctionApp.name
output pipelineFunctionAppName string = pipelineFunctionApp.name
output botPrincipalId          string = botFunctionApp.identity.principalId
output pipelinePrincipalId     string = pipelineFunctionApp.identity.principalId
