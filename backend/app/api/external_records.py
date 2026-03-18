"""
External Records API — court, patent, UCC, and bank statement verification records.

Routes
------
GET    /engagements/{id}/external-records                      List records
POST   /engagements/{id}/external-records/fetch/court          Fetch from CourtListener
POST   /engagements/{id}/external-records/fetch/patents        Fetch from USPTO
POST   /engagements/{id}/external-records/upload/bank-statement Upload bank statement
DELETE /engagements/{id}/external-records/{record_id}          Delete a record
GET    /engagements/{id}/external-records/confidence           Compute confidence score
"""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_db as get_session
from app.integrations.verification.bank_statement_parser import BankStatementParser
from app.integrations.verification.courtlistener import CourtListenerClient
from app.integrations.verification.uspto import USPTOClient
from app.models.engagement import Engagement
from app.models.external_record import ExternalRecord, ExternalRecordSource
from app.models.finding import Finding
from app.services.verification_service import compute_confidence_score

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class ExternalRecordResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    source: str
    record_type: str
    external_id: str | None
    title: str
    description: str | None
    url: str | None
    risk_level: str
    raw_data: dict
    corroborates_finding: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, rec: ExternalRecord) -> "ExternalRecordResponse":
        return cls(
            id=rec.id,
            engagement_id=rec.engagement_id,
            source=rec.source.value if hasattr(rec.source, "value") else str(rec.source),
            record_type=rec.record_type,
            external_id=rec.external_id,
            title=rec.title,
            description=rec.description,
            url=rec.url,
            risk_level=rec.risk_level,
            raw_data=rec.raw_data or {},
            corroborates_finding=rec.corroborates_finding,
            created_at=rec.created_at.isoformat(),
        )


class CourtFetchRequest(BaseModel):
    company_name: str
    max_results: int = 20
    api_token: str | None = None


