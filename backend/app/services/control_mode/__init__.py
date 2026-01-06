"""
tmux Control Mode integration for real-time output streaming.

This module provides push-based updates from tmux instead of polling,
significantly reducing latency and resource usage.
"""

from .client import ControlModeClient, ControlModeError
from .session_manager import SessionManager
from .parser import ControlModeParser, MessageType
from .escaping import unescape_output, escape_input

__all__ = [
    "ControlModeClient",
    "ControlModeError",
    "SessionManager",
    "ControlModeParser",
    "MessageType",
    "unescape_output",
    "escape_input",
]
