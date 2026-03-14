"""Engagement CRUD and control endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.database import async_session_factory
from app.dependencies import get_session
from app.models.engagement import Engagement, EngagementStatus
from app.models.agent_run import AgentRun, AgentRunStatus, AgentType
from app.models.finding import Finding
from app.schemas.engagement import (
    EngagementCreate,
    EngagementResponse,
    EngagementUpdate,
    EngagementWithRuns,
)
from app.schemas.agent import FindingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_orchestrator(engagement_id: UUID, redis: Any | None) -> None:
    """Background task: run the full orchestration pipeline in its own DB session."""
    from app.agents.orchestrator import AgentOrchestrator
    from app.websocket.agent_status import emit_agent_event

    async def on_event(event_type: str, data: dict) -> None:
        try:
            await emit_agent_event(str(engagement_id), event_type, data)
        except Exception:
            pass

    async with async_session_factory() as session:
        try:
            orch = AgentOrchestrator(
                engagement_id=engagement_id,
                db=session,
                redis=redis,
                on_event=on_event,
            )
            result = await orch.run()

            # Persist pipeline_data into engagement.config so the UI can read it
            engagement = await session.get(Engagement, engagement_id)
            if engagement and result.get("pipeline_data"):
                engagement.config = {
                    **engagement.config,
                    "pipeline_data": result["pipeline_data"],
                }
                flag_modified(engagement, "config")

            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Orchestrator background task failed for %s", engagement_id)


@router.post("", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    payload: EngagementCreate,
    db: AsyncSession = Depends(get_session),
) -> Engagement:
    """Create a new due diligence engagement."""
    engagement = Engagement(
        company_name=payload.company_name,
        target_company=payload.target_company,
        pe_firm=payload.pe_firm,
        deal_size=payload.deal_size,
        engagement_type=payload.engagement_type,
        config=payload.config,
        notes=payload.notes,
    )
    db.add(engagement)
    await db.flush()
    await db.refresh(engagement)
    return engagement


@router.get("", response_model=list[EngagementResponse])
async def list_engagements(
    skip: int = 0,
    limit: int = 50,
    status_filter: EngagementStatus | None = None,
    db: AsyncSession = Depends(get_session),
) -> list[Engagement]:
    """List engagements, optionally filtered by status."""
    query = select(Engagement).order_by(Engagement.created_at.desc())
    if status_filter:
        query = query.where(Engagement.status == status_filter)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{engagement_id}", response_model=EngagementWithRuns)
async def get_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> Engagement:
    """Get engagement details including agent run summaries."""
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement


@router.patch("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    engagement_id: UUID,
    payload: EngagementUpdate,
    db: AsyncSession = Depends(get_session),
) -> Engagement:
    """Update engagement details (only in DRAFT status)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status != EngagementStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update engagement in {engagement.status} status",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(engagement, field, value)

    await db.flush()
    await db.refresh(engagement)
    return engagement


@router.post("/{engagement_id}/start", response_model=EngagementWithRuns)
async def start_engagement(
    engagement_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Engagement:
    """Start agent orchestration for an engagement."""
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status not in (EngagementStatus.DRAFT, EngagementStatus.PAUSED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start engagement in {engagement.status} status",
        )

    # Determine which agents to run from config
    agent_types_to_run = engagement.config.get("agents", ["research", "analysis", "delivery"])

    # Create agent runs if this is a fresh start (not resume)
    if engagement.status == EngagementStatus.DRAFT:
        for agent_type_str in agent_types_to_run:
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                continue
            agent_run = AgentRun(
                engagement_id=engagement.id,
                agent_type=agent_type,
                status=AgentRunStatus.QUEUED,
            )
            db.add(agent_run)

    engagement.status = EngagementStatus.RUNNING
    engagement.started_at = datetime.now(timezone.utc)

    # Commit NOW so the background task's separate session can see the agent runs.
    # (FastAPI background tasks run before dependency teardown, so the auto-commit
    # from get_session would arrive too late.)
    await db.commit()

    # Reload with agent runs for the response
    db.expire_all()
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()

    # Dispatch orchestrator as a background task
    redis = getattr(request.app.state, "redis", None)
    background_tasks.add_task(_run_orchestrator, engagement.id, redis)

    return engagement


@router.post("/{engagement_id}/pause", response_model=EngagementResponse)
async def pause_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> Engagement:
    """Pause a running engagement (checkpoint all active agents)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status != EngagementStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Can only pause a running engagement",
        )

    engagement.status = EngagementStatus.PAUSED

    # Pause all running agent runs
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.status == AgentRunStatus.RUNNING,
        )
    )
    for agent_run in result.scalars().all():
        agent_run.status = AgentRunStatus.PAUSED

    await db.flush()
    await db.refresh(engagement)
    return engagement


@router.post("/{engagement_id}/resume", response_model=EngagementWithRuns)
async def resume_engagement(
    engagement_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Engagement:
    """Resume a paused engagement from the last checkpoint."""
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status != EngagementStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail="Can only resume a paused engagement",
        )

    engagement.status = EngagementStatus.RUNNING

    # Re-queue paused agents
    for run in engagement.agent_runs:
        if run.status == AgentRunStatus.PAUSED:
            run.status = AgentRunStatus.QUEUED

    await db.commit()

    # Reload
    db.expire_all()
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()

    redis = getattr(request.app.state, "redis", None)
    background_tasks.add_task(_run_orchestrator, engagement.id, redis)

    return engagement


@router.get("/{engagement_id}/findings", response_model=list[FindingResponse])
async def get_engagement_findings(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> list[Finding]:
    """Get all findings across all agents for an engagement."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(Finding.created_at.desc())
    )
    return list(result.scalars().all())
