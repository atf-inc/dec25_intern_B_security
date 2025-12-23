from __future__ import annotations

import os
import asyncio
from typing import Optional

import redis.asyncio as redis
from redis.asyncio.client import Redis

# Queue Names
EMAIL_INTENT_QUEUE = 'emails:intent'
EMAIL_ANALYSIS_QUEUE = 'emails:analysis'
JOB_AGGREGATOR_QUEUE = 'emails:job'
EMAIL_INTENT_DONE_QUEUE = 'emails:intent:done'
EMAIL_ANALYSIS_DONE_QUEUE = 'emails:analysis:done'
FINAL_REPORT_QUEUE = 'job:completed'

# Singleton state
_redis_client: Optional[Redis] = None
_redis_lock = asyncio.Lock()


def get_redis_url() -> str:
    """Get Redis URL from environment variable or default."""
    return os.getenv('REDIS_URL', 'redis://localhost:6379/0')


async def get_redis_client() -> Redis:
    """
    Get a singleton async Redis client.

    This is concurrency-safe and guarantees only one client instance.
    """
    global _redis_client

    if _redis_client is None:
        async with _redis_lock:
            if _redis_client is None:  # double-checked locking
                _redis_client = redis.from_url(
                    get_redis_url(),
                    encoding='utf-8',
                    decode_responses=True,
                )

    return _redis_client


async def close_redis() -> None:
    """Gracefully close the singleton Redis client."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
