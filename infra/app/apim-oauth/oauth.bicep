@description('The name of the API Management service')
param apimServiceName string

@description('The Azure region for resources')
param location string

@description('The principle id of the user-assigned managed identity for Entra app')
param entraAppUserAssignedIdentityPrincipleId string

@description('The client ID of the user-assigned managed identity for Entra app')
param entraAppUserAssignedIdentityClientId string

@description('The name of the Entra application')
param entraClientAppUniqueName string

@description('The display name of the Entra application')
param entraClientAppDisplayName string


@description('The name of the Entra application')
param entraResourceAppUniqueName string

@description('The display name of the Entra application')
param entraResourceAppDisplayName string

resource apimService 'Microsoft.ApiManagement/service@2021-08-01' existing = {
  name: apimServiceName
}

// This is for creating the Entra Resource application for OBO flow
// Client app will be used for acquiring the token for the resource app
// And then the resource app token will be exchanged for the Entra resource access token
module entraResourceApp './entra-resource-app.bicep' = {
  name: 'entraResourceApp'
  params:{
    entraAppUniqueName: entraResourceAppUniqueName
    entraAppDisplayName: entraResourceAppDisplayName
    userAssignedIdentityPrincipleId: entraAppUserAssignedIdentityPrincipleId
  }
}


module entraClientApp './entra-client-app.bicep' = {
  name: 'entraClientApp'
  params:{
    entraAppUniqueName: entraClientAppUniqueName
    entraAppDisplayName: entraClientAppDisplayName
    resourceAppId: entraResourceApp.outputs.entraAppId
    resourceAppScopeId: entraResourceApp.outputs.entraAppScopeId
    apimOauthCallback: '${apimService.properties.gatewayUrl}/oauth-callback'
    userAssignedIdentityPrincipleId: entraAppUserAssignedIdentityPrincipleId
  }
}

// Generate cryptographic values for encryption
module cryptoGenerator './crypto-generator.bicep' = {
  name: 'cryptoGenerator'
  params: {
    location: location
  }
}

// Define the Named Values
resource EntraIDTenantIdNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'EntraIDTenantId'
  properties: {
    displayName: 'EntraIDTenantId'
    value: entraClientApp.outputs.entraAppTenantId
    secret: false
  }
}

resource EntraIDClientIdNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'EntraIDClientId'
  properties: {
    displayName: 'EntraIDClientId'
    value: entraClientApp.outputs.entraAppId
    secret: false
  }
}

resource EntraIDResourceClientIdNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'EntraIDResourceClientId'
  properties: {
    displayName: 'EntraIDResourceClientId'
    value: entraResourceApp.outputs.entraAppId
    secret: false
  }
}

resource EntraIdFicClientIdNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'EntraIDFicClientId'
  properties: {
    displayName: 'EntraIdFicClientId'
    value: entraAppUserAssignedIdentityClientId
    secret: false
  }
}

resource OAuthCallbackUriNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'OAuthCallbackUri'
  properties: {
    displayName: 'OAuthCallbackUri'
    value: '${apimService.properties.gatewayUrl}/oauth-callback'
    secret: false
  }
}

resource OAuthScopesNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'OAuthScopes'
  properties: {
    displayName: 'OAuthScopes'
    value: 'api://${entraResourceApp.outputs.entraAppId}/mcp.server.read'
    secret: false
  }
}

resource EncryptionIVNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'EncryptionIV'
  properties: {
    displayName: 'EncryptionIV'
    value: cryptoGenerator.outputs.encryptionIV
    secret: true
  }
}

resource EncryptionKeyNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'EncryptionKey'
  properties: {
    displayName: 'EncryptionKey'
    value: cryptoGenerator.outputs.encryptionKey
    secret: true
  }
}

resource McpClientIdNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'McpClientId'
  properties: {
    displayName: 'McpClientId'
    value: entraClientApp.outputs.entraAppId
    secret: false
  }
}

