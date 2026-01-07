"""WebSocket event models"""
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from .input import InputRequest
from .pane import PaneInfo, PaneStatus


class PaneUpdateEvent(BaseModel):
    """Event emitted when pane output or status changes"""
    event: Literal["pane_update"] = "pane_update"
    pane_id: str
    status: PaneStatus
    lines: list[str] = Field(default_factory=list)
    input_request: Optional[InputRequest] = None
    cursor_x: int = 0
    cursor_y: int = 0


class PaneDiscoveryEvent(BaseModel):
    """Event emitted when a new pane is discovered"""
    event: Literal["pane_discovered"] = "pane_discovered"
    pane: PaneInfo


class PaneRemovedEvent(BaseModel):
    """Event emitted when a pane is removed/closed"""
    event: Literal["pane_removed"] = "pane_removed"
    pane_id: str


# Union type for all WebSocket events
WebSocketEvent = Union[PaneUpdateEvent, PaneDiscoveryEvent, PaneRemovedEvent]
