"""
Credential vault — AES-256 encrypted credential storage.

Securely stores and retrieves enterprise system credentials.
Credentials are encrypted at rest using AES-256-GCM.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.credential import Credential, CredentialType

logger = logging.getLogger(__name__)
settings = get_settings()


class CredentialVault:
    """
    Encrypted credential storage using AES-256-GCM.

    Credentials are encrypted before being stored in PostgreSQL
    and decrypted on retrieval. The encryption key is loaded
    from the CREDENTIAL_ENCRYPTION_KEY environment variable.
    """

    def __init__(self, db: AsyncSession, encryption_key: str | None = None):
        self.db = db
        self._key = self._load_key(encryption_key or settings.credential_encryption_key)

    def _load_key(self, key_str: str) -> bytes:
        """Load or generate an AES-256 key."""
        if not key_str:
            if settings.environment == "production":
                raise RuntimeError(
                    "CREDENTIAL_ENCRYPTION_KEY is not set. "
                    "Credentials cannot be stored or retrieved in production without an encryption key. "
                    "Generate one with: python -c \"import base64,os; print(base64.b64encode(os.urandom(32)).decode())\""
                )
            logger.error(
                "CREDENTIAL_ENCRYPTION_KEY not configured — using ephemeral key. "
                "All credentials will be LOST on restart. Set CREDENTIAL_ENCRYPTION_KEY in production."
            )
            return AESGCM.generate_key(bit_length=256)
        # Key should be base64-encoded 32 bytes
        try:
            key = base64.b64decode(key_str)
            if len(key) != 32:
                raise ValueError(f"Key must be 32 bytes, got {len(key)}")
            return key
        except Exception:
            if settings.environment == "production":
                raise RuntimeError(
                    "CREDENTIAL_ENCRYPTION_KEY is set but has an invalid format. "
                    "It must be a base64-encoded 32-byte key. "
                    "Generate one with: python -c \"import base64,os; print(base64.b64encode(os.urandom(32)).decode())\""
                )
            logger.error(
                "Invalid CREDENTIAL_ENCRYPTION_KEY format — using ephemeral key. "
                "All credentials will be LOST on restart."
            )
            return AESGCM.generate_key(bit_length=256)

    def _encrypt(self, data: dict) -> bytes:
        """Encrypt a dict to bytes using AES-256-GCM."""
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)  # 96-bit nonce
        plaintext = json.dumps(data).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # Prepend nonce to ciphertext for storage
        return nonce + ciphertext

    def _decrypt(self, encrypted: bytes) -> dict:
        """Decrypt bytes back to a dict."""
        aesgcm = AESGCM(self._key)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))

    async def store_credentials(
        self,
        engagement_id: UUID,
        system_name: str,
        credential_type: str,
        credential_data: dict,
    ) -> Credential:
        """Encrypt and store credentials for an enterprise system."""
        encrypted = self._encrypt(credential_data)

        credential = Credential(
            engagement_id=engagement_id,
            system_name=system_name,
            credential_type=CredentialType(credential_type),
            encrypted_data=encrypted,
        )
        self.db.add(credential)
        await self.db.flush()
        await self.db.refresh(credential)

        logger.info(f"Stored credentials for {system_name} (engagement {engagement_id})")
        return credential

    async def get_credentials(
        self,
        engagement_id: UUID,
        system_name: str,
    ) -> dict:
        """Retrieve and decrypt credentials for a system."""
        result = await self.db.execute(
            select(Credential).where(
                Credential.engagement_id == engagement_id,
                Credential.system_name == system_name,
            )
        )
        credential = result.scalar_one_or_none()

        if not credential:
            logger.warning(f"No credentials found for {system_name}")
            return {}

        return self._decrypt(credential.encrypted_data)

    async def delete_credentials(
        self,
        engagement_id: UUID,
        system_name: str,
    ) -> bool:
        """Delete credentials for a system."""
        result = await self.db.execute(
            select(Credential).where(
                Credential.engagement_id == engagement_id,
                Credential.system_name == system_name,
            )
        )
        credential = result.scalar_one_or_none()
        if credential:
            await self.db.delete(credential)
            await self.db.flush()
            return True
        return False
