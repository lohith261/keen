"""Pydantic schemas for agent runs, checkpoints, and findings."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AgentRunResponse(BaseModel):
    """Full agent run detail."""

    id: UUID
    engagement_id: UUID
    agent_type: str
    status: str
    current_step: int
    total_steps: int
    progress_pct: float
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckpointResponse(BaseModel):
    """Checkpoint summary (state_data excluded for size)."""

    id: UUID
    agent_run_id: UUID
    step_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    """Agent finding / discovery."""

    id: UUID
    agent_run_id: UUID
    finding_type: str
    source_system: str | None = None
    title: str
    description: str | None = None
    data: dict
    severity: str
    requires_human_review: bool
    created_at: datetime

    model_config = {"from_attributes": True}