class PatentFetchRequest(BaseModel):
    company_name: str
    max_results: int = 20


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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/{engagement_id}/external-records", response_model=list[ExternalRecordResponse])
async def list_external_records(
    engagement_id: UUID,
    source: str | None = Query(default=None, description="Filter by source"),
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[ExternalRecordResponse]:
    """List external verification records for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    stmt = (
        select(ExternalRecord)
        .where(ExternalRecord.engagement_id == engagement_id)
        .order_by(ExternalRecord.created_at.desc())
    )
    if source:
        stmt = stmt.where(ExternalRecord.source == source)

    result = await db.execute(stmt)
    records = result.scalars().all()
    return [ExternalRecordResponse.from_orm(r) for r in records]


@router.post("/{engagement_id}/external-records/fetch/court")
async def fetch_court_records(
    engagement_id: UUID,
    body: CourtFetchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Fetch court records from CourtListener and store as ExternalRecords."""
    await _get_engagement(engagement_id, current_user, db)

    client = CourtListenerClient(api_token=body.api_token)
    cases = await client.search_cases(body.company_name, max_results=body.max_results)

    created = []
    for case in cases:
        rec = ExternalRecord(
            id=uuid.uuid4(),
            engagement_id=engagement_id,
            user_id=current_user.sub,
            source=ExternalRecordSource.COURTLISTENER,
            record_type="court_case",
            external_id=case.get("external_id"),
            title=case.get("case_name") or "Unknown Case",
            description=case.get("description"),
            url=case.get("url"),
            risk_level="warning",
            raw_data=case,
        )
        db.add(rec)
        created.append(rec)

    if created:
        await db.commit()
        for r in created:
            await db.refresh(r)

    logger.info(
        "Fetched %d court records for engagement=%s company=%s",
        len(created),
        engagement_id,
        body.company_name,
    )
    return {"count": len(created), "records": [ExternalRecordResponse.from_orm(r) for r in created]}


@router.post("/{engagement_id}/external-records/fetch/patents")
async def fetch_patent_records(
    engagement_id: UUID,
    body: PatentFetchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Fetch patent records from USPTO and store as ExternalRecords."""
    await _get_engagement(engagement_id, current_user, db)

    client = USPTOClient()
    patents = await client.search_patents(body.company_name, max_results=body.max_results)

    created = []
    for patent in patents:
        rec = ExternalRecord(
            id=uuid.uuid4(),
            engagement_id=engagement_id,
            user_id=current_user.sub,
            source=ExternalRecordSource.USPTO,
            record_type="patent",
            external_id=patent.get("external_id"),
            title=patent.get("title") or patent.get("patent_number") or "Patent",
            description=None,
            url=None,
            risk_level="info",
            raw_data=patent,
        )
        db.add(rec)
        created.append(rec)

    if created:
        await db.commit()
        for r in created:
            await db.refresh(r)

    logger.info(
        "Fetched %d patent records for engagement=%s company=%s",
        len(created),
        engagement_id,
        body.company_name,
    )
    return {"count": len(created), "records": [ExternalRecordResponse.from_orm(r) for r in created]}


@router.post("/{engagement_id}/external-records/upload/bank-statement")
async def upload_bank_statement(
    engagement_id: UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> ExternalRecordResponse:
    """Upload a bank statement PDF or TXT file, parse it, and store summary."""
    await _get_engagement(engagement_id, current_user, db)

    filename = file.filename or "bank_statement.pdf"
    data = await file.read()

    parser = BankStatementParser()
    parse_result = parser.parse(data, filename)

    # Summarise for the title / description
    tx_count = parse_result.get("transaction_count", 0)
    anomaly_count = len(parse_result.get("anomalies", []))
    risk_level = "warning" if anomaly_count > 0 else "info"

    rec = ExternalRecord(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        user_id=current_user.sub,
        source=ExternalRecordSource.BANK_STATEMENT,
        record_type="bank_statement",
        external_id=None,
        title=f"Bank Statement — {filename}",
        description=(
            f"{tx_count} transactions parsed; {anomaly_count} anomaly(ies) detected."
        ),
        url=None,
        risk_level=risk_level,
        raw_data=parse_result,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    logger.info(
        "Bank statement uploaded for engagement=%s file=%s tx=%d anomalies=%d",
        engagement_id,
        filename,
        tx_count,
        anomaly_count,
    )
    return ExternalRecordResponse.from_orm(rec)


@router.delete("/{engagement_id}/external-records/{record_id}", status_code=204)
async def delete_external_record(
    engagement_id: UUID,
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete an external record."""
    await _get_engagement(engagement_id, current_user, db)

    rec = await db.get(ExternalRecord, record_id)
    if not rec or rec.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="External record not found")

    await db.delete(rec)
    await db.commit()


@router.get("/{engagement_id}/external-records/confidence")
async def get_confidence_score(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """
    Compute confidence scores for all findings in this engagement,
    corroborated by the external records present.
    """
    await _get_engagement(engagement_id, current_user, db)

    # Fetch all external records for the engagement
    ext_result = await db.execute(
        select(ExternalRecord).where(ExternalRecord.engagement_id == engagement_id)
    )
    ext_records = ext_result.scalars().all()

    # Fetch agent_run findings linked to this engagement via agent_runs
    from app.models.agent_run import AgentRun  # local import to avoid circular

    run_result = await db.execute(
        select(AgentRun).where(AgentRun.engagement_id == engagement_id)
    )
    runs = run_result.scalars().all()
    run_ids = [r.id for r in runs]

    findings = []
    if run_ids:
        finding_result = await db.execute(
            select(Finding).where(Finding.agent_run_id.in_(run_ids))
        )
        findings = finding_result.scalars().all()

    findings_dicts = [
        {
            "id": str(f.id),
            "title": f.title,
            "source_system": f.source_system or "",
        }
        for f in findings
    ]
    ext_dicts = [
        {
            "corroborates_finding": r.corroborates_finding,
            "source": r.source.value if hasattr(r.source, "value") else str(r.source),
        }
        for r in ext_records
    ]

    return compute_confidence_score(findings_dicts, ext_dicts)
