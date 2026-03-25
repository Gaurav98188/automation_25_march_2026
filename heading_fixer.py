"""
heading_fixer.py
----------------
Corrects Markdown heading levels that the PDF extractor assigns incorrectly.

The PDF extractor often promotes or demotes headings based on font size
rather than document structure.  This module reassigns heading depth by
inspecting the heading's *content* rather than its current `#` prefix.

Correction rules
----------------
  Content pattern         Correct depth   Examples
  ───────────────────     ─────────────   ──────────────────────────
  N.N.N.N …              #####           (depth-4 numbered sections)
  N.N.N …                ####            3.2.1.  3.3.1.
  N.N …                  ###             1.1.  2.1.  3.2.
  N. …                   ##              1.  2.  3.  4.
  (N). …  or  (N) …      #####           (1).  (11).
  ■ …                    ######          ■蓄積データ  ■操作仕様
  記 録 MEMO              (drop line)     PDF header artefact
  MITSUBISHI …            (drop line)     PDF header artefact

Public API
----------
    fix_headings(text) -> str
"""

from __future__ import annotations

import re

# ── Classifiers ───────────────────────────────────────────────────────────────

_NUM4_RE    = re.compile(r"\d+\.\d+\.\d+\.\d+")   # N.N.N.N
_NUM3_RE    = re.compile(r"\d+\.\d+\.\d+")         # N.N.N
_NUM2_RE    = re.compile(r"\d+\.\d+")              # N.N
_NUM1_RE    = re.compile(r"\d+\.")                 # N.
_PAREN_RE   = re.compile(r"\(\d+\)")               # (N)
_DROP_RE    = re.compile(r"記\s*録\s+MEMO|MITSUBISHI ELECTRIC SOFTWARE")


# ── Core logic ────────────────────────────────────────────────────────────────

def _rewrite_heading(content: str) -> str | None:
    """
    Given the heading text *content* (leading `#` chars and whitespace
    already stripped), return the correctly prefixed heading line, or
    None to signal that the line should be dropped entirely.

    Returns None (keep-unchanged sentinel) for content that does not
    match any known pattern — the caller will preserve the original line.
    """
    if _DROP_RE.match(content):
        return None                         # sentinel: drop this line

    if _NUM4_RE.match(content):
        return "##### " + content           # N.N.N.N → H5
    if _NUM3_RE.match(content):
        return "#### " + content            # N.N.N   → H4
    if _NUM2_RE.match(content):
        return "### " + content             # N.N     → H3
    if _NUM1_RE.match(content):
        return "## " + content              # N.      → H2
    if _PAREN_RE.match(content):
        return "##### " + content           # (N).    → H5
    if content.startswith("■"):
        return "###### " + content          # ■…      → H6

    return None                             # sentinel: keep original


def fix_headings(text: str) -> str:
    """
    Rewrite every Markdown heading line to its correct depth.

    Lines that are headings (`#`-prefixed) are reclassified.  Lines that
    match artefact patterns are dropped entirely.  All other lines pass
    through unchanged.

    Parameters
    ----------
    text : Markdown content

    Returns
    -------
    str : Markdown with corrected heading levels.
    """
    result: list[str] = []

    for line in text.split("\n"):
        if not line.startswith("#"):
            result.append(line)
            continue

        content   = line.lstrip("#").lstrip()
        corrected = _rewrite_heading(content)

        if corrected is None and _DROP_RE.match(content):
            continue                    # drop artefact heading
        elif corrected is None:
            result.append(line)         # no pattern matched — keep as-is
        else:
            result.append(corrected)

    return "\n".join(result)
