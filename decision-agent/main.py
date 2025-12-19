import os
import logging
import asyncio
import json
import requests
import httpx
from typing import List, Optional, Dict, Any, Literal, Set
from fastapi import FastAPI, BackgroundTasks, status
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger
import google.auth
from googleapiclient.discovery import build
import base64
import time
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
FINAL_AGENT_URL = os.getenv("FINAL_AGENT_URL", "http://localhost:9001")
HA_API_KEY = os.getenv("HYBRID_ANALYSIS_API_KEY") # Required for Phase 2B
USE_REAL_SANDBOX = os.getenv("USE_REAL_SANDBOX", "true").lower() == "true"
HA_API_URL = "https://www.hybrid-analysis.com/api/v2"
PORT = int(os.getenv("PORT", "8080"))

# --- Logging ---
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(fmt="%(asctime)s %(levelname)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# --- State (Phase 2A: In-memory Idempotency) ---
seen_messages: Set[str] = set()

# --- Models ---
class AttachmentMetadata(BaseModel):
    filename: str
    mime_type: str
    size: int
    attachment_id: Optional[str] = None

class StructuredEmailPayload(BaseModel):
    message_id: str
    sender: str
    subject: str
    extracted_urls: List[str]
    attachment_metadata: List[AttachmentMetadata]

class SandboxResult(BaseModel):
    verdict: Literal["malicious", "suspicious", "clean", "unknown"]
    score: int
    family: Optional[str] = None
    confidence: float = 0.0

class DecisionMetadata(BaseModel):
    provider: str
    timed_out: bool = False
    reason: Optional[str] = None

class UnifiedDecisionPayload(BaseModel):
    message_id: str
    static_risk_score: int
    sandboxed: bool
    sandbox_result: Optional[SandboxResult] = None
    decision_metadata: DecisionMetadata

# --- Risk Gate Logic (Pure, Deterministic) ---
RISKY_EXTENSIONS = {'.exe', '.scr', '.vbs', '.js', '.bat', '.iso', '.dll', '.ps1'}

def evaluate_static_risk(payload: StructuredEmailPayload) -> tuple[bool, str, int]:
    """
    Evaluates static indicators to decide if sandboxing is needed.
    Returns: (should_sandbox, reason, static_risk_score)
    """
    score = 0
    reasons = []
    should_sandbox = False

    # 1. Attachment Check
    for att in payload.attachment_metadata:
        ext = os.path.splitext(att.filename)[1].lower()
        if ext in RISKY_EXTENSIONS:
            score += 70
            reasons.append(f"Risky extension {ext}")
            should_sandbox = True
        elif att.mime_type == "application/zip":
            score += 30
            reasons.append("Archive attachment")
            should_sandbox = True # Inspecting zips is standard

    # 2. URL Check (Basic heuristics for Phase 2A)
    if len(payload.extracted_urls) > 0:
        score += 10 # Presence of URLs
        if len(payload.extracted_urls) > 3:
            score += 20
            reasons.append("Many URLs")
            should_sandbox = True 

    # Normalize score
    score = min(score, 100)
    reason_str = "; ".join(reasons) if reasons else "Low static risk"
    
    # Fail-safe
    if score > 50:
        should_sandbox = True
        
    return should_sandbox, reason_str, score

# --- Mock Sandbox Logic (Phase 2A) ---
async def simulate_sandbox_scan(payload: StructuredEmailPayload) -> SandboxResult:
    """Simulates a call to Hybrid Analysis."""
    logger.info(f"Simulating sandbox scan for {payload.message_id}...")
    await asyncio.sleep(2.0)
    
    if "urgent" in payload.subject.lower() or "invoice" in payload.subject.lower():
         return SandboxResult(verdict="malicious", score=90, family="MockTrojan", confidence=0.99)
    
    return SandboxResult(verdict="clean", score=0, confidence=1.0)

# --- Helper: Gmail Lazy Fetch (Phase 2B) ---
def get_gmail_service():
    """Builds and returns the Gmail API service using ADC (same as Ingest Agent)."""
    # Note: Decision Agent needs roles/gmail.readonly identity
    creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/gmail.readonly'])
    return build('gmail', 'v1', credentials=creds)

def fetch_attachment_from_gmail(message_id: str, attachment_id: str) -> bytes:
    """Lazily fetches the actual attachment content from Gmail (Blocking)."""
    try:
        service = get_gmail_service()
        logger.info(f"Fetching attachment {attachment_id} for Msg {message_id}...")
        resp = service.users().messages().attachments().get(
            userId='me',
            id=attachment_id,
            messageId=message_id
        ).execute()
        
        data = resp.get('data')
        if not data:
            raise ValueError("No data found in attachment response")
            
        return base64.urlsafe_b64decode(data)
    except Exception as e:
        logger.error(f"Failed to fetch attachment from Gmail: {e}")
        raise

async def fetch_attachment_async(message_id: str, attachment_id: str) -> bytes:
    """Non-blocking wrapper for fetching attachment."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        fetch_attachment_from_gmail,
        message_id,
        attachment_id
    )

# --- Helper: Hybrid Analysis Client (Phase 2B) ---
async def submit_to_hybrid_analysis(
    file_content: Optional[bytes] = None, 
    filename: Optional[str] = None,
    url: Optional[str] = None
) -> Optional[str]:
    """
    Submits a file OR url to Hybrid Analysis V2.
    Returns: job_id (str) or None if submission failed.
    """
    if not HA_API_KEY:
        logger.warning("Skipping HA submission: No API Key found.")
        return None

    headers = {
        "api-key": HA_API_KEY,
        "User-Agent": "SecurityDecisionAgent/1.0"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if file_content:
                files = {'file': (filename, file_content)}
                data = {
                    'environment_id': '100', 
                    'allow_community_access': 'false' 
                }
                logger.info(f"Submitting file '{filename}' to Hybrid Analysis...")
                resp = await client.post(
                    f"{HA_API_URL}/submit/file", 
                    headers=headers, 
                    files=files, 
                    data=data
                )
            elif url:
                data = {
                    'url': url,
                    'environment_id': '100',
                    'allow_community_access': 'false'
                }
                logger.info(f"Submitting URL '{url}' to Hybrid Analysis...")
                resp = await client.post(
                    f"{HA_API_URL}/submit/url", 
                    headers=headers, 
                    data=data
                )
            else:
                return None

            if resp.status_code == 429:
                logger.warning("Hybrid Analysis Rate Limit (429). Backing off for 60s.")
                await asyncio.sleep(60)
                return None
            
            resp.raise_for_status()
            result = resp.json()
            job_id = result.get('job_id')
            logger.info(f"Hybrid Analysis Job Submitted. ID: {job_id}")
            return job_id

        except Exception as e:
            logger.error(f"HA Submission Failed: {e}")
            return None

async def poll_ha_report(job_id: str) -> Optional[Dict[str, Any]]:
    """Polls the report API until finished or timeout."""
    if not job_id: 
        return None
        
    headers = {"api-key": HA_API_KEY, "User-Agent": "SecurityDecisionAgent/1.0"}
    url = f"{HA_API_URL}/report/{job_id}"
    delays = [30, 60, 60, 60, 60]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for delay in delays:
            logger.info(f"Waiting {delay}s before polling HA job {job_id}...")
            await asyncio.sleep(delay)
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    logger.info(f"Job {job_id} report not found yet (404), continuing...")
                    continue
                resp.raise_for_status()
                report = resp.json()
                if report.get('verdict') is not None:
                     return report
            except Exception as e:
                logger.warning(f"Polling error for {job_id}: {e}")
    
    logger.warning(f"Job {job_id} timed out after polling.")
    return None

def normalize_ha_report(report: Dict[str, Any]) -> SandboxResult:
    """Maps HA V2 JSON to internal SandboxResult."""
    if not report:
        return SandboxResult(verdict="unknown", score=0, family="Timeout/Error")
    
    verdict_raw = report.get('verdict', 'unknown') 
    threat_score = report.get('threat_score', 0) 
    verdict_map = {
        "malicious": "malicious",
        "suspicious": "suspicious",
        "no_specific_threat": "clean",
        "whitelisted": "clean"
    }
    final_verdict = verdict_map.get(verdict_raw, "unknown")
    tags = report.get('tags', [])
    family = tags[0] if tags else None
    
    return SandboxResult(
        verdict=final_verdict,
        score=threat_score,
        family=family,
        confidence=float(report.get('threat_level', 0))/2.0
    )

async def hybrid_analysis_scan(payload: StructuredEmailPayload) -> SandboxResult:
    """Orchestrator: Fetch -> Submit -> Poll -> Normalize."""
    target_data = None
    target_name = None
    target_url = None
    
    for att in payload.attachment_metadata:
        ext = os.path.splitext(att.filename)[1].lower()
        if ext in RISKY_EXTENSIONS or att.mime_type == "application/zip":
            if att.attachment_id:
                try:
                    # Async Fetch (Non-blocking)
                    target_data = await fetch_attachment_async(payload.message_id, att.attachment_id)
                    target_name = att.filename
                    break
                except Exception as e:
                    logger.error("Failed to fetch risky attachment, falling back...")
    
    if not target_data and payload.extracted_urls:
        target_url = payload.extracted_urls[0] 
        
    if not target_data and not target_url:
        logger.warning(f"Asked to sandbox {payload.message_id} but found no actionable content.")
        return SandboxResult(verdict="unknown", score=0, family="NoContent")

    job_id = None
    if target_data:
        job_id = await submit_to_hybrid_analysis(file_content=target_data, filename=target_name)
    else:
        job_id = await submit_to_hybrid_analysis(url=target_url)

    # Check logic: if polling returns None, we treat as Timeout inside normalize
    report = await poll_ha_report(job_id)
    return normalize_ha_report(report)

# --- Async Processing ---
async def process_analysis(payload: StructuredEmailPayload):
    """Orchestrates: Risk Gate -> (Optional) Sandbox -> Unified Output -> Forward"""
    if payload.message_id in seen_messages:
        logger.warning("Duplicate message_id, skipping analysis", extra={"message_id": payload.message_id})
        return
    seen_messages.add(payload.message_id)

    logger.info(f"Starting analysis for {payload.message_id}")
    
    should_sandbox, reason, static_score = evaluate_static_risk(payload)
    logger.info(f"Risk Gate Result: sandboxed={should_sandbox} score={static_score} reason='{reason}'")
    
    sandbox_res = None
    provider = "risk-gate-only"
    timed_out = False
    
    if should_sandbox:
        try:
            if HA_API_KEY and USE_REAL_SANDBOX:
                provider = "hybrid-analysis"
                sandbox_res = await hybrid_analysis_scan(payload)
                if sandbox_res.verdict == "unknown" and sandbox_res.family == "Timeout/Error":
                     timed_out = True
            else:
                provider = "mock-hybrid-analysis"
                sandbox_res = await simulate_sandbox_scan(payload)
                
        except Exception as e:
            logger.error(f"Sandbox failed for {payload.message_id}: {e}", exc_info=True)
            sandbox_res = SandboxResult(verdict="unknown", score=50, family="Error", confidence=0.0)
            
    unified = UnifiedDecisionPayload(
        message_id=payload.message_id,
        static_risk_score=static_score,
        sandboxed=should_sandbox,
        sandbox_result=sandbox_res,
        decision_metadata=DecisionMetadata(
            provider=provider,
            timed_out=timed_out,
            reason=reason
        )
    )
    
    await forward_to_final_agent(unified)

async def forward_to_final_agent(payload: UnifiedDecisionPayload):
    try:
        logger.info("Forwarding decision to Final Agent", extra={"message_id": payload.message_id, "verdict": payload.sandbox_result.verdict if payload.sandbox_result else "skipped"})
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(FINAL_AGENT_URL, json=payload.model_dump())
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to forward decision for {payload.message_id}: {e}")

# --- FastAPI App ---
app = FastAPI(title="Decision Agent")

@app.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_email(payload: StructuredEmailPayload, background_tasks: BackgroundTasks):
    """Ingress endpoint."""
    logger.info("Received analysis request", extra={"message_id": payload.message_id})
    background_tasks.add_task(process_analysis, payload)
    return {"status": "accepted", "message_id": payload.message_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
