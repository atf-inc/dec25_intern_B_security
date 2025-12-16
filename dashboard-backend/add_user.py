#!/usr/bin/env python
"""Add a user to the database by their Google ID and email.

Usage:
    python add_user.py <google_id> <email> [--admin]
    
Example:
    python add_user.py "123456789012345678901" "user@gmail.com" --admin
"""

import argparse
import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from database import engine, init_db
from models import Organisation, User, UserRole
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


async def add_user(google_id: str, email: str, is_admin: bool = False):
    await init_db()

    async with AsyncSession(engine) as session:
        # Get the first organisation
        result = await session.exec(select(Organisation))
        org = result.first()

        if not org:
            print("ERROR: No organisation exists. Run seed_db.py first.")
            sys.exit(1)

        # Check if user already exists
        result = await session.exec(select(User).where(User.google_id == google_id))
        existing_user = result.first()

        if existing_user:
            print(f"User already exists: {existing_user.email} (id: {existing_user.id})")
            return

        # Create the user
        role = UserRole.platform_admin if is_admin else UserRole.member
        org_id = org.id
        org_name = org.name  # Store before session expires
        
        user = User(
            org_id=org_id,
            google_id=google_id,
            email=email,
            role=role,
        )
        session.add(user)
        await session.commit()
        
        print(f"Created User: {email}")
        print(f"  Google ID: {google_id}")
        print(f"  Role: {role.value}")
        print(f"  Organisation: {org_name}")


def main():
    parser = argparse.ArgumentParser(description="Add a user to the database")
    parser.add_argument("google_id", help="The user's Google ID (sub claim from ID token)")
    parser.add_argument("email", help="The user's email address")
    parser.add_argument("--admin", action="store_true", help="Make user a platform admin")
    
    args = parser.parse_args()
    asyncio.run(add_user(args.google_id, args.email, args.admin))


if __name__ == "__main__":
    main()
