@description('Azure region for all resources')
param location string

@description('Crisis event ID used to name the per-crisis partition')
param crisisEventId string

@description('Cosmos DB throughput mode')
@allowed(['serverless', 'autoscale', 'manual'])
param throughputMode string = 'autoscale'

var accountName = 'cosmos-crisis-platform-${uniqueString(resourceGroup().id)}'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: accountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [{ locationName: location, failoverPriority: 0 }]
    enableAutomaticFailover: false
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosAccount
  name: 'crisis-platform'
  properties: { resource: { id: 'crisis-platform' } }
}

var containers = [
  { name: 'reports',               partitionKey: '/crisis_event_id' }
  { name: 'buildings',             partitionKey: '/crisis_event_id' }
  { name: 'building_versions',     partitionKey: '/building_id'     }
  { name: 'contributors',          partitionKey: '/submitter_hash'  }
  { name: 'crisis_events',         partitionKey: '/id'              }
  { name: 'partner_subscriptions', partitionKey: '/partner_id'      }
]

resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = [for c in containers: {
  parent: database
  name: c.name
  properties: {
    resource: {
      id: c.name
      partitionKey: { paths: [c.partitionKey], kind: 'Hash' }
    }
    options: throughputMode == 'autoscale'
      ? { autoscaleSettings: { maxThroughput: 4000 } }
      : {}
  }
}]

output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosAccountName string = cosmosAccount.name
