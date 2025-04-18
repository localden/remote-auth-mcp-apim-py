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

# cca_auth_client = msal.ConfidentialClientApplication(
#     application_cid, 
#     authority=f'https://login.microsoftonline.com/{application_tenant}',
#     client_credential={"client_assertion": get_managed_identity_token('api://AzureADTokenExchange')}
# )

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_graph_user_details",
    description="Get user details from Microsoft Graph.",
    toolProperties="[]",
)
def get_graph_user_details(context) -> str:
    """
    A function that simply returns the context for debugging purposes.

    Args:
        context: The trigger context as a JSON string containing the request information.

    Returns:
        str: The full context as JSON for inspection.
    """   
    
    token_error = None

    try:
        logging.info(f"Context type: {type(context).__name__}")

        # Get a managed identity token
        try:
            # Use the existing function to get a managed identity token for Microsoft Graph
            mi_token = get_managed_identity_token("api://AzureADTokenExchange")
            token_acquired = True
            token_error = None
        except Exception as mi_error:
            mi_token = None
            token_acquired = False
            token_error = str(mi_error)
            logging.warning(f"Failed to acquire managed identity token: {token_error}")
        
        try:
            context_obj = json.loads(context)
            # Add the Azure application details to the response
            context_obj['application_uami'] = application_uami
            context_obj['application_cid'] = application_cid
            context_obj['application_tenant'] = application_tenant

            # Add the managed identity token information
            context_obj['mi_token_acquired'] = token_acquired
            if token_acquired:
                context_obj['managed_identity_token'] = mi_token
            else:
                context_obj['mi_token_error'] = str(token_error)
            
            logging.info(f"Received context object: {json.dumps(context_obj)[:500]}...")
            return json.dumps(context_obj, indent=2)
        except json.JSONDecodeError:
            logging.info("Context is not valid JSON, returning as is")
            # For non-JSON context, we'll need to return a JSON object instead
            response = {
                "original_context": context, 
                "application_uami": application_uami,
                "application_cid": application_cid,
                "application_tenant": application_tenant,
                "mi_token_acquired": token_acquired
            }
            
            # Add token info
            if token_acquired:
                response['managed_identity_token'] = mi_token
            else:
                response['mi_token_error'] = str(token_error)
            
            return json.dumps(response, indent=2)
        
        logging.info(f"Received context object: {str(context)[:500]}...")
        return json.dumps(context, indent=2, default=str)
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

