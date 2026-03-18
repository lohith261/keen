"""
Portfolio Monitoring API.

Routes
──────
POST   /engagements/{id}/monitoring          Create a monitoring schedule
GET    /engagements/{id}/monitoring          List schedules for engagement
GET    /engagements/{id}/monitoring/{sid}    Get schedule + recent runs
PATCH  /engagements/{id}/monitoring/{sid}   Update schedule (enable/disable, frequency)
DELETE /engagements/{id}/monitoring/{sid}   Delete schedule
POST   /engagements/{id}/monitoring/{sid}/run  Trigger an immediate monitoring run
GET    /engagements/{id}/monitoring/{sid}/runs  List runs for a schedule
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.database import get_db as get_session
from app.models.engagement import Engagement
from app.models.monitoring import MonitoringRun, MonitoringSchedule
from app.services.monitoring_service import run_monitoring_schedule

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    name: str
    frequency: str = "monthly"              # monthly | quarterly | weekly | manual
    cron_expression: str | None = None
    sources: list[str] | None = None        # source system names to monitor
    baseline_snapshot: dict[str, Any] | None = None


class ScheduleUpdate(BaseModel):
    name: str | None = None
    frequency: str | None = None
    cron_expression: str | None = None
    sources: list[str] | None = None
    enabled: bool | None = None
    baseline_snapshot: dict[str, Any] | None = None


class RunCreate(BaseModel):
    current_metrics: dict[str, Any]        # freshly pulled KPIs for delta computation


class RunResponse(BaseModel):
    id: UUID
    schedule_id: UUID
    engagement_id: UUID
    status: str
    deltas: list[dict[str, Any]] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    name: str
    frequency: str
    cron_expression: str | None
    enabled: bool
    sources: list[str] | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    recent_runs: list[RunResponse] = []

    model_config = {"from_attributes": True}


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_engagement(engagement_id: UUID, user: AuthUser, db: AsyncSession) -> Engagement:
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng.user_id and eng.user_id != user.sub:
        raise HTTPException(status_code=403, detail="Access denied")
    return eng


async def _get_schedule(
    engagement_id: UUID, schedule_id: UUID, db: AsyncSession
) -> MonitoringSchedule:
    sched = await db.get(MonitoringSchedule, schedule_id)
    if not sched or sched.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Monitoring schedule not found")
    return sched


def _schedule_response(sched: MonitoringSchedule, runs: list[MonitoringRun]) -> ScheduleResponse:
    return ScheduleResponse(
        id=sched.id,
        engagement_id=sched.engagement_id,
        name=sched.name,
        frequency=sched.frequency,
        cron_expression=sched.cron_expression,
        enabled=sched.enabled,
        sources=sched.sources,
        last_run_at=sched.last_run_at,
        next_run_at=sched.next_run_at,
        created_at=sched.created_at,
        recent_runs=[
            RunResponse(
                id=r.id,
                schedule_id=r.schedule_id,
                engagement_id=r.engagement_id,
                status=r.status,
                deltas=r.deltas,
                error_message=r.error_message,
                started_at=r.started_at,
                completed_at=r.completed_at,
                created_at=r.created_at,
            )
            for r in runs
        ],
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/{engagement_id}/monitoring", response_model=ScheduleResponse)
async def create_schedule(
    engagement_id: UUID,
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> ScheduleResponse:
    """Create a new portfolio monitoring schedule for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    sched = MonitoringSchedule(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        user_id=current_user.sub,
        name=body.name,
        frequency=body.frequency,
        cron_expression=body.cron_expression,
        sources=body.sources,
        baseline_snapshot=body.baseline_snapshot,
        enabled=True,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return _schedule_response(sched, [])


@router.get("/{engagement_id}/monitoring", response_model=list[ScheduleResponse])
async def list_schedules(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[ScheduleResponse]:
    """List all monitoring schedules for an engagement."""
    await _get_engagement(engagement_id, current_user, db)

    result = await db.execute(
        select(MonitoringSchedule)
        .where(MonitoringSchedule.engagement_id == engagement_id)
        .order_by(MonitoringSchedule.created_at)
    )
    schedules = result.scalars().all()

    responses = []
    for sched in schedules:
        runs_result = await db.execute(
            select(MonitoringRun)
            .where(MonitoringRun.schedule_id == sched.id)
            .order_by(MonitoringRun.created_at.desc())
            .limit(5)
        )
        runs = list(runs_result.scalars().all())
        responses.append(_schedule_response(sched, runs))
    return responses


@router.get("/{engagement_id}/monitoring/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    engagement_id: UUID,
    schedule_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> ScheduleResponse:
    """Get a monitoring schedule with its recent runs."""
    await _get_engagement(engagement_id, current_user, db)
    sched = await _get_schedule(engagement_id, schedule_id, db)

    runs_result = await db.execute(
        select(MonitoringRun)
        .where(MonitoringRun.schedule_id == sched.id)
        .order_by(MonitoringRun.created_at.desc())
        .limit(10)
    )
    runs = list(runs_result.scalars().all())
    return _schedule_response(sched, runs)


@router.patch("/{engagement_id}/monitoring/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    engagement_id: UUID,
    schedule_id: UUID,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> ScheduleResponse:
    """Update a monitoring schedule (enable/disable, frequency, sources, baseline)."""
    await _get_engagement(engagement_id, current_user, db)
    sched = await _get_schedule(engagement_id, schedule_id, db)

    if body.name is not None:
        sched.name = body.name
    if body.frequency is not None:
        sched.frequency = body.frequency
    if body.cron_expression is not None:
        sched.cron_expression = body.cron_expression
    if body.sources is not None:
        sched.sources = body.sources
    if body.enabled is not None:
        sched.enabled = body.enabled
    if body.baseline_snapshot is not None:
        sched.baseline_snapshot = body.baseline_snapshot

    await db.commit()
    await db.refresh(sched)
    return _schedule_response(sched, [])


@router.delete("/{engagement_id}/monitoring/{schedule_id}", status_code=204)
async def delete_schedule(
    engagement_id: UUID,
    schedule_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete a monitoring schedule and all its runs."""
    await _get_engagement(engagement_id, current_user, db)
    sched = await _get_schedule(engagement_id, schedule_id, db)
    await db.delete(sched)
    await db.commit()


@router.post("/{engagement_id}/monitoring/{schedule_id}/run", response_model=RunResponse)
async def trigger_run(
    engagement_id: UUID,
    schedule_id: UUID,
    body: RunCreate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> RunResponse:
    """Trigger an immediate monitoring run with the provided current metrics."""
    await _get_engagement(engagement_id, current_user, db)
    sched = await _get_schedule(engagement_id, schedule_id, db)

    run = await run_monitoring_schedule(sched, body.current_metrics, db)
    return RunResponse(
        id=run.id,
        schedule_id=run.schedule_id,
        engagement_id=run.engagement_id,
        status=run.status,
        deltas=run.deltas,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


@router.get("/{engagement_id}/monitoring/{schedule_id}/runs", response_model=list[RunResponse])
async def list_runs(
    engagement_id: UUID,
    schedule_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> list[RunResponse]:
    """List all monitoring runs for a schedule."""
    await _get_engagement(engagement_id, current_user, db)
    await _get_schedule(engagement_id, schedule_id, db)

    result = await db.execute(
        select(MonitoringRun)
        .where(MonitoringRun.schedule_id == schedule_id)
        .order_by(MonitoringRun.created_at.desc())
        .limit(50)
    )
    runs = result.scalars().all()
    return [
        RunResponse(
            id=r.id,
            schedule_id=r.schedule_id,
            engagement_id=r.engagement_id,
            status=r.status,
            deltas=r.deltas,
            error_message=r.error_message,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
        )
        for r in runs
    ]
