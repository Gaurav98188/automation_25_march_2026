"""
footer_table_remover.py
-----------------------
Removes PDF page-footer tables that the PDF-to-Markdown extractor
captures verbatim.  These tables appear in two forms:

Form A — standalone footer table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The entire table is footer noise (company name, DWG number, date/approver
row).  The whole ``<table>…</table>`` block is deleted.

Example::

    <table>
    <tr>
      <th colspan="4">MITSUBISHI ELECTRIC SOFTWARE</th>
      <th colspan="2" rowspan="2">TITLE データ管理機能 ソフトウェア仕様書</th>
    </tr>
    <tr>
      <td colspan="2" rowspan="2"></td>
      <td rowspan="2">作成·照査 DRAWN</td>
      <td rowspan="2"></td>
    </tr>
    <tr>
      <td rowspan="2">DWG.NO.<br>MCO23-01K0004</td>
      <td rowspan="2">6</td>
    </tr>
    <tr>
      <td>日 付 DATE</td>
      <td></td>
      <td>設計 • 検認 APPROVED</td>
      <td></td>
    </tr>
    </table>

Form B — content table with trailing footer rows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A real specification table (with actual content rows) has extra footer rows
appended at the end.  Only the trailing footer rows are stripped; the
content rows and the ``</table>`` tag are kept.

Example (the last 4 rows are footer noise)::

    <table>
    <tr><th>記 録</th><th>No</th>…</tr>    ← real content
    …
    <tr><td>10</td><td>クラウド…</td></tr> ← last real content row
    <tr><td></td>…</tr>                    ← footer starts here
    <tr><td colspan="5">MITSUBISHI…</td></tr>
    <tr><td colspan="5">作成·照査 DRAWN…</td></tr>
    <tr><td>日 DATE</td><td>付…APPROVED…</td></tr>
    </table>

Detection logic
---------------
A table row is classified as **footer noise** if its full text contains any
of the keywords in ``FOOTER_ROW_KEYWORDS`` OR if it is entirely empty.

A table is classified as:
- ``footer_only``  — every row is footer noise  → delete the whole table
- ``mixed``        — some leading rows are real content, trailing rows are
                      footer noise  → strip the trailing footer rows
- ``content``      — no footer noise rows at all  → keep untouched

The revision table (改定欄) is excluded from this logic because it
legitimately contains "DRAWN", "CHECKED", "APPROVED" in its header row and
is already handled by ``cover_replacer.replace_revision_table()``.

Public API
----------
    remove_footer_tables(text) -> str
"""

from __future__ import annotations
import re
from bs4 import BeautifulSoup

# ── Footer row detection ──────────────────────────────────────────────────────
# A row whose text contains any of these strings is considered footer noise.
# These strings appear exclusively in the decorative page-border band of each
# PDF page — never in real specification content.
FOOTER_ROW_KEYWORDS: tuple[str, ...] = (
    "MITSUBISHI ELECTRIC SOFTWARE",
    "DWG.NO.",
    "DWG. NO.",
    "設計 • 検認",
    "設計·検認",
    "設計 · 検認",
    "作成·照査",
    "作成 · 照査",
    "日 付 DATE",
    "TITLE データ管理機能",
)

# Tables containing this string are the revision table (改定欄), which is
# handled elsewhere and must not be touched here.
_REVISION_TABLE_MARKER = "内 容 CONTENTS"

# Regex to find all <table>…</table> blocks (including multiline content).
_TABLE_RE = re.compile(r"<table[\s\S]*?</table>", re.IGNORECASE)


# ── Row classifier ────────────────────────────────────────────────────────────

def _is_footer_row(row_text: str) -> bool:
    """
    Return True if *row_text* (full text of a <tr>) is footer noise.
    An empty row also counts as footer noise.
    """
    stripped = row_text.strip()
    if not stripped:
        return True
    return any(kw in stripped for kw in FOOTER_ROW_KEYWORDS)


# ── Table classifier ──────────────────────────────────────────────────────────

def _classify_table(html: str) -> str:
    """
    Classify a ``<table>…</table>`` block.

    Returns
    -------
    "footer_only"  — entire table is noise; delete it.
    "mixed"        — real content rows + trailing footer rows; strip footer rows.
    "content"      — keep as-is.
    """
    # Never touch the revision table
    if _REVISION_TABLE_MARKER in html:
        return "content"

    # Tables with a <caption> always contain specification content and must never
    # be deleted entirely.  However, they may still have trailing footer rows
    # that need stripping — handled by falling through to the "mixed" check below.
    has_caption = "<caption" in html.lower()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return "content"

    rows = table.find_all("tr")
    if not rows:
        return "content"

    row_texts = [r.get_text(separator=" ") for r in rows]
    footer_flags = [_is_footer_row(t) for t in row_texts]

    if all(footer_flags) and not has_caption:
        return "footer_only"
    elif all(footer_flags) and has_caption:
        # Unlikely but safe: a captioned table where all rows are footer noise
        # — treat as mixed so we strip rows rather than delete the whole table
        return "mixed"

    # Find the last row index that is real content
    last_real_idx = max(
        (i for i, flag in enumerate(footer_flags) if not flag),
        default=-1,
    )

    if last_real_idx < len(rows) - 1:
        # There are footer rows after the last real content row.
        # If the table has a caption it can only be "mixed" (never deleted).
        return "mixed"

    return "content"


# ── Table transformers ────────────────────────────────────────────────────────

def _strip_trailing_footer_rows(html: str) -> str:
    """
    Remove trailing footer ``<tr>…</tr>`` rows from a mixed table and
    return the cleaned table HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")
    row_texts = [r.get_text(separator=" ") for r in rows]

    # Remove rows from the end while they are footer noise
    while rows and _is_footer_row(row_texts[-1]):
        rows[-1].decompose()
        rows.pop()
        row_texts.pop()

    return str(soup)


# ── Public API ────────────────────────────────────────────────────────────────

def remove_footer_tables(text: str) -> str:
    """
    Remove PDF page-footer tables from the Markdown text.

    - Standalone footer-only tables are deleted entirely.
    - Content tables with trailing footer rows have those rows stripped.
    - Pure content tables and the revision table are left untouched.

    Parameters
    ----------
    text : Markdown content (after cover/revision replacement has run)

    Returns
    -------
    str : Markdown with footer tables removed.
    """
    def _replace(match: re.Match) -> str:
        html = match.group(0)
        classification = _classify_table(html)

        if classification == "footer_only":
            return ""                              # delete the whole table

        if classification == "mixed":
            return _strip_trailing_footer_rows(html)  # strip footer rows only

        return html                                # keep untouched

    return _TABLE_RE.sub(_replace, text)