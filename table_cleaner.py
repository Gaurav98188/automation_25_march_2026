"""
table_cleaner.py
----------------
Fixes two classes of HTML table corruption that arise when a PDF
page break lands in the middle of a table:

  Problem 1 — Page comments inside tables
      <!-- PageNumber: N --> and <!-- PageBreak --> comments appear
      between <tr> rows inside a <table>…</table> block, which
      produces invalid HTML.
      Fix: buffer these comments while inside a table and re-emit
      them immediately after the closing </table> tag.

  Problem 2 — Empty <tr> blocks
      The page-break artefact sometimes leaves behind empty row pairs:
          <tr>
          </tr>
      Fix: remove them with a regex.

Public API
----------
    clean_tables(text) -> str
"""

from __future__ import annotations

import re

# Matches <!-- PageNumber: N --> and <!-- PageBreak --> comment lines.
_PAGE_COMMENT_RE = re.compile(r"^\s*<!-- Page(Number|Break)[^>]*-->\s*$")

# Matches empty <tr>…</tr> pairs (whitespace only between tags).
_EMPTY_TR_RE = re.compile(r"<tr>\s*\n\s*</tr>", re.MULTILINE)


def clean_tables(text: str) -> str:
    """
    Apply both table-cleaning passes to *text*.

    Parameters
    ----------
    text : Markdown content

    Returns
    -------
    str : Markdown with table artefacts fixed.
    """
    text = _move_page_comments_after_tables(text)
    text = _EMPTY_TR_RE.sub("", text)
    return text


def _move_page_comments_after_tables(text: str) -> str:
    """
    Walk the document line by line, tracking whether we are currently
    inside a <table> block.  Any page-comment line found inside a table
    is buffered and re-emitted after the matching </table> tag.
    """
    lines = text.split("\n")
    result:   list[str] = []
    buffered: list[str] = []
    inside_table = False

    for line in lines:
        lower = line.lower()

        if "<table" in lower:
            inside_table = True

        if inside_table and _PAGE_COMMENT_RE.match(line):
            buffered.append(line)    # hold — will emit after </table>
            continue

        if "</table>" in lower:
            inside_table = False
            result.append(line)
            if buffered:
                result.extend(buffered)
                buffered.clear()
            continue

        result.append(line)

    # Safety flush (should not occur with valid paired tags)
    result.extend(buffered)
    return "\n".join(result)