resource APIMGatewayURLNamedValue 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  parent: apimService
  name: 'APIMGatewayURL'
  properties: {
    displayName: 'APIMGatewayURL'
    value: apimService.properties.gatewayUrl
    secret: false
  }
}

// Create the OAuth API
resource oauthApi 'Microsoft.ApiManagement/service/apis@2021-08-01' = {
  parent: apimService
  name: 'oauth'
  properties: {
    displayName: 'OAuth'
    description: 'OAuth 2.0 Authentication API'
    subscriptionRequired: false
    path: ''
    protocols: [
      'https'
    ]
    serviceUrl: 'https://login.microsoftonline.com/${entraClientApp.outputs.entraAppTenantId}/oauth2/v2.0'
  }
}

// Add a GET operation for the authorization endpoint
resource oauthAuthorizeOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'authorize'
  properties: {
    displayName: 'Authorize'
    method: 'GET'
    urlTemplate: '/authorize'
    description: 'OAuth 2.0 authorization endpoint'
  }
}

// Add policy for the authorize operation
resource oauthAuthorizePolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthAuthorizeOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('authorize.policy.xml')
  }
}

// Add a POST operation for the token endpoint
resource oauthTokenOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'token'
  properties: {
    displayName: 'Token'
    method: 'POST'
    urlTemplate: '/token'
    description: 'OAuth 2.0 token endpoint'
  }
}

// Add policy for the token operation
resource oauthTokenPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthTokenOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('token.policy.xml')
  }
}

// Add a GET operation for the OAuth callback endpoint
resource oauthCallbackOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'oauth-callback'
  properties: {
    displayName: 'OAuth Callback'
    method: 'GET'
    urlTemplate: '/oauth-callback'
    description: 'OAuth 2.0 callback endpoint to handle authorization code flow'
  }
}

// Add policy for the OAuth callback operation
resource oauthCallbackPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthCallbackOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('oauth-callback.policy.xml')
  }
  dependsOn: [
    EncryptionKeyNamedValue
    EncryptionIVNamedValue
  ]
}

// Add a POST operation for the register endpoint
resource oauthRegisterOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'register'
  properties: {
    displayName: 'Register'
    method: 'POST'
    urlTemplate: '/register'
    description: 'OAuth 2.0 client registration endpoint'
  }
}

// Add policy for the register operation
resource oauthRegisterPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthRegisterOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('register.policy.xml')
  }
}

// Add a OPTIONS operation for the register endpoint
resource oauthRegisterOptionsOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'register-options'
  properties: {
    displayName: 'Register Options'
    method: 'OPTIONS'
    urlTemplate: '/register'
    description: 'CORS preflight request handler for register endpoint'
  }
}

// Add policy for the register options operation
resource oauthRegisterOptionsPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthRegisterOptionsOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('register-options.policy.xml')
  }
}

// Add a OPTIONS operation for the OAuth metadata endpoint
resource oauthMetadataOptionsOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'oauthmetadata-options'
  properties: {
    displayName: 'OAuth Metadata Options'
    method: 'OPTIONS'
    urlTemplate: '/.well-known/oauth-authorization-server'
    description: 'CORS preflight request handler for OAuth metadata endpoint'
  }
}

// Add policy for the OAuth metadata options operation
resource oauthMetadataOptionsPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthMetadataOptionsOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('oauthmetadata-options.policy.xml')
  }
}

// Add a GET operation for the OAuth metadata endpoint
resource oauthMetadataGetOperation 'Microsoft.ApiManagement/service/apis/operations@2021-08-01' = {
  parent: oauthApi
  name: 'oauthmetadata-get'
  properties: {
    displayName: 'OAuth Metadata Get'
    method: 'GET'
    urlTemplate: '/.well-known/oauth-authorization-server'
    description: 'OAuth 2.0 metadata endpoint'
  }
}

// Add policy for the OAuth metadata get operation
resource oauthMetadataGetPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2021-08-01' = {
  parent: oauthMetadataGetOperation
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('oauthmetadata-get.policy.xml')
  }
}

output apiId string = oauthApi.id
output entraResourceAppId string = entraResourceApp.outputs.entraAppId
