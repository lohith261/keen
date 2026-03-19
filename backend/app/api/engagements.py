"""Engagement CRUD and control endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.api.auth_deps import AuthUser, get_current_user, get_optional_user
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

            # ── Commit #1: findings + engagement status ───────────────────────
            # Commit ALL findings and status updates produced by the agents
            # *before* attempting to store the (potentially large) pipeline_data
            # blob. This ensures findings survive even if pipeline_data storage
            # fails (which would otherwise trigger a rollback and erase them).
            await session.commit()

        except Exception:
            await session.rollback()
            logger.exception("Orchestrator background task failed for %s", engagement_id)
            return

        # ── Commit #2: pipeline_data in engagement.config ─────────────────────
        # Separate transaction so a serialisation failure here never rolls back
        # the already-committed findings.
        try:
            async with async_session_factory() as config_session:
                engagement = await config_session.get(Engagement, engagement_id)
                if engagement and result.get("pipeline_data"):
                    engagement.config = {
                        **engagement.config,
                        "pipeline_data": result["pipeline_data"],
                    }
                    flag_modified(engagement, "config")
                    await config_session.commit()
        except Exception:
            logger.exception(
                "Failed to persist pipeline_data for %s (findings already committed)",
                engagement_id,
            )


@router.post("", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    payload: EngagementCreate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> Engagement:
    """Create a new due diligence engagement (requires auth)."""
    engagement = Engagement(
        company_name=payload.company_name,
        target_company=payload.target_company,
        pe_firm=payload.pe_firm,
        deal_size=payload.deal_size,
        engagement_type=payload.engagement_type,
        config=payload.config,
        notes=payload.notes,
        user_id=current_user.sub,
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
    current_user: AuthUser = Depends(get_current_user),
) -> list[Engagement]:
    """List engagements for the authenticated user."""
    query = select(Engagement).order_by(Engagement.created_at.desc())
    # Show engagements owned by this user OR legacy rows (user_id is null)
    from sqlalchemy import or_
    query = query.where(
        or_(
            Engagement.user_id == current_user.sub,
            Engagement.user_id.is_(None),
        )
    )
    if status_filter:
        query = query.where(Engagement.status == status_filter)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{engagement_id}", response_model=EngagementWithRuns)
async def get_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
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
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to access this engagement")
    return engagement


@router.patch("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    engagement_id: UUID,
    payload: EngagementUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> Engagement:
    """Update engagement details (only in DRAFT status)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to update this engagement")
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
    current_user: AuthUser = Depends(get_current_user),
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
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to start this engagement")
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
    current_user: AuthUser = Depends(get_current_user),
) -> Engagement:
    """Pause a running engagement (checkpoint all active agents)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to pause this engagement")
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
    current_user: AuthUser = Depends(get_current_user),
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
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to resume this engagement")
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


class RestartBody(BaseModel):
    demo_mode: bool | None = None  # Override the demo_mode stored in engagement config


@router.post("/{engagement_id}/restart", response_model=EngagementWithRuns)
async def restart_engagement(
    engagement_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    body: RestartBody = RestartBody(),
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> Engagement:
    """Reset a completed or failed engagement back to draft and re-run the full pipeline."""
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to restart this engagement")
    # Allow force-restart even from RUNNING (e.g. after a server restart left the
    # engagement stuck in RUNNING with no active background task).
    # We simply proceed — old AgentRuns are deleted below, which implicitly
    # cancels any in-progress work for the stopped process.

    # Delete old agent runs — findings cascade via agent_run_id FK
    for run in list(engagement.agent_runs):
        await db.delete(run)

    # Reset engagement state
    engagement.status = EngagementStatus.DRAFT
    engagement.started_at = None
    engagement.completed_at = None

    # Apply demo_mode override if provided (e.g. frontend toggling live vs demo)
    if body.demo_mode is not None:
        updated_config = dict(engagement.config or {})
        updated_config["demo_mode"] = body.demo_mode
        engagement.config = updated_config
        flag_modified(engagement, "config")

    await db.flush()

    # Create fresh agent runs
    agent_types_to_run = engagement.config.get("agents", ["research", "analysis", "delivery"])
    for agent_type_str in agent_types_to_run:
        try:
            agent_type = AgentType(agent_type_str)
        except ValueError:
            continue
        db.add(AgentRun(
            engagement_id=engagement.id,
            agent_type=agent_type,
            status=AgentRunStatus.QUEUED,
        ))

    engagement.status = EngagementStatus.RUNNING
    engagement.started_at = datetime.now(timezone.utc)
    await db.commit()

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
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete an engagement (only owner or legacy rows)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    # Only the owner (or admin for legacy null rows) may delete
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to delete this engagement")
    await db.delete(engagement)


@router.get("/{engagement_id}/findings", response_model=list[FindingResponse])
async def get_engagement_findings(
    engagement_id: UUID,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[Finding]:
    """Get findings across all agents for an engagement (paginated)."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to access this engagement")

    result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(Finding.created_at.desc())
        .offset(skip)
        .limit(min(limit, 500))  # hard cap at 500 per page
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
    current_user: AuthUser = Depends(get_current_user),
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
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to export this engagement")

    # Gather deliverables from engagement config.
    # The delivery agent stores them at:
    #   pipeline_data.delivery.finalize_delivery.deliverables
    pipeline_data = engagement.config.get("pipeline_data", {})
    deliverables = (
        pipeline_data
        .get("delivery", {})
        .get("finalize_delivery", {})
        .get("deliverables", {})
    )

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


