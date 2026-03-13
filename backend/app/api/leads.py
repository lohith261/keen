"""Lead capture endpoints — "Request Access" form from the landing page."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadResponse

router = APIRouter()


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    db: AsyncSession = Depends(get_session),
) -> Lead:
    """Submit a 'Request Access' form."""
    lead = Lead(
        name=payload.name,
        email=payload.email,
        company=payload.company,
        aum_range=payload.aum_range,
        message=payload.message,
    )
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
) -> list[Lead]:
    """List all leads (admin endpoint)."""
    result = await db.execute(
        select(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> Lead:
    """Get a single lead by ID."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
