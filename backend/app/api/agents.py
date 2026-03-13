"""Agent run status, checkpoint, and findings endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.agent_run import AgentRun
from app.models.checkpoint import Checkpoint
from app.models.finding import Finding
from app.schemas.agent import AgentRunResponse, CheckpointResponse, FindingResponse

router = APIRouter()


@router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> AgentRun:
    """Get an agent run's current status and progress."""
    agent_run = await db.get(AgentRun, run_id)
    if not agent_run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return agent_run


@router.get("/{run_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(
    run_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> list[Checkpoint]:
    """List all checkpoints for an agent run."""
    # Verify run exists
    agent_run = await db.get(AgentRun, run_id)
    if not agent_run:
        raise HTTPException(status_code=404, detail="Agent run not found")

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
) -> list[Finding]:
    """List all findings from a specific agent run."""
    agent_run = await db.get(AgentRun, run_id)
    if not agent_run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    result = await db.execute(
        select(Finding)
        .where(Finding.agent_run_id == run_id)
        .order_by(Finding.created_at.desc())
    )
    return list(result.scalars().all())
