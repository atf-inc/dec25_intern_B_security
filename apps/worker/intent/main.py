from __future__ import annotations

import asyncio
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.database import get_session, init_db
from packages.shared.constants import EmailStatus, RiskTier
from packages.shared.models import EmailEvent
from packages.shared.queue import get_redis_client, EMAIL_INTENT_QUEUE


def classify_risk(score: int) -> RiskTier:
    if score < 30:
        return RiskTier.SAFE
    if score < 80:
        return RiskTier.CAUTIOUS
    return RiskTier.THREAT


def build_dummy_analysis(score: int) -> dict:
    return {
        "indicators": ["suspicious_link", "urgency_language"],
        "confidence": round(min(1.0, max(0.0, score / 100)), 2),
        "threat_type": "phishing" if score >= 50 else "info",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def _create_gmail_label_sync(service, label_name: str) -> str:
    """
    Synchronous helper to create Gmail label.
    Returns the label ID or None.
    """
    from googleapiclient.errors import HttpError
    
    # First, check if label already exists
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:
            if label['name'] == label_name:
                print(f"Label '{label_name}' already exists")
                return label['id']
    except HttpError as e:
        print(f"Error listing labels: {e}")
        return None
    
    # Label doesn't exist, create it
    # Note: Gmail will auto-assign colors, custom colors require specific palette codes
    label_config = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    
    try:
        result = service.users().labels().create(userId='me', body=label_config).execute()
        label_id = result.get('id')
        print(f"✓ Created Gmail label '{label_name}' with ID: {label_id}")
        return label_id
    except HttpError as e:
        print(f"Failed to create label '{label_name}': {e}")
        return None


async def create_gmail_label(service, label_name: str) -> str:
    """
    Create a Gmail label if it doesn't exist.
    Returns the label ID.
    Runs synchronous Gmail API calls in thread pool.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _create_gmail_label_sync, service, label_name)


async def get_fresh_access_token(refresh_token: str) -> str:
    """
    Use refresh_token to get a fresh access_token from Google OAuth.
    Returns the access token string.
    """
    import os
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    
    # Get OAuth credentials from environment
    client_id = os.getenv('AUTH_GOOGLE_ID')
    client_secret = os.getenv('AUTH_GOOGLE_SECRET')
    
    if not client_id or not client_secret:
        raise ValueError("AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET must be set in environment")
    
    # Create credentials object with refresh token
    creds = Credentials(
        token=None,  # No access token yet
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=['https://www.googleapis.com/auth/gmail.modify']
    )
    
    # Refresh to get new access token
    creds.refresh(Request())
    
    return creds.token


async def apply_gmail_label(user_id: str, message_id: str, risk_tier: RiskTier) -> bool:
    """
    Apply Gmail label to an email based on its risk tier.
    Creates the label if it doesn't exist.
    Uses refresh_token to get fresh access_token.
    Returns True on success, False on failure.
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    
    # Map risk tier to Gmail label
    label_mapping = {
        RiskTier.SAFE: "MailShieldAI/SAFE",
        RiskTier.CAUTIOUS: "MailShieldAI/CAUTIOUS",
        RiskTier.THREAT: "MailShieldAI/THREAT"
    }
    label_name = label_mapping.get(risk_tier, "MailShieldAI/CAUTIOUS")
    
    try:
        # Get user's refresh token from database
        from packages.shared.models import User
        query = select(User).where(User.id == user_id)
        async for session in get_session():
            result = await session.exec(query)
            user = result.first()
            
            if not user or not user.refresh_token:
                print(f"No refresh_token for user {user_id}, skipping label")
                return False
            
            # Get fresh access token using refresh token
            try:
                access_token = await get_fresh_access_token(user.refresh_token)
            except Exception as token_error:
                print(f"Failed to refresh access token: {token_error}")
                return False
            
            # Create Gmail service with fresh access token
            creds = Credentials(token=access_token)
            service = build('gmail', 'v1', credentials=creds)
            
            # Create or get label ID
            label_id = await create_gmail_label(service, label_name)
            if not label_id:
                print(f"Failed to get/create label {label_name}")
                return False
            
            # Apply the label
            try:
                service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'addLabelIds': [label_id]}
                ).execute()
                print(f"✓ Applied Gmail label {label_name} to message {message_id}")
                return True
            except HttpError as e:
                print(f"Failed to apply label: {e}")
                return False
            break
    except Exception as e:
        print(f"Failed to apply Gmail label: {e}")
        import traceback
        traceback.print_exc()
        return False


