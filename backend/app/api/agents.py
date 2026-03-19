"""Agent run status, checkpoint, and findings endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.dependencies import get_session
from app.models.agent_run import AgentRun
from app.models.checkpoint import Checkpoint
from app.models.engagement import Engagement
from app.models.finding import Finding
from app.schemas.agent import AgentRunResponse, CheckpointResponse, FindingResponse

router = APIRouter()


async def _get_owned_run(run_id: UUID, current_user: AuthUser, db: AsyncSession) -> AgentRun:
    """Fetch an agent run and verify the current user owns the parent engagement."""
    agent_run = await db.get(AgentRun, run_id)
    if not agent_run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    # Verify ownership via parent engagement
    engagement = await db.get(Engagement, agent_run.engagement_id)
    if engagement and engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised to access this agent run")
    return agent_run


@router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> AgentRun:
    """Get an agent run's current status and progress."""
    return await _get_owned_run(run_id, current_user, db)


@router.get("/{run_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(
    run_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[Checkpoint]:
    """List all checkpoints for an agent run."""
    await _get_owned_run(run_id, current_user, db)

    result = await db.execute(
        select(Checkpoint)
        .where(Checkpoint.agent_run_id == run_id)
        .order_by(Checkpoint.step_index.desc())
    )
    return list(result.scalars().all())


@router.get("/{run_id}/findings", response_model=list[FindingResponse])
async def list_agent_findings(
    run_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[Finding]:
    """List all findings from a specific agent run."""
    await _get_owned_run(run_id, current_user, db)

    result = await db.execute(
        select(Finding)
        .where(Finding.agent_run_id == run_id)
        .order_by(Finding.created_at.desc())
    )
    return list(result.scalars().all())
