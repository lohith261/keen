"""External record model — court, patent, UCC, and bank statement verification records."""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ExternalRecordSource(str, enum.Enum):
    COURTLISTENER = "courtlistener"
    USPTO = "uspto"
    UCC = "ucc"
    BANK_STATEMENT = "bank_statement"


class ExternalRecord(Base):
    __tablename__ = "external_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    source = Column(
        SAEnum(
            ExternalRecordSource,
            name="external_record_source",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )

    record_type = Column(String(100), nullable=False)
    external_id = Column(String(500), nullable=True)
    title = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(2000), nullable=True)

    # info | warning | critical
    risk_level = Column(String(20), nullable=False, default="info", index=True)

    raw_data = Column(JSONB, default=dict, nullable=False)

    # ID of the finding this record corroborates (cross-reference)
    corroborates_finding = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="external_records")

    def __repr__(self) -> str:
        return (
            f"<ExternalRecord {self.id} source={self.source} risk={self.risk_level}"
            f" title={self.title!r}>"
        )
