extension microsoftGraphV1

@description('The name of the Entra application')
param entraAppUniqueName string

@description('The display name of the Entra application')
param entraAppDisplayName string

@description('Tenant ID where the application is registered')
param tenantId string = tenant().tenantId

@description('The principle id of the user-assigned managed identity')
param userAssignedIdentityPrincipleId string

@description('The OAuth callback URL for the API Management service')
param apimOauthCallback string

var loginEndpoint = environment().authentication.loginEndpoint
var issuer = '${loginEndpoint}${tenantId}/v2.0'

resource entraResourceApp 'Microsoft.Graph/applications@v1.0' = {

  displayName: entraAppDisplayName
  uniqueName: entraAppUniqueName

  web: {
    redirectUris: [
      apimOauthCallback
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

var identifierUri = 'api://${entraResourceApp.appId}'

// workaround for https://github.com/microsoftgraph/msgraph-bicep-types/issues/239
resource appWithIdentifierUris 'Microsoft.Graph/applications@v1.0' = {
  displayName: entraResourceApp.displayName
  uniqueName: entraAppUniqueName
  identifierUris: [
    identifierUri
  ]
  web: entraResourceApp.web
  requiredResourceAccess: entraResourceApp.requiredResourceAccess
}

resource microsoftGraphServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' existing = {
  appId: '00000003-0000-0000-c000-000000000000'
}

resource applicationRegistrationServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: appWithIdentifierUris.appId
}

resource grants 'Microsoft.Graph/oauth2PermissionGrants@v1.0' = {
  clientId: applicationRegistrationServicePrincipal.id
  consentType: 'AllPrincipals'
  resourceId: microsoftGraphServicePrincipal.id
  scope: 'User.Read'
}

// Outputs
output entraAppId string = appWithIdentifierUris.appId
output entraAppTenantId string = tenantId
