"""Shared test fixtures for dashboard-backend tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from collections.abc import AsyncGenerator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Set environment variables before importing modules
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DEV_MODE", "true")

from models import Organisation, User, UserRole


# Use SQLite in-memory for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with AsyncSession(test_engine) as session:
        yield session


@pytest_asyncio.fixture
async def test_org(test_session: AsyncSession) -> dict:
    """Create a test organisation and return its data as a dict."""
    import hashlib
    # Use a known test API key for testing
    test_api_key = "sk_test-api-key-12345"
    test_api_key_hash = hashlib.sha256(test_api_key.encode()).hexdigest()
    test_api_key_prefix = test_api_key[:8]
    
    org = Organisation(
        id=uuid.uuid4(),
        name="Test Organisation",
        domain="test.com",
        api_key_hash=test_api_key_hash,
        api_key_prefix=test_api_key_prefix,
    )
    test_session.add(org)
    await test_session.commit()
    await test_session.refresh(org)
    # Return plain dict to avoid lazy loading issues
    # Include plaintext key for test purposes only
    return {
        "id": org.id,
        "name": org.name,
        "domain": org.domain,
        "api_key": test_api_key,  # Plaintext for testing
        "api_key_hash": org.api_key_hash,
        "api_key_prefix": org.api_key_prefix,
    }


@pytest_asyncio.fixture
async def test_admin_user(test_session: AsyncSession, test_org: dict) -> dict:
    """Create a test admin user and return its data as a dict."""
    user = User(
        id=uuid.uuid4(),
        org_id=test_org["id"],
        google_id="google_admin_123",
        email="admin@test.com",
        role=UserRole.admin,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    # Return plain dict to avoid lazy loading issues
    return {
        "id": user.id,
        "org_id": user.org_id,
        "google_id": user.google_id,
        "email": user.email,
        "role": user.role,
    }


@pytest_asyncio.fixture
async def test_member_user(test_session: AsyncSession, test_org: dict) -> dict:
    """Create a test member user and return its data as a dict."""
    user = User(
        id=uuid.uuid4(),
        org_id=test_org["id"],
        google_id="google_member_456",
        email="member@test.com",
        role=UserRole.member,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    # Return plain dict to avoid lazy loading issues
    return {
        "id": user.id,
        "org_id": user.org_id,
        "google_id": user.google_id,
        "email": user.email,
        "role": user.role,
    }


def create_mock_jwt(google_id: str) -> str:
    """Create a mock token for testing in dev mode.
    
    In dev mode, tokens starting with "dev_" are accepted without verification.
    The google_id is extracted from after the "dev_" prefix.
    """
    return f"dev_{google_id}"


def auth_header_for_user(user: dict) -> dict[str, str]:
    """Generate Authorization header for a user dict."""
    token = create_mock_jwt(user["google_id"])
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_client(
    test_session: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with dependency overrides."""
    from main import app
    from database import get_session

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
