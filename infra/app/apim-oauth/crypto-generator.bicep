// filepath: c:\Users\chyuan\git\mcp\annaji\remote-mcp-apim-functions\infra\app\apim-oauth\crypto-generator.bicep
// This module generates cryptographically secure encryption key and IV for AES encryption
// Key is 32 bytes (256-bit) and IV is 16 bytes (128-bit)

param location string

// Using a deployment script to generate cryptographically secure values for AES encryption
resource cryptoValuesScript 'Microsoft.Resources/deploymentScripts@2020-10-01' = {
  name: 'generateCryptoValues'
  location: location
  kind: 'AzurePowerShell'
  properties: {
    azPowerShellVersion: '7.0'
    timeout: 'PT30M'
    retentionInterval: 'P1D'
    scriptContent: '''
      # Generate random 32 bytes (256-bit) key for AES-256
      $key = New-Object byte[] 32
      $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
      $rng.GetBytes($key)
      $keyBase64 = [Convert]::ToBase64String($key)
      
      # Generate random 16 bytes (128-bit) IV
      $iv = New-Object byte[] 16
      $rng.GetBytes($iv)
      $ivBase64 = [Convert]::ToBase64String($iv)
      
      # Output the values
      $DeploymentScriptOutputs = @{}
      $DeploymentScriptOutputs['encryptionKey'] = $keyBase64
      $DeploymentScriptOutputs['encryptionIV'] = $ivBase64
    '''
  }
}

// Output the generated encryption key and IV
output encryptionKey string = cryptoValuesScript.properties.outputs.encryptionKey
output encryptionIV string = cryptoValuesScript.properties.outputs.encryptionIV
