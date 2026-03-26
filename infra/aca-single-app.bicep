targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Prefix used for resource naming.')
param namePrefix string = 'padhal'

@description('Log Analytics workspace name.')
param logAnalyticsWorkspaceName string = '${namePrefix}-law'

@description('Container Apps managed environment name.')
param containerAppsEnvironmentName string = '${namePrefix}-env'

@description('Container App name.')
param containerAppName string = '${namePrefix}-app'

@description('Container Registry name used by the Container App.')
param acrName string = '${toLower(namePrefix)}acr'

@description('Container Registry login server.')
param acrLoginServer string = '${acrName}.azurecr.io'

@description('User-assigned managed identity name for Container App.')
param userAssignedIdentityName string = '${namePrefix}-uai'

@description('Federated credential name used for GitHub Actions OIDC.')
param githubFederatedCredentialName string = 'github-main'

@description('GitHub repository owner (org or user).')
param githubRepoOwner string = 'kusbr'

@description('GitHub repository name.')
param githubRepoName string = 'padhal'

@description('GitHub branch used by the workflow subject claim.')
param githubRepoBranch string = 'main'

@description('OIDC issuer URL for GitHub Actions.')
param githubOidcIssuer string = 'https://token.actions.githubusercontent.com'

@description('OIDC audience for Azure workload identity federation.')
param githubOidcAudience string = 'api://AzureADTokenExchange'

@description('Padhal API image from ACR.')
param apiImage string = '${acrLoginServer}/padhal-api:latest'

@description('Padhal frontend image from ACR.')
param frontendImage string = '${acrLoginServer}/padhal-frontend:latest'

@description('Redis container image.')
param redisImage string = 'redis:7-alpine'

@description('Expose the app publicly on HTTPS.')
param ingressExternal bool = true

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    retentionInDays: 30
    features: {
      searchVersion: 1
      legacy: 0
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

resource containerAppIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: userAssignedIdentityName
  location: location
}

resource githubFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31-preview' = {
  name: githubFederatedCredentialName
  parent: containerAppIdentity
  properties: {
    issuer: githubOidcIssuer
    subject: 'repo:${githubRepoOwner}/${githubRepoName}:ref:refs/heads/${githubRepoBranch}'
    audiences: [
      githubOidcAudience
    ]
  }
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerAppIdentity.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: containerAppIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource acrPushRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerAppIdentity.id, 'AcrPush')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '8311e382-0749-4cb8-b61a-304f252e45ec'
    )
    principalId: containerAppIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${containerAppIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      registries: [
        {
          server: acrLoginServer
          identity: containerAppIdentity.id
        }
      ]
      ingress: {
        external: ingressExternal
        allowInsecure: false
        targetPort: 8000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          env: [
            {
              name: 'REDIS_URL'
              value: 'redis://localhost:6379/0'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
        {
          name: 'redis'
          image: redisImage
          command: [
            'redis-server'
          ]
          args: [
            '--save'
            ''
            '--appendonly'
            'no'
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullRoleAssignment
    acrPushRoleAssignment
  ]
}

output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
