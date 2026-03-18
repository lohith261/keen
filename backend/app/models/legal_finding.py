"""LegalFinding model — contract clause findings from document analysis."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class LegalFinding(Base):
    __tablename__ = "legal_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    # Clause classification
    # change_of_control | ip_ownership | non_compete | litigation | regulatory | other
    clause_type = Column(String(50), nullable=False, index=True)

    text_excerpt = Column(Text, nullable=False)

    # risk_level: info | warning | critical
    risk_level = Column(String(20), nullable=False, default="info")

    requires_review = Column(Boolean, nullable=False, default=True)
    reviewed = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="legal_findings")

    def __repr__(self) -> str:
        return (
            f"<LegalFinding {self.id} clause={self.clause_type!r} risk={self.risk_level!r}>"
        )
