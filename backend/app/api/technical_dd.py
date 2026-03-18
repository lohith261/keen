"""
Technical Due Diligence API — GitHub repository analysis.

Routes
------
POST   /engagements/{id}/technical-dd            Trigger analysis for a repo
GET    /engagements/{id}/technical-dd            List all reports
GET    /engagements/{id}/technical-dd/{report_id} Get one report
DELETE /engagements/{id}/technical-dd/{report_id} Delete a report
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_db as get_session
from app.integrations.github.client import GitHubAnalyzer
from app.models.engagement import Engagement
from app.models.technical_dd import TechnicalDDReport

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class TechnicalDDRequest(BaseModel):
    repo_url: str
    github_token: str | None = None


class TechnicalDDResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    repo_url: str | None
    language_stats: dict
    contributor_count: int | None
    bus_factor: int | None
    commit_velocity: float | None
    open_issues_count: int | None
    security_vulnerabilities: list
    dependency_risks: list
    health_score: float | None
    status: str
    error_message: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, r: TechnicalDDReport) -> "TechnicalDDResponse":
        return cls(
            id=r.id,
            engagement_id=r.engagement_id,
            repo_url=r.repo_url,
            language_stats=r.language_stats or {},
            contributor_count=r.contributor_count,
            bus_factor=r.bus_factor,
            commit_velocity=r.commit_velocity,
            open_issues_count=r.open_issues_count,
            security_vulnerabilities=r.security_vulnerabilities or [],
            dependency_risks=r.dependency_risks or [],
            health_score=r.health_score,
            status=r.status,
            error_message=r.error_message,
            created_at=r.created_at.isoformat(),
        )


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


@router.post("/{engagement_id}/technical-dd", response_model=TechnicalDDResponse)
async def create_technical_dd_report(
    engagement_id: UUID,
    body: TechnicalDDRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TechnicalDDResponse:
    """
    Trigger GitHub repository analysis for an engagement.
    Creates a report record (status=pending), runs analysis, and updates it.
    """
    await _get_engagement(engagement_id, current_user, db)

    report = TechnicalDDReport(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        user_id=current_user.sub,
        repo_url=body.repo_url,
        language_stats={},
        security_vulnerabilities=[],
        dependency_risks=[],
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Run analysis synchronously (await directly — GitHub API calls are fast enough)
    # For very slow repos callers can wrap in a background task at the app level.
    try:
        analyzer = GitHubAnalyzer(token=body.github_token)
        result = await analyzer.analyze_repo(body.repo_url)

        report.language_stats = result.get("language_stats", {})
        report.contributor_count = result.get("contributor_count")
        report.bus_factor = result.get("bus_factor")
        report.commit_velocity = result.get("commit_velocity")
        report.open_issues_count = result.get("open_issues_count")
        report.security_vulnerabilities = result.get("security_vulnerabilities", [])
        report.dependency_risks = result.get("dependency_risks", [])
        report.health_score = result.get("health_score")
        report.status = "ready"

        logger.info(
            "Technical DD complete: engagement=%s repo=%s health=%.1f",
            engagement_id,
            body.repo_url,
            report.health_score or 0,
        )
    except Exception as exc:
        report.status = "error"
        report.error_message = str(exc)
        logger.warning(
            "Technical DD failed: engagement=%s repo=%s error=%s",
            engagement_id,
            body.repo_url,
            exc,
        )

    await db.commit()
    await db.refresh(report)
    return TechnicalDDResponse.from_orm(report)


@router.get("/{engagement_id}/technical-dd", response_model=list[TechnicalDDResponse])
async def list_technical_dd_reports(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[TechnicalDDResponse]:
    """List all technical DD reports for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    result = await db.execute(
        select(TechnicalDDReport)
        .where(TechnicalDDReport.engagement_id == engagement_id)
        .order_by(TechnicalDDReport.created_at.desc())
    )
    reports = result.scalars().all()
    return [TechnicalDDResponse.from_orm(r) for r in reports]


@router.get(
    "/{engagement_id}/technical-dd/{report_id}",
    response_model=TechnicalDDResponse,
)
async def get_technical_dd_report(
    engagement_id: UUID,
    report_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TechnicalDDResponse:
    """Get a single technical DD report."""
    await _get_engagement(engagement_id, current_user, db)

    report = await db.get(TechnicalDDReport, report_id)
    if not report or report.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Technical DD report not found")
    return TechnicalDDResponse.from_orm(report)


@router.delete("/{engagement_id}/technical-dd/{report_id}", status_code=204)
async def delete_technical_dd_report(
    engagement_id: UUID,
    report_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete a technical DD report."""
    await _get_engagement(engagement_id, current_user, db)

    report = await db.get(TechnicalDDReport, report_id)
    if not report or report.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Technical DD report not found")

    await db.delete(report)
    await db.commit()
