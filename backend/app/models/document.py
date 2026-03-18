"""Document model — uploaded files attached to a due diligence engagement."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    # File metadata
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)   # pdf | xlsx | pptx | docx
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)      # pages (PDF) or sheets (Excel)

    # Extracted content
    extracted_text = Column(Text, nullable=True)

    # Processing state: processing | ready | error
    status = Column(String(20), default="processing", nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document {self.id} file={self.filename!r} status={self.status}>"
