import os
import base64
import json
import logging
import httpx
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel
from pythonjsonlogger import json as jsonlogger

# --- Configuration ---
# API Service URL (Internal)
API_BASE_URL = os.getenv('API_BASE_URL', 'http://api:8000')
PORT = int(os.getenv('PORT', '8080'))

# --- Logging Setup ---
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# --- FastAPI App ---
app = FastAPI(title='Email Ingest Worker')


# --- Models ---
class PubSubMessage(BaseModel):
    data: str
    messageId: str
    publishTime: str
    attributes: Optional[Dict[str, str]] = None


class PubSubBody(BaseModel):
    message: PubSubMessage
    subscription: str


# --- Helpers ---
def decode_pubsub_data(data_base64: str) -> Dict[str, Any]:
    """Decodes the Base64 encoded Pub/Sub message data."""
    try:
        decoded_bytes = base64.b64decode(data_base64)
        decoded_str = decoded_bytes.decode('utf-8')
        return json.loads(decoded_str)
    except Exception as e:
        logger.error(f'Failed to decode Pub/Sub data: {e}', extra={'error': str(e)})
        raise ValueError(f'Invalid Pub/Sub data: {e}')


# --- Endpoints ---
@app.get('/health')
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {'status': 'ok'}


@app.post('/')
async def receive_pubsub_push(body: PubSubBody, request: Request):
    """
    Handle incoming Pub/Sub push messages.
    Forwards event to API for background processing.
    """
    trace_context = request.headers.get('X-Cloud-Trace-Context')
    req_logger_extra = {'trace_context': trace_context, 'messageId': body.message.messageId}

    try:
        logger.info('Received Pub/Sub message', extra=req_logger_extra)

        # 1. Decode Data to get minimal info
        decoded_data = decode_pubsub_data(body.message.data)

        email_address = decoded_data.get('emailAddress')
        history_id = decoded_data.get('historyId')

        if not email_address or not history_id:
            logger.warning('Invalid Pub/Sub payload: missing email or historyId', extra=req_logger_extra)
            # ACK to remove bad message from queue
            return {'status': 'acked_invalid_payload'}

        # 2. Forward to API
        async with httpx.AsyncClient(timeout=30.0) as client:
            api_url = f'{API_BASE_URL}/api/emails/sync/background'
            payload = {'email_address': email_address, 'history_id': int(history_id)}

            logger.info(f'Forwarding to API: {api_url}', extra={**req_logger_extra, 'email': email_address})

            response = await client.post(api_url, json=payload)

            if response.status_code >= 400:
                logger.error(
                    f'API returned error: {response.status_code}',
                    extra={**req_logger_extra, 'response': response.text},
                )
                # If API fails, we return error to Pub/Sub to trigger retry?
                # Or we ACK if it's a 4xx (client error, won't succeed on retry)?
                if response.status_code < 500:
                    return {'status': 'acked_api_rejected'}
                else:
                    # 5xx error, let Pub/Sub retry
                    return {'status': 'error_api_failed'}, 500

            logger.info('Successfully forwarded to API', extra=req_logger_extra)
            return {'status': 'success'}

    except Exception as e:
        logger.exception('Unexpected error in worker', extra=req_logger_extra)
        # Return 200 to ACK if we want to drop it, or 500 to retry.
        # Usually for unknown crashes we might want to ACK to avoid infinite loops if it's a poison message,
        # but for transient issues we want retry.
        # For now, let's ACK to be safe and rely on logs.
        return {'status': 'error_handled'}
