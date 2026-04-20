@description('Azure region for all resources')
param location string

@description('Storage redundancy — LRS for dev, GRS for production')
@allowed(['Standard_LRS', 'Standard_GRS'])
param sku string = 'Standard_GRS'

var storageAccountName = 'stcrisis${uniqueString(resourceGroup().id)}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: sku }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource photoContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'report-photos'
  properties: { publicAccess: 'None' }
}

// Lifecycle policy — move to cool tier after 30 days, archive after 90 days
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [{
        name: 'photo-lifecycle'
        enabled: true
        type: 'Lifecycle'
        definition: {
          filters: { blobTypes: ['blockBlob'], prefixMatch: ['report-photos/'] }
          actions: {
            baseBlob: {
              tierToCool:    { daysAfterModificationGreaterThan: 30  }
              tierToArchive: { daysAfterModificationGreaterThan: 90  }
            }
          }
        }
      }]
    }
  }
}

output storageAccountName string = storageAccount.name
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
