#!/usr/bin/env python
"""Seed the database with an initial Organisation and User for local development."""

import asyncio
import hashlib
import secrets
import uuid

from dotenv import load_dotenv

load_dotenv()

from database import engine, init_db
from models import Organisation, User, UserRole
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


def _generate_api_key() -> tuple[str, str, str]:
    """Generate an API key and return (plaintext_key, hashed_key, prefix)."""
    plaintext_key = f"pg_{secrets.token_urlsafe(32)}"
    prefix = plaintext_key[:8]
    hashed_key = hashlib.sha256(plaintext_key.encode()).hexdigest()
    return plaintext_key, hashed_key, prefix


async def seed():
    await init_db()

    async with AsyncSession(engine) as session:
        # Check if any org exists
        result = await session.exec(select(Organisation))
        existing_org = result.first()

        if existing_org:
            print(f"Organisation already exists: {existing_org.name} (id: {existing_org.id})")
            org = existing_org
        else:
            # Create a default organisation
            plaintext_key, hashed_key, prefix = _generate_api_key()
            org = Organisation(
                name="Default Organisation",
                domain="example.com",
                api_key_hash=hashed_key,
                api_key_prefix=prefix,
            )
            session.add(org)
            await session.commit()
            await session.refresh(org)
            print(f"Created Organisation: {org.name} (id: {org.id})")
            # API Key is generated for the organisation. Do not log sensitive keys.

        # Check if dev user exists
        result = await session.exec(select(User).where(User.google_id == "dev-user-123"))
        existing_user = result.first()

        if existing_user:
            print(f"Dev user already exists: {existing_user.email} (id: {existing_user.id})")
        else:
            # Create a platform admin user for DEV_MODE
            user = User(
                org_id=org.id,
                google_id="dev-user-123",  # Matches DEV_MODE token parsing in main.py
                email="dev@example.com",
                role=UserRole.platform_admin,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created User: {user.email} (role: {user.role.value}, id: {user.id})")

        print("\nSeeding complete! You can now use the dashboard.")


if __name__ == "__main__":
    asyncio.run(seed())
