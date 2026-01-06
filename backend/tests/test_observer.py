"""Tests for ObserverDaemon service"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.events import PaneDiscoveryEvent, PaneRemovedEvent, PaneUpdateEvent
from app.models.input import InputRequest, InputType
from app.models.pane import PaneState, PaneStatus
from app.services.observer import ObserverDaemon
from app.services.parser import InputParser
from app.services.registry import PaneRegistry
from app.services.tmux import TmuxPane, TmuxService


@pytest.fixture
def mock_tmux() -> MagicMock:
    """Create mock TmuxService"""
    service = MagicMock(spec=TmuxService)
    service.socket_path = None
    service.is_available = AsyncMock(return_value=True)
    service.list_sessions = AsyncMock(return_value=["session1"])
    service.list_windows = AsyncMock(return_value=[{"index": 0, "name": "main"}])
    service.discover_all_panes = AsyncMock(return_value=[
        TmuxPane(
            pane_id="%0",
            session_name="session1",
            window_name="main",
            window_index=0,
            pane_index=0,
            pane_title="test",
            pane_active=True,
        )
    ])
    service.capture_pane = AsyncMock(return_value=["line1", "line2", "line3"])
    service.send_keys = AsyncMock(return_value=True)
    return service


@pytest.fixture
def registry() -> PaneRegistry:
    """Create fresh registry"""
    return PaneRegistry()


@pytest.fixture
def parser() -> InputParser:
    """Create parser"""
    return InputParser()


@pytest.fixture
def observer(mock_tmux: MagicMock, registry: PaneRegistry, parser: InputParser) -> ObserverDaemon:
    """Create observer with polling mode (easier to test)"""
    return ObserverDaemon(
        tmux_service=mock_tmux,
        registry=registry,
        parser=parser,
        use_control_mode=False,  # Use polling for easier testing
        poll_interval=0.1,
        discovery_interval=0.5,
    )


class TestObserverDaemon:
    """Tests for ObserverDaemon"""

    async def test_initial_state(self, observer: ObserverDaemon):
        """Test observer starts in correct initial state"""
        assert observer.is_running is False
        assert observer.mode == "none"

    async def test_start_polling_mode(self, observer: ObserverDaemon):
        """Test starting observer in polling mode"""
        # Start and immediately stop
        await observer.start()
        assert observer.is_running is True
        assert observer.mode == "polling"

        await observer.stop()
        assert observer.is_running is False
        assert observer.mode == "none"

    async def test_discover_panes(
        self,
        observer: ObserverDaemon,
        registry: PaneRegistry,
        mock_tmux: MagicMock,
    ):
        """Test pane discovery adds panes to registry"""
        await observer._discover_panes()

        panes = await registry.get_all()
        assert len(panes) == 1
        assert panes[0].pane_id == "%0"
        assert panes[0].session_name == "session1"

    async def test_discover_new_pane_emits_event(
        self,
        observer: ObserverDaemon,
        mock_tmux: MagicMock,
    ):
        """Test that discovering new panes emits events"""
        events = []

        async def capture_event(event):
            events.append(event)

        observer.on_event(capture_event)
        await observer._discover_panes()

        assert len(events) == 1
        assert isinstance(events[0], PaneDiscoveryEvent)
        assert events[0].pane.pane_id == "%0"

    async def test_discover_removed_pane_emits_event(
        self,
        observer: ObserverDaemon,
        registry: PaneRegistry,
        mock_tmux: MagicMock,
    ):
        """Test that removing panes emits removal events"""
        # First add a pane
        pane = PaneState(
            pane_id="%99",
            session_name="old",
            window_name="old",
            status=PaneStatus.RUNNING,
        )
        await registry.update("%99", pane)

        events = []

        async def capture_event(event):
            events.append(event)

        observer.on_event(capture_event)

        # Discover (mock returns different pane, so %99 should be removed)
        await observer._discover_panes()

        # Should have discovery event for %0 and removal event for %99
        assert len(events) == 2
        removal_events = [e for e in events if isinstance(e, PaneRemovedEvent)]
        assert len(removal_events) == 1
        assert removal_events[0].pane_id == "%99"

    async def test_poll_pane_updates_output(
        self,
        observer: ObserverDaemon,
        registry: PaneRegistry,
        mock_tmux: MagicMock,
    ):
        """Test polling updates pane output"""
        # Add pane first
        pane = PaneState(
            pane_id="%0",
            session_name="session1",
            window_name="main",
            status=PaneStatus.RUNNING,
        )
        await registry.update("%0", pane)

        # Poll the pane
        await observer._poll_pane("%0")

        # Check output was captured
        updated_pane = await registry.get("%0")
        assert updated_pane is not None
        assert updated_pane.last_lines == ["line1", "line2", "line3"]

    async def test_poll_pane_detects_input_request(
        self,
        observer: ObserverDaemon,
        registry: PaneRegistry,
        mock_tmux: MagicMock,
    ):
        """Test polling detects input requests"""
        # Add pane
        pane = PaneState(
            pane_id="%0",
            session_name="session1",
            window_name="main",
            status=PaneStatus.RUNNING,
        )
        await registry.update("%0", pane)

        # Mock capture to return input request marker
        mock_tmux.capture_pane = AsyncMock(return_value=[
            "some output",
            "[INPUT_REQUIRED]",
            "TYPE: text",
            "PROMPT: Enter name:",
        ])

        events = []
        async def capture_event(event):
            events.append(event)
        observer.on_event(capture_event)

        # Poll
        await observer._poll_pane("%0")

        # Check input request was detected
        updated_pane = await registry.get("%0")
        assert updated_pane is not None
        assert updated_pane.status == PaneStatus.WAITING_INPUT
        assert updated_pane.input_request is not None
        assert updated_pane.input_request.input_type == InputType.TEXT

    async def test_poll_pane_clears_input_request(
        self,
        observer: ObserverDaemon,
        registry: PaneRegistry,
        mock_tmux: MagicMock,
    ):
        """Test polling clears input request when marker gone"""
        # Add pane with existing input request
        pane = PaneState(
            pane_id="%0",
            session_name="session1",
            window_name="main",
            status=PaneStatus.WAITING_INPUT,
            input_request=InputRequest(input_type=InputType.TEXT, prompt="test"),
        )
        await registry.update("%0", pane)

        # Mock capture without input marker
        mock_tmux.capture_pane = AsyncMock(return_value=["normal output"])

        # Poll
        await observer._poll_pane("%0")

        # Check input request was cleared
        updated_pane = await registry.get("%0")
        assert updated_pane is not None
        assert updated_pane.status == PaneStatus.RUNNING
        assert updated_pane.input_request is None

    async def test_event_callback_registration(self, observer: ObserverDaemon):
        """Test event callback registration and removal"""
        callback = AsyncMock()

        observer.on_event(callback)
        assert len(observer._callbacks) == 1

        observer.remove_callback(callback)
        assert len(observer._callbacks) == 0

    async def test_event_callback_error_handling(
        self,
        observer: ObserverDaemon,
        mock_tmux: MagicMock,
    ):
        """Test that callback errors don't stop event processing"""
        call_count = 0

        async def failing_callback(event):
            raise Exception("callback error")

        async def counting_callback(event):
            nonlocal call_count
            call_count += 1

        observer.on_event(failing_callback)
        observer.on_event(counting_callback)

        # This should not raise despite first callback failing
        await observer._discover_panes()

        # Second callback should still have been called
        assert call_count == 1

    async def test_double_start_ignored(self, observer: ObserverDaemon):
        """Test that starting twice is ignored"""
        await observer.start()
        await observer.start()  # Should not raise

        assert observer.is_running is True

        await observer.stop()

    async def test_stop_when_not_running(self, observer: ObserverDaemon):
        """Test stopping when not running is safe"""
        await observer.stop()  # Should not raise
        assert observer.is_running is False


class TestObserverControlMode:
    """Tests for control mode specific behavior"""

    async def test_control_mode_fallback_to_polling(
        self,
        mock_tmux: MagicMock,
        registry: PaneRegistry,
        parser: InputParser,
    ):
        """Test fallback to polling when control mode fails"""
        observer = ObserverDaemon(
            tmux_service=mock_tmux,
            registry=registry,
            parser=parser,
            use_control_mode=True,
            poll_interval=0.1,
            discovery_interval=0.5,
        )

        # Patch SessionManager to fail
        with patch('app.services.observer.SessionManager') as mock_session_manager:
            mock_instance = MagicMock()
            mock_instance.start = AsyncMock(side_effect=Exception("control mode failed"))
            mock_instance.stop = AsyncMock()
            mock_session_manager.return_value = mock_instance

            await observer.start()

            # Should fall back to polling
            assert observer.mode == "polling"

            await observer.stop()
