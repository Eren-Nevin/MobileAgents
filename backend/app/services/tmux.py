"""TMux CLI wrapper service"""
import asyncio
import logging
import shlex
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TmuxPane:
    """Raw pane data from tmux"""
    pane_id: str
    session_name: str
    window_name: str
    window_index: int
    pane_index: int
    pane_title: str
    pane_active: bool


class TmuxError(Exception):
    """Exception raised for tmux command errors"""
    pass


class TmuxService:
    """Async wrapper for tmux CLI commands"""

    def __init__(self, socket_path: Optional[str] = None):
        """
        Initialize TmuxService.

        Args:
            socket_path: Optional path to tmux socket (for non-default servers)
        """
        self.socket_path = socket_path

    def _base_cmd(self) -> list[str]:
        """Get base tmux command with optional socket"""
        cmd = ["tmux"]
        if self.socket_path:
            cmd.extend(["-S", self.socket_path])
        return cmd

    async def _run_command(self, *args: str) -> str:
        """
        Run a tmux command asynchronously.

        Args:
            *args: Command arguments to append to base tmux command

        Returns:
            Command stdout as string

        Raises:
            TmuxError: If command fails
        """
        cmd = self._base_cmd() + list(args)
        logger.debug(f"Running tmux command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                # "no server running" is expected when tmux isn't started
                if "no server running" in error_msg or "no sessions" in error_msg:
                    return ""
                raise TmuxError(f"tmux command failed: {error_msg}")

            return stdout.decode()

        except FileNotFoundError:
            raise TmuxError("tmux not found. Please install tmux.")

    async def is_available(self) -> bool:
        """Check if tmux is available and running"""
        try:
            await self._run_command("list-sessions", "-F", "#{session_name}")
            return True
        except TmuxError:
            return False

    async def list_sessions(self) -> list[str]:
        """
        List all tmux session names.

        Returns:
            List of session names
        """
        output = await self._run_command(
            "list-sessions", "-F", "#{session_name}"
        )
        if not output.strip():
            return []
        return [line.strip() for line in output.strip().split("\n") if line.strip()]

    async def list_windows(self, session: str) -> list[dict]:
        """
        List windows in a session.

        Args:
            session: Session name

        Returns:
            List of window info dicts with keys: index, name
        """
        output = await self._run_command(
            "list-windows",
            "-t", session,
            "-F", "#{window_index}|#{window_name}"
        )
        if not output.strip():
            return []

        windows = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                windows.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                })
        return windows

    async def list_panes(self, session: str, window_index: int) -> list[TmuxPane]:
        """
        List panes in a window.

        Args:
            session: Session name
            window_index: Window index

        Returns:
            List of TmuxPane objects
        """
        target = f"{session}:{window_index}"
        output = await self._run_command(
            "list-panes",
            "-t", target,
            "-F", "#{pane_id}|#{session_name}|#{window_name}|#{window_index}|#{pane_index}|#{pane_title}|#{pane_active}"
        )
        if not output.strip():
            return []

        panes = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) >= 7:
                panes.append(TmuxPane(
                    pane_id=parts[0],
                    session_name=parts[1],
                    window_name=parts[2],
                    window_index=int(parts[3]),
                    pane_index=int(parts[4]),
                    pane_title=parts[5],
                    pane_active=parts[6] == "1",
                ))
        return panes

    async def discover_all_panes(self) -> list[TmuxPane]:
        """
        Discover all panes across all sessions and windows.

        Returns:
            List of all TmuxPane objects
        """
        all_panes: list[TmuxPane] = []

        sessions = await self.list_sessions()
        for session in sessions:
            windows = await self.list_windows(session)
            for window in windows:
                panes = await self.list_panes(session, window["index"])
                all_panes.extend(panes)

        logger.debug(f"Discovered {len(all_panes)} panes across {len(sessions)} sessions")
        return all_panes

    async def capture_pane(
        self,
        pane_id: str,
        lines: int = 500,
        start_line: Optional[int] = None,
    ) -> list[str]:
        """
        Capture output from a pane.

        Args:
            pane_id: Pane identifier (e.g., '%3')
            lines: Number of lines to capture from end (default 500)
            start_line: Optional specific start line (negative for scrollback)

        Returns:
            List of output lines
        """
        # -e flag includes escape sequences (ANSI colors)
        args = ["capture-pane", "-p", "-e", "-t", pane_id]

        if start_line is not None:
            args.extend(["-S", str(start_line)])
        else:
            args.extend(["-S", f"-{lines}"])

        output = await self._run_command(*args)

        # Split into lines, preserving empty lines
        result = output.split("\n")

        # Remove trailing empty line if present (artifact of split)
        if result and result[-1] == "":
            result = result[:-1]

        return result

    async def send_keys(
        self,
        pane_id: str,
        text: str,
        enter: bool = True,
        literal: bool = True,
    ) -> bool:
        """
        Send keys to a pane.

        Args:
            pane_id: Pane identifier
            text: Text to send
            enter: Whether to send Enter key after text
            literal: If True, send as literal text; if False, interpret special keys

        Returns:
            True if successful
        """
        try:
            if literal:
                # Use literal-keys mode with -l to avoid interpretation
                args = ["send-keys", "-t", pane_id, "-l", text]
            else:
                # Send as tmux key names (e.g., Up, Down, Left, Right, Enter)
                args = ["send-keys", "-t", pane_id, text]
            await self._run_command(*args)

            if enter and literal:
                await self._run_command("send-keys", "-t", pane_id, "Enter")

            logger.info(f"Sent keys to pane {pane_id}: {text[:50]}{'...' if len(text) > 50 else ''}")
            return True

        except TmuxError as e:
            logger.error(f"Failed to send keys to pane {pane_id}: {e}")
            return False

    async def get_pane_pid(self, pane_id: str) -> Optional[int]:
        """
        Get the PID of the process running in a pane.

        Args:
            pane_id: Pane identifier

        Returns:
            PID or None if pane not found
        """
        try:
            output = await self._run_command(
                "display-message",
                "-t", pane_id,
                "-p", "#{pane_pid}"
            )
            return int(output.strip()) if output.strip() else None
        except (TmuxError, ValueError):
            return None
