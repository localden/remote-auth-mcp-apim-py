import azure.functions as func
import json
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test function to capture and log the entire request received from APIM.
    """
    logging.info('Python HTTP trigger function processed a request.')
    
    # Get the request headers
    headers = dict(req.headers)
    logging.info(f"Request headers: {headers}")
    
    # Get the request body
    try:
        body_raw = req.get_body()
        body_str = body_raw.decode('utf-8')
        logging.info(f"Raw request body: {body_str}")
        
        # Try to parse as JSON
        try:
            body_json = json.loads(body_str)
            logging.info(f"Request body as JSON: {body_json}")
            
            # Check if bearerToken is included
            if "bearerToken" in body_json:
                logging.info(f"Bearer token found in body: {body_json['bearerToken'][:20]}...")
            else:
                logging.info("No bearerToken found in body JSON")
        except json.JSONDecodeError:
            logging.info("Body is not valid JSON")
    except Exception as e:
        logging.error(f"Error reading body: {str(e)}")
    
    # Return the full request details as a response
    response_body = {
        "message": "Request details captured",
        "headers": headers,
        "body": body_str if 'body_str' in locals() else None,
        "body_json": body_json if 'body_json' in locals() else None
    }
    
    return func.HttpResponse(
        json.dumps(response_body, indent=2),
        mimetype="application/json",
        status_code=200
    )
