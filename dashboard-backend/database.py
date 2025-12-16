import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from models import EmailEvent, Organisation, User  # noqa: F401 - ensure metadata import

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Convert postgresql:// to postgresql+asyncpg:// for async driver
# Determine pool settings based on database type
connect_args = {}
pool_args = {}

if "postgresql" in DATABASE_URL:
    pool_args = {
        "poolclass": QueuePool,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }
else:
    # SQLite / other (aiosqlite usually prefers NullPool or implicit default)
    # Using default pool for SQLite (often NullPool or SingletonThreadPool depending on context)
    pass

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    **pool_args,
)


async def init_db() -> None:
    """Create database tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
