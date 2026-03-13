"""Shared FastAPI dependencies."""

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def get_redis(request: Request) -> Redis | None:
    """Return the Redis client attached at startup (may be None)."""
    return getattr(request.app.state, "redis", None)


# Re-export for convenience
get_session = get_db
