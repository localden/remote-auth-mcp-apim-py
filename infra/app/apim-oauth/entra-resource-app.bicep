extension microsoftGraphV1

@description('The name of the Entra application')
param entraAppUniqueName string

@description('The display name of the Entra application')
param entraAppDisplayName string

@description('Tenant ID where the application is registered')
param tenantId string = tenant().tenantId

@description('The principle id of the user-assigned managed identity')
param userAssignedIdentityPrincipleId string

@description('The scope ID for adding a new permission scope for the resource app')
param scopeId string = newGuid()

var loginEndpoint = environment().authentication.loginEndpoint
var issuer = '${loginEndpoint}${tenantId}/v2.0'

resource entraResourceApp 'Microsoft.Graph/applications@v1.0' = {

  displayName: entraAppDisplayName
  uniqueName: entraAppUniqueName
}

resource entraResourceAppWithSettings 'Microsoft.Graph/applications@v1.0' = {

  displayName: entraAppDisplayName
  uniqueName: entraAppUniqueName
  identifierUris: [
    'api://${entraResourceApp.appId}'
  ]
  api: {
    oauth2PermissionScopes: [
      {
        id: scopeId
        adminConsentDescription: 'Access MCP Server Data'
        adminConsentDisplayName: 'Access MCP Server Data'
        isEnabled: true
        type: 'User'
        userConsentDescription: 'Access MCP Server Data'
        userConsentDisplayName: 'Access MCP Server Data'
        value: 'mcp.server.read'
      }
    ]
  }
  requiredResourceAccess: [
    {
      resourceAppId: '00000003-0000-0000-c000-000000000000' // Microsoft Graph
      resourceAccess: [
        {
          id: 'e1fe6dd8-ba31-4d61-89e7-88639da4683d'
          type: 'Scope'
        }
      ]
    }
  ]

  resource fic 'federatedIdentityCredentials@v1.0' = {
    name: '${entraResourceApp.uniqueName}/msiAsFic'
    description: 'Trust the user-assigned MI as a credential for the app'
    audiences: [
       'api://AzureADTokenExchange'
    ]
    issuer: issuer
    subject: userAssignedIdentityPrincipleId
  }
}

resource microsoftGraphServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' existing = {
  appId: '00000003-0000-0000-c000-000000000000'
}

resource applicationRegistrationServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: entraResourceApp.appId
}

resource grants 'Microsoft.Graph/oauth2PermissionGrants@v1.0' = {
  clientId: applicationRegistrationServicePrincipal.id
  consentType: 'AllPrincipals'
  resourceId: microsoftGraphServicePrincipal.id
  scope: 'User.Read'
}

// Outputs
output entraAppId string = entraResourceApp.appId
output entraAppTenantId string = tenantId
output entraAppScopeId string = entraResourceAppWithSettings.api.oauth2PermissionScopes[0].id
