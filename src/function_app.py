from dataclasses import dataclass
import json
import logging
import os
import requests

import azure.functions as func
from msgraph import GraphServiceClient
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"

@dataclass
class ToolProperty:
    propertyName: str
    propertyType: str
    description: str


# Define the tool properties using the ToolProperty class
tool_properties_save_snippets_object = [
    ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet."),
    ToolProperty(_SNIPPET_PROPERTY_NAME, "string", "The content of the snippet."),
]

tool_properties_get_snippets_object = [ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet.")]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])


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
    try:
        logging.info(f"Context type: {type(context).__name__}")
        
        # Get the APPLICATION_UAMI environment variable value
        application_uami = os.environ.get('APPLICATION_UAMI', 'Not set')
        
        # Just log and return the context directly
        if isinstance(context, str):
            # If it's a string, try to pretty-print the JSON
            try:
                context_obj = json.loads(context)
                # Add the APPLICATION_UAMI value to the response
                context_obj['application_uami'] = application_uami
                logging.info(f"Received context object: {json.dumps(context_obj)[:500]}...")
                return json.dumps(context_obj, indent=2)
            except json.JSONDecodeError:
                logging.info("Context is not valid JSON, returning as is")
                # For non-JSON context, we'll need to return a JSON object instead
                return json.dumps({"original_context": context, "application_uami": application_uami}, indent=2)
        else:
            # If it's already an object, add the APPLICATION_UAMI and return it pretty-printed
            if isinstance(context, dict):
                context['application_uami'] = application_uami
            else:
                # If it's not a dict, convert to dict with the original context and add APPLICATION_UAMI
                context = {"original_context": str(context), "application_uami": application_uami}
            
            logging.info(f"Received context object: {str(context)[:500]}...")
            return json.dumps(context, indent=2, default=str)
            
    except Exception as e:
        logging.error(f"Exception in hello_mcp: {str(e)}")
        return json.dumps({
            "error": f"An error occurred: {str(e)}",
            "raw_context_type": str(type(context)),
            "raw_context": str(context)[:1000] + ("..." if len(str(context)) > 1000 else "")
        }, indent=2)

def get_managed_identity_token(audience, miClientId):
    url = f'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource={audience}&client_id={miClientId}'
    headers = {'Metadata': 'true'}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        return None

