targetScope = 'resourceGroup'

// ==============================================================================
// Parameters
// ==============================================================================

@description('Deployment environment (e.g., dev, prod, test).')
@maxLength(8)
param environment string = 'dev'

@description('The Azure region where resources should be deployed.')
param location string = resourceGroup().location

@description('The admin username for the PostgreSQL database.')
param pgAdminUsername string = 'documind_admin'

@description('The admin password for the PostgreSQL database (must meet complexity requirements).')
@secure()
param pgAdminPassword string

@description('The database name inside the PostgreSQL server.')
param pgDatabaseName string = 'documind_db'

@description('The name of the Blob Storage container to hold raw documents.')
param blobContainerName string = 'raw-documents'

// ==============================================================================
// Variables for Dynamic Naming (Ensuring compliance with resource requirements)
// ==============================================================================

var uniqueSuffix = uniqueString(resourceGroup().id)

// Storage Account name must be 3-24 characters, numbers and lowercase letters only
var storageAccountName = 'documindst${environment}${substring(uniqueSuffix, 0, 8)}'

// ACR must be 5-50 alphanumeric characters
var acrName = 'documindacr${environment}${substring(uniqueSuffix, 0, 8)}'

// Key Vault name must be 3-24 characters alphanumeric and hyphens
var keyVaultName = 'documind-kv-${environment}-${substring(uniqueSuffix, 0, 5)}'

var pgServerName = 'documind-pg-${environment}-${uniqueSuffix}'
var openAiServiceName = 'documind-openai-${environment}-${uniqueSuffix}'
var searchServiceName = 'documind-search-${environment}-${uniqueSuffix}'
var logAnalyticsName = 'documind-law-${environment}-${uniqueSuffix}'
var containerAppEnvName = 'documind-cae-${environment}-${uniqueSuffix}'
var containerAppName = 'documind-backend-${environment}'

// ==============================================================================
// Resources
// ==============================================================================

// 1. Azure OpenAI Service
resource openAiService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiServiceName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: openAiServiceName
    publicNetworkAccess: 'Enabled'
  }
}

// 1.1 Deployment for text-embedding-3-large
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAiService
  name: 'text-embedding-3-large'
  sku: {
    name: 'Standard'
    capacity: 120 // 120k TPM
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
}

// 1.2 Deployment for gpt-4o
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAiService
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 40 // 40k TPM
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
  }
}

// 2. Azure AI Search Service (Standard tier minimum for Semantic Ranker)
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: 'standard' // s1
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'free' // Enables semantic search feature
  }
}

// 3. Azure Database for PostgreSQL Flexible Server
resource pgServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: pgServerName
  location: location
  sku: {
    name: 'Standard_D2s_v3'
    tier: 'GeneralPurpose'
  }
  properties: {
    version: '16'
    administratorLogin: pgAdminUsername
    administratorLoginPassword: pgAdminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// 3.1 PostgreSQL Database
resource pgDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: pgServer
  name: pgDatabaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// 3.2 PostgreSQL Firewall Rule (Allow other Azure resources like ACA to communicate with DB)
resource pgFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: pgServer
  name: 'allow-all-azure-ips'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// 4. Azure Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true // Modern authorization
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: true
    softDeleteRetentionInDays: 7
  }
}

// 5. Azure Storage Account (Blob storage for raw documents)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// 5.1 Blob Service
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// 5.2 Blob Container
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: blobContainerName
  properties: {
    publicAccess: 'None'
  }
}

// 6. Azure Container Registry (ACR)
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// 7. Log Analytics Workspace for Container App Environment logs
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 8. Container App Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// 9. Container App (Backend API)
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.name
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/aci-helloworld:latest' // Placeholder until container build
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            {
              name: 'DJANGO_DEBUG'
              value: 'False'
            }
            {
              name: 'DB_HOST'
              value: pgServer.properties.fullyQualifiedDomainName
            }
            {
              name: 'DB_NAME'
              value: pgDatabaseName
            }
            {
              name: 'DB_USER'
              value: pgAdminUsername
            }
            {
              name: 'DB_PASSWORD'
              value: pgAdminPassword
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: openAiService.properties.endpoint
            }
            {
              name: 'AZURE_SEARCH_SERVICE_ENDPOINT'
              value: 'https://${searchService.name}.search.windows.net'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_NAME'
              value: blobContainerName
            }
          ]
        }
      ]
    }
  }
}

// ==============================================================================
// Outputs
// ==============================================================================

output openAiEndpoint string = openAiService.properties.endpoint
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output storageAccountName string = storageAccount.name
output acrLoginServer string = acr.properties.loginServer
output backendFqdn string = containerApp.properties.configuration.ingress.fqdn
