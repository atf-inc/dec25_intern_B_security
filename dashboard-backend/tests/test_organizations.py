"""Tests for organization endpoints."""
import pytest
from httpx import AsyncClient

from tests.conftest import create_mock_jwt


@pytest.mark.asyncio
async def test_create_organization_as_admin(test_client: AsyncClient, test_admin_user: dict):
    """POST /api/organizations succeeds for admin user."""
    token = create_mock_jwt(test_admin_user["google_id"])
    payload = {
        "name": "New Test Org",
        "domain": "neworg.com",
    }
    response = await test_client.post(
        "/api/organizations",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["domain"] == payload["domain"]
    assert "api_key" in data
    assert data["api_key"].startswith("sk_")  # Secure API key with prefix
    assert "api_key_prefix" in data
    assert data["api_key_prefix"] == data["api_key"][:8]  # Prefix matches first 8 chars


@pytest.mark.asyncio
async def test_create_organization_as_member_forbidden(test_client: AsyncClient, test_member_user: dict):
    """POST /api/organizations returns 403 for non-admin user."""
    token = create_mock_jwt(test_member_user["google_id"])
    payload = {
        "name": "New Test Org",
        "domain": "neworg.com",
    }
    response = await test_client.post(
        "/api/organizations",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_organizations_as_admin(test_client: AsyncClient, test_admin_user: dict, test_org: dict):
    """GET /api/organizations returns list for admin user."""
    token = create_mock_jwt(test_admin_user["google_id"])
    response = await test_client.get(
        "/api/organizations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Verify our test org is in the list
    assert any(org["id"] == str(test_org["id"]) for org in data)


@pytest.mark.asyncio
async def test_list_organizations_as_member_forbidden(test_client: AsyncClient, test_member_user: dict):
    """GET /api/organizations returns 403 for non-admin user."""
    token = create_mock_jwt(test_member_user["google_id"])
    response = await test_client.get(
        "/api/organizations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_organizations_requires_auth(test_client: AsyncClient):
    """GET /api/organizations returns 401 without auth."""
    response = await test_client.get("/api/organizations")
    assert response.status_code == 401
