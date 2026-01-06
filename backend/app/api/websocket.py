"""WebSocket API for real-time updates"""
import asyncio
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..models.events import WebSocketEvent
from .deps import get_observer, get_registry

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info(f"WebSocket connected, total: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        async with self._lock:
            self._connections.discard(websocket)
        logger.info(f"WebSocket disconnected, total: {len(self._connections)}")

    async def broadcast(self, event: WebSocketEvent) -> None:
        """
        Broadcast an event to all connected clients in parallel.

        Automatically removes dead connections.
        """
        if not self._connections:
            return

        message = event.model_dump_json()
        dead_connections: Set[WebSocket] = set()

        async with self._lock:
            connections = list(self._connections)

        async def send_to_client(ws: WebSocket) -> None:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"Failed to send to websocket: {e}")
                dead_connections.add(ws)

        # Send to all clients in parallel
        await asyncio.gather(*[send_to_client(ws) for ws in connections], return_exceptions=True)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                self._connections -= dead_connections

    @property
    def connection_count(self) -> int:
        """Get number of active connections"""
        return len(self._connections)


# Global connection manager
manager = ConnectionManager()


async def broadcast_event(event: WebSocketEvent) -> None:
    """
    Broadcast an event to all WebSocket clients.

    This function is registered as an observer callback.
    """
    await manager.broadcast(event)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time pane updates.

    Clients receive:
    - pane_update: When pane output or status changes
    - pane_discovered: When a new pane is found
    - pane_removed: When a pane is closed

    Clients can send:
    - ping: Returns pong
    - get_state: Returns current pane list
    """
    await manager.connect(websocket)

    # Send initial state
    try:
        registry = get_registry()
        panes = await registry.get_all()
        initial_state = {
            "event": "initial_state",
            "panes": [pane.to_info().model_dump() for pane in panes],
        }
        await websocket.send_json(initial_state)
    except Exception as e:
        logger.error(f"Failed to send initial state: {e}")

    try:
        while True:
            # Handle incoming messages
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_state":
                try:
                    registry = get_registry()
                    panes = await registry.get_all()
                    state = {
                        "event": "state",
                        "panes": [pane.to_info().model_dump() for pane in panes],
                    }
                    await websocket.send_json(state)
                except Exception as e:
                    logger.error(f"Failed to get state: {e}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)
