@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Crisis event ID used for naming and partitioning')
param crisisEventId string

@description('ISO 3166-1 alpha-2 country code for this crisis')
param country string

@description('Environment tag')
@allowed(['dev', 'staging', 'production'])
param environment string = 'production'

@secure()
param postgresAdminPassword string

// ----- Monitoring (deployed first — other modules reference instrumentation key) -----
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: { location: location }
}

// ----- Storage -----
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    sku: environment == 'production' ? 'Standard_GRS' : 'Standard_LRS'
  }
}

// ----- Cosmos DB -----
module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  params: {
    location: location
    crisisEventId: crisisEventId
    throughputMode: environment == 'production' ? 'autoscale' : 'serverless'
  }
}

// ----- PostgreSQL + PostGIS -----
module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    adminPassword: postgresAdminPassword
    skuName: environment == 'production' ? 'Standard_D2s_v3' : 'Standard_B1ms'
  }
}

// ----- Azure AI Services -----
module cognitive 'modules/cognitive.bicep' = {
  name: 'cognitive'
  params: {
    location: location
    sku: environment == 'production' ? 'S1' : 'F0'
  }
}

// ----- Key Vault (before Functions — Functions reference vault URI) -----
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    secretsUserPrincipalIds: functions.outputs.botPrincipalId == ''
      ? []
      : [functions.outputs.botPrincipalId, functions.outputs.pipelinePrincipalId]
  }
  dependsOn: [functions]
}

// ----- Azure Functions -----
module functions 'modules/functions.bicep' = {
  name: 'functions'
  params: {
    location: location
    storageAccountName: storage.outputs.storageAccountName
    appInsightsInstrumentationKey: monitoring.outputs.instrumentationKey
    keyVaultUri: 'https://placeholder/'  // updated post-deploy via keyvault module output
    sku: environment == 'production' ? 'EP1' : 'Y1'
  }
}

// ----- Outputs -----
output cosmosEndpoint        string = cosmos.outputs.cosmosEndpoint
output storageAccountName    string = storage.outputs.storageAccountName
output postgresHost          string = postgres.outputs.postgresHost
output visionEndpoint        string = cognitive.outputs.visionEndpoint
output keyVaultUri           string = keyvault.outputs.keyVaultUri
output botFunctionAppName    string = functions.outputs.botFunctionAppName
output pipelineFunctionAppName string = functions.outputs.pipelineFunctionAppName
