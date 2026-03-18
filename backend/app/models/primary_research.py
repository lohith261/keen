"""Primary research model — customer interviews, channel checks, win/loss records."""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class PrimaryResearchType(str, enum.Enum):
    CUSTOMER_INTERVIEW = "customer_interview"
    CHANNEL_CHECK = "channel_check"
    WIN_LOSS = "win_loss"
    MARKET_SIZING = "market_sizing"


class PrimaryResearch(Base):
    __tablename__ = "primary_research"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    type = Column(
        SAEnum(
            PrimaryResearchType,
            name="primary_research_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )

    company_name = Column(String(500), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_role = Column(String(255), nullable=True)
    interview_date = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive | neutral | negative
    key_themes = Column(JSONB, default=list, nullable=False)
    action_items = Column(JSONB, default=list, nullable=False)

    status = Column(String(50), nullable=False, default="draft", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="primary_research_records")

    def __repr__(self) -> str:
        return (
            f"<PrimaryResearch {self.id} type={self.type} company={self.company_name!r}"
            f" status={self.status}>"
        )
