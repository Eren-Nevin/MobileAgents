"""
Parser for tmux control mode protocol messages.

Message types:
- %output %pane_id : escaped_data     - Pane output
- %begin timestamp cmd_num flags      - Command response start
- %end timestamp cmd_num exit_code    - Command response end (success)
- %error timestamp cmd_num message    - Command response end (error)
- %window-add @window_id              - New window
- %window-close @window_id            - Window closed
- %window-renamed @window_id name     - Window renamed
- %session-changed $session_id name   - Session switched
- %sessions-changed                   - Session list changed
- %pane-mode-changed %pane_id         - Pane mode changed
- %layout-change @window_id layout    - Layout changed
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .escaping import unescape_output


class MessageType(Enum):
    """Types of control mode messages."""
    OUTPUT = auto()
    BEGIN = auto()
    END = auto()
    ERROR = auto()
    WINDOW_ADD = auto()
    WINDOW_CLOSE = auto()
    WINDOW_RENAMED = auto()
    SESSION_CHANGED = auto()
    SESSIONS_CHANGED = auto()
    PANE_MODE_CHANGED = auto()
    LAYOUT_CHANGE = auto()
    UNKNOWN = auto()


@dataclass
class ControlModeMessage:
    """Parsed control mode message."""
    type: MessageType
    raw: str

    # For OUTPUT messages
    pane_id: Optional[str] = None
    data: Optional[str] = None

    # For BEGIN/END/ERROR messages
    timestamp: Optional[int] = None
    command_number: Optional[int] = None
    flags: Optional[int] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None

    # For window/session messages
    window_id: Optional[str] = None
    session_id: Optional[str] = None
    name: Optional[str] = None
    layout: Optional[str] = None


class ControlModeParser:
    """
    Parser for tmux control mode output stream.

    Usage:
        parser = ControlModeParser()
        for line in stdout:
            msg = parser.parse_line(line)
            if msg.type == MessageType.OUTPUT:
                handle_output(msg.pane_id, msg.data)
    """

    # Regex patterns for different message types
    _OUTPUT_PATTERN = re.compile(r'^%output (%\d+) (.*)$')
    _BEGIN_PATTERN = re.compile(r'^%begin (\d+) (\d+) (\d+)$')
    _END_PATTERN = re.compile(r'^%end (\d+) (\d+) (\d+)$')
    _ERROR_PATTERN = re.compile(r'^%error (\d+) (\d+) (.*)$')
    _WINDOW_ADD_PATTERN = re.compile(r'^%window-add (@\d+)$')
    _WINDOW_CLOSE_PATTERN = re.compile(r'^%window-close (@\d+)$')
    _WINDOW_RENAMED_PATTERN = re.compile(r'^%window-renamed (@\d+) (.*)$')
    _SESSION_CHANGED_PATTERN = re.compile(r'^%session-changed (\$\d+) (.*)$')
    _SESSIONS_CHANGED_PATTERN = re.compile(r'^%sessions-changed$')
    _PANE_MODE_CHANGED_PATTERN = re.compile(r'^%pane-mode-changed (%\d+)$')
    _LAYOUT_CHANGE_PATTERN = re.compile(r'^%layout-change (@\d+) (.*)$')

    def parse_line(self, line: str) -> ControlModeMessage:
        """
        Parse a single line from control mode output.

        Args:
            line: Raw line from tmux control mode stdout

        Returns:
            Parsed ControlModeMessage
        """
        line = line.rstrip('\n\r')

        # Try each pattern
        if match := self._OUTPUT_PATTERN.match(line):
            pane_id = match.group(1)
            # Output data starts after ": " - need to handle the colon
            raw_data = match.group(2)
            # Remove leading ": " if present
            if raw_data.startswith(': '):
                raw_data = raw_data[2:]
            elif raw_data.startswith(':'):
                raw_data = raw_data[1:]
            return ControlModeMessage(
                type=MessageType.OUTPUT,
                raw=line,
                pane_id=pane_id,
                data=unescape_output(raw_data),
            )

        if match := self._BEGIN_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.BEGIN,
                raw=line,
                timestamp=int(match.group(1)),
                command_number=int(match.group(2)),
                flags=int(match.group(3)),
            )

        if match := self._END_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.END,
                raw=line,
                timestamp=int(match.group(1)),
                command_number=int(match.group(2)),
                exit_code=int(match.group(3)),
            )

        if match := self._ERROR_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.ERROR,
                raw=line,
                timestamp=int(match.group(1)),
                command_number=int(match.group(2)),
                error_message=match.group(3),
            )

        if match := self._WINDOW_ADD_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.WINDOW_ADD,
                raw=line,
                window_id=match.group(1),
            )

        if match := self._WINDOW_CLOSE_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.WINDOW_CLOSE,
                raw=line,
                window_id=match.group(1),
            )

        if match := self._WINDOW_RENAMED_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.WINDOW_RENAMED,
                raw=line,
                window_id=match.group(1),
                name=match.group(2),
            )

        if match := self._SESSION_CHANGED_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.SESSION_CHANGED,
                raw=line,
                session_id=match.group(1),
                name=match.group(2),
            )

        if self._SESSIONS_CHANGED_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.SESSIONS_CHANGED,
                raw=line,
            )

        if match := self._PANE_MODE_CHANGED_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.PANE_MODE_CHANGED,
                raw=line,
                pane_id=match.group(1),
            )

        if match := self._LAYOUT_CHANGE_PATTERN.match(line):
            return ControlModeMessage(
                type=MessageType.LAYOUT_CHANGE,
                raw=line,
                window_id=match.group(1),
                layout=match.group(2),
            )

        # Unknown message type
        return ControlModeMessage(
            type=MessageType.UNKNOWN,
            raw=line,
        )

    @staticmethod
    def is_notification(line: str) -> bool:
        """Check if a line is a notification (starts with %)."""
        return line.startswith('%')
