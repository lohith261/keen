"""TechnicalDDReport model — GitHub repository analysis results for technical due diligence."""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class TechnicalDDReport(Base):
    __tablename__ = "technical_dd_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    # Repository info
    repo_url = Column(String(500), nullable=True)

    # Language breakdown — {language: bytes}
    language_stats = Column(JSONB, nullable=False, default=dict)

    # Contributor metrics
    contributor_count = Column(Integer, nullable=True)
    # Minimum number of contributors whose commits account for >= 50% of total
    bus_factor = Column(Integer, nullable=True)
    # Average commits per week over the last 90 days (approx. 13 weeks)
    commit_velocity = Column(Float, nullable=True)

    open_issues_count = Column(Integer, nullable=True)

    # Security findings — list of {package, severity, summary, url}
    security_vulnerabilities = Column(JSONB, nullable=False, default=list)
    # Dependency risk items — list of {name, version, risk, reason}
    dependency_risks = Column(JSONB, nullable=False, default=list)

    # Composite health score 0–100
    health_score = Column(Float, nullable=True)

    # Processing state: pending | ready | error
    status = Column(String(20), nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="technical_dd_reports")

    def __repr__(self) -> str:
        return (
            f"<TechnicalDDReport {self.id} repo={self.repo_url!r} status={self.status!r}>"
        )
