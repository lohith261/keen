"""
Portfolio monitoring service.

Runs a lightweight re-pull of configured live sources for a monitored
engagement and computes deltas vs the acquisition-time baseline snapshot.

Architecture
────────────
Each MonitoringSchedule stores:
  - baseline_snapshot: JSON dict of {metric: value} captured at acquisition close
  - sources: list of source systems to re-pull (e.g. ["salesforce", "netsuite"])

On each run:
  1. Re-run the Research Agent in metrics-only mode for the configured sources
  2. Extract the same KPIs as the baseline
  3. Compute delta per metric: {metric, baseline, current, delta_pct, severity}
  4. Persist result as MonitoringRun with deltas JSON

This module provides run_monitoring_schedule() which is called:
  - Manually via POST /monitoring/{schedule_id}/run (immediate)
  - On schedule via a task queue worker (future: Celery / RQ / APScheduler)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import MonitoringRun, MonitoringSchedule

logger = logging.getLogger(__name__)


def _compute_deltas(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Compare current metrics against baseline and produce delta findings.

    Metrics are numeric key-value pairs. Returns list of:
    {metric, baseline, current, delta_abs, delta_pct, severity}
    """
    deltas = []
    for metric, base_val in baseline.items():
        curr_val = current.get(metric)
        if curr_val is None or not isinstance(base_val, (int, float)):
            continue

        delta_abs = curr_val - base_val
        delta_pct = (delta_abs / base_val * 100) if base_val != 0 else 0.0

        # Severity thresholds: >10% change = warning, >25% = critical
        abs_pct = abs(delta_pct)
        severity = "info"
        if abs_pct >= 25:
            severity = "critical"
        elif abs_pct >= 10:
            severity = "warning"

        deltas.append({
            "metric": metric,
            "baseline": base_val,
            "current": curr_val,
            "delta_abs": round(delta_abs, 4),
            "delta_pct": round(delta_pct, 2),
            "severity": severity,
        })

    return sorted(deltas, key=lambda d: abs(d["delta_pct"]), reverse=True)


async def run_monitoring_schedule(
    schedule: MonitoringSchedule,
    current_metrics: dict[str, Any],
    db: AsyncSession,
) -> MonitoringRun:
    """
    Execute one monitoring run for a schedule.

    current_metrics: dict of {metric_key: current_value} freshly pulled from live sources.
    The caller (API layer) is responsible for fetching live data and passing it here.
    """
    run = MonitoringRun(
        id=uuid.uuid4(),
        schedule_id=schedule.id,
        engagement_id=schedule.engagement_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()

    try:
        baseline = schedule.baseline_snapshot or {}
        deltas = _compute_deltas(baseline, current_metrics)

        run.deltas = deltas
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)

        # Update schedule's last_run_at
        schedule.last_run_at = run.completed_at

        logger.info(
            "Monitoring run %s complete: %d deltas for schedule %s",
            run.id, len(deltas), schedule.id,
        )
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        logger.exception("Monitoring run %s failed: %s", run.id, exc)

    await db.commit()
    await db.refresh(run)
    return run
