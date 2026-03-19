"""
Documents API — upload, list, and delete documents attached to an engagement.

Uploaded files are processed immediately (text extracted synchronously).
For very large files (>20 MB) consider moving extraction to a background task.

Routes
------
POST   /engagements/{id}/documents          Upload a file
GET    /engagements/{id}/documents          List documents for engagement
DELETE /engagements/{id}/documents/{doc_id} Delete a document
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_db as get_session
from app.models.document import Document
from app.models.engagement import Engagement
from app.services.document_processor import detect_file_type, extract_text

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ── Magic byte signatures ─────────────────────────────────────────────────────
# Maps expected file_type strings → list of accepted magic byte prefixes.
# Files whose bytes don't match are rejected even if the extension looks right.
_MAGIC_BYTES: dict[str, list[bytes]] = {
    "pdf":  [b"%PDF"],
    "xlsx": [b"PK\x03\x04"],          # ZIP-based (Office Open XML)
    "xls":  [b"\xd0\xcf\x11\xe0"],    # OLE2 compound file
    "pptx": [b"PK\x03\x04"],
    "docx": [b"PK\x03\x04"],
    "csv":  [],                         # plain text — no magic bytes
    "txt":  [],
}


def _verify_magic_bytes(data: bytes, file_type: str) -> bool:
    """Return True if file bytes match the expected magic bytes for file_type."""
    signatures = _MAGIC_BYTES.get(file_type, [])
    if not signatures:
        return True   # txt/csv: accept any bytes
    return any(data.startswith(sig) for sig in signatures)


# ── Schemas ──────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    filename: str
    file_type: str
    file_size_bytes: int | None
    page_count: int | None
    status: str
    error_message: str | None
    has_text: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, doc: Document) -> "DocumentResponse":
        return cls(
            id=doc.id,
            engagement_id=doc.engagement_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            page_count=doc.page_count,
            status=doc.status,
            error_message=doc.error_message,
            has_text=bool(doc.extracted_text),
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{engagement_id}/documents", response_model=DocumentResponse)
async def upload_document(
    engagement_id: UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a file and extract its text content."""
    # Verify engagement exists and belongs to this user
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Access denied")

    filename = file.filename or "unnamed"
    content_type = file.content_type or ""
    file_type = detect_file_type(filename, content_type)
    if not file_type:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Accepted: PDF, Excel, PowerPoint, Word, CSV, TXT",
        )

    # Read file bytes
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Verify magic bytes — reject files that lie about their type
    if not _verify_magic_bytes(data, file_type):
        raise HTTPException(
            status_code=415,
            detail=(
                f"File content does not match the declared type '{file_type}'. "
                "Please upload a valid file."
            ),
        )

    # Create DB record in "processing" state
    doc = Document(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        user_id=current_user.sub,
        filename=filename,
        file_type=file_type,
        file_size_bytes=len(data),
        status="processing",
    )
    db.add(doc)
    await db.flush()

    # Extract text in a thread pool so large files don't block the event loop
    loop = asyncio.get_event_loop()
    try:
        extracted_text, page_count = await loop.run_in_executor(
            None, extract_text, data, file_type
        )
        doc.extracted_text = extracted_text
        doc.page_count = page_count
        doc.status = "ready"
        logger.info(
            "Document processed: engagement=%s file=%s pages=%s chars=%s",
            engagement_id, filename, page_count, len(extracted_text),
        )
    except RuntimeError as exc:
        doc.status = "error"
        doc.error_message = str(exc)
        logger.warning("Document extraction failed: %s — %s", filename, exc)

    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.from_orm(doc)


@router.get("/{engagement_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[DocumentResponse]:
    """List all documents for an engagement."""
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Document)
        .where(Document.engagement_id == engagement_id)
        .order_by(Document.created_at)
    )
    docs = result.scalars().all()
    return [DocumentResponse.from_orm(d) for d in docs]


@router.delete("/{engagement_id}/documents/{document_id}", status_code=204)
async def delete_document(
    engagement_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete a document and its extracted text."""
    doc = await db.get(Document, document_id)
    if not doc or doc.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id and doc.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(doc)
    await db.commit()
