import json
import logging
import os
import requests
import msal
import traceback
import jwt
from jwt.exceptions import PyJWTError

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# This variable is set in Bicep and is automatically provisioned.
application_uami = os.environ.get('APPLICATION_UAMI', 'Not set')
application_cid = os.environ.get('APPLICATION_CID', 'Not set')
application_tenant = os.environ.get('APPLICATION_TENANT', 'Not set')

managed_identity = msal.UserAssignedManagedIdentity(client_id=application_uami)

mi_auth_client = msal.ManagedIdentityClient(managed_identity, http_client=requests.Session())

def get_managed_identity_token(audience):
    token = mi_auth_client.acquire_token_for_client(resource=audience)

    if "access_token" in token:
        return token["access_token"]
    else:
        raise Exception(f"Failed to acquire token: {token.get('error_description', 'Unknown error')}")

def get_jwks_key(token):
    """
    Fetches the JSON Web Key from Azure AD for token signature validation.
    
    Args:
        token: The JWT token to validate
        
    Returns:
        tuple: (signing_key, error_message)
            - signing_key: The public key to verify the token, or None if retrieval failed
            - error_message: Detailed error message if retrieval failed, None otherwise
    """
    try:
        # Get the kid and issuer from the token
        try:
            header = jwt.get_unverified_header(token)
            if not header:
                return None, "Failed to parse JWT header"
        except Exception as e:
            return None, f"Invalid JWT header format: {str(e)}"
            
        kid = header.get('kid')
        if not kid:
            return None, "JWT header missing 'kid' (Key ID) claim"
        
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            if not payload:
                return None, "Failed to decode JWT payload"
        except Exception as e:
            return None, f"Invalid JWT payload format: {str(e)}"        
        
        issuer = payload.get('iss')
        if not issuer:
            return None, "JWT payload missing 'iss' (Issuer) claim"
        
        expected_issuer = f"https://sts.windows.net/{application_tenant}/"
        if issuer != expected_issuer:
            return None, f"JWT issuer '{issuer}' does not match expected issuer '{expected_issuer}'"
            
        jwks_uri = f"https://login.microsoftonline.com/{application_tenant}/discovery/v2.0/keys"
        try:
            resp = requests.get(jwks_uri, timeout=10)
            if resp.status_code != 200:
                return None, f"Failed to fetch JWKS: HTTP {resp.status_code} - {resp.text[:100]}"
                
            jwks = resp.json()
            if not jwks or 'keys' not in jwks or not jwks['keys']:
                return None, "JWKS response is empty or missing 'keys' array"
        except requests.RequestException as e:
            return None, f"Network error fetching JWKS: {str(e)}"
        except json.JSONDecodeError as e:
            return None, f"Invalid JWKS response format: {str(e)}"

        signing_key = None
        for key in jwks['keys']:
            if key.get('kid') == kid:
                try:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break
                except Exception as e:
                    return None, f"Failed to parse JWK for kid='{kid}': {str(e)}"
                
        if not signing_key:
            return None, f"No matching key found in JWKS for kid='{kid}'"
            
        return signing_key, None
    except Exception as e:
        return None, f"Unexpected error getting JWKS key: {str(e)}"

def validate_bearer_token(bearer_token, expected_audience):
    """
    Validates a JWT bearer token against the expected audience and verifies its signature.
    
    Args:
        bearer_token: The JWT token to validate
        expected_audience: The expected audience value
        
    Returns:
        tuple: (is_valid, error_message, decoded_token)
            - is_valid: boolean indicating if the token is valid
            - error_message: error message if validation failed, None otherwise
            - decoded_token: the decoded token if validation succeeded, None otherwise
    """
    if not bearer_token:
        return False, "No bearer token provided", None
    
    try:
        logging.info(f"Validating JWT token against audience: {expected_audience}")
        
        signing_key, key_error = get_jwks_key(bearer_token)
        if not signing_key:
            return False, f"JWT key retrieval failed: {key_error}", None
        
        try:
            decoded_token = jwt.decode(
                bearer_token,
                signing_key,
                algorithms=['RS256'],
                audience=expected_audience,
                options={"verify_aud": True}
            )
            
            logging.info(f"JWT token successfully validated. Token contains claims for subject: {decoded_token.get('sub', 'unknown')}")
            return True, None, decoded_token
        except jwt.exceptions.InvalidAudienceError:
            return False, f"JWT has an invalid audience. Expected: {expected_audience}", None
        except jwt.exceptions.ExpiredSignatureError:
            return False, "JWT token has expired", None
        except jwt.exceptions.InvalidSignatureError:
            return False, "JWT has an invalid signature", None
        except PyJWTError as jwt_error:
            error_message = f"JWT validation failed: {str(jwt_error)}"
            logging.error(f"JWT validation error: {error_message}")
            return False, error_message, None
    except Exception as e:
        error_message = f"Unexpected error during JWT validation: {str(e)}"
        logging.error(error_message)
        return False, error_message, None

