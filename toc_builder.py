from __future__ import annotations
import re

def _build_toc_html(toc_entries):

    lines = [
        "\n## 目次\n\n",
        '<table style="width:100%; border-collapse:collapse;" border="1">\n',
        "<tr>\n",
        '<th style="width:10%; text-align:center;">区分</th>\n',
        '<th style="width:75%;">表題</th>\n',
        '<th style="width:15%; text-align:center;">頁</th>\n',
        "</tr>\n"
    ]

    for level, anchor, title, page in toc_entries:

        # indentation based on level
        indent_px = level

        # section number (extract 1, 1.1 etc.)
        section_no_match = re.match(r'([\d\.]+)', title)
        section_no = section_no_match.group(1) if section_no_match else ""

        lines.append("<tr>\n")

        # 区分 column (section number)
        lines.append(f'<td style="text-align:center;">{section_no}</td>\n')

        # 表題 column (WITH anchor link)
        lines.append(
            f'<td style="padding-left:{indent_px}px;">'
            f'<a href="#{anchor}">{title}</a></td>\n'
        )

        # 頁 column
        lines.append(
            f'<td style="text-align:center;">'
            f'<a href="#{anchor}">{page}</a></td>\n'
        )

        lines.append("</tr>\n")

    lines.append("</table>\n\n")

    return "".join(lines)


def replace_toc(text, toc_entries):

    if not toc_entries:
        return text

    toc_html = _build_toc_html(toc_entries)

    return re.sub(
        r'<table.*?>.*?</table>',
        toc_html,
        text,
        count=1,
        flags=re.DOTALL
    )