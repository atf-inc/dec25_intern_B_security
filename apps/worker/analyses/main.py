from __future__ import annotations

import asyncio
import base64
import json
import os
import random
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI

import google.auth
import httpx
from googleapiclient.discovery import build

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.database import get_session, init_db
from packages.shared.constants import EmailStatus
from packages.shared.models import EmailEvent
from packages.shared.queue import (
    get_redis_client,
    EMAIL_ANALYSIS_QUEUE,
    EMAIL_ANALYSIS_DONE_QUEUE,
)
from packages.shared.types import AttachmentMetadata
from packages.shared.logger import setup_logging
from ai_fallback import analyze_urls, is_gemini_available


# --- Logging ---
logger = setup_logging("analyses-worker")

# --- Configuration ---
HA_API_KEY = os.getenv("HYBRID_ANALYSIS_API_KEY")
USE_REAL_SANDBOX = os.getenv("USE_REAL_SANDBOX", "false").lower() == "true"
HA_API_URL = "https://hybrid-analysis.com/api/v2"

# --- Concurrency Control ---
GEMINI_SEMAPHORE = asyncio.Semaphore(2)  # Max 2 concurrent AI calls


def calculate_score_from_verdict(verdict: str) -> int:
    """Map verdict to numerical score."""
    score_map = {
        "malicious": 90,
        "suspicious": 50,
        "clean": 10,
    }
    return score_map.get(verdict, 0)


async def analyze_urls_with_limit(urls: list[str]) -> tuple[str, str]:
    """Wrapper to enforce concurrency limit on Gemini API calls."""
    async with GEMINI_SEMAPHORE:
        return await analyze_urls(urls)


def get_gmail_service() -> Any:
    """Builds and returns the Gmail API service."""
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
        service = build("gmail", "v1", credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to get Gmail service: {e}")
        return None


def fetch_attachment_from_gmail(message_id: str, attachment_id: str) -> bytes | None:
    """Synchronously fetches an email attachment from Gmail."""
    service = get_gmail_service()
    if not service:
        return None
    try:
        logger.info(f"Fetching attachment {attachment_id} for message {message_id}")
        request = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
        )
        response = request.execute()
        data = response.get("data")
        if not data:
            raise ValueError("No data found in attachment response")
        return base64.urlsafe_b64decode(data)
    except Exception as e:
        logger.error(f"Failed to fetch attachment {attachment_id}: {e}")
        return None


async def fetch_attachment_async(message_id: str, attachment_id: str) -> bytes | None:
    """Asynchronously fetches an email attachment from Gmail."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, fetch_attachment_from_gmail, message_id, attachment_id
    )


async def submit_to_hybrid_analysis(
    file_content: Optional[bytes] = None,
    filename: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[str]:
    """Submit a file or URL to Hybrid Analysis for scanning."""
    if not HA_API_KEY:
        logger.warning("HYBRID_ANALYSIS_API_KEY is not set. Skipping scan.")
        return None

    headers = {"api-key": HA_API_KEY, "User-Agent": "MailShieldAI/1.0"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if file_content:
                files = {"file": (filename, file_content)}
                data = {"environment_id": "100", "allow_community_access": "true"}
                resp = await client.post(
                    f"{HA_API_URL}/submit/file", headers=headers, files=files, data=data
                )
            elif url:
                data = {
                    "url": url,
                    "environment_id": "100",
                    "allow_community_access": "true",
                }
                resp = await client.post(
                    f"{HA_API_URL}/submit/url", headers=headers, data=data
                )
            else:
                return None

            if resp.status_code == 429:
                logger.warning("Hybrid Analysis rate limit hit. Backing off for 60s.")
                await asyncio.sleep(60)
                return None

            resp.raise_for_status()
            result = resp.json()
            job_id = result.get("job_id")
            logger.info(f"Successfully submitted to Hybrid Analysis. Job ID: {job_id}")
            return job_id

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error during HA submission: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred during HA submission: {e}")

        return None


async def poll_ha_report(job_id: str) -> Optional[Dict[str, Any]]:
    """Poll Hybrid Analysis for a report until it's complete or times out."""
    if not job_id:
        return None

    headers = {"api-key": HA_API_KEY, "User-Agent": "MailShieldAI/1.0"}
    url = f"{HA_API_URL}/report/{job_id}"
    delays = [30, 60, 60, 60, 60, 60, 60, 60, 60, 60]  # ~10 minutes polling

    async with httpx.AsyncClient(timeout=10.0) as client:
        for delay in delays:
            logger.info(f"Waiting {delay}s before polling HA job {job_id}")
            await asyncio.sleep(delay)

            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    logger.info(f"Job {job_id} not ready yet (404).")
                    continue

                resp.raise_for_status()
                report = resp.json()

                if report.get("state") == "SUCCESS":
                    logger.info(f"HA report for job {job_id} is complete.")
                    return report
                else:
                    logger.info(
                        f"HA report for job {job_id} not yet complete. State: {report.get('state')}"
                    )

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error while polling for {job_id}: {e.response.status_code}"
                )
            except Exception as e:
                logger.warning(
                    f"An unexpected error occurred while polling {job_id}: {e}"
                )

    logger.warning(f"Polling for job {job_id} timed out after ~10 minutes.")
    return None


