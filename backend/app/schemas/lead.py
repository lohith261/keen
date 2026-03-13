"""Pydantic schemas for leads (Request Access form)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LeadCreate(BaseModel):
    """Schema for creating a new lead from the landing page."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Jane Smith"])
    email: str = Field(..., min_length=5, max_length=255, examples=["jane@acmecapital.com"])
    company: str | None = Field(None, max_length=255, examples=["Acme Capital Partners"])
    aum_range: str | None = Field(None, max_length=100, examples=["$100M-$500M"])
    message: str | None = Field(None, examples=["Interested in piloting for our next deal."])


class LeadResponse(BaseModel):
    """Schema for returning a lead."""

    id: UUID
    name: str
    email: str
    company: str | None = None
    aum_range: str | None = None
    message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
