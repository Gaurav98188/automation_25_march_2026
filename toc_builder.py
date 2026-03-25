"""
toc_builder.py
--------------
Rebuilds the Table of Contents (目次) as a styled HTML table with
clickable anchor hyperlinks and left-indent hierarchy levels.

The section structure is defined in config.TOC_ENTRIES.  Update that
list when adapting the pipeline to a different document.

Public API
----------
    replace_toc(text) -> str
"""

from __future__ import annotations

from config import TOC_ENTRIES

_PAGE_BREAK = "<!-- PageBreak -->"


def _build_toc_html() -> str:
    """
    Build the full TOC HTML string from TOC_ENTRIES.

    Each top-level entry (indent == 0) receives a rowspan <td> on the
    left that spans all of its indented children, matching the original
    document's section-group visual style.
    """
    # Pre-process: compute rowspan for each top-level entry
    rows: list[tuple] = []
    i = 0
    while i < len(TOC_ENTRIES):
        indent, anchor, label, page = TOC_ENTRIES[i]
        if indent == 0:
            span = 1
            j = i + 1
            while j < len(TOC_ENTRIES) and TOC_ENTRIES[j][0] > 0:
                span += 1
                j += 1
            rows.append(("top", str(span), anchor, label, page))
            i += 1
        else:
            rows.append(("child", str(indent), anchor, label, page))
            i += 1

    # Build HTML lines
    lines: list[str] = [
        "\n## 目次\n\n",
        '<table style="width:100%; border-collapse:collapse; table-layout:fixed;" border="1">\n\n',
        "<tr>\n",
        '<th style="width:5%; text-align:center;">区分</th>\n',
        '<th style="width:90%;">表題</th>\n',
        '<th style="width:5%; text-align:center;">頁</th>\n',
        "</tr>\n\n",
    ]

    for row in rows:
        if row[0] == "top":
            _, span, anchor, label, page = row
            lines += [
                "<tr>\n",
                f'<td rowspan="{span}"></td>\n',
                f'<td><a href="#{anchor}">{label}</a></td>\n',
                f'<td style="text-align:center;"><a href="#{anchor}">{page}</a></td>\n',
                "</tr>\n\n",
            ]
        else:
            _, indent, anchor, label, page = row
            lines += [
                "<tr>\n",
                f'<td style="padding-left:{indent}px;"><a href="#{anchor}">{label}</a></td>\n',
                f'<td style="text-align:center;"><a href="#{anchor}">{page}</a></td>\n',
                "</tr>\n\n",
            ]

    lines.append("</table>\n\n")
    return "".join(lines)


def replace_toc(text: str) -> str:
    """
    Locate the TOC block (between page breaks 2 and 3), verify it contains
    TOC content, and replace it with the rebuilt anchor-linked table.

    Parameters
    ----------
    text : Markdown content after cover and revision table have been replaced.

    Returns
    -------
    str : Markdown with the TOC replaced.
    """
    # Collect all page-break positions
    breaks: list[int] = []
    start = 0
    while True:
        pos = text.find(_PAGE_BREAK, start)
        if pos == -1:
            break
        breaks.append(pos)
        start = pos + 1

    if len(breaks) < 3:
        return text

    toc_start = breaks[1] + len(_PAGE_BREAK)
    toc_end   = breaks[2]
    toc_block = text[toc_start:toc_end]

    if "目" not in toc_block and "CONTENTS" not in toc_block:
        return text

    new_toc = _build_toc_html()
    return (
        text[:toc_start]
        + "\n\n"
        + new_toc
        + "\n<!-- PageNumber: 3 -->\n"
        + _PAGE_BREAK
        + "\n\n"
        + text[toc_end + len(_PAGE_BREAK):]
    )
