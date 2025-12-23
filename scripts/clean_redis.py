#!/usr/bin/env python
"""
Seed / reset Redis streams for local development.

This script will:
1. Scan all Redis keys
2. Delete ONLY keys of type 'stream'

Other Redis data (strings, hashes, sets) are untouched.

⚠️ Intended for DEV use only.
"""

import os
import sys
import time

# Add project root to sys.path to enable packages imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
import redis

load_dotenv()


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ENV = os.getenv("ENV", "dev")


def delete_all_streams() -> list[str]:
    """Delete all Redis stream keys using SCAN (safe, non-blocking)."""
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    cursor = 0
    deleted: list[str] = []

    while True:
        cursor, keys = r.scan(cursor=cursor, count=100)
        for key in keys:
            try:
                if r.type(key) == "stream":
                    r.delete(key)
                    deleted.append(key)
            except redis.RedisError:
                # Key may disappear mid-scan; safe to ignore
                continue

        if cursor == 0:
            break

    return deleted


def main():
    print("WARNING: This will delete ALL Redis streams!")
    print(f"Redis URL: {REDIS_URL}")
    print("Press Ctrl+C within 3 seconds to cancel...")

    try:
        time.sleep(3)
    except KeyboardInterrupt:
        print("Cancelled.")
        return

    if ENV == "prod":
        raise RuntimeError("Refusing to delete Redis streams in production")

    print("Starting Redis stream cleanup...")

    deleted = delete_all_streams()

    if deleted:
        print("Deleted Redis streams:")
        for k in deleted:
            print(f"  - {k}")
    else:
        print("No Redis streams found.")

    print(f"Redis cleanup complete. ({len(deleted)} streams deleted)")


if __name__ == "__main__":
    main()
