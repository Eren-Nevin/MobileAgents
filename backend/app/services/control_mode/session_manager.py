"""
Session manager for tmux control mode connections.

Manages ControlModeClient instances for multiple tmux sessions,
handling session discovery, client lifecycle, and event aggregation.
"""

import asyncio
import logging
from typing import Callable, Optional, Awaitable

from .client import ControlModeClient, ControlModeError

logger = logging.getLogger(__name__)


# Callback types
PaneOutputCallback = Callable[[str, str, str], Awaitable[None]]  # (session, pane_id, data)
PaneAddedCallback = Callable[[str], Awaitable[None]]  # (pane_id)
PaneRemovedCallback = Callable[[str], Awaitable[None]]  # (pane_id)
SessionsChangedCallback = Callable[[], Awaitable[None]]


class SessionManager:
    """
    Manages ControlModeClient instances for multiple sessions.

    Responsibilities:
    - Create/destroy clients per session
    - Handle session discovery
    - Coordinate reconnection
    - Aggregate events from all sessions
    """

    def __init__(
        self,
        socket_path: Optional[str] = None,
        on_pane_output: Optional[PaneOutputCallback] = None,
        on_sessions_changed: Optional[SessionsChangedCallback] = None,
        reconnect_delay: float = 1.0,
        max_reconnect_attempts: int = 5,
    ):
        self.socket_path = socket_path
        self._on_pane_output = on_pane_output
        self._on_sessions_changed = on_sessions_changed
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        self._clients: dict[str, ControlModeClient] = {}
        self._running = False
        self._lock = asyncio.Lock()
        self._reconnect_tasks: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        """
        Start monitoring all sessions.

        1. Discover existing sessions via `tmux list-sessions`
        2. Create ControlModeClient per session
        3. Start all clients
        """
        if self._running:
            return

        self._running = True
        logger.info("Starting session manager")

        # Discover and connect to all sessions
        await self._discover_and_connect()

    async def stop(self) -> None:
        """Stop all control mode clients."""
        logger.info("Stopping session manager")
        self._running = False

        # Cancel reconnect tasks
        for task in self._reconnect_tasks.values():
            task.cancel()
        self._reconnect_tasks.clear()

        # Stop all clients
        async with self._lock:
            for session_name, client in list(self._clients.items()):
                try:
                    await client.stop()
                except Exception as e:
                    logger.error(f"Error stopping client {session_name}: {e}")
            self._clients.clear()

    async def refresh_sessions(self) -> None:
        """Re-discover sessions and update clients."""
        if not self._running:
            return
        await self._discover_and_connect()

    async def get_sessions(self) -> list[str]:
        """Get list of connected session names."""
        async with self._lock:
            return list(self._clients.keys())

    async def _discover_and_connect(self) -> None:
        """Discover sessions and create/remove clients as needed."""
        # Get current sessions
        sessions = await self._list_sessions()
        logger.info(f"Discovered {len(sessions)} tmux sessions")

        async with self._lock:
            current_sessions = set(self._clients.keys())
            new_sessions = set(sessions) - current_sessions
            removed_sessions = current_sessions - set(sessions)

            # Remove clients for closed sessions
            for session_name in removed_sessions:
                logger.info(f"Session closed: {session_name}")
                client = self._clients.pop(session_name, None)
                if client:
                    await client.stop()

            # Create clients for new sessions
            for session_name in new_sessions:
                logger.info(f"New session: {session_name}")
                await self._create_client(session_name)

    async def _list_sessions(self) -> list[str]:
        """List tmux sessions."""
        cmd = ['tmux']
        if self.socket_path:
            cmd.extend(['-S', self.socket_path])
        cmd.extend(['list-sessions', '-F', '#{session_name}'])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                # No sessions or tmux not running
                error = stderr.decode().strip()
                if 'no server running' in error or 'no sessions' in error:
                    return []
                logger.warning(f"list-sessions error: {error}")
                return []

            return [s.strip() for s in stdout.decode().strip().split('\n') if s.strip()]

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    async def _create_client(self, session_name: str) -> None:
        """Create and start a control mode client for a session."""
        client = ControlModeClient(
            session_name=session_name,
            socket_path=self.socket_path,
            on_output=self._make_output_handler(session_name),
            on_session_change=self._handle_session_change,
            on_disconnect=self._handle_client_disconnect,
        )

        try:
            await client.start()
            self._clients[session_name] = client
        except ControlModeError as e:
            logger.error(f"Failed to start client for {session_name}: {e}")

    def _make_output_handler(self, session_name: str):
        """Create an output handler for a specific session."""
        async def handler(pane_id: str, data: str) -> None:
            if self._on_pane_output:
                try:
                    await self._on_pane_output(session_name, pane_id, data)
                except Exception as e:
                    logger.error(f"Pane output callback error: {e}")
        return handler

    async def _handle_session_change(self, event_type: str) -> None:
        """Handle session change events."""
        if event_type == 'sessions_changed':
            logger.info("Sessions changed, refreshing...")
            # Schedule refresh to avoid blocking
            asyncio.create_task(self.refresh_sessions())
            if self._on_sessions_changed:
                try:
                    await self._on_sessions_changed()
                except Exception as e:
                    logger.error(f"Sessions changed callback error: {e}")

    async def _handle_client_disconnect(self, session_name: str) -> None:
        """Handle client disconnection."""
        logger.warning(f"Client disconnected: {session_name}")

        async with self._lock:
            self._clients.pop(session_name, None)

        if self._running:
            # Schedule reconnection
            if session_name not in self._reconnect_tasks:
                task = asyncio.create_task(
                    self._reconnect_session(session_name)
                )
                self._reconnect_tasks[session_name] = task

    async def _reconnect_session(self, session_name: str) -> None:
        """Attempt to reconnect to a session."""
        for attempt in range(self.max_reconnect_attempts):
            if not self._running:
                break

            delay = self.reconnect_delay * (2 ** attempt)
            logger.info(
                f"Reconnecting to {session_name} in {delay}s "
                f"(attempt {attempt + 1}/{self.max_reconnect_attempts})"
            )
            await asyncio.sleep(delay)

            if not self._running:
                break

            # Check if session still exists
            sessions = await self._list_sessions()
            if session_name not in sessions:
                logger.info(f"Session {session_name} no longer exists")
                break

            # Try to reconnect
            async with self._lock:
                if session_name in self._clients:
                    break  # Already reconnected

                try:
                    await self._create_client(session_name)
                    logger.info(f"Reconnected to {session_name}")
                    break
                except Exception as e:
                    logger.warning(f"Reconnect failed for {session_name}: {e}")

        # Clean up reconnect task
        self._reconnect_tasks.pop(session_name, None)

    async def capture_pane(
        self,
        session_name: str,
        pane_id: str,
        lines: int = 500,
    ) -> list[str]:
        """
        Capture pane content via the session's control mode client.

        Args:
            session_name: Name of the tmux session
            pane_id: Pane ID (e.g., '%3')
            lines: Number of lines to capture

        Returns:
            List of output lines
        """
        async with self._lock:
            client = self._clients.get(session_name)

        if not client:
            raise ControlModeError(f"No client for session: {session_name}")

        return await client.capture_pane(pane_id, lines)
