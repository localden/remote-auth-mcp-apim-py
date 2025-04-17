extension microsoftGraphV1

@description('The name of the Entra application')
param entraAppUniqueName string

@description('The display name of the Entra application')
param entraAppDisplayName string

@description('Tenant ID where the application is registered')
param tenantId string = tenant().tenantId

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
      resourceAppId: '8ae8b916-b70b-4bde-980b-3d2fafaafa87' // MCP server
      resourceAccess: [
        {
          id: 'fe4dfec2-18a4-4a84-a478-c67992f9bbb6' // mcp.server scope for my app registration
          type: 'Scope'
        }
      ]
    }
    // {
    //   resourceAppId: '00000003-0000-0000-c000-000000000000' // Microsoft Graph
    //   resourceAccess: [
    //     {
    //       id: 'e1fe6dd8-ba31-4d61-89e7-88639da4683d' // Replace with the actual scope ID for mcp.server
    //       type: 'Scope'
    //     }
    //   ]
    // }
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
