"""Expert call transcript model — Tegus, Third Bridge, and manual uploads."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ExpertTranscript(Base):
    """An expert call transcript attached to a due diligence engagement."""

    __tablename__ = "expert_transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    # Source: tegus | third_bridge | manual_upload
    source = Column(String(50), nullable=False, default="manual_upload")
    external_id = Column(String(255), nullable=True, index=True)

    # Transcript metadata
    title = Column(String(500), nullable=False)
    expert_name = Column(String(255), nullable=True)
    expert_role = Column(String(255), nullable=True)
    call_date = Column(Date, nullable=True)
    company_name = Column(String(255), nullable=True)

    # Raw transcript text (from upload or API fetch)
    transcript_text = Column(Text, nullable=True)

    # LLM-extracted analysis
    sentiment = Column(String(20), nullable=True)  # positive | neutral | negative
    key_themes = Column(JSONB, nullable=True)  # list[str]
    extracted_insights = Column(Text, nullable=True)

    # File info (for uploads)
    file_size_bytes = Column(Integer, nullable=True)

    # Status: processing | ready | error
    status = Column(String(20), nullable=False, default="processing", index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="transcripts")

    def __repr__(self) -> str:
        return f"<ExpertTranscript {self.id} title={self.title!r} source={self.source}>"
