"""
Engagement service — business logic for managing due diligence engagements.

Orchestrates the lifecycle: create → configure → start → monitor → complete.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.engagement import Engagement, EngagementStatus
from app.models.agent_run import AgentRun, AgentRunStatus, AgentType

logger = logging.getLogger(__name__)


class EngagementService:
    """High-level engagement management."""

    def __init__(self, db: AsyncSession, redis: Any | None = None):
        self.db = db
        self.redis = redis

    async def create_engagement(
        self,
        company_name: str,
        config: dict | None = None,
        **kwargs: Any,
    ) -> Engagement:
        """Create a new engagement with default configuration."""
        default_config = {
            "agents": ["research", "analysis", "delivery"],
            "systems": [
                "salesforce", "netsuite", "sec_edgar",
                "bloomberg", "pitchbook", "zoominfo",
            ],
            "distribution_channels": ["internal"],
            "checkpointing": True,
            "timeout_hours": 4,
        }

        if config:
            default_config.update(config)

        engagement = Engagement(
            company_name=company_name,
            config=default_config,
            **kwargs,
        )
        self.db.add(engagement)
        await self.db.flush()
        await self.db.refresh(engagement)
        return engagement

    async def get_engagement_with_status(self, engagement_id: UUID) -> dict | None:
        """Get engagement with computed status information."""
        result = await self.db.execute(
            select(Engagement)
            .options(selectinload(Engagement.agent_runs))
            .where(Engagement.id == engagement_id)
        )
        engagement = result.scalar_one_or_none()
        if not engagement:
            return None

        # Compute aggregate progress
        runs = engagement.agent_runs
        total_progress = sum(r.progress_pct for r in runs) / max(len(runs), 1)

        return {
            "engagement": engagement,
            "total_progress": total_progress,
            "agents_completed": sum(1 for r in runs if r.status == AgentRunStatus.COMPLETED),
            "agents_running": sum(1 for r in runs if r.status == AgentRunStatus.RUNNING),
            "agents_failed": sum(1 for r in runs if r.status == AgentRunStatus.FAILED),
            "agents_total": len(runs),
        }

    async def calculate_duration(self, engagement_id: UUID) -> dict:
        """Calculate elapsed and estimated remaining time."""
        engagement = await self.db.get(Engagement, engagement_id)
        if not engagement or not engagement.started_at:
            return {"elapsed_seconds": 0, "estimated_remaining_seconds": 0}

        now = datetime.now(timezone.utc)
        elapsed = (now - engagement.started_at).total_seconds()

        # Rough estimate based on progress
        result = await self.db.execute(
            select(AgentRun).where(AgentRun.engagement_id == engagement_id)
        )
        runs = list(result.scalars().all())
        avg_progress = sum(r.progress_pct for r in runs) / max(len(runs), 1)

        if avg_progress > 0:
            estimated_total = elapsed / (avg_progress / 100)
            remaining = max(0, estimated_total - elapsed)
        else:
            remaining = 0

        return {
            "elapsed_seconds": elapsed,
            "estimated_remaining_seconds": remaining,
        }
