"""AgentRun model — an individual agent execution within an engagement."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AgentType(str, enum.Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DELIVERY = "delivery"


class AgentRunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type = Column(
        Enum(AgentType, name="agent_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        Enum(AgentRunStatus, name="agent_run_status", values_callable=lambda x: [e.value for e in x]),
        default=AgentRunStatus.QUEUED,
        nullable=False,
        index=True,
    )
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

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
    engagement = relationship("Engagement", back_populates="agent_runs")
    checkpoints = relationship("Checkpoint", back_populates="agent_run", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="agent_run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AgentRun {self.id} type={self.agent_type} status={self.status}>"
