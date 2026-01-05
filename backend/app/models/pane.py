"""Pane-related Pydantic models"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .input import InputRequest


class PaneStatus(str, Enum):
    """Status of a tmux pane"""
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    IDLE = "idle"
    EXITED = "exited"


class PaneInfo(BaseModel):
    """Basic pane information returned by API"""
    pane_id: str = Field(..., description="Unique pane identifier (e.g., '%3')")
    session_name: str = Field(..., description="tmux session name")
    window_name: str = Field(..., description="tmux window name")
    window_index: int = Field(..., description="Window index within session")
    pane_index: int = Field(..., description="Pane index within window")
    title: str = Field(default="", description="Pane title")
    status: PaneStatus = Field(default=PaneStatus.RUNNING, description="Current pane status")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    model_config = {"from_attributes": True}


class PaneState(BaseModel):
    """Internal state tracking for a pane"""
    pane_id: str
    session_name: str
    window_name: str
    window_index: int = 0
    pane_index: int = 0
    title: str = ""
    status: PaneStatus = PaneStatus.RUNNING
    last_output_hash: str = ""
    last_lines: list[str] = Field(default_factory=list)
    input_request: Optional[InputRequest] = None
    last_activity: datetime = Field(default_factory=datetime.now)

    def to_info(self) -> PaneInfo:
        """Convert internal state to API response model"""
        return PaneInfo(
            pane_id=self.pane_id,
            session_name=self.session_name,
            window_name=self.window_name,
            window_index=self.window_index,
            pane_index=self.pane_index,
            title=self.title,
            status=self.status,
            last_updated=self.last_activity,
        )


class PaneOutput(BaseModel):
    """Pane output response"""
    pane_id: str
    lines: list[str] = Field(default_factory=list)
    line_count: int = 0
    input_request: Optional[InputRequest] = None
