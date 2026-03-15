"""Engagement CRUD and control endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
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


@router.delete("/{engagement_id}", status_code=204)
async def delete_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    """Delete an engagement and all its agent runs and findings (cascade)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    await db.delete(engagement)


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


@router.get(
    "/{engagement_id}/export/pdf",
    response_class=StreamingResponse,
    summary="Download the due diligence report as PDF",
    tags=["Export"],
)
async def export_pdf(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Generate and download a full PDF due diligence report for a completed engagement.

    The PDF includes:
    - Cover page with recommendation banner
    - Executive summary
    - Findings table (severity-coded)
    - Detailed analysis sections
    - Data sources & methodology appendix
    """
    from app.export.pdf import generate_pdf, REPORTLAB_AVAILABLE

    if not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="PDF export is not available: reportlab package is not installed.",
        )

    # Load the engagement
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Gather pipeline_data from engagement config
    pipeline_data = engagement.config.get("pipeline_data", {})
    deliverables = pipeline_data.get("deliverables", {})

    # If no deliverables yet, build a minimal placeholder so the PDF still renders
    if not deliverables:
        deliverables = {
            "executive_summary": {
                "title": "Due Diligence Executive Summary",
                "recommendation": "proceed_with_caution",
                "recommendation_rationale": "Analysis is still in progress or no pipeline has been run.",
                "key_findings": [],
                "risk_assessment": "",
                "source_count": 0,
            },
            "detailed_report": {"sections": [], "status": "pending"},
            "audit_trail": {
                "sources_accessed": [],
                "findings_generated": 0,
                "compliance_status": "pending",
            },
        }

    # Pull all findings from DB
    findings_result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(
            Finding.severity.desc(),   # critical first
            Finding.created_at.asc(),
        )
    )
    db_findings = findings_result.scalars().all()
    findings_dicts = [
        {
            "id": str(f.id),
            "finding_type": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
            "source_system": f.source_system,
            "title": f.title,
            "description": f.description,
            "data": f.data,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "requires_human_review": f.requires_human_review,
        }
        for f in db_findings
    ]

    config = engagement.config or {}
    target_company = config.get("target_company") or config.get("company_name", "Target Company")
    pe_firm = config.get("company_name", "PE Firm")

    # Generate the PDF (runs synchronously — fast enough for a report)
    import asyncio
    loop = asyncio.get_event_loop()
    pdf_bytes = await loop.run_in_executor(
        None,
        lambda: generate_pdf(
            deliverables=deliverables,
            findings=findings_dicts,
            target_company=target_company,
            pe_firm=pe_firm,
        ),
    )

    safe_name = target_company.replace(" ", "_").replace("/", "-")[:40]
    filename = f"KEEN_DiligenceReport_{safe_name}.pdf"

    import io
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
