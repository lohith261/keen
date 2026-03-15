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
    """
    LLM health check — probes Anthropic, OpenAI, and Gemini in parallel.
    Passes if at least one provider can respond to a real message.
    Fails only if all three are unavailable/unconfigured/out-of-credits.
    """
    import asyncio

    import anthropic
    import openai

    from app.config import get_settings

    settings = get_settings()

    # ── Per-provider probe functions ─────────────────────────────────────────

    async def _check_anthropic() -> dict:
        if not settings.anthropic_api_key:
            return {"provider": "anthropic", "ok": False, "detail": "API key not configured"}
        try:
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            msg = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return {"provider": "anthropic", "ok": True, "detail": msg.model}
        except anthropic.AuthenticationError:
            return {"provider": "anthropic", "ok": False, "detail": "invalid API key"}
        except anthropic.RateLimitError:
            return {"provider": "anthropic", "ok": False, "detail": "rate limited"}
        except anthropic.BadRequestError as exc:
            exc_str = str(exc)
            if "credit balance is too low" in exc_str or "quota" in exc_str.lower():
                return {"provider": "anthropic", "ok": False, "detail": "insufficient credits"}
            return {"provider": "anthropic", "ok": False, "detail": str(exc)}
        except Exception as exc:
            return {"provider": "anthropic", "ok": False, "detail": str(exc)}

    async def _check_openai() -> dict:
        if not settings.openai_api_key:
            return {"provider": "openai", "ok": False, "detail": "API key not configured"}
        try:
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            model_used = resp.model
            return {"provider": "openai", "ok": True, "detail": model_used}
        except openai.AuthenticationError:
            return {"provider": "openai", "ok": False, "detail": "invalid API key"}
        except openai.RateLimitError:
            return {"provider": "openai", "ok": False, "detail": "rate limited"}
        except openai.BadRequestError as exc:
            return {"provider": "openai", "ok": False, "detail": str(exc)}
        except Exception as exc:
            return {"provider": "openai", "ok": False, "detail": str(exc)}

    async def _check_gemini() -> dict:
        if not settings.gemini_api_key:
            return {"provider": "gemini", "ok": False, "detail": "API key not configured"}
        try:
            import httpx
            # Use the v1 REST API directly — avoids the google-generativeai SDK
            # defaulting to v1beta which doesn't support newer model IDs.
            for model_name in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.0-pro"):
                url = (
                    f"https://generativelanguage.googleapis.com/v1/models/"
                    f"{model_name}:generateContent?key={settings.gemini_api_key}"
                )
                payload = {
                    "contents": [{"parts": [{"text": "hi"}]}],
                    "generationConfig": {"maxOutputTokens": 1},
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return {"provider": "gemini", "ok": True, "detail": model_name}
                if resp.status_code == 404:
                    continue  # model not found, try next
                # Auth / quota errors — no point retrying other models
                body = resp.json()
                err_msg = body.get("error", {}).get("message", resp.text)[:120]
                if resp.status_code == 400 and "API_KEY_INVALID" in err_msg:
                    return {"provider": "gemini", "ok": False, "detail": "invalid API key"}
                if resp.status_code == 429:
                    return {"provider": "gemini", "ok": False, "detail": "quota exceeded"}
                return {"provider": "gemini", "ok": False, "detail": err_msg}
            return {"provider": "gemini", "ok": False, "detail": "no supported model found"}
        except Exception as exc:
            return {"provider": "gemini", "ok": False, "detail": str(exc)[:120]}

    async def _check_groq() -> dict:
        if not settings.groq_api_key:
            return {"provider": "groq", "ok": False, "detail": "API key not configured"}
        try:
            from groq import AsyncGroq  # type: ignore[import]
            client = AsyncGroq(api_key=settings.groq_api_key)
            resp = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return {"provider": "groq", "ok": True, "detail": resp.model}
        except Exception as exc:
            exc_str = str(exc)
            if "invalid_api_key" in exc_str.lower() or "401" in exc_str:
                detail = "invalid API key"
            elif "429" in exc_str or "rate" in exc_str.lower():
                detail = "rate limited"
            else:
                detail = exc_str[:120]
            return {"provider": "groq", "ok": False, "detail": detail}

    # ── Run all four in parallel ──────────────────────────────────────────────
    results = await asyncio.gather(
        _check_anthropic(), _check_openai(), _check_gemini(), _check_groq()
    )

    providers = {r["provider"]: r for r in results}
    any_ok = any(r["ok"] for r in results)

    return {
        "status": "connected" if any_ok else "error",
        "providers": {
            name: {"ok": r["ok"], "detail": r.get("detail")}
            for name, r in providers.items()
        },
    }
