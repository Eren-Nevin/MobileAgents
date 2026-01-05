"""Input request parser service"""
import logging
import re
from typing import Optional

from ..models.input import InputRequest, InputType

logger = logging.getLogger(__name__)


class InputParser:
    """
    Parses [INPUT_REQUIRED] blocks from pane output.

    Expected format:
    ```
    [INPUT_REQUIRED]
    TYPE: text|choice|confirm
    PROMPT: <prompt text>           # for text type
    MESSAGE: <message text>         # for confirm type
    OPTIONS:                        # for choice type
    1) Option one
    2) Option two
    ```
    """

    INPUT_MARKER = "[INPUT_REQUIRED]"

    # Regex patterns
    TYPE_PATTERN = re.compile(r"TYPE:\s*(text|choice|confirm)", re.IGNORECASE)
    PROMPT_PATTERN = re.compile(r"PROMPT:\s*(.+)", re.IGNORECASE)
    MESSAGE_PATTERN = re.compile(r"MESSAGE:\s*(.+)", re.IGNORECASE)
    OPTIONS_PATTERN = re.compile(r"OPTIONS:\s*$", re.IGNORECASE)
    OPTION_LINE_PATTERN = re.compile(r"^\s*\d+\)\s*(.+)$")

    def parse(self, lines: list[str]) -> Optional[InputRequest]:
        """
        Scan lines for INPUT_REQUIRED block and parse it.

        Args:
            lines: Output lines from pane

        Returns:
            Parsed InputRequest or None if no input required
        """
        # Find the marker - look from the end as it's more likely to be recent
        marker_index = None
        for i in range(len(lines) - 1, -1, -1):
            if self.INPUT_MARKER in lines[i]:
                marker_index = i
                break

        if marker_index is None:
            return None

        # Extract the block starting from marker
        block = self._extract_block(lines, marker_index)
        if not block:
            return None

        return self._parse_block(block)

    def _extract_block(self, lines: list[str], marker_index: int) -> list[str]:
        """
        Extract the input block starting from the marker.

        The block ends when we encounter:
        - An empty line after content
        - Another marker
        - End of lines
        - A line that doesn't match expected patterns (after initial lines)

        Args:
            lines: All output lines
            marker_index: Index of the INPUT_REQUIRED marker

        Returns:
            List of lines in the block
        """
        block = []
        found_content = False

        for i in range(marker_index, min(marker_index + 20, len(lines))):
            line = lines[i].strip()

            # Skip the marker line itself for parsing
            if self.INPUT_MARKER in line:
                continue

            # Empty line after content signals end of block
            if not line:
                if found_content:
                    break
                continue

            found_content = True
            block.append(line)

        return block

    def _parse_block(self, block: list[str]) -> Optional[InputRequest]:
        """
        Parse extracted block into InputRequest.

        Args:
            block: Lines of the input block

        Returns:
            Parsed InputRequest or None if invalid
        """
        if not block:
            return None

        # Find type
        input_type = None
        prompt = None
        message = None
        options = None

        i = 0
        while i < len(block):
            line = block[i]

            # Check for TYPE
            type_match = self.TYPE_PATTERN.match(line)
            if type_match:
                type_str = type_match.group(1).lower()
                try:
                    input_type = InputType(type_str)
                except ValueError:
                    logger.warning(f"Unknown input type: {type_str}")
                i += 1
                continue

            # Check for PROMPT
            prompt_match = self.PROMPT_PATTERN.match(line)
            if prompt_match:
                prompt = prompt_match.group(1).strip()
                i += 1
                continue

            # Check for MESSAGE
            message_match = self.MESSAGE_PATTERN.match(line)
            if message_match:
                message = message_match.group(1).strip()
                i += 1
                continue

            # Check for OPTIONS
            if self.OPTIONS_PATTERN.match(line):
                options = []
                i += 1
                # Parse option lines
                while i < len(block):
                    opt_match = self.OPTION_LINE_PATTERN.match(block[i])
                    if opt_match:
                        options.append(opt_match.group(1).strip())
                        i += 1
                    else:
                        break
                continue

            i += 1

        # Validate and create request
        if input_type is None:
            # Try to infer type from content
            if options:
                input_type = InputType.CHOICE
            elif message:
                input_type = InputType.CONFIRM
            elif prompt:
                input_type = InputType.TEXT
            else:
                logger.warning("Could not determine input type from block")
                return None

        return InputRequest(
            input_type=input_type,
            prompt=prompt,
            message=message,
            options=options if options else None,
        )

    def has_input_marker(self, lines: list[str]) -> bool:
        """
        Quick check if lines contain the input marker.

        Args:
            lines: Output lines to check

        Returns:
            True if marker found
        """
        for line in reversed(lines):  # Check from end
            if self.INPUT_MARKER in line:
                return True
        return False
