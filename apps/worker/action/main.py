"""
Action Agent - The Enforcer

This is the third and final agent in the MailShieldAI security pipeline.
It consumes security verdicts from the Decision Agent, applies Gmail labels,
and uses Gemini AI as a fallback for "unknown" verdicts.

Flow:
1. Receive UnifiedDecisionPayload from Decision Agent
2. If verdict is "unknown", trigger Gemini AI analysis of URLs
3. Apply appropriate Gmail label (MailShield/MALICIOUS, CAUTIOUS, or SAFE)
4. For malicious emails, optionally move to Spam folder
5. Log action for audit trail

Author: MailShieldAI Team
"""

import os
import logging
import asyncio
from typing import Optional, Set, Literal

from fastapi import FastAPI, BackgroundTasks, status
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger
import google.auth
from googleapiclient.discovery import build
from dotenv import load_dotenv

from gmail_labels import apply_labels, ensure_labels_exist, get_label_for_verdict
from ai_fallback import analyze_urls, is_gemini_available

load_dotenv()

# --- Configuration ---
PORT = int(os.getenv("PORT", "9001"))  # Different port from Decision Agent (8080)
MOVE_MALICIOUS_TO_SPAM = os.getenv("MOVE_MALICIOUS_TO_SPAM", "true").lower() == "true"

# --- Concurrency Control ---
# Limit concurrent Gmail/Gemini API calls to avoid rate limits
GMAIL_SEMAPHORE = asyncio.Semaphore(5)  # Gmail allows ~5-10 modify/sec
GEMINI_SEMAPHORE = asyncio.Semaphore(2)  # Conservative for AI calls

