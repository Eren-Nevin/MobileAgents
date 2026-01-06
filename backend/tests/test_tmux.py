"""Tests for TmuxService"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tmux import TmuxError, TmuxPane, TmuxService


@pytest.fixture
def tmux_service() -> TmuxService:
    """Create TmuxService instance"""
    return TmuxService()


@pytest.fixture
def tmux_service_with_socket() -> TmuxService:
    """Create TmuxService with custom socket"""
    return TmuxService(socket_path="/tmp/tmux-test/default")


class TestTmuxService:
    """Tests for TmuxService"""

    def test_base_cmd_default(self, tmux_service: TmuxService):
        """Test base command without socket"""
        assert tmux_service._base_cmd() == ["tmux"]

    def test_base_cmd_with_socket(self, tmux_service_with_socket: TmuxService):
        """Test base command with custom socket"""
        cmd = tmux_service_with_socket._base_cmd()
        assert cmd == ["tmux", "-S", "/tmp/tmux-test/default"]

    async def test_run_command_success(self, tmux_service: TmuxService):
        """Test successful command execution"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"output\n", b""))
            mock_exec.return_value = mock_process

            result = await tmux_service._run_command("list-sessions")

            assert result == "output\n"
            mock_exec.assert_called_once()

    async def test_run_command_failure(self, tmux_service: TmuxService):
        """Test command failure raises TmuxError"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
            mock_exec.return_value = mock_process

            with pytest.raises(TmuxError) as exc_info:
                await tmux_service._run_command("bad-command")

            assert "error message" in str(exc_info.value)

    async def test_run_command_no_server(self, tmux_service: TmuxService):
        """Test graceful handling of no tmux server"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"no server running"))
            mock_exec.return_value = mock_process

            # Should return empty string, not raise
            result = await tmux_service._run_command("list-sessions")
            assert result == ""

    async def test_run_command_no_sessions(self, tmux_service: TmuxService):
        """Test graceful handling of no sessions"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"no sessions"))
            mock_exec.return_value = mock_process

            result = await tmux_service._run_command("list-sessions")
            assert result == ""

    async def test_run_command_tmux_not_found(self, tmux_service: TmuxService):
        """Test handling of tmux not installed"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError()

            with pytest.raises(TmuxError) as exc_info:
                await tmux_service._run_command("list-sessions")

            assert "not found" in str(exc_info.value)

    async def test_is_available_true(self, tmux_service: TmuxService):
        """Test is_available returns True when tmux is running"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "session1\n"

            result = await tmux_service.is_available()

            assert result is True

    async def test_is_available_false(self, tmux_service: TmuxService):
        """Test is_available returns False on error"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.side_effect = TmuxError("no server")

            result = await tmux_service.is_available()

            assert result is False

    async def test_list_sessions(self, tmux_service: TmuxService):
        """Test listing sessions"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "session1\nsession2\n"

            result = await tmux_service.list_sessions()

            assert result == ["session1", "session2"]

    async def test_list_sessions_empty(self, tmux_service: TmuxService):
        """Test listing sessions when none exist"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = ""

            result = await tmux_service.list_sessions()

            assert result == []

    async def test_list_windows(self, tmux_service: TmuxService):
        """Test listing windows"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "0|main\n1|editor\n"

            result = await tmux_service.list_windows("session1")

            assert result == [
                {"index": 0, "name": "main"},
                {"index": 1, "name": "editor"},
            ]

    async def test_list_panes(self, tmux_service: TmuxService):
        """Test listing panes"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "%0|session1|main|0|0|title1|1\n%1|session1|main|0|1|title2|0\n"

            result = await tmux_service.list_panes("session1", 0)

            assert len(result) == 2
            assert result[0].pane_id == "%0"
            assert result[0].pane_active is True
            assert result[1].pane_id == "%1"
            assert result[1].pane_active is False

    async def test_discover_all_panes(self, tmux_service: TmuxService):
        """Test discovering all panes"""
        with patch.object(tmux_service, "list_sessions") as mock_sessions:
            mock_sessions.return_value = ["session1"]

            with patch.object(tmux_service, "list_windows") as mock_windows:
                mock_windows.return_value = [{"index": 0, "name": "main"}]

                with patch.object(tmux_service, "list_panes") as mock_panes:
                    mock_panes.return_value = [
                        TmuxPane(
                            pane_id="%0",
                            session_name="session1",
                            window_name="main",
                            window_index=0,
                            pane_index=0,
                            pane_title="test",
                            pane_active=True,
                        )
                    ]

                    result = await tmux_service.discover_all_panes()

                    assert len(result) == 1
                    assert result[0].pane_id == "%0"

    async def test_capture_pane(self, tmux_service: TmuxService):
        """Test capturing pane output"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "line1\nline2\nline3\n"

            result = await tmux_service.capture_pane("%0", lines=100)

            assert result == ["line1", "line2", "line3"]
            # Check -S flag was passed
            call_args = mock_run.call_args[0]
            assert "-S" in call_args
            assert "-100" in call_args

    async def test_capture_pane_with_start_line(self, tmux_service: TmuxService):
        """Test capturing pane with specific start line"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "line1\nline2\n"

            result = await tmux_service.capture_pane("%0", start_line=-50)

            call_args = mock_run.call_args[0]
            assert "-50" in call_args

    async def test_send_keys_literal(self, tmux_service: TmuxService):
        """Test sending literal keys"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = ""

            result = await tmux_service.send_keys("%0", "hello", enter=True, literal=True)

            assert result is True
            # Should be called twice - once for text, once for Enter
            assert mock_run.call_count == 2

    async def test_send_keys_special(self, tmux_service: TmuxService):
        """Test sending special keys (non-literal)"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = ""

            result = await tmux_service.send_keys("%0", "Up", enter=False, literal=False)

            assert result is True
            # Should only be called once (no Enter)
            assert mock_run.call_count == 1
            # Check -l flag is NOT present
            call_args = mock_run.call_args[0]
            assert "-l" not in call_args

    async def test_send_keys_failure(self, tmux_service: TmuxService):
        """Test send_keys returns False on error"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.side_effect = TmuxError("pane not found")

            result = await tmux_service.send_keys("%0", "hello")

            assert result is False

    async def test_get_pane_pid(self, tmux_service: TmuxService):
        """Test getting pane PID"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.return_value = "12345\n"

            result = await tmux_service.get_pane_pid("%0")

            assert result == 12345

    async def test_get_pane_pid_not_found(self, tmux_service: TmuxService):
        """Test getting PID for nonexistent pane"""
        with patch.object(tmux_service, "_run_command") as mock_run:
            mock_run.side_effect = TmuxError("pane not found")

            result = await tmux_service.get_pane_pid("%999")

            assert result is None


class TestTmuxPane:
    """Tests for TmuxPane dataclass"""

    def test_tmux_pane_creation(self):
        """Test TmuxPane creation"""
        pane = TmuxPane(
            pane_id="%0",
            session_name="test",
            window_name="main",
            window_index=0,
            pane_index=0,
            pane_title="title",
            pane_active=True,
        )

        assert pane.pane_id == "%0"
        assert pane.session_name == "test"
        assert pane.pane_active is True
