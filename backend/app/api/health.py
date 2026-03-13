"""Health check endpoints."""

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session, get_redis

router = APIRouter()


@router.get("")
async def health() -> dict:
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "keen-backend",
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness(
    request: Request,
    db: AsyncSession = Depends(get_session),
    redis: Redis | None = Depends(get_redis),
) -> dict:
    """Readiness check — verifies DB and Redis connectivity."""
    checks: dict[str, str] = {}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # Redis
    if redis:
        try:
            await redis.ping()
            checks["redis"] = "connected"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
    else:
        checks["redis"] = "unavailable"

    all_ok = all(v == "connected" for v in checks.values() if v != "unavailable")
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
    }
