@description('Azure region for all resources')
param location string

@description('SKU — S0 is the only available tier for Azure OpenAI')
param sku string = 'S0'

@description('Model to deploy — e.g. gpt-4.1-mini')
param modelName string = 'gpt-4.1-mini'

@description('Deployment name used by the application')
param deploymentName string = 'gpt-4.1-mini'

var accountName = 'aoai-crisis-${uniqueString(resourceGroup().id)}'

resource aoaiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  kind: 'OpenAI'
  sku: { name: sku }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: aoaiAccount
  name: deploymentName
  sku: { name: 'Standard', capacity: 10 }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: '2025-04-14'
    }
  }
}

output aoaiEndpoint   string = aoaiAccount.properties.endpoint
output aoaiKey        string = aoaiAccount.listKeys().key1
output deploymentName string = modelDeployment.name
