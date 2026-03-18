"""
Legal Findings API — contract clause analysis for due diligence.

Routes
------
GET    /engagements/{id}/legal-findings                           List findings
POST   /engagements/{id}/legal-findings/analyze/{document_id}    Analyze one document
POST   /engagements/{id}/legal-findings/analyze-all              Analyze all ready documents
PATCH  /engagements/{id}/legal-findings/{finding_id}             Update review state
DELETE /engagements/{id}/legal-findings/{finding_id}             Delete a finding
GET    /engagements/{id}/legal-findings/risk-summary             Risk summary
"""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_db as get_session
from app.models.document import Document
from app.models.engagement import Engagement
from app.models.legal_finding import LegalFinding
from app.services.contract_analyzer_service import analyze_contract, score_contract_risk

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class LegalFindingResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    document_id: UUID | None
    clause_type: str
    text_excerpt: str
    risk_level: str
    requires_review: bool
    reviewed: bool
    notes: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, f: LegalFinding) -> "LegalFindingResponse":
        return cls(
            id=f.id,
            engagement_id=f.engagement_id,
            document_id=f.document_id,
            clause_type=f.clause_type,
            text_excerpt=f.text_excerpt,
            risk_level=f.risk_level,
            requires_review=f.requires_review,
            reviewed=f.reviewed,
            notes=f.notes,
            created_at=f.created_at.isoformat(),
        )


class LegalFindingUpdate(BaseModel):
    reviewed: bool | None = None
    notes: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_engagement(
    engagement_id: UUID, user: AuthUser, db: AsyncSession
) -> Engagement:
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng.user_id and eng.user_id != user.sub:
        raise HTTPException(status_code=403, detail="Access denied")
    return eng


async def _analyze_document(
    document: Document,
    engagement_id: UUID,
    user_sub: str,
    db: AsyncSession,
) -> list[LegalFinding]:
    """Run contract analysis on a document and persist findings. Returns new LegalFinding rows."""
    text = document.extracted_text or ""
    raw_findings = analyze_contract(
        text, str(document.id), str(engagement_id)
    )

    created: list[LegalFinding] = []
    for raw in raw_findings:
        finding = LegalFinding(
            id=uuid.uuid4(),
            engagement_id=engagement_id,
            document_id=document.id,
            user_id=user_sub,
            clause_type=raw["clause_type"],
            text_excerpt=raw["text_excerpt"],
            risk_level=raw["risk_level"],
            requires_review=raw["requires_review"],
            reviewed=False,
            notes=None,
        )
        db.add(finding)
        created.append(finding)

    return created


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/{engagement_id}/legal-findings", response_model=list[LegalFindingResponse])
async def list_legal_findings(
    engagement_id: UUID,
    clause_type: str | None = Query(default=None, description="Filter by clause type"),
    requires_review: bool | None = Query(default=None, description="Filter by requires_review"),
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[LegalFindingResponse]:
    """List all legal findings for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    stmt = (
        select(LegalFinding)
        .where(LegalFinding.engagement_id == engagement_id)
        .order_by(LegalFinding.created_at.desc())
    )
    if clause_type:
        stmt = stmt.where(LegalFinding.clause_type == clause_type)
    if requires_review is not None:
        stmt = stmt.where(LegalFinding.requires_review == requires_review)

    result = await db.execute(stmt)
    findings = result.scalars().all()
    return [LegalFindingResponse.from_orm(f) for f in findings]


@router.post("/{engagement_id}/legal-findings/analyze/{document_id}")
async def analyze_document(
    engagement_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Analyze a single document for contract clauses and store findings."""
    await _get_engagement(engagement_id, current_user, db)

    doc = await db.get(Document, document_id)
    if not doc or doc.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.extracted_text:
        raise HTTPException(
            status_code=422,
            detail="Document has no extracted text. Ensure it has status 'ready'.",
        )

    new_findings = await _analyze_document(doc, engagement_id, current_user.sub, db)
    await db.commit()
    for f in new_findings:
        await db.refresh(f)

    raw_dicts = [
        {"risk_level": f.risk_level, "clause_type": f.clause_type} for f in new_findings
    ]
    risk_summary = score_contract_risk(raw_dicts)

    logger.info(
        "Legal analysis: engagement=%s document=%s findings=%d",
        engagement_id,
        document_id,
        len(new_findings),
    )
    return {
        "count": len(new_findings),
        "risk_summary": risk_summary,
        "findings": [LegalFindingResponse.from_orm(f) for f in new_findings],
    }


@router.post("/{engagement_id}/legal-findings/analyze-all")
async def analyze_all_documents(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Analyze all ready documents for an engagement and store legal findings."""
    await _get_engagement(engagement_id, current_user, db)

    result = await db.execute(
        select(Document).where(
            Document.engagement_id == engagement_id,
            Document.status == "ready",
        )
    )
    documents = result.scalars().all()

    all_findings: list[LegalFinding] = []
    for doc in documents:
        new_findings = await _analyze_document(doc, engagement_id, current_user.sub, db)
        all_findings.extend(new_findings)

    if all_findings:
        await db.commit()
        for f in all_findings:
            await db.refresh(f)

    raw_dicts = [
        {"risk_level": f.risk_level, "clause_type": f.clause_type} for f in all_findings
    ]
    risk_summary = score_contract_risk(raw_dicts)

    logger.info(
        "Legal analysis all: engagement=%s docs=%d findings=%d",
        engagement_id,
        len(documents),
        len(all_findings),
    )
    return {
        "documents_analyzed": len(documents),
        "total_findings": len(all_findings),
        "risk_summary": risk_summary,
    }


@router.patch(
    "/{engagement_id}/legal-findings/{finding_id}",
    response_model=LegalFindingResponse,
)
async def update_legal_finding(
    engagement_id: UUID,
    finding_id: UUID,
    body: LegalFindingUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> LegalFindingResponse:
    """Update the reviewed status and/or notes on a legal finding."""
    await _get_engagement(engagement_id, current_user, db)

    finding = await db.get(LegalFinding, finding_id)
    if not finding or finding.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Legal finding not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(finding, field, value)

    await db.commit()
    await db.refresh(finding)
    return LegalFindingResponse.from_orm(finding)


@router.delete("/{engagement_id}/legal-findings/{finding_id}", status_code=204)
async def delete_legal_finding(
    engagement_id: UUID,
    finding_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete a legal finding."""
    await _get_engagement(engagement_id, current_user, db)

    finding = await db.get(LegalFinding, finding_id)
    if not finding or finding.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Legal finding not found")

    await db.delete(finding)
    await db.commit()


@router.get("/{engagement_id}/legal-findings/risk-summary")
async def get_risk_summary(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Return overall risk summary across all legal findings for the engagement."""
    await _get_engagement(engagement_id, current_user, db)

    result = await db.execute(
        select(LegalFinding).where(LegalFinding.engagement_id == engagement_id)
    )
    findings = result.scalars().all()

    findings_dicts = [
        {"risk_level": f.risk_level, "clause_type": f.clause_type} for f in findings
    ]
    return score_contract_risk(findings_dicts)
