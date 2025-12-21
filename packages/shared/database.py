"""Database configuration for MailShieldAI - PostgreSQL only (GCP Cloud SQL)."""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please configure PostgreSQL connection.")

# Convert postgresql:// to postgresql+asyncpg:// for async driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Validate Database URL
if not (DATABASE_URL.startswith("postgresql+asyncpg://") or DATABASE_URL.startswith("sqlite+aiosqlite://")):
    raise RuntimeError(
        "Invalid DATABASE_URL. Only PostgreSQL and SQLite are supported. "
    )

# GCP Cloud SQL PostgreSQL configuration
# Using default AsyncAdaptedQueuePool (as recommended by CodeRabbit)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)


async def init_db() -> None:
    """Create database tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSession(engine) as session:
        yield session
