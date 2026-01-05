"""Observer daemon for polling tmux panes"""
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
from .parser import InputParser
from .registry import PaneRegistry
from .tmux import TmuxPane, TmuxService

logger = logging.getLogger(__name__)

# Type alias for event callback
EventCallback = Callable[[WebSocketEvent], Awaitable[None]]


class ObserverDaemon:
    """
    Background daemon that polls tmux panes and detects changes.
    Runs as asyncio tasks within the FastAPI application.
    """

    def __init__(
        self,
        tmux_service: TmuxService,
        registry: PaneRegistry,
        parser: InputParser,
        poll_interval: float = 1.0,
        discovery_interval: float = 5.0,
        capture_lines: int = 500,
    ):
        """
        Initialize the observer daemon.

        Args:
            tmux_service: TmuxService instance for tmux interaction
            registry: PaneRegistry for state storage
            parser: InputParser for detecting input requests
            poll_interval: Seconds between output polls
            discovery_interval: Seconds between pane discovery
            capture_lines: Number of lines to capture from each pane
        """
        self.tmux = tmux_service
        self.registry = registry
        self.parser = parser
        self.poll_interval = poll_interval
        self.discovery_interval = discovery_interval
        self.capture_lines = capture_lines

        self._running = False
        self._discovery_task: Optional[asyncio.Task] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._callbacks: list[EventCallback] = []

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
        """Start the observer background tasks"""
        if self._running:
            logger.warning("Observer already running")
            return

        self._running = True
        logger.info("Starting observer daemon")

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

    async def stop(self) -> None:
        """Gracefully stop the observer"""
        if not self._running:
            return

        logger.info("Stopping observer daemon")
        self._running = False

        # Cancel tasks
        for task in [self._discovery_task, self._polling_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._discovery_task = None
        self._polling_task = None

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
            # Capture pane output
            lines = await self.tmux.capture_pane(pane_id, self.capture_lines)

            # Calculate hash for change detection
            content = "\n".join(lines[-100:])  # Hash last 100 lines for efficiency
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

                    # Emit update event
                    pane = await self.registry.get(pane_id)  # Refresh state
                    if pane:
                        event = PaneUpdateEvent(
                            pane_id=pane_id,
                            status=pane.status,
                            lines=lines,
                            input_request=pane.input_request,
                        )
                        await self._emit_event(event)

        except Exception as e:
            logger.error(f"Error polling pane {pane_id}: {e}")

    @property
    def is_running(self) -> bool:
        """Check if observer is running"""
        return self._running
