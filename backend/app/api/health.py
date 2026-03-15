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


@router.get("/llm")
async def llm_health() -> dict:
    """LLM health check — makes a minimal Anthropic API call to verify the key is valid and the service is reachable."""
    import anthropic

    from app.config import get_settings

    settings = get_settings()

    if not settings.anthropic_api_key:
        return {
            "status": "unconfigured",
            "llm": "error: ANTHROPIC_API_KEY not set",
            "model": None,
        }

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        # Cheapest possible call: 1 input token, 1 output token
        msg = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        model_used = msg.model
        return {
            "status": "connected",
            "llm": "connected",
            "model": model_used,
        }
    except anthropic.AuthenticationError:
        return {
            "status": "error",
            "llm": "error: invalid API key",
            "model": None,
        }
    except anthropic.RateLimitError:
        # Rate-limited means the key is valid but we're throttled — treat as connected
        return {
            "status": "connected",
            "llm": "connected (rate limited)",
            "model": "claude-haiku-4-5",
        }
    except Exception as exc:
        return {
            "status": "error",
            "llm": f"error: {exc}",
            "model": None,
        }
