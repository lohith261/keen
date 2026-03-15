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
            import google.generativeai as genai  # type: ignore[import]
            genai.configure(api_key=settings.gemini_api_key)
            # Try models in order of preference; fall through if a model is unavailable
            gemini_model_used = None
            resp = None
            for model_name in ("gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"):
                try:
                    model = genai.GenerativeModel(model_name)
                    resp = await asyncio.get_event_loop().run_in_executor(
                        None, lambda m=model: m.generate_content(
                            "hi", generation_config={"max_output_tokens": 1}
                        )
                    )
                    _ = resp.text  # raises if response is blocked
                    gemini_model_used = model_name
                    break
                except Exception:
                    continue
            if gemini_model_used is None:
                raise RuntimeError("No Gemini model responded successfully")
            return {"provider": "gemini", "ok": True, "detail": gemini_model_used}
        except Exception as exc:
            exc_str = str(exc)
            if "API_KEY_INVALID" in exc_str or "invalid" in exc_str.lower():
                detail = "invalid API key"
            elif "quota" in exc_str.lower() or "429" in exc_str:
                detail = "quota exceeded"
            else:
                detail = exc_str[:120]
            return {"provider": "gemini", "ok": False, "detail": detail}

    # ── Run all three in parallel ─────────────────────────────────────────────
    results = await asyncio.gather(_check_anthropic(), _check_openai(), _check_gemini())

    providers = {r["provider"]: r for r in results}
    any_ok = any(r["ok"] for r in results)

    return {
        "status": "connected" if any_ok else "error",
        "providers": {
            name: {"ok": r["ok"], "detail": r.get("detail")}
            for name, r in providers.items()
        },
    }
