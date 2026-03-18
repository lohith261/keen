"""Main API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.engagements import router as engagements_router
from app.api.agents import router as agents_router
from app.api.credentials import router as credentials_router
from app.api.documents import router as documents_router
from app.api.monitoring import router as monitoring_router
from app.api.transcripts import router as transcripts_router
from app.api.primary_research import router as primary_research_router
from app.api.external_records import router as external_records_router
from app.api.legal_findings import router as legal_findings_router
from app.api.technical_dd import router as technical_dd_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
api_router.include_router(engagements_router, prefix="/engagements", tags=["Engagements"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(credentials_router, prefix="/credentials", tags=["Credentials"])
api_router.include_router(documents_router, prefix="/engagements", tags=["Documents"])
api_router.include_router(monitoring_router, prefix="/engagements", tags=["Monitoring"])
api_router.include_router(transcripts_router, prefix="/engagements", tags=["Transcripts"])
api_router.include_router(primary_research_router, prefix="/engagements", tags=["CommercialDD"])
api_router.include_router(external_records_router, prefix="/engagements", tags=["ExternalVerification"])
api_router.include_router(legal_findings_router, prefix="/engagements", tags=["LegalDD"])
api_router.include_router(technical_dd_router, prefix="/engagements", tags=["TechnicalDD"])
