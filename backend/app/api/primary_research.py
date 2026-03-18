"""
Primary Research API — manage customer interviews, channel checks, win/loss records.

Routes
------
POST   /engagements/{id}/primary-research            Create a record
GET    /engagements/{id}/primary-research            List records (optional ?type= filter)
GET    /engagements/{id}/primary-research/summary    Aggregated summary
GET    /engagements/{id}/primary-research/{record_id} Get one record
PATCH  /engagements/{id}/primary-research/{record_id} Update a record
DELETE /engagements/{id}/primary-research/{record_id} Delete a record
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_db as get_session
from app.models.engagement import Engagement
from app.models.primary_research import PrimaryResearch, PrimaryResearchType
from app.services.primary_research_service import extract_themes, infer_sentiment, summarize_interviews

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class PrimaryResearchCreate(BaseModel):
    type: PrimaryResearchType
    company_name: str
    contact_name: str | None = None
    contact_role: str | None = None
    interview_date: datetime | None = None
    notes: str | None = None
    action_items: list[str] = []


class PrimaryResearchUpdate(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    contact_role: str | None = None
    interview_date: datetime | None = None
    notes: str | None = None
    sentiment: str | None = None
    key_themes: list[str] | None = None
    action_items: list[str] | None = None
    status: str | None = None


class PrimaryResearchResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    type: str
    company_name: str
    contact_name: str | None
    contact_role: str | None
    interview_date: datetime | None
    notes: str | None
    sentiment: str | None
    key_themes: list[str]
    action_items: list[str]
    status: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, rec: PrimaryResearch) -> "PrimaryResearchResponse":
        return cls(
            id=rec.id,
            engagement_id=rec.engagement_id,
            type=rec.type.value if hasattr(rec.type, "value") else str(rec.type),
            company_name=rec.company_name,
            contact_name=rec.contact_name,
            contact_role=rec.contact_role,
            interview_date=rec.interview_date,
            notes=rec.notes,
            sentiment=rec.sentiment,
            key_themes=rec.key_themes or [],
            action_items=rec.action_items or [],
            status=rec.status,
            created_at=rec.created_at.isoformat(),
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_engagement(
    engagement_id: UUID, user: AuthUser, db: AsyncSession
) -> Engagement:
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng.user_id and eng.user_id != user.sub:
        raise HTTPException(status_code=403, detail="Access denied")
    return eng


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/{engagement_id}/primary-research", response_model=PrimaryResearchResponse)
async def create_primary_research(
    engagement_id: UUID,
    body: PrimaryResearchCreate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> PrimaryResearchResponse:
    """Create a primary research record. Auto-extracts themes and sentiment from notes."""
    await _get_engagement(engagement_id, current_user, db)

    notes = body.notes or ""
    key_themes = extract_themes(notes)
    sentiment = infer_sentiment(notes)

    rec = PrimaryResearch(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        user_id=current_user.sub,
        type=body.type,
        company_name=body.company_name,
        contact_name=body.contact_name,
        contact_role=body.contact_role,
        interview_date=body.interview_date,
        notes=body.notes,
        sentiment=sentiment,
        key_themes=key_themes,
        action_items=body.action_items,
        status="draft",
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return PrimaryResearchResponse.from_orm(rec)


@router.get("/{engagement_id}/primary-research", response_model=list[PrimaryResearchResponse])
async def list_primary_research(
    engagement_id: UUID,
    type: str | None = Query(default=None, description="Filter by research type"),
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[PrimaryResearchResponse]:
    """List primary research records for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    stmt = (
        select(PrimaryResearch)
        .where(PrimaryResearch.engagement_id == engagement_id)
        .order_by(PrimaryResearch.created_at.desc())
    )
    if type:
        stmt = stmt.where(PrimaryResearch.type == type)

    result = await db.execute(stmt)
    records = result.scalars().all()
    return [PrimaryResearchResponse.from_orm(r) for r in records]


@router.get("/{engagement_id}/primary-research/summary")
async def get_primary_research_summary(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Return aggregated summary of all primary research for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    result = await db.execute(
        select(PrimaryResearch).where(PrimaryResearch.engagement_id == engagement_id)
    )
    records = result.scalars().all()
    return summarize_interviews(records)


@router.get(
    "/{engagement_id}/primary-research/{record_id}",
    response_model=PrimaryResearchResponse,
)
async def get_primary_research(
    engagement_id: UUID,
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> PrimaryResearchResponse:
    """Get a single primary research record."""
    await _get_engagement(engagement_id, current_user, db)

    rec = await db.get(PrimaryResearch, record_id)
    if not rec or rec.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Primary research record not found")
    return PrimaryResearchResponse.from_orm(rec)


@router.patch(
    "/{engagement_id}/primary-research/{record_id}",
    response_model=PrimaryResearchResponse,
)
async def update_primary_research(
    engagement_id: UUID,
    record_id: UUID,
    body: PrimaryResearchUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> PrimaryResearchResponse:
    """Update a primary research record. Re-runs theme extraction if notes change."""
    await _get_engagement(engagement_id, current_user, db)

    rec = await db.get(PrimaryResearch, record_id)
    if not rec or rec.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Primary research record not found")

    update_data = body.model_dump(exclude_unset=True)

    # If notes are being updated, re-run theme extraction and sentiment
    if "notes" in update_data and update_data["notes"] is not None:
        notes = update_data["notes"]
        if "key_themes" not in update_data:
            update_data["key_themes"] = extract_themes(notes)
        if "sentiment" not in update_data:
            update_data["sentiment"] = infer_sentiment(notes)

    for field, value in update_data.items():
        setattr(rec, field, value)

    await db.commit()
    await db.refresh(rec)
    return PrimaryResearchResponse.from_orm(rec)


@router.delete("/{engagement_id}/primary-research/{record_id}", status_code=204)
async def delete_primary_research(
    engagement_id: UUID,
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete a primary research record."""
    await _get_engagement(engagement_id, current_user, db)

    rec = await db.get(PrimaryResearch, record_id)
    if not rec or rec.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Primary research record not found")

    await db.delete(rec)
    await db.commit()
