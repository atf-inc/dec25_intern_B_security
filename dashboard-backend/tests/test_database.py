"""Tests for database and model functionality."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import EmailEvent, EmailStatus, Organisation, RiskTier, User, UserRole


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """Tables are created after init_db."""
    # Create a fresh in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Verify tables exist by trying to query them
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Organisation))
        orgs = result.all()
        assert orgs == []  # Empty but table exists

        result = await session.exec(select(User))
        users = result.all()
        assert users == []

        result = await session.exec(select(EmailEvent))
        emails = result.all()
        assert emails == []

    await engine.dispose()


@pytest.mark.asyncio
async def test_organisation_crud(test_session: AsyncSession):
    """Create and read Organisation."""
    import hashlib
    test_api_key = "sk_crud-api-key-123"
    test_api_key_hash = hashlib.sha256(test_api_key.encode()).hexdigest()
    test_api_key_prefix = test_api_key[:8]
    
    org = Organisation(
        id=uuid.uuid4(),
        name="CRUD Test Org",
        domain="crudtest.com",
        api_key_hash=test_api_key_hash,
        api_key_prefix=test_api_key_prefix,
    )
    test_session.add(org)
    await test_session.commit()

    # Read back
    result = await test_session.exec(
        select(Organisation).where(Organisation.api_key_hash == test_api_key_hash)
    )
    fetched = result.first()
    assert fetched is not None
    assert fetched.name == "CRUD Test Org"
    assert fetched.domain == "crudtest.com"
    assert fetched.api_key_prefix == test_api_key_prefix


@pytest.mark.asyncio
async def test_user_crud(test_session: AsyncSession, test_org: dict):
    """Create and read User with org relationship."""
    user = User(
        id=uuid.uuid4(),
        org_id=test_org["id"],
        google_id="google_crud_test",
        email="crud@test.com",
        role=UserRole.member,
    )
    test_session.add(user)
    await test_session.commit()

    # Read back
    result = await test_session.exec(
        select(User).where(User.google_id == "google_crud_test")
    )
    fetched = result.first()
    assert fetched is not None
    assert fetched.email == "crud@test.com"
    assert fetched.org_id == test_org["id"]


@pytest.mark.asyncio
async def test_email_event_crud(test_session: AsyncSession, test_org: dict):
    """Create and read EmailEvent with defaults."""
    email = EmailEvent(
        id=uuid.uuid4(),
        org_id=test_org["id"],
        sender="sender@test.com",
        recipient="recipient@test.com",
        subject="CRUD Test Email",
    )
    test_session.add(email)
    await test_session.commit()

    # Read back
    result = await test_session.exec(
        select(EmailEvent).where(EmailEvent.subject == "CRUD Test Email")
    )
    fetched = result.first()
    assert fetched is not None
    assert fetched.sender == "sender@test.com"
    assert fetched.status == EmailStatus.pending  # Default value
    assert fetched.risk_score is None
    assert fetched.risk_tier is None


@pytest.mark.asyncio
async def test_email_event_status_transitions(test_session: AsyncSession, test_org: dict):
    """Status enum transitions work correctly."""
    email = EmailEvent(
        id=uuid.uuid4(),
        org_id=test_org["id"],
        sender="sender@test.com",
        recipient="recipient@test.com",
        subject="Status Test Email",
        status=EmailStatus.pending,
    )
    test_session.add(email)
    await test_session.commit()

    # Update status
    email.status = EmailStatus.processing
    test_session.add(email)
    await test_session.commit()
    await test_session.refresh(email)
    assert email.status == EmailStatus.processing

    # Complete
    email.status = EmailStatus.completed
    email.risk_score = 75
    email.risk_tier = RiskTier.cautious
    test_session.add(email)
    await test_session.commit()
    await test_session.refresh(email)
    assert email.status == EmailStatus.completed
    assert email.risk_score == 75
    assert email.risk_tier == RiskTier.cautious


@pytest.mark.asyncio
async def test_user_role_enum():
    """UserRole admin/member values work correctly."""
    assert UserRole.admin.value == "admin"
    assert UserRole.member.value == "member"
    assert UserRole("admin") == UserRole.admin
    assert UserRole("member") == UserRole.member


@pytest.mark.asyncio
async def test_email_status_enum():
    """EmailStatus enum values are correct."""
    assert EmailStatus.pending.value == "PENDING"
    assert EmailStatus.processing.value == "PROCESSING"
    assert EmailStatus.completed.value == "COMPLETED"
    assert EmailStatus.failed.value == "FAILED"


@pytest.mark.asyncio
async def test_risk_tier_enum():
    """RiskTier enum values are correct."""
    assert RiskTier.safe.value == "SAFE"
    assert RiskTier.cautious.value == "CAUTIOUS"
    assert RiskTier.threat.value == "THREAT"