# --- Logging ---
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(fmt="%(asctime)s %(levelname)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# --- State: In-memory Idempotency ---
# Tracks message_ids that have already been processed
# TODO: For production, use Redis/DB for cross-replica persistence
processed_messages: Set[str] = set()


# --- Models ---
class SandboxResult(BaseModel):
    """Result from sandbox analysis."""
    verdict: Literal["malicious", "suspicious", "clean", "unknown"]
    score: int
    family: Optional[str] = None
    confidence: float = 0.0


class DecisionMetadata(BaseModel):
    """Metadata about how the decision was made."""
    provider: str
    timed_out: bool = False
    reason: Optional[str] = None


class UnifiedDecisionPayload(BaseModel):
    """
    Payload received from the Decision Agent.
    Contains the security verdict and metadata.
    """
    message_id: str
    static_risk_score: int
    sandboxed: bool
    sandbox_result: Optional[SandboxResult] = None
    decision_metadata: DecisionMetadata
    # Optional: URLs for Gemini fallback (may be passed from ingest)
    extracted_urls: Optional[list[str]] = None


class ActionResult(BaseModel):
    """Result of the action taken."""
    message_id: str
    original_verdict: str
    final_verdict: str
    label_applied: str
    moved_to_spam: bool
    ai_analysis_used: bool
    ai_reasoning: Optional[str] = None


# --- Gmail Service ---
def get_gmail_service():
    """
    Builds and returns the Gmail API service using ADC.
    Note: Action Agent needs gmail.modify scope (not just readonly).
    """
    creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/gmail.modify'])
    return build('gmail', 'v1', credentials=creds)


# --- Core Processing Logic ---
async def process_action(payload: UnifiedDecisionPayload) -> ActionResult:
    """
    Main processing logic for applying actions based on security verdict.
    
    1. Check idempotency
    2. Determine verdict (with Gemini fallback for "unknown")
    3. Apply Gmail labels
    4. Return audit result
    """
    message_id = payload.message_id
    
    # Idempotency check
    if message_id in processed_messages:
        logger.info(f"Message {message_id} already processed, skipping")
        return ActionResult(
            message_id=message_id,
            original_verdict="skipped",
            final_verdict="skipped",
            label_applied="none",
            moved_to_spam=False,
            ai_analysis_used=False
        )
    
    processed_messages.add(message_id)
    
    # Determine original verdict
    original_verdict = "clean"  # Default
    if payload.sandbox_result:
        original_verdict = payload.sandbox_result.verdict
    
    final_verdict = original_verdict
    ai_reasoning = None
    ai_used = False
    
    # Gemini fallback for unknown verdicts
    if original_verdict == "unknown" and payload.extracted_urls:
        logger.info(f"Triggering Gemini fallback for {message_id}")
        async with GEMINI_SEMAPHORE:
            ai_verdict, ai_reasoning = await analyze_urls(payload.extracted_urls)
            final_verdict = ai_verdict
            ai_used = True
            logger.info(
                f"Gemini resolved unknown -> {ai_verdict}",
                extra={"message_id": message_id, "reason": ai_reasoning[:100] if ai_reasoning else None}
            )
    elif original_verdict == "unknown":
        # No URLs to analyze, default to cautious
        final_verdict = "suspicious"
        ai_reasoning = "No URLs available for analysis, defaulting to cautious"
    
    # Determine if we should move to spam
    move_to_spam = MOVE_MALICIOUS_TO_SPAM and final_verdict == "malicious"
    
    # Apply Gmail labels
    label_applied = get_label_for_verdict(final_verdict)
    
    try:
        async with GMAIL_SEMAPHORE:
            service = get_gmail_service()
            success = await apply_labels(
                service=service,
                message_id=message_id,
                verdict=final_verdict,
                move_to_spam=move_to_spam
            )
            
            if not success:
                logger.error(f"Failed to apply labels to {message_id}")
                label_applied = "FAILED"
    except Exception as e:
        logger.error(f"Gmail labeling failed for {message_id}: {e}", exc_info=True)
        label_applied = f"ERROR: {str(e)[:50]}"
    
    # Log the action for audit
    logger.info(
        "Action completed",
        extra={
            "message_id": message_id,
            "original_verdict": original_verdict,
            "final_verdict": final_verdict,
            "label_applied": label_applied,
            "moved_to_spam": move_to_spam,
            "ai_used": ai_used
        }
    )
    
    return ActionResult(
        message_id=message_id,
        original_verdict=original_verdict,
        final_verdict=final_verdict,
        label_applied=label_applied,
        moved_to_spam=move_to_spam,
        ai_analysis_used=ai_used,
        ai_reasoning=ai_reasoning
    )


async def process_action_background(payload: UnifiedDecisionPayload):
    """Background wrapper for process_action with error handling."""
    try:
        await process_action(payload)
    except Exception as e:
        logger.error(f"Unhandled error processing {payload.message_id}: {e}", exc_info=True)


# --- FastAPI App ---
app = FastAPI(
    title="Action Agent",
    description="Applies Gmail labels based on security verdicts from Decision Agent",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize on startup:
    1. Check Gemini availability
    2. Pre-create MailShield labels (optional, handles race conditions)
    """
    logger.info("Starting Action Agent...")
    
    # Check Gemini
    gemini_ok = await is_gemini_available()
    if gemini_ok:
        logger.info("✓ Gemini AI fallback is available")
    else:
        logger.warning("⚠ Gemini AI fallback is NOT available (check GEMINI_API_KEY)")
    
    # Try to pre-create labels (soft fail, will be created on-demand anyway)
    try:
        service = get_gmail_service()
        await ensure_labels_exist(service)
        logger.info("✓ MailShield labels initialized")
    except Exception as e:
        logger.warning(f"Could not pre-create labels (will create on-demand): {e}")
    
    logger.info(f"Action Agent started on port {PORT}")


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    gemini_ok = await is_gemini_available()
    return {
        "status": "ok",
        "service": "action-agent",
        "gemini_available": gemini_ok,
        "processed_count": len(processed_messages)
    }


@app.post("/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_action(
    payload: UnifiedDecisionPayload,
    background_tasks: BackgroundTasks
):
    """
    Execute security action based on Decision Agent verdict.
    
    - malicious → MailShield/MALICIOUS label + move to Spam
    - suspicious → MailShield/CAUTIOUS label
    - clean → MailShield/SAFE label
    - unknown → Gemini AI analysis → appropriate action
    """
    logger.info(
        "Received action request",
        extra={
            "message_id": payload.message_id,
            "verdict": payload.sandbox_result.verdict if payload.sandbox_result else "none"
        }
    )
    
    # Process in background to return immediately
    background_tasks.add_task(process_action_background, payload)
    
    return {
        "status": "accepted",
        "message_id": payload.message_id,
        "queued": True
    }


@app.post("/execute-sync", status_code=status.HTTP_200_OK)
async def execute_action_sync(payload: UnifiedDecisionPayload) -> ActionResult:
    """
    Synchronous version of execute for testing.
    Returns the full action result immediately.
    """
    return await process_action(payload)


@app.get("/stats")
async def get_stats():
    """Get processing statistics."""
    return {
        "processed_messages": len(processed_messages),
        "recent_messages": list(processed_messages)[-10:]  # Last 10
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
