"""
Control mode client for a single tmux session.

Manages a persistent connection to tmux via `tmux -C attach -t session`
and streams real-time output notifications.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Awaitable

from .parser import ControlModeParser, ControlModeMessage, MessageType

logger = logging.getLogger(__name__)


# Callback types
OutputCallback = Callable[[str, str], Awaitable[None]]  # (pane_id, data)
WindowCallback = Callable[[str, str], Awaitable[None]]  # (event_type, window_id)
SessionCallback = Callable[[str], Awaitable[None]]  # (event_type)
DisconnectCallback = Callable[[str], Awaitable[None]]  # (session_name)


@dataclass
class CommandResponse:
    """Response from a control mode command."""
    success: bool
    output: str
    error: Optional[str] = None
    command_number: int = 0


class ControlModeError(Exception):
    """Error in control mode operation."""
    pass


class ControlModeClient:
    """
    Async client for a single tmux session's control mode.

    Handles:
    - Spawning `tmux -C attach -t {session}`
    - Reading stdout stream for notifications
    - Writing commands to stdin
    - Parsing %begin/%end responses
    - Emitting callbacks for %output, window changes, etc.
    """

    def __init__(
        self,
        session_name: str,
        socket_path: Optional[str] = None,
        on_output: Optional[OutputCallback] = None,
        on_window_change: Optional[WindowCallback] = None,
        on_session_change: Optional[SessionCallback] = None,
        on_disconnect: Optional[DisconnectCallback] = None,
    ):
        self.session_name = session_name
        self.socket_path = socket_path
        self._on_output = on_output
        self._on_window_change = on_window_change
        self._on_session_change = on_session_change
        self._on_disconnect = on_disconnect

        self._process: Optional[asyncio.subprocess.Process] = None
        self._parser = ControlModeParser()
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None

        # Command response handling
        self._command_number = 0
        self._pending_commands: dict[int, asyncio.Future[CommandResponse]] = {}
        self._response_buffer: dict[int, list[str]] = {}

    async def start(self) -> None:
        """Start the control mode process and reader task."""
        if self._running:
            return

        # Build command
        cmd = ['tmux']
        if self.socket_path:
            cmd.extend(['-S', self.socket_path])
        cmd.extend(['-C', 'attach-session', '-t', self.session_name])

        logger.info(f"Starting control mode for session: {self.session_name}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            raise ControlModeError(f"Failed to start tmux control mode: {e}")

        self._running = True
        self._reader_task = asyncio.create_task(self._read_loop())
        logger.info(f"Control mode started for session: {self.session_name}")

    async def stop(self) -> None:
        """Gracefully terminate the control mode connection."""
        if not self._running:
            return

        logger.info(f"Stopping control mode for session: {self.session_name}")
        self._running = False

        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        # Terminate process
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self._process.kill()
            except Exception:
                pass
            self._process = None

        # Cancel pending commands
        for future in self._pending_commands.values():
            if not future.done():
                future.cancel()
        self._pending_commands.clear()
        self._response_buffer.clear()

    async def send_command(self, command: str) -> CommandResponse:
        """
        Send a command and wait for %begin/%end response.

        Args:
            command: tmux command to execute

        Returns:
            CommandResponse with success status and output
        """
        if not self._running or not self._process or not self._process.stdin:
            raise ControlModeError("Control mode not running")

        self._command_number += 1
        cmd_num = self._command_number

        # Create future for response
        future: asyncio.Future[CommandResponse] = asyncio.Future()
        self._pending_commands[cmd_num] = future
        self._response_buffer[cmd_num] = []

        # Send command
        try:
            self._process.stdin.write(f"{command}\n".encode())
            await self._process.stdin.drain()
        except Exception as e:
            self._pending_commands.pop(cmd_num, None)
            self._response_buffer.pop(cmd_num, None)
            raise ControlModeError(f"Failed to send command: {e}")

        # Wait for response with timeout
        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            self._pending_commands.pop(cmd_num, None)
            self._response_buffer.pop(cmd_num, None)
            raise ControlModeError(f"Command timed out: {command}")

    async def capture_pane(self, pane_id: str, lines: int = 500) -> list[str]:
        """
        Capture pane content via control mode command.

        Args:
            pane_id: Pane ID (e.g., '%3')
            lines: Number of lines to capture from scrollback

        Returns:
            List of output lines
        """
        response = await self.send_command(
            f"capture-pane -p -e -t {pane_id} -S -{lines}"
        )
        if not response.success:
            raise ControlModeError(f"capture-pane failed: {response.error}")
        return response.output.splitlines()

    @property
    def is_running(self) -> bool:
        """Check if the client is running."""
        return self._running

    async def _read_loop(self) -> None:
        """
        Continuously read from stdout, parse notifications.

        Handles:
        - %output %pane_id : data
        - %window-add @window_id
        - %window-close @window_id
        - %session-changed $session_id name
        - %sessions-changed
        - %begin/%end command responses
        """
        if not self._process or not self._process.stdout:
            return

        current_cmd_num: Optional[int] = None

        try:
            while self._running:
                line_bytes = await self._process.stdout.readline()
                if not line_bytes:
                    # EOF - process terminated
                    logger.warning(f"Control mode EOF for session: {self.session_name}")
                    break

                line = line_bytes.decode('utf-8', errors='replace')
                msg = self._parser.parse_line(line)

                await self._handle_message(msg, current_cmd_num)

                # Track current command for response buffering
                if msg.type == MessageType.BEGIN:
                    current_cmd_num = msg.command_number
                elif msg.type in (MessageType.END, MessageType.ERROR):
                    current_cmd_num = None

        except asyncio.CancelledError:
            logger.debug(f"Reader cancelled for session: {self.session_name}")
        except Exception as e:
            logger.error(f"Reader error for session {self.session_name}: {e}")
        finally:
            self._running = False
            if self._on_disconnect:
                try:
                    await self._on_disconnect(self.session_name)
                except Exception as e:
                    logger.error(f"Disconnect callback error: {e}")

    async def _handle_message(
        self,
        msg: ControlModeMessage,
        current_cmd_num: Optional[int],
    ) -> None:
        """Handle a parsed control mode message."""

        if msg.type == MessageType.OUTPUT:
            # Real-time pane output
            if self._on_output and msg.pane_id and msg.data is not None:
                try:
                    await self._on_output(msg.pane_id, msg.data)
                except Exception as e:
                    logger.error(f"Output callback error: {e}")

        elif msg.type == MessageType.BEGIN:
            # Command response starting
            cmd_num = msg.command_number
            if cmd_num is not None and cmd_num not in self._response_buffer:
                self._response_buffer[cmd_num] = []

        elif msg.type == MessageType.END:
            # Command response complete
            cmd_num = msg.command_number
            if cmd_num is not None and cmd_num in self._pending_commands:
                output = '\n'.join(self._response_buffer.get(cmd_num, []))
                response = CommandResponse(
                    success=(msg.exit_code == 0),
                    output=output,
                    command_number=cmd_num,
                )
                future = self._pending_commands.pop(cmd_num)
                self._response_buffer.pop(cmd_num, None)
                if not future.done():
                    future.set_result(response)

        elif msg.type == MessageType.ERROR:
            # Command error
            cmd_num = msg.command_number
            if cmd_num is not None and cmd_num in self._pending_commands:
                response = CommandResponse(
                    success=False,
                    output='',
                    error=msg.error_message,
                    command_number=cmd_num,
                )
                future = self._pending_commands.pop(cmd_num)
                self._response_buffer.pop(cmd_num, None)
                if not future.done():
                    future.set_result(response)

        elif msg.type in (MessageType.WINDOW_ADD, MessageType.WINDOW_CLOSE):
            # Window events
            if self._on_window_change and msg.window_id:
                event_type = 'add' if msg.type == MessageType.WINDOW_ADD else 'close'
                try:
                    await self._on_window_change(event_type, msg.window_id)
                except Exception as e:
                    logger.error(f"Window callback error: {e}")

        elif msg.type == MessageType.SESSIONS_CHANGED:
            # Session list changed
            if self._on_session_change:
                try:
                    await self._on_session_change('sessions_changed')
                except Exception as e:
                    logger.error(f"Session callback error: {e}")

        elif msg.type == MessageType.UNKNOWN:
            # Buffer unknown lines as potential command output
            if current_cmd_num is not None:
                if current_cmd_num in self._response_buffer:
                    self._response_buffer[current_cmd_num].append(msg.raw)
