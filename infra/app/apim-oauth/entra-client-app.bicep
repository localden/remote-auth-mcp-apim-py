extension microsoftGraphV1

@description('The name of the Entra application')
param entraAppUniqueName string

@description('The display name of the Entra application')
param entraAppDisplayName string

@description('Tenant ID where the application is registered')
param tenantId string = tenant().tenantId

@description('Resource App ID for which the delegated permissions are being requested')
param resourceAppId string

@description('Resource App Scope ID for which the delegated permissions are being requested')
param resourceAppScopeId string = tenant().tenantId

@description('The OAuth callback URL for the API Management service')
param apimOauthCallback string

@description('The principle id of the user-assigned managed identity')
param userAssignedIdentityPrincipleId string

var loginEndpoint = environment().authentication.loginEndpoint
var issuer = '${loginEndpoint}${tenantId}/v2.0'

resource entraApp 'Microsoft.Graph/applications@v1.0' = {
  
  displayName: entraAppDisplayName
  uniqueName: entraAppUniqueName
  web: {
    redirectUris: [
      apimOauthCallback
    ]
  }
  requiredResourceAccess: [
    {
      resourceAppId: resourceAppId // MCP server
      resourceAccess: [
        {
          id: resourceAppScopeId // mcp.server scope for my app registration
          type: 'Scope'
        }
      ]
    }
  ]

  resource fic 'federatedIdentityCredentials@v1.0' = {
    name: '${entraApp.uniqueName}/msiAsFic'
    description: 'Trust the user-assigned MI as a credential for the app'
    audiences: [
       'api://AzureADTokenExchange'
    ]
    issuer: issuer
    subject: userAssignedIdentityPrincipleId
  }
}

// Outputs
output entraAppId string = entraApp.appId
output entraAppTenantId string = tenantId
