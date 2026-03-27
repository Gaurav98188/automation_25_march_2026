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
    lines = text.split("\n")

    result: list[str] = []
    blank_run = 0
    pending_page_number: str | None = None

    for line in lines:
        stripped = line.strip()

        # ✅ Capture page number (but don't output yet)
        if re.fullmatch(r"\d{1,3}", stripped):
            pending_page_number = stripped
            continue  # remove original number line

        # ✅ When PageBreak comes, insert correct page number
        if stripped == "<!-- PageBreak -->":
            if pending_page_number is not None:
                result.append(f"<!-- PageNumber: {pending_page_number} -->")
                pending_page_number = None

            result.append(line)  # keep PageBreak
            continue

        # Remove boilerplate
        if _is_boilerplate(line):
            continue

        # Collapse blank lines
        if stripped == "":
            blank_run += 1
            if blank_run <= _MAX_BLANK_LINES:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)

    return "\n".join(result)