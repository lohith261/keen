"""Portfolio monitoring models — scheduled metric pulls and delta tracking."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MonitoringSchedule(Base):
    """A recurring monitoring schedule attached to a post-acquisition engagement."""

    __tablename__ = "monitoring_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=True)
    frequency = Column(String(50), nullable=False, default="monthly")
    enabled = Column(Boolean, nullable=False, default=True)

    # Which source systems to pull on each run
    sources = Column(JSONB, nullable=True)

    # Acquisition-time baseline for delta comparison
    baseline_snapshot = Column(JSONB, nullable=True)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    runs = relationship("MonitoringRun", back_populates="schedule", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MonitoringSchedule {self.id} name={self.name!r} freq={self.frequency}>"


class MonitoringRun(Base):
    """A single execution of a monitoring schedule."""

    __tablename__ = "monitoring_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitoring_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(String(20), nullable=False, default="pending", index=True)

    # Delta findings vs baseline
    deltas = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    schedule = relationship("MonitoringSchedule", back_populates="runs")

    def __repr__(self) -> str:
        return f"<MonitoringRun {self.id} status={self.status}>"
