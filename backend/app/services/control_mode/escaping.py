"""
Escape/unescape utilities for tmux control mode protocol.

tmux control mode escapes:
- Characters with code < 32 (control chars) as \\xxx (octal)
- Backslash itself as \\134

Example: "hello\\012world" -> "hello\nworld"
"""

import re


# Pattern to match octal escape sequences like \012 or \134
_OCTAL_PATTERN = re.compile(r'\\([0-7]{3})')


def unescape_output(data: str) -> str:
    """
    Unescape tmux control mode output data.

    Converts octal escape sequences (\\xxx) back to their original characters.

    Args:
        data: Escaped string from tmux %output notification

    Returns:
        Unescaped string with original characters restored

    Example:
        >>> unescape_output("hello\\012world")
        'hello\\nworld'
        >>> unescape_output("backslash: \\134")
        'backslash: \\\\'
    """
    def replace_octal(match: re.Match) -> str:
        octal_value = match.group(1)
        char_code = int(octal_value, 8)
        return chr(char_code)

    return _OCTAL_PATTERN.sub(replace_octal, data)


def escape_input(data: str) -> str:
    """
    Escape data for sending to tmux control mode.

    Escapes control characters and backslashes to octal format.

    Args:
        data: String to escape

    Returns:
        Escaped string safe for tmux control mode
    """
    result = []
    for char in data:
        code = ord(char)
        # Escape control chars (except newline which tmux handles) and backslash
        if code < 32 or char == '\\':
            result.append(f'\\{code:03o}')
        else:
            result.append(char)
    return ''.join(result)


def unescape_line(line: str) -> str:
    """
    Unescape a single line of output, handling edge cases.

    This is a convenience wrapper that also strips trailing whitespace
    that tmux sometimes adds.
    """
    return unescape_output(line).rstrip()
