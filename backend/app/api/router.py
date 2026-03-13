"""Main API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.engagements import router as engagements_router
from app.api.agents import router as agents_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
api_router.include_router(engagements_router, prefix="/engagements", tags=["Engagements"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
