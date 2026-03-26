targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Prefix used for resource naming.')
param namePrefix string = 'padhal'

@description('Azure Container Registry name. Must be globally unique and alphanumeric.')
param acrName string = '${toLower(namePrefix)}acr'

@allowed([
  'Basic'
  'Standard'
  'Premium'
])
@description('SKU for Azure Container Registry.')
param acrSku string = 'Basic'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: acrSku
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output acrId string = acr.id
