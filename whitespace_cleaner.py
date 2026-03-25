"""
whitespace_cleaner.py
---------------------
Final cosmetic pass over the assembled Markdown document:

  1. Normalise line endings: CRLF and bare CR → LF.
  2. Strip trailing whitespace from every line.
  3. Collapse runs of more than 2 consecutive blank lines into 2.
  4. Ensure the file ends with exactly one newline character.

This step runs last in the pipeline so that upstream transformations
do not need to worry about whitespace hygiene.

Public API
----------
    clean_whitespace(text) -> str
"""

from __future__ import annotations

import re

_EXCESS_BLANKS_RE = re.compile(r"\n{4,}")


def clean_whitespace(text: str) -> str:
    """
    Apply all whitespace normalisations.

    Parameters
    ----------
    text : assembled Markdown content

    Returns
    -------
    str : normalised Markdown content.
    """
    # 1. Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Strip trailing spaces/tabs from each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    # 3. Collapse runs of 4+ newlines (≥ 3 consecutive blank lines) to 3 newlines
    text = _EXCESS_BLANKS_RE.sub("\n\n\n", text)

    # 4. Single trailing newline
    text = text.rstrip("\n") + "\n"

    return text
