from dataclasses import dataclass
import json
import logging
import os
import requests
import msal
import traceback

import azure.functions as func
from msgraph import GraphServiceClient
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# This variable is set in Bicep and is automatically provisioned.
application_uami = os.environ.get('APPLICATION_UAMI', 'Not set')
application_cid = os.environ.get('APPLICATION_CID', 'Not set')
application_tenant = os.environ.get('APPLICATION_TENANT', 'Not set')

managed_identity = msal.UserAssignedManagedIdentity(client_id=application_uami)

mi_auth_client = msal.ManagedIdentityClient(managed_identity, http_client=requests.Session())

# Define the token function before using it
def get_managed_identity_token(audience):
    token = mi_auth_client.acquire_token_for_client(resource=audience)

    if "access_token" in token:
        return token["access_token"]
    else:
        raise Exception(f"Failed to acquire token: {token.get('error_description', 'Unknown error')}")

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
        # Parse context to get the bearer token
        try:
            context_obj = json.loads(context)
            # Navigate through nested structure to find bearerToken in arguments
            arguments = context_obj.get('arguments', {})
            bearer_token = None
            
            # Log the arguments structure for debugging
            logging.info(f"Arguments structure: {json.dumps(arguments)[:500]}")
            
            if isinstance(arguments, dict):
                bearer_token = arguments.get('bearerToken')
            
            if not bearer_token:
                logging.warning("No bearer token found in context arguments")
                token_acquired = False
                token_error = "No bearer token found in context arguments"
            else:
                # Use On-Behalf-Of flow with the user's token
                result = cca_auth_client.acquire_token_on_behalf_of(
                    user_assertion=bearer_token,
                    scopes=['https://graph.microsoft.com/.default']
                )
                
                if "access_token" in result:
                    logging.info("Successfully acquired access token using OBO flow")
                    token_acquired = True
                    access_token = result["access_token"]
                    token_error = None
                    
                    # Use the token to call Microsoft Graph API
                    try:
                        # Create an authentication object for Microsoft Graph
                        headers = {
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        }
                        
                        # Get the user profile information
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

        # Prepare the response
        try:
            response = {}
            
            if user_data:
                # Return user data as the primary content
                response = user_data
                # Add status information
                response['success'] = True
            else:
                # If we failed to get user data, return error information
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

def get_managed_identity_token(audience):
    token = mi_auth_client.acquire_token_for_client(resource=audience)

    if "access_token" in token:
        return token["access_token"]
    else:
        raise Exception(f"Failed to acquire token: {token.get('error_description', 'Unknown error')}")

