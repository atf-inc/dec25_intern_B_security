import os
import base64
import json
import logging
import requests
import re
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import socket

# --- Configuration ---
# In production, these would be loaded from Secret Manager or Env Vars
DECISION_AGENT_URL = os.getenv("DECISION_AGENT_URL") # Don't set default here to test startup validation
PORT = int(os.getenv("PORT", "8080"))

# --- Logging Setup ---
# Structured JSON logging for Cloud Logging compatibility
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# --- FastAPI App ---
app = FastAPI(title="Email Ingest Agent")

@app.on_event("startup")
async def startup_event():
    """Fail fast on critical configuration errors."""
    logger.info("Starting Email Ingest Agent...")
    
    # 1. Critical Config Check
    if not DECISION_AGENT_URL:
        logger.critical("DECISION_AGENT_URL environment variable is not set. Exiting.")
        raise RuntimeError("DECISION_AGENT_URL environment variable is not set.")
        
    # 2. Auth Check (Soft fail)
    try:
        get_gmail_service()
        logger.info("Gmail Service initialized successfully (ADC found).")
    except Exception as e:
        logger.warning(f"Could not initialize Gmail Service on startup (Auth might be missing?): {e}")
        # We allow startup because IAM might propagate later or this is a dev env.

# --- Models ---
class PubSubMessage(BaseModel):
    data: str
    messageId: str
    publishTime: str
    attributes: Optional[Dict[str, str]] = None

class PubSubBody(BaseModel):
    message: PubSubMessage
    subscription: str

class AttachmentMetadata(BaseModel):
    filename: str
    mime_type: str
    size: int

class StructuredEmailPayload(BaseModel):
    message_id: str
    sender: str
    subject: str
    extracted_urls: List[str]
    attachment_metadata: List[AttachmentMetadata]

# --- Helpers ---
def decode_pubsub_data(data_base64: str) -> Dict[str, Any]:
    """Decodes the Base64 encoded Pub/Sub message data."""
    try:
        decoded_bytes = base64.b64decode(data_base64)
        decoded_str = decoded_bytes.decode("utf-8")
        return json.loads(decoded_str)
    except Exception as e:
        logger.error(f"Failed to decode Pub/Sub data: {e}", extra={"error": str(e)})
        raise ValueError(f"Invalid Pub/Sub data: {e}")

def get_gmail_service():
    """
    Builds and returns the Gmail API service using ADC.
    Sets default timeout to avoid hanging connections.
    """
    # Enforce default socket timeout (global for this process, simple but effective)
    socket.setdefaulttimeout(10) # 10 seconds for Gmail API interactions
    creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/gmail.readonly'])
    return build('gmail', 'v1', credentials=creds)

def extract_message_content(message_detail: Dict[str, Any]) -> StructuredEmailPayload:
    """
    Pure logic function to extract data from Gmail message JSON.
    Parses MIME structure (nested parts) to find URLs and attachments.
    """
    msg_id = message_detail.get('id', 'unknown')
    payload = message_detail.get('payload', {})
    headers = payload.get('headers', [])
    
    # Extract Headers
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
    
    extracted_urls = set()
    attachment_metadata = []

    def walk_parts(part):
        mime_type = part.get('mimeType', '')
        body = part.get('body', {})
        data = body.get('data')
        filename = part.get('filename')

        # 1. Attachment Handling (Metadata only)
        if filename and body.get('attachmentId'):
            attachment_metadata.append(AttachmentMetadata(
                filename=filename,
                mime_type=mime_type,
                size=body.get('size', 0)
            ))
            # Do NOT fetch attachment content (security constraint)
            return

        # 2. Body Content Handling (URLs)
        if mime_type in ['text/plain', 'text/html'] and data:
            try:
                # Gmail API uses Base64URL encoding
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                # Simple regex for URLs - can be refined
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', decoded_data)
                extracted_urls.update(urls)
            except Exception as e:
                logger.warning(f"Failed to decode part body in {msg_id}: {e}")

        # 3. Recursion
        if 'parts' in part:
            for subpart in part['parts']:
                walk_parts(subpart)
        # Handle payload valid for non-multipart
        if 'parts' not in part and not filename and mime_type.startswith('multipart'):
             # This handles cases where multipart info might be nested differently or top level
             # But 'parts' usually exists. Check payload.
             pass 

    # Start recursion from top-level payload
    walk_parts(payload)

    return StructuredEmailPayload(
        message_id=msg_id,
        sender=sender,
        subject=subject,
        extracted_urls=list(extracted_urls),
        attachment_metadata=attachment_metadata
    )

