"""Checkpoint manager — handles state serialization, storage, and retrieval."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkpoint import Checkpoint

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages agent state checkpoints with dual storage (Redis + PostgreSQL).

    Redis provides fast access for hot checkpoints; PostgreSQL provides
    durable persistence for crash recovery.
    """

    def __init__(self, db: AsyncSession, redis: Any | None = None):
        self.db = db
        self.redis = redis

    async def save(
        self,
        agent_run_id: UUID,
        step_index: int,
        state: dict,
    ) -> Checkpoint:
        """Save a checkpoint to both Redis and PostgreSQL."""
        checkpoint_data = {
            "step_index": step_index,
            "state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Redis (fast, ephemeral)
        if self.redis:
            key = f"checkpoint:{agent_run_id}"
            await self.redis.set(key, json.dumps(checkpoint_data), ex=86400)

        # PostgreSQL (durable)
        checkpoint = Checkpoint(
            agent_run_id=agent_run_id,
            step_index=step_index,
            state_data=checkpoint_data,
        )
        self.db.add(checkpoint)
        await self.db.flush()
        await self.db.refresh(checkpoint)

        logger.info(f"Checkpoint saved: run={agent_run_id} step={step_index}")
        return checkpoint

    async def load_latest(self, agent_run_id: UUID) -> dict | None:
        """Load the most recent checkpoint for an agent run."""
        # Try Redis first
        if self.redis:
            key = f"checkpoint:{agent_run_id}"
            data = await self.redis.get(key)
            if data:
                return json.loads(data)

        # Fall back to PostgreSQL
        result = await self.db.execute(
            select(Checkpoint)
            .where(Checkpoint.agent_run_id == agent_run_id)
            .order_by(Checkpoint.step_index.desc())
            .limit(1)
        )
        checkpoint = result.scalar_one_or_none()
        if checkpoint:
            return checkpoint.state_data

        return None

    async def list_checkpoints(
        self,
        agent_run_id: UUID,
        limit: int = 50,
    ) -> list[Checkpoint]:
        """List checkpoints for an agent run, most recent first."""
        result = await self.db.execute(
            select(Checkpoint)
            .where(Checkpoint.agent_run_id == agent_run_id)
            .order_by(Checkpoint.step_index.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def clear_redis_checkpoint(self, agent_run_id: UUID) -> None:
        """Remove the Redis checkpoint for a completed/failed run."""
        if self.redis:
            key = f"checkpoint:{agent_run_id}"
            await self.redis.delete(key)
