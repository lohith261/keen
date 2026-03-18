"""Engagement model — a due diligence engagement."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class EngagementStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False, index=True)
    target_company = Column(String(255), nullable=True)
    pe_firm = Column(String(255), nullable=True)
    deal_size = Column(String(100), nullable=True)
    engagement_type = Column(String(100), default="full_diligence")
    status = Column(
        Enum(EngagementStatus, name="engagement_status", values_callable=lambda x: [e.value for e in x]),
        default=EngagementStatus.DRAFT,
        nullable=False,
        index=True,
    )
    config = Column(JSONB, default=dict, doc="Agent config — which agents/systems to use")
    notes = Column(Text, nullable=True)
    user_id = Column(String(255), nullable=True, index=True, doc="Supabase user UUID (null = legacy)")

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    agent_runs = relationship("AgentRun", back_populates="engagement", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="engagement", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="engagement", cascade="all, delete-orphan")
    transcripts = relationship("ExpertTranscript", back_populates="engagement", cascade="all, delete-orphan")
    monitoring_schedules = relationship("MonitoringSchedule", cascade="all, delete-orphan")
    primary_research_records = relationship("PrimaryResearch", back_populates="engagement", cascade="all, delete-orphan")
    external_records = relationship("ExternalRecord", back_populates="engagement", cascade="all, delete-orphan")
    legal_findings = relationship("LegalFinding", back_populates="engagement", cascade="all, delete-orphan")
    technical_dd_reports = relationship("TechnicalDDReport", back_populates="engagement", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Engagement {self.id} company={self.company_name!r} status={self.status}>"
