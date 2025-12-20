#!/usr/bin/env python
"""Seed the database with a dev user for local development.

In production, users are auto-provisioned on first Google OAuth login.
This script is only needed for DEV_MODE testing.
"""

import asyncio

from dotenv import load_dotenv

load_dotenv()

from database import engine, init_db
from models import User
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


async def seed():
    """Create database tables and optionally seed a dev user."""
    await init_db()
    print("Database tables created/verified.")

    async with AsyncSession(engine) as session:
        # Check if dev user already exists
        result = await session.exec(select(User).where(User.google_id == "dev-user-123"))
        existing_user = result.first()

        if existing_user:
            print(f"Dev user already exists: {existing_user.email} (id: {existing_user.id})")
        else:
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

        print("\nSeeding complete!")
        print("In DEV_MODE, use 'dev_anytoken' as your bearer token to authenticate.")


if __name__ == "__main__":
    asyncio.run(seed())
