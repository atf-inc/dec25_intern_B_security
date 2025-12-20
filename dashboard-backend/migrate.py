"""Database migration script to add new threat intelligence columns."""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)


async def migrate():
    """Add new columns to email_events table."""
    
    # New columns to add
    migrations = [
        # Email timestamp
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS received_at TIMESTAMP WITHOUT TIME ZONE",
        
        # Threat Intelligence columns
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS threat_category VARCHAR",
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS detection_reason VARCHAR",
        
        # Security Metadata columns
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS spf_status VARCHAR",
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS dkim_status VARCHAR",
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS dmarc_status VARCHAR",
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS sender_ip VARCHAR",
        "ALTER TABLE email_events ADD COLUMN IF NOT EXISTS attachment_info VARCHAR",
        
        # Add SPAM value to email_status_enum
        # usage of 'IF NOT EXISTS' for enum values requires newer Postgres or DO block, 
        # but simpler to just run it and ignore error if already exists (handled by loop below)
        "ALTER TYPE email_status_enum ADD VALUE IF NOT EXISTS 'SPAM'",
    ]
    
    async with engine.begin() as conn:
        for sql in migrations:
            print(f"Running: {sql}")
            try:
                await conn.execute(text(sql))
                print("  ✓ Success")
            except Exception as e:
                print(f"  ✗ Error: {e}")
    
    print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
