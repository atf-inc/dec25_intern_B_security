"""Tests for user endpoints."""
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import create_mock_jwt


@pytest.mark.asyncio
async def test_create_user_as_admin(test_client: AsyncClient, test_admin_user: dict):
    """POST /api/users succeeds for admin user."""
    token = create_mock_jwt(test_admin_user["google_id"])
    payload = {
        "email": "newuser@test.com",
        "google_id": "clerk_new_user_789",
        "role": "member",
    }
    response = await test_client.post(
        "/api/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["google_id"] == payload["google_id"]
    assert data["role"] == payload["role"]
    assert data["org_id"] == str(test_admin_user["org_id"])


@pytest.mark.asyncio
async def test_create_user_as_member_forbidden(test_client: AsyncClient, test_member_user: dict):
    """POST /api/users returns 403 for non-admin user."""
    token = create_mock_jwt(test_member_user["google_id"])
    payload = {
        "email": "newuser@test.com",
        "google_id": "clerk_new_user_789",
    }
    response = await test_client.post(
        "/api/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users(test_client: AsyncClient, test_admin_user: dict):
    """GET /api/users returns users in organisation."""
    token = create_mock_jwt(test_admin_user["google_id"])
    response = await test_client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Admin user should be in the list
    assert any(u["google_id"] == test_admin_user["google_id"] for u in data)


@pytest.mark.asyncio
async def test_list_users_as_member_forbidden(test_client: AsyncClient, test_member_user: dict):
    """GET /api/users returns 403 for non-admin user."""
    token = create_mock_jwt(test_member_user["google_id"])
    response = await test_client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_role(test_client: AsyncClient, test_admin_user: dict, test_member_user: dict):
    """PATCH /api/users/{id}/role updates user role."""
    token = create_mock_jwt(test_admin_user["google_id"])
    user_id = str(test_member_user["id"])

    response = await test_client.patch(
        f"/api/users/{user_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_update_user_role_not_found(test_client: AsyncClient, test_admin_user: dict):
    """PATCH /api/users/{id}/role returns 404 for non-existent user."""
    token = create_mock_jwt(test_admin_user["google_id"])
    fake_id = str(uuid.uuid4())

    response = await test_client.patch(
        f"/api/users/{fake_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_users_requires_auth(test_client: AsyncClient):
    """GET /api/users returns 401 without auth."""
    response = await test_client.get("/api/users")
    assert response.status_code == 401
