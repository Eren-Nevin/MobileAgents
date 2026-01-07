"""Observer daemon for monitoring tmux panes via control mode or polling"""
import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Awaitable, Callable, Optional

from ..models.events import (
    PaneDiscoveryEvent,
    PaneRemovedEvent,
    PaneUpdateEvent,
    WebSocketEvent,
)
from ..models.pane import PaneState, PaneStatus
from .control_mode import SessionManager, ControlModeError
from .parser import InputParser
from .registry import PaneRegistry
from .tmux import TmuxPane, TmuxService

logger = logging.getLogger(__name__)

# Type alias for event callback
EventCallback = Callable[[WebSocketEvent], Awaitable[None]]


class ObserverDaemon:
    """
    Background daemon that monitors tmux panes for changes.

    Supports two modes:
    - Control mode (default): Real-time streaming via tmux -C
    - Polling mode (fallback): Periodic capture-pane polling
    """

    def __init__(
        self,
        tmux_service: TmuxService,
        registry: PaneRegistry,
        parser: InputParser,
        use_control_mode: bool = True,
        poll_interval: float = 1.0,
        discovery_interval: float = 5.0,
        capture_lines: int = 500,
        control_mode_reconnect_delay: float = 1.0,
        control_mode_max_reconnects: int = 5,
    ):
        """
        Initialize the observer daemon.

        Args:
            tmux_service: TmuxService instance for tmux interaction
            registry: PaneRegistry for state storage
            parser: InputParser for detecting input requests
            use_control_mode: Use tmux control mode for real-time updates
            poll_interval: Seconds between output polls (fallback only)
            discovery_interval: Seconds between pane discovery
            capture_lines: Number of lines to capture from each pane
            control_mode_reconnect_delay: Initial reconnect delay for control mode
            control_mode_max_reconnects: Max reconnection attempts for control mode
        """
        self.tmux = tmux_service
        self.registry = registry
        self.parser = parser
        self.use_control_mode = use_control_mode
        self.poll_interval = poll_interval
        self.discovery_interval = discovery_interval
        self.capture_lines = capture_lines
        self.control_mode_reconnect_delay = control_mode_reconnect_delay
        self.control_mode_max_reconnects = control_mode_max_reconnects

        self._running = False
        self._mode: str = "none"  # "control_mode", "polling", or "none"
        self._discovery_task: Optional[asyncio.Task] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._session_manager: Optional[SessionManager] = None
        self._callbacks: list[EventCallback] = []

        # Track pending updates for batching
        self._pending_updates: dict[str, asyncio.Task] = {}
        self._update_debounce_ms: int = 15  # Debounce updates within 15ms

    def on_event(self, callback: EventCallback) -> None:
        """
        Register a callback for state change events.

        Args:
            callback: Async function to call with WebSocketEvent
        """
        self._callbacks.append(callback)
        logger.debug(f"Registered event callback, total: {len(self._callbacks)}")

    def remove_callback(self, callback: EventCallback) -> None:
        """Remove a registered callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _emit_event(self, event: WebSocketEvent) -> None:
        """
        Emit event to all registered callbacks.

        Args:
            event: Event to emit
        """
        for callback in self._callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    async def start(self) -> None:
        """Start the observer with control mode or fallback to polling"""
        if self._running:
            logger.warning("Observer already running")
            return

        self._running = True
        logger.info("Starting observer daemon")

        if self.use_control_mode:
            try:
                await self._start_control_mode()
                self._mode = "control_mode"
                logger.info("Observer running in control mode (real-time)")
            except Exception as e:
                logger.warning(f"Control mode failed ({e}), falling back to polling")
                await self._start_polling()
                self._mode = "polling"
                logger.info("Observer running in polling mode (fallback)")
        else:
            await self._start_polling()
            self._mode = "polling"
            logger.info("Observer running in polling mode")

    async def stop(self) -> None:
        """Gracefully stop the observer"""
        if not self._running:
            return

        logger.info("Stopping observer daemon")
        self._running = False

        # Stop control mode
        if self._session_manager:
            await self._session_manager.stop()
            self._session_manager = None

        # Cancel polling tasks
        for task in [self._discovery_task, self._polling_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._discovery_task = None
        self._polling_task = None
        self._mode = "none"

    # =========================================================================
    # Control Mode Implementation
    # =========================================================================

    async def _start_control_mode(self) -> None:
        """Initialize and start control mode session manager"""
        self._session_manager = SessionManager(
            socket_path=self.tmux.socket_path,
            on_pane_output=self._handle_control_mode_output,
            on_sessions_changed=self._handle_sessions_changed,
            reconnect_delay=self.control_mode_reconnect_delay,
            max_reconnect_attempts=self.control_mode_max_reconnects,
        )

        await self._session_manager.start()

        # Run initial discovery to populate registry
        await self._discover_panes()

        # Capture initial state for all panes
        await self._capture_initial_state()

        # Start discovery loop (control mode handles output streaming)
        self._discovery_task = asyncio.create_task(
            self._discovery_loop(),
            name="observer_discovery"
        )

    async def _capture_initial_state(self) -> None:
        """Capture initial pane content for all discovered panes"""
        panes = await self.registry.get_all()

        for pane in panes:
            try:
                lines = await self.tmux.capture_pane(pane.pane_id, self.capture_lines)
                await self.registry.update_output(
                    pane.pane_id,
                    lines,
                    ""  # No hash needed for control mode
                )
                logger.debug(f"Captured initial state for {pane.pane_id}")
            except Exception as e:
                logger.warning(f"Failed to capture initial state for {pane.pane_id}: {e}")

    async def _handle_control_mode_output(
        self,
        session_name: str,
        pane_id: str,
        data: str,
    ) -> None:
        """
        Handle real-time output from control mode.

        Args:
            session_name: tmux session name
            pane_id: Pane ID (e.g., '%3')
            data: Output data (may contain escape sequences)
        """
        # Append output to registry
        appended = await self.registry.append_output(pane_id, data)

        if appended:
            # Schedule debounced update event
            await self._schedule_update_event(pane_id)

    async def _schedule_update_event(self, pane_id: str) -> None:
        """
        Schedule a debounced update event for a pane.

        This batches rapid output updates into single events.
        """
        # Cancel existing pending update for this pane
        if pane_id in self._pending_updates:
            self._pending_updates[pane_id].cancel()

        # Schedule new update
        async def emit_update():
            await asyncio.sleep(self._update_debounce_ms / 1000)
            await self._emit_pane_update(pane_id)
            self._pending_updates.pop(pane_id, None)

        task = asyncio.create_task(emit_update())
        self._pending_updates[pane_id] = task

    async def _emit_pane_update(self, pane_id: str) -> None:
        """Emit a pane update event with current state"""
        pane = await self.registry.get(pane_id)
        if not pane:
            return

        # Use capture_pane to get properly rendered terminal content
        # For incremental updates, only capture last 300 lines for faster transfer
        incremental_lines = 300
        try:
            lines = await self.tmux.capture_pane(pane_id, incremental_lines)
            cursor_pos = await self.tmux.get_cursor_position(pane_id)
            if cursor_pos:
                cursor_x, cursor_y_raw, pane_height = cursor_pos
                # Calculate actual line index in captured output
                # Visible portion is the last pane_height lines
                visible_start = max(0, len(lines) - pane_height)
                cursor_y = visible_start + cursor_y_raw
            else:
                cursor_x, cursor_y = 0, 0
            # Update registry with captured content
            await self.registry.update_output(pane_id, lines, "")
        except Exception as e:
            logger.warning(f"Failed to capture pane {pane_id}: {e}")
            lines = await self.registry.get_output(pane_id)
            cursor_x, cursor_y = 0, 0

        # Parse for input request
        input_request = self.parser.parse(lines)
        if input_request:
            await self.registry.set_input_request(pane_id, input_request)
        elif pane.input_request and not self.parser.has_input_marker(lines):
            await self.registry.clear_input_request(pane_id)

        # Refresh pane state
        pane = await self.registry.get(pane_id)
        if pane:
            event = PaneUpdateEvent(
                pane_id=pane_id,
                status=pane.status,
                lines=lines,
                input_request=pane.input_request,
                cursor_x=cursor_x,
                cursor_y=cursor_y,
            )
            await self._emit_event(event)

    async def _handle_sessions_changed(self) -> None:
        """Handle session list changes from control mode"""
        logger.info("Sessions changed, running discovery")
        await self._discover_panes()

    # =========================================================================
    # Polling Mode Implementation (Fallback)
    # =========================================================================

    async def _start_polling(self) -> None:
        """Start polling-based observation (fallback mode)"""
        # Start background tasks
        self._discovery_task = asyncio.create_task(
            self._discovery_loop(),
            name="observer_discovery"
        )
        self._polling_task = asyncio.create_task(
            self._polling_loop(),
            name="observer_polling"
        )

        # Run initial discovery
        await self._discover_panes()

    async def _polling_loop(self) -> None:
        """Poll all known panes for output changes"""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._poll_all_panes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _poll_all_panes(self) -> None:
        """Poll all registered panes for changes"""
        panes = await self.registry.get_all()

        # Poll panes concurrently
        tasks = [self._poll_pane(pane.pane_id) for pane in panes]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_pane(self, pane_id: str) -> None:
        """
        Poll a single pane for output changes.

        Args:
            pane_id: Pane to poll
        """
        try:
            # Capture pane output and cursor position
            lines = await self.tmux.capture_pane(pane_id, self.capture_lines)
            cursor_pos = await self.tmux.get_cursor_position(pane_id)
            if cursor_pos:
                cursor_x, cursor_y_raw, pane_height = cursor_pos
                # Calculate actual line index in captured output
                visible_start = max(0, len(lines) - pane_height)
                cursor_y = visible_start + cursor_y_raw
            else:
                cursor_x, cursor_y = 0, 0

            # Calculate hash for change detection (fewer lines = faster)
            content = "\n".join(lines[-50:])  # Hash last 50 lines for efficiency
            output_hash = hashlib.sha256(content.encode()).hexdigest()

            # Check if output changed
            changed = await self.registry.update_output(pane_id, lines, output_hash)

            if changed:
                # Parse for input request
                input_request = self.parser.parse(lines)
                pane = await self.registry.get(pane_id)

                if pane:
                    # Update input request if found
                    if input_request:
                        await self.registry.set_input_request(pane_id, input_request)
                    elif pane.input_request and not self.parser.has_input_marker(lines):
                        # Input marker gone, clear the request
                        await self.registry.clear_input_request(pane_id)

                    # Update cursor position
                    pane.cursor_x = cursor_x
                    pane.cursor_y = cursor_y

                    # Emit update event
                    pane = await self.registry.get(pane_id)  # Refresh state
                    if pane:
                        event = PaneUpdateEvent(
                            pane_id=pane_id,
                            status=pane.status,
                            lines=lines,
                            input_request=pane.input_request,
                            cursor_x=cursor_x,
                            cursor_y=cursor_y,
                        )
                        await self._emit_event(event)

        except Exception as e:
            logger.error(f"Error polling pane {pane_id}: {e}")

    # =========================================================================
    # Shared Discovery Logic
    # =========================================================================

    async def _discovery_loop(self) -> None:
        """Periodically discover new/removed panes"""
        while self._running:
            try:
                await asyncio.sleep(self.discovery_interval)
                await self._discover_panes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _discover_panes(self) -> None:
        """Discover panes and update registry"""
        try:
            tmux_panes = await self.tmux.discover_all_panes()
        except Exception as e:
            logger.error(f"Failed to discover panes: {e}")
            return

        # Get current pane IDs
        current_ids = await self.registry.get_pane_ids()
        discovered_ids = {p.pane_id for p in tmux_panes}

        # Find new panes
        new_ids = discovered_ids - current_ids
        for tmux_pane in tmux_panes:
            if tmux_pane.pane_id in new_ids:
                await self._add_pane(tmux_pane)

        # Find removed panes
        removed_ids = current_ids - discovered_ids
        for pane_id in removed_ids:
            await self._remove_pane(pane_id)

    async def _add_pane(self, tmux_pane: TmuxPane) -> None:
        """Add a newly discovered pane"""
        state = PaneState(
            pane_id=tmux_pane.pane_id,
            session_name=tmux_pane.session_name,
            window_name=tmux_pane.window_name,
            window_index=tmux_pane.window_index,
            pane_index=tmux_pane.pane_index,
            title=tmux_pane.pane_title,
            status=PaneStatus.RUNNING,
            last_activity=datetime.now(),
        )

        await self.registry.update(tmux_pane.pane_id, state)

        # If in control mode, capture initial state for new pane
        if self._mode == "control_mode":
            try:
                lines = await self.tmux.capture_pane(tmux_pane.pane_id, self.capture_lines)
                await self.registry.update_output(tmux_pane.pane_id, lines, "")
            except Exception as e:
                logger.warning(f"Failed to capture initial state for {tmux_pane.pane_id}: {e}")

        # Emit discovery event
        event = PaneDiscoveryEvent(pane=state.to_info())
        await self._emit_event(event)

        logger.info(f"Discovered new pane: {tmux_pane.pane_id} ({tmux_pane.session_name}:{tmux_pane.window_name})")

    async def _remove_pane(self, pane_id: str) -> None:
        """Remove a pane that no longer exists"""
        await self.registry.remove(pane_id)

        # Emit removal event
        event = PaneRemovedEvent(pane_id=pane_id)
        await self._emit_event(event)

        logger.info(f"Removed pane: {pane_id}")

    @property
    def is_running(self) -> bool:
        """Check if observer is running"""
        return self._running

    @property
    def mode(self) -> str:
        """Get current observation mode ('control_mode', 'polling', or 'none')"""
        return self._mode
