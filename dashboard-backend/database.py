"""Database configuration for MailShieldAI - PostgreSQL only (GCP Cloud SQL)."""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from models import EmailEvent, User  # noqa: F401 - ensure metadata import

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please configure PostgreSQL connection.")

# Convert postgresql:// to postgresql+asyncpg:// for async driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Validate PostgreSQL URL
if not DATABASE_URL.startswith("postgresql+asyncpg://"):
    raise RuntimeError(
        "Invalid DATABASE_URL. Only PostgreSQL is supported. "
        "Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
    )

# GCP Cloud SQL PostgreSQL configuration
# Using QueuePool for connection pooling (suitable for long-running services)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=QueuePool,
    pool_size=5,  # Number of connections to keep open
    max_overflow=10,  # Additional connections allowed beyond pool_size
    pool_pre_ping=True,  # Verify connections before using (handles dropped connections)
)


async def init_db() -> None:
    """Create database tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSession(engine) as session:
        yield session
