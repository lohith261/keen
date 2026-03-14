"""KEEN Backend — FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.router import api_router
from app.websocket.agent_status import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    try:
        await app.state.redis.ping()
        print("✓ Redis connected")
    except Exception as exc:
        print(f"⚠ Redis unavailable ({exc}) — checkpointing will use DB only")
        app.state.redis = None

    yield

    # ── Shutdown ─────────────────────────────────────────
    if app.state.redis:
        await app.state.redis.close()
        print("✓ Redis disconnected")


app = FastAPI(
    title="KEEN API",
    description="Multi-Agent PE Due Diligence Backend",
    version="0.1.1",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)
