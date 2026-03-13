"""Abstract base agent with checkpointing, progress reporting, and lifecycle management."""

from __future__ import annotations

import abc
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.checkpoint import Checkpoint
from app.models.finding import Finding, FindingType, Severity

logger = logging.getLogger(__name__)
settings = get_settings()


class StepResult:
    """Result of a single execution step."""

    def __init__(
        self,
        success: bool = True,
        data: dict | None = None,
        findings: list[dict] | None = None,
        message: str = "",
    ):
        self.success = success
        self.data = data or {}
        self.findings = findings or []
        self.message = message


class BaseAgent(abc.ABC):
    """
    Abstract base for all KEEN agents.

    Provides:
    - Step-based execution with automatic checkpointing every N seconds
    - State persistence and resume-from-checkpoint
    - Progress reporting via callback
    - Structured finding creation
    """

    agent_type: str = "base"

    def __init__(
        self,
        agent_run_id: UUID,
        engagement_id: UUID,
        db: AsyncSession,
        redis: Any | None = None,
        on_progress: Any | None = None,  # async callback(event_type, data)
    ):
        self.agent_run_id = agent_run_id
        self.engagement_id = engagement_id
        self.db = db
        self.redis = redis
        self.on_progress = on_progress

        # Execution state
        self.current_step: int = 0
        self.total_steps: int = 0
        self.state: dict[str, Any] = {}
        self._checkpoint_task: asyncio.Task | None = None
        self._should_stop = asyncio.Event()

    # ── Abstract interface ───────────────────────────────

    @abc.abstractmethod
    def define_steps(self, config: dict) -> list[str]:
        """
        Return an ordered list of step names for this agent.
        Called once at the start of execution.
        """
        ...

    @abc.abstractmethod
    async def execute_step(self, step_index: int, step_name: str) -> StepResult:
        """
        Execute a single step. Must be idempotent for checkpoint safety.

        Args:
            step_index: 0-based index into the steps list
            step_name: Name returned from define_steps()

        Returns:
            StepResult with outcome data and optional findings.
        """
        ...

    # ── Public API ───────────────────────────────────────

    async def run(self, config: dict) -> dict:
        """
        Main execution loop.

        1. Defines steps from config
        2. Checks for existing checkpoint and resumes if found
        3. Iterates through steps with periodic checkpointing
        4. Returns final result dict
        """
        steps = self.define_steps(config)
        self.total_steps = len(steps)

        # Check for checkpoint to resume from
        resume_step = await self._try_resume()
        if resume_step is not None:
            self.current_step = resume_step
            logger.info(
                f"[{self.agent_type}] Resuming from step {resume_step}/{self.total_steps}"
            )
        else:
            self.current_step = 0

        # Update agent run status
        await self._update_run_status(AgentRunStatus.RUNNING)

        # Start periodic checkpoint timer
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())

        results: dict[str, Any] = {}

        try:
            for i in range(self.current_step, self.total_steps):
                if self._should_stop.is_set():
                    logger.info(f"[{self.agent_type}] Stopping at step {i}")
                    await self._save_checkpoint(i)
                    await self._update_run_status(AgentRunStatus.PAUSED)
                    return {"status": "paused", "step": i, "results": results}

                step_name = steps[i]
                self.current_step = i

                # Report progress
                await self._report_progress(i, step_name, "executing")

                # Execute the step
                try:
                    result = await self.execute_step(i, step_name)
                except Exception as exc:
                    logger.exception(f"[{self.agent_type}] Step {i} ({step_name}) failed")
                    await self._save_checkpoint(i)
                    await self._update_run_status(
                        AgentRunStatus.FAILED,
                        error=f"Step {step_name}: {exc}",
                    )
                    return {"status": "failed", "step": i, "error": str(exc)}

                if not result.success:
                    await self._save_checkpoint(i)
                    await self._update_run_status(
                        AgentRunStatus.FAILED,
                        error=result.message,
                    )
                    return {"status": "failed", "step": i, "error": result.message}

                # Store step data
                results[step_name] = result.data
                self.state[f"step_{i}_result"] = result.data

                # Persist any findings
                for finding_data in result.findings:
                    await self._create_finding(finding_data)

                # Report step completion
                await self._report_progress(i, step_name, "completed")

            # All steps complete
            await self._update_run_status(AgentRunStatus.COMPLETED)
            return {"status": "completed", "results": results}

        finally:
            if self._checkpoint_task and not self._checkpoint_task.done():
                self._checkpoint_task.cancel()
                try:
                    await self._checkpoint_task
                except asyncio.CancelledError:
                    pass

    async def stop(self) -> None:
        """Signal the agent to stop after the current step."""
        self._should_stop.set()

    # ── Checkpoint machinery ─────────────────────────────

    async def _checkpoint_loop(self) -> None:
        """Periodic checkpoint every CHECKPOINT_INTERVAL_SECONDS."""
        interval = settings.checkpoint_interval_seconds
        while True:
            await asyncio.sleep(interval)
            try:
                await self._save_checkpoint(self.current_step)
                logger.debug(
                    f"[{self.agent_type}] Checkpoint at step {self.current_step}"
                )
            except Exception:
                logger.exception(f"[{self.agent_type}] Checkpoint failed")

    async def _save_checkpoint(self, step_index: int) -> None:
        """Persist current state to DB (and Redis if available)."""
        checkpoint_data = {
            "step_index": step_index,
            "state": self.state,
            "agent_type": self.agent_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Save to Redis for fast access
        if self.redis:
            key = f"checkpoint:{self.agent_run_id}"
            import json
            await self.redis.set(key, json.dumps(checkpoint_data), ex=86400)  # 24h TTL

        # Save to PostgreSQL for durability
        checkpoint = Checkpoint(
            agent_run_id=self.agent_run_id,
            step_index=step_index,
            state_data=checkpoint_data,
        )
        self.db.add(checkpoint)
        await self.db.flush()

        # Emit checkpoint event
        if self.on_progress:
            await self.on_progress("checkpoint", {
                "agent_run_id": str(self.agent_run_id),
                "step_index": step_index,
            })

    async def _try_resume(self) -> int | None:
        """Try to find a valid checkpoint to resume from. Returns step index or None."""
        # Try Redis first
        if self.redis:
            import json
            key = f"checkpoint:{self.agent_run_id}"
            data = await self.redis.get(key)
            if data:
                checkpoint_data = json.loads(data)
                self.state = checkpoint_data.get("state", {})
                return checkpoint_data["step_index"] + 1  # Resume from NEXT step

        # Fall back to DB
        result = await self.db.execute(
            select(Checkpoint)
            .where(Checkpoint.agent_run_id == self.agent_run_id)
            .order_by(Checkpoint.step_index.desc())
            .limit(1)
        )
        checkpoint = result.scalar_one_or_none()
        if checkpoint:
            self.state = checkpoint.state_data.get("state", {})
            return checkpoint.step_index + 1

        return None

    # ── Status reporting ─────────────────────────────────

    async def _update_run_status(
        self,
        status: AgentRunStatus,
        error: str | None = None,
    ) -> None:
        """Update the agent_run record in the DB."""
        agent_run = await self.db.get(AgentRun, self.agent_run_id)
        if agent_run:
            agent_run.status = status
            agent_run.current_step = self.current_step
            agent_run.total_steps = self.total_steps
            agent_run.progress_pct = (
                (self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0
            )
            if error:
                agent_run.error_message = error
            if status == AgentRunStatus.RUNNING and not agent_run.started_at:
                agent_run.started_at = datetime.now(timezone.utc)
            if status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED):
                agent_run.completed_at = datetime.now(timezone.utc)
                if status == AgentRunStatus.COMPLETED:
                    agent_run.progress_pct = 100.0
            await self.db.flush()

        # Emit status event
        if self.on_progress:
            await self.on_progress("agent_status", {
                "agent_run_id": str(self.agent_run_id),
                "agent_type": self.agent_type,
                "status": status.value,
                "progress_pct": agent_run.progress_pct if agent_run else 0,
                "error": error,
            })

    async def _report_progress(self, step: int, step_name: str, stage: str) -> None:
        """Emit a progress event."""
        if self.on_progress:
            await self.on_progress("progress", {
                "agent_run_id": str(self.agent_run_id),
                "agent_type": self.agent_type,
                "step": step,
                "total_steps": self.total_steps,
                "step_name": step_name,
                "stage": stage,
                "progress_pct": (step / self.total_steps * 100) if self.total_steps > 0 else 0,
            })

    # ── Findings ─────────────────────────────────────────

    async def _create_finding(self, data: dict) -> Finding:
        """Persist a finding to the database."""
        finding = Finding(
            agent_run_id=self.agent_run_id,
            finding_type=FindingType(data.get("type", "data_point")),
            source_system=data.get("source_system"),
            title=data.get("title", "Untitled Finding"),
            description=data.get("description"),
            data=data.get("data", {}),
            severity=Severity(data.get("severity", "info")),
            requires_human_review=data.get("requires_human_review", False),
        )
        self.db.add(finding)
        await self.db.flush()

        # Emit finding event
        if self.on_progress:
            await self.on_progress("finding", {
                "agent_run_id": str(self.agent_run_id),
                "finding_id": str(finding.id),
                "title": finding.title,
                "severity": finding.severity.value,
                "source_system": finding.source_system,
            })

        return finding
