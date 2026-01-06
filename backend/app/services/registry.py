"""Pane state registry service"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from ..models.input import InputRequest
from ..models.pane import PaneState, PaneStatus

logger = logging.getLogger(__name__)


class PaneRegistry:
    """
    In-memory registry of all tracked panes.
    Thread-safe for async access using asyncio.Lock.
    """

    def __init__(self):
        self._panes: dict[str, PaneState] = {}
        self._lock = asyncio.Lock()

    async def get_all(self) -> list[PaneState]:
        """
        Get all tracked panes.

        Returns:
            List of all pane states
        """
        async with self._lock:
            return list(self._panes.values())

    async def get(self, pane_id: str) -> Optional[PaneState]:
        """
        Get a specific pane state.

        Args:
            pane_id: Pane identifier

        Returns:
            PaneState or None if not found
        """
        async with self._lock:
            return self._panes.get(pane_id)

    async def get_pane_ids(self) -> set[str]:
        """
        Get set of all tracked pane IDs.

        Returns:
            Set of pane IDs
        """
        async with self._lock:
            return set(self._panes.keys())

    async def update(self, pane_id: str, state: PaneState) -> None:
        """
        Update or create a pane state.

        Args:
            pane_id: Pane identifier
            state: New pane state
        """
        async with self._lock:
            self._panes[pane_id] = state
            logger.debug(f"Updated pane {pane_id} state: {state.status}")

    async def update_output(
        self,
        pane_id: str,
        lines: list[str],
        output_hash: str,
    ) -> bool:
        """
        Update pane output if it has changed.

        Args:
            pane_id: Pane identifier
            lines: New output lines
            output_hash: Hash of the new output

        Returns:
            True if output was updated (changed), False if no change
        """
        async with self._lock:
            pane = self._panes.get(pane_id)
            if not pane:
                return False

            if pane.last_output_hash == output_hash:
                return False

            pane.last_lines = lines
            pane.last_output_hash = output_hash
            pane.last_activity = datetime.now()
            return True

    async def append_output(
        self,
        pane_id: str,
        new_data: str,
        max_lines: int = 500,
    ) -> bool:
        """
        Append new output data to pane buffer (for control mode streaming).

        This method is used for incremental updates from control mode's
        %output notifications, appending data to existing lines.

        Args:
            pane_id: Pane identifier
            new_data: New output data to append (may contain newlines)
            max_lines: Maximum lines to keep in buffer

        Returns:
            True if appended, False if pane not found
        """
        async with self._lock:
            pane = self._panes.get(pane_id)
            if not pane:
                return False

            # Append to the last line or create new lines
            if new_data:
                # Split by newlines
                new_lines = new_data.split('\n')

                if pane.last_lines:
                    # Append first part to last existing line
                    pane.last_lines[-1] += new_lines[0]
                    # Add remaining lines
                    if len(new_lines) > 1:
                        pane.last_lines.extend(new_lines[1:])
                else:
                    pane.last_lines = new_lines

                # Trim to max buffer size
                if len(pane.last_lines) > max_lines:
                    pane.last_lines = pane.last_lines[-max_lines:]

                pane.last_activity = datetime.now()
                # Clear hash since we're doing incremental updates
                pane.last_output_hash = ""

            return True

    async def get_output(self, pane_id: str) -> list[str]:
        """
        Get current output lines for a pane.

        Args:
            pane_id: Pane identifier

        Returns:
            List of output lines, or empty list if pane not found
        """
        async with self._lock:
            pane = self._panes.get(pane_id)
            if not pane:
                return []
            return list(pane.last_lines)

    async def update_status(self, pane_id: str, status: PaneStatus) -> bool:
        """
        Update pane status.

        Args:
            pane_id: Pane identifier
            status: New status

        Returns:
            True if status changed, False otherwise
        """
        async with self._lock:
            pane = self._panes.get(pane_id)
            if not pane:
                return False

            if pane.status == status:
                return False

            pane.status = status
            pane.last_activity = datetime.now()
            logger.info(f"Pane {pane_id} status changed to {status}")
            return True

    async def set_input_request(
        self,
        pane_id: str,
        request: Optional[InputRequest],
    ) -> bool:
        """
        Set input request for a pane.

        Args:
            pane_id: Pane identifier
            request: Input request or None to clear

        Returns:
            True if updated, False if pane not found
        """
        async with self._lock:
            pane = self._panes.get(pane_id)
            if not pane:
                return False

            pane.input_request = request
            if request:
                pane.status = PaneStatus.WAITING_INPUT
                logger.info(f"Pane {pane_id} waiting for {request.input_type} input")
            pane.last_activity = datetime.now()
            return True

    async def clear_input_request(self, pane_id: str) -> bool:
        """
        Clear input request for a pane (after input submitted).

        Args:
            pane_id: Pane identifier

        Returns:
            True if cleared, False if pane not found
        """
        async with self._lock:
            pane = self._panes.get(pane_id)
            if not pane:
                return False

            pane.input_request = None
            pane.status = PaneStatus.RUNNING
            pane.last_activity = datetime.now()
            logger.info(f"Pane {pane_id} input request cleared")
            return True

    async def remove(self, pane_id: str) -> bool:
        """
        Remove a pane from the registry.

        Args:
            pane_id: Pane identifier

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if pane_id in self._panes:
                del self._panes[pane_id]
                logger.info(f"Removed pane {pane_id} from registry")
                return True
            return False

    async def clear(self) -> None:
        """Clear all panes from registry"""
        async with self._lock:
            self._panes.clear()
            logger.info("Cleared all panes from registry")

    @property
    def count(self) -> int:
        """Get number of tracked panes (not async-safe, for logging only)"""
        return len(self._panes)
