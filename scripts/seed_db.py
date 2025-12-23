#!/usr/bin/env python
"""Seed the database with fresh tables and dev user for local development.

This script will:
1. Drop all existing tables (complete wipe)
2. Create fresh tables based on current models
3. Seed with a dev user for DEV_MODE testing

In production, users are auto-provisioned on first Google OAuth login.
"""

import asyncio
import os
import sys

# Add project root to sys.path to enable packages imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.shared.database import engine
from packages.shared.models import User, EmailEvent  # CRITICAL: Must import models for metadata
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession



async def drop_all_tables():
    """Drop all existing tables - COMPLETE DATABASE WIPE."""
    print("Dropping all existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    print("Tables dropped.")


async def create_all_tables():
    """Create all tables from scratch based on current models."""
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Tables created.")


async def seed_dev_user():
    """Seed the database with a dev user for DEV_MODE testing."""
    async with AsyncSession(engine) as session:
        # Create a dev user for DEV_MODE testing
        user = User(
            google_id="dev-user-123",  # Matches DEV_MODE token parsing in main.py
            email="dev@example.com",
            name="Dev User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Created dev user: {user.email} (id: {user.id})")


async def main():
    """Main seeding workflow."""
    print("WARNING: This will completely wipe your database!")
    print("Press Ctrl+C within 3 seconds to cancel...")
    
    try:
        await asyncio.sleep(3)
    except KeyboardInterrupt:
        print("Cancelled.")
        return
    
    print("Starting database reset...")
    
    # Step 1: Drop all tables
    await drop_all_tables()
    
    # Step 2: Create fresh tables
    await create_all_tables()
    
    print("Database reset complete.")


if __name__ == "__main__":
    asyncio.run(main())
