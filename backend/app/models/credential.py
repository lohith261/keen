"""Credential model — encrypted enterprise system credentials."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CredentialType(str, enum.Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"
    USERNAME_PASSWORD = "username_password"
    SSO = "sso"
    TOKEN = "token"


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    system_name = Column(String(100), nullable=False, index=True)
    credential_type = Column(
        Enum(CredentialType, name="credential_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    encrypted_data = Column(LargeBinary, nullable=False, doc="AES-256 encrypted credential blob")
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    engagement = relationship("Engagement", back_populates="credentials")

    def __repr__(self) -> str:
        return f"<Credential {self.id} system={self.system_name!r}>"
