"""Finding model — agent discoveries, discrepancies, and data points."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class FindingType(str, enum.Enum):
    DATA_POINT = "data_point"
    DISCREPANCY = "discrepancy"
    EXCEPTION = "exception"
    INSIGHT = "insight"
    EXECUTIVE_SUMMARY = "executive_summary"
    FLAG = "flag"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_type = Column(
        Enum(FindingType, name="finding_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_system = Column(String(100), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    data = Column(JSONB, default=dict, doc="Structured finding data")
    severity = Column(
        Enum(Severity, name="finding_severity", values_callable=lambda x: [e.value for e in x]),
        default=Severity.INFO,
        nullable=False,
    )
    requires_human_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    agent_run = relationship("AgentRun", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding {self.id} type={self.finding_type} severity={self.severity}>"
