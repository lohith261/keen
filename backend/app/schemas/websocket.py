"""Pydantic schemas for WebSocket messages."""

from datetime import datetime

from pydantic import BaseModel


class WSMessage(BaseModel):
    """Base WebSocket message."""

    event: str
    timestamp: datetime
    data: dict = {}


class AgentStatusEvent(WSMessage):
    """Agent status change event."""

    event: str = "agent_status"


class ProgressEvent(WSMessage):
    """Progress update event."""

    event: str = "progress"


class FindingEvent(WSMessage):
    """New finding notification."""

    event: str = "finding"


class OrchestratorEvent(WSMessage):
    """Orchestrator-level event (hand-off, completion, failure)."""

    event: str = "orchestrator"