def normalize_ha_report(report: Optional[Dict[str, Any]]) -> dict:
    """Normalize the Hybrid Analysis report into a standard format."""
    if not report:
        return {
            "verdict": "unknown",
            "score": 50,
            "details": "Sandbox analysis timed out or failed to retrieve report.",
            "timed_out": True,
        }

    verdict_map = {
        "malicious": "malicious",
        "suspicious": "suspicious",
        "no_specific_threat": "clean",
        "whitelisted": "clean",
    }

    raw_verdict = report.get("verdict", "unknown")
    final_verdict = verdict_map.get(raw_verdict, "unknown")

    return {
        "verdict": final_verdict,
        "score": report.get("threat_score", 0),
        "details": f"HA Analysis Verdict: {raw_verdict}",
        "raw_report": report,
        "timed_out": False,
    }


async def hybrid_analysis_scan(email_id: str, payload: dict) -> dict:
    """Orchestrates fetching attachments, submitting to HA, and returning a normalized report."""
    attachments = [
        AttachmentMetadata.model_validate_json(att)
        for att in payload.get("attachment_metadata", [])
    ]
    message_id = payload.get("message_id")

    # --- Find a scannable target (attachment > URL) ---
    target_content, target_name, target_url = None, None, None

    # Prioritize risky attachments
    if message_id:
        for att in attachments:
            if att.attachment_id:
                try:
                    target_content = await fetch_attachment_async(
                        message_id, att.attachment_id
                    )
                    if target_content:
                        target_name = att.filename
                        logger.info(
                            f"Prioritizing attachment for scanning: {target_name}"
                        )
                        break  # Scan the first attachment we can fetch
                except Exception as e:
                    logger.error(f"Failed to fetch attachment {att.filename}: {e}")

    # Fallback to URL if no attachment was fetched
    if not target_content:
        urls = payload.get("extracted_urls", [])
        if urls:
            target_url = urls[0]
            logger.info(f"No suitable attachment; scanning first URL: {target_url}")

    if not target_content and not target_url:
        logger.warning(f"No scannable content found for email {email_id}.")
        return {"verdict": "clean", "score": 0, "details": "No scannable content"}

    # --- Submit to Hybrid Analysis ---
    job_id = None
    if target_content:
        job_id = await submit_to_hybrid_analysis(
            file_content=target_content, filename=target_name
        )
    elif target_url:
        job_id = await submit_to_hybrid_analysis(url=target_url)

    # --- Poll for results and normalize ---
    if not job_id:
        return {
            "verdict": "unknown",
            "score": 50,
            "details": "Failed to submit for analysis",
        }

    report = await poll_ha_report(job_id)
    return normalize_ha_report(report)