@router.get(
    "/{engagement_id}/export/excel",
    response_class=StreamingResponse,
    summary="Download the due diligence report as Excel workbook",
    tags=["Export"],
)
async def export_excel(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    """
    Generate and download a structured Excel workbook for a completed engagement.

    The workbook includes:
    - Cover sheet (engagement metadata + recommendation)
    - Executive Summary tab
    - Key Findings tab (severity-colour-coded)
    - One data tab per connected source (Salesforce, NetSuite, Bloomberg, etc.)
    - Compliance tab (PII scan results)
    """
    import asyncio
    import io

    from app.export.excel import generate_excel

    # Load the engagement
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to export this engagement")

    pipeline_data = engagement.config.get("pipeline_data", {})
    deliverables = (
        pipeline_data
        .get("delivery", {})
        .get("finalize_delivery", {})
        .get("deliverables", {})
    ) or {}

    # Source data lives in research step state
    research_state = pipeline_data.get("research", {})
    source_data: dict = {}
    for key, value in research_state.items():
        if key.startswith("data_") and isinstance(value, dict):
            source_data[key.replace("data_", "")] = value

    # Pull findings from DB
    findings_result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(Finding.severity.desc(), Finding.created_at.asc())
    )
    db_findings = findings_result.scalars().all()
    findings_dicts = [
        {
            "id": str(f.id),
            "finding_type": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
            "source_system": f.source_system,
            "title": f.title,
            "description": f.description,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "requires_human_review": f.requires_human_review,
        }
        for f in db_findings
    ]

    config = engagement.config or {}
    target_company = config.get("target_company") or config.get("company_name", "Target Company")
    pe_firm = config.get("company_name", "PE Firm")

    loop = asyncio.get_event_loop()
    excel_bytes = await loop.run_in_executor(
        None,
        lambda: generate_excel(
            deliverables=deliverables,
            findings=findings_dicts,
            source_data=source_data,
            target_company=target_company,
            pe_firm=pe_firm,
        ),
    )

    safe_name = target_company.replace(" ", "_").replace("/", "-")[:40]
    filename = f"KEEN_DiligenceReport_{safe_name}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{engagement_id}/export/gsheets",
    summary="Export the due diligence report to Google Sheets",
    tags=["Export"],
)
async def export_gsheets(
    engagement_id: UUID,
    credentials_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a Google Spreadsheet from a completed engagement and return its URL.

    The caller must supply ``credentials_id`` (the engagement id used as the
    vault namespace) — credentials are loaded from the vault under system key
    ``google_sheets``.

    Returns JSON: ``{"url": "https://docs.google.com/spreadsheets/d/..."}``
    """
    import json as _json

    from app.auth.vault import CredentialVault
    from app.export.gsheets import GSPREAD_AVAILABLE, create_google_sheet

    if not GSPREAD_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Google Sheets export is unavailable: gspread / google-auth not installed.",
        )

    # Load the engagement
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Load Google credentials from vault
    vault = CredentialVault(db=db)
    try:
        cred_engagement_id = UUID(credentials_id)
    except ValueError:
        cred_engagement_id = engagement_id
    raw_creds = await vault.get_credentials(cred_engagement_id, "google_sheets")
    if not raw_creds:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Google Sheets credentials found. "
                "Please add a Google service account key via the Credentials panel."
            ),
        )

    # Parse service account JSON
    sa_json_str = raw_creds.get("service_account_json", "")
    if not sa_json_str:
        raise HTTPException(status_code=400, detail="service_account_json is empty in stored credentials.")
    try:
        service_account_info = _json.loads(sa_json_str)
    except _json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"service_account_json is not valid JSON: {exc}") from exc

    share_email = raw_creds.get("share_email") or None

    # Gather engagement data (same logic as Excel endpoint)
    pipeline_data = engagement.config.get("pipeline_data", {})
    deliverables = (
        pipeline_data
        .get("delivery", {})
        .get("finalize_delivery", {})
        .get("deliverables", {})
    ) or {}

    research_state = pipeline_data.get("research", {})
    source_data: dict = {}
    for key, value in research_state.items():
        if key.startswith("data_") and isinstance(value, dict):
            source_data[key.replace("data_", "")] = value

    # Pull findings
    findings_result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(Finding.severity.desc(), Finding.created_at.asc())
    )
    db_findings = findings_result.scalars().all()
    findings_dicts = [
        {
            "id": str(f.id),
            "finding_type": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
            "source_system": f.source_system,
            "title": f.title,
            "description": f.description,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "requires_human_review": f.requires_human_review,
        }
        for f in db_findings
    ]

    config = engagement.config or {}
    target_company = config.get("target_company") or config.get("company_name", "Target Company")
    pe_firm = config.get("company_name", "PE Firm")

    # Run in executor (gspread is synchronous)
    loop = asyncio.get_event_loop()
    try:
        sheet_url = await loop.run_in_executor(
            None,
            lambda: create_google_sheet(
                deliverables=deliverables,
                findings=findings_dicts,
                source_data=source_data,
                target_company=target_company,
                pe_firm=pe_firm,
                service_account_info=service_account_info,
                share_email=share_email,
            ),
        )
    except Exception as exc:
        logger.exception("Google Sheets export failed for engagement %s", engagement_id)
        raise HTTPException(status_code=500, detail=f"Google Sheets export failed: {exc}") from exc

    return {"url": sheet_url}


@router.get(
    "/{engagement_id}/export/drive",
    summary="Upload the due diligence report (PDF + Excel) to Google Drive",
    tags=["Export"],
)
async def export_drive(
    engagement_id: UUID,
    credentials_id: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    """
    Generate a PDF and Excel report for a completed engagement, upload both
    to Google Drive using the stored Google service-account credentials, and
    return shareable links.

    Credentials are loaded from the vault under system key ``google_sheets``
    (same service account is reused for Drive access).

    Returns JSON::

        {
          "pdf":   {"url": "https://drive.google.com/file/d/.../view"},
          "excel": {"url": "https://drive.google.com/file/d/.../view"},
          "status": "completed" | "partial" | "error"
        }
    """
    import json as _json

    from app.auth.vault import CredentialVault
    from app.export.excel import create_excel_report
    from app.export.pdf import create_pdf_report
    from app.integrations.distribution.google_drive import upload_report as gd_upload

    # Load the engagement
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Load Google credentials from vault (reuse google_sheets service account)
    vault = CredentialVault(db=db)
    try:
        cred_engagement_id = UUID(credentials_id) if credentials_id else engagement_id
    except ValueError:
        cred_engagement_id = engagement_id

    raw_creds = await vault.get_credentials(cred_engagement_id, "google_sheets")
    if not raw_creds:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Google credentials found. "
                "Please add a Google service account key via the Credentials panel."
            ),
        )

    sa_json_str = raw_creds.get("service_account_json", "")
    if not sa_json_str:
        raise HTTPException(
            status_code=400,
            detail="service_account_json is empty in stored credentials.",
        )
    try:
        service_account_info = _json.loads(sa_json_str)
    except _json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"service_account_json is not valid JSON: {exc}",
        ) from exc

    folder_id: str | None = raw_creds.get("folder_id") or None
    share_email: str | None = raw_creds.get("share_email") or None

    # Gather engagement data
    pipeline_data = engagement.config.get("pipeline_data", {})
    deliverables = (
        pipeline_data
        .get("delivery", {})
        .get("finalize_delivery", {})
        .get("deliverables", {})
    ) or {}

    research_state = pipeline_data.get("research", {})
    source_data: dict = {}
    for key, value in research_state.items():
        if key.startswith("data_") and isinstance(value, dict):
            source_data[key.replace("data_", "")] = value

    findings_result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(Finding.severity.desc(), Finding.created_at.asc())
    )
    db_findings = findings_result.scalars().all()
    findings_dicts = [
        {
            "id": str(f.id),
            "finding_type": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
            "source_system": f.source_system,
            "title": f.title,
            "description": f.description,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "requires_human_review": f.requires_human_review,
        }
        for f in db_findings
    ]

    config = engagement.config or {}
    target_company = config.get("target_company") or config.get("company_name", "Target Company")
    pe_firm = config.get("company_name", "PE Firm")

    # Generate PDF + Excel bytes (sync libraries → run in executor)
    loop = asyncio.get_event_loop()
    try:
        pdf_bytes = await loop.run_in_executor(
            None,
            lambda: create_pdf_report(
                deliverables=deliverables,
                findings=findings_dicts,
                target_company=target_company,
                pe_firm=pe_firm,
            ),
        )
        excel_bytes = await loop.run_in_executor(
            None,
            lambda: create_excel_report(
                deliverables=deliverables,
                findings=findings_dicts,
                source_data=source_data,
                target_company=target_company,
                pe_firm=pe_firm,
            ),
        )
    except Exception as exc:
        logger.exception("Report generation failed for Drive export, engagement %s", engagement_id)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc

    # Upload to Drive
    try:
        result = await loop.run_in_executor(
            None,
            lambda: gd_upload(
                service_account_info=service_account_info,
                target_company=target_company,
                deliverables=deliverables,
                findings=findings_dicts,
                pdf_bytes=pdf_bytes,
                excel_bytes=excel_bytes,
                folder_id=folder_id,
                share_email=share_email,
            ),
        )
    except Exception as exc:
        logger.exception("Google Drive upload failed for engagement %s", engagement_id)
        raise HTTPException(status_code=500, detail=f"Google Drive upload failed: {exc}") from exc

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Drive upload failed"))

    return result
