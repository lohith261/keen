"""WebSocket endpoint for real-time agent status streaming."""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._broadcast_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, engagement_id: str | None = None) -> None:
        await websocket.accept()
        if engagement_id:
            self._connections.setdefault(engagement_id, []).append(websocket)
        else:
            self._broadcast_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, engagement_id: str | None = None) -> None:
        if engagement_id and engagement_id in self._connections:
            self._connections[engagement_id] = [
                ws for ws in self._connections[engagement_id] if ws != websocket
            ]
            if not self._connections[engagement_id]:
                del self._connections[engagement_id]
        elif websocket in self._broadcast_connections:
            self._broadcast_connections.remove(websocket)

    async def send_to_engagement(self, engagement_id: str, message: dict) -> None:
        """Send message to all clients watching a specific engagement."""
        connections = self._connections.get(engagement_id, [])
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, engagement_id)

    async def broadcast(self, message: dict) -> None:
        """Send message to all broadcast subscribers."""
        dead: list[WebSocket] = []
        for ws in self._broadcast_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/agent-status")
async def agent_status_ws(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time agent status.

    Query params:
        engagement_id — subscribe to a specific engagement (optional)

    Sends events:
        - heartbeat (every 30s)
        - agent_status — agent state changes
        - progress — step progress updates
        - finding — new finding discovered
        - orchestrator — workflow-level events
    """
    engagement_id = websocket.query_params.get("engagement_id")
    await manager.connect(websocket, engagement_id)

    try:
        while True:
            # Send a heartbeat every 30 seconds and listen for client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Client can send ping or subscribe/unsubscribe messages
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({
                            "event": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "event": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"status": "connected"},
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket, engagement_id)


async def emit_agent_event(
    engagement_id: str,
    event: str,
    data: dict,
) -> None:
    """
    Helper to emit an event to all clients watching an engagement.

    Called from agent workers / orchestrator.
    """
    message = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    await manager.send_to_engagement(engagement_id, message)
    await manager.broadcast(message)
