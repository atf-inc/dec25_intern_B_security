"""Tests for email endpoints."""
import pytest
from httpx import AsyncClient

from tests.conftest import create_mock_jwt


@pytest.mark.asyncio
async def test_ingest_email_with_api_key(test_client: AsyncClient, test_org: dict):
    """POST /api/emails with valid X-API-Key creates email."""
    payload = {
        "sender": "sender@example.com",
        "recipient": "recipient@test.com",
        "subject": "Test Email",
        "body_preview": "This is a test email body",
    }
    response = await test_client.post(
        "/api/emails",
        json=payload,
        headers={"x-api-key": test_org["api_key"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sender"] == payload["sender"]
    assert data["recipient"] == payload["recipient"]
    assert data["subject"] == payload["subject"]
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_ingest_email_with_bearer_token(test_client: AsyncClient, test_admin_user: dict):
    """POST /api/emails with valid Bearer token creates email."""
    payload = {
        "sender": "sender@example.com",
        "recipient": "recipient@test.com",
        "subject": "Test Email via Bearer",
    }
    token = create_mock_jwt(test_admin_user["google_id"])
    response = await test_client.post(
        "/api/emails",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sender"] == payload["sender"]
    assert data["subject"] == payload["subject"]


@pytest.mark.asyncio
async def test_ingest_email_missing_auth(test_client: AsyncClient):
    """POST /api/emails without auth returns 401."""
    payload = {
        "sender": "sender@example.com",
        "recipient": "recipient@test.com",
        "subject": "Test Email",
    }
    response = await test_client.post("/api/emails", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_emails_empty(test_client: AsyncClient, test_admin_user: dict):
    """GET /api/emails returns empty list when no emails exist."""
    token = create_mock_jwt(test_admin_user["google_id"])
    response = await test_client.get(
        "/api/emails",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_emails_returns_created(test_client: AsyncClient, test_org: dict, test_admin_user: dict):
    """GET /api/emails returns emails after creation."""
    # Create an email first
    payload = {
        "sender": "sender@example.com",
        "recipient": "recipient@test.com",
        "subject": "Test Email for List",
    }
    create_response = await test_client.post(
        "/api/emails",
        json=payload,
        headers={"x-api-key": test_org["api_key"]},
    )
    assert create_response.status_code == 201

    # List emails
    token = create_mock_jwt(test_admin_user["google_id"])
    response = await test_client.get(
        "/api/emails",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(e["subject"] == "Test Email for List" for e in data)


@pytest.mark.asyncio
async def test_list_emails_requires_auth(test_client: AsyncClient):
    """GET /api/emails without auth returns 401."""
    response = await test_client.get("/api/emails")
    assert response.status_code == 401
