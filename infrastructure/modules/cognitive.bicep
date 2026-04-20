@description('Azure region for all resources')
param location string

@description('SKU — F0 (free) for dev, S1 for production')
@allowed(['F0', 'S1'])
param sku string = 'S1'

resource aiVision 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: 'cog-vision-crisis-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'ComputerVision'
  sku: { name: sku }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource aiTranslator 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: 'cog-translator-crisis-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'TextTranslation'
  sku: { name: sku }
  properties: { publicNetworkAccess: 'Enabled' }
}

output visionEndpoint    string = aiVision.properties.endpoint
output translatorEndpoint string = 'https://api.cognitive.microsofttranslator.com'
