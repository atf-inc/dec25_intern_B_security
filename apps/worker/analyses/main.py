from __future__ import annotations

import asyncio
import base64
import os
import random
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import google.auth
import httpx
from googleapiclient.discovery import build

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pythonjsonlogger import json as jsonlogger

from packages.shared.database import get_session, init_db
from packages.shared.constants import EmailStatus
from packages.shared.models import EmailEvent
from packages.shared.queue import get_redis_client, EMAIL_ANALYSIS_QUEUE
from packages.shared.types import AttachmentMetadata


# --- Logging ---
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(fmt="%(asctime)s %(levelname)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# --- Configuration ---
HA_API_KEY = os.getenv("HYBRID_ANALYSIS_API_KEY")
USE_REAL_SANDBOX = os.getenv("USE_REAL_SANDBOX", "false").lower() == "true"
HA_API_URL = "https://hybrid-analysis.com/api/v2"


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
    """Process a single email event through the analysis agent."""
    try:
        logger.info(f"Starting sandbox analysis for email {email.id}")

        # --- Phase 1: Attachment Fetching ---
        attachments = [
            AttachmentMetadata.model_validate_json(att)
            for att in payload.get("attachment_metadata", [])
        ]
        message_id = payload.get("message_id")
        fetched_attachments = {}

        if message_id:
            for att in attachments:
                if att.attachment_id:
                    try:
                        attachment_bytes = await fetch_attachment_async(
                            message_id, att.attachment_id
                        )
                        if attachment_bytes:
                            fetched_attachments[att.filename] = len(attachment_bytes)
                            logger.info(
                                f"Successfully fetched {att.filename}: {len(attachment_bytes)} bytes"
                            )
                        else:
                            logger.warning(
                                f"Failed to fetch attachment {att.filename} for message {message_id}"
                            )
                    except Exception as e:
                        logger.error(f"Error fetching attachment {att.filename}: {e}")

        # --- Mock Sandbox Logic (Phase 2 will replace this) ---
        await asyncio.sleep(2)  # Simulate analysis time

        sandbox_result = {
            "verdict": "clean",
            "score": 10,
            "details": "Simulated scan. Attachment fetch testing complete.",
            "urls_scanned": payload.get("extracted_urls", []),
            "attachments_scanned": [att.filename for att in attachments],
            "attachments_fetched": fetched_attachments,
        }

        email.sandbox_result = sandbox_result
        email.status = EmailStatus.COMPLETED
        email.updated_at = datetime.now(timezone.utc)

        session.add(email)
        await session.commit()
        await session.refresh(email)
        logger.info(f"Sandbox analysis completed for email {email.id}")
        return True

    except Exception as e:
        logger.error(f"Error in process_email_analysis: {e}")
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
                    from contextlib import asynccontextmanager

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


def main() -> None:
    """Entry point for the worker service."""
    logger.info("Starting analysis worker...")
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
