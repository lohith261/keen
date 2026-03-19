"""Lead capture endpoints — "Request Access" form from the landing page."""

import time
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.dependencies import get_session
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadResponse

router = APIRouter()

# ── Simple in-memory rate limiter ─────────────────────────────────────────────
# Limits POST /leads to 5 submissions per IP per hour.
# Uses a sliding-window counter keyed by client IP.
_RATE_LIMIT_MAX = 5          # max submissions
_RATE_LIMIT_WINDOW = 3600    # per 1 hour (seconds)
_ip_submissions: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    # Drop timestamps outside the window
    _ip_submissions[ip] = [t for t in _ip_submissions[ip] if t > window_start]
    if len(_ip_submissions[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait before submitting again.",
            headers={"Retry-After": str(_RATE_LIMIT_WINDOW)},
        )
    _ip_submissions[ip].append(now)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Lead:
    """Submit a 'Request Access' form (public endpoint — no auth required)."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
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
    current_user: AuthUser = Depends(get_current_user),  # requires login
) -> list[Lead]:
    """List all leads (requires authentication)."""
    result = await db.execute(
        select(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),  # requires login
) -> Lead:
    """Get a single lead by ID (requires authentication)."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