async def process_email(session: AsyncSession, email: EmailEvent) -> None:
    session.add(email)
    await session.commit()
    await session.refresh(email)

    try:
        risk_score = random.randint(0, 100)
        risk_tier = classify_risk(risk_score)
        analysis_result = build_dummy_analysis(risk_score)

        email.risk_score = risk_score
        email.risk_tier = risk_tier
        email.analysis_result = analysis_result
        email.status = EmailStatus.COMPLETED
        
        # Apply Gmail label based on risk tier
        if email.message_id and email.user_id:
            await apply_gmail_label(str(email.user_id), email.message_id, risk_tier)
        
    except Exception:  # noqa: BLE001
        email.status = EmailStatus.FAILED
        email.analysis_result = {"error": "processing_failed"}

    session.add(email)
    await session.commit()
    await session.refresh(email)


async def run_loop() -> None:
    """Main worker loop using Redis Streams Consumer Groups."""
    await init_db()
    redis = await get_redis_client()

    group_name = "intent_workers"
    consumer_name = f"worker-{random.randint(1000, 9999)}"

    # Create consumer group if it doesn't exist
    try:
        await redis.xgroup_create(EMAIL_INTENT_QUEUE, group_name, id="0", mkstream=True)
        print(f"Consumer group {group_name} created.")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            print(f"Error creating consumer group: {e}")

    print(f"Worker {consumer_name} started. Listening on {EMAIL_INTENT_QUEUE}...")

    while True:
        try:
            # Read from group
            # Count=1, block=5000ms
            streams = await redis.xreadgroup(
                group_name,
                consumer_name,
                {EMAIL_INTENT_QUEUE: ">"},
                count=1,
                block=5000,
            )

            if not streams:
                continue

            for stream_name, messages in streams:
                for message_id, payload in messages:
                    email_id_str = payload.get("email_id")
                    payload_subject = payload.get("subject")
                    payload_body = payload.get("body")

                    if not email_id_str:
                        print(f"Invalid payload in message {message_id}")
                        await redis.xack(EMAIL_INTENT_QUEUE, group_name, message_id)
                        continue

                    print(f"Processing message {message_id} (Email ID: {email_id_str})")

                    processed_successfully = False
                    async for session in get_session():
                        try:
                            query = select(EmailEvent).where(
                                EmailEvent.id == email_id_str
                            )
                            result = await session.exec(query)
                            email = result.first()

                            if not email:
                                print(f"Email {email_id_str} not found.")
                                break

                            processed_successfully = await process_email(
                                session, email, payload_subject, payload_body
                            )
                        except Exception as inner_e:
                            print(f"Error processing {email_id_str}: {inner_e}")
                        break

                    if processed_successfully:
                        await redis.xack(EMAIL_INTENT_QUEUE, group_name, message_id)
                        print(f"Acknowledged message {message_id}")

        except Exception as e:
            print(f"Worker loop error: {e}")
            await asyncio.sleep(1)


# Create lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start background tasks."""
    # Startup
    task = asyncio.create_task(run_loop())
    print("Intent worker background task started")
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
    return {"status": "ok", "service": "intent-worker"}


def main() -> None:
    """Entry point for the worker service."""
    port = int(os.getenv("PORT", "8080"))
    # Run uvicorn server
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
