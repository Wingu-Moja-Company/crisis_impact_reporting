@description('Azure region for all resources')
param location string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-crisis-platform-${uniqueString(resourceGroup().id)}'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 90 }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-crisis-platform-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// Alert: ingestion error rate > 1%
resource errorRateAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-ingestion-error-rate'
  location: 'global'
  properties: {
    description: 'Ingestion error rate exceeded 1%'
    severity: 2
    enabled: true
    scopes: [appInsights.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [{
        name: 'ErrorRate'
        metricName: 'exceptions/count'
        operator: 'GreaterThan'
        threshold: 10
        timeAggregation: 'Count'
        criterionType: 'StaticThresholdCriterion'
      }]
    }
    autoMitigate: true
  }
}

output instrumentationKey string = appInsights.properties.InstrumentationKey
output appInsightsId       string = appInsights.id
