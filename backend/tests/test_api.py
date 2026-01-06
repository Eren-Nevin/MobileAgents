"""Tests for REST API endpoints"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.input import InputRequest, InputType
from app.models.pane import PaneState, PaneStatus
from app.services.registry import PaneRegistry


class TestPanesAPI:
    """Tests for /api/panes endpoints"""

    async def test_list_panes_empty(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test listing panes when empty"""
        response = await async_client.get("/api/panes")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_panes(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test listing panes"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            status=PaneStatus.RUNNING,
        )
        await registry.update("%0", pane)

        response = await async_client.get("/api/panes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["pane_id"] == "%0"
        assert data[0]["status"] == "running"

    async def test_get_pane(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test getting a specific pane"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
        )
        await registry.update("%0", pane)

        response = await async_client.get("/api/panes/%0")

        assert response.status_code == 200
        data = response.json()
        assert data["pane_id"] == "%0"
        assert data["session_name"] == "test"

    async def test_get_pane_not_found(self, async_client):
        """Test getting a nonexistent pane"""
        response = await async_client.get("/api/panes/%999")

        assert response.status_code == 404

    async def test_get_pane_output(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test getting pane output"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            last_lines=["line1", "line2", "line3"],
        )
        await registry.update("%0", pane)

        response = await async_client.get("/api/panes/%0/output")

        assert response.status_code == 200
        data = response.json()
        assert data["pane_id"] == "%0"
        assert data["lines"] == ["line1", "line2", "line3"]
        assert data["line_count"] == 3

    async def test_send_input_success(
        self,
        async_client,
        registry: PaneRegistry,
        mock_tmux_service: MagicMock,
    ):
        """Test sending input to a pane"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            status=PaneStatus.WAITING_INPUT,
            input_request=InputRequest(input_type=InputType.TEXT, prompt="Enter:"),
        )
        await registry.update("%0", pane)

        response = await async_client.post(
            "/api/panes/%0/input",
            json={"input_type": "text", "value": "hello"},
        )

        assert response.status_code == 200
        mock_tmux_service.send_keys.assert_called_once_with("%0", "hello")

    async def test_send_input_not_waiting(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test sending input when pane is not waiting"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            status=PaneStatus.RUNNING,
        )
        await registry.update("%0", pane)

        response = await async_client.post(
            "/api/panes/%0/input",
            json={"input_type": "text", "value": "hello"},
        )

        assert response.status_code == 400

    async def test_send_input_type_mismatch(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test sending input with wrong type"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            status=PaneStatus.WAITING_INPUT,
            input_request=InputRequest(input_type=InputType.TEXT, prompt="Enter:"),
        )
        await registry.update("%0", pane)

        response = await async_client.post(
            "/api/panes/%0/input",
            json={"input_type": "choice", "value": "1"},
        )

        assert response.status_code == 400

    async def test_health_check(self, async_client):
        """Test health check endpoint"""
        response = await async_client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestKeysAPI:
    """Tests for /api/panes/{id}/keys endpoint"""

    async def test_send_keys_success(
        self,
        async_client,
        registry: PaneRegistry,
        mock_tmux_service: MagicMock,
    ):
        """Test sending raw keys to a pane"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            status=PaneStatus.RUNNING,  # Can send keys even when not waiting
        )
        await registry.update("%0", pane)

        response = await async_client.post(
            "/api/panes/%0/keys",
            json={"keys": "hello", "enter": True},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_tmux_service.send_keys.assert_called_once_with(
            "%0", "hello", enter=True, literal=True
        )

    async def test_send_keys_no_enter(
        self,
        async_client,
        registry: PaneRegistry,
        mock_tmux_service: MagicMock,
    ):
        """Test sending keys without Enter"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
        )
        await registry.update("%0", pane)

        response = await async_client.post(
            "/api/panes/%0/keys",
            json={"keys": "a", "enter": False},
        )

        assert response.status_code == 200
        mock_tmux_service.send_keys.assert_called_once_with(
            "%0", "a", enter=False, literal=True
        )

    async def test_send_keys_special_key(
        self,
        async_client,
        registry: PaneRegistry,
        mock_tmux_service: MagicMock,
    ):
        """Test sending special keys (non-literal)"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
        )
        await registry.update("%0", pane)

        response = await async_client.post(
            "/api/panes/%0/keys",
            json={"keys": "Up", "enter": False, "literal": False},
        )

        assert response.status_code == 200
        mock_tmux_service.send_keys.assert_called_once_with(
            "%0", "Up", enter=False, literal=False
        )

    async def test_send_keys_pane_not_found(self, async_client):
        """Test sending keys to nonexistent pane"""
        response = await async_client.post(
            "/api/panes/%999/keys",
            json={"keys": "hello", "enter": True},
        )

        assert response.status_code == 404

    async def test_send_keys_failure(
        self,
        async_client,
        registry: PaneRegistry,
        mock_tmux_service: MagicMock,
    ):
        """Test handling of tmux send_keys failure"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
        )
        await registry.update("%0", pane)

        mock_tmux_service.send_keys = AsyncMock(return_value=False)

        response = await async_client.post(
            "/api/panes/%0/keys",
            json={"keys": "hello", "enter": True},
        )

        assert response.status_code == 500

    async def test_get_pane_output_with_refresh(
        self,
        async_client,
        registry: PaneRegistry,
        mock_tmux_service: MagicMock,
    ):
        """Test getting pane output with refresh flag"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            last_lines=["old line"],
        )
        await registry.update("%0", pane)

        mock_tmux_service.capture_pane = AsyncMock(
            return_value=["fresh line 1", "fresh line 2"]
        )

        response = await async_client.get("/api/panes/%0/output?refresh=true")

        assert response.status_code == 200
        data = response.json()
        assert data["lines"] == ["fresh line 1", "fresh line 2"]
        mock_tmux_service.capture_pane.assert_called_once()

    async def test_get_pane_output_custom_lines(
        self,
        async_client,
        registry: PaneRegistry,
    ):
        """Test getting pane output with custom line count"""
        pane = PaneState(
            pane_id="%0",
            session_name="test",
            window_name="main",
            last_lines=["line1", "line2", "line3", "line4", "line5"],
        )
        await registry.update("%0", pane)

        response = await async_client.get("/api/panes/%0/output?lines=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["lines"]) == 3
        # Should return last 3 lines
        assert data["lines"] == ["line3", "line4", "line5"]
