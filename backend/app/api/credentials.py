"""
Credentials API — store and retrieve encrypted enterprise system credentials.

Endpoints:
  POST   /credentials/{engagement_id}/{system_name}   Store credentials for a system
  GET    /credentials/{engagement_id}                 List systems with stored credentials
  DELETE /credentials/{engagement_id}/{system_name}   Remove credentials for a system
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.vault import CredentialVault
from app.dependencies import get_session
from app.models.credential import Credential

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Schemas ────────────────────────────────────────────────────────────────────


class CredentialUpsert(BaseModel):
    """Request body for storing credentials."""

    credential_type: str = Field(
        ...,
        description="Type of credential: api_key | oauth | username_password | sso | token",
        examples=["oauth"],
    )
    credential_data: dict[str, Any] = Field(
        ...,
        description="The credential key/value pairs to encrypt and store.",
        examples=[{"access_token": "...", "refresh_token": "...", "instance_url": "..."}],
    )


class CredentialSummary(BaseModel):
    """Summary of a stored credential (no sensitive data)."""

    system_name: str
    credential_type: str
    last_validated_at: str | None = None
    created_at: str


class CredentialListResponse(BaseModel):
    systems: list[CredentialSummary]
    total: int


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post(
    "/{engagement_id}/{system_name}",
    status_code=status.HTTP_201_CREATED,
    summary="Store credentials for a system",
)
async def store_credentials(
    engagement_id: UUID,
    system_name: str,
    body: CredentialUpsert,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Encrypt and store credentials for an enterprise system associated with an engagement.

    Credentials are encrypted with AES-256-GCM before storage.
    If credentials already exist for this system, they are replaced.
    """
    vault = CredentialVault(db)

    # Delete existing credentials first (upsert pattern)
    await vault.delete_credentials(engagement_id, system_name)

    credential = await vault.store_credentials(
        engagement_id=engagement_id,
        system_name=system_name,
        credential_type=body.credential_type,
        credential_data=body.credential_data,
    )
    await db.commit()

    logger.info("Stored credentials for %s (engagement %s)", system_name, engagement_id)
    return {
        "id": str(credential.id),
        "system_name": credential.system_name,
        "credential_type": credential.credential_type.value,
        "created_at": credential.created_at.isoformat(),
    }


@router.get(
    "/{engagement_id}",
    response_model=CredentialListResponse,
    summary="List systems with stored credentials",
)
async def list_credentials(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> CredentialListResponse:
    """
    Return which enterprise systems have credentials stored for this engagement.
    Never returns the decrypted credential data.
    """
    result = await db.execute(
        select(Credential).where(Credential.engagement_id == engagement_id)
    )
    credentials = result.scalars().all()

    summaries = [
        CredentialSummary(
            system_name=c.system_name,
            credential_type=c.credential_type.value,
            last_validated_at=c.last_validated_at.isoformat() if c.last_validated_at else None,
            created_at=c.created_at.isoformat(),
        )
        for c in credentials
    ]

    return CredentialListResponse(systems=summaries, total=len(summaries))


@router.delete(
    "/{engagement_id}/{system_name}",
    status_code=status.HTTP_200_OK,
    summary="Remove credentials for a system",
)
async def delete_credentials(
    engagement_id: UUID,
    system_name: str,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Permanently remove stored credentials for a system from this engagement.
    """
    vault = CredentialVault(db)
    deleted = await vault.delete_credentials(engagement_id, system_name)
    await db.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for system '{system_name}' in engagement {engagement_id}",
        )

    return {"deleted": True, "system_name": system_name}
