"""Pydantic schemas for engagements."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EngagementCreate(BaseModel):
    """Schema for creating a new due diligence engagement."""

    company_name: str = Field(..., min_length=1, max_length=255, examples=["Target Corp"])
    target_company: str | None = Field(None, max_length=255, examples=["Target Corp"])
    pe_firm: str | None = Field(None, max_length=255, examples=["Acme Capital Partners"])
    deal_size: str | None = Field(None, max_length=100, examples=["$250M"])
    engagement_type: str = Field("full_diligence", max_length=100)
    config: dict = Field(
        default_factory=dict,
        examples=[{
            "agents": ["research", "analysis", "delivery"],
            "systems": ["salesforce", "netsuite", "sec_edgar"],
        }],
    )
    notes: str | None = None


class EngagementUpdate(BaseModel):
    """Schema for updating an engagement."""

    company_name: str | None = None
    target_company: str | None = None
    pe_firm: str | None = None
    deal_size: str | None = None
    engagement_type: str | None = None
    config: dict | None = None
    notes: str | None = None


class EngagementResponse(BaseModel):
    """Schema for returning an engagement."""

    id: UUID
    company_name: str
    target_company: str | None = None
    pe_firm: str | None = None
    deal_size: str | None = None
    engagement_type: str
    status: str
    config: dict
    notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EngagementWithRuns(EngagementResponse):
    """Engagement response including agent run summaries."""

    agent_runs: list["AgentRunSummary"] = []


class AgentRunSummary(BaseModel):
    """Compact agent run info for embedding in engagement responses."""

    id: UUID
    agent_type: str
    status: str
    progress_pct: float
    current_step: int
    total_steps: int

    model_config = {"from_attributes": True}


# Rebuild for forward ref
EngagementWithRuns.model_rebuild()
