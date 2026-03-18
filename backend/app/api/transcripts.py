"""
Expert Call Transcripts API.

Routes
──────
POST   /engagements/{id}/transcripts          Upload a transcript (text/PDF) or fetch from Tegus/Third Bridge
GET    /engagements/{id}/transcripts          List transcripts for engagement
GET    /engagements/{id}/transcripts/{tid}   Get transcript + extracted insights
DELETE /engagements/{id}/transcripts/{tid}   Delete transcript
POST   /engagements/{id}/transcripts/fetch   Fetch from Tegus or Third Bridge by company name
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_session
from app.models.engagement import Engagement
from app.models.transcript import ExpertTranscript

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Schemas ────────────────────────────────────────────────────────────────────

class TranscriptResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    source: str
    external_id: str | None
    title: str
    expert_name: str | None
    expert_role: str | None
    call_date: date | None
    company_name: str | None
    sentiment: str | None
    key_themes: list[str] | None
    extracted_insights: str | None
    file_size_bytes: int | None
    status: str
    error_message: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, t: ExpertTranscript) -> "TranscriptResponse":
        return cls(
            id=t.id,
            engagement_id=t.engagement_id,
            source=t.source,
            external_id=t.external_id,
            title=t.title,
            expert_name=t.expert_name,
            expert_role=t.expert_role,
            call_date=t.call_date,
            company_name=t.company_name,
            sentiment=t.sentiment,
            key_themes=t.key_themes,
            extracted_insights=t.extracted_insights,
            file_size_bytes=t.file_size_bytes,
            status=t.status,
            error_message=t.error_message,
            created_at=t.created_at.isoformat(),
        )


class FetchRequest(BaseModel):
    source: str          # tegus | third_bridge
    company_name: str
    max_transcripts: int = 10


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_engagement(engagement_id: UUID, user: AuthUser, db: AsyncSession) -> Engagement:
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng.user_id and eng.user_id != user.sub:
        raise HTTPException(status_code=403, detail="Access denied")
    return eng


def _simple_sentiment(text: str) -> str:
    """Lightweight keyword-based sentiment — used when LLM not available."""
    text_lower = text.lower()
    positives = ["strong", "excellent", "growth", "leader", "innovative", "best in class", "impressed"]
    negatives = ["concern", "weak", "declining", "problem", "issue", "risk", "churn", "struggled"]
    pos_hits = sum(1 for w in positives if w in text_lower)
    neg_hits = sum(1 for w in negatives if w in text_lower)
    if pos_hits > neg_hits + 1:
        return "positive"
    if neg_hits > pos_hits + 1:
        return "negative"
    return "neutral"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/{engagement_id}/transcripts", response_model=TranscriptResponse)
async def upload_transcript(
    engagement_id: UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TranscriptResponse:
    """Upload a transcript file (TXT or PDF). Text is extracted and basic sentiment run."""
    await _get_engagement(engagement_id, current_user, db)

    filename = file.filename or "transcript.txt"
    data = await file.read()

    if len(data) > MAX_TRANSCRIPT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_TRANSCRIPT_BYTES // (1024*1024)} MB",
        )

    # Extract text
    text = ""
    if filename.lower().endswith(".pdf"):
        try:
            import pdfplumber
            import io
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                text = "\n\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except Exception as exc:
            logger.warning("Transcript PDF extraction failed: %s", exc)
            text = data.decode("utf-8", errors="replace")
    else:
        text = data.decode("utf-8", errors="replace")

    sentiment = _simple_sentiment(text) if text else None

    transcript = ExpertTranscript(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        user_id=current_user.sub,
        source="manual_upload",
        title=filename,
        transcript_text=text,
        sentiment=sentiment,
        file_size_bytes=len(data),
        status="ready" if text else "error",
        error_message=None if text else "Could not extract text from file",
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)
    return TranscriptResponse.from_orm(transcript)


@router.post("/{engagement_id}/transcripts/fetch", response_model=list[TranscriptResponse])
async def fetch_from_provider(
    engagement_id: UUID,
    body: FetchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[TranscriptResponse]:
    """
    Fetch transcripts from Tegus or Third Bridge for a company.
    Requires the respective API key stored in the KEEN credential vault.
    """
    engagement = await _get_engagement(engagement_id, current_user, db)

    # Import provider client
    if body.source == "tegus":
        from app.integrations.tegus.client import TegusClient  # type: ignore
        from app.auth.manager import CredentialManager  # type: ignore
        try:
            creds = await CredentialManager.get(engagement_id, "tegus", db)
            client = TegusClient(api_key=creds["api_key"])
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Tegus credentials not configured: {exc}",
            ) from exc
        raw_transcripts = await client.fetch_for_company(
            body.company_name, max_transcripts=body.max_transcripts
        )
    elif body.source == "third_bridge":
        from app.integrations.third_bridge.client import ThirdBridgeClient  # type: ignore
        from app.auth.manager import CredentialManager  # type: ignore
        try:
            creds = await CredentialManager.get(engagement_id, "third_bridge", db)
            client = ThirdBridgeClient(
                client_id=creds["client_id"],
                client_secret=creds["client_secret"],
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Third Bridge credentials not configured: {exc}",
            ) from exc
        raw_transcripts = await client.fetch_for_company(
            body.company_name, max_interviews=body.max_transcripts
        )
    else:
        raise HTTPException(status_code=400, detail="source must be 'tegus' or 'third_bridge'")

    created = []
    for raw in raw_transcripts:
        text = raw.get("text", "")
        # Skip if external_id already exists (dedup)
        ext_id = raw.get("external_id")
        if ext_id:
            existing = await db.execute(
                select(ExpertTranscript).where(
                    ExpertTranscript.engagement_id == engagement_id,
                    ExpertTranscript.external_id == ext_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

        transcript = ExpertTranscript(
            id=uuid.uuid4(),
            engagement_id=engagement_id,
            user_id=current_user.sub,
            source=body.source,
            external_id=ext_id,
            title=raw.get("title", "Expert Call Transcript"),
            expert_name=raw.get("expert_name"),
            expert_role=raw.get("expert_role"),
            call_date=raw.get("call_date"),
            company_name=raw.get("company_name", body.company_name),
            transcript_text=text,
            sentiment=_simple_sentiment(text) if text else None,
            file_size_bytes=len(text.encode()) if text else None,
            status="ready" if text else "processing",
        )
        db.add(transcript)
        created.append(transcript)

    if created:
        await db.commit()
        for t in created:
            await db.refresh(t)

    return [TranscriptResponse.from_orm(t) for t in created]


@router.get("/{engagement_id}/transcripts", response_model=list[TranscriptResponse])
async def list_transcripts(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[TranscriptResponse]:
    """List all expert transcripts for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    result = await db.execute(
        select(ExpertTranscript)
        .where(ExpertTranscript.engagement_id == engagement_id)
        .order_by(ExpertTranscript.created_at.desc())
    )
    return [TranscriptResponse.from_orm(t) for t in result.scalars().all()]


@router.delete("/{engagement_id}/transcripts/{transcript_id}", status_code=204)
async def delete_transcript(
    engagement_id: UUID,
    transcript_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete an expert transcript."""
    t = await db.get(ExpertTranscript, transcript_id)
    if not t or t.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if t.user_id and t.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(t)
    await db.commit()
