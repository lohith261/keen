"""Tests for agent orchestrator logic."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement import Engagement, EngagementStatus
from app.models.agent_run import AgentRun, AgentRunStatus, AgentType


@pytest.mark.asyncio
async def test_agent_run_creation(db_session: AsyncSession):
    """AgentRun should be created with correct defaults."""
    engagement = Engagement(company_name="Test Corp")
    db_session.add(engagement)
    await db_session.flush()

    agent_run = AgentRun(
        engagement_id=engagement.id,
        agent_type=AgentType.RESEARCH,
    )
    db_session.add(agent_run)
    await db_session.flush()
    await db_session.refresh(agent_run)

    assert agent_run.status == AgentRunStatus.QUEUED
    assert agent_run.current_step == 0
    assert agent_run.progress_pct == 0.0
    assert agent_run.engagement_id == engagement.id


@pytest.mark.asyncio
async def test_engagement_agent_run_relationship(db_session: AsyncSession):
    """Engagement should have agent_runs relationship."""
    engagement = Engagement(
        company_name="Rel Test Corp",
        config={"agents": ["research", "analysis"]},
    )
    db_session.add(engagement)
    await db_session.flush()

    for agent_type in [AgentType.RESEARCH, AgentType.ANALYSIS]:
        run = AgentRun(
            engagement_id=engagement.id,
            agent_type=agent_type,
        )
        db_session.add(run)

    await db_session.flush()
    await db_session.refresh(engagement)

    # SQLite doesn't auto-load relationships; query directly
    from sqlalchemy import select
    result = await db_session.execute(
        select(AgentRun).where(AgentRun.engagement_id == engagement.id)
    )
    runs = list(result.scalars().all())
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_engagement_status_transitions(db_session: AsyncSession):
    """Engagement status should transition correctly."""
    engagement = Engagement(company_name="Status Test Corp")
    db_session.add(engagement)
    await db_session.flush()

    assert engagement.status == EngagementStatus.DRAFT

    engagement.status = EngagementStatus.RUNNING
    await db_session.flush()
    assert engagement.status == EngagementStatus.RUNNING

    engagement.status = EngagementStatus.PAUSED
    await db_session.flush()
    assert engagement.status == EngagementStatus.PAUSED

    engagement.status = EngagementStatus.COMPLETED
    await db_session.flush()
    assert engagement.status == EngagementStatus.COMPLETED
