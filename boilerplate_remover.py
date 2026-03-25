"""
boilerplate_remover.py
----------------------
Removes per-page footer and header noise lines that PDF-to-Markdown tools
copy verbatim from the decorative border area of each page.

Noise patterns are defined in config.BOILERPLATE_LINE_PATTERNS.  Add new
patterns there when adapting the pipeline to a different PDF template.

Public API
----------
    remove_boilerplate(text) -> str
"""

from __future__ import annotations

import re

from config import BOILERPLATE_LINE_PATTERNS

# Compile all patterns into a single alternation regex at import time.
_BOILERPLATE_RE: re.Pattern[str] = re.compile(
    "|".join(f"(?:{p})" for p in BOILERPLATE_LINE_PATTERNS)
)

# Maximum number of consecutive blank lines allowed in the output.
_MAX_BLANK_LINES: int = 2


def _is_boilerplate(line: str) -> bool:
    """Return True if *line* (stripped) matches any boilerplate pattern."""
    return bool(_BOILERPLATE_RE.fullmatch(line.strip()))


def remove_boilerplate(text: str) -> str:
    """
    Remove every line that matches a boilerplate pattern, then collapse
    runs of more than _MAX_BLANK_LINES consecutive empty lines.

    Parameters
    ----------
    text : raw Markdown content

    Returns
    -------
    str : Markdown with noise lines removed and blank lines normalised.
    """
    # Pass 1: drop boilerplate lines
    kept: list[str] = [
        line for line in text.split("\n")
        if not _is_boilerplate(line)
    ]

    # Pass 2: collapse excessive blank lines
    result: list[str] = []
    blank_run = 0
    for line in kept:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= _MAX_BLANK_LINES:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)

    return "\n".join(result)
