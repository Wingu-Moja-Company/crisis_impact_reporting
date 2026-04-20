@description('Azure region for all resources')
param location string

@secure()
@description('PostgreSQL administrator password')
param adminPassword string

@description('SKU — Burstable B1ms for dev, General Purpose D2s for production')
@allowed(['Standard_B1ms', 'Standard_D2s_v3'])
param skuName string = 'Standard_D2s_v3'

var serverName = 'pg-crisis-footprints-${uniqueString(resourceGroup().id)}'

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: skuName == 'Standard_B1ms' ? 'Burstable' : 'GeneralPurpose'
  }
  properties: {
    administratorLogin: 'crisisadmin'
    administratorLoginPassword: adminPassword
    version: '16'
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Enabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgresServer
  name: 'crisis_footprints'
  properties: { charset: 'UTF8', collation: 'en_US.UTF8' }
}

// Enable PostGIS extension
resource postgisExtension 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: { value: 'POSTGIS', source: 'user-override' }
}

output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
output postgresDatabase string = postgresDatabase.name