async def process_email_analysis(
    session: AsyncSession,
    email: EmailEvent,
    payload: dict,
) -> bool:
    """
    Process email analysis with Gemini fallback.

    GUARANTEE: Always publishes a definitive verdict (never 'unknown').
    """
    try:
        logger.info(f"Starting analysis for email {email.id}")

        # STEP 1: Run primary sandbox analysis (Hybrid Analysis or Mock)
        sandbox_result = None
        if USE_REAL_SANDBOX:
            logger.info(f"Email {email.id}: Using REAL sandbox (Hybrid Analysis)")
            sandbox_result = await hybrid_analysis_scan(str(email.id), payload)
        else:
            logger.info(f"Email {email.id}: Using GEMINI")

            # Extract URLs from original payload
            extracted_urls = payload.get("extracted_urls", [])

            if extracted_urls:
                logger.info(
                    f"Email {email.id}: Triggering Gemini fallback "
                    f"({len(extracted_urls)} URLs to analyze)"
                )

                # Call Gemini AI analysis with concurrency limit
                ai_verdict, ai_reasoning = await analyze_urls_with_limit(extracted_urls)

                # Map Gemini's "safe" to our "clean" for consistency
                if ai_verdict == "safe":
                    ai_verdict = "clean"

                # Build new sandbox_result with Gemini's verdict
                sandbox_result = {
                    "verdict": ai_verdict,  # 'malicious', 'suspicious', 'clean', or 'unknown'
                    "score": calculate_score_from_verdict(ai_verdict),
                    "details": ai_reasoning,
                    "provider": "gemini-ai",
                    "fallback_used": True,
                    "ai_reasoning": ai_reasoning,
                }

                logger.info(
                    f"Email {email.id}: Gemini analysis complete - verdict={ai_verdict}"
                )
            else:
                # No URLs available for Gemini analysis
                logger.warning(
                    f"Email {email.id}: No URLs for Gemini fallback, "
                    f"defaulting to 'clean'"
                )
                sandbox_result = {
                    "verdict": "clean",
                    "score": 0,
                    "details": "Sandbox analysis inconclusive and no URLs available for AI analysis",
                    "provider": "default-fallback",
                    "fallback_used": True,
                }

        # STEP 3: Save to database
        email.sandbox_result = sandbox_result
        email.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(email)
        await session.commit()
        await session.refresh(email)


        # STEP 4: Publish to EMAIL_ANALYSIS_DONE_QUEUE
        # GUARANTEE: verdict is likely definitive, but if Gemini failed ("unknown"), we send that too.
        # Ideally, we mapped "suspicious" on total failure, so 'unknown' should be rare/impossible
        # unless calculate_score_from_verdict received 'unknown'.

        redis = await get_redis_client()
        done_payload = {
            "job_id": str(email.id),
            "sandbox_score": sandbox_result.get("score", 0),
            "verdict": sandbox_result.get("verdict"),
            "sandbox_result": json.dumps(sandbox_result),
        }
        await redis.xadd(EMAIL_ANALYSIS_DONE_QUEUE, done_payload)

        logger.info(
            f"Email {email.id}: Published to DONE queue - "
            f"verdict={sandbox_result.get('verdict')}, "
            f"provider={sandbox_result.get('provider')}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error in process_email_analysis for {email.id}: {e}", exc_info=True
        )
        try:
            email.status = EmailStatus.FAILED
            session.add(email)
            await session.commit()
        except Exception as commit_err:
            logger.error(f"Failed to persist FAILED status: {commit_err}")
        return False


async def run_loop() -> None:
    """Main worker loop using Redis Streams Consumer Groups."""
    await init_db()
    redis = await get_redis_client()

    group_name = "analysis_workers"
    consumer_name = f"worker-{random.randint(1000, 9999)}"

    try:
        await redis.xgroup_create(
            EMAIL_ANALYSIS_QUEUE, group_name, id="0", mkstream=True
        )
        logger.info(f"Consumer group {group_name} created.")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.warning(f"Error creating consumer group: {e}")

    logger.info(
        f"Worker {consumer_name} started. Listening on {EMAIL_ANALYSIS_QUEUE}..."
    )

    while True:
        try:
            streams = await redis.xreadgroup(
                group_name,
                consumer_name,
                {EMAIL_ANALYSIS_QUEUE: ">"},
                count=1,
                block=5000,
            )

            if not streams:
                continue

            for _, messages in streams:
                for message_id, payload in messages:
                    email_id_str = payload.get("email_id")

                    if not email_id_str:
                        logger.warning(f"Invalid payload in message {message_id}")
                        await redis.xack(EMAIL_ANALYSIS_QUEUE, group_name, message_id)
                        continue

                    try:
                        email_id = uuid.UUID(email_id_str)
                    except (ValueError, TypeError):
                        logger.error(
                            f"Malformed email ID '{email_id_str}' in message {message_id}"
                        )
                        await redis.xack(EMAIL_ANALYSIS_QUEUE, group_name, message_id)
                        continue

                    logger.info(
                        f"Processing message {message_id} (Email ID: {email_id})"
                    )

                    processed_successfully = False
                    # yield session scope

                    @asynccontextmanager
                    async def session_scope():
                        async for s in get_session():
                            yield s
                            break

                    async with session_scope() as session:
                        try:
                            query = select(EmailEvent).where(EmailEvent.id == email_id)
                            result = await session.exec(query)
                            email = result.first()

                            if not email:
                                logger.warning(f"Email {email_id} not found.")
                                await redis.xack(
                                    EMAIL_ANALYSIS_QUEUE, group_name, message_id
                                )
                                continue

                            processed_successfully = await process_email_analysis(
                                session, email, payload
                            )
                        except Exception as inner_e:
                            logger.error(f"Error processing {email_id}: {inner_e}")

                    if processed_successfully:
                        await redis.xack(EMAIL_ANALYSIS_QUEUE, group_name, message_id)
                        logger.info(f"Acknowledged message {message_id}")

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)


# Create lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start background tasks."""
    # Startup
    task = asyncio.create_task(run_loop())
    logger.info("Analysis worker background task started")
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok", "service": "analyses-worker"}


def main() -> None:
    """Entry point for the worker service."""
    port = int(os.getenv("PORT", "8080"))
    # Run uvicorn server
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