def process_gmail_event(email_address: str, history_id: int) -> List[StructuredEmailPayload]:
    """
    Orchestrates Gmail API calls:
    1. Auth (ADC).
    2. List history to find changed messages.
    3. Fetch full message details.
    4. Extract content.
    """
    service = get_gmail_service()
    payloads = []

    try:
        # 1. List History
        logger.info(f"Querying history for {email_address} since {history_id}")
        history_response = service.users().history().list(
            userId='me', 
            startHistoryId=history_id
        ).execute()

        # Handle "HistoryId Not Found" (404-like logic or just empty history)
        # If historyId is too old, Gmail returns historyIdNotFound error usually raised by execute()
        # This block handles valid response but maybe no history.
        if 'history' not in history_response:
             logger.info("No history found for this ID (might be up to date)")
             return []

        # 2. Deduplicate Messages
        message_ids = set()
        for record in history_response['history']:
            if 'messagesAdded' in record:
                for msg in record['messagesAdded']:
                    if 'message' in msg and 'id' in msg['message']:
                        message_ids.add(msg['message']['id'])
        
        logger.info(f"Found {len(message_ids)} new messages")

        # 3. Fetch & Extract
        for msg_id in message_ids:
            try:
                message_detail = service.users().messages().get(
                    userId='me', 
                    id=msg_id, 
                    format='full'
                ).execute()
                
                structured = extract_message_content(message_detail)
                payloads.append(structured)
            except Exception as e:
                logger.error(f"Failed to fetch/extract message {msg_id}: {e}")
                # Continue processing other messages
                continue

    except HttpError as e:
        if e.resp.status == 404:
            logger.warning("History ID not found (too old). synchronizing...", extra={"historyId": history_id})
            # In a real sync engine, we'd do a full sync. Here we just skip/ACK as per plan.
            return []
        else:
            logger.error(f"Gmail API error: {e}")
            raise # Let outer handler catch and decided whether to ACK

    return payloads

def forward_to_decision_agent(payload: StructuredEmailPayload, trace_context: Optional[str] = None):
    """
    Forwards the structured payload to the Decision Agent.
    """
    headers = {}
    if trace_context:
        headers["X-Cloud-Trace-Context"] = trace_context

    try:
        logger.info("Forwarding payload to Decision Agent", extra={"url": DECISION_AGENT_URL, "message_id": payload.message_id, "trace_context": trace_context})
        response = requests.post(
            DECISION_AGENT_URL,
            json=payload.model_dump(),
            headers=headers,
            timeout=5 
        )
        response.raise_for_status()
        logger.info("Successfully forwarded to Decision Agent", extra={"status_code": response.status_code, "trace_context": trace_context})
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to forward msg {payload.message_id}: {e}", extra={"error": str(e), "trace_context": trace_context})
        raise # Raise so caller knows this specific one failed (for metrics) but caller handles try/except


# --- Endpoints ---

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}

@app.post("/")
async def receive_pubsub_push(body: PubSubBody, request: Request):
    """
    Handle incoming Pub/Sub push messages.
    """
    # 0. Trace Context
    trace_context = request.headers.get("X-Cloud-Trace-Context")
    
    # Bind logger with trace context for this request scope logic
    # (Using local extra= param is simpler for now than context vars, effectively done below)
    req_logger_extra = {"trace_context": trace_context, "messageId": body.message.messageId}

    try:
        # 1. Log receipt
        logger.info("Received Pub/Sub message", extra=req_logger_extra)

        # 2. Decode the inner data
        decoded_data = decode_pubsub_data(body.message.data)
        
        email_address = decoded_data.get("emailAddress", "me") # 'me' is valid for Gmail API with service account
        history_id = decoded_data.get("historyId")

        if not history_id:
            logger.warning("No historyId found in message", extra={"data": decoded_data, "trace_context": trace_context})
            return {"status": "acked", "reason": "missing_history_id"}

        # 3. Process Gmail Event (Real API)
        # Note: This might return empty list, one, or multiple payloads.
        structured_payloads = process_gmail_event(email_address, history_id)

        # 4. Forward Each With Error Isolation
        results = []
        for payload in structured_payloads:
            try:
                forward_to_decision_agent(payload, trace_context=trace_context)
                results.append({"msg_id": payload.message_id, "status": "success"})
            except Exception:
                # Log error but CONTINUE the loop
                logger.error(f"Failed to process/forward message {payload.message_id}", exc_info=True, extra=req_logger_extra)
                results.append({"msg_id": payload.message_id, "status": "failed"})

        # 5. ACK (Always return 200 unless critical system failure)
        return {"status": "success", "results": results}

    except Exception as e:
        logger.exception("Unexpected error processing message", extra=req_logger_extra)
        # Return 200 to ACK Pub/Sub to prevent retry of bad message (unless it's a transient server error we want to retry? 
        # For this exercise, we prioritize system stability -> ACK)
        return {"status": "error_handled"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