cca_auth_client = msal.ConfidentialClientApplication(
    application_cid, 
    authority=f'https://login.microsoftonline.com/{application_tenant}',
    client_credential={"client_assertion": get_managed_identity_token('api://AzureADTokenExchange')}
)

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_graph_user_details",
    description="Get user details from Microsoft Graph.",
    toolProperties="[]",
)
def get_graph_user_details(context) -> str:
    """
    Gets user details from Microsoft Graph using the bearer token.
    
    Args:
        context: The trigger context as a JSON string containing the request information.
        
    Returns:
        str: JSON containing the user details from Microsoft Graph.
    """
    
    token_error = None
    user_data = None
    
    try:
        logging.info(f"Context type: {type(context).__name__}")

        try:
            context_obj = json.loads(context)

            arguments = context_obj.get('arguments', {})
            bearer_token = None

            logging.info(f"Arguments structure: {json.dumps(arguments)[:500]}")
            
            if isinstance(arguments, dict):
                bearer_token = arguments.get('bearerToken')
            
            if not bearer_token:
                logging.warning("No bearer token found in context arguments")
                token_acquired = False
                token_error = "No bearer token found in context arguments"
            else:
                expected_audience = f"api://{application_cid}"
                is_valid, validation_error, decoded_token = validate_bearer_token(bearer_token, expected_audience)
                
                if is_valid:
                    result = cca_auth_client.acquire_token_on_behalf_of(
                        user_assertion=bearer_token,
                        scopes=['https://graph.microsoft.com/.default']
                    )
                else:
                    token_acquired = False
                    token_error = validation_error
                    result = {"error": "invalid_token", "error_description": validation_error}
                
                if "access_token" in result:
                    logging.info("Successfully acquired access token using OBO flow")
                    token_acquired = True
                    access_token = result["access_token"]
                    token_error = None
                    
                    try:
                        headers = {
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        }

                        graph_url = 'https://graph.microsoft.com/v1.0/me'
                        response = requests.get(graph_url, headers=headers)
                        
                        if response.status_code == 200:
                            user_data = response.json()
                            logging.info("Successfully retrieved user data from Microsoft Graph")
                        else:
                            logging.error(f"Failed to get user data: {response.status_code}, {response.text}")
                            token_error = f"Graph API error: {response.status_code}"
                    except Exception as graph_error:
                        logging.error(f"Error calling Graph API: {str(graph_error)}")
                        token_error = f"Graph API error: {str(graph_error)}"
                else:
                    token_acquired = False
                    token_error = result.get('error_description', 'Unknown error acquiring token')
                    logging.warning(f"Failed to acquire token using OBO flow: {token_error}")
        except Exception as e:
            token_acquired = False
            token_error = str(e)
            logging.error(f"Exception when acquiring token: {token_error}")

        try:
            response = {}
            
            if user_data:
                response = user_data
                response['success'] = True
            else:
                response['success'] = False
                response['error'] = token_error or "Failed to retrieve user data"
            
            logging.info(f"Returning response: {json.dumps(response)[:500]}...")
            return json.dumps(response, indent=2)
        except Exception as format_error:
            logging.error(f"Error formatting response: {str(format_error)}")
            return json.dumps({
                "success": False,
                "error": f"Error formatting response: {str(format_error)}"
            }, indent=2)
    except Exception as e:
        stack_trace = traceback.format_exc()
        return json.dumps({
            "error": f"An error occurred: {str(e)}\n{stack_trace}",
            "stack_trace": stack_trace,
            "raw_context": str(context)
        }, indent=2)
