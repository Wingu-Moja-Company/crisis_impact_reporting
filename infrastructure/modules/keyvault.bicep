@description('Azure region for all resources')
param location string

@description('Principal IDs granted Key Vault Secrets User role (Managed Identities)')
param secretsUserPrincipalIds array = []

var vaultName = 'kv-crisis-${uniqueString(resourceGroup().id)}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    networkAcls: { defaultAction: 'Allow', bypass: 'AzureServices' }
  }
}

// Grant each Managed Identity the Secrets User role
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in secretsUserPrincipalIds: {
  name: guid(keyVault.id, principalId, secretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}]

output keyVaultUri  string = keyVault.properties.vaultUri
output keyVaultName string = keyVault.name
