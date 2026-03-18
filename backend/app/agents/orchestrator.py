"""Agent Orchestrator — coordinates Research → Analysis → Delivery agents."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.engagement import Engagement, EngagementStatus
from app.models.agent_run import AgentRun, AgentRunStatus, AgentType
from app.models.document import Document
from app.agents.research import ResearchAgent
from app.agents.analysis import AnalysisAgent
from app.agents.delivery import DeliveryAgent

logger = logging.getLogger(__name__)

# Map agent types to their implementation classes
AGENT_CLASSES = {
    AgentType.RESEARCH: ResearchAgent,
    AgentType.ANALYSIS: AnalysisAgent,
    AgentType.DELIVERY: DeliveryAgent,
}

# Default execution order: Research feeds Analysis which feeds Delivery
EXECUTION_ORDER = [AgentType.RESEARCH, AgentType.ANALYSIS, AgentType.DELIVERY]


class AgentOrchestrator:
    """
    Coordinates multi-agent execution for a due diligence engagement.

    Execution flow:
        1. Research Agent authenticates + extracts data from enterprise systems
        2. Analysis Agent cross-references and detects discrepancies
        3. Delivery Agent generates board-ready output

    Each agent runs sequentially (output of one feeds the next).
    Within each agent, steps execute with 90-second checkpointing.
    """

    def __init__(
        self,
        engagement_id: UUID,
        db: AsyncSession,
        redis: Any | None = None,
        on_event: Any | None = None,  # async callback(event_type, data)
    ):
        self.engagement_id = engagement_id
        self.db = db
        self.redis = redis
        self.on_event = on_event
        self._should_stop = asyncio.Event()

    async def run(self) -> dict:
        """
        Execute the full orchestration pipeline.

        Returns a dict with overall status and per-agent results.
        """
        # Load engagement with agent runs
        result = await self.db.execute(
            select(Engagement)
            .options(selectinload(Engagement.agent_runs))
            .where(Engagement.id == self.engagement_id)
        )
        engagement = result.scalar_one_or_none()
        if not engagement:
            raise ValueError(f"Engagement {self.engagement_id} not found")

        config = engagement.config or {}

        # Load uploaded documents and inject as context for Research agent
        docs_result = await self.db.execute(
            select(Document)
            .where(Document.engagement_id == self.engagement_id)
            .where(Document.status == "ready")
            .order_by(Document.created_at)
        )
        uploaded_documents = [
            {
                "filename": doc.filename,
                "file_type": doc.file_type,
                "page_count": doc.page_count,
                "extracted_text": doc.extracted_text or "",
            }
            for doc in docs_result.scalars().all()
        ]
        if uploaded_documents:
            logger.info(
                "Injecting %d uploaded document(s) into pipeline for engagement %s",
                len(uploaded_documents), self.engagement_id,
            )

        # Build a map of agent type → agent run
        runs_by_type: dict[AgentType, AgentRun] = {
            run.agent_type: run for run in engagement.agent_runs
        }

        # Filter to only the agents configured for this engagement
        requested_agents = config.get("agents", ["research", "analysis", "delivery"])
        execution_order = [
            at for at in EXECUTION_ORDER if at.value in requested_agents
        ]

        await self._emit_event("orchestrator", {
            "engagement_id": str(self.engagement_id),
            "status": "started",
            "agents": [a.value for a in execution_order],
        })

        pipeline_data: dict[str, Any] = {}
        overall_status = "completed"

        for agent_type in execution_order:
            if self._should_stop.is_set():
                overall_status = "paused"
                break

            agent_run = runs_by_type.get(agent_type)
            if not agent_run:
                logger.warning(f"No agent run found for {agent_type}, skipping")
                continue

            # Skip already completed agents (on resume)
            if agent_run.status == AgentRunStatus.COMPLETED:
                logger.info(f"Agent {agent_type.value} already completed, skipping")
                continue

            await self._emit_event("orchestrator", {
                "engagement_id": str(self.engagement_id),
                "status": "agent_starting",
                "agent_type": agent_type.value,
            })

            # Instantiate the agent
            agent_cls = AGENT_CLASSES[agent_type]
            agent = agent_cls(
                agent_run_id=agent_run.id,
                engagement_id=self.engagement_id,
                db=self.db,
                redis=self.redis,
                on_progress=self.on_event,
            )

            # Inject data from previous agents into config, and surface
            # top-level engagement fields (company_name, target_company) so
            # agents can use them in prompts without reading the DB.
            step_config = {
                **config,
                "pipeline_data": pipeline_data,
                "company_name": engagement.company_name,
                "target_company": engagement.target_company or engagement.company_name,
                "uploaded_documents": uploaded_documents,
            }

            # Execute the agent
            try:
                agent_result = await agent.run(step_config)
            except Exception as exc:
                logger.exception(f"Agent {agent_type.value} crashed")
                agent_result = {"status": "failed", "error": str(exc)}

            # Store results for the next agent in the pipeline
            pipeline_data[agent_type.value] = agent_result.get("results", {})

            await self._emit_event("orchestrator", {
                "engagement_id": str(self.engagement_id),
                "status": "agent_completed",
                "agent_type": agent_type.value,
                "agent_status": agent_result.get("status", "unknown"),
            })

            # If an agent failed, stop the pipeline
            if agent_result.get("status") == "failed":
                overall_status = "failed"
                engagement.status = EngagementStatus.FAILED
                await self.db.flush()
                break

        # Update engagement status
        if overall_status == "completed":
            engagement.status = EngagementStatus.COMPLETED
            engagement.completed_at = datetime.now(timezone.utc)
        elif overall_status == "paused":
            engagement.status = EngagementStatus.PAUSED

        await self.db.flush()

        await self._emit_event("orchestrator", {
            "engagement_id": str(self.engagement_id),
            "status": overall_status,
        })

        return {
            "engagement_id": str(self.engagement_id),
            "status": overall_status,
            "pipeline_data": pipeline_data,
        }

    async def stop(self) -> None:
        """Signal the orchestrator to stop after the current agent completes."""
        self._should_stop.set()

    async def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit an orchestrator event."""
        if self.on_event:
            try:
                await self.on_event(event_type, data)
            except Exception:
                logger.exception("Failed to emit orchestrator event")
