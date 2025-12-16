"""Shared test fixtures for dashboard-backend tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Set DATABASE_URL before importing models/database to avoid RuntimeError
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from models import EmailStatus, Organisation, User, UserRole


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
async def test_org(test_session: AsyncSession) -> Organisation:
    """Create a test organisation."""
    org = Organisation(
        id=uuid.uuid4(),
        name="Test Organisation",
        domain="test.com",
        api_key="test-api-key-12345",
    )
    test_session.add(org)
    await test_session.commit()
    await test_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_admin_user(test_session: AsyncSession, test_org: Organisation) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid.uuid4(),
        org_id=test_org.id,
        clerk_id="clerk_admin_123",
        email="admin@test.com",
        role=UserRole.admin,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_member_user(test_session: AsyncSession, test_org: Organisation) -> User:
    """Create a test member user."""
    user = User(
        id=uuid.uuid4(),
        org_id=test_org.id,
        clerk_id="clerk_member_456",
        email="member@test.com",
        role=UserRole.member,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


def create_mock_jwt(clerk_id: str) -> str:
    """Create a mock JWT token for testing."""
    payload = {"sub": clerk_id}
    # Using a simple secret for tests - no signature verification in dev mode
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def auth_header_for_user(user: User) -> dict[str, str]:
    """Generate Authorization header for a user."""
    token = create_mock_jwt(user.clerk_id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_client(
    test_engine, test_session: AsyncSession
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
